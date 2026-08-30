"""Evaluate dynamic return-correlation clusters on breakout-retest events."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.correlation_cluster import correlation_cluster_confirmed
from experiments.run_breakout_retest_v2 import event_metrics
from experiments.run_lowturn_livermore import _clean
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel


def build_enriched(events_path: str, start: str, end: str) -> tuple[pd.DataFrame, dict]:
    events = pd.read_csv(events_path, parse_dates=["breakout_date", "signal_date"])
    events["symbol"] = events["symbol"].astype(str).str.zfill(6)
    symbols = set(events["symbol"])
    cfg = Config()
    connection = connect(cfg, read_only=True)
    try:
        built = load_or_build_panel(cfg, "2015-09-01", end, con=connection)
    finally:
        connection.close()
    panel = built.df[built.df["Symbol"].isin(symbols)][
        ["TradingDay", "Symbol", "adj_close"]
    ].copy()
    panel["TradingDay"] = pd.to_datetime(panel["TradingDay"])
    wide_close = panel.pivot(index="TradingDay", columns="Symbol", values="adj_close").sort_index()
    returns = wide_close.pct_change(fill_method=None)
    day_map = {day: index for index, day in enumerate(returns.index)}
    events["day_index"] = events["breakout_date"].map(day_map)
    events_by_day = {
        int(day): set(rows["symbol"])
        for day, rows in events.dropna(subset=["day_index"]).groupby("day_index")
    }
    peer_counts = []
    median_correlations = []
    max_correlations = []
    candidate_counts = []
    peer_details = []
    for row in events.itertuples(index=False):
        if pd.isna(row.day_index) or row.symbol not in returns.columns:
            candidate_counts.append(0)
            peer_counts.append(0)
            median_correlations.append(np.nan)
            max_correlations.append(np.nan)
            peer_details.append("[]")
            continue
        day_index = int(row.day_index)
        candidates: set[str] = set()
        for index in range(day_index - 4, day_index + 1):
            candidates.update(events_by_day.get(index, set()))
        candidates.discard(str(row.symbol))
        candidate_counts.append(len(candidates))
        window = returns.iloc[max(0, day_index - 60) : day_index]
        qualifying = []
        for peer in sorted(candidates):
            if peer not in window.columns:
                continue
            pair = window[[row.symbol, peer]].dropna()
            if len(pair) < 50:
                continue
            correlation = float(pair[row.symbol].corr(pair[peer]))
            if np.isfinite(correlation) and correlation >= 0.60:
                qualifying.append({"symbol": peer, "correlation": correlation})
        correlations = [item["correlation"] for item in qualifying]
        peer_counts.append(len(qualifying))
        median_correlations.append(float(np.median(correlations)) if correlations else np.nan)
        max_correlations.append(float(max(correlations)) if correlations else np.nan)
        peer_details.append(json.dumps(qualifying, ensure_ascii=False, separators=(",", ":")))
    events["correlation_candidate_count5"] = candidate_counts
    events["correlation_peer_count5"] = peer_counts
    events["median_peer_correlation"] = median_correlations
    events["max_peer_correlation"] = max_correlations
    events["correlation_peers"] = peer_details
    events["correlation_cluster_confirmed"] = [
        correlation_cluster_confirmed(
            int(count), float(correlation) if np.isfinite(correlation) else -1.0
        )
        for count, correlation in zip(peer_counts, median_correlations, strict=True)
    ]
    metadata = {
        "panel_version": built.version_hash,
        "events": len(events),
        "cluster_confirmed_events": int(events["correlation_cluster_confirmed"].sum()),
        "events_with_candidates": int((events["correlation_candidate_count5"] > 0).sum()),
        "start": start,
        "end": end,
    }
    del panel, wide_close, returns
    gc.collect()
    return events, metadata


def decide(events: pd.DataFrame) -> tuple[dict, dict]:
    executed = events[events["execution_reason"] == "executed"]
    clustered = executed[executed["correlation_cluster_confirmed"]]
    base = event_metrics(executed, 20)
    cluster = event_metrics(clustered, 20)
    mean_uplift = cluster["mean"] - base["mean"]
    win_uplift = cluster["win_rate"] - base["win_rate"]
    checks = {
        "count": cluster["count"] >= 50,
        "mean": cluster["mean"] >= 0.01,
        "median": cluster["median"] > 0,
        "win_rate": cluster["win_rate"] > 0.52,
        "positive_folds": sum(fold["mean"] > 0 for fold in cluster["folds"].values()) >= 2,
        "bootstrap": cluster["bootstrap_95"][0] > 0,
        "uplift": mean_uplift >= 0.01 or win_uplift >= 0.05,
    }
    if all(checks.values()):
        verdict = "GO"
    elif mean_uplift > 0:
        verdict = "MARGINAL"
    else:
        verdict = "NO-GO"
    failure_table = (
        events.groupby(["correlation_cluster_confirmed", "terminal_reason"])
        .size()
        .unstack(fill_value=0)
        .to_dict(orient="index")
    )
    return {
        "verdict": verdict,
        "checks": checks,
        "all_executed20": base,
        "correlation_cluster20": cluster,
        "mean_uplift": mean_uplift,
        "win_rate_uplift": win_uplift,
    }, {str(key): value for key, value in failure_table.items()}


def render_markdown(payload: dict) -> str:
    base = payload["decision"]["all_executed20"]
    cluster = payload["decision"]["correlation_cluster20"]
    return "\n".join(
        [
            "# 突破回踩动态相关聚集结果",
            "",
            f"- verdict: **{payload['decision']['verdict']}**",
            f"- correlation-cluster executed events: {cluster['count']}",
            "",
            "| Sample | Mean active20 | Median | Win rate | Bootstrap 95% |",
            "| --- | ---: | ---: | ---: | --- |",
            f"| all | {base['mean']:.2%} | {base['median']:.2%} | {base['win_rate']:.2%} | "
            f"[{base['bootstrap_95'][0]:.2%}, {base['bootstrap_95'][1]:.2%}] |",
            f"| correlation cluster | {cluster['mean']:.2%} | {cluster['median']:.2%} | {cluster['win_rate']:.2%} | "
            f"[{cluster['bootstrap_95'][0]:.2%}, {cluster['bootstrap_95'][1]:.2%}] |",
        ]
    )


def run(events_path: str, ledger: str, start: str, end: str) -> dict:
    events, metadata = build_enriched(events_path, start, end)
    events.to_csv(ledger, index=False, date_format="%Y-%m-%d")
    decision, failure_table = decide(events)
    return _clean(
        {
            "study": "a-share-breakout-retest-correlation-cluster-v1",
            "data": metadata,
            "decision": decision,
            "failure_table": failure_table,
            "ledger": ledger,
            "limitations": [
                "correlation peers are defined only among recent breakout events",
                "daily returns cannot identify intraday lead-lag direction",
                "the sample is not virgin OOS",
            ],
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", default="overall/a-share-breakout-retest-v2-events.csv")
    parser.add_argument("--ledger", default="overall/a-share-breakout-retest-v2-correlation-events.csv")
    parser.add_argument("--start", default="2016-01-01")
    parser.add_argument("--end", default="2026-08-25")
    parser.add_argument("--out-json", default="overall/a-share-breakout-retest-correlation-cluster.json")
    parser.add_argument("--out-md", default="overall/a-share-breakout-retest-correlation-cluster.md")
    args = parser.parse_args(argv)
    payload = run(args.events, args.ledger, args.start, args.end)
    Path(args.out_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = render_markdown(payload)
    Path(args.out_md).write_text(markdown + "\n", encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
