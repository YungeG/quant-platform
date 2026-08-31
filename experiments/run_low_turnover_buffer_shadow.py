"""Append frozen V18 target decisions to the forward-only shadow ledger."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

QUANT_REPO = Path("/home/ygguo/agent-projs/quant-claude")
if str(QUANT_REPO) not in sys.path:
    sys.path.insert(0, str(QUANT_REPO))

import pandas as pd

from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from experiments.run_low_turnover_buffer import ANCHOR, COST_PER_SIDE, TOP_N, _prepare, scheduled_selections

FIELDS = (
    "recorded_cutoff",
    "data_version",
    "signal_date",
    "record_type",
    "status",
    "observed_sessions_since_signal",
    "target_holdings",
    "period_return",
    "benchmark_return",
    "active_return",
    "trade_authorized",
    "notes",
)


def update_ledger(
    ledger_path: Path,
    manifest: dict,
    cutoff: str,
    data_version: str,
    sessions: list[pd.Timestamp],
    target_history: list[tuple[pd.Timestamp, tuple[str, ...]]],
) -> dict:
    params = manifest["parameters"]
    if (
        manifest["strategy_id"] != "a-share-low-turnover-top20-buffer40-v1"
        or params["enter_rank"] != TOP_N
        or params["retain_rank"] != 40
        or params["rebalance_sessions"] != ANCHOR
        or params["cost_per_side"] != COST_PER_SIDE
        or manifest["trade_authorized"] is not False
    ):
        raise ValueError("shadow manifest does not match frozen V18")
    with ledger_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or tuple(rows[0]) != FIELDS:
        raise ValueError("shadow ledger schema or baseline is missing")
    last_signal = pd.Timestamp(max(row["signal_date"] for row in rows))
    cutoff_day = pd.Timestamp(cutoff)
    appended = 0
    for day, target in target_history:
        if day <= last_signal or day > cutoff_day:
            continue
        rows.append({
            "recorded_cutoff": cutoff,
            "data_version": data_version,
            "signal_date": str(day.date()),
            "record_type": "TARGET",
            "status": "TARGET_RECORDED",
            "observed_sessions_since_signal": str(sum(session > day for session in sessions)),
            "target_holdings": "|".join(target),
            "period_return": "",
            "benchmark_return": "",
            "active_return": "",
            "trade_authorized": "false",
            "notes": "Frozen target only; formal order execution remains capability-blocked",
        })
        last_signal = day
        appended += 1
    if appended:
        with ledger_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    return {
        "shadow_id": manifest["shadow_id"],
        "cutoff": cutoff,
        "data_version": data_version,
        "appended": appended,
        "latest_signal_date": str(last_signal.date()),
        "trade_authorized": False,
    }


def run(start: str, end: str, manifest_path: str, ledger_path: str) -> dict:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if pd.Timestamp(end) < pd.Timestamp(manifest["freeze_data_cutoff"]):
        raise ValueError("end must not precede the frozen shadow cutoff")
    config = Config()
    connection = connect(config, read_only=True)
    try:
        built = load_or_build_panel(config, start, end, con=connection)
    finally:
        connection.close()
    data = _prepare(built.df)
    sessions = sorted(pd.to_datetime(data.TradingDay.unique()))
    history = [(day, target) for day, _, _, _, target in scheduled_selections(data)]
    return update_ledger(Path(ledger_path), manifest, end, built.version_hash, sessions, history)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2016-01-01")
    parser.add_argument("--end", required=True)
    parser.add_argument("--manifest", default="overall/a-share-low-turnover-buffer-v18-forward-shadow-manifest.json")
    parser.add_argument("--ledger", default="overall/a-share-low-turnover-buffer-v18-forward-shadow-ledger.csv")
    args = parser.parse_args(argv)
    print(json.dumps(run(args.start, args.end, args.manifest, args.ledger), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
