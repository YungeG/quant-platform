from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "overall/integration-v6.md"
FIXTURE = ROOT / "tests/contracts/integration-v6-target-stream-research-v1.json"
APPROVAL = ROOT / "implementation/v6-contract-target-stream-research-v1.md"
PLAN = ROOT / "implementation/plans/target-stream-research.md"
PLAN_README = ROOT / "implementation/plans/README.md"
ROADMAP = ROOT / "implementation/roadmap.md"
GLOSSARY = ROOT / "CONTEXT.md"
FIXTURE_SHA = "dcae07677fc0c0a68c034310f2183c192f9b46ad4002a5293a88213966d28ae2"
APPROVED_AT = "2026-08-26T03:14:51Z"
BASELINES = {
    "platform": "04b01a1db1408ab7277a116f02ce706243ac1499",
    "backtest": "8de544e7794ee05b652355c9809b5454d7ace494",
    "foundation": "9d88ed67a84d06c558276f8bae2206b069bcec8f",
    "research": "1557ec1904de6f2a8f8a32c2f37ce038a0daa022",
    "validation": "cd966d92dad2110af7d8b1bf580536f6c3cdb998",
    "promotion": "8e6dddf5da0494b57cca6990d5024fe4198e6b44",
}
PYPROJECT_SHA = "fd91992418122cbce414ff5fa0c39878290df1d49f69b9758d5ca1ec64806024"
UV_LOCK_SHA = "75a91665859490d03544066d0585bceec9b6dbe7156cf322b4cb67f95a6a420f"


def _fixture() -> dict[str, object]:
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == FIXTURE_SHA
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_integration_v6_contract_is_frozen_and_exactly_approved() -> None:
    fixture = _fixture()
    approval = APPROVAL.read_text(encoding="utf-8")
    contract = CONTRACT.read_text(encoding="utf-8")

    assert fixture["contract_id"] == "integration-v6-target-stream-research-v1"
    assert fixture["node_id"] == "TSR-CON-01"
    assert fixture["schema_version"] == 1
    assert fixture["status"] == "frozen"
    assert fixture["approval"] == {
        "approved_at": APPROVED_AT,
        "owners": {
            "Platform": "YungeG",
            "Backtest": "YungeG",
            "Research": "YungeG",
            "Validation": "YungeG",
            "Promotion": "YungeG",
        },
        "binds_exact_fixture_hash": True,
    }
    assert fixture["baseline_shas"] == BASELINES
    assert FIXTURE_SHA in approval
    assert approval.count(f"| `YungeG` | APPROVED | `{APPROVED_AT}` |") == 5
    assert "**Status:** APPROVED" in approval
    assert "`TSR-BT-01` is READY" in approval
    assert "no implementation is claimed" in contract


