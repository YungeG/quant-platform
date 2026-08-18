from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "overall/integration-v2.md"
ROADMAP = ROOT / "implementation/roadmap.md"
GLOSSARY = ROOT / "CONTEXT.md"
PROTECTED_V1 = ROOT / "foundation/tests/fixtures/architecture/p00-contract-v1.json"
PLAN_DIR = ROOT / "implementation/plans"


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
        "V2-CON-01": "ACTIVE",
        "MB-CORE-01": "WAITING_CONTRACT",
        "BT-MODEL-01": "WAITING_CONTRACT",
        "RP-MODEL-01": "WAITING_CORE_SEAM",
        "V2-SEAM-01": "WAITING_PROVIDER",
        "SV-MODEL-01": "WAITING_RESEARCH",
        "PG-MODEL-01": "WAITING_VALIDATION",
        "FI-02": "WAITING_LEAVES",
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
