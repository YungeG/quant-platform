import json

import pandas as pd

from experiments.run_early_reporting_peer_diffusion import COST, build_signals, evaluate_stock_arm


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
