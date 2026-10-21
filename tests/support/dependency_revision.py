"""Git base coordinate for tests; never editable snapshot or cleanliness proof.

Exact installed/build authority remains the public runtime, source hashes and
dirty-state guards. A local Git HEAD must not be presented as a released build.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


def backtest_revision(root: Path | None = None) -> str:
    import tomllib

    root = root or Path(__file__).resolve().parents[2]
    project = tomllib.loads((root / "pyproject.toml").read_text())
    source = project["tool"]["uv"]["sources"]["crypto-quant-backtest"]
    if "rev" in source and "path" not in source:
        revision = source["rev"]
        if type(revision) is not str or not revision:
            raise ValueError("Backtest Git revision must be explicit")
        return revision
    if "path" not in source or "rev" in source or source.get("editable") is not True:
        raise ValueError("unsupported Backtest source; no historical revision fallback")
    package = (root / source["path"]).resolve()
    if not (package / "src/crypto_quant_backtest/__init__.py").is_file():
        raise ValueError("local editable Backtest package is unavailable")
    try:
        revision = subprocess.check_output(
            ["git", "-C", str(package), "rev-parse", "--verify", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("local editable Backtest Git base is unavailable") from error
    if len(revision) != 40 or any(char not in "0123456789abcdef" for char in revision):
        raise ValueError("local editable Backtest Git base must be canonical")
    return revision
