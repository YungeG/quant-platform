"""RETRO-V1 pure current-snapshot statistics. No Reader, I/O or financial engine.

Session anchors index the frozen market calendar, not historical information availability.
Actual late acquisition/observation and unknown historical availability remain intact.
Probabilities are estimated at Decimal precision 28, persisted at 12 places,
and scored at exactly that persisted precision. Missing observations stay missing.
"""

from __future__ import annotations

import random
import re
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from typing import Any
from zoneinfo import ZoneInfo

from experiments import a_share_price_volume_research_v1 as _reference

MODELS = ("CLIMATOLOGY", "PRICE_ONLY", "PRICE_VOLUME", "SHUFFLED_VOLUME")
RETRO_PARTITIONS = ("TRAIN", "DEVELOPMENT", "RETROSPECTIVE_EVAL")
MIN_WEEKS = (104, 26, 52)
MIN_ROWS = 50
MIN_CELL_WEEKS = 12
WARMUP = 65
HORIZON = 5
BOOTSTRAP_DRAWS = 1000
CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)
SHANGHAI = ZoneInfo("Asia/Shanghai")
ZERO = Decimal(0)
ONE = Decimal(1)
P_QUANTUM = Decimal("0.000000000001")
PriceCell = tuple[int, int, int, int, int]


RetrospectiveContractError: Any = _reference.ResearchContractError


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise RetrospectiveContractError(code, message)


def _timestamp(value: datetime) -> None:
    _require(
        type(value) is datetime
        and getattr(value.tzinfo, "key", None) == "Asia/Shanghai",
        "TIMEZONE_MISMATCH",
        "timestamps must explicitly use Asia/Shanghai",
    )


_decimal: Any = _reference._decimal


json_value: Any = _reference.json_value


canonical_bytes: Any = _reference.canonical_bytes


identity: Any = _reference.identity


def _aware(value: datetime) -> None:
    _require(
        type(value) is datetime
        and value.tzinfo is not None
        and value.utcoffset() is not None,
        "SNAPSHOT_TIME_INVALID",
        "actual snapshot/computation times need explicit timezones",
    )


@dataclass(frozen=True, slots=True)
class SnapshotProvenance:
    revision: str
    source: str
    raw_sha256: str
    event_time: datetime
    acquired_at: datetime
    observed_at: datetime
    historical_available_at: datetime | None = None

    def __post_init__(self) -> None:
        _require(
            type(self.revision) is str and bool(self.revision),
            "REVISION_CONFLICT",
            "explicit snapshot revision required",
        )
        _require(
            type(self.source) is str
            and bool(self.source)
            and type(self.raw_sha256) is str
            and re.fullmatch(r"[0-9a-f]{64}", self.raw_sha256) is not None,
            "SOURCE_IDENTITY_CONFLICT",
            "explicit registered source and raw SHA256 required",
        )
        for stamp in (self.event_time, self.acquired_at, self.observed_at):
            _aware(stamp)
        _require(
            self.event_time <= self.acquired_at <= self.observed_at,
            "SNAPSHOT_TIME_INVALID",
            "retain actual event/acquisition/observation order",
        )
        if self.historical_available_at is not None:
            _aware(self.historical_available_at)
            _require(
                self.event_time <= self.historical_available_at <= self.observed_at,
                "SNAPSHOT_TIME_INVALID",
                "known historical availability must be defensible, never fabricated",
            )


@dataclass(frozen=True, slots=True)
class CalendarDay:
    day: date
    is_open: bool
    provenance: SnapshotProvenance


@dataclass(frozen=True, slots=True)
class Split:
    partition: str
    read_from: date
    read_to: date
    decision_from: date
    decision_to: date


@dataclass(frozen=True, slots=True)
class RetrospectivePlan:
    dataset_revision: str
    source_hashes: tuple[tuple[str, str], ...]
    calendar: tuple[CalendarDay, ...]
    splits: tuple[Split, ...]
    universe_scope: str
    snapshot_observed_at: datetime
    cohort: tuple[str, ...]
    fixture_only: bool
    cohort_classifications: tuple[SnapshotClassification, ...] = ()
    design_version: str = "RETRO-V1"
    data_mode: str = "CURRENT_SNAPSHOT_RETROSPECTIVE"


@dataclass(frozen=True, slots=True, order=True)
class RetrospectiveSampleKey:
    instrument_id: str
    decision_session: date
    session_anchor: datetime
    dataset_revision: str


@dataclass(frozen=True, slots=True)
class DailyBar:
    session: date
    close: Decimal | None
    provenance: SnapshotProvenance
    volume: Decimal | None = None
    quantity_unit: str | None = None
    listed: bool | None = None
    suspended: bool | None = None
    comparable: bool | None = None
    up_limit: Decimal | None = None
    down_limit: Decimal | None = None

    def __post_init__(self) -> None:
        _decimal(self.close, "close", positive=True)
        _decimal(self.volume, "volume")
        _decimal(self.up_limit, "up_limit", positive=True)
        _decimal(self.down_limit, "down_limit", positive=True)
        for value in (self.listed, self.suspended, self.comparable):
            _require(
                value is None or type(value) is bool,
                "INVALID_STATE",
                "state must be bool/null",
            )
        if self.up_limit is not None and self.down_limit is not None:
            _require(
                self.up_limit > self.down_limit, "LIMIT_CONFLICT", "inverted limits"
            )


@dataclass(frozen=True, slots=True)
class SnapshotClassification:
    instrument_id: str
    venue: str
    industry_code: str
    ordinary_a_share: bool | None
    selected: bool | None
    provenance: SnapshotProvenance

    def __post_init__(self) -> None:
        for value in (self.ordinary_a_share, self.selected):
            _require(
                value is None or type(value) is bool,
                "CLASSIFICATION_INVALID",
                "classification must be bool/null, not a PIT assertion",
            )


@dataclass(frozen=True, slots=True)
class FeatureView:
    key: RetrospectiveSampleKey
    partition: str
    classification: SnapshotClassification | None
    stock: tuple[DailyBar, ...]
    industry: tuple[DailyBar, ...]


@dataclass(frozen=True, slots=True)
class OutcomeView:
    key: RetrospectiveSampleKey
    partition: str
    stock: tuple[DailyBar, ...]


@dataclass(frozen=True, slots=True)
class PriceFact:
    instrument_id: str
    session: date
    digest: str


