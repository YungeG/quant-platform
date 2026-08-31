import json

import numpy as np
import pandas as pd

from experiments.run_early_reporting_peer_diffusion import (
    COST,
    MAX_EARLY_FRACTION,
    MIN_EARLY_FRACTION,
    MIN_POSITIVE_SHARE,
    MIN_REPORTERS,
    _members_at,
    build_signals,
    evaluate_stock_arm,
)


def _legacy_build_signals(members: pd.DataFrame, announcements: pd.DataFrame) -> pd.DataFrame:
    prior = announcements[["Symbol", "period", "ann_date", "tr_yoy", "netprofit_yoy"]].copy()
    prior["period"] = prior.period + 1
    prior = prior.rename(columns={"ann_date": "prior_ann_date", "tr_yoy": "prior_revenue_yoy", "netprofit_yoy": "prior_profit_yoy"})
    events = announcements.merge(prior, on=["Symbol", "period"], how="left")
    events["revenue_acceleration"] = events.tr_yoy - events.prior_revenue_yoy
    events["profit_acceleration"] = events.netprofit_yoy - events.prior_profit_yoy
    events["positive"] = (events.revenue_acceleration > 0) & (events.profit_acceleration > 0) & (events.prior_ann_date <= events.ann_date)
    rows = []
    emitted = set()
    for (day, period), _ in events.groupby(["ann_date", "period"], sort=True):
        active = _members_at(members, day)
        for industry, industry_members in active.groupby("l1_name", sort=True):
            symbols = set(industry_members.Symbol)
            reported = events[(events.period == period) & (events.ann_date <= day) & events.Symbol.isin(symbols)]
            valid = reported.dropna(subset=["revenue_acceleration", "profit_acceleration"])
            fraction = len(reported) / len(symbols) if symbols else 0.0
            positive_share = float(valid.positive.mean()) if len(valid) else np.nan
            key = (industry, period)
            if key in emitted or len(valid) < MIN_REPORTERS or not MIN_EARLY_FRACTION <= fraction <= MAX_EARLY_FRACTION or not positive_share >= MIN_POSITIVE_SHARE:
                continue
            emitted.add(key)
            rows.append({
                "signal_date": day,
                "report_period": str(period),
                "industry": industry,
                "industry_members": len(symbols),
                "reported_count": len(reported),
                "valid_reporter_count": len(valid),
                "early_fraction": fraction,
                "positive_share": positive_share,
                "median_revenue_acceleration": float(valid.revenue_acceleration.median()),
                "median_profit_acceleration": float(valid.profit_acceleration.median()),
                "reported_symbols": json.dumps(sorted(reported.Symbol.unique())),
                "peer_symbols": json.dumps(sorted(symbols - set(reported.Symbol))),
            })
    return pd.DataFrame(rows)


def test_signal_uses_only_early_unreported_peers_and_requires_positive_acceleration():
    members = pd.DataFrame({
        "ts_code": [f"00000{i}.SZ" for i in range(1, 11)],
        "Symbol": [f"00000{i}" for i in range(1, 11)],
        "name": ["normal"] * 10,
        "l1_name": ["industry"] * 10,
        "in_date": pd.to_datetime(["2020-01-01"] * 10),
        "out_date": pd.to_datetime([None] * 10),
    })
    rows = []
    for number in range(1, 4):
        symbol = f"00000{number}"
        rows.extend([
            {"Symbol": symbol, "ann_date": pd.Timestamp("2024-04-01"), "end_date": pd.Timestamp("2024-03-31"), "period": pd.Period("2024Q1"), "tr_yoy": 20, "netprofit_yoy": 20, "update_flag": 0},
            {"Symbol": symbol, "ann_date": pd.Timestamp("2024-08-01"), "end_date": pd.Timestamp("2024-06-30"), "period": pd.Period("2024Q2"), "tr_yoy": 30, "netprofit_yoy": 30, "update_flag": 0},
        ])
    signals = build_signals(members, pd.DataFrame(rows))
    assert len(signals) == 1
    signal = signals.iloc[0]
    assert signal.reported_count == 3
    assert signal.early_fraction == 0.3
    assert set(json.loads(signal.peer_symbols)) == {f"00000{i}" for i in range(4, 11)}


def test_indexed_signal_builder_matches_legacy_across_periods_days_and_industries():
    symbols = [f"{number:06d}" for number in range(1, 21)]
    members = pd.DataFrame({
        "ts_code": [f"{symbol}.SZ" for symbol in symbols],
        "Symbol": symbols,
        "name": ["normal"] * 20,
        "l1_name": ["alpha"] * 10 + ["beta"] * 10,
        "in_date": pd.to_datetime(["2020-01-01"] * 20),
        "out_date": pd.to_datetime([None] * 20),
    })
    rows = []
    for symbol in ["000001", "000002", "000003", "000011", "000012", "000013", "999999"]:
        rows.append({"Symbol": symbol, "period": pd.Period("2024Q1"), "ann_date": pd.Timestamp("2024-04-01"), "tr_yoy": 10, "netprofit_yoy": 10})
        rows.append({
            "Symbol": symbol,
            "period": pd.Period("2024Q2"),
            "ann_date": pd.Timestamp("2024-07-20" if symbol in {"000001", "000002", "000011", "000012", "999999"} else "2024-07-25"),
            "tr_yoy": 20,
            "netprofit_yoy": 20,
        })
    for symbol in ["000001", "000002", "000003"]:
        rows.append({"Symbol": symbol, "period": pd.Period("2024Q3"), "ann_date": pd.Timestamp("2024-10-20"), "tr_yoy": 25, "netprofit_yoy": 25})
    announcements = pd.DataFrame(rows)

    expected = _legacy_build_signals(members, announcements).reset_index(drop=True)
    actual = build_signals(members, announcements).reset_index(drop=True)

    pd.testing.assert_frame_equal(actual, expected)


def test_stock_arm_indexes_prices_once_without_changing_t_plus_one_return():
    sessions = list(pd.bdate_range("2024-01-01", periods=22))
    prices = pd.DataFrame({
        "Symbol": ["000001"] * len(sessions),
        "TradingDay": sessions,
        "adj_open": [10.0] * len(sessions),
        "adj_close": [12.0] * len(sessions),
    })
    signals = pd.DataFrame([{"signal_date": sessions[0], "peer_symbols": json.dumps(["000001", "missing"])}])

    event = evaluate_stock_arm(signals, prices, sessions).iloc[0]

    assert event.entry_date == sessions[1]
    assert event.eligible_peers == 2
    assert event.priced_peers == 1
    assert event.return_20d == 12.0 / 10.0 - 1 - COST
