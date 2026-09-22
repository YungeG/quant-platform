from dataclasses import replace
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, localcontext
from typing import Any

import pytest

from experiments.a_share_market_regime import CHINA_TZ
from experiments.a_share_sector_rounds import (
    RULE_VERSION,
    RoundPhase,
    SectorRoundSignal,
    replay_sector_rounds,
)


def synthetic(rs5_values):
    """Prepared fake indicators/calendar, not a historical market dataset."""
    calendar = {}
    signals = []
    day = date(2025, 1, 6)
    for rs5 in rs5_values:
        while day.weekday() >= 5:
            calendar[day] = False
            day += timedelta(days=1)
        calendar[day] = True
        signals.append(SectorRoundSignal(
            day, Decimal(rs5), Decimal(110), Decimal(100),
            datetime.combine(day, time(15, 1), CHINA_TZ),
        ))
        day += timedelta(days=1)
    return tuple(signals), calendar


def replay(signals, calendar, *, as_of=None, origin=None, sector="synthetic-B"):
    return replay_sector_rounds(
        sector=sector, signals=signals, calendar=calendar,
        initial_inactive_on=origin if origin is not None else min(calendar),
        as_of=as_of if as_of is not None else datetime.combine(max(calendar), time(16), CHINA_TZ),
    )


def test_smoke_independent_round_lifecycle_and_replay():
    signals, calendar = synthetic(("0.02",) * 2 + ("0",) * 3 + ("0.03",) * 12)
    result = replay(signals, calendar)
    assert result.replay_complete
    assert result.phase is RoundPhase.ACTIVE
    assert len(result.rounds) == 2
    first, second = result.rounds
    assert first.start_date == signals[1].trading_date
    assert first.start_known_at == signals[1].available_at
    assert first.end_date == signals[4].trading_date
    assert first.end_known_at == signals[4].available_at
    assert second.start_date == signals[16].trading_date
    assert second.end_date is None
    assert first.logical_key == ("synthetic-B", signals[1].available_at, RULE_VERSION)
    assert len({item.logical_key for item in result.rounds}) == 2
    assert replay(tuple(reversed(signals)), dict(reversed(tuple(calendar.items())))) == result
    assert replay(signals, calendar) == result  # No persistent appends or A-hint dependency.


def test_smoke_gap_preserves_started_round_as_unresolved():
    signals, calendar = synthetic(("0.03",) * 2 + ("0",) * 4)
    missing = signals[2]
    result = replay(signals[:2] + signals[3:], calendar)
    assert result.phase is RoundPhase.UNKNOWN
    assert not result.replay_complete
    assert result.unresolved_on == missing.trading_date
    assert len(result.rounds) == 1
    assert result.rounds[0].end_date is None
    assert result.rounds[0].unresolved_on == missing.trading_date
    assert result.start_streak == result.end_streak == result.cooldown_remaining == 0
    assert result.reasons == (f"missing_signal: {missing.trading_date}",)


def test_smoke_late_data_does_not_retroactively_start():
    signals, calendar = synthetic(("0.03",) * 4)
    late = replace(signals[0], available_at=signals[2].available_at)
    result = replay((late,) + signals[1:], calendar)
    assert result.phase is RoundPhase.UNKNOWN
    assert result.rounds == ()
    assert result.unresolved_on == signals[0].trading_date
    assert result.reasons[0].startswith("signal_not_available:")


def test_smoke_duplicate_is_input_error_not_empty_success():
    signals, calendar = synthetic(("0.03",) * 2)
    with pytest.raises(ValueError, match="duplicate signal/date"):
        replay(signals + signals[:1], calendar)


