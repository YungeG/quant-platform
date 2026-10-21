"""D009 v1.1 pure, exploratory statistics. No Reader, I/O or financial engine.

All dates index the injected market calendar, not the next valid stock quote.
Probabilities are estimated at Decimal precision 28, persisted at 12 places,
and scored at exactly that persisted precision. Missing observations stay missing.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from typing import Any
from zoneinfo import ZoneInfo

MODELS = ("CLIMATOLOGY", "PRICE_ONLY", "PRICE_VOLUME", "SHUFFLED_VOLUME")
PARTITIONS = ("TRAIN", "DEVELOPMENT", "HELD_OUT")
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


class ResearchContractError(ValueError):
    """A local input/output contract error, never a Platform terminal grade."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise ResearchContractError(code, message)


def _timestamp(value: datetime) -> None:
    _require(
        type(value) is datetime
        and getattr(value.tzinfo, "key", None) == "Asia/Shanghai",
        "TIMEZONE_MISMATCH",
        "timestamps must explicitly use Asia/Shanghai",
    )


def _decimal(value: Decimal | None, name: str, *, positive: bool = False) -> None:
    if value is not None:
        _require(
            type(value) is Decimal and value.is_finite(),
            "INVALID_NUMERIC_VALUE",
            f"{name} must be a finite Decimal, not a float",
        )
        _require(
            value > ZERO if positive else value >= ZERO,
            "INVALID_NUMERIC_VALUE",
            f"invalid {name}",
        )


def json_value(value: Any) -> Any:
    """Deterministic local file representation; not a Platform envelope."""
    if is_dataclass(value) and not isinstance(value, type):
        return json_value(asdict(value))
    if isinstance(value, Decimal):
        _require(value.is_finite(), "INVALID_NUMERIC_VALUE", "nonfinite output")
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): json_value(v) for k, v in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [json_value(v) for v in value]
    if value is None or type(value) in (str, int, bool):
        return value
    raise ResearchContractError(
        "UNSUPPORTED_VALUE", f"unsupported {type(value).__name__}"
    )


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        json_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def identity(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class Provenance:
    revision: str
    source: str
    raw_sha256: str
    event_time: datetime
    available_at: datetime
    acquired_at: datetime

    def __post_init__(self) -> None:
        for stamp in (self.event_time, self.available_at, self.acquired_at):
            _timestamp(stamp)
        _require(
            self.available_at >= self.event_time,
            "INVALID_AVAILABILITY",
            "availability cannot precede the event",
        )


@dataclass(frozen=True, slots=True)
class CalendarDay:
    day: date
    is_open: bool
    provenance: Provenance


@dataclass(frozen=True, slots=True)
class Split:
    partition: str
    read_from: date
    read_to: date
    decision_from: date
    decision_to: date


@dataclass(frozen=True, slots=True)
class Plan:
    dataset_revision: str
    source_hashes: tuple[tuple[str, str], ...]
    calendar: tuple[CalendarDay, ...]
    splits: tuple[Split, ...]
    universe_scope: str
    synthetic: bool
    design_version: str = "D009-v1.1"


@dataclass(frozen=True, slots=True, order=True)
class SampleKey:
    instrument_id: str
    decision_session: date
    as_of: datetime
    dataset_revision: str


@dataclass(frozen=True, slots=True)
class DailyBar:
    session: date
    close: Decimal | None
    provenance: Provenance
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
class Membership:
    effective_from: date
    effective_to: date
    venue: str
    industry_code: str
    ordinary_a_share: bool | None
    is_member: bool | None
    provenance: Provenance


@dataclass(frozen=True, slots=True)
class FeatureView:
    key: SampleKey
    partition: str
    membership: Membership | None
    stock: tuple[DailyBar, ...]
    industry: tuple[DailyBar, ...]


@dataclass(frozen=True, slots=True)
class OutcomeView:
    key: SampleKey
    partition: str
    stock: tuple[DailyBar, ...]


@dataclass(frozen=True, slots=True)
class FeatureRow:
    key: SampleKey
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

    @property
    def predictable(self) -> bool:
        return not self.reasons and self.r5 is not None and self.r5 > ZERO


FeatureRows = tuple[FeatureRow, ...]


@dataclass(frozen=True, slots=True)
class LabelRow:
    key: SampleKey
    partition: str
    y: int | None
    gain_5d: bool | None
    trend_at_5d: bool | None
    label_end: date | None
    label_available_at: datetime | None
    end_change: Decimal | None = None
    adverse_change: Decimal | None = None
    min_close_over_ma20: Decimal | None = None
    reasons: tuple[str, ...] = ()
    target_defined: bool = True


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
    training_count: int
    training_weeks: tuple[date, ...]
    training_cutoff: date
    thresholds: Thresholds
    climatology_estimate: Decimal
    climatology_probability: Decimal
    price_cells: tuple[CellCard, ...]
    volume_cells: tuple[CellCard, ...]
    shuffled_cells: tuple[CellCard, ...]
    training_shuffle: ShuffleStats


@dataclass(frozen=True, slots=True)
class PredictionRow:
    key: SampleKey
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


@dataclass(frozen=True, slots=True)
class PredictionRows:
    plan_identity: str
    model_identity: str
    training_count: int
    training_weeks: tuple[date, ...]
    rows: tuple[PredictionRow, ...]
    shuffle: tuple[ShuffleStats, ...]


@dataclass(frozen=True, slots=True)
class WeekSlot:
    partition: str
    week: date
    decision_session: date | None
    mother_count: int
    r5_known_count: int
    up_candidate_count: int
    price_valid_count: int
    exclusion_reasons: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True, slots=True)