@dataclass(frozen=True, slots=True)
class FeatureRow:
    key: RetrospectiveSampleKey
    partition: str
    r5: Decimal | None = None
    r20: Decimal | None = None
    a20: Decimal | None = None
    ma20: Decimal | None = None
    ma60: Decimal | None = None
    trend: bool | None = None
    industry_up: bool | None = None
    rv: Decimal | None = None
    nv: int | None = None
    price_valid: bool = False
    reasons: tuple[str, ...] = ()
    stock_history_identity: str | None = None
    price_facts: tuple[PriceFact, ...] = ()

    @property
    def predictable(self) -> bool:
        return not self.reasons and self.r5 is not None and self.r5 > ZERO


FeatureRows = tuple[FeatureRow, ...]


@dataclass(frozen=True, slots=True)
class LabelRow:
    key: RetrospectiveSampleKey
    partition: str
    y: int | None
    gain_5d: bool | None
    trend_at_5d: bool | None
    label_end: date | None
    label_computed_at: datetime
    end_change: Decimal | None = None
    adverse_change: Decimal | None = None
    min_close_over_ma20: Decimal | None = None
    reasons: tuple[str, ...] = ()
    target_defined: bool = True
    stock_history_identity: str | None = None
    price_facts: tuple[PriceFact, ...] = ()


LabelRows = tuple[LabelRow, ...]


@dataclass(frozen=True, slots=True)
class TrainPanel:
    features: FeatureRows
    labels: LabelRows


@dataclass(frozen=True, slots=True)
class Thresholds:
    r5: Decimal
    r20: Decimal
    a20: Decimal


@dataclass(frozen=True, slots=True)
class CellCard:
    price_cell: PriceCell
    nv: int | None
    positives: int
    count: int
    weeks: tuple[date, ...]
    estimate: Decimal
    probability: Decimal
    fallback: str | None


@dataclass(frozen=True, slots=True)
class ShuffleStats:
    partition: str
    groups: int
    singleton_groups: int
    same_value_groups: int
    rows: int
    unshufflable_rows: int
    changed_rows: int


@dataclass(frozen=True, slots=True)
class FrozenModelCards:
    plan_identity: str
    train_identity: str
    training_features_identity: str
    training_count: int
    training_weeks: tuple[date, ...]
    training_window_end: date
    fitted_at: datetime
    thresholds: Thresholds
    climatology_estimate: Decimal
    climatology_probability: Decimal
    price_cells: tuple[CellCard, ...]
    volume_cells: tuple[CellCard, ...]
    shuffled_cells: tuple[CellCard, ...]
    training_shuffle: ShuffleStats


@dataclass(frozen=True, slots=True)
class PredictionRow:
    key: RetrospectiveSampleKey
    partition: str
    price_cell: PriceCell
    nv: int
    shuffled_nv: int
    trend: bool
    industry_up: bool
    rv: Decimal
    probabilities: tuple[Decimal, Decimal, Decimal, Decimal]
    price_fallback: str | None
    pv_fallback: str | None
    shuffled_fallback: str | None
    stock_history_identity: str | None = None


@dataclass(frozen=True, slots=True)
class PredictionRows:
    plan_identity: str
    model_identity: str
    training_count: int
    training_weeks: tuple[date, ...]
    predicted_at: datetime
    rows: tuple[PredictionRow, ...]
    shuffle: tuple[ShuffleStats, ...]
    feature_scope: tuple[tuple[str, RetrospectiveSampleKey], ...] = ()
    feature_facts: tuple[PriceFact, ...] = ()


# Source/partition-neutral numerical result DTOs match their shared primitives.
WeekSlot = _reference.WeekSlot


@dataclass(frozen=True, slots=True)
class EvaluationRow:
    prediction: PredictionRow
    label: LabelRow | None
    evaluated: bool


WeekResult = _reference.WeekResult
HalfResult = _reference.HalfResult
BootstrapResult = _reference.BootstrapResult
PartitionDiagnostics = _reference.PartitionDiagnostics


@dataclass(frozen=True, slots=True)
class DiagnosticReport:
    plan_identity: str
    model_identity: str
    predictions_identity: str
    calendar_grid_identity: str
    partitions: tuple[PartitionDiagnostics, ...]
    bootstrap_4: BootstrapResult
    bootstrap_13: BootstrapResult
    verdict: str
    verdict_reasons: tuple[str, ...]
    censor_sensitive: bool | None
    evaluation_rows: tuple[EvaluationRow, ...]
    evaluated_at: datetime
    data_mode: str = "CURRENT_SNAPSHOT_RETROSPECTIVE"
    untouched_claim: bool = False
    causal_pit_claim: bool = False
    interpretation: str = (
        "Current-snapshot retrospective association only, conditional on the declared post-hoc cohort, observable E and coarse price baseline; "
        "not causal/PIT, untouched OOS, a ValidationReport, profitability or trading permission."
    )


@dataclass(slots=True)
class _Index:
    days: dict[date, CalendarDay]
    splits: dict[str, Split]
    sessions: dict[str, tuple[date, ...]]
    sources: dict[str, str]


week_key: Any = _reference.week_key


_dates: Any = _reference._dates


def _provenance(
    plan: RetrospectivePlan, sources: dict[str, str], p: SnapshotProvenance
) -> None:
    _require(
        type(p) is SnapshotProvenance,
        "SNAPSHOT_PROVENANCE_REQUIRED",
        "strict A provenance cannot substitute for snapshot facts",
    )
    _require(
        p.revision == plan.dataset_revision,
        "REVISION_CONFLICT",
        "mixed snapshot revisions",
    )
    _require(
        p.source in sources and sources[p.source] == p.raw_sha256,
        "SOURCE_IDENTITY_CONFLICT",
        "source/hash is not bound",
    )
    _require(
        p.observed_at <= plan.snapshot_observed_at,
        "SNAPSHOT_TIME_INVALID",
        "observation after frozen snapshot",
    )


