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

from experiments.a_share_market_regime import CHINA_TZ, INDEX_CODES, MarketPhase, PublishedIndexClose
from experiments.a_share_risk_state import PricePoint
from experiments.a_share_sector_opportunities import (
    DEFAULT_SCREEN_CONFIG,
    PublishedStockClose,
    StockScreenConfig,
    StockScreenStatus,
    evaluate_sector_opportunities,
)
from experiments.run_a_share_market_regime import main


ROOT = Path(__file__).resolve().parents[2]


def market(slope=1, count=202):
    """Synthetic weekdays only; not a real exchange calendar or market sample."""
    calendar = {}
    indices = []
    day = date(2025, 1, 6)
    for index in range(count):
        while day.weekday() >= 5:
            calendar[day] = False
            day += timedelta(days=1)
        calendar[day] = True
        indices.extend(PublishedIndexClose(
            code, PricePoint(day, Decimal(1000 + slope * index)),
            datetime.combine(day, time(15, 1), CHINA_TZ),
        ) for code in INDEX_CODES)
        day += timedelta(days=1)
    as_of = datetime.combine(day - timedelta(days=1), time(16), CHINA_TZ)
    return tuple(indices), calendar, as_of


def stock(data, instrument="000001.SZ", sector="板块甲", *, drift="0.004", swing="0.025", count=60):
    _, calendar, _ = data
    days = sorted(day for day, is_open in calendar.items() if is_open)[-count:]
    points = []
    close = Decimal(100)
    for index, day in enumerate(days):
        if index:
            close *= 1 + Decimal(drift) + (Decimal(swing) if index % 2 else -Decimal(swing))
        points.append(PublishedStockClose(
            instrument, sector, PricePoint(day, close), Decimal("200000000"), False, False,
            datetime.combine(day, time(15, 2), CHINA_TZ),
        ))
    return tuple(points)


def evaluate(data, stocks, sectors=("板块甲",), config=DEFAULT_SCREEN_CONFIG):
    indices, calendar, as_of = data
    return evaluate_sector_opportunities(
        index_observations=indices, stock_observations=stocks,
        calendar=calendar, as_of=as_of, selected_sectors=sectors, config=config,
    )


def csv_inputs(tmp_path, data, stocks):
    indices, calendar, as_of = data
    prices = tmp_path / "indices.csv"
    calendar_path = tmp_path / "calendar.csv"
    stock_path = tmp_path / "stocks.csv"
    tables = (
        (prices, ("ts_code", "trade_date", "close", "available_at"),
         [(row.instrument, row.point.trading_date.isoformat(), str(row.point.close), row.available_at.isoformat()) for row in indices]),
        (calendar_path, ("cal_date", "is_open"), [(day.isoformat(), int(flag)) for day, flag in calendar.items()]),
        (stock_path, ("ts_code", "sector", "trade_date", "adj_close", "amount_cny", "is_st", "is_suspended", "available_at"),
         [(row.instrument, row.sector, row.point.trading_date.isoformat(), str(row.point.close), str(row.amount_cny),
           int(row.is_st), int(row.is_suspended), row.available_at.isoformat()) for row in stocks]),
    )
    for path, header, rows in tables:
        with path.open("w", newline="", encoding="utf-8") as output:
            writer = csv.writer(output)
            writer.writerow(header)
            writer.writerows(rows)
    return ["--prices", str(prices), "--calendar", str(calendar_path), "--as-of", as_of.isoformat(),
            "--stocks", str(stock_path), "--sectors", "板块甲"]


def cli(args):
    return subprocess.run(
        [sys.executable, "-m", "experiments.run_a_share_market_regime", *args],
        cwd=ROOT, text=True, capture_output=True, check=False, timeout=10,
    )


def test_cli_sector_smoke_and_replay(tmp_path):
    data = market()
    stocks = stock(data) + stock(data, "000002.SZ", swing="0.001") + stock(data, "600001.SH", "板块乙")
    args = csv_inputs(tmp_path, data, stocks)
    process = cli(args)
    assert process.returncode == 0, process.stderr
    assert process.stderr == ""
    payload = json.loads(process.stdout)
    assert payload["authority"] == "diagnostic_only"
    assert payload["trade_authorized"] is False
    assert payload["result"]["phase"] == "bull"
    screen = payload["screening"]
    assert screen["strategy"] == "a_share_sector_opportunities_v1"
    assert screen["complete"] is True
    assert screen["watchlist"] == ["000001.SZ"]
    assert screen["selected_sectors"] == ["板块甲"]
    assert len(screen["limitations"]) == 3
    assert [item["instrument"] for item in screen["stocks"]] == ["000001.SZ", "000002.SZ"]
    assert screen["stocks"][1]["reasons"] == ["volatility_too_low"]
    assert payload["sources"]["stocks"]["sha256"] == hashlib.sha256(Path(args[7]).read_bytes()).hexdigest()
    assert cli(args).stdout == process.stdout


