"""Local port of industry taxonomy, Y/N membership and half-month daily collection."""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .runtime import (
    PROJECT_ROOT,
    PipelineError,
    add_io_arguments,
    atomic_csv,
    date_text,
    execution_guard,
    init_tushare,
    local_now,
    pd,
    provider_path,
    transport_options,
)

DEFAULT_SRC = "SW2021"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "a_share_ingestion" / "industry"
DEFAULT_DAILY_START_DATE = "20210101"

CLASSIFY_COLUMNS = (
    "index_code",
    "industry_name",
    "parent_code",
    "level",
    "industry_code",
    "is_pub",
    "src",
)
MEMBER_COLUMNS = (
    "l1_code",
    "l1_name",
    "l2_code",
    "l2_name",
    "l3_code",
    "l3_name",
    "ts_code",
    "name",
    "in_date",
    "out_date",
    "is_new",
)
DAILY_COLUMNS = (
    "ts_code",
    "trade_date",
    "name",
    "open",
    "low",
    "high",
    "close",
    "change",
    "pct_change",
    "vol",
    "amount",
    "pe",
    "pb",
    "float_mv",
)


def normalize_member_is_new_modes(value: str | Iterable[str] | None) -> list[str]:
    if value is None:
        return ["Y", "N"]
    if isinstance(value, str):
        raw_parts = value.replace(";", ",").split(",")
    else:
        raw_parts = []
        for item in value:
            raw_parts.extend(str(item).replace(";", ",").split(","))
    modes: list[str] = []
    for part in raw_parts:
        mode = str(part).strip().upper()
        if not mode:
            continue
        if mode not in {"Y", "N"}:
            raise ValueError(f"member_is_new must contain only Y/N, got: {part}")
        if mode not in modes:
            modes.append(mode)
    return modes or ["Y", "N"]


def normalize_date_text(value: str | None) -> str | None:
    if value in (None, "", "None", "NaT", "nan", "NaN"):
        return None
    if pd.isna(value):
        return None
    return pd.Timestamp(value).strftime("%Y%m%d")


def query_with_backoff(query_fn, *, sleep_seconds: float) -> Any:
    try:
        return query_fn()
    except Exception as exc:  # pragma: no cover - network-side retry path
        message = str(exc)
        if "频率超限" not in message:
            raise
        time.sleep(max(sleep_seconds, 60.0))
        return query_fn()


def month_windows(start_date: str, end_date: str) -> list[tuple[str, str]]:
    import calendar
    from datetime import date, timedelta

    start = date.fromisoformat(date_text(start_date))
    end = date.fromisoformat(date_text(end_date))
    if end < start:
        raise ValueError("end_date must be >= start_date")
    cursor = start.replace(day=1)
    windows = []
    while cursor <= end:
        last = date(
            cursor.year, cursor.month, calendar.monthrange(cursor.year, cursor.month)[1]
        )
        middle = cursor.replace(day=15)
        for left, right in ((cursor, middle), (middle + timedelta(days=1), last)):
            left, right = max(left, start), min(right, end)
            if left <= right:
                windows.append((left.strftime("%Y%m%d"), right.strftime("%Y%m%d")))
        cursor = last + timedelta(days=1)
    return windows


def normalize_classify_frame(
    frame: Any, *, src: str, fetched_at: str | None = None
) -> Any:
    if frame.empty:
        return pd.DataFrame(columns=[*CLASSIFY_COLUMNS, "fetched_at"])
    out = frame.copy()
    for column in CLASSIFY_COLUMNS[:-1]:
        if column not in out.columns:
            out[column] = None
    out["src"] = src
    out["index_code"] = out["index_code"].astype(str)
    out["industry_name"] = out["industry_name"].astype(str)
    out["parent_code"] = out["parent_code"].astype(str)
    out["level"] = out["level"].astype(str)
    out["industry_code"] = out["industry_code"].astype(str)
    out["is_pub"] = pd.to_numeric(out["is_pub"], errors="coerce")
    out["fetched_at"] = fetched_at or local_now().strftime("%Y-%m-%d %H:%M:%S")
    return out.loc[:, [*CLASSIFY_COLUMNS, "fetched_at"]]