class EvaluationRow:
    prediction: PredictionRow
    label: LabelRow | None
    evaluated: bool


@dataclass(frozen=True, slots=True)
class WeekResult:
    slot: WeekSlot
    state: str
    half: int
    f_count: int
    e_count: int
    active_f_count: int
    active_e_count: int
    losses: tuple[Decimal | None, ...]
    delta: Decimal | None
    coverage_f: Decimal | None
    coverage_e: Decimal | None
    label_observability: Decimal | None
    censor_low: Decimal | None
    censor_high: Decimal | None


@dataclass(frozen=True, slots=True)
class HalfResult:
    half: int
    grid_slots: int
    effective_weeks: int
    delta: Decimal | None
    coverage_e: Decimal | None
    coverage_f: Decimal | None


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    block_length: int
    seed: int
    values: tuple[Decimal | None, ...]
    invalid_count: int
    interval: tuple[Decimal, Decimal] | None
    reason: str | None


@dataclass(frozen=True, slots=True)
class PartitionDiagnostics:
    partition: str
    weeks: tuple[WeekResult, ...]
    counts: tuple[tuple[str, int], ...]
    brier: tuple[Decimal | None, ...]
    delta: Decimal | None
    relative_improvement: Decimal | None
    coverage_e: Decimal | None
    coverage_f: Decimal | None
    halves: tuple[HalfResult, HalfResult]
    censor_bounds: tuple[Decimal | None, Decimal | None]
    future_unknown_reasons: tuple[tuple[str, int], ...]
    undefined_target_count: int
    # (PV prediction >= .5, known label count, prediction count)
    observability_groups: tuple[tuple[bool, int, int], ...]
    # (past T, gain_5d, trend_at_5d, count)
    label_components: tuple[tuple[bool, bool, bool, int], ...]
    # (model, bin0..4, count, mean p, observed rate)
    calibration: tuple[tuple[str, int, int, Decimal, Decimal], ...]
    # (model, TP, FP, TN, FN), fixed .5 threshold
    confusion: tuple[tuple[str, int, int, int, int], ...]
    # (T,I,NV,count,positives,end_change,adverse_change,min_close/MA20-1)
    state_rates: tuple[tuple[bool, bool, int, int, int, Decimal, Decimal, Decimal], ...]
    rv_le_point8_count: int


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
    interpretation: str = (
        "Exploratory evidence only for observable E and the declared coarse price baseline; "
        "not causality, full-universe evidence, a ValidationReport or trading permission."
    )


@dataclass(slots=True)
class _Index:
    days: dict[date, CalendarDay]
    splits: dict[str, Split]
    sessions: dict[str, tuple[date, ...]]
    sources: dict[str, str]


