"""Derive source-bound Backtest daily NAV/MaxDD from already-consumed pharma runs.

The two original analysis CAS mirrors stay read-only. New CAS accepts only the
new NAV profile/analysis namespaces; no fallback, ledger, economic run or OOS.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re

import crypto_quant_backtest as bt
from crypto_quant_domain import ArtifactEnvelope, ArtifactReadResult, ArtifactRef, canonical_bytes
from crypto_quant_foundation import LocalFoundation

from experiments.analyze_a_share_pharma_completed_development import (
    EVIDENCE, RUNS, PUBLICATION_HASHES, _no_governance_clock,
)

_NAV_TYPES = frozenset({"cn_a_share_portfolio_daily_nav_metric_profile", "cn_a_share_portfolio_daily_nav_analysis"})
_INPUT_HEADER = re.compile(rb'^\{"artifact_type":"backtest_execution_input_bundle","content_hash":"(sha256:[0-9a-f]{64})"')


class _NavArtifactStore:
    """Exact namespace routing, never read-fallback or a second CAS implementation."""
    def __init__(self, original: Path, output: Path) -> None:
        if not (original / "artifacts" / "sha256").is_dir():
            raise FileNotFoundError("original verified analysis CAS is not retained")
        self.original = LocalFoundation(original, clock=_no_governance_clock)
        self.derived = LocalFoundation(output, clock=_no_governance_clock)

    def read(self, *, ref: ArtifactRef) -> ArtifactReadResult:
        store = self.derived if ref.artifact_type in _NAV_TYPES else self.original
        return store.read(ref=ref)

    def put(self, *, envelope: ArtifactEnvelope) -> ArtifactRef:
        if envelope.artifact_type not in _NAV_TYPES or envelope.schema_version != 1:
            raise ValueError("new NAV CAS accepts only the two exact derived namespaces")
        return self.derived.put(envelope=envelope)


def _input_ref(run: Path) -> ArtifactRef:
    # Metadata locator only. The Backtest sole input8 decoder independently
    # verifies the complete source bytes; this bounded header cannot qualify it.
    files = tuple(sorted((run / "retained-artifact-envelopes").glob("*.json")))
    if not files or len(files) > 64:
        raise ValueError("expected one bounded original artifact archive")
    found = []
    for path in files:
        if path.is_symlink() or not path.is_file():
            raise ValueError("retained archive metadata must not use symlinks")
        with path.open("rb") as stream:
            match = _INPUT_HEADER.match(stream.read(256))
        if match is not None:
            sha = match.group(1).decode("ascii")
            if path.name != sha[7:] + ".json":
                raise ValueError("input metadata filename does not bind its ref")
            found.append(ArtifactRef("backtest_execution_input_bundle", 8, sha))
    if len(found) != 1:
        raise ValueError("expected exactly one original input8 transport ref")
    return found[0]


def analyze_daily_nav(*, arm: str, output_root: Path) -> dict[str, object]:
    if arm not in RUNS:
        raise ValueError("arm must be A or B")
    original = EVIDENCE / "development-analysis-v1" / arm / "analysis-cas"
    output = output_root.resolve()
    protected = (*RUNS.values(), EVIDENCE / "development-analysis-v1")
    if any(output.is_relative_to(p.resolve()) or p.resolve().is_relative_to(output) for p in protected):
        raise ValueError("NAV output must be disjoint from all original evidence")
    store = _NavArtifactStore(original, output / "analysis-cas")
    publication = bt.BacktestCanonicalPublicationRef(ArtifactRef(
        "canonical_publication_manifest", 1, "sha256:" + PUBLICATION_HASHES[arm]))
    input_ref = _input_ref(RUNS[arm])
    runtime = bt.CnASharePortfolioDailyNavAnalysisRuntimeV1(reader=store, publisher=store)
    profile = runtime.publish_metric_profile()
    ref = runtime.derive(publication_ref=publication, execution_input_ref=input_ref, metric_profile_ref=profile)
    value = bt.BacktestEvidenceRepository(reader=store).load_cn_a_share_portfolio_daily_nav(ref)
    if runtime.derive(publication_ref=publication, execution_input_ref=input_ref, metric_profile_ref=profile) != ref:
        raise ValueError("source-derived NAV replay changed its identity")
    summary: dict[str, object] = {
        "kind": "pharma_daily_nav_development_analysis", "arm": arm,
        "mode": "assumption_bound_development", "analysis_ref": ref,
        "analysis": value.to_canonical_dict(), "curve_points": len(value.points),
        "analysis_replay_identical": True, "new_economic_run": False,
        "source_basis": "2026-09-29 user-approved daily accuracy/EOD assumption; original modeled fees",
        "measurement_time": "frozen trading close, not verified provider publication time",
        "market_stream_retention_proven": False, "paired_validation_performed": False,
        "holdout_reserved": False, "validation_report": None, "deployment_authorized": False,
    }
    raw = canonical_bytes(summary)
    path = output / "summary.json"
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError("occupied NAV summary differs; do not overwrite")
    else:
        with path.open("xb") as stream:
            stream.write(raw)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=tuple(RUNS), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze_daily_nav(arm=args.arm, output_root=args.output)
    value = result["analysis"]
    assert isinstance(value, dict)
    print(canonical_bytes({"arm": args.arm, "summary": str(args.output / "summary.json"),
        "analysis_ref": result["analysis_ref"], "simple_period_return": value["simple_period_return"],
        "maximum_drawdown": value["maximum_drawdown"], "curve_points": result["curve_points"],
        "trade_count": value["trade_count"], "result_grade": value["result_grade"],
        "new_economic_run": False, "validation_report": None}).decode("utf-8"))


if __name__ == "__main__":
    main()