def test_cli_sector_incomplete_is_exit_one(tmp_path):
    data = market()
    process = cli(csv_inputs(tmp_path, data, stock(data)[:-1]))
    assert process.returncode == 1, process.stderr
    assert process.stderr == ""
    screen = json.loads(process.stdout)["screening"]
    assert screen["complete"] is False
    assert screen["watchlist"] == []
    assert screen["stocks"][0]["status"] == "unresolved"
    assert screen["stocks"][0]["reasons"] == ["current_close_missing_or_unavailable"]


def test_cli_bad_stock_input_is_exit_two(tmp_path):
    data = market()
    args = csv_inputs(tmp_path, data, stock(data))
    path = Path(args[7])
    path.write_text(path.read_text().replace(",0,0,", ",false,0,"), encoding="utf-8")
    process = cli(args)
    assert process.returncode == 2
    assert process.stdout == ""
    assert "is_st must be 0 or 1" in process.stderr


def test_defaults_and_indicator_definitions():
    assert DEFAULT_SCREEN_CONFIG.required_sessions == 60
    data = market()
    rows = stock(data, count=3)
    rows = tuple(replace(row, point=PricePoint(row.point.trading_date, Decimal(value)))
                 for row, value in zip(rows, (100, 110, 99), strict=True))
    config = StockScreenConfig(lookback=2, trend_window=3, min_annualized_volatility=Decimal(0),
                               max_annualized_volatility=Decimal(10))
    decision = evaluate(data, rows, config=config).stocks[0]
    metrics = decision.metrics
    assert metrics is not None
    assert metrics.adjusted_close == 99
    assert metrics.moving_average == 103
    assert metrics.momentum == Decimal("-0.01")
    assert abs(metrics.annualized_volatility - Decimal("5.04").sqrt()) < Decimal("1e-25")
    assert metrics.average_amount_cny == Decimal("200000000")
    assert metrics.previous_high == 110
    assert metrics.available_at == rows[-1].available_at
    assert decision.reasons == ("uptrend_not_confirmed",)


@pytest.mark.parametrize(("slope", "phase", "status", "reason"), [
    (1, MarketPhase.BULL, StockScreenStatus.WATCH, "bull_trend_watch_only"),
    (0, MarketPhase.TRANSITION, StockScreenStatus.WATCH, "transition_breakout_watch_only"),
    (-1, MarketPhase.BEAR, StockScreenStatus.BLOCKED, "bear_market"),
])
def test_market_gate(slope, phase, status, reason):
    data = market(slope)
    result = evaluate(data, stock(data))
    assert result.market.phase is phase
    assert result.stocks[0].status is status
    assert result.stocks[0].reasons == (reason,)
    assert result.complete is True  # A known bear-market veto is not a missing-data error.
    assert result.watchlist == (("000001.SZ",) if status is StockScreenStatus.WATCH else ())


def test_transition_requires_strict_prior_high_breakout_not_just_uptrend():
    data = market(0)
    rows = stock(data)
    high = max(row.point.close for row in rows[-21:-1])
    rows = rows[:-1] + (replace(rows[-1], point=PricePoint(rows[-1].point.trading_date, high)),)
    result = evaluate(data, rows)
    assert result.stocks[0].metrics is not None
    assert result.stocks[0].metrics.momentum > 0
    assert result.stocks[0].metrics.adjusted_close == result.stocks[0].metrics.previous_high
    assert result.watchlist == ()
    assert result.stocks[0].reasons == ("transition_requires_breakout",)
    assert evaluate(market(1), rows).watchlist == ("000001.SZ",)


def test_unknown_market_never_produces_a_watchlist():
    data = market()
    indices, calendar, as_of = data
    result = evaluate((indices[:-1], calendar, as_of), stock(data))
    assert result.market.phase is MarketPhase.UNKNOWN
    assert result.watchlist == ()
    assert result.complete is False
    assert result.stocks[0].status is StockScreenStatus.UNRESOLVED
    assert result.stocks[0].reasons == ("market_unknown",)


