from __future__ import annotations

import ast
import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

import crypto_quant_backtest as backtest
import pytest
from crypto_quant_domain import (
    ArtifactEnvelope,
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    ArtifactReadResult,
    ArtifactRef,
    ArtifactRetentionUnavailableError,
    CurrencyId,
    ExecutionStyle,
    InstrumentCatalog,
    InstrumentDefinition,
    InstrumentId,
    InstrumentType,
    Money,
    PositionEffect,
    Price,
    PricePurpose,
    Scale,
    SimulationInstant,
    SourceSequence,
    StrategySleeveId,
    TimeInForce,
    TimelinePhase,
    UtcInstant,
    VenueId,
    canonical_bytes,
    canonical_sha256,
)
from crypto_quant_foundation import LocalFoundation
from crypto_quant_market_data import InMemoryMarketBundleReader, MarketEvent
from crypto_quant_research import (
    DataSlice,
    FeatureDatasetManifest,
    FeatureRecipe,
    ModelBuildPlan,
    TrainerRecipe,
    validate_model_build,
)
from crypto_quant_trading import (
    MarkObservation,
    OrderCapabilityKey,
    OrderCapabilitySet,
    OrderStyleCapability,
    PriceConstraintShape,
    QuantityLattice,
)

_ROOT = Path(__file__).resolve().parents[2]
_ACCEPTED_BACKTEST_SHA = "033344172b24847e73941bb97a06da0490527edf"
_CURRENT_BACKTEST_SHA = "f73d068d24ffb7ecc0b7d78194fcbc96908d3c04"
_VENUE = VenueId("synthetic")
_USD = CurrencyId("USD")
_INSTRUMENT = InstrumentId(_VENUE, "cash:btc-usd")
_TARGET_TIME = UtcInstant(100)
_BAR_TIME = UtcInstant(200)


def _hash(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()


def _file_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _source_revision() -> tuple[str, bool]:
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=_ROOT, text=True
    ).strip()
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(Path(__file__).relative_to(_ROOT))],
        cwd=_ROOT,
        check=False,
        capture_output=True,
    ).returncode == 0
    clean = tracked and subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", str(Path(__file__).relative_to(_ROOT))],
        cwd=_ROOT,
        check=False,
    ).returncode == 0
    return revision, clean


def _catalog() -> InstrumentCatalog:
    base = CurrencyId("BTC")
    return InstrumentCatalog(
        currencies=(base, _USD),
        instruments=(
            InstrumentDefinition(
                _INSTRUMENT,
                InstrumentType.SPOT,
                base,
                _USD,
                _USD,
            ),
        ),
        symbol_timelines=(),
    )


def _target_event() -> MarketEvent:
    return MarketEvent(
        event_id="cash-development-target-100",
        stream_key="targets",
        event_type=backtest.TARGET_STREAM_EVENT_TYPE,
        capability=backtest.TARGET_STREAM_CAPABILITY,
        instrument_id=None,
        event_time=_TARGET_TIME,
        available_time=_TARGET_TIME,
        phase=TimelinePhase(30, "strategy_decision"),
        source_sequence=SourceSequence(1),
        revision_id="rev-1",
        supersedes_revision_id=None,
        source_key="platform.cash-development.targets.v1",
        source_hash=_hash("platform cash-development targets v1"),
        payload={
            "schema_version": 1,
            "candidate": {
                "schema_version": 1,
                "strategy_id": "trend-v1",
                "sleeve_id": "trend.primary",
                "decision_time": 100,
                "observed_through": 99,
                "effective_time": 100,
                "expires_at": 250,
                "targets": [
                    {
                        "instrument_id": {
                            "venue": _VENUE.value,
                            "stable_key": _INSTRUMENT.stable_key,
                        },
                        "value": "0.5",
                    }
                ],
                "confidence": "1",
                "reason": "Platform P00 public binding",
                "evidence": {"model_revision": _hash("platform-p00-model-v1")},
            },
        },
    )