def _retro_index(plan: RetrospectivePlan) -> _Index:
    _require(
        bool(plan.dataset_revision.strip()), "INVALID_PLAN", "revision is required"
    )
    _require(
        bool(plan.universe_scope.strip()), "INVALID_PLAN", "universe must be declared"
    )
    _require(
        type(plan.fixture_only) is bool, "INVALID_PLAN", "fixture flag is required"
    )
    _require(plan.design_version == "RETRO-V1", "INVALID_PLAN", "wrong design version")
    _aware(plan.snapshot_observed_at)
    _require(
        plan.data_mode == "CURRENT_SNAPSHOT_RETROSPECTIVE",
        "INVALID_PLAN",
        "explicit retrospective data mode required",
    )
    _require(
        type(plan.cohort) is tuple
        and bool(plan.cohort)
        and plan.cohort == tuple(sorted(set(plan.cohort))),
        "COHORT_CONFLICT",
        "declare one sorted fixed post-hoc cohort",
    )
    _require(
        all(re.fullmatch(r"[0-9]{6}\.(?:XSHG|XSHE)", item) for item in plan.cohort),
        "COHORT_CONFLICT",
        "ordinary SH/SZ identifiers required",
    )
    sources = dict(plan.source_hashes)
    _require(
        len(sources) == len(plan.source_hashes) and bool(sources),
        "SOURCE_IDENTITY_CONFLICT",
        "duplicate/empty sources",
    )
    for source, digest in plan.source_hashes:
        _require(
            bool(source)
            and len(digest) == 64
            and all(c in "0123456789abcdef" for c in digest),
            "SOURCE_IDENTITY_CONFLICT",
            "expected raw sha256",
        )
    _require(
        tuple(item.instrument_id for item in plan.cohort_classifications)
        == plan.cohort,
        "COHORT_CONFLICT",
        "bind one frozen post-hoc classification per declared instrument",
    )
    for classification in plan.cohort_classifications:
        _provenance(plan, sources, classification.provenance)
        _require(
            classification.venue == classification.instrument_id.rsplit(".", 1)[1],
            "COHORT_CONFLICT",
            "frozen classification venue disagrees with instrument",
        )
    _require(
        tuple(s.partition for s in plan.splits) == RETRO_PARTITIONS,
        "SPLIT_CONFLICT",
        "declare TRAIN/DEVELOPMENT/RETROSPECTIVE_EVAL in order",
    )
    for i, split in enumerate(plan.splits):
        _require(
            split.read_from < split.decision_from < split.decision_to <= split.read_to,
            "SPLIT_CONFLICT",
            "invalid half-open intervals",
        )
        _require(
            split.decision_from.weekday() == split.decision_to.weekday() == 0,
            "SPLIT_CONFLICT",
            "decision grid bounds must be Mondays",
        )
        if i:
            _require(
                plan.splits[i - 1].read_to <= split.read_from,
                "SPLIT_OVERLAP",
                "complete read intervals must be disjoint",
            )
    days = {d.day: d for d in plan.calendar}
    _require(
        len(days) == len(plan.calendar), "CALENDAR_CONFLICT", "duplicate calendar date"
    )
    for day in plan.calendar:
        _require(
            type(day.day) is date and type(day.is_open) is bool,
            "CALENDAR_CONFLICT",
            "calendar needs known open/closed state",
        )
        _provenance(plan, sources, day.provenance)
    sessions: dict[str, tuple[date, ...]] = {}
    for split in plan.splits:
        required = _dates(split.read_from, split.read_to)
        _require(
            all(day in days for day in required),
            "CALENDAR_GAP",
            "calendar must include closed dates too",
        )
        sessions[split.partition] = tuple(day for day in required if days[day].is_open)
    return _Index(days, {s.partition: s for s in plan.splits}, sessions, sources)


def _retro_sample(
    plan: RetrospectivePlan, index: _Index, key: RetrospectiveSampleKey, partition: str
) -> tuple[Split, tuple[date, ...], int]:
    _require(partition in index.splits, "SPLIT_CONFLICT", "unknown partition")
    split = index.splits[partition]
    _timestamp(key.session_anchor)
    _require(
        key.dataset_revision == plan.dataset_revision,
        "REVISION_CONFLICT",
        "wrong sample revision",
    )
    _require(
        key.instrument_id in plan.cohort,
        "COHORT_CONFLICT",
        "sample outside fixed post-hoc cohort",
    )
    _require(
        key.session_anchor
        == datetime.combine(key.decision_session, time(23, 59, 59), SHANGHAI),
        "INVALID_SESSION_ANCHOR",
        "fixed historical position anchor, not information availability",
    )
    _require(
        split.decision_from <= key.decision_session < split.decision_to,
        "SPLIT_CONFLICT",
        "sample outside decision interval",
    )
    sessions = index.sessions[partition]
    _require(
        key.decision_session in sessions, "CALENDAR_CONFLICT", "decision is not open"
    )
    opened = [
        d
        for d in _dates(
            week_key(key.decision_session),
            week_key(key.decision_session) + timedelta(days=7),
        )
        if index.days[d].is_open
    ]
    _require(
        bool(opened) and key.decision_session == opened[-1],
        "INVALID_DECISION_SESSION",
        "use last scheduled open session",
    )
    return split, sessions, sessions.index(key.decision_session)


_unique: Any = _reference._unique


def _retro_bars(
    plan: RetrospectivePlan,
    index: _Index,
    split: Split,
    bars: tuple[DailyBar, ...],
    cutoff: date,
) -> dict[date, DailyBar]:
    result: dict[date, DailyBar] = {}
    for bar in bars:
        _require(
            bar.session not in result,
            "DUPLICATE_STOCK_DAY",
            "duplicate day or simultaneous revisions",
        )
        _require(
            split.read_from <= bar.session < split.read_to,
            "READ_WINDOW_VIOLATION",
            "bar outside declared complete read interval",
        )
        _require(
            bar.session <= cutoff,
            "FUTURE_IN_FEATURE_VIEW",
            "view contains prices after its cutoff",
        )
        _require(
            bar.session in index.days and index.days[bar.session].is_open,
            "CALENDAR_CONFLICT",
            "quote on a closed/unknown day",
        )
        _provenance(plan, index.sources, bar.provenance)
        _require(
            bar.provenance.event_time.astimezone(SHANGHAI).date() == bar.session,
            "EVENT_DATE_CONFLICT",
            "quote event must match its session",
        )
        result[bar.session] = bar
    return result


def _retro_prices(
    bars: dict[date, DailyBar], needed: tuple[date, ...], *, stock: bool
) -> tuple[tuple[Decimal, ...], tuple[str, ...]]:
    reasons: set[str] = set()
    values: list[Decimal] = []
    for day in needed:
        bar = bars.get(day)
        if bar is None:
            reasons.add("PRICE_MISSING")
            continue
        if bar.close is None:
            reasons.add("PRICE_MISSING")
        else:
            values.append(bar.close)
        if bar.comparable is not True:
            reasons.add("PRICE_SCALE_UNRESOLVED")
        if stock:
            if bar.listed is None or bar.suspended is None:
                reasons.add("LISTING_OR_SUSPENSION_UNKNOWN")
            elif not bar.listed:
                reasons.add("NOT_LISTED")
            elif bar.suspended:
                reasons.add("SUSPENDED")
    return tuple(values), tuple(sorted(reasons))


