from __future__ import annotations

import ast
import json
import socket
from dataclasses import replace
from pathlib import Path
from typing import Any

import crypto_quant_backtest as backtest
import pytest
from crypto_quant_bundle_builder import (
    LocalMarketBundleRepository,
    LocalMarketBundleRepositoryConfig,
)
from crypto_quant_domain import Money, Scale, canonical_bytes
from crypto_quant_foundation import LocalFoundation
from crypto_quant_market_data import LocalMarketBundleReader
from crypto_quant_research import (
    DeferredTrialExecution,
    FrozenExperimentInputs,
    IntegratedDataSlice,
    IntegratedExperimentSpec,
    IntegratedHardFilter,
    IntegratedOrderingCriterion,
    IntegratedParameterCombination,
    IntegratedSelectionPolicy,
    PublishedNoSelection,
    PublishedStrategyCandidate,
    build_integrated_trial_declarations,
    execute_experiment,
)
from crypto_quant_validation import SampleConsumptionLedger

_ROOT = Path(__file__).resolve().parents[2]

# The immutable BundleV2 fixture lives with the Backtest candidate that owns it.
import tests  # noqa: E402

tests.__path__.append(str(_ROOT / "backtest/tests"))
from tests.runtime.providers import (  # noqa: E402
    test_binance_usdm_tradifi_preparation_v2 as tradifi_fixture,
)
from tests.runtime.resolution import _fixtures as resolution_fixture  # noqa: E402

_SAMPLE_LOG = "validation.sample-consumption.v1"
_ARTIFACT_LOG = "research.artifacts.v1"
_EXECUTION_LOG = "research.execution.v1"
_RESERVED_AT = "2026-08-18T00:00:00.000000Z"
_RECEIVED_AT = "2026-08-18T00:00:01.000000Z"


def _plain(value: object) -> dict[str, object]:
    decoded = json.loads(canonical_bytes(value))
    assert type(decoded) is dict
    return decoded


def _artifact_ref(artifact_type: str, marker: str) -> dict[str, object]:
    return {
        "type": "artifact_ref",
        "artifact_type": artifact_type,
        "schema_version": 1,
        "content_hash": "sha256:" + marker * 64,
    }


@pytest.fixture(scope="module")
def koru_bundle_v2():
    bundle = tradifi_fixture._nonempty_bundle()
    assert bundle.manifest.schema_version == 2
    template = replace(tradifi_fixture._intent(bundle), experiment_id=None)
    provider_inputs = backtest.BinanceUsdmTradifiProviderInputs(
        resolution_fixture.build_manifest(),
        Money(1_000_000_000_000, Scale(8), "USDT"),
    )
    return bundle, template, provider_inputs


