import csv
import hashlib
import json
import subprocess
import sys
from dataclasses import replace
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, localcontext
from pathlib import Path

import pytest

from experiments import run_a_share_market_regime as runner
from experiments.a_share_market_regime import (
    CHINA_TZ,
    DEFAULT_CONFIG,
    INDEX_CODES,
    EvaluationBasis,
    MarketPhase,
    PublishedIndexClose,
    RegimeConfig,
    evaluate_market_regime,
)
from experiments.a_share_risk_state import PricePoint
from experiments.run_a_share_market_regime import main


ROOT = Path(__file__).resolve().parents[2]
SMALL_CONFIG = RegimeConfig(ma_window=3, momentum_window=2, confirmation_sessions=3)


def market(closes):
    """Synthetic calendar, deliberately not a claim about real exchange holidays."""
    assert len(closes) == 3 and len({len(values) for values in closes}) == 1
    calendar = {}
    observations = []
    day = date(2025, 1, 6)
    for values in zip(*closes, strict=True):
        while day.weekday() >= 5:
            calendar[day] = False
            day += timedelta(days=1)
        calendar[day] = True
        for instrument, close in zip(INDEX_CODES, values, strict=True):
            observations.append(PublishedIndexClose(
                instrument, PricePoint(day, Decimal(close)),
                datetime.combine(day, time(15, 1), CHINA_TZ),
            ))
        day += timedelta(days=1)
    as_of = datetime.combine(day - timedelta(days=1), time(16), CHINA_TZ)
    return tuple(observations), calendar, as_of


def trending(slopes=(1, 1, 1), count=202):
    return market(tuple(tuple(1000 + slope * i for i in range(count)) for slope in slopes))


def evaluate(data, config=DEFAULT_CONFIG):
    observations, calendar, as_of = data
    return evaluate_market_regime(
        observations=observations, calendar=calendar, as_of=as_of, config=config,
    )


@pytest.mark.parametrize(("slopes", "phase"), [
    ((1, 1, 1), MarketPhase.BULL),
    ((-1, -1, -1), MarketPhase.BEAR),
    ((0, 0, 0), MarketPhase.TRANSITION),
    ((1, 1, -1), MarketPhase.BULL),
    ((1, -1, -1), MarketPhase.BEAR),
    ((1, -1, 0), MarketPhase.TRANSITION),
])
def test_default_market_phases(slopes, phase):
    result = evaluate(trending(slopes))
    assert result.phase == phase
    assert result.candidate_phase == phase
    assert result.required_sessions == 202
    assert result.consecutive_sessions == 3
    assert len(result.indices) == 3
    assert tuple(day.phase for day in result.confirmation) == (phase,) * 3


def test_indicators_include_today_and_use_exact_session_lag():
    observations, calendar, as_of = trending()
    result = evaluate((observations, calendar, as_of))
    assert result.decision_date == as_of.date()
    assert result.indices[0].close == Decimal(1201)
    assert result.indices[0].moving_average == Decimal("1101.5")
    assert result.indices[0].momentum == Decimal(1201) / Decimal(1141) - 1
    assert result.indices[0].available_at == observations[-3].available_at
    assert len(result.confirmation) == 3
    assert result.reasons == ("confirmed_bull: 3 consecutive sessions",)


@pytest.mark.parametrize("count", [60, 199, 200, 201])
def test_warmup_requires_indicators_plus_confirmation(count):
    result = evaluate(trending(count=count))
    assert result.phase == MarketPhase.UNKNOWN
    assert result.required_sessions == 202
    assert result.reasons[0].startswith("insufficient_history:")


@pytest.mark.parametrize("values", [(2, 4, 3), (2, 3, 3), (10, 1, 4)])
def test_equal_thresholds_and_conflicting_indicators_are_transition(values):
    result = evaluate(
        market((values,) * 3), RegimeConfig(ma_window=3, momentum_window=1, confirmation_sessions=1),
    )
    assert result.phase == MarketPhase.TRANSITION
    assert all(item.phase == MarketPhase.TRANSITION for item in result.indices)


