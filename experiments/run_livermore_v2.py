"""Run the frozen A-share Livermore V2 staged study."""

from __future__ import annotations

import argparse
import gc
import json
import math
import sys
from dataclasses import replace
from pathlib import Path

QUANT_REPO = Path("/home/ygguo/agent-projs/quant-claude")
if str(QUANT_REPO) not in sys.path:
    sys.path.insert(0, str(QUANT_REPO))

import numpy as np
import pandas as pd

from experiments.lowturn_livermore import Bar, Candidate, StrategyConfig, simulate
from experiments.run_lowturn_livermore import FOLDS, _clean, _metrics, summarize
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.research.combination import repair_point_in_time_size


MARKET_CODE = "801003.SI"


def _load_industry_indices(connection, start: str, end: str) -> pd.DataFrame:
    return connection.execute(
        """
        with l1 as (
            select distinct L1Code as TSCode, L1Name as IndustryName
            from IndustryMemberHistoryData
        ), rows as (
            select d.TradeDate, d.TSCode, l1.IndustryName, d.PctChange
            from IndustryDailyData d
            join l1 on d.TSCode = l1.TSCode
            where d.TradeDate between ? and ?
            union all
            select d.TradeDate, d.TSCode, 'MARKET' as IndustryName, d.PctChange
            from IndustryDailyData d
            where d.TSCode = ? and d.TradeDate between ? and ?
        )
        select * from rows
        """,
        [start, end, MARKET_CODE, start, end],
    ).df()


