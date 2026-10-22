"""Regression tests for post-hoc statistics, not a fill/PnL simulator."""
import zlib

import numpy as np
import pandas as pd
import pytest

from experiments.l2_three_stock_microstructure_v1 import (
    analyze_day,
    continuous,
    displayed_cost,
    event_window_sum,
    hhmmssmmm_to_ms,
    load_member,
    ordered_side,
    strict_asof,
    summarize,
)


def test_time_and_sessions_exclude_lunch_and_closing_auction():
    raw = np.array([93000000, 113000000, 130000000, 145700000])
    ms = hhmmssmmm_to_ms(raw)
    assert ms.tolist() == [34200000, 41400000, 46800000, 53820000]
    assert continuous(ms).tolist() == [True, False, True, False]
    with pytest.raises(ValueError):
        hhmmssmmm_to_ms(np.array([96000000]))


def test_events_exclude_signal_timestamp_and_include_window_start():
    t = np.array([0, 30000, 60000, 90000])
    result = event_window_sum(t, np.array([1, 2, 4, 8]), np.array([60000, 90000]))
    assert result.tolist() == [3, 6]
    with pytest.raises(ValueError):
        event_window_sum(t[::-1], np.ones(4), np.array([60000]))


def test_asof_is_strict_and_rejects_missing_or_stale_quotes():
    t = np.array([1000, 2000, 3000])
    indices, valid = strict_asof(t, np.array([1000, 2000, 3001, 20000]))
    assert indices.tolist() == [0, 0, 2, 2]
    assert valid.tolist() == [False, True, True, False]


def test_book_curve_walks_levels_and_does_not_invent_depth():
    ask = np.array([[10.2, 10.4], [10.2, 10.4]])
    qty = np.array([[100, 100], [100, 100]])
    mid = np.array([10.1, 10.1])
    result = displayed_cost(ask, qty, mid, 2000, "buy")
    expected = (2000 / (100 + 980 / 10.4) / 10.1 - 1) * 10000
    assert result == pytest.approx([expected, expected])
    assert np.isnan(displayed_cost(ask, qty, mid, 3000, "buy")).all()
    bid = np.array([[10, 9.9]])
    assert displayed_cost(bid, np.array([[100, 100]]), mid[:1], 500, "sell")[0] == pytest.approx((1 - 10 / 10.1) * 10000)
    with pytest.raises(ValueError):
        displayed_cost(ask, qty, mid, 100, "unknown")


def test_depth_order_rejects_positive_levels_after_gaps():
    assert ordered_side(np.array([[10, 10.1, 0], [10, 0, 10.1], [10.1, 10, 0]]), "buy").tolist() == [True, False, False]
    assert ordered_side(np.array([[10, 9.9, 0]]), "sell").tolist() == [True]


def test_raw_decode_preserves_provenance_and_rejects_corruption(tmp_path):
    text = "万得代码,交易所代码,自然日,时间,成交编号,成交代码,委托代码,BS标志,成交价格,成交数量,叫卖序号,叫买序号,\n688655.SH,688655,20260930,92500000,1,\x00, ,B,100000,100,1,2,\n"
    raw = text.encode("gb18030")
    path = tmp_path / "trade.csv"
    path.write_bytes(raw)
    meta = {"bytes": len(raw), "crc32": f"{zlib.crc32(raw) & 0xffffffff:08X}"}
    frame, detail = load_member(path, meta, "20260930", "688655.SH", "逐笔成交.csv")
    assert detail["nul_bytes"] == 1
    assert frame.iloc[0]["成交代码"] == ""
    assert frame.iloc[0]["BS标志"] == "B"
    with pytest.raises(ValueError, match="Wrong date"):
        load_member(path, meta, "20261016", "688655.SH", "逐笔成交.csv")
    path.write_bytes(raw[:-1] + b" ")
    with pytest.raises(ValueError, match="CRC"):
        load_member(path, meta, "20260930", "688655.SH", "逐笔成交.csv")


