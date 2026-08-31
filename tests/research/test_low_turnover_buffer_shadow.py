import csv
from pathlib import Path

import pandas as pd

from experiments.run_low_turnover_buffer import scheduled_selections
from experiments.run_low_turnover_buffer_shadow import FIELDS, update_ledger


def test_scheduled_selections_preserve_top40_holdings_and_replace_rank41():
    sessions = pd.bdate_range("2026-01-05", periods=6)
    rows = []
    for day in sessions:
        for number in range(1, 51):
            score = float(51 - number)
            if day == sessions[-1] and number == 1:
                score = -100.0
            if day == sessions[-1] and number == 21:
                score = 100.0
            rows.append({
                "TradingDay": day,
                "Symbol": f"{number:06d}",
                "practical": True,
                "_score": score,
                "fwd5": 0.01,
            })
    selections = list(scheduled_selections(pd.DataFrame(rows)))

    assert list(selections[0][4]) == [f"{number:06d}" for number in range(1, 21)]
    assert list(selections[1][4]) == [f"{number:06d}" for number in range(2, 22)]


def test_shadow_update_appends_each_frozen_target_once_without_returns(tmp_path: Path):
    ledger = tmp_path / "ledger.csv"
    with ledger.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerow({
            "recorded_cutoff": "2026-08-31",
            "data_version": "old",
            "signal_date": "2026-08-25",
            "record_type": "BASELINE",
            "status": "BASELINE_ONLY",
            "observed_sessions_since_signal": "4",
            "target_holdings": "|".join(f"{number:06d}" for number in range(1, 21)),
            "period_return": "",
            "benchmark_return": "",
            "active_return": "",
            "trade_authorized": "false",
            "notes": "baseline",
        })
    manifest = {
        "shadow_id": "shadow",
        "strategy_id": "a-share-low-turnover-top20-buffer40-v1",
        "trade_authorized": False,
        "parameters": {
            "enter_rank": 20,
            "retain_rank": 40,
            "rebalance_sessions": 5,
            "cost_per_side": 0.0012,
        },
    }
    sessions = list(pd.bdate_range("2026-08-25", "2026-09-02"))
    history = [
        (pd.Timestamp("2026-08-25"), tuple(f"{number:06d}" for number in range(1, 21))),
        (pd.Timestamp("2026-09-01"), tuple(f"{number:06d}" for number in range(2, 22))),
    ]

    first = update_ledger(ledger, manifest, "2026-09-02", "new", sessions, history)
    second = update_ledger(ledger, manifest, "2026-09-02", "new", sessions, history)
    rows = list(csv.DictReader(ledger.open(encoding="utf-8")))

    assert first["appended"] == 1
    assert second["appended"] == 0
    assert len(rows) == 2
    assert rows[-1]["target_holdings"].split("|") == [f"{number:06d}" for number in range(2, 22)]
    assert rows[-1]["period_return"] == ""
    assert rows[-1]["trade_authorized"] == "false"