@pytest.mark.parametrize(("count", "phase", "start_streak", "end_streak", "cooldown", "round_count"), [
    (1, RoundPhase.INACTIVE, 1, 0, 0, 0),
    (2, RoundPhase.ACTIVE, 0, 0, 0, 1),
    (3, RoundPhase.ACTIVE, 0, 1, 0, 1),
    (4, RoundPhase.ACTIVE, 0, 2, 0, 1),
    (5, RoundPhase.COOLDOWN, 0, 0, 10, 1),
    (6, RoundPhase.COOLDOWN, 0, 0, 9, 1),
    (14, RoundPhase.COOLDOWN, 0, 0, 1, 1),
    (15, RoundPhase.INACTIVE, 0, 0, 0, 1),
    (16, RoundPhase.INACTIVE, 1, 0, 0, 1),
    (17, RoundPhase.ACTIVE, 0, 0, 0, 2),
])
def test_exact_confirmation_end_and_cooldown_boundaries(count, phase, start_streak, end_streak, cooldown, round_count):
    values = (("0.02",) * 2 + ("0",) * 3 + ("0.03",) * 12)[:count]
    result = replay(*synthetic(values))
    assert result.phase is phase
    assert result.start_streak == start_streak
    assert result.end_streak == end_streak
    assert result.cooldown_remaining == cooldown
    assert len(result.rounds) == round_count


@pytest.mark.parametrize(("rs5", "close", "ma20", "starts"), [
    ("0.02", "101", "100", True),
    ("0.019999999", "101", "100", False),
    ("0.02", "100", "100", False),
    ("0.10", "99", "100", False),
    ("0", "101", "100", False),
])
def test_start_uses_inclusive_rs_and_strict_trend(rs5, close, ma20, starts):
    signals, calendar = synthetic((rs5,) * 2)
    signals = tuple(replace(s, close=Decimal(close), ma20=Decimal(ma20)) for s in signals)
    assert (replay(signals, calendar).phase is RoundPhase.ACTIVE) is starts


def test_failed_start_day_breaks_consecutive_confirmation():
    values = ("0.03", "0.01", "0.03", "0.03")
    signals, calendar = synthetic(values)
    result = replay(signals, calendar)
    assert len(result.rounds) == 1
    assert result.rounds[0].start_date == signals[3].trading_date


def test_positive_rs_breaks_end_confirmation_and_no_continuous_uptrend_resplit():
    signals, calendar = synthetic(("0.03",) * 20)
    assert len(replay(signals, calendar).rounds) == 1
    signals, calendar = synthetic(("0.03", "0.03", "0", "0", "0.000001", "-0.01", "0", "0"))
    result = replay(signals, calendar)
    assert len(result.rounds) == 1
    assert result.rounds[0].end_date == signals[-1].trading_date


def test_missing_day_cannot_join_start_confirmation_or_create_later_rounds():
    signals, calendar = synthetic(("0.03",) * 6)
    result = replay(signals[:1] + signals[2:], calendar)
    assert result.phase is RoundPhase.UNKNOWN
    assert result.rounds == ()
    assert result.start_streak == 0
    assert result.unresolved_on == signals[1].trading_date


def test_gap_in_cooldown_keeps_completed_round_and_stops_later_inference():
    signals, calendar = synthetic(("0.03",) * 2 + ("0",) * 3 + ("0.03",) * 12)
    result = replay(signals[:6] + signals[7:], calendar)
    assert result.phase is RoundPhase.UNKNOWN
    assert len(result.rounds) == 1
    assert result.rounds[0].end_date == signals[4].trading_date
    assert result.rounds[0].unresolved_on is None
    assert result.unresolved_on == signals[6].trading_date


def test_restoring_causally_available_input_recovers_only_by_origin_replay():
    signals, calendar = synthetic(("0.03",) * 2 + ("0",) * 3)
    assert replay(signals[:1] + signals[2:], calendar).phase is RoundPhase.UNKNOWN
    repaired = replay(signals, calendar)
    assert repaired.phase is RoundPhase.COOLDOWN
    assert repaired.rounds[0].start_known_at == signals[1].available_at
    # A genuinely late record cannot be "repaired" by treating its arrival as historical availability.
    late = replace(signals[1], available_at=signals[-1].available_at)
    assert replay(signals[:1] + (late,) + signals[2:], calendar).phase is RoundPhase.UNKNOWN


