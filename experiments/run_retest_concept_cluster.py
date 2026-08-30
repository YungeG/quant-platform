"""Evaluate PIT Eastmoney concept co-breakouts where historical data exists."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.concept_cluster import concept_cluster_confirmed
from experiments.run_breakout_retest_v2 import event_metrics
from experiments.run_lowturn_livermore import _clean


def ts_code(symbol: str) -> str:
    symbol = str(symbol).zfill(6)
    if symbol.startswith(("4", "8", "9")):
        return f"{symbol}.BJ"
    if symbol.startswith(("5", "6", "68")):
        return f"{symbol}.SH"
    return f"{symbol}.SZ"


def build_enriched(
    events_path: str,
    members_path: str,
    index_path: str,
    queries_path: str,
) -> tuple[pd.DataFrame, dict]:
    events = pd.read_csv(events_path, parse_dates=["breakout_date", "signal_date"])
    events["symbol"] = events["symbol"].astype(str).str.zfill(6)
    members = pd.read_csv(members_path, dtype=str)
    indexes = pd.read_csv(index_path, dtype={"trade_date": str, "ts_code": str})
    queries = pd.read_csv(queries_path, dtype={"date": str, "symbol": str})
    queries["symbol"] = queries["symbol"].fillna("")
    successful_queries = {
        (str(row.date), str(row.symbol))
        for row in queries.itertuples(index=False)
        if row.kind == "member" and (row.ok is True or str(row.ok).lower() == "true")
    }
    member_map = {
        (str(date), str(stock)): set(rows["ts_code"].astype(str))
        for (date, stock), rows in members.groupby(["trade_date", "con_code"])
    }
    indexes["member_count"] = pd.to_numeric(indexes["up_num"], errors="coerce").fillna(0) + pd.to_numeric(
        indexes["down_num"], errors="coerce"
    ).fillna(0)
    valid_index = indexes[
        (indexes["idx_type"] == "概念板块")
        & indexes["member_count"].between(10, 100)
    ]
    concept_info = {
        (str(date), str(code)): {"name": str(row.iloc[0]["name"]), "member_count": int(row.iloc[0]["member_count"])}
        for (date, code), row in valid_index.groupby(["trade_date", "ts_code"])
    }
    available_dates = set(indexes["trade_date"].astype(str))
    by_day = {
        int(day): set(rows["symbol"])
        for day, rows in events.groupby("day_index")
    }
    complete_flags = []
    confirmed_flags = []
    evidence_rows = []
    for row in events.itertuples(index=False):
        if row.execution_reason != "executed":
            complete_flags.append(False)
            confirmed_flags.append(False)
            evidence_rows.append("[]")
            continue
        date = row.breakout_date.strftime("%Y%m%d")
        peers: set[str] = set()
        for day_index in range(int(row.day_index) - 4, int(row.day_index) + 1):
            peers.update(by_day.get(day_index, set()))
        peers.discard(str(row.symbol))
        stocks = peers | {str(row.symbol)}
        complete = date in available_dates and all(
            (date, ts_code(stock)) in successful_queries for stock in stocks
        )
        complete_flags.append(complete)
        if not complete:
            confirmed_flags.append(False)
            evidence_rows.append("[]")
            continue
        target_concepts = member_map.get((date, ts_code(row.symbol)), set())
        evidence = []
        for concept in sorted(target_concepts):
            info = concept_info.get((date, concept))
            if info is None:
                continue
            shared_peers = [
                peer
                for peer in sorted(peers)
                if concept in member_map.get((date, ts_code(peer)), set())
            ]
            if shared_peers:
                evidence.append(
                    {
                        "concept_code": concept,
                        "concept_name": info["name"],
                        "member_count": info["member_count"],
                        "shared_peer_count": len(shared_peers),
                        "shared_peers": shared_peers,
                    }
                )
        confirmed = concept_cluster_confirmed(
            [item["shared_peer_count"] for item in evidence]
        )
        confirmed_flags.append(confirmed)
        evidence_rows.append(json.dumps(evidence, ensure_ascii=False, separators=(",", ":")))
    events["concept_data_complete"] = complete_flags
    events["concept_cluster_confirmed"] = confirmed_flags
    events["concept_cluster_evidence"] = evidence_rows
    executed = events[events["execution_reason"] == "executed"]
    metadata = {
        "events": len(events),
        "executed_events": len(executed),
        "complete_executed_events": int(executed["concept_data_complete"].sum()),
        "executed_data_complete_rate": float(executed["concept_data_complete"].mean()),
        "concept_confirmed_events": int(executed["concept_cluster_confirmed"].sum()),
        "available_date_min": min(available_dates) if available_dates else None,
        "available_date_max": max(available_dates) if available_dates else None,
    }
    return events, metadata


def decide(events: pd.DataFrame, completeness: float) -> dict:
    complete = events[
        (events["execution_reason"] == "executed") & events["concept_data_complete"]
    ]
    confirmed = complete[complete["concept_cluster_confirmed"]]
    base = event_metrics(complete, 20)
    concept = event_metrics(confirmed, 20)
    mean_uplift = concept["mean"] - base["mean"]
    win_uplift = concept["win_rate"] - base["win_rate"]
    checks = {
        "count": concept["count"] >= 30,
        "mean": concept["mean"] >= 0.01,
        "median": concept["median"] > 0,
        "win_rate": concept["win_rate"] > 0.52,
        "positive_folds": sum(fold["mean"] > 0 for fold in concept["folds"].values()) >= 2,
        "bootstrap": concept["bootstrap_95"][0] > 0,
        "uplift": mean_uplift >= 0.01 or win_uplift >= 0.05,
        "completeness": completeness >= 0.95,
    }
    if not checks["completeness"]:
        verdict = "DATA-BLOCKED"
    elif all(checks.values()):
        verdict = "GO"
    elif mean_uplift > 0:
        verdict = "MARGINAL"
    else:
        verdict = "NO-GO"
    return {
        "verdict": verdict,
        "checks": checks,
        "complete_sample20": base,
        "concept_cluster20": concept,
        "mean_uplift": mean_uplift,
        "win_rate_uplift": win_uplift,
    }


def render_markdown(payload: dict) -> str:
    base = payload["decision"]["complete_sample20"]
    concept = payload["decision"]["concept_cluster20"]
    return "\n".join(
        [
            "# 突破回踩题材概念聚集结果",
            "",
            f"- verdict: **{payload['decision']['verdict']}**",
            f"- complete/total executed: {payload['data']['complete_executed_events']}/{payload['data']['executed_events']}",
            f"- concept-cluster events: {concept['count']}",
            "",
            "| Sample | Mean active20 | Median | Win rate |",
            "| --- | ---: | ---: | ---: |",
            f"| complete-period all | {base['mean']:.2%} | {base['median']:.2%} | {base['win_rate']:.2%} |",
            f"| concept cluster | {concept['mean']:.2%} | {concept['median']:.2%} | {concept['win_rate']:.2%} |",
        ]
    )


def run(events: str, members: str, indexes: str, queries: str, ledger: str) -> dict:
    frame, metadata = build_enriched(events, members, indexes, queries)
    frame.to_csv(ledger, index=False, date_format="%Y-%m-%d")
    decision = decide(frame, metadata["executed_data_complete_rate"])
    return _clean(
        {
            "study": "a-share-breakout-retest-concept-cluster-v1",
            "data": metadata,
            "decision": decision,
            "ledger": ledger,
            "limitations": [
                "Eastmoney PIT concept membership is available only from 2025 in the proxy history",
                "historical completeness is below the frozen gate",
                "concept memberships may change because the provider taxonomy is dynamic",
            ],
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", default="overall/a-share-breakout-retest-v2-correlation-events.csv")
    parser.add_argument("--members", default="overall/a-share-dc-concept-members.csv")
    parser.add_argument("--index", default="overall/a-share-dc-concept-index.csv")
    parser.add_argument("--queries", default="overall/a-share-dc-concept-queries.csv")
    parser.add_argument("--ledger", default="overall/a-share-breakout-retest-v2-concept-events.csv")
    parser.add_argument("--out-json", default="overall/a-share-breakout-retest-concept-cluster.json")
    parser.add_argument("--out-md", default="overall/a-share-breakout-retest-concept-cluster.md")
    args = parser.parse_args(argv)
    payload = run(args.events, args.members, args.index, args.queries, args.ledger)
    Path(args.out_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = render_markdown(payload)
    Path(args.out_md).write_text(markdown + "\n", encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
