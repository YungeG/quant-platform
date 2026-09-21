"""Current runtime authority comes from the workspace pin, not historical receipts."""

import tomllib
from pathlib import Path


def backtest_revision() -> str:
    root = Path(__file__).resolve().parents[2]
    project = tomllib.loads((root / "pyproject.toml").read_text())
    return project["tool"]["uv"]["sources"]["crypto-quant-backtest"]["rev"]
