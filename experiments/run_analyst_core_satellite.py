"""Blend the analyst-revision stock sleeve with the validated 1/N core."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.multi_asset import simulate_allocation
from experiments.run_lowturn_livermore import _clean, _metrics, _returns
from experiments.run_multi_asset import COST_RATE, INITIAL_NAV, build_targets, load_data


FOLDS = (
    ("2017-2019", "2017-01-01", "2019-12-31"),
    ("2020-2022", "2020-01-01", "2022-12-31"),
    ("2023-2026", "2023-01-01", "2026-12-31"),
)


def summarize(nav: pd.Series) -> dict:
    returns = _returns(nav, INITIAL_NAV)
    metrics = _metrics(returns)
    folds = {name: _metrics(returns.loc[start:end]) for name, start, end in FOLDS}
    yearly = {str(year): float((1 + group).prod() - 1) for year, group in returns.groupby(returns.index.year)}
    best = max(yearly, key=yearly.get)
    remaining = [value for year, value in yearly.items() if year != best]
    cagr_without_best = float(np.prod([1 + value for value in remaining]) ** (1 / len(remaining)) - 1)
    return {"metrics": metrics, "folds": folds, "yearly_returns": yearly, "cagr_excluding_best_year": cagr_without_best}


def run(revision_nav_path: str, asset_path: str, start: str, end: str) -> dict:
    revision = pd.read_csv(revision_nav_path, parse_dates=["date"]).set_index("date")["nav"].sort_index()
    dates, bars, returns, _, _ = load_data(asset_path, start, end)
    targets = build_targets(dates, returns)["equal_1n"]
    core_result = simulate_allocation(dates, bars, targets, initial_nav=INITIAL_NAV, cost_rate=COST_RATE)
    core = pd.Series(core_result.nav, index=pd.to_datetime(core_result.dates), dtype=float)
    index = revision.index.intersection(core.index)
    revision = revision.loc[index]
    core = core.loc[index]
    revision_norm = revision / revision.iloc[0]
    core_norm = core / core.iloc[0]
    variants = {"core_1n": summarize(core)}
    for weight in (0.20, 0.30, 0.50):
        nav = INITIAL_NAV * (weight * revision_norm + (1.0 - weight) * core_norm)
        variants[f"analyst_{int(weight * 100)}"] = summarize(nav)
    main = variants["analyst_30"]
    baseline = variants["core_1n"]
    checks = {
        "cagr": main["metrics"]["cagr"] >= 0.10,
        "sharpe": main["metrics"]["sharpe"] >= 0.90,
        "drawdown": main["metrics"]["max_drawdown"] >= -0.20,
        "positive_folds": all(fold["cagr"] > 0 for fold in main["folds"].values()),
        "cagr_margin": main["metrics"]["cagr"] >= baseline["metrics"]["cagr"] + 0.01,
        "best_year_independence": main["cagr_excluding_best_year"] > 0,
    }
    verdict = "GO" if all(checks.values()) else (
        "MARGINAL" if main["metrics"]["cagr"] > baseline["metrics"]["cagr"] else "NO-GO"
    )
    return _clean(
        {
            "study": "a-share-analyst-core-satellite-v1",
            "data": {"start": index.min().date().isoformat(), "end": index.max().date().isoformat()},
            "variants": variants,
            "decision": {"verdict": verdict, "checks": checks},
            "limitations": [
                "subaccounts use fixed initial capital and are not rebalanced across sleeves",
                "analyst data is source-bounded and the interval is not virgin OOS",
            ],
        }
    )


def render_markdown(payload: dict) -> str:
    lines = [
        "# 分析师修正核心卫星组合结果", "",
        f"- verdict: **{payload['decision']['verdict']}**", "",
        "| Variant | CAGR | Sharpe | Max drawdown |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name, row in payload["variants"].items():
        metrics = row["metrics"]
        lines.append(f"| {name} | {metrics['cagr']:.2%} | {metrics['sharpe']:.3f} | {metrics['max_drawdown']:.2%} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision-nav", default="overall/a-share-analyst-revision-nav.csv")
    parser.add_argument("--assets", default="overall/a-share-multi-asset-etf-daily.csv")
    parser.add_argument("--start", default="2017-01-03")
    parser.add_argument("--end", default="2026-08-25")
    parser.add_argument("--out-json", default="overall/a-share-analyst-core-satellite.json")
    parser.add_argument("--out-md", default="overall/a-share-analyst-core-satellite.md")
    args = parser.parse_args(argv)
    payload = run(args.revision_nav, args.assets, args.start, args.end)
    Path(args.out_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = render_markdown(payload)
    Path(args.out_md).write_text(markdown + "\n", encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