def test_current_day_visibility_and_confirmation_timestamp():
    signals, calendar = synthetic(("0.03",) * 2)
    before_close = signals[-1].available_at.replace(hour=14)
    before_publish = signals[-1].available_at.replace(minute=0)
    earlier = replay(signals, calendar, as_of=before_close)
    assert earlier.phase is RoundPhase.INACTIVE
    assert earlier.start_streak == 1
    assert earlier.decision_date == signals[0].trading_date
    assert replay(signals, calendar, as_of=before_publish).phase is RoundPhase.UNKNOWN
    at_publish = replay(signals, calendar, as_of=signals[-1].available_at)
    assert at_publish.phase is RoundPhase.ACTIVE
    assert at_publish.rounds[0].start_known_at == signals[-1].available_at
    assert at_publish.rounds[0].start_known_at != signals[-1].available_at.replace(minute=0)


def test_end_cannot_be_confirmed_before_third_weak_signal_is_available():
    signals, calendar = synthetic(("0.03",) * 2 + ("0",) * 3)
    before = replay(signals, calendar, as_of=signals[-1].available_at.replace(minute=0))
    assert before.phase is RoundPhase.UNKNOWN
    assert before.rounds[0].end_date is None
    at_publish = replay(signals, calendar, as_of=signals[-1].available_at)
    assert at_publish.rounds[0].end_known_at == signals[-1].available_at


def test_future_data_and_explicit_timezones_do_not_change_past_replay():
    signals, calendar = synthetic(("0.03",) * 5)
    as_of = signals[1].available_at
    expected = replay(signals[:2], {d: v for d, v in calendar.items() if d <= as_of.date()}, as_of=as_of)
    changed = signals[:2] + tuple(replace(s, rs5=Decimal("-0.99")) for s in signals[2:])
    assert replay(changed, calendar, as_of=as_of) == expected
    assert replay(signals, calendar, as_of=as_of.astimezone(timezone.utc)) == expected
    utc_signals = tuple(replace(s, available_at=s.available_at.astimezone(timezone.utc)) for s in signals)
    assert replay(utc_signals, calendar, as_of=as_of) == expected
    with localcontext() as context:
        context.prec = 2
        assert replay(signals, calendar, as_of=as_of) == expected


def test_weekend_and_declared_weekday_holiday_do_not_count_as_sessions():
    signals, calendar = synthetic(("0.03",) * 2 + ("0",) * 3 + ("0.03",) * 13)
    holiday = signals[6].trading_date
    calendar[holiday] = False
    signals = tuple(s for s in signals if s.trading_date != holiday)
    result = replay(signals, calendar)
    assert result.rounds[-1].start_date == signals[-1].trading_date
    # Hold the final state across two declared closed calendar days.
    last = max(calendar)
    calendar[last + timedelta(days=1)] = False
    calendar[last + timedelta(days=2)] = False
    closed = replay(signals, calendar)
    assert closed.decision_date == result.decision_date
    assert closed.rounds == result.rounds
    assert closed.phase is result.phase


@pytest.mark.parametrize("issue", ["empty", "start_missing", "end_missing", "internal_gap"])
def test_calendar_missingness_is_unknown_not_an_empty_valid_report(issue):
    signals, calendar = synthetic(("0.03",) * 8)
    origin = min(calendar)
    as_of = datetime.combine(max(calendar), time(16), CHINA_TZ)
    if issue == "empty":
        calendar = {}
    elif issue == "start_missing":
        calendar.pop(origin)
    elif issue == "end_missing":
        calendar.pop(as_of.date())
    else:
        calendar.pop(origin + timedelta(days=5))  # A closed weekend day must remain explicit.
    result = replay(signals, calendar, origin=origin, as_of=as_of)
    assert result.phase is RoundPhase.UNKNOWN
    assert result.rounds == ()
    assert result.reasons[0].startswith("calendar_")