def _index_states(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = frame.copy()
    data["TradeDate"] = pd.to_datetime(data["TradeDate"])
    data = data.drop_duplicates(["TradeDate", "TSCode"], keep="last")
    data = data.sort_values(["TSCode", "TradeDate"])
    data["index_value"] = data.groupby("TSCode", sort=False)["PctChange"].transform(
        lambda series: (1.0 + series.fillna(0.0) / 100.0).cumprod()
    )
    data["ma60"] = data.groupby("TSCode", sort=False)["index_value"].transform(
        lambda series: series.rolling(60, min_periods=60).mean()
    )
    data["ret60"] = data.groupby("TSCode", sort=False)["index_value"].transform(
        lambda series: series / series.shift(60) - 1.0
    )
    market = data[data["TSCode"] == MARKET_CODE].copy()
    market["ma120"] = market["index_value"].rolling(120, min_periods=120).mean()
    industries = data[data["TSCode"] != MARKET_CODE].copy()
    industries = industries.merge(
        market[["TradeDate", "ret60"]].rename(columns={"ret60": "market_ret60"}),
        on="TradeDate",
        how="left",
    )
    industries["confirmed"] = (
        (industries["index_value"] > industries["ma60"])
        & (industries["ret60"] > industries["market_ret60"])
    )
    return market, industries


def build_inputs(start: str, end: str) -> tuple:
    warmup_start = (pd.Timestamp(start) - pd.Timedelta(days=400)).date().isoformat()
    cfg = Config()
    connection = connect(cfg, read_only=True)
    try:
        built = load_or_build_panel(cfg, warmup_start, end, con=connection)
        industry_raw = _load_industry_indices(connection, warmup_start, end)
    finally:
        connection.close()

    panel = repair_point_in_time_size(built.df)
    panel["TradingDay"] = pd.to_datetime(panel["TradingDay"])
    panel = panel.sort_values(["Symbol", "TradingDay"]).reset_index(drop=True)
    grouped = panel.groupby("Symbol", sort=False)
    panel["_daily_return"] = grouped["adj_close"].pct_change(fill_method=None)
    panel["_ma60"] = grouped["adj_close"].transform(
        lambda series: series.rolling(60, min_periods=60).mean()
    )
    panel["_prior60_high"] = grouped["adj_close"].transform(
        lambda series: series.shift(1).rolling(60, min_periods=60).max()
    )
    panel["_ret60"] = grouped["adj_close"].transform(
        lambda series: series / series.shift(60) - 1.0
    )
    previous_close = grouped["adj_close"].shift(1)
    true_range = pd.concat(
        [
            panel["adj_high"] - panel["adj_low"],
            (panel["adj_high"] - previous_close).abs(),
            (panel["adj_low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    panel["_atr20"] = true_range.groupby(panel["Symbol"], sort=False).transform(
        lambda series: series.rolling(20, min_periods=20).mean()
    )

    size_pct = panel.groupby("TradingDay")["log_size"].rank(pct=True, method="first")
    adv_pct = panel.groupby("TradingDay")["adv20"].rank(pct=True, method="first")
    panel["practical"] = (
        (~panel["suspended"].fillna(True))
        & (panel["age"] >= 252)
        & (panel["Close"] >= 5.0)
        & (panel["Volume"] > 0)
        & panel["log_size"].notna()
        & panel["_ret60"].notna()
        & panel["_atr20"].notna()
        & (size_pct > 0.50)
        & (adv_pct > 0.50)
    )
    panel["_benchmark_eligible"] = (
        panel.groupby("Symbol", sort=False)["practical"].shift(1).fillna(False).astype(bool)
    )
    benchmark = (
        panel[panel["_benchmark_eligible"]]
        .groupby("TradingDay")["_daily_return"]
        .mean()
        .fillna(0.0)
    )
    breadth_base = (
        (~panel["suspended"].fillna(True))
        & (panel["age"] >= 60)
        & panel["_ma60"].notna()
        & (panel["Volume"] > 0)
    )
    breadth = (
        (panel.loc[breadth_base, "adj_close"] > panel.loc[breadth_base, "_ma60"])
        .groupby(panel.loc[breadth_base, "TradingDay"])
        .mean()
    )

    market_index, industries = _index_states(industry_raw)
    market_index = market_index.set_index("TradeDate").sort_index()
    market_index["breadth"] = breadth.reindex(market_index.index)
    market_index["trend_on"] = market_index["index_value"] > market_index["ma120"]
    market_index["breadth_on"] = market_index["breadth"] > 0.50
    market_index["state"] = np.select(
        [
            market_index["trend_on"] & market_index["breadth_on"],
            market_index["trend_on"] | market_index["breadth_on"],
        ],
        ["ON", "WATCH"],
        default="OFF",
    )
    market_ret60 = market_index["ret60"].to_dict()
    market_state = market_index["state"].to_dict()
    industry_confirm = {
        (pd.Timestamp(row.TradeDate), str(row.IndustryName)): bool(row.confirmed)
        for row in industries.itertuples(index=False)
    }

    simulation_sessions = sorted(
        panel.loc[panel["TradingDay"] >= pd.Timestamp(start), "TradingDay"].drop_duplicates()
    )
    decision_dates = set(simulation_sessions[::5])
    candidates: dict[str, list[Candidate]] = {}
    candidate_symbols: set[str] = set()
    decisions = panel[panel["TradingDay"].isin(decision_dates) & panel["practical"]].copy()
    for day, group in decisions.groupby("TradingDay"):
        if market_state.get(pd.Timestamp(day), "OFF") != "ON":
            continue
        market_return = market_ret60.get(pd.Timestamp(day))
        if market_return is None or not np.isfinite(market_return):
            continue
        eligible = group[
            (group["adj_close"] > group["_prior60_high"])
            & (group["_ret60"] > market_return)
            & (group["PctChange"] < 7.0)
        ].copy()
        if eligible.empty:
            continue
        eligible = eligible[
            [
                bool(industry_confirm.get((pd.Timestamp(day), str(industry)), False))
                for industry in eligible["industry"]
            ]
        ]
        if eligible.empty:
            continue
        eligible["_relative_strength"] = eligible["_ret60"] - market_return
        eligible["_risk_pct"] = np.clip(
            2.0 * eligible["_atr20"] / eligible["adj_close"], 0.06, 0.12
        )
        ranked = eligible.sort_values(
            ["_relative_strength", "Symbol"], ascending=[False, True]
        ).head(20)
        rows = [
            Candidate(
                symbol=str(symbol),
                score=float(score),
                risk_pct=float(risk_pct),
                max_entry_price=float(close * (1.0 + 0.5 * risk_pct)),
            )
            for symbol, score, risk_pct, close in zip(
                ranked["Symbol"],
                ranked["_relative_strength"],
                ranked["_risk_pct"],
                ranked["adj_close"],
                strict=True,
            )
        ]
        if rows:
            key = pd.Timestamp(day).date().isoformat()
            candidates[key] = rows
            candidate_symbols.update(candidate.symbol for candidate in rows)

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
        panel["Symbol"].isin(candidate_symbols)
        & panel["TradingDay"].isin(simulation_sessions)
    ][columns].copy()
    market = market.set_index(["TradingDay", "Symbol"]).sort_index()
    dates = [pd.Timestamp(day).date().isoformat() for day in simulation_sessions]
    benchmark_map = {
        pd.Timestamp(day).date().isoformat(): float(value)
        for day, value in benchmark.items()
        if day >= pd.Timestamp(start) and np.isfinite(value)
    }
    add_allowed = {
        date: market_state.get(pd.Timestamp(date), "OFF") == "ON" for date in dates
    }
    state_counts = pd.Series(
        [market_state.get(pd.Timestamp(date), "OFF") for date in dates]
    ).value_counts()
    metadata = {
        "panel_version": built.version_hash,
        "rows": int(len(panel)),
        "start": dates[0],
        "end": dates[-1],
        "candidate_signal_days": len(candidates),
        "candidate_symbols": len(candidate_symbols),
        "average_candidates_per_signal_day": (
            float(np.mean([len(rows) for rows in candidates.values()])) if candidates else 0.0
        ),
        "market_state_days": {str(key): int(value) for key, value in state_counts.items()},
    }
    del panel, decisions, industry_raw, market_index, industries
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

    return dates, lookup, candidates, benchmark_map, add_allowed, metadata


def decide(entry: dict, managed: dict, full: dict) -> dict:
    entry_gate = entry["excess_cagr"] > 0 and entry["positive_excess_folds"] >= 2
    risk_gate = (
        managed["metrics"]["sharpe"] > entry["metrics"]["sharpe"]
        or abs(managed["metrics"]["max_drawdown"])
        <= abs(entry["metrics"]["max_drawdown"]) * 0.80
    )
    pyramid_gate = (
        (
            full["metrics"]["cagr"] > managed["metrics"]["cagr"]
            or full["metrics"]["sharpe"] > managed["metrics"]["sharpe"]
        )
        and full["metrics"]["max_drawdown"] >= managed["metrics"]["max_drawdown"] - 0.05
    )
    full_checks = {
        "excess_cagr": full["excess_cagr"] > 0,
        "sharpe": full["metrics"]["sharpe"] >= 0.60,
        "max_drawdown": full["metrics"]["max_drawdown"] >= -0.35,
        "positive_excess_folds": full["positive_excess_folds"] >= 2,
        "best_year_independence": full["cagr_excluding_best_year"] >= 0,
        "cost_retention": full["gross_to_net_cagr_retention"] >= 0.70,
        "execution": full["blocked_buy_rate"] <= 0.10 and full["missing_valuation_rate"] <= 0.02,
    }
    if entry_gate and risk_gate and pyramid_gate and all(full_checks.values()):
        verdict = "GO"
    elif entry_gate and full["metrics"]["cagr"] > 0 and full["metrics"]["sharpe"] > 0:
        verdict = "MARGINAL"
    else:
        verdict = "NO-GO"
    return {
        "verdict": verdict,
        "entry_gate": entry_gate,
        "risk_management_gate": risk_gate,
        "pyramiding_gate": pyramid_gate,
        "full_checks": full_checks,
    }


def render_markdown(payload: dict) -> str:
    lines = [
        "# A股 Livermore V2 回测结果",
        "",
        f"- verdict: **{payload['decision']['verdict']}**",
        f"- data: {payload['data']['start']}—{payload['data']['end']}",
        f"- candidate signal days: {payload['data']['candidate_signal_days']}",
        "",
        "| Variant | CAGR | Sharpe | Max drawdown | Excess CAGR | Avg exposure |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key in ("entry_fixed_20", "risk_managed", "full_livermore", "benchmark"):
        row = payload["variants"][key]
        metrics = row["metrics"]
        lines.append(
            f"| {key} | {metrics['cagr']:.2%} | {metrics['sharpe']:.3f} | "
            f"{metrics['max_drawdown']:.2%} | {row.get('excess_cagr', 0.0):.2%} | "
            f"{row.get('average_exposure', 1.0):.2%} |"
        )
    decision = payload["decision"]
    lines.extend(
        [
            "",
            "## Staged gates",
            "",
            f"- {'PASS' if decision['entry_gate'] else 'FAIL'} `entry_gate`",
            f"- {'PASS' if decision['risk_management_gate'] else 'FAIL'} `risk_management_gate`",
            f"- {'PASS' if decision['pyramiding_gate'] else 'FAIL'} `pyramiding_gate`",
        ]
    )
    for name, passed in decision["full_checks"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} `{name}`")
    return "\n".join(lines)


def run(start: str, end: str) -> dict:
    dates, lookup, candidates, benchmark, add_allowed, metadata = build_inputs(start, end)
    configs = {
        "entry_fixed_20": StrategyConfig(
            name="entry_fixed_20",
            initial_fraction=0.25,
            pyramid=False,
            max_units=1,
            stop_enabled=False,
            fixed_hold_days=20,
            buy_retry_days=1,
        ),
        "risk_managed": StrategyConfig(
            name="risk_managed",
            pyramid=False,
            max_units=1,
            risk_sized=True,
            buy_retry_days=1,
        ),
        "full_livermore": StrategyConfig(
            name="full_livermore",
            risk_sized=True,
            pyramid=True,
            max_units=3,
            buy_retry_days=1,
        ),
    }
    variants = {}
    for name, config in configs.items():
        net = simulate(dates, lookup, candidates, benchmark, config, add_allowed=add_allowed)
        gross = simulate(
            dates,
            lookup,
            candidates,
            benchmark,
            replace(config, buy_cost=0.0, sell_cost=0.0),
            add_allowed=add_allowed,
        )
        variants[name] = summarize(net, gross, config)
    benchmark_returns = pd.Series(
        [benchmark.get(date, 0.0) for date in dates], index=pd.to_datetime(dates), dtype=float
    )
    variants["benchmark"] = {
        "metrics": _metrics(benchmark_returns),
        "excess_cagr": 0.0,
        "average_exposure": 1.0,
    }
    decision = decide(
        variants["entry_fixed_20"], variants["risk_managed"], variants["full_livermore"]
    )
    return _clean(
        {
            "study": "a-share-livermore-v2",
            "data": metadata,
            "rules": {
                "market": "SW A index above MA120 and breadth above 50%",
                "industry": "above MA60 and 60d return above market",
                "entry": "prior-60d-high breakout and positive 60d relative strength",
                "risk": "R=clamp(2*ATR20/close,6%,12%); 0.5% NAV risk per unit",
                "adds": ["+1R", "+2R"],
                "trailing": "highest close minus 1.5R after +1R",
            },
            "variants": variants,
            "decision": decision,
            "limitations": [
                "historical ST status authority is unavailable",
                "industry and market indices use stored daily percentage changes",
                "PctChange-reconstructed stock adjustment replaces a corporate-action event stream",
                "the interval is not virgin OOS",
            ],
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2016-01-01")
    parser.add_argument("--end", default="2026-08-25")
    parser.add_argument("--out-json", default="overall/a-share-livermore-v2.json")
    parser.add_argument("--out-md", default="overall/a-share-livermore-v2.md")
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