def _bar_event() -> MarketEvent:
    return MarketEvent(
        event_id="cash-development-bar-200",
        stream_key="bars.open",
        event_type=backtest.BAR_OPEN_EVENT_TYPE,
        capability=backtest.BAR_OPEN_CAPABILITY,
        instrument_id=_INSTRUMENT,
        event_time=_BAR_TIME,
        available_time=_BAR_TIME,
        phase=TimelinePhase(60, "bar_open"),
        source_sequence=SourceSequence(2),
        revision_id="rev-1",
        supersedes_revision_id=None,
        source_key="platform.cash-development.bar-open.v1",
        source_hash=_hash("platform cash-development bar-open v1"),
        payload={
            "schema_version": 1,
            "bar_kind": "real",
            "open_price": {
                "units": 10_000,
                "scale": 2,
                "quote_currency": "USD",
            },
        },
    )


def _market_reader() -> InMemoryMarketBundleReader:
    target = _target_event()
    bar = _bar_event()
    return InMemoryMarketBundleReader.build(
        bundle_key="platform-cash-development-public-seam-v1",
        schema_version=1,
        coverage_start=UtcInstant(0),
        coverage_end_exclusive=UtcInstant(400),
        instrument_catalog_hash=canonical_sha256(_catalog()),
        capabilities=(target.capability, bar.capability),
        streams={"targets": (target,), "bars.open": (bar,)},
    )


def _quantity_lattice() -> QuantityLattice:
    return QuantityLattice.create(
        instrument_id=_INSTRUMENT,
        lattice_key="platform.cash-development.lattice.v1",
        lattice_version=1,
        atomic_scale=Scale(3),
        step_units=1,
        buy_lot_units=1,
        sell_lot_units=1,
        min_quantity_units=1,
        min_notional=Money(100, Scale(2), "USD"),
        odd_lot_close_permitted=False,
    )


def _capabilities(*, market: bool = True) -> OrderCapabilitySet:
    styles = (
        (
            OrderStyleCapability(
                ExecutionStyle.MARKET,
                (PriceConstraintShape.NONE,),
                (TimeInForce.DAY,),
            ),
        )
        if market
        else ()
    )
    return OrderCapabilitySet.create(
        capability_set_key="platform.cash-development.capabilities.v1",
        capability_set_version=1,
        style_capabilities=styles,
        supports_reduce_only=True,
        supported_position_effects=(
            PositionEffect.AUTO,
            PositionEffect.OPEN,
            PositionEffect.CLOSE,
        ),
        declared_capability_keys=tuple(value.value for value in OrderCapabilityKey),
    )


