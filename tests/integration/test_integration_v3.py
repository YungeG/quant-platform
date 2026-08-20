from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import crypto_quant_backtest as backtest
from crypto_quant_promotion import PublishedPositiveDecision, evaluate_positive_case
from crypto_quant_validation import OosRule, PublishedValidationReport, ValidationPolicy

ROOT = Path(__file__).resolve().parents[2]
_V1_PATH = ROOT / "tests/integration/test_integration_v1.py"
_V1_SPEC = importlib.util.spec_from_file_location("platform_fi_v1", _V1_PATH)
assert _V1_SPEC is not None and _V1_SPEC.loader is not None
_V1 = importlib.util.module_from_spec(_V1_SPEC)
sys.modules[_V1_SPEC.name] = _V1
_V1_SPEC.loader.exec_module(_V1)

_RESEARCH = _V1._RESEARCH
_VALIDATION = _V1._VALIDATION
_PROMOTION = _V1._PROMOTION
_ADMISSION = _V1._ADMISSION


def _supported_policy(profile_ref: object) -> ValidationPolicy:
    base = _VALIDATION._policy(profile_ref)
    return ValidationPolicy(
        base.accepted_backtest_grades,
        base.accepted_metric_profile_refs,
        base.holdout,
        OosRule(
            profile_ref,
            "simple_period_return",
            "fraction",
            "gte",
            "-0.2",
            1,
        ),
        base.decision_rule,
    )


def test_real_supported_validation_reaches_shadow_ready_and_replays(
    tmp_path: Path,
) -> None:
    foundation, ledger, provider, research_inputs = _RESEARCH._runtime(tmp_path)
    candidate = _RESEARCH.execute_experiment(
        research_inputs,
        foundation,
        ledger,
        provider,
    )
    selected = _V1._payload(foundation, candidate.strategy_candidate_ref)
    profile_wire = _RESEARCH._plain(
        research_inputs.experiment_spec.metric_profile_refs[0]
    )
    validation_policy = _supported_policy(profile_wire)
    provider._prepared["validation:oos:positive"] = _RESEARCH._prepare_with(
        foundation,
        tmp_path / "publications",
        experiment_id="fi:oos:positive",
        market=True,
    )
    validation = _VALIDATION.validate_candidate(
        candidate.strategy_candidate_ref,
        validation_policy,
        {"binding_key": "validation:oos:positive"},
        _VALIDATION._RESERVED_AT,
        foundation,
        ledger,
        provider,
    )
    assert type(validation) is PublishedValidationReport
    validation_report = _V1._payload(foundation, validation.validation_report_ref)
    assert validation_report["result"] == "supported"
    assert validation_report["threshold_evaluations"] == [
        {
            "metric_key": "simple_period_return",
            "minimum_trade_count": 1,
            "observed": "-0.1",
            "operator": "gte",
            "passed": True,
            "threshold": "-0.2",
            "trade_count": 1,
        }
    ]

    publication_ref = provider._nominal(selected["selected_publication_ref"])
    analysis_ref = provider._nominal(selected["selected_analysis_ref"])
    profile_ref = _V1._ref(profile_wire)
    repository = backtest.BacktestEvidenceRepository(foundation)
    admissions = tuple(
        _ADMISSION.admit_backtest_evidence(subject, repository, foundation)
        for subject in (publication_ref, analysis_ref, profile_ref)
    )
    completed = provider.load_completed(selected["selected_publication_ref"])
    analysis = provider.load_analysis(selected["selected_analysis_ref"])
    assert analysis["simple_period_return"] == "-0.1"
    assert analysis["trade_count"] == 1

    plan_ref = _V1._ref(validation_report["validation_plan_ref"])
    promotion_policy: dict[str, object] = {
        "accepted_validation_plan_refs": [plan_ref.to_canonical_dict()],
        "required_validation_result": "supported",
        "accepted_backtest_grades": ["development"],
        "accepted_metric_profile_refs": [profile_wire],
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
    assert type(promotion) is PublishedPositiveDecision
    assert promotion.promotion_evaluation_ref.schema_version == 2
    assert promotion.promotion_decision_ref.schema_version == 2
    evaluation = _V1._payload(foundation, promotion.promotion_evaluation_ref)
    decision = _V1._payload(foundation, promotion.promotion_decision_ref)
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
        "promotion.evidence-status.v1",
        "promotion.reviews.v1",
        "promotion.artifacts.v1",
    )
    before_replay = {name: len(foundation.entries(name)) for name in log_names}
    run_calls = provider.run_calls
    candidate_replay = _RESEARCH.execute_experiment(
        research_inputs,
        foundation,
        ledger,
        provider,
    )
    validation_replay = _VALIDATION.validate_candidate(
        candidate.strategy_candidate_ref,
        validation_policy,
        {"binding_key": "validation:oos:positive"},
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
    assert provider.run_calls == run_calls == 5
    assert {name: len(foundation.entries(name)) for name in log_names} == before_replay
