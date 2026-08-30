"""Run the frozen stock-bond-gold allocation study."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.multi_asset import (
    AssetBar,
    equal_risk_contribution_weights,
    inverse_vol_weights,
    simulate_allocation,
)
from experiments.run_lowturn_livermore import _clean, _metrics, _returns


ASSETS = ("equity", "bond", "gold")
FOLDS = (
    ("2017-2019", "2017-01-01", "2019-12-31"),
    ("2020-2022", "2020-01-01", "2022-12-31"),
    ("2023-2026", "2023-01-01", "2026-12-31"),
)
INITIAL_NAV = 400_000.0
COST_RATE = 0.0008


def load_data(path: str, start: str, end: str) -> tuple:
    data = pd.read_csv(path, parse_dates=["trade_date"])
    data = data[data["trade_date"] <= pd.Timestamp(end)].copy()
    opens = data.pivot(index="trade_date", columns="asset", values="adj_open").sort_index()
    closes = data.pivot(index="trade_date", columns="asset", values="adj_close").sort_index()
    raw_opens = data.pivot(index="trade_date", columns="asset", values="open").sort_index()
    complete = opens.dropna().index.intersection(closes.dropna().index).intersection(raw_opens.dropna().index)
    opens = opens.loc[complete, list(ASSETS)]
    closes = closes.loc[complete, list(ASSETS)]
    raw_opens = raw_opens.loc[complete, list(ASSETS)]
    returns = closes.pct_change(fill_method=None)
    simulation_dates = complete[complete >= pd.Timestamp(start)]
    dates = [date.date().isoformat() for date in simulation_dates]
    bars = {
        asset: {
            date.date().isoformat(): AssetBar(
                adj_open=float(opens.loc[date, asset]),
                adj_close=float(closes.loc[date, asset]),
                raw_open=float(raw_opens.loc[date, asset]),
            )
            for date in simulation_dates
        }
        for asset in ASSETS
    }
    return dates, bars, returns, raw_opens, closes


def build_targets(dates: list[str], returns: pd.DataFrame) -> dict[str, dict[str, dict[str, float]]]:
    signals = dates[::63]
    targets = {
        "all_equity": {},
        "60_40": {},
        "fixed_30_50_20": {},
        "equal_1n": {},
        "inverse_vol": {},
        "erc": {},
    }
    for date in signals:
        targets["all_equity"][date] = {"equity": 1.0, "bond": 0.0, "gold": 0.0}
        targets["60_40"][date] = {"equity": 0.60, "bond": 0.40, "gold": 0.0}
        targets["fixed_30_50_20"][date] = {"equity": 0.30, "bond": 0.50, "gold": 0.20}
        targets["equal_1n"][date] = {asset: 1.0 / 3.0 for asset in ASSETS}
        signal_time = pd.Timestamp(date)
        window = returns.loc[:signal_time, list(ASSETS)].dropna().tail(252)
        if len(window) < 200:
            dynamic = {asset: 1.0 / 3.0 for asset in ASSETS}
            targets["inverse_vol"][date] = dynamic
            targets["erc"][date] = dynamic
            continue
        volatility = {asset: float(window[asset].std(ddof=1)) for asset in ASSETS}
        targets["inverse_vol"][date] = inverse_vol_weights(volatility)
        covariance = window.cov().to_numpy(dtype=float).tolist()
        targets["erc"][date] = equal_risk_contribution_weights(ASSETS, covariance)
    return targets


def summarize(
    result,
    gross_result,
    targets: dict[str, dict[str, float]],
    raw_opens: pd.DataFrame,
) -> dict:
    index = pd.to_datetime(result.dates)
    nav = pd.Series(result.nav, index=index, dtype=float)
    gross_nav = pd.Series(gross_result.nav, index=index, dtype=float)
    returns = _returns(nav, INITIAL_NAV)
    gross_returns = _returns(gross_nav, INITIAL_NAV)
    metrics = _metrics(returns)
    gross_metrics = _metrics(gross_returns)
    folds = {name: _metrics(returns.loc[start:end]) for name, start, end in FOLDS}
    yearly = {
        str(year): float((1.0 + group).prod() - 1.0)
        for year, group in returns.groupby(returns.index.year)
    }
    years = len(returns) / 252.0
    annual_turnover = float(sum(result.turnover) / years) if years > 0 else 0.0
    retention = metrics["cagr"] / gross_metrics["cagr"] if gross_metrics["cagr"] > 0 else 0.0
    average_weights = {
        asset: float(np.mean([weights.get(asset, 0.0) for weights in result.weights]))
        for asset in ASSETS
    }
    date_index = {date: position for position, date in enumerate(result.dates)}
    feasible = 0
    required = 0
    for signal_date, weights in targets.items():
        signal_position = date_index.get(signal_date)
        if signal_position is None or signal_position + 1 >= len(result.dates):
            continue
        execution_date = pd.Timestamp(result.dates[signal_position + 1])
        nav_reference = result.nav[signal_position]
        for asset, weight in weights.items():
            if weight <= 0:
                continue
            required += 1
            raw_price = float(raw_opens.loc[execution_date, asset])
            if nav_reference * weight / raw_price >= 100:
                feasible += 1
    return {
        "metrics": metrics,
        "gross_metrics": gross_metrics,
        "folds": folds,
        "yearly_returns": yearly,
        "stress_returns": {year: yearly.get(year) for year in ("2018", "2022")},
        "annual_turnover": annual_turnover,
        "gross_to_net_cagr_retention": retention,
        "total_cost": float(sum(result.costs)),
        "average_weights": average_weights,
        "lot_feasibility": feasible / required if required else 0.0,
    }


def complexity_pass(candidate: dict, fixed: dict) -> bool:
    candidate_metrics = candidate["metrics"]
    fixed_metrics = fixed["metrics"]
    return (
        candidate_metrics["sharpe"] >= fixed_metrics["sharpe"] + 0.05
        or (
            candidate_metrics["max_drawdown"] >= fixed_metrics["max_drawdown"] + 0.05
            and candidate_metrics["cagr"] >= fixed_metrics["cagr"] - 0.01
        )
    )


def decide(variants: dict) -> dict:
    fixed = variants["fixed_30_50_20"]
    equity = variants["all_equity"]
    sixty = variants["60_40"]
    fixed_metrics = fixed["metrics"]
    equity_metrics = equity["metrics"]
    drawdown_improvement = (
        (abs(equity_metrics["max_drawdown"]) - abs(fixed_metrics["max_drawdown"]))
        / abs(equity_metrics["max_drawdown"])
        if equity_metrics["max_drawdown"] < 0
        else 0.0
    )
    stress = fixed["stress_returns"]
    equity_stress = equity["stress_returns"]
    sixty_stress = sixty["stress_returns"]
    checks = {
        "drawdown_improvement": drawdown_improvement >= 0.35,
        "sharpe_improvement": fixed_metrics["sharpe"] >= equity_metrics["sharpe"] + 0.20,
        "cagr_floor": fixed_metrics["cagr"] > 0 and fixed_metrics["cagr"] >= sixty["metrics"]["cagr"] - 0.01,
        "positive_folds": all(fold["cagr"] > 0 for fold in fixed["folds"].values()),
        "stress_years": (
            all(stress[year] > equity_stress[year] for year in ("2018", "2022"))
            and any(stress[year] > sixty_stress[year] for year in ("2018", "2022"))
        ),
        "cost_retention": fixed["gross_to_net_cagr_retention"] >= 0.98,
        "turnover": fixed["annual_turnover"] <= 1.0,
        "lot_feasibility": fixed["lot_feasibility"] >= 1.0,
    }
    if all(checks.values()):
        verdict = "GO"
    elif fixed_metrics["cagr"] > 0 and drawdown_improvement >= 0.20:
        verdict = "MARGINAL"
    else:
        verdict = "NO-GO"
    dynamic_passes = {
        name: complexity_pass(variants[name], fixed) for name in ("inverse_vol", "erc")
    }
    preferred = "fixed_30_50_20"
    passing = [name for name, passed in dynamic_passes.items() if passed]
    if passing:
        preferred = max(passing, key=lambda name: variants[name]["metrics"]["sharpe"])
    return {
        "verdict": verdict,
        "checks": checks,
        "drawdown_improvement": drawdown_improvement,
        "dynamic_complexity_pass": dynamic_passes,
        "preferred": preferred,
    }


def render_markdown(payload: dict) -> str:
    lines = [
        "# A股股债金多资产配置结果",
        "",
        f"- verdict: **{payload['decision']['verdict']}**",
        f"- preferred: **{payload['decision']['preferred']}**",
        f"- data: {payload['data']['start']}—{payload['data']['end']}",
        "",
        "| Strategy | CAGR | Sharpe | Max drawdown | Turnover | Eq/Bond/Gold avg |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for name, row in payload["variants"].items():
        metrics = row["metrics"]
        weights = row["average_weights"]
        lines.append(
            f"| {name} | {metrics['cagr']:.2%} | {metrics['sharpe']:.3f} | "
            f"{metrics['max_drawdown']:.2%} | {row['annual_turnover']:.2f} | "
            f"{weights['equity']:.0%}/{weights['bond']:.0%}/{weights['gold']:.0%} |"
        )
    lines.extend(["", "## Gate", ""])
    for name, passed in payload["decision"]["checks"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} `{name}`")
    for name, passed in payload["decision"]["dynamic_complexity_pass"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} `{name}_complexity`")
    return "\n".join(lines)


def run(data_path: str, start: str, end: str) -> dict:
    dates, bars, returns, raw_opens, _ = load_data(data_path, start, end)
    targets = build_targets(dates, returns)
    variants = {}
    for name, strategy_targets in targets.items():
        net = simulate_allocation(
            dates,
            bars,
            strategy_targets,
            initial_nav=INITIAL_NAV,
            cost_rate=COST_RATE,
        )
        gross = simulate_allocation(
            dates,
            bars,
            strategy_targets,
            initial_nav=INITIAL_NAV,
            cost_rate=0.0,
        )
        variants[name] = summarize(net, gross, strategy_targets, raw_opens)
    decision = decide(variants)
    return _clean(
        {
            "study": "a-share-stock-bond-gold-v1",
            "data": {
                "source": data_path,
                "start": dates[0],
                "end": dates[-1],
                "sessions": len(dates),
                "rebalance_interval": 63,
                "cost_rate_per_side": COST_RATE,
            },
            "variants": variants,
            "decision": decision,
            "limitations": [
                "ETF market prices include premiums, discounts, fees, and tracking differences",
                "the sample begins in 2017 and is not virgin OOS",
                "continuous-weight returns are primary; 100-share board lots are a feasibility gate",
                "no leverage, trend filter, expected-return forecast, or tax overlay is modeled",
            ],
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="overall/a-share-multi-asset-etf-daily.csv")
    parser.add_argument("--start", default="2017-01-03")
    parser.add_argument("--end", default="2026-08-25")
    parser.add_argument("--out-json", default="overall/a-share-multi-asset.json")
    parser.add_argument("--out-md", default="overall/a-share-multi-asset.md")
    args = parser.parse_args(argv)
    payload = run(args.data, args.start, args.end)
    Path(args.out_json).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown = render_markdown(payload)
    Path(args.out_md).write_text(markdown + "\n", encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
