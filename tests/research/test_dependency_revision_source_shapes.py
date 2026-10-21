"""Test Git-coordinate helper; editable base is not installed/snapshot authority."""
from __future__ import annotations

import subprocess

import pytest

from tests.support.dependency_revision import backtest_revision


def _project(root, source):
    (root / "pyproject.toml").write_text("[tool.uv.sources]\ncrypto-quant-backtest = { " + source + " }\n")


def test_git_pin_path_preserves_declared_revision_without_git_process(tmp_path, monkeypatch):
    _project(tmp_path, 'git = "https://example.invalid/repo", rev = "' + "a" * 40 + '"')
    def forbidden(*args, **kwargs):
        pytest.fail("pinned source must not inspect local Git")
    monkeypatch.setattr(subprocess, "check_output", forbidden)
    assert backtest_revision(tmp_path) == "a" * 40


def test_editable_source_reports_only_actual_git_base_and_does_not_infer_clean(tmp_path, monkeypatch):
    _project(tmp_path, 'path = "backtest/packages/backtest-runtime", editable = true')
    package = tmp_path / "backtest/packages/backtest-runtime"
    file = package / "src/crypto_quant_backtest/__init__.py"
    file.parent.mkdir(parents=True)
    file.write_text("# dirty local test package\n")
    def git(args, *, cwd, text):
        assert text
        if args == ["git", "ls-files", "--stage", "--", "backtest"]:
            assert cwd == tmp_path
            return "160000 " + "b" * 40 + " 0\tbacktest\n"
        assert args == ["git", "rev-parse", "HEAD"] and cwd == tmp_path / "backtest"
        return "b" * 40 + "\n"
    monkeypatch.setattr(subprocess, "check_output", git)
    assert backtest_revision(tmp_path) == "b" * 40
    assert file.read_text() == "# dirty local test package\n"


@pytest.mark.parametrize("source", ['path = "absent", editable = false',
    'path = "absent", editable = true', 'git = "https://example.invalid/repo"',
    'path = "absent", rev = "abc", editable = true'])
def test_unknown_or_unavailable_source_never_substitutes_historical_sha(tmp_path, source):
    _project(tmp_path, source)
    with pytest.raises(ValueError):
        backtest_revision(tmp_path)
