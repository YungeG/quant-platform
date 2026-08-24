from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "overall/integration-v2.md"
ROADMAP = ROOT / "implementation/roadmap.md"
GLOSSARY = ROOT / "CONTEXT.md"
PROTECTED_V1 = ROOT / "foundation/tests/fixtures/architecture/p00-contract-v1.json"
PLAN_DIR = ROOT / "implementation/plans"
FIXTURE = ROOT / "tests/contracts/integration-v2-model-build-v1.json"
APPROVAL = ROOT / "implementation/v2-contract-model-build-v1.md"
BT_MODEL_RECEIPT = ROOT / "implementation/bt-model-01-receipt.md"
V2_SEAM_RECEIPT = ROOT / "implementation/v2-seam-01-receipt.md"
RP_MODEL_RECEIPT = ROOT / "implementation/rp-model-01-receipt.md"
SV_MODEL_RECEIPT = ROOT / "implementation/sv-model-01-receipt.md"
PG_MODEL_RECEIPT = ROOT / "implementation/pg-model-01-receipt.md"
FI_02_RECEIPT = ROOT / "implementation/fi-02-receipt.md"
FIXTURE_SHA = "4d6c764b6e0b6374daab462b8b74ce8c9f75b73b68d96979d3e7d3a99bd441bb"
HISTORICAL_BT_MODEL_SHA = "033344172b24847e73941bb97a06da0490527edf"
CURRENT_BACKTEST_GITLINK_SHA = "8de544e7794ee05b652355c9809b5454d7ace494"
V2_SEAM_RESEARCH_SHA = "51897c2118828febc844e9b21980e31cf0760138"
RP_MODEL_SHA = "f05c91b2fa75826fb0439ccdcb0d2ae507bff013"
MODEL_LEDGER_SHA = "256e17c2f528f374e1041cd16d7e829f1f120556"
SV_RESEARCH_SHA = "9251222d4fa2f3ec548161e6949bf117e30d9348"
SV_MODEL_SHA = "acf2e36ed009deeee399744508e83af16cdc90d9"
PG_RESEARCH_SHA = "d2dd913a1efd23728c7889bd15c894d6cf22ad4e"
PG_VALIDATION_SHA = "41c35219d227fe5cdb736747b917144f6b8a8c65"
PG_MODEL_SHA = "966b5984c430ec61c53b15761099d2620ed028e6"
FI_02_GOLDEN_SHA = "92f320affa1c41afdadab1cb1c0a7ec6b7672105"
V2_LOCK_SHA = "dcfeab99dfdf28daa9206d8f94315740d288c7f43df89d6ccc21e415e25101ef"


def test_v2_protected_fixture_and_both_owner_approvals_match() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    approval = APPROVAL.read_text(encoding="utf-8")

    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == FIXTURE_SHA
    assert fixture["contract_id"] == "integration-v2-model-build-v1"
    assert fixture["status"] == "frozen"
    assert fixture["ownership"]["backtest"] == [
        "ModelArtifactRef",
        "ModelRevisionTimeline",
        "point-in-time model visibility",
        "model-aware request, invocation, and SemanticRun identity",
    ]
    assert fixture["schemas"]["ModelBuildPlan@1"] == [
        "feature_recipe_ref",
        "trainer_recipe_ref",
        "training_slice",
        "seed",
    ]
    assert fixture["task_universe"]["null_plan"]["v1_identity_unchanged"] is True
    assert fixture["task_universe"]["non_null_plan"]["total"] == 10
    assert fixture["trial_binding"] == {
        "declaration_binding": ["primary_model", "model_build_plan_ref"],
        "result_time_evidence_in_trial_identity": False,
        "trial_spec_resolved_value": "crypto_quant_backtest.ModelArtifactRef",
        "resolution_requires_completed_model_training": True,
    }
    assert fixture["model_evidence_rules"]["platform_duplicates_model_artifact_ref"] is False
    assert fixture["model_evidence_rules"]["cross_clock_publication_comparison"] is False
    assert fixture["backtest_binding"]["failure_phase"] == "before Attempt creation"
    assert FIXTURE_SHA in approval
    assert "| Platform | `YungeG` | APPROVED |" in approval
    assert "| Backtest | `YungeG` | APPROVED |" in approval


def test_bt_model_receipt_and_superproject_pin_match() -> None:
    receipt = BT_MODEL_RECEIPT.read_text(encoding="utf-8")
    index_entry = subprocess.check_output(
        ["git", "ls-files", "-s", "backtest"], cwd=ROOT, text=True
    ).split()

    assert index_entry[:2] == ["160000", CURRENT_BACKTEST_GITLINK_SHA]
    assert HISTORICAL_BT_MODEL_SHA in receipt
    assert "1861 passed" in receipt
    assert "Status:** ACCEPTED" in receipt