@pytest.mark.parametrize(("changes", "reason"), [
    ({"swing": "0.001"}, "volatility_too_low"),
    ({"swing": "0.075"}, "volatility_too_high"),
    ({"drift": "-0.004"}, "uptrend_not_confirmed"),
])
def test_price_filters(changes, reason):
    data = market()
    result = evaluate(data, stock(data, **changes))
    assert result.watchlist == ()
    assert result.stocks[0].status is StockScreenStatus.REJECTED
    assert reason in result.stocks[0].reasons


def test_liquidity_filter_and_inclusive_thresholds():
    data = market()
    rows = stock(data)
    first = evaluate(data, rows).stocks[0].metrics
    assert first is not None
    config = replace(DEFAULT_SCREEN_CONFIG, min_annualized_volatility=first.annualized_volatility,
                     max_annualized_volatility=first.annualized_volatility,
                     min_average_amount_cny=first.average_amount_cny)
    assert evaluate(data, rows, config=config).watchlist == ("000001.SZ",)
    thin = tuple(replace(row, amount_cny=Decimal("99999999")) for row in rows)
    result = evaluate(data, thin)
    assert result.watchlist == ()
    assert result.stocks[0].reasons == ("insufficient_liquidity",)


def test_equal_ma_or_zero_momentum_cannot_pass_trend_gate():
    data = market()
    rows = stock(data)
    result = evaluate(data, rows, config=replace(DEFAULT_SCREEN_CONFIG, trend_window=1))
    assert result.stocks[0].reasons == ("uptrend_not_confirmed",)
    # Flat price is neither an uptrend nor high volatility, even when volatility is allowed to be zero.
    flat = stock(data, drift="0", swing="0")
    result = evaluate(data, flat, config=replace(DEFAULT_SCREEN_CONFIG, min_annualized_volatility=Decimal(0)))
    assert result.watchlist == ()
    assert result.stocks[0].reasons == ("uptrend_not_confirmed",)


@pytest.mark.parametrize(("flag", "reason"), [("is_st", "st_stock"), ("is_suspended", "suspended")])
def test_current_stock_status_exclusions(flag, reason):
    data = market()
    rows = stock(data)
    rows = rows[:-1] + (replace(rows[-1], **{flag: True}),)
    result = evaluate(data, rows)
    assert result.watchlist == ()
    assert result.stocks[0].status is StockScreenStatus.REJECTED
    assert result.stocks[0].reasons == (reason,)
    assert result.stocks[0].metrics is None


@pytest.mark.parametrize("problem", ["missing_first", "missing_internal", "late_internal", "suspended", "zero_amount"])
def test_history_is_not_forward_filled_or_shortened(problem):
    data = market()
    rows = list(stock(data))
    if problem == "missing_first":
        rows.pop(0)
    elif problem == "missing_internal":
        rows.pop(30)
    elif problem == "late_internal":
        rows[30] = replace(rows[30], available_at=data[2] + timedelta(seconds=1))
    elif problem == "suspended":
        rows[30] = replace(rows[30], is_suspended=True)
    else:
        rows[30] = replace(rows[30], amount_cny=Decimal(0))
    result = evaluate(data, tuple(rows))
    assert result.watchlist == ()
    assert result.complete is False
    assert result.stocks[0].status is StockScreenStatus.UNRESOLVED
    assert result.stocks[0].metrics is None


def test_unavailable_latest_row_cannot_leak_sector_status_or_prices():
    data = market()
    rows = stock(data)
    delayed = replace(rows[-1], available_at=data[2] + timedelta(hours=1))
    expected = evaluate(data, rows[:-1] + (delayed,))
    poisoned = replace(delayed, sector="板块乙", is_st=True, point=PricePoint(delayed.point.trading_date, Decimal("999999")))
    assert evaluate(data, rows[:-1] + (poisoned,)) == expected
    assert expected.watchlist == ()
    assert expected.stocks[0].reasons == ("current_close_missing_or_unavailable",)


