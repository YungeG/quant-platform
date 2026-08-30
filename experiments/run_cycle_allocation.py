"""Backtest a lagged China growth/inflation cycle overlay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.cycle_allocation import (
    CYCLE_WEIGHTS,
    classify_cycle_fast,
    classify_cycle_slow,
)
from experiments.multi_asset import simulate_allocation
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
FIXED = {"equity": 0.30, "bond": 0.50, "gold": 0.20}


def month_end_dates(dates: list[str]) -> list[str]:
    frame = pd.DataFrame({"date": pd.to_datetime(dates)})
    return [
        value.date().isoformat()
        for value in frame.groupby(frame["date"].dt.to_period("M"))["date"].max()
    ]


def build_cycle_targets(
    dates: list[str], macro_path: str
) -> tuple[dict[str, dict[str, dict[str, float]]], dict]:
    macro = pd.read_csv(macro_path, parse_dates=["month"]).sort_values("month")
    macro = macro.dropna(subset=["composite_pmi", "ppi_yoy"])
    fast_targets: dict[str, dict[str, float]] = {}
    slow_targets: dict[str, dict[str, float]] = {}
    fixed_monthly: dict[str, dict[str, float]] = {}
    state_history = []
    for signal_date in month_end_dates(dates):
        signal_time = pd.Timestamp(signal_date)
        cutoff = (signal_time.to_period("M") - 1).to_timestamp()
        available = macro[macro["month"] <= cutoff]
        fixed_monthly[signal_date] = dict(FIXED)
        if len(available) >= 4:
            latest = available.tail(4)
            label, growth_impulse, inflation_impulse = classify_cycle_fast(
                latest["composite_pmi"].tolist(), latest["ppi_yoy"].tolist()
            )
            fast_targets[signal_date] = dict(CYCLE_WEIGHTS[label])
        else:
            label, growth_impulse, inflation_impulse = "unavailable", 0.0, 0.0
            fast_targets[signal_date] = dict(FIXED)
        if len(available) >= 6:
            slow = available.tail(6)
            slow_label, slow_growth, slow_inflation = classify_cycle_slow(
                slow["composite_pmi"].tolist(), slow["ppi_yoy"].tolist()
            )
            slow_targets[signal_date] = dict(CYCLE_WEIGHTS[slow_label])
        else:
            slow_label, slow_growth, slow_inflation = "unavailable", 0.0, 0.0
            slow_targets[signal_date] = dict(FIXED)
        state_history.append(
            {
                "signal_date": signal_date,
                "data_through": cutoff.date().isoformat(),
                "fast_state": label,
                "fast_growth_impulse": growth_impulse,
                "fast_inflation_impulse": inflation_impulse,
                "slow_state": slow_label,
                "slow_growth_impulse": slow_growth,
                "slow_inflation_impulse": slow_inflation,
            }
        )
    latest = macro.tail(6)
    current_fast = classify_cycle_fast(
        latest.tail(4)["composite_pmi"].tolist(), latest.tail(4)["ppi_yoy"].tolist()
    )
    current_slow = classify_cycle_slow(
        latest["composite_pmi"].tolist(), latest["ppi_yoy"].tolist()
    )
    current = {
        "data_through": latest["month"].iloc[-1].date().isoformat(),
        "fast_state": current_fast[0],
        "fast_growth_impulse": current_fast[1],
        "fast_inflation_impulse": current_fast[2],
        "fast_weights": CYCLE_WEIGHTS[current_fast[0]],
        "slow_state": current_slow[0],
        "slow_growth_impulse": current_slow[1],
        "slow_inflation_impulse": current_slow[2],
        "slow_weights": CYCLE_WEIGHTS[current_slow[0]],
    }
    return {
        "cycle_fast": fast_targets,
        "cycle_slow": slow_targets,
        "fixed_monthly": fixed_monthly,
    }, {"current": current, "history": state_history}


def cagr_excluding_best_year(yearly: dict[str, float]) -> float:
    if len(yearly) <= 1:
        return 0.0
    best = max(yearly, key=yearly.get)
    remaining = [value for year, value in yearly.items() if year != best]
    return float(np.prod([1.0 + value for value in remaining]) ** (1.0 / len(remaining)) - 1.0)


def decide(cycle: dict, fixed: dict) -> dict:
    cycle_metrics = cycle["metrics"]
    fixed_metrics = fixed["metrics"]
    excess_folds = {
        name: cycle["folds"][name]["cagr"] - fixed["folds"][name]["cagr"]
        for name, _, _ in FOLDS
    }
    stress_ok = all(
        cycle["stress_returns"][year] >= fixed["stress_returns"][year] - 0.05
        for year in ("2018", "2022")
    )
    checks = {
        "cagr_margin": cycle_metrics["cagr"] >= fixed_metrics["cagr"] + 0.01,
        "sharpe_floor": cycle_metrics["sharpe"] >= fixed_metrics["sharpe"] - 0.05,
        "max_drawdown": cycle_metrics["max_drawdown"] >= -0.15,
        "positive_excess_folds": sum(value > 0 for value in excess_folds.values()) >= 2,
        "stress_years": stress_ok,
        "best_year_independence": cagr_excluding_best_year(cycle["yearly_returns"]) > 0,
        "cost_retention": cycle["gross_to_net_cagr_retention"] >= 0.98,
        "turnover": cycle["annual_turnover"] <= 1.5,
        "lot_feasibility": cycle["lot_feasibility"] >= 1.0,
    }
    if all(checks.values()):
        verdict = "GO"
    elif cycle_metrics["cagr"] > 0 and cycle_metrics["max_drawdown"] >= -0.20:
        verdict = "MARGINAL"
    else:
        verdict = "NO-GO"
    return {"verdict": verdict, "checks": checks, "fold_excess_cagr": excess_folds}


def render_markdown(payload: dict) -> str:
    lines = [
        "# 中国经济周期驱动股债金配置结果",
        "",
        f"- verdict: **{payload['decision']['verdict']}**",
        f"- current fast state: **{payload['current_cycle']['fast_state']}**",
        f"- current slow state: **{payload['current_cycle']['slow_state']}**",
        "",
        "| Strategy | CAGR | Sharpe | Max drawdown | Turnover |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, row in payload["variants"].items():
        metrics = row["metrics"]
        lines.append(
            f"| {name} | {metrics['cagr']:.2%} | {metrics['sharpe']:.3f} | "
            f"{metrics['max_drawdown']:.2%} | {row['annual_turnover']:.2f} |"
        )
    lines.extend(["", "## Gate", ""])
    for name, passed in payload["decision"]["checks"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} `{name}`")
    return "\n".join(lines)


def run(etf_path: str, macro_path: str, start: str, end: str) -> dict:
    dates, bars, returns, raw_opens, _ = load_data(etf_path, start, end)
    quarterly = build_targets(dates, returns)
    cycle_targets, cycle_state = build_cycle_targets(dates, macro_path)
    targets = {
        "fixed_quarterly": quarterly["fixed_30_50_20"],
        "equal_1n": quarterly["equal_1n"],
        "inverse_vol": quarterly["inverse_vol"],
        **cycle_targets,
    }
    variants = {}
    for name, strategy_targets in targets.items():
        net = simulate_allocation(
            dates, bars, strategy_targets, initial_nav=INITIAL_NAV, cost_rate=COST_RATE
        )
        gross = simulate_allocation(
            dates, bars, strategy_targets, initial_nav=INITIAL_NAV, cost_rate=0.0
        )
        variants[name] = summarize(net, gross, strategy_targets, raw_opens)
    decision = decide(variants["cycle_fast"], variants["fixed_quarterly"])
    current = cycle_state["current"]
    recommended = (
        current["fast_weights"] if decision["verdict"] == "GO" else FIXED
    )
    return _clean(
        {
            "study": "china-cycle-stock-bond-gold-v1",
            "data": {
                "etf_source": etf_path,
                "macro_source": macro_path,
                "start": dates[0],
                "end": dates[-1],
            },
            "variants": variants,
            "decision": decision,
            "current_cycle": current,
            "recommended_weights": recommended,
            "cycle_state_history": cycle_state["history"],
            "limitations": [
                "macro history is current-vintage and lacks historical revision snapshots",
                "a one-month lag is imposed but cannot eliminate revision bias",
                "cycle weights are fixed economic hypotheses rather than optimized allocations",
                "the current official assessment can turn before the slow classifier confirms",
            ],
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--etf-data", default="overall/a-share-multi-asset-etf-daily.csv")
    parser.add_argument("--macro-data", default="overall/a-share-macro-cycle-monthly.csv")
    parser.add_argument("--start", default="2017-01-03")
    parser.add_argument("--end", default="2026-08-25")
    parser.add_argument("--out-json", default="overall/a-share-cycle-allocation.json")
    parser.add_argument("--out-md", default="overall/a-share-cycle-allocation.md")
    args = parser.parse_args(argv)
    payload = run(args.etf_data, args.macro_data, args.start, args.end)
    Path(args.out_json).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown = render_markdown(payload)
    Path(args.out_md).write_text(markdown + "\n", encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