@pytest.mark.parametrize(("count", "phase", "consecutive"), [
    (6, MarketPhase.TRANSITION, 1),
    (7, MarketPhase.TRANSITION, 2),
    (8, MarketPhase.BEAR, 3),
])
def test_bear_flip_requires_three_consecutive_sessions(count, phase, consecutive):
    values = (1, 2, 3, 4, 5, 3, 2, 1)[:count]
    result = evaluate(market((values,) * 3), SMALL_CONFIG)
    assert result.phase == phase
    assert result.candidate_phase == MarketPhase.BEAR
    assert result.consecutive_sessions == consecutive


def test_transition_interrupts_confirmation():
    result = evaluate(market(((1, 2, 3, 4, 3, 5),) * 3), SMALL_CONFIG)
    assert tuple(day.phase for day in result.confirmation) == (
        MarketPhase.BULL, MarketPhase.TRANSITION, MarketPhase.BULL,
    )
    assert result.phase == MarketPhase.TRANSITION
    assert result.consecutive_sessions == 1
    assert "confirmation_pending" in result.reasons[0]


def test_future_closes_do_not_change_a_past_result():
    observations, calendar, _ = trending(count=205)
    day = observations[-12].point.trading_date  # Session 202 of 205.
    as_of = datetime.combine(day, time(16), CHINA_TZ)
    prefix = tuple(item for item in observations if item.point.trading_date <= day)
    expected = evaluate((prefix, {d: v for d, v in calendar.items() if d <= day}, as_of))
    changed_future = tuple(
        replace(item, point=PricePoint(item.point.trading_date, Decimal("0.01")))
        if item.point.trading_date > day else item for item in observations
    )
    assert expected.phase == MarketPhase.BULL
    assert evaluate((observations, calendar, as_of)) == expected
    assert evaluate((changed_future, calendar, as_of)) == expected


def test_late_close_cannot_retroactively_confirm_a_prior_day():
    observations, calendar, as_of = trending()
    delayed_day = observations[-9].point.trading_date
    delayed = tuple(
        replace(item, available_at=as_of) if item.point.trading_date == delayed_day else item
        for item in observations
    )
    result = evaluate((delayed, calendar, as_of))
    assert result.phase == MarketPhase.UNKNOWN
    assert result.candidate_phase == MarketPhase.BULL
    assert result.confirmation[0].phase == MarketPhase.UNKNOWN
    assert any("close_not_available" in reason for reason in result.reasons)


def test_latest_close_requires_actual_availability_and_allows_exact_boundary():
    observations, calendar, as_of = trending()
    before_available = as_of.replace(hour=15, minute=0)
    assert evaluate((observations, calendar, before_available)).phase == MarketPhase.UNKNOWN
    exactly_available = as_of.replace(hour=15, minute=1)
    assert evaluate((observations, calendar, exactly_available)).phase == MarketPhase.BULL


def test_input_order_timezone_and_decimal_context_do_not_change_result():
    observations, calendar, as_of = trending()
    expected = evaluate((observations, calendar, as_of))
    reordered = (tuple(reversed(observations)), dict(reversed(tuple(calendar.items()))), as_of)
    assert evaluate(reordered) == expected
    assert evaluate((observations, calendar, as_of.astimezone(timezone.utc))) == expected
    with localcontext() as context:
        context.prec = 3
        assert evaluate((observations, calendar, as_of)) == expected


@pytest.mark.parametrize("missing", ["latest_one", "internal_all", "entire_index", "old_ma_close"])
def test_missing_data_never_forward_fills_or_shrinks_universe(missing):
    observations, calendar, as_of = trending()
    if missing == "latest_one":
        filtered = observations[:-1]
    elif missing == "internal_all":
        gap = observations[300].point.trading_date
        filtered = tuple(item for item in observations if item.point.trading_date != gap)
    elif missing == "entire_index":
        filtered = tuple(item for item in observations if item.instrument != INDEX_CODES[-1])
    else:
        filtered = observations[1:]
    result = evaluate((filtered, calendar, as_of))
    assert result.phase == MarketPhase.UNKNOWN
    assert any("missing_close" in reason for reason in result.reasons)


