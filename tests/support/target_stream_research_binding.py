from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import crypto_quant_backtest as backtest
from crypto_quant_domain import (
    ArtifactRef,
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
    SourceSequence,
    StrategySleeveId,
    TimeInForce,
    TimelinePhase,
    UtcInstant,
    VenueId,
    canonical_bytes,
    canonical_sha256,
)
from crypto_quant_market_data import InMemoryMarketBundleReader, MarketEvent
from crypto_quant_research import (
    DataSlice,
    ExperimentParameterCombination,
    ExperimentSelectionPolicy,
    ExperimentSpec,
    FrozenTargetExperimentInputs,
    HardFilter,
    OrderingCriterion,
    TargetRecipe,
    TrialExecution,
)
from crypto_quant_trading import (
    MarkObservation,
    OrderCapabilityKey,
    OrderCapabilitySet,
    OrderStyleCapability,
    PriceConstraintShape,
    QuantityLattice,
)
from crypto_quant_validation import Holdout, OosRule, ValidationPolicy

RESERVED_AT = "2026-08-26T00:00:00.000000Z"
RECEIVED_AT = "2026-08-26T00:00:01.000000Z"
BACKTEST_SHA = "f73d068d24ffb7ecc0b7d78194fcbc96908d3c04"

_VENUE = VenueId("synthetic")
_USD = CurrencyId("USD")
_INSTRUMENT = InstrumentId(_VENUE, "cash:btc-usd")


def plain(value: object) -> Any:
    return json.loads(canonical_bytes(value))


def artifact_ref(value: Mapping[str, Any]) -> ArtifactRef:
    return ArtifactRef(
        value["artifact_type"], value["schema_version"], value["content_hash"]
    )


def _hash(marker: str) -> str:
    return "sha256:" + marker * 64


def _artifact_wire(artifact_type: str, marker: str) -> dict[str, object]:
    return ArtifactRef(artifact_type, 1, _hash(marker)).to_canonical_dict()


def _target_ref(value: Mapping[str, Any]) -> backtest.BacktestTargetStreamRef:
    return backtest.BacktestTargetStreamRef(artifact_ref(value["artifact_ref"]))


def _catalog() -> InstrumentCatalog:
    btc = CurrencyId("BTC")
    return InstrumentCatalog(
        currencies=(btc, _USD),
        instruments=(
            InstrumentDefinition(
                _INSTRUMENT, InstrumentType.SPOT, btc, _USD, _USD
            ),
        ),
        symbol_timelines=(),
    )


def _target_event() -> MarketEvent:
    return MarketEvent(
        event_id="target-100",
        stream_key="targets",
        event_type=backtest.TARGET_STREAM_EVENT_TYPE,
        capability=backtest.TARGET_STREAM_CAPABILITY,
        instrument_id=None,
        event_time=UtcInstant(100),
        available_time=UtcInstant(100),
        phase=TimelinePhase(30, "strategy_decision"),
        source_sequence=SourceSequence(1),
        revision_id="rev-1",
        supersedes_revision_id=None,
        source_key="targets.v1",
        source_hash=_hash("1"),
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
                "reason": "platform target-stream golden",
                "evidence": {"source": "fixed"},
            },
        },
    )


