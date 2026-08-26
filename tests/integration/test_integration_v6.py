from __future__ import annotations

import ast
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping

import crypto_quant_backtest as backtest
import pytest
from crypto_quant_domain import ArtifactRef, canonical_bytes, canonical_sha256
from crypto_quant_foundation import LocalFoundation
from crypto_quant_promotion import PromotionActors, evaluate_positive_case
from crypto_quant_research import PublishedStrategyCandidate, execute_target_experiment
from crypto_quant_validation import (
    PublishedValidationReport,
    SampleConsumptionLedger,
    validate_target_candidate,
)

ROOT = Path(__file__).resolve().parents[2]
_BINDING_PATH = ROOT / "tests/support/target_stream_research_binding.py"
_BINDING_SPEC = importlib.util.spec_from_file_location(
    "platform_target_stream_research_binding", _BINDING_PATH
)
assert _BINDING_SPEC is not None and _BINDING_SPEC.loader is not None
_BINDING = importlib.util.module_from_spec(_BINDING_SPEC)
sys.modules[_BINDING_SPEC.name] = _BINDING
_BINDING_SPEC.loader.exec_module(_BINDING)


def _payload(foundation: LocalFoundation, ref: ArtifactRef) -> dict[str, Any]:
    return json.loads(foundation.read(ref=ref).source_bytes)["payload"]


def _ref(value: Mapping[str, Any]) -> ArtifactRef:
    return ArtifactRef(
        value["artifact_type"], value["schema_version"], value["content_hash"]
    )


def _promotion_fails_closed(ref: ArtifactRef, foundation: LocalFoundation) -> None:
    actors = PromotionActors(
        "target-stream-opener", (), "target-stream-decider", "target-stream-issuer", "unsupported v6 ref"
    )
    with pytest.raises(ValueError) as raised:
        evaluate_positive_case(
            ref,
            {"required_validation_result": "supported"},
            actors,
            foundation,
            fixture_evidence={"completed": {}, "analysis": {}},
        )
    assert getattr(raised.value, "code", None) == "GOVERNED_CLOSURE_INVALID"


def test_support_adapter_uses_public_package_roots_and_exact_backtest_authority() -> None:
    allowed_roots = {
        "crypto_quant_backtest",
        "crypto_quant_domain",
        "crypto_quant_market_data",
        "crypto_quant_research",
        "crypto_quant_trading",
        "crypto_quant_validation",
    }
    tree = ast.parse(_BINDING_PATH.read_text(encoding="utf-8"))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("crypto_quant_")
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
        if alias.name.startswith("crypto_quant_")
    }

    assert imported == allowed_roots
    assert _BINDING.BACKTEST_SHA == "f73d068d24ffb7ecc0b7d78194fcbc96908d3c04"
    assert "BacktestTargetStreamRepository" in backtest.__all__
    assert "prepare_cash_target_stream_backtest" in backtest.__all__


