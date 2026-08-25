from __future__ import annotations

import csv
import datetime as dt
import importlib.util
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "build_dataset.py"
DATA_DIR = SCRIPT_PATH.parent / "data"
SPEC = importlib.util.spec_from_file_location("koruusdt_build_dataset", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)  # type: ignore[union-attr]


@pytest.fixture(name="bd")
def _module():
    return MODULE


def utc_ms(value: str) -> int:
    return int(dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)


def read_csv(name: str) -> list[dict[str, str]]:
    with (DATA_DIR / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_split_adjustment_regimes(bd):
    def row(timestamp: str) -> dict[str, float | int]:
        return {
            "open_time_ms": utc_ms(timestamp),
            "open": 100.0,
            "high": 120.0,
            "low": 90.0,
            "close": 110.0,
            "volume": 1000.0,
        }

    pre = bd.apply_split_adjustment(row("2026-07-14T23:00:00Z"))
    window = bd.apply_split_adjustment(row("2026-07-15T01:00:00Z"))
    post = bd.apply_split_adjustment(row("2026-07-15T10:00:00Z"))

    assert bd.adjustment_regime(utc_ms("2026-07-14T23:00:00Z")) == "pre_adjustment"
    assert bd.adjustment_regime(utc_ms("2026-07-15T00:00:00Z")) == "adjustment_window"
    assert bd.adjustment_regime(utc_ms("2026-07-15T00:15:00Z")) == "adjustment_window"
    assert bd.adjustment_regime(utc_ms("2026-07-15T09:35:00Z")) == "adjustment_window"
    assert bd.adjustment_regime(utc_ms("2026-07-15T10:00:00Z")) == "post_adjustment"
    assert pre == {"open": 5.0, "high": 6.0, "low": 4.5, "close": 5.5, "volume": 20000.0}
    assert all(value is None for value in window.values())
    assert post == {"open": 100.0, "high": 120.0, "low": 90.0, "close": 110.0, "volume": 1000.0}


def test_iso_output_preserves_milliseconds(bd):
    assert bd.to_iso_ms(utc_ms("2026-07-01T00:00:00Z") + 1) == "2026-07-01T00:00:00.001Z"


def test_as_of_lookup_no_lookahead_and_ten_minutes_is_milliseconds(bd):
    rows = [
        {"timestamp_ms": utc_ms("2026-07-01T00:00:00Z"), "value": 1.0},
        {"timestamp_ms": utc_ms("2026-07-01T01:00:00Z"), "value": 2.0},
        {"timestamp_ms": utc_ms("2026-07-01T03:00:00Z"), "value": 3.0},
    ]

    assert bd.as_of_lookup(rows, rows[0]["timestamp_ms"], "timestamp_ms")["value"] == 1.0
    assert bd.as_of_lookup(rows, rows[0]["timestamp_ms"] + 30 * 60 * 1000, "timestamp_ms")["value"] == 1.0
    assert bd.as_of_lookup(rows, rows[1]["timestamp_ms"] + 10 * 60 * 1000, "timestamp_ms")["value"] == 2.0
    assert bd.as_of_lookup(rows, rows[0]["timestamp_ms"] - 1, "timestamp_ms") is None

    target = utc_ms("2026-07-01T02:00:00Z")
    future_funding = [{"funding_time_ms": target + 1, "funding_rate": 0.004}]
    assert bd.as_of_lookup(future_funding, target, "funding_time_ms") is None


def test_yahoo_close_is_unavailable_during_its_own_bar(bd):
    bar_start = utc_ms("2026-07-01T14:30:00Z")
    rows = [{"timestamp_ms": bar_start, "available_at_ms": bar_start + bd.HOUR_MS, "close": 42.0}]

    assert bd.as_of_lookup(rows, bar_start + 10 * 60 * 1000, "available_at_ms") is None
    assert bd.as_of_lookup(rows, bar_start + bd.HOUR_MS - 1, "available_at_ms") is None
    assert bd.as_of_lookup(rows, bar_start + bd.HOUR_MS, "available_at_ms")["close"] == 42.0


def test_yahoo_endpoint_fallback_and_both_failures_propagate(monkeypatch, bd):
    start_ms = utc_ms("2026-07-01T14:30:00Z")
    end_ms = start_ms + bd.HOUR_MS
    payload = {
        "chart": {
            "result": [
                {
                    "timestamp": [start_ms // 1000],
                    "indicators": {
                        "quote": [
                            {
                                "open": [40.0],
                                "high": [43.0],
                                "low": [39.0],
                                "close": [42.0],
                                "volume": [100.0],
                            }
                        ]
                    },
                }
            ]
        }
    }
    calls = []

    def primary_fails(url):
        calls.append(url)
        if "query1.finance.yahoo.com" in url:
            raise TimeoutError("primary timed out")
        return payload

    monkeypatch.setattr(bd, "fetch_json", primary_fails)
    rows, endpoint = bd.fetch_yahoo_hourly("KORU", start_ms, end_ms)

    assert ["query1.finance.yahoo.com" in url for url in calls] == [True, False]
    assert endpoint == "https://query2.finance.yahoo.com/v8/finance/chart/KORU"
    assert rows[0]["close"] == 42.0

    def both_fail(url):
        if "query1.finance.yahoo.com" in url:
            raise TimeoutError("primary timed out")
        raise RuntimeError("fallback failed")

    monkeypatch.setattr(bd, "fetch_json", both_fail)
    with pytest.raises(RuntimeError, match="fallback failed") as caught:
        bd.fetch_yahoo_hourly("KORU", start_ms, end_ms)
    assert isinstance(caught.value.__cause__, TimeoutError)


@pytest.mark.parametrize(
    ("symbol", "bar_start", "available_at"),
    [
        ("^KS200", "2026-07-02T06:00:00Z", "2026-07-02T06:30:00Z"),
        ("005930.KS", "2026-07-02T06:00:00Z", "2026-07-02T06:30:00Z"),
        ("000660.KS", "2026-07-02T06:00:00Z", "2026-07-02T06:30:00Z"),
        ("KORU", "2026-07-02T19:30:00Z", "2026-07-02T20:00:00Z"),
        ("MU", "2026-07-02T19:30:00Z", "2026-07-02T20:00:00Z"),
        ("SNDK", "2026-07-02T19:30:00Z", "2026-07-02T20:00:00Z"),
        ("^SOX", "2026-07-02T19:30:00Z", "2026-07-02T20:00:00Z"),
    ],
)
def test_yahoo_terminal_bar_uses_session_close_and_no_lookahead(bd, symbol, bar_start, available_at):
    start_ms = utc_ms(bar_start)
    available_ms = utc_ms(available_at)
    row = {
        "timestamp_ms": start_ms,
        "available_at_ms": bd.yahoo_available_at_ms(symbol, start_ms),
        "close": 42.0,
    }

    assert row["available_at_ms"] == available_ms
    assert bd.as_of_lookup([row], available_ms - 1, "available_at_ms") is None
    assert bd.as_of_lookup([row], available_ms, "available_at_ms")["close"] == 42.0


def test_mark_keyed_binance_lookup_does_not_carry_stale_rows(bd):
    old_ts = utc_ms("2026-07-01T00:00:00Z")
    target_ts = utc_ms("2026-07-01T01:00:00Z")
    rows_by_time = {old_ts: {"open_time_ms": old_ts, "close": 1.0}}

    assert bd.exact_lookup(rows_by_time, old_ts)["close"] == 1.0
    assert bd.exact_lookup(rows_by_time, target_ts) is None


def test_weekday_clock_flags_use_zoneinfo_but_not_holiday_calendars(bd):
    assert bd.is_us_core_weekday_clock(utc_ms("2026-07-02T14:00:00Z"))
    assert bd.is_krx_regular_weekday_clock(utc_ms("2026-07-02T00:30:00Z"))
    assert not bd.is_us_core_weekday_clock(utc_ms("2026-07-04T13:00:00Z"))
    assert not bd.is_krx_regular_weekday_clock(utc_ms("2026-07-04T13:00:00Z"))


def test_binance_kline_pagination_and_exclusive_end(monkeypatch, bd):
    start_ms = utc_ms("2026-07-01T00:00:00Z")
    end_ms = start_ms + 1001 * bd.HOUR_MS
    calls = []

    def fake_fetch(url):
        calls.append(parse_qs(urlparse(url).query))
        cursor = int(calls[-1]["startTime"][0])
        count = 1000 if len(calls) == 1 else 2
        return [
            [cursor + offset * bd.HOUR_MS, "1", "2", "0.5", "1.5"]
            for offset in range(count)
        ]

    monkeypatch.setattr(bd, "fetch_json", fake_fetch)
    rows = bd.fetch_binance_paginated_klines("TEST", "/fapi/v1/klines", start_ms, end_ms)

    assert len(rows) == 1001
    assert rows[0]["open_time_ms"] == start_ms
    assert rows[-1]["open_time_ms"] == end_ms - bd.HOUR_MS
    assert len(calls) == 2
    assert calls[0]["endTime"] == [str(end_ms - 1)]
    assert calls[1]["startTime"] == [str(start_ms + 1000 * bd.HOUR_MS)]


def test_funding_exclusive_end_and_absent_type_is_null(monkeypatch, bd):
    start_ms = int(bd.LISTING_START.timestamp() * 1000)
    end_ms = start_ms + 2
    payload = [
        {"fundingTime": start_ms, "fundingRate": "0.001", "symbol": "KORUUSDT"},
        {"fundingTime": end_ms, "fundingRate": "0.002", "symbol": "KORUUSDT"},
    ]
    monkeypatch.setattr(bd, "fetch_json", lambda _url: payload)

    rows = bd.fetch_binance_funding("KORUUSDT", start_ms, end_ms)

    assert len(rows) == 1
    assert rows[0]["funding_time_ms"] == start_ms
    assert rows[0]["funding_time_type"] is None


def test_expected_mark_grid_and_cross_source_timestamps_fail_closed(bd):
    start_ms = utc_ms("2026-07-01T00:00:00Z")
    end_ms = start_ms + 3 * bd.HOUR_MS
    complete = [{"open_time_ms": start_ms + i * bd.HOUR_MS} for i in range(3)]
    bd.validate_binance_hourly_rows(
        start_ms,
        end_ms,
        last=complete,
        mark=complete,
        index=complete,
        premium=complete,
    )

    with pytest.raises(SystemExit, match="complete requested hourly grid"):
        bd.validate_binance_hourly_rows(start_ms, end_ms, mark=complete[:-1])
    with pytest.raises(SystemExit, match="last timestamps"):
        bd.validate_binance_hourly_rows(start_ms, end_ms, mark=complete, last=complete[:-1])


def test_manifest_hash_is_deterministic_and_hashes_manifest_payload(bd):
    payload_a = {"a": 1, "nested": {"b": 2, "a": 1}, "manifest_sha256": ""}
    payload_b = {"manifest_sha256": "sha256:ignored", "nested": {"a": 1, "b": 2}, "a": 1}

    assert bd.manifest_sha256(payload_a) == bd.manifest_sha256(payload_b)
    payload_b["a"] = 2
    assert bd.manifest_sha256(payload_a) != bd.manifest_sha256(payload_b)

    manifest = json.loads((DATA_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["manifest_sha256"] == bd.manifest_sha256(manifest)


def test_fixed_snapshot_semantic_invariants_and_artifact_hashes(bd):
    manifest = json.loads((DATA_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["time_range_utc"] == {
        "start": "2026-06-22T13:55:00.000Z",
        "end": "2026-08-24T11:00:00.000Z",
    }
    assert manifest["builder"] == {
        "path": "research/koruusdt/build_dataset.py",
        "sha256": bd.sha256_hex(SCRIPT_PATH),
    }
    assert manifest["requested_window"]["interval"] == "1h"
    assert "zoneinfo" in manifest["runtime"]["note"]
    assert manifest["contract_metadata"]["authoritative_listing_announcement_url"]
    assert manifest["contract_metadata"]["split_adjustment"]["authoritative_announcement_urls"]
    yahoo_sources = [source for source in manifest["sources"] if source["type"] == "YAHOO_CHART"]
    assert len(yahoo_sources) == len(bd.YAHOO_SYMBOLS)
    assert all(source["endpoint"].startswith(bd.YAHOO_CHART_ENDPOINTS) for source in yahoo_sources)
    assert all("retrieval_note" not in source for source in yahoo_sources)
    for artifact in manifest["artifacts"]:
        path = DATA_DIR / artifact["path"]
        assert artifact["sha256"] == bd.sha256_hex(path)
        assert artifact["rows"] == len(read_csv(artifact["path"]))

    raw_timestamp_sets = []
    for name in ("binance_last_raw.csv", "binance_mark_raw.csv", "binance_index_raw.csv", "binance_premium_raw.csv"):
        raw_timestamp_sets.append([utc_ms(row["open_time_utc"]) for row in read_csv(name)])
    assert all(timestamps == raw_timestamp_sets[0] for timestamps in raw_timestamp_sets[1:])
    assert raw_timestamp_sets[0] == bd.expected_hourly_grid(
        utc_ms("2026-06-22T13:55:00.000Z"),
        utc_ms("2026-08-24T11:00:00.000Z"),
    )

    funding_rows = read_csv("binance_funding_raw.csv")
    assert all(int(row["funding_time_ms"]) == utc_ms(row["funding_time_utc"]) for row in funding_rows)

    rows = read_csv("aligned_hourly.csv")
    assert "is_krx_regular_weekday_clock" in rows[0]
    assert "is_us_core_weekday_clock" in rows[0]
    timestamps = [int(row["timestamp_ms"]) for row in rows]
    assert timestamps == sorted(timestamps)
    assert len(timestamps) == len(set(timestamps))

    price_quantity_columns = [
        column
        for column in rows[0]
        if column.startswith(("binance_last_", "binance_mark_", "binance_index_"))
        and column.endswith("_normalized")
    ]
    for row in rows:
        regime = row["adjustment_regime"]
        assert regime in {"pre_adjustment", "adjustment_window", "post_adjustment"}
        assert (row["is_split_adjustment_window"] == "True") == (regime == "adjustment_window")
        if regime == "adjustment_window":
            assert all(row[column] == "" for column in price_quantity_columns)

        for source in ("last", "mark", "index"):
            for field in ("open", "high", "low", "close", "volume"):
                raw = row.get(f"binance_{source}_{field}_raw", "")
                normalized = row.get(f"binance_{source}_{field}_normalized", "")
                if not raw:
                    assert not normalized
                elif regime == "adjustment_window":
                    assert normalized == ""
                else:
                    multiplier = 20.0 if field == "volume" and regime == "pre_adjustment" else 1.0
                    if field != "volume" and regime == "pre_adjustment":
                        multiplier = 0.05
                    assert float(normalized) == pytest.approx(float(raw) * multiplier)

        for column, value in row.items():
            if column.endswith("_age_seconds") and value:
                assert int(value) >= 0

        for key, _symbol in bd.YAHOO_SYMBOLS:
            available = row[f"{key}_available_at_utc"]
            source = row[f"{key}_source_bar_ts_utc"]
            if available:
                assert bd.yahoo_available_at_ms(_symbol, utc_ms(source)) == utc_ms(available)
                assert utc_ms(available) <= int(row["timestamp_ms"])

        if row.get("funding_observed_ts_utc"):
            assert int(row["funding_observed_time_ms"]) == utc_ms(row["funding_observed_ts_utc"])

        for field in ("open", "high", "low", "close", "volume"):
            raw = row.get(f"binance_premium_{field}_raw", "")
            normalized = row.get(f"binance_premium_{field}_normalized", "")
            assert normalized == raw