def test_initial_state_must_be_declared_not_inferred_from_signal_prefix():
    signals, calendar = synthetic(("0.03",) * 4)
    as_of = signals[-1].available_at
    # Deliberately malformed keyword input exercises runtime validation.
    arguments: dict[str, Any] = dict(sector="B", signals=signals, calendar=calendar, as_of=as_of)
    with pytest.raises(TypeError, match="initial_inactive_on"):
        replay_sector_rounds(**arguments)
    result = replay(signals, calendar, origin=signals[2].trading_date)
    assert result.initial_inactive_on == signals[2].trading_date
    assert result.rounds[0].start_date == signals[3].trading_date
    assert result.replay_complete  # Not a claim that the caller's initial-state assertion is true.


def test_no_completed_session_is_unknown():
    signals, calendar = synthetic(("0.03",))
    result = replay(signals, calendar, as_of=signals[0].available_at.replace(hour=10))
    assert result.phase is RoundPhase.UNKNOWN
    assert result.decision_date is None
    assert result.reasons[0].startswith("no_completed_session:")


def test_sector_identity_is_part_of_logical_key_but_not_a_required_a_signal():
    signals, calendar = synthetic(("0.03",) * 2)
    first = replay(signals, calendar, sector="synthetic-B")
    other = replay(signals, calendar, sector="synthetic-C")
    assert first.rounds[0].logical_key != other.rounds[0].logical_key
    assert first.rounds[0].start_known_at == other.rounds[0].start_known_at


@pytest.mark.parametrize(("field", "value", "error"), [
    ("trading_date", "2025-01-06", TypeError),
    ("trading_date", datetime(2025, 1, 6), TypeError),
    ("rs5", 0.02, TypeError),
    ("rs5", Decimal("NaN"), TypeError),
    ("rs5", Decimal("Infinity"), TypeError),
    ("close", Decimal(0), ValueError),
    ("close", Decimal(-1), ValueError),
    ("ma20", Decimal(0), ValueError),
    ("ma20", "100", TypeError),
    ("available_at", datetime(2025, 1, 6, 16), ValueError),
    ("available_at", datetime(2025, 1, 6, 14, 59, tzinfo=CHINA_TZ), ValueError),
])
def test_invalid_signal_fields_raise(field, value, error):
    signals, _ = synthetic(("0.03",))
    with pytest.raises(error):
        replace(signals[0], **{field: value})


@pytest.mark.parametrize(("field", "value", "error"), [
    ("sector", "", ValueError),
    ("sector", " B", ValueError),
    ("sector", 5, ValueError),
    ("signals", [], TypeError),
    ("signals", (None,), TypeError),
    ("calendar", [], TypeError),
    ("calendar", {date(2025, 1, 6): 1}, TypeError),
    ("calendar", {"2025-01-06": True}, TypeError),
    ("initial_inactive_on", "2025-01-06", TypeError),
    ("initial_inactive_on", date(2026, 1, 1), ValueError),
    ("as_of", datetime(2025, 1, 7, 16), ValueError),
])
def test_invalid_replay_arguments_raise(field, value, error):
    signals, calendar = synthetic(("0.03",) * 2)
    # Any is limited to negative tests that intentionally violate the interface.
    arguments: dict[str, Any] = dict(
        sector="B", signals=signals, calendar=calendar,
        initial_inactive_on=min(calendar), as_of=signals[-1].available_at,
    )
    arguments[field] = value
    with pytest.raises(error):
        replay_sector_rounds(**arguments)


def test_closed_session_signal_is_malformed_even_before_completeness_checks():
    signals, calendar = synthetic(("0.03",) * 2)
    calendar[signals[0].trading_date] = False
    with pytest.raises(ValueError, match="signal on a closed session"):
        replay(signals, calendar)


def test_declared_inactive_origin_cannot_be_a_closed_day():
    origin = date(2025, 1, 5)
    calendar = {origin: False, origin + timedelta(days=1): True}
    with pytest.raises(ValueError, match="initial_inactive_on must be an open session"):
        replay((), calendar)
