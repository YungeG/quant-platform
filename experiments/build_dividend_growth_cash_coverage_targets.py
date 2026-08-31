"""Apply the frozen practical A-share universe to dividend-growth state."""
from __future__ import annotations

import argparse
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
from factormine.research.combination import repair_point_in_time_size


def practical_universe(day: pd.DataFrame) -> pd.DataFrame:
    size_rank = day.CircMV.rank(ascending=False, method="first")
    adv_pct = day.adv20.rank(pct=True, method="first")
    return day[
        (~day.is_st.fillna(True))
        & (~day.suspended.fillna(True))
        & (day.age >= 252)
        & (day.Close >= 5)
        & (day.Volume > 0)
        & day.CircMV.notna()
        & (size_rank <= 500)
        & (adv_pct > 0.5)
    ].copy()


def run(state_csv: str, as_of: str, out_csv: str, out_json: str) -> dict:
    state = pd.read_csv(state_csv, dtype={"security_code": str})
    eligible = set(state.loc[state.eligible.astype(str).str.lower().eq("true"), "security_code"].str.zfill(6))
    config = Config()
    connection = connect(config, read_only=True)
    try:
        built = load_or_build_panel(config, "2025-01-01", as_of, con=connection)
    finally:
        connection.close()
    panel = repair_point_in_time_size(built.df)
    panel["TradingDay"] = pd.to_datetime(panel.TradingDay)
    day = panel[panel.TradingDay <= pd.Timestamp(as_of)]
    decision_day = pd.Timestamp(day.TradingDay.max())
    day = day[day.TradingDay == decision_day]
    practical = practical_universe(day)
    target = practical[practical.Symbol.astype(str).isin(eligible)].copy().sort_values("Symbol")
    target["weight"] = 1.0 / len(target) if len(target) else 0.0
    target[["TradingDay", "Symbol", "Close", "CircMV", "adv20", "weight"]].to_csv(out_csv, index=False)
    payload = {
        "study": "a-share-dividend-growth-cash-coverage-target-v1",
        "as_of": as_of,
        "decision_day": str(decision_day.date()),
        "data_version": built.version_hash,
        "fundamental_eligible_symbols": len(eligible),
        "practical_target_symbols": len(target),
        "target_weight": 1.0 / len(target) if len(target) else None,
        "status": "TARGET_STATE_BUILT_NO_BACKTEST" if len(target) else "NO_TARGETS",
        "backtest_ready": False,
        "trade_authorized": False,
    }
    Path(out_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-csv", default="overall/a-share-dividend-growth-cash-coverage-state-v1.csv")
    parser.add_argument("--as-of", default="2025-12-31")
    parser.add_argument("--out-csv", default="overall/a-share-dividend-growth-cash-coverage-target-v1.csv")
    parser.add_argument("--out-json", default="overall/a-share-dividend-growth-cash-coverage-target-v1.json")
    args = parser.parse_args(argv)
    print(json.dumps(run(args.state_csv, args.as_of, args.out_csv, args.out_json), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