def test_v2_seam_receipt_pins_research_and_root_lock() -> None:
    receipt = V2_SEAM_RECEIPT.read_text(encoding="utf-8")
    research_entry = subprocess.check_output(
        ["git", "ls-files", "-s", "research-platform"], cwd=ROOT, text=True
    ).split()

    assert research_entry[0] == "160000"
    assert subprocess.run(
        [
            "git",
            "-C",
            "research-platform",
            "merge-base",
            "--is-ancestor",
            V2_SEAM_RESEARCH_SHA,
            research_entry[1],
        ],
        cwd=ROOT,
        check=False,
    ).returncode == 0
    assert V2_SEAM_RESEARCH_SHA in receipt
    assert HISTORICAL_BT_MODEL_SHA in receipt
    assert V2_LOCK_SHA in receipt
    assert "294 passed" in receipt


def test_rp_model_receipt_pins_research_and_validation_ledger() -> None:
    receipt = RP_MODEL_RECEIPT.read_text(encoding="utf-8")
    research_entry = subprocess.check_output(
        ["git", "ls-files", "-s", "research-platform"], cwd=ROOT, text=True
    ).split()
    validation_entry = subprocess.check_output(
        ["git", "ls-files", "-s", "strategy-validation"], cwd=ROOT, text=True
    ).split()

    assert research_entry[0] == "160000"
    assert validation_entry[0] == "160000"
    assert subprocess.run(
        [
            "git",
            "-C",
            "research-platform",
            "merge-base",
            "--is-ancestor",
            RP_MODEL_SHA,
            research_entry[1],
        ],
        cwd=ROOT,
        check=False,
    ).returncode == 0
    assert subprocess.run(
        [
            "git",
            "-C",
            "strategy-validation",
            "merge-base",
            "--is-ancestor",
            MODEL_LEDGER_SHA,
            validation_entry[1],
        ],
        cwd=ROOT,
        check=False,
    ).returncode == 0
    assert RP_MODEL_SHA in receipt
    assert MODEL_LEDGER_SHA in receipt
    assert "301 passed" in receipt


def test_sv_model_receipt_pins_validation_and_research_observation() -> None:
    receipt = SV_MODEL_RECEIPT.read_text(encoding="utf-8")
    research_entry = subprocess.check_output(
        ["git", "ls-files", "-s", "research-platform"], cwd=ROOT, text=True
    ).split()
    validation_entry = subprocess.check_output(
        ["git", "ls-files", "-s", "strategy-validation"], cwd=ROOT, text=True
    ).split()

    assert research_entry[0] == "160000"
    assert validation_entry[0] == "160000"
    assert subprocess.run(
        [
            "git",
            "-C",
            "research-platform",
            "merge-base",
            "--is-ancestor",
            SV_RESEARCH_SHA,
            research_entry[1],
        ],
        cwd=ROOT,
        check=False,
    ).returncode == 0
    assert subprocess.run(
        [
            "git",
            "-C",
            "strategy-validation",
            "merge-base",
            "--is-ancestor",
            SV_MODEL_SHA,
            validation_entry[1],
        ],
        cwd=ROOT,
        check=False,
    ).returncode == 0
    assert SV_RESEARCH_SHA in receipt
    assert SV_MODEL_SHA in receipt
    assert "305 passed" in receipt