def _build_manifest() -> backtest.BuildArtifactManifest:
    package_hashes = {
        backtest.BuildArtifactRole.TRADING_DOMAIN: (
            "crypto-quant-domain",
            "6552f027631013c41073f394a3ac8c16326fe56f27313bcc864074255682f734",
        ),
        backtest.BuildArtifactRole.TRADING_KERNEL: (
            "crypto-quant-trading",
            "68dedd449a9aeb56c9fd547d675cd3029c7a4102af13ac000645913515e5acf2",
        ),
        backtest.BuildArtifactRole.MARKET_DATA_CONTRACTS: (
            "crypto-quant-market-data",
            "8e63e9a1ea212c3003da3a6e48776f76800d088915a100ae517251cbbe4980cb",
        ),
        backtest.BuildArtifactRole.BACKTEST_RUNTIME: (
            "crypto-quant-backtest",
            "2d8c0ffbc581ae4e8e75f974f6f4c3d897ca7f24620a8a8955568073f1749e5b",
        ),
    }
    revision, clean = _source_revision()
    artifacts = [
        backtest.BuildArtifactRef(
            role=backtest.BuildArtifactRole.DECISION_SOURCE,
            artifact_key="platform-p00-public-binding",
            artifact_version="1",
            install_mode=(
                backtest.ArtifactInstallMode.WHEEL
                if clean
                else backtest.ArtifactInstallMode.EDITABLE
            ),
            source_tree_state=(
                backtest.SourceTreeState.CLEAN
                if clean
                else backtest.SourceTreeState.DIRTY
            ),
            content_hash=_file_hash(Path(__file__)),
            source_snapshot_hash=None,
        )
    ]
    artifacts.extend(
        backtest.BuildArtifactRef(
            role=role,
            artifact_key=key,
            artifact_version="0.1.0",
            install_mode=backtest.ArtifactInstallMode.WHEEL,
            source_tree_state=backtest.SourceTreeState.CLEAN,
            content_hash="sha256:" + digest,
            source_snapshot_hash=None,
        )
        for role, (key, digest) in package_hashes.items()
    )
    return backtest.BuildArtifactManifest(
        schema_version=1,
        build_key="platform.p00.cash-development.v1",
        artifacts=tuple(artifacts),
        dependency_lock_hash=_file_hash(_ROOT / "uv.lock"),
        runtime_libraries=(
            backtest.RuntimeLibraryRef(
                library_key="python",
                version="3.13.5",
                content_hash=_hash("CPython 3.13.5"),
            ),
        ),
        container_image_digest=None,
        provenance=backtest.BuildProvenance(
            git_commit=revision,
            hostname="platform-p00",
            source_root="/workspace/platform",
            built_at=UtcInstant(1_000),
        ),
    )


def _mark(units: int, at: int, source: str) -> MarkObservation:
    return MarkObservation(
        instrument_id=_INSTRUMENT,
        quote_currency_id=_USD,
        price_purpose=PricePurpose.VALUATION,
        price=Price(units, Scale(2), str(_INSTRUMENT), "USD"),
        observed_at=UtcInstant(at),
        available_at=UtcInstant(at),
        stream_id=f"marks.{source}",
        source_event_id=f"platform-cash-development-{source}",
        revision_id="rev-1",
    )


def _provider_inputs(*, market: bool = True) -> backtest.CashDevelopmentProviderInputs:
    return backtest.CashDevelopmentProviderInputs(
        schema_version=1,
        build_artifact_manifest=_build_manifest(),
        instrument_catalog=_catalog(),
        strategy_id="trend-v1",
        sleeve_id=StrategySleeveId("trend.primary"),
        initial_cash=Money(100_000, Scale(2), "USD"),
        quantity_lattice=_quantity_lattice(),
        decision_mark=_mark(10_000, 100, "decision"),
        final_mark=_mark(8_000, 299, "final"),
        order_capabilities=_capabilities(market=market),
    )


def _intent(experiment_id: str) -> backtest.CashDevelopmentRequestIntent:
    return backtest.CashDevelopmentRequestIntent(
        schema_version=1,
        experiment_id=experiment_id,
        timeline_window=backtest.TimelineWindow(
            UtcInstant(0), UtcInstant(90), UtcInstant(300)
        ),
        execution_account_id="account:primary",
        reporting_currency=_USD,
        master_random_seed=7,
    )


def _prepare_with(
    foundation: LocalFoundation,
    publication_root: Path,
    *,
    experiment_id: str,
    market: bool = True,
    store: object | None = None,
) -> backtest.PreparedBacktestExecution:
    structural_store = store or foundation
    return backtest.prepare_cash_development_backtest(
        request_intent=_intent(experiment_id),
        provider_inputs=_provider_inputs(market=market),
        artifact_reader=structural_store,  # type: ignore[arg-type]
        artifact_publisher=structural_store,  # type: ignore[arg-type]
        market_reader=_market_reader(),
        publication_root=publication_root,
    )


