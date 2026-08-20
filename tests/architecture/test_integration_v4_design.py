from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "overall/integration-v4.md"
ROADMAP = ROOT / "implementation/roadmap.md"
PLAN = ROOT / "implementation/plans/v4-shadow-spec.md"
GLOSSARY = ROOT / "CONTEXT.md"
FIXTURE = ROOT / "tests/contracts/integration-v4-shadow-spec-v1.json"
APPROVAL = ROOT / "implementation/v4-contract-shadow-spec-v1.md"
FIXTURE_SHA = "0f030a47ffb5ac3b64d40330ab72686e04e4e85feddec7d489c9ae34f5c7ece7"
INTEGRATION_V3_RELEASE_SHA = "3ea0be372d14501decbbfd0343b06488eb2dee28"
ACCEPTED_BACKTEST_SHA = "033344172b24847e73941bb97a06da0490527edf"


def test_v4_shadow_spec_candidate_is_frozen_but_not_approved() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    approval = APPROVAL.read_text(encoding="utf-8")
    contract = CONTRACT.read_text(encoding="utf-8")

    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == FIXTURE_SHA
    assert fixture["contract_id"] == "integration-v4-shadow-spec-v1"
    assert fixture["status"] == "frozen"
    assert fixture["owner_log"] == "shadow.artifacts.v1"
    assert fixture["schemas"] == {
        "ShadowSpec@1": [
            "promotion_decision_ref",
            "proposed_by_ref",
            "observation_start",
            "observation_end",
        ]
    }
    assert fixture["decision_requirements"] == {
        "decision_schema": "PromotionDecision@2",
        "decision": "shadow_ready",
        "decision_limitations": [],
        "evaluation_schema": "PromotionEvaluation@2",
        "evaluation_result": "ELIGIBLE",
        "evaluation_reason_codes": [],
        "promotion_policy_required_validation_result": "supported",
        "exact_published_linkage": True,
    }
    assert fixture["time_rules"]["publication_not_after_start"] is True
    assert fixture["time_rules"][
        "end_not_after_evaluation_plus_policy_maximum_age"
    ] is True
    assert fixture["identity_rules"]["candidate_ref_duplicated"] is False
    assert fixture["identity_rules"]["validation_report_ref_duplicated"] is False
    assert fixture["authority"] == {
        "evidence_only": True,
        "creates_shadow_runtime": False,
        "subscribes_market_data": False,
        "creates_simulated_fills_or_positions": False,
        "allocates_capital": False,
        "authorizes_live_or_deployment": False,
        "grants_credentials_or_order_routing": False,
    }
    assert fixture["compatibility"]["backtest_changes"] == 0
    assert FIXTURE_SHA in approval
    assert approval.count("| — | PENDING | — |") == 3
    assert "**Status:** AWAITING_APPROVAL" in approval
    assert "creates no Shadow runtime" in contract


def test_v4_roadmap_authorizes_only_contract_approval() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")
    plan = PLAN.read_text(encoding="utf-8")
    glossary = GLOSSARY.read_text(encoding="utf-8")
    registry = roadmap.split("## 2. Status registry", 1)[1].split(
        "## 3. Execution DAG", 1
    )[0]
    backtest_entry = subprocess.check_output(
        ["git", "ls-files", "-s", "backtest"], cwd=ROOT, text=True
    ).split()

    assert registry.count("| `V4-CON-01` | READY_FOR_APPROVAL |") == 1
    assert "FI-03 ─→ V4-CON-01 [READY_FOR_APPROVAL]" in roadmap
    assert "no implementation node before approval" in roadmap
    assert "ShadowSpec@1(" in plan
    assert "**ShadowSpec (V4 candidate)**" in glossary
    assert "SHADOW-" not in roadmap
    assert subprocess.check_output(
        ["git", "rev-list", "-n", "1", "integration-v3"], cwd=ROOT, text=True
    ).strip() == INTEGRATION_V3_RELEASE_SHA
    assert backtest_entry[:2] == ["160000", ACCEPTED_BACKTEST_SHA]
