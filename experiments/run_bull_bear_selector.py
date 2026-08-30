"""Select validated portfolios by an ex-ante bull/bear price state."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.multi_asset import inverse_vol_weights, simulate_allocation
from experiments.run_multi_asset import (
    ASSETS,
    COST_RATE,
    INITIAL_NAV,
    build_targets,
    load_data,
    summarize,
)
from experiments.run_lowturn_livermore import _clean


FOLDS = (
    ("2017-2019", "2017-01-01", "2019-12-31"),
    ("2020-2022", "2020-01-01", "2022-12-31"),
    ("2023-2026", "2023-01-01", "2026-12-31"),
)


def month_ends(dates: list[str]) -> list[str]:
    series = pd.Series(pd.to_datetime(dates))
    return [value.date().isoformat() for value in series.groupby(series.dt.to_period("M")).max()]


def build_selector_targets(
    dates: list[str], returns: pd.DataFrame, closes: pd.DataFrame
) -> tuple[dict[str, dict[str, float]], list[dict]]:
    equity = closes["equity"]
    ma200 = equity.rolling(200, min_periods=200).mean()
    ret60 = equity / equity.shift(60) - 1.0
    targets = {}
    states = []
    for date in month_ends(dates):
        timestamp = pd.Timestamp(date)
        if not np.isfinite(ma200.get(timestamp, np.nan)) or not np.isfinite(ret60.get(timestamp, np.nan)):
            state = "transition"
        elif equity.loc[timestamp] > ma200.loc[timestamp] and ret60.loc[timestamp] > 0:
            state = "bull"
        elif equity.loc[timestamp] < ma200.loc[timestamp] and ret60.loc[timestamp] < 0:
            state = "bear"
        else:
            state = "transition"
        if state == "bull":
            weights = {"equity": 1.0, "bond": 0.0, "gold": 0.0}
        elif state == "transition":
            weights = {asset: 1.0 / 3.0 for asset in ASSETS}
        else:
            window = returns.loc[:timestamp, list(ASSETS)].dropna().tail(252)
            weights = (
                inverse_vol_weights({asset: float(window[asset].std(ddof=1)) for asset in ASSETS})
                if len(window) >= 200
                else {asset: 1.0 / 3.0 for asset in ASSETS}
            )
        targets[date] = weights
        states.append(
            {
                "signal_date": date,
                "state": state,
                "equity_close": float(equity.loc[timestamp]),
                "ma200": float(ma200.get(timestamp, np.nan)),
                "ret60": float(ret60.get(timestamp, np.nan)),
                "weights": weights,
            }
        )
    return targets, states


def cagr_without_best(yearly: dict[str, float]) -> float:
    best = max(yearly, key=yearly.get)
    values = [value for year, value in yearly.items() if year != best]
    return float(np.prod([1.0 + value for value in values]) ** (1.0 / len(values)) - 1.0)


def decide(selector: dict, baseline: dict) -> dict:
    checks = {
        "cagr": selector["metrics"]["cagr"] >= 0.10,
        "cagr_margin": selector["metrics"]["cagr"] >= baseline["metrics"]["cagr"] + 0.01,
        "sharpe": selector["metrics"]["sharpe"] >= 0.80,
        "max_drawdown": selector["metrics"]["max_drawdown"] >= -0.20,
        "fold_margin": sum(
            selector["folds"][name]["cagr"] > baseline["folds"][name]["cagr"]
            for name, _, _ in FOLDS
        )
        >= 2,
        "stress_years": all(selector["stress_returns"][year] >= -0.15 for year in ("2018", "2022")),
        "best_year_independence": cagr_without_best(selector["yearly_returns"]) > 0,
        "cost_retention": selector["gross_to_net_cagr_retention"] >= 0.97,
        "turnover": selector["annual_turnover"] <= 2.0,
        "lot_feasibility": selector["lot_feasibility"] >= 1.0,
    }
    if all(checks.values()):
        verdict = "GO"
    elif selector["metrics"]["cagr"] >= 0.08 and selector["metrics"]["max_drawdown"] >= -0.20:
        verdict = "MARGINAL"
    else:
        verdict = "NO-GO"
    return {"verdict": verdict, "checks": checks}


def render_markdown(payload: dict) -> str:
    lines = [
        "# A股牛熊分阶段策略结果", "",
        f"- verdict: **{payload['decision']['verdict']}**",
        f"- current state: **{payload['current_state']}**", "",
        "| Strategy | CAGR | Sharpe | Max drawdown | Turnover |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, row in payload["variants"].items():
        m = row["metrics"]
        lines.append(f"| {name} | {m['cagr']:.2%} | {m['sharpe']:.3f} | {m['max_drawdown']:.2%} | {row['annual_turnover']:.2f} |")
    return "\n".join(lines)


def run(data_path: str, start: str, end: str) -> dict:
    dates, bars, returns, raw_opens, closes = load_data(data_path, start, end)
    selector_targets, states = build_selector_targets(dates, returns, closes)
    baselines = build_targets(dates, returns)
    targets = {
        "regime_selector": selector_targets,
        "equal_1n": baselines["equal_1n"],
        "fixed_30_50_20": baselines["fixed_30_50_20"],
        "inverse_vol": baselines["inverse_vol"],
        "all_equity": baselines["all_equity"],
    }
    variants = {}
    for name, strategy_targets in targets.items():
        net = simulate_allocation(dates, bars, strategy_targets, initial_nav=INITIAL_NAV, cost_rate=COST_RATE)
        gross = simulate_allocation(dates, bars, strategy_targets, initial_nav=INITIAL_NAV, cost_rate=0.0)
        variants[name] = summarize(net, gross, strategy_targets, raw_opens)
    decision = decide(variants["regime_selector"], variants["equal_1n"])
    return _clean({
        "study": "a-share-bull-bear-selector-v1",
        "data": {"source": data_path, "start": dates[0], "end": dates[-1]},
        "variants": variants,
        "decision": decision,
        "state_counts": dict(Counter(row["state"] for row in states)),
        "current_state": states[-1]["state"],
        "current_weights": states[-1]["weights"],
        "state_history": states,
        "limitations": [
            "state is observed monthly and reacts after trends begin",
            "the same sample informed prior strategy research and is not virgin OOS",
            "no breadth, valuation, leverage, or shorting is used",
        ],
    })


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="overall/a-share-multi-asset-etf-daily.csv")
    parser.add_argument("--start", default="2017-01-03")
    parser.add_argument("--end", default="2026-08-25")
    parser.add_argument("--out-json", default="overall/a-share-bull-bear-selector.json")
    parser.add_argument("--out-md", default="overall/a-share-bull-bear-selector.md")
    args = parser.parse_args(argv)
    payload = run(args.data, args.start, args.end)
    Path(args.out_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = render_markdown(payload)
    Path(args.out_md).write_text(markdown + "\n", encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