def _prepare(
    tmp_path: Path,
    *,
    experiment_id: str = "platform:trial:cash-development-1",
    market: bool = True,
) -> tuple[backtest.PreparedBacktestExecution, LocalFoundation]:
    foundation = LocalFoundation(tmp_path / "foundation")
    return (
        _prepare_with(
            foundation,
            tmp_path / "publications",
            experiment_id=experiment_id,
            market=market,
        ),
        foundation,
    )


class _FaultInjectingStore:
    def __init__(self, foundation: LocalFoundation) -> None:
        self.foundation = foundation
        self.target: ArtifactRef | None = None
        self.failure: str | None = None
        self.substitute: ArtifactRef | None = None

    def put(self, *, envelope: ArtifactEnvelope) -> ArtifactRef:
        return self.foundation.put(envelope=envelope)

    def read(self, *, ref: ArtifactRef) -> ArtifactReadResult:
        if ref != self.target:
            return self.foundation.read(ref=ref)
        if self.failure == "not_found":
            raise ArtifactNotFoundError("injected missing execution input")
        if self.failure == "retention":
            raise ArtifactRetentionUnavailableError("injected retention failure")
        if self.failure == "integrity":
            raise ArtifactIntegrityError("injected execution-input tamper")
        if self.failure == "substitution" and self.substitute is not None:
            return self.foundation.read(ref=self.substitute)
        raise AssertionError("fault target requires a valid failure mode")


@dataclass(frozen=True, slots=True)
class _TamperingReader:
    foundation: LocalFoundation
    target: ArtifactRef

    def read(self, *, ref: ArtifactRef) -> ArtifactReadResult:
        if ref == self.target:
            raise ArtifactIntegrityError("injected structural tamper")
        return self.foundation.read(ref=ref)


@dataclass(frozen=True, slots=True)
class _RetentionReader:
    foundation: LocalFoundation
    target: ArtifactRef

    def read(self, *, ref: ArtifactRef) -> ArtifactReadResult:
        if ref == self.target:
            raise ArtifactRetentionUnavailableError("retention unavailable")
        return self.foundation.read(ref=ref)


def test_public_binding_completes_replays_and_derives_verified_analysis(
    tmp_path: Path,
) -> None:
    prepared, foundation = _prepare(tmp_path)

    request_read = foundation.read(ref=prepared.request_ref.to_artifact_ref())
    assert canonical_bytes(request_read.envelope.payload) == canonical_bytes(
        prepared.execution_request.request
    )
    assert prepared.execution_request.schema_version == 2
    assert prepared.execution_request.request.experiment_id == _intent(
        "platform:trial:cash-development-1"
    ).experiment_id

    first = prepared.runtime.run(prepared.execution_request)
    attempt_records = tuple(
        (tmp_path / "publications").rglob("attempt-execution-record.json")
    )
    second = prepared.runtime.run(prepared.execution_request)
    assert type(first) is backtest.BacktestCanonicalPublicationRef
    assert second == first
    assert tuple(
        (tmp_path / "publications").rglob("attempt-execution-record.json")
    ) == attempt_records

    other, _ = _prepare(
        tmp_path / "other-context",
        experiment_id="platform:trial:cash-development-2",
    )
    assert other.request_ref != prepared.request_ref
    assert other.semantic_run_id != prepared.semantic_run_id

    repository = backtest.BacktestEvidenceRepository(foundation)
    completed = repository.load_completed(first)
    assert completed.semantic_run_id == prepared.semantic_run_id
    assert len(completed.execution_summary.fills) == 1
    assert completed.execution_summary.final_portfolio_snapshot.equity == Money(
        90_000, Scale(2), "USD"
    )

    analysis_runtime = backtest.BacktestAnalysisRuntime(foundation)
    profile_ref = analysis_runtime.publish_metric_profile()
    first_analysis = analysis_runtime.derive(completed, profile_ref)
    second_analysis = analysis_runtime.derive(completed, profile_ref)
    assert second_analysis == first_analysis
    analysis = repository.load_analysis(first_analysis)
    assert analysis.simple_period_return == "-0.1"
    assert analysis.trade_count == 1
    assert analysis.result_grade.value == "development"
    assert analysis.metric_profile_ref == profile_ref
    assert analysis.source_publication_ref == first
    assert analysis.source_execution_result_hash == completed.source_execution_result_hash


