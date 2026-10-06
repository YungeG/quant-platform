"""Offline archive/authority guards; no Backtest run or new market sample."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
import crypto_quant_backtest as bt
from crypto_quant_domain import ArtifactEnvelope, ArtifactRef, canonical_bytes
from crypto_quant_foundation import LocalFoundation

from experiments import analyze_a_share_pharma_completed_development as probe


def _archive(root: Path) -> tuple[Path, ArtifactRef]:
    envelope = ArtifactEnvelope.create("pharma_test_archive", 1, {"value": "not economic evidence"})
    ref = ArtifactRef.from_envelope(envelope)
    archive = root / "retained-artifact-envelopes"
    archive.mkdir(parents=True)
    path = archive / (ref.content_hash[7:] + ".json")
    path.write_bytes(canonical_bytes(envelope))
    return path, ref


def test_small_archive_exact_copy_without_owner_log_or_clock(tmp_path):
    path, ref = _archive(tmp_path / "run")
    original = path.read_bytes()
    store = LocalFoundation(tmp_path / "cas", clock=probe._no_governance_clock)
    sources = probe._import_archive(tmp_path / "run", store)
    assert sources == ((path, original),)
    assert store.read(ref=ref).source_bytes == original
    assert probe._import_archive(tmp_path / "run", store) == sources
    assert path.read_bytes() == original
    assert not list((tmp_path / "cas").rglob("*.jsonl"))
    assert not (tmp_path / "cas" / ".foundation.clock").exists()


@pytest.mark.parametrize("damage", ("payload", "filename", "whitespace", "duplicate", "extra", "symlink"))
def test_tampered_archive_rejected_before_analysis(tmp_path, monkeypatch, damage):
    path, _ = _archive(tmp_path / "run")
    original = path.read_bytes()
    if damage == "payload":
        path.write_bytes(original.replace(b"not economic evidence", b"forged economic evidence"))
    elif damage == "filename":
        path.rename(path.with_name("0" * 64 + ".json"))
    elif damage == "whitespace":
        path.write_bytes(original + b"\n")
    elif damage == "duplicate":
        path.write_bytes(original.replace(b'{"artifact_type":', b'{"artifact_type":"ignored","artifact_type":', 1))
    elif damage == "extra":
        path.write_bytes(original[:-1] + b',"unexpected":true}')
    else:
        retained = tmp_path / "real.json"
        path.rename(retained)
        path.symlink_to(retained)
    def forbidden(*args, **kwargs):
        pytest.fail("invalid evidence must not publish a metric or analysis")
    monkeypatch.setattr(bt.BacktestAnalysisRuntime, "publish_metric_profile", forbidden)
    ref = bt.BacktestCanonicalPublicationRef(ArtifactRef("canonical_publication_manifest", 1, "sha256:" + "1" * 64))
    with pytest.raises((ValueError, TypeError)):
        probe.analyze_existing_completion(run_root=tmp_path / "run", publication_ref=ref,
                                          output_root=tmp_path / "out")
    assert not (tmp_path / "out" / "summary.json").exists()


def test_unverified_completion_rejected_before_analysis(tmp_path, monkeypatch):
    _archive(tmp_path / "run")
    def forbidden(*args, **kwargs):
        pytest.fail("missing completed graph must not publish a metric or analysis")
    monkeypatch.setattr(bt.BacktestAnalysisRuntime, "publish_metric_profile", forbidden)
    ref = bt.BacktestCanonicalPublicationRef(ArtifactRef("canonical_publication_manifest", 1, "sha256:" + "1" * 64))
    with pytest.raises(bt.BacktestEvidenceError):
        probe.analyze_existing_completion(run_root=tmp_path / "run", publication_ref=ref,
                                          output_root=tmp_path / "out")
    assert not (tmp_path / "out" / "summary.json").exists()


def test_output_cannot_write_into_original_evidence(tmp_path):
    path, ref = _archive(tmp_path / "run")
    original = path.read_bytes()
    publication = bt.BacktestCanonicalPublicationRef(ArtifactRef("canonical_publication_manifest", 1, "sha256:" + "1" * 64))
    for destination in (tmp_path, tmp_path / "run", tmp_path / "run/subdir"):
        with pytest.raises(ValueError, match="disjoint"):
            probe.analyze_existing_completion(run_root=tmp_path / "run", publication_ref=publication,
                                              output_root=destination)
    assert path.read_bytes() == original


def test_driver_imports_public_roots_and_does_not_execute_or_reserve():
    tree = ast.parse(Path(probe.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("crypto_quant_"):
            assert "." not in node.module
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {"run", "reserve", "validate_candidate", "execute_experiment"}
            if node.func.attr == "append":
                assert isinstance(node.func.value, ast.Name) and node.func.value.id == "sources"
