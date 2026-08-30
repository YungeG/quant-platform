"""Backtest A-share size-index core portfolios."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.multi_asset import AssetBar, inverse_vol_weights, simulate_allocation
from experiments.run_lowturn_livermore import _clean, _metrics, _returns


ASSETS = ("equity300", "equity500", "equity1000", "bond", "gold")
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
    raw = data.pivot(index="trade_date", columns="asset", values="open").sort_index()
    complete = opens.dropna().index.intersection(closes.dropna().index).intersection(raw.dropna().index)
    complete = complete[complete >= pd.Timestamp(start)]
    opens = opens.loc[complete, list(ASSETS)]
    closes = closes.loc[complete, list(ASSETS)]
    raw = raw.loc[complete, list(ASSETS)]
    dates = [date.date().isoformat() for date in complete]
    bars = {
        asset: {
            date.date().isoformat(): AssetBar(
                adj_open=float(opens.loc[date, asset]),
                adj_close=float(closes.loc[date, asset]),
                raw_open=float(raw.loc[date, asset]),
            )
            for date in complete
        }
        for asset in ASSETS
    }
    return dates, bars, closes.pct_change(fill_method=None), raw


def build_targets(dates: list[str], returns: pd.DataFrame) -> dict:
    targets = {name: {} for name in (
        "three_asset_1n", "balanced_size", "broad_equal5", "small_tilt", "size_vol_budget"
    )}
    for date in dates[::63]:
        targets["three_asset_1n"][date] = {
            "equity300": 1 / 3, "equity500": 0.0, "equity1000": 0.0,
            "bond": 1 / 3, "gold": 1 / 3,
        }
        targets["balanced_size"][date] = {
            "equity300": 0.20, "equity500": 0.20, "equity1000": 0.10,
            "bond": 0.30, "gold": 0.20,
        }
        targets["broad_equal5"][date] = {asset: 0.20 for asset in ASSETS}
        targets["small_tilt"][date] = {
            "equity300": 0.15, "equity500": 0.20, "equity1000": 0.25,
            "bond": 0.20, "gold": 0.20,
        }
        window = returns.loc[: pd.Timestamp(date), ["equity300", "equity500", "equity1000"]].dropna().tail(252)
        if len(window) < 200:
            equity_weights = {asset: 1 / 3 for asset in ("equity300", "equity500", "equity1000")}
        else:
            equity_weights = inverse_vol_weights(
                {asset: float(window[asset].std(ddof=1)) for asset in window.columns}
            )
        targets["size_vol_budget"][date] = {
            **{asset: equity_weights[asset] * 0.50 for asset in equity_weights},
            "bond": 0.30,
            "gold": 0.20,
        }
    return targets


def summarize(result, gross, targets, raw_opens) -> dict:
    index = pd.to_datetime(result.dates)
    returns = _returns(pd.Series(result.nav, index=index), INITIAL_NAV)
    gross_returns = _returns(pd.Series(gross.nav, index=index), INITIAL_NAV)
    metrics = _metrics(returns)
    gross_metrics = _metrics(gross_returns)
    folds = {name: _metrics(returns.loc[start:end]) for name, start, end in FOLDS}
    yearly = {str(year): float((1 + group).prod() - 1) for year, group in returns.groupby(returns.index.year)}
    best = max(yearly, key=yearly.get)
    remaining = [value for year, value in yearly.items() if year != best]
    cagr_without_best = float(np.prod([1 + value for value in remaining]) ** (1 / len(remaining)) - 1)
    years = len(returns) / 252
    retention = metrics["cagr"] / gross_metrics["cagr"] if gross_metrics["cagr"] > 0 else 0.0
    date_index = {date: i for i, date in enumerate(result.dates)}
    feasible = required = 0
    for signal, weights in targets.items():
        i = date_index.get(signal)
        if i is None or i + 1 >= len(result.dates):
            continue
        execution = pd.Timestamp(result.dates[i + 1])
        nav = result.nav[i]
        for asset, weight in weights.items():
            if weight <= 0:
                continue
            required += 1
            feasible += int(nav * weight / float(raw_opens.loc[execution, asset]) >= 100)
    return {
        "metrics": metrics,
        "gross_metrics": gross_metrics,
        "folds": folds,
        "yearly_returns": yearly,
        "stress_returns": {year: yearly[year] for year in ("2018", "2022")},
        "cagr_excluding_best_year": cagr_without_best,
        "annual_turnover": float(sum(result.turnover) / years),
        "gross_to_net_cagr_retention": retention,
        "average_weights": {
            asset: float(np.mean([weights.get(asset, 0.0) for weights in result.weights]))
            for asset in ASSETS
        },
        "lot_feasibility": feasible / required if required else 0.0,
        "total_cost": float(sum(result.costs)),
    }


def decide(variants: dict) -> dict:
    main = variants["balanced_size"]
    baseline = variants["three_asset_1n"]
    checks = {
        "cagr": main["metrics"]["cagr"] >= 0.10,
        "cagr_margin": main["metrics"]["cagr"] >= baseline["metrics"]["cagr"] + 0.01,
        "sharpe": main["metrics"]["sharpe"] >= 0.80,
        "max_drawdown": main["metrics"]["max_drawdown"] >= -0.20,
        "positive_folds": all(fold["cagr"] > 0 for fold in main["folds"].values()),
        "stress_years": all(main["stress_returns"][year] >= -0.15 for year in ("2018", "2022")),
        "best_year_independence": main["cagr_excluding_best_year"] > 0,
        "cost_retention": main["gross_to_net_cagr_retention"] >= 0.98,
        "turnover": main["annual_turnover"] <= 1.0,
        "lot_feasibility": main["lot_feasibility"] >= 1.0,
    }
    if all(checks.values()):
        verdict = "GO"
    elif main["metrics"]["cagr"] >= 0.08 and main["metrics"]["max_drawdown"] >= -0.20:
        verdict = "MARGINAL"
    else:
        verdict = "NO-GO"
    preferred = "balanced_size"
    broad = variants["broad_equal5"]
    if (
        broad["metrics"]["cagr"] >= main["metrics"]["cagr"] - 0.005
        and broad["metrics"]["sharpe"] >= main["metrics"]["sharpe"] - 0.05
    ):
        preferred = "broad_equal5"
    vol = variants["size_vol_budget"]
    if (
        vol["metrics"]["sharpe"] >= variants[preferred]["metrics"]["sharpe"] + 0.05
        or (
            vol["metrics"]["max_drawdown"] >= variants[preferred]["metrics"]["max_drawdown"] + 0.03
            and vol["metrics"]["cagr"] >= variants[preferred]["metrics"]["cagr"] - 0.01
        )
    ):
        preferred = "size_vol_budget"
    return {"verdict": verdict, "preferred": preferred, "checks": checks}


def render_markdown(payload: dict) -> str:
    lines = [
        "# A股规模指数核心策略结果", "",
        f"- verdict: **{payload['decision']['verdict']}**",
        f"- preferred: **{payload['decision']['preferred']}**", "",
        "| Strategy | CAGR | Sharpe | Max drawdown | Turnover |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, row in payload["variants"].items():
        m = row["metrics"]
        lines.append(f"| {name} | {m['cagr']:.2%} | {m['sharpe']:.3f} | {m['max_drawdown']:.2%} | {row['annual_turnover']:.2f} |")
    return "\n".join(lines)


def run(data_path: str, start: str, end: str) -> dict:
    dates, bars, returns, raw = load_data(data_path, start, end)
    targets = build_targets(dates, returns)
    variants = {}
    for name, strategy_targets in targets.items():
        net = simulate_allocation(dates, bars, strategy_targets, initial_nav=INITIAL_NAV, cost_rate=COST_RATE)
        gross = simulate_allocation(dates, bars, strategy_targets, initial_nav=INITIAL_NAV, cost_rate=0.0)
        variants[name] = summarize(net, gross, strategy_targets, raw)
    decision = decide(variants)
    return _clean({
        "study": "a-share-size-index-core-v1",
        "data": {"source": data_path, "start": dates[0], "end": dates[-1]},
        "variants": variants,
        "decision": decision,
        "limitations": [
            "ETF history begins in late 2016 and is not virgin OOS",
            "no leverage, macro timing, or stock-selection alpha is included",
            "CSI1000 ETF liquidity is lower than CSI300/500 ETFs",
        ],
    })


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="overall/a-share-size-etf-daily.csv")
    parser.add_argument("--start", default="2017-01-03")
    parser.add_argument("--end", default="2026-08-25")
    parser.add_argument("--out-json", default="overall/a-share-size-index.json")
    parser.add_argument("--out-md", default="overall/a-share-size-index.md")
    args = parser.parse_args(argv)
    payload = run(args.data, args.start, args.end)
    Path(args.out_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = render_markdown(payload)
    Path(args.out_md).write_text(markdown + "\n", encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