def test_public_binding_returns_real_blocked_and_cancelled_terminals(
    tmp_path: Path,
) -> None:
    blocked, blocked_foundation = _prepare(
        tmp_path / "blocked",
        experiment_id="platform:trial:blocked",
        market=False,
    )
    blocked_ref = blocked.runtime.run(blocked.execution_request)
    blocked_terminal = backtest.BacktestEvidenceRepository(
        blocked_foundation
    ).load_terminal(blocked_ref)
    assert blocked_terminal.status.value == "BLOCKED"
    assert blocked.runtime.run(blocked.execution_request) == blocked_ref

    cancelled, cancelled_foundation = _prepare(
        tmp_path / "cancelled",
        experiment_id="platform:trial:cancelled",
    )
    cancellation = backtest.EngineCancellationRequest(
        cancel_before_event_id=_target_event().event_id,
        reason_code="platform_cancelled",
    )
    cancelled_ref = cancelled.runtime.run_with_cancellation(
        cancelled.execution_request,
        cancellation,
    )
    cancelled_terminal = backtest.BacktestEvidenceRepository(
        cancelled_foundation
    ).load_terminal(cancelled_ref)
    assert cancelled_terminal.status.value == "CANCELLED"
    assert (
        cancelled.runtime.run_with_cancellation(
            cancelled.execution_request,
            cancellation,
        )
        == cancelled_ref
    )


@pytest.mark.parametrize(
    "failure",
    ("not_found", "retention", "integrity", "substitution"),
)
def test_execution_input_preflight_fails_before_attempt(
    tmp_path: Path,
    failure: str,
) -> None:
    foundation = LocalFoundation(tmp_path / "foundation")
    store = _FaultInjectingStore(foundation)
    publication_root = tmp_path / "publications"
    prepared = _prepare_with(
        foundation,
        publication_root,
        experiment_id=f"platform:trial:preflight-{failure}",
        store=store,
    )
    store.target = prepared.execution_request.execution_input_bundle_ref
    store.failure = failure
    store.substitute = prepared.request_ref.to_artifact_ref()

    with pytest.raises(RuntimeError, match="execution input hydration failed"):
        prepared.runtime.run(prepared.execution_request)
    assert not (publication_root / "runs").exists()


