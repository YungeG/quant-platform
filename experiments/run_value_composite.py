"""Run the frozen daily-PIT EP/BP quarterly value study."""

from __future__ import annotations

import argparse
import gc
import json
import sys
from dataclasses import replace
from pathlib import Path

QUANT_REPO = Path("/home/ygguo/agent-projs/quant-claude")
if str(QUANT_REPO) not in sys.path:
    sys.path.insert(0, str(QUANT_REPO))

import numpy as np
import pandas as pd

from experiments.lowturn_livermore import Bar
from experiments.quarterly_portfolio import BasketConfig, simulate_basket
from experiments.run_largecap_lowvol import INITIAL_NAV, simulate_index, summarize_basket
from experiments.run_lowturn_livermore import _clean, _metrics, _returns
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.preprocess.pipeline import preprocess_factor
from factormine.research.combination import repair_point_in_time_size


FOLDS = (
    ("2016-2019", "2016-01-01", "2019-12-31"),
    ("2020-2022", "2020-01-01", "2022-12-31"),
    ("2023-2026", "2023-01-01", "2026-12-31"),
)


def build_inputs(start: str, end: str) -> tuple:
    cfg = Config()
    connection = connect(cfg, read_only=True)
    try:
        built = load_or_build_panel(cfg, "2014-11-27", end, con=connection)
    finally:
        connection.close()
    panel = repair_point_in_time_size(built.df)
    panel["TradingDay"] = pd.to_datetime(panel["TradingDay"])
    adv_pct = panel.groupby("TradingDay")["adv20"].rank(pct=True, method="first")
    panel["practical"] = (
        (~panel["suspended"].fillna(True))
        & (panel["age"] >= 252)
        & (panel["Close"] >= 5.0)
        & (panel["Volume"] > 0)
        & panel["CircMV"].notna()
        & (adv_pct > 0.50)
    )
    sessions = sorted(
        panel.loc[panel["TradingDay"] >= pd.Timestamp(start), "TradingDay"].drop_duplicates()
    )
    decision_dates = sessions[::63]
    decisions = panel[panel["TradingDay"].isin(decision_dates) & panel["practical"]].copy()
    decisions = (
        decisions.sort_values(["TradingDay", "CircMV"], ascending=[True, False])
        .groupby("TradingDay", group_keys=False)
        .head(500)
        .copy()
    )
    connection = connect(cfg, read_only=True)
    try:
        decision_frame = pd.DataFrame({"TradingDay": decision_dates})
        connection.register("_value_decision_dates", decision_frame)
        valuation = connection.execute(
            """
            select f.Symbol, f.TradingDay, f.PETTM, f.PB
            from FundamentalData f
            join _value_decision_dates d on f.TradingDay = d.TradingDay
            """
        ).df()
        connection.unregister("_value_decision_dates")
    finally:
        connection.close()
    valuation["TradingDay"] = pd.to_datetime(valuation["TradingDay"])
    decisions = decisions.merge(
        valuation,
        on=["TradingDay", "Symbol"],
        how="left",
        validate="one_to_one",
    )
    scored_decisions = decisions[(decisions["PETTM"] > 0) & (decisions["PB"] > 0)].copy()
    scored_decisions["_ep"] = 1.0 / scored_decisions["PETTM"]
    scored_decisions["_bp"] = 1.0 / scored_decisions["PB"]
    scored_decisions["selectable"] = True
    scored_decisions["_ep_z"] = preprocess_factor(scored_decisions, "_ep").reindex(
        scored_decisions.index
    )
    scored_decisions["_bp_z"] = preprocess_factor(scored_decisions, "_bp").reindex(
        scored_decisions.index
    )
    scored_decisions["_composite"] = (
        0.5 * scored_decisions["_ep_z"] + 0.5 * scored_decisions["_bp_z"]
    )

    targets = {"composite_50": {}, "ep_50": {}, "bp_50": {}}
    cap_targets: dict[str, dict[str, float]] = {}
    equal_targets: dict[str, dict[str, float]] = {}
    all_symbols: set[str] = set()
    coverage = []
    for day, group in decisions.groupby("TradingDay"):
        key = pd.Timestamp(day).date().isoformat()
        scored = scored_decisions[
            scored_decisions["TradingDay"] == pd.Timestamp(day)
        ].dropna(subset=["_ep_z", "_bp_z", "_composite"])
        if len(scored) < 100:
            continue
        targets["composite_50"][key] = (
            scored.sort_values(["_composite", "Symbol"], ascending=[False, True])["Symbol"]
            .astype(str)
            .head(50)
            .tolist()
        )
        targets["ep_50"][key] = (
            scored.sort_values(["_ep_z", "Symbol"], ascending=[False, True])["Symbol"]
            .astype(str)
            .head(50)
            .tolist()
        )
        targets["bp_50"][key] = (
            scored.sort_values(["_bp_z", "Symbol"], ascending=[False, True])["Symbol"]
            .astype(str)
            .head(50)
            .tolist()
        )
        valid_cap = group[group["CircMV"] > 0]
        cap_sum = float(valid_cap["CircMV"].sum())
        cap_targets[key] = {
            str(symbol): float(value / cap_sum)
            for symbol, value in zip(valid_cap["Symbol"], valid_cap["CircMV"], strict=True)
        }
        equal_targets[key] = {str(symbol): 1.0 / len(group) for symbol in group["Symbol"]}
        all_symbols.update(group["Symbol"].astype(str))
        coverage.append(len(scored) / len(group))

    columns = [
        "TradingDay",
        "Symbol",
        "adj_open",
        "adj_close",
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
        "PctChange",
    ]
    market = panel[
        panel["Symbol"].isin(all_symbols) & panel["TradingDay"].isin(sessions)
    ][columns].copy()
    market = market.set_index(["TradingDay", "Symbol"]).sort_index()
    dates = [pd.Timestamp(day).date().isoformat() for day in sessions]
    metadata = {
        "panel_version": built.version_hash,
        "rows": int(len(panel)),
        "start": dates[0],
        "end": dates[-1],
        "rebalance_count": len(cap_targets),
        "symbols": len(all_symbols),
        "average_scored_coverage": float(np.mean(coverage)) if coverage else 0.0,
    }
    del panel, decisions, scored_decisions, valuation
    gc.collect()

    def lookup(date: str, symbol: str) -> Bar | None:
        try:
            row = market.loc[(pd.Timestamp(date), symbol)]
        except KeyError:
            return None
        return Bar(
            adj_open=float(row["adj_open"]),
            adj_close=float(row["adj_close"]),
            raw_open=float(row["Open"]),
            raw_high=float(row["High"]),
            raw_low=float(row["Low"]),
            raw_close=float(row["Close"]),
            volume=float(row["Volume"]),
            pct_change=float(row["PctChange"]),
        )

    return dates, lookup, targets, cap_targets, equal_targets, metadata


