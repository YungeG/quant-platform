#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import platform
import urllib.request
from bisect import bisect_right
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode
from zoneinfo import ZoneInfo

UTC = dt.timezone.utc
KRX_TZ = ZoneInfo("Asia/Seoul")
US_TZ = ZoneInfo("America/New_York")
BINANCE_BASE = "https://fapi.binance.com"
YAHOO_CHART_ENDPOINTS = (
    "https://query1.finance.yahoo.com/v8/finance/chart/",
    "https://query2.finance.yahoo.com/v8/finance/chart/",
)

LISTING_START = dt.datetime(2026, 6, 22, 13, 55, tzinfo=UTC)
SPLIT_START = dt.datetime(2026, 7, 15, 0, 15, tzinfo=UTC)
SPLIT_END = dt.datetime(2026, 7, 15, 9, 35, tzinfo=UTC)
HOUR_MS = 60 * 60 * 1000
LISTING_ANNOUNCEMENT_URL = "https://www.binance.com/en/support/announcement/detail/88ea4a4f9f0b4ad4b7b308195c026fe4"
SPLIT_ANNOUNCEMENT_URL = "https://www.binance.com/en/support/announcement/detail/c226162366c54b78a7f98021b38e10c5"
SPLIT_COMPLETION_URL = "https://www.binance.com/en/support/announcement/detail/2ce887ba8fe14fdaa088e5bed7553a4e"
DIREXION_SPLIT_URL = "https://www.direxion.com/press-release/direxion-to-split-nine-etfs"


YAHOO_SYMBOLS = [
    ("koru", "KORU"),
    ("ks200", "^KS200"),
    ("samsung", "005930.KS"),
    ("skhynix", "000660.KS"),
    ("mu", "MU"),
    ("sndk", "SNDK"),
    ("krwx", "KRW=X"),
    ("sox", "^SOX"),
]


def parse_utc_arg(value: str) -> dt.datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("UTC timestamps must include timezone")
    return parsed.astimezone(UTC)