@pytest.mark.parametrize("issue", ["gap", "stale", "empty", "weekdays_only"])
def test_incomplete_calendar_returns_unknown(issue):
    observations, calendar, as_of = trending()
    if issue == "gap":
        calendar.pop(observations[300].point.trading_date)
    elif issue == "stale":
        calendar.pop(as_of.date())
    elif issue == "empty":
        calendar = {}
    else:
        calendar = {d: v for d, v in calendar.items() if v}
    result = evaluate((observations, calendar, as_of))
    assert result.phase == MarketPhase.UNKNOWN
    assert result.reasons[0].startswith("calendar_")


def test_weekend_and_intraday_report_previous_close_not_new_intraday_phase():
    observations, calendar, as_of = trending(count=205)
    friday = as_of.date()
    assert friday.weekday() == 4
    calendar[friday + timedelta(days=1)] = False
    calendar[friday + timedelta(days=2)] = False
    monday = friday + timedelta(days=3)
    calendar[monday] = True
    for evaluation_time in (
        as_of + timedelta(days=2),
        datetime.combine(monday, time(10), CHINA_TZ),
    ):
        result = evaluate((observations, calendar, evaluation_time))
        assert result.phase == MarketPhase.BULL
        assert result.decision_date == friday
    result = evaluate((observations, calendar, datetime.combine(monday, time(16), CHINA_TZ)))
    assert result.phase == MarketPhase.UNKNOWN
    assert result.decision_date == monday


def test_declared_weekday_holiday_is_not_a_missing_trading_session():
    observations, calendar, as_of = trending(count=203)
    trading_days = sorted(day for day, is_open in calendar.items() if is_open)
    holiday = trading_days[-2]
    assert holiday.weekday() < 5
    calendar[holiday] = False
    filtered = tuple(item for item in observations if item.point.trading_date != holiday)
    result = evaluate((filtered, calendar, as_of))
    assert result.phase == MarketPhase.BULL
    assert tuple(day.trading_date for day in result.confirmation) == (
        trading_days[-4], trading_days[-3], trading_days[-1],
    )


def test_longer_momentum_window_controls_warmup_and_alignment():
    config = RegimeConfig(ma_window=2, momentum_window=5, confirmation_sessions=3)
    assert config.required_sessions == 8
    assert evaluate(trending(count=7), config).phase == MarketPhase.UNKNOWN
    result = evaluate(trending(count=8), config)
    assert result.phase == MarketPhase.BULL
    assert result.indices[0].moving_average == Decimal("1006.5")
    assert result.indices[0].momentum == Decimal(1007) / Decimal(1002) - 1


def test_no_completed_session_returns_unknown():
    day = date(2025, 1, 6)
    result = evaluate(((), {day: True}, datetime.combine(day, time(10), CHINA_TZ)))
    assert result.phase == MarketPhase.UNKNOWN
    assert result.decision_date is None
    assert "no_completed_session" in result.reasons[0]


@pytest.mark.parametrize("close", ["NaN", "Infinity", "-1", "0"])
def test_invalid_prices_are_rejected(close):
    with pytest.raises((TypeError, ValueError), match="close"):
        PricePoint(date(2025, 1, 6), Decimal(close))


def test_duplicate_closed_session_and_unsupported_index_are_rejected():
    observations, calendar, as_of = trending()
    with pytest.raises(ValueError, match="duplicate index/date"):
        evaluate((observations + observations[:1], calendar, as_of))
    calendar[as_of.date()] = False
    with pytest.raises(ValueError, match="closed session"):
        evaluate((observations, calendar, as_of))
    with pytest.raises(ValueError, match="unsupported index"):
        replace(observations[0], instrument="510300.SH")


def test_naive_timestamps_and_intraday_closes_are_rejected():
    observations, calendar, as_of = trending()
    with pytest.raises(ValueError, match="timezone-aware"):
        evaluate((observations, calendar, as_of.replace(tzinfo=None)))
    with pytest.raises(ValueError, match="timezone-aware"):
        replace(observations[-1], available_at=as_of.replace(tzinfo=None))
    with pytest.raises(ValueError, match="before the 15:00"):
        replace(observations[-1], available_at=as_of.replace(hour=14))