def decide(main: dict) -> dict:
    benchmark = main["benchmark_metrics"]
    checks = {
        "cagr_margin": main["excess_cagr"] >= 0.01,
        "sharpe_margin": main["metrics"]["sharpe"] >= benchmark["sharpe"] + 0.10,
        "drawdown": main["metrics"]["max_drawdown"] >= benchmark["max_drawdown"] - 0.05,
        "positive_excess_folds": main["positive_excess_folds"] >= 2,
        "best_year_independence": main["cagr_excluding_best_year"] >= 0,
        "cost_retention": main["gross_to_net_cagr_retention"] >= 0.90,
        "turnover": main["annual_turnover"] <= 2.0,
        "execution": (
            main["average_positions"] >= 40
            and main["execution_failure_rate"] <= 0.10
            and main["missing_valuation_rate"] <= 0.02
        ),
    }
    if all(checks.values()):
        verdict = "GO"
    elif main["metrics"]["cagr"] > 0 and main["excess_cagr"] > 0:
        verdict = "MARGINAL"
    else:
        verdict = "NO-GO"
    return {"verdict": verdict, "checks": checks}


def render_markdown(payload: dict) -> str:
    lines = [
        "# A股PIT价值复合策略回测结果",
        "",
        f"- verdict: **{payload['decision']['verdict']}**",
        f"- data: {payload['data']['start']}—{payload['data']['end']}",
        f"- rebalances: {payload['data']['rebalance_count']}",
        "",
        "| Variant | CAGR | Sharpe | Max drawdown | Excess CAGR | Avg positions | Turnover |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name in ("composite_50", "ep_50", "bp_50"):
        row = payload["variants"][name]
        metrics = row["metrics"]
        lines.append(
            f"| {name} | {metrics['cagr']:.2%} | {metrics['sharpe']:.3f} | "
            f"{metrics['max_drawdown']:.2%} | {row['excess_cagr']:.2%} | "
            f"{row['average_positions']:.1f} | {row['annual_turnover']:.2f} |"
        )
    for name in ("top500_cap", "top500_equal"):
        metrics = payload["benchmarks"][name]
        lines.append(
            f"| {name} | {metrics['cagr']:.2%} | {metrics['sharpe']:.3f} | "
            f"{metrics['max_drawdown']:.2%} | 0.00% | 500 | 0.00 |"
        )
    lines.extend(["", "## Gate", ""])
    for name, passed in payload["decision"]["checks"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} `{name}`")
    return "\n".join(lines)


def run(start: str, end: str) -> dict:
    dates, lookup, targets, cap_targets, equal_targets, metadata = build_inputs(start, end)
    cap_nav = simulate_index(dates, lookup, cap_targets)
    equal_nav = simulate_index(dates, lookup, equal_targets)
    cap_returns = _returns(cap_nav, INITIAL_NAV)
    equal_returns = _returns(equal_nav, INITIAL_NAV)
    configs = {
        "composite_50": BasketConfig(name="composite_50", target_count=50),
        "ep_50": BasketConfig(name="ep_50", target_count=50),
        "bp_50": BasketConfig(name="bp_50", target_count=50),
    }
    variants = {}
    for name, config in configs.items():
        net = simulate_basket(dates, lookup, targets[name], config)
        gross = simulate_basket(
            dates,
            lookup,
            targets[name],
            replace(config, buy_cost=0.0, sell_cost=0.0),
        )
        variants[name] = summarize_basket(net, gross, cap_returns, config, folds=FOLDS)
    decision = decide(variants["composite_50"])
    return _clean(
        {
            "study": "a-share-pit-value-composite-v1",
            "data": metadata,
            "rules": {
                "universe": "top500 float market cap within top-half ADV and positive PETTM/PB",
                "factors": ["EP=1/PETTM", "BP=1/PB"],
                "preprocess": "MAD winsorize, SW L1 industry and log-size neutralize, z-score",
                "rebalance": "every 63 sessions, next open",
            },
            "variants": variants,
            "benchmarks": {
                "top500_cap": _metrics(cap_returns),
                "top500_equal": _metrics(equal_returns),
            },
            "decision": decision,
            "limitations": [
                "ROE/ROA quality data is unavailable point-in-time and is not used",
                "historical ST authority is unavailable",
                "stock adjustment is reconstructed from stored percentage changes",
                "the interval is not virgin OOS",
            ],
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2016-01-01")
    parser.add_argument("--end", default="2026-08-25")
    parser.add_argument("--out-json", default="overall/a-share-value-composite.json")
    parser.add_argument("--out-md", default="overall/a-share-value-composite.md")
    args = parser.parse_args(argv)
    payload = run(args.start, args.end)
    Path(args.out_json).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown = render_markdown(payload)
    Path(args.out_md).write_text(markdown + "\n", encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
