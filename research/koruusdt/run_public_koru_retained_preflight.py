#!/usr/bin/env python3
"""Offline public-root preflight for the retained KORU premium discovery inputs.

`--smoke` validates the immutable source authority and discovery boundary, then
stops before source replay/economics.  `--full` is the explicit, offline
preflight that reconstructs the retained source, target-free economics bundle,
and four premium readers; it never starts an Experiment or Backtest.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import signal
import socket
import stat
import subprocess
import sys
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn, cast
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
ATTEMPT_SCHEMA = "koru_retained_preflight_attempt_v1"
INPUT_CATALOG_SCHEMA = "koru_retained_preflight_input_catalog_v1"
RECEIPT_SCHEMA = "koru_retained_preflight_receipt_v1"
COMPLETE_MARKER = "complete.json"
TIMEOUT_MARKER = "timeout.json"
TIMING_KEYS = ("snapshot_open_elapsed_ns", "child_elapsed_ns")
INPUT_SNAPSHOT_AUTHORITY_SCHEMA = "koru_retained_preflight_input_snapshot_authority_v1"
RAW_SNAPSHOT_PROVENANCE_SCHEMA = "koru_retained_preflight_raw_snapshot_provenance_v1"
SOURCE_PROJECTION_LOG = "research.source_projections.v1"
SOURCE_PROJECTION_PUBLICATION_SCHEMA = "koru_source_projection_publication_authority_v1"
SOURCE_PROJECTION_PUBLICATION_RECEIPT_SCHEMA = "koru_source_projection_publication_receipt_v1"
SOURCE_PROJECTION_PUBLICATION_IDENTITY_SCHEMA = "koru_source_projection_publication_attempt_v1"
SOURCE_PROJECTION_PUBLICATION_FACT_SCHEMA = "koru_source_projection_publication_fact_v1"
SOURCE_PROJECTION_PROGRESS_SCHEMA = "koru_source_projection_progress_v1"
SOURCE_PROJECTION_PROGRESS = "progress.json"
SOURCE_PROJECTION_PHASES = (
    "raw_snapshot_open_verification",
    "aggregate_retained_capture",
    "mark_normalization",
    "index_normalization",
    "aggregate_boundary_index",
    "funding_normalization",
    "source_projection_assembly",
    "authority_serialization",
    "owner_log_publication",
)
DEFAULT_SOURCE_PROJECTION_MAX_SECONDS = 300
MAX_SOURCE_PROJECTION_SECONDS = 900
_SOURCE_PUBLICATION_TIMEOUT_TEST_MODE = "source-publication-timeout-v1"
_SOURCE_PUBLICATION_FAILURE_TEST_MODE = "source-publication-failure-v1"
_SOURCE_PUBLICATION_TIMEOUT_AFTER_PHASE_TEST_PREFIX = "source-publication-timeout-after-phase:"
_RAW_INPUT_VIEW: RawBlobSnapshotView | None = None
_RAW_INPUT_MEMBER_KEYS: dict[str, str] | None = None
TERMINATE_GRACE_SECONDS = 1.0
_TIMEOUT_TEST_MODE = "foundation-timeout-v1"

sys.path.insert(0, str(ROOT / "research-platform" / "src"))

for package in (
    "trading-domain",
    "trading-kernel",
    "market-data-contracts",
    "market-bundle-builder",
    "backtest-runtime",
):
    sys.path.insert(0, str(BACKTEST / "packages" / package / "src"))

from crypto_quant_bundle_builder import (
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
    BinanceUsdmKoruTradifiSourceProjectionRequestV2,
    KoruDirectionalTargetRecipeV1,
    KoruMarkIndexPremiumParametersV1,
    KoruPremiumReaderSetBuildRequestV1,
    KoruTradifiEconomicsBundleRequestV3,
    KoruTradifiEconomicsTermsV3,
    KoruTradifiSourceProjectionContentIdentityV2,
    RawBlobSnapshotSourceMember,
    RawBlobSnapshotView,
    RawSourceMember,
    build_binance_usdm_koru_aggregate_trade_boundary_index_v1,
    build_binance_usdm_koru_price_bars_retained_observations_evidence_v1,
    build_binance_usdm_koru_tradifi_source_projection_v2,
    build_koru_premium_reader_set_v1,
    build_koru_premium_recipe_authority_v1,
    build_koru_tradifi_calendar_unit_authority_v1,
    canonical_koru_premium_payload_v1,
    capture_binance_usdm_koru_aggregate_trades_from_retained_rest_v1,
    capture_binance_usdm_koru_aggregate_trades_source_bounded_v1,
    capture_binance_usdm_koru_funding_rate_history_source_bounded_v1,
    capture_binance_usdm_koru_price_bars_from_retained_observations_v1,
    capture_binance_usdm_koru_price_bars_source_bounded_v1,
    normalize_binance_usdm_koru_funding_rate_history_source_bounded_v1,
    normalize_binance_usdm_koru_price_bars_source_bounded_v1,
    open_binance_usdm_koru_tradifi_source_projection_authority_v1,
    publish_koru_tradifi_economics_bundle_v3,
    serialize_binance_usdm_koru_tradifi_source_projection_authority_v1,
    verify_koru_tradifi_calendar_unit_authority_v1,
)
from crypto_quant_domain import (
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
from crypto_quant_foundation import LocalFoundation, LogCheckpoint, LogEntryRef
from crypto_quant_research import (
    KORU_PREMIUM_PREFLIGHT_AUTHORITY_V2_LOG,
    open_published_koru_premium_preflight_authority_v2,
    open_verified_raw_blob_snapshot,
    publish_raw_blob_snapshot,
)

INSTRUMENT = InstrumentId(VenueId("binance_usdm"), "koru-usdt-tradifi-perpetual")
PREMIUM_PREFLIGHT_AUTHORITY_V2_LOCATOR_SCHEMA = "koru_premium_preflight_authority_v2_locator"
PREMIUM_PREFLIGHT_AUTHORITY_V2_CONSUMER_RECEIPT_SCHEMA = "koru_premium_preflight_authority_v2_consumer_receipt"
_PREMIUM_PREFLIGHT_AUTHORITY_V2_READER_IDS = (
    "KORU-PRM-01", "KORU-PRM-02", "KORU-PRM-03", "KORU-PRM-04",
)
_PREMIUM_PREFLIGHT_AUTHORITY_V2_STOPPED_BEFORE = "Experiment_Holdout_and_Backtest"


def _hash(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _canonical_pretty_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def _load(path: Path) -> dict[str, Any]:
    return _load_bytes(path.read_bytes(), str(path))


def _load_bytes(raw: bytes, label: str) -> dict[str, Any]:
    value = json.loads(raw)
    if type(value) is not dict:
        raise ValueError(f"{label}: expected JSON object")
    return value


def _input_member_key(relative: str) -> str:
    if type(relative) is not str or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("retained input path is invalid")
    return "data/" + relative


def _input_bytes(relative: str) -> bytes:
    """Read one retained input only through the verified raw view during full replay."""
    key = _input_member_key(relative)
    if _RAW_INPUT_VIEW is not None:
        if _RAW_INPUT_MEMBER_KEYS is None or key not in _RAW_INPUT_MEMBER_KEYS:
            raise ValueError("retained input is absent from verified raw snapshot")
        return _RAW_INPUT_VIEW.member_bytes(_RAW_INPUT_MEMBER_KEYS[key])
    return (DATA / relative).read_bytes()


def _input_member_keys() -> set[str]:
    if _RAW_INPUT_VIEW is not None:
        if _RAW_INPUT_MEMBER_KEYS is None:
            raise ValueError("verified raw snapshot member mapping is unavailable")
        published = {member.member_key for member in _RAW_INPUT_VIEW.manifest.members}
        return {path for path, member_key in _RAW_INPUT_MEMBER_KEYS.items() if member_key in published}
    return {"data/" + path.relative_to(DATA).as_posix() for path in DATA.rglob("*") if path.is_file()}


def _self_hash(value: dict[str, Any], path: Path | str) -> None:
    expected = value.get("manifest_sha256")
    body = dict(value)
    body["manifest_sha256"] = ""
    if type(expected) is not str or expected != _hash(_canonical_json(body)):
        raise ValueError(f"{path}: manifest self-hash mismatch")


def _utc_ns(value: str) -> int:
    parsed = datetime.fromisoformat(value)
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
    """The parent watchdog archived a child that exceeded its deadline."""

    def __init__(self, max_seconds: int, receipt_path: Path) -> None:
        self.max_seconds = max_seconds
        self.receipt_path = receipt_path
        super().__init__(
            f"full preflight deadline exceeded after {max_seconds} seconds; "
            f"timeout receipt: {receipt_path}"
        )


def _validate_full_max_seconds(max_seconds: int) -> int:
    if type(max_seconds) is not int or not 1 <= max_seconds <= MAX_FULL_SECONDS:
        raise ValueError(f"full --max-seconds must be an integer from 1 to {MAX_FULL_SECONDS}")
    return max_seconds


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
    relative = "public_preflight_sources_v1/manifest.json"
    raw = _input_bytes(relative)
    value = _load_bytes(raw, relative)
    if raw != _canonical_pretty_json(value):
        raise ValueError("public preflight authority manifest bytes are noncanonical")
    _self_hash(value, relative)
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
    prefix = "data/public_preflight_sources_v1/"
    actual_files = {
        member.removeprefix(prefix)
        for member in _input_member_keys() if member.startswith(prefix)
    }
    if actual_files != {"manifest.json", *expected}:
        raise ValueError("public preflight authority file cover mismatch")
    for filename, expected_hash in expected.items():
        row = by_name[filename]
        raw = _input_bytes("public_preflight_sources_v1/" + filename)
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
        source: _utc_ns(_load_bytes(
            _input_bytes(f"public_preflight_sources_v1/{source}/acquisition-receipt.json"),
            f"public_preflight_sources_v1/{source}/acquisition-receipt.json",
        )["captured_at_utc"])
        for source in ("binance", "krx", "nyse")
    }
    members = tuple(
        RawSourceMember(
            member_key, _input_bytes("public_preflight_sources_v1/" + member_key), "0644",
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
    names = ("execution_data_manifest.json", "manifest.json", "execution_gap_impact.json")
    execution, base, gap = tuple(_load_bytes(_input_bytes(name), name) for name in names)
    for value, name in zip((execution, base, gap), names, strict=True):
        _self_hash(value, name)
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
    raw = _input_bytes(relative_path)
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
        "research/koruusdt/data/execution_data_manifest.json", _hash(_input_bytes("execution_data_manifest.json")),
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
        request, _input_bytes("execution_data_manifest.json"), tuple(page_bytes), _checked(derived, files),
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
        _hash(_input_bytes("manifest.json")), base["manifest_sha256"], endpoint,
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
        request, _input_bytes(raw_name), _input_bytes("manifest.json"), derived_bytes, accepted_archive, accepted_checksum
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


def _diagnostic_row_count(entries: object) -> int:
    if type(entries) is not list:
        return 0
    return sum(entry["row_count"] for entry in entries if type(entry) is dict and type(entry.get("row_count")) is int)


def build_source(*, phase_completed: Callable[[str, Mapping[str, int]], None] | None = None) -> Any:
    """Full retained replay using only exported Builder/Domain value APIs."""
    def complete(phase: str, counts: Mapping[str, int]) -> None:
        if phase_completed is not None:
            phase_completed(phase, counts)

    authority_manifest = _authority_manifest()
    authority = _calendar_authority(authority_manifest)
    execution, base, gap = _retained_manifests()
    files = _files(execution)
    aggregate_daily = execution["datasets"]["aggTrades"]["daily"]
    aggregates = (*_official_aggregates(execution, files), _retained_aggregate(execution, files))
    complete("aggregate_retained_capture", {
        "aggregate_capture_count": len(aggregates),
        "aggregate_daily_input_row_count": _diagnostic_row_count(aggregate_daily),
        "aggregate_retained_page_count": sum(
            1 for path, entry in files.items()
            if path.startswith("binance_usdm/aggTrades/rest-bounded/")
            and entry.get("status") == "canonical_rest_response"
        ),
    })
    mark_daily = execution["datasets"]["markPriceKlines_1h"]["daily"]
    mark = (*_official_prices(BinanceUsdmKoruPriceBarsSourceKindV1.MARK_PRICE, execution, files), _retained_price(BinanceUsdmKoruPriceBarsSourceKindV1.MARK_PRICE, execution, base, files))
    complete("mark_normalization", {
        "mark_normalization_count": len(mark),
        "mark_daily_input_row_count": _diagnostic_row_count(mark_daily),
    })
    index_daily = execution["datasets"]["indexPriceKlines_1h"]["daily"]
    index = (*_official_prices(BinanceUsdmKoruPriceBarsSourceKindV1.INDEX_PRICE, execution, files), _retained_price(BinanceUsdmKoruPriceBarsSourceKindV1.INDEX_PRICE, execution, base, files))
    complete("index_normalization", {
        "index_normalization_count": len(index),
        "index_daily_input_row_count": _diagnostic_row_count(index_daily),
    })
    boundaries = _boundaries(gap)
    boundary_index = _unwrap(build_binance_usdm_koru_aggregate_trade_boundary_index_v1(
        BinanceUsdmKoruAggregateTradeBoundaryIndexRequestV1(
            aggregates, UtcInstant(START_MS * 1_000_000), UtcInstant(END_MS * 1_000_000), boundaries
        )
    ), "aggregate boundary index")
    complete("aggregate_boundary_index", {"aggregate_boundary_event_count": len(boundaries)})
    funding = _funding(files)
    complete("funding_normalization", {
        "funding_input_event_count": _diagnostic_row_count([files.get("binance_usdm/fundingHistory/accepted-capture/funding-history.json", {})]),
    })
    source = _unwrap(build_binance_usdm_koru_tradifi_source_projection_v2(
        BinanceUsdmKoruTradifiSourceProjectionRequestV2(
            UtcInstant(START_MS * 1_000_000), UtcInstant(END_MS * 1_000_000),
            canonical_sha256({"type": "koruusdt_retained_discovery_instrument_binding_v1", "instrument_id": INSTRUMENT.to_canonical_dict(), "symbol": "KORUUSDT", "contract_type": base["contractType"], "base_manifest_identity": base["manifest_sha256"]}),
            Scale(8), boundary_index, mark, index, funding, authority,
        )
    ), "source projection")
    complete("source_projection_assembly", {
        "aggregate_capture_count": len(aggregates), "mark_normalization_count": len(mark),
        "index_normalization_count": len(index), "aggregate_boundary_event_count": len(boundaries),
    })
    return source


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


def _log_entry_ref_from_canonical(value: object) -> LogEntryRef:
    if type(value) is not dict or set(value) != {"log_name", "log_sequence", "receipt_hash"}:
        raise ValueError("input snapshot publication entry ref is invalid")
    try:
        entry_ref = LogEntryRef(value["log_name"], value["log_sequence"], value["receipt_hash"])
    except (TypeError, ValueError) as error:
        raise ValueError("input snapshot publication entry ref is invalid") from error
    if entry_ref.log_name != "research.raw_snapshots.v1":
        raise ValueError("input snapshot publication log is invalid")
    return entry_ref


def _artifact_ref_from_canonical(value: object) -> ArtifactRef:
    if type(value) is not dict or set(value) != {"type", "artifact_type", "schema_version", "content_hash"}:
        raise ValueError("input snapshot manifest ref is invalid")
    if value["type"] != "artifact_ref":
        raise ValueError("input snapshot manifest ref is invalid")
    try:
        return ArtifactRef(value["artifact_type"], value["schema_version"], value["content_hash"])
    except (TypeError, ValueError) as error:
        raise ValueError("input snapshot manifest ref is invalid") from error


def _canonical_input_snapshot_authority(value: Mapping[str, object]) -> dict[str, object]:
    required = {
        "type", "schema_version", "manifest_ref", "snapshot_id", "provenance_hash",
        "publication_entry_ref", "input_catalog_sha256",
    }
    if type(value) is not dict or set(value) != required or value.get("type") != INPUT_SNAPSHOT_AUTHORITY_SCHEMA or value.get("schema_version") != 1:
        raise ValueError("input snapshot authority schema mismatch")
    manifest_ref = _artifact_ref_from_canonical(value["manifest_ref"])
    entry_ref = _log_entry_ref_from_canonical(value["publication_entry_ref"])
    if (
        manifest_ref.artifact_type != "raw_blob_snapshot_manifest"
        or manifest_ref.schema_version != 1
        or any(type(value[key]) is not str for key in ("snapshot_id", "provenance_hash", "input_catalog_sha256"))
    ):
        raise ValueError("input snapshot authority identity mismatch")
    canonical = {
        "type": INPUT_SNAPSHOT_AUTHORITY_SCHEMA,
        "schema_version": 1,
        "manifest_ref": manifest_ref.to_canonical_dict(),
        "snapshot_id": value["snapshot_id"],
        "provenance_hash": value["provenance_hash"],
        "publication_entry_ref": {
            "log_name": entry_ref.log_name,
            "log_sequence": entry_ref.log_sequence,
            "receipt_hash": entry_ref.receipt_hash,
        },
        "input_catalog_sha256": value["input_catalog_sha256"],
    }
    if canonical != value:
        raise ValueError("input snapshot authority is noncanonical")
    return canonical


def _full_mode_config(max_seconds: int, input_snapshot_authority: Mapping[str, object]) -> dict[str, object]:
    return {
        "type": "koru_retained_preflight_full_mode_config_v1",
        "schema_version": 1,
        "max_seconds": _validate_full_max_seconds(max_seconds),
        "hard_cap_seconds": MAX_FULL_SECONDS,
        "owner_log": OWNER_LOG,
        "input_snapshot": "raw_blob_snapshot_v1",
        "input_snapshot_authority": _canonical_input_snapshot_authority(input_snapshot_authority),
        "source_projection_resume": "forbidden_replay_retained_input",
    }


def _raw_snapshot_catalog_config() -> dict[str, object]:
    return {
        "type": "koru_retained_preflight_raw_snapshot_catalog_config_v1",
        "schema_version": 1,
        "input_snapshot": "raw_blob_snapshot_v1",
        "owner_log": "research.raw_snapshots.v1",
        "source_projection_resume": "forbidden_replay_retained_input",
    }


def _input_relative(path: Path) -> str:
    try:
        return "data/" + path.resolve().relative_to(DATA.resolve()).as_posix()
    except ValueError as error:
        raise ValueError(f"retained input is outside data root: {path}") from error


def _catalog_source_paths() -> tuple[Path, ...]:
    authority = _authority_manifest()
    execution, _base, _gap = _retained_manifests()
    files = _files(execution)
    paths = {
        AUTHORITY_MANIFEST,
        EXECUTION_MANIFEST,
        BASE_MANIFEST,
        GAP_AUDIT,
        DATA / "binance_mark_raw.csv",
        DATA / "binance_index_raw.csv",
        *(AUTHORITY_ROOT / row["filename"] for row in authority["members"]),
        *(DATA / relative for relative in files),
    }
    selected = tuple(sorted(paths, key=_input_relative))
    if any(path.is_symlink() for path in selected):
        raise ValueError("retained input catalog contains a symlink")
    if not selected or any(not path.is_file() for path in selected):
        raise ValueError("retained input catalog is incomplete")
    return selected


def _read_regular_source_bytes(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ValueError(f"retained input is unavailable: {path}") from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"retained input is not regular: {path}")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    raw = b"".join(chunks)
    if before.st_dev != after.st_dev or before.st_ino != after.st_ino or before.st_size != after.st_size:
        raise ValueError(f"retained input changed while reading: {path}")
    return raw


def _catalog_digest(value: Mapping[str, object]) -> str:
    body = dict(value)
    body["catalog_sha256"] = ""
    return _hash(_canonical_json(body))


def _allowed_koru_discovery_input_member_cover() -> frozenset[str]:
    """Canonical raw-member cover from retained manifests and authority sources."""
    return frozenset(_snapshot_member_key(_input_relative(path)) for path in _catalog_source_paths())


def _build_input_catalog(config: Mapping[str, object]) -> dict[str, object]:
    rows = []
    for path in _catalog_source_paths():
        raw = _read_regular_source_bytes(path)
        rows.append({"path": _input_relative(path), "sha256": _hash(raw), "size_bytes": len(raw)})
    catalog: dict[str, object] = {
        "type": INPUT_CATALOG_SCHEMA,
        "schema_version": 1,
        "full_mode_config": dict(config),
        "files": rows,
        "catalog_sha256": "",
    }
    if set(_snapshot_member_mapping(catalog).values()) != _allowed_koru_discovery_input_member_cover():
        raise ValueError("input catalog does not have the exact KORU discovery member cover")
    catalog["catalog_sha256"] = _catalog_digest(catalog)
    return catalog


def _validate_input_catalog(catalog: Mapping[str, object]) -> None:
    if set(catalog) != {"type", "schema_version", "full_mode_config", "files", "catalog_sha256"}:
        raise ValueError("input catalog schema mismatch")
    if catalog["type"] != INPUT_CATALOG_SCHEMA or catalog["schema_version"] != 1:
        raise ValueError("input catalog identity mismatch")
    if catalog["full_mode_config"] != _raw_snapshot_catalog_config() or type(catalog["files"]) is not list:
        raise ValueError("input catalog values mismatch")
    if catalog["catalog_sha256"] != _catalog_digest(catalog):
        raise ValueError("input catalog self-hash mismatch")
    files = cast(list[dict[str, object]], catalog["files"])
    paths: list[str] = []
    for row in files:
        path, digest, size = row.get("path"), row.get("sha256"), row.get("size_bytes")
        if (
            set(row) != {"path", "sha256", "size_bytes"}
            or type(path) is not str
            or not path.startswith("data/")
            or Path(path).is_absolute()
            or ".." in Path(path).parts
            or type(digest) is not str
            or type(size) is not int
            or size < 0
        ):
            raise ValueError("input catalog file row mismatch")
        paths.append(path)
    if not paths or paths != sorted(paths) or len(set(paths)) != len(paths):
        raise ValueError("input catalog file cover mismatch")


def _snapshot_member_key(path: str) -> str:
    return "retained/" + hashlib.sha256(path.encode("ascii")).hexdigest()


def _snapshot_member_mapping(catalog: Mapping[str, object]) -> dict[str, str]:
    mapping = {
        cast(str, row["path"]): _snapshot_member_key(cast(str, row["path"]))
        for row in cast(list[dict[str, object]], catalog["files"])
    }
    if len(mapping) != len(catalog["files"]) or len(set(mapping.values())) != len(mapping):
        raise ValueError("input snapshot member key mapping is invalid")
    return mapping


def _input_snapshot_authority(publication: object, catalog: Mapping[str, object]) -> dict[str, object]:
    manifest = publication.manifest
    return {
        "type": INPUT_SNAPSHOT_AUTHORITY_SCHEMA,
        "schema_version": 1,
        "manifest_ref": publication.manifest_ref.to_canonical_dict(),
        "snapshot_id": manifest.snapshot_id,
        "provenance_hash": manifest.provenance_hash,
        "publication_entry_ref": {
            "log_name": publication.publication_entry_ref.log_name,
            "log_sequence": publication.publication_entry_ref.log_sequence,
            "receipt_hash": publication.publication_entry_ref.receipt_hash,
        },
        "input_catalog_sha256": catalog["catalog_sha256"],
    }


def _open_input_snapshot_authority(
    foundation_root: Path, input_snapshot_authority: Mapping[str, object],
) -> tuple[dict[str, Any], RawBlobSnapshotView]:
    authority = _canonical_input_snapshot_authority(input_snapshot_authority)
    manifest_ref = _artifact_ref_from_canonical(authority["manifest_ref"])
    entry_ref = _log_entry_ref_from_canonical(authority["publication_entry_ref"])
    view = open_verified_raw_blob_snapshot(LocalFoundation(foundation_root), manifest_ref, entry_ref)
    manifest = view.manifest
    provenance = manifest.provenance
    if (
        manifest.snapshot_id != authority["snapshot_id"]
        or manifest.provenance_hash != authority["provenance_hash"]
        or not isinstance(provenance, Mapping)
        or set(provenance) != {"type", "schema_version", "input_catalog", "member_keys"}
        or provenance["type"] != RAW_SNAPSHOT_PROVENANCE_SCHEMA
        or provenance["schema_version"] != 1
        or not isinstance(provenance["input_catalog"], Mapping)
        or not isinstance(provenance["member_keys"], Mapping)
    ):
        raise ValueError("input snapshot authority does not bind manifest provenance")
    catalog = cast(dict[str, Any], json.loads(canonical_bytes(provenance["input_catalog"])))
    _validate_input_catalog(catalog)
    if catalog["catalog_sha256"] != authority["input_catalog_sha256"]:
        raise ValueError("input snapshot authority does not bind catalog")
    member_keys = provenance["member_keys"]
    expected_mapping = _snapshot_member_mapping(catalog)
    if member_keys != expected_mapping:
        raise ValueError("input snapshot manifest member mapping mismatch")
    actual = {member.member_key for member in manifest.members}
    if actual != set(expected_mapping.values()):
        raise ValueError("input snapshot manifest member cover mismatch")
    for row in cast(list[dict[str, object]], catalog["files"]):
        raw = view.member_bytes(expected_mapping[cast(str, row["path"])])
        if _hash(raw) != row["sha256"] or len(raw) != row["size_bytes"]:
            raise ValueError("input snapshot manifest member mismatch")
    return catalog, view


def prepare_input_snapshot_authority(foundation_root: Path) -> dict[str, object]:
    """Publish exact retained bytes before a timed full preflight begins."""
    catalog = _build_input_catalog(_raw_snapshot_catalog_config())
    _validate_input_catalog(catalog)
    members = tuple(
        RawBlobSnapshotSourceMember(
            _snapshot_member_mapping(catalog)[cast(str, row["path"])],
            _read_regular_source_bytes(DATA.parent / cast(str, row["path"])),
            "0644",
        )
        for row in cast(list[dict[str, object]], catalog["files"])
    )
    publication = publish_raw_blob_snapshot(
        LocalFoundation(foundation_root),
        members=members,
        provenance={
            "type": RAW_SNAPSHOT_PROVENANCE_SCHEMA,
            "schema_version": 1,
            "input_catalog": catalog,
            "member_keys": _snapshot_member_mapping(catalog),
        },
    )
    authority = _input_snapshot_authority(publication, catalog)
    _open_input_snapshot_authority(foundation_root, authority)
    return authority


@contextmanager
def _raw_input_snapshot_context(catalog: Mapping[str, object], view: RawBlobSnapshotView) -> Iterator[None]:
    """Temporarily route retained-source readers through a verified raw snapshot."""
    global _RAW_INPUT_VIEW, _RAW_INPUT_MEMBER_KEYS
    prior_view, prior_member_keys = _RAW_INPUT_VIEW, _RAW_INPUT_MEMBER_KEYS
    _RAW_INPUT_VIEW, _RAW_INPUT_MEMBER_KEYS = view, _snapshot_member_mapping(catalog)
    try:
        yield
    finally:
        _RAW_INPUT_VIEW, _RAW_INPUT_MEMBER_KEYS = prior_view, prior_member_keys


def _fixed_koru_discovery_scope() -> dict[str, object]:
    return {
        "timeline_window_start": UtcInstant(START_MS * 1_000_000).to_canonical_dict(),
        "timeline_window_end_exclusive": UtcInstant(END_MS * 1_000_000).to_canonical_dict(),
    }


def _verify_koru_discovery_snapshot_scope(catalog: Mapping[str, object], view: RawBlobSnapshotView) -> dict[str, object]:
    """Reject any partial or holdout raw snapshot before retained-source replay."""
    allowed = _allowed_koru_discovery_input_member_cover()
    if {member.member_key for member in view.manifest.members} != allowed:
        raise ValueError("raw snapshot does not have the exact KORU discovery member cover")
    with _raw_input_snapshot_context(catalog, view):
        _authority_manifest()
        _retained_manifests()
    return _fixed_koru_discovery_scope()


def _validate_source_projection_max_seconds(max_seconds: int) -> int:
    if type(max_seconds) is not int or not 1 <= max_seconds <= MAX_SOURCE_PROJECTION_SECONDS:
        raise ValueError(
            "source-projection --max-seconds must be an integer from 1 to "
            f"{MAX_SOURCE_PROJECTION_SECONDS}"
        )
    return max_seconds


def _source_projection_attempt_id(value: object) -> str:
    if (
        type(value) is not str
        or not 1 <= len(value) <= 128
        or value[0] not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for character in value)
    ):
        raise ValueError("source-projection publication attempt ID is invalid")
    return value


def _source_projection_paths(root: Path, attempt_id: str) -> dict[str, Path]:
    return {
        "staging": root / ".source-projection-staging" / attempt_id,
        "published": root / "source-projections" / attempt_id,
        "timed_out": root / "source-projection-timed-out" / attempt_id,
        "failed": root / "source-projection-failed" / attempt_id,
        "receipt": root / "source-projection-receipts" / f"{attempt_id}.json",
        "identity": root / "source-projection-identities" / f"{attempt_id}.json",
        "lock": root / ".source-projection-locks" / f"{attempt_id}.lock",
    }


def _prepare_source_projection_publication_root(root: Path) -> Path:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    names = (
        ".source-projection-staging", "source-projections", "source-projection-timed-out",
        "source-projection-failed", "source-projection-receipts", "source-projection-identities",
        ".source-projection-locks",
    )
    for name in names:
        (root / name).mkdir(exist_ok=True)
    device = root.stat().st_dev
    if any((root / name).stat().st_dev != device for name in names[:4]):
        raise ValueError("source-projection publication locations must share a filesystem")
    return root


def _source_projection_identity(
    raw_snapshot_authority: Mapping[str, object], publication_attempt_id: str,
) -> dict[str, object]:
    return {
        "type": SOURCE_PROJECTION_PUBLICATION_IDENTITY_SCHEMA,
        "schema_version": 1,
        "publication_attempt_id": _source_projection_attempt_id(publication_attempt_id),
        "raw_snapshot_authority": _canonical_input_snapshot_authority(raw_snapshot_authority),
        "discovery_scope": _fixed_koru_discovery_scope(),
    }


def _source_projection_log_entry_ref_from_canonical(value: object) -> LogEntryRef:
    if type(value) is not dict or set(value) != {"log_name", "log_sequence", "receipt_hash"}:
        raise ValueError("source-projection publication entry ref is invalid")
    try:
        entry_ref = LogEntryRef(value["log_name"], value["log_sequence"], value["receipt_hash"])
    except (TypeError, ValueError) as error:
        raise ValueError("source-projection publication entry ref is invalid") from error
    if entry_ref.log_name != SOURCE_PROJECTION_LOG:
        raise ValueError("source-projection publication log is invalid")
    return entry_ref


def _source_projection_content_identity(source: Any) -> dict[str, object]:
    return KoruTradifiSourceProjectionContentIdentityV2(
        source.fragment_digest, source.request.request_hash,
    ).to_canonical_dict()


def _assert_exact_koru_source_projection_scope(source: Any) -> None:
    if {
        "timeline_window_start": source.request.timeline_window_start.to_canonical_dict(),
        "timeline_window_end_exclusive": source.request.timeline_window_end_exclusive.to_canonical_dict(),
    } != _fixed_koru_discovery_scope():
        raise ValueError("source projection discovery scope is not the exact KORU discovery interval")


def _source_projection_builder_input_identity(source: Any, raw_snapshot_authority: Mapping[str, object]) -> dict[str, object]:
    authority = _canonical_input_snapshot_authority(raw_snapshot_authority)
    return {
        "type": "koru_source_projection_builder_input_identity_v1",
        "builder_id": "binance_usdm_koru_tradifi_source_projection_v2",
        "input_snapshot_id": authority["snapshot_id"],
        "input_catalog_sha256": authority["input_catalog_sha256"],
        "source_projection_request_hash": source.request.request_hash,
    }


def _source_projection_publication_authority(
    identity: Mapping[str, object], source: Any, source_projection_authority_ref: ArtifactRef,
    publication_entry_ref: LogEntryRef,
) -> dict[str, object]:
    authority = {
        "type": SOURCE_PROJECTION_PUBLICATION_SCHEMA,
        "schema_version": 1,
        "publication_attempt_id": identity["publication_attempt_id"],
        "raw_snapshot_authority": identity["raw_snapshot_authority"],
        "discovery_scope": identity["discovery_scope"],
        "source_projection_authority_ref": source_projection_authority_ref.to_canonical_dict(),
        "source_projection_content_identity": _source_projection_content_identity(source),
        "builder_input_identity": _source_projection_builder_input_identity(
            source, cast(Mapping[str, object], identity["raw_snapshot_authority"]),
        ),
        "publication_entry_ref": {
            "log_name": publication_entry_ref.log_name,
            "log_sequence": publication_entry_ref.log_sequence,
            "receipt_hash": publication_entry_ref.receipt_hash,
        },
    }
    return _canonical_source_projection_publication_authority(authority)


def _canonical_source_projection_publication_authority(value: Mapping[str, object]) -> dict[str, object]:
    required = {
        "type", "schema_version", "publication_attempt_id", "raw_snapshot_authority", "discovery_scope",
        "source_projection_authority_ref", "source_projection_content_identity", "builder_input_identity",
        "publication_entry_ref",
    }
    if (
        type(value) is not dict or set(value) != required
        or value.get("type") != SOURCE_PROJECTION_PUBLICATION_SCHEMA or value.get("schema_version") != 1
    ):
        raise ValueError("source-projection publication authority schema mismatch")
    attempt_id = _source_projection_attempt_id(value["publication_attempt_id"])
    raw_authority = _canonical_input_snapshot_authority(cast(Mapping[str, object], value["raw_snapshot_authority"]))
    projection_ref = _artifact_ref_from_canonical(value["source_projection_authority_ref"])
    entry_ref = _source_projection_log_entry_ref_from_canonical(value["publication_entry_ref"])
    content_identity = value["source_projection_content_identity"]
    builder_input_identity = value["builder_input_identity"]
    if (
        projection_ref.artifact_type != "binance_usdm_koru_tradifi_source_projection_authority_v1"
        or projection_ref.schema_version != 1
        or value["discovery_scope"] != _fixed_koru_discovery_scope()
        or type(content_identity) is not dict
        or set(content_identity) != {"type", "schema_version", "source_fragment_digest", "source_projection_request_hash"}
        or content_identity.get("type") != "koru_tradifi_source_projection_content_identity_v2"
        or content_identity.get("schema_version") != 2
        or any(type(content_identity[key]) is not str for key in ("source_fragment_digest", "source_projection_request_hash"))
        or type(builder_input_identity) is not dict
        or builder_input_identity != {
            "type": "koru_source_projection_builder_input_identity_v1",
            "builder_id": "binance_usdm_koru_tradifi_source_projection_v2",
            "input_snapshot_id": raw_authority["snapshot_id"],
            "input_catalog_sha256": raw_authority["input_catalog_sha256"],
            "source_projection_request_hash": content_identity["source_projection_request_hash"],
        }
    ):
        raise ValueError("source-projection publication authority identity mismatch")
    canonical = {
        "type": SOURCE_PROJECTION_PUBLICATION_SCHEMA,
        "schema_version": 1,
        "publication_attempt_id": attempt_id,
        "raw_snapshot_authority": raw_authority,
        "discovery_scope": _fixed_koru_discovery_scope(),
        "source_projection_authority_ref": projection_ref.to_canonical_dict(),
        "source_projection_content_identity": content_identity,
        "builder_input_identity": builder_input_identity,
        "publication_entry_ref": {
            "log_name": entry_ref.log_name,
            "log_sequence": entry_ref.log_sequence,
            "receipt_hash": entry_ref.receipt_hash,
        },
    }
    if canonical != value:
        raise ValueError("source-projection publication authority is noncanonical")
    return canonical


def _source_projection_publication_fact_values(
    raw_snapshot_authority: Mapping[str, object], discovery_scope: Mapping[str, object],
    source_projection_authority_ref: ArtifactRef, source_projection_content_identity: Mapping[str, object],
    builder_input_identity: Mapping[str, object],
) -> dict[str, object]:
    return {
        "type": SOURCE_PROJECTION_PUBLICATION_FACT_SCHEMA,
        "schema_version": 1,
        "raw_snapshot_authority": _canonical_input_snapshot_authority(raw_snapshot_authority),
        "discovery_scope": dict(discovery_scope),
        "source_projection_authority_ref": source_projection_authority_ref.to_canonical_dict(),
        "source_projection_content_identity": dict(source_projection_content_identity),
        "builder_input_identity": dict(builder_input_identity),
    }


def _source_projection_publication_fact(authority: Mapping[str, object]) -> dict[str, object]:
    authority = _canonical_source_projection_publication_authority(authority)
    return _source_projection_publication_fact_values(
        cast(Mapping[str, object], authority["raw_snapshot_authority"]),
        cast(Mapping[str, object], authority["discovery_scope"]),
        _artifact_ref_from_canonical(authority["source_projection_authority_ref"]),
        cast(Mapping[str, object], authority["source_projection_content_identity"]),
        cast(Mapping[str, object], authority["builder_input_identity"]),
    )


def _source_projection_publication_event_id(fact: Mapping[str, object]) -> str:
    return canonical_sha256(("koru-source-projection-publication-v1", SOURCE_PROJECTION_LOG, fact))


def _source_projection_entry_for_exact_fact(
    foundation: LocalFoundation, authority: Mapping[str, object], entry_ref: LogEntryRef,
) -> None:
    fact = _source_projection_publication_fact(authority)
    try:
        entries = foundation.entries(SOURCE_PROJECTION_LOG, through=entry_ref)
    except Exception as error:
        raise ValueError("source-projection publication entry is unavailable") from error
    if (
        not entries or entries[-1].entry_ref != entry_ref
        or entries[-1].event_id != _source_projection_publication_event_id(fact)
        or entries[-1].payload != canonical_bytes(fact)
    ):
        raise ValueError("source-projection publication entry does not bind authority")


def _checkpoint_from_canonical(value: object) -> LogCheckpoint:
    if type(value) is not dict or set(value) != {"log_name", "as_of", "upper_log_sequence", "head_receipt_hash"}:
        raise ValueError("source-projection owner-log checkpoint is invalid")
    try:
        checkpoint = LogCheckpoint(
            value["log_name"], value["as_of"], value["upper_log_sequence"], value["head_receipt_hash"],
        )
    except (TypeError, ValueError) as error:
        raise ValueError("source-projection owner-log checkpoint is invalid") from error
    if checkpoint.log_name != SOURCE_PROJECTION_LOG:
        raise ValueError("source-projection owner-log checkpoint is invalid")
    return checkpoint


def _checkpoint_canonical(checkpoint: LogCheckpoint) -> dict[str, object]:
    return {
        "log_name": checkpoint.log_name,
        "as_of": checkpoint.as_of,
        "upper_log_sequence": checkpoint.upper_log_sequence,
        "head_receipt_hash": checkpoint.head_receipt_hash,
    }


def _source_projection_envelope_from_bytes(source: bytes) -> ArtifactEnvelope:
    try:
        body = json.loads(source.decode("utf-8"))
        envelope = ArtifactEnvelope(
            body["artifact_type"], body["schema_version"], body["payload"], body["content_hash"],
        )
    except (KeyError, TypeError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("source-projection authority envelope is invalid") from error
    if (
        type(body) is not dict
        or set(body) != {"artifact_type", "schema_version", "payload", "content_hash"}
        or canonical_bytes(envelope) != source
    ):
        raise ValueError("source-projection authority envelope is noncanonical")
    return envelope


def _verify_koru_source_projection_authority_in_foundation(
    foundation: LocalFoundation, authority: Mapping[str, object], checkpoint: Mapping[str, object] | None = None,
) -> Any:
    authority = _canonical_source_projection_publication_authority(authority)
    ref = _artifact_ref_from_canonical(authority["source_projection_authority_ref"])
    try:
        readback = foundation.read(ref=ref)
    except Exception as error:
        raise ValueError("source-projection authority artifact is unavailable") from error
    envelope = _source_projection_envelope_from_bytes(readback.source_bytes)
    if envelope != readback.envelope or ArtifactRef.from_envelope(envelope) != ref:
        raise ValueError("source-projection authority artifact readback mismatch")
    source = open_binance_usdm_koru_tradifi_source_projection_authority_v1(readback.source_bytes)
    _assert_exact_koru_source_projection_scope(source)
    if _source_projection_content_identity(source) != authority["source_projection_content_identity"]:
        raise ValueError("source-projection authority content identity mismatch")
    if _source_projection_builder_input_identity(
        source, cast(Mapping[str, object], authority["raw_snapshot_authority"]),
    ) != authority["builder_input_identity"]:
        raise ValueError("source-projection authority builder input identity mismatch")
    _source_projection_entry_for_exact_fact(
        foundation, authority, _source_projection_log_entry_ref_from_canonical(authority["publication_entry_ref"]),
    )
    if checkpoint is not None:
        parsed = _checkpoint_from_canonical(checkpoint)
        entries = foundation.entries(SOURCE_PROJECTION_LOG, through=parsed)
        if not entries or entries[-1].entry_ref != _source_projection_log_entry_ref_from_canonical(authority["publication_entry_ref"]):
            raise ValueError("source-projection owner-log checkpoint does not bind authority")
    return source


def _atomic_write(path: Path, value: Mapping[str, object]) -> None:
    raw = _canonical_pretty_json(dict(value))
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    _fsync_directory(path.parent)


def _create_new_json(path: Path, value: Mapping[str, object]) -> None:
    raw = _canonical_pretty_json(dict(value))
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise
    _fsync_directory(path.parent)


def _load_canonical(path: Path, label: str) -> dict[str, Any]:
    raw = path.read_bytes()
    value = _load(path)
    if raw != _canonical_pretty_json(value):
        raise ValueError(f"{label} is noncanonical")
    return value


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _attempt_preimage(
    config: Mapping[str, object], catalog_sha256: str, retry_ordinal: int, parent_attempt_id: str | None,
) -> dict[str, object]:
    if type(retry_ordinal) is not int or retry_ordinal < 0:
        raise ValueError("retry ordinal must be a non-negative integer")
    if parent_attempt_id is not None and (type(parent_attempt_id) is not str or not parent_attempt_id):
        raise ValueError("parent attempt ID must be a non-empty string when supplied")
    authority = _canonical_input_snapshot_authority(cast(Mapping[str, object], config["input_snapshot_authority"]))
    if authority["input_catalog_sha256"] != catalog_sha256:
        raise ValueError("input snapshot authority catalog identity mismatch")
    return {
        "type": ATTEMPT_SCHEMA,
        "schema_version": 1,
        "full_mode_config": dict(config),
        "input_snapshot_authority": authority,
        "frozen_input_catalog_sha256": catalog_sha256,
        "retry_ordinal": retry_ordinal,
        "parent_attempt_id": parent_attempt_id,
    }


def _attempt_id(preimage: Mapping[str, object]) -> str:
    body = dict(preimage)
    body.pop("attempt_id", None)
    return ATTEMPT_SCHEMA + ":" + hashlib.sha256(_canonical_json(body)).hexdigest()


def _attempt_identity(preimage: Mapping[str, object]) -> dict[str, object]:
    identity = dict(preimage)
    identity["attempt_id"] = _attempt_id(preimage)
    return identity


def _attempt_paths(root: Path, attempt_id: str) -> dict[str, Path]:
    return {
        "staging": root / ".staging" / attempt_id,
        "published": root / "attempts" / attempt_id,
        "timed_out": root / "timed-out" / attempt_id,
        "receipt": root / "receipts" / f"{attempt_id}.json",
        "identity": root / "attempt-identities" / f"{attempt_id}.json",
        "lock": root / ".attempt-locks" / f"{attempt_id}.lock",
    }


def _prepare_attempt_root(root: Path) -> Path:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    for name in (".staging", "attempts", "timed-out", "receipts", "attempt-identities", ".attempt-locks"):
        (root / name).mkdir(exist_ok=True)
    device = root.stat().st_dev
    if any((root / name).stat().st_dev != device for name in (".staging", "attempts", "timed-out")):
        raise ValueError("attempt locations must share a filesystem")
    return root


@contextmanager
def _attempt_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(exist_ok=True)
    with path.open("a+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _reserve_attempt(root: Path, identity: Mapping[str, object]) -> None:
    attempt_id = identity["attempt_id"]
    if type(attempt_id) is not str or attempt_id != _attempt_id(identity):
        raise ValueError("attempt identity is invalid")
    _create_new_json(_attempt_paths(root, attempt_id)["identity"], identity)


def _load_attempt_identity(root: Path, attempt_id: str) -> dict[str, Any]:
    identity = _load_canonical(_attempt_paths(root, attempt_id)["identity"], "attempt identity")
    if (
        identity.get("attempt_id") != attempt_id
        or attempt_id != _attempt_id(identity)
        or identity.get("input_snapshot_authority") != identity.get("full_mode_config", {}).get("input_snapshot_authority")
    ):
        raise ValueError("attempt identity conflict")
    _canonical_input_snapshot_authority(cast(Mapping[str, object], identity["input_snapshot_authority"]))
    return identity


def _elapsed_timings(value: Mapping[str, object], *, complete: bool) -> dict[str, int]:
    expected = TIMING_KEYS if complete else TIMING_KEYS[:-1]
    if set(value) != set(expected):
        raise ValueError("attempt timing schema mismatch")
    timings: dict[str, int] = {}
    for key in expected:
        elapsed = value[key]
        if type(elapsed) is not int or elapsed < 0:
            raise ValueError("attempt timing schema mismatch")
        timings[key] = elapsed
    return timings


def _child_full_preflight(
    staging: Path, attempt_id: str, input_snapshot_authority: Mapping[str, object],
    raw_snapshot_foundation_root: Path, parent_timings: Mapping[str, object],
) -> None:
    global _RAW_INPUT_VIEW, _RAW_INPUT_MEMBER_KEYS
    timings = _elapsed_timings(parent_timings, complete=False)
    child_started_at = time.monotonic_ns()
    catalog, _RAW_INPUT_VIEW = _open_input_snapshot_authority(raw_snapshot_foundation_root, input_snapshot_authority)
    _RAW_INPUT_MEMBER_KEYS = _snapshot_member_mapping(catalog)
    try:
        smoke(staging / "foundation")
        source = build_source()
    finally:
        _RAW_INPUT_VIEW = None
        _RAW_INPUT_MEMBER_KEYS = None
    foundation = LocalFoundation(staging / "foundation")
    store = KoruEconomicsArtifactStoreV1(foundation)
    _append_owner_record(foundation, _source_projection_record(source))
    market = staging / "market"
    economics = _unwrap(publish_koru_tradifi_economics_bundle_v3(
        KoruTradifiEconomicsBundleRequestV3(
            source, KoruTradifiSourceProjectionContentIdentityV2(source.fragment_digest, source.request.request_hash),
            KoruTradifiEconomicsTermsV3.from_source_projection(source, execution_account_id="account-1"), store, market / "economics",
        )
    ), "target-free economics bundle")
    readers = _unwrap(build_koru_premium_reader_set_v1(
        KoruPremiumReaderSetBuildRequestV1(economics, _premium_authorities(source, store), market / "premium-readers")
    ), "premium reader set")
    for record in _owner_publication_records(source, readers):
        _append_owner_record(foundation, record)
    _append_owner_record(foundation, _reader_set_record(source, economics, readers))
    expected_records = _expected_owner_records(source, economics, readers, store.publication_records)
    owner_log = _checkpoint_summary(foundation, expected_records)
    result: dict[str, object] = {
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
        "owner_log": owner_log,
        "stopped_before": "Experiment_Holdout_and_Backtest",
    }
    reader_set = _reader_set_record(source, economics, readers)
    _atomic_write(staging / COMPLETE_MARKER, {
        "type": "koru_retained_preflight_complete_v1",
        "schema_version": 1,
        "attempt_id": attempt_id,
        "input_catalog_sha256": catalog["catalog_sha256"],
        "input_snapshot_authority": _canonical_input_snapshot_authority(input_snapshot_authority),
        "expected_owner_records": list(expected_records),
        "owner_log": owner_log,
        "reader_set": {
            "reader_set_digest": reader_set["reader_set_digest"],
            "premium_reader_ids": result["premium_reader_ids"],
        },
        "timings": {**timings, "child_elapsed_ns": time.monotonic_ns() - child_started_at},
        "result": result,
    })


def _same_owner_log_cover(left: Mapping[str, object], right: Mapping[str, object]) -> bool:
    left_checkpoint, right_checkpoint = left.get("checkpoint"), right.get("checkpoint")
    if type(left_checkpoint) is not dict or type(right_checkpoint) is not dict:
        return False
    stable = ("log_name", "upper_log_sequence", "head_receipt_hash")
    return (
        all(left_checkpoint.get(key) == right_checkpoint.get(key) for key in stable)
        and left.get("entries") == right.get("entries")
        and left.get("publication_records") == right.get("publication_records")
    )


def _validate_completed_attempt(
    staging: Path, identity: Mapping[str, object], expected_parent_timings: Mapping[str, object] | None = None,
) -> dict[str, object]:
    marker = _load_canonical(staging / COMPLETE_MARKER, "child complete marker")
    required = {
        "type", "schema_version", "attempt_id", "input_catalog_sha256", "input_snapshot_authority",
        "expected_owner_records", "owner_log", "reader_set", "timings", "result",
    }
    if (
        set(marker) != required
        or marker["type"] != "koru_retained_preflight_complete_v1"
        or marker["schema_version"] != 1
        or marker["attempt_id"] != identity["attempt_id"]
        or marker["input_catalog_sha256"] != identity["frozen_input_catalog_sha256"]
        or marker["input_snapshot_authority"] != identity["input_snapshot_authority"]
        or type(marker["expected_owner_records"]) is not list
        or not all(type(record) is dict for record in marker["expected_owner_records"])
        or type(marker["result"]) is not dict
        or type(marker["reader_set"]) is not dict
        or type(marker["timings"]) is not dict
    ):
        raise ValueError("child complete marker identity mismatch")
    expected = tuple(marker["expected_owner_records"])
    types = [record.get("type") for record in expected]
    if (
        types.count("koru_source_projection_publication_v1") != 1
        or types.count("koru_compiler_result_publication_v1") != 1
        or types.count("koru_prm_overlay_publication_v1") != 4
        or types.count("koru_premium_reader_set_publication_v1") != 1
        or types.count("koru_artifact_publication_v1") < 1
    ):
        raise ValueError("child owner-log record cover is incomplete")
    owner_log = _checkpoint_summary(LocalFoundation(staging / "foundation"), expected)
    if (
        not _same_owner_log_cover(marker["owner_log"], owner_log)
        or marker["result"].get("owner_log") != marker["owner_log"]
    ):
        raise ValueError("child owner-log checkpoint mismatch")
    result = marker["result"]
    reader_set = marker["reader_set"]
    if (
        result.get("mode") != "full"
        or result.get("network_performed") is not False
        or result.get("holdout_touched") is not False
        or result.get("stopped_before") != "Experiment_Holdout_and_Backtest"
        or reader_set.get("premium_reader_ids") != result.get("premium_reader_ids")
        or type(reader_set.get("reader_set_digest")) is not str
    ):
        raise ValueError("child complete result mismatch")
    timings = _elapsed_timings(marker["timings"], complete=True)
    if expected_parent_timings is not None and {
        key: timings[key] for key in TIMING_KEYS[:-1]
    } != _elapsed_timings(expected_parent_timings, complete=False):
        raise ValueError("child complete timing mismatch")
    return {
        "owner_log_checkpoint": owner_log["checkpoint"],
        "reader_set": reader_set,
        "timings": timings,
        "result": result,
    }


def _child_source_projection_timeout_test() -> None:
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    time.sleep(60)


def _child_timeout_test(staging: Path) -> None:
    """Build bounded forensic state for the parent timeout integration test."""
    foundation = LocalFoundation(staging / "foundation")
    envelope = ArtifactEnvelope.create("strategy_definition", 1, {"strategy_id": "timeout-integration"})
    ref = foundation.put(envelope=envelope)
    record = _artifact_publication_record(envelope, ref)
    _append_owner_record(foundation, record)
    _atomic_write(staging / "timeout-test-ready.json", {
        "type": "koru_retained_preflight_timeout_test_v1",
        "artifact_ref": json.loads(canonical_bytes(ref)),
        "envelope": json.loads(canonical_bytes(envelope)),
        "owner_record": json.loads(canonical_bytes(record)),
    })
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    time.sleep(60)


def _child_command(
    staging: Path, attempt_id: str, input_snapshot_authority: Mapping[str, object], raw_snapshot_foundation_root: Path,
) -> list[str]:
    return [
        sys.executable, str(Path(__file__).resolve()), "--_child", "--staging", str(staging),
        "--attempt-id", attempt_id,
        "--input-snapshot-authority", _canonical_json(_canonical_input_snapshot_authority(input_snapshot_authority)).decode(),
        "--raw-snapshot-foundation-root", str(raw_snapshot_foundation_root),
    ]


def _reap_process_group(process: subprocess.Popen[bytes]) -> int | None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    until = time.monotonic() + TERMINATE_GRACE_SECONDS
    while time.monotonic() < until:
        if process.poll() is not None:
            break
        time.sleep(0.01)
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    return process.wait()


def _wait_for_child(
    process: subprocess.Popen[bytes], max_seconds: int, started_at: float,
) -> tuple[bool, int | None]:
    deadline = started_at + max_seconds
    while True:
        status = process.poll()
        if status is not None:
            if time.monotonic() >= deadline:
                return True, _reap_process_group(process)
            return False, status
        if time.monotonic() >= deadline:
            return True, _reap_process_group(process)
        time.sleep(0.01)


def _timeout_state(
    identity: Mapping[str, object], child_status: int | None, timings: Mapping[str, object],
) -> dict[str, object]:
    return {
        "type": "koru_retained_preflight_timeout_v1",
        "schema_version": 1,
        "attempt_id": identity["attempt_id"],
        "input_catalog_sha256": identity["frozen_input_catalog_sha256"],
        "input_snapshot_authority": identity["input_snapshot_authority"],
        "child_status": {"exit_code": child_status, "timed_out": True},
        "archive_state": "archived",
        "cleanup_state": "process_group_reaped",
        "timings": _elapsed_timings(timings, complete=True),
    }


def _validate_timeout_state(state: Mapping[str, object], identity: Mapping[str, object]) -> dict[str, int]:
    required = {
        "type", "schema_version", "attempt_id", "input_catalog_sha256", "input_snapshot_authority",
        "child_status", "archive_state", "cleanup_state", "timings",
    }
    child_status = state.get("child_status")
    timings = state.get("timings")
    if (
        set(state) != required
        or state.get("type") != "koru_retained_preflight_timeout_v1"
        or state.get("schema_version") != 1
        or state.get("attempt_id") != identity.get("attempt_id")
        or state.get("input_catalog_sha256") != identity.get("frozen_input_catalog_sha256")
        or state.get("input_snapshot_authority") != identity.get("input_snapshot_authority")
        or type(child_status) is not dict
        or child_status.get("timed_out") is not True
        or state.get("archive_state") != "archived"
        or state.get("cleanup_state") != "process_group_reaped"
        or type(timings) is not dict
    ):
        raise ValueError("timeout state conflict")
    return _elapsed_timings(timings, complete=True)


def _timeout_receipt(identity: Mapping[str, object], state: Mapping[str, object]) -> dict[str, object]:
    timings = _validate_timeout_state(state, identity)
    return {
        "type": RECEIPT_SCHEMA,
        "schema_version": 1,
        "outcome": "timeout",
        "attempt_id": identity["attempt_id"],
        "attempt_identity": dict(identity),
        "input_catalog_sha256": identity["frozen_input_catalog_sha256"],
        "input_snapshot_authority": identity["input_snapshot_authority"],
        "final_authority": [],
        "child_status": state["child_status"],
        "archive_state": state["archive_state"],
        "cleanup_state": state["cleanup_state"],
        "timings": timings,
    }


def _archive_timeout(
    root: Path, attempt_id: str, child_status: int | None, timings: Mapping[str, object],
) -> Path:
    paths = _attempt_paths(root, attempt_id)
    if paths["timed_out"].exists():
        raise ValueError("timed-out attempt archive already exists")
    identity = _load_attempt_identity(root, attempt_id)
    state = _timeout_state(identity, child_status, timings)
    _atomic_write(paths["staging"] / TIMEOUT_MARKER, state)
    os.rename(paths["staging"], paths["timed_out"])
    _fsync_directory(paths["timed_out"].parent)
    _create_new_json(paths["receipt"], _timeout_receipt(identity, state))
    return paths["receipt"]


def _promote_attempt_container(root: Path, attempt_id: str) -> Path:
    paths = _attempt_paths(root, attempt_id)
    if paths["published"].exists():
        raise ValueError("published attempt container already exists")
    os.rename(paths["staging"], paths["published"])
    _fsync_directory(paths["published"].parent)
    return paths["published"]


def _success_receipt(root: Path, identity: Mapping[str, object], validated: Mapping[str, object]) -> dict[str, object]:
    attempt_id = identity["attempt_id"]
    assert type(attempt_id) is str
    return {
        "type": RECEIPT_SCHEMA,
        "schema_version": 1,
        "outcome": "success",
        "attempt_id": attempt_id,
        "attempt_identity": dict(identity),
        "input_catalog_sha256": identity["frozen_input_catalog_sha256"],
        "input_snapshot_authority": identity["input_snapshot_authority"],
        "timings": validated["timings"],
        "final_authority": [{
            "attempt_container": f"attempts/{attempt_id}",
            "owner_log_checkpoint": validated["owner_log_checkpoint"],
            "reader_set": validated["reader_set"],
        }],
    }


def _validate_receipt(receipt: Mapping[str, object], identity: Mapping[str, object]) -> None:
    common = {
        "type", "schema_version", "outcome", "attempt_id", "attempt_identity",
        "input_catalog_sha256", "input_snapshot_authority", "final_authority",
    }
    if (
        not common <= set(receipt)
        or receipt.get("type") != RECEIPT_SCHEMA
        or receipt.get("schema_version") != 1
        or receipt.get("attempt_id") != identity.get("attempt_id")
        or receipt.get("attempt_identity") != identity
        or receipt.get("input_catalog_sha256") != identity.get("frozen_input_catalog_sha256")
        or receipt.get("input_snapshot_authority") != identity.get("input_snapshot_authority")
        or type(receipt.get("final_authority")) is not list
    ):
        raise ValueError("receipt identity conflict")
    timings = receipt.get("timings")
    if receipt["outcome"] == "timeout":
        if (
            set(receipt) != common | {"child_status", "archive_state", "cleanup_state", "timings"}
            or receipt["final_authority"] != []
            or receipt.get("archive_state") != "archived"
            or receipt.get("cleanup_state") != "process_group_reaped"
            or type(timings) is not dict
        ):
            raise ValueError("timeout receipt conflict")
        _elapsed_timings(timings, complete=True)
    elif receipt["outcome"] == "success":
        authority = receipt["final_authority"]
        if (
            set(receipt) != common | {"timings"}
            or type(authority) is not list
            or len(authority) != 1
            or type(timings) is not dict
        ):
            raise ValueError("success receipt conflict")
        _elapsed_timings(timings, complete=True)
    else:
        raise ValueError("receipt outcome conflict")


def _load_receipt(root: Path, attempt_id: str) -> dict[str, Any] | None:
    path = _attempt_paths(root, attempt_id)["receipt"]
    if not path.exists():
        return None
    identity = _load_attempt_identity(root, attempt_id)
    receipt = _load_canonical(path, "attempt receipt")
    _validate_receipt(receipt, identity)
    if receipt["outcome"] == "timeout":
        state = _load_canonical(_attempt_paths(root, attempt_id)["timed_out"] / TIMEOUT_MARKER, "timeout state")
        if receipt != _timeout_receipt(identity, state):
            raise ValueError("timeout receipt does not bind archived state")
    return receipt


def recover_attempt(root: Path, attempt_id: str) -> dict[str, object]:
    """Emit the one missing success receipt only after full promoted-container validation."""
    root = _prepare_attempt_root(root)
    paths = _attempt_paths(root, attempt_id)
    with _attempt_lock(paths["lock"]):
        identity = _load_attempt_identity(root, attempt_id)
        receipt = _load_receipt(root, attempt_id)
        if receipt is not None:
            if paths["published"].exists():
                if receipt["outcome"] != "success":
                    raise ValueError("promoted attempt conflicts with non-success receipt")
                validated = _validate_completed_attempt(paths["published"], identity)
                if not _success_receipt_binds_validated(receipt, root, identity, validated):
                    raise ValueError("success receipt does not bind promoted authority")
            return receipt
        if not paths["published"].is_dir():
            raise ValueError("attempt has no receipt and no promoted container")
        validated = _validate_completed_attempt(paths["published"], identity)
        receipt = _success_receipt(root, identity, validated)
        _create_new_json(paths["receipt"], receipt)
        return receipt


def _recover_pending_attempts(root: Path) -> None:
    for container in sorted((root / "attempts").iterdir()):
        if not container.is_dir():
            raise ValueError("published attempt path is not a container")
        if not _attempt_paths(root, container.name)["receipt"].exists():
            recover_attempt(root, container.name)


def _success_receipt_binds_validated(
    receipt: Mapping[str, object], root: Path, identity: Mapping[str, object], validated: Mapping[str, object],
) -> bool:
    expected = _success_receipt(root, identity, validated)
    if {key: value for key, value in receipt.items() if key != "final_authority"} != {
        key: value for key, value in expected.items() if key != "final_authority"
    }:
        return False
    actual_authority = receipt["final_authority"]
    expected_authority = cast(list[dict[str, object]], expected["final_authority"])
    if type(actual_authority) is not list or len(actual_authority) != 1 or type(actual_authority[0]) is not dict:
        return False
    actual, expected_value = actual_authority[0], expected_authority[0]
    if actual.get("attempt_container") != expected_value["attempt_container"] or actual.get("reader_set") != expected_value["reader_set"]:
        return False
    actual_checkpoint, expected_checkpoint = actual.get("owner_log_checkpoint"), expected_value.get("owner_log_checkpoint")
    return type(actual_checkpoint) is dict and type(expected_checkpoint) is dict and all(
        actual_checkpoint.get(key) == expected_checkpoint.get(key)
        for key in ("log_name", "upper_log_sequence", "head_receipt_hash")
    )


def read_success_receipt(root: Path, attempt_id: str) -> dict[str, object]:
    """The only consumer entrypoint; staging and timeout attempts are never authority."""
    root = _prepare_attempt_root(root)
    receipt = _load_receipt(root, attempt_id)
    if receipt is None or receipt["outcome"] != "success":
        raise ValueError("attempt has no consumable success receipt")
    identity = _load_attempt_identity(root, attempt_id)
    validated = _validate_completed_attempt(_attempt_paths(root, attempt_id)["published"], identity)
    if not _success_receipt_binds_validated(receipt, root, identity, validated):
        raise ValueError("success receipt does not bind promoted authority")
    return receipt


def _source_projection_initial_progress(identity: Mapping[str, object]) -> dict[str, object]:
    return {
        "type": SOURCE_PROJECTION_PROGRESS_SCHEMA,
        "schema_version": 1,
        "snapshot_authority_identity": _canonical_input_snapshot_authority(
            cast(Mapping[str, object], identity["raw_snapshot_authority"])
        ),
        "current_phase": SOURCE_PROJECTION_PHASES[0],
        "completed_phases": [],
        "phase_elapsed_ns": {},
        "completed_elapsed_ns": {},
        "input_counts": {},
    }


def _canonical_source_projection_progress(
    value: Mapping[str, object], identity: Mapping[str, object],
) -> dict[str, object]:
    required = {
        "type", "schema_version", "snapshot_authority_identity", "current_phase", "completed_phases",
        "phase_elapsed_ns", "completed_elapsed_ns", "input_counts",
    }
    if type(value) is not dict or set(value) != required or value.get("type") != SOURCE_PROJECTION_PROGRESS_SCHEMA or value.get("schema_version") != 1:
        raise ValueError("source-projection progress schema mismatch")
    snapshot_authority = _canonical_input_snapshot_authority(
        cast(Mapping[str, object], value["snapshot_authority_identity"])
    )
    if snapshot_authority != identity["raw_snapshot_authority"]:
        raise ValueError("source-projection progress snapshot authority mismatch")
    completed = value["completed_phases"]
    phase_elapsed = value["phase_elapsed_ns"]
    completed_elapsed = value["completed_elapsed_ns"]
    counts = value["input_counts"]
    if type(completed) is not list or type(phase_elapsed) is not dict or type(completed_elapsed) is not dict or type(counts) is not dict:
        raise ValueError("source-projection progress values mismatch")
    if completed != list(SOURCE_PROJECTION_PHASES[:len(completed)]):
        raise ValueError("source-projection progress phases are not monotonic")
    expected_current = "complete" if len(completed) == len(SOURCE_PROJECTION_PHASES) else SOURCE_PROJECTION_PHASES[len(completed)]
    if value["current_phase"] != expected_current or set(phase_elapsed) != set(completed) or set(completed_elapsed) != set(completed):
        raise ValueError("source-projection progress phase state mismatch")
    prior_elapsed = -1
    for phase in completed:
        phase_ns, total_ns = phase_elapsed[phase], completed_elapsed[phase]
        if type(phase_ns) is not int or phase_ns < 0 or type(total_ns) is not int or total_ns < prior_elapsed:
            raise ValueError("source-projection progress timings are not monotonic")
        prior_elapsed = total_ns
    if any(type(key) is not str or type(count) is not int or count < 0 for key, count in counts.items()):
        raise ValueError("source-projection progress input counts mismatch")
    return {
        "type": SOURCE_PROJECTION_PROGRESS_SCHEMA,
        "schema_version": 1,
        "snapshot_authority_identity": snapshot_authority,
        "current_phase": expected_current,
        "completed_phases": list(completed),
        "phase_elapsed_ns": dict(phase_elapsed),
        "completed_elapsed_ns": dict(completed_elapsed),
        "input_counts": dict(counts),
    }


def _source_projection_progress_recorder(
    staging: Path, identity: Mapping[str, object],
) -> Callable[[str, Mapping[str, int]], None]:
    path = staging / SOURCE_PROJECTION_PROGRESS
    progress = _source_projection_initial_progress(identity)
    _atomic_write(path, progress)
    started_at = time.monotonic_ns()
    phase_started_at = started_at

    def completed(phase: str, counts: Mapping[str, int]) -> None:
        nonlocal phase_started_at
        expected = cast(str, progress["current_phase"])
        if phase != expected:
            raise ValueError("source-projection diagnostic phase order mismatch")
        now = time.monotonic_ns()
        progress["completed_phases"] = [*cast(list[str], progress["completed_phases"]), phase]
        cast(dict[str, int], progress["phase_elapsed_ns"])[phase] = now - phase_started_at
        cast(dict[str, int], progress["completed_elapsed_ns"])[phase] = now - started_at
        cast(dict[str, int], progress["input_counts"]).update(counts)
        completed_count = len(cast(list[str], progress["completed_phases"]))
        progress["current_phase"] = (
            "complete" if completed_count == len(SOURCE_PROJECTION_PHASES) else SOURCE_PROJECTION_PHASES[completed_count]
        )
        _atomic_write(path, _canonical_source_projection_progress(progress, identity))
        phase_started_at = now

    return completed


def _load_source_projection_progress(staging: Path, identity: Mapping[str, object]) -> dict[str, object]:
    return _canonical_source_projection_progress(
        _load_canonical(staging / SOURCE_PROJECTION_PROGRESS, "source-projection progress"), identity,
    )


def _source_projection_complete_marker(
    identity: Mapping[str, object], authority: Mapping[str, object], checkpoint: LogCheckpoint,
) -> dict[str, object]:
    return {
        "type": "koru_source_projection_publication_complete_v1",
        "schema_version": 1,
        "identity": dict(identity),
        "source_projection_authority": _canonical_source_projection_publication_authority(authority),
        "owner_log_checkpoint": _checkpoint_canonical(checkpoint),
    }


def _publish_source_projection_in_staging(
    staging: Path, identity: Mapping[str, object], raw_snapshot_foundation_root: Path,
) -> None:
    progress = _source_projection_progress_recorder(staging, identity)
    raw_authority = _canonical_input_snapshot_authority(
        cast(Mapping[str, object], identity["raw_snapshot_authority"])
    )
    catalog, view = _open_input_snapshot_authority(raw_snapshot_foundation_root, raw_authority)
    if _verify_koru_discovery_snapshot_scope(catalog, view) != identity["discovery_scope"]:
        raise ValueError("raw snapshot discovery scope does not match source publication identity")
    progress("raw_snapshot_open_verification", {
        "raw_snapshot_member_count": len(cast(list[object], catalog["files"])),
        "raw_snapshot_input_byte_count": sum(cast(int, row["size_bytes"]) for row in cast(list[dict[str, object]], catalog["files"])),
    })
    with _raw_input_snapshot_context(catalog, view):
        source = build_source(phase_completed=progress)
    _assert_exact_koru_source_projection_scope(source)
    serialized = serialize_binance_usdm_koru_tradifi_source_projection_authority_v1(source)
    envelope = _source_projection_envelope_from_bytes(serialized)
    progress("authority_serialization", {"authority_serialized_byte_count": len(serialized)})
    foundation = LocalFoundation(staging / "foundation")
    projection_ref = foundation.put(envelope=envelope)
    if projection_ref != ArtifactRef.from_envelope(envelope):
        raise ValueError("Foundation returned an unexpected source-projection authority ref")
    readback = foundation.read(ref=projection_ref)
    if readback.envelope != envelope or readback.source_bytes != serialized:
        raise ValueError("Foundation source-projection authority readback mismatch")
    rebuilt = open_binance_usdm_koru_tradifi_source_projection_authority_v1(readback.source_bytes)
    _assert_exact_koru_source_projection_scope(rebuilt)
    if _source_projection_content_identity(rebuilt) != _source_projection_content_identity(source):
        raise ValueError("source-projection authority serialization identity mismatch")
    content_identity = _source_projection_content_identity(rebuilt)
    builder_input_identity = _source_projection_builder_input_identity(rebuilt, raw_authority)
    fact = _source_projection_publication_fact_values(
        raw_authority, cast(Mapping[str, object], identity["discovery_scope"]), projection_ref,
        content_identity, builder_input_identity,
    )
    receipt = foundation.append(
        SOURCE_PROJECTION_LOG, _source_projection_publication_event_id(fact), canonical_bytes(fact),
    )
    entry_ref = receipt.entry_ref
    authority = _source_projection_publication_authority(identity, rebuilt, projection_ref, entry_ref)
    _source_projection_entry_for_exact_fact(foundation, authority, entry_ref)
    checkpoint = foundation.checkpoint(SOURCE_PROJECTION_LOG)
    _verify_koru_source_projection_authority_in_foundation(
        foundation, authority, _checkpoint_canonical(checkpoint),
    )
    progress("owner_log_publication", {"owner_log_event_count": 1})
    _atomic_write(staging / COMPLETE_MARKER, _source_projection_complete_marker(identity, authority, checkpoint))


def _validate_source_projection_complete(
    staging: Path, identity: Mapping[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    marker = _load_canonical(staging / COMPLETE_MARKER, "source-projection complete marker")
    required = {"type", "schema_version", "identity", "source_projection_authority", "owner_log_checkpoint"}
    if (
        set(marker) != required
        or marker["type"] != "koru_source_projection_publication_complete_v1"
        or marker["schema_version"] != 1
        or marker["identity"] != identity
        or type(marker["source_projection_authority"]) is not dict
        or type(marker["owner_log_checkpoint"]) is not dict
    ):
        raise ValueError("source-projection complete marker identity mismatch")
    authority = _canonical_source_projection_publication_authority(marker["source_projection_authority"])
    if authority["publication_attempt_id"] != identity["publication_attempt_id"]:
        raise ValueError("source-projection complete marker attempt mismatch")
    _verify_koru_source_projection_authority_in_foundation(
        LocalFoundation(staging / "foundation"), authority, marker["owner_log_checkpoint"],
    )
    return authority, cast(dict[str, object], marker["owner_log_checkpoint"])


def _source_projection_success_receipt(
    identity: Mapping[str, object], authority: Mapping[str, object], checkpoint: Mapping[str, object],
) -> dict[str, object]:
    return {
        "type": SOURCE_PROJECTION_PUBLICATION_RECEIPT_SCHEMA,
        "schema_version": 1,
        "outcome": "success",
        "identity": dict(identity),
        "source_projection_authority": _canonical_source_projection_publication_authority(authority),
        "owner_log_checkpoint": dict(checkpoint),
        "final_authority": [{
            "publication_container": f"source-projections/{identity['publication_attempt_id']}",
            "source_projection_authority": _canonical_source_projection_publication_authority(authority),
            "owner_log_checkpoint": dict(checkpoint),
        }],
    }


def _source_projection_non_success_receipt(
    identity: Mapping[str, object], outcome: str, child_status: int | None, archive_state: str,
    progress: Mapping[str, object],
) -> dict[str, object]:
    if outcome not in {"timeout", "non_success"}:
        raise ValueError("source-projection non-success outcome is invalid")
    return {
        "type": SOURCE_PROJECTION_PUBLICATION_RECEIPT_SCHEMA,
        "schema_version": 1,
        "outcome": outcome,
        "identity": dict(identity),
        "final_authority": [],
        "diagnostic_progress": _canonical_source_projection_progress(progress, identity),
        "child_status": {"exit_code": child_status, "timed_out": outcome == "timeout"},
        "archive_state": archive_state,
    }


def _validate_source_projection_receipt(receipt: Mapping[str, object], identity: Mapping[str, object]) -> None:
    common = {"type", "schema_version", "outcome", "identity", "final_authority"}
    if (
        not common <= set(receipt)
        or receipt.get("type") != SOURCE_PROJECTION_PUBLICATION_RECEIPT_SCHEMA
        or receipt.get("schema_version") != 1
        or receipt.get("identity") != identity
        or type(receipt.get("final_authority")) is not list
    ):
        raise ValueError("source-projection receipt identity mismatch")
    if receipt["outcome"] == "success":
        if (
            set(receipt) != common | {"source_projection_authority", "owner_log_checkpoint"}
            or len(cast(list[object], receipt["final_authority"])) != 1
            or type(receipt.get("source_projection_authority")) is not dict
            or type(receipt.get("owner_log_checkpoint")) is not dict
        ):
            raise ValueError("source-projection success receipt mismatch")
        authority = _canonical_source_projection_publication_authority(
            cast(Mapping[str, object], receipt["source_projection_authority"])
        )
        final = cast(list[dict[str, object]], receipt["final_authority"])[0]
        if (
            type(final) is not dict
            or final != {
                "publication_container": f"source-projections/{identity['publication_attempt_id']}",
                "source_projection_authority": authority,
                "owner_log_checkpoint": receipt["owner_log_checkpoint"],
            }
        ):
            raise ValueError("source-projection success authority mismatch")
        _checkpoint_from_canonical(receipt["owner_log_checkpoint"])
    elif receipt["outcome"] in {"timeout", "non_success"}:
        child_status = receipt.get("child_status")
        if (
            set(receipt) != common | {"diagnostic_progress", "child_status", "archive_state"}
            or receipt["final_authority"] != []
            or type(receipt.get("diagnostic_progress")) is not dict
            or type(child_status) is not dict
            or set(child_status) != {"exit_code", "timed_out"}
            or type(child_status["exit_code"]) not in {int, type(None)}
            or child_status["timed_out"] is not (receipt["outcome"] == "timeout")
            or receipt["archive_state"] != ("timed_out" if receipt["outcome"] == "timeout" else "failed")
        ):
            raise ValueError("source-projection non-success receipt mismatch")
        _canonical_source_projection_progress(cast(Mapping[str, object], receipt["diagnostic_progress"]), identity)
    else:
        raise ValueError("source-projection receipt outcome mismatch")


def _load_source_projection_receipt(root: Path, attempt_id: str) -> dict[str, object] | None:
    path = _source_projection_paths(root, attempt_id)["receipt"]
    if not path.exists():
        return None
    identity = _load_canonical(_source_projection_paths(root, attempt_id)["identity"], "source-projection identity")
    receipt = _load_canonical(path, "source-projection receipt")
    _validate_source_projection_receipt(receipt, identity)
    return receipt


def _source_projection_timeout_after_phase(value: str | None) -> str | None:
    if value is None or not value.startswith(_SOURCE_PUBLICATION_TIMEOUT_AFTER_PHASE_TEST_PREFIX):
        return None
    phase = value.removeprefix(_SOURCE_PUBLICATION_TIMEOUT_AFTER_PHASE_TEST_PREFIX)
    if phase not in SOURCE_PROJECTION_PHASES:
        raise ValueError("source-projection diagnostic timeout phase is invalid")
    return phase


def _child_source_projection_diagnostic_timeout_test(
    staging: Path, identity: Mapping[str, object], phase: str,
) -> NoReturn:
    """Synthetic watchdog seam; it never opens retained inputs or publishes authority."""
    progress = _source_projection_progress_recorder(staging, identity)
    for candidate in SOURCE_PROJECTION_PHASES:
        progress(candidate, {"synthetic_completed_phase_count": SOURCE_PROJECTION_PHASES.index(candidate) + 1})
        if candidate == phase:
            while True:
                time.sleep(60)
    raise AssertionError("diagnostic timeout phase was not reached")


def _source_projection_child_command(
    staging: Path, identity: Mapping[str, object], raw_snapshot_foundation_root: Path,
) -> list[str]:
    return [
        sys.executable, str(Path(__file__).resolve()), "--_source-projection-child",
        "--staging", str(staging),
        "--source-projection-identity", _canonical_json(identity).decode(),
        "--raw-snapshot-foundation-root", str(raw_snapshot_foundation_root),
    ]


def publish_koru_source_projection_authority(
    raw_snapshot_foundation_root: Path, input_snapshot_authority: Mapping[str, object],
    source_projection_publication_root: Path, source_projection_attempt_id: str, *,
    max_seconds: int = DEFAULT_SOURCE_PROJECTION_MAX_SECONDS, _child_test_mode: str | None = None,
) -> dict[str, object]:
    """Publish only verified KORU SourceProjectionV2 authority from raw snapshot bytes."""
    if (
        _child_test_mode not in (None, _SOURCE_PUBLICATION_TIMEOUT_TEST_MODE, _SOURCE_PUBLICATION_FAILURE_TEST_MODE)
        and _source_projection_timeout_after_phase(_child_test_mode) is None
    ):
        raise ValueError("unsupported source-projection child test mode")
    max_seconds = _validate_source_projection_max_seconds(max_seconds)
    raw_authority = _canonical_input_snapshot_authority(input_snapshot_authority)
    catalog, view = _open_input_snapshot_authority(raw_snapshot_foundation_root, raw_authority)
    _verify_koru_discovery_snapshot_scope(catalog, view)
    identity = _source_projection_identity(raw_authority, source_projection_attempt_id)
    root = _prepare_source_projection_publication_root(source_projection_publication_root)
    paths = _source_projection_paths(root, source_projection_attempt_id)
    with _attempt_lock(paths["lock"]):
        existing = _load_source_projection_receipt(root, source_projection_attempt_id)
        if existing is not None:
            if existing["identity"] != identity:
                raise ValueError("source-projection publication attempt identity conflicts with requested raw snapshot")
            if existing["outcome"] != "success":
                raise ValueError("source-projection publication attempt already has a non-success receipt")
            open_koru_source_projection_authority(
                root, cast(Mapping[str, object], existing["source_projection_authority"])
            )
            return existing
        _create_new_json(paths["identity"], identity)
        paths["staging"].mkdir(parents=True)
        _atomic_write(paths["staging"] / SOURCE_PROJECTION_PROGRESS, _source_projection_initial_progress(identity))
        command = _source_projection_child_command(paths["staging"], identity, raw_snapshot_foundation_root)
        if _child_test_mode is not None:
            command.extend(["--_test-mode", _child_test_mode])
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        timed_out, child_status = _wait_for_child(process, max_seconds, time.monotonic())
        if timed_out:
            progress = _load_source_projection_progress(paths["staging"], identity)
            os.rename(paths["staging"], paths["timed_out"])
            _fsync_directory(paths["timed_out"].parent)
            receipt = _source_projection_non_success_receipt(identity, "timeout", child_status, "timed_out", progress)
            _create_new_json(paths["receipt"], receipt)
            return receipt
        if child_status != 0:
            progress = _load_source_projection_progress(paths["staging"], identity)
            os.rename(paths["staging"], paths["failed"])
            _fsync_directory(paths["failed"].parent)
            receipt = _source_projection_non_success_receipt(identity, "non_success", child_status, "failed", progress)
            _create_new_json(paths["receipt"], receipt)
            return receipt
        authority, checkpoint = _validate_source_projection_complete(paths["staging"], identity)
        os.rename(paths["staging"], paths["published"])
        _fsync_directory(paths["published"].parent)
        receipt = _source_projection_success_receipt(identity, authority, checkpoint)
        _create_new_json(paths["receipt"], receipt)
        open_koru_source_projection_authority(root, authority)
        return receipt


def open_koru_source_projection_authority(
    source_projection_publication_root: Path, source_projection_authority: Mapping[str, object],
) -> Any:
    """Open KORU source authority only from its exact published owner-log fact."""
    authority = _canonical_source_projection_publication_authority(source_projection_authority)
    root = _prepare_source_projection_publication_root(source_projection_publication_root)
    attempt_id = cast(str, authority["publication_attempt_id"])
    receipt = _load_source_projection_receipt(root, attempt_id)
    if receipt is None or receipt["outcome"] != "success" or receipt.get("source_projection_authority") != authority:
        raise ValueError("source-projection authority has no consumable success receipt")
    paths = _source_projection_paths(root, attempt_id)
    if not paths["published"].is_dir():
        raise ValueError("source-projection authority publication container is unavailable")
    return _verify_koru_source_projection_authority_in_foundation(
        LocalFoundation(paths["published"] / "foundation"), authority,
        cast(Mapping[str, object], receipt["owner_log_checkpoint"]),
    )


def _child_source_projection_publication(
    staging: Path, identity: Mapping[str, object], raw_snapshot_foundation_root: Path,
) -> None:
    _publish_source_projection_in_staging(staging, identity, raw_snapshot_foundation_root)


def _premium_preflight_authority_v2_locator(locator: Mapping[str, object]) -> tuple[dict[str, object], ArtifactRef, LogEntryRef]:
    required = {"type", "schema_version", "authority_ref", "publication_entry_ref"}
    if (
        type(locator) is not dict
        or set(locator) != required
        or locator.get("type") != PREMIUM_PREFLIGHT_AUTHORITY_V2_LOCATOR_SCHEMA
        or locator.get("schema_version") != 1
    ):
        raise ValueError("premium-preflight V2 locator is invalid")
    authority_wire = locator["authority_ref"]
    entry_wire = locator["publication_entry_ref"]
    if (
        type(authority_wire) is not dict
        or set(authority_wire) != {"type", "artifact_type", "schema_version", "content_hash"}
        or authority_wire.get("type") != "artifact_ref"
    ):
        raise ValueError("premium-preflight V2 authority ref is invalid")
    try:
        authority_ref = ArtifactRef(
            authority_wire["artifact_type"], authority_wire["schema_version"], authority_wire["content_hash"],
        )
    except (TypeError, ValueError) as error:
        raise ValueError("premium-preflight V2 authority ref is invalid") from error
    if (
        authority_ref.artifact_type != "koru_premium_preflight_authority_v2"
        or authority_ref.schema_version != 2
        or authority_ref.to_canonical_dict() != authority_wire
        or type(entry_wire) is not dict
        or set(entry_wire) != {"log_name", "log_sequence", "receipt_hash"}
    ):
        raise ValueError("premium-preflight V2 locator is invalid")
    if (
        type(entry_wire["log_name"]) is not str
        or type(entry_wire["log_sequence"]) is not int
        or entry_wire["log_sequence"] < 1
        or type(entry_wire["receipt_hash"]) is not str
        or len(entry_wire["receipt_hash"]) != 71
        or not entry_wire["receipt_hash"].startswith("sha256:")
        or any(character not in "0123456789abcdef" for character in entry_wire["receipt_hash"][7:])
    ):
        raise ValueError("premium-preflight V2 publication entry ref is invalid")
    entry_ref = LogEntryRef(entry_wire["log_name"], entry_wire["log_sequence"], entry_wire["receipt_hash"])
    canonical = {
        "type": PREMIUM_PREFLIGHT_AUTHORITY_V2_LOCATOR_SCHEMA,
        "schema_version": 1,
        "authority_ref": authority_ref.to_canonical_dict(),
        "publication_entry_ref": {
            "log_name": entry_ref.log_name,
            "log_sequence": entry_ref.log_sequence,
            "receipt_hash": entry_ref.receipt_hash,
        },
    }
    if entry_ref.log_name != KORU_PREMIUM_PREFLIGHT_AUTHORITY_V2_LOG or canonical != locator:
        raise ValueError("premium-preflight V2 locator is noncanonical")
    return canonical, authority_ref, entry_ref


def _premium_preflight_authority_v2_operational_root(root: Path, label: str) -> Path:
    if not isinstance(root, Path) or not root.is_absolute():
        raise ValueError(f"{label} must be an absolute local directory")
    try:
        resolved = root.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"{label} must be an existing local directory") from error
    if not resolved.is_dir():
        raise ValueError(f"{label} must be an existing local directory")
    return resolved


def _premium_preflight_authority_v2_receipt_path(receipt_root: Path, locator: Mapping[str, object]) -> Path:
    directory = receipt_root / "receipts"
    try:
        directory.mkdir(exist_ok=True)
    except OSError as error:
        raise ValueError("premium-preflight V2 receipt directory is unavailable") from error
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("premium-preflight V2 receipt directory is unsafe")
    return directory / f"{canonical_sha256(locator).removeprefix('sha256:')}.json"


def _premium_preflight_authority_v2_common_receipt(
    locator: Mapping[str, object], outcome: str, verification_replay_performed: bool,
) -> dict[str, object]:
    return {
        "type": PREMIUM_PREFLIGHT_AUTHORITY_V2_CONSUMER_RECEIPT_SCHEMA,
        "schema_version": 1,
        "outcome": outcome,
        "authority_locator": dict(locator),
        "network_performed": False,
        "holdout_touched": False,
        "upstream_producer_work_performed": False,
        "verification_replay_performed": verification_replay_performed,
        "stopped_before": _PREMIUM_PREFLIGHT_AUTHORITY_V2_STOPPED_BEFORE,
    }


def _premium_preflight_authority_v2_success_receipt(locator: Mapping[str, object], authority: Any) -> dict[str, object]:
    full_spine = json.loads(canonical_bytes(authority.to_canonical_dict()))
    if type(full_spine) is not dict:
        raise ValueError("premium-preflight V2 authority spine is invalid")
    premium_reader_ids = tuple(binding.premium_id for binding in authority.reader_set.reader_set.bindings)
    reader_set_digest = authority.reader_set.reader_set.reader_set_digest
    spine_reader_set = full_spine.get("reader_set")
    if (
        premium_reader_ids != _PREMIUM_PREFLIGHT_AUTHORITY_V2_READER_IDS
        or type(spine_reader_set) is not dict
        or spine_reader_set.get("reader_set_digest") != reader_set_digest
    ):
        raise ValueError("premium-preflight V2 authority reader set is invalid")
    return {
        **_premium_preflight_authority_v2_common_receipt(locator, "success", True),
        "launch_gate": "GO_FOR_SEPARATE_EXPERIMENT_LAUNCH_REVIEW",
        "final_authority": [{
            "authority_ref": locator["authority_ref"],
            "publication_entry_ref": locator["publication_entry_ref"],
            "full_spine": full_spine,
            "full_spine_sha256": canonical_sha256(full_spine),
            "premium_reader_ids": list(premium_reader_ids),
            "reader_set_digest": reader_set_digest,
        }],
    }


def _premium_preflight_authority_v2_failure_receipt(locator: Mapping[str, object]) -> dict[str, object]:
    return {
        **_premium_preflight_authority_v2_common_receipt(locator, "non_success", True),
        "failure_stage": "authority_spine_verification",
        "launch_gate": "NO_GO",
        "final_authority": [],
    }


def _validate_premium_preflight_authority_v2_consumer_receipt(
    receipt: Mapping[str, object], locator: Mapping[str, object],
) -> dict[str, object]:
    common = {
        "type", "schema_version", "outcome", "authority_locator", "network_performed",
        "holdout_touched", "upstream_producer_work_performed", "verification_replay_performed",
        "stopped_before", "launch_gate", "final_authority",
    }
    if (
        type(receipt) is not dict
        or not common <= set(receipt)
        or receipt.get("type") != PREMIUM_PREFLIGHT_AUTHORITY_V2_CONSUMER_RECEIPT_SCHEMA
        or receipt.get("schema_version") != 1
        or receipt.get("authority_locator") != locator
        or receipt.get("network_performed") is not False
        or receipt.get("holdout_touched") is not False
        or receipt.get("upstream_producer_work_performed") is not False
        or receipt.get("verification_replay_performed") is not True
        or receipt.get("stopped_before") != _PREMIUM_PREFLIGHT_AUTHORITY_V2_STOPPED_BEFORE
        or type(receipt.get("final_authority")) is not list
    ):
        raise ValueError("premium-preflight V2 consumer receipt is invalid")
    if receipt["outcome"] == "success":
        final_authority = receipt["final_authority"]
        if (
            set(receipt) != common
            or receipt.get("launch_gate") != "GO_FOR_SEPARATE_EXPERIMENT_LAUNCH_REVIEW"
            or len(final_authority) != 1
            or type(final_authority[0]) is not dict
        ):
            raise ValueError("premium-preflight V2 success receipt is invalid")
        final = final_authority[0]
        full_spine = final.get("full_spine")
        reader_set = full_spine.get("reader_set") if type(full_spine) is dict else None
        if (
            set(final) != {
                "authority_ref", "publication_entry_ref", "full_spine", "full_spine_sha256",
                "premium_reader_ids", "reader_set_digest",
            }
            or final["authority_ref"] != locator["authority_ref"]
            or final["publication_entry_ref"] != locator["publication_entry_ref"]
            or type(full_spine) is not dict
            or final["full_spine_sha256"] != canonical_sha256(full_spine)
            or final["premium_reader_ids"] != list(_PREMIUM_PREFLIGHT_AUTHORITY_V2_READER_IDS)
            or type(final["reader_set_digest"]) is not str
            or type(reader_set) is not dict
            or reader_set.get("reader_set_digest") != final["reader_set_digest"]
        ):
            raise ValueError("premium-preflight V2 success authority is invalid")
    elif receipt["outcome"] == "non_success":
        if (
            set(receipt) != common | {"failure_stage"}
            or receipt.get("failure_stage") != "authority_spine_verification"
            or receipt.get("launch_gate") != "NO_GO"
            or receipt["final_authority"] != []
        ):
            raise ValueError("premium-preflight V2 failure receipt is invalid")
    else:
        raise ValueError("premium-preflight V2 receipt outcome is invalid")
    return dict(receipt)


def _read_premium_preflight_authority_v2_consumer_receipt(
    path: Path, locator: Mapping[str, object],
) -> dict[str, object] | None:
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file():
        raise ValueError("premium-preflight V2 receipt path is unsafe")
    return _validate_premium_preflight_authority_v2_consumer_receipt(
        _load_canonical(path, "premium-preflight V2 consumer receipt"), locator,
    )


def _write_premium_preflight_authority_v2_consumer_receipt(
    path: Path, receipt: Mapping[str, object], locator: Mapping[str, object],
) -> dict[str, object]:
    try:
        _create_new_json(path, receipt)
    except FileExistsError:
        existing = _read_premium_preflight_authority_v2_consumer_receipt(path, locator)
        if existing != receipt:
            raise ValueError("premium-preflight V2 consumer receipt conflicts with locator")
        return cast(dict[str, object], existing)
    readback = _read_premium_preflight_authority_v2_consumer_receipt(path, locator)
    if readback != receipt:
        raise ValueError("premium-preflight V2 consumer receipt readback mismatch")
    return cast(dict[str, object], readback)


def consume_published_koru_premium_preflight_authority_v2(
    *, locator: Mapping[str, object], foundation_root: Path, repository_root: Path, receipt_root: Path,
) -> dict[str, object]:
    canonical_locator, authority_ref, publication_entry_ref = _premium_preflight_authority_v2_locator(locator)
    foundation_path = _premium_preflight_authority_v2_operational_root(foundation_root, "Foundation root")
    repository_path = _premium_preflight_authority_v2_operational_root(repository_root, "repository root")
    output_root = _premium_preflight_authority_v2_operational_root(receipt_root, "receipt root")
    receipt_path = _premium_preflight_authority_v2_receipt_path(output_root, canonical_locator)
    existing = _read_premium_preflight_authority_v2_consumer_receipt(receipt_path, canonical_locator)
    if existing is not None:
        return existing
    try:
        with deny_network():
            authority = open_published_koru_premium_preflight_authority_v2(
                LocalFoundation(foundation_path), authority_ref=authority_ref,
                publication_entry_ref=publication_entry_ref, repository_root=repository_path,
            )
        receipt = _premium_preflight_authority_v2_success_receipt(canonical_locator, authority)
    except Exception:  # noqa: BLE001 - authority consumer must fail closed
        receipt = _premium_preflight_authority_v2_failure_receipt(canonical_locator)
    return _write_premium_preflight_authority_v2_consumer_receipt(receipt_path, receipt, canonical_locator)


def full_preflight(
    attempt_root: Path, max_seconds: int = DEFAULT_FULL_MAX_SECONDS, *,
    input_snapshot_authority: Mapping[str, object], raw_snapshot_foundation_root: Path,
    retry_ordinal: int = 0, parent_attempt_id: str | None = None, _child_test_mode: str | None = None,
) -> dict[str, object]:
    """Run one isolated full attempt from a previously published raw snapshot."""
    if _child_test_mode not in (None, _TIMEOUT_TEST_MODE):
        raise ValueError("unsupported child test mode")
    authority = _canonical_input_snapshot_authority(input_snapshot_authority)
    snapshot_opened_at = time.monotonic_ns()
    catalog, _view = _open_input_snapshot_authority(raw_snapshot_foundation_root, authority)
    _verify_koru_discovery_snapshot_scope(catalog, _view)
    snapshot_open_elapsed_ns = time.monotonic_ns() - snapshot_opened_at
    config = _full_mode_config(max_seconds, authority)
    root = _prepare_attempt_root(attempt_root)
    _recover_pending_attempts(root)
    catalog_sha256 = cast(str, catalog["catalog_sha256"])
    identity = _attempt_identity(_attempt_preimage(config, catalog_sha256, retry_ordinal, parent_attempt_id))
    attempt_id = cast(str, identity["attempt_id"])
    paths = _attempt_paths(root, attempt_id)
    with _attempt_lock(paths["lock"]):
        _reserve_attempt(root, identity)
        paths["staging"].mkdir(parents=True)
        parent_timings = {"snapshot_open_elapsed_ns": snapshot_open_elapsed_ns}
        child_started_at = time.monotonic_ns()
        command = _child_command(paths["staging"], attempt_id, authority, raw_snapshot_foundation_root)
        command.extend(["--_parent-timings", json.dumps(parent_timings, sort_keys=True)])
        if _child_test_mode is not None:
            command.extend(["--_test-mode", _child_test_mode])
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        timed_out, child_status = _wait_for_child(process, max_seconds, time.monotonic())
        if timed_out:
            timings = {**parent_timings, "child_elapsed_ns": time.monotonic_ns() - child_started_at}
            receipt_path = _archive_timeout(root, attempt_id, child_status, timings)
            raise FullPreflightDeadlineExceeded(max_seconds, receipt_path)
        if child_status != 0:
            raise RuntimeError(f"full preflight child failed with exit status {child_status}")
        validated = _validate_completed_attempt(paths["staging"], identity, parent_timings)
        _promote_attempt_container(root, attempt_id)
        receipt = _success_receipt(root, identity, validated)
        _create_new_json(paths["receipt"], receipt)
        return read_success_receipt(root, attempt_id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--smoke", action="store_true", help="bounded source authority validation; default")
    mode.add_argument("--prepare-input-snapshot", action="store_true", help="publish retained raw bytes before full preflight")
    mode.add_argument("--publish-source-projection", action="store_true", help="publish KORU SourceProjectionV2 from a verified raw snapshot")
    mode.add_argument("--diagnose-source-projection", action="store_true", help="bounded source-projection publication with timeout phase receipt")
    mode.add_argument("--consume-published-preflight-authority-v2", action="store_true", help="offline V2 authority-spine verification receipt; no Experiment")
    mode.add_argument("--full", action="store_true", help="isolated retained source/economics/reader attempt; no Experiment")
    mode.add_argument("--_child", action="store_true", help=argparse.SUPPRESS)
    mode.add_argument("--_source-projection-child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--max-seconds", type=int, default=DEFAULT_FULL_MAX_SECONDS, help="full-only parent deadline (1-300; default: 300)")
    parser.add_argument("--foundation-root", type=Path, help="smoke-only Foundation root")
    parser.add_argument("--preflight-authority-v2-locator", help="canonical published V2 authority locator JSON")
    parser.add_argument("--preflight-authority-v2-foundation-root", type=Path, help="existing local Foundation root for V2 authority verification")
    parser.add_argument("--preflight-authority-v2-repository-root", type=Path, help="existing local repository root for V2 authority verification")
    parser.add_argument("--preflight-authority-v2-receipt-root", type=Path, help="existing local receipt root for V2 authority verification")
    parser.add_argument("--attempt-root", type=Path, help="full-attempt receipt, staging, archive, and published-container root")
    parser.add_argument("--raw-snapshot-foundation-root", type=Path, help="durable raw snapshot Foundation root")
    parser.add_argument("--input-snapshot-authority", help="canonical raw snapshot authority JSON")
    parser.add_argument("--source-projection-publication-root", type=Path, help="source-projection publication root")
    parser.add_argument("--source-projection-attempt-id", help="explicit source-projection publication attempt identity")
    parser.add_argument("--source-projection-max-seconds", type=int, default=DEFAULT_SOURCE_PROJECTION_MAX_SECONDS, help="source-projection-only watchdog (1-900; default: 300)")
    parser.add_argument("--source-projection-identity", help=argparse.SUPPRESS)
    parser.add_argument("--retry-ordinal", type=int, default=0, help="new full-attempt retry ordinal (default: 0)")
    parser.add_argument("--parent-attempt-id", help="optional parent attempt ID for a retry")
    parser.add_argument("--staging", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--attempt-id", help=argparse.SUPPRESS)
    parser.add_argument("--_parent-timings", help=argparse.SUPPRESS)
    parser.add_argument("--_test-mode", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args._source_projection_child:
        if not (args.staging and args.source_projection_identity and args.raw_snapshot_foundation_root):
            parser.error("source-projection child requires staging, identity, and raw snapshot Foundation")
        try:
            identity = json.loads(args.source_projection_identity)
            if type(identity) is not dict:
                raise ValueError("source-projection identity must be an object")
            raw_authority = _canonical_input_snapshot_authority(identity["raw_snapshot_authority"])
            if identity != _source_projection_identity(raw_authority, identity["publication_attempt_id"]):
                raise ValueError("source-projection identity is invalid")
        except (KeyError, ValueError, json.JSONDecodeError) as error:
            parser.error(str(error))
        with deny_network():
            diagnostic_timeout_phase = _source_projection_timeout_after_phase(args._test_mode)
            if diagnostic_timeout_phase is not None:
                _child_source_projection_diagnostic_timeout_test(args.staging, identity, diagnostic_timeout_phase)
            elif args._test_mode == _SOURCE_PUBLICATION_TIMEOUT_TEST_MODE:
                _child_source_projection_timeout_test()
            elif args._test_mode == _SOURCE_PUBLICATION_FAILURE_TEST_MODE:
                raise RuntimeError("source-projection publication test failure")
            elif args._test_mode is None:
                _child_source_projection_publication(args.staging, identity, args.raw_snapshot_foundation_root)
            else:
                parser.error("unsupported source-projection child test mode")
        return 0
    if args._child:
        if not (args.staging and args.attempt_id and args._parent_timings and args.raw_snapshot_foundation_root and args.input_snapshot_authority):
            parser.error("child requires staging, attempt identity, snapshot authority, snapshot Foundation, and timings")
        try:
            authority = json.loads(args.input_snapshot_authority)
            if type(authority) is not dict:
                raise ValueError("input snapshot authority must be an object")
            authority = _canonical_input_snapshot_authority(authority)
            parent_timings = json.loads(args._parent_timings)
            if type(parent_timings) is not dict:
                raise ValueError("parent timings must be an object")
            _elapsed_timings(parent_timings, complete=False)
        except (ValueError, json.JSONDecodeError) as error:
            parser.error(str(error))
        with deny_network():
            if args._test_mode == _TIMEOUT_TEST_MODE:
                _child_timeout_test(args.staging)
            elif args._test_mode is None:
                _child_full_preflight(args.staging, args.attempt_id, authority, args.raw_snapshot_foundation_root, parent_timings)
            else:
                parser.error("unsupported child test mode")
        return 0
    if args.prepare_input_snapshot:
        if args.foundation_root is not None or args.attempt_root is not None or args.input_snapshot_authority is not None or args.raw_snapshot_foundation_root is None:
            parser.error("--prepare-input-snapshot requires only --raw-snapshot-foundation-root")
        with deny_network():
            result = prepare_input_snapshot_authority(args.raw_snapshot_foundation_root)
    elif args.publish_source_projection or args.diagnose_source_projection:
        try:
            _validate_source_projection_max_seconds(args.source_projection_max_seconds)
            if (
                args.foundation_root is not None or args.attempt_root is not None
                or args.raw_snapshot_foundation_root is None or args.input_snapshot_authority is None
                or args.source_projection_publication_root is None or args.source_projection_attempt_id is None
            ):
                parser.error("--publish-source-projection requires --raw-snapshot-foundation-root, --input-snapshot-authority, --source-projection-publication-root, and --source-projection-attempt-id")
            parsed = json.loads(args.input_snapshot_authority)
            if type(parsed) is not dict:
                raise ValueError("input snapshot authority must be an object")
            result = publish_koru_source_projection_authority(
                args.raw_snapshot_foundation_root, parsed, args.source_projection_publication_root,
                args.source_projection_attempt_id, max_seconds=args.source_projection_max_seconds,
            )
        except (ValueError, json.JSONDecodeError) as error:
            parser.error(str(error))
    elif args.consume_published_preflight_authority_v2:
        try:
            if (
                args.foundation_root is not None or args.attempt_root is not None
                or args.raw_snapshot_foundation_root is not None or args.input_snapshot_authority is not None
                or args.source_projection_publication_root is not None or args.source_projection_attempt_id is not None
                or args.preflight_authority_v2_locator is None
                or args.preflight_authority_v2_foundation_root is None
                or args.preflight_authority_v2_repository_root is None
                or args.preflight_authority_v2_receipt_root is None
            ):
                parser.error("--consume-published-preflight-authority-v2 requires its locator, Foundation root, repository root, and receipt root only")
            parsed = json.loads(args.preflight_authority_v2_locator)
            if type(parsed) is not dict:
                raise ValueError("premium-preflight V2 locator must be an object")
            result = consume_published_koru_premium_preflight_authority_v2(
                locator=parsed,
                foundation_root=args.preflight_authority_v2_foundation_root,
                repository_root=args.preflight_authority_v2_repository_root,
                receipt_root=args.preflight_authority_v2_receipt_root,
            )
        except (ValueError, json.JSONDecodeError) as error:
            parser.error(str(error))
    elif args.full:
        try:
            _validate_full_max_seconds(args.max_seconds)
            if args.foundation_root is not None or args.attempt_root is None or args.raw_snapshot_foundation_root is None or args.input_snapshot_authority is None:
                parser.error("--full requires --attempt-root, --raw-snapshot-foundation-root, and --input-snapshot-authority")
            parsed = json.loads(args.input_snapshot_authority)
            if type(parsed) is not dict:
                raise ValueError("input snapshot authority must be an object")
            authority = _canonical_input_snapshot_authority(parsed)
            with deny_network():
                result = full_preflight(
                    args.attempt_root, args.max_seconds, input_snapshot_authority=authority,
                    raw_snapshot_foundation_root=args.raw_snapshot_foundation_root,
                    retry_ordinal=args.retry_ordinal, parent_attempt_id=args.parent_attempt_id,
                )
        except FullPreflightDeadlineExceeded as error:
            print(f"{error}; no successful summary written", file=sys.stderr)
            return 1
        except (ValueError, json.JSONDecodeError) as error:
            parser.error(str(error))
    else:
        with deny_network():
            result = smoke(args.foundation_root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 1 if (
        args.publish_source_projection or args.diagnose_source_projection
        or args.consume_published_preflight_authority_v2
    ) and result.get("outcome") != "success" else 0


if __name__ == "__main__":
    raise SystemExit(main())
