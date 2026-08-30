import pytest

from experiments.multi_asset import (
    AssetBar,
    equal_risk_contribution_weights,
    inverse_vol_weights,
    simulate_allocation,
)


def bars(equity, bond):
    dates = list(equity)
    return {
        "equity": {
            date: AssetBar(adj_open=values[0], adj_close=values[1], raw_open=values[0])
            for date, values in equity.items()
        },
        "bond": {
            date: AssetBar(adj_open=bond[date][0], adj_close=bond[date][1], raw_open=bond[date][0])
            for date in dates
        },
    }


def test_inverse_volatility_weights():
    weights = inverse_vol_weights({"equity": 0.20, "bond": 0.05, "gold": 0.10})
    assert weights == pytest.approx({"equity": 1 / 7, "bond": 4 / 7, "gold": 2 / 7})


def test_erc_on_diagonal_covariance_matches_inverse_volatility():
    weights = equal_risk_contribution_weights(
        ["equity", "bond", "gold"],
        [[0.04, 0.0, 0.0], [0.0, 0.0025, 0.0], [0.0, 0.0, 0.01]],
    )
    assert weights == pytest.approx(
        {"equity": 1 / 7, "bond": 4 / 7, "gold": 2 / 7}, rel=1e-6
    )


def test_signal_executes_at_next_open():
    dates = ["d0", "d1", "d2"]
    market = bars(
        {"d0": (10, 10), "d1": (10, 11), "d2": (11, 11)},
        {"d0": (10, 10), "d1": (10, 10), "d2": (10, 10)},
    )
    result = simulate_allocation(
        dates, market, {"d0": {"equity": 1.0, "bond": 0.0}}, cost_rate=0.0
    )
    assert result.nav[0] == 400_000
    assert result.nav[1] == pytest.approx(440_000)


def test_old_holding_receives_overnight_move_before_rebalance():
    dates = ["d0", "d1", "d2"]
    market = bars(
        {"d0": (10, 10), "d1": (10, 10), "d2": (12, 12)},
        {"d0": (10, 10), "d1": (10, 10), "d2": (10, 10)},
    )
    result = simulate_allocation(
        dates,
        market,
        {
            "d0": {"equity": 1.0, "bond": 0.0},
            "d1": {"equity": 0.0, "bond": 1.0},
        },
        cost_rate=0.0,
    )
    assert result.nav[2] == pytest.approx(480_000)
    assert result.weights[2]["bond"] == pytest.approx(1.0)


def test_leverage_creates_negative_cash_and_daily_financing_cost():
    dates = ["d0", "d1", "d2"]
    market = bars(
        {"d0": (10, 10), "d1": (10, 10), "d2": (10, 10)},
        {"d0": (10, 10), "d1": (10, 10), "d2": (10, 10)},
    )
    result = simulate_allocation(
        dates,
        market,
        {"d0": {"equity": 1.5, "bond": 0.0}},
        cost_rate=0.0,
        financing_rate=0.252,
        normalize_targets=False,
    )
    assert result.financing_costs[1] == pytest.approx(200.0)
    assert result.nav[1] == pytest.approx(399_800.0)
    assert result.leverage[1] > 1.5


def test_full_switch_charges_both_sell_and_buy_notional():
    dates = ["d0", "d1", "d2"]
    market = bars(
        {"d0": (10, 10), "d1": (10, 10), "d2": (10, 10)},
        {"d0": (10, 10), "d1": (10, 10), "d2": (10, 10)},
    )
    result = simulate_allocation(
        dates,
        market,
        {
            "d0": {"equity": 1.0, "bond": 0.0},
            "d1": {"equity": 0.0, "bond": 1.0},
        },
        cost_rate=0.001,
    )
    assert result.costs[1] == pytest.approx(400.0)
    assert result.costs[2] == pytest.approx(799.2)
    assert result.turnover[2] == pytest.approx(1.0)
