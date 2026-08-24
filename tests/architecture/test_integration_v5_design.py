from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "overall/integration-v5.md"
ROADMAP = ROOT / "implementation/roadmap.md"
PLAN = ROOT / "implementation/plans/v5-decision-grade-proof.md"
GLOSSARY = ROOT / "CONTEXT.md"
FIXTURE = ROOT / "tests/contracts/integration-v5-decision-grade-proof-v1.json"
APPROVAL = ROOT / "implementation/v5-contract-decision-grade-proof-v1.md"
BT_PORT_02 = ROOT / "tests/contracts/backtest-consumer-port-v2.json"
FIXTURE_SHA = "1bd5ec02c990b87521f26ef42f309dc4dadfe1a62a0739a649040a935e513695"
BT_PORT_02_SHA = "8884f7595a62995eaf296a7ad5f0518745146905da3e2fd69a92587a9423c4a8"
PLATFORM_BT_PORT_02_SHA = "5948dd62f50d197f3e35d499a8e44e04b2257981"
BACKTEST_DRP_03_SHA = "cebb9b033b7eeffbbff712715fc017708ac5a247"
BACKTEST_MODEL_SEAM_SHA = "033344172b24847e73941bb97a06da0490527edf"
BACKTEST_DIVERGENCE_SHA = "cd1d7588ae451a3fa22a2b230b2cd5c3aa65973f"
BACKTEST_FANIN_SHA = "8de544e7794ee05b652355c9809b5454d7ace494"
V5_LOCK_SHA = "75a91665859490d03544066d0585bceec9b6dbe7156cf322b4cb67f95a6a420f"


def test_v5_decision_grade_contract_is_frozen_and_approved() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    approval = APPROVAL.read_text(encoding="utf-8")
    contract = CONTRACT.read_text(encoding="utf-8")

    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == FIXTURE_SHA
    assert hashlib.sha256(BT_PORT_02.read_bytes()).hexdigest() == BT_PORT_02_SHA
    assert fixture["contract_id"] == "integration-v5-decision-grade-proof-v1"
    assert fixture["status"] == "frozen"
    assert fixture["predecessor"]["backtest_consumer_contract"] == "BT-PORT-02"
    assert fixture["predecessor"]["backtest_revision"] == BACKTEST_DRP_03_SHA
    assert fixture["backtest_operations"] == {
        "v1": ["run", "load_completed", "derive", "load_analysis"],
        "v2": ["run", "load_completed_v3", "derive", "load_analysis_v2"],
        "raw_artifact_ref_is_completed": False,
        "heuristic_unwrap_allowed": False,
        "cross_version_retry_or_downgrade_allowed": False,
    }
    assert fixture["admission"] == {
        "artifact": "BacktestEvidenceAdmission@2",
        "fields": ["subject_ref"],
        "subject_variants": [
            "BacktestCanonicalPublicationRefV2",
            "AnalysisArtifactRefV2",
        ],
        "owner_log": "platform.backtest-evidence-admission.v1",
        "completed_verifier": "load_completed_v3",
        "analysis_verifier": "load_analysis_v2",
        "metric_profile_path": "BacktestEvidenceAdmission@1",
        "replay_idempotent": True,
        "version_distinct_event_id": True,
    }
    assert fixture["validation"]["accepted_grade_modes"] == [
        ["development"],
        ["decision_grade"],
    ]
    assert fixture["validation"]["mixed_grade_mode_allowed"] is False
    assert fixture["validation"]["proof_refs_duplicated_in_case_evidence"] is False
    assert fixture["promotion"]["policy_accepts_decision_grade"] is True
    assert fixture["compatibility"]["integration_v1_v4_unchanged"] is True
    assert fixture["compatibility"]["backtest_changes"] == 0
    assert FIXTURE_SHA in approval
    assert BT_PORT_02_SHA in approval
    assert approval.count(
        "| `YungeG` | APPROVED | `2026-08-24T02:48:28Z` |"
    ) == 4
    assert "**Status:** APPROVED" in approval
    assert "never decodes the proof artifacts" in contract


def test_v5_roadmap_records_the_approved_contract_and_execution_dag() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")
    plan = PLAN.read_text(encoding="utf-8")
    glossary = GLOSSARY.read_text(encoding="utf-8")
    registry = roadmap.split("## 2. Status registry", 1)[1].split(
        "## 3. Execution DAG", 1
    )[0]
    backtest_entry = subprocess.check_output(
        ["git", "ls-files", "-s", "backtest"], cwd=ROOT, text=True
    ).split()

    assert registry.count("| `BT-PORT-02` | DONE |") == 1
    assert registry.count("| `V5-CON-01` | APPROVED |") == 1
    assert registry.count("| `V5-PIN-01` | READY_FOR_ACCEPTANCE |") == 1
    for node in (
        "DG-ADM-01",
        "RP-DG-01",
        "SV-DG-01",
        "PG-DG-01",
        "DG-THIN-01",
        "FI-04",
    ):
        assert registry.count(f"| `{node}` | BLOCKED |") == 1
    assert "FI-03 + BT-PORT-02 ─→ V5-CON-01 [APPROVED]" in roadmap
    assert "V5-PIN-01 [READY_FOR_ACCEPTANCE]" in roadmap
    assert BACKTEST_MODEL_SEAM_SHA in plan
    assert BACKTEST_DRP_03_SHA in plan
    assert BACKTEST_FANIN_SHA in plan
    assert "Backtest:     2438 passed" in plan
    assert "Platform RP:  90 passed" in plan
    assert "BacktestEvidenceAdmission@2(subject_ref)" in plan
    assert "## `V5-PIN-01`" in plan
    assert "## `DG-ADM-01`" in plan
    assert "## `RP-DG-01`" in plan
    assert "## `SV-DG-01`" in plan
    assert "## `PG-DG-01`" in plan
    assert "## `DG-THIN-01`" in plan
    assert "## `FI-04`" in plan
    assert "**BacktestEvidenceAdmission**" in glossary
    assert subprocess.run(
        ["git", "merge-base", "--is-ancestor", PLATFORM_BT_PORT_02_SHA, "HEAD"],
        cwd=ROOT,
        check=False,
    ).returncode == 0
    assert backtest_entry[:2] == ["160000", BACKTEST_FANIN_SHA]
    assert subprocess.check_output(
        ["git", "-C", "backtest", "merge-base", BACKTEST_MODEL_SEAM_SHA, BACKTEST_DRP_03_SHA],
        cwd=ROOT,
        text=True,
    ).strip() == BACKTEST_DIVERGENCE_SHA
    for capability_sha in (BACKTEST_MODEL_SEAM_SHA, BACKTEST_DRP_03_SHA):
        assert subprocess.run(
            [
                "git",
                "-C",
                "backtest",
                "merge-base",
                "--is-ancestor",
                capability_sha,
                BACKTEST_FANIN_SHA,
            ],
            cwd=ROOT,
            check=False,
        ).returncode == 0

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert pyproject.count(BACKTEST_FANIN_SHA) == 5
    assert hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest() == V5_LOCK_SHA
    assert BACKTEST_FANIN_SHA in lock
    for superseded_pin in (BACKTEST_MODEL_SEAM_SHA, BACKTEST_DRP_03_SHA):
        assert superseded_pin not in pyproject
        assert superseded_pin not in lock
