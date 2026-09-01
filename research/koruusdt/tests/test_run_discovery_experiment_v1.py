from __future__ import annotations

import ast
import importlib.util
import json
import socket
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BACKTEST = ROOT / "backtest"
sys.path.insert(0, str(BACKTEST))
SCRIPT = Path(__file__).resolve().parents[1] / "run_discovery_experiment_v1.py"
SPEC = importlib.util.spec_from_file_location("run_discovery_experiment_v1", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)

import crypto_quant_backtest as backtest  # noqa: E402
from crypto_quant_bundle_builder import (  # noqa: E402
    LocalMarketBundleRepository,
    LocalMarketBundleRepositoryConfig,
)
from crypto_quant_domain import (  # noqa: E402
    ArtifactEnvelope,
    ArtifactRef,
    Money,
    Scale,
    canonical_bytes,
    canonical_sha256,
)
from crypto_quant_foundation import LocalFoundation  # noqa: E402
from crypto_quant_market_data import LocalMarketBundleReader  # noqa: E402
from crypto_quant_research import (  # noqa: E402
    DeferredTrialExecution,
    FrozenExperimentInputs,
    IntegratedDataSlice,
    IntegratedExperimentSpec,
    IntegratedHardFilter,
    IntegratedOrderingCriterion,
    IntegratedParameterCombination,
    IntegratedSelectionPolicy,
    PublishedStrategyCandidate,
    build_integrated_trial_declarations,
)
from crypto_quant_validation import SampleConsumptionLedger  # noqa: E402
from tests.runtime.providers import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    test_binance_usdm_tradifi_preparation_v2 as fixture,
)
from tests.runtime.resolution import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    _fixtures as resolution_fixture,
)


def _artifact_ref(artifact_type: str, marker: str) -> dict[str, object]:
    return {
        "type": "artifact_ref",
        "artifact_type": artifact_type,
        "schema_version": 1,
        "content_hash": "sha256:" + marker * 64,
    }


def test_frozen_declarations_exact_cover_eight_without_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runner.retained,
        "build_manifest",
        lambda **_: (_ for _ in ()).throw(
            AssertionError("declarations must not do I/O")
        ),
    )

    inputs = runner.frozen_inputs()
    declarations = build_integrated_trial_declarations(inputs.experiment_spec)

    assert len(declarations) == 8
    assert inputs.experiment_spec.seeds == (0,)
    assert inputs.experiment_spec.budget == {"max_trials": 8}
    assert len(inputs.experiment_spec.data_slices) == 1
    data_slice = inputs.experiment_spec.data_slices[0]
    assert (data_slice.interval_start, data_slice.interval_end) == (
        "2026-07-15T10:00:00.000000Z",
        "2026-08-24T11:00:00.000000Z",
    )
    assert {item.request_spec["intent_key"] for item in inputs.trial_executions} == {
        f"p{index:02d}" for index in range(1, 9)
    }
    assert {item.trial_declaration_ref for item in inputs.trial_executions} == {
        item.ref for item in declarations
    }


def test_frozen_selection_policy_is_exact() -> None:
    policy = runner.frozen_selection_policy()

    assert policy.eligible_trial_statuses == ("COMPLETED",)
    assert policy.accepted_backtest_grades == ("development",)
    assert [
        (item.field_name, item.operator, item.threshold) for item in policy.hard_filters
    ] == [
        ("trade_count", "gte", 8),
        ("simple_period_return", "gt", "0"),
    ]
    assert [(item.field_name, item.direction) for item in policy.ordering] == [
        ("simple_period_return", "descending"),
        ("trade_count", "descending"),
    ]
    assert policy.max_selections == 1
    assert policy.tie_break == "trial_declaration_ref_ascending"


def test_production_script_imports_only_public_package_roots() -> None:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"), filename=str(SCRIPT))
    modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    modules.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    crypto_imports = {name for name in modules if name.startswith("crypto_quant")}

    assert crypto_imports <= {
        "crypto_quant_backtest",
        "crypto_quant_bundle_builder",
        "crypto_quant_domain",
        "crypto_quant_foundation",
        "crypto_quant_market_data",
        "crypto_quant_research",
        "crypto_quant_validation",
    }
    assert "run_discovery_backtests_v1" not in modules


