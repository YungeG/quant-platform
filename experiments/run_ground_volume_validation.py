"""Validate the market-wide 'ground volume' regime without touching strategy code."""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
from datetime import date, datetime
from pathlib import Path
from typing import Iterable


CARRIERS = (
    ("csi300_total_return", "H00300.CSI"),
    ("csi500_total_return", "H00905.CSI"),
    ("csi1000_total_return", "H00852.CSI"),
    ("csi_dividend_total_return", "H00922.CSI"),
)
FOLDS = (
    ("2015-2018", date(2015, 1, 1), date(2018, 12, 31)),
    ("2019-2022", date(2019, 1, 1), date(2022, 12, 31)),
    ("2023-end", date(2023, 1, 1), date.max),
)


def rolling_volume_scores(values: list[float], window: int = 250) -> list[float | None]:
    """Match the prior study: current turnover rank against the previous window-1 days."""
    scores: list[float | None] = [None] * len(values)
    for index in range(window - 1, len(values)):
        current = values[index]
        previous = values[index - window + 1 : index]
        percentile = sum(current > value for value in previous) / len(previous)
        scores[index] = 1.0 - percentile
    return scores


def month_end_indices(dates: list[date]) -> list[int]:
    indices: list[int] = []
    for index, current in enumerate(dates):
        if index == len(dates) - 1 or (
            dates[index + 1].year,
            dates[index + 1].month,
        ) != (current.year, current.month):
            indices.append(index)
    return indices


def _mean(values: Iterable[float]) -> float | None:
    items = list(values)
    return statistics.fmean(items) if items else None


def _spread(samples: list[dict]) -> dict:
    ground = [item["forward_return"] for item in samples if item["score"] >= 0.80]
    high = [item["forward_return"] for item in samples if item["score"] <= 0.20]
    ground_mean = _mean(ground)
    high_mean = _mean(high)
    return {
        "spread": None if ground_mean is None or high_mean is None else ground_mean - high_mean,
        "ground_mean": ground_mean,
        "high_volume_mean": high_mean,
        "ground_n": len(ground),
        "high_volume_n": len(high),
    }


def prediction_statistics(
    dates: list[date],
    closes: list[float],
    scores: list[float | None],
    horizon: int = 120,
) -> dict:
    monthly: list[dict] = []
    for ordinal, index in enumerate(month_end_indices(dates)):
        if scores[index] is None or index + horizon >= len(closes):
            continue
        monthly.append(
            {
                "date": dates[index],
                "ordinal": ordinal,
                "score": float(scores[index]),
                "forward_return": closes[index + horizon] / closes[index] - 1.0,
            }
        )

    folds = {}
    for name, start, end in FOLDS:
        folds[name] = _spread(
            [item for item in monthly if start <= item["date"] <= end]
        )

    offsets = []
    for offset in range(6):
        result = _spread([item for item in monthly if item["ordinal"] % 6 == offset])
        offsets.append({"offset": offset, **result})
    valid_offset_spreads = [item["spread"] for item in offsets if item["spread"] is not None]

    entries = []
    previous_ground = False
    for item in monthly:
        ground = item["score"] >= 0.80
        if ground and not previous_ground:
            entries.append(item["forward_return"])
        previous_ground = ground

    full = _spread(monthly)
    positive_folds = sum(
        result["spread"] is not None and result["spread"] > 0 for result in folds.values()
    )
    positive_offsets = sum(value > 0 for value in valid_offset_spreads)
    median_offset = (
        statistics.median(valid_offset_spreads) if valid_offset_spreads else None
    )
    signal_go = bool(
        full["spread"] is not None
        and full["spread"] > 0
        and positive_folds >= 2
        and median_offset is not None
        and median_offset > 0
        and positive_offsets >= 4
    )
    return {
        "full": full,
        "folds": folds,
        "offsets": offsets,
        "positive_folds": positive_folds,
        "positive_offsets": positive_offsets,
        "median_offset_spread": median_offset,
        "minimum_offset_spread": min(valid_offset_spreads) if valid_offset_spreads else None,
        "ground_entry": {
            "mean_forward_return": _mean(entries),
            "n": len(entries),
        },
        "signal_go": signal_go,
        "monthly_sample_count": len(monthly),
    }


