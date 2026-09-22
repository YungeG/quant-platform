"""Read frozen local CSVs and emit an explainable, diagnostic-only regime JSON."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal, DecimalException
from pathlib import Path

from experiments.a_share_market_regime import (
    CHINA_TZ,
    DEFAULT_CONFIG,
    EvaluationBasis,
    MarketPhase,
    PublishedIndexClose,
    evaluate_market_regime,
)
from experiments.a_share_risk_state import PricePoint
from experiments.a_share_sector_opportunities import (
    DEFAULT_SCREEN_CONFIG,
    PublishedStockClose,
    evaluate_sector_opportunities,
)

PHASE_LABELS = {
    MarketPhase.BULL: "牛市",
    MarketPhase.BEAR: "熊市",
    MarketPhase.TRANSITION: "震荡/转换期",
    MarketPhase.UNKNOWN: "无法判断",
}


def _read_csv(path: Path, required: set[str]) -> tuple[list[dict[str, str]], str]:
    content = path.read_bytes()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")), strict=True)
    headers = reader.fieldnames
    if not headers or len(headers) != len(set(headers)) or not required.issubset(headers):
        raise ValueError(f"{path}: unique headers including {sorted(required)} are required")
    rows = []
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"{path}:{reader.line_num}: row width must match headers")
        if any(not row[column].strip() for column in required):
            raise ValueError(f"{path}:{reader.line_num}: required values cannot be empty")
        rows.append(row)
    return rows, hashlib.sha256(content).hexdigest()


def _json_value(value: object) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"cannot serialize {type(value).__name__}")


def _flag(value: str, name: str) -> bool:
    if value.strip() not in ("0", "1"):
        raise ValueError(f"{name} must be 0 or 1")
    return value.strip() == "1"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="A股牛熊阶段诊断（本地收盘数据，不授权交易）")
    parser.add_argument("--prices", required=True, type=Path, help="指数收盘 CSV")
    parser.add_argument("--calendar", required=True, type=Path, help="含休市日的完整交易日历 CSV")
    evaluation_time = parser.add_mutually_exclusive_group(required=True)
    evaluation_time.add_argument("--as-of", help="固定评估时点，如 2025-06-30T16:00:00+08:00")
    evaluation_time.add_argument(
        "--now", action="store_true",
        help="显式使用系统当前时刻评估最近已收盘交易日；仍须提供最新本地快照，不联网",
    )
    parser.add_argument(
        "--basis", choices=[basis.value for basis in EvaluationBasis], default="historical",
        help="historical：原历史点时确认；snapshot：只用 as-of 已知版本重算当前形态，不证明历史当时确认",
    )
    parser.add_argument("--stocks", type=Path, help="可选：含板块/状态/复权价格/成交额的股票 CSV")
    parser.add_argument("--sectors", nargs="+", help="可选：只观察这些板块（精确名称，与 --stocks 同时指定）")
    args = parser.parse_args(argv)
    if (args.stocks is None) != (args.sectors is None):
        parser.error("--stocks and --sectors must be supplied together")
    if args.basis == "snapshot" and args.stocks is not None:
        parser.error("--basis snapshot is diagnostic-only and cannot be used with --stocks/--sectors")
    screening = None
    stocks_hash = None
    try:
        # Capture once, before any input I/O. A file read must not move the cutoff.
        as_of = datetime.now(CHINA_TZ) if args.now else datetime.fromisoformat(args.as_of)
        price_rows, prices_hash = _read_csv(
            args.prices, {"ts_code", "trade_date", "close", "available_at"}
        )
        calendar_rows, calendar_hash = _read_csv(args.calendar, {"cal_date", "is_open"})
        calendar: dict[date, bool] = {}
        for row in calendar_rows:
            day = date.fromisoformat(row["cal_date"].strip())
            is_open = row["is_open"].strip()
            if day in calendar:
                raise ValueError(f"duplicate calendar date: {day}")
            if is_open not in ("0", "1"):
                raise ValueError(f"{day}: is_open must be 0 or 1")
            calendar[day] = is_open == "1"
        observations = tuple(
            PublishedIndexClose(
                row["ts_code"].strip(),
                PricePoint(date.fromisoformat(row["trade_date"].strip()), Decimal(row["close"].strip())),
                datetime.fromisoformat(row["available_at"].strip()),
            )
            for row in price_rows
        )
        if args.stocks is not None:
            stock_rows, stocks_hash = _read_csv(args.stocks, {
                "ts_code", "sector", "trade_date", "adj_close", "amount_cny",
                "is_st", "is_suspended", "available_at",
            })
            stocks = tuple(PublishedStockClose(
                instrument=row["ts_code"].strip(),
                sector=row["sector"].strip(),
                point=PricePoint(date.fromisoformat(row["trade_date"].strip()), Decimal(row["adj_close"].strip())),
                amount_cny=Decimal(row["amount_cny"].strip()),
                is_st=_flag(row["is_st"], "is_st"),
                is_suspended=_flag(row["is_suspended"], "is_suspended"),
                available_at=datetime.fromisoformat(row["available_at"].strip()),
            ) for row in stock_rows)
            screening = evaluate_sector_opportunities(
                index_observations=observations, stock_observations=stocks,
                calendar=calendar, as_of=as_of,
                selected_sectors=tuple(sector.strip() for sector in args.sectors),
            )
            result = screening.market
        else:
            result = evaluate_market_regime(
                observations=observations, calendar=calendar, as_of=as_of,
                basis=EvaluationBasis(args.basis),
            )
    except (OSError, UnicodeError, csv.Error, ValueError, TypeError, DecimalException) as exc:
        parser.error(str(exc))

    sources = {
        "prices": {"path": str(args.prices), "sha256": prices_hash},
        "calendar": {"path": str(args.calendar), "sha256": calendar_hash},
    }
    if stocks_hash is not None:
        sources["stocks"] = {"path": str(args.stocks), "sha256": stocks_hash}
    result_payload = asdict(result)
    if result.basis is EvaluationBasis.HISTORICAL:
        result_payload.pop("basis")  # Preserve the original v1 JSON/replay bytes.
    payload = {
        "strategy": "a_share_market_regime_v1",
        "authority": "diagnostic_only",
        "trade_authorized": False,
        "as_of_source": "system_clock" if args.now else "explicit",
        "phase_label": PHASE_LABELS[result.phase],
        "config": asdict(DEFAULT_CONFIG),
        "sources": sources,
        "result": result_payload,
    }
    if result.basis is EvaluationBasis.SNAPSHOT:
        payload.update({
            "strategy": "a_share_market_snapshot_v1",
            "phase_label": f"{PHASE_LABELS[result.phase]}（当前快照重算，非历史点时确认）",
            "historical_confirmation_claimed": False,
            "limitations": [
                "仅使用 as-of 前已知版本重算最近收盘形态；过去窗口标签不是当时发布的信号。",
                "不是盘中或转折预测；三指数代理不等于全A个股广度；不是交易指令。",
                "未据此执行收益/OOS验证，不是正式Research/Backtest/Validation证据。",
            ],
        })
    if screening is not None:
        details = asdict(screening)
        details.pop("market")  # The identical market evaluation already lives under result.
        payload["screening"] = {
            "strategy": "a_share_sector_opportunities_v1",
            "config": asdict(DEFAULT_SCREEN_CONFIG),
            "limitations": [
                "高波动不等于获利机会；名单仅供观察，不授权交易。",
                "只检查输入股票池，不证明板块成员完整；点时归属、状态与复权数据真实性须由输入方核验。",
                "未核验涨跌停、公告风险、T+1、成本或可成交性；未验证样本外收益。",
            ],
            **details,
        }
    print(json.dumps(payload, default=_json_value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    return 1 if result.phase is MarketPhase.UNKNOWN or (screening is not None and not screening.complete) else 0


if __name__ == "__main__":
    raise SystemExit(main())