def to_iso(dt_value: dt.datetime) -> str:
    return dt_value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def to_iso_ms(ms: int) -> str:
    return to_iso(dt.datetime.fromtimestamp(ms // 1000, tz=UTC).replace(microsecond=(ms % 1000) * 1000))


def sha256_hex(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return f"sha256:{h.hexdigest()}"


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_sha256(payload: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def manifest_sha256(payload: dict[str, Any]) -> str:
    hashable = dict(payload)
    hashable["manifest_sha256"] = ""
    return canonical_sha256(hashable)


def fetch_json(url: str, timeout: int = 30) -> list[dict[str, Any]] | list[list[Any]]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "koruusdt-research-dataset-builder/1.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        if response.status != 200:
            raise SystemExit(f"request failed: {url} -> {response.status}")
        data = response.read().decode("utf-8")
        return json.loads(data)


def fetch_binance_paginated_klines(
    symbol: str,
    endpoint: str,
    start_ms: int,
    end_ms: int,
    symbol_param: str = "symbol",
) -> list[dict[str, Any]]:
    if start_ms >= end_ms:
        return []

    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    cursor = start_ms

    while cursor < end_ms:
        params = {
            symbol_param: symbol,
            "interval": "1h",
            "startTime": cursor,
            "endTime": end_ms - 1,
            "limit": 1000,
        }
        url = f"{BINANCE_BASE}{endpoint}?{urlencode(params)}"
        payload = fetch_json(url)
        if not isinstance(payload, list):
            raise SystemExit(f"unexpected response type for {endpoint}")
        if not payload:
            break

        for item in payload:
            if not isinstance(item, list) or not item:
                raise SystemExit(f"unexpected kline row for {endpoint}")
            ts = int(item[0])
            if ts < start_ms or ts >= end_ms or ts in seen:
                continue
            row: dict[str, Any] = {
                "open_time_ms": ts,
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
            }
            if len(item) > 6:
                row["close_time_ms"] = int(item[6])
            if len(item) > 5:
                row["volume"] = float(item[5])
            if len(item) > 7:
                row["quote_volume"] = float(item[7])
            if len(item) > 8:
                row["num_trades"] = int(item[8])
            if len(item) > 9:
                row["taker_buy_base_volume"] = float(item[9])
            if len(item) > 10:
                row["taker_buy_quote_volume"] = float(item[10])
            if len(item) > 11:
                row["ignore"] = float(item[11])
            rows.append(row)
            seen.add(ts)

        if len(payload) < 1000:
            break
        last_ts = int(payload[-1][0])
        if last_ts < cursor:
            break
        cursor = last_ts + HOUR_MS

    rows.sort(key=lambda row: row["open_time_ms"])
    return rows


def fetch_binance_funding(symbol: str, start_ms: int, end_ms: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cursor = max(start_ms, int(LISTING_START.timestamp() * 1000))
    seen: set[int] = set()

    while cursor < end_ms:
        params = {
            "symbol": symbol,
            "startTime": cursor,
            "endTime": end_ms - 1,
            "limit": 1000,
        }
        url = f"{BINANCE_BASE}/fapi/v1/fundingRate?{urlencode(params)}"
        payload = fetch_json(url)
        if not isinstance(payload, list):
            raise SystemExit("unexpected funding response type")
        if not payload:
            break

        for item in payload:
            if not isinstance(item, dict):
                raise SystemExit("unexpected funding row type")
            ts = int(item["fundingTime"])
            if ts >= end_ms or ts in seen:
                continue
            rows.append(
                {
                    "funding_time_ms": ts,
                    "funding_rate": float(item["fundingRate"]),
                    "funding_time_type": item.get("fundingRateType"),
                    "symbol": item["symbol"],
                    "mark_price": float(item["markPrice"]) if "markPrice" in item else None,
                    "interest_rate": float(item["interestRate"]) if "interestRate" in item else None,
                    "next_funding_time_ms": int(item["nextFundingTime"]) if "nextFundingTime" in item else None,
                }
            )
            seen.add(ts)

        if len(payload) < 1000:
            break
        last_ts = int(payload[-1]["fundingTime"])
        cursor = last_ts + 1

    rows.sort(key=lambda row: row["funding_time_ms"])
    return rows


def yahoo_available_at_ms(symbol: str, bar_start_ms: int) -> int:
    bar_start = dt.datetime.fromtimestamp(bar_start_ms / 1000.0, tz=UTC)
    if symbol in {"^KS200", "005930.KS", "000660.KS"}:
        close = bar_start.astimezone(KRX_TZ).replace(hour=15, minute=30, second=0, microsecond=0)
    elif symbol in {"KORU", "MU", "SNDK", "^SOX"}:
        close = bar_start.astimezone(US_TZ).replace(hour=16, minute=0, second=0, microsecond=0)
    else:
        return bar_start_ms + HOUR_MS
    return min(bar_start_ms + HOUR_MS, int(close.timestamp() * 1000))


def fetch_yahoo_hourly(symbol: str, start_ms: int, end_ms: int) -> tuple[list[dict[str, Any]], str]:
    params = {
        "interval": "1h",
        "period1": int(start_ms / 1000),
        "period2": int(end_ms / 1000),
        "includePrePost": "false",
        "events": "div,splits",
        "includeAdjustedClose": "true",
    }
    first_error: Exception | None = None
    for base_url in YAHOO_CHART_ENDPOINTS:
        endpoint = f"{base_url}{quote(symbol)}"
        try:
            payload = fetch_json(f"{endpoint}?{urlencode(params)}")
            break
        except Exception as error:
            if first_error is None:
                first_error = error
                continue
            raise error from first_error
    if not isinstance(payload, dict):
        raise SystemExit(f"unexpected Yahoo payload for {symbol}")
    result = payload.get("chart", {}).get("result")
    if not isinstance(result, list) or not result:
        raise SystemExit(f"no chart result for {symbol}")
    chart = result[0]
    timestamps = chart.get("timestamp")
    indicators = (chart.get("indicators") or {}).get("quote")
    if not isinstance(timestamps, list) or not indicators or not isinstance(indicators, list):
        raise SystemExit(f"unexpected chart structure for {symbol}")
    quote_row = indicators[0]

    rows: list[dict[str, Any]] = []
    for idx, ts in enumerate(timestamps):
        if ts is None:
            continue
        ms = int(ts) * 1000
        if ms >= end_ms:
            continue
        close = quote_row.get("close", [])[idx]
        if close is None:
            continue
        row = {
            "timestamp_ms": ms,
            "available_at_ms": yahoo_available_at_ms(symbol, ms),
            "open": float(quote_row["open"][idx]) if quote_row.get("open", [])[idx] is not None else None,
            "high": float(quote_row["high"][idx]) if quote_row.get("high", [])[idx] is not None else None,
            "low": float(quote_row["low"][idx]) if quote_row.get("low", [])[idx] is not None else None,
            "close": float(close),
            "volume": float(quote_row["volume"][idx]) if quote_row.get("volume", [])[idx] is not None else None,
        }
        if row["open"] is not None and row["high"] is not None and row["low"] is not None and row["close"] is not None:
            rows.append(row)
    rows.sort(key=lambda row: row["timestamp_ms"])
    return rows, endpoint


def as_of_lookup(rows: list[dict[str, Any]], target_ms: int, ts_key: str) -> dict[str, Any] | None:
    if not rows:
        return None
    times = [row[ts_key] for row in rows]
    idx = bisect_right(times, target_ms) - 1
    if idx < 0:
        return None
    return rows[idx]


def exact_lookup(rows_by_time: dict[int, dict[str, Any]], target_ms: int) -> dict[str, Any] | None:
    return rows_by_time.get(target_ms)


def expected_hourly_grid(start_ms: int, end_ms: int) -> list[int]:
    first = ((start_ms + HOUR_MS - 1) // HOUR_MS) * HOUR_MS
    return list(range(first, end_ms, HOUR_MS))


def validate_binance_hourly_rows(
    start_ms: int,
    end_ms: int,
    **sources: list[dict[str, Any]],
) -> None:
    expected = expected_hourly_grid(start_ms, end_ms)
    mark_times = [row["open_time_ms"] for row in sources["mark"]]
    if mark_times != expected:
        raise SystemExit("mark rows do not match the complete requested hourly grid")
    for name, rows in sources.items():
        times = [row["open_time_ms"] for row in rows]
        if times != mark_times:
            raise SystemExit(f"{name} timestamps do not exactly match mark timestamps")


def is_krx_regular_weekday_clock(timestamp_ms: int) -> bool:
    local = dt.datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC).astimezone(KRX_TZ)
    if local.weekday() >= 5:
        return False
    open_at = dt.time(9, 0)
    close_at = dt.time(15, 30)
    return open_at <= local.timetz().replace(tzinfo=None) < close_at


def is_us_core_weekday_clock(timestamp_ms: int) -> bool:
    local = dt.datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC).astimezone(US_TZ)
    if local.weekday() >= 5:
        return False
    open_at = dt.time(9, 30)
    close_at = dt.time(16, 0)
    return open_at <= local.timetz().replace(tzinfo=None) < close_at


def adjustment_regime(timestamp_ms: int) -> str:
    timestamp = dt.datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC)
    bar_end = timestamp + dt.timedelta(milliseconds=HOUR_MS)
    if bar_end <= SPLIT_START:
        return "pre_adjustment"
    if timestamp <= SPLIT_END:
        return "adjustment_window"
    return "post_adjustment"


def apply_split_adjustment(row: dict[str, Any]) -> dict[str, Any]:
    regime = adjustment_regime(row["open_time_ms"])
    price_factor = 0.05 if regime == "pre_adjustment" else 1.0
    quantity_factor = 20.0 if regime == "pre_adjustment" else 1.0
    adjusted = {
        key: None if regime == "adjustment_window" else row[key] * price_factor
        for key in ("open", "high", "low", "close")
    }
    if "volume" in row:
        adjusted["volume"] = None if regime == "adjustment_window" else row["volume"] * quantity_factor
    return adjusted


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def build_manifest_payload(
    start_ts: dt.datetime,
    end_ts: dt.datetime,
    out_dir: Path,
    source_rows: dict[str, int],
    source_meta: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    start_ms = int(start_ts.timestamp() * 1000)
    end_ms = int(end_ts.timestamp() * 1000)
    binance_start_ms = max(start_ms, int(LISTING_START.timestamp() * 1000))
    file_entries = []
    for relative_path in sorted(source_rows):
        path = out_dir / relative_path
        file_entries.append(
            {
                "path": relative_path,
                "sha256": sha256_hex(path),
                "rows": source_rows[relative_path],
            }
        )

    def binance_source(source_id: str, endpoint: str, meta_key: str, symbol_param: str = "symbol") -> dict[str, Any]:
        parameters: dict[str, Any] = {
            symbol_param: "KORUUSDT",
            "startTime": binance_start_ms,
            "endTime": end_ms - 1,
            "limit": 1000,
        }
        if endpoint != "/fapi/v1/fundingRate":
            parameters["interval"] = "1h"
        return {
            "source_id": source_id,
            "type": "BINANCE_FUNDING" if endpoint.endswith("fundingRate") else "BINANCE_KLINES",
            "endpoint": f"{BINANCE_BASE}{endpoint}",
            "parameters": parameters,
            "end_semantics": "endTime is inclusive at the endpoint; requested end is exclusive, so endTime=end_ms-1",
            "as_of_utc": source_meta[meta_key]["as_of"],
        }

    sources = [
        binance_source("binance_futures_kline_last", "/fapi/v1/klines", "binance_last"),
        binance_source("binance_futures_mark_price_kline", "/fapi/v1/markPriceKlines", "binance_mark"),
        binance_source(
            "binance_futures_index_price_kline",
            "/fapi/v1/indexPriceKlines",
            "binance_index",
            "pair",
        ),
        binance_source(
            "binance_futures_premium_index_kline",
            "/fapi/v1/premiumIndexKlines",
            "binance_premium",
        ),
        binance_source("binance_futures_funding", "/fapi/v1/fundingRate", "binance_funding"),
    ]

    for key, symbol in YAHOO_SYMBOLS:
        source = source_meta[f"yahoo_{key}"]
        sources.append(
            {
                "source_id": symbol,
                "type": "YAHOO_CHART",
                "endpoint": source["endpoint"],
                "parameters": {
                    "interval": "1h",
                    "period1": start_ms // 1000,
                    "period2": end_ms // 1000,
                    "includePrePost": "false",
                    "events": "div,splits",
                    "includeAdjustedClose": "true",
                },
                "end_semantics": "period2 is exclusive",
                "as_of_utc": source["as_of"],
                "grade": "secondary_not_decision_grade",
            }
        )

    return {
        "type": "koruusdt_research_dataset_manifest_v1",
        "schema_version": 1,
        "generated_at_utc": to_iso(dt.datetime.now(UTC)),
        "builder": {
            "path": "research/koruusdt/build_dataset.py",
            "sha256": sha256_hex(Path(__file__).resolve()),
        },
        "runtime": {
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "note": "stdlib-only builder; zoneinfo uses the host Python runtime and host IANA timezone database, whose versions can affect timezone-derived values",
        },
        "contractType": "TRADIFI_PERPETUAL",
        "instrument": "KORUUSDT",
        "sampling": "1h mark-bar keyed",
        "requested_window": {
            "start_utc_inclusive": to_iso(start_ts),
            "end_utc_exclusive": to_iso(end_ts),
            "interval": "1h",
            "start_ms": start_ms,
            "end_ms_exclusive": end_ms,
        },
        "time_range_utc": {
            "start": to_iso(start_ts),
            "end": to_iso(end_ts),
        },
        "source_identifiers": {
            "symbol": "KORUUSDT",
            "exchange": "Binance USD-M",
            "yahoo_grade": "secondary_non_decision",
        },
        "transformation_notes": [
            "raw Binance observations are preserved in separate *_raw.csv files",
            "normalized price/base-quantity columns use explicit pre_adjustment, adjustment_window, and post_adjustment regimes; pre-adjustment price * 0.05 and base quantity * 20, bars overlapping the adjustment window null, post-adjustment unchanged",
            "Binance last/index/premium observations require exact mark-bar timestamp matches; premium basis values are never price-scaled",
            "Yahoo 1h timestamps are source bar starts; availability is min(start+1h, regular-session close) for KRX/US symbols and start+1h for KRW=X; values are backward/as-of joined on available_at only",
            "Yahoo historical chart responses are mutable vendor data and may be revised or disappear; artifact hashes pin this retrieval but do not guarantee byte-identical regeneration",
            "is_krx_regular_weekday_clock and is_us_core_weekday_clock encode weekday clock windows only; holidays are not encoded and the fields do not assert exchange-open truth",
            "funding observations use backward/as-of joins and include observed timestamp, numeric millisecond timestamp, and age",
        ],
        "sources": sources,
        "artifacts": file_entries,
        "contract_metadata": {
            "listed_utc": to_iso(LISTING_START),
            "authoritative_listing_announcement_url": LISTING_ANNOUNCEMENT_URL,
            "split_adjustment": {
                "authoritative_announcement_urls": [
                    SPLIT_ANNOUNCEMENT_URL,
                    SPLIT_COMPLETION_URL,
                    DIREXION_SPLIT_URL,
                ],
                "window_utc_start": to_iso(SPLIT_START),
                "window_utc_end": to_iso(SPLIT_END),
                "pre_adjustment_price_multiplier": 0.05,
                "pre_adjustment_base_qty_multiplier": 20.0,
                "economic_return_boundary_notes": "No forward-return columns are generated to avoid inferring economic return across the split boundary",
            },
        },
        "manifest_sha256": "",
    }


def build_dataset(start: dt.datetime, end: dt.datetime, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)

    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)

    fetch_times: dict[str, dict[str, Any]] = {}
    source_row_counts: dict[str, int] = {}

    last_start = max(start_ms, int(LISTING_START.timestamp() * 1000))
    last_rows = fetch_binance_paginated_klines("KORUUSDT", "/fapi/v1/klines", last_start, end_ms)
    fetch_times["binance_last"] = {"as_of": to_iso(dt.datetime.now(UTC))}

    mark_rows = fetch_binance_paginated_klines("KORUUSDT", "/fapi/v1/markPriceKlines", last_start, end_ms)
    fetch_times["binance_mark"] = {"as_of": to_iso(dt.datetime.now(UTC))}
    index_rows = fetch_binance_paginated_klines(
        "KORUUSDT",
        "/fapi/v1/indexPriceKlines",
        last_start,
        end_ms,
        symbol_param="pair",
    )
    fetch_times["binance_index"] = {"as_of": to_iso(dt.datetime.now(UTC))}
    premium_rows = fetch_binance_paginated_klines("KORUUSDT", "/fapi/v1/premiumIndexKlines", last_start, end_ms)
    fetch_times["binance_premium"] = {"as_of": to_iso(dt.datetime.now(UTC))}
    funding_rows = fetch_binance_funding("KORUUSDT", int(LISTING_START.timestamp() * 1000), end_ms)
    fetch_times["binance_funding"] = {"as_of": to_iso(dt.datetime.now(UTC))}

    validate_binance_hourly_rows(
        last_start,
        end_ms,
        last=last_rows,
        mark=mark_rows,
        index=index_rows,
        premium=premium_rows,
    )

    yahoo_rows: dict[str, list[dict[str, Any]]] = {}
    for key, symbol in YAHOO_SYMBOLS:
        rows, endpoint = fetch_yahoo_hourly(symbol, start_ms, end_ms)
        yahoo_rows[key] = rows
        fetch_times[f"yahoo_{key}"] = {
            "as_of": to_iso(dt.datetime.now(UTC)),
            "endpoint": endpoint,
        }

    last_by_time = {row["open_time_ms"]: row for row in last_rows}
    index_by_time = {row["open_time_ms"]: row for row in index_rows}
    premium_by_time = {row["open_time_ms"]: row for row in premium_rows}

    aligned_rows: list[dict[str, Any]] = []
    for row in mark_rows:
        ts = row["open_time_ms"]
        regime = adjustment_regime(ts)
        aligned: dict[str, Any] = {
            "timestamp_utc": to_iso_ms(ts),
            "timestamp_ms": ts,
            "is_krx_regular_weekday_clock": is_krx_regular_weekday_clock(ts),
            "is_us_core_weekday_clock": is_us_core_weekday_clock(ts),
            "adjustment_regime": regime,
            "is_split_adjustment_window": regime == "adjustment_window",
        }

        # Mark-keyed Binance series must match the target timestamp exactly.
        last_obs = exact_lookup(last_by_time, ts)
        if last_obs:
            for key in ("open", "high", "low", "close", "volume"):
                if key in last_obs:
                    aligned[f"binance_last_{key}_raw"] = last_obs[key]
            adjusted = apply_split_adjustment(last_obs)
            for key, value in adjusted.items():
                aligned[f"binance_last_{key}_normalized"] = value

        mark_obs = row
        if mark_obs:
            for key in ("open", "high", "low", "close", "volume"):
                if key in mark_obs:
                    aligned[f"binance_mark_{key}_raw"] = mark_obs[key]
            adjusted = apply_split_adjustment(mark_obs)
            for key, value in adjusted.items():
                aligned[f"binance_mark_{key}_normalized"] = value

        index_obs = exact_lookup(index_by_time, ts)
        if index_obs:
            for key in ("open", "high", "low", "close", "volume"):
                if key in index_obs:
                    aligned[f"binance_index_{key}_raw"] = index_obs[key]
            adjusted = apply_split_adjustment(index_obs)
            for key, value in adjusted.items():
                aligned[f"binance_index_{key}_normalized"] = value

        premium_obs = exact_lookup(premium_by_time, ts)
        if premium_obs:
            for key in ("open", "high", "low", "close", "volume"):
                if key in premium_obs:
                    aligned[f"binance_premium_{key}_raw"] = premium_obs[key]
                    aligned[f"binance_premium_{key}_normalized"] = premium_obs[key]

        funding_obs = as_of_lookup(funding_rows, ts, "funding_time_ms")
        if funding_obs:
            aligned["funding_rate_raw"] = funding_obs["funding_rate"]
            aligned["funding_rate_type"] = funding_obs["funding_time_type"]
            aligned["funding_mark_price_raw"] = funding_obs["mark_price"]
            aligned["funding_observed_ts_utc"] = to_iso_ms(funding_obs["funding_time_ms"])
            aligned["funding_observed_time_ms"] = funding_obs["funding_time_ms"]
            aligned["funding_age_seconds"] = int((ts - funding_obs["funding_time_ms"]) / 1000)

        for key, symbol in YAHOO_SYMBOLS:
            obs = as_of_lookup(yahoo_rows[key], ts, "available_at_ms")
            if obs is None:
                aligned[f"{key}_close_raw"] = None
                aligned[f"{key}_source_bar_ts_utc"] = None
                aligned[f"{key}_available_at_utc"] = None
                aligned[f"{key}_age_seconds"] = None
                continue
            aligned[f"{key}_close_raw"] = obs["close"]
            aligned[f"{key}_source_bar_ts_utc"] = to_iso_ms(obs["timestamp_ms"])
            aligned[f"{key}_available_at_utc"] = to_iso_ms(obs["available_at_ms"])
            aligned[f"{key}_age_seconds"] = int((ts - obs["available_at_ms"]) / 1000)

        aligned_rows.append(aligned)

    # Stable and strict ordering
    aligned_rows.sort(key=lambda row: row["timestamp_ms"])
    if len(aligned_rows) != len({row["timestamp_ms"] for row in aligned_rows}):
        raise SystemExit("aligned rows are not unique by timestamp")

    # Write raw CSVs
    source_row_counts["binance_last_raw.csv"] = write_csv(
        out_dir / "binance_last_raw.csv",
        [
            {
                "open_time_utc": to_iso_ms(row["open_time_ms"]),
                **{k: row[k] for k in ("open", "high", "low", "close", "volume", "close_time_ms", "quote_volume", "num_trades", "taker_buy_base_volume", "taker_buy_quote_volume", "ignore") if k in row},
            }
            for row in last_rows
        ],
        [
            "open_time_utc",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time_ms",
            "quote_volume",
            "num_trades",
            "taker_buy_base_volume",
            "taker_buy_quote_volume",
            "ignore",
        ],
    )

    source_row_counts["binance_mark_raw.csv"] = write_csv(
        out_dir / "binance_mark_raw.csv",
        [
            {
                "open_time_utc": to_iso_ms(row["open_time_ms"]),
                "close_time_utc": to_iso_ms(row["close_time_ms"]) if row.get("close_time_ms") is not None else None,
                **{k: row[k] for k in ("open", "high", "low", "close", "volume") if k in row},
            }
            for row in mark_rows
        ],
        ["open_time_utc", "open", "high", "low", "close", "close_time_utc", "volume"],
    )

    source_row_counts["binance_index_raw.csv"] = write_csv(
        out_dir / "binance_index_raw.csv",
        [
            {
                "open_time_utc": to_iso_ms(row["open_time_ms"]),
                "close_time_utc": to_iso_ms(row["close_time_ms"]) if row.get("close_time_ms") is not None else None,
                **{k: row[k] for k in ("open", "high", "low", "close", "volume") if k in row},
            }
            for row in index_rows
        ],
        ["open_time_utc", "open", "high", "low", "close", "close_time_utc", "volume"],
    )

    source_row_counts["binance_premium_raw.csv"] = write_csv(
        out_dir / "binance_premium_raw.csv",
        [
            {
                "open_time_utc": to_iso_ms(row["open_time_ms"]),
                "close_time_utc": to_iso_ms(row["close_time_ms"]) if row.get("close_time_ms") is not None else None,
                **{k: row[k] for k in ("open", "high", "low", "close", "volume") if k in row},
            }
            for row in premium_rows
        ],
        ["open_time_utc", "open", "high", "low", "close", "close_time_utc", "volume"],
    )

    source_row_counts["binance_funding_raw.csv"] = write_csv(
        out_dir / "binance_funding_raw.csv",
        [
            {
                "funding_time_utc": to_iso_ms(row["funding_time_ms"]),
                "funding_time_ms": row["funding_time_ms"],
                "funding_time_type": row["funding_time_type"],
                "funding_rate": row["funding_rate"],
                "mark_price": row["mark_price"],
                "interest_rate": row["interest_rate"],
                "next_funding_time_ms": row["next_funding_time_ms"],
            }
            for row in funding_rows
        ],
        [
            "funding_time_utc",
            "funding_time_ms",
            "funding_rate",
            "funding_time_type",
            "mark_price",
            "interest_rate",
            "next_funding_time_ms",
        ],
    )

    for key, symbol in YAHOO_SYMBOLS:
        filename = f"yahoo_{key}_raw.csv"
        rows = yahoo_rows[key]
        source_row_counts[filename] = write_csv(
            out_dir / filename,
            [
                {
                    "timestamp_utc": to_iso_ms(row["timestamp_ms"]),
                    "available_at_utc": to_iso_ms(row["available_at_ms"]),
                    **{k: row[k] for k in ("open", "high", "low", "close", "volume")},
                }
                for row in rows
            ],
            ["timestamp_utc", "available_at_utc", "open", "high", "low", "close", "volume"],
        )

    aligned_fieldnames = sorted(
        set(
            field
            for row in aligned_rows
            for field in row
        )
    )
    source_row_counts["aligned_hourly.csv"] = write_csv(
        out_dir / "aligned_hourly.csv",
        aligned_rows,
        aligned_fieldnames,
    )

    manifest = build_manifest_payload(
        start,
        end,
        out_dir,
        source_row_counts,
        {
            **fetch_times,
        },
    )

    manifest_path = out_dir / "manifest.json"
    manifest["manifest_sha256"] = manifest_sha256(manifest)
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    manifest_path.write_text(manifest_text, encoding="utf-8")
    return manifest_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build KORUUSDT exploratory dataset")
    parser.add_argument("--start", required=True, type=parse_utc_arg, help="UTC start time (inclusive), e.g. 2026-06-22T13:55:00Z")
    parser.add_argument("--end", required=True, type=parse_utc_arg, help="UTC end time (exclusive), e.g. 2026-08-01T00:00:00Z")
    parser.add_argument("--out-dir", default=str(Path(__file__).resolve().parent / "data"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.out_dir).resolve()
    start = args.start
    end = args.end

    if end <= start:
        raise SystemExit("--end must be after --start")

    manifest = build_dataset(start, end, out_dir)
    print(f"wrote manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
