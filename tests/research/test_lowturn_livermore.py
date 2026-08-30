from experiments.lowturn_livermore import Bar, Candidate, StrategyConfig, simulate


def bar(price, *, close=None, pct=0.0, volume=1_000.0, flat=False):
    close = price if close is None else close
    high = low = close if flat else max(price, close)
    if not flat:
        low = min(price, close)
    return Bar(
        adj_open=float(price),
        adj_close=float(close),
        raw_open=float(price),
        raw_high=float(high),
        raw_low=float(low),
        raw_close=float(close),
        volume=float(volume),
        pct_change=float(pct),
    )


def run(dates, prices, *, config=None):
    def lookup(date, symbol):
        return prices.get((date, symbol))

    return simulate(
        dates,
        lookup,
        {dates[0]: [Candidate("X", 1.0)]},
        {},
        config or StrategyConfig(name="test"),
    )


def test_entry_executes_at_next_open():
    dates = ["d0", "d1", "d2"]
    result = run(dates, {(day, "X"): bar(10) for day in dates})
    buys = [trade for trade in result.trades if trade["side"] == "BUY"]
    assert buys[0]["date"] == "d1"


def test_pyramiding_adds_only_after_profit_thresholds():
    dates = [f"d{i}" for i in range(6)]
    prices = {
        ("d0", "X"): bar(10),
        ("d1", "X"): bar(10, close=10),
        ("d2", "X"): bar(10.4, close=10.6),
        ("d3", "X"): bar(10.7, close=11.1),
        ("d4", "X"): bar(11.0, close=11.2),
        ("d5", "X"): bar(11.2, close=11.3),
    }
    result = run(dates, prices)
    buys = [trade for trade in result.trades if trade["side"] == "BUY"]
    assert [trade["reason"] for trade in buys] == ["entry", "add", "add"]
    assert [trade["date"] for trade in buys] == ["d1", "d3", "d4"]


def test_losing_position_is_stopped_and_never_averaged_down():
    dates = ["d0", "d1", "d2", "d3"]
    prices = {
        ("d0", "X"): bar(10),
        ("d1", "X"): bar(10, close=9),
        ("d2", "X"): bar(8.9, close=8.9),
        ("d3", "X"): bar(9),
    }
    result = run(dates, prices)
    assert [trade["reason"] for trade in result.trades] == ["entry", "hard_stop"]
    assert result.trades[-1]["date"] == "d2"


def test_blocked_buy_retries_three_days_then_expires():
    dates = [f"d{i}" for i in range(5)]
    prices = {
        ("d0", "X"): bar(10),
        ("d1", "X"): bar(11, pct=10, flat=True),
        ("d2", "X"): bar(12.1, pct=10, flat=True),
        ("d3", "X"): bar(13.31, pct=10, flat=True),
        ("d4", "X"): bar(13),
    }
    result = run(dates, prices)
    assert not result.trades
    assert result.blocked_buys == 3
    assert result.expired_buys == 1


def test_blocked_sell_is_retried_until_open():
    dates = ["d0", "d1", "d2", "d3", "d4"]
    prices = {
        ("d0", "X"): bar(10),
        ("d1", "X"): bar(10, close=9),
        ("d2", "X"): bar(8.1, pct=-10, flat=True),
        ("d3", "X"): bar(8.0, close=8.0),
        ("d4", "X"): bar(8.1),
    }
    result = run(dates, prices)
    sells = [trade for trade in result.trades if trade["side"] == "SELL"]
    assert sells[0]["date"] == "d3"
    assert result.blocked_sells == 1


def test_risk_sized_unit_uses_half_percent_nav_risk():
    dates = ["d0", "d1", "d2"]
    prices = {(day, "X"): bar(10) for day in dates}

    def lookup(date, symbol):
        return prices.get((date, symbol))

    result = simulate(
        dates,
        lookup,
        {"d0": [Candidate("X", 1.0, risk_pct=0.08)]},
        {},
        StrategyConfig(name="risk", risk_sized=True, pyramid=False, max_units=1),
    )
    buy = result.trades[0]
    assert buy["notional"] == 25_000


def test_gap_guard_cancels_chased_entry():
    dates = ["d0", "d1", "d2"]
    prices = {"d0": bar(10), "d1": bar(10.5), "d2": bar(10.4)}

    def lookup(date, symbol):
        return prices.get(date)

    result = simulate(
        dates,
        lookup,
        {"d0": [Candidate("X", 1.0, risk_pct=0.08, max_entry_price=10.4)]},
        {},
        StrategyConfig(name="gap", risk_sized=True, buy_retry_days=1),
    )
    assert not result.trades
    assert result.gap_skips == 1


def test_market_watch_blocks_add_until_on():
    dates = ["d0", "d1", "d2", "d3", "d4"]
    prices = {
        "d0": bar(10),
        "d1": bar(10, close=11.1),
        "d2": bar(11.1, close=11.2),
        "d3": bar(11.2, close=12.2),
        "d4": bar(12.2),
    }

    def lookup(date, symbol):
        return prices.get(date)

    result = simulate(
        dates,
        lookup,
        {"d0": [Candidate("X", 1.0, risk_pct=0.10)]},
        {},
        StrategyConfig(name="state", risk_sized=True),
        add_allowed={"d1": False, "d2": True, "d3": True, "d4": True},
    )
    buys = [trade for trade in result.trades if trade["side"] == "BUY"]
    assert [trade["date"] for trade in buys] == ["d1", "d3", "d4"]


def test_r_based_trailing_stop_activates_after_one_r():
    dates = ["d0", "d1", "d2", "d3", "d4"]
    prices = {
        "d0": bar(10),
        "d1": bar(10, close=11.2),
        "d2": bar(11.0, close=9.6),
        "d3": bar(9.5, close=9.5),
        "d4": bar(9.6),
    }

    def lookup(date, symbol):
        return prices.get(date)

    result = simulate(
        dates,
        lookup,
        {"d0": [Candidate("X", 1.0, risk_pct=0.10)]},
        {},
        StrategyConfig(name="trail", risk_sized=True, pyramid=False, max_units=1),
    )
    sells = [trade for trade in result.trades if trade["side"] == "SELL"]
    assert sells[0]["reason"] == "trailing_stop"
    assert sells[0]["date"] == "d3"