def test_public_repository_fails_closed_for_missing_tamper_and_retention(
    tmp_path: Path,
) -> None:
    prepared, foundation = _prepare(tmp_path)
    publication_ref = prepared.runtime.run(prepared.execution_request)
    assert type(publication_ref) is backtest.BacktestCanonicalPublicationRef

    missing_ref = backtest.BacktestCanonicalPublicationRef.from_artifact_ref(
        ArtifactRef("canonical_publication_manifest", 1, "sha256:" + "0" * 64)
    )
    with pytest.raises(backtest.BacktestEvidenceError) as missing:
        backtest.BacktestEvidenceRepository(foundation).load_completed(missing_ref)
    assert missing.value.code is backtest.BacktestEvidenceFailureCode.PORT_REF_NOT_FOUND

    with pytest.raises(backtest.BacktestEvidenceError) as tampered:
        backtest.BacktestEvidenceRepository(
            _TamperingReader(foundation, publication_ref.artifact_ref)
        ).load_completed(publication_ref)
    assert tampered.value.code is backtest.BacktestEvidenceFailureCode.PORT_EVIDENCE_TAMPERED

    completed = backtest.BacktestEvidenceRepository(foundation).load_completed(
        publication_ref
    )
    analysis_runtime = backtest.BacktestAnalysisRuntime(foundation)
    profile_ref = analysis_runtime.publish_metric_profile()
    analysis_ref = analysis_runtime.derive(completed, profile_ref)
    with pytest.raises(backtest.BacktestEvidenceError) as retention:
        backtest.BacktestEvidenceRepository(
            _RetentionReader(foundation, profile_ref)
        ).load_analysis(analysis_ref)
    assert retention.value.code is backtest.BacktestEvidenceFailureCode.PORT_RETENTION_UNAVAILABLE

    with pytest.raises(TypeError):
        analysis_runtime.derive(publication_ref, profile_ref)  # type: ignore[arg-type]

    repository = backtest.BacktestEvidenceRepository(foundation)
    with pytest.raises(backtest.BacktestEvidenceError) as wrong_type:
        repository.load_completed(publication_ref.artifact_ref)  # type: ignore[arg-type]
    assert wrong_type.value.code is backtest.BacktestEvidenceFailureCode.PORT_REF_TYPE_MISMATCH

    malformed_envelope = ArtifactEnvelope.create(
        "canonical_publication_manifest",
        1,
        {"type": "canonical_publication_manifest", "schema_version": 1},
    )
    malformed_ref = backtest.BacktestCanonicalPublicationRef.from_artifact_ref(
        foundation.put(envelope=malformed_envelope)
    )
    with pytest.raises(backtest.BacktestEvidenceError) as malformed:
        repository.load_completed(malformed_ref)
    assert malformed.value.code is backtest.BacktestEvidenceFailureCode.PORT_MANIFEST_INVALID

    foreign = _prepare_with(
        foundation,
        tmp_path / "foreign-publications",
        experiment_id="platform:trial:foreign-analysis-link",
    )
    foreign_publication = foreign.runtime.run(foreign.execution_request)
    assert type(foreign_publication) is backtest.BacktestCanonicalPublicationRef
    forged_analysis = backtest.BacktestAnalysis(
        metric_profile_ref=profile_ref,
        source_publication_ref=foreign_publication,
        source_execution_result_hash=completed.source_execution_result_hash,
        simple_period_return="-0.1",
        trade_count=1,
        result_grade=completed.result_grade,
    )
    forged_ref = backtest.AnalysisArtifactRef(
        foundation.put(
            envelope=ArtifactEnvelope.create("backtest_analysis", 1, forged_analysis)
        )
    )
    with pytest.raises(backtest.BacktestEvidenceError) as foreign_link:
        repository.load_analysis(forged_ref)
    assert foreign_link.value.code is backtest.BacktestEvidenceFailureCode.PORT_ANALYSIS_LINK_MISMATCH


def _model_build_evidence():
    training_slice = DataSlice(
        _market_reader().bundle_ref.to_canonical_dict(),
        "platform-model-training-v1",
        "1970-01-01T00:00:00.000000Z",
        "1970-01-01T00:00:00.000001Z",
    )
    feature = FeatureRecipe(
        "returns-v1",
        _hash("platform feature code"),
        _hash("platform feature schema"),
        ("close",),
    )
    trainer = TrainerRecipe(
        "linear-v1",
        _hash("platform trainer code"),
        "alpha.primary",
        {"ridge": "0.1"},
    )
    plan = ModelBuildPlan(feature.ref, trainer.ref, training_slice, 7)
    manifest = FeatureDatasetManifest(
        plan.ref,
        training_slice.dataset_revision,
        training_slice.interval_start,
        training_slice.interval_end,
        feature.feature_schema_hash,
        _hash("platform training data"),
        100,
    )
    artifact = backtest.ModelArtifactRef(
        model_key=trainer.model_key,
        model_hash=_hash("platform model artifact"),
        training_data_hash=manifest.training_data_hash,
        training_start=UtcInstant(0),
        training_end=UtcInstant(1_000),
        training_code_hash=trainer.training_code_hash,
        feature_schema_hash=feature.feature_schema_hash,
        available_at=SimulationInstant(
            UtcInstant(1_000),
            TimelinePhase(70, "model_availability"),
            SourceSequence(1),
        ),
        revision_id="genesis",
        supersedes_revision_id=None,
    )
    evidence = validate_model_build(
        plan,
        feature,
        trainer,
        manifest,
        artifact.to_canonical_dict(),
    )
    timeline = backtest.ModelRevisionTimeline(
        model_key=trainer.model_key,
        decision_instant=SimulationInstant(
            UtcInstant(1_000),
            TimelinePhase(70, "model_availability"),
            SourceSequence(2),
        ),
        artifacts=(artifact,),
    )
    return evidence, artifact, timeline


