#!/usr/bin/env python3
"""Build the retained KORUUSDT discovery SourceProjectionV2 and TargetV2 manifest.

The production builder path is entirely offline. It reads only retained repository
bytes, invokes public market-bundle-builder modules from the checked-out Backtest
submodule, and emits summaries/hashes rather than source or target event bodies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, NoReturn
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DATA = HERE / "data"
BACKTEST = REPO / "backtest"
OUTPUT = DATA / "discovery_source_targets_v2.json"
EXECUTION_MANIFEST = DATA / "execution_data_manifest.json"
BASE_MANIFEST = DATA / "manifest.json"
GAP_AUDIT = DATA / "execution_gap_impact.json"

# Use the checked-out production modules, not the workspace's older pinned wheels.
for package in (
    "trading-domain",
    "trading-kernel",
    "market-data-contracts",
    "market-bundle-builder",
    "backtest-runtime",
):
    sys.path.insert(0, str(BACKTEST / "packages" / package / "src"))

from crypto_quant_bundle_builder.binance_usdm_koru_aggtrade_boundary_index_v1 import (  # noqa: E402
    BinanceUsdmKoruAggregateTradeBoundaryIndexRequestV1,
    BinanceUsdmKoruExecutionBoundaryV1,
    build_binance_usdm_koru_aggregate_trade_boundary_index_v1,
)
from crypto_quant_bundle_builder.binance_usdm_koru_aggtrades_source_bounded_v1 import (  # noqa: E402
    BINANCE_USDM_KORU_AGGREGATE_TRADE_AVAILABILITY_AUTHORITY_V1,
    BinanceUsdmKoruAggregateTradesSourceBoundedRequestV1,
    BinanceUsdmKoruRetainedAggregateTradesAuthorityV1,
    BinanceUsdmKoruRetainedAggregateTradesPageV1,
    capture_binance_usdm_koru_aggregate_trades_from_retained_rest_v1,
    capture_binance_usdm_koru_aggregate_trades_source_bounded_v1,
)
from crypto_quant_bundle_builder.binance_usdm_koru_closed_market_range_targets_v2 import (  # noqa: E402
    BinanceUsdmKoruClosedMarketRangeTargetsRequestV2,
    build_binance_usdm_koru_closed_market_range_targets_v2,
)
from crypto_quant_bundle_builder.binance_usdm_koru_funding_rate_history_source_bounded_v1 import (  # noqa: E402
    BinanceUsdmKoruFundingRateHistorySourceBoundedRequestV1,
    BinanceUsdmKoruFundingRateHistoryTransportResponseV1,
    capture_binance_usdm_koru_funding_rate_history_source_bounded_v1,
    normalize_binance_usdm_koru_funding_rate_history_source_bounded_v1,
)
from crypto_quant_bundle_builder.binance_usdm_koru_price_bars_source_bounded_v1 import (  # noqa: E402
    BinanceUsdmKoruPriceBarsSourceBoundedRequestV1,
    BinanceUsdmKoruPriceBarsSourceKindV1,
    BinanceUsdmKoruRetainedPriceBarsAuthorityV1,
    build_binance_usdm_koru_price_bars_retained_observations_evidence_v1,
    capture_binance_usdm_koru_price_bars_from_retained_observations_v1,
    capture_binance_usdm_koru_price_bars_source_bounded_v1,
    normalize_binance_usdm_koru_price_bars_source_bounded_v1,
)
from crypto_quant_bundle_builder.binance_usdm_koru_tradifi_execution_bundle_v2 import (  # noqa: E402
    BinanceUsdmKoruTradifiExecutionBundleRequestV2,
    build_binance_usdm_koru_tradifi_execution_bundle_v2,
)
from crypto_quant_bundle_builder.binance_usdm_koru_tradifi_source_projection_v2 import (  # noqa: E402
    BinanceUsdmKoruTradifiSourceProjectionRequestV2,
    _eligible_boundaries,
    _verified_authority,
    build_binance_usdm_koru_source_profile_authority_v2,
    build_binance_usdm_koru_tradifi_source_projection_v2,
)
from crypto_quant_bundle_builder.koru_tradifi_calendar_unit_authority_v1 import (  # noqa: E402
    APPROVED_MEMBER_HASHES,
    build_koru_tradifi_calendar_unit_authority_v1,
    verify_koru_tradifi_calendar_unit_authority_v1,
)
from crypto_quant_bundle_builder.source_snapshots import RawSourceMember  # noqa: E402
from crypto_quant_backtest import (  # noqa: E402
    BinanceUsdmKoruTradifiDevelopmentProfileRequestV1,
    TimelineWindow,
    build_binance_usdm_koru_tradifi_development_profile_v1,
)
from crypto_quant_domain import (  # noqa: E402
    InstrumentId,
    Money,
    Scale,
    SimulationInstant,
    SourceSequence,
    TimelinePhase,
    UtcInstant,
    VenueId,
    canonical_sha256,
)

SCHEMA_VERSION = 1
START_MS = 1_784_109_600_000
END_MS = 1_787_569_200_000
DAY_MS = 86_400_000
AGG_COMMIT = "a61ef741ce582cd61dbc6e3a623066de7c6b8bf4"
AGG_COMMIT_UTC = "2026-08-26T06:50:03Z"
PRICE_FUNDING_COMMIT = "9aca2510ba8aea8397501494aa58742f07ce758f"
PRICE_FUNDING_COMMIT_UTC = "2026-08-26T09:46:54Z"
ACCOUNT_ID = "account-1"
INITIAL_EQUITY = Money(1_000_000_000_000, Scale(8), "USDT")
INSTRUMENT = InstrumentId(VenueId("binance_usdm"), "koru-usdt-tradifi-perpetual")
CALENDAR_FIXTURE = (
    BACKTEST
    / "tests/fixtures/market_data/providers/tradifi/koru-calendar-unit-v1"
)
FUNDING_FIXTURE = (
    BACKTEST
    / "tests/fixtures/market_data/providers/binance_usdm/koru-funding-history-v1"
)
ACCEPTED_FIXTURE_TEST = (
    BACKTEST
    / "tests/bundle_builder/providers/binance_usdm/"
    "test_koru_tradifi_execution_bundle_v1.py"
)
_HASH = re.compile(r"sha256:[0-9a-f]{64}\Z")


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def utc_ns(value: str) -> int:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError(f"not exact UTC: {value}")
    delta = parsed - datetime(1970, 1, 1, tzinfo=UTC)
    return (
        delta.days * 86_400_000_000_000
        + delta.seconds * 1_000_000_000
        + delta.microseconds * 1_000
    )


def utc_ms(value: str) -> int:
    return utc_ns(value) // 1_000_000


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    if type(value) is not dict:
        raise ValueError(f"{path} must contain one JSON object")
    return value


def _json_ready(value: object) -> object:
    if value is None or type(value) in (bool, int, float, str):
        return value
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_ready(item) for item in value]
    to_canonical_dict = getattr(value, "to_canonical_dict", None)
    if callable(to_canonical_dict):
        return _json_ready(to_canonical_dict())
    raise TypeError(f"cannot encode {type(value).__name__} as canonical JSON")


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        _json_ready(value),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def manifest_bytes(value: dict[str, Any]) -> bytes:
    body = dict(value)
    body["manifest_sha256"] = ""
    body["manifest_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return (
        json.dumps(
            _json_ready(body),
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode()


def validate_self_hash(value: dict[str, Any], path: Path) -> None:
    expected = value.get("manifest_sha256")
    if type(expected) is not str or _HASH.fullmatch(expected) is None:
        raise ValueError(f"{path}: missing canonical manifest_sha256")
    body = dict(value)
    body["manifest_sha256"] = ""
    if sha256_bytes(canonical_json_bytes(body)) != expected:
        raise ValueError(f"{path}: canonical self-hash mismatch")


def _unwrap(outcome: Any, label: str) -> Any:
    if outcome.result is None:
        failure = outcome.failure
        detail = getattr(failure, "subject", None) or getattr(
            failure, "member_key", None
        )
        raise RuntimeError(f"{label} failed: {failure.code.value}:{detail}")
    return outcome.result


def _files(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = manifest.get("files")
    if type(entries) is not list:
        raise ValueError("execution manifest files must be a list")
    result = {entry["path"]: entry for entry in entries}
    if len(result) != len(entries):
        raise ValueError("execution manifest contains duplicate file paths")
    return result


def _checked_bytes(
    relative_path: str, files: dict[str, dict[str, Any]]
) -> bytes:
    entry = files.get(relative_path)
    if entry is None:
        raise ValueError(f"unmanifested retained file: {relative_path}")
    raw = (DATA / relative_path).read_bytes()
    if sha256_bytes(raw) != entry["sha256"] or len(raw) != entry["size_bytes"]:
        raise ValueError(f"retained file hash/size mismatch: {relative_path}")
    return raw


def _capture_summary(capture: Any, normalization_hash: str | None = None) -> dict[str, Any]:
    request = capture.request
    result = {
        "utc_date": getattr(request, "utc_date", None),
        "request_hash": request.request_hash,
        "snapshot_id": capture.snapshot.snapshot_id,
        "snapshot_content_tree_hash": capture.snapshot.content_tree_hash,
        "snapshot_provenance_hash": capture.snapshot.provenance_hash,
        "capture_hash": capture.capture_hash,
    }
    if normalization_hash is not None:
        result["normalization_hash"] = normalization_hash
    return result


def _local_fetch(urls: dict[str, bytes]):
    def fetch(url: str) -> tuple[int, bytes]:
        try:
            return 200, urls[url]
        except KeyError as error:
            raise RuntimeError(f"network disabled; unbound URL: {url}") from error

    return fetch


def _official_aggregate_captures(
    files: dict[str, dict[str, Any]],
) -> tuple[tuple[Any, ...], list[dict[str, Any]]]:
    acquired = utc_ns(AGG_COMMIT_UTC)
    captures = []
    summaries = []
    for daily in load_json(EXECUTION_MANIFEST)["datasets"]["aggTrades"]["daily"]:
        utc_date = daily["utc_date"]
        base = f"binance_usdm/aggTrades/daily/KORUUSDT-aggTrades-{utc_date}.zip"
        archive = _checked_bytes(base, files)
        checksum = _checked_bytes(base + ".CHECKSUM", files)
        request = BinanceUsdmKoruAggregateTradesSourceBoundedRequestV1(
            INSTRUMENT,
            utc_date,
            files[base]["provider_last_modified_ns"],
            acquired,
            sha256_bytes(archive),
            sha256_bytes(checksum),
        )
        archive_url, checksum_url = request.urls
        capture = _unwrap(
            capture_binance_usdm_koru_aggregate_trades_source_bounded_v1(
                request, _local_fetch({archive_url: archive, checksum_url: checksum})
            ),
            f"aggregate capture {utc_date}",
        )
        captures.append(capture)
        summaries.append(_capture_summary(capture))
    return tuple(captures), summaries


def _retained_aggregate_capture(
    execution: dict[str, Any], files: dict[str, dict[str, Any]]
) -> tuple[Any, dict[str, Any]]:
    prefix = "binance_usdm/aggTrades/rest-bounded/2026-08-24/"
    page_entries = sorted(
        (
            entry
            for path, entry in files.items()
            if path.startswith(prefix) and entry["status"] == "canonical_rest_response"
        ),
        key=lambda entry: entry["path"],
    )
    pages = []
    page_bytes = []
    for entry in page_entries:
        query = parse_qs(urlparse(entry["source_url"]).query)
        name = entry["path"].removeprefix(prefix)
        pages.append(
            BinanceUsdmKoruRetainedAggregateTradesPageV1(
                member_name=name,
                content_sha256=entry["sha256"],
                source_url=entry["source_url"],
                request_start_time_milliseconds=int(query["startTime"][0]),
                request_end_time_milliseconds=int(query["endTime"][0]),
                page_number=int(name.removesuffix(".json").rsplit("-", 1)[1]),
                row_count=entry["row_count"],
                from_aggregate_trade_id=(
                    int(query["fromId"][0]) if "fromId" in query else None
                ),
            )
        )
        page_bytes.append(_checked_bytes(entry["path"], files))
    derived_name = "KORUUSDT-aggTrades-2026-08-24.discovery-bounded.csv"
    derived_path = prefix + derived_name
    archive_path = derived_path.removesuffix(".csv") + ".zip"
    checksum_path = archive_path + ".CHECKSUM"
    authority = BinanceUsdmKoruRetainedAggregateTradesAuthorityV1(
        execution_manifest_path="research/koruusdt/data/execution_data_manifest.json",
        execution_manifest_file_sha256=sha256_file(EXECUTION_MANIFEST),
        execution_manifest_identity=execution["manifest_sha256"],
        execution_manifest_generated_at_epoch_nanoseconds=utc_ns(
            execution["generated_at_utc"]
        ),
        pages=tuple(pages),
        selected_coverage_start=UtcInstant(1_787_553_260_640_000_000),
        selected_coverage_end_exclusive=UtcInstant(END_MS * 1_000_000),
        declared_missing_prefix_start=UtcInstant(1_787_529_600_000_000_000),
        declared_missing_prefix_end_exclusive=UtcInstant(
            1_787_553_260_640_000_000
        ),
        availability_authority=(
            BINANCE_USDM_KORU_AGGREGATE_TRADE_AVAILABILITY_AUTHORITY_V1
        ),
        derived_csv_member_name=derived_name,
        derived_csv_sha256=files[derived_path]["sha256"],
        derived_csv_schema_identity="binance_usdm_aggtrades_csv_7_column_v1",
    )
    acquired = utc_ns(AGG_COMMIT_UTC)
    request = BinanceUsdmKoruAggregateTradesSourceBoundedRequestV1(
        INSTRUMENT,
        "2026-08-24",
        acquired,
        acquired,
        files[archive_path]["sha256"],
        files[checksum_path]["sha256"],
        authority,
    )
    capture = _unwrap(
        capture_binance_usdm_koru_aggregate_trades_from_retained_rest_v1(
            request,
            EXECUTION_MANIFEST.read_bytes(),
            tuple(page_bytes),
            _checked_bytes(derived_path, files),
            _checked_bytes(archive_path, files),
            _checked_bytes(checksum_path, files),
        ),
        "retained aggregate capture",
    )
    return capture, _capture_summary(capture)


def _official_price_results(
    kind: BinanceUsdmKoruPriceBarsSourceKindV1,
    execution: dict[str, Any],
    files: dict[str, dict[str, Any]],
) -> tuple[tuple[Any, ...], list[dict[str, Any]]]:
    dataset = (
        "markPriceKlines_1h"
        if kind is BinanceUsdmKoruPriceBarsSourceKindV1.MARK_PRICE
        else "indexPriceKlines_1h"
    )
    directory = "mark" if kind.value == "mark_price" else "index"
    acquired = utc_ns(PRICE_FUNDING_COMMIT_UTC)
    results = []
    summaries = []
    for daily in execution["datasets"][dataset]["daily"]:
        utc_date = daily["utc_date"]
        base = (
            f"binance_usdm/priceBars/{directory}/1h/daily/"
            f"KORUUSDT-1h-{utc_date}.zip"
        )
        archive = _checked_bytes(base, files)
        checksum = _checked_bytes(base + ".CHECKSUM", files)
        request = BinanceUsdmKoruPriceBarsSourceBoundedRequestV1(
            kind,
            INSTRUMENT,
            "1h",
            utc_date,
            files[base]["provider_last_modified_ns"],
            acquired,
            sha256_bytes(archive),
            sha256_bytes(checksum),
        )
        archive_url, checksum_url = request.urls
        capture = _unwrap(
            capture_binance_usdm_koru_price_bars_source_bounded_v1(
                request, _local_fetch({archive_url: archive, checksum_url: checksum})
            ),
            f"{kind.value} capture {utc_date}",
        )
        result = _unwrap(
            normalize_binance_usdm_koru_price_bars_source_bounded_v1(capture),
            f"{kind.value} normalization {utc_date}",
        )
        results.append(result)
        summaries.append(_capture_summary(capture, result.normalization_hash))
    return tuple(results), summaries


def _retained_price_result(
    kind: BinanceUsdmKoruPriceBarsSourceKindV1,
    execution: dict[str, Any],
    base: dict[str, Any],
    files: dict[str, dict[str, Any]],
) -> tuple[Any, dict[str, Any]]:
    directory = "mark" if kind.value == "mark_price" else "index"
    raw_name = "binance_mark_raw.csv" if directory == "mark" else "binance_index_raw.csv"
    endpoint = (
        "https://fapi.binance.com/fapi/v1/markPriceKlines"
        if directory == "mark"
        else "https://fapi.binance.com/fapi/v1/indexPriceKlines"
    )
    parameter_name = "symbol" if directory == "mark" else "pair"
    dataset = execution["datasets"][
        "markPriceKlines_1h" if directory == "mark" else "indexPriceKlines_1h"
    ]
    derived_info = dataset["derived_2026_08_24"]["derivation_binding"]
    derived_path = (
        f"binance_usdm/priceBars/{directory}/1h/derived-bounded/2026-08-24/"
        "KORUUSDT-1h-2026-08-24.discovery-bounded.csv"
    )
    archive_path = derived_path.removesuffix(".csv") + ".zip"
    checksum_path = archive_path + ".CHECKSUM"
    authority = BinanceUsdmKoruRetainedPriceBarsAuthorityV1(
        source_artifact_type="binance_fapi_price_bars_raw_csv_v1",
        source_artifact_path=f"research/koruusdt/data/{raw_name}",
        source_artifact_sha256=derived_info["input"]["sha256"],
        source_acquired_at_epoch_nanoseconds=utc_ns(
            derived_info["frozen_source_metadata"]["as_of_utc"]
        ),
        base_manifest_path="research/koruusdt/data/manifest.json",
        base_manifest_file_sha256=sha256_file(BASE_MANIFEST),
        base_manifest_identity=base["manifest_sha256"],
        original_binance_endpoint=endpoint,
        original_binance_parameter_sha256=canonical_sha256(
            {
                "endTime": END_MS - 1,
                "interval": "1h",
                "limit": 1000,
                "startTime": 1_782_136_500_000,
                parameter_name: "KORUUSDT",
            }
        ),
        original_request_start=UtcInstant(1_782_136_500_000_000_000),
        original_request_end_exclusive=UtcInstant(END_MS * 1_000_000),
        provider_availability_authority_ref=(
            "binance.fapi.completed-kline-close-exclusive.v1"
        ),
        selected_coverage_start=UtcInstant(1_787_529_600_000_000_000),
        selected_coverage_end_exclusive=UtcInstant(END_MS * 1_000_000),
        derived_csv_member_name="KORUUSDT-1h-2026-08-24.discovery-bounded.csv",
        derived_csv_sha256=files[derived_path]["sha256"],
        derived_csv_schema_identity=(
            "binance_usdm_koru_price_bars_discovery_bounded_csv_7_column_scale8_v1"
        ),
    )
    derived = _checked_bytes(derived_path, files)
    repository_archive = _checked_bytes(archive_path, files)
    repository_checksum = _checked_bytes(checksum_path, files)
    accepted_archive, accepted_checksum = (
        build_binance_usdm_koru_price_bars_retained_observations_evidence_v1(
            authority, derived
        )
    )
    acquired = utc_ns(PRICE_FUNDING_COMMIT_UTC)
    request = BinanceUsdmKoruPriceBarsSourceBoundedRequestV1(
        kind,
        INSTRUMENT,
        "1h",
        "2026-08-24",
        acquired,
        acquired,
        sha256_bytes(accepted_archive),
        sha256_bytes(accepted_checksum),
        authority,
    )
    capture = _unwrap(
        capture_binance_usdm_koru_price_bars_from_retained_observations_v1(
            request,
            (DATA / raw_name).read_bytes(),
            BASE_MANIFEST.read_bytes(),
            derived,
            accepted_archive,
            accepted_checksum,
        ),
        f"retained {kind.value} capture",
    )
    result = _unwrap(
        normalize_binance_usdm_koru_price_bars_source_bounded_v1(capture),
        f"retained {kind.value} normalization",
    )
    return result, {
        **_capture_summary(capture, result.normalization_hash),
        "repository_derived_artifacts": {
            "csv_sha256": sha256_bytes(derived),
            "zip_sha256": sha256_bytes(repository_archive),
            "checksum_sha256": sha256_bytes(repository_checksum),
        },
        "accepted_capture_evidence": {
            "zip_sha256": sha256_bytes(accepted_archive),
            "checksum_sha256": sha256_bytes(accepted_checksum),
            "operation": "build_binance_usdm_koru_price_bars_retained_observations_evidence_v1",
        },
    }


def _funding_result(
    execution: dict[str, Any], files: dict[str, dict[str, Any]]
) -> tuple[Any, dict[str, Any]]:
    prefix = "binance_usdm/fundingHistory/accepted-capture/"
    raw = _checked_bytes(prefix + "funding-history.json", files)
    retained_receipt = _checked_bytes(prefix + "acquisition-receipt.json", files)
    fixture_raw = (FUNDING_FIXTURE / "funding-history.json").read_bytes()
    fixture_receipt = (FUNDING_FIXTURE / "acquisition-receipt.json").read_bytes()
    if raw != fixture_raw or retained_receipt != fixture_receipt:
        raise ValueError("retained funding bytes do not equal the accepted fixture")
    receipt = json.loads(retained_receipt)
    request_values = receipt["request"]
    request = BinanceUsdmKoruFundingRateHistorySourceBoundedRequestV1(
        INSTRUMENT,
        request_values["start_time_milliseconds"],
        request_values["end_time_milliseconds"],
        request_values["limit"],
        receipt["response_sha256"],
    )
    response = BinanceUsdmKoruFundingRateHistoryTransportResponseV1(
        "GET",
        receipt["url"],
        receipt["url"],
        receipt["status"],
        raw,
        receipt["date_header"],
        utc_ns(receipt["captured_at_utc"]),
    )
    capture = _unwrap(
        capture_binance_usdm_koru_funding_rate_history_source_bounded_v1(
            request, lambda url: response
        ),
        "accepted funding capture",
    )
    if (
        capture.snapshot.member_bytes("response/funding-history.json") != raw
        or capture.snapshot.member_bytes("acquisition/acquisition-receipt.json")
        != retained_receipt
    ):
        raise ValueError("funding builder did not replay accepted fixture bytes")
    result = _unwrap(
        normalize_binance_usdm_koru_funding_rate_history_source_bounded_v1(capture),
        "accepted funding normalization",
    )
    return result, {
        **_capture_summary(capture, result.normalization_hash),
        "authority_source": "accepted_backtest_funding_fixture_byte_exact_mirror",
        "fixture_response_sha256": sha256_bytes(fixture_raw),
        "fixture_receipt_sha256": sha256_bytes(fixture_receipt),
        "repository_retention_commit": PRICE_FUNDING_COMMIT,
        "repository_retention_commit_utc": PRICE_FUNDING_COMMIT_UTC,
    }


def _authority_result(gap: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    receipt_times = {}
    for source in ("krx", "nyse", "binance"):
        receipt = load_json(CALENDAR_FIXTURE / source / "acquisition-receipt.json")
        receipt_times[source] = utc_ns(receipt["captured_at_utc"])
    members = tuple(
        RawSourceMember(
            member_key,
            (CALENDAR_FIXTURE / member_key).read_bytes(),
            "0644",
            receipt_times[member_key.partition("/")[0]],
            expected_hash,
        )
        for member_key, expected_hash in APPROVED_MEMBER_HASHES
    )
    result = _unwrap(
        build_koru_tradifi_calendar_unit_authority_v1(
            members=members, expected_hashes=APPROVED_MEMBER_HASHES
        ),
        "accepted calendar/unit authority",
    )
    verified = _unwrap(
        verify_koru_tradifi_calendar_unit_authority_v1(
            result=result, expected_hashes=APPROVED_MEMBER_HASHES
        ),
        "calendar/unit authority verification",
    )
    expected_refs = tuple(row["ref"] for row in gap["authority_artifacts"])
    actual_refs = tuple(ref.to_canonical_dict() for ref in verified.refs)
    if actual_refs != expected_refs:
        raise ValueError("calendar/unit refs differ from accepted gap-audit fixture refs")
    return verified, {
        "authority_source": "accepted_backtest_calendar_unit_fixture",
        "fixture_root": "backtest/tests/fixtures/market_data/providers/tradifi/koru-calendar-unit-v1",
        "approved_member_hashes": [list(value) for value in APPROVED_MEMBER_HASHES],
        "source_snapshot_id": verified.source_snapshot.snapshot_id,
        "result_hash": canonical_sha256(verified),
        "refs": list(actual_refs),
    }


def validate_gap_audit(gap: dict[str, Any]) -> tuple[BinanceUsdmKoruExecutionBoundaryV1, ...]:
    validate_self_hash(gap, GAP_AUDIT)
    projection = gap.get("actual_first_trade_projections")
    if type(projection) is not dict or projection.get("eligible_boundary_count") != 611:
        raise ValueError("gap audit must contain exactly 611 eligible boundaries")
    events = projection.get("events")
    if type(events) is not list or len(events) != 611:
        raise ValueError("gap audit projection events must exact-cover 611 boundaries")
    pairs = tuple((row["boundary_utc"], row["cutoff_utc"]) for row in events)
    if pairs != tuple(sorted(pairs)) or len(set(pairs)) != 611:
        raise ValueError("gap audit boundary/cutoff pairs must be sorted and unique")
    summary = gap.get("summary")
    expected_parameters = [f"p{index:02d}" for index in range(1, 9)]
    if (
        type(summary) is not dict
        or summary.get("clear_parameters") != expected_parameters
        or summary.get("impacted_events") != []
        or summary.get("impacted_parameters") != []
        or summary.get("missing_eligible_projection_boundaries") != []
        or summary.get("parameters_potentially_impacted_by_missing_projection") != []
        or summary.get("positions_carried_across_gap_start") != []
        or any(row.get("status") != "clear" for row in gap.get("parameters", []))
    ):
        raise ValueError("gap audit is not clear for all eight parameters")
    return tuple(
        BinanceUsdmKoruExecutionBoundaryV1(
            UtcInstant(utc_ns(boundary)), UtcInstant(utc_ns(cutoff))
        )
        for boundary, cutoff in pairs
    )


def validate_target_streams(target: Any) -> list[dict[str, Any]]:
    summaries = []
    for index, stream in enumerate(target.streams, 1):
        states = []
        for event in stream.events:
            candidate = event.payload["candidate"]
            targets = candidate["targets"]
            if type(targets) is not tuple or len(targets) != 1:
                raise ValueError(f"p{index:02d} target shape is not exact")
            states.append(targets[0]["value"] != "0")
        alternating = not states or (
            states[0] and all(left != right for left, right in zip(states, states[1:]))
        )
        flat = not states or not states[-1]
        if not alternating or not flat:
            raise ValueError(f"p{index:02d} stream is nonalternating or nonflat")
        summaries.append(
            {
                "parameter_id": f"p{index:02d}",
                "parameter_ref": stream.parameter_ref.to_canonical_dict(),
                "stream_key": stream.stream_key,
                "target_stream_digest": stream.target_stream_digest,
                "event_count": len(stream.events),
                "candidate_event_hashes": [event.event_hash for event in stream.events],
                "alternating": alternating,
                "flat_at_end": flat,
            }
        )
    if len(summaries) != 8:
        raise ValueError("target builder must return exactly eight streams")
    return summaries


def build_profile_and_bundle(source: Any, target: Any) -> tuple[Any, Any, Any, Any]:
    source_authority_envelope, source_authority_ref = (
        build_binance_usdm_koru_source_profile_authority_v2(source)
    )
    profile = _unwrap(
        build_binance_usdm_koru_tradifi_development_profile_v1(
            BinanceUsdmKoruTradifiDevelopmentProfileRequestV1(
                timeline_window=TimelineWindow(
                    source.request.timeline_window_start,
                    source.request.timeline_window_start,
                    source.request.timeline_window_end_exclusive,
                ),
                composed_at=SimulationInstant(
                    UtcInstant(utc_ns(PRICE_FUNDING_COMMIT_UTC) + 1),
                    TimelinePhase(200, "profile_composition"),
                    SourceSequence(0),
                ),
                account_id=ACCOUNT_ID,
                xkrx_calendar_ref=source.xkrx_calendar_ref,
                arcx_calendar_ref=source.arcx_calendar_ref,
                post_adjustment_unit_regime_ref=(
                    source.post_adjustment_unit_regime_ref
                ),
                source_profile_authority_envelope=source_authority_envelope,
                source_profile_authority_ref=source_authority_ref,
                source_events=source.source_events,
            )
        ),
        "development profile",
    )
    bundle = _unwrap(
        build_binance_usdm_koru_tradifi_execution_bundle_v2(
            BinanceUsdmKoruTradifiExecutionBundleRequestV2(
                source_projection=source,
                target_result=target,
                source_profile_authority_envelope=source_authority_envelope,
                source_profile_authority_ref=source_authority_ref,
                profile_composition_request_wire=(
                    profile.profile_composition_request_wire
                ),
                profile_composition_request_hash=(
                    profile.profile_composition_request_hash
                ),
                execution_account_id=ACCOUNT_ID,
                initial_equity=INITIAL_EQUITY,
                sleeve_allocation_fraction="1",
            )
        ),
        "execution BundleV2",
    )
    return source_authority_envelope, source_authority_ref, profile, bundle


def profile_summary(profile: Any) -> dict[str, Any]:
    return {
        "request_hash": profile.request.request_hash,
        "result_digest": profile.result_digest,
        "profile_composition_request_hash": profile.profile_composition_request_hash,
        "resolved_profile_hash": canonical_sha256(profile.resolved_profile),
        "profile_registry_hash": canonical_sha256(profile.profile_registry),
        "financial_dispatcher_spec_hash": canonical_sha256(
            profile.financial_dispatcher_spec
        ),
        "source_profile_authority_hash": profile.source_profile_authority_hash,
        "source_profile_authority_ref": (
            profile.source_profile_authority_ref.to_canonical_dict()
        ),
        "source_stream_hashes": [list(value) for value in profile.source_stream_hashes],
        "source_stream_counts": [list(value) for value in profile.source_stream_counts],
        "source_stream_count": len(profile.source_stream_counts),
        "source_event_count": sum(value[1] for value in profile.source_stream_counts),
        "source_authority_verified": profile.source_authority_verified,
        "limitations": list(profile.limitations),
    }


def bundle_summary(bundle: Any) -> dict[str, Any]:
    manifest = bundle.manifest
    reader = bundle.reader
    return {
        "request_hash": bundle.request.request_hash,
        "result_digest": bundle.result_digest,
        "bundle_ref": bundle.bundle_ref.to_canonical_dict(),
        "bundle_key": manifest.bundle_key,
        "bundle_schema_version": manifest.schema_version,
        "manifest_hash": canonical_sha256(manifest),
        "manifest_content_hash": manifest.content_hash,
        "authority_refs": [value.to_canonical_dict() for value in bundle.authority_refs],
        "authority_artifacts": [
            {
                "artifact_type": value.artifact_type,
                "schema_version": value.schema_version,
                "content_hash": value.content_hash,
            }
            for value in bundle.authority_artifacts
        ],
        "stream_manifests": [value.to_canonical_dict() for value in manifest.streams],
        "stream_count": len(manifest.streams),
        "event_count_total": sum(value.event_count for value in manifest.streams),
        "reader_ref": reader.bundle_ref.to_canonical_dict(),
        "reader_hash": canonical_sha256(
            {
                "bundle_ref": reader.bundle_ref,
                "manifest": reader.manifest,
                "streams": reader.streams,
            }
        ),
        "development_only": bundle.development_only,
        "deployment_authorized": bundle.deployment_authorized,
        "limitations": list(bundle.request.to_canonical_dict()["limitations"]),
    }


def _git_head() -> str:
    return subprocess.run(
        ["git", "-C", str(BACKTEST), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def build_manifest() -> dict[str, Any]:
    execution = load_json(EXECUTION_MANIFEST)
    base = load_json(BASE_MANIFEST)
    gap = load_json(GAP_AUDIT)
    validate_self_hash(execution, EXECUTION_MANIFEST)
    validate_self_hash(base, BASE_MANIFEST)
    audited_boundaries = validate_gap_audit(gap)
    files = _files(execution)

    aggregate_captures, aggregate_summaries = _official_aggregate_captures(files)
    retained_aggregate, retained_aggregate_summary = _retained_aggregate_capture(
        execution, files
    )
    aggregate_captures += (retained_aggregate,)
    aggregate_summaries.append(retained_aggregate_summary)

    mark_results, mark_summaries = _official_price_results(
        BinanceUsdmKoruPriceBarsSourceKindV1.MARK_PRICE, execution, files
    )
    retained_mark, retained_mark_summary = _retained_price_result(
        BinanceUsdmKoruPriceBarsSourceKindV1.MARK_PRICE, execution, base, files
    )
    mark_results += (retained_mark,)
    mark_summaries.append(retained_mark_summary)

    index_results, index_summaries = _official_price_results(
        BinanceUsdmKoruPriceBarsSourceKindV1.INDEX_PRICE, execution, files
    )
    retained_index, retained_index_summary = _retained_price_result(
        BinanceUsdmKoruPriceBarsSourceKindV1.INDEX_PRICE, execution, base, files
    )
    index_results += (retained_index,)
    index_summaries.append(retained_index_summary)

    funding, funding_summary = _funding_result(execution, files)
    authority, authority_summary = _authority_result(gap)
    probe = SimpleNamespace(
        authority_result=authority,
        timeline_window_start=UtcInstant(START_MS * 1_000_000),
        timeline_window_end_exclusive=UtcInstant(END_MS * 1_000_000),
        aggregate_trade_boundary_index_result=SimpleNamespace(
            request=SimpleNamespace(captures=aggregate_captures)
        ),
    )
    sessions, cash_opens, admission_start = _verified_authority(probe)
    boundaries = _eligible_boundaries(
        probe, sessions, cash_opens, admission_start
    )
    missing_start = retained_aggregate.request.authority.declared_missing_prefix_start
    missing_end = (
        retained_aggregate.request.authority.declared_missing_prefix_end_exclusive
    )
    executable_boundaries = tuple(
        value
        for value in boundaries
        if not (missing_start <= value.boundary < missing_end)
    )
    if executable_boundaries != audited_boundaries:
        raise ValueError(
            "gap audit boundaries differ from production calendar-derived boundaries"
        )

    boundary_request = BinanceUsdmKoruAggregateTradeBoundaryIndexRequestV1(
        captures=aggregate_captures,
        timeline_window_start=UtcInstant(START_MS * 1_000_000),
        timeline_window_end_exclusive=UtcInstant(END_MS * 1_000_000),
        boundaries=boundaries,
    )
    boundary_index = _unwrap(
        build_binance_usdm_koru_aggregate_trade_boundary_index_v1(boundary_request),
        "aggregate boundary index",
    )
    print("built aggregate boundary index", file=sys.stderr)
    expected_missing = tuple(
        value for value in boundaries if missing_start <= value.boundary < missing_end
    )
    if tuple(value.boundary for value in boundary_index.missing_boundaries) != tuple(
        value.boundary for value in expected_missing
    ):
        raise ValueError("boundary index missing evidence does not match retained gap")

    instrument_catalog_hash = canonical_sha256(
        {
            "type": "koruusdt_retained_discovery_instrument_binding_v1",
            "instrument_id": INSTRUMENT.to_canonical_dict(),
            "symbol": "KORUUSDT",
            "contract_type": base["contractType"],
            "base_manifest_identity": base["manifest_sha256"],
        }
    )
    source = _unwrap(
        build_binance_usdm_koru_tradifi_source_projection_v2(
            BinanceUsdmKoruTradifiSourceProjectionRequestV2(
                timeline_window_start=UtcInstant(START_MS * 1_000_000),
                timeline_window_end_exclusive=UtcInstant(END_MS * 1_000_000),
                instrument_catalog_hash=instrument_catalog_hash,
                projection_scale=Scale(8),
                aggregate_trade_boundary_index_result=boundary_index,
                mark_price_results=mark_results,
                index_price_results=index_results,
                funding_result=funding,
                authority_result=authority,
            )
        ),
        "SourceProjectionV2",
    )
    print("built SourceProjectionV2", file=sys.stderr)
    if tuple(value.hourly_boundary for value in source.missing_boundaries) != tuple(
        value.boundary for value in expected_missing
    ):
        raise ValueError("SourceProjectionV2 missing evidence does not match retained gap")
    target = _unwrap(
        build_binance_usdm_koru_closed_market_range_targets_v2(
            BinanceUsdmKoruClosedMarketRangeTargetsRequestV2(source)
        ),
        "TargetV2",
    )
    print("built TargetV2", file=sys.stderr)
    target_summaries = validate_target_streams(target)
    print("building development profile and BundleV2", file=sys.stderr)
    source_authority_envelope, source_authority_ref, profile, bundle = (
        build_profile_and_bundle(source, target)
    )
    print("built development profile and BundleV2", file=sys.stderr)

    accepted_fixture = gap["accepted_bundle_fixture"]
    accepted_fixture_binding = {
        **accepted_fixture,
        "path_sha256": sha256_file(REPO / accepted_fixture["path"]),
        "authority_source": "accepted_backtest_fixture_binding_from_gap_audit",
    }
    value: dict[str, Any] = {
        "type": "koruusdt_discovery_source_targets_v2_manifest",
        "schema_version": SCHEMA_VERSION,
        "instrument": "KORUUSDT",
        "window": {
            "start_utc_inclusive": "2026-07-15T10:00:00.000Z",
            "end_utc_exclusive": "2026-08-24T11:00:00.000Z",
            "semantics": "half-open",
        },
        "builder": {
            "path": "research/koruusdt/build_discovery_source_targets_v2.py",
            "sha256": sha256_file(Path(__file__)),
            "backtest_head": _git_head(),
            "backtest_builder_modules": [
                "binance_usdm_koru_aggtrades_source_bounded_v1",
                "binance_usdm_koru_price_bars_source_bounded_v1",
                "binance_usdm_koru_funding_rate_history_source_bounded_v1",
                "koru_tradifi_calendar_unit_authority_v1",
                "binance_usdm_koru_aggtrade_boundary_index_v1",
                "binance_usdm_koru_tradifi_source_projection_v2",
                "binance_usdm_koru_closed_market_range_targets_v2",
                "binance_usdm_koru_tradifi_development_profile_v1",
                "binance_usdm_koru_tradifi_execution_bundle_v2",
            ],
            "network_performed": False,
        },
        "input_manifests": {
            "base": {
                "path": "research/koruusdt/data/manifest.json",
                "file_sha256": sha256_file(BASE_MANIFEST),
                "manifest_sha256": base["manifest_sha256"],
            },
            "execution": {
                "path": "research/koruusdt/data/execution_data_manifest.json",
                "file_sha256": sha256_file(EXECUTION_MANIFEST),
                "manifest_sha256": execution["manifest_sha256"],
            },
            "gap_audit": {
                "path": "research/koruusdt/data/execution_gap_impact.json",
                "file_sha256": sha256_file(GAP_AUDIT),
                "manifest_sha256": gap["manifest_sha256"],
                "eligible_boundary_count": 611,
                "event_hashes_sha256": gap["actual_first_trade_projections"][
                    "event_hashes_sha256"
                ],
                "status": "clear",
            },
        },
        "repository_retention": {
            "aggregate_trades": {
                "commit": AGG_COMMIT,
                "commit_timestamp_utc": AGG_COMMIT_UTC,
            },
            "price_and_funding": {
                "commit": PRICE_FUNDING_COMMIT,
                "commit_timestamp_utc": PRICE_FUNDING_COMMIT_UTC,
            },
        },
        "captures": {
            "aggregate_trades": aggregate_summaries,
            "mark_price_1h": mark_summaries,
            "index_price_1h": index_summaries,
            "funding": funding_summary,
        },
        "accepted_authority": {
            "funding_normalization_hash": funding.normalization_hash,
            "calendar_unit": authority_summary,
            "accepted_bundle_fixture": accepted_fixture_binding,
        },
        "instrument_catalog_hash": instrument_catalog_hash,
        "boundary_index": {
            "request_hash": boundary_index.request.request_hash,
            "result_digest": boundary_index.result_digest,
            "streamed_row_count": boundary_index.streamed_row_count,
            "streamed_reconstruction_digest": (
                boundary_index.streamed_reconstruction_digest
            ),
            "selected_count": len(boundary_index.selected_source_events),
            "missing_count": len(boundary_index.missing_boundaries),
            "intra_day_raw_id_gap_stream": (
                boundary_index.intra_day_raw_id_gap_stream.to_canonical_dict()
            ),
            "cross_date_raw_id_gap_stream": (
                boundary_index.cross_date_raw_id_gap_stream.to_canonical_dict()
            ),
            "aggregate_id_coverage_gaps": [
                value.to_canonical_dict()
                for value in boundary_index.aggregate_id_coverage_gaps
            ],
        },
        "source_projection_v2": {
            "request_hash": source.request.request_hash,
            "fragment_digest": source.fragment_digest,
            "source_event_count": len(source.source_events),
            "projection_event_count": len(source.projection_events),
            "missing_boundary_count": len(source.missing_boundaries),
            "stream_manifests": [
                value.to_canonical_dict() for value in source.stream_manifests
            ],
            "authority_refs": [
                source.xkrx_calendar_ref.to_canonical_dict(),
                source.arcx_calendar_ref.to_canonical_dict(),
                source.post_adjustment_unit_regime_ref.to_canonical_dict(),
            ],
            "development_only": source.development_only,
            "decision_grade_eligible": source.decision_grade_eligible,
            "deployment_authorized": source.deployment_authorized,
        },
        "targets_v2": {
            "request_hash": target.request.request_hash,
            "result_digest": target.result_digest,
            "strategy_ref": target.strategy.ref.to_canonical_dict(),
            "parameter_refs": [
                value.ref.to_canonical_dict() for value in target.parameters
            ],
            "streams": target_summaries,
            "development_authorized": target.development_authorized,
            "deployment_authorized": target.deployment_authorized,
        },
        "source_profile_authority_v2": {
            "artifact_type": source_authority_envelope.artifact_type,
            "schema_version": source_authority_envelope.schema_version,
            "content_hash": source_authority_envelope.content_hash,
            "ref": source_authority_ref.to_canonical_dict(),
        },
        "development_profile_v1": profile_summary(profile),
        "execution_bundle_v2": bundle_summary(bundle),
        "limitations": [
            "development_only",
            "advisory_only",
            "decision_grade_eligible_false",
            "deployment_authorized_false",
            "development_profile_and_execution_bundle_are_not_backtest_or_economics_evidence",
            "aug24_aggregate_trade_prefix_missing_but_gap_audit_clear",
            "aug24_mark_index_are_base_manifest_derived_retained_observations",
            "instrument_catalog_hash_is_local_retained_discovery_binding_not_deployment_catalog",
            "official_archive_acquisition_is_conservatively_bound_to_repository_retention_commits",
        ],
        "advisory_flags": {
            "gap_audit_clear": True,
            "all_target_streams_alternating": True,
            "all_target_streams_flat_at_end": True,
            "profile_source_authority_verified": profile.source_authority_verified,
            "execution_bundle_development_only": bundle.development_only,
            "execution_bundle_deployment_authorized": bundle.deployment_authorized,
            "network_performed": False,
            "backtest_evidence": False,
            "economics_evidence": False,
        },
        "manifest_sha256": "",
    }
    return json.loads(manifest_bytes(value))


def _die(message: str) -> NoReturn:
    raise SystemExit(message)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="rebuild and byte-compare the checked-in output without writing",
    )
    args = parser.parse_args(argv)
    rebuilt = manifest_bytes(build_manifest())
    if args.validate_only:
        if not OUTPUT.exists():
            _die(f"missing output: {OUTPUT}")
        current = OUTPUT.read_bytes()
        if current != rebuilt:
            _die(
                f"validation mismatch: expected {sha256_bytes(current)}, "
                f"rebuilt {sha256_bytes(rebuilt)}"
            )
        print(f"validated {OUTPUT}: {sha256_bytes(rebuilt)}")
        return 0
    temporary = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
    temporary.write_bytes(rebuilt)
    os.replace(temporary, OUTPUT)
    print(f"wrote {OUTPUT}: {sha256_bytes(rebuilt)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
