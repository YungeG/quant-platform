from experiments.lowturn_livermore import Bar
from experiments.quarterly_portfolio import (
    BasketConfig,
    select_industry_balanced,
    simulate_basket,
)


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


def simulate(dates, prices, targets, *, target_count=2, retry=3):
    def lookup(date, symbol):
        return prices.get((date, symbol))

    return simulate_basket(
        dates,
        lookup,
        targets,
        BasketConfig(name="test", target_count=target_count, buy_retry_days=retry),
    )


def test_industry_balanced_selection_enforces_cap():
    rows = [
        ("A", "bank", 0.10, 0.10),
        ("B", "bank", 0.11, 0.20),
        ("C", "bank", 0.12, 0.30),
        ("D", "utility", 0.13, 0.15),
    ]
    assert select_industry_balanced(rows, count=3, industry_cap=2) == ["A", "D", "B"]


def test_target_is_bought_at_next_open_in_board_lots():
    dates = ["d0", "d1", "d2"]
    prices = {(day, "A"): bar(10) for day in dates}
    result = simulate(dates, prices, {"d0": ["A"]}, target_count=1)
    buy = result.trades[0]
    assert buy["date"] == "d1"
    assert buy["raw_shares"] == 39_900


def test_unchanged_target_is_not_rebalanced():
    dates = ["d0", "d1", "d2", "d3"]
    prices = {(day, "A"): bar(10) for day in dates}
    result = simulate(dates, prices, {"d0": ["A"], "d2": ["A"]}, target_count=1)
    assert [trade["side"] for trade in result.trades] == ["BUY"]


def test_dropped_name_is_sold_before_replacement_is_bought():
    dates = ["d0", "d1", "d2", "d3", "d4"]
    prices = {
        **{(day, "A"): bar(10) for day in dates},
        **{(day, "B"): bar(20) for day in dates},
    }
    result = simulate(
        dates,
        prices,
        {"d0": ["A"], "d2": ["B"]},
        target_count=1,
    )
    trades_d3 = [trade["side"] for trade in result.trades if trade["date"] == "d3"]
    assert trades_d3 == ["SELL", "BUY"]


def test_blocked_sell_is_delayed():
    dates = ["d0", "d1", "d2", "d3", "d4"]
    prices = {
        ("d0", "A"): bar(10),
        ("d1", "A"): bar(10),
        ("d2", "A"): bar(10),
        ("d3", "A"): bar(9, pct=-10, flat=True),
        ("d4", "A"): bar(8.8),
    }
    result = simulate(dates, prices, {"d0": ["A"], "d2": []}, target_count=1)
    sell = [trade for trade in result.trades if trade["side"] == "SELL"][0]
    assert sell["date"] == "d4"
    assert result.blocked_sells == 1


def test_blocked_buy_retries_three_days():
    dates = ["d0", "d1", "d2", "d3", "d4"]
    prices = {
        ("d0", "A"): bar(10),
        ("d1", "A"): bar(11, pct=10, flat=True),
        ("d2", "A"): bar(12.1, pct=10, flat=True),
        ("d3", "A"): bar(12),
        ("d4", "A"): bar(12),
    }
    result = simulate(dates, prices, {"d0": ["A"]}, target_count=1)
    buy = [trade for trade in result.trades if trade["side"] == "BUY"][0]
    assert buy["date"] == "d3"
    assert result.blocked_buys == 2


def test_too_expensive_stock_remains_cash():
    dates = ["d0", "d1", "d2"]
    prices = {(day, "A"): bar(5_000) for day in dates}
    result = simulate(dates, prices, {"d0": ["A"]}, target_count=30)
    assert not result.trades
    assert result.lot_failures == 1
    assert result.position_count[-1] == 0
