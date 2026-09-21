"""A newer checkout must not hide an older locked or installed Backtest cohort."""

import importlib.metadata
import json
import re
import subprocess
import tomllib
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = (
    "crypto-quant-backtest",
    "crypto-quant-bundle-builder",
    "crypto-quant-domain",
    "crypto-quant-market-data",
    "crypto-quant-trading",
)


def _revision() -> str:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    sources = project["tool"]["uv"]["sources"]
    revisions = {sources[name]["rev"] for name in PACKAGES}
    assert len(revisions) == 1, "Backtest packages must use the same Git revision"
    revision = revisions.pop()
    assert re.fullmatch(r"[0-9a-f]{40}", revision), "Pin an immutable full commit"
    return revision


def test_submodule_checkout_and_lock_match_declared_backtest_revision() -> None:
    revision = _revision()
    gitlink = subprocess.check_output(
        ["git", "-C", str(ROOT), "ls-files", "--stage", "--", "backtest"],
        text=True, timeout=10,
    ).split()
    assert gitlink == ["160000", revision, "0", "backtest"], "Gitlink and dependency pin differ"
    checkout = subprocess.check_output(
        ["git", "-C", str(ROOT / "backtest"), "rev-parse", "HEAD"],
        text=True, timeout=10,
    ).strip()
    assert checkout == revision, "Backtest source checkout is not the pinned revision"
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    packages = {package["name"]: package for package in lock["package"]}
    for name in PACKAGES:
        source = urlsplit(packages[name]["source"]["git"])
        assert source.fragment == revision, f"{name}: lock resolves a different revision"
        assert parse_qs(source.query)["rev"] == [revision]


def test_installed_cohort_matches_pin_and_has_public_cn_preparation() -> None:
    revision = _revision()
    for name in PACKAGES:
        distribution = importlib.metadata.distribution(name)
        direct_url = json.loads(distribution.read_text("direct_url.json") or "{}")
        assert direct_url.get("vcs_info", {}).get("commit_id") == revision, (
            f"{name}: installed source differs from the pin; use this worktree's synced environment"
        )
    import crypto_quant_backtest as backtest

    assert callable(getattr(backtest, "prepare_cn_a_share_development_backtest", None))
