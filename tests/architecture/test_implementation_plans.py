from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROADMAP = ROOT / "implementation/roadmap.md"
PLAN_DIR = ROOT / "implementation/plans"
P00_PLAT_RECEIPT = ROOT / "implementation/p00-plat-01-receipt.md"
P00_BTA_RECEIPT = ROOT / "implementation/p00-bta-01-receipt.md"
P00_SEAM_RECEIPT = ROOT / "implementation/p00-seam-01-receipt.md"
PLAT_ADM_RECEIPT = ROOT / "implementation/plat-adm-01-receipt.md"
RP_THIN_RECEIPT = ROOT / "implementation/rp-thin-02-receipt.md"
SV_THIN_RECEIPT = ROOT / "implementation/sv-thin-01-receipt.md"
PLAN_FILES = {
    "PF-LOG-01": PLAN_DIR / "foundation.md",
    "PF-CORE-01": PLAN_DIR / "foundation.md",
    "RP-CORE-02": PLAN_DIR / "research.md",
    "RP-SHELL-01": PLAN_DIR / "research.md",
    "RP-THIN-02": PLAN_DIR / "research.md",
    "SV-CORE-01": PLAN_DIR / "validation.md",
    "SV-LEDGER-01": PLAN_DIR / "validation.md",
    "SV-SHELL-01": PLAN_DIR / "validation.md",
    "SV-THIN-01": PLAN_DIR / "validation.md",
    "PG-CORE-01": PLAN_DIR / "promotion.md",
    "PG-LEDGER-01": PLAN_DIR / "promotion.md",
    "PG-SHELL-01": PLAN_DIR / "promotion.md",
    "PG-THIN-01": PLAN_DIR / "promotion.md",
    "P00-SEAM-01": PLAN_DIR / "fan-in.md",
    "PLAT-ADM-01": PLAN_DIR / "fan-in.md",
    "FI-01": PLAN_DIR / "fan-in.md",
}


def test_roadmap_is_the_single_mutable_status_registry() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")
    assert "sole mutable status registry" in roadmap
    status_registry = roadmap.split("## 2. Status registry", 1)[1].split(
        "## 3. Execution DAG", 1
    )[0]
    assert "| `PF-LOG-01` | DONE |" in status_registry

    for node, owner in PLAN_FILES.items():
        assert status_registry.count(f"| `{node}` |") == 1
        text = owner.read_text(encoding="utf-8")
        assert f"## `{node}`" in text
        assert "Mutable status authority" in text
        assert "status: " not in text


def test_p00_platform_receipt_binds_the_clean_workspace_revision() -> None:
    receipt = P00_PLAT_RECEIPT.read_text(encoding="utf-8")
    roadmap = ROADMAP.read_text(encoding="utf-8")

    for value in (
        "bb75f2d903111be55be23bcb2d730c8cdec3bf3a",
        "9e5937895d7559b8537a4595d73b6aabc94f6f13",
        "8eb23bf50135257476e49e3795ebe4b8acb33ba17957cf45dc32262db426ad78",
        "7dfc93cbd2f3f9993782142bed47e54151f620b04fad0a6599aef90dffdefb81",
        "248 passed",
        "Pre-validation status:** clean",
        "Post-validation status:** clean",
    ):
        assert value in receipt
    assert "| `P00-PLAT-01` | DONE |" in roadmap
    assert "does not close `P00-BTA-01` or `P00-SEAM-01`" in receipt


def test_p00_backtest_and_seam_receipts_bind_the_clean_revision() -> None:
    bta = P00_BTA_RECEIPT.read_text(encoding="utf-8")
    seam = P00_SEAM_RECEIPT.read_text(encoding="utf-8")
    roadmap = ROADMAP.read_text(encoding="utf-8")

    for value in (
        "7aa76dc2de65fb713a146e27651538dd755d5231",
        "e3c04fb612d6798aef1420b60864d4f315ed12ac",
        "9d88ed67a84d06c558276f8bae2206b069bcec8f",
        "d96c6ebf36bbb9baf332e956be220c9d01bbb7d2010b82e9568d54ddcd6d39b6",
        "257 passed",
    ):
        assert value in bta or value in seam
    assert "Pre/post validation status:** clean" in bta
    assert "| `P00-BTA-01` | DONE |" in roadmap
    assert "| `P00-SEAM-01` | DONE |" in roadmap
    assert "does not admit evidence into Platform governance" in seam


