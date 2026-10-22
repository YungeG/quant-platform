import numpy as np
import pandas as pd
import pytest

from experiments.l2_three_stock_quote_stress_v2 import (
    aggregate, daily_space, quote_cost_rows, quote_space,
)


def quote_fixture():
    ask = np.array([10.01, 10.03, 10.04, 10.06, 10.10])
    bid = ask - .01
    q = pd.DataFrame({"day": "20261016", "symbol": "688137.SH", "ms": [34259000, 34262000, 34265000, 34319000, 34559000], "valid": True, "ask1": ask, "bid1": bid, "mid": (ask + bid) / 2})
    grid = pd.DataFrame({"day": ["20261016"], "symbol": ["688137.SH"], "grid_ms": [34260000], "imbalance10": [.5]})
    return q, grid


def test_delay_changes_entry_not_signal_or_exit_timestamp():
    q, grid = quote_fixture()
    immediate = quote_space(q, grid, 0, 60000).iloc[0]
    delayed = quote_space(q, grid, 3000, 60000).iloc[0]
    assert delayed.entry_quote_ms == 34262000
    assert delayed.exit_quote_ms == immediate.exit_quote_ms == 34319000
    assert delayed.imbalance10 == immediate.imbalance10 == .5
    assert delayed.buy_quote_space_bps == pytest.approx((10.05 / 10.03 - 1) * 10000)
    assert delayed.sell_quote_space_bps == pytest.approx((10.02 / 10.06 - 1) * 10000)
    assert delayed.buy_quote_space_bps < immediate.buy_quote_space_bps


def test_delayed_invalid_quote_is_not_skipped_for_older_good_book():
    q, grid = quote_fixture()
    q.loc[2, "valid"] = False
    assert len(quote_space(q, grid, 0, 60000)) == 1
    assert len(quote_space(q, grid, 3000, 60000)) == 1
    assert quote_space(q, grid, 6000, 60000).empty


def test_flat_market_has_negative_crossing_space_not_zero_profit():
    q, grid = quote_fixture()
    q["ask1"] = 10.01
    q["bid1"] = 10.0
    q["mid"] = 10.005
    row = quote_space(q, grid, 3000, 60000).iloc[0]
    assert row.delayed_mid_change_bps == pytest.approx(0)
    assert row.buy_quote_space_bps == pytest.approx((10 / 10.01 - 1) * 10000)
    assert row.sell_quote_space_bps < 0


def test_cost_coverage_denominator_keeps_one_sided_snapshots():
    q = pd.DataFrame({"day": ["20261016"] * 2, "symbol": ["688137.SH"] * 2, "valid": [True, False], "mid": [10, 10]})
    arrays = {"ask": np.array([[10.001], [10.001]]), "bid": np.array([[9.999], [9.999]]), "aq": np.array([[1000000], [1000000]]), "bq": np.array([[1000000], [1000000]])}
    rows = quote_cost_rows(q, arrays)
    assert len(rows) == 10
    assert all(row["priceable_share_all_snapshots"] == .5 for row in rows)
    assert all(not row["daily_guard_5_pass"] for row in rows)
    assert all(row["cost_le_5_share_all_snapshots"] == .5 for row in rows)


def test_daily_groups_require_five_and_aggregate_days_equally():
    q, grid = quote_fixture()
    obs = quote_space(q, grid, 3000, 60000)
    assert daily_space(pd.concat([obs] * 4)) == []
    first = daily_space(pd.concat([obs] * 5))[0]
    second = {**first, "day": "20261015", "n": 1000, "quote_space_mean_bps": -20.0}
    first["quote_space_mean_bps"] = 10.0
    costs = pd.DataFrame(quote_cost_rows(pd.DataFrame({"day": ["20261016"], "symbol": ["688137.SH"], "valid": [True], "mid": [10]}), {"ask": np.array([[10.001]]), "bid": np.array([[9.999]]), "aq": np.array([[1000000]]), "bq": np.array([[1000000]])}))
    result = aggregate(pd.DataFrame([first, second]), costs)
    assert result["quote_space"][0]["quote_space_mean_bps"] == pytest.approx(-5)
    assert result["quote_space"][0]["n"] == 1005
