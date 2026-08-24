from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import crypto_quant_backtest as backtest
import pytest
from crypto_quant_domain import ArtifactRef, canonical_bytes, canonical_sha256
from crypto_quant_foundation import LocalFoundation
from crypto_quant_promotion import PublishedPositiveDecision, evaluate_positive_case

ROOT = Path(__file__).resolve().parents[2]

_RESEARCH_PATH = ROOT / "research-platform/tests/test_research_shell.py"
_RESEARCH_SPEC = importlib.util.spec_from_file_location(
    "platform_research_shell", _RESEARCH_PATH
)
assert _RESEARCH_SPEC is not None and _RESEARCH_SPEC.loader is not None
_RESEARCH = importlib.util.module_from_spec(_RESEARCH_SPEC)

sys.modules[_RESEARCH_SPEC.name] = _RESEARCH
_RESEARCH_SPEC.loader.exec_module(_RESEARCH)

_VALIDATION_PATH = ROOT / "strategy-validation/tests/test_validation_shell.py"
_VALIDATION_SPEC = importlib.util.spec_from_file_location(
    "platform_validation_shell", _VALIDATION_PATH
)
assert _VALIDATION_SPEC is not None and _VALIDATION_SPEC.loader is not None
_VALIDATION = importlib.util.module_from_spec(_VALIDATION_SPEC)
sys.modules[_VALIDATION_SPEC.name] = _VALIDATION
_VALIDATION_SPEC.loader.exec_module(_VALIDATION)

_PROMOTION_PATH = ROOT / "promotion-gate/tests/test_integrated_promotion.py"
_PROMOTION_SPEC = importlib.util.spec_from_file_location(
    "platform_integrated_promotion_v5", _PROMOTION_PATH
)
assert _PROMOTION_SPEC is not None and _PROMOTION_SPEC.loader is not None
_PROMOTION = importlib.util.module_from_spec(_PROMOTION_SPEC)
sys.modules[_PROMOTION_SPEC.name] = _PROMOTION
_PROMOTION_SPEC.loader.exec_module(_PROMOTION)

_ADMISSION_PATH = ROOT / "tests/support/backtest_evidence_admission.py"
_ADMISSION_SPEC = importlib.util.spec_from_file_location(
    "platform_backtest_admission", _ADMISSION_PATH
)
assert _ADMISSION_SPEC is not None and _ADMISSION_SPEC.loader is not None
_ADMISSION = importlib.util.module_from_spec(_ADMISSION_SPEC)
sys.modules[_ADMISSION_SPEC.name] = _ADMISSION
_ADMISSION_SPEC.loader.exec_module(_ADMISSION)


def _artifact_ref(raw: dict[str, object]) -> ArtifactRef:
    return ArtifactRef(
        raw["artifact_type"],  # type: ignore[index]
        raw["schema_version"],  # type: ignore[index]
        raw["content_hash"],  # type: ignore[index]
    )


def _wire(ref) -> dict[str, object]:
    return ref.to_canonical_dict()


def _payload(foundation, ref) -> dict[str, object]:
    try:
        return json.loads(foundation.read(ref=ref).source_bytes)["payload"]
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError, KeyError) as error:
        pytest.fail(f"Platform artifact is malformed: {error}")