def _metrics(returns: list[float]) -> dict:
    if not returns:
        return {
            "cagr": None,
            "sharpe": None,
            "max_drawdown": None,
            "calmar": None,
        }
    nav = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for value in returns:
        nav *= 1.0 + value
        peak = max(peak, nav)
        max_drawdown = min(max_drawdown, nav / peak - 1.0)
    years = len(returns) / 252.0
    cagr = nav ** (1.0 / years) - 1.0 if years > 0 and nav > 0 else -1.0
    stdev = statistics.stdev(returns) if len(returns) > 1 else 0.0
    sharpe = statistics.fmean(returns) / stdev * math.sqrt(252) if stdev > 0 else 0.0
    calmar = cagr / abs(max_drawdown) if max_drawdown < 0 else float("inf")
    return {
        "cagr": cagr,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "calmar": calmar,
    }


def timing_returns(
    dates: list[date],
    closes: list[float],
    scores: list[float | None],
    cost_oneway: float = 0.001,
    cash_annual: float = 0.02,
) -> dict:
    month_ends = set(month_end_indices(dates))
    effective_targets: dict[int, float] = {}
    for index in month_ends:
        score = scores[index]
        if score is not None and index + 1 < len(dates):
            effective_targets[index + 1] = 1.0 if score >= 0.80 else 0.50

    cash_daily = (1.0 + cash_annual) ** (1.0 / 252.0) - 1.0
    exposure = 0.50
    timing: list[float] = []
    exposures: list[float] = []
    index_returns: list[float] = []
    total_turnover = exposure
    for index in range(1, len(dates)):
        change_cost = 0.0
        if index == 1:
            change_cost += exposure * cost_oneway
        if index in effective_targets:
            target = effective_targets[index]
            change = abs(target - exposure)
            total_turnover += change
            change_cost += change * cost_oneway
            exposure = target
        index_return = closes[index] / closes[index - 1] - 1.0
        timing.append(
            exposure * index_return
            + (1.0 - exposure) * cash_daily
            - change_cost
        )
        exposures.append(exposure)
        index_returns.append(index_return)

    average_exposure = statistics.fmean(exposures)
    constant = [
        average_exposure * value + (1.0 - average_exposure) * cash_daily
        for value in index_returns
    ]
    constant[0] -= average_exposure * cost_oneway
    buy_hold = list(index_returns)
    buy_hold[0] -= cost_oneway

    fold_results = {}
    return_dates = dates[1:]
    for name, start, end in FOLDS:
        selected = [index for index, current in enumerate(return_dates) if start <= current <= end]
        timing_fold = [timing[index] for index in selected]
        fold_exposure = [exposures[index] for index in selected]
        fold_index = [index_returns[index] for index in selected]
        fold_average = statistics.fmean(fold_exposure) if fold_exposure else 0.0
        fold_constant = [
            fold_average * value + (1.0 - fold_average) * cash_daily
            for value in fold_index
        ]
        if fold_constant:
            fold_constant[0] -= fold_average * cost_oneway
        timing_metrics = _metrics(timing_fold)
        constant_metrics = _metrics(fold_constant)
        fold_results[name] = {
            "timing": timing_metrics,
            "constant": constant_metrics,
            "calmar_delta": _finite_delta(
                timing_metrics["calmar"], constant_metrics["calmar"]
            ),
        }

    timing_metrics = _metrics(timing)
    constant_metrics = _metrics(constant)
    positive_fold_calmar = sum(
        result["calmar_delta"] is not None and result["calmar_delta"] >= 0
        for result in fold_results.values()
    )
    calmar_delta = _finite_delta(timing_metrics["calmar"], constant_metrics["calmar"])
    portfolio_go = bool(
        timing_metrics["cagr"] is not None
        and timing_metrics["cagr"] > 0
        and timing_metrics["sharpe"] > constant_metrics["sharpe"]
        and calmar_delta is not None
        and calmar_delta >= 0.05
        and positive_fold_calmar >= 2
    )
    return {
        "timing": timing_metrics,
        "constant_same_average_exposure": constant_metrics,
        "buy_and_hold": _metrics(buy_hold),
        "average_exposure": average_exposure,
        "total_turnover": total_turnover,
        "annual_turnover": total_turnover / (len(timing) / 252.0),
        "calmar_delta": calmar_delta,
        "positive_fold_calmar": positive_fold_calmar,
        "folds": fold_results,
        "portfolio_go": portfolio_go,
    }