def _case(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fixture: Any,
    *,
    minimum_trades: int,
    intent_key: str = "koru-v2",
):
    def reject_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("public KORU Research execution must not use the network")

    monkeypatch.setattr(socket, "create_connection", reject_network)
    monkeypatch.setattr(socket.socket, "connect", reject_network)

    bundle, template, provider_inputs = fixture
    foundation = LocalFoundation(tmp_path / "foundation", clock=lambda: _RECEIVED_AT)
    for envelope in (*bundle.target_result.artifacts, *bundle.authority_artifacts):
        foundation.put(envelope=envelope)

    profile_ref = backtest.BacktestAnalysisRuntime(
        foundation
    ).publish_metric_profile()
    published = LocalMarketBundleRepository(
        config=LocalMarketBundleRepositoryConfig(root=tmp_path / "market")
    ).publish_market_bundle_v1(
        manifest=bundle.reader.manifest,
        stream_payloads={
            key: canonical_bytes(events)
            for key, events in bundle.reader.streams.items()
        },
        retention_policy_ref="retention.koru-public-execution.v1",
    )
    assert published.result is not None
    market_reader = LocalMarketBundleReader.open(
        repository_root=(tmp_path / "market").resolve(),
        bundle_ref=published.result.bundle_ref,
    )
    operations = backtest.BinanceUsdmTradifiBacktestOperations(
        intent_templates={"koru-v2": template},
        provider_inputs=provider_inputs,
        artifact_reader=foundation,
        artifact_publisher=foundation,
        market_reader=market_reader,
        publication_root=tmp_path / "publications",
    )
    spec = IntegratedExperimentSpec(
        hypothesis_ref=_artifact_ref("hypothesis", "1"),
        strategy_definition_ref=_plain(bundle.target_result.strategy.ref),
        data_slices=(
            IntegratedDataSlice(
                _plain(bundle.reader.bundle_ref),
                "koru-bundle-v2-development",
                "2026-07-18T00:00:00.000000Z",
                "2026-07-18T12:00:00.000000Z",
            ),
        ),
        parameter_combinations=(
            IntegratedParameterCombination((("intent_key", intent_key),)),
        ),
        seeds=(0,),
        scenario_refs=(_artifact_ref("scenario", "2"),),
        backtest_template_ref=_artifact_ref("backtest_template", "3"),
        model_build_plan=None,
        metric_profile_refs=(_plain(profile_ref),),
        budget={"max_trials": 1},
    )
    trial = build_integrated_trial_declarations(spec)[0]
    policy = IntegratedSelectionPolicy(
        metric_profile_ref=spec.metric_profile_refs[0],
        eligible_trial_statuses=("COMPLETED",),
        accepted_backtest_grades=("development",),
        hard_filters=(
            IntegratedHardFilter("trade_count", "gte", minimum_trades),
        ),
        ordering=(
            IntegratedOrderingCriterion("simple_period_return", "descending"),
            IntegratedOrderingCriterion("trade_count", "descending"),
        ),
        max_selections=1,
        tie_break="trial_declaration_ref_ascending",
    )
    inputs = FrozenExperimentInputs(
        spec,
        policy,
        {"type": "actor_ref", "actor_id": "koru-public-integration"},
        (DeferredTrialExecution(trial.ref, {"intent_key": intent_key}),),
        _RESERVED_AT,
    )
    ledger = SampleConsumptionLedger(foundation)
    counters = {"prepare": 0, "run_prepared": 0, "derive": 0}
    observations: list[tuple[str, int]] = []
    request_refs: list[dict[str, object]] = []
    prepare = operations.prepare
    run_prepared = operations.run_prepared
    derive = operations.derive

    def counted_prepare(request_spec: object, experiment_id: str):
        counters["prepare"] += 1
        observations.append(("prepare", len(foundation.entries(_SAMPLE_LOG))))
        prepared = prepare(request_spec, experiment_id)  # type: ignore[arg-type]
        request_refs.append(prepared.backtest_request_ref)
        return prepared

    def counted_run_prepared(prepared: object):
        counters["run_prepared"] += 1
        observations.append(("run_prepared", len(foundation.entries(_SAMPLE_LOG))))
        return run_prepared(prepared)  # type: ignore[arg-type]

    def counted_derive(completed_ref: object, metric_profile_ref: object):
        counters["derive"] += 1
        return derive(completed_ref, metric_profile_ref)  # type: ignore[arg-type]

    monkeypatch.setattr(operations, "prepare", counted_prepare)
    monkeypatch.setattr(operations, "run_prepared", counted_run_prepared)
    monkeypatch.setattr(operations, "derive", counted_derive)
    return foundation, ledger, operations, inputs, counters, observations, request_refs


def _envelopes(foundation: LocalFoundation, log_name: str) -> list[dict[str, Any]]:
    return [json.loads(entry.payload) for entry in foundation.entries(log_name)]