def test_platform_admission_receipt_binds_the_clean_revision() -> None:
    receipt = PLAT_ADM_RECEIPT.read_text(encoding="utf-8")
    roadmap = ROADMAP.read_text(encoding="utf-8")

    for value in (
        "bb68146da4b188e4da114ff7adaaa594c47a49f7",
        "92810375fdf6c0c48c1edaeade74b97755f20220",
        "266 passed",
        "Pre/post validation status:** clean",
        "c1fc5ae645cefd11c301a4dff4f8c4f77c2692eeb026b7f04c1557ac70d2f92f",
        "3c4f1b4d138b5377bc37222c775b1b640da62053fb8e5d8f23aa0cf82e009a8e",
    ):
        assert value in receipt
    assert "| `PLAT-ADM-01` | DONE |" in roadmap
    assert "does not produce Research, Validation, Promotion, or FI receipts" in receipt


def test_research_thin_receipt_binds_the_clean_revision() -> None:
    receipt = RP_THIN_RECEIPT.read_text(encoding="utf-8")
    roadmap = ROADMAP.read_text(encoding="utf-8")

    for value in (
        "e262c1cbde25e7d6283a11e624855155692c0171",
        "330aa4539f6ddbb874e7f29f9125d075037c732f",
        "270 passed",
        "Pre/post validation status:** clean",
        "7715e57668368cc8a6358fe06801173897af5d86d3ca82e2f1813aa5023d161d",
        "905fbd19e1c1c36fafdc92c9167dbfa0d7ca256547fdfb25a7b66da7b38d33c1",
    ):
        assert value in receipt
    assert "| `RP-THIN-02` | DONE |" in roadmap
    assert "Validation, Promotion, and FI receipts remain downstream" in receipt


def test_validation_thin_receipt_binds_the_clean_revision() -> None:
    receipt = SV_THIN_RECEIPT.read_text(encoding="utf-8")
    roadmap = ROADMAP.read_text(encoding="utf-8")

    for value in (
        "b84346cfe42ca0d75021e2b08b9a81445225d7e8",
        "692f6ca1a471ec7ccf7e284a4a71ed30652b3661",
        "275 passed",
        "Pre/post validation status:** clean",
        "2e4563b8de7dd8c06798508f611bf7caacc28b11769bd71fa1348be97de5cfba",
        "74e4386fb11bdf79ca606c62c2d2158ce87fa2a77745834426a1dcfe243febb5",
    ):
        assert value in receipt
    assert "| `SV-THIN-01` | DONE |" in roadmap
    assert "Promotion and FI receipts remain downstream" in receipt


def test_module_plans_have_deep_interface_and_acceptance_sections() -> None:
    for name in ("foundation.md", "research.md", "validation.md", "promotion.md"):
        text = (PLAN_DIR / name).read_text(encoding="utf-8")
        for required in (
            "## Execution DAG",
            "### Outcome",
            "### Failure precedence",
            "### Acceptance",
            "## Dependencies",
            "## Exclusions",
        ):
            assert required in text, f"{name} missing {required}"

    assert "SV-LEDGER-01.reserve()" in (PLAN_DIR / "research.md").read_text(
        encoding="utf-8"
    )
    assert "platform.backtest-evidence-admission.v1" in (
        PLAN_DIR / "promotion.md"
    ).read_text(encoding="utf-8")
    fan_in = (PLAN_DIR / "fan-in.md").read_text(encoding="utf-8")
    assert "not a fifth installable package" in fan_in
    assert "parallel package fan-out" in ROADMAP.read_text(encoding="utf-8")
    for shell in ("RP-SHELL-01", "SV-SHELL-01", "PG-SHELL-01"):
        assert shell in fan_in


def test_planned_dependency_graph_is_acyclic() -> None:
    dependencies = {
        "PF-LOG-01": (),
        "PF-CORE-01": ("PF-LOG-01",),
        "SV-LEDGER-01": ("PF-CORE-01",),
        "PG-LEDGER-01": ("PF-CORE-01",),
        "RP-SHELL-01": ("PF-CORE-01", "SV-LEDGER-01"),
        "SV-SHELL-01": ("PF-CORE-01", "SV-LEDGER-01"),
        "PG-SHELL-01": ("PF-CORE-01", "PG-LEDGER-01"),
        "P00-SEAM-01": ("PF-CORE-01",),
        "PLAT-ADM-01": ("PF-CORE-01", "P00-SEAM-01"),
        "RP-THIN-02": ("RP-SHELL-01", "P00-SEAM-01"),
        "SV-THIN-01": ("SV-SHELL-01", "RP-THIN-02", "P00-SEAM-01"),
        "PG-THIN-01": ("PG-SHELL-01", "SV-THIN-01", "PLAT-ADM-01"),
        "FI-01": ("RP-THIN-02", "SV-THIN-01", "PG-THIN-01"),
    }
    remaining = set(dependencies)
    completed: set[str] = set()
    while remaining:
        ready = {
            node
            for node in remaining
            if set(dependencies[node]).isdisjoint(remaining)
        }
        assert ready, f"dependency cycle: {sorted(remaining)}"
        completed.update(ready)
        remaining -= ready

    assert completed == set(dependencies)
