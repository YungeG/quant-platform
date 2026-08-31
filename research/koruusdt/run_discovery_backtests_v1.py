#!/usr/bin/env python3
"""Run local KORUUSDT discovery Backtests from retained authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, NoReturn, cast

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
BACKTEST = ROOT / "backtest"
for relative in (
    "packages/backtest-runtime/src",
    "packages/market-bundle-builder/src",
    "packages/market-data-contracts/src",
    "packages/trading-domain/src",
    "packages/trading-kernel/src",
):
    sys.path.insert(0, str(BACKTEST / relative))

import build_discovery_source_targets_v2 as retained  # noqa: E402
from crypto_quant_backtest import (  # noqa: E402
    ArtifactInstallMode,
    BinanceUsdmTradifiBarBacktestIntent,
    BinanceUsdmTradifiBarRequestIntent,
    BinanceUsdmTradifiProviderInputs,
    BuildArtifactManifest,
    BuildArtifactRef,
    BuildArtifactRole,
    BuildProvenance,
    DeterministicBarEngine,
    RequestedResultGrade,
    RuntimeLibraryRef,
    SourceTreeState,
    TimelineWindow,
    prepare_binance_usdm_tradifi_bar_backtest,
)
from crypto_quant_domain import (  # noqa: E402
    ArtifactReadResult,
    ArtifactRef,
    CurrencyId,
    Money,
    Scale,
    UtcInstant,
    canonical_bytes,
    canonical_sha256,
)

OUTPUT = Path(__file__).with_name("data") / "discovery_backtests_v1.json"
SCHEMA_VERSION = 1
INITIAL_EQUITY = Money(1_000_000_000_000, Scale(8), "USDT")


@dataclass(frozen=True)
class _ArtifactStore:
    values: dict[ArtifactRef, ArtifactReadResult]

    @classmethod
    def from_bundle(cls, bundle: Any) -> _ArtifactStore:
        values: dict[ArtifactRef, ArtifactReadResult] = {}
        for envelope in (*bundle.target_result.artifacts, *bundle.authority_artifacts):
            ref = ArtifactRef.from_envelope(envelope)
            source = canonical_bytes(envelope)
            values[ref] = ArtifactReadResult(
                envelope,
                object(),
                source,
                "sha256:" + hashlib.sha256(source).hexdigest(),
            )
        if len(values) != 13:
            raise ValueError("discovery artifact store must exact-cover 13 authorities")
        return cls(values)

    def read(self, *, ref: ArtifactRef) -> ArtifactReadResult:
        return self.values[ref]


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(BACKTEST), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _tree_hash(commit: str, path: str) -> str:
    return canonical_sha256(
        {
            "type": "repository_tree_binding_v1",
            "git_commit": commit,
            "path": path,
            "git_object": _git("rev-parse", f"{commit}:{path}"),
        }
    )


def _build_artifact_manifest() -> BuildArtifactManifest:
    if _git("status", "--short"):
        raise ValueError("Backtest worktree must be clean before discovery execution")
    commit = _git("rev-parse", "HEAD")
    commit_ns = int(_git("show", "-s", "--format=%ct", commit)) * 1_000_000_000
    definitions = (
        (
            BuildArtifactRole.DECISION_SOURCE,
            "precomputed-target-stream-adapter",
            "packages/backtest-runtime",
        ),
        (
            BuildArtifactRole.TRADING_DOMAIN,
            "crypto-quant-domain",
            "packages/trading-domain",
        ),
        (
            BuildArtifactRole.TRADING_KERNEL,
            "crypto-quant-trading",
            "packages/trading-kernel",
        ),
        (
            BuildArtifactRole.MARKET_DATA_CONTRACTS,
            "crypto-quant-market-data",
            "packages/market-data-contracts",
        ),
        (
            BuildArtifactRole.BACKTEST_RUNTIME,
            "crypto-quant-backtest",
            "packages/backtest-runtime",
        ),
    )
    artifacts = tuple(
        BuildArtifactRef(
            role=role,
            artifact_key=key,
            artifact_version="0.1.0",
            install_mode=ArtifactInstallMode.WHEEL,
            source_tree_state=SourceTreeState.CLEAN,
            content_hash=_tree_hash(commit, path),
            source_snapshot_hash=None,
        )
        for role, key, path in definitions
    )
    return BuildArtifactManifest(
        schema_version=1,
        build_key="koruusdt.discovery.backtest.build.v1",
        artifacts=artifacts,
        dependency_lock_hash="sha256:"
        + hashlib.sha256((BACKTEST / "uv.lock").read_bytes()).hexdigest(),
        runtime_libraries=(
            RuntimeLibraryRef(
                "python",
                "3.13.5",
                canonical_sha256("cpython-3.13.5"),
            ),
        ),
        container_image_digest=None,
        provenance=BuildProvenance(
            git_commit=commit,
            hostname="repository-retained-build",
            source_root="backtest",
            built_at=UtcInstant(commit_ns),
        ),
    )


def _money(value: Money) -> str:
    return format(Decimal(value.units) / Decimal(value.scale.factor), "f")


@dataclass(frozen=True)
class _PublicExecutionContext:
    """Public inputs required to prepare and execute bounded local trials."""

    bundle: Any
    strategy_definition_ref: Any
    parameter_refs: tuple[Any, ...]
    artifact_reader: Any
    build_artifact_manifest: BuildArtifactManifest


def _trial_summary(parameter_id: str, prepared: Any, executed: Any) -> dict[str, Any]:
    if executed.result is None:
        failure = executed.engine_failure or executed.input_validation_failure
        return {
            "parameter_id": parameter_id,
            "status": "failed",
            "failure": failure.to_canonical_dict() if failure is not None else None,
        }
    result = executed.result
    snapshot = result.final_portfolio_snapshot
    simple_return = Decimal(snapshot.equity.units - INITIAL_EQUITY.units) / Decimal(
        INITIAL_EQUITY.units
    )
    roles = tuple(value.role for value in result.financial_artifacts)
    return {
        "parameter_id": parameter_id,
        "status": "completed",
        "case_hash": prepared.execution_case.case_hash,
        "execution_input_ref": prepared.execution_input_ref.to_canonical_dict(),
        "execution_input_hash": prepared.execution_input_envelope.content_hash,
        "engine_result_hash": result.result_hash,
        "trace_hash": result.trace.trace_hash,
        "fill_count": len(result.fills),
        "fill_ids": [value.fill_id.value for value in result.fills],
        "fill_times_epoch_nanoseconds": [
            value.execution_time.epoch_nanoseconds for value in result.fills
        ],
        "fill_liquidity_roles": [value.liquidity for value in result.fills],
        "simple_period_return": format(simple_return, "f"),
        "initial_equity_usdt": _money(INITIAL_EQUITY),
        "final_equity_usdt": _money(snapshot.equity),
        "realized_pnl_usdt": _money(snapshot.realized_pnl),
        "unrealized_pnl_usdt": _money(snapshot.unrealized_pnl),
        "fees_usdt": _money(snapshot.fees),
        "funding_usdt": _money(snapshot.financing),
        "final_position_count": len(snapshot.positions),
        "financial_artifact_count": len(result.financial_artifacts),
        "funding_accounting_count": sum(
            value == "funding_accounting" or value.startswith("funding_accounting.")
            for value in roles
        ),
        "liquidation_audit_count": sum(
            value.startswith("liquidation_audit.hourly.") for value in roles
        ),
        "margin_projection_count": sum(
            value.startswith("margin_projection.hourly.") for value in roles
        ),
        "run_end_status": result.run_end_report.closeout_status.value,
    }


def _parameter_ref(context: _PublicExecutionContext, parameter_id: str) -> Any:
    if not parameter_id.startswith("p") or not parameter_id[1:].isdigit():
        raise ValueError(f"invalid discovery parameter id: {parameter_id}")
    index = int(parameter_id[1:]) - 1
    if not 0 <= index < len(context.parameter_refs):
        raise ValueError(f"unknown discovery parameter id: {parameter_id}")
    return context.parameter_refs[index]


def _failure_label(failure: object) -> str:
    if not isinstance(failure, dict):
        return "unknown_failure"
    code = failure.get("code")
    subject = failure.get("subject")
    if type(code) is str and type(subject) is str:
        return f"{code}:{subject}"
    subject_keys = failure.get("subject_keys")
    if type(code) is str and isinstance(subject_keys, list):
        return f"{code}:{','.join(str(value) for value in subject_keys)}"
    return str(code) if type(code) is str else "unknown_failure"


def _run_trial(
    context: _PublicExecutionContext, parameter_id: str, *, emit: Any = print
) -> dict[str, Any]:
    bundle = context.bundle
    emit(f"stage: preparing {parameter_id}", file=sys.stderr)
    window = TimelineWindow(
        bundle.manifest.coverage_start,
        bundle.manifest.coverage_start,
        bundle.manifest.coverage_end_exclusive,
    )
    intent = BinanceUsdmTradifiBarBacktestIntent(
        BinanceUsdmTradifiBarRequestIntent(
            experiment_id=f"koruusdt-discovery-{parameter_id}-seed-0",
            timeline_window=window,
            execution_account_id="account-1",
            reporting_currency=CurrencyId("USDT"),
            master_random_seed=0,
            market_bundle_ref=bundle.reader.bundle_ref,
            strategy_definition_ref=context.strategy_definition_ref,
            strategy_parameter_set_ref=_parameter_ref(context, parameter_id),
            result_grade_requested=RequestedResultGrade.DEVELOPMENT,
        ),
        BinanceUsdmTradifiProviderInputs(
            context.build_artifact_manifest, INITIAL_EQUITY
        ),
    )
    outcome = prepare_binance_usdm_tradifi_bar_backtest(
        intent, context.artifact_reader, bundle.reader
    )
    if outcome.failure is not None or outcome.result is None:
        trial = {
            "parameter_id": parameter_id,
            "status": "failed",
            "failure": (
                outcome.failure.to_canonical_dict()
                if outcome.failure is not None
                else None
            ),
        }
        emit(
            f"stage: {parameter_id} preparation failed: "
            f"{_failure_label(trial['failure'])}",
            file=sys.stderr,
        )
        return trial
    emit(f"stage: executing {parameter_id}", file=sys.stderr)
    trial = _trial_summary(
        parameter_id,
        outcome.result,
        DeterministicBarEngine().run(outcome.result.execution_case),
    )
    if trial["status"] != "completed":
        emit(
            f"stage: {parameter_id} engine failed: "
            f"{_failure_label(trial['failure'])}",
            file=sys.stderr,
        )
    return trial


def _select(trials: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    eligible = sorted(
        (
            value
            for value in trials
            if value["status"] == "completed"
            and value["fill_count"] >= 8
            and Decimal(value["simple_period_return"]) > 0
        ),
        key=lambda value: (
            -Decimal(value["simple_period_return"]),
            -value["fill_count"],
            value["parameter_id"],
        ),
    )
    return eligible[:1], "selected" if eligible else "discovery_no_selection"


def _build_results(
    context: _PublicExecutionContext,
    parameter_ids: tuple[str, ...],
    *,
    retained_metadata: dict[str, Any],
    emit: Any = print,
) -> dict[str, Any]:
    trials = [
        _run_trial(context, parameter_id, emit=emit) for parameter_id in parameter_ids
    ]
    failures = [
        f"{value['parameter_id']}:{_failure_label(value.get('failure'))}"
        for value in trials
        if value["status"] != "completed"
    ]
    if failures:
        raise RuntimeError(
            "discovery local backtest failed; no authoritative output will be written: "
            + ", ".join(failures)
        )
    selected, selection_status = _select(trials)
    value: dict[str, Any] = {
        "type": "koruusdt_discovery_backtests_v1",
        "schema_version": SCHEMA_VERSION,
        "report_scope": "bounded_local_backtest_execution_report",
        "public_research_execute_experiment_published": False,
        **retained_metadata,
        "bundle_ref": context.bundle.bundle_ref.to_canonical_dict(),
        "bundle_result_digest": context.bundle.result_digest,
        "build_artifact_manifest": context.build_artifact_manifest.to_canonical_dict(),
        "seed": 0,
        "trial_count": len(trials),
        "trials": trials,
        "selection_policy": {
            "hard_filters": ["fill_count >= 8", "simple_period_return > 0"],
            "ordering": [
                "simple_period_return descending",
                "fill_count descending",
                "parameter_id ascending",
            ],
            "max_selections": 1,
        },
        "selected_parameter_ids": [value["parameter_id"] for value in selected],
        "selection_status": selection_status,
        "holdout_touched": False,
        "network_performed": False,
        "deployment_authorized": False,
        "manifest_sha256": "",
    }
    return json.loads(retained.manifest_bytes(value))


def build_results(
    parameter_ids: tuple[str, ...] = tuple(f"p{index:02d}" for index in range(1, 9)),
) -> dict[str, Any]:
    print("stage: reconstructing retained public context", file=sys.stderr)
    retained_manifest, retained_context = cast(
        tuple[dict[str, Any], dict[str, Any]],
        retained.build_manifest(return_context=True),
    )
    bundle = retained_context["bundle"]
    context = _PublicExecutionContext(
        bundle=bundle,
        strategy_definition_ref=retained_context["target"].strategy.ref,
        parameter_refs=tuple(
            value.ref for value in retained_context["target"].parameters
        ),
        artifact_reader=_ArtifactStore.from_bundle(bundle),
        build_artifact_manifest=_build_artifact_manifest(),
    )
    return _build_results(
        context,
        parameter_ids,
        retained_metadata={
            "backtest_head": _git("rev-parse", "HEAD"),
            "retained_manifest_file_sha256": "sha256:"
            + hashlib.sha256(retained.OUTPUT.read_bytes()).hexdigest(),
            "retained_manifest_sha256": retained_manifest["manifest_sha256"],
            "source_profile_authority_ref": retained_context[
                "source_authority_ref"
            ].to_canonical_dict(),
            "profile_result_digest": retained_context["profile"].result_digest,
        },
    )


def _die(message: str) -> NoReturn:
    raise SystemExit(message)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--parameter-id",
        choices=("p01",),
        help="run only the bounded p01 smoke trial (the only supported direct parameter)",
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    parameter_ids = (
        (args.parameter_id,)
        if args.parameter_id
        else tuple(f"p{index:02d}" for index in range(1, 9))
    )
    rebuilt = retained.manifest_bytes(build_results(parameter_ids))
    if args.validate_only:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != rebuilt:
            _die("checked discovery Backtest output is stale")
        print(
            f"validated {OUTPUT}: sha256:{hashlib.sha256(rebuilt).hexdigest()}",
            file=sys.stderr,
        )
        return 0
    OUTPUT.write_bytes(rebuilt)
    print(
        f"wrote {OUTPUT}: sha256:{hashlib.sha256(rebuilt).hexdigest()}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