def test_integration_v6_target_materializer_and_module_wires_are_exact() -> None:
    fixture = _fixture()
    backtest = fixture["backtest_target_authority"]
    materializer = fixture["materializer"]
    research = fixture["research"]
    validation = fixture["validation"]

    assert backtest["artifact_envelope"] == "backtest_target_stream@1"
    assert backtest["ref"] == {
        "nominal_type": "BacktestTargetStreamRef",
        "wire_fields": ["type", "artifact_ref"],
        "wire_type": "backtest_target_stream_ref",
    }
    assert backtest["payload_fields"] == ["producer_context_ref", "target_stream"]
    assert backtest["repository"] == {
        "class": "BacktestTargetStreamRepository",
        "operations": [
            "publish(producer_context_ref, target_stream) -> BacktestTargetStreamRef",
            "load(ref) -> VerifiedBacktestTargetStream",
        ],
        "storage": "CAS/exact-read only",
        "platform_owner_log": False,
    }
    assert backtest["verified_view"]["fields"] == [
        "ref",
        "producer_context_ref",
        "target_stream",
        "digest",
    ]
    assert backtest["identity"] == {
        "equal_streams_with_different_producer_contexts_have_different_refs": True,
        "semantic_request_and_run_bind": "target_stream_digest",
        "semantic_request_and_run_exclude": [
            "producer_context_ref",
            "BacktestTargetStreamRef",
        ],
    }

    assert materializer["property"] == (
        "strategy_artifact: BuildArtifactRef(role=DECISION_SOURCE, immutable identity)"
    )
    assert materializer["method"] == (
        "materialize_target(request: Mapping[str, object]) -> Mapping[str, object]"
    )
    assert materializer["request"]["fields"] == [
        "type",
        "schema_version",
        "consumer_ref",
        "target_recipe_ref",
        "market_bundle_ref",
        "dataset_revision",
        "interval_start",
        "interval_end",
        "parameter_values",
        "seed",
    ]
    assert materializer["result"]["fields"] == [
        "type",
        "schema_version",
        "request_hash",
        "strategy_artifact",
        "input_data_hash",
        "target_stream",
    ]
    assert materializer["result"][
        "contains_additional_refs_prepared_run_or_cache_handles"
    ] is False
    assert materializer["reads"] == "immutable MarketBundle reads only"
    assert materializer["network_or_current_apis_allowed"] is False

    assert research["target_recipe"] == {
        "artifact": "TargetRecipe@1",
        "fields": [
            "target_key",
            "strategy_artifact",
            "target_schema_hash",
            "input_names",
        ],
    }
    assert research["target_build_task"]["artifact"] == "TargetBuildTask@1"
    assert research["target_build_task"]["task_kind"] == "TARGET_BUILD"
    assert research["target_build_task"]["task_outcome_witness"] == "TARGET_BUILD"
    assert research["materialization_evidence"]["fields"] == [
        "target_build_task_ref",
        "trial_declaration_ref",
        "target_recipe_ref",
        "materialization_request_hash",
        "input_data_hash",
        "target_stream_ref",
        "target_stream_digest",
        "event_count",
    ]
    assert research["experiment_specs"] == {
        "target_experiment": "ExperimentSpec@2",
        "additive_field": "target_recipe_ref",
        "ordinary_and_model_experiment_spec_v1_bytes_unchanged": True,
    }
    assert research["reservation_producer"] == "existing integrated TrialDeclaration@1"
    assert research["candidate"] == {
        "artifact": "StrategyCandidate@3",
        "additive_field": "selected_target_materialization_evidence_ref",
        "candidate_family_fields_unchanged": True,
        "experiment_execution_manifest_fields_unchanged": True,
        "target_mode_dispatch": "exact",
    }

    assert validation["reservation_producer"] == "existing out_of_sample ValidationCase"
    assert validation["plan"] == {
        "artifact": "ValidationPlan@2",
        "additive_bindings": ["target_recipe_ref", "strategy_artifact"],
    }
    assert validation["materialization_evidence"]["artifact"] == (
        "ValidationTargetMaterializationEvidence@1"
    )
    assert validation["materialization_evidence"]["fields"] == [
        "validation_case_ref",
        "candidate_ref",
        "target_recipe_ref",
        "materialization_request_hash",
        "input_data_hash",
        "target_stream_ref",
        "target_stream_digest",
        "event_count",
    ]
    assert validation["new_operation"] == {
        "name": "validate_target_candidate",
        "parameters": [
            "candidate_ref",
            "policy",
            "reservation_at",
            "foundation",
            "sample_ledger",
            "materializer",
            "backtest",
        ],
        "fresh_or_generic_preparation_input_parameter": False,
        "backtest_target_operations": [
            "publish_target(producer_context_ref, target_stream)",
            "load_target(target_ref)",
            "prepare_target(validation_case_ref, target_ref)",
        ],
    }
    assert validation["existing_validate_candidate_unchanged"] is True
    assert validation["all_v1_bytes_unchanged"] is True
    assert validation["discovery_target_ref_substitution_as_oos_valid"] is False


