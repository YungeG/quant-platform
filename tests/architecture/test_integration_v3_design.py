from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "overall/integration-v3.md"
ROADMAP = ROOT / "implementation/roadmap.md"
PLAN = ROOT / "implementation/plans/v3-positive-promotion.md"
FIXTURE = ROOT / "tests/contracts/integration-v3-positive-promotion-v1.json"
APPROVAL = ROOT / "implementation/v3-contract-positive-promotion-v1.md"
PG_POS_RECEIPT = ROOT / "implementation/pg-pos-01-receipt.md"
FIXTURE_SHA = "2f826867f54f8c083f9d3574702a8ccaac8c7ebea5e64f57fff791a6b0e500d9"
ACCEPTED_BACKTEST_SHA = "033344172b24847e73941bb97a06da0490527edf"
PG_POS_SHA = "de10a535b8c6a4da79a3b0f29e1dddd925d23586"
PG_POS_RUNTIME_SHA = "7210621bc56e3d6cc51bb38c0acea6ca6d5ecc03"
PLATFORM_IMPLEMENTATION_SHA = "5e309f87edbbf5460b2c1e2d3664d22b67791c47"


def test_v3_positive_promotion_contract_is_frozen_and_approved() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    approval = APPROVAL.read_text(encoding="utf-8")
    contract = CONTRACT.read_text(encoding="utf-8")

    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == FIXTURE_SHA
    assert fixture["contract_id"] == "integration-v3-positive-promotion-v1"
    assert fixture["status"] == "frozen"
    assert fixture["schemas"] == {
        "PromotionEvaluation@2": [
            "promotion_case_ref",
            "evidence_status_snapshot_ref",
            "review_log_checkpoint",
            "result",
            "reason_codes",
        ],
        "PromotionDecision@2": [
            "promotion_evaluation_ref",
            "decider_ref",
            "decision",
            "rationale",
            "limitations",
        ],
    }
    assert fixture["positive_policy"]["required_validation_result"] == "supported"
    assert fixture["decision_mapping"]["ELIGIBLE"] == "shadow_ready"
    assert fixture["shadow_ready"] == {
        "evidence_only": True,
        "may_be_cited_by_future_shadow_proposal": True,
        "creates_shadow_spec": False,
        "starts_runtime": False,
        "authorizes_live_or_deployment": False,
        "grants_credentials_or_order_routing": False,
    }
    assert fixture["compatibility"]["POSITIVE_PATH_DEFERRED_preserved"] is True
    assert fixture["compatibility"]["backtest_changes"] == 0
    assert FIXTURE_SHA in approval
    assert approval.count(
        "| `YungeG` | APPROVED | `2026-08-20T06:57:25Z` |"
    ) == 2
    assert "**Status:** APPROVED" in approval
    assert "`shadow_ready` grants no operational capability" in contract


def test_v3_roadmap_records_accepted_core_and_runtime_candidate() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")
    plan = PLAN.read_text(encoding="utf-8")
    receipt = PG_POS_RECEIPT.read_text(encoding="utf-8")
    registry = roadmap.split("## 2. Status registry", 1)[1].split(
        "## 3. Execution DAG", 1
    )[0]
    backtest_entry = subprocess.check_output(
        ["git", "ls-files", "-s", "backtest"], cwd=ROOT, text=True
    ).split()
    promotion_entry = subprocess.check_output(
        ["git", "ls-files", "-s", "promotion-gate"], cwd=ROOT, text=True
    ).split()

    assert registry.count("| `V3-CON-01` | APPROVED |") == 1
    assert registry.count("| `PG-POS-01` | DONE |") == 1
    assert registry.count("| `PG-POS-RUNTIME-01` | READY_FOR_ACCEPTANCE |") == 1
    assert "PG-POS-RUNTIME-01 [READY_FOR_ACCEPTANCE]" in roadmap
    assert "evaluate_positive(case, policy, status_snapshot, review_result)" in plan
    assert "evaluate_positive_case(validation_report_ref" in plan
    assert promotion_entry[:2] == ["160000", PG_POS_RUNTIME_SHA]
    assert backtest_entry[:2] == ["160000", ACCEPTED_BACKTEST_SHA]
    assert subprocess.run(
        [
            "git",
            "-C",
            "promotion-gate",
            "merge-base",
            "--is-ancestor",
            PG_POS_SHA,
            PG_POS_RUNTIME_SHA,
        ],
        cwd=ROOT,
        check=False,
    ).returncode == 0
    assert subprocess.run(
        ["git", "merge-base", "--is-ancestor", PLATFORM_IMPLEMENTATION_SHA, "HEAD"],
        cwd=ROOT,
        check=False,
    ).returncode == 0
    for expected in (
        FIXTURE_SHA,
        PLATFORM_IMPLEMENTATION_SHA,
        PG_POS_SHA,
        "19 passed",
        "67 passed",
        "315 passed",
        "Status:** ACCEPTED",
    ):
        assert expected in receipt
