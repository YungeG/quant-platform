#!/usr/bin/env python3
"""Offline public-root preflight for the retained KORU premium discovery inputs.

`--smoke` validates the immutable source authority and discovery boundary, then
stops before source replay/economics.  `--full` is the explicit, offline
preflight that reconstructs the retained source, target-free economics bundle,
and four premium readers; it never starts an Experiment or Backtest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import signal
import socket
import sys
import tempfile
import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BACKTEST = ROOT / "backtest"
DATA = HERE / "data"
AUTHORITY_ROOT = DATA / "public_preflight_sources_v1"
AUTHORITY_MANIFEST = AUTHORITY_ROOT / "manifest.json"
EXECUTION_MANIFEST = DATA / "execution_data_manifest.json"
BASE_MANIFEST = DATA / "manifest.json"
GAP_AUDIT = DATA / "execution_gap_impact.json"
OWNER_LOG = "research.artifacts.v1"
DISCOVERY_START = "2026-07-15T10:00:00Z"
DISCOVERY_END = "2026-08-24T11:00:00Z"
START_MS = 1_784_109_600_000
END_MS = 1_787_569_200_000
AGG_ACQUIRED_AT = "2026-08-26T06:50:03Z"
PRICE_ACQUIRED_AT = "2026-08-26T09:46:54Z"
DEFAULT_FULL_MAX_SECONDS = 300
MAX_FULL_SECONDS = 300

for package in (
    "trading-domain",
    "trading-kernel",
    "market-data-contracts",
    "market-bundle-builder",
    "backtest-runtime",
):
    sys.path.insert(0, str(BACKTEST / "packages" / package / "src"))

from crypto_quant_bundle_builder import (  # noqa: E402
    APPROVED_MEMBER_HASHES,
    BINANCE_USDM_KORU_AGGREGATE_TRADE_AVAILABILITY_AUTHORITY_V1,
    BinanceUsdmKoruAggregateTradeBoundaryIndexRequestV1,
    BinanceUsdmKoruAggregateTradesSourceBoundedRequestV1,
    BinanceUsdmKoruExecutionBoundaryV1,
    BinanceUsdmKoruFundingRateHistorySourceBoundedRequestV1,
    BinanceUsdmKoruFundingRateHistoryTransportResponseV1,
    BinanceUsdmKoruPriceBarsSourceBoundedRequestV1,
    BinanceUsdmKoruPriceBarsSourceKindV1,
    BinanceUsdmKoruRetainedAggregateTradesAuthorityV1,
    BinanceUsdmKoruRetainedAggregateTradesPageV1,
    BinanceUsdmKoruRetainedPriceBarsAuthorityV1,
    KoruMarkIndexPremiumParametersV1,
    KoruPremiumReaderSetBuildRequestV1,
    KoruTradifiEconomicsBundleRequestV3,
    KoruTradifiEconomicsTermsV3,
    KoruTradifiSourceProjectionContentIdentityV2,
    KoruDirectionalTargetRecipeV1,
    RawSourceMember,
    build_binance_usdm_koru_aggregate_trade_boundary_index_v1,
    build_binance_usdm_koru_tradifi_source_projection_v2,
    build_koru_premium_reader_set_v1,
    build_koru_premium_recipe_authority_v1,
    canonical_koru_premium_payload_v1,
    build_koru_tradifi_calendar_unit_authority_v1,
    build_binance_usdm_koru_price_bars_retained_observations_evidence_v1,
    capture_binance_usdm_koru_aggregate_trades_from_retained_rest_v1,
    capture_binance_usdm_koru_aggregate_trades_source_bounded_v1,
    capture_binance_usdm_koru_funding_rate_history_source_bounded_v1,
    capture_binance_usdm_koru_price_bars_from_retained_observations_v1,
    capture_binance_usdm_koru_price_bars_source_bounded_v1,
    normalize_binance_usdm_koru_funding_rate_history_source_bounded_v1,
    normalize_binance_usdm_koru_price_bars_source_bounded_v1,
    publish_koru_tradifi_economics_bundle_v3,
    verify_koru_tradifi_calendar_unit_authority_v1,
    BinanceUsdmKoruTradifiSourceProjectionRequestV2,
)
from crypto_quant_domain import (  # noqa: E402
    ArtifactEnvelope,
    ArtifactReadResult,
    ArtifactRef,
    InstrumentId,
    Scale,
    UtcInstant,
    VenueId,
    canonical_bytes,
    canonical_sha256,
)
from crypto_quant_foundation import LocalFoundation  # noqa: E402

INSTRUMENT = InstrumentId(VenueId("binance_usdm"), "koru-usdt-tradifi-perpetual")


def _hash(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _canonical_pretty_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    if type(value) is not dict:
        raise ValueError(f"{path}: expected JSON object")
    return value


def _self_hash(value: dict[str, Any], path: Path) -> None:
    expected = value.get("manifest_sha256")
    body = dict(value)
    body["manifest_sha256"] = ""
    if type(expected) is not str or expected != _hash(_canonical_json(body)):
        raise ValueError(f"{path}: manifest self-hash mismatch")


def _utc_ns(value: str) -> int:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError(f"not UTC: {value}")
    delta = parsed - datetime(1970, 1, 1, tzinfo=UTC)
    return delta.days * 86_400_000_000_000 + delta.seconds * 1_000_000_000 + delta.microseconds * 1_000


def _unwrap(outcome: object, label: str) -> Any:
    result = getattr(outcome, "result", None)
    if result is None:
        failure = getattr(outcome, "failure", None)
        raise RuntimeError(f"{label} failed: {failure}")
    return result


def _network_denied(*_args: object, **_kwargs: object) -> NoReturn:
    raise RuntimeError("network is disabled for public retained preflight")


class FullPreflightDeadlineExceeded(TimeoutError):
    """The process-local full-preflight deadline elapsed."""

    def __init__(self, max_seconds: int) -> None:
        self.max_seconds = max_seconds
        super().__init__(f"full preflight deadline exceeded after {max_seconds} seconds")


def _validate_full_max_seconds(max_seconds: int) -> int:
    if type(max_seconds) is not int or not 1 <= max_seconds <= MAX_FULL_SECONDS:
        raise ValueError(f"full --max-seconds must be an integer from 1 to {MAX_FULL_SECONDS}")
    return max_seconds


@contextmanager
def full_deadline(max_seconds: int) -> Iterator[None]:
    """Interrupt full preflight in-process; callers must still use `timeout 300`."""
    max_seconds = _validate_full_max_seconds(max_seconds)
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("full preflight deadline requires the process main thread")
    if not hasattr(signal, "SIGALRM") or not hasattr(signal, "setitimer"):
        raise RuntimeError("full preflight deadline is unavailable on this platform")

    def expired(_signum: int, _frame: object) -> NoReturn:
        raise FullPreflightDeadlineExceeded(max_seconds)

    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, expired)
    previous_timer = signal.setitimer(signal.ITIMER_REAL, float(max_seconds))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, *previous_timer)
        signal.signal(signal.SIGALRM, previous_handler)


@contextmanager
def deny_network() -> Iterator[None]:
    """Deny sockets even if an accidental dependency attempts a connection."""
    with (
        patch.object(socket, "create_connection", _network_denied),
        patch.object(socket.socket, "connect", _network_denied),
        patch.object(socket.socket, "connect_ex", _network_denied),
    ):
        yield


def _authority_manifest() -> dict[str, Any]:
    raw = AUTHORITY_MANIFEST.read_bytes()
    value = _load(AUTHORITY_MANIFEST)
    if raw != _canonical_pretty_json(value):
        raise ValueError("public preflight authority manifest bytes are noncanonical")
    _self_hash(value, AUTHORITY_MANIFEST)
    expected_keys = {
        "type", "schema_version", "authority_schema", "authority_schema_version",
        "members", "intended_discovery_interval", "acquisition", "integrity_exception", "manifest_sha256",
    }
    if (
        set(value) != expected_keys
        or value["type"] != "koruusdt_public_preflight_sources_v1"
        or value["schema_version"] != 1
        or value["authority_schema"] != "koru_tradifi_calendar_unit_authority_v1"
        or value["authority_schema_version"] != 1
        or value["intended_discovery_interval"] != {
            "start_utc_inclusive": DISCOVERY_START,
            "end_utc_exclusive": DISCOVERY_END,
            "semantics": "half-open",
        }
        or value["acquisition"] != {
            "network_performed": False,
            "status": "no_network_repository_copy",
            "source_fixture_paths_are_provenance_only": True,
        }
        or value["integrity_exception"] != {
            "member": "krx/landing.html",
            "sha256": "sha256:c181b15a7c08cc48a4fc390160cdf748c3680006155f1a0124465613f32b978e",
            "reason": "malformed_vendor_html_preserved_byte_exact",
            "validator_waiver": "scoped_pi_lens_ignore",
        }
        or type(value["members"]) is not list
    ):
        raise ValueError("public preflight authority manifest schema mismatch")
    expected = dict(APPROVED_MEMBER_HASHES)
    members = value["members"]
    by_name: dict[str, dict[str, Any]] = {}
    for row in members:
        if type(row) is dict and type(filename := row.get("filename")) is str:
            by_name[filename] = row
    if len(by_name) != len(members) or tuple(sorted(by_name)) != tuple(sorted(expected)):
        raise ValueError("public preflight authority member cover mismatch")
    actual_files = {
        path.relative_to(AUTHORITY_ROOT).as_posix()
        for path in AUTHORITY_ROOT.rglob("*") if path.is_file()
    }
    if actual_files != {"manifest.json", *expected}:
        raise ValueError("public preflight authority file cover mismatch")
    for filename, expected_hash in expected.items():
        row = by_name[filename]
        raw = (AUTHORITY_ROOT / filename).read_bytes()
        if (
            set(row) != {"filename", "sha256", "size_bytes", "source_fixture_path"}
            or row["sha256"] != expected_hash
            or row["size_bytes"] != len(raw)
            or _hash(raw) != expected_hash
            or row["source_fixture_path"]
            != "backtest/tests/fixtures/market_data/providers/tradifi/koru-calendar-unit-v1/" + filename
        ):
            raise ValueError(f"public preflight authority mismatch: {filename}")
    return value


def _calendar_authority(manifest: Mapping[str, Any]) -> Any:
    receipt_times = {
        source: _utc_ns(_load(AUTHORITY_ROOT / source / "acquisition-receipt.json")["captured_at_utc"])
        for source in ("binance", "krx", "nyse")
    }
    members = tuple(
        RawSourceMember(
            member_key, (AUTHORITY_ROOT / member_key).read_bytes(), "0644",
            receipt_times[member_key.partition("/")[0]], expected_hash,
        )
        for member_key, expected_hash in APPROVED_MEMBER_HASHES
    )
    result = _unwrap(
        build_koru_tradifi_calendar_unit_authority_v1(
            members=members, expected_hashes=APPROVED_MEMBER_HASHES
        ),
        "calendar/unit authority",
    )
    verified = _unwrap(
        verify_koru_tradifi_calendar_unit_authority_v1(
            result=result, expected_hashes=APPROVED_MEMBER_HASHES
        ),
        "calendar/unit authority verification",
    )
    if manifest["acquisition"]["network_performed"] is not False:
        raise ValueError("authority acquisition must be no-network")
    return verified


def _retained_manifests() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    execution, base, gap = _load(EXECUTION_MANIFEST), _load(BASE_MANIFEST), _load(GAP_AUDIT)
    for value, path in ((execution, EXECUTION_MANIFEST), (base, BASE_MANIFEST), (gap, GAP_AUDIT)):
        _self_hash(value, path)
    interval = execution.get("backtest_authority_interval")
    if interval != {
        "start_ms": START_MS,
        "end_ms_exclusive": END_MS,
        "start_utc_inclusive": "2026-07-15T10:00:00.000Z",
        "end_utc_exclusive": "2026-08-24T11:00:00.000Z",
        "semantics": "half-open",
    }:
        raise ValueError("retained discovery interval does not exclude holdout")
    if "2026-08-25" in json.dumps(execution, sort_keys=True):
        raise ValueError("retained execution manifest names holdout data")
    return execution, base, gap


def _smoke_foundation_root_is_absent_or_empty(foundation_root: Path | None) -> None:
    if foundation_root is not None and foundation_root.exists() and (
        not foundation_root.is_dir() or any(foundation_root.iterdir())
    ):
        raise ValueError("preflight foundation root must be absent or empty; Foundation state is not an input")


def smoke(foundation_root: Path | None = None) -> dict[str, object]:
    """Validate the bounded public authority path without initializing Foundation."""
    authority_manifest = _authority_manifest()
    authority = _calendar_authority(authority_manifest)
    execution, _base, _gap = _retained_manifests()
    _smoke_foundation_root_is_absent_or_empty(foundation_root)
    return {
        "mode": "smoke",
        "network_performed": False,
        "holdout_touched": False,
        "authority_member_count": len(authority_manifest["members"]),
        "authority_snapshot_id": authority.source_snapshot.snapshot_id,
        "execution_manifest_sha256": execution["manifest_sha256"],
        "stopped_before": "full_retained_source_replay_and_economics",
    }


def _files(manifest: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows = manifest.get("files")
    if type(rows) is not list:
        raise ValueError("execution manifest files missing")
    files = {row.get("path"): row for row in rows if type(row) is dict}
    if len(files) != len(rows) or any(type(path) is not str for path in files):
        raise ValueError("execution manifest file cover invalid")
    return files  # type: ignore[return-value]


def _checked(relative_path: str, files: Mapping[str, Mapping[str, Any]]) -> bytes:
    entry = files.get(relative_path)
    if entry is None:
        raise ValueError(f"unmanifested retained file: {relative_path}")
    raw = (DATA / relative_path).read_bytes()
    if _hash(raw) != entry.get("sha256") or len(raw) != entry.get("size_bytes"):
        raise ValueError(f"retained file hash mismatch: {relative_path}")
    return raw


def _fetch(values: Mapping[str, bytes]):
    def fetch(url: str) -> tuple[int, bytes]:
        if url not in values:
            raise RuntimeError(f"network disabled; unbound retained URL: {url}")
        return 200, values[url]
    return fetch


def _query(source_url: str) -> dict[str, str]:
    query = source_url.partition("?")[2]
    return {key: value for key, _, value in (part.partition("=") for part in query.split("&"))}


def _official_aggregates(execution: Mapping[str, Any], files: Mapping[str, Mapping[str, Any]]) -> tuple[Any, ...]:
    acquired = _utc_ns(AGG_ACQUIRED_AT)
    captures = []
    for daily in execution["datasets"]["aggTrades"]["daily"]:
        date = daily["utc_date"]
        path = f"binance_usdm/aggTrades/daily/KORUUSDT-aggTrades-{date}.zip"
        archive, checksum = _checked(path, files), _checked(path + ".CHECKSUM", files)
        request = BinanceUsdmKoruAggregateTradesSourceBoundedRequestV1(
            INSTRUMENT, date, files[path]["provider_last_modified_ns"], acquired,
            _hash(archive), _hash(checksum),
        )
        archive_url, checksum_url = request.urls
        captures.append(_unwrap(
            capture_binance_usdm_koru_aggregate_trades_source_bounded_v1(
                request, _fetch({archive_url: archive, checksum_url: checksum})
            ), f"aggregate capture {date}",
        ))
    return tuple(captures)


def _retained_aggregate(execution: Mapping[str, Any], files: Mapping[str, Mapping[str, Any]]) -> Any:
    prefix = "binance_usdm/aggTrades/rest-bounded/2026-08-24/"
    entries = sorted(
        (entry for path, entry in files.items() if path.startswith(prefix) and entry.get("status") == "canonical_rest_response"),
        key=lambda entry: entry["path"],
    )
    pages, page_bytes = [], []
    for entry in entries:
        query = _query(entry["source_url"])
        name = entry["path"].removeprefix(prefix)
        pages.append(BinanceUsdmKoruRetainedAggregateTradesPageV1(
            name, entry["sha256"], entry["source_url"], int(query["startTime"]),
            int(query["endTime"]), int(name.removesuffix(".json").rsplit("-", 1)[1]),
            entry["row_count"], int(query["fromId"]) if "fromId" in query else None,
        ))
        page_bytes.append(_checked(entry["path"], files))
    derived = prefix + "KORUUSDT-aggTrades-2026-08-24.discovery-bounded.csv"
    archive = derived.removesuffix(".csv") + ".zip"
    checksum = archive + ".CHECKSUM"
    authority = BinanceUsdmKoruRetainedAggregateTradesAuthorityV1(
        "research/koruusdt/data/execution_data_manifest.json", _hash(EXECUTION_MANIFEST.read_bytes()),
        execution["manifest_sha256"], _utc_ns(execution["generated_at_utc"]), tuple(pages),
        UtcInstant(1_787_553_260_640_000_000), UtcInstant(END_MS * 1_000_000),
        UtcInstant(1_787_529_600_000_000_000), UtcInstant(1_787_553_260_640_000_000),
        BINANCE_USDM_KORU_AGGREGATE_TRADE_AVAILABILITY_AUTHORITY_V1,
        derived.removeprefix(prefix), files[derived]["sha256"], "binance_usdm_aggtrades_csv_7_column_v1",
    )
    acquired = _utc_ns(AGG_ACQUIRED_AT)
    request = BinanceUsdmKoruAggregateTradesSourceBoundedRequestV1(
        INSTRUMENT, "2026-08-24", acquired, acquired, files[archive]["sha256"], files[checksum]["sha256"], authority
    )
    return _unwrap(capture_binance_usdm_koru_aggregate_trades_from_retained_rest_v1(
        request, EXECUTION_MANIFEST.read_bytes(), tuple(page_bytes), _checked(derived, files),
        _checked(archive, files), _checked(checksum, files),
    ), "retained aggregate capture")


def _official_prices(kind: Any, execution: Mapping[str, Any], files: Mapping[str, Mapping[str, Any]]) -> tuple[Any, ...]:
    dataset, directory = (
        ("markPriceKlines_1h", "mark") if kind is BinanceUsdmKoruPriceBarsSourceKindV1.MARK_PRICE
        else ("indexPriceKlines_1h", "index")
    )
    acquired = _utc_ns(PRICE_ACQUIRED_AT)
    results = []
    for daily in execution["datasets"][dataset]["daily"]:
        date = daily["utc_date"]
        path = f"binance_usdm/priceBars/{directory}/1h/daily/KORUUSDT-1h-{date}.zip"
        archive, checksum = _checked(path, files), _checked(path + ".CHECKSUM", files)
        request = BinanceUsdmKoruPriceBarsSourceBoundedRequestV1(
            kind, INSTRUMENT, "1h", date, files[path]["provider_last_modified_ns"], acquired,
            _hash(archive), _hash(checksum),
        )
        archive_url, checksum_url = request.urls
        capture = _unwrap(capture_binance_usdm_koru_price_bars_source_bounded_v1(
            request, _fetch({archive_url: archive, checksum_url: checksum})
        ), f"{kind.value} capture {date}")
        results.append(_unwrap(normalize_binance_usdm_koru_price_bars_source_bounded_v1(capture), f"{kind.value} normalization {date}"))
    return tuple(results)


def _retained_price(kind: Any, execution: Mapping[str, Any], base: Mapping[str, Any], files: Mapping[str, Mapping[str, Any]]) -> Any:
    directory = "mark" if kind is BinanceUsdmKoruPriceBarsSourceKindV1.MARK_PRICE else "index"
    raw_name = f"binance_{directory}_raw.csv"
    dataset = execution["datasets"]["markPriceKlines_1h" if directory == "mark" else "indexPriceKlines_1h"]
    binding = dataset["derived_2026_08_24"]["derivation_binding"]
    prefix = f"binance_usdm/priceBars/{directory}/1h/derived-bounded/2026-08-24/"
    derived = prefix + "KORUUSDT-1h-2026-08-24.discovery-bounded.csv"
    endpoint = "https://fapi.binance.com/fapi/v1/markPriceKlines" if directory == "mark" else "https://fapi.binance.com/fapi/v1/indexPriceKlines"
    parameter = "symbol" if directory == "mark" else "pair"
    authority = BinanceUsdmKoruRetainedPriceBarsAuthorityV1(
        "binance_fapi_price_bars_raw_csv_v1", f"research/koruusdt/data/{raw_name}", binding["input"]["sha256"],
        _utc_ns(binding["frozen_source_metadata"]["as_of_utc"]), "research/koruusdt/data/manifest.json",
        _hash(BASE_MANIFEST.read_bytes()), base["manifest_sha256"], endpoint,
        canonical_sha256({"endTime": END_MS - 1, "interval": "1h", "limit": 1000, "startTime": 1_782_136_500_000, parameter: "KORUUSDT"}),
        UtcInstant(1_782_136_500_000_000_000), UtcInstant(END_MS * 1_000_000),
        "binance.fapi.completed-kline-close-exclusive.v1", UtcInstant(1_787_529_600_000_000_000),
        UtcInstant(END_MS * 1_000_000), derived.removeprefix(prefix), files[derived]["sha256"],
        "binance_usdm_koru_price_bars_discovery_bounded_csv_7_column_scale8_v1",
    )
    derived_bytes = _checked(derived, files)
    accepted_archive, accepted_checksum = build_binance_usdm_koru_price_bars_retained_observations_evidence_v1(authority, derived_bytes)
    acquired = _utc_ns(PRICE_ACQUIRED_AT)
    request = BinanceUsdmKoruPriceBarsSourceBoundedRequestV1(
        kind, INSTRUMENT, "1h", "2026-08-24", acquired, acquired, _hash(accepted_archive), _hash(accepted_checksum), authority
    )
    capture = _unwrap(capture_binance_usdm_koru_price_bars_from_retained_observations_v1(
        request, (DATA / raw_name).read_bytes(), BASE_MANIFEST.read_bytes(), derived_bytes, accepted_archive, accepted_checksum
    ), f"retained {kind.value} capture")
    return _unwrap(normalize_binance_usdm_koru_price_bars_source_bounded_v1(capture), f"retained {kind.value} normalization")


def _funding(files: Mapping[str, Mapping[str, Any]]) -> Any:
    prefix = "binance_usdm/fundingHistory/accepted-capture/"
    raw, receipt_bytes = _checked(prefix + "funding-history.json", files), _checked(prefix + "acquisition-receipt.json", files)
    receipt = json.loads(receipt_bytes)
    request_values = receipt["request"]
    request = BinanceUsdmKoruFundingRateHistorySourceBoundedRequestV1(
        INSTRUMENT, request_values["start_time_milliseconds"], request_values["end_time_milliseconds"], request_values["limit"], receipt["response_sha256"]
    )
    response = BinanceUsdmKoruFundingRateHistoryTransportResponseV1(
        "GET", receipt["url"], receipt["url"], receipt["status"], raw, receipt["date_header"], _utc_ns(receipt["captured_at_utc"])
    )
    capture = _unwrap(capture_binance_usdm_koru_funding_rate_history_source_bounded_v1(request, lambda _url: response), "funding capture")
    return _unwrap(normalize_binance_usdm_koru_funding_rate_history_source_bounded_v1(capture), "funding normalization")


def _boundaries(gap: Mapping[str, Any]) -> tuple[Any, ...]:
    events = gap.get("actual_first_trade_projections", {}).get("events")
    if type(events) is not list or len(events) != 611:
        raise ValueError("retained gap audit boundary cover invalid")
    values = tuple(
        BinanceUsdmKoruExecutionBoundaryV1(UtcInstant(_utc_ns(row["boundary_utc"])), UtcInstant(_utc_ns(row["cutoff_utc"])))
        for row in events
    )
    if values != tuple(sorted(values, key=lambda item: item.boundary.epoch_nanoseconds)):
        raise ValueError("retained gap audit boundaries are not canonical")
    return values


def build_source() -> Any:
    """Full retained replay using only exported Builder/Domain value APIs."""
    authority_manifest = _authority_manifest()
    authority = _calendar_authority(authority_manifest)
    execution, base, gap = _retained_manifests()
    files = _files(execution)
    aggregates = (*_official_aggregates(execution, files), _retained_aggregate(execution, files))
    mark = (*_official_prices(BinanceUsdmKoruPriceBarsSourceKindV1.MARK_PRICE, execution, files), _retained_price(BinanceUsdmKoruPriceBarsSourceKindV1.MARK_PRICE, execution, base, files))
    index = (*_official_prices(BinanceUsdmKoruPriceBarsSourceKindV1.INDEX_PRICE, execution, files), _retained_price(BinanceUsdmKoruPriceBarsSourceKindV1.INDEX_PRICE, execution, base, files))
    boundaries = _boundaries(gap)
    boundary_index = _unwrap(build_binance_usdm_koru_aggregate_trade_boundary_index_v1(
        BinanceUsdmKoruAggregateTradeBoundaryIndexRequestV1(
            aggregates, UtcInstant(START_MS * 1_000_000), UtcInstant(END_MS * 1_000_000), boundaries
        )
    ), "aggregate boundary index")
    return _unwrap(build_binance_usdm_koru_tradifi_source_projection_v2(
        BinanceUsdmKoruTradifiSourceProjectionRequestV2(
            UtcInstant(START_MS * 1_000_000), UtcInstant(END_MS * 1_000_000),
            canonical_sha256({"type": "koruusdt_retained_discovery_instrument_binding_v1", "instrument_id": INSTRUMENT.to_canonical_dict(), "symbol": "KORUUSDT", "contract_type": base["contractType"], "base_manifest_identity": base["manifest_sha256"]}),
            Scale(8), boundary_index, mark, index, _funding(files), authority,
        )
    ), "source projection")


def _artifact_event_id(ref: ArtifactRef) -> str:
    return f"koru-artifact-publication-v1:{ref.content_hash}"


def _artifact_publication_record(envelope: ArtifactEnvelope, ref: ArtifactRef) -> dict[str, object]:
    return {
        "type": "koru_artifact_publication_v1",
        "schema_version": 1,
        "artifact_ref": ref.to_canonical_dict(),
        "envelope": envelope.to_canonical_dict(),
        "envelope_sha256": canonical_sha256(envelope),
    }


def _record_ref_identities(record: Mapping[str, object]) -> list[object]:
    """Return the canonical ref identities embedded in an owner-log payload."""
    identities: list[object] = []

    def visit(value: object) -> None:
        if type(value) is dict:
            if value.get("type") in {"artifact_ref", "market_bundle_ref"}:
                identities.append(value)
            for key in sorted(value):
                visit(value[key])
        elif type(value) is list:
            for item in value:
                visit(item)

    visit(json.loads(canonical_bytes(record)))
    return identities


def _record_event_id(record: Mapping[str, object]) -> str:
    return "koru-publication-record-v1:" + canonical_sha256({
        "canonical_payload": record,
        "ref_identities": _record_ref_identities(record),
    })


def _owner_record_event_id(record: Mapping[str, object]) -> str:
    if record.get("type") != "koru_artifact_publication_v1":
        return _record_event_id(record)
    ref = record.get("artifact_ref")
    envelope = record.get("envelope")
    if type(ref) is not dict or type(envelope) is not dict:
        raise ValueError("artifact publication record is malformed")
    reconstructed = ArtifactEnvelope(
        envelope["artifact_type"], envelope["schema_version"], envelope["payload"], envelope["content_hash"]
    )
    expected_ref = ArtifactRef.from_envelope(reconstructed)
    if (
        ref != expected_ref.to_canonical_dict()
        or record.get("envelope_sha256") != canonical_sha256(reconstructed)
    ):
        raise ValueError("artifact publication record identity mismatch")
    return _artifact_event_id(expected_ref)


def _source_projection_record(source: Any) -> dict[str, object]:
    identity = KoruTradifiSourceProjectionContentIdentityV2(
        source.fragment_digest, source.request.request_hash
    )
    return {
        "type": "koru_source_projection_publication_v1",
        "schema_version": 1,
        "source_projection_content_identity": identity.to_canonical_dict(),
        "source_fragment_digest": source.fragment_digest,
        "source_projection_request_hash": source.request.request_hash,
    }


class KoruEconomicsArtifactStoreV1:
    """Foundation CAS adapter that owner-logs every stored envelope."""

    def __init__(self, foundation: LocalFoundation) -> None:
        if type(foundation) is not LocalFoundation:
            raise TypeError("foundation must be a LocalFoundation")
        self._foundation = foundation
        self._publication_records: list[dict[str, object]] = []

    @property
    def publication_records(self) -> tuple[dict[str, object], ...]:
        return tuple(self._publication_records)

    def put(self, *, envelope: ArtifactEnvelope) -> ArtifactRef:
        ref = self._foundation.put(envelope=envelope)
        if ref != ArtifactRef.from_envelope(envelope):
            raise ValueError("Foundation returned an unexpected artifact ref")
        result = self.read(ref=ref)
        if (
            result.envelope != envelope
            or result.source_bytes != canonical_bytes(envelope)
            or result.source_hash != canonical_sha256(envelope)
        ):
            raise ValueError("Foundation artifact readback mismatch")
        record = _artifact_publication_record(envelope, ref)
        self._foundation.append(OWNER_LOG, _owner_record_event_id(record), canonical_bytes(record))
        self._publication_records.append(record)
        return ref

    def read(self, *, ref: ArtifactRef) -> ArtifactReadResult:
        return self._foundation.read(ref=ref)


def _premium_authorities(source: Any, store: KoruEconomicsArtifactStoreV1) -> tuple[Any, ...]:
    rows = []
    for number, entry in enumerate(("20", "30", "40", "60"), 1):
        premium_id = f"KORU-PRM-{number:02d}"
        placeholder = ArtifactRef("strategy_definition", 1, "sha256:" + "0" * 64)
        recipe = KoruDirectionalTargetRecipeV1(
            "mark_index_premium", premium_id, f"strategy-{premium_id}", f"sleeve-{premium_id}", placeholder,
            ArtifactRef("strategy_parameter_set", 1, "sha256:" + "0" * 64), premium_id, INSTRUMENT, "0.25", "1h",
            KoruMarkIndexPremiumParametersV1(entry, "5", 12),
        )
        strategy = ArtifactEnvelope.create("strategy_definition", 1, canonical_koru_premium_payload_v1(recipe, artifact_type="strategy_definition"))
        parameter = ArtifactEnvelope.create("strategy_parameter_set", 1, canonical_koru_premium_payload_v1(recipe, artifact_type="strategy_parameter_set"))
        strategy_ref, parameter_ref = store.put(envelope=strategy), store.put(envelope=parameter)
        rows.append(build_koru_premium_recipe_authority_v1(
            replace(recipe, strategy_ref=strategy_ref, parameter_ref=parameter_ref), strategy, parameter
        ))
    return tuple(rows)


def _entry_summary(entry: Any) -> dict[str, object]:
    return {
        "event_id": entry.event_id,
        "entry_ref": {
            "log_name": entry.entry_ref.log_name,
            "log_sequence": entry.entry_ref.log_sequence,
            "receipt_hash": entry.entry_ref.receipt_hash,
        },
        "payload_sha256": entry.payload_source_hash,
    }


def _append_owner_record(foundation: LocalFoundation, record: Mapping[str, object]) -> None:
    event_id, payload = _owner_record_event_id(record), canonical_bytes(record)
    receipt = foundation.append(OWNER_LOG, event_id, payload)
    entry = next(
        (item for item in foundation.entries(OWNER_LOG, through=receipt.entry_ref) if item.entry_ref == receipt.entry_ref),
        None,
    )
    if entry is None or entry.event_id != event_id or entry.payload != payload:
        raise ValueError("owner-log record readback mismatch")


def _checkpoint_summary(
    foundation: LocalFoundation, expected_records: tuple[Mapping[str, object], ...] = (),
) -> dict[str, object]:
    checkpoint = foundation.checkpoint(OWNER_LOG)
    entries = foundation.entries(OWNER_LOG, through=checkpoint)
    summary: dict[str, object] = {
        "checkpoint": {
            "log_name": checkpoint.log_name,
            "as_of": checkpoint.as_of,
            "upper_log_sequence": checkpoint.upper_log_sequence,
            "head_receipt_hash": checkpoint.head_receipt_hash,
        },
        "entries": [_entry_summary(entry) for entry in entries],
    }
    if expected_records:
        expected = tuple((_owner_record_event_id(record), canonical_bytes(record)) for record in expected_records)
        if len({event_id for event_id, _payload in expected}) != len(expected):
            raise ValueError("owner-log expected record event IDs are not unique")
        actual = tuple((entry.event_id, entry.payload) for entry in entries)
        if len({event_id for event_id, _payload in actual}) != len(actual):
            raise ValueError("owner-log record event IDs are not unique")
        if (
            checkpoint.log_name != OWNER_LOG
            or checkpoint.upper_log_sequence != len(expected)
            or checkpoint.head_receipt_hash != entries[-1].receipt_hash
        ):
            raise ValueError("owner-log checkpoint identity does not cover expected records")
        for event_id, payload in actual:
            try:
                record = json.loads(payload)
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ValueError("owner-log record payload is invalid") from error
            if type(record) is not dict or payload != canonical_bytes(record) or event_id != _owner_record_event_id(record):
                raise ValueError("owner-log record payload or ref identity is noncanonical")
        if set(actual) != set(expected) or actual != expected:
            raise ValueError("owner-log records do not exactly cover expected records")
        summary["publication_records"] = [_entry_summary(entry) for entry in entries]
    return summary


def _compiler_result_record(source: Any, readers: Any) -> dict[str, object]:
    bindings = tuple(readers.bindings)
    if not bindings:
        raise ValueError("compiler bindings are empty")
    first = bindings[0]
    if any(binding.source_fragment_digest != source.fragment_digest for binding in bindings):
        raise ValueError("compiler source fragment binding")
    return {
        "type": "koru_compiler_result_publication_v1",
        "schema_version": 1,
        "compiler_result_ref": first.compiler_result_ref.to_canonical_dict(),
        "compiler_result_digest": first.compiler_result_digest,
        "source_fragment_digest": source.fragment_digest,
        "scope_ref": first.scope_ref.to_canonical_dict(),
        "scope_digest": first.scope_digest,
        "ordered_prm_recipes": [
            {
                "premium_id": binding.premium_id,
                "recipe_ref": binding.parameter_ref.to_canonical_dict(),
                "recipe_digest": binding.recipe_digest,
                "target_stream_key": binding.target_stream_key,
                "target_stream_digest": binding.target_stream_digest,
            }
            for binding in bindings
        ],
    }


def _overlay_publication_record(binding: Any) -> dict[str, object]:
    return {
        "type": "koru_prm_overlay_publication_v1",
        "schema_version": 1,
        "premium_id": binding.premium_id,
        "overlay_bundle_ref": binding.overlay_bundle_ref.to_canonical_dict(),
        "overlay_bundle_digest": binding.overlay_bundle_digest,
        "overlay_manifest": json.loads(canonical_bytes(binding.reader.manifest)),
        "target_stream_ref": binding.parameter_ref.to_canonical_dict(),
        "target_stream_key": binding.target_stream_key,
        "target_stream_digest": binding.target_stream_digest,
        "recipe_refs": {
            "strategy_ref": binding.strategy_ref.to_canonical_dict(),
            "parameter_ref": binding.parameter_ref.to_canonical_dict(),
        },
        "recipe_digest": binding.recipe_digest,
        "economics_bundle_ref": binding.economics_bundle_ref.to_canonical_dict(),
        "economics_bundle_digest": binding.economics_bundle_digest,
        "economics_authority_digest": binding.economics_authority_digest,
    }


def _owner_publication_records(source: Any, readers: Any) -> tuple[dict[str, object], ...]:
    return (
        _compiler_result_record(source, readers),
        *(_overlay_publication_record(binding) for binding in readers.bindings),
    )


def _reader_set_record(source: Any, economics: Any, readers: Any) -> dict[str, object]:
    return {
        "type": "koru_premium_reader_set_publication_v1",
        "schema_version": 1,
        "source_fragment_digest": source.fragment_digest,
        "economics_authority_digest": economics.authority_digest,
        "economics_bundle_ref": economics.bundle_ref.to_canonical_dict(),
        "economics_authority_refs": [ref.to_canonical_dict() for ref in economics.authority_refs],
        "reader_set_digest": readers.reader_set_digest,
        "bindings": [
            {
                "premium_id": binding.premium_id,
                "strategy_ref": binding.strategy_ref.to_canonical_dict(),
                "parameter_ref": binding.parameter_ref.to_canonical_dict(),
                "compiler_result_ref": binding.compiler_result_ref.to_canonical_dict(),
                "overlay_bundle_ref": binding.overlay_bundle_ref.to_canonical_dict(),
            }
            for binding in readers.bindings
        ],
    }


def _expected_owner_records(
    source: Any, economics: Any, readers: Any, artifact_records: tuple[dict[str, object], ...],
) -> tuple[dict[str, object], ...]:
    publications = _owner_publication_records(source, readers)
    overlays = [record for record in publications if record["type"] == "koru_prm_overlay_publication_v1"]
    if (
        len(publications) != 5
        or [record["premium_id"] for record in overlays] != ["KORU-PRM-01", "KORU-PRM-02", "KORU-PRM-03", "KORU-PRM-04"]
    ):
        raise ValueError("owner-log must include one compiler result and exactly four overlays")
    return (
        _source_projection_record(source),
        *artifact_records,
        *publications,
        _reader_set_record(source, economics, readers),
    )


def full_preflight(
    foundation_root: Path | None = None, max_seconds: int = DEFAULT_FULL_MAX_SECONDS,
) -> dict[str, object]:
    """Build source/economics/readers only; this is not an Experiment entrypoint."""
    with full_deadline(max_seconds):
        smoke(foundation_root)
        source = build_source()
        with tempfile.TemporaryDirectory(prefix="koru-public-preflight-") as directory:
            root = Path(directory)
            foundation = LocalFoundation(foundation_root) if foundation_root is not None else LocalFoundation(root / "foundation")
            store = KoruEconomicsArtifactStoreV1(foundation)
            _append_owner_record(foundation, _source_projection_record(source))
            economics = _unwrap(publish_koru_tradifi_economics_bundle_v3(
                KoruTradifiEconomicsBundleRequestV3(
                    source, KoruTradifiSourceProjectionContentIdentityV2(source.fragment_digest, source.request.request_hash),
                    KoruTradifiEconomicsTermsV3.from_source_projection(source, execution_account_id="account-1"), store, root / "economics",
                )
            ), "target-free economics bundle")
            readers = _unwrap(build_koru_premium_reader_set_v1(
                KoruPremiumReaderSetBuildRequestV1(economics, _premium_authorities(source, store), root / "premium-readers")
            ), "premium reader set")
            publication_records = _owner_publication_records(source, readers)
            for record in publication_records:
                _append_owner_record(foundation, record)
            _append_owner_record(foundation, _reader_set_record(source, economics, readers))
            expected_records = _expected_owner_records(source, economics, readers, store.publication_records)
            return {
                "mode": "full", "network_performed": False, "holdout_touched": False,
                "source_fragment_digest": source.fragment_digest, "economics_authority_digest": economics.authority_digest,
                "artifact_refs": [
                    ref.to_canonical_dict()
                    for ref in (
                        *economics.authority_refs,
                        *(binding.strategy_ref for binding in readers.bindings),
                        *(binding.parameter_ref for binding in readers.bindings),
                    )
                ],
                "premium_reader_ids": [binding.premium_id for binding in readers.bindings],
                "owner_log": _checkpoint_summary(foundation, expected_records),
                "stopped_before": "Experiment_Holdout_and_Backtest",
            }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--smoke", action="store_true", help="bounded source authority validation; default")
    mode.add_argument("--full", action="store_true", help="full retained source/economics/reader preflight; does not run an Experiment")
    parser.add_argument("--max-seconds", type=int, default=DEFAULT_FULL_MAX_SECONDS, help="full-only process deadline (1-300; default: 300)")
    parser.add_argument("--foundation-root", type=Path, help="Foundation root; smoke leaves it absent or requires an empty directory, while full initializes and publishes to it")
    args = parser.parse_args(argv)
    if args.full:
        try:
            _validate_full_max_seconds(args.max_seconds)
        except ValueError as error:
            parser.error(str(error))
    try:
        with deny_network():
            result = full_preflight(args.foundation_root, args.max_seconds) if args.full else smoke(args.foundation_root)
    except FullPreflightDeadlineExceeded as error:
        print(f"{error}; no successful summary written", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