def test_pg_model_receipt_pins_all_governed_model_revisions() -> None:
    receipt = PG_MODEL_RECEIPT.read_text(encoding="utf-8")
    research_entry = subprocess.check_output(
        ["git", "ls-files", "-s", "research-platform"], cwd=ROOT, text=True
    ).split()
    validation_entry = subprocess.check_output(
        ["git", "ls-files", "-s", "strategy-validation"], cwd=ROOT, text=True
    ).split()
    promotion_revision = subprocess.check_output(
        ["git", "-C", "promotion-gate", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()

    assert research_entry[:2] == ["160000", PG_RESEARCH_SHA]
    assert validation_entry[:2] == ["160000", PG_VALIDATION_SHA]
    assert subprocess.run(
        [
            "git",
            "-C",
            "promotion-gate",
            "merge-base",
            "--is-ancestor",
            PG_MODEL_SHA,
            promotion_revision,
        ],
        cwd=ROOT,
        check=False,
    ).returncode == 0
    assert PG_RESEARCH_SHA in receipt
    assert PG_VALIDATION_SHA in receipt
    assert PG_MODEL_SHA in receipt
    assert "308 passed" in receipt


def test_fi_02_receipt_closes_all_v2_leaves_and_preserves_v1() -> None:
    receipt = FI_02_RECEIPT.read_text(encoding="utf-8")

    assert subprocess.run(
        ["git", "merge-base", "--is-ancestor", FI_02_GOLDEN_SHA, "HEAD"],
        cwd=ROOT,
        check=False,
    ).returncode == 0
    assert FI_02_GOLDEN_SHA in receipt
    assert V2_LOCK_SHA in receipt
    assert "Fresh remote recursive clone" in receipt
    assert "310 passed" in receipt
    for leaf in (
        BT_MODEL_RECEIPT,
        V2_SEAM_RECEIPT,
        RP_MODEL_RECEIPT,
        SV_MODEL_RECEIPT,
        PG_MODEL_RECEIPT,
    ):
        assert leaf.is_file()
    assert hashlib.sha256(PROTECTED_V1.read_bytes()).hexdigest() == (
        "aebb1be1894d739b06856e012e4343d7835fc1ed0306d8c28a4bfb1d8025b782"
    )


def test_v2_contract_is_additive_model_provenance_not_a_second_runtime() -> None:
    contract = CONTRACT.read_text(encoding="utf-8")

    for required in (
        "FeatureRecipe@1",
        "TrainerRecipe@1",
        "ModelBuildPlan@1",
        "FeatureBuildTask@1",
        "ModelTrainingTask@1",
        "FeatureDatasetManifest@1",
        "ModelBuildEvidence@1",
        "Backtest.ModelArtifactRef",
        "2 ModelBuild + 4 Trial + 4 Analysis = 10",
        "PromotionDecision = needs_more_evidence",
    ):
        assert required in contract
    assert "Platform never duplicates `ModelArtifactRef`" in contract
    assert "actual feature matrix wire format or model byte format" in contract
    assert "Python callable/Protocol/plugin ABI" in contract


def test_v2_roadmap_has_one_active_contract_node_and_an_acyclic_fan_in() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")
    registry = roadmap.split("## 2. Status registry", 1)[1].split(
        "## 3. Execution DAG", 1
    )[0]

    expected = {
        "V2-CON-01": "DONE",
        "MB-CORE-01": "DONE",
        "BT-MODEL-01": "DONE",
        "RP-MODEL-01": "DONE",
        "V2-SEAM-01": "DONE",
        "SV-MODEL-01": "DONE",
        "PG-MODEL-01": "DONE",
        "FI-02": "DONE",
    }
    for node, state in expected.items():
        assert registry.count(f"| `{node}` | {state} |") == 1
    assert "MB-CORE-01 ───────────────┐" in roadmap
    assert "BT-MODEL-01 ────────┐" in roadmap
    assert "SV-MODEL-01" in roadmap
    assert "PG-MODEL-01" in roadmap


def test_v2_plans_keep_status_in_the_roadmap_and_name_deep_interfaces() -> None:
    plans = {
        "v2-contract.md": ("V2-CON-01",),
        "v2-research-model-build.md": ("MB-CORE-01", "RP-MODEL-01"),
        "v2-backtest-model.md": ("BT-MODEL-01", "V2-SEAM-01"),
        "v2-fan-in.md": ("SV-MODEL-01", "PG-MODEL-01", "FI-02"),
    }
    for name, nodes in plans.items():
        text = (PLAN_DIR / name).read_text(encoding="utf-8")
        assert "Mutable status authority" in text
        assert "status: " not in text
        assert "### Outcome" in text
        assert "### Dependencies" in text
        assert "### Exclusions" in text
        for node in nodes:
            assert f"## `{node}`" in text
    assert "one deep orchestration interface" in (
        PLAN_DIR / "v2-research-model-build.md"
    ).read_text(encoding="utf-8")


def test_v2_glossary_is_implementation_free_and_v1_fixture_is_unchanged() -> None:
    glossary = GLOSSARY.read_text(encoding="utf-8")
    for term in (
        "**FeatureRecipe**",
        "**TrainerRecipe**",
        "**ModelBuildPlan**",
        "**FeatureDatasetManifest**",
        "**ModelBuildEvidence**",
    ):
        assert term in glossary
    assert hashlib.sha256(PROTECTED_V1.read_bytes()).hexdigest() == (
        "aebb1be1894d739b06856e012e4343d7835fc1ed0306d8c28a4bfb1d8025b782"
    )
