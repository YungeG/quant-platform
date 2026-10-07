"""Old Git pins and clean local submodule dependency identities."""
from pathlib import Path

import pytest
from tests.support import dependency_revision as probe


def _project(tmp_path, monkeypatch, source):
    root = tmp_path / "platform"
    path = root / "tests/support/dependency_revision.py"
    path.parent.mkdir(parents=True)
    (root / "backtest").mkdir()
    (root / "pyproject.toml").write_text("[tool.uv.sources]\ncrypto-quant-backtest = " + source + "\n")
    monkeypatch.setattr(probe, "__file__", str(path))
    return root


def test_old_git_revision_is_preserved_without_git_io(tmp_path, monkeypatch):
    _project(tmp_path, monkeypatch, '{ git = "https://example.invalid/backtest", rev = "' + "a" * 40 + '", subdirectory = "packages/backtest-runtime" }')
    def forbidden(*args, **kwargs):
        pytest.fail("an existing explicit rev must not be re-inferred")
    monkeypatch.setattr(probe.subprocess, "check_output", forbidden)
    assert probe.backtest_revision() == "a" * 40


def test_local_source_is_bound_to_the_exact_gitlink_checkout(tmp_path, monkeypatch):
    root = _project(tmp_path, monkeypatch, '{ path = "backtest/packages/backtest-runtime", editable = true }')
    calls = []
    def checked(command, *, cwd, text):
        calls.append((command, Path(cwd)))
        if "ls-files" in command:
            assert Path(cwd) == root
            return "160000 " + "b" * 40 + " 0\tbacktest\n"
        assert command == ["git", "rev-parse", "HEAD"] and Path(cwd) == root / "backtest"
        return "b" * 40 + "\n"
    monkeypatch.setattr(probe.subprocess, "check_output", checked)
    assert probe.backtest_revision() == "b" * 40
    assert len(calls) == 2


@pytest.mark.parametrize("part", ("wrong_path", "checkout_mismatch", "conflicted_gitlink", "missing_gitlink"))
def test_local_source_rejects_unsupported_or_unpinned_identity(tmp_path, monkeypatch, part):
    source = '{ path = "backtest/packages/backtest-runtime", editable = true }'
    if part == "wrong_path":
        source = '{ path = "some-other-dirty-directory", editable = true }'
    _project(tmp_path, monkeypatch, source)
    def checked(command, **kwargs):
        if "ls-files" in command:
            if part == "missing_gitlink":
                return ""
            return "160000 " + "b" * 40 + (" 1" if part == "conflicted_gitlink" else " 0") + "\tbacktest\n"
        return ("c" if part == "checkout_mismatch" else "b") * 40 + "\n"
    monkeypatch.setattr(probe.subprocess, "check_output", checked)
    with pytest.raises(ValueError):
        probe.backtest_revision()