def _bar_event() -> MarketEvent:
    return MarketEvent(
        event_id="bar-200",
        stream_key="bars.open",
        event_type=backtest.BAR_OPEN_EVENT_TYPE,
        capability=backtest.BAR_OPEN_CAPABILITY,
        instrument_id=_INSTRUMENT,
        event_time=UtcInstant(200),
        available_time=UtcInstant(200),
        phase=TimelinePhase(60, "bar_open"),
        source_sequence=SourceSequence(2),
        revision_id="rev-1",
        supersedes_revision_id=None,
        source_key="bars.open.v1",
        source_hash=_hash("2"),
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


def _manifest() -> backtest.BuildArtifactManifest:
    roles = (
        (backtest.BuildArtifactRole.DECISION_SOURCE, "target-source", "1"),
        (backtest.BuildArtifactRole.TRADING_DOMAIN, "domain", "2"),
        (backtest.BuildArtifactRole.TRADING_KERNEL, "trading", "3"),
        (backtest.BuildArtifactRole.MARKET_DATA_CONTRACTS, "market", "4"),
        (backtest.BuildArtifactRole.BACKTEST_RUNTIME, "backtest", "5"),
    )
    return backtest.BuildArtifactManifest(
        schema_version=1,
        build_key="platform.target-stream-research.v1",
        artifacts=tuple(
            backtest.BuildArtifactRef(
                role,
                key,
                "0.1.0",
                backtest.ArtifactInstallMode.WHEEL,
                backtest.SourceTreeState.CLEAN,
                _hash(marker),
                None,
            )
            for role, key, marker in roles
        ),
        dependency_lock_hash=_hash("6"),
        runtime_libraries=(
            backtest.RuntimeLibraryRef("python", "3.13.5", _hash("7")),
        ),
        container_image_digest=None,
        provenance=backtest.BuildProvenance(
            BACKTEST_SHA,
            "platform-fan-in",
            "/workspace/platform",
            UtcInstant(1_000),
        ),
    )


def _lattice() -> QuantityLattice:
    return QuantityLattice.create(
        instrument_id=_INSTRUMENT,
        lattice_key="lattice.v1",
        lattice_version=1,
        atomic_scale=Scale(3),
        step_units=1,
        buy_lot_units=1,
        sell_lot_units=1,
        min_quantity_units=1,
        min_notional=Money(100, Scale(2), "USD"),
        odd_lot_close_permitted=False,
    )


def _capabilities() -> OrderCapabilitySet:
    return OrderCapabilitySet.create(
        capability_set_key="capabilities.v1",
        capability_set_version=1,
        style_capabilities=(
            OrderStyleCapability(
                ExecutionStyle.MARKET,
                (PriceConstraintShape.NONE,),
                (TimeInForce.DAY,),
            ),
        ),
        supports_reduce_only=True,
        supported_position_effects=(
            PositionEffect.AUTO,
            PositionEffect.OPEN,
            PositionEffect.CLOSE,
        ),
        declared_capability_keys=tuple(value.value for value in OrderCapabilityKey),
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
        source_event_id=f"mark-{source}",
        revision_id="rev-1",
    )


class FixedTargetMaterializer:
    def __init__(self, strategy_artifact: object, target_stream: object) -> None:
        self.strategy_artifact = strategy_artifact
        self.target_stream = target_stream
        self.calls = 0
        self.requests: list[dict[str, object]] = []

    def materialize_target(
        self, request: Mapping[str, object]
    ) -> Mapping[str, object]:
        self.calls += 1
        self.requests.append(deepcopy(dict(request)))
        return {
            "type": "target_materialization_result",
            "schema_version": 1,
            "request_hash": canonical_sha256(request),
            "strategy_artifact": self.strategy_artifact,
            "input_data_hash": _hash("d"),
            "target_stream": self.target_stream,
        }


class CashTargetStreamBinding:
    def __init__(self, foundation: Any, publication_root: Path) -> None:
        self.foundation = foundation
        self.publication_root = publication_root
        self.repository = backtest.BacktestTargetStreamRepository(
            reader=foundation, publisher=foundation
        )
        self.analysis_runtime = backtest.BacktestAnalysisRuntime(foundation)
        self.metric_profile_ref = self.analysis_runtime.publish_metric_profile()
        self.target_stream = backtest.PrecomputedTargetStream(
            "targets", (_target_event(),)
        )
        bar = _bar_event()
        self.market_reader = InMemoryMarketBundleReader.build(
            bundle_key="platform-target-stream-market-v1",
            schema_version=1,
            coverage_start=UtcInstant(0),
            coverage_end_exclusive=UtcInstant(400),
            instrument_catalog_hash=canonical_sha256(_catalog()),
            capabilities=(bar.capability,),
            streams={"bars.open": (bar,)},
        )
        self.strategy_artifact = plain(
            next(
                item
                for item in _manifest().artifacts
                if item.role is backtest.BuildArtifactRole.DECISION_SOURCE
            )
        )
        self.publish_target_calls = 0
        self.load_target_calls = 0
        self.preparation_calls = 0
        self.run_calls = 0
        self.economic_run_calls = 0
        self.derive_calls = 0
        self._prepared: dict[str, backtest.PreparedBacktestExecution] = {}
        self._run_keys: set[str] = set()
        self._evidence = backtest.BacktestEvidenceRepository(foundation)

    def materializer(self) -> FixedTargetMaterializer:
        return FixedTargetMaterializer(
            self.strategy_artifact, plain(self.target_stream)
        )

    def publish_target(
        self,
        producer_context_ref: Mapping[str, object],
        target_stream: Mapping[str, object],
    ) -> dict[str, object]:
        self.publish_target_calls += 1
        if canonical_bytes(target_stream) != canonical_bytes(self.target_stream):
            raise ValueError("target stream does not match the fixed golden")
        return plain(
            self.repository.publish(
                artifact_ref(producer_context_ref), self.target_stream
            )
        )

    def load_target(self, ref: Mapping[str, object]) -> dict[str, object]:
        self.load_target_calls += 1
        loaded = self.repository.load(_target_ref(ref))
        return {
            "ref": plain(loaded.ref),
            "producer_context_ref": plain(loaded.producer_context_ref),
            "target_stream": plain(loaded.target_stream),
            "digest": loaded.digest,
        }

    def _prepare(
        self, consumer: str, target_ref: Mapping[str, object]
    ) -> backtest.PreparedBacktestExecution:
        self.preparation_calls += 1
        prepared = backtest.prepare_cash_target_stream_backtest(
            request_intent=backtest.CashDevelopmentRequestIntent(
                1,
                consumer,
                backtest.TimelineWindow(
                    UtcInstant(0), UtcInstant(90), UtcInstant(300)
                ),
                "account:primary",
                _USD,
                7,
            ),
            provider_inputs=backtest.CashDevelopmentProviderInputs(
                1,
                _manifest(),
                _catalog(),
                "trend-v1",
                StrategySleeveId("trend.primary"),
                Money(100_000, Scale(2), "USD"),
                _lattice(),
                _mark(10_000, 100, "decision"),
                _mark(8_000, 299, "final"),
                _capabilities(),
            ),
            target_stream_ref=_target_ref(target_ref),
            artifact_reader=self.foundation,
            artifact_publisher=self.foundation,
            market_reader=self.market_reader,
            publication_root=self.publication_root,
        )
        self._prepared[canonical_bytes(prepared.request_ref).decode()] = prepared
        return prepared

    def prepare_trials(
        self, trials: tuple[Any, ...], target_ref: Mapping[str, object]
    ) -> tuple[TrialExecution, ...]:
        executions = []
        for trial in trials:
            request_ref = plain(self._prepare(trial.ref, target_ref).request_ref)
            executions.append(TrialExecution(trial.ref, request_ref, request_ref))
        return tuple(executions)

    def prepare_target(
        self,
        validation_case_ref: Mapping[str, object],
        target_ref: Mapping[str, object],
    ) -> dict[str, object]:
        consumer = canonical_bytes(validation_case_ref).decode()
        return plain(self._prepare(consumer, target_ref).request_ref)

    def run(self, request: Mapping[str, object]) -> dict[str, object]:
        self.run_calls += 1
        request_ref = dict(request)
        request_ref.pop("experiment_id", None)
        key = canonical_bytes(request_ref).decode()
        prepared = self._prepared.get(key)
        if prepared is None:
            raise KeyError(key)
        run_key = canonical_bytes(prepared.request_ref).decode()
        if run_key not in self._run_keys:
            self._run_keys.add(run_key)
            self.economic_run_calls += 1
        if key not in self._run_keys:
            self._run_keys.add(key)
        return plain(prepared.runtime.run(prepared.execution_request))

    def load_completed(self, ref: Mapping[str, Any]) -> dict[str, object]:
        completed = self._evidence.load_completed(
            backtest.BacktestCanonicalPublicationRef(artifact_ref(ref["artifact_ref"]))
        )
        return {
            "publication_ref": plain(completed.source_publication_ref),
            "semantic_run_id": completed.semantic_run_id,
            "execution_result_hash": completed.source_execution_result_hash,
            "result_grade": completed.result_grade.value,
        }

    def load_terminal(self, ref: object) -> dict[str, object]:
        raise AssertionError(f"unexpected terminal Backtest result: {ref}")

    def derive(
        self,
        publication_ref: Mapping[str, Any],
        metric_profile_ref: Mapping[str, Any],
    ) -> dict[str, object]:
        self.derive_calls += 1
        if artifact_ref(metric_profile_ref) != self.metric_profile_ref:
            raise ValueError("metric profile does not match the golden")
        completed = self._evidence.load_completed(
            backtest.BacktestCanonicalPublicationRef(
                artifact_ref(publication_ref["artifact_ref"])
            )
        )
        return plain(
            self.analysis_runtime.derive(completed, self.metric_profile_ref)
        )

    def load_analysis(self, ref: Mapping[str, Any]) -> dict[str, object]:
        return plain(
            self._evidence.load_analysis(
                backtest.AnalysisArtifactRef(artifact_ref(ref["artifact_ref"]))
            )
        )


def target_experiment_inputs(
    binding: CashTargetStreamBinding,
) -> FrozenTargetExperimentInputs:
    recipe = TargetRecipe(
        "fixed-targets",
        binding.strategy_artifact,
        _hash("c"),
        ("bars.open",),
    )
    metric_ref = binding.metric_profile_ref.to_canonical_dict()
    spec = ExperimentSpec(
        _artifact_wire("hypothesis", "1"),
        _artifact_wire("strategy_definition", "2"),
        (
            DataSlice(
                binding.market_reader.bundle_ref.to_canonical_dict(),
                "platform-discovery-v1",
                "2026-01-01T00:00:00.000000Z",
                "2026-02-01T00:00:00.000000Z",
            ),
        ),
        (ExperimentParameterCombination((("lookback", "10"),)),),
        (1,),
        (_artifact_wire("scenario", "4"),),
        _artifact_wire("backtest_template", "5"),
        None,
        (metric_ref,),
        {"max_trials": 1},
        recipe.ref,
    )
    return FrozenTargetExperimentInputs(
        spec,
        recipe,
        ExperimentSelectionPolicy(
            metric_ref,
            ("COMPLETED",),
            ("development",),
            (HardFilter("trade_count", "gte", 1),),
            (OrderingCriterion("simple_period_return", "descending"),),
            1,
            "trial_declaration_ref_ascending",
        ),
        {"type": "actor_ref", "actor_id": "research"},
        RESERVED_AT,
    )


def target_validation_policy(
    binding: CashTargetStreamBinding,
) -> ValidationPolicy:
    metric_ref = binding.metric_profile_ref.to_canonical_dict()
    return ValidationPolicy(
        ("development",),
        (metric_ref,),
        Holdout(
            binding.market_reader.bundle_ref.to_canonical_dict(),
            "platform-oos-v1",
            "2026-03-01T00:00:00.000000Z",
            "2026-04-01T00:00:00.000000Z",
            "HOLDOUT",
            False,
        ),
        OosRule(
            metric_ref,
            "simple_period_return",
            "fraction",
            "gte",
            "-1",
            1,
        ),
    )