@pytest.mark.parametrize("kwargs", [
    {"ma_window": 0}, {"momentum_window": -1}, {"confirmation_sessions": True},
    {"ma_window": 3.5},
])
def test_invalid_config_is_rejected(kwargs):
    with pytest.raises(ValueError, match="positive integer"):
        RegimeConfig(**kwargs)


def test_api_input_types_are_checked():
    observations, calendar, as_of = trending()
    with pytest.raises(TypeError, match="observations"):
        evaluate((list(observations), calendar, as_of))
    with pytest.raises(TypeError, match="calendar"):
        evaluate((observations, {as_of.date(): 1}, as_of))
    with pytest.raises(TypeError, match="config"):
        evaluate((observations, calendar, as_of), config=None)  # type: ignore[arg-type]


def csv_inputs(tmp_path, observations, calendar, as_of):
    prices = tmp_path / "prices.csv"
    calendar_path = tmp_path / "calendar.csv"
    with prices.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(("ts_code", "trade_date", "close", "available_at"))
        for item in observations:
            writer.writerow((item.instrument, item.point.trading_date.strftime("%Y%m%d"),
                             str(item.point.close), item.available_at.isoformat()))
    with calendar_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(("cal_date", "is_open"))
        writer.writerows((d.isoformat(), int(v)) for d, v in calendar.items())
    return ["--prices", str(prices), "--calendar", str(calendar_path), "--as-of", as_of.isoformat()]


def cli(args):
    return subprocess.run(
        [sys.executable, "-m", "experiments.run_a_share_market_regime", *args],
        cwd=ROOT, text=True, capture_output=True, check=False, timeout=10,
    )


def test_cli_default_smoke_and_replay(tmp_path):
    args = csv_inputs(tmp_path, *trending())
    process = cli(args)
    assert process.returncode == 0, process.stderr
    assert process.stderr == ""
    report = json.loads(process.stdout)
    assert report["strategy"] == "a_share_market_regime_v1"
    assert report["authority"] == "diagnostic_only"
    assert report["trade_authorized"] is False
    assert report["phase_label"] == "牛市"
    assert report["result"]["phase"] == "bull"
    assert report["result"]["indices"][0]["moving_average"] == "1101.5"
    assert report["config"] == {"ma_window": 200, "momentum_window": 60, "confirmation_sessions": 3}
    assert report["sources"]["prices"]["sha256"] == hashlib.sha256(Path(args[1]).read_bytes()).hexdigest()
    assert report["sources"]["calendar"]["sha256"] == hashlib.sha256(Path(args[3]).read_bytes()).hexdigest()
    assert cli(args).stdout == process.stdout


def test_cli_unknown_is_json_with_exit_one(tmp_path):
    observations, calendar, as_of = trending()
    process = cli(csv_inputs(tmp_path, observations[:-1], calendar, as_of))
    assert process.returncode == 1
    assert process.stderr == ""
    report = json.loads(process.stdout)
    assert report["result"]["phase"] == "unknown"
    assert report["phase_label"] == "无法判断"
    assert any("missing_close" in reason for reason in report["result"]["reasons"])


def test_cli_bad_input_is_exit_two_without_success_json(tmp_path):
    args = csv_inputs(tmp_path, *trending())
    Path(args[1]).write_text("ts_code,trade_date,close,available_at\n000300.SH,20250106,NaN,2025-01-06T16:00:00+08:00\n")
    process = cli(args)
    assert process.returncode == 2
    assert "finite Decimal" in process.stderr
    assert process.stdout == ""