def test_entirely_unavailable_stock_is_unresolved_without_inventing_membership():
    data = market()
    invisible = tuple(replace(row, available_at=data[2] + timedelta(hours=1))
                      for row in stock(data, "000002.SZ", "板块乙"))
    result = evaluate(data, stock(data) + invisible)
    assert result.complete is False
    assert result.watchlist == ("000001.SZ",)
    assert result.stocks[1].status is StockScreenStatus.UNRESOLVED
    assert result.stocks[1].sector is None
    assert result.stocks[1].reasons == ("sector_and_price_not_available",)


def test_exact_row_availability_boundary():
    data = market()
    rows = stock(data)
    indices, calendar, as_of = data
    before = evaluate((indices, calendar, as_of.replace(hour=15, minute=1)), rows)
    assert before.watchlist == ()
    assert before.complete is False
    at_boundary = evaluate((indices, calendar, rows[-1].available_at), rows)
    assert at_boundary.watchlist == ("000001.SZ",)


def test_future_rows_and_future_only_instruments_cannot_affect_past_result():
    indices, calendar, _ = market(count=205)
    day = indices[-12].point.trading_date  # 202nd session.
    as_of = datetime.combine(day, time(16), CHINA_TZ)
    data = indices, calendar, as_of
    rows = stock(data, count=65)
    prefix = tuple(row for row in rows if row.point.trading_date <= day)
    past_indices = tuple(row for row in indices if row.point.trading_date <= day)
    expected = evaluate((past_indices, {d: flag for d, flag in calendar.items() if d <= day}, as_of), prefix)
    future = tuple(replace(row, sector="板块乙", is_st=True,
                           point=PricePoint(row.point.trading_date, Decimal("999999")))
                   if row.point.trading_date > day else row for row in rows)
    future_only = tuple(replace(row, instrument="000002.SZ") for row in rows if row.point.trading_date > day)
    assert expected.watchlist == ("000001.SZ",)
    assert evaluate(data, future + future_only) == expected


def test_sector_membership_uses_the_current_visible_row():
    data = market()
    rows = stock(data)
    moved = rows[:-1] + (replace(rows[-1], sector="板块乙"),)
    assert evaluate(data, moved).watchlist == ()
    result = evaluate(data, moved, sectors=("板块乙",))
    assert result.watchlist == ("000001.SZ",)
    assert result.stocks[0].sector == "板块乙"


def test_only_explicit_sectors_are_screened_and_absent_sectors_are_unresolved():
    data = market()
    rows = stock(data) + stock(data, "600001.SH", "板块乙")
    assert len(evaluate(data, rows).stocks) == 1
    result = evaluate(data, rows, sectors=("板块乙", "板块甲"))
    assert result.selected_sectors == ("板块乙", "板块甲")  # Canonical lexicographic order.
    assert set(result.watchlist) == {"000001.SZ", "600001.SH"}
    assert result.complete is True
    result = evaluate(data, rows, sectors=("板块甲", "不存在的板块"))
    assert result.unresolved_sectors == ("不存在的板块",)
    assert result.complete is False
    assert result.watchlist == ("000001.SZ",)  # Explicitly partial, never a complete-sector claim.
    empty = evaluate(data, ())
    assert empty.complete is False
    assert empty.unresolved_sectors == ("板块甲",)
    assert empty.watchlist == ()


def test_order_timezone_context_replay_and_momentum_ranking_are_deterministic():
    data = market()
    rows = (stock(data, "000001.SZ", drift="0.0040001")
            + stock(data, "000002.SZ", drift="0.0040002")
            + stock(data, "600001.SH", drift="0.0040001"))
    expected = evaluate(data, rows)
    assert expected.watchlist == ("000002.SZ", "000001.SZ", "600001.SH")
    indices, calendar, as_of = data
    reordered = tuple(reversed(indices)), dict(reversed(tuple(calendar.items()))), as_of.astimezone(timezone.utc)
    assert evaluate(reordered, tuple(reversed(rows))) == expected
    with localcontext() as context:
        context.prec = 3
        assert evaluate(data, rows) == expected


def test_weekend_and_intraday_use_previous_completed_session():
    data = market(count=205)
    indices, calendar, as_of = data
    assert as_of.weekday() == 4
    rows = stock(data)
    for offset in (1, 2, 3):
        calendar[as_of.date() + timedelta(days=offset)] = offset == 3
    for cutoff in (as_of + timedelta(days=2), (as_of + timedelta(days=3)).replace(hour=10)):
        result = evaluate((indices, calendar, cutoff), rows)
        assert result.market.decision_date == as_of.date()
        assert result.watchlist == ("000001.SZ",)
    result = evaluate((indices, calendar, as_of + timedelta(days=3)), rows)
    assert result.watchlist == ()
    assert result.complete is False