_mean = _reference._mean


_nullable_mean: Any = _reference._nullable_mean


_structure: Any = _reference._structure


def _complete_cohort(
    plan: RetrospectivePlan, index: _Index, rows: tuple[Any, ...]
) -> None:
    """Missing records must be UNKNOWN rows, never silently removed stocks/weeks."""
    expected = set()
    for partition in {row.partition for row in rows}:
        split = index.splits[partition]
        last = {}
        for day in index.sessions[partition]:
            if split.decision_from <= day < split.decision_to:
                last[week_key(day)] = day
        expected.update(
            RetrospectiveSampleKey(
                instrument,
                day,
                datetime.combine(day, time(23, 59, 59), SHANGHAI),
                plan.dataset_revision,
            )
            for day in last.values()
            for instrument in plan.cohort
        )
    _require(
        {row.key for row in rows} == expected,
        "INCOMPLETE_COHORT_GRID",
        "retain every declared stock/open decision week",
    )


def _consistent_views(
    plan: RetrospectivePlan, index: _Index, views: tuple[Any, ...]
) -> None:
    facts: dict[tuple[str, date], DailyBar | None] = {}
    classifications: dict[str, SnapshotClassification | None] = {}
    for view in views:
        split, sessions, t = _retro_sample(plan, index, view.key, view.partition)
        end = (
            t if isinstance(view, FeatureView) else min(t + HORIZON, len(sessions) - 1)
        )
        stock = _retro_bars(plan, index, split, view.stock, sessions[end])
        series = [(view.key.instrument_id, stock)]
        if isinstance(view, FeatureView):
            instrument = view.key.instrument_id
            frozen_classification = next(
                item
                for item in plan.cohort_classifications
                if item.instrument_id == instrument
            )
            if view.classification is not None:
                _provenance(plan, index.sources, view.classification.provenance)
                _require(
                    view.classification.instrument_id == instrument
                    and view.classification.venue == instrument.rsplit(".", 1)[1],
                    "COHORT_CONFLICT",
                    "classification must match the declared instrument and venue",
                )
            _require(
                view.classification == frozen_classification,
                "SNAPSHOT_FACT_CONFLICT",
                "classification cannot drift across partitions/calls",
            )
            _require(
                instrument not in classifications
                or classifications[instrument] == view.classification,
                "SNAPSHOT_FACT_CONFLICT",
                "one fixed post-hoc classification per instrument",
            )
            classifications[instrument] = view.classification
            series.append(
                (
                    "industry:801150",
                    _retro_bars(plan, index, split, view.industry, sessions[t]),
                )
            )
        for identity_key, bars in series:
            for day in sessions[max(0, t - WARMUP + 1) : end + 1]:
                key = (identity_key, day)
                fact = bars.get(day)
                _require(
                    key not in facts or facts[key] == fact,
                    "SNAPSHOT_FACT_CONFLICT",
                    "one value/missingness per snapshot fact",
                )
                facts[key] = fact


def _bind_histories(
    plan: RetrospectivePlan, index: _Index, views: tuple[Any, ...], rows: list[Any]
) -> tuple[Any, ...]:
    by_key = {view.key: view for view in views}
    result = []
    for row in rows:
        _, sessions, t = _retro_sample(plan, index, row.key, row.partition)
        bars = {bar.session: bar for bar in by_key[row.key].stock}
        end = (
            t
            if isinstance(by_key[row.key], FeatureView)
            else min(t + HORIZON, len(sessions) - 1)
        )
        facts = []
        for day in sessions[max(0, t - WARMUP + 1) : end + 1]:
            bar = bars.get(day)
            # Bind only shared price/state/provenance, not fields unused by price-only labels.
            projection = (
                None
                if bar is None
                else (
                    bar.close,
                    bar.listed,
                    bar.suspended,
                    bar.comparable,
                    bar.provenance,
                )
            )
            facts.append(
                PriceFact(row.key.instrument_id, day, identity((day, projection)))
            )
        history = tuple(
            fact for fact in facts if fact.session <= row.key.decision_session
        )
        result.append(
            replace(
                row, stock_history_identity=identity(history), price_facts=tuple(facts)
            )
        )
    return tuple(result)


def _all_facts(groups: tuple[tuple[PriceFact, ...], ...]) -> tuple[PriceFact, ...]:
    facts: dict[tuple[str, date], PriceFact] = {}
    for group in groups:
        for fact in group:
            _history_valid(fact.digest)
            key = (fact.instrument_id, fact.session)
            _require(
                key not in facts or facts[key] == fact,
                "SNAPSHOT_FACT_CONFLICT",
                "conflicting frozen price facts",
            )
            facts[key] = fact
    return tuple(facts[key] for key in sorted(facts))


def _same_facts(left: tuple[PriceFact, ...], right: tuple[PriceFact, ...]) -> None:
    # An outcome may overlap a later excluded mother-sample feature window.
    _all_facts((left, right))


def _row_facts(index: _Index, row: Any, *, outcome: bool) -> None:
    sessions = index.sessions[row.partition]
    t = sessions.index(row.key.decision_session)
    end = min(t + HORIZON, len(sessions) - 1) if outcome else t
    expected = sessions[max(0, t - WARMUP + 1) : end + 1]
    _require(
        tuple(fact.session for fact in row.price_facts) == expected
        and all(
            fact.instrument_id == row.key.instrument_id for fact in row.price_facts
        ),
        "SNAPSHOT_FACT_CONFLICT",
        "complete position lineage required, including missing facts",
    )
    _all_facts((row.price_facts,))
    history = tuple(
        fact for fact in row.price_facts if fact.session <= row.key.decision_session
    )
    _require(
        identity(history) == row.stock_history_identity,
        "SNAPSHOT_FACT_CONFLICT",
        "history digest disagrees with per-day facts",
    )


def _history_valid(value: str | None) -> None:
    _require(
        type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
        "SNAPSHOT_FACT_CONFLICT",
        "bind immutable 65-session stock history, including missingness",
    )