@pytest.mark.parametrize(("target", "content", "message"), [
    (1, "trade_date,close\n20250106,100\n", "unique headers"),
    (1, "ts_code,trade_date,close,close,available_at\n", "unique headers"),
    (1, "ts_code,trade_date,close,available_at\n000300.SH,20250106,100\n", "row width"),
    (1, "ts_code,trade_date,close,available_at\n000300.SH,20250106,100,2025-01-06T16:00:00+08:00,extra\n", "row width"),
    (1, "ts_code,trade_date,close,available_at\n000300.SH,20250106,,2025-01-06T16:00:00+08:00\n", "cannot be empty"),
    (3, "cal_date,is_open\n20250106,true\n", "is_open must be"),
    (3, "cal_date,is_open\n20250106,1\n20250106,1\n", "duplicate calendar"),
])
def test_cli_rejects_malformed_csv(tmp_path, capsys, target, content, message):
    args = csv_inputs(tmp_path, *trending())
    Path(args[target]).write_text(content, encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    output = capsys.readouterr()
    assert message in output.err
    assert output.out == ""


def test_cli_missing_file_and_naive_as_of_are_errors(tmp_path, capsys):
    args = csv_inputs(tmp_path, *trending())
    args[-1] = "2025-10-17T16:00:00"
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    assert "timezone-aware" in capsys.readouterr().err
    args[1] = str(tmp_path / "missing.csv")
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    assert "No such file" in capsys.readouterr().err


@pytest.fixture
def frozen_clock(monkeypatch):
    class FrozenDateTime(datetime):
        value = None
        calls = 0

        @classmethod
        def now(cls, tz=None):
            cls.calls += 1
            assert tz is CHINA_TZ
            assert cls.value is not None
            return cls.value.astimezone(tz)

    monkeypatch.setattr(runner, "datetime", FrozenDateTime)
    return FrozenDateTime


def test_cli_now_smoke_and_explicit_replay(tmp_path, capsys, monkeypatch, frozen_clock):
    observations, calendar, as_of = trending()
    args = csv_inputs(tmp_path, observations, calendar, as_of)
    frozen_clock.value = as_of.astimezone(timezone.utc)
    read_csv = runner._read_csv

    def read_after_clock_capture(*args):
        assert frozen_clock.calls == 1
        return read_csv(*args)

    monkeypatch.setattr(runner, "_read_csv", read_after_clock_capture)
    assert main(args[:-2] + ["--now"]) == 0
    output = capsys.readouterr()
    assert output.err == ""
    current = json.loads(output.out)
    assert current["as_of_source"] == "system_clock"
    assert current["result"]["as_of"] == as_of.isoformat()
    assert current["result"]["phase"] == "bull"
    assert current["trade_authorized"] is False

    # The captured cutoff, exact same files and --as-of reproduce the diagnosis.
    assert main(args[:-1] + [current["result"]["as_of"]]) == 0
    replay_output = capsys.readouterr()
    assert replay_output.err == ""
    replay = json.loads(replay_output.out)
    assert replay.pop("as_of_source") == "explicit"
    current.pop("as_of_source")
    assert replay == current
    assert frozen_clock.calls == 1  # Explicit replay must never read the clock.


@pytest.mark.parametrize(("offset", "hour", "minute", "phase"), [
    (1, 16, 0, "bull"),   # Saturday: Friday's close, not a new intraday phase.
    (2, 16, 0, "bull"),   # Sunday.
    (3, 10, 0, "bull"),   # Monday intraday.
    (3, 14, 59, "bull"),
    (3, 15, 0, "unknown"),  # Monday closed but its prices are absent: no fallback.
    (3, 16, 0, "unknown"),
])
def test_cli_now_uses_only_latest_completed_session(
    tmp_path, capsys, frozen_clock, offset, hour, minute, phase,
):
    observations, calendar, as_of = trending(count=205)
    friday = as_of.date()
    assert friday.weekday() == 4
    for days, is_open in ((1, False), (2, False), (3, True)):
        calendar[friday + timedelta(days=days)] = is_open
    frozen_clock.value = (as_of + timedelta(days=offset)).replace(hour=hour, minute=minute)
    args = csv_inputs(tmp_path, observations, calendar, as_of)
    assert main(args[:-2] + ["--now"]) == (1 if phase == "unknown" else 0)
    output = capsys.readouterr()
    assert output.err == ""
    report = json.loads(output.out)
    assert report["result"]["phase"] == phase
    decision_date = friday if phase == "bull" else friday + timedelta(days=3)
    assert report["result"]["decision_date"] == decision_date.isoformat()
    assert report["result"]["as_of"] == frozen_clock.value.isoformat()
    assert frozen_clock.calls == 1


def test_cli_now_stale_calendar_is_unknown(tmp_path, capsys, frozen_clock):
    observations, calendar, as_of = trending()
    args = csv_inputs(tmp_path, observations, calendar, as_of)
    frozen_clock.value = as_of + timedelta(days=1)
    assert main(args[:-2] + ["--now"]) == 1
    output = capsys.readouterr()
    assert output.err == ""
    report = json.loads(output.out)
    assert report["result"]["phase"] == "unknown"
    assert report["result"]["decision_date"] is None
    assert report["result"]["reasons"][0].startswith("calendar_not_covered:")
    # The old snapshot still supports its old as-of; it is not current evidence.
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["result"]["phase"] == "bull"


def test_cli_now_unpublished_close_is_unknown(tmp_path, capsys, frozen_clock):
    observations, calendar, as_of = trending()
    frozen_clock.value = as_of.replace(hour=15, minute=0)
    args = csv_inputs(tmp_path, observations, calendar, as_of)
    assert main(args[:-2] + ["--now"]) == 1
    output = capsys.readouterr()
    assert output.err == ""
    report = json.loads(output.out)
    assert report["result"]["phase"] == "unknown"
    assert any("close_not_available" in reason for reason in report["result"]["reasons"])


def test_cli_now_acquisition_time_cannot_backdate_confirmation(tmp_path, capsys, frozen_clock):
    observations, calendar, as_of = trending()
    observations = tuple(replace(item, available_at=as_of) for item in observations)
    frozen_clock.value = as_of
    args = csv_inputs(tmp_path, observations, calendar, as_of)
    assert main(args[:-2] + ["--now"]) == 1
    output = capsys.readouterr()
    assert output.err == ""
    result = json.loads(output.out)["result"]
    assert result["phase"] == "unknown"
    assert result["candidate_phase"] == "bull"
    assert [item["phase"] for item in result["confirmation"]] == ["unknown", "unknown", "bull"]


def test_cli_now_bad_input_is_exit_two(tmp_path, capsys, frozen_clock):
    observations, calendar, as_of = trending()
    frozen_clock.value = as_of
    args = csv_inputs(tmp_path, observations, calendar, as_of)
    Path(args[1]).write_text(
        "ts_code,trade_date,close,available_at\n000300.SH,20250106,NaN,2025-01-06T16:00:00+08:00\n",
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as error:
        main(args[:-2] + ["--now"])
    assert error.value.code == 2
    output = capsys.readouterr()
    assert "finite Decimal" in output.err
    assert output.out == ""


@pytest.mark.parametrize(("mode", "message"), [
    ([], "one of the arguments --as-of --now is required"),
    (["--now", "--as-of", "2025-06-30T16:00:00+08:00"], "not allowed with argument"),
])
def test_cli_time_mode_must_be_explicit_and_exclusive(tmp_path, mode, message):
    process = cli([
        "--prices", str(tmp_path / "unused.csv"),
        "--calendar", str(tmp_path / "unused_calendar.csv"), *mode,
    ])
    assert process.returncode == 2
    assert message in process.stderr
    assert process.stdout == ""
    assert "No such file" not in process.stderr  # Reject mode before reading inputs.


def test_cli_now_real_clock_empty_calendar_fails_closed(tmp_path):
    args = csv_inputs(tmp_path, (), {}, datetime(2025, 1, 1, tzinfo=CHINA_TZ))
    process = cli(args[:-2] + ["--now"])
    assert process.returncode == 1
    assert process.stderr == ""
    report = json.loads(process.stdout)
    assert report["as_of_source"] == "system_clock"
    assert datetime.fromisoformat(report["result"]["as_of"]).utcoffset() == timedelta(hours=8)
    assert report["result"]["phase"] == "unknown"
    assert report["result"]["reasons"][0].startswith("calendar_not_covered:")


def test_cli_help_exposes_now_and_replay_modes():
    process = cli(["--help"])
    assert process.returncode == 0
    assert "--now" in process.stdout
    assert "--as-of" in process.stdout
    assert "不联网" in process.stdout
    assert "--basis" in process.stdout


def snapshot(data, config=DEFAULT_CONFIG):
    observations, calendar, as_of = data
    return evaluate_market_regime(
        observations=observations, calendar=calendar, as_of=as_of, config=config,
        basis=EvaluationBasis.SNAPSHOT,
    )


@pytest.mark.parametrize(("slopes", "phase"), [
    ((1, 1, 1), MarketPhase.BULL),
    ((-1, -1, -1), MarketPhase.BEAR),
    ((1, -1, 0), MarketPhase.TRANSITION),
])
def test_snapshot_reuses_rules_without_claiming_historical_visibility(slopes, phase):
    observations, calendar, as_of = trending(slopes)
    observed_now = tuple(replace(item, available_at=as_of) for item in observations)
    data = observed_now, calendar, as_of
    strict = evaluate(data)
    current = snapshot(data)
    assert strict.phase == MarketPhase.UNKNOWN
    assert strict.basis == EvaluationBasis.HISTORICAL
    assert current.phase == phase
    assert current.basis == EvaluationBasis.SNAPSHOT
    assert current.required_sessions == 202 and current.consecutive_sessions == 3
    assert [item.phase for item in current.confirmation] == [phase] * 3
    assert all(item.available_at == as_of for item in current.indices)
    assert not any(reason.startswith("confirmed_") for reason in current.reasons)
    assert observed_now == data[0]  # No timestamp backdating or input mutation.


def test_snapshot_uses_now_not_fridays_cutoff_during_monday_session():
    observations, calendar, friday = trending(count=205)
    as_of = friday + timedelta(days=3)
    as_of = as_of.replace(hour=10)
    for offset, flag in ((1, False), (2, False), (3, True)):
        calendar[friday.date() + timedelta(days=offset)] = flag
    observed_now = tuple(replace(item, available_at=as_of) for item in observations)
    data = observed_now, calendar, as_of
    assert evaluate(data).phase == MarketPhase.UNKNOWN
    current = snapshot(data)
    assert current.phase == MarketPhase.BULL
    assert current.decision_date == friday.date()
    assert current.as_of == as_of
    assert current.reasons == ("snapshot_pattern_bull: 3 sessions reconstructed at as_of",)


def test_snapshot_never_uses_unobserved_revision_and_keeps_exact_boundary():
    observations, calendar, as_of = trending()
    late = tuple(replace(item, available_at=as_of + timedelta(microseconds=1)) for item in observations)
    before = snapshot((late, calendar, as_of))
    assert before.phase == MarketPhase.UNKNOWN
    assert before.basis == EvaluationBasis.SNAPSHOT
    assert all(reason.startswith("close_not_available:") for reason in before.reasons)
    assert snapshot((late, calendar, as_of + timedelta(microseconds=1))).phase == MarketPhase.BULL


def test_snapshot_ignores_future_prices_and_is_order_timezone_decimal_stable():
    observations, calendar, _ = trending(count=205)
    day = observations[-12].point.trading_date
    as_of = datetime.combine(day, time(16), CHINA_TZ)
    prefix = tuple(item for item in observations if item.point.trading_date <= day)
    expected = snapshot((prefix, calendar, as_of))
    changed = tuple(
        replace(item, point=PricePoint(item.point.trading_date, Decimal("0.01")))
        if item.point.trading_date > day else item for item in observations
    )
    with localcontext() as context:
        context.prec = 3
        actual = snapshot((tuple(reversed(changed)), dict(reversed(tuple(calendar.items()))),
                           as_of.astimezone(timezone.utc)))
    assert actual == expected
    assert expected.phase == MarketPhase.BULL


@pytest.mark.parametrize("issue", ["missing", "gap", "stale", "warmup"])
def test_snapshot_missing_inputs_remain_unknown(issue):
    observations, calendar, as_of = trending(count=201 if issue == "warmup" else 202)
    if issue == "missing":
        observations = observations[:-1]
    elif issue == "gap":
        calendar.pop(sorted(calendar)[3])
    elif issue == "stale":
        calendar.pop(as_of.date())
    result = snapshot((observations, calendar, as_of))
    assert result.phase == MarketPhase.UNKNOWN
    assert result.basis == EvaluationBasis.SNAPSHOT


def test_snapshot_still_requires_three_consecutive_pattern_sessions():
    result = snapshot(market(((1, 2, 3, 4, 5, 3),) * 3), SMALL_CONFIG)
    assert result.phase == MarketPhase.TRANSITION
    assert result.candidate_phase == MarketPhase.BEAR
    assert result.consecutive_sessions == 1
    assert result.reasons == ("snapshot_pattern_pending: bear 1/3",)


@pytest.mark.parametrize("basis", [None, "snapshot", True])
def test_invalid_basis_is_rejected(basis):
    observations, calendar, as_of = trending()
    with pytest.raises(TypeError, match="basis must be EvaluationBasis"):
        evaluate_market_regime(observations=observations, calendar=calendar, as_of=as_of, basis=basis)


def test_cli_snapshot_smoke_now_and_replay(tmp_path, capsys, frozen_clock):
    observations, calendar, as_of = trending()
    observations = tuple(replace(item, available_at=as_of) for item in observations)
    args = csv_inputs(tmp_path, observations, calendar, as_of)
    frozen_clock.value = as_of
    assert main(args[:-2] + ["--basis", "snapshot", "--now"]) == 0
    output = capsys.readouterr()
    assert output.err == ""
    report = json.loads(output.out)
    assert report["strategy"] == "a_share_market_snapshot_v1"
    assert report["historical_confirmation_claimed"] is False
    assert report["trade_authorized"] is False and report["authority"] == "diagnostic_only"
    assert report["result"]["basis"] == "snapshot"
    assert report["result"]["phase"] == "bull"
    assert "非历史点时确认" in report["phase_label"]
    assert len(report["limitations"]) == 3
    assert main(args + ["--basis", "snapshot"]) == 0
    replay = json.loads(capsys.readouterr().out)
    assert replay.pop("as_of_source") == "explicit"
    assert report.pop("as_of_source") == "system_clock"
    assert replay == report
    assert frozen_clock.calls == 1
    assert main(args) == 1  # Default historical semantics have NOT silently changed.
    strict = json.loads(capsys.readouterr().out)
    assert strict["strategy"] == "a_share_market_regime_v1"
    assert strict["result"]["phase"] == "unknown"
    assert "basis" not in strict["result"]  # Preserve historical v1 wire format.


@pytest.mark.parametrize(("issue", "exit_code"), [("missing", 1), ("late", 1), ("invalid", 2)])
def test_cli_snapshot_failure_paths(tmp_path, issue, exit_code):
    observations, calendar, as_of = trending()
    if issue == "missing":
        observations = observations[:-1]
    elif issue == "late":
        observations = tuple(replace(item, available_at=as_of + timedelta(seconds=1)) for item in observations)
    args = csv_inputs(tmp_path, observations, calendar, as_of)
    if issue == "invalid":
        Path(args[1]).write_text("ts_code,trade_date,close,available_at\n000300.SH,20250106,NaN,2025-01-06T16:00:00+08:00\n")
    process = cli(args + ["--basis", "snapshot"])
    assert process.returncode == exit_code
    if exit_code == 2:
        assert process.stdout == "" and "finite Decimal" in process.stderr
    else:
        assert process.stderr == ""
        report = json.loads(process.stdout)
        assert report["result"]["phase"] == "unknown"
        assert report["historical_confirmation_claimed"] is False


def test_cli_snapshot_cannot_feed_stock_gate(tmp_path, capsys):
    with pytest.raises(SystemExit) as error:
        main(["--prices", str(tmp_path / "missing.csv"), "--calendar", str(tmp_path / "missing_calendar.csv"),
              "--as-of", "2026-09-21T10:00:00+08:00", "--basis", "snapshot",
              "--stocks", str(tmp_path / "missing_stocks.csv"), "--sectors", "example"])
    assert error.value.code == 2
    output = capsys.readouterr()
    assert output.out == "" and "cannot be used with --stocks/--sectors" in output.err
    assert "No such file" not in output.err
