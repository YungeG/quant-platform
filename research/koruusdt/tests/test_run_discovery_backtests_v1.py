from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BACKTEST = ROOT / "backtest"
sys.path.insert(0, str(BACKTEST))
SCRIPT = Path(__file__).resolve().parents[1] / "run_discovery_backtests_v1.py"
SPEC = importlib.util.spec_from_file_location("run_discovery_backtests_v1", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)

from crypto_quant_domain import canonical_bytes  # noqa: E402
from tests.runtime.providers import (  # noqa: E402
    test_binance_usdm_tradifi_preparation_v2 as fixture,
)


def _context(bundle) -> object:
    return runner._PublicExecutionContext(
        bundle=bundle,
        strategy_definition_ref=bundle.target_result.strategy.ref,
        parameter_refs=tuple(value.ref for value in bundle.target_result.parameters),
        artifact_reader=fixture._Store(bundle),
        build_artifact_manifest=fixture.build_manifest(),
    )


def test_p01_tiny_bundle_smoke_reaches_schema7_engine_summary_and_selection() -> None:
    context = _context(fixture._nonempty_bundle())

    first = runner._run_trial(context, "p01", emit=lambda *args, **kwargs: None)
    second = runner._run_trial(context, "p01", emit=lambda *args, **kwargs: None)

    assert first == second
    assert first["status"] == "completed"
    assert first["execution_input_ref"]["schema_version"] == 8
    assert first["fill_count"] == 2
    assert first["fill_times_epoch_nanoseconds"] == [
        1_784_347_500_000_000_000,
        1_784_354_700_000_000_000,
    ]
    assert first["fill_liquidity_roles"] == ["taker", "taker"]
    assert first["final_position_count"] == 0
    assert first["fees_usdt"] != "0"
    assert "funding_usdt" in first
    assert first["funding_accounting_count"] == 1
    assert first["liquidation_audit_count"] == 3
    assert first["margin_projection_count"] == 3

    report = runner._build_results(
        context,
        ("p01",),
        retained_metadata={},
        emit=lambda *args, **kwargs: None,
    )
    assert report["report_scope"] == "bounded_local_backtest_execution_report"
    assert report["public_research_execute_experiment_published"] is False
    assert report["selected_parameter_ids"] == []
    assert report["selection_status"] == "discovery_no_selection"


def test_broken_preparation_is_failed_and_blocks_report_publication() -> None:
    bundle = fixture._nonempty_bundle()
    payload = json.loads(canonical_bytes(bundle.account_authority_event.payload))
    payload["account_id"] = "other-account"
    broken = fixture._with_events(
        bundle,
        replace(bundle.account_authority_event, payload=payload),
    )
    context = runner._PublicExecutionContext(
        bundle=broken,
        strategy_definition_ref=bundle.target_result.strategy.ref,
        parameter_refs=tuple(value.ref for value in bundle.target_result.parameters),
        artifact_reader=fixture._Store(bundle),
        build_artifact_manifest=fixture.build_manifest(),
    )

    emitted: list[str] = []

    def emit(message: str, **_: object) -> None:
        emitted.append(message)

    trial = runner._run_trial(context, "p01", emit=emit)

    assert trial["status"] == "failed"
    assert trial["failure"]["code"] == "preparation_authority_invalid"
    assert "fill_count" not in trial
    assert emitted[-1] == (
        "stage: p01 preparation failed: "
        "preparation_authority_invalid:account_event_contract"
    )
    with pytest.raises(
        RuntimeError, match="no authoritative output will be written: p01"
    ):
        runner._build_results(
            context,
            ("p01",),
            retained_metadata={},
            emit=lambda *args, **kwargs: None,
        )


def test_validate_only_checks_existing_output_without_economic_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "discovery_backtests_v1.json"
    output.write_bytes(
        runner.retained.manifest_bytes(
            {
                "type": "koruusdt_discovery_backtests_v1",
                "schema_version": 1,
                "trial_count": 1,
                "manifest_sha256": "",
            }
        )
    )
    monkeypatch.setattr(runner, "OUTPUT", output)
    monkeypatch.setattr(
        runner,
        "build_results",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("validate-only must not execute Backtest")
        ),
    )

    assert runner.main(["--validate-only"]) == 0


def test_validate_only_fails_fast_when_output_is_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runner, "OUTPUT", tmp_path / "missing.json")
    monkeypatch.setattr(
        runner,
        "build_results",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("validate-only must not execute Backtest")
        ),
    )

    with pytest.raises(SystemExit, match="output is absent"):
        runner.main(["--validate-only"])