def _wire_key(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class _TypedAdmissionRepository:
    def __init__(self, provider: object) -> None:
        self._provider = provider

    def load_completed_v3(
        self,
        ref: backtest.BacktestCanonicalPublicationRefV2,
    ) -> dict[str, object]:
        if type(ref) is not backtest.BacktestCanonicalPublicationRefV2:
            raise TypeError("exact BacktestCanonicalPublicationRefV2 required")
        wire = json.loads(canonical_bytes(ref))
        return self._provider.load_completed_v3(wire)  # type: ignore[attr-defined, no-any-return]

    def load_analysis_v2(
        self,
        ref: backtest.AnalysisArtifactRefV2,
    ) -> dict[str, object]:
        if type(ref) is not backtest.AnalysisArtifactRefV2:
            raise TypeError("exact AnalysisArtifactRefV2 required")
        wire = json.loads(canonical_bytes(ref))
        return self._provider.load_analysis_v2(wire)  # type: ignore[attr-defined, no-any-return]


def test_real_decision_grade_candidate_supported_chain_is_exact_v2_replay_stable(
    tmp_path: Path,
) -> None:
    foundation = LocalFoundation(tmp_path, clock=lambda: _RESEARCH.RECEIVED_AT)
    ledger = _VALIDATION.SampleConsumptionLedger(foundation)
    provider = _RESEARCH.DecisionGradePort(foundation)
    case = _RESEARCH.load_contract_fixture(_RESEARCH.CONTRACT_V2_PATH)["cases"][0]

    candidate = _RESEARCH.execute_experiment(
        _RESEARCH._decision_grade_inputs(),
        foundation,
        ledger,
        provider,
    )
    selected = _RESEARCH._payload(foundation, candidate.strategy_candidate_ref)

    assert (
        selected["selected_publication_ref"]
        == case["completed_v3"]["publication_ref"]
    )
    assert selected["selected_analysis_ref"] == case["analysis_v2"]["analysis_ref"]

    completed = provider.load_completed_v3(selected["selected_publication_ref"])
    analysis = provider.load_analysis_v2(selected["selected_analysis_ref"])
    assert completed["result_grade"] == "decision_grade"
    assert (
        completed["rebuild_verification_ref"]
        == case["completed_v3"]["rebuild_verification_ref"]
    )
    assert (
        completed["proof_publication_manifest_ref"]
        == case["completed_v3"]["proof_publication_manifest_ref"]
    )
    assert analysis["result_grade"] == "decision_grade"
    assert analysis["simple_period_return"] == "0.02392"
    assert analysis["trade_count"] == 1
    assert provider.completed_v3_calls
    assert provider.analysis_v2_calls

    policy = _VALIDATION._policy(
        case["analysis_v2"]["metric_profile_ref"],
        grade="decision_grade",
    )
    validation = _VALIDATION.validate_candidate(
        candidate.strategy_candidate_ref,
        policy,
        {"fixture_case": "decision_grade_completed_v3"},
        _VALIDATION.RESERVED_AT,
        foundation,
        ledger,
        provider,
    )
    report = _VALIDATION._payload(foundation, validation.validation_report_ref)
    plan = _VALIDATION._payload(foundation, validation.validation_plan_ref)
    assert report["result"] == "supported"
    assert plan["accepted_backtest_grades"] == ["decision_grade"]
    outcome = _VALIDATION._oos_result_payload(foundation)
    evidence = outcome["evidence"]
    assert set(evidence) == {
        "publication_ref",
        "analysis_ref",
        "metric_profile_ref",
        "source_execution_result_hash",
        "result_grade",
        "metric_key",
        "metric_value",
        "trade_count",
    }
    assert evidence["metric_value"] == "0.02392"
    assert evidence["trade_count"] == 1
    assert evidence["result_grade"] == "decision_grade"
    assert "rebuild_verification_ref" not in evidence
    assert "proof_publication_manifest_ref" not in evidence

    publication_ref = backtest.BacktestCanonicalPublicationRefV2(
        _artifact_ref(selected["selected_publication_ref"]["artifact_ref"])  # type: ignore[index]
    )
    analysis_ref = backtest.AnalysisArtifactRefV2(
        _artifact_ref(selected["selected_analysis_ref"]["artifact_ref"])  # type: ignore[index]
    )
    profile_ref = _artifact_ref(case["analysis_v2"]["metric_profile_ref"])
    repository = _TypedAdmissionRepository(provider)
    admissions = (
        _ADMISSION.admit_backtest_evidence(publication_ref, repository, foundation),
        _ADMISSION.admit_backtest_evidence(analysis_ref, repository, foundation),
        _ADMISSION.admit_backtest_evidence(profile_ref, repository, foundation),
    )

    admission_entries = tuple(
        json.loads(entry.payload)
        for entry in foundation.entries("platform.backtest-evidence-admission.v1")
    )
    assert len(admission_entries) == 3
    expected_versions = {
        _wire_key(case["completed_v3"]["publication_ref"]): 2,
        _wire_key(case["analysis_v2"]["analysis_ref"]): 2,
        _wire_key(case["analysis_v2"]["metric_profile_ref"]): 1,
    }
    for entry in foundation.entries("platform.backtest-evidence-admission.v1"):
        envelope = json.loads(entry.payload)
        key = _wire_key(envelope["payload"]["subject_ref"])
        version = expected_versions[key]
        assert envelope["schema_version"] == version
        assert entry.event_id == canonical_sha256(
            (
                f"backtest-evidence-admission-v{version}",
                envelope["payload"]["subject_ref"],
            )
        )

    promotion_policy = {
        "accepted_validation_plan_refs": [_wire(validation.validation_plan_ref)],
        "required_validation_result": "supported",
        "accepted_backtest_grades": ["decision_grade"],
        "accepted_metric_profile_refs": [case["analysis_v2"]["metric_profile_ref"]],
        "maximum_governed_evidence_age_microseconds": 10_000_000_000,
        "required_review_roles": ["quant_reviewer", "risk_approver"],
        "forbidden_limitations": [],
        "decision_for_not_eligible": "rejected",
    }
    actors = _PROMOTION._actors(validation.validation_report_ref, promotion_policy)
    promotion = evaluate_positive_case(
        validation.validation_report_ref,
        promotion_policy,
        actors,
        foundation,
        fixture_evidence={"completed": completed, "analysis": analysis},
    )

    evaluation = _payload(foundation, promotion.promotion_evaluation_ref)
    decision = _payload(foundation, promotion.promotion_decision_ref)

    assert type(promotion) is PublishedPositiveDecision
    assert promotion.promotion_evaluation_ref.schema_version == 2
    assert promotion.promotion_decision_ref.schema_version == 2
    assert set(evaluation) == {
        "promotion_case_ref",
        "evidence_status_snapshot_ref",
        "review_log_checkpoint",
        "result",
        "reason_codes",
    }
    assert set(decision) == {
        "promotion_evaluation_ref",
        "decider_ref",
        "decision",
        "rationale",
        "limitations",
    }
    assert evaluation["result"] == "ELIGIBLE"
    assert evaluation["reason_codes"] == []
    assert decision["decision"] == "shadow_ready"
    assert decision["limitations"] == []

    log_names = (
        "research.artifacts.v1",
        "research.execution.v1",
        "validation.sample-consumption.v1",
        "validation.artifacts.v1",
        "platform.backtest-evidence-admission.v1",
        "promotion.artifacts.v1",
        "promotion.evidence-status.v1",
        "promotion.reviews.v1",
    )
    before_replay = {
        "provider": (len(provider.run_requests), len(provider.derive_calls)),
        "logs": {name: len(foundation.entries(name)) for name in log_names},
    }

    candidate_replay = _RESEARCH.execute_experiment(
        _RESEARCH._decision_grade_inputs(),
        foundation,
        ledger,
        provider,
    )
    validation_replay = _VALIDATION.validate_candidate(
        candidate.strategy_candidate_ref,
        policy,
        {"fixture_case": "decision_grade_completed_v3"},
        _VALIDATION.RESERVED_AT,
        foundation,
        ledger,
        provider,
    )
    admission_replay = (
        _ADMISSION.admit_backtest_evidence(publication_ref, repository, foundation),
        _ADMISSION.admit_backtest_evidence(analysis_ref, repository, foundation),
        _ADMISSION.admit_backtest_evidence(profile_ref, repository, foundation),
    )
    promotion_replay = evaluate_positive_case(
        validation.validation_report_ref,
        promotion_policy,
        actors,
        foundation,
        fixture_evidence={"completed": completed, "analysis": analysis},
    )

    assert candidate_replay == candidate
    assert validation_replay == validation
    assert admission_replay == admissions
    assert promotion_replay == promotion
    assert before_replay["provider"] == (
        len(provider.run_requests),
        len(provider.derive_calls),
    )
    assert before_replay["logs"] == {
        name: len(foundation.entries(name)) for name in log_names
    }

    assert (
        promotion_replay.promotion_evaluation_ref
        == promotion.promotion_evaluation_ref
    )
    assert promotion_replay.promotion_decision_ref == promotion.promotion_decision_ref
