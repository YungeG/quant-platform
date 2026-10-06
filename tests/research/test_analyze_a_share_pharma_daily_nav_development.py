"""Root NAV consumer guards; no producer/source bypass or financial arithmetic."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
from crypto_quant_domain import ArtifactEnvelope, ArtifactRef, canonical_bytes
from crypto_quant_foundation import LocalFoundation, FoundationFailure
from experiments import analyze_a_share_pharma_daily_nav_development as nav


def test_exact_namespace_routing_has_no_source_fallback(tmp_path):
    original = LocalFoundation(tmp_path / "old")
    source = ArtifactEnvelope.create("original_readonly_source", 1, {"value": "immutable"})
    ref = original.put(envelope=source)
    store = nav._NavArtifactStore(tmp_path / "old", tmp_path / "new")
    assert store.read(ref=ref).source_bytes == canonical_bytes(source)
    with pytest.raises(ValueError, match="exact derived namespaces"):
        store.put(envelope=source)
    with pytest.raises(FoundationFailure):
        store.read(ref=ArtifactRef("cn_a_share_portfolio_daily_nav_analysis", 1, "sha256:" + "1" * 64))
    assert not (tmp_path / "old" / ".foundation.clock").exists()
    assert not (tmp_path / "new" / ".foundation.clock").exists()


def test_missing_original_cas_is_not_created_as_an_empty_ledger(tmp_path):
    with pytest.raises(FileNotFoundError):
        nav._NavArtifactStore(tmp_path / "missing", tmp_path / "new")
    assert not (tmp_path / "missing").exists() and not (tmp_path / "new").exists()


def test_input_locator_requires_one_hash_bound_archive_header(tmp_path):
    root = tmp_path / "run" / "retained-artifact-envelopes"
    root.mkdir(parents=True)
    ref = ArtifactRef("backtest_execution_input_bundle", 8, "sha256:" + "2" * 64)
    raw = b'{"artifact_type":"backtest_execution_input_bundle","content_hash":"' + ref.content_hash.encode() + b'","payload":{}}'
    path = root / ("2" * 64 + ".json")
    path.write_bytes(raw)  # Header locator is NOT the semantic input verifier.
    assert nav._input_ref(root.parent) == ref
    path.rename(root / ("3" * 64 + ".json"))
    with pytest.raises(ValueError, match="filename"):
        nav._input_ref(root.parent)


def test_nav_output_cannot_touch_prior_analysis_or_backtest(monkeypatch, tmp_path):
    evidence = tmp_path / "evidence"
    run = evidence / "old-run"
    monkeypatch.setattr(nav, "EVIDENCE", evidence)
    monkeypatch.setattr(nav, "RUNS", {"A": run})
    for destination in (run, run / "subdir", evidence, evidence / "development-analysis-v1/A"):
        with pytest.raises(ValueError, match="disjoint"):
            nav.analyze_daily_nav(arm="A", output_root=destination)
    assert not evidence.exists()


def test_driver_uses_public_roots_without_engine_or_governance_calls():
    tree = ast.parse(Path(nav.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("crypto_quant_"):
            assert "." not in node.module
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {"run", "reserve", "validate_candidate", "execute_experiment"}
            if node.func.attr == "append":
                assert isinstance(node.func.value, ast.Name) and node.func.value.id == "found"
