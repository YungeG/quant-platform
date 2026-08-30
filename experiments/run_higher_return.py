"""Evaluate moderate leverage on validated stock-bond-gold allocations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.multi_asset import simulate_allocation
from experiments.run_multi_asset import (
    ASSETS,
    COST_RATE,
    INITIAL_NAV,
    build_targets,
    load_data,
)
from experiments.run_lowturn_livermore import _clean, _metrics, _returns


FOLDS = (
    ("2017-2019", "2017-01-01", "2019-12-31"),
    ("2020-2022", "2020-01-01", "2022-12-31"),
    ("2023-2026", "2023-01-01", "2026-12-31"),
)


def scale_targets(
    targets: dict[str, dict[str, float]], leverage: float
) -> dict[str, dict[str, float]]:
    return {
        date: {asset: weight * leverage for asset, weight in weights.items()}
        for date, weights in targets.items()
    }


def volatility_target_weights(
    dates: list[str], returns: pd.DataFrame
) -> dict[str, dict[str, float]]:
    targets = {}
    base = np.array([1.0 / 3.0] * 3)
    for date in dates[::63]:
        window = returns.loc[: pd.Timestamp(date), list(ASSETS)].dropna().tail(252)
        if len(window) < 200:
            leverage = 1.0
        else:
            covariance = window.cov().to_numpy(dtype=float) * 252.0
            volatility = float(np.sqrt(base @ covariance @ base))
            leverage = float(np.clip(0.12 / volatility, 0.75, 1.50)) if volatility > 0 else 1.0
        targets[date] = {asset: leverage / 3.0 for asset in ASSETS}
    return targets


def summarize(result, gross_result, stress_result, targets, raw_opens) -> dict:
    index = pd.to_datetime(result.dates)
    returns = _returns(pd.Series(result.nav, index=index), INITIAL_NAV)
    gross_returns = _returns(pd.Series(gross_result.nav, index=index), INITIAL_NAV)
    stress_returns = _returns(pd.Series(stress_result.nav, index=index), INITIAL_NAV)
    metrics = _metrics(returns)
    gross_metrics = _metrics(gross_returns)
    stress_metrics = _metrics(stress_returns)
    folds = {name: _metrics(returns.loc[start:end]) for name, start, end in FOLDS}
    yearly = {
        str(year): float((1.0 + group).prod() - 1.0)
        for year, group in returns.groupby(returns.index.year)
    }
    stress_yearly = {
        str(year): float((1.0 + group).prod() - 1.0)
        for year, group in stress_returns.groupby(stress_returns.index.year)
    }
    years = len(returns) / 252.0
    annual_turnover = float(sum(result.turnover) / years) if years > 0 else 0.0
    retention = metrics["cagr"] / gross_metrics["cagr"] if gross_metrics["cagr"] > 0 else 0.0
    date_index = {date: position for position, date in enumerate(result.dates)}
    feasible = required = 0
    for signal_date, weights in targets.items():
        position = date_index.get(signal_date)
        if position is None or position + 1 >= len(result.dates):
            continue
        execution_date = pd.Timestamp(result.dates[position + 1])
        nav_reference = result.nav[position]
        for asset, weight in weights.items():
            if weight <= 0:
                continue
            required += 1
            if nav_reference * weight / float(raw_opens.loc[execution_date, asset]) >= 100:
                feasible += 1
    return {
        "metrics": metrics,
        "gross_metrics": gross_metrics,
        "funding_7pct_metrics": stress_metrics,
        "folds": folds,
        "yearly_returns": yearly,
        "funding_7pct_yearly_returns": stress_yearly,
        "stress_returns": {year: yearly.get(year) for year in ("2018", "2022")},
        "annual_turnover": annual_turnover,
        "average_leverage": float(np.mean(result.leverage)),
        "maximum_leverage": float(np.max(result.leverage)),
        "transaction_cost": float(sum(result.costs)),
        "financing_cost": float(sum(result.financing_costs)),
        "gross_to_net_cagr_retention": retention,
        "lot_feasibility": feasible / required if required else 0.0,
    }


def candidate_gate(result: dict) -> dict:
    metrics = result["metrics"]
    funding = result["funding_7pct_metrics"]
    return {
        "cagr": metrics["cagr"] >= 0.10,
        "sharpe": metrics["sharpe"] >= 0.80,
        "max_drawdown": metrics["max_drawdown"] >= -0.20,
        "positive_folds": all(fold["cagr"] > 0 for fold in result["folds"].values()),
        "stress_years": all(result["stress_returns"][year] >= -0.15 for year in ("2018", "2022")),
        "funding_stress": funding["cagr"] >= 0.08 and funding["max_drawdown"] >= -0.22,
        "leverage": result["maximum_leverage"] <= 1.50,
        "cost_retention": result["gross_to_net_cagr_retention"] >= 0.97,
        "lot_feasibility": result["lot_feasibility"] >= 1.0,
    }


def decide(variants: dict) -> dict:
    order = (
        "equal_1n_1.25x",
        "equal_1n_1.50x",
        "fixed_30_50_20_1.50x",
        "equal_1n_vol12",
    )
    gates = {name: candidate_gate(variants[name]) for name in order}
    passing = [name for name in order if all(gates[name].values())]
    if passing:
        verdict = "GO"
        preferred = passing[0]
        vol = variants["equal_1n_vol12"]
        fixed = variants[preferred]
        if "equal_1n_vol12" in passing and (
            vol["metrics"]["sharpe"] >= fixed["metrics"]["sharpe"] + 0.05
            or (
                vol["metrics"]["max_drawdown"] >= fixed["metrics"]["max_drawdown"] + 0.03
                and vol["metrics"]["cagr"] >= fixed["metrics"]["cagr"] - 0.01
            )
        ):
            preferred = "equal_1n_vol12"
    else:
        preferred = max(order, key=lambda name: variants[name]["metrics"]["cagr"])
        best = variants[preferred]["metrics"]
        if best["cagr"] >= 0.08 and best["max_drawdown"] >= -0.20:
            verdict = "MARGINAL"
        else:
            verdict = "NO-GO"
    return {"verdict": verdict, "preferred": preferred, "gates": gates}


def render_markdown(payload: dict) -> str:
    lines = [
        "# 股债金更高收益配置结果",
        "",
        f"- verdict: **{payload['decision']['verdict']}**",
        f"- preferred: **{payload['decision']['preferred']}**",
        "",
        "| Strategy | CAGR | Sharpe | Max drawdown | Avg/Max leverage | 7% funding CAGR |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, row in payload["variants"].items():
        metrics = row["metrics"]
        lines.append(
            f"| {name} | {metrics['cagr']:.2%} | {metrics['sharpe']:.3f} | "
            f"{metrics['max_drawdown']:.2%} | {row['average_leverage']:.2f}/{row['maximum_leverage']:.2f} | "
            f"{row['funding_7pct_metrics']['cagr']:.2%} |"
        )
    return "\n".join(lines)


def run(data_path: str, start: str, end: str) -> dict:
    dates, bars, returns, raw_opens, _ = load_data(data_path, start, end)
    base = build_targets(dates, returns)
    targets = {
        "equal_1n": base["equal_1n"],
        "equal_1n_1.25x": scale_targets(base["equal_1n"], 1.25),
        "equal_1n_1.50x": scale_targets(base["equal_1n"], 1.50),
        "fixed_30_50_20_1.50x": scale_targets(base["fixed_30_50_20"], 1.50),
        "equal_1n_vol12": volatility_target_weights(dates, returns),
    }
    variants = {}
    for name, strategy_targets in targets.items():
        net = simulate_allocation(
            dates,
            bars,
            strategy_targets,
            initial_nav=INITIAL_NAV,
            cost_rate=COST_RATE,
            financing_rate=0.05,
            normalize_targets=False,
        )
        gross = simulate_allocation(
            dates,
            bars,
            strategy_targets,
            initial_nav=INITIAL_NAV,
            cost_rate=0.0,
            financing_rate=0.05,
            normalize_targets=False,
        )
        stress = simulate_allocation(
            dates,
            bars,
            strategy_targets,
            initial_nav=INITIAL_NAV,
            cost_rate=COST_RATE,
            financing_rate=0.07,
            normalize_targets=False,
        )
        variants[name] = summarize(net, gross, stress, strategy_targets, raw_opens)
    decision = decide(variants)
    return _clean(
        {
            "study": "a-share-higher-return-multi-asset-v1",
            "data": {"source": data_path, "start": dates[0], "end": dates[-1]},
            "variants": variants,
            "decision": decision,
            "limitations": [
                "no broker-specific margin calls or forced liquidation are modeled",
                "financing is assumed continuously available at 5% base and 7% stress",
                "realized leverage can drift above target between quarterly rebalances",
                "deployment requires broker eligibility and collateral audit",
            ],
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="overall/a-share-multi-asset-etf-daily.csv")
    parser.add_argument("--start", default="2017-01-03")
    parser.add_argument("--end", default="2026-08-25")
    parser.add_argument("--out-json", default="overall/a-share-higher-return.json")
    parser.add_argument("--out-md", default="overall/a-share-higher-return.md")
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