def test_development_cash_target_stream_research_to_independent_oos_golden_replays(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    foundation = LocalFoundation(
        tmp_path / "foundation", clock=lambda: _BINDING.RECEIVED_AT
    )
    ledger = SampleConsumptionLedger(foundation)
    assess_holdout = ledger.assess_holdout
    governance_calls = {"assess_holdout": 0}

    def counted_assess_holdout(*args, **kwargs):
        governance_calls["assess_holdout"] += 1
        return assess_holdout(*args, **kwargs)

    monkeypatch.setattr(ledger, "assess_holdout", counted_assess_holdout)
    binding = _BINDING.CashTargetStreamBinding(
        foundation, tmp_path / "backtest-publications"
    )
    discovery_materializer = binding.materializer()

    candidate = execute_target_experiment(
        _BINDING.target_experiment_inputs(binding),
        foundation,
        ledger,
        discovery_materializer,
        binding,
    )

    assert type(candidate) is PublishedStrategyCandidate
    assert candidate.strategy_candidate_ref.schema_version == 3
    assert type(binding.repository) is backtest.BacktestTargetStreamRepository
    assert type(binding.analysis_runtime) is backtest.BacktestAnalysisRuntime
    candidate_payload = _payload(foundation, candidate.strategy_candidate_ref)
    discovery_evidence_ref = _ref(
        candidate_payload["selected_target_materialization_evidence_ref"]
    )
    discovery_evidence = _payload(foundation, discovery_evidence_ref)
    target_task = _payload(
        foundation, _ref(discovery_evidence["target_build_task_ref"])
    )
    target_digest = canonical_sha256(binding.target_stream)

    assert set(discovery_evidence) == {
        "target_build_task_ref",
        "trial_declaration_ref",
        "target_recipe_ref",
        "materialization_request_hash",
        "input_data_hash",
        "target_stream_ref",
        "target_stream_digest",
        "event_count",
    }
    assert target_task["trial_declaration_ref"] == candidate_payload[
        "selected_trial_declaration_ref"
    ]
    assert target_task["target_recipe_ref"] == discovery_evidence[
        "target_recipe_ref"
    ]
    assert discovery_evidence["trial_declaration_ref"] == candidate_payload[
        "selected_trial_declaration_ref"
    ]
    assert discovery_evidence["materialization_request_hash"] == canonical_sha256(
        discovery_materializer.requests[0]
    )
    assert discovery_evidence["input_data_hash"] == _BINDING._hash("d")
    assert discovery_evidence["target_stream_digest"] == target_digest
    assert discovery_evidence["event_count"] == 1

    discovery_target = binding.load_target(discovery_evidence["target_stream_ref"])
    assert discovery_target["producer_context_ref"] == candidate_payload[
        "selected_trial_declaration_ref"
    ]
    assert discovery_target["digest"] == target_digest
    assert len(discovery_target["target_stream"]["events"]) == 1

    completed = binding.load_completed(candidate_payload["selected_publication_ref"])
    analysis = binding.load_analysis(candidate_payload["selected_analysis_ref"])
    assert completed["publication_ref"] == candidate_payload[
        "selected_publication_ref"
    ]
    assert completed["result_grade"] == "development"
    assert analysis["analysis_ref"] == candidate_payload["selected_analysis_ref"]
    assert analysis["source_publication_ref"] == candidate_payload[
        "selected_publication_ref"
    ]
    assert analysis["source_execution_result_hash"] == completed[
        "execution_result_hash"
    ]
    assert analysis["metric_profile_ref"] == _BINDING.plain(
        binding.metric_profile_ref
    )
    assert analysis["simple_period_return"] == "-0.1"
    assert analysis["trade_count"] == 1
    assert analysis["result_grade"] == "development"

    validation_materializer = binding.materializer()
    validation = validate_target_candidate(
        candidate.strategy_candidate_ref,
        _BINDING.target_validation_policy(binding),
        _BINDING.RESERVED_AT,
        foundation,
        ledger,
        validation_materializer,
        binding,
    )

    assert type(validation) is PublishedValidationReport
    assert governance_calls == {"assess_holdout": 1}
    assert validation.validation_plan_ref.schema_version == 2
    assert validation.validation_report_ref.schema_version == 2
    plan = _payload(foundation, validation.validation_plan_ref)
    report = _payload(foundation, validation.validation_report_ref)
    oos_evidence_ref = _ref(
        report["validation_target_materialization_evidence_ref"]
    )
    oos_evidence = _payload(foundation, oos_evidence_ref)
    oos_target = binding.load_target(oos_evidence["target_stream_ref"])

    assert plan["candidate_ref"] == _BINDING.plain(candidate.strategy_candidate_ref)
    assert plan["target_recipe_ref"] == discovery_evidence["target_recipe_ref"]
    assert plan["strategy_artifact"] == binding.strategy_artifact
    assert plan["accepted_backtest_grades"] == ["development"]
    assert plan["holdout"]["dataset_revision"] == "platform-oos-v1"
    assert set(oos_evidence) == {
        "validation_case_ref",
        "candidate_ref",
        "target_recipe_ref",
        "materialization_request_hash",
        "input_data_hash",
        "target_stream_ref",
        "target_stream_digest",
        "event_count",
    }
    assert oos_evidence["candidate_ref"] == _BINDING.plain(
        candidate.strategy_candidate_ref
    )
    assert oos_evidence["target_recipe_ref"] == discovery_evidence[
        "target_recipe_ref"
    ]
    assert oos_evidence["materialization_request_hash"] == canonical_sha256(
        validation_materializer.requests[0]
    )
    assert oos_evidence["input_data_hash"] == _BINDING._hash("d")
    assert oos_evidence["target_stream_digest"] == target_digest
    assert oos_evidence["event_count"] == 1
    assert oos_evidence["target_stream_ref"] != discovery_evidence[
        "target_stream_ref"
    ]
    assert canonical_bytes(oos_target["target_stream"]) == canonical_bytes(
        discovery_target["target_stream"]
    )
    assert oos_target["producer_context_ref"] == oos_evidence[
        "validation_case_ref"
    ]

    assert report["result"] == "supported"
    assert report["limitations"] == []
    assert report["threshold_evaluations"] == [
        {
            "metric_key": "simple_period_return",
            "minimum_trade_count": 1,
            "observed": "-0.1",
            "operator": "gte",
            "passed": True,
            "threshold": "-1",
            "trade_count": 1,
        }
    ]
    oos_case_result = next(
        _payload(foundation, _ref(ref))
        for ref in report["case_result_refs"]
        if _payload(foundation, _ref(ref))[
            "validation_target_materialization_evidence_ref"
        ]
        is not None
    )
    assert oos_case_result["validation_target_materialization_evidence_ref"] == _BINDING.plain(
        oos_evidence_ref
    )
    assert oos_case_result["evidence"] == {
        "publication_ref": oos_case_result["evidence"]["publication_ref"],
        "analysis_ref": oos_case_result["evidence"]["analysis_ref"],
        "metric_profile_ref": _BINDING.plain(binding.metric_profile_ref),
        "source_execution_result_hash": oos_case_result["evidence"][
            "source_execution_result_hash"
        ],
        "result_grade": "development",
        "metric_key": "simple_period_return",
        "metric_value": "-0.1",
        "trade_count": 1,
    }

    promotion_logs = (
        "promotion.artifacts.v1",
        "promotion.evidence-status.v1",
        "promotion.reviews.v1",
    )
    _promotion_fails_closed(candidate.strategy_candidate_ref, foundation)
    _promotion_fails_closed(validation.validation_report_ref, foundation)
    assert all(foundation.entries(name) == () for name in promotion_logs)

    log_names = (
        "research.artifacts.v1",
        "research.execution.v1",
        "validation.sample-consumption.v1",
        "validation.artifacts.v1",
        *promotion_logs,
    )
    before_replay = {
        "counters": (
            discovery_materializer.calls,
            len(discovery_materializer.requests),
            validation_materializer.calls,
            len(validation_materializer.requests),
            binding.publish_target_calls,
            binding.preparation_calls,
            binding.run_calls,
            binding.economic_run_calls,
            binding.derive_calls,
        ),
        "target_loads": binding.load_target_calls,
        "governance": dict(governance_calls),
        "logs": {name: len(foundation.entries(name)) for name in log_names},
    }

    candidate_replay = execute_target_experiment(
        _BINDING.target_experiment_inputs(binding),
        foundation,
        ledger,
        discovery_materializer,
        binding,
    )
    validation_replay = validate_target_candidate(
        candidate.strategy_candidate_ref,
        _BINDING.target_validation_policy(binding),
        _BINDING.RESERVED_AT,
        foundation,
        ledger,
        validation_materializer,
        binding,
    )

    assert candidate_replay == candidate
    assert validation_replay == validation
    assert type(candidate_replay) is PublishedStrategyCandidate
    assert type(validation_replay) is PublishedValidationReport
    assert candidate_replay.strategy_candidate_ref == candidate.strategy_candidate_ref
    assert validation_replay.validation_report_ref == validation.validation_report_ref
    assert before_replay["counters"] == (
        discovery_materializer.calls,
        len(discovery_materializer.requests),
        validation_materializer.calls,
        len(validation_materializer.requests),
        binding.publish_target_calls,
        binding.preparation_calls,
        binding.run_calls,
        binding.economic_run_calls,
        binding.derive_calls,
    )
    assert binding.load_target_calls == before_replay["target_loads"] + 3
    assert governance_calls == before_replay["governance"]
    assert before_replay["logs"] == {
        name: len(foundation.entries(name)) for name in log_names
    }
