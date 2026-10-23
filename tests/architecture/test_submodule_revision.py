from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from tests.support import dependency_revision
from tests.support.dependency_revision import submodule_revision


def init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@x", "commit", "--allow-empty", "-qm", "init"], cwd=path, check=True)


def test_declared_current_gitlink_matches_checked_out_head(tmp_path: Path) -> None:
    child = tmp_path / "backtest"
    child.mkdir()
    init_repo(child)
    root = tmp_path / "root"
    root.mkdir()
    init_repo(root)
    sha = subprocess.check_output(["git", "-C", child, "rev-parse", "HEAD"], text=True).strip()
    subprocess.run(["git", "-C", root, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(child), "backtest"], check=True)
    assert submodule_revision("backtest", root) == sha


@pytest.mark.parametrize("row", [
    "100644 abcdef0123456789abcdef0123456789abcdef01 0\tbacktest",
    "160000 ABCDEF0123456789ABCDEF0123456789ABCDEF 0\tbacktest",
    "160000 zbcdef0123456789abcdef0123456789abcdef01 0\tbacktest",
    "160000 abcdef0123456789abcdef0123456789abcdef01 2\tbacktest",
    "160000 abcdef0123456789abcdef0123456789abcdef01 0\tother",
])
def test_rejects_invalid_mode_stage_or_sha(monkeypatch, tmp_path, row: str) -> None:
    monkeypatch.setattr(dependency_revision.subprocess, "check_output", Mock(return_value=row + "\n"))
    with pytest.raises(ValueError):
        submodule_revision("backtest", tmp_path)


def test_rejects_zero_or_multiple_index_rows(monkeypatch, tmp_path) -> None:
    row = "160000 " + "a" * 40 + " 0\tbacktest\n"
    check = Mock(side_effect=["", row * 2])
    monkeypatch.setattr(dependency_revision.subprocess, "check_output", check)
    for _ in range(2):
        with pytest.raises(ValueError):
            submodule_revision("backtest", tmp_path)


def test_rejects_checkout_mismatch(monkeypatch, tmp_path) -> None:
    check = Mock(side_effect=["160000 " + "a" * 40 + " 0\tbacktest\n", "b" * 40])
    monkeypatch.setattr(dependency_revision.subprocess, "check_output", check)
    with pytest.raises(ValueError, match="checkout differs"):
        submodule_revision("backtest", tmp_path)


@pytest.mark.parametrize("failure", [OSError("read failed"), subprocess.CalledProcessError(1, "git")])
def test_wraps_git_read_failures(monkeypatch, tmp_path, failure) -> None:
    monkeypatch.setattr(dependency_revision.subprocess, "check_output", Mock(side_effect=failure))
    with pytest.raises(ValueError, match="unavailable"):
        submodule_revision("backtest", tmp_path)


def test_rejects_unknown_submodule() -> None:
    with pytest.raises(ValueError, match="unknown"):
        submodule_revision("../backtest")
