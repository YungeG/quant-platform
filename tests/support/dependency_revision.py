"""Git coordinates only; matching a gitlink is not a clean build or runtime proof.

Installed/build authority still requires public runtime, source identities and
its own dirty-state guards. Do not present a local HEAD as a released build.
"""
from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path


def backtest_revision(root: Path | None = None) -> str:
    root = root or Path(__file__).resolve().parents[2]
    project = tomllib.loads((root / "pyproject.toml").read_text())
    source = project["tool"]["uv"]["sources"]["crypto-quant-backtest"]
    if "rev" in source and "path" not in source:
        revision = source["rev"]
        if type(revision) is not str or not revision:
            raise ValueError("Backtest Git revision must be explicit")
        return revision
    if source != {"path": "backtest/packages/backtest-runtime", "editable": True}:
        raise ValueError("Backtest local source must use the exact submodule runtime path")
    package = root / "backtest/packages/backtest-runtime"
    if not (package / "src/crypto_quant_backtest/__init__.py").is_file():
        raise ValueError("local editable Backtest package is unavailable")
    try:
        entry = subprocess.check_output(
            ["git", "ls-files", "--stage", "--", "backtest"], cwd=root, text=True
        ).strip().split()
        if (len(entry) != 4 or entry[0] != "160000" or entry[2:] != ["0", "backtest"]
                or len(entry[1]) != 40 or any(c not in "0123456789abcdef" for c in entry[1])):
            raise ValueError("Backtest dependency must have one exact staged gitlink")
        checked_out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root / "backtest", text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("local editable Backtest Git base is unavailable") from error
    if checked_out != entry[1]:
        raise ValueError("Backtest checkout differs from the workspace gitlink")
    return entry[1]