def test_integration_v6_execution_replay_precedence_and_scope_are_exact() -> None:
    fixture = _fixture()
    execution = fixture["backtest_execution"]

    assert execution["timeline"] == "DeterministicTimelineV2"
    assert execution["cursor"] == "TimelineCursorV2"
    assert execution["timeline_identity_fields"] == [
        "market_bundle_ref",
        "sorted_market_stream_keys",
        "target_stream_digest",
        "window",
    ]
    assert execution["execution_input_bundle"] == {
        "artifact": "backtest_execution_input_bundle@6",
        "embeds": "canonical target stream value",
        "embeds_target_ref": False,
        "timeline_and_decision_injection": "source-neutral v2",
    }
    assert execution["protected_bytes_unchanged"] == {
        "execution_input_bundle_versions": [1, 2, 3, 4, 5],
        "request_versions": [1],
        "completed": True,
        "terminal": True,
        "analysis": True,
        "publication": True,
    }
    assert execution["development_operation"] == {
        "name": "prepare_cash_target_stream_backtest",
        "inputs": [
            "CashDevelopmentRequestIntent",
            "CashDevelopmentProviderInputs",
            "BacktestTargetStreamRef",
        ],
        "profile_specific": True,
        "strategy_specific": False,
    }
    assert fixture["promotion"] == {
        "unsupported_until": "TSR-PG-01",
        "unsupported_refs": ["StrategyCandidate@3", "ValidationReport@2"],
        "failure_mode": "fail closed as unsupported",
        "coercion_or_fallback": False,
    }
    assert fixture["failure_precedence"] == {
        "high_level_groups": [
            "public arg/type",
            "reservation",
            "materializer artifact/request/result",
            "target publish/load/ref/tamper/retention/context/digest",
            "evidence publication",
            "preparation",
            "Backtest terminal/provider",
            "analysis/link",
            "manifest/selection",
            "Validation target substitution/holdout",
            "report",
            "Promotion unsupported",
        ],
        "preserve_module_specific_existing_precedence_inside_each_group": True,
    }
    assert fixture["replay_commit_points"] == {
        "reservation": "idempotent",
        "materialization_evidence_publication": (
            "module commit preventing rematerialization"
        ),
        "target_cas_orphan_is_research_or_validation_evidence": False,
        "recovery_order": [
            "exact-load verified first evidence/ref",
            "reconstructed prepared request/run",
        ],
        "immutable_target_cas_load_required": True,
        "idempotent_preparation_reconstruction_allowed": True,
        "forbidden_second_actions": [
            "sample/materializer-input read",
            "target materialization",
            "economic run",
            "governance refresh",
        ],
    }
    assert fixture["initial_scope"] == {
        "grade": "development",
        "market_profile": "cash golden",
        "targets": "fixed one-slice portfolio targets",
        "metrics": ["simple_period_return", "trade_count"],
        "model_combination": False,
        "decision_grade": False,
        "real_binance_qualification": False,
        "real_a_share_qualification": False,
        "promotion_support": False,
    }


def test_integration_v6_status_and_root_baseline_remain_frozen() -> None:
    fixture = _fixture()
    roadmap = ROADMAP.read_text(encoding="utf-8")
    plan = PLAN.read_text(encoding="utf-8")
    plan_readme = PLAN_README.read_text(encoding="utf-8")
    glossary = GLOSSARY.read_text(encoding="utf-8")
    registry = roadmap.split("## 2. Status registry", 1)[1].split(
        "## 3. Execution DAG", 1
    )[0]

    assert registry.count("| `V6-CON-01` | APPROVED |") == 1
    assert registry.count("| `TSR-CON-01` | APPROVED |") == 1
    assert registry.count("| `TSR-BT-01` | READY |") == 1
    assert registry.count("| `TSR-RP-01` | BLOCKED |") == 1
    assert registry.count("| `TSR-SV-01` | BLOCKED |") == 1
    assert registry.count("| `TSR-FI-01` | BLOCKED |") == 1
    assert registry.count("| `TSR-PG-01` | DEFERRED |") == 1
    assert "FI-04 ─→ V6-CON-01 / TSR-CON-01 [APPROVED]" in roadmap
    assert "TSR-BT-01 [READY]" in roadmap
    assert "READY_FOR_TSR_BT_01" in plan
    assert "no implementation claim" in plan.lower()
    assert "approved contract; Backtest leaf READY" in plan_readme
    assert "**Backtest target stream**" in glossary
    assert "**Target materialization evidence**" in glossary

    assert fixture["root_baseline"] == {
        "pyproject_sha256": PYPROJECT_SHA,
        "uv_lock_sha256": UV_LOCK_SHA,
        "backtest_vcs_revision": BASELINES["backtest"],
        "backtest_vcs_revision_occurrences": 5,
        "contract_approval_changes_gitlinks_or_pins": False,
    }
    assert hashlib.sha256((ROOT / "pyproject.toml").read_bytes()).hexdigest() == PYPROJECT_SHA
    assert hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest() == UV_LOCK_SHA
    assert (ROOT / "pyproject.toml").read_text(encoding="utf-8").count(
        BASELINES["backtest"]
    ) == 5

    for path, key in (
        ("backtest", "backtest"),
        ("foundation", "foundation"),
        ("research-platform", "research"),
        ("strategy-validation", "validation"),
        ("promotion-gate", "promotion"),
    ):
        entry = subprocess.check_output(
            ["git", "ls-files", "-s", path], cwd=ROOT, text=True
        ).split()
        assert entry[:2] == ["160000", BASELINES[key]]
