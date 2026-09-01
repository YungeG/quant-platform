#!/usr/bin/env python3
"""Execute the frozen KORUUSDT eight-arm discovery Experiment offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn, cast

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BACKTEST = ROOT / "backtest"
DATA = HERE / "data"
FORMAL_ROOT = DATA / "formal_discovery_v1"
OUTPUT = DATA / "discovery_experiment_v1.json"
STATE_IDENTITY = FORMAL_ROOT / "state_identity.json"

sys.path.insert(0, str(HERE))
import build_discovery_source_targets_v2 as retained  # noqa: E402
from crypto_quant_backtest import (  # noqa: E402
    ArtifactInstallMode,
    BacktestAnalysisRuntime,
    BinanceUsdmTradifiBacktestOperations,
    BinanceUsdmTradifiBarRequestIntent,
    BinanceUsdmTradifiProviderInputs,
    BuildArtifactManifest,
    BuildArtifactRef,
    BuildArtifactRole,
    BuildProvenance,
    RequestedResultGrade,
    RuntimeLibraryRef,
    SourceTreeState,
    TimelineWindow,
)
from crypto_quant_bundle_builder import (  # noqa: E402
    LocalMarketBundleRepository,
    LocalMarketBundleRepositoryConfig,
)
from crypto_quant_domain import (  # noqa: E402
    ArtifactEnvelope,
    ArtifactRef,
    CurrencyId,
    Money,
    Scale,
    UtcInstant,
    canonical_bytes,
    canonical_sha256,
)
from crypto_quant_foundation import (  # noqa: E402
    FoundationFailure,
    LocalFoundation,
    LogCheckpoint,
    LogEntryRef,
)
from crypto_quant_market_data import LocalMarketBundleReader  # noqa: E402
from crypto_quant_research import (  # noqa: E402
    DeferredTrialExecution,
    FrozenExperimentInputs,
    IntegratedDataSlice,
    IntegratedExperimentSpec,
    IntegratedHardFilter,
    IntegratedOrderingCriterion,
    IntegratedParameterCombination,
    IntegratedSelectionPolicy,
    PublishedNoSelection,
    PublishedStrategyCandidate,
    build_integrated_trial_declarations,
    execute_experiment,
)
from crypto_quant_validation import (  # noqa: E402
    SampleConsumptionLedger,
    SampleConsumptionRecord,
)

SCHEMA_VERSION = 1
PLATFORM_PIN_COMMIT = "5371e0d8707a0f1717bcd0df9c4722d0b8e4162b"
BACKTEST_COMMIT = "ed32bb578ffa792f6429aaad94ce8fc05c3eec2f"
RESEARCH_COMMIT = "37c5f59454494802257e10b4b9fb2497c75f8c06"
RETAINED_FILE_HASH = (
    "sha256:eb38679a2ec9b2a31420ae58bdd50fcb1a1d362cd90bce0a3f30753c397ba47e"
)
RETAINED_MANIFEST_HASH = (
    "sha256:e5a29995a4326a50238ed3f945257b045d4b1a6e0b16a5f619837f56704f77df"
)
DIAGNOSTIC_FILE_HASH = (
    "sha256:ebf720bb2b1df7fef3080e573cc072f74f611518272da4a0efa93dfbd5982322"
)
DIAGNOSTIC_MANIFEST_HASH = (
    "sha256:60d1d9173803957feb23deace6debd62798d43795e03195adb7dac44a4779ce8"
)
BUNDLE_RESULT_DIGEST = (
    "sha256:d122adc40979100dfe707cb87a11cf08c13613abcfc97e47f88baf98a2cd8ebb"
)
PROFILE_RESULT_DIGEST = (
    "sha256:3e8c794912c0339c1c8c36660e53c256d4cd8c6910de148224bf4bb7f039d402"
)
SOURCE_PROFILE_REF = {
    "type": "artifact_ref",
    "artifact_type": "binance_usdm_koru_source_profile_authority",
    "schema_version": 2,
    "content_hash": "sha256:1c79ff9945bda06b752a63c7418fcf582707e4ef08287147f18214c3a0cdad03",
}
BUNDLE_REF = {
    "type": "market_bundle_ref",
    "bundle_key": "binance-usdm-koru-tradifi-execution-development-v2-376ed7ae23f6872c8649925d55ef7e7faa89cd3cf6b630fe3fcaca0f84b011f7",
    "manifest_hash": "sha256:cf512bdee193cceb92034b5d2c6adbb5d2e37854c199fc44cdd3222c16e6aae2",
}
STRATEGY_REF = {
    "type": "artifact_ref",
    "artifact_type": "strategy_definition",
    "schema_version": 1,
    "content_hash": "sha256:b5c153a127ad3ed4c1286ba4d2948fa52e581239f0d3bd01f3074c410eed9c81",
}
METRIC_PROFILE_REF = {
    "type": "artifact_ref",
    "artifact_type": "backtest_metric_profile",
    "schema_version": 1,
    "content_hash": "sha256:bced4dbef8bbf6e1ec9821ae3b68e8c6ce2bbed953f95fe1214c8e21676dbd6a",
}
PARAMETER_REFS = (
    "sha256:23911e260d3fe6e4fbc009851523bbb095209466e44c70b63ae2114e37f05f78",
    "sha256:f02521f9194c671a24c7a05bb0ebe3e11eac2cfddccd5b3c52e11f58b1bab9f9",
    "sha256:b577c11a94a1f4fed3247cf9bd3508de092be7d14a01dfd58e3805b1a4a69c43",
    "sha256:bd3c440d01a144317ddacad9814b0791e13079bc898c4e06dea455566ad7a14a",
    "sha256:cbcd7d3a81c71411abe0c2191b0f7b17209b3d55965361c8e6c0798b5c1e30e9",
    "sha256:bec582ad24da484a13c0fc960e4ae351c4cbd62f7806d07a03d579db04cdffc0",
    "sha256:aa46923df87d9ed25ee58fde6e4af0108d7e79e3ad7cfe17ac26d0dd9bf910d3",
    "sha256:e85e8a778fcdfdc4176f9fa6c395c86e47bd7a356309dc08b3074024bfa89911",
)
DISCOVERY_START = "2026-07-15T10:00:00.000000Z"
DISCOVERY_END = "2026-08-24T11:00:00.000000Z"
DATASET_REVISION = "koruusdt.discovery.bundle-v2.cf512bdee193cceb"
RESERVATION_AT = "2026-08-26T12:00:00.000000Z"
FOUNDATION_TIME = "2026-08-26T12:00:01.000000Z"
INITIAL_EQUITY = Money(1_000_000_000_000, Scale(8), "USDT")
SAMPLE_LOG = "validation.sample-consumption.v1"
ARTIFACT_LOG = "research.artifacts.v1"
EXECUTION_LOG = "research.execution.v1"
OWNER_LOGS = (SAMPLE_LOG, ARTIFACT_LOG, EXECUTION_LOG)


def _artifact_ref(artifact_type: str, content_hash: str) -> dict[str, object]:
    return {
        "type": "artifact_ref",
        "artifact_type": artifact_type,
        "schema_version": 1,
        "content_hash": content_hash,
    }


HYPOTHESIS_REF = _artifact_ref(
    "hypothesis", canonical_sha256("koruusdt.closed-market-range.discovery.v1")
)
SCENARIO_REF = _artifact_ref(
    "scenario", canonical_sha256("koruusdt.discovery.observed-market.v1")
)
BACKTEST_TEMPLATE_REF = _artifact_ref(
    "backtest_template", canonical_sha256("binance-usdm-tradifi-development.v1")
)
SELECTION_ACTOR_REF = _artifact_ref(
    "actor", canonical_sha256("koruusdt.formal-discovery-owner.v1")
)


def frozen_experiment_spec() -> IntegratedExperimentSpec:
    """Return the exact eight-arm declaration matrix without performing I/O."""
    return IntegratedExperimentSpec(
        hypothesis_ref=HYPOTHESIS_REF,
        strategy_definition_ref=STRATEGY_REF,
        data_slices=(
            IntegratedDataSlice(
                BUNDLE_REF,
                DATASET_REVISION,
                DISCOVERY_START,
                DISCOVERY_END,
            ),
        ),
        parameter_combinations=tuple(
            IntegratedParameterCombination((("intent_key", f"p{index:02d}"),))
            for index in range(1, 9)
        ),
        seeds=(0,),
        scenario_refs=(SCENARIO_REF,),
        backtest_template_ref=BACKTEST_TEMPLATE_REF,
        model_build_plan=None,
        metric_profile_refs=(METRIC_PROFILE_REF,),
        budget={"max_trials": 8},
    )


def frozen_selection_policy() -> IntegratedSelectionPolicy:
    return IntegratedSelectionPolicy(
        metric_profile_ref=METRIC_PROFILE_REF,
        eligible_trial_statuses=("COMPLETED",),
        accepted_backtest_grades=("development",),
        hard_filters=(
            IntegratedHardFilter("trade_count", "gte", 8),
            IntegratedHardFilter("simple_period_return", "gt", "0"),
        ),
        ordering=(
            IntegratedOrderingCriterion("simple_period_return", "descending"),
            IntegratedOrderingCriterion("trade_count", "descending"),
        ),
        max_selections=1,
        tie_break="trial_declaration_ref_ascending",
    )


def frozen_inputs() -> FrozenExperimentInputs:
    spec = frozen_experiment_spec()
    declarations = build_integrated_trial_declarations(spec)
    executions = tuple(
        DeferredTrialExecution(
            declaration.ref,
            {"intent_key": dict(declaration.parameter_values.values)["intent_key"]},
        )
        for declaration in declarations
    )
    return FrozenExperimentInputs(
        spec,
        frozen_selection_policy(),
        SELECTION_ACTOR_REF,
        executions,
        RESERVATION_AT,
    )


def _plain(value: object) -> Any:
    return json.loads(canonical_bytes(value))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
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
            "git_object": _git(BACKTEST, "rev-parse", f"{commit}:{path}"),
        }
    )


def _build_artifact_manifest() -> BuildArtifactManifest:
    if _git(BACKTEST, "rev-parse", "HEAD") != BACKTEST_COMMIT:
        raise ValueError("Backtest checkout does not match the accepted commit")
    if _git(BACKTEST, "status", "--short"):
        raise ValueError("Backtest worktree must be clean")
    commit_ns = (
        int(_git(BACKTEST, "show", "-s", "--format=%ct", BACKTEST_COMMIT))
        * 1_000_000_000
    )
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
    return BuildArtifactManifest(
        schema_version=1,
        build_key="koruusdt.discovery.backtest.build.v1",
        artifacts=tuple(
            BuildArtifactRef(
                role=role,
                artifact_key=key,
                artifact_version="0.1.0",
                install_mode=ArtifactInstallMode.WHEEL,
                source_tree_state=SourceTreeState.CLEAN,
                content_hash=_tree_hash(BACKTEST_COMMIT, path),
                source_snapshot_hash=None,
            )
            for role, key, path in definitions
        ),
        dependency_lock_hash=_sha256_file(BACKTEST / "uv.lock"),
        runtime_libraries=(
            RuntimeLibraryRef("python", "3.13.5", canonical_sha256("cpython-3.13.5")),
        ),
        container_image_digest=None,
        provenance=BuildProvenance(
            git_commit=BACKTEST_COMMIT,
            hostname="repository-retained-build",
            source_root="backtest",
            built_at=UtcInstant(commit_ns),
        ),
    )


def _commits() -> dict[str, str]:
    return {
        "platform": _git(ROOT, "rev-parse", "HEAD"),
        "platform_pin": PLATFORM_PIN_COMMIT,
        "backtest": BACKTEST_COMMIT,
        "research": RESEARCH_COMMIT,
    }


def _retained_hashes() -> dict[str, object]:
    return {
        "source_targets_file": RETAINED_FILE_HASH,
        "source_targets_manifest": RETAINED_MANIFEST_HASH,
        "diagnostic_file": DIAGNOSTIC_FILE_HASH,
        "diagnostic_manifest": DIAGNOSTIC_MANIFEST_HASH,
        "bundle_result_digest": BUNDLE_RESULT_DIGEST,
        "profile_result_digest": PROFILE_RESULT_DIGEST,
        "source_profile_authority_ref": SOURCE_PROFILE_REF,
    }


def _state_value() -> dict[str, object]:
    inputs = frozen_inputs()
    return {
        "type": "koruusdt_formal_discovery_state_identity_v1",
        "schema_version": 1,
        "experiment_ref": inputs.experiment_spec.ref,
        "selection_policy_ref": inputs.selection_policy.ref,
        "trial_intents": [item.request_spec for item in inputs.trial_executions],
        "commits": _commits(),
        "retained_hashes": _retained_hashes(),
        "network_performed": False,
        "holdout_touched": False,
        "manifest_sha256": "",
    }


def _write_canonical(path: Path, value: dict[str, object]) -> bytes:
    encoded = retained.manifest_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(encoded)
    temporary.replace(path)
    return encoded


def _validate_canonical(path: Path, expected_type: str) -> dict[str, Any]:
    source = path.read_bytes()
    value = json.loads(source)
    if type(value) is not dict or value.get("type") != expected_type:
        raise ValueError(f"{path}: wrong document type")
    retained.validate_self_hash(value, path)
    if retained.manifest_bytes(value) != source:
        raise ValueError(f"{path}: document is not canonical")
    return value


def _prepare_state() -> None:
    if FORMAL_ROOT.exists():
        entries = tuple(FORMAL_ROOT.iterdir())
        if entries:
            if not STATE_IDENTITY.exists():
                raise ValueError(
                    "formal discovery root is nonempty without state identity"
                )
            if {entry.name for entry in entries} - {
                STATE_IDENTITY.name,
                "foundation",
                "market",
                "backtest_publications",
            }:
                raise ValueError("formal discovery root contains unmanaged state")
            existing = _validate_canonical(
                STATE_IDENTITY, "koruusdt_formal_discovery_state_identity_v1"
            )
            expected = json.loads(retained.manifest_bytes(_state_value()))
            if existing != expected:
                existing_semantics = json.loads(json.dumps(existing))
                expected_semantics = json.loads(json.dumps(expected))
                existing_platform = existing_semantics["commits"]["platform"]
                expected_platform = expected_semantics["commits"]["platform"]
                existing_semantics["commits"]["platform"] = ""
                expected_semantics["commits"]["platform"] = ""
                existing_semantics["manifest_sha256"] = ""
                expected_semantics["manifest_sha256"] = ""
                if (
                    existing_semantics != expected_semantics
                    or subprocess.run(
                        [
                            "git",
                            "-C",
                            str(ROOT),
                            "merge-base",
                            "--is-ancestor",
                            existing_platform,
                            expected_platform,
                        ],
                        check=False,
                    ).returncode
                    != 0
                ):
                    raise ValueError("formal discovery root contains incompatible state")
                _write_canonical(STATE_IDENTITY, _state_value())
            return
    if OUTPUT.exists():
        raise ValueError("discovery summary exists without compatible evidence state")
    FORMAL_ROOT.mkdir(parents=True, exist_ok=True)
    _write_canonical(STATE_IDENTITY, _state_value())


def _verify_clean_worktrees() -> None:
    allowed = (
        "research/koruusdt/data/formal_discovery_v1/",
        "research/koruusdt/data/discovery_experiment_v1.json",
    )
    dirty = []
    for line in _git(ROOT, "status", "--porcelain", "--untracked-files=all").splitlines():
        if "R" in line[:2] or "C" in line[:2]:
            dirty.append(line)
            continue
        path = line[3:]
        if not any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in allowed):
            dirty.append(line)
    if dirty:
        raise ValueError("Platform worktree contains unmanaged changes")
    if _git(BACKTEST, "status", "--short"):
        raise ValueError("Backtest worktree must be clean")
    if _git(ROOT / "research-platform", "status", "--short"):
        raise ValueError("Research worktree must be clean")


def _verify_pins() -> None:
    _verify_clean_worktrees()
    if _git(ROOT, "rev-parse", PLATFORM_PIN_COMMIT) != PLATFORM_PIN_COMMIT:
        raise ValueError("Platform pin commit is unavailable")
    if subprocess.run(
        ["git", "-C", str(ROOT), "merge-base", "--is-ancestor", PLATFORM_PIN_COMMIT, "HEAD"],
        check=False,
    ).returncode != 0:
        raise ValueError("Platform checkout does not descend from the accepted pin")
    if _git(BACKTEST, "rev-parse", "HEAD") != BACKTEST_COMMIT:
        raise ValueError("Backtest checkout does not match the accepted commit")
    if _git(ROOT / "research-platform", "rev-parse", "HEAD") != RESEARCH_COMMIT:
        raise ValueError("Research checkout does not match the accepted commit")
    if _sha256_file(retained.OUTPUT) != RETAINED_FILE_HASH:
        raise ValueError("retained Source/Target file hash mismatch")
    retained_value = _validate_canonical(
        retained.OUTPUT, "koruusdt_discovery_source_targets_v2_manifest"
    )
    if retained_value["manifest_sha256"] != RETAINED_MANIFEST_HASH:
        raise ValueError("retained Source/Target manifest hash mismatch")


def _verify_context(
    manifest: Mapping[str, object], context: Mapping[str, object]
) -> Any:
    bundle = cast(Any, context["bundle"])
    if _plain(bundle.bundle_ref) != BUNDLE_REF:
        raise ValueError("reconstructed BundleV2 ref mismatch")
    if bundle.result_digest != BUNDLE_RESULT_DIGEST:
        raise ValueError("reconstructed BundleV2 digest mismatch")
    profile = cast(Any, context["profile"])
    if profile.result_digest != PROFILE_RESULT_DIGEST:
        raise ValueError("reconstructed profile digest mismatch")
    if _plain(context["source_authority_ref"]) != SOURCE_PROFILE_REF:
        raise ValueError("reconstructed source profile authority mismatch")
    if manifest.get("advisory_flags", {}).get("network_performed") is not False:  # type: ignore[union-attr]
        raise ValueError("retained reconstruction reported network activity")
    target = cast(Any, context["target"])
    if _plain(target.strategy.ref) != STRATEGY_REF:
        raise ValueError("reconstructed strategy ref mismatch")
    if tuple(value.ref.content_hash for value in target.parameters) != PARAMETER_REFS:
        raise ValueError("reconstructed parameter refs mismatch")
    return bundle


def _publish_bundle(bundle: Any) -> LocalMarketBundleReader:
    repository = LocalMarketBundleRepository(
        config=LocalMarketBundleRepositoryConfig(root=FORMAL_ROOT / "market")
    )
    outcome = repository.publish_market_bundle_v1(
        manifest=bundle.reader.manifest,
        stream_payloads={
            key: canonical_bytes(events)
            for key, events in bundle.reader.streams.items()
        },
        retention_policy_ref="retention.koru-formal-discovery.v1",
    )
    if outcome.result is None:
        raise RuntimeError(f"market bundle publication failed: {outcome.failure}")
    if _plain(outcome.result.bundle_ref) != BUNDLE_REF:
        raise ValueError("published market bundle ref mismatch")
    return LocalMarketBundleReader.open(
        repository_root=(FORMAL_ROOT / "market").resolve(),
        bundle_ref=outcome.result.bundle_ref,
    )


def _intent_templates(bundle: Any) -> dict[str, BinanceUsdmTradifiBarRequestIntent]:
    target = bundle.target_result
    window = TimelineWindow(
        bundle.manifest.coverage_start,
        bundle.manifest.coverage_start,
        bundle.manifest.coverage_end_exclusive,
    )
    templates = {
        f"p{index:02d}": BinanceUsdmTradifiBarRequestIntent(
            experiment_id=None,
            timeline_window=window,
            execution_account_id="account-1",
            reporting_currency=CurrencyId("USDT"),
            master_random_seed=0,
            market_bundle_ref=bundle.reader.bundle_ref,
            strategy_definition_ref=target.strategy.ref,
            strategy_parameter_set_ref=target.parameters[index - 1].ref,
            result_grade_requested=RequestedResultGrade.DEVELOPMENT,
        )
        for index in range(1, 9)
    }
    if tuple(templates) != tuple(f"p{index:02d}" for index in range(1, 9)):
        raise ValueError("request intent templates do not exact-cover p01-p08")
    return templates


@dataclass
class _CountingOperations:
    operations: BinanceUsdmTradifiBacktestOperations
    prepare_count: int = 0
    run_prepared_count: int = 0
    derive_count: int = 0

    def prepare(self, request_spec: Mapping[str, object], experiment_id: str) -> object:
        self.prepare_count += 1
        return self.operations.prepare(request_spec, experiment_id)

    def run_prepared(self, prepared: object) -> dict[str, object]:
        self.run_prepared_count += 1
        return self.operations.run_prepared(prepared)  # type: ignore[arg-type]

    def derive(
        self,
        completed_ref: Mapping[str, object],
        metric_profile_ref: Mapping[str, object],
    ) -> dict[str, object]:
        self.derive_count += 1
        return self.operations.derive(completed_ref, metric_profile_ref)

    def __getattr__(self, name: str) -> object:
        return getattr(self.operations, name)

    @property
    def economic_counts(self) -> tuple[int, int, int]:
        return self.prepare_count, self.run_prepared_count, self.derive_count


def execute_with_replay(
    inputs: FrozenExperimentInputs,
    foundation: LocalFoundation,
    ledger: SampleConsumptionLedger,
    operations: object,
    publication_root: Path,
) -> tuple[PublishedStrategyCandidate | PublishedNoSelection, tuple[int, int, int]]:
    counted = (
        operations
        if type(operations) is _CountingOperations
        else _CountingOperations(cast(BinanceUsdmTradifiBacktestOperations, operations))
    )
    first = execute_experiment(inputs, foundation, ledger, counted)
    counts = counted.economic_counts
    publications = sum(1 for path in publication_root.rglob("*") if path.is_file())
    second = execute_experiment(inputs, foundation, ledger, counted)
    if second != first:
        raise RuntimeError("execute_experiment replay result changed")
    if counted.economic_counts != counts:
        raise RuntimeError("execute_experiment replay repeated economic execution")
    if sum(1 for path in publication_root.rglob("*") if path.is_file()) != publications:
        raise RuntimeError("execute_experiment replay changed Backtest publications")
    return first, counts


def _checkpoint_value(value: LogCheckpoint) -> dict[str, object]:
    return {
        "log_name": value.log_name,
        "as_of": value.as_of,
        "upper_log_sequence": value.upper_log_sequence,
        "head_receipt_hash": value.head_receipt_hash,
    }


def _entry_ref_value(value: LogEntryRef) -> dict[str, object]:
    return {
        "log_name": value.log_name,
        "log_sequence": value.log_sequence,
        "receipt_hash": value.receipt_hash,
    }


def _published_payloads(
    foundation: LocalFoundation, log_name: str
) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for entry in foundation.entries(log_name):
        try:
            decoded = json.loads(entry.payload.decode("utf-8"))
            envelope = ArtifactEnvelope(
                decoded["artifact_type"],
                decoded["schema_version"],
                decoded["payload"],
                decoded["content_hash"],
            )
            if canonical_bytes(envelope) != entry.payload:
                raise ValueError("entry payload is not canonical")
            ref = ArtifactRef.from_envelope(envelope)
            if entry.event_id != canonical_sha256(
                ("artifact-publication-v1", log_name, ref)
            ):
                raise ValueError("entry event id does not bind artifact")
            stored = foundation.read(ref=ref)
            if (
                stored.envelope != envelope
                or stored.source_bytes != entry.payload
                or stored.source_hash != canonical_sha256(envelope)
            ):
                raise ValueError("entry does not bind Foundation CAS artifact")
            value = json.loads(canonical_bytes(envelope))
            if type(value) is not dict or type(value.get("payload")) is not dict:
                raise ValueError("artifact payload is not an object")
        except (
            FoundationFailure,
            KeyError,
            TypeError,
            UnicodeDecodeError,
            ValueError,
            json.JSONDecodeError,
        ) as error:
            raise ValueError(f"{log_name}: invalid public artifact entry") from error
        payloads.append(value)
    return payloads


def _outcome_summary(foundation: LocalFoundation) -> dict[str, object]:
    outcomes = [
        envelope["payload"]
        for envelope in _published_payloads(foundation, EXECUTION_LOG)
        if envelope.get("artifact_type") == "task_outcome"
    ]
    states = Counter(outcome["state"] for outcome in outcomes)
    completed_refs: list[object] = []
    analysis_refs: list[object] = []
    for outcome in outcomes:
        witness = outcome.get("witness")
        if type(witness) is not dict:
            continue
        completed = witness.get("trial_completed_publication")
        if type(completed) is dict and "publication_ref" in completed:
            completed_refs.append(completed["publication_ref"])
        analysis = witness.get("analysis_derivation")
        if type(analysis) is dict and "analysis_ref" in analysis:
            analysis_refs.append(analysis["analysis_ref"])
    def key(value: object) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    return {
        "count": len(outcomes),
        "states": dict(sorted(states.items())),
        "completed_publication_refs": sorted(completed_refs, key=key),
        "analysis_refs": sorted(analysis_refs, key=key),
    }


def _artifact_ref_from_envelope(envelope: Mapping[str, object]) -> dict[str, object]:
    return {
        "type": "artifact_ref",
        "artifact_type": envelope["artifact_type"],
        "schema_version": envelope["schema_version"],
        "content_hash": envelope["content_hash"],
    }


def _validate_selection_evidence(
    summary: Mapping[str, object], foundation: LocalFoundation
) -> None:
    selection = summary.get("selection")
    if type(selection) is not dict:
        raise ValueError("summary selection result is invalid")
    refs: dict[str, list[dict[str, object]]] = {}
    for envelope in (
        *_published_payloads(foundation, ARTIFACT_LOG),
        *_published_payloads(foundation, EXECUTION_LOG),
    ):
        artifact_type = envelope.get("artifact_type")
        if type(artifact_type) is str:
            refs.setdefault(artifact_type, []).append(
                _artifact_ref_from_envelope(envelope)
            )
    if selection.get("candidate_family_ref") not in refs.get("candidate_family", []):
        raise ValueError("selection candidate family ref does not match evidence")
    if selection.get("execution_manifest_ref") not in refs.get(
        "experiment_execution_manifest", []
    ):
        raise ValueError("selection execution manifest ref does not match evidence")
    if selection.get("type") == "selected":
        if selection.get("selection_result_ref") not in refs.get(
            "strategy_candidate", []
        ):
            raise ValueError("selected result ref does not match evidence")
    elif (
        selection.get("type") != "discovery_no_selection"
        or selection.get("no_selection_ref") != selection.get("candidate_family_ref")
        or selection.get("reason_code") != "NO_ELIGIBLE_TRIAL"
        or refs.get("strategy_candidate")
    ):
        raise ValueError("no-selection result does not match evidence")


def _sample_records(foundation: LocalFoundation) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for entry in foundation.entries(SAMPLE_LOG):
        try:
            decoded = json.loads(entry.payload.decode("utf-8"))
            envelope = ArtifactEnvelope(
                decoded["artifact_type"],
                decoded["schema_version"],
                decoded["payload"],
                decoded["content_hash"],
            )
            if (
                envelope.artifact_type != "sample_consumption_append"
                or envelope.schema_version != 1
                or canonical_bytes(envelope) != entry.payload
            ):
                raise ValueError("sample append envelope is invalid")
            payload = _plain(envelope.payload)
            if type(payload) is not dict or set(payload) != {"record", "producer_ref"}:
                raise ValueError("sample append payload is invalid")
            record_wire = payload["record"]
            producer_wire = payload["producer_ref"]
            if (
                type(record_wire) is not dict
                or set(record_wire)
                != {
                    "dataset_revision",
                    "interval_start",
                    "interval_end",
                    "purpose",
                    "consumer_id",
                    "consumed_at",
                }
                or type(producer_wire) is not dict
                or set(producer_wire)
                != {"type", "artifact_type", "schema_version", "content_hash"}
                or producer_wire.get("type") != "artifact_ref"
            ):
                raise ValueError("sample append values are invalid")
            record = SampleConsumptionRecord(**record_wire)
            producer = ArtifactRef(
                producer_wire["artifact_type"],
                producer_wire["schema_version"],
                producer_wire["content_hash"],
            )
            expected_event_id = canonical_sha256(
                (
                    "sample-consumption-append-v1",
                    producer,
                    record.dataset_revision,
                    record.interval_start,
                    record.interval_end,
                    record.purpose,
                )
            )
            if entry.event_id != expected_event_id or record.consumed_at > entry.accepted_at:
                raise ValueError("sample append event identity is invalid")
        except (
            KeyError,
            TypeError,
            UnicodeDecodeError,
            ValueError,
            json.JSONDecodeError,
        ) as error:
            raise ValueError("sample ledger contains invalid append evidence") from error
        records.append(
            {
                "dataset_revision": record.dataset_revision,
                "interval_start": record.interval_start,
                "interval_end": record.interval_end,
                "purpose": record.purpose,
                "consumer_id": record.consumer_id,
                "consumed_at": record.consumed_at,
            }
        )
    return records


def _sample_summary(foundation: LocalFoundation) -> dict[str, object]:
    records = _sample_records(foundation)
    if "holdout" in json.dumps(records, sort_keys=True).lower():
        raise ValueError("sample ledger contains holdout evidence")
    if any(record.get("interval_end") != DISCOVERY_END for record in records):
        raise ValueError("sample ledger contains a non-discovery cutoff")
    purposes = Counter(record["purpose"] for record in records)
    return {
        "record_count": len(records),
        "purpose_counts": dict(sorted(purposes.items())),
        "dataset_revisions": sorted({record["dataset_revision"] for record in records}),
        "intervals": sorted(
            {(record["interval_start"], record["interval_end"]) for record in records}
        ),
    }


def _evidence_tree() -> tuple[str, int]:
    entries = []
    for path in sorted(value for value in FORMAL_ROOT.rglob("*") if value.is_file()):
        if path.name == ".foundation.clock":
            continue
        entries.append((path.relative_to(FORMAL_ROOT).as_posix(), _sha256_file(path)))
    return canonical_sha256(entries), len(entries)


def _result_summary(
    result: PublishedStrategyCandidate | PublishedNoSelection,
) -> dict[str, object]:
    common = {
        "candidate_family_ref": _plain(result.candidate_family_ref),
        "execution_manifest_ref": _plain(result.execution_manifest_ref),
        "manifest_cutoff": _entry_ref_value(result.manifest_cutoff),
    }
    if type(result) is PublishedStrategyCandidate:
        return {
            "type": "selected",
            "selection_result_ref": _plain(result.strategy_candidate_ref),
            **common,
        }
    return {
        "type": "discovery_no_selection",
        "no_selection_ref": _plain(result.candidate_family_ref),
        "reason_code": result.reason_code,
        **common,
    }


def _build_summary(
    foundation: LocalFoundation,
    result: PublishedStrategyCandidate | PublishedNoSelection,
) -> dict[str, object]:
    checkpoints = {
        log_name: _checkpoint_value(foundation.checkpoint(log_name))
        for log_name in OWNER_LOGS
    }
    evidence_hash, evidence_count = _evidence_tree()
    outcome = _outcome_summary(foundation)
    if outcome["count"] != 16:
        raise ValueError("formal Experiment must preserve exactly 16 task outcomes")
    inputs = frozen_inputs()
    return {
        "type": "koruusdt_discovery_experiment_v1",
        "schema_version": SCHEMA_VERSION,
        "experiment_ref": inputs.experiment_spec.ref,
        "selection_policy_ref": inputs.selection_policy.ref,
        "selection": _result_summary(result),
        "owner_log_checkpoints": checkpoints,
        "task_outcomes": {
            "count": outcome["count"],
            "states": outcome["states"],
        },
        "completed_publication_refs": outcome["completed_publication_refs"],
        "analysis_refs": outcome["analysis_refs"],
        "sample_ledger": _sample_summary(foundation),
        "replay_verified": True,
        "network_performed": False,
        "holdout_touched": False,
        "commits": _commits(),
        "retained_hashes": _retained_hashes(),
        "evidence": {
            "root": "research/koruusdt/data/formal_discovery_v1",
            "file_count": evidence_count,
            "tree_sha256": evidence_hash,
        },
        "manifest_sha256": "",
    }


def _validate_summary_shape(summary: Mapping[str, object]) -> None:
    inputs = frozen_inputs()
    if summary.get("experiment_ref") != inputs.experiment_spec.ref:
        raise ValueError("summary Experiment ref mismatch")
    if summary.get("selection_policy_ref") != inputs.selection_policy.ref:
        raise ValueError("summary selection policy ref mismatch")
    selection = summary.get("selection")
    if type(selection) is not dict or selection.get("type") not in {
        "selected",
        "discovery_no_selection",
    }:
        raise ValueError("summary selection result is invalid")
    if not {"candidate_family_ref", "execution_manifest_ref", "manifest_cutoff"} <= set(
        selection
    ):
        raise ValueError("summary selection evidence is incomplete")
    if selection["type"] == "selected" and "selection_result_ref" not in selection:
        raise ValueError("summary selected result ref is absent")
    if selection["type"] == "discovery_no_selection" and not {
        "no_selection_ref",
        "reason_code",
    } <= set(selection):
        raise ValueError("summary no-selection ref is absent")
    checkpoints = summary.get("owner_log_checkpoints")
    if type(checkpoints) is not dict or set(checkpoints) != set(OWNER_LOGS):
        raise ValueError("summary owner log checkpoints are incomplete")
    for log_name, checkpoint in checkpoints.items():
        if (
            type(checkpoint) is not dict
            or checkpoint.get("log_name") != log_name
            or set(checkpoint)
            != {
                "log_name",
                "as_of",
                "upper_log_sequence",
                "head_receipt_hash",
            }
        ):
            raise ValueError("summary owner log checkpoint is invalid")
    outcomes = summary.get("task_outcomes")
    if type(outcomes) is not dict or outcomes.get("count") != 16:
        raise ValueError("summary must contain exactly 16 task outcomes")
    states = outcomes.get("states")
    if (
        type(states) is not dict
        or any(type(count) is not int or count < 0 for count in states.values())
        or sum(cast(dict[str, int], states).values()) != 16
    ):
        raise ValueError("summary task outcome states are invalid")
    if (
        type(summary.get("completed_publication_refs")) is not list
        or type(summary.get("analysis_refs")) is not list
    ):
        raise ValueError("summary completed/analysis refs are invalid")
    sample = summary.get("sample_ledger")
    discovery_count = len(frozen_inputs().trial_executions)
    if (
        type(sample) is not dict
        or sample.get("record_count") != discovery_count + 1
        or sample.get("purpose_counts")
        != {"discovery": discovery_count, "selection": 1}
        or sample.get("dataset_revisions") != [DATASET_REVISION]
        or sample.get("intervals") != [[DISCOVERY_START, DISCOVERY_END]]
    ):
        raise ValueError("summary sample ledger is invalid")


def validate_summary() -> dict[str, Any]:
    _verify_pins()
    if not OUTPUT.exists():
        raise ValueError("checked discovery Experiment summary is absent")
    summary = _validate_canonical(OUTPUT, "koruusdt_discovery_experiment_v1")
    _validate_summary_shape(summary)
    if not STATE_IDENTITY.exists():
        raise ValueError("formal discovery state identity is absent")
    existing_state = _validate_canonical(
        STATE_IDENTITY, "koruusdt_formal_discovery_state_identity_v1"
    )
    if existing_state != json.loads(retained.manifest_bytes(_state_value())):
        raise ValueError("formal discovery state identity is incompatible")
    foundation = LocalFoundation(
        FORMAL_ROOT / "foundation", clock=lambda: FOUNDATION_TIME
    )
    checkpoints = {
        log_name: _checkpoint_value(foundation.checkpoint(log_name))
        for log_name in OWNER_LOGS
    }
    if summary.get("owner_log_checkpoints") != checkpoints:
        raise ValueError("summary owner-log checkpoints do not match evidence")
    outcomes = _outcome_summary(foundation)
    if summary.get("task_outcomes") != {
        "count": outcomes["count"],
        "states": outcomes["states"],
    }:
        raise ValueError("summary task outcomes do not match evidence")
    if summary.get("completed_publication_refs") != outcomes[
        "completed_publication_refs"
    ] or summary.get("analysis_refs") != outcomes["analysis_refs"]:
        raise ValueError("summary publication refs do not match evidence")
    if summary.get("sample_ledger") != _sample_summary(foundation):
        raise ValueError("summary sample ledger does not match evidence")
    _validate_selection_evidence(summary, foundation)
    evidence_hash, evidence_count = _evidence_tree()
    evidence = summary.get("evidence")
    if type(evidence) is not dict or evidence != {
        "root": "research/koruusdt/data/formal_discovery_v1",
        "file_count": evidence_count,
        "tree_sha256": evidence_hash,
    }:
        raise ValueError("formal discovery evidence hash mismatch")
    if (
        summary.get("commits") != _commits()
        or summary.get("retained_hashes") != _retained_hashes()
    ):
        raise ValueError("summary authority pins mismatch")
    if summary.get("replay_verified") is not True:
        raise ValueError("summary does not prove replay")
    if (
        summary.get("network_performed") is not False
        or summary.get("holdout_touched") is not False
    ):
        raise ValueError("summary violates offline discovery scope")
    return summary


def _reconcile_summary_from_evidence() -> dict[str, Any]:
    summary = _validate_canonical(OUTPUT, "koruusdt_discovery_experiment_v1")
    _validate_summary_shape(summary)
    foundation = LocalFoundation(
        FORMAL_ROOT / "foundation", clock=lambda: FOUNDATION_TIME
    )
    _validate_selection_evidence(summary, foundation)
    outcome = _outcome_summary(foundation)
    summary["owner_log_checkpoints"] = {
        log_name: _checkpoint_value(foundation.checkpoint(log_name))
        for log_name in OWNER_LOGS
    }
    summary["task_outcomes"] = {
        "count": outcome["count"],
        "states": outcome["states"],
    }
    summary["completed_publication_refs"] = outcome["completed_publication_refs"]
    summary["analysis_refs"] = outcome["analysis_refs"]
    summary["sample_ledger"] = _sample_summary(foundation)
    summary["commits"] = _commits()
    summary["retained_hashes"] = _retained_hashes()
    evidence_hash, evidence_count = _evidence_tree()
    summary["evidence"] = {
        "root": "research/koruusdt/data/formal_discovery_v1",
        "file_count": evidence_count,
        "tree_sha256": evidence_hash,
    }
    summary["replay_verified"] = True
    summary["network_performed"] = False
    summary["holdout_touched"] = False
    _write_canonical(OUTPUT, cast(dict[str, object], summary))
    return validate_summary()


def run() -> dict[str, Any]:
    _verify_pins()
    _prepare_state()
    if OUTPUT.exists():
        return _reconcile_summary_from_evidence()
    rebuilt_manifest, rebuilt_context = cast(
        tuple[dict[str, Any], dict[str, Any]],
        retained.build_manifest(return_context=True),
    )
    bundle = _verify_context(rebuilt_manifest, rebuilt_context)
    foundation = LocalFoundation(
        FORMAL_ROOT / "foundation", clock=lambda: FOUNDATION_TIME
    )
    for envelope in (*bundle.target_result.artifacts, *bundle.authority_artifacts):
        foundation.put(envelope=envelope)
    metric_ref = BacktestAnalysisRuntime(foundation).publish_metric_profile()
    if _plain(metric_ref) != METRIC_PROFILE_REF:
        raise ValueError("public metric profile ref mismatch")
    market_reader = _publish_bundle(bundle)
    publication_root = FORMAL_ROOT / "backtest_publications"
    operations = BinanceUsdmTradifiBacktestOperations(
        intent_templates=_intent_templates(bundle),
        provider_inputs=BinanceUsdmTradifiProviderInputs(
            _build_artifact_manifest(), INITIAL_EQUITY
        ),
        artifact_reader=foundation,
        artifact_publisher=foundation,
        market_reader=market_reader,
        publication_root=publication_root,
    )
    result, _ = execute_with_replay(
        frozen_inputs(),
        foundation,
        SampleConsumptionLedger(foundation),
        operations,
        publication_root,
    )
    if OUTPUT.exists():
        summary = validate_summary()
        if summary["selection"] != _result_summary(result):
            raise ValueError("replayed result does not match canonical summary")
        return summary
    summary = _build_summary(foundation, result)
    _write_canonical(OUTPUT, summary)
    return validate_summary()


def _die(message: str) -> NoReturn:
    raise SystemExit(message)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.validate_only:
            summary = validate_summary()
            print(f"validated {OUTPUT}: {summary['manifest_sha256']}", file=sys.stderr)
            return 0
        summary = run()
        print(f"wrote {OUTPUT}: {summary['manifest_sha256']}", file=sys.stderr)
        return 0
    except (
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as error:
        _die(f"discovery Experiment failed: {error}")


if __name__ == "__main__":
    raise SystemExit(main())