def make_retrospective_features(
    plan: RetrospectivePlan, asof_price_and_volume_rows: tuple[FeatureView, ...]
) -> FeatureRows:
    """Reconstruct event-position features, not a historical available-information set."""
    with localcontext(CONTEXT):
        index = _retro_index(plan)
        _unique(asof_price_and_volume_rows)
        _consistent_views(plan, index, asof_price_and_volume_rows)
        _complete_cohort(plan, index, asof_price_and_volume_rows)
        result: list[FeatureRow] = []
        for view in sorted(asof_price_and_volume_rows, key=lambda v: v.key):
            split, sessions, t = _retro_sample(plan, index, view.key, view.partition)
            stock = _retro_bars(
                plan, index, split, view.stock, view.key.decision_session
            )
            industry = _retro_bars(
                plan, index, split, view.industry, view.key.decision_session
            )
            reasons: set[str] = set()
            member = view.classification
            if member is None:
                reasons.add("CLASSIFICATION_UNKNOWN")
            else:
                _provenance(plan, index.sources, member.provenance)
                _require(
                    member.instrument_id == view.key.instrument_id
                    and member.venue == view.key.instrument_id.rsplit(".", 1)[1],
                    "COHORT_CONFLICT",
                    "classification belongs to another instrument",
                )
                if member.selected is None or member.ordinary_a_share is None:
                    reasons.add("CLASSIFICATION_UNKNOWN")
                elif not (
                    member.selected
                    and member.ordinary_a_share
                    and member.venue in ("XSHG", "XSHE")
                    and member.industry_code == "801150"
                ):
                    reasons.add("OUTSIDE_DECLARED_COHORT")
            if t + 1 < WARMUP:
                result.append(
                    FeatureRow(
                        view.key,
                        view.partition,
                        reasons=tuple(sorted(reasons | {"INSUFFICIENT_HISTORY"})),
                    )
                )
                continue
            needed = sessions[t - WARMUP + 1 : t + 1]
            prices, price_reasons = _retro_prices(stock, needed, stock=True)
            industry_prices, industry_reasons = _retro_prices(
                industry, needed, stock=False
            )
            reasons.update(price_reasons)
            reasons.update(industry_reasons)
            if price_reasons or industry_reasons:
                result.append(
                    FeatureRow(view.key, view.partition, reasons=tuple(sorted(reasons)))
                )
                continue
            r5, r20, a20, ma20, ma60, trend = _structure(prices)
            industry_up = (
                industry_prices[-1] > _mean(industry_prices[-20:])
                and industry_prices[-1] / industry_prices[-21] - ONE > ZERO
            )
            for day in needed[-5:]:
                bar = stock[day]
                if bar.up_limit is None or bar.down_limit is None:
                    reasons.add("LIMIT_STATUS_UNKNOWN")
                elif bar.close in (bar.up_limit, bar.down_limit):
                    reasons.add("CLOSE_LIMIT_TOUCH")
            volumes: list[Decimal] = []
            units: set[str] = set()
            for day in needed[-25:]:
                bar = stock[day]
                if bar.volume is None:
                    reasons.add("VOLUME_MISSING")
                else:
                    volumes.append(bar.volume)
                if not bar.quantity_unit:
                    reasons.add("VOLUME_UNIT_MISMATCH")
                else:
                    units.add(bar.quantity_unit)
            if len(units) != 1:
                reasons.add("VOLUME_UNIT_MISMATCH")
            rv: Decimal | None = None
            nv: int | None = None
            if (
                len(volumes) == 25
                and len(units) == 1
                and "VOLUME_UNIT_MISMATCH" not in reasons
            ):
                baseline = _mean(volumes[:20])
                if baseline == ZERO:
                    reasons.add("ZERO_VOLUME_BASELINE")
                else:
                    rv = _mean(volumes[-5:]) / baseline
                    nv = int(rv <= ONE)
            if r5 <= ZERO:
                reasons.add("NO_UP_CANDIDATE")
            result.append(
                FeatureRow(
                    view.key,
                    view.partition,
                    r5,
                    r20,
                    a20,
                    ma20,
                    ma60,
                    trend,
                    industry_up,
                    rv,
                    nv,
                    True,
                    tuple(sorted(reasons)),
                )
            )
        return _bind_histories(plan, index, asof_price_and_volume_rows, result)


def make_retrospective_labels(
    plan: RetrospectivePlan,
    outcome_price_rows: tuple[OutcomeView, ...],
    *,
    computed_at: datetime,
) -> LabelRows:
    """Reconstruct labels at actual injected computation time, not historical availability."""
    _aware(computed_at)
    _require(
        computed_at >= plan.snapshot_observed_at,
        "COMPUTATION_TIME_INVALID",
        "labels cannot precede frozen observation",
    )
    with localcontext(CONTEXT):
        index = _retro_index(plan)
        _unique(outcome_price_rows)
        _consistent_views(plan, index, outcome_price_rows)
        result = []
        for view in sorted(outcome_price_rows, key=lambda v: v.key):
            split, sessions, t = _retro_sample(plan, index, view.key, view.partition)
            if t + HORIZON >= len(sessions):
                result.append(
                    LabelRow(
                        view.key,
                        view.partition,
                        None,
                        None,
                        None,
                        None,
                        computed_at,
                        reasons=("LABEL_WINDOW_OUTSIDE_SPLIT",),
                    )
                )
                continue
            end = sessions[t + HORIZON]
            bars = _retro_bars(plan, index, split, view.stock, end)
            if t + 1 < WARMUP:
                result.append(
                    LabelRow(
                        view.key,
                        view.partition,
                        None,
                        None,
                        None,
                        end,
                        computed_at,
                        reasons=("INSUFFICIENT_HISTORY",),
                    )
                )
                continue
            needed = sessions[t - WARMUP + 1 : t + HORIZON + 1]
            prices, reasons = _retro_prices(bars, needed, stock=True)
            if reasons:
                result.append(
                    LabelRow(
                        view.key,
                        view.partition,
                        None,
                        None,
                        None,
                        end,
                        computed_at,
                        reasons=tuple(sorted(set(reasons) | {"LABEL_UNOBSERVABLE"})),
                        target_defined="PRICE_SCALE_UNRESOLVED" not in reasons,
                    )
                )
                continue
            current = prices[-HORIZON - 1]
            future = prices[-HORIZON:]
            gain = future[-1] > current
            trend = _structure(prices)[-1]
            ma20 = _mean(prices[-HORIZON - 20 : -HORIZON])
            result.append(
                LabelRow(
                    view.key,
                    view.partition,
                    int(gain and trend),
                    gain,
                    trend,
                    end,
                    computed_at,
                    future[-1] / current - ONE,
                    min(ZERO, min(value / current - ONE for value in future)),
                    min(future) / ma20 - ONE,
                )
            )
        return _bind_histories(plan, index, outcome_price_rows, result)


def _feature_valid(row: FeatureRow) -> None:
    _reference._feature_valid(row)  # type: ignore[arg-type] -- this scalar-only helper never reads key/source/partition
    _history_valid(row.stock_history_identity)


