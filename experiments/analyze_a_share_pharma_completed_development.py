"""Analyze already-consumed pharma COMPLETED evidence through public Backtest APIs.

No Engine, new sample, Research reservation, OOS or ValidationReport is created.
LocalFoundation here is an analysis-only CAS mirror, never a sample ledger.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import crypto_quant_backtest as bt
from crypto_quant_domain import ArtifactEnvelope, ArtifactRef, canonical_bytes
from crypto_quant_foundation import LocalFoundation

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "research/evidence/a-share-pharma-october-2024-acquisition-20260930"
RUNS = {
    "A": EVIDENCE / "public-ab-union-v1/A-fixed-session/test_actual_frozen_union_two_w0/A",
    "B": EVIDENCE / "public-ab-union-v1/B-session/test_actual_frozen_union_two_w0/B",
}
PUBLICATION_HASHES = {
    "A": "5024e04904336051f9086552bd094ec435cbb5bec0722958d7f92bb78ec457c0",
    "B": "127dcda2e157f1584363ae4dd9f750bf51955617072f98184c88e6d41782961d",
}


def _no_governance_clock() -> str:
    raise AssertionError("analysis-only CAS must not append governance/sample records")


def _import_archive(run_root: Path, store: LocalFoundation) -> tuple[tuple[Path, bytes], ...]:
    archive = run_root / "retained-artifact-envelopes"
    files = tuple(sorted(archive.glob("*.json")))
    if archive.is_symlink() or not files or len(files) > 64:
        raise ValueError("expected a bounded retained envelope archive")
    if any(path.is_symlink() or not path.is_file() for path in files):
        raise ValueError("retained envelope must be a regular non-symlink file")
    if sum(path.stat().st_size for path in files) > 64 * 1024 * 1024:
        raise ValueError("retained archive exceeds the 64MiB single-arm bound")
    sources = []
    for path in files:
        raw = path.read_bytes()
        value = json.loads(raw)
        if type(value) is not dict or set(value) != {
            "artifact_type", "schema_version", "payload", "content_hash"
        }:
            raise ValueError("retained source must be an exact ArtifactEnvelope")
        envelope = ArtifactEnvelope(**value)
        ref = ArtifactRef.from_envelope(envelope)
        if canonical_bytes(envelope) != raw or path.name != ref.content_hash[7:] + ".json":
            raise ValueError("retained envelope bytes or filename do not bind its ref")
        if store.put(envelope=envelope) != ref:
            raise ValueError("analysis CAS did not preserve the retained ref")
        if store.read(ref=ref).source_bytes != raw:
            raise ValueError("analysis CAS mirror changed retained bytes")
        sources.append((path, raw))
    return tuple(sources)


def analyze_existing_completion(
    *, run_root: Path, publication_ref: bt.BacktestCanonicalPublicationRef, output_root: Path
) -> dict[str, object]:
    """Derive the accepted simple-return/fill-count profile, not paired/DD metrics."""
    if type(publication_ref) is not bt.BacktestCanonicalPublicationRef:
        raise TypeError("exact BacktestCanonicalPublicationRef required")
    source_root, destination = run_root.resolve(), output_root.resolve()
    if destination.is_relative_to(source_root) or source_root.is_relative_to(destination):
        raise ValueError("analysis output must be disjoint from the original run")
    store = LocalFoundation(destination / "analysis-cas", clock=_no_governance_clock)
    sources = _import_archive(source_root, store)
    repository = bt.BacktestEvidenceRepository(reader=store)
    completed = repository.load_completed(publication_ref)
    if completed.result_grade is not bt.ResultGrade.DEVELOPMENT:
        raise ValueError("this pharma operation accepts development completion only")
    runtime = bt.BacktestAnalysisRuntime(publisher=store)
    metric_ref = runtime.publish_metric_profile()
    analysis_ref = runtime.derive(completed, metric_ref)
    if type(analysis_ref) is not bt.AnalysisArtifactRef:
        raise TypeError("completed@2 must produce the accepted analysis@1 ref")
    analysis = repository.load_analysis(analysis_ref)
    if (analysis.source_publication_ref != publication_ref
            or analysis.source_execution_result_hash != completed.source_execution_result_hash
            or analysis.metric_profile_ref != metric_ref
            or analysis.result_grade is not completed.result_grade):
        raise ValueError("verified analysis does not bind the original completed run")
    # Replay derivation only: no Runtime.run, economic execution or governance clock.
    if runtime.derive(completed, metric_ref) != analysis_ref:
        raise ValueError("public analysis replay changed its ref")
    if any(path.read_bytes() != raw for path, raw in sources):
        raise ValueError("original retained evidence changed during analysis")
    summary: dict[str, object] = {
        "kind": "pharma_completed_development_analysis",
        "mode": "assumption_bound_development",
        "analysis_ref": analysis_ref,
        "metric_profile_ref": metric_ref,
        "source_publication_ref": publication_ref,
        "source_execution_result_hash": completed.source_execution_result_hash,
        "simple_period_return": analysis.simple_period_return,
        "trade_count": analysis.trade_count,
        "result_grade": analysis.result_grade.value,
        "retained_envelopes": len(sources),
        "retained_source_bytes": sum(len(raw) for _, raw in sources),
        "analysis_replay_identical": True,
        "original_evidence_unchanged": True,
        "daily_availability_basis": "2026-09-29 user-approved EOD research assumption",
        "provider_availability_verified": False,
        "fee_basis": "original run-bound modeled fees, not verified account charges",
        "maximum_drawdown": None,
        "paired_validation_performed": False,
        "holdout_reserved": False,
        "validation_report": None,
        "deployment_authorized": False,
    }
    raw = canonical_bytes(summary)
    path = destination / "summary.json"
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError("occupied analysis summary differs; do not overwrite")
    else:
        with path.open("xb") as stream:
            stream.write(raw)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=tuple(RUNS), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ref = bt.BacktestCanonicalPublicationRef(ArtifactRef(
        "canonical_publication_manifest", 1, "sha256:" + PUBLICATION_HASHES[args.arm]
    ))
    summary = analyze_existing_completion(
        run_root=RUNS[args.arm], publication_ref=ref, output_root=args.output
    )
    print(canonical_bytes(summary).decode("utf-8"))


if __name__ == "__main__":
    main()