def normalize_member_frame(frame: Any, *, fetched_at: str | None = None) -> Any:
    if frame.empty:
        return pd.DataFrame(columns=[*MEMBER_COLUMNS, "fetched_at"])
    out = frame.copy()
    for column in MEMBER_COLUMNS:
        if column not in out.columns:
            out[column] = None
    out["l1_code"] = out["l1_code"].astype(str)
    out["l1_name"] = out["l1_name"].astype(str)
    out["l2_code"] = out["l2_code"].astype(str)
    out["l2_name"] = out["l2_name"].astype(str)
    out["l3_code"] = out["l3_code"].astype(str)
    out["l3_name"] = out["l3_name"].astype(str)
    out["ts_code"] = out["ts_code"].astype(str)
    out["name"] = out["name"].astype(str)
    out["in_date"] = out["in_date"].astype(str).map(normalize_date_text)
    out["out_date"] = out["out_date"].astype(str).map(normalize_date_text)
    out["is_new"] = out["is_new"].astype(str)
    out["fetched_at"] = fetched_at or local_now().strftime("%Y-%m-%d %H:%M:%S")
    return out.loc[:, [*MEMBER_COLUMNS, "fetched_at"]]


def normalize_daily_frame(
    frame: Any,
    *,
    fetched_at: str | None = None,
    window_start: str | None = None,
    window_end: str | None = None,
) -> Any:
    if frame.empty:
        return pd.DataFrame(
            columns=[*DAILY_COLUMNS, "window_start", "window_end", "fetched_at"]
        )
    out = frame.copy()
    for column in DAILY_COLUMNS:
        if column not in out.columns:
            out[column] = None
    out["ts_code"] = out["ts_code"].astype(str)
    out["trade_date"] = out["trade_date"].map(
        lambda value: (
            None if pd.isna(value) else pd.Timestamp(value).strftime("%Y-%m-%d")
        )
    )
    out["name"] = out["name"].astype(str)
    for column in [
        "open",
        "low",
        "high",
        "close",
        "change",
        "pct_change",
        "vol",
        "amount",
        "pe",
        "pb",
        "float_mv",
    ]:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    out["window_start"] = window_start
    out["window_end"] = window_end
    out["fetched_at"] = fetched_at or local_now().strftime("%Y-%m-%d %H:%M:%S")
    return out.loc[:, [*DAILY_COLUMNS, "window_start", "window_end", "fetched_at"]]