def week_key(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _dates(start: date, end: date) -> tuple[date, ...]:
    return tuple(start + timedelta(days=i) for i in range((end - start).days))


def _provenance(plan: Plan, sources: dict[str, str], p: Provenance) -> None:
    _require(
        p.revision == plan.dataset_revision,
        "REVISION_CONFLICT",
        "mixed snapshot revisions",
    )
    _require(
        sources.get(p.source) == p.raw_sha256,
        "SOURCE_IDENTITY_CONFLICT",
        "source/hash is not the bound raw identity",
    )


def _index(plan: Plan) -> _Index:
    _require(
        bool(plan.dataset_revision.strip()), "INVALID_PLAN", "revision is required"
    )
    _require(
        bool(plan.universe_scope.strip()), "INVALID_PLAN", "universe must be declared"
    )
    _require(type(plan.synthetic) is bool, "INVALID_PLAN", "synthetic flag is required")
    _require(plan.design_version == "D009-v1.1", "INVALID_PLAN", "wrong design version")
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
        tuple(s.partition for s in plan.splits) == PARTITIONS,
        "SPLIT_CONFLICT",
        "declare TRAIN/DEVELOPMENT/HELD_OUT in order",
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


def _sample(
    plan: Plan, index: _Index, key: SampleKey, partition: str
) -> tuple[Split, tuple[date, ...], int]:
    _require(partition in index.splits, "SPLIT_CONFLICT", "unknown partition")
    split = index.splits[partition]
    _timestamp(key.as_of)
    _require(
        key.dataset_revision == plan.dataset_revision,
        "REVISION_CONFLICT",
        "wrong sample revision",
    )
    _require(
        bool(key.instrument_id.strip()), "INVALID_SAMPLE_KEY", "instrument is required"
    )
    _require(
        key.as_of == datetime.combine(key.decision_session, time(23, 59, 59), SHANGHAI),
        "INVALID_AS_OF",
        "fixed end-of-session cutoff required",
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
    week = week_key(key.decision_session)
    week_days = _dates(week, week + timedelta(days=7))
    opened = [day for day in week_days if index.days[day].is_open]
    _require(
        bool(opened) and key.decision_session == opened[-1],
        "INVALID_DECISION_SESSION",
        "use last scheduled open day, not always Friday",
    )
    for day in (
        _dates(split.read_from, key.decision_session + timedelta(days=1)) + week_days
    ):
        p = index.days[day].provenance
        _require(
            max(p.event_time, p.available_at) <= key.as_of,
            "CALENDAR_NOT_AVAILABLE",
            "calendar was not known at decision",
        )
    return split, sessions, sessions.index(key.decision_session)


def _unique(rows: tuple[Any, ...]) -> None:
    keys = [row.key for row in rows]
    _require(
        len(keys) == len(set(keys)),
        "DUPLICATE_SAMPLE",
        "one immutable row per sample key",
    )
    stock_weeks = [(k.instrument_id, week_key(k.decision_session)) for k in keys]
    _require(
        len(stock_weeks) == len(set(stock_weeks)),
        "DUPLICATE_SAMPLE",
        "at most one stock/week",
    )


def _bars(
    plan: Plan, index: _Index, split: Split, bars: tuple[DailyBar, ...], cutoff: date
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
            bar.provenance.event_time.date() == bar.session,
            "EVENT_DATE_CONFLICT",
            "quote event must match its session",
        )
        result[bar.session] = bar
    return result


def _prices(
    bars: dict[date, DailyBar],
    needed: tuple[date, ...],
    cutoff: datetime,
    *,
    stock: bool,
) -> tuple[tuple[Decimal, ...], tuple[str, ...], datetime | None]:
    reasons: set[str] = set()
    values: list[Decimal] = []
    stamps: list[datetime] = []
    for day in needed:
        bar = bars.get(day)
        if bar is None:
            reasons.add("PRICE_MISSING")
            continue
        p = bar.provenance
        stamps.extend((p.event_time, p.available_at))
        if max(p.event_time, p.available_at) > cutoff:
            reasons.add("NOT_AVAILABLE_AT_CUTOFF")
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
    return tuple(values), tuple(sorted(reasons)), max(stamps) if stamps else None


def _mean(values: tuple[Decimal, ...] | list[Decimal]) -> Decimal:
    return sum(values, ZERO) / Decimal(len(values))


def _nullable_mean(
    values: tuple[Decimal | None, ...] | list[Decimal | None],
) -> Decimal | None:
    known = [v for v in values if v is not None]
    return _mean(known) if known else None


def _structure(
    closes: tuple[Decimal, ...],
) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, bool]:
    ma20 = _mean(closes[-20:])
    ma60 = _mean(closes[-60:])
    prior_ma20 = _mean(closes[-25:-5])
    r5 = closes[-1] / closes[-6] - ONE
    r20 = closes[-1] / closes[-21] - ONE
    a20 = _mean(
        tuple(
            abs(closes[j] / closes[j - 1] - ONE)
            for j in range(len(closes) - 20, len(closes))
        )
    )
    return r5, r20, a20, ma20, ma60, closes[-1] > ma20 > ma60 and ma20 > prior_ma20


def make_features(
    plan: Plan, asof_price_and_volume_rows: tuple[FeatureView, ...]
) -> FeatureRows:
    """No OutcomeView or future stock data may enter this function."""
    with localcontext(CONTEXT):
        index = _index(plan)
        _unique(asof_price_and_volume_rows)
        result: list[FeatureRow] = []
        for view in sorted(asof_price_and_volume_rows, key=lambda v: v.key):
            split, sessions, t = _sample(plan, index, view.key, view.partition)
            stock = _bars(plan, index, split, view.stock, view.key.decision_session)
            industry = _bars(
                plan, index, split, view.industry, view.key.decision_session
            )
            reasons: set[str] = set()
            member = view.membership
            if member is None:
                reasons.add("MEMBERSHIP_UNKNOWN")
            else:
                _provenance(plan, index.sources, member.provenance)
                _require(
                    member.effective_from < member.effective_to,
                    "MEMBERSHIP_CONFLICT",
                    "invalid member interval",
                )
                if (
                    max(member.provenance.event_time, member.provenance.available_at)
                    > view.key.as_of
                ):
                    reasons.update(("MEMBERSHIP_UNKNOWN", "NOT_AVAILABLE_AT_CUTOFF"))
                elif member.is_member is None or member.ordinary_a_share is None:
                    reasons.add("MEMBERSHIP_UNKNOWN")
                elif not (
                    member.is_member
                    and member.ordinary_a_share
                    and member.venue in ("XSHG", "XSHE")
                    and member.industry_code == "801150"
                    and member.effective_from
                    <= view.key.decision_session
                    < member.effective_to
                ):
                    reasons.add("OUTSIDE_DECLARED_UNIVERSE")
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
            prices, price_reasons, _ = _prices(
                stock, needed, view.key.as_of, stock=True
            )
            industry_prices, industry_reasons, _ = _prices(
                industry, needed, view.key.as_of, stock=False
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
        return tuple(result)


def make_labels(plan: Plan, outcome_price_rows: tuple[OutcomeView, ...]) -> LabelRows:
    """Labels use their own historic+future price view; no volume or refitting."""
    with localcontext(CONTEXT):
        index = _index(plan)
        _unique(outcome_price_rows)
        result: list[LabelRow] = []
        for view in sorted(outcome_price_rows, key=lambda v: v.key):
            split, sessions, t = _sample(plan, index, view.key, view.partition)
            if t + HORIZON >= len(sessions):
                result.append(
                    LabelRow(
                        view.key,
                        view.partition,
                        None,
                        None,
                        None,
                        None,
                        None,
                        reasons=("LABEL_WINDOW_OUTSIDE_SPLIT",),
                    )
                )
                continue
            end = sessions[t + HORIZON]
            bars = _bars(plan, index, split, view.stock, end)
            if t + 1 < WARMUP:
                result.append(
                    LabelRow(
                        view.key,
                        view.partition,
                        None,
                        None,
                        None,
                        end,
                        None,
                        reasons=("INSUFFICIENT_HISTORY",),
                    )
                )
                continue
            needed = sessions[t - WARMUP + 1 : t + HORIZON + 1]
            # Exclusive read end; availability on/after it cannot form a label here.
            deadline = datetime.combine(split.read_to, time(), SHANGHAI)
            prices, reasons, available = _prices(
                bars, needed, deadline - timedelta(microseconds=1), stock=True
            )
            if reasons:
                label_reasons = set(reasons) | {"LABEL_UNOBSERVABLE"}
                if "NOT_AVAILABLE_AT_CUTOFF" in reasons:
                    label_reasons.add("LABEL_NOT_YET_AVAILABLE")
                result.append(
                    LabelRow(
                        view.key,
                        view.partition,
                        None,
                        None,
                        None,
                        end,
                        available,
                        reasons=tuple(sorted(label_reasons)),
                        target_defined="PRICE_SCALE_UNRESOLVED" not in reasons,
                    )
                )
                continue
            current = prices[-HORIZON - 1]
            future = prices[-HORIZON:]
            gain = future[-1] > current
            trend = _structure(prices)[-1]
            ma20_t = _mean(prices[-HORIZON - 20 : -HORIZON])
            result.append(
                LabelRow(
                    view.key,
                    view.partition,
                    int(gain and trend),
                    gain,
                    trend,
                    end,
                    available,
                    future[-1] / current - ONE,
                    min(ZERO, min(c / current - ONE for c in future)),
                    min(future) / ma20_t - ONE,
                )
            )
        return tuple(result)


def _feature_valid(row: FeatureRow) -> None:
    if not row.predictable:
        _require(
            bool(row.reasons),
            "MALFORMED_FEATURE",
            "unobservable/excluded features require reasons",
        )
        return
    _require(
        row.price_valid
        and type(row.trend) is bool
        and type(row.industry_up) is bool
        and type(row.nv) is int
        and row.nv in (0, 1),
        "MALFORMED_FEATURE",
        "unknown feature is not an unseen valid cell",
    )
    for value in (row.r5, row.r20, row.a20, row.ma20, row.ma60, row.rv):
        _require(
            type(value) is Decimal and value.is_finite(),
            "MALFORMED_FEATURE",
            "known features require finite Decimal values",
        )
    assert row.rv is not None
    _require(
        row.rv >= ZERO and row.nv == int(row.rv <= ONE),
        "MALFORMED_FEATURE",
        "NV must match RV",
    )


def _label_valid(plan: Plan, index: _Index, row: LabelRow) -> None:
    split, sessions, t = _sample(plan, index, row.key, row.partition)
    if row.y is None:
        _require(
            bool(row.reasons),
            "MALFORMED_LABEL",
            "unknown label requires an explanation",
        )
        return
    _require(
        type(row.y) is int and row.y in (0, 1) and not row.reasons,
        "MALFORMED_LABEL",
        "label must be 0/1 or unknown",
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
        "incorrect label horizon",
    )
    _require(
        row.label_available_at is not None,
        "MALFORMED_LABEL",
        "known label requires availability",
    )
    assert row.label_available_at is not None and row.label_end is not None
    _require(
        row.target_defined, "MALFORMED_LABEL", "known label must have a defined target"
    )
    _timestamp(row.label_available_at)
    _require(
        datetime.combine(row.label_end, time(), SHANGHAI)
        <= row.label_available_at
        < datetime.combine(split.read_to, time(), SHANGHAI),
        "LABEL_NOT_YET_AVAILABLE",
        "label formation must be inside complete read interval",
    )
    for value in (row.end_change, row.adverse_change, row.min_close_over_ma20):
        _require(
            type(value) is Decimal and value.is_finite(),
            "MALFORMED_LABEL",
            "known label requires price path descriptions",
        )


def _cell(row: FeatureRow, thresholds: Thresholds) -> PriceCell:
    _feature_valid(row)
    assert row.r5 is not None and row.r20 is not None and row.a20 is not None
    return (
        int(row.r5 > thresholds.r5),
        int(row.r20 > thresholds.r20),
        int(row.a20 > thresholds.a20),
        int(bool(row.trend)),
        int(bool(row.industry_up)),
    )


def _shuffle(
    rows: FeatureRows, thresholds: Thresholds
) -> tuple[dict[SampleKey, int], tuple[ShuffleStats, ...]]:
    groups: dict[tuple[str, date, PriceCell], list[FeatureRow]] = defaultdict(list)
    for row in sorted(rows, key=lambda r: r.key):
        _feature_valid(row)
        _require(row.predictable, "MALFORMED_FEATURE", "shuffle accepts only F")
        groups[
            (row.partition, week_key(row.key.decision_session), _cell(row, thresholds))
        ].append(row)
    assignments: dict[SampleKey, int] = {}
    stats: list[ShuffleStats] = []
    for partition in PARTITIONS:
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


def _support(count: int, weeks: tuple[date, ...]) -> str | None:
    if count == 0:
        return "UNSEEN_CELL"
    failures = []
    if count < MIN_ROWS:
        failures.append("ROWS_LT_50")
    if len(weeks) < MIN_CELL_WEEKS:
        failures.append("WEEKS_LT_12")
    return "+".join(failures) if failures else None


def _p(value: Decimal) -> Decimal:
    return value.quantize(P_QUANTUM)


def fit_models(plan: Plan, train_panel: TrainPanel) -> FrozenModelCards:
    """One TRAIN-only fit; no dependence on development/held-out data."""
    with localcontext(CONTEXT):
        index = _index(plan)
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
            _sample(plan, index, row.key, row.partition)
            _feature_valid(row)
        for row in train_panel.labels:
            _require(
                row.partition == "TRAIN", "NON_TRAIN_FIT", "fit accepts TRAIN only"
            )
            _label_valid(plan, index, row)
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
        shuffled, shuffle_stats = _shuffle(rows, thresholds)
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
            n,
            tuple(sorted({week_key(r.key.decision_session) for r in rows})),
            index.splits["TRAIN"].read_to,
            thresholds,
            g,
            _p(g),
            tuple(price_cards),
            volume_cards[0],
            volume_cards[1],
            shuffle_stats[0],
        )


def predict_models(
    plan: Plan, model_cards: FrozenModelCards, feature_rows: FeatureRows
) -> PredictionRows:
    """Four probabilities on exactly F; labels are not an argument."""
    with localcontext(CONTEXT):
        index = _index(plan)
        _require(
            model_cards.plan_identity == identity(plan),
            "MODEL_PLAN_CONFLICT",
            "model cards belong to another frozen plan",
        )
        _require(
            model_cards.training_cutoff == index.splits["TRAIN"].read_to,
            "MODEL_PLAN_CONFLICT",
            "wrong training cutoff",
        )
        _unique(feature_rows)
        for row in feature_rows:
            _sample(plan, index, row.key, row.partition)
            _feature_valid(row)
        rows = tuple(
            sorted((r for r in feature_rows if r.predictable), key=lambda r: r.key)
        )
        shuffled, stats = _shuffle(rows, model_cards.thresholds)
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
                )
            )
        return PredictionRows(
            model_cards.plan_identity,
            identity(model_cards),
            model_cards.training_count,
            model_cards.training_weeks,
            tuple(predictions),
            stats,
        )