def test_owner_log_reader_rejects_entry_without_cas_artifact(tmp_path: Path) -> None:
    foundation = LocalFoundation(tmp_path / "foundation")
    envelope = ArtifactEnvelope.create("task_outcome", 1, {"state": "COMPLETED"})
    ref = ArtifactRef.from_envelope(envelope)
    foundation.append(
        runner.EXECUTION_LOG,
        canonical_sha256(("artifact-publication-v1", runner.EXECUTION_LOG, ref)),
        canonical_bytes(envelope),
    )

    with pytest.raises(ValueError, match="invalid public artifact entry"):
        runner._published_payloads(foundation, runner.EXECUTION_LOG)


def test_clean_worktree_gate_rejects_renamed_managed_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def git(repo: Path, *args: str) -> str:
        if repo == runner.ROOT and args[:2] == ("status", "--porcelain"):
            return "R  research/koruusdt/data/discovery_experiment_v1.json -> outside.json"
        return ""

    monkeypatch.setattr(runner, "_git", git)

    with pytest.raises(ValueError, match="unmanaged changes"):
        runner._verify_clean_worktrees()


def test_persistent_state_replays_compatible_and_rejects_unmanaged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    formal_root = tmp_path / "formal"
    monkeypatch.setattr(runner, "FORMAL_ROOT", formal_root)
    monkeypatch.setattr(runner, "OUTPUT", tmp_path / "summary.json")
    monkeypatch.setattr(runner, "STATE_IDENTITY", formal_root / "state_identity.json")

    runner._prepare_state()
    runner._prepare_state()
    (formal_root / "foreign.txt").write_text("incompatible\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unmanaged state"):
        runner._prepare_state()


def test_validate_only_rejects_fabricated_summary_without_owner_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    formal_root = tmp_path / "formal"
    output = tmp_path / "summary.json"
    state_identity = formal_root / "state_identity.json"
    monkeypatch.setattr(runner, "FORMAL_ROOT", formal_root)
    monkeypatch.setattr(runner, "OUTPUT", output)
    monkeypatch.setattr(runner, "STATE_IDENTITY", state_identity)
    monkeypatch.setattr(runner, "_verify_pins", lambda: None)
    monkeypatch.setattr(
        runner.retained,
        "build_manifest",
        lambda **_: (_ for _ in ()).throw(
            AssertionError("validate-only must not reconstruct or run economics")
        ),
    )

    runner._write_canonical(state_identity, runner._state_value())
    (formal_root / "evidence.txt").write_text("public evidence\n", encoding="utf-8")
    evidence_hash, evidence_count = runner._evidence_tree()
    inputs = runner.frozen_inputs()
    result_ref = _artifact_ref("candidate_family", "5")
    runner._write_canonical(
        output,
        {
            "type": "koruusdt_discovery_experiment_v1",
            "schema_version": 1,
            "experiment_ref": inputs.experiment_spec.ref,
            "selection_policy_ref": inputs.selection_policy.ref,
            "selection": {
                "type": "discovery_no_selection",
                "no_selection_ref": result_ref,
                "reason_code": "discovery_no_selection",
                "candidate_family_ref": result_ref,
                "execution_manifest_ref": _artifact_ref(
                    "experiment_execution_manifest", "6"
                ),
                "manifest_cutoff": {
                    "log_name": runner.EXECUTION_LOG,
                    "log_sequence": 1,
                    "receipt_hash": "sha256:" + "7" * 64,
                },
            },
            "owner_log_checkpoints": {
                log_name: {
                    "log_name": log_name,
                    "as_of": "2026-08-26T12:00:01.000000Z",
                    "upper_log_sequence": 1,
                    "head_receipt_hash": "sha256:" + "8" * 64,
                }
                for log_name in runner.OWNER_LOGS
            },
            "task_outcomes": {"count": 16, "states": {"COMPLETED": 16}},
            "completed_publication_refs": [],
            "analysis_refs": [],
            "sample_ledger": {
                "record_count": 2,
                "purpose_counts": {"discovery": 1, "selection": 1},
                "dataset_revisions": [runner.DATASET_REVISION],
                "intervals": [[runner.DISCOVERY_START, runner.DISCOVERY_END]],
            },
            "commits": runner._commits(),
            "retained_hashes": runner._retained_hashes(),
            "replay_verified": True,
            "network_performed": False,
            "holdout_touched": False,
            "evidence": {
                "root": "research/koruusdt/data/formal_discovery_v1",
                "file_count": evidence_count,
                "tree_sha256": evidence_hash,
            },
            "manifest_sha256": "",
        },
    )

    with pytest.raises(SystemExit, match="owner-log checkpoints"):
        runner.main(["--validate-only"])


