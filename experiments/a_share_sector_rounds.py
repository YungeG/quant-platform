"""Synthetic-first replay of independent sector rounds, without trading simulation.

Inputs are precomputed, point-in-time RS5/MA20 signals; this module does not
construct or qualify a market series. A caller must declare a known inactive
origin (no pending confirmation or cooldown), not infer it from a file's first row.
See research/a-share-sector-rounds.md for the deliberately fail-closed gap policy.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum

from experiments.a_share_market_regime import CHINA_TZ


RULE_VERSION = "layered_candidate_v1"


class RoundPhase(str, Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    COOLDOWN = "cooldown"
    UNKNOWN = "unknown"


def _china_time(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value.astimezone(CHINA_TZ)


@dataclass(frozen=True, slots=True)
class SectorRoundSignal:
    trading_date: date
    rs5: Decimal
    close: Decimal
    ma20: Decimal
    available_at: datetime

    def __post_init__(self) -> None:
        if type(self.trading_date) is not date:
            raise TypeError("trading_date must be a date")
        for name in ("rs5", "close", "ma20"):
            value = getattr(self, name)
            if type(value) is not Decimal or not value.is_finite():
                raise TypeError(f"{name} must be a finite Decimal")
            if name != "rs5" and value <= 0:
                raise ValueError(f"{name} must be positive")
        available_at = _china_time(self.available_at, "available_at")
        if available_at < datetime.combine(self.trading_date, time(15), CHINA_TZ):
            raise ValueError("daily indicators cannot be available before the 15:00 close")
        object.__setattr__(self, "available_at", available_at)


@dataclass(frozen=True, slots=True)
class SectorRound:
    sector: str
    start_date: date
    start_known_at: datetime
    end_date: date | None = None
    end_known_at: datetime | None = None
    unresolved_on: date | None = None
    rule_version: str = RULE_VERSION

    @property
    def logical_key(self) -> tuple[str, datetime, str]:
        """Research deduplication coordinate, NOT a Platform ArtifactRef."""
        return self.sector, self.start_known_at, self.rule_version


@dataclass(frozen=True, slots=True)
class SectorRoundReplay:
    sector: str
    initial_inactive_on: date
    as_of: datetime
    decision_date: date | None
    phase: RoundPhase
    rounds: tuple[SectorRound, ...]
    start_streak: int
    end_streak: int
    cooldown_remaining: int
    unresolved_on: date | None
    reasons: tuple[str, ...]
    rule_version: str = RULE_VERSION

    @property
    def replay_complete(self) -> bool:
        """Only supplied-indicator replay; never declared-scope data completeness."""
        return self.phase is not RoundPhase.UNKNOWN


def replay_sector_rounds(
    *,
    sector: str,
    signals: tuple[SectorRoundSignal, ...],
    calendar: Mapping[date, bool],
    initial_inactive_on: date,
    as_of: datetime,
) -> SectorRoundReplay:
    """Replay v1 from an explicitly declared inactive start of day, without I/O.

    ``initial_inactive_on`` is the first eligible session, not an inferred warmup
    boundary. Caller authority for that initial state and indicator lineage is
    outside this module. Each session uses min(as_of, that day's end) as its
    availability cutoff; start/end timestamps are actual signal availability.

    Malformed inputs raise. An incomplete calendar or the first missing/late
    session returns UNKNOWN, preserving earlier confirmed rounds. No later state
    is inferred across that gap. Replay is stateless and order-independent.
    """
    as_of = _china_time(as_of, "as_of")
    if type(sector) is not str or not sector.strip() or sector != sector.strip():
        raise ValueError("sector must be a nonempty trimmed stable identity")
    if type(initial_inactive_on) is not date:
        raise TypeError("initial_inactive_on must be a date")
    if initial_inactive_on > as_of.date():
        raise ValueError("initial_inactive_on must not be after as_of")
    if type(signals) is not tuple or any(type(item) is not SectorRoundSignal for item in signals):
        raise TypeError("signals must be a tuple of SectorRoundSignal values")
    if not isinstance(calendar, Mapping) or any(
        type(day) is not date or type(is_open) is not bool for day, is_open in calendar.items()
    ):
        raise TypeError("calendar must map dates to booleans")
    by_date: dict[date, SectorRoundSignal] = {}
    for item in signals:
        if item.trading_date in by_date:
            raise ValueError(f"duplicate signal/date: {item.trading_date}; supply one frozen revision")
        if item.trading_date in calendar and not calendar[item.trading_date]:
            raise ValueError(f"signal on a closed session: {item.trading_date}")
        by_date[item.trading_date] = item

    rounds: list[SectorRound] = []
    decision_date: date | None = None
    phase = RoundPhase.INACTIVE
    start_streak = end_streak = cooldown = 0

    def unknown(reason: str, day: date | None = None) -> SectorRoundReplay:
        if rounds and rounds[-1].end_date is None:
            rounds[-1] = replace(rounds[-1], unresolved_on=day)
        return SectorRoundReplay(
            sector, initial_inactive_on, as_of, decision_date, RoundPhase.UNKNOWN,
            tuple(rounds), 0, 0, 0, day, (reason,),
        )

    days = sorted(day for day in calendar if initial_inactive_on <= day <= as_of.date())
    if not days or days[0] != initial_inactive_on or days[-1] != as_of.date():
        return unknown("calendar_not_covered: include every day from origin through as_of")
    if len(days) != (as_of.date() - initial_inactive_on).days + 1:
        return unknown("calendar_gap: closed days must also be explicit")
    if not calendar[initial_inactive_on]:
        raise ValueError("initial_inactive_on must be an open session")
    sessions = [
        day for day in days
        if calendar[day] and datetime.combine(day, time(15), CHINA_TZ) <= as_of
    ]
    if not sessions:
        return unknown("no_completed_session: no close at or before as_of")
    decision_date = sessions[-1]
    for day in sessions:
        signal = by_date.get(day)
        # ponytail: stop at the first gap; a causally complete origin replay is
        # required for recovery. Add checkpoint recovery only with an approved contract.
        if signal is None:
            return unknown(f"missing_signal: {day}", day)
        cutoff = min(as_of, datetime.combine(day, time.max, CHINA_TZ))
        if signal.available_at > cutoff:
            return unknown(f"signal_not_available: {day} not known by {cutoff.isoformat()}", day)
        if phase is RoundPhase.COOLDOWN:
            cooldown -= 1
            if cooldown == 0:
                phase = RoundPhase.INACTIVE
            continue  # Even the tenth cooldown day cannot seed a new confirmation.
        if phase is RoundPhase.ACTIVE:
            end_streak = end_streak + 1 if signal.rs5 <= 0 else 0
            if end_streak == 3:
                rounds[-1] = replace(rounds[-1], end_date=day, end_known_at=signal.available_at)
                phase = RoundPhase.COOLDOWN
                end_streak = 0
                cooldown = 10
        else:
            starts = signal.rs5 >= Decimal("0.02") and signal.close > signal.ma20
            start_streak = start_streak + 1 if starts else 0
            if start_streak == 2:
                rounds.append(SectorRound(sector, day, signal.available_at))
                phase = RoundPhase.ACTIVE
                start_streak = 0
    return SectorRoundReplay(
        sector, initial_inactive_on, as_of, decision_date, phase, tuple(rounds),
        start_streak, end_streak, cooldown, None, (),
    )
