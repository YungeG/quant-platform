from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROADMAP = ROOT / "implementation/roadmap.md"
PLAN_DIR = ROOT / "implementation/plans"
P00_PLAT_RECEIPT = ROOT / "implementation/p00-plat-01-receipt.md"
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
