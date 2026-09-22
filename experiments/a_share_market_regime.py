"""Causal, diagnostic-only A-share market regime; no orders or return simulation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Context, Decimal, localcontext
from enum import Enum
from zoneinfo import ZoneInfo

from experiments.a_share_risk_state import PricePoint

CHINA_TZ = ZoneInfo("Asia/Shanghai")
INDEX_CODES = ("000300.SH", "000905.SH", "000852.SH")


class MarketPhase(str, Enum):
    BULL = "bull"
    BEAR = "bear"
    TRANSITION = "transition"
    UNKNOWN = "unknown"


class EvaluationBasis(str, Enum):
    HISTORICAL = "historical"
    SNAPSHOT = "snapshot"


@dataclass(frozen=True, slots=True)
class RegimeConfig:
    ma_window: int = 200
    momentum_window: int = 60
    confirmation_sessions: int = 3

    def __post_init__(self) -> None:
        for name in ("ma_window", "momentum_window", "confirmation_sessions"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be a positive integer")

    @property
    def required_sessions(self) -> int:
        return max(self.ma_window, self.momentum_window + 1) + self.confirmation_sessions - 1


DEFAULT_CONFIG = RegimeConfig()


def _china_time(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value.astimezone(CHINA_TZ)


@dataclass(frozen=True, slots=True)
class PublishedIndexClose:
    instrument: str
    point: PricePoint
    available_at: datetime

    def __post_init__(self) -> None:
        if self.instrument not in INDEX_CODES:
            raise ValueError(f"unsupported index: {self.instrument}; expected {INDEX_CODES}")
        if type(self.point) is not PricePoint:
            raise TypeError("point must be PricePoint")
        available_at = _china_time(self.available_at, "available_at")
        if available_at < datetime.combine(self.point.trading_date, time(15), CHINA_TZ):
            raise ValueError("daily close cannot be available before the 15:00 session close")
        object.__setattr__(self, "available_at", available_at)


@dataclass(frozen=True, slots=True)
class IndexSignal:
    instrument: str
    trading_date: date
    available_at: datetime
    close: Decimal
    moving_average: Decimal
    momentum: Decimal
    phase: MarketPhase


@dataclass(frozen=True, slots=True)
class SessionPhase:
    trading_date: date
    phase: MarketPhase


@dataclass(frozen=True, slots=True)
class MarketRegime:
    as_of: datetime
    decision_date: date | None
    phase: MarketPhase
    candidate_phase: MarketPhase
    required_sessions: int
    consecutive_sessions: int
    indices: tuple[IndexSignal, ...]
    confirmation: tuple[SessionPhase, ...]
    reasons: tuple[str, ...]
    basis: EvaluationBasis = EvaluationBasis.HISTORICAL


def _index_signal(
    instrument: str,
    points: tuple[PublishedIndexClose, ...],
    config: RegimeConfig,
) -> IndexSignal:
    # Fixed arithmetic context makes replay independent of the caller's Decimal context.
    with localcontext(Context(prec=28)):
        close = points[-1].point.close
        average = sum(
            (item.point.close for item in points[-config.ma_window :]), Decimal(0)
        ) / config.ma_window
        momentum = close / points[-config.momentum_window - 1].point.close - 1
    phase = MarketPhase.TRANSITION
    if close > average and momentum > 0:
        phase = MarketPhase.BULL
    elif close < average and momentum < 0:
        phase = MarketPhase.BEAR
    return IndexSignal(
        instrument, points[-1].point.trading_date, points[-1].available_at,
        close, average, momentum, phase,
    )


def evaluate_market_regime(
    *,
    observations: tuple[PublishedIndexClose, ...],
    calendar: Mapping[date, bool],
    as_of: datetime,
    config: RegimeConfig = DEFAULT_CONFIG,
    basis: EvaluationBasis = EvaluationBasis.HISTORICAL,
) -> MarketRegime:
    """Classify the latest completed session known at an explicit evaluation time.

    Calendar must include every calendar day (including closed days) through as_of.
    HISTORICAL requires visibility by each confirmation day's end, capped by as_of.
    SNAPSHOT reconstructs the same trailing pattern using only revisions visible at
    as_of; it does NOT establish what was known on past confirmation days. Neither
    mode rewrites availability timestamps. Missing/late inputs fail closed, with no
    filling or smaller universe. Malformed inputs raise; insufficient evidence is UNKNOWN.
    """
    as_of = _china_time(as_of, "as_of")
    if type(config) is not RegimeConfig:
        raise TypeError("config must be RegimeConfig")
    if type(basis) is not EvaluationBasis:
        raise TypeError("basis must be EvaluationBasis")
    if type(observations) is not tuple or any(
        type(item) is not PublishedIndexClose for item in observations
    ):
        raise TypeError("observations must be a tuple of PublishedIndexClose values")
    if not isinstance(calendar, Mapping) or any(
        type(day) is not date or type(is_open) is not bool
        for day, is_open in calendar.items()
    ):
        raise TypeError("calendar must map dates to booleans")
    by_key: dict[tuple[str, date], PublishedIndexClose] = {}
    for item in observations:
        key = (item.instrument, item.point.trading_date)
        if key in by_key:
            raise ValueError(f"duplicate index/date: {key}; supply one frozen revision")
        if item.point.trading_date in calendar and not calendar[item.point.trading_date]:
            raise ValueError(f"close on a closed session: {key}")
        by_key[key] = item

    def unknown(reason: str, decision_date: date | None = None) -> MarketRegime:
        return MarketRegime(
            as_of, decision_date, MarketPhase.UNKNOWN, MarketPhase.UNKNOWN,
            config.required_sessions, 0, (), (), (reason,), basis,
        )

    today = as_of.date()
    days = sorted(day for day in calendar if day <= today)
    if not days or days[-1] != today:
        return unknown(f"calendar_not_covered: calendar must extend through {today}")
    if len(days) != (today - days[0]).days + 1:
        return unknown("calendar_gap: every calendar day, including closed days, is required")
    sessions = [
        day for day in days
        if calendar[day] and datetime.combine(day, time(15), CHINA_TZ) <= as_of
    ]
    if not sessions:
        return unknown("no_completed_session: no market close at or before as_of")
    decision_date = sessions[-1]
    if len(sessions) < config.required_sessions:
        return unknown(
            f"insufficient_history: need {config.required_sessions} completed sessions, "
            f"have {len(sessions)}", decision_date,
        )

    confirmation: list[SessionPhase] = []
    reasons: list[str] = []
    indices: tuple[IndexSignal, ...] = ()
    window_size = max(config.ma_window, config.momentum_window + 1)
    for end in range(len(sessions) - config.confirmation_sessions + 1, len(sessions) + 1):
        window = sessions[end - window_size : end]
        day = window[-1]
        cutoff = as_of if basis is EvaluationBasis.SNAPSHOT else min(
            as_of, datetime.combine(day, time.max, CHINA_TZ),
        )
        signals: list[IndexSignal] = []
        for instrument in INDEX_CODES:
            missing = next((d for d in window if (instrument, d) not in by_key), None)
            if missing is not None:
                reasons.append(f"missing_close: {instrument} {missing} required for {day}")
                continue
            points = tuple(by_key[instrument, d] for d in window)
            late = next((p for p in points if p.available_at > cutoff), None)
            if late is not None:
                reasons.append(
                    f"close_not_available: {instrument} {late.point.trading_date} "
                    f"not known by {cutoff.isoformat()}"
                )
                continue
            signals.append(_index_signal(instrument, points, config))
        indices = tuple(signals)
        candidate = MarketPhase.TRANSITION
        if len(indices) != len(INDEX_CODES):
            candidate = MarketPhase.UNKNOWN
        elif sum(item.phase == MarketPhase.BULL for item in indices) >= 2:
            candidate = MarketPhase.BULL
        elif sum(item.phase == MarketPhase.BEAR for item in indices) >= 2:
            candidate = MarketPhase.BEAR
        confirmation.append(SessionPhase(day, candidate))

    candidate = confirmation[-1].phase
    consecutive = 0
    for item in reversed(confirmation):
        if item.phase is not candidate or candidate is MarketPhase.UNKNOWN:
            break
        consecutive += 1
    if reasons:
        phase = MarketPhase.UNKNOWN
    elif candidate in (MarketPhase.BULL, MarketPhase.BEAR):
        if consecutive == config.confirmation_sessions:
            phase = candidate
            if basis is EvaluationBasis.SNAPSHOT:
                reasons.append(f"snapshot_pattern_{phase.value}: {consecutive} sessions reconstructed at as_of")
            else:
                reasons.append(f"confirmed_{phase.value}: {consecutive} consecutive sessions")
        else:
            phase = MarketPhase.TRANSITION
            prefix = "snapshot_pattern_pending" if basis is EvaluationBasis.SNAPSHOT else "confirmation_pending"
            reasons.append(
                f"{prefix}: {candidate.value} {consecutive}/{config.confirmation_sessions}"
            )
    else:
        phase = MarketPhase.TRANSITION
        reasons.append("indices_disagree_or_flat: no two-index directional majority")
    return MarketRegime(
        as_of, decision_date, phase, candidate, config.required_sessions,
        consecutive, indices, tuple(confirmation), tuple(reasons), basis,
    )