def save_component(df: Any, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_csv(df, path)
    return path


def collect_industry_dataset(
    pro,
    *,
    src: str = DEFAULT_SRC,
    level: str | None = None,
    member_is_new: str | Iterable[str] | None = None,
    daily_start_date: str = DEFAULT_DAILY_START_DATE,
    daily_end_date: str | None = None,
    sleep_seconds: float = 1.3,
) -> dict[str, Any]:
    fetched_at = local_now().strftime("%Y-%m-%d %H:%M:%S")
    daily_end = daily_end_date or local_now().strftime("%Y%m%d")

    taxonomy_all = query_with_backoff(
        lambda: pro.index_classify(src=src), sleep_seconds=sleep_seconds
    )
    taxonomy_all = normalize_classify_frame(
        taxonomy_all, src=src, fetched_at=fetched_at
    )
    classify = taxonomy_all
    if level:
        classify = classify[
            classify["level"].astype(str).str.upper().eq(level.upper())
        ].reset_index(drop=True)

    member_frames: list[Any] = []
    member_is_new_modes = normalize_member_is_new_modes(member_is_new)
    member_codes = taxonomy_all.loc[
        taxonomy_all["level"].astype(str).str.upper().eq("L3")
        & pd.to_numeric(taxonomy_all["is_pub"], errors="coerce")
        .fillna(0)
        .astype(int)
        .eq(1),
        "index_code",
    ].tolist()
    for code in member_codes:
        l3_code = code if str(code).endswith(".SI") else f"{code}.SI"
        for is_new_mode in member_is_new_modes:
            frame = query_with_backoff(
                lambda value=l3_code, mode=is_new_mode: pro.index_member_all(
                    l3_code=value, is_new=mode
                ),
                sleep_seconds=sleep_seconds,
            )
            member_frames.append(normalize_member_frame(frame, fetched_at=fetched_at))
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

    member = (
        pd.concat(member_frames, ignore_index=True)
        if member_frames
        else pd.DataFrame(columns=[*MEMBER_COLUMNS, "fetched_at"])
    )
    if not member.empty:
        member["l3_code"] = member["l3_code"].astype(str)
        member["ts_code"] = member["ts_code"].astype(str)
        member = member.drop_duplicates(
            subset=["l3_code", "ts_code", "in_date", "out_date", "is_new"], keep="last"
        )
        member = member.sort_values(["l3_code", "ts_code", "in_date"]).reset_index(
            drop=True
        )

    daily_frames: list[Any] = []
    windows = month_windows(daily_start_date, daily_end)
    for window_start, window_end in windows:
        frame = query_with_backoff(
            lambda ws=window_start, we=window_end: pro.sw_daily(
                start_date=ws, end_date=we
            ),
            sleep_seconds=sleep_seconds,
        )
        daily_frames.append(
            normalize_daily_frame(
                frame,
                fetched_at=fetched_at,
                window_start=window_start,
                window_end=window_end,
            )
        )
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    daily = (
        pd.concat(daily_frames, ignore_index=True)
        if daily_frames
        else pd.DataFrame(
            columns=[*DAILY_COLUMNS, "window_start", "window_end", "fetched_at"]
        )
    )
    if not daily.empty:
        daily["trade_date"] = daily["trade_date"].astype(str)
        daily["ts_code"] = daily["ts_code"].astype(str)
        daily = daily.drop_duplicates(subset=["ts_code", "trade_date"], keep="last")
        daily = daily.sort_values(["trade_date", "ts_code"]).reset_index(drop=True)

    return {
        "classify": classify,
        "taxonomy_all": taxonomy_all,
        "member": member,
        "daily": daily,
    }


def write_industry_dataset(
    frames: dict[str, Any],
    output_dir: Path,
    *,
    src: str,
    level: str | None,
    member_is_new: str | Iterable[str] | None,
    member_l3_count: int,
    daily_start_date: str,
    daily_end_date: str,
    sleep_seconds: float,
    source_transport: dict[str, Any] | None = None,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)

    classify_path = save_component(
        frames["classify"], output_dir / "index_classify.csv"
    )
    taxonomy_path = save_component(
        frames["taxonomy_all"], output_dir / "index_classify_all.csv"
    )
    member_path = save_component(frames["member"], output_dir / "index_member_all.csv")
    daily_path = save_component(frames["daily"], output_dir / "sw_daily.csv")

    classify = frames["classify"]
    taxonomy_all = frames["taxonomy_all"]
    member = frames["member"]
    daily = frames["daily"]
    member_is_new_modes = normalize_member_is_new_modes(member_is_new)
    member_is_new_counts = (
        member["is_new"].fillna("").astype(str).str.upper().value_counts().to_dict()
        if not member.empty
        else {}
    )
    current_member = (
        member[member["is_new"].fillna("").astype(str).str.upper().eq("Y")]
        if not member.empty
        else member
    )
    historical_member = (
        member[member["is_new"].fillna("").astype(str).str.upper().eq("N")]
        if not member.empty
        else member
    )
    active_like_member = (
        member[
            member["out_date"].isna()
            | member["out_date"].fillna("").astype(str).str.strip().eq("")
        ]
        if not member.empty
        else member
    )

    payload = {
        "schema_version": 1,
        "generated_at": local_now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "tushare",
        "src": src,
        "level": level,
        "member_is_new": ",".join(member_is_new_modes),
        "member_is_new_modes": member_is_new_modes,
        "daily_window": {
            "start_date": daily_start_date,
            "end_date": daily_end_date,
            "split": "half-month",
            "sleep_seconds": sleep_seconds,
            "window_count": len(month_windows(daily_start_date, daily_end_date)),
            "member_l3_count": member_l3_count,
        },
        "rows": {
            "taxonomy_all": len(taxonomy_all),
            "classify": len(classify),
            "classify_published": int(
                pd.to_numeric(classify.get("is_pub"), errors="coerce")
                .fillna(0)
                .astype(int)
                .sum()
            )
            if not classify.empty
            else 0,
            "member": len(member),
            "member_current": len(current_member),
            "member_historical": len(historical_member),
            "member_active_like": len(active_like_member),
            "daily": len(daily),
        },
        "member_coverage": {
            "is_new_counts": {
                str(key): int(value) for key, value in member_is_new_counts.items()
            },
            "l1_count": int(member["l1_code"].nunique()) if not member.empty else 0,
            "l2_count": int(member["l2_code"].nunique()) if not member.empty else 0,
            "l3_count": int(member["l3_code"].nunique()) if not member.empty else 0,
            "symbol_count": int(member["ts_code"].nunique()) if not member.empty else 0,
            "current_symbol_count": int(current_member["ts_code"].nunique())
            if not current_member.empty
            else 0,
            "historical_symbol_count": int(historical_member["ts_code"].nunique())
            if not historical_member.empty
            else 0,
            "active_like_symbol_count": int(active_like_member["ts_code"].nunique())
            if not active_like_member.empty
            else 0,
        },
        "daily_coverage": {
            "start": daily["trade_date"].min() if not daily.empty else None,
            "end": daily["trade_date"].max() if not daily.empty else None,
            "index_count": int(daily["ts_code"].nunique()) if not daily.empty else 0,
        },
        "level_counts": classify["level"].value_counts().sort_index().to_dict()
        if not classify.empty
        else {},
        "files": {
            "index_classify_csv": str(classify_path),
            "index_classify_all_csv": str(taxonomy_path),
            "index_member_all_csv": str(member_path),
            "sw_daily_csv": str(daily_path),
        },
    }
    if source_transport is not None:
        payload["source_transport"] = source_transport
    (output_dir / "manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch and package Tushare SW industry data into local evidence files."
    )
    add_io_arguments(parser, network=True)
    parser.add_argument(
        "--src", default=DEFAULT_SRC, help="申万版本，例如 SW2021 或 SW2014"
    )
    parser.add_argument(
        "--level",
        default=None,
        choices=["L1", "L2", "L3"],
        help="可选：只拉某个分级的行业分类",
    )
    parser.add_argument(
        "--member-is-new",
        default="Y,N",
        help="行业成分 is_new 模式，逗号分隔；默认 Y,N 同时拉当前最新和历史非最新成员",
    )
    parser.add_argument(
        "--start-date", type=date_text, required=True, help="daily 起始日期 YYYYMMDD"
    )
    parser.add_argument(
        "--end-date",
        type=date_text,
        required=True,
        help="daily 结束日期 YYYYMMDD，默认今天",
    )
    parser.add_argument("--output-dir", default=None, help="输出证据目录")
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=1.3,
        help="Tushare 调用间隔，避免频率限制",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON 摘要")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.start_date > args.end_date:
        raise PipelineError("start-date must not exceed end-date")
    if not execution_guard(args, "industry"):
        return 0
    pro = init_tushare(args.max_requests, **transport_options(args))
    frames = collect_industry_dataset(
        pro,
        src=args.src,
        level=args.level,
        member_is_new=args.member_is_new,
        daily_start_date=args.start_date,
        daily_end_date=args.end_date,
        sleep_seconds=args.sleep_seconds,
    )
    summary = write_industry_dataset(
        frames,
        Path(args.output_dir)
        if args.output_dir
        else provider_path("industry_evidence_dir"),
        src=args.src,
        level=args.level,
        member_is_new=args.member_is_new,
        member_l3_count=int(frames["member"]["l3_code"].nunique())
        if not frames["member"].empty
        else 0,
        daily_start_date=args.start_date,
        daily_end_date=args.end_date or local_now().strftime("%Y%m%d"),
        sleep_seconds=args.sleep_seconds,
        source_transport=pro.usage(),
    )
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("Tushare industry dataset")
        print(f"Classify rows: {summary['rows']['classify']}")
        print(f"Member rows: {summary['rows']['member']}")
        print(f"Daily rows: {summary['rows']['daily']}")
        print(f"Output: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
