from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import crypto_quant_backtest as backtest
import pytest
from crypto_quant_domain import ArtifactRef, canonical_bytes
from crypto_quant_promotion import PublishedNegativeDecision, evaluate_case
from crypto_quant_validation import PublishedValidationReport

ROOT = Path(__file__).resolve().parents[2]
_PROMOTION_PATH = ROOT / "promotion-gate/tests/test_integrated_promotion.py"
_PROMOTION_SPEC = importlib.util.spec_from_file_location(
    "platform_fi_promotion", _PROMOTION_PATH
)
assert _PROMOTION_SPEC is not None and _PROMOTION_SPEC.loader is not None
_PROMOTION = importlib.util.module_from_spec(_PROMOTION_SPEC)
sys.modules[_PROMOTION_SPEC.name] = _PROMOTION
_PROMOTION_SPEC.loader.exec_module(_PROMOTION)
_VALIDATION = _PROMOTION._VALIDATION
_RESEARCH = _VALIDATION._RESEARCH
_ADMISSION = _PROMOTION._ADMISSION


def _ref(wire: dict[str, Any]) -> ArtifactRef:
    return ArtifactRef(
        wire["artifact_type"],
        wire["schema_version"],
        wire["content_hash"],
    )


def _payload(foundation, ref) -> dict[str, Any]:
    try:
        return json.loads(foundation.read(ref=ref).source_bytes)["payload"]
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError, KeyError) as error:
        pytest.fail(f"FI artifact is malformed: {error}")


def _status_subjects(foundation) -> set[str]:
    subjects: set[str] = set()
    for entry in foundation.entries("promotion.evidence-status.v1"):
        try:
            envelope = json.loads(entry.payload)
            subject = envelope["payload"]["subject_ref"]
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError, KeyError) as error:
            pytest.fail(f"FI status entry is malformed: {error}")
        subjects.add(json.dumps(subject, separators=(",", ":"), sort_keys=True))
    return subjects


def test_whole_platform_golden_is_one_replay_stable_provenance_chain(
    tmp_path: Path,
) -> None:
    foundation, ledger, provider, research_inputs = _RESEARCH._runtime(tmp_path)
    candidate = _RESEARCH.execute_experiment(
        research_inputs,
        foundation,
        ledger,
        provider,
    )
    selected = _payload(foundation, candidate.strategy_candidate_ref)
    profile_wire = _RESEARCH._plain(
        research_inputs.experiment_spec.metric_profile_refs[0]
    )
    validation_policy = _VALIDATION._policy(profile_wire)
    provider._prepared["validation:oos"] = _RESEARCH._prepare_with(
        foundation,
        tmp_path / "publications",
        experiment_id="fi:oos:adverse",
        market=True,
    )
    validation = _VALIDATION.validate_candidate(
        candidate.strategy_candidate_ref,
        validation_policy,
        {"binding_key": "validation:oos"},
        _VALIDATION._RESERVED_AT,
        foundation,
        ledger,
        provider,
    )
    assert type(validation) is PublishedValidationReport
    validation_report = _payload(foundation, validation.validation_report_ref)
    assert validation_report["result"] == "rejected"

    publication_ref = provider._nominal(selected["selected_publication_ref"])
    analysis_ref = provider._nominal(selected["selected_analysis_ref"])
    profile_ref = _ref(profile_wire)
    repository = backtest.BacktestEvidenceRepository(foundation)
    admissions = tuple(
        _ADMISSION.admit_backtest_evidence(subject, repository, foundation)
        for subject in (publication_ref, analysis_ref, profile_ref)
    )
    completed = provider.load_completed(selected["selected_publication_ref"])
    analysis = provider.load_analysis(selected["selected_analysis_ref"])
    assert repository.load_completed(publication_ref).source_execution_result_hash == (
        completed["execution_result_hash"]
    )
    assert repository.load_analysis(analysis_ref).analysis_ref == analysis_ref

    plan_ref = _ref(validation_report["validation_plan_ref"])
    promotion_policy: dict[str, object] = {
        "accepted_validation_plan_refs": [plan_ref.to_canonical_dict()],
        "required_validation_result": "rejected",
        "accepted_backtest_grades": ["development"],
        "accepted_metric_profile_refs": [profile_wire],
        "maximum_governed_evidence_age_microseconds": 10_000_000_000,
        "required_review_roles": ["quant_reviewer", "risk_approver"],
        "forbidden_limitations": [],
        "decision_for_not_eligible": "rejected",
    }
    actors = _PROMOTION._actors(validation.validation_report_ref, promotion_policy)
    promotion = evaluate_case(
        validation.validation_report_ref,
        promotion_policy,
        actors,
        foundation,
        fixture_evidence={"completed": completed, "analysis": analysis},
    )
    assert type(promotion) is PublishedNegativeDecision
    decision = _payload(foundation, promotion.promotion_decision_ref)
    assert decision["decision"] == "needs_more_evidence"

    runs = provider.run_calls
    attempts = tuple(tmp_path.rglob("attempt-execution-record.json"))
    candidate_replay = _RESEARCH.execute_experiment(
        research_inputs,
        foundation,
        ledger,
        provider,
    )
    validation_replay = _VALIDATION.validate_candidate(
        candidate.strategy_candidate_ref,
        validation_policy,
        {"binding_key": "validation:oos"},
        _VALIDATION._RESERVED_AT,
        foundation,
        ledger,
        provider,
    )
    admission_replay = tuple(
        _ADMISSION.admit_backtest_evidence(
            subject,
            backtest.BacktestEvidenceRepository(foundation),
            foundation,
        )
        for subject in (publication_ref, analysis_ref, profile_ref)
    )
    promotion_replay = evaluate_case(
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
    assert provider.run_calls == runs == 5
    assert tuple(tmp_path.rglob("attempt-execution-record.json")) == attempts

    plan = _payload(foundation, plan_ref)
    snapshot_ref = _ref(plan["sample_consumption_snapshot_ref"])
    snapshot = _payload(foundation, snapshot_ref)
    assessment = _payload(
        foundation,
        _ref(validation_report["sample_integrity_ref"]),
    )
    assert assessment["snapshot_ref"] == plan["sample_consumption_snapshot_ref"]
    assert snapshot["checkpoint"]["upper_log_sequence"] == 5

    subjects = _status_subjects(foundation)
    for governed in (
        selected["selected_publication_ref"],
        selected["selected_analysis_ref"],
        validation.validation_report_ref.to_canonical_dict(),
    ):
        assert json.dumps(governed, separators=(",", ":"), sort_keys=True) in subjects
    assert len(foundation.entries("platform.backtest-evidence-admission.v1")) == 3
    assert canonical_bytes(profile_wire) in canonical_bytes(analysis)

    assert not any(
        path.exists()
        for path in (
            ROOT / "foundation/uv.lock",
            ROOT / "research-platform/uv.lock",
            ROOT / "strategy-validation/uv.lock",
            ROOT / "promotion-gate/uv.lock",
        )
    )
