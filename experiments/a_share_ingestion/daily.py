"""Local port of the inspected daily collector; no import-time I/O."""

from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import timedelta
from pathlib import Path
from typing import Any

from .runtime import (
    BoundedAPI,
    PipelineError,
    add_io_arguments,
    atomic_csv,
    configure_paths,
    date_text,
    execution_guard,
    init_tushare,
    local_now,
    parse_symbols,
    pd,
    positive_int,
    provider_path,
    setup_logging,
    strip_exchange_symbol,
    transport_options,
    validate_symbol,
)

logger = logging.getLogger(__name__)
CSV_CACHE_DIR: Path
STATIC_DIR: Path
STOCK_BASIC_FILE: Path
RUN_STATE_FILE: Path


def configure(data_root: Path):
    global CSV_CACHE_DIR, STATIC_DIR, STOCK_BASIC_FILE, RUN_STATE_FILE
    configure_paths(data_root)
    CSV_CACHE_DIR = provider_path("market_data_dir")
    STATIC_DIR = provider_path("static_dir")
    STOCK_BASIC_FILE = STATIC_DIR / "stock_basic.csv"
    RUN_STATE_FILE = data_root / "download_progress_tushare.json"


def normalize_symbol(ts_code: str) -> str:
    return strip_exchange_symbol(ts_code)


def ensure_stock_basic(pro) -> Any:
    if STOCK_BASIC_FILE.exists():
        df = pd.read_csv(STOCK_BASIC_FILE)
        if not df.empty:
            df["symbol"] = df["symbol"].astype(str).str.zfill(6)
            return df
    logger.info("stock_basic.csv 不存在，尝试从 Tushare 获取...")
    df = pro.stock_basic(
        exchange="", list_status="L", fields="ts_code,symbol,name,market,list_date"
    )
    df["symbol"] = df["symbol"].astype(str).str.zfill(6)
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    atomic_csv(df, STOCK_BASIC_FILE)
    return df


def get_stock_list(pro, include_st: bool = False) -> Any:
    df = ensure_stock_basic(pro)
    if not include_st and "name" in df.columns:
        df = df[~df["name"].astype(str).str.contains("ST", na=False)]
    logger.info(f"股票列表数量：{len(df)}")
    df["symbol"] = df["symbol"].map(lambda value: validate_symbol(str(value).zfill(6)))
    return df[["ts_code", "symbol", "name"]].copy()


def read_local_latest_date(symbol: str) -> Any | None:
    csv_path = CSV_CACHE_DIR / f"{symbol}.csv"
    if not csv_path.exists():
        return None
    try:
        df = pd.read_csv(csv_path, usecols=["date"])
        if df.empty:
            return None
        return pd.to_datetime(df["date"]).max()
    except (OSError, ValueError, KeyError, TypeError):
        return None


def determine_fetch_window(
    symbol: str,
    target_end: Any,
    full_history: bool = False,
    start_date: str | None = None,
):
    if start_date:
        return (
            True,
            pd.Timestamp(start_date).strftime("%Y%m%d"),
            target_end.strftime("%Y%m%d"),
            f"按指定区间补齐 {start_date} -> {target_end.strftime('%Y-%m-%d')}",
        )
    local_latest = read_local_latest_date(symbol)
    if full_history or local_latest is None:
        fetch_start = (target_end - timedelta(days=365 * 5)).strftime("%Y%m%d")
        return (
            True,
            fetch_start,
            target_end.strftime("%Y%m%d"),
            "全量初始化或本地无数据",
        )
    local_latest = pd.Timestamp(local_latest)
    if local_latest >= target_end:
        return False, None, None, f"已是最新 {local_latest.strftime('%Y-%m-%d')}"
    fetch_start = (local_latest + timedelta(days=1)).strftime("%Y%m%d")
    return (
        True,
        fetch_start,
        target_end.strftime("%Y%m%d"),
        f"增量补齐 {fetch_start} -> {target_end.strftime('%Y%m%d')}",
    )


def fetch_daily_data(pro, ts_code: str, start_date: str, end_date: str) -> Any:
    df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
    if df.empty:
        return pd.DataFrame()
    df = df.rename(
        columns={
            "trade_date": "date",
            "vol": "volume",
            "pct_chg": "pct_change",
            "amount": "amount",
        }
    )
    df["symbol"] = df["ts_code"].map(normalize_symbol)
    df["date"] = pd.to_datetime(df["date"])
    if (
        not df["ts_code"].eq(ts_code).all()
        or not df["date"].notna().all()
        or not df["date"]
        .between(pd.Timestamp(start_date), pd.Timestamp(end_date))
        .all()
        or df["date"].duplicated().any()
    ):
        raise PipelineError("daily response instrument/date scope mismatch")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce") * 100
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce") * 1000
    out = df[
        [
            "date",
            "symbol",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
            "pct_change",
        ]
    ].copy()
    return out.sort_values("date").reset_index(drop=True)