def test_v2_model_build_evidence_binds_real_backtest_request_and_run(
    tmp_path: Path,
) -> None:
    evidence, artifact, timeline = _model_build_evidence()
    foundation = LocalFoundation(tmp_path / "foundation")
    prepared = backtest.prepare_model_bound_cash_development_backtest(
        request_intent=_intent("platform:trial:model-bound-1"),
        provider_inputs=_provider_inputs(),
        model_timeline=timeline,
        expected_model_key=artifact.model_key,
        expected_artifact_ref_hash=artifact.artifact_ref_hash,
        artifact_reader=foundation,
        artifact_publisher=foundation,
        market_reader=_market_reader(),
        publication_root=tmp_path / "publications",
    )

    publication_ref = prepared.runtime.run(prepared.execution_request)
    completed = backtest.BacktestEvidenceRepository(foundation).load_completed(
        publication_ref
    )

    assert evidence.model_artifact["artifact_ref_hash"] == artifact.artifact_ref_hash
    assert prepared.model_binding.artifact_ref_hash == artifact.artifact_ref_hash
    assert prepared.execution_request.request.model_binding == prepared.model_binding
    assert completed.engine_context.model_binding == prepared.model_binding
    assert completed.semantic_run_id == prepared.semantic_run_id


def test_v2_model_substitution_fails_before_request_or_attempt(tmp_path: Path) -> None:
    _, artifact, timeline = _model_build_evidence()
    foundation = LocalFoundation(tmp_path / "foundation")
    publication_root = tmp_path / "publications"

    with pytest.raises(backtest.ModelPreparationFailure) as caught:
        backtest.prepare_model_bound_cash_development_backtest(
            request_intent=_intent("platform:trial:model-substitution"),
            provider_inputs=_provider_inputs(),
            model_timeline=timeline,
            expected_model_key=artifact.model_key,
            expected_artifact_ref_hash="sha256:" + "0" * 64,
            artifact_reader=foundation,
            artifact_publisher=foundation,
            market_reader=_market_reader(),
            publication_root=publication_root,
        )

    assert caught.value.code == "MODEL_BINDING_MISMATCH"
    assert not publication_root.exists()


def test_binding_imports_only_public_package_roots() -> None:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"), filename=__file__)
    imported = {
        name
        for node in ast.walk(tree)
        for name in (
            [alias.name for alias in node.names]
            if isinstance(node, ast.Import)
            else [node.module]
            if isinstance(node, ast.ImportFrom) and node.module is not None
            else []
        )
    }
    allowed_crypto_roots = {
        "crypto_quant_backtest",
        "crypto_quant_domain",
        "crypto_quant_foundation",
        "crypto_quant_market_data",
        "crypto_quant_research",
        "crypto_quant_trading",
    }
    assert {name for name in imported if name.startswith("crypto_quant")} == (
        allowed_crypto_roots
    )
    assert _CURRENT_BACKTEST_SHA in (_ROOT / "uv.lock").read_text(encoding="utf-8")
    assert subprocess.run(
        [
            "git",
            "-C",
            "backtest",
            "merge-base",
            "--is-ancestor",
            _ACCEPTED_BACKTEST_SHA,
            _CURRENT_BACKTEST_SHA,
        ],
        cwd=_ROOT,
        check=False,
    ).returncode == 0
