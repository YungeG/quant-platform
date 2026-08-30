"""Backtest PIT quarterly fundamental momentum."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from experiments.quarterly_portfolio import Bar, BasketConfig, simulate_basket
from experiments.run_analyst_revision import FOLDS, benchmark_returns, json_clean, month_ends
from experiments.run_largecap_lowvol import summarize_basket
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.research.combination import repair_point_in_time_size


def load_fundamentals(path: str) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype={"ts_code": str, "ann_date": str, "end_date": str})
    frame["Symbol"] = frame["ts_code"].str[:6]
    frame["ann_date"] = pd.to_datetime(frame["ann_date"], errors="coerce")
    frame["end_date"] = pd.to_datetime(frame["end_date"], errors="coerce")
    for column in ("q_sales_yoy", "q_roe", "q_ocf_to_sales", "update_flag"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    quarter = frame["end_date"].dt.quarter
    frame["period_index"] = frame["end_date"].dt.year * 4 + quarter
    return frame.dropna(subset=["ann_date", "end_date", "period_index"])


def momentum_snapshot(data: pd.DataFrame, universe: pd.DataFrame, day: pd.Timestamp) -> pd.DataFrame:
    visible = data[data["ann_date"] <= day].sort_values(
        ["Symbol", "period_index", "ann_date", "update_flag"]
    ).drop_duplicates(["Symbol", "period_index"], keep="last")
    current = visible.sort_values(["Symbol", "period_index"]).drop_duplicates("Symbol", keep="last")
    previous = visible[["Symbol", "period_index", "q_sales_yoy"]].rename(
        columns={"period_index": "previous_index", "q_sales_yoy": "previous_sales_yoy"}
    )
    year_ago = visible[["Symbol", "period_index", "q_roe", "q_ocf_to_sales"]].rename(
        columns={"period_index": "year_ago_index", "q_roe": "year_ago_roe", "q_ocf_to_sales": "year_ago_ocf"}
    )
    current = current.copy()
    current["previous_index"] = current["period_index"] - 1
    current["year_ago_index"] = current["period_index"] - 4
    current = current.merge(previous, on=["Symbol", "previous_index"], how="left").merge(
        year_ago, on=["Symbol", "year_ago_index"], how="left"
    )
    current["sales_acceleration"] = current["q_sales_yoy"] - current["previous_sales_yoy"]
    current["roe_improvement"] = current["q_roe"] - current["year_ago_roe"]
    current["cash_improvement"] = current["q_ocf_to_sales"] - current["year_ago_ocf"]
    frame = universe.merge(
        current[["Symbol", "sales_acceleration", "roe_improvement", "cash_improvement"]],
        on="Symbol",
        how="left",
    )
    group_size = frame.groupby("industry")["Symbol"].transform("count")
    for source, target in (
        ("sales_acceleration", "sales_pct"),
        ("roe_improvement", "roe_pct"),
        ("cash_improvement", "cash_pct"),
    ):
        frame[target] = frame.groupby("industry")[source].rank(pct=True, method="average")
    frame["momentum_score"] = frame[["sales_pct", "roe_pct", "cash_pct"]].mean(axis=1, skipna=False)
    frame.loc[group_size < 5, "momentum_score"] = np.nan
    return frame


def ic_summary(rows: pd.DataFrame) -> dict:
    monthly = []
    for day, group in rows.dropna(subset=["momentum_score", "active20"]).groupby("signal_date"):
        if len(group) < 20 or group["momentum_score"].nunique() < 2:
            continue
        monthly.append({"signal_date": day, "ic": float(spearmanr(group["momentum_score"], group["active20"]).statistic), "count": len(group)})
    frame = pd.DataFrame(monthly)
    mean = float(frame["ic"].mean()) if len(frame) else 0.0
    std = float(frame["ic"].std(ddof=1)) if len(frame) > 1 else 0.0
    folds = {}
    for name, start, end in FOLDS:
        fold = frame[frame["signal_date"].between(start, end)] if len(frame) else frame
        folds[name] = {"count": len(fold), "mean_ic": float(fold["ic"].mean()) if len(fold) else 0.0}
    return {
        "count": len(frame), "mean": mean, "median": float(frame["ic"].median()) if len(frame) else 0.0,
        "win_rate": float((frame["ic"] > 0).mean()) if len(frame) else 0.0,
        "t_stat": mean / (std / np.sqrt(len(frame))) if std > 0 else 0.0,
        "average_coverage": float(frame["count"].mean()) if len(frame) else 0.0, "folds": folds,
    }


def build_inputs(start: str, end: str, data: pd.DataFrame) -> tuple:
    cfg = Config()
    connection = connect(cfg, read_only=True)
    try:
        built = load_or_build_panel(cfg, "2014-11-27", end, con=connection)
    finally:
        connection.close()
    panel = repair_point_in_time_size(built.df)
    panel["TradingDay"] = pd.to_datetime(panel["TradingDay"])
    panel = panel.sort_values(["Symbol", "TradingDay"]).reset_index(drop=True)
    grouped = panel.groupby("Symbol", sort=False)
    panel["_fwd20"] = grouped["adj_open"].shift(-21) / grouped["adj_open"].shift(-1) - 1.0
    adv_pct = panel.groupby("TradingDay")["adv20"].rank(pct=True, method="first")
    panel["practical"] = (~panel["suspended"].fillna(True)) & (panel["age"] >= 252) & (panel["Close"] >= 5) & (panel["Volume"] > 0) & panel["CircMV"].notna() & (adv_pct > 0.50)
    sessions = sorted(panel.loc[panel["TradingDay"] >= pd.Timestamp(start), "TradingDay"].drop_duplicates())
    targets = {}
    signals = []
    all_symbols: set[str] = set()
    for day in month_ends(sessions):
        universe = panel[(panel["TradingDay"] == day) & panel["practical"]].nlargest(500, "CircMV")
        if len(universe) < 300:
            continue
        scored = momentum_snapshot(data, universe, day)
        benchmark = float(scored["_fwd20"].mean())
        scored["active20"] = scored["_fwd20"] - benchmark
        signals.extend(
            {"signal_date": day, "symbol": row.Symbol, "momentum_score": row.momentum_score, "active20": row.active20}
            for row in scored.itertuples(index=False)
        )
        selected = scored.dropna(subset=["momentum_score"]).sort_values(
            ["momentum_score", "Symbol"], ascending=[False, True]
        ).head(30)
        targets[day.date().isoformat()] = selected["Symbol"].astype(str).tolist()
        all_symbols.update(targets[day.date().isoformat()])
    columns = ["TradingDay", "Symbol", "adj_open", "adj_close", "Open", "High", "Low", "Close", "Volume", "PctChange"]
    market = panel[panel["Symbol"].isin(all_symbols) & panel["TradingDay"].isin(sessions)][columns].set_index(["TradingDay", "Symbol"]).sort_index()
    dates = [day.date().isoformat() for day in sessions]
    def lookup(date: str, symbol: str) -> Bar | None:
        try: row = market.loc[(pd.Timestamp(date), symbol)]
        except KeyError: return None
        return Bar(adj_open=float(row["adj_open"]), adj_close=float(row["adj_close"]), raw_open=float(row["Open"]), raw_high=float(row["High"]), raw_low=float(row["Low"]), raw_close=float(row["Close"]), volume=float(row["Volume"]), pct_change=float(row["PctChange"]))
    metadata = {"panel_version": built.version_hash, "decisions": len(targets), "selected_symbols": len(all_symbols)}
    del panel; gc.collect()
    return dates, lookup, targets, pd.DataFrame(signals), metadata


def run(data_path: str, start: str, end: str, benchmark_path: str) -> dict:
    data = load_fundamentals(data_path)
    dates, lookup, targets, signals, metadata = build_inputs(start, end, data)
    config = BasketConfig(name="fundamental_momentum", target_count=30, initial_nav=400_000, buy_cost=0.00155, sell_cost=0.00155)
    gross_config = BasketConfig(name="fundamental_momentum_gross", target_count=30, initial_nav=400_000, buy_cost=0, sell_cost=0)
    result = simulate_basket(dates, lookup, targets, config); gross = simulate_basket(dates, lookup, targets, gross_config)
    benchmark = benchmark_returns(benchmark_path, dates)
    portfolio = summarize_basket(result, gross, benchmark, config, folds=FOLDS)
    ic = ic_summary(signals)
    checks = {
        "mean_ic": ic["mean"] >= 0.02, "t_stat": ic["t_stat"] >= 2,
        "ic_folds": sum(f["mean_ic"] > 0 for f in ic["folds"].values()) >= 2,
        "cagr": portfolio["metrics"]["cagr"] >= 0.10, "excess": portfolio["excess_cagr"] >= 0.02,
        "sharpe": portfolio["metrics"]["sharpe"] >= 0.8, "drawdown": portfolio["metrics"]["max_drawdown"] >= -0.30,
        "portfolio_folds": portfolio["positive_excess_folds"] == 3, "turnover": portfolio["annual_turnover"] <= 6,
    }
    verdict = "GO" if all(checks.values()) else ("MARGINAL" if ic["mean"] > 0 and portfolio["excess_cagr"] > 0 else "NO-GO")
    return json_clean({"study":"a-share-fundamental-momentum-v1","data":{**metadata,"fundamental_rows":len(data)},"ic":ic,"portfolio":portfolio,"decision":{"verdict":verdict,"checks":checks}})


def main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser();p.add_argument("--data",default="overall/a-share-fundamental-momentum.csv");p.add_argument("--start",default="2017-01-03");p.add_argument("--end",default="2026-08-26");p.add_argument("--benchmark",default="overall/a-share-multi-asset-etf-daily.csv");p.add_argument("--out-json",default="overall/a-share-fundamental-momentum.json");p.add_argument("--out-md",default="overall/a-share-fundamental-momentum.md");a=p.parse_args(argv)
    payload=run(a.data,a.start,a.end,a.benchmark);Path(a.out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    m=payload["portfolio"]["metrics"];text=f"# A股基本面动量结果\n\n- verdict: **{payload['decision']['verdict']}**\n- mean IC: {payload['ic']['mean']:.4f}; t: {payload['ic']['t_stat']:.2f}\n- CAGR/Sharpe/MDD: {m['cagr']:.2%} / {m['sharpe']:.3f} / {m['max_drawdown']:.2%}\n";Path(a.out_md).write_text(text,encoding="utf-8");print(text);return 0
if __name__=="__main__": raise SystemExit(main())