@pytest.mark.parametrize(
    ("minimum_trades", "result_type"),
    ((1, PublishedStrategyCandidate), (999, PublishedNoSelection)),
)
def test_public_koru_bundle_v2_experiment_is_durable_and_policy_selected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    koru_bundle_v2: Any,
    minimum_trades: int,
    result_type: type,
) -> None:
    (
        foundation,
        ledger,
        operations,
        inputs,
        counters,
        observations,
        request_refs,
    ) = _case(
        tmp_path,
        monkeypatch,
        koru_bundle_v2,
        minimum_trades=minimum_trades,
    )

    first = execute_experiment(inputs, foundation, ledger, operations)
    attempts = tuple((tmp_path / "publications").rglob("attempt-execution-record.json"))
    second = execute_experiment(inputs, foundation, ledger, operations)

    assert type(first) is result_type
    assert second == first
    assert counters == {"prepare": 1, "run_prepared": 1, "derive": 1}
    assert observations == [("prepare", 1), ("run_prepared", 1)]
    assert attempts
    assert (
        tuple((tmp_path / "publications").rglob("attempt-execution-record.json"))
        == attempts
    )

    sample_records = [
        envelope["payload"]["record"]
        for envelope in _envelopes(foundation, _SAMPLE_LOG)
    ]
    assert [record["purpose"] for record in sample_records] == [
        "discovery",
        "selection",
    ]
    assert "holdout" not in json.dumps(sample_records)

    artifacts = _envelopes(foundation, _ARTIFACT_LOG)
    trial_specs = [
        envelope["payload"]
        for envelope in artifacts
        if envelope["artifact_type"] == "backtest_trial_spec"
    ]
    assert len(trial_specs) == 1
    assert trial_specs[0]["backtest_request_ref"] == request_refs[0]

    outcomes = [
        envelope["payload"]
        for envelope in _envelopes(foundation, _EXECUTION_LOG)
        if envelope["artifact_type"] == "task_outcome"
    ]
    assert [outcome["state"] for outcome in outcomes] == ["COMPLETED", "COMPLETED"]
    completed_ref = outcomes[0]["witness"]["trial_completed_publication"][
        "publication_ref"
    ]
    completed = operations.load_completed(completed_ref)
    assert completed["result_grade"] == "development"
    assert completed["execution_result_hash"].startswith("sha256:")

    analysis_ref = outcomes[1]["witness"]["analysis_derivation"]["analysis_ref"]
    analysis = operations.load_analysis(analysis_ref)
    assert analysis["simple_period_return"] is not None
    assert analysis["trade_count"] >= 1

    candidates = [
        envelope
        for envelope in artifacts
        if envelope["artifact_type"] == "strategy_candidate"
    ]
    assert bool(candidates) is (result_type is PublishedStrategyCandidate)


def test_public_preparation_failure_maps_to_local_failure_without_trial_spec(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    koru_bundle_v2: Any,
) -> None:
    foundation, ledger, operations, inputs, counters, _, _ = _case(
        tmp_path,
        monkeypatch,
        koru_bundle_v2,
        minimum_trades=1,
        intent_key="missing",
    )

    result = execute_experiment(inputs, foundation, ledger, operations)

    assert type(result) is PublishedNoSelection
    assert counters == {"prepare": 1, "run_prepared": 0, "derive": 0}
    assert not any(
        envelope["artifact_type"] == "backtest_trial_spec"
        for envelope in _envelopes(foundation, _ARTIFACT_LOG)
    )
    outcomes = [
        envelope["payload"]
        for envelope in _envelopes(foundation, _EXECUTION_LOG)
        if envelope["artifact_type"] == "task_outcome"
    ]
    assert outcomes[0]["state"] == "FAILED"
    assert outcomes[0]["witness"] == {
        "local_failure": {"failure_code": "BACKTEST_OPERATION_FAILED"}
    }
    assert outcomes[1]["state"] == "BLOCKED"


def test_public_execution_import_guard() -> None:
    paths = (
        Path(__file__),
        _ROOT / "research-platform/src/crypto_quant_research/runtime.py",
    )
    allowed_roots = {
        "crypto_quant_backtest",
        "crypto_quant_bundle_builder",
        "crypto_quant_domain",
        "crypto_quant_foundation",
        "crypto_quant_market_data",
        "crypto_quant_research",
        "crypto_quant_validation",
    }
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = [
            (node.module, tuple(alias.name for alias in node.names))
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        ]
        imports.extend(
            (alias.name, ())
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        crypto_imports = {
            module for module, _ in imports if module.startswith("crypto_quant")
        }
        assert crypto_imports <= allowed_roots
        assert not any(
            name == "Engine" or name.startswith("Engine")
            for module, names in imports
            if module == "crypto_quant_backtest"
            for name in names
        )
        assert "crypto_quant_research.integration" not in crypto_imports
        assert "crypto_quant_research.runtime" not in crypto_imports