def merge_and_save_csv(new_df: Any, symbol: str):
    CSV_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    validate_symbol(symbol)
    path = CSV_CACHE_DIR / f"{symbol}.csv"
    if path.exists():
        old_df = pd.read_csv(path)
        if not old_df.empty:
            old_df["date"] = pd.to_datetime(old_df["date"])
            merged = pd.concat([old_df, new_df], ignore_index=True)
            merged = (
                merged.drop_duplicates(subset=["date"], keep="last")
                .sort_values("date")
                .reset_index(drop=True)
            )
        else:
            merged = new_df.copy()
    else:
        merged = new_df.copy()
    atomic_csv(merged, path)


def write_run_state(state: dict):
    RUN_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    RUN_STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def update_all_stocks(
    target_date: str | None = None,
    start_date: str | None = None,
    limit: int | None = None,
    include_st: bool = False,
    full_history: bool = False,
    *,
    max_requests: int,
    api: Any = None,
    symbols: tuple[str, ...] | None = None,
):
    pro = api if api is not None else init_tushare(max_requests)
    if symbols is None:
        stock_list = get_stock_list(pro, include_st=include_st)
    else:
        stock_list = pd.DataFrame(
            [
                {"ts_code": code, "symbol": normalize_symbol(code), "name": None}
                for code in symbols
            ]
        )
    if limit:
        stock_list = stock_list.head(limit)
    target_end = (
        pd.Timestamp(target_date) if target_date else pd.Timestamp(local_now().date())
    )
    total = len(stock_list)
    success_count = fail_count = skip_count = empty_count = 0
    processed = []
    for _, row in stock_list.iterrows():
        symbol = str(row["symbol"]).zfill(6)
        ts_code = row["ts_code"]
        need_fetch, fetch_start, fetch_end, reason = determine_fetch_window(
            symbol,
            target_end=target_end,
            full_history=full_history,
            start_date=start_date,
        )
        if not need_fetch:
            skip_count += 1
            processed.append({"symbol": symbol, "status": "skipped", "reason": reason})
            continue
        if fetch_start is None or fetch_end is None:
            raise PipelineError("missing declared fetch window")
        try:
            df = fetch_daily_data(
                pro, ts_code=ts_code, start_date=fetch_start, end_date=fetch_end
            )
            if df.empty:
                empty_count += 1
                processed.append(
                    {
                        "symbol": symbol,
                        "status": "empty",
                        "start_date": fetch_start,
                        "end_date": fetch_end,
                    }
                )
            else:
                merge_and_save_csv(df, symbol)
                success_count += 1
                processed.append(
                    {
                        "symbol": symbol,
                        "status": "updated",
                        "rows": len(df),
                        "start_date": fetch_start,
                        "end_date": fetch_end,
                    }
                )
            time.sleep(0.12)
        except PipelineError:
            raise
        except Exception as e:  # noqa: BLE001 -- retain per-stock failure, type-only logging
            fail_count += 1
            processed.append(
                {"symbol": symbol, "status": "failed", "error_type": type(e).__name__}
            )
            logger.warning("%s fetch failed: %s", symbol, type(e).__name__)
    summary = {
        "target_date": target_end.strftime("%Y-%m-%d"),
        "success_count": success_count,
        "fail_count": fail_count,
        "skip_count": skip_count,
        "empty_count": empty_count,
        "total": total,
        "processed": processed,
    }
    if isinstance(pro, BoundedAPI):
        summary["source_transport"] = pro.usage()
    write_run_state(summary)
    logger.info(
        f"完成：success={success_count} fail={fail_count} skip={skip_count} empty={empty_count}"
    )
    return summary


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Tushare 行情数据抓取脚本")
    add_io_arguments(parser, network=True)
    parser.add_argument("--target-date", type=date_text, required=True)
    parser.add_argument("--start-date", type=date_text, required=True)
    parser.add_argument("--limit", type=positive_int, required=True)
    parser.add_argument(
        "--symbols",
        type=parse_symbols,
        default=None,
        help="Explicit TS codes; bypasses stock_basic and does not assert ST/PIT eligibility",
    )
    parser.add_argument("--include-st", action="store_true")
    parser.add_argument("--full-history", action="store_true")
    args = parser.parse_args(argv)
    if args.start_date > args.target_date:
        raise PipelineError("start-date must not exceed target-date")
    if args.symbols is not None and len(args.symbols) > args.limit:
        raise PipelineError("explicit symbols exceed --limit")
    if not execution_guard(args, "daily"):
        return 0
    configure(args.data_root)
    api = init_tushare(args.max_requests, **transport_options(args))
    setup_logging(args.data_root)
    update_all_stocks(
        target_date=args.target_date,
        start_date=args.start_date,
        limit=args.limit,
        include_st=args.include_st,
        full_history=args.full_history,
        max_requests=args.max_requests,
        api=api,
        symbols=args.symbols,
    )


if __name__ == "__main__":
    main()