def _retro_label_valid(plan: RetrospectivePlan, index: _Index, row: LabelRow) -> None:
    _, sessions, t = _retro_sample(plan, index, row.key, row.partition)
    _history_valid(row.stock_history_identity)
    _row_facts(index, row, outcome=True)
    _aware(row.label_computed_at)
    if row.label_computed_at is not None:
        _aware(row.label_computed_at)
        _require(
            row.label_computed_at >= plan.snapshot_observed_at,
            "COMPUTATION_TIME_INVALID",
            "retain actual label computation time",
        )
    if row.y is None:
        _require(bool(row.reasons), "MALFORMED_LABEL", "unknown label needs a reason")
        return
    _require(
        type(row.y) is int and row.y in (0, 1) and not row.reasons,
        "MALFORMED_LABEL",
        "known label is 0/1",
    )
    _require(
        type(row.gain_5d) is bool
        and type(row.trend_at_5d) is bool
        and row.y == int(row.gain_5d and row.trend_at_5d),
        "MALFORMED_LABEL",
        "composite label mismatch",
    )
    _require(
        t + HORIZON < len(sessions) and row.label_end == sessions[t + HORIZON],
        "LABEL_WINDOW_OUTSIDE_SPLIT",
        "five-session tail required",
    )
    _require(
        row.label_computed_at is not None and row.target_defined,
        "MALFORMED_LABEL",
        "known label needs actual computation time and a defined target",
    )
    for value in (row.end_change, row.adverse_change, row.min_close_over_ma20):
        _require(
            type(value) is Decimal and value.is_finite(),
            "MALFORMED_LABEL",
            "finite descriptions required",
        )


_cell: Any = _reference._cell


def _retro_shuffle(
    rows: FeatureRows, thresholds: Thresholds
) -> tuple[dict[RetrospectiveSampleKey, int], tuple[ShuffleStats, ...]]:
    groups: dict[tuple[str, date, PriceCell], list[FeatureRow]] = defaultdict(list)
    for row in sorted(rows, key=lambda r: r.key):
        _feature_valid(row)
        _require(row.predictable, "MALFORMED_FEATURE", "shuffle accepts only F")
        groups[
            (row.partition, week_key(row.key.decision_session), _cell(row, thresholds))
        ].append(row)
    assignments: dict[RetrospectiveSampleKey, int] = {}
    stats: list[ShuffleStats] = []
    for partition in RETRO_PARTITIONS:
        rng = random.Random(2)
        n_groups = singleton = same = n_rows = unshufflable = changed = 0
        for group in sorted(k for k in groups if k[0] == partition):
            members = groups[group]
            original = [int(r.nv) for r in members if r.nv is not None]
            shuffled = original.copy()
            rng.shuffle(shuffled)
            n_groups += 1
            n_rows += len(members)
            if len(members) == 1:
                singleton += 1
                unshufflable += 1
            elif len(set(original)) == 1:
                same += 1
                unshufflable += len(members)
            for row, before, after in zip(members, original, shuffled, strict=True):
                assignments[row.key] = after
                changed += int(before != after)
        if n_groups:
            stats.append(
                ShuffleStats(
                    partition, n_groups, singleton, same, n_rows, unshufflable, changed
                )
            )
    return assignments, tuple(stats)


_support: Any = _reference._support


_p: Any = _reference._p