def test_one_trial_tiny_public_execute_and_replay_sentinel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def reject_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("tiny sentinel must stay offline")

    monkeypatch.setattr(socket, "create_connection", reject_network)
    monkeypatch.setattr(socket.socket, "connect", reject_network)
    bundle = fixture._nonempty_bundle()
    foundation = LocalFoundation(
        tmp_path / "foundation", clock=lambda: "2026-08-18T00:00:01.000000Z"
    )
    for envelope in (*bundle.target_result.artifacts, *bundle.authority_artifacts):
        foundation.put(envelope=envelope)
    metric_ref = backtest.BacktestAnalysisRuntime(foundation).publish_metric_profile()
    publication = LocalMarketBundleRepository(
        config=LocalMarketBundleRepositoryConfig(root=tmp_path / "market")
    ).publish_market_bundle_v1(
        manifest=bundle.reader.manifest,
        stream_payloads={
            key: canonical_bytes(events)
            for key, events in bundle.reader.streams.items()
        },
        retention_policy_ref="retention.koru-discovery-smoke.v1",
    )
    assert publication.result is not None
    market_reader = LocalMarketBundleReader.open(
        repository_root=(tmp_path / "market").resolve(),
        bundle_ref=publication.result.bundle_ref,
    )
    operations = backtest.BinanceUsdmTradifiBacktestOperations(
        intent_templates={
            "p01": replace(fixture._intent(bundle), experiment_id=None),
        },
        provider_inputs=backtest.BinanceUsdmTradifiProviderInputs(
            resolution_fixture.build_manifest(),
            Money(1_000_000_000_000, Scale(8), "USDT"),
        ),
        artifact_reader=foundation,
        artifact_publisher=foundation,
        market_reader=market_reader,
        publication_root=tmp_path / "publications",
    )
    spec = IntegratedExperimentSpec(
        hypothesis_ref=_artifact_ref("hypothesis", "1"),
        strategy_definition_ref=json.loads(
            canonical_bytes(bundle.target_result.strategy.ref)
        ),
        data_slices=(
            IntegratedDataSlice(
                json.loads(canonical_bytes(bundle.reader.bundle_ref)),
                "koru-tiny-replay-sentinel",
                "2026-07-18T00:00:00.000000Z",
                "2026-07-18T12:00:00.000000Z",
            ),
        ),
        parameter_combinations=(
            IntegratedParameterCombination((("intent_key", "p01"),)),
        ),
        seeds=(0,),
        scenario_refs=(_artifact_ref("scenario", "2"),),
        backtest_template_ref=_artifact_ref("backtest_template", "3"),
        model_build_plan=None,
        metric_profile_refs=(json.loads(canonical_bytes(metric_ref)),),
        budget={"max_trials": 1},
    )
    trial = build_integrated_trial_declarations(spec)[0]
    policy = IntegratedSelectionPolicy(
        metric_profile_ref=spec.metric_profile_refs[0],
        eligible_trial_statuses=("COMPLETED",),
        accepted_backtest_grades=("development",),
        hard_filters=(IntegratedHardFilter("trade_count", "gte", 1),),
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
        _artifact_ref("actor", "4"),
        (DeferredTrialExecution(trial.ref, {"intent_key": "p01"}),),
        "2026-08-18T00:00:00.000000Z",
    )

    result, counts = runner.execute_with_replay(
        inputs,
        foundation,
        SampleConsumptionLedger(foundation),
        operations,
        tmp_path / "publications",
    )

    assert type(result) is PublishedStrategyCandidate
    assert counts == (1, 1, 1)
    assert len(foundation.entries("validation.sample-consumption.v1")) == 2
    summary = {"selection": runner._result_summary(result)}
    runner._validate_selection_evidence(summary, foundation)
    tampered = json.loads(json.dumps(summary))
    tampered["selection"]["selection_result_ref"]["content_hash"] = (  # type: ignore[index]
        "sha256:" + "f" * 64
    )
    with pytest.raises(ValueError, match="selected result ref"):
        runner._validate_selection_evidence(tampered, foundation)