def test_effects_are_equal_day_weighted_not_trade_weighted():
    symbol = "688655.SH"
    days = pd.DataFrame([{"day": day, "symbol": symbol, "quote_rows": 100, "trade_rows": 100, "order_rows": 100, "continuous_quotes": 100, "invalid_quotes": 0, "volume_matches": True, "trade_count_matches": True, "volume_gap_shares": 0, "trade_count_gap": 0, "expected_volume_shares": 100, "expected_trade_count": 100} for day in ("20260901", "20260902")])
    observations = []
    for day, high_n, effect in (("20260901", 5, 10), ("20260902", 1000, -20)):
        for sign, n in ((1, high_n), (-1, 5)):
            observations.extend([{"day": day, "symbol": symbol, "imbalance10": sign, "flow60": sign, "ret1_bps": effect if sign > 0 else 0, "ret5_bps": effect if sign > 0 else 0, "threshold_ready": True, "thin": False, "wide": False, "cancel_high": False, "crossfile_verified": True}] * n)
    grids = pd.DataFrame(observations)
    periods = pd.DataFrame([{"day": "20260901", "symbol": symbol, "period": "09:30-10:00", "quotes": 100, "spread_median_bps": 1}])
    summary = summarize(days, grids, periods)[symbol]
    effect = summary["signals"][0]
    assert effect["valid_days"] == 2
    assert effect["daily_difference_mean_bps"] == pytest.approx(-5)
    assert effect["first_half_bps"] == pytest.approx(10)
    assert effect["second_half_bps"] == pytest.approx(-20)


def minimal_day_frames():
    times = [34259000, 34319000, 34559000]
    quote = pd.DataFrame({"ms": times, "当日累计成交量": [100] * 3, "成交笔数": [1] * 3})
    for i in range(1, 11):
        quote[f"申卖价{i}"] = [102000 + i * 100, 102000 + i * 100, 0]
        quote[f"申卖量{i}"] = [100, 100, 0]
        quote[f"申买价{i}"] = [100000 - i * 100] * 3
        quote[f"申买量{i}"] = [100] * 3
    order = pd.DataFrame({"ms": [34200000], "委托类型": ["A"], "委托代码": ["B"], "委托数量": [100]})
    trade = pd.DataFrame({"ms": [34200000], "成交价格": [100000], "成交数量": [100], "BS标志": ["B"]})
    return {"行情.csv": quote, "逐笔委托.csv": order, "逐笔成交.csv": trade}


def test_nonfinite_deeper_book_level_fails_closed():
    frames = minimal_day_frames()
    frames["行情.csv"]["申卖价2"] = frames["行情.csv"]["申卖价2"].astype(float)
    frames["行情.csv"].loc[0, "申卖价2"] = np.nan
    with pytest.raises(ValueError, match="Nonfinite"):
        analyze_day("20260901", "688655.SH", frames)


def test_future_endpoint_validity_is_independent_per_horizon():
    _, grid, _, _ = analyze_day("20260901", "688655.SH", minimal_day_frames())
    at_0931 = grid.loc[grid.grid_ms == 34260000].iloc[0]
    assert np.isfinite(at_0931.ret1_bps)
    assert np.isnan(at_0931.ret5_bps)


def test_crossfile_gap_is_explicit_and_never_zero_filled():
    frames = minimal_day_frames()
    frames["行情.csv"].loc[2, "当日累计成交量"] = 110
    day, grid, periods, _ = analyze_day("20260901", "688655.SH", frames)
    assert not day["volume_matches"] and day["volume_gap_shares"] == 10
    assert not grid.crossfile_verified.any()
    summary = summarize(pd.DataFrame([day]), grid, periods)["688655.SH"]
    assert summary["eligible_analysis_days"] == 0
    assert len(summary["excluded_days"]) == 1
    assert summary["signals"][0]["daily_difference_mean_bps"] is None