def fit_retrospective_models(
    plan: RetrospectivePlan, train_panel: TrainPanel, *, fitted_at: datetime
) -> FrozenModelCards:
    """One TRAIN-only fit; current-snapshot evidence, never a historical run."""
    _aware(fitted_at)
    _require(
        fitted_at >= plan.snapshot_observed_at,
        "COMPUTATION_TIME_INVALID",
        "fit before snapshot",
    )
    _require(
        all(
            row.label_computed_at is None or row.label_computed_at <= fitted_at
            for row in train_panel.labels
        ),
        "COMPUTATION_TIME_INVALID",
        "fit before label computation",
    )
    with localcontext(CONTEXT):
        index = _retro_index(plan)
        _unique(train_panel.features)
        _unique(train_panel.labels)
        labels = {r.key: r for r in train_panel.labels}
        _require(
            set(labels) == {r.key for r in train_panel.features},
            "TRAIN_MASK_CONFLICT",
            "TRAIN views must pair by key before forming common mask",
        )
        for row in train_panel.features:
            _require(
                row.partition == "TRAIN", "NON_TRAIN_FIT", "fit accepts TRAIN only"
            )
            _retro_sample(plan, index, row.key, row.partition)
            _feature_valid(row)
            _row_facts(index, row, outcome=False)
            _require(
                row.stock_history_identity == labels[row.key].stock_history_identity,
                "SNAPSHOT_FACT_CONFLICT",
                "TRAIN features and labels must use identical stock history",
            )
        _complete_cohort(plan, index, train_panel.features)
        for row in train_panel.labels:
            _require(
                row.partition == "TRAIN", "NON_TRAIN_FIT", "fit accepts TRAIN only"
            )
            _retro_label_valid(plan, index, row)
        _same_facts(
            _all_facts(tuple(row.price_facts for row in train_panel.features)),
            _all_facts(tuple(row.price_facts for row in train_panel.labels)),
        )
        rows = tuple(
            sorted(
                (
                    r
                    for r in train_panel.features
                    if r.predictable and labels[r.key].y is not None
                ),
                key=lambda r: r.key,
            )
        )
        _require(bool(rows), "EMPTY_TRAIN", "cannot fit an empty common TRAIN panel")
        medians = []
        for name in ("r5", "r20", "a20"):
            values = sorted(getattr(r, name) for r in rows)
            medians.append(values[(len(values) - 1) // 2])
        thresholds = Thresholds(*medians)
        n = len(rows)
        positives = sum(int(labels[r.key].y or 0) for r in rows)
        g = Decimal(positives + 1) / Decimal(n + 2)
        price_groups: dict[PriceCell, list[FeatureRow]] = defaultdict(list)
        for row in rows:
            price_groups[_cell(row, thresholds)].append(row)
        price_cards = []
        price_estimates: dict[PriceCell, Decimal] = {}
        for cell, group in sorted(price_groups.items()):
            weeks = tuple(sorted({week_key(r.key.decision_session) for r in group}))
            fallback = _support(len(group), weeks)
            s = sum(int(labels[r.key].y or 0) for r in group)
            estimate = (
                g
                if fallback
                else (Decimal(s) + Decimal(20) * g) / Decimal(len(group) + 20)
            )
            price_estimates[cell] = estimate
            price_cards.append(
                CellCard(
                    cell, None, s, len(group), weeks, estimate, _p(estimate), fallback
                )
            )
        shuffled, shuffle_stats = _retro_shuffle(rows, thresholds)
        volume_cards: list[tuple[CellCard, ...]] = []
        for use_shuffle in (False, True):
            groups: dict[tuple[PriceCell, int], list[FeatureRow]] = defaultdict(list)
            for row in rows:
                assert row.nv is not None
                groups[
                    (
                        _cell(row, thresholds),
                        shuffled[row.key] if use_shuffle else row.nv,
                    )
                ].append(row)
            cards = []
            for (cell, nv), group in sorted(groups.items()):
                weeks = tuple(sorted({week_key(r.key.decision_session) for r in group}))
                fallback = _support(len(group), weeks)
                s = sum(int(labels[r.key].y or 0) for r in group)
                parent = price_estimates[cell]
                estimate = (
                    parent
                    if fallback
                    else (Decimal(s) + Decimal(20) * parent) / Decimal(len(group) + 20)
                )
                cards.append(
                    CellCard(
                        cell, nv, s, len(group), weeks, estimate, _p(estimate), fallback
                    )
                )
            volume_cards.append(tuple(cards))
        return FrozenModelCards(
            identity(plan),
            identity(TrainPanel(rows, tuple(labels[r.key] for r in rows))),
            identity(tuple(sorted(train_panel.features, key=lambda row: row.key))),
            n,
            tuple(sorted({week_key(r.key.decision_session) for r in rows})),
            index.splits["TRAIN"].read_to,
            fitted_at,
            thresholds,
            g,
            _p(g),
            tuple(price_cards),
            volume_cards[0],
            volume_cards[1],
            shuffle_stats[0],
        )


def predict_retrospective_models(
    plan: RetrospectivePlan,
    model_cards: FrozenModelCards,
    feature_rows: FeatureRows,
    *,
    predicted_at: datetime,
) -> PredictionRows:
    """Four probabilities on exactly F; labels are not an argument."""
    _aware(predicted_at)
    _require(
        predicted_at >= model_cards.fitted_at,
        "COMPUTATION_TIME_INVALID",
        "prediction before fit",
    )
    with localcontext(CONTEXT):
        index = _retro_index(plan)
        _require(
            model_cards.plan_identity == identity(plan),
            "MODEL_PLAN_CONFLICT",
            "model cards belong to another frozen plan",
        )
        _require(
            model_cards.training_window_end == index.splits["TRAIN"].read_to,
            "MODEL_PLAN_CONFLICT",
            "wrong training cutoff",
        )
        _unique(feature_rows)
        for row in feature_rows:
            _retro_sample(plan, index, row.key, row.partition)
            _feature_valid(row)
            _row_facts(index, row, outcome=False)
        _complete_cohort(plan, index, feature_rows)
        train_features = tuple(
            sorted(
                (row for row in feature_rows if row.partition == "TRAIN"),
                key=lambda row: row.key,
            )
        )
        if train_features:
            _require(
                identity(train_features) == model_cards.training_features_identity,
                "SNAPSHOT_FACT_CONFLICT",
                "TRAIN prediction features differ from the frozen fit input",
            )
        rows = tuple(
            sorted((r for r in feature_rows if r.predictable), key=lambda r: r.key)
        )
        shuffled, stats = _retro_shuffle(rows, model_cards.thresholds)
        prices = {c.price_cell: c for c in model_cards.price_cells}
        volumes = {(c.price_cell, c.nv): c for c in model_cards.volume_cells}
        controls = {(c.price_cell, c.nv): c for c in model_cards.shuffled_cells}
        predictions = []
        for row in rows:
            cell = _cell(row, model_cards.thresholds)
            assert row.nv is not None and row.rv is not None
            parent = prices.get(cell)
            p0 = parent.probability if parent else model_cards.climatology_probability
            pv = volumes.get((cell, row.nv))
            control = controls.get((cell, shuffled[row.key]))
            predictions.append(
                PredictionRow(
                    row.key,
                    row.partition,
                    cell,
                    row.nv,
                    shuffled[row.key],
                    bool(row.trend),
                    bool(row.industry_up),
                    row.rv,
                    (
                        model_cards.climatology_probability,
                        p0,
                        pv.probability if pv else p0,
                        control.probability if control else p0,
                    ),
                    parent.fallback if parent else "UNSEEN_CELL",
                    pv.fallback if pv else "UNSEEN_CELL",
                    control.fallback if control else "UNSEEN_CELL",
                    row.stock_history_identity,
                )
            )
        return PredictionRows(
            model_cards.plan_identity,
            identity(model_cards),
            model_cards.training_count,
            model_cards.training_weeks,
            predicted_at,
            tuple(predictions),
            stats,
            tuple(
                (row.partition, row.key)
                for row in sorted(feature_rows, key=lambda row: row.key)
            ),
            _all_facts(tuple(row.price_facts for row in feature_rows)),
        )


_bootstrap = _reference._bootstrap


def _grid(plan: RetrospectivePlan, index: _Index, slots: tuple[WeekSlot, ...]) -> None:
    actual = {(s.partition, s.week): s for s in slots}
    _require(
        len(actual) == len(slots), "CALENDAR_GRID_CONFLICT", "duplicate week slots"
    )
    expected: set[tuple[str, date]] = set()
    for split in plan.splits:
        week = split.decision_from
        while week < split.decision_to:
            expected.add((split.partition, week))
            slot = actual.get((split.partition, week))
            _require(
                slot is not None, "CALENDAR_GRID_GAP", "complete contiguous G required"
            )
            assert slot is not None
            opened = [
                d
                for d in _dates(week, week + timedelta(days=7))
                if index.days[d].is_open
            ]
            _require(
                slot.decision_session == (opened[-1] if opened else None)
                and slot.mother_count == (len(plan.cohort) if opened else 0),
                "CALENDAR_GRID_CONFLICT",
                "grid disagrees with market calendar",
            )
            _require(
                all(
                    type(n) is int and n >= 0
                    for n in (
                        slot.mother_count,
                        slot.r5_known_count,
                        slot.up_candidate_count,
                        slot.price_valid_count,
                    )
                ),
                "CALENDAR_GRID_CONFLICT",
                "invalid stage counts",
            )
            _require(
                slot.up_candidate_count <= slot.r5_known_count <= slot.mother_count
                and slot.price_valid_count <= slot.mother_count,
                "CALENDAR_GRID_CONFLICT",
                "contradictory stage counts",
            )
            if not opened:
                _require(
                    slot.mother_count == 0,
                    "CALENDAR_GRID_CONFLICT",
                    "closed week cannot contain samples",
                )
            week += timedelta(days=7)
    _require(
        set(actual) == expected,
        "CALENDAR_GRID_CONFLICT",
        "unexpected week outside declared grid",
    )


_prediction_valid: Any = _reference._prediction_valid


_summarize: Any = _reference._summarize


_valid_interval: Any = _reference._valid_interval


_decide: Any = _reference._decide


def evaluate_retrospective_predictions(
    plan: RetrospectivePlan,
    predictions: PredictionRows,
    labels: LabelRows,
    calendar_week_grid: tuple[WeekSlot, ...],
    *,
    evaluated_at: datetime,
) -> DiagnosticReport:
    """Evaluate persisted probabilities, preserving G, F, E and future censoring."""
    _aware(evaluated_at)
    _require(
        evaluated_at >= predictions.predicted_at,
        "COMPUTATION_TIME_INVALID",
        "evaluation before prediction freeze",
    )
    for row in labels:
        _require(
            row.label_computed_at is None or row.label_computed_at <= evaluated_at,
            "COMPUTATION_TIME_INVALID",
            "evaluation before labels computed",
        )
        if row.partition != "TRAIN":
            _require(
                row.label_computed_at is not None
                and row.label_computed_at > predictions.predicted_at,
                "OUTCOME_BEFORE_PREDICTIONS",
                "non-training labels must be computed after prediction freeze",
            )
    with localcontext(CONTEXT):
        index = _retro_index(plan)
        _require(
            predictions.plan_identity == identity(plan),
            "PREDICTION_PLAN_CONFLICT",
            "wrong frozen prediction plan",
        )
        _require(
            len(predictions.model_identity) == 64,
            "MODEL_IDENTITY_CONFLICT",
            "frozen model identity required",
        )
        _unique(predictions.rows)
        _unique(labels)
        _grid(plan, index, calendar_week_grid)
        label_map = {r.key: r for r in labels}
        for label in labels:
            _retro_label_valid(plan, index, label)
        scope_rows = tuple(
            FeatureRow(key, partition) for partition, key in predictions.feature_scope
        )
        _unique(scope_rows)
        for row in scope_rows:
            _retro_sample(plan, index, row.key, row.partition)
        _complete_cohort(plan, index, scope_rows)
        expected_facts = set()
        for row in scope_rows:
            sessions = index.sessions[row.partition]
            t = sessions.index(row.key.decision_session)
            expected_facts.update(
                (row.key.instrument_id, day)
                for day in sessions[max(0, t - WARMUP + 1) : t + 1]
            )
        frozen_facts = _all_facts((predictions.feature_facts,))
        _require(
            {(fact.instrument_id, fact.session) for fact in frozen_facts}
            == expected_facts,
            "SNAPSHOT_FACT_CONFLICT",
            "freeze lineage for the full mother sample, not just F",
        )
        _same_facts(frozen_facts, _all_facts(tuple(row.price_facts for row in labels)))
        evaluations = []
        for pred in sorted(predictions.rows, key=lambda r: r.key):
            _retro_sample(plan, index, pred.key, pred.partition)
            _prediction_valid(pred)
            _history_valid(pred.stock_history_identity)
            _require(
                (pred.partition, pred.key) in predictions.feature_scope,
                "SNAPSHOT_FACT_CONFLICT",
                "F must originate in frozen mother-sample scope",
            )
            label = label_map.get(pred.key)
            if label is not None:
                _require(
                    pred.stock_history_identity == label.stock_history_identity,
                    "SNAPSHOT_FACT_CONFLICT",
                    "frozen F and outcomes must use identical stock history",
                )
                _require(
                    label.partition == pred.partition,
                    "LABEL_PARTITION_CONFLICT",
                    "join cannot cross partitions",
                )
            evaluations.append(
                EvaluationRow(pred, label, label is not None and label.y is not None)
            )
        joined = tuple(evaluations)
        summaries = tuple(
            _summarize(
                partition,
                tuple(
                    sorted(
                        (s for s in calendar_week_grid if s.partition == partition),
                        key=lambda s: s.week,
                    )
                ),
                tuple(r for r in joined if r.prediction.partition == partition),
            )
            for partition in RETRO_PARTITIONS
        )
        held = summaries[2]
        ci4 = _bootstrap(tuple(w.delta for w in held.weeks), 4, 1)
        ci13 = _bootstrap(tuple(w.delta for w in held.weeks), 13, 3)
        validity = []
        for summary, minimum in zip(summaries, MIN_WEEKS, strict=True):
            if dict(summary.counts).get("W_eff", 0) < minimum:
                validity.append(f"{summary.partition}_WEEKS_LT_{minimum}")
        if len(predictions.training_weeks) < MIN_WEEKS[0]:
            validity.append("FITTED_TRAIN_WEEKS_LT_104")
        for y in (0, 1):
            weeks = {
                week_key(r.prediction.key.decision_session)
                for r in joined
                if r.prediction.partition == "RETROSPECTIVE_EVAL"
                and r.evaluated
                and r.label is not None
                and r.label.y == y
            }
            if len(weeks) < 12:
                validity.append(f"RETROSPECTIVE_EVAL_CLASS_{y}_WEEKS_LT_12")
        if held.coverage_e is None or held.coverage_e == ZERO:
            validity.append("NO_ACTIVE_PV_COVERAGE_E")
        if any(h.effective_weeks == 0 for h in held.halves):
            validity.append("EMPTY_TIME_HALF")
        if any(v is None for v in held.brier):
            validity.append("UNDEFINED_BRIER")
        verdict: str
        verdict, reasons = _decide(
            tuple(validity),
            ci4,
            ci13,
            (held.halves[0].delta, held.halves[1].delta),
            held.brier,
            held.relative_improvement,
        )
        sensitive = (
            held.censor_bounds[0] <= ZERO
            if held.delta is not None
            and held.delta > ZERO
            and held.censor_bounds[0] is not None
            else None
        )
        return DiagnosticReport(
            identity(plan),
            predictions.model_identity,
            identity(predictions),
            identity(calendar_week_grid),
            summaries,
            ci4,
            ci13,
            {
                "incremental_in_declared_E": "retrospective_incremental_association",
                "no_declared_advantage": "no_retrospective_advantage",
            }.get(verdict, verdict),
            reasons,
            sensitive,
            joined,
            evaluated_at,
        )