def _bootstrap(
    values: tuple[Decimal | None, ...], length: int, seed: int
) -> BootstrapResult:
    """Physical, noncircular slots; nulls and all model pairs stay together."""
    with localcontext(CONTEXT):
        n = len(values)
        if n < length:
            return BootstrapResult(
                length,
                seed,
                (None,) * BOOTSTRAP_DRAWS,
                BOOTSTRAP_DRAWS,
                None,
                "GRID_SHORTER_THAN_BLOCK",
            )
        rng = random.Random(seed)
        draws: list[Decimal | None] = []
        for _ in range(BOOTSTRAP_DRAWS):
            sampled: list[Decimal | None] = []
            while len(sampled) < n:
                start = rng.randrange(n - length + 1)
                sampled.extend(values[start : start + length])
            draws.append(_nullable_mean(sampled[:n]))
        invalid = sum(v is None for v in draws)
        ordered = sorted(v for v in draws if v is not None)
        interval = (ordered[24], ordered[974]) if invalid == 0 else None
        return BootstrapResult(
            length,
            seed,
            tuple(draws),
            invalid,
            interval,
            "ALL_NULL_REPLICATE" if invalid else None,
        )


def _grid(plan: Plan, index: _Index, slots: tuple[WeekSlot, ...]) -> None:
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
                slot.decision_session == (opened[-1] if opened else None),
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