def _finite_delta(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    if math.isinf(left) and math.isinf(right):
        return 0.0
    if math.isinf(left):
        return None
    if math.isinf(right):
        return None
    return left - right


def _read_token(env_file: Path) -> str:
    token = os.environ.get("TUSHARE_TOKEN")
    if token:
        return token
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("TUSHARE_TOKEN="):
                return line.split("=", 1)[1].strip().strip("'\"")
    raise RuntimeError("TUSHARE_TOKEN is required")


def load_turnover(duckdb_path: Path, start: str = "2014-01-01") -> list[tuple[date, float]]:
    import duckdb

    connection = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        rows = connection.execute(
            """
            SELECT TradingDay, sum(Amount) AS turnover
            FROM MarketData
            WHERE TradingDay >= ? AND Amount IS NOT NULL
            GROUP BY TradingDay
            ORDER BY TradingDay
            """,
            [start],
        ).fetchall()
    finally:
        connection.close()
    return [(row[0], float(row[1])) for row in rows if row[1] and row[1] > 0]


def load_index(
    code: str,
    start: str,
    end: str,
    cache_dir: Path,
    env_file: Path,
) -> list[tuple[date, float]]:
    cache_root = cache_dir.resolve()
    cache_root.mkdir(parents=True, exist_ok=True)
    safe_code = code.replace(".", "_")
    if not safe_code.replace("_", "").isalnum() or not start.isdigit() or not end.isdigit():
        raise ValueError("unsafe index cache identity")
    cache = (cache_root / f"{safe_code}_{start}_{end}.json").resolve()
    if cache_root not in cache.parents:
        raise ValueError("index cache path escapes cache root")
    if cache.exists():
        payload = json.loads(cache.read_text(encoding="utf-8"))
        return [(date.fromisoformat(item[0]), float(item[1])) for item in payload]

    import tushare as ts

    pro = ts.pro_api(_read_token(env_file))
    frame = pro.index_daily(ts_code=code, start_date=start, end_date=end)
    rows = sorted(
        (
            datetime.strptime(str(row.trade_date), "%Y%m%d").date(),
            float(row.close),
        )
        for row in frame.itertuples()
    )
    cache.write_text(
        json.dumps([[day.isoformat(), close] for day, close in rows]),
        encoding="utf-8",
    )
    return rows


def align_series(
    turnover: list[tuple[date, float]],
    index_rows: list[tuple[date, float]],
) -> tuple[list[date], list[float], list[float]]:
    turnover_by_date = dict(turnover)
    close_by_date = dict(index_rows)
    dates = sorted(set(turnover_by_date) & set(close_by_date))
    return (
        dates,
        [turnover_by_date[current] for current in dates],
        [close_by_date[current] for current in dates],
    )


def _safe_json(value):
    if isinstance(value, dict):
        return {key: _safe_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe_json(item) for item in value]
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def render_markdown(payload: dict) -> str:
    lines = [
        "# A股地量效应验证结果",
        "",
        f"- verdict: **{payload['verdict']}**",
        f"- signal GO carriers: {payload['signal_go_count']}/{len(payload['carriers'])}",
        f"- portfolio GO carriers: {payload['portfolio_go_count']}/{len(payload['carriers'])}",
        f"- data through: {payload['data_through']}",
        "",
        "| 载体 | 120日spread | 正时间折 | 正偏移 | 偏移中位 | Signal | Timing CAGR | Calmar Δ | Portfolio |",
        "| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |",
    ]
    for item in payload["carriers"]:
        prediction = item["prediction_120"]
        portfolio = item["portfolio"]
        lines.append(
            "| {label} | {spread} | {folds}/3 | {offsets}/6 | {median} | {signal} | {cagr} | {calmar} | {portfolio_go} |".format(
                label=item["label"],
                spread=_percent(prediction["full"]["spread"]),
                folds=prediction["positive_folds"],
                offsets=prediction["positive_offsets"],
                median=_percent(prediction["median_offset_spread"]),
                signal="GO" if prediction["signal_go"] else "NO",
                cagr=_percent(portfolio["timing"]["cagr"]),
                calmar=_number(portfolio["calmar_delta"]),
                portfolio_go="GO" if portfolio["portfolio_go"] else "NO",
            )
        )
    lines.extend(
        [
            "",
            "## Gate",
            "",
            "- GO：至少2个载体Signal GO，且至少1个载体Portfolio GO。",
            "- MARGINAL：至少2个载体Signal GO，但没有Portfolio GO。",
            "- NO-GO：少于2个载体Signal GO。",
        ]
    )
    return "\n".join(lines)


def _percent(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2%}"


def _number(value: float | None) -> str:
    return "n/a" if value is None else f"{value:+.3f}"


def run_study(
    duckdb_path: Path,
    cache_dir: Path,
    env_file: Path,
) -> dict:
    turnover = load_turnover(duckdb_path)
    end = turnover[-1][0].strftime("%Y%m%d")
    carriers = []
    for label, code in CARRIERS:
        index_rows = load_index(code, "20140101", end, cache_dir, env_file)
        dates, turnovers, closes = align_series(turnover, index_rows)
        scores = rolling_volume_scores(turnovers)
        predictions = {
            str(horizon): prediction_statistics(dates, closes, scores, horizon)
            for horizon in (20, 60, 120)
        }
        carriers.append(
            {
                "label": label,
                "code": code,
                "start": dates[0],
                "end": dates[-1],
                "n_days": len(dates),
                "prediction_20": predictions["20"],
                "prediction_60": predictions["60"],
                "prediction_120": predictions["120"],
                "portfolio": timing_returns(dates, closes, scores),
            }
        )

    signal_go_count = sum(item["prediction_120"]["signal_go"] for item in carriers)
    portfolio_go_count = sum(item["portfolio"]["portfolio_go"] for item in carriers)
    verdict = (
        "GO"
        if signal_go_count >= 2 and portfolio_go_count >= 1
        else "MARGINAL"
        if signal_go_count >= 2
        else "NO-GO"
    )
    return {
        "study": "a-share-ground-volume-validation-v1",
        "duckdb_path": str(duckdb_path),
        "data_through": turnover[-1][0],
        "signal_go_count": signal_go_count,
        "portfolio_go_count": portfolio_go_count,
        "verdict": verdict,
        "carriers": carriers,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--duckdb",
        default="/srv/bcache-8t/ygguo/duckdb/quant-a50/quant_a50.duckdb",
    )
    parser.add_argument(
        "--env-file",
        default="/home/ygguo/agent-projs/cycle-rotation-platform/.env",
    )
    parser.add_argument(
        "--cache-dir",
        default="/tmp/a-share-ground-volume-validation",
    )
    parser.add_argument(
        "--out-json",
        default="overall/a-share-ground-volume-validation.json",
    )
    parser.add_argument(
        "--out-md",
        default="overall/a-share-ground-volume-validation.md",
    )
    args = parser.parse_args(argv)

    payload = run_study(Path(args.duckdb), Path(args.cache_dir), Path(args.env_file))
    safe = _safe_json(payload)
    Path(args.out_json).write_text(
        json.dumps(safe, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown = render_markdown(safe)
    Path(args.out_md).write_text(markdown + "\n", encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
