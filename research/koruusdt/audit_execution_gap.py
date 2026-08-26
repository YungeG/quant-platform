"""Advisory target-intent audit for the bounded 2026-08-24 aggTrades gap."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BACKTEST = ROOT / "backtest"
DATA = Path(__file__).resolve().parent / "data"
OUTPUT = DATA / "execution_gap_impact.json"
TARGET_BUILDER = (
    BACKTEST
    / "packages/market-bundle-builder/src/crypto_quant_bundle_builder/"
    "binance_usdm_koru_closed_market_range_targets_v1.py"
)

# The workspace dependency predates the frozen target builder. Import the exact local
# implementation and accepted bundle fixture without changing the submodule.
for _path in reversed(
    (
        BACKTEST,
        BACKTEST / "packages/market-bundle-builder/src",
        BACKTEST / "packages/backtest-runtime/src",
        BACKTEST / "packages/trading-domain/src",
        BACKTEST / "packages/market-data-contracts/src",
        BACKTEST / "packages/trading-kernel/src",
    )
):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from crypto_quant_bundle_builder.binance_usdm_koru_closed_market_range_targets_v1 import (  # noqa: E402
    _BarPair,
    _closed_intervals,
    _parameter_bindings,
    _Projection,
    _strategy_binding,
    _stream_events,
)
from crypto_quant_domain import (  # noqa: E402
    SourceSequence,
    TimelinePhase,
    UtcInstant,
    canonical_sha256,
)
from crypto_quant_market_data import (  # noqa: E402
    MarketBundleCapability,
    MarketEvent,
)
from tests.bundle_builder.providers.binance_usdm import (  # noqa: E402
    test_koru_tradifi_execution_bundle_v1 as _accepted_bundle_fixture,
)

_accepted_bundle_result = _accepted_bundle_fixture._empty_result

_HOUR_NS = 3_600_000_000_000
_PRICE_SCALE = 100_000_000
_GAP_START = "2026-08-24T00:00:00.000Z"
_GAP_END = "2026-08-24T06:34:20.640Z"


@dataclass(frozen=True)
class _Request:
    timeline_window_start: UtcInstant
    timeline_window_end_exclusive: UtcInstant


@dataclass(frozen=True)
class _AuditSource:
    request: _Request
    xkrx_calendar: object
    arcx_calendar: object
    post_adjustment_unit_regime: object
    xkrx_calendar_ref: object
    arcx_calendar_ref: object
    post_adjustment_unit_regime_ref: object
    fragment_digest: str


@dataclass(frozen=True)
class _AggTrade:
    archive_path: str
    archive_sha256: str
    aggregate_trade_id: int
    price: str
    quantity: str
    first_trade_id: int
    last_trade_id: int
    transact_time_ns: int
    is_buyer_maker: bool


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()


def _manifest_sha256(value: dict[str, Any]) -> str:
    hashable = dict(value)
    hashable["manifest_sha256"] = ""
    return "sha256:" + hashlib.sha256(_canonical_json_bytes(hashable)).hexdigest()


def _ns(value: str) -> int:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError(f"not exact UTC text: {value}")
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    delta = parsed - epoch
    return (
        delta.days * 86_400_000_000_000
        + delta.seconds * 1_000_000_000
        + delta.microseconds * 1_000
    )


def _utc(value: int) -> str:
    seconds, fraction = divmod(value, 1_000_000_000)
    base = datetime.fromtimestamp(seconds, UTC).strftime("%Y-%m-%dT%H:%M:%S")
    digits = f"{fraction:09d}".rstrip("0")
    return f"{base}.{digits.ljust(3, '0')}Z"


def _price_units(value: str) -> int:
    whole, dot, fraction = value.partition(".")
    if not whole.isdigit() or (dot and (not fraction.isdigit() or len(fraction) > 8)):
        raise ValueError(f"price is not positive scale-8 text: {value}")
    units = int(whole) * _PRICE_SCALE + int(fraction.ljust(8, "0") or "0")
    if units <= 0:
        raise ValueError(f"price is not positive: {value}")
    return units


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _validated_manifests() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    base_path = DATA / "manifest.json"
    execution_path = DATA / "execution_data_manifest.json"
    base = _load_json(base_path)
    execution = _load_json(execution_path)
    if base.get("manifest_sha256") != _manifest_sha256(base):
        raise ValueError("base manifest canonical hash mismatch")
    if execution.get("manifest_sha256") != _manifest_sha256(execution):
        raise ValueError("execution data manifest canonical hash mismatch")
    base_file_hash = _sha256(base_path)
    if execution.get("base_manifest") != {
        "path": "manifest.json",
        "sha256": base_file_hash,
    }:
        raise ValueError(
            "execution data manifest does not bind the exact base manifest"
        )
    artifacts = {
        row["path"]: row
        for row in base.get("artifacts", [])
        if isinstance(row, dict) and isinstance(row.get("path"), str)
    }
    for name in ("binance_mark_raw.csv", "binance_index_raw.csv"):
        if name not in artifacts or artifacts[name].get("sha256") != _sha256(
            DATA / name
        ):
            raise ValueError(f"frozen CSV hash mismatch: {name}")
    missing = [
        row
        for row in execution.get("missing_intervals", [])
        if isinstance(row, dict)
        and row.get("dataset") == "aggTrades"
        and row.get("start_utc_inclusive") == _GAP_START
        and row.get("end_utc_exclusive") == _GAP_END
    ]
    if len(missing) != 1:
        raise ValueError("exact bounded aggTrades gap is not uniquely manifest-bound")
    return base, execution, artifacts


def _source_event(kind: str, row: dict[str, str], sequence: int) -> MarketEvent:
    opened_ns = _ns(row["open_time_utc"])
    completed_ns = opened_ns + _HOUR_NS
    preimage = {
        "type": "koruusdt_execution_gap_audit_source_independent_bar_v1",
        "source_kind": kind,
        "row": row,
    }
    identity = canonical_sha256({"identity": "event", "preimage": preimage})
    return MarketEvent(
        event_id=f"koruusdt-gap-audit-{kind}-v1:{identity}",
        stream_key=f"research.koruusdt.execution_gap_audit.{kind}.1h.v1",
        event_type="research_source_independent_1h_price_bar",
        capability=MarketBundleCapability("research.source-independent-price-bar", 1),
        instrument_id=None,
        event_time=UtcInstant(completed_ns),
        available_time=UtcInstant(completed_ns),
        phase=TimelinePhase(0, "market_data"),
        source_sequence=SourceSequence(sequence),
        revision_id=canonical_sha256({"identity": "revision", "preimage": preimage}),
        supersedes_revision_id=None,
        source_key=f"research.koruusdt.frozen_csv.{kind}.v1",
        source_hash=canonical_sha256({"identity": "source", "preimage": preimage}),
        payload={
            "schema_version": 1,
            "source_kind": kind,
            "price_purpose": "strategy",
            "interval": "1h",
            "price_scale": 8,
            "high_units": _price_units(row["high"]),
            "low_units": _price_units(row["low"]),
            "close_units": _price_units(row["close"]),
            "open_time_utc": row["open_time_utc"],
            "close_time_utc": row["close_time_utc"],
            "advisory_target_intent_input": True,
            "backtest_evidence": False,
        },
    )


def _price_events(
    name: str, kind: str, start_ns: int, end_ns: int
) -> dict[int, MarketEvent]:
    result: dict[int, MarketEvent] = {}
    with (DATA / name).open(newline="", encoding="utf-8") as handle:
        for sequence, row in enumerate(csv.DictReader(handle)):
            completed_ns = _ns(row["open_time_utc"]) + _HOUR_NS
            if not start_ns <= completed_ns < end_ns:
                continue
            event = _source_event(kind, row, sequence)
            if completed_ns in result:
                raise ValueError(f"duplicate {kind} completion: {_utc(completed_ns)}")
            result[completed_ns] = event
    if not result:
        raise ValueError(f"no retained {kind} events")
    return result


def _eligible_boundaries(
    closed: tuple[tuple[int, int], ...], start_ns: int, end_ns: int
) -> tuple[tuple[int, int], ...]:
    result = []
    for interval_start, interval_end in closed:
        boundary = max(
            ((interval_start + _HOUR_NS - 1) // _HOUR_NS) * _HOUR_NS,
            ((start_ns + _HOUR_NS - 1) // _HOUR_NS) * _HOUR_NS,
        )
        while boundary < interval_end and boundary < end_ns:
            result.append((boundary, interval_end))
            boundary += _HOUR_NS
    return tuple(result)


def _aggtrade_archives(execution: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    archives = []
    for row in execution.get("files", []):
        if not isinstance(row, dict):
            continue
        path = row.get("path")
        sha256 = row.get("sha256")
        if (
            isinstance(path, str)
            and isinstance(sha256, str)
            and path.startswith("binance_usdm/aggTrades/")
            and path.endswith(".zip")
            and (
                "/daily/" in path
                or path.endswith("KORUUSDT-aggTrades-2026-08-24.discovery-bounded.zip")
            )
        ):
            archives.append((path, sha256))
    archives.sort()
    if len(archives) != 41:
        raise ValueError("expected 40 daily and one REST-bounded aggTrades archives")
    return tuple(archives)


def _coverage_is_complete(
    boundary_ns: int,
    event_time_ns: int,
    missing: tuple[tuple[int, int], ...],
) -> bool:
    return all(
        max(boundary_ns, missing_start) >= min(event_time_ns + 1, missing_end)
        for missing_start, missing_end in missing
    )


@lru_cache(maxsize=4)
def _first_retained_trades(
    boundaries: tuple[tuple[int, int], ...],
    archives: tuple[tuple[str, str], ...],
    missing: tuple[tuple[int, int], ...],
) -> tuple[tuple[int, int, _AggTrade], ...]:
    retained = []
    position = 0
    expected_header = (
        b"agg_trade_id,price,quantity,first_trade_id,last_trade_id,"
        b"transact_time,is_buyer_maker"
    )
    for relative_path, expected_sha256 in archives:
        path = DATA / relative_path
        if _sha256(path) != expected_sha256:
            raise ValueError(f"frozen aggTrades archive hash mismatch: {relative_path}")
        with zipfile.ZipFile(path) as archive:
            members = [name for name in archive.namelist() if not name.endswith("/")]
            if len(members) != 1:
                raise ValueError(
                    f"aggTrades archive must contain one member: {relative_path}"
                )
            lines = archive.read(members[0]).splitlines()
        if not lines or lines[0] != expected_header:
            raise ValueError(f"aggTrades schema mismatch: {relative_path}")
        for line in lines[1:]:
            fields = line.split(b",")
            if len(fields) != 7:
                raise ValueError(f"aggTrades row width mismatch: {relative_path}")
            transact_time_ns = int(fields[5]) * 1_000_000
            while (
                position < len(boundaries)
                and boundaries[position][0] <= transact_time_ns
            ):
                boundary_ns, cutoff_ns = boundaries[position]
                if (
                    transact_time_ns < cutoff_ns
                    and _coverage_is_complete(boundary_ns, transact_time_ns, missing)
                ):
                    price = fields[1].decode()
                    _price_units(price)
                    maker = fields[6]
                    if maker not in {b"true", b"false"}:
                        raise ValueError("aggTrades buyer-maker value is noncanonical")
                    retained.append(
                        (
                            boundary_ns,
                            cutoff_ns,
                            _AggTrade(
                                archive_path=relative_path,
                                archive_sha256=expected_sha256,
                                aggregate_trade_id=int(fields[0]),
                                price=price,
                                quantity=fields[2].decode(),
                                first_trade_id=int(fields[3]),
                                last_trade_id=int(fields[4]),
                                transact_time_ns=transact_time_ns,
                                is_buyer_maker=maker == b"true",
                            ),
                        )
                    )
                position += 1
            if position == len(boundaries):
                return tuple(retained)
    return tuple(retained)


def _projection_event(
    boundary_ns: int, cutoff_ns: int, trade: _AggTrade, sequence: int
) -> MarketEvent:
    preimage = {
        "type": "koruusdt_execution_gap_advisory_first_retained_aggtrade_v1",
        "boundary": boundary_ns,
        "cutoff": cutoff_ns,
        "archive_path": trade.archive_path,
        "archive_sha256": trade.archive_sha256,
        "aggregate_trade_id": trade.aggregate_trade_id,
        "first_trade_id": trade.first_trade_id,
        "last_trade_id": trade.last_trade_id,
        "transact_time_ns": trade.transact_time_ns,
        "price": trade.price,
    }
    identity = canonical_sha256({"identity": "event", "preimage": preimage})
    return MarketEvent(
        event_id=f"koruusdt-gap-audit-first-retained-aggtrade-v1:{identity}",
        stream_key=(
            "research.koruusdt.execution_gap_audit."
            "first_retained_aggregate_trade.1h.v1"
        ),
        event_type="bar_open",
        capability=MarketBundleCapability("bar_open", 1),
        instrument_id=None,
        event_time=UtcInstant(trade.transact_time_ns),
        available_time=UtcInstant(trade.transact_time_ns),
        phase=TimelinePhase(20, "bar_open"),
        source_sequence=SourceSequence(sequence),
        revision_id=canonical_sha256({"identity": "revision", "preimage": preimage}),
        supersedes_revision_id=None,
        source_key="research.koruusdt.execution_gap_audit.reconstructed_aggtrade.v1",
        source_hash=canonical_sha256({"identity": "source", "preimage": preimage}),
        payload={
            "schema_version": 1,
            "label": "ADVISORY_RECONSTRUCTED_FIRST_RETAINED_AGGTRADE",
            "bar_kind": "real",
            "open_price": {
                "units": _price_units(trade.price),
                "scale": 8,
                "quote_currency": "USDT",
            },
            "aggregate_trade_id": trade.aggregate_trade_id,
            "first_trade_id": trade.first_trade_id,
            "last_trade_id": trade.last_trade_id,
            "quantity": trade.quantity,
            "is_buyer_maker": trade.is_buyer_maker,
            "source_archive_path": trade.archive_path,
            "source_archive_sha256": trade.archive_sha256,
            "actual_captured_aggtrade": True,
            "source_object_reconstructed": True,
            "advisory_only": True,
            "backtest_evidence": False,
        },
    )


def _gap_projection_audit(
    closed: tuple[tuple[int, int], ...],
    projections: dict[int, _Projection],
    gap_start_ns: int,
    gap_end_ns: int,
    parameter_ids: tuple[str, ...],
) -> dict[str, Any]:
    eligible = _eligible_boundaries(closed, gap_start_ns, gap_end_ns)
    missing = tuple(boundary for boundary, _ in eligible if boundary not in projections)
    return {
        "eligible_boundaries": tuple(boundary for boundary, _ in eligible),
        "missing_projection_boundaries": missing,
        "potentially_impacted_parameters": parameter_ids if missing else (),
    }


def _build_inputs() -> tuple[
    _AuditSource,
    tuple[tuple[int, int], ...],
    dict[int, _BarPair],
    dict[int, _Projection],
    dict[str, Any],
]:
    base, execution, artifacts = _validated_manifests()
    accepted_bundle = _accepted_bundle_result()
    authority = accepted_bundle.source_projection
    admission = authority.post_adjustment_unit_regime.payload[
        "authoritative_post_adjustment_admission"
    ]
    start_ns = max(
        _ns(execution["discovery_interval"]["start_utc_inclusive"]),
        _ns(admission["start"]),
    )
    end_ns = _ns(execution["discovery_interval"]["end_utc_exclusive"])
    if end_ns > _ns(admission["end_exclusive"]):
        raise ValueError("discovery end exceeds accepted unit-regime authority")

    archives = _aggtrade_archives(execution)
    missing = tuple(
        (_ns(row["start_utc_inclusive"]), _ns(row["end_utc_exclusive"]))
        for row in execution["missing_intervals"]
        if row.get("dataset") == "aggTrades"
    )
    input_binding = {
        "type": "koruusdt_execution_gap_audit_input_binding_v2",
        "window": {"start": _utc(start_ns), "end_exclusive": _utc(end_ns)},
        "frozen_csvs": {
            name: artifacts[name]["sha256"]
            for name in ("binance_mark_raw.csv", "binance_index_raw.csv")
        },
        "aggtrade_archives": [
            {"path": path, "sha256": sha256} for path, sha256 in archives
        ],
        "authority_refs": [
            ref.to_canonical_dict() for ref in accepted_bundle.authority_refs
        ],
        "projection_policy": (
            "actual_first_retained_aggtrade_at_or_after_each_eligible_boundary;"
            "no_projection_across_manifest_missing_coverage"
        ),
    }
    source = _AuditSource(
        request=_Request(UtcInstant(start_ns), UtcInstant(end_ns)),
        xkrx_calendar=authority.xkrx_calendar,
        arcx_calendar=authority.arcx_calendar,
        post_adjustment_unit_regime=authority.post_adjustment_unit_regime,
        xkrx_calendar_ref=authority.xkrx_calendar_ref,
        arcx_calendar_ref=authority.arcx_calendar_ref,
        post_adjustment_unit_regime_ref=authority.post_adjustment_unit_regime_ref,
        fragment_digest=canonical_sha256(input_binding),
    )
    mark = _price_events("binance_mark_raw.csv", "mark_price", start_ns, end_ns)
    index = _price_events("binance_index_raw.csv", "index_price", start_ns, end_ns)
    if mark.keys() != index.keys():
        raise ValueError("frozen mark/index completion grids differ")
    pairs = {
        completed: _BarPair(completed, mark[completed], index[completed])
        for completed in sorted(mark)
    }
    closed = _closed_intervals(source)  # type: ignore[arg-type]
    eligible = _eligible_boundaries(closed, start_ns, end_ns)
    retained = _first_retained_trades(eligible, archives, missing)
    projections = {
        boundary: _Projection(
            boundary,
            cutoff,
            _projection_event(boundary, cutoff, trade, sequence),
        )
        for sequence, (boundary, cutoff, trade) in enumerate(retained)
    }
    metadata = {
        "base": base,
        "execution": execution,
        "artifacts": artifacts,
        "accepted_bundle": accepted_bundle,
        "input_binding": input_binding,
        "mark_events": mark,
        "index_events": index,
        "eligible_boundaries": eligible,
        "aggtrade_archives": archives,
        "missing_coverage": missing,
    }
    return source, closed, pairs, projections, metadata


def _candidate_wire(event: MarketEvent, kind: str) -> dict[str, Any]:
    candidate = event.payload["candidate"]
    evidence = candidate["evidence"]
    return {
        "kind": kind,
        "event_id": event.event_id,
        "event_hash": event.event_hash,
        "decision_time_utc": _utc(candidate["decision_time"]),
        "projection_boundary_utc": _utc(evidence["projection_boundary"]),
        "projection_actual_event_time_utc": _utc(
            evidence["projection_actual_event_time"]
        ),
        "projection_event_id": evidence["projection_event_id"],
        "projection_event_hash": evidence["projection_event_hash"],
        "projection_cutoff_utc": _utc(evidence["projection_cutoff"]),
        "reason": candidate["reason"],
        "target": candidate["targets"][0]["value"],
    }


def _validate_stream(events: tuple[MarketEvent, ...], parameter_id: str) -> None:
    if len(events) % 2:
        raise ValueError(f"target stream is nonflat at discovery end: {parameter_id}")
    previous_boundary = -1
    for index, event in enumerate(events):
        candidate = event.payload["candidate"]
        target = candidate["targets"][0]["value"]
        boundary = candidate["evidence"]["projection_boundary"]
        if boundary < previous_boundary:
            raise ValueError(f"target stream boundary regression: {parameter_id}")
        if (index % 2 == 0 and target == "0") or (index % 2 == 1 and target != "0"):
            raise ValueError(f"target stream is non-alternating: {parameter_id}")
        previous_boundary = boundary
    if events and events[-1].payload["candidate"]["targets"][0]["value"] != "0":
        raise ValueError(f"target stream is nonflat at discovery end: {parameter_id}")


def build_audit() -> dict[str, Any]:
    source, closed, pairs, projections, metadata = _build_inputs()
    strategy = _strategy_binding()
    parameters = _parameter_bindings(strategy.ref)
    gap_start_ns = _ns(_GAP_START)
    gap_end_ns = _ns(_GAP_END)
    gap_projection_audit = _gap_projection_audit(
        closed,
        projections,
        gap_start_ns,
        gap_end_ns,
        tuple(parameter.parameter_id for parameter in parameters),
    )
    missing_gap_boundaries = gap_projection_audit["missing_projection_boundaries"]
    parameter_results = []
    impacted_parameters = []
    impacted_events = []
    carried_positions = []

    for parameter in parameters:
        events = _stream_events(
            source=source,  # type: ignore[arg-type]
            strategy_ref=strategy.ref,
            parameter=parameter,
            closed=closed,
            pairs=pairs,
            projections=projections,
        )
        _validate_stream(events, parameter.parameter_id)
        candidates = tuple(
            _candidate_wire(event, "entry" if index % 2 == 0 else "exit")
            for index, event in enumerate(events)
        )
        impacted = []
        for candidate in candidates:
            boundary = _ns(candidate["projection_boundary_utc"])
            actual = _ns(candidate["projection_actual_event_time_utc"])
            if max(boundary, gap_start_ns) < min(actual + 1, gap_end_ns):
                row = {
                    "parameter_id": parameter.parameter_id,
                    **candidate,
                    "unresolved_first_trade_search_overlap": {
                        "start_utc_inclusive": _utc(max(boundary, gap_start_ns)),
                        "end_utc_exclusive": _utc(min(actual + 1, gap_end_ns)),
                    },
                }
                impacted.append(row)
                impacted_events.append(row)
        carried = []
        for entry, exit_event in zip(candidates[::2], candidates[1::2], strict=True):
            entry_actual = _ns(entry["projection_actual_event_time_utc"])
            exit_actual = _ns(exit_event["projection_actual_event_time_utc"])
            if entry_actual < gap_start_ns <= exit_actual:
                row = {
                    "parameter_id": parameter.parameter_id,
                    "entry_event_hash": entry["event_hash"],
                    "entry_projection_boundary_utc": entry[
                        "projection_boundary_utc"
                    ],
                    "entry_projection_actual_event_time_utc": entry[
                        "projection_actual_event_time_utc"
                    ],
                    "exit_event_hash": exit_event["event_hash"],
                    "exit_projection_boundary_utc": exit_event[
                        "projection_boundary_utc"
                    ],
                    "exit_projection_actual_event_time_utc": exit_event[
                        "projection_actual_event_time_utc"
                    ],
                    "target": entry["target"],
                }
                carried.append(row)
                carried_positions.append(row)
        status = (
            "impacted" if impacted or carried or missing_gap_boundaries else "clear"
        )
        if status == "impacted":
            impacted_parameters.append(parameter.parameter_id)
        parameter_results.append(
            {
                "parameter_id": parameter.parameter_id,
                "status": status,
                "formation_hours": parameter.formation_hours,
                "max_formation_range": str(parameter.max_formation_range),
                "max_hold_hours": parameter.max_hold_hours,
                "parameter_artifact_ref": parameter.ref.to_canonical_dict(),
                "candidate_event_count": len(candidates),
                "candidate_event_hashes": [row["event_hash"] for row in candidates],
                "candidate_events": list(candidates),
                "impacted_events": impacted,
                "missing_eligible_projection_boundaries": [
                    _utc(boundary) for boundary in missing_gap_boundaries
                ],
                "positions_carried_across_gap_start": carried,
                "alternating": True,
                "flat_at_discovery_end": True,
            }
        )

    base_path = DATA / "manifest.json"
    execution_path = DATA / "execution_data_manifest.json"
    accepted_bundle = metadata["accepted_bundle"]
    projection_hashes = [
        projection.event.event_hash for _, projection in sorted(projections.items())
    ]
    projection_rows = [
        {
            "boundary_utc": _utc(boundary),
            "cutoff_utc": _utc(projection.cutoff_ns),
            "actual_event_time_utc": _utc(
                projection.event.event_time.epoch_nanoseconds
            ),
            "projection_event_id": projection.event.event_id,
            "projection_event_hash": projection.event.event_hash,
            "aggregate_trade_id": projection.event.payload["aggregate_trade_id"],
            "first_trade_id": projection.event.payload["first_trade_id"],
            "last_trade_id": projection.event.payload["last_trade_id"],
            "open_price": dict(projection.event.payload["open_price"]),
            "source_archive_path": projection.event.payload["source_archive_path"],
            "source_archive_sha256": projection.event.payload[
                "source_archive_sha256"
            ],
        }
        for boundary, projection in sorted(projections.items())
    ]
    unresolved_eligible_boundaries = [
        _utc(boundary)
        for boundary, _ in metadata["eligible_boundaries"]
        if boundary not in projections
    ]
    before_gap = max(
        (
            projection
            for projection in projections.values()
            if projection.boundary_ns < gap_start_ns
        ),
        key=lambda projection: projection.boundary_ns,
    )
    after_gap = min(
        (
            projection
            for projection in projections.values()
            if projection.boundary_ns >= gap_end_ns
        ),
        key=lambda projection: projection.boundary_ns,
    )
    result: dict[str, Any] = {
        "type": "koruusdt_execution_gap_impact_audit_v2",
        "schema_version": 2,
        "manifest_sha256": "",
        "instrument": "KORUUSDT",
        "audit_scope": "bounded_advisory_gap_impact",
        "discovery_window": metadata["input_binding"]["window"],
        "missing_aggtrades_interval": {
            "start_utc_inclusive": _GAP_START,
            "end_utc_exclusive": _GAP_END,
            "semantics": "half-open",
        },
        "base_manifest": {
            "path": str(base_path.relative_to(ROOT)),
            "file_sha256": _sha256(base_path),
            "manifest_sha256": metadata["base"]["manifest_sha256"],
        },
        "execution_data_manifest": {
            "path": str(execution_path.relative_to(ROOT)),
            "file_sha256": _sha256(execution_path),
            "manifest_sha256": metadata["execution"]["manifest_sha256"],
        },
        "frozen_target_builder": {
            "path": str(TARGET_BUILDER.relative_to(ROOT)),
            "file_sha256": _sha256(TARGET_BUILDER),
            "backtest_head": _git_head(BACKTEST),
            "imported_symbols": [
                "_stream_events",
                "_parameter_bindings",
                "_strategy_binding",
                "_BarPair",
                "_Projection",
                "_closed_intervals",
            ],
        },
        "strategy_definition_ref": strategy.ref.to_canonical_dict(),
        "accepted_bundle_fixture": {
            "path": (
                "backtest/tests/bundle_builder/providers/binance_usdm/"
                "test_koru_tradifi_execution_bundle_v1.py"
            ),
            "factory": "_empty_result",
            "result_digest": accepted_bundle.result_digest,
        },
        "authority_artifacts": [
            {
                "envelope": {
                    "artifact_type": envelope.artifact_type,
                    "schema_version": envelope.schema_version,
                    "content_hash": envelope.content_hash,
                },
                "ref": ref.to_canonical_dict(),
            }
            for envelope, ref in zip(
                accepted_bundle.authority_artifacts,
                accepted_bundle.authority_refs,
                strict=True,
            )
        ],
        "source_independent_price_events": {
            "mark_csv": {
                "path": "research/koruusdt/data/binance_mark_raw.csv",
                "sha256": metadata["artifacts"]["binance_mark_raw.csv"]["sha256"],
                "event_count": len(metadata["mark_events"]),
                "event_hashes_sha256": canonical_sha256(
                    tuple(
                        event.event_hash
                        for event in metadata["mark_events"].values()
                    )
                ),
            },
            "index_csv": {
                "path": "research/koruusdt/data/binance_index_raw.csv",
                "sha256": metadata["artifacts"]["binance_index_raw.csv"]["sha256"],
                "event_count": len(metadata["index_events"]),
                "event_hashes_sha256": canonical_sha256(
                    tuple(
                        event.event_hash
                        for event in metadata["index_events"].values()
                    )
                ),
            },
            "source_fragment_digest": source.fragment_digest,
        },
        "actual_first_trade_projections": {
            "eligible_boundary_count": len(metadata["eligible_boundaries"]),
            "projection_count": len(projections),
            "event_hashes_sha256": canonical_sha256(tuple(projection_hashes)),
            "unresolved_eligible_boundaries": unresolved_eligible_boundaries,
            "gap_calendar_eligible_boundaries": [
                _utc(boundary)
                for boundary in gap_projection_audit["eligible_boundaries"]
            ],
            "gap_missing_projection_boundaries": [
                _utc(boundary) for boundary in missing_gap_boundaries
            ],
            "nearest_projection_before_gap": {
                "boundary_utc": _utc(before_gap.boundary_ns),
                "actual_event_time_utc": _utc(
                    before_gap.event.event_time.epoch_nanoseconds
                ),
                "cutoff_utc": _utc(before_gap.cutoff_ns),
            },
            "nearest_projection_after_gap": {
                "boundary_utc": _utc(after_gap.boundary_ns),
                "actual_event_time_utc": _utc(
                    after_gap.event.event_time.epoch_nanoseconds
                ),
                "cutoff_utc": _utc(after_gap.cutoff_ns),
            },
            "events": projection_rows,
            "label": "ADVISORY_RECONSTRUCTED_FIRST_RETAINED_AGGTRADE",
            "source_objects_reconstructed": True,
            "advisory_only": True,
            "backtest_evidence": False,
        },
        "parameters": parameter_results,
        "summary": {
            "impacted_parameters": impacted_parameters,
            "impacted_events": impacted_events,
            "missing_eligible_projection_boundaries": [
                _utc(boundary) for boundary in missing_gap_boundaries
            ],
            "parameters_potentially_impacted_by_missing_projection": list(
                gap_projection_audit["potentially_impacted_parameters"]
            ),
            "positions_carried_across_gap_start": carried_positions,
            "clear_parameters": [
                row["parameter_id"]
                for row in parameter_results
                if row["status"] == "clear"
            ],
        },
        "flags": {
            "advisory_only": True,
            "backtest_evidence": False,
            "source_objects_reconstructed": True,
            "captured_aggtrade_values_used": True,
            "decision_grade_eligible": False,
            "deployment_authorized": False,
        },
    }
    result["manifest_sha256"] = _manifest_sha256(result)
    return result


def _git_head(path: Path) -> str:
    head = (path / ".git").read_text(encoding="utf-8").strip()
    if head.startswith("gitdir: "):
        git_dir = (path / head.removeprefix("gitdir: ")).resolve()
        ref = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
        if ref.startswith("ref: "):
            return (git_dir / ref.removeprefix("ref: ")).read_text(
                encoding="utf-8"
            ).strip()
        return ref
    raise ValueError("backtest submodule gitdir is not available")


def write_audit(path: Path = OUTPUT) -> dict[str, Any]:
    result = build_audit()
    path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    result = write_audit()
    summary = result["summary"]
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    print("impacted parameters:", summary["impacted_parameters"])
    print("impacted events:", len(summary["impacted_events"]))
    print(
        "positions carried across gap start:",
        len(summary["positions_carried_across_gap_start"]),
    )


if __name__ == "__main__":
    main()
