from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE_DIR = ROOT / "research/koruusdt"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import pytest

import audit_execution_gap as audit


def test_audit_reuses_frozen_builder_and_finds_no_gap_impact() -> None:
    result = audit.build_audit()

    assert audit._stream_events.__module__.endswith(
        "binance_usdm_koru_closed_market_range_targets_v1"
    )
    assert result["summary"] == {
        "impacted_parameters": [],
        "impacted_events": [],
        "missing_eligible_projection_boundaries": [],
        "parameters_potentially_impacted_by_missing_projection": [],
        "positions_carried_across_gap_start": [],
        "clear_parameters": [f"p{index:02d}" for index in range(1, 9)],
    }
    assert [row["candidate_event_count"] for row in result["parameters"]] == [
        8,
        8,
        12,
        12,
        6,
        6,
        12,
        12,
    ]
    assert all(
        row["status"] == "clear"
        and row["alternating"]
        and row["flat_at_discovery_end"]
        for row in result["parameters"]
    )


def test_projections_use_actual_archive_bound_first_trades() -> None:
    _, _, _, projections, _ = audit._build_inputs()

    assert projections
    assert all(
        projection.boundary_ns <= projection.event.event_time.epoch_nanoseconds
        < projection.cutoff_ns
        and projection.event.available_time == projection.event.event_time
        and projection.event.payload["label"]
        == "ADVISORY_RECONSTRUCTED_FIRST_RETAINED_AGGTRADE"
        and projection.event.payload["actual_captured_aggtrade"] is True
        and projection.event.payload["source_object_reconstructed"] is True
        and projection.event.payload["backtest_evidence"] is False
        and projection.event.payload["aggregate_trade_id"] > 0
        and projection.event.payload["first_trade_id"] > 0
        and projection.event.payload["last_trade_id"]
        >= projection.event.payload["first_trade_id"]
        and projection.event.payload["open_price"]["units"] > 0
        for projection in projections.values()
    )
    result = audit.build_audit()
    inventory = result["actual_first_trade_projections"]
    assert inventory["eligible_boundary_count"] == inventory["projection_count"]
    assert inventory["unresolved_eligible_boundaries"] == []
    assert inventory["gap_calendar_eligible_boundaries"] == []


def test_shifting_captured_first_trade_changes_candidate_audit_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = audit.build_audit()
    source, closed, pairs, projections, metadata = audit._build_inputs()
    boundary = audit._ns(
        baseline["parameters"][0]["candidate_events"][0]["projection_boundary_utc"]
    )
    projection = projections[boundary]
    shifted_time = audit.UtcInstant(
        projection.event.event_time.epoch_nanoseconds + 1_000_000
    )
    shifted_event = replace(
        projection.event,
        event_time=shifted_time,
        available_time=shifted_time,
    )
    shifted_projections = dict(projections)
    shifted_projections[boundary] = audit._Projection(
        projection.boundary_ns,
        projection.cutoff_ns,
        shifted_event,
    )
    monkeypatch.setattr(
        audit,
        "_build_inputs",
        lambda: (source, closed, pairs, shifted_projections, metadata),
    )

    shifted = audit.build_audit()

    assert shifted["parameters"][0]["candidate_event_hashes"] != baseline[
        "parameters"
    ][0]["candidate_event_hashes"]
    assert shifted["manifest_sha256"] != baseline["manifest_sha256"]


def test_synthetic_missing_eligible_boundary_impacts_every_parameter() -> None:
    result = audit._gap_projection_audit(
        ((0, 3 * audit._HOUR_NS),),
        {0: None},  # type: ignore[dict-item]
        0,
        2 * audit._HOUR_NS,
        ("p01", "p02"),
    )

    assert result == {
        "eligible_boundaries": (0, audit._HOUR_NS),
        "missing_projection_boundaries": (audit._HOUR_NS,),
        "potentially_impacted_parameters": ("p01", "p02"),
    }


def test_nonflat_and_non_alternating_streams_fail_closed() -> None:
    source, closed, pairs, projections, _ = audit._build_inputs()
    strategy = audit._strategy_binding()
    parameter = audit._parameter_bindings(strategy.ref)[0]
    events = audit._stream_events(
        source=source,
        strategy_ref=strategy.ref,
        parameter=parameter,
        closed=closed,
        pairs=pairs,
        projections=projections,
    )

    with pytest.raises(ValueError, match="nonflat"):
        audit._validate_stream(events[:1], parameter.parameter_id)
    with pytest.raises(ValueError, match="non-alternating"):
        audit._validate_stream((events[0], events[0]), parameter.parameter_id)


def test_checked_output_is_canonical_reproduction() -> None:
    expected = audit.build_audit()
    actual = json.loads(audit.OUTPUT.read_bytes())

    assert actual == expected
    assert actual["manifest_sha256"] == audit._manifest_sha256(actual)
