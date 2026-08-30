"""Test a PIT annual-quality filter on the analyst-revision stock sleeve."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from experiments.quarterly_portfolio import Bar, BasketConfig, simulate_basket
from experiments.run_analyst_revision import (
    FOLDS,
    benchmark_returns,
    consensus_revisions,
    load_reports,
    month_ends,
)
from experiments.run_largecap_lowvol import summarize_basket
from experiments.run_lowturn_livermore import _clean
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.research.combination import repair_point_in_time_size


def load_quality(path: str) -> pd.DataFrame:
    quality = pd.read_csv(path, dtype={"ts_code": str, "ann_date": str, "end_date": str})
    quality["Symbol"] = quality["ts_code"].str[:6]
    quality["ann_date"] = pd.to_datetime(quality["ann_date"], errors="coerce")
    quality["end_date"] = pd.to_datetime(quality["end_date"], errors="coerce")
    for column in ("roe_waa", "grossprofit_margin", "debt_to_assets", "update_flag"):
        quality[column] = pd.to_numeric(quality[column], errors="coerce")
    return quality.dropna(subset=["ann_date", "end_date"])


def quality_snapshot(quality: pd.DataFrame, universe: pd.DataFrame, day: pd.Timestamp) -> pd.DataFrame:
    visible = quality[quality["ann_date"] <= day].sort_values(
        ["Symbol", "end_date", "ann_date", "update_flag"]
    ).drop_duplicates("Symbol", keep="last")
    frame = universe.merge(
        visible[["Symbol", "roe_waa", "grossprofit_margin", "debt_to_assets"]],
        on="Symbol",
        how="left",
    )
    group_size = frame.groupby("industry")["Symbol"].transform("count")
    frame["roe_pct"] = frame.groupby("industry")["roe_waa"].rank(pct=True, method="average")
    frame["margin_pct"] = frame.groupby("industry")["grossprofit_margin"].rank(pct=True, method="average")
    frame["debt_pct"] = frame.groupby("industry")["debt_to_assets"].rank(
        pct=True, method="average", ascending=False
    )
    frame["quality_score"] = frame[["roe_pct", "margin_pct", "debt_pct"]].mean(axis=1, skipna=False)
    frame.loc[group_size < 5, "quality_score"] = np.nan
    return frame


def ic_summary(rows: pd.DataFrame) -> dict:
    monthly = []
    for day, group in rows.dropna(subset=["quality_score", "active20"]).groupby("signal_date"):
        if len(group) < 20 or group["quality_score"].nunique() < 2:
            continue
        monthly.append({"signal_date": day, "ic": float(spearmanr(group["quality_score"], group["active20"]).statistic), "count": len(group)})
    frame = pd.DataFrame(monthly)
    if frame.empty:
        return {"count": 0, "mean": 0.0, "median": 0.0, "win_rate": 0.0, "t_stat": 0.0, "folds": {}}
    mean = float(frame["ic"].mean())
    std = float(frame["ic"].std(ddof=1))
    folds = {}
    for name, start, end in FOLDS:
        fold = frame[frame["signal_date"].between(start, end)]
        folds[name] = {"count": len(fold), "mean_ic": float(fold["ic"].mean()) if len(fold) else 0.0}
    return {
        "count": len(frame),
        "mean": mean,
        "median": float(frame["ic"].median()),
        "win_rate": float((frame["ic"] > 0).mean()),
        "t_stat": mean / (std / np.sqrt(len(frame))) if std > 0 else 0.0,
        "average_coverage": float(frame["count"].mean()),
        "folds": folds,
    }


def build_inputs(start: str, end: str, reports: pd.DataFrame, quality: pd.DataFrame) -> tuple:
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
    panel["practical"] = (
        (~panel["suspended"].fillna(True))
        & (panel["age"] >= 252)
        & (panel["Close"] >= 5.0)
        & (panel["Volume"] > 0)
        & panel["CircMV"].notna()
        & (adv_pct > 0.50)
    )
    sessions = sorted(panel.loc[panel["TradingDay"] >= pd.Timestamp(start), "TradingDay"].drop_duplicates())
    targets = {}
    quality_rows = []
    all_symbols: set[str] = set()
    for day in month_ends(sessions):
        universe = panel[(panel["TradingDay"] == day) & panel["practical"]].nlargest(500, "CircMV")
        if len(universe) < 300:
            continue
        scored = quality_snapshot(quality, universe, day)
        benchmark = float(scored["_fwd20"].mean())
        scored["active20"] = scored["_fwd20"] - benchmark
        for row in scored.itertuples(index=False):
            quality_rows.append(
                {"signal_date": day, "symbol": row.Symbol, "quality_score": row.quality_score, "active20": row.active20}
            )
        cutoff = float(scored["quality_score"].quantile(0.30))
        revision = consensus_revisions(reports, day)
        candidates = scored.merge(revision, on="Symbol", how="inner")
        selected = candidates[
            (candidates["revision"] > 0)
            & candidates["quality_score"].notna()
            & (candidates["quality_score"] >= cutoff)
        ].sort_values(["revision", "current_count", "Symbol"], ascending=[False, False, True]).head(30)
        key = day.date().isoformat()
        targets[key] = selected["Symbol"].astype(str).tolist()
        all_symbols.update(targets[key])

    columns = ["TradingDay", "Symbol", "adj_open", "adj_close", "Open", "High", "Low", "Close", "Volume", "PctChange"]
    market = panel[
        panel["Symbol"].isin(all_symbols) & panel["TradingDay"].isin(sessions)
    ][columns].set_index(["TradingDay", "Symbol"]).sort_index()
    dates = [day.date().isoformat() for day in sessions]

    def lookup(date: str, symbol: str) -> Bar | None:
        try:
            row = market.loc[(pd.Timestamp(date), symbol)]
        except KeyError:
            return None
        return Bar(
            adj_open=float(row["adj_open"]), adj_close=float(row["adj_close"]), raw_open=float(row["Open"]),
            raw_high=float(row["High"]), raw_low=float(row["Low"]), raw_close=float(row["Close"]),
            volume=float(row["Volume"]), pct_change=float(row["PctChange"]),
        )

    metadata = {"panel_version": built.version_hash, "decisions": len(targets), "selected_symbols": len(all_symbols)}
    del panel
    gc.collect()
    return dates, lookup, targets, pd.DataFrame(quality_rows), metadata


def decide(quality_ic: dict, overlay: dict, baseline: dict) -> dict:
    checks = {
        "drawdown_improvement": overlay["metrics"]["max_drawdown"] >= baseline["metrics"]["max_drawdown"] + 0.05,
        "sharpe_improvement": overlay["metrics"]["sharpe"] >= baseline["metrics"]["sharpe"] + 0.10,
        "cagr_retention": overlay["metrics"]["cagr"] >= baseline["metrics"]["cagr"] - 0.015,
        "positive_excess_folds": overlay["positive_excess_folds"] == 3,
    }
    verdict = "GO" if all(checks.values()) else "NO-GO"
    return {"verdict": verdict, "checks": checks, "quality_ic_positive": quality_ic["mean"] > 0}


def run(quality_path: str, raw_dir: str, start: str, end: str, benchmark_path: str, baseline_path: str) -> dict:
    quality = load_quality(quality_path)
    reports = load_reports(raw_dir)
    dates, lookup, targets, quality_rows, metadata = build_inputs(start, end, reports, quality)
    config = BasketConfig(name="analyst_revision_quality", target_count=30, initial_nav=400_000.0, buy_cost=0.00155, sell_cost=0.00155)
    gross_config = BasketConfig(name="analyst_revision_quality_gross", target_count=30, initial_nav=400_000.0, buy_cost=0.0, sell_cost=0.0)
    result = simulate_basket(dates, lookup, targets, config)
    gross = simulate_basket(dates, lookup, targets, gross_config)
    benchmark = benchmark_returns(benchmark_path, dates)
    overlay = summarize_basket(result, gross, benchmark, config, folds=FOLDS)
    baseline = json.loads(Path(baseline_path).read_text(encoding="utf-8"))["portfolio"]
    quality_ic = ic_summary(quality_rows)
    decision = decide(quality_ic, overlay, baseline)
    return _clean(
        {
            "study": "a-share-analyst-revision-quality-overlay-v1",
            "data": {**metadata, "quality_rows": len(quality), "quality_signal_rows": len(quality_rows)},
            "quality_ic": quality_ic,
            "overlay": overlay,
            "baseline": {"metrics": baseline["metrics"], "folds": baseline["folds"]},
            "decision": decision,
            "limitations": [
                "quality data is provider-source-bounded and annual only",
                "industry classification is the local PIT panel mapping",
                "the interval is not virgin OOS",
            ],
        }
    )


def render_markdown(payload: dict) -> str:
    q = payload["quality_ic"]
    o = payload["overlay"]["metrics"]
    b = payload["baseline"]["metrics"]
    return "\n".join(
        [
            "# PIT质量因子与分析师修正叠加结果", "",
            f"- verdict: **{payload['decision']['verdict']}**", "",
            f"- quality IC: {q['mean']:.4f}; t-stat: {q['t_stat']:.2f}",
            f"- overlay CAGR/Sharpe/MDD: {o['cagr']:.2%} / {o['sharpe']:.3f} / {o['max_drawdown']:.2%}",
            f"- baseline CAGR/Sharpe/MDD: {b['cagr']:.2%} / {b['sharpe']:.3f} / {b['max_drawdown']:.2%}",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quality", default="overall/a-share-pit-quality.csv")
    parser.add_argument("--reports", default="overall/a-share-report-rc-raw")
    parser.add_argument("--start", default="2017-01-03")
    parser.add_argument("--end", default="2026-08-26")
    parser.add_argument("--benchmark", default="overall/a-share-multi-asset-etf-daily.csv")
    parser.add_argument("--baseline", default="overall/a-share-analyst-revision.json")
    parser.add_argument("--out-json", default="overall/a-share-quality-overlay.json")
    parser.add_argument("--out-md", default="overall/a-share-quality-overlay.md")
    args = parser.parse_args(argv)
    payload = run(args.quality, args.reports, args.start, args.end, args.benchmark, args.baseline)
    Path(args.out_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = render_markdown(payload)
    Path(args.out_md).write_text(markdown + "\n", encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
