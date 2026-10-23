"""Git coordinates only; matching a gitlink is not a clean build or runtime proof.

Installed/build authority still requires public runtime, source identities and
its own dirty-state guards. Do not present a local HEAD as a released build.
"""
from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

SUBMODULES = ("backtest", "foundation", "research-platform", "strategy-validation", "promotion-gate")


def submodule_revision(name: str, root: Path | None = None) -> str:
    if name not in SUBMODULES:
        raise ValueError("unknown dependency submodule")
    root = root or Path(__file__).resolve().parents[2]
    try:
        rows = subprocess.check_output(["git", "ls-files", "--stage", "--", name], cwd=root, text=True).splitlines()
        if len(rows) != 1:
            raise ValueError("dependency must have exactly one staged gitlink")
        fields = rows[0].split()
        if (len(fields) != 4 or fields[0] != "160000" or fields[2:] != ["0", name]
                or len(fields[1]) != 40 or any(c not in "0123456789abcdef" for c in fields[1])):
            raise ValueError("dependency must have one exact staged gitlink")
        checked_out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root / name, text=True).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("dependency Git coordinate is unavailable") from error
    if checked_out != fields[1]:
        raise ValueError("dependency checkout differs from workspace gitlink")
    return fields[1]


def backtest_revision(root: Path | None = None) -> str:
    root = root or Path(__file__).resolve().parents[2]
    project = tomllib.loads((root / "pyproject.toml").read_text())
    source = project["tool"]["uv"]["sources"]["crypto-quant-backtest"]
    if "rev" in source and "path" not in source:
        revision = source["rev"]
        if (type(revision) is not str or len(revision) != 40
                or any(c not in "0123456789abcdef" for c in revision)):
            raise ValueError("Backtest Git revision must be explicit lowercase SHA-1")
        return revision
    if source != {"path": "backtest/packages/backtest-runtime", "editable": True}:
        raise ValueError("Backtest local source must use the exact submodule runtime path")
    package = root / "backtest/packages/backtest-runtime"
    if not (package / "src/crypto_quant_backtest/__init__.py").is_file():
        raise ValueError("local editable Backtest package is unavailable")
    return submodule_revision("backtest", root)