def _prediction_valid(row: PredictionRow) -> None:
    _require(
        len(row.probabilities) == 4,
        "PREDICTION_MASK_CONFLICT",
        "four paired models required",
    )
    for p in row.probabilities:
        _require(
            type(p) is Decimal
            and p.is_finite()
            and ZERO <= p <= ONE
            and p.as_tuple().exponent == -12,
            "PERSISTED_PROBABILITY_REQUIRED",
            "score the exact finite p12 output",
        )
    _require(
        type(row.nv) is int
        and row.nv in (0, 1)
        and type(row.shuffled_nv) is int
        and row.shuffled_nv in (0, 1),
        "MALFORMED_PREDICTION",
        "NV is binary",
    )
    _require(
        type(row.trend) is bool and type(row.industry_up) is bool,
        "MALFORMED_PREDICTION",
        "known states required",
    )
    _decimal(row.rv, "rv")


def _summarize(
    partition: str, slots: tuple[WeekSlot, ...], evaluations: tuple[EvaluationRow, ...]
) -> PartitionDiagnostics:
    groups: dict[date, list[EvaluationRow]] = defaultdict(list)
    for row in evaluations:
        groups[week_key(row.prediction.key.decision_session)].append(row)
    weeks: list[WeekResult] = []
    counts: Counter[str] = Counter()
    unknown: Counter[str] = Counter()
    components: Counter[tuple[bool, bool, bool]] = Counter()
    calibration: dict[tuple[int, int], list[tuple[Decimal, int]]] = defaultdict(list)
    confusion = [[0, 0, 0, 0] for _ in MODELS]
    states: dict[tuple[bool, bool, int], list[LabelRow]] = defaultdict(list)
    observability = [[0, 0], [0, 0]]
    undefined = shrunk = 0
    for position, slot in enumerate(slots):
        group = groups.get(slot.week, [])
        known = [r for r in group if r.evaluated]
        f, e = len(group), len(known)
        _require(
            f <= slot.up_candidate_count and f <= slot.price_valid_count,
            "CALENDAR_GRID_CONFLICT",
            "F exceeds known price/up-candidate set",
        )
        if slot.decision_session is None:
            _require(f == 0, "CALENDAR_GRID_CONFLICT", "predictions in a closed week")
            state = "STRUCTURAL_CLOSED"
        elif e:
            state = "EVALUABLE"
        elif f:
            state = "EMPTY_E_UNOBSERVABLE"
        elif (
            slot.mother_count > 0
            and slot.r5_known_count == slot.mother_count
            and slot.up_candidate_count == 0
        ):
            state = "NO_UP_CANDIDATE"
        else:
            state = "EMPTY_F_UNOBSERVABLE"
        losses: tuple[Decimal | None, ...] = tuple(
            _mean(
                [
                    (r.prediction.probabilities[m] - Decimal(r.label.y)) ** 2
                    for r in known
                    if r.label is not None and r.label.y is not None
                ]
            )
            if e
            else None
            for m in range(4)
        )
        delta = (
            losses[1] - losses[2]
            if losses[1] is not None and losses[2] is not None
            else None
        )
        active_f = sum(r.prediction.pv_fallback is None for r in group)
        active_e = sum(r.prediction.pv_fallback is None for r in known)
        lows: list[Decimal] = []
        highs: list[Decimal] = []
        for row in group:
            pred, label = row.prediction, row.label
            threshold = int(pred.probabilities[2] >= Decimal("0.5"))
            observability[threshold][1] += 1
            shrunk += int(pred.rv <= Decimal("0.8"))
            if row.evaluated:
                assert label is not None and label.y is not None
                y = Decimal(label.y)
                d = (pred.probabilities[1] - y) ** 2 - (pred.probabilities[2] - y) ** 2
                lows.append(d)
                highs.append(d)
                observability[threshold][0] += 1
                components[
                    (pred.trend, bool(label.gain_5d), bool(label.trend_at_5d))
                ] += 1
                states[(pred.trend, pred.industry_up, pred.nv)].append(label)
                for m, p in enumerate(pred.probabilities):
                    bin_index = min(4, int(p * Decimal(5)))
                    calibration[(m, bin_index)].append((p, label.y))
                    positive = p >= Decimal("0.5")
                    confusion[m][
                        0
                        if positive and label.y
                        else 1
                        if positive
                        else 3
                        if label.y
                        else 2
                    ] += 1
            else:
                ds = tuple(
                    (pred.probabilities[1] - y) ** 2 - (pred.probabilities[2] - y) ** 2
                    for y in (ZERO, ONE)
                )
                lows.append(min(ds))
                highs.append(max(ds))
                unknown.update(
                    label.reasons if label is not None else ("LABEL_UNOBSERVABLE",)
                )
                undefined += int(label is not None and not label.target_defined)
        counts[state] += 1
        counts["mother_rows"] += slot.mother_count
        counts["price_valid_rows"] += slot.price_valid_count
        counts["price_to_f_exclusions"] += slot.price_valid_count - f
        counts["F_rows"] += f
        counts["E_rows"] += e
        counts["scheduled_weeks"] += int(slot.decision_session is not None)
        counts["F_nonempty_weeks"] += int(f > 0)
        counts["W_eff"] += int(e > 0)
        weeks.append(
            WeekResult(
                slot,
                state,
                int(position >= len(slots) // 2),
                f,
                e,
                active_f,
                active_e,
                losses,
                delta,
                Decimal(active_f) / Decimal(f) if f else None,
                Decimal(active_e) / Decimal(e) if e else None,
                Decimal(e) / Decimal(f) if f else None,
                _mean(lows) if f else None,
                _mean(highs) if f else None,
            )
        )
    counts["N_grid"] = len(slots)
    brier = tuple(_nullable_mean([w.losses[m] for w in weeks]) for m in range(4))
    delta = _nullable_mean([w.delta for w in weeks])
    relative = (
        delta / brier[1]
        if delta is not None and brier[1] is not None and brier[1] != ZERO
        else None
    )
    halves = []
    for half in (0, 1):
        part = [w for w in weeks if w.half == half]
        halves.append(
            HalfResult(
                half,
                len(part),
                sum(w.e_count > 0 for w in part),
                _nullable_mean([w.delta for w in part]),
                _nullable_mean([w.coverage_e for w in part]),
                _nullable_mean([w.coverage_f for w in part]),
            )
        )
    state_rates = []
    for (trend, industry, nv), labels in sorted(states.items()):
        state_rates.append(
            (
                trend,
                industry,
                nv,
                len(labels),
                sum(int(r.y or 0) for r in labels),
                _mean([r.end_change for r in labels if r.end_change is not None]),
                _mean(
                    [r.adverse_change for r in labels if r.adverse_change is not None]
                ),
                _mean(
                    [
                        r.min_close_over_ma20
                        for r in labels
                        if r.min_close_over_ma20 is not None
                    ]
                ),
            )
        )
    return PartitionDiagnostics(
        partition,
        tuple(weeks),
        tuple(sorted(counts.items())),
        brier,
        delta,
        relative,
        _nullable_mean([w.coverage_e for w in weeks]),
        _nullable_mean([w.coverage_f for w in weeks]),
        (halves[0], halves[1]),
        (
            _nullable_mean([w.censor_low for w in weeks]),
            _nullable_mean([w.censor_high for w in weeks]),
        ),
        tuple(sorted(unknown.items())),
        undefined,
        tuple(
            (bool(i), counts[0], counts[1]) for i, counts in enumerate(observability)
        ),
        tuple((*k, v) for k, v in sorted(components.items())),
        tuple(
            (
                MODELS[m],
                b,
                len(rows),
                _mean([r[0] for r in rows]),
                _mean([Decimal(r[1]) for r in rows]),
            )
            for (m, b), rows in sorted(calibration.items())
        ),
        tuple(
            (MODELS[i], values[0], values[1], values[2], values[3])
            for i, values in enumerate(confusion)
        ),
        tuple(state_rates),
        shrunk,
    )


def _valid_interval(result: BootstrapResult) -> bool:
    ci = result.interval
    return (
        len(result.values) == BOOTSTRAP_DRAWS
        and result.invalid_count == 0
        and all(type(v) is Decimal and v.is_finite() for v in result.values)
        and ci is not None
        and len(ci) == 2
        and all(type(v) is Decimal and v.is_finite() for v in ci)
        and ci[0] <= ci[1]
    )


def _decide(
    validity: tuple[str, ...],
    ci4: BootstrapResult,
    ci13: BootstrapResult,
    half_deltas: tuple[Decimal | None, Decimal | None],
    brier: tuple[Decimal | None, ...],
    relative: Decimal | None,
    blocked: tuple[str, ...] = (),
) -> tuple[str, tuple[str, ...]]:
    if blocked:
        return "blocked", blocked
    failures = list(validity)
    for name, result in (("4", ci4), ("13", ci13)):
        if not _valid_interval(result):
            failures.append(f"INVALID_BOOTSTRAP_{name}")
    if failures:
        return "insufficient", tuple(failures)
    assert ci4.interval is not None and ci13.interval is not None
    positive4, positive13 = ci4.interval[0] > ZERO, ci13.interval[0] > ZERO
    if positive4 != positive13:
        return "insufficient", ("BOOTSTRAP_DIRECTION_CONFLICT",)
    if positive4 and positive13:
        if any(d is None or d <= ZERO for d in half_deltas):
            return "insufficient", ("TIME_HALF_CONFLICT",)
        if brier[2] is None or brier[3] is None or brier[2] >= brier[3]:
            return "insufficient", ("SHUFFLED_VOLUME_CONFLICT",)
        if (
            relative is not None
            and relative >= Decimal("0.02")
            and brier[0] is not None
            and brier[2] < brier[0]
        ):
            return "incremental_in_declared_E", ()
    return "no_declared_advantage", ()


def evaluate_predictions(
    plan: Plan,
    predictions: PredictionRows,
    labels: LabelRows,
    calendar_week_grid: tuple[WeekSlot, ...],
) -> DiagnosticReport:
    """Evaluate persisted probabilities, preserving G, F, E and future censoring."""
    with localcontext(CONTEXT):
        index = _index(plan)
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
            _label_valid(plan, index, label)
        evaluations = []
        for pred in sorted(predictions.rows, key=lambda r: r.key):
            _sample(plan, index, pred.key, pred.partition)
            _prediction_valid(pred)
            label = label_map.get(pred.key)
            if label is not None:
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
            for partition in PARTITIONS
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
                if r.prediction.partition == "HELD_OUT"
                and r.evaluated
                and r.label is not None
                and r.label.y == y
            }
            if len(weeks) < 12:
                validity.append(f"HELD_OUT_CLASS_{y}_WEEKS_LT_12")
        if held.coverage_e is None or held.coverage_e == ZERO:
            validity.append("NO_ACTIVE_PV_COVERAGE_E")
        if any(h.effective_weeks == 0 for h in held.halves):
            validity.append("EMPTY_TIME_HALF")
        if any(v is None for v in held.brier):
            validity.append("UNDEFINED_BRIER")
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
            verdict,
            reasons,
            sensitive,
            joined,
        )
