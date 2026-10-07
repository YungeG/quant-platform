"""Current runtime authority comes from the workspace pin, not historical receipts."""

import subprocess
import tomllib
from pathlib import Path


def backtest_revision() -> str:
    root = Path(__file__).resolve().parents[2]
    project = tomllib.loads((root / "pyproject.toml").read_text())
    source = project["tool"]["uv"]["sources"]["crypto-quant-backtest"]
    if "rev" in source:
        return source["rev"]
    if source != {"path": "backtest/packages/backtest-runtime", "editable": True}:
        raise ValueError("Backtest local source must use the exact submodule runtime path")
    entry = subprocess.check_output(
        ["git", "ls-files", "--stage", "--", "backtest"], cwd=root, text=True
    ).strip().split()
    if len(entry) != 4 or entry[0] != "160000" or entry[2:] != ["0", "backtest"]:
        raise ValueError("Backtest dependency must have one exact staged gitlink")
    checked_out = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root / "backtest", text=True
    ).strip()
    if checked_out != entry[1]:
        raise ValueError("Backtest checkout differs from the workspace gitlink")
    return entry[1]