def test_calendar_gaps_and_long_stock_window_fail_closed():
    data = market()
    indices, calendar, as_of = data
    rows = stock(data)
    calendar.pop(as_of.date())
    result = evaluate((indices, calendar, as_of), rows)
    assert result.market.phase is MarketPhase.UNKNOWN
    assert result.watchlist == ()
    assert result.complete is False
    result = evaluate(market(), rows, config=replace(DEFAULT_SCREEN_CONFIG, trend_window=203))
    assert result.stocks[0].reasons == ("insufficient_calendar_history",)


def test_duplicate_and_closed_session_stock_data_are_rejected():
    data = market()
    rows = stock(data)
    with pytest.raises(ValueError, match="duplicate stock/date"):
        evaluate(data, rows + rows[:1])
    closed = next(day for day, is_open in data[1].items() if not is_open)
    invalid = replace(rows[0], point=PricePoint(closed, Decimal(100)),
                      available_at=datetime.combine(closed, time(16), CHINA_TZ))
    with pytest.raises(ValueError, match="closed session"):
        evaluate(data, rows + (invalid,))


@pytest.mark.parametrize("changes", [
    {"instrument": "ABC.SH"}, {"instrument": "000300.SH"}, {"instrument": "510300.SH"},
    {"instrument": "399001.SZ"}, {"instrument": "159901.SZ"}, {"instrument": "200001.SZ"},
    {"sector": ""}, {"sector": " 板块甲"}, {"point": None},
    {"amount_cny": Decimal("NaN")}, {"amount_cny": Decimal("Infinity")},
    {"amount_cny": Decimal(-1)}, {"amount_cny": 1.5}, {"is_st": "0"}, {"is_suspended": 0},
    {"available_at": datetime(2025, 1, 1)},
    {"available_at": datetime(2025, 1, 1, 14, tzinfo=CHINA_TZ)},
])
def test_malformed_stock_inputs_are_rejected(changes):
    with pytest.raises((TypeError, ValueError)):
        replace(stock(market())[0], **changes)


@pytest.mark.parametrize("changes", [
    {"lookback": 1}, {"lookback": True}, {"lookback": 2.5}, {"trend_window": 0},
    {"min_annualized_volatility": Decimal("NaN")}, {"max_annualized_volatility": Decimal("Infinity")},
    {"min_annualized_volatility": Decimal("0.9")}, {"max_annualized_volatility": Decimal(0)},
    {"min_average_amount_cny": Decimal(-1)}, {"min_average_amount_cny": 1.0},
])
def test_malformed_config_is_rejected(changes):
    with pytest.raises(ValueError):
        StockScreenConfig(**changes)


@pytest.mark.parametrize("sectors", [(), ("",), (" 板块甲",), ("板块甲", "板块甲"), ["板块甲"], (1,)])
def test_sector_selection_must_be_explicit_and_unambiguous(sectors):
    data = market()
    with pytest.raises(ValueError, match="selected_sectors"):
        evaluate(data, stock(data), sectors=sectors)


def test_api_rejects_invalid_config_or_stock_container():
    data = market()
    rows = stock(data)
    with pytest.raises(TypeError, match="config"):
        evaluate(data, rows, config=None)  # type: ignore[arg-type]  # Deliberately malformed API input.
    with pytest.raises(TypeError, match="stock_observations"):
        evaluate(data, list(rows))
    with pytest.raises(TypeError, match="stock_observations"):
        evaluate(data, (rows[0].point,))


@pytest.mark.parametrize("missing", ["stocks", "sectors"])
def test_cli_requires_stock_file_and_sector_selection_together(tmp_path, capsys, missing):
    data = market()
    args = csv_inputs(tmp_path, data, stock(data))
    if missing == "stocks":
        del args[6:8]
    else:
        del args[8:]
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "must be supplied together" in output.err


def test_cli_absent_sector_and_duplicate_stocks(tmp_path, capsys):
    data = market()
    rows = stock(data)
    args = csv_inputs(tmp_path, data, rows)
    args[-1] = "未知板块"
    assert main(args) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["screening"]["unresolved_sectors"] == ["未知板块"]
    assert payload["screening"]["watchlist"] == []
    args = csv_inputs(tmp_path, data, rows + rows[:1])
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "duplicate stock/date" in output.err
