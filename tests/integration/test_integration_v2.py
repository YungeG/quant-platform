from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import crypto_quant_backtest as backtest
from crypto_quant_domain import ArtifactRef

_ROOT = Path(__file__).resolve().parents[2]
_PROMOTION_PATH = _ROOT / "promotion-gate/tests/test_integrated_promotion.py"
_PROMOTION_SPEC = importlib.util.spec_from_file_location(
    "platform_integrated_promotion_v2", _PROMOTION_PATH
)
assert _PROMOTION_SPEC is not None and _PROMOTION_SPEC.loader is not None
_PROMOTION = importlib.util.module_from_spec(_PROMOTION_SPEC)
sys.modules[_PROMOTION_SPEC.name] = _PROMOTION
_PROMOTION_SPEC.loader.exec_module(_PROMOTION)
_VALIDATION = _PROMOTION._VALIDATION
_RESEARCH = _VALIDATION._RESEARCH


def _ref(value: dict[str, object]) -> ArtifactRef:
    return ArtifactRef(
        value["artifact_type"],  # type: ignore[arg-type]
        value["schema_version"],  # type: ignore[arg-type]
        value["content_hash"],  # type: ignore[arg-type]
    )


def _payload(foundation, ref: ArtifactRef) -> dict[str, object]:
    return json.loads(foundation.read(ref=ref).source_bytes)["payload"]


def test_integration_v2_whole_platform_golden_replays_one_model_lineage(
    tmp_path: Path,
) -> None:
    foundation, ledger, builder, provider, inputs, artifact = _RESEARCH._model_runtime(
        tmp_path / "research"
    )

    candidate = _RESEARCH.execute_model_experiment(
        inputs, foundation, ledger, builder, provider
    )
    candidate_replay = _RESEARCH.execute_model_experiment(
        inputs, foundation, ledger, builder, provider
    )
    candidate_payload = _payload(foundation, candidate.strategy_candidate_ref)
    profile_ref = _VALIDATION._plain(
        inputs.experiment_spec.metric_profile_refs[0]
    )
    validation_policy = _VALIDATION._policy(profile_ref)
    prepared = backtest.prepare_model_bound_cash_development_backtest(
        request_intent=_RESEARCH._BINDING_MODULE._intent("validation:oos:model"),
        provider_inputs=_RESEARCH._BINDING_MODULE._provider_inputs(),
        model_timeline=provider._timeline,
        expected_model_key=artifact.model_key,
        expected_artifact_ref_hash=artifact.artifact_ref_hash,
        artifact_reader=foundation,
        artifact_publisher=foundation,
        market_reader=_RESEARCH._BINDING_MODULE._market_reader(),
        publication_root=tmp_path / "research/publications",
    )
    provider._prepared["validation:oos:model"] = prepared

    validation = _VALIDATION.validate_candidate(
        candidate.strategy_candidate_ref,
        validation_policy,
        {"binding_key": "validation:oos:model"},
        _VALIDATION._RESERVED_AT,
        foundation,
        ledger,
        provider,
    )
    validation_replay = _VALIDATION.validate_candidate(
        candidate.strategy_candidate_ref,
        validation_policy,
        {"binding_key": "validation:oos:model"},
        _VALIDATION._RESERVED_AT,
        foundation,
        ledger,
        provider,
    )
    report = _payload(foundation, validation.validation_report_ref)
    plan_ref = _ref(report["validation_plan_ref"])  # type: ignore[arg-type]
    selected_publication = provider._nominal(
        candidate_payload["selected_publication_ref"]
    )
    selected_analysis = provider._nominal(candidate_payload["selected_analysis_ref"])
    metric_profile_ref = _ref(profile_ref)  # type: ignore[arg-type]
    repository = backtest.BacktestEvidenceRepository(foundation)
    admission_refs = tuple(
        _PROMOTION._ADMISSION.admit_backtest_evidence(
            subject, repository, foundation
        )
        for subject in (
            selected_publication,
            selected_analysis,
            metric_profile_ref,
        )
    )
    fixture_evidence = {
        "completed": provider.load_completed(
            candidate_payload["selected_publication_ref"]
        ),
        "analysis": provider.load_analysis(candidate_payload["selected_analysis_ref"]),
    }
    promotion_policy: dict[str, object] = {
        "accepted_validation_plan_refs": [plan_ref.to_canonical_dict()],
        "required_validation_result": "rejected",
        "accepted_backtest_grades": ["development"],
        "accepted_metric_profile_refs": [profile_ref],
        "maximum_governed_evidence_age_microseconds": 10_000_000_000,
        "required_review_roles": ["quant_reviewer", "risk_approver"],
        "forbidden_limitations": [],
        "decision_for_not_eligible": "rejected",
    }
    actors = _PROMOTION._actors(validation.validation_report_ref, promotion_policy)
    decision = _PROMOTION.evaluate_case(
        validation.validation_report_ref,
        promotion_policy,
        actors,
        foundation,
        fixture_evidence=fixture_evidence,
    )
    before_replay = {
        name: len(foundation.entries(name))
        for name in (
            "research.artifacts.v1",
            "research.execution.v1",
            "validation.sample-consumption.v1",
            "validation.artifacts.v1",
            "promotion.evidence-status.v1",
            "promotion.reviews.v1",
            "promotion.artifacts.v1",
        )
    }
    replayed_admissions = tuple(
        _PROMOTION._ADMISSION.admit_backtest_evidence(
            subject,
            backtest.BacktestEvidenceRepository(foundation),
            foundation,
        )
        for subject in (
            selected_publication,
            selected_analysis,
            metric_profile_ref,
        )
    )
    decision_replay = _PROMOTION.evaluate_case(
        validation.validation_report_ref,
        promotion_policy,
        actors,
        foundation,
        fixture_evidence=fixture_evidence,
    )

    assert candidate_replay == candidate
    assert validation_replay == validation
    assert decision_replay == decision
    assert replayed_admissions == admission_refs
    assert builder.feature_calls == 1
    assert builder.training_calls == 1
    assert builder.reservations_before_read == [1, 2]
    assert provider.prepare_calls == 4
    assert provider.run_calls == 5
    assert provider.derive_calls == 4
    assert {
        name: len(foundation.entries(name)) for name in before_replay
    } == before_replay

    outcomes = [
        json.loads(entry.payload)
        for entry in foundation.entries("research.execution.v1")
        if json.loads(entry.payload)["artifact_type"] == "task_outcome"
    ]
    assert len(outcomes) == 10
    assert [item["payload"]["state"] for item in outcomes].count("COMPLETED") == 8
    assert [item["payload"]["state"] for item in outcomes].count("BLOCKED") == 2

    family = _payload(foundation, _ref(candidate_payload["candidate_family_ref"]))  # type: ignore[arg-type]
    assert set(family) == {"experiment_ref", "execution_manifest_ref"}
    model_evidence = _payload(
        foundation,
        _ref(candidate_payload["model_build_evidence_ref"]),  # type: ignore[arg-type]
    )
    trial_spec = _payload(
        foundation,
        _ref(candidate_payload["selected_trial_spec_ref"]),  # type: ignore[arg-type]
    )
    completed = fixture_evidence["completed"]
    artifact_hash = model_evidence["model_artifact"]["artifact_ref_hash"]  # type: ignore[index]
    assert artifact_hash == artifact.artifact_ref_hash
    assert trial_spec["resolved_model_refs"][0]["artifact_ref_hash"] == artifact_hash  # type: ignore[index]
    assert completed["model_binding"]["artifact_ref_hash"] == artifact_hash  # type: ignore[index]
    assert prepared.model_binding.artifact_ref_hash == artifact_hash

    research_artifacts = [
        json.loads(entry.payload)
        for entry in foundation.entries("research.artifacts.v1")
    ]
    first_build_ledger_sequence = min(
        entry.ledger_sequence
        for entry in foundation.entries("research.execution.v1")
        if json.loads(entry.payload)["artifact_type"] == "task_attempt_started"
    )
    assert max(
        entry.ledger_sequence
        for entry in foundation.entries("research.artifacts.v1")
        if json.loads(entry.payload)["artifact_type"]
        in {"feature_recipe", "trainer_recipe", "model_build_plan"}
    ) < first_build_ledger_sequence
    model_outcome_sequence = max(
        entry.ledger_sequence
        for entry in foundation.entries("research.execution.v1")
        if json.loads(entry.payload).get("payload", {}).get("task_ref", {}).get("kind")
        == "MODEL_TRAINING"
        and json.loads(entry.payload)["artifact_type"] == "task_outcome"
    )
    assert min(
        entry.ledger_sequence
        for entry in foundation.entries("research.artifacts.v1")
        if json.loads(entry.payload)["artifact_type"] == "backtest_trial_spec"
    ) > model_outcome_sequence
    assert any(
        item["artifact_type"] == "strategy_candidate"
        and item["schema_version"] == 2
        for item in research_artifacts
    )

    assert report["result"] == "rejected"
    promotion_decision = _payload(foundation, decision.promotion_decision_ref)
    assert promotion_decision["decision"] == "needs_more_evidence"
