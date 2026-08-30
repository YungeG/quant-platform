"""Evaluate fine-grained peer-breakout clustering on the retest ledger."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from experiments.peer_cluster import cluster_confirmed
from experiments.run_breakout_retest_v2 import event_metrics
from experiments.run_lowturn_livermore import _clean


DB_PATH = "/srv/bcache-8t/ygguo/duckdb/quant-a50/quant_a50.duckdb"


def _active_count(members: pd.DataFrame, code_column: str, code: str, day: pd.Timestamp) -> int:
    rows = members[members[code_column] == code]
    return int(((rows["in_date"] <= day) & (rows["out_date"] >= day)).sum())


def _peer_counts(events: pd.DataFrame) -> pd.Series:
    result = pd.Series(0, index=events.index, dtype=int)
    for _, group in events.dropna(subset=["peer_group_code", "day_index"]).groupby("peer_group_code"):
        by_day = {
            int(day): set(rows["symbol"].astype(str))
            for day, rows in group.groupby("day_index")
        }
        for index, row in group.iterrows():
            peers: set[str] = set()
            for day_index in range(int(row.day_index) - 4, int(row.day_index) + 1):
                peers.update(by_day.get(day_index, set()))
            peers.discard(str(row.symbol))
            result.loc[index] = len(peers)
    return result


def build_enriched(
    events_path: str,
    members_path: str,
    start: str,
    end: str,
) -> tuple[pd.DataFrame, dict]:
    events = pd.read_csv(events_path, parse_dates=["breakout_date", "signal_date"])
    events["symbol"] = events["symbol"].astype(str).str.zfill(6)
    members = pd.read_csv(members_path, dtype=str)
    members["symbol"] = members["ts_code"].str[:6]
    members["in_date"] = pd.to_datetime(members["in_date"], format="%Y%m%d", errors="coerce").fillna(pd.Timestamp("1900-01-01"))
    members["out_date"] = pd.to_datetime(members["out_date"], format="%Y%m%d", errors="coerce").fillna(pd.Timestamp("2100-01-01"))
    context = members[
        ["symbol", "l1_code", "l1_name", "l2_code", "l2_name", "l3_code", "l3_name", "in_date", "out_date"]
    ]
    events = events.merge(context, on="symbol", how="left")
    active = (events["in_date"] <= events["breakout_date"]) & (events["out_date"] >= events["breakout_date"])
    for column in ("l1_code", "l1_name", "l2_code", "l2_name", "l3_code", "l3_name"):
        events.loc[~active, column] = np.nan

    l3_counts = []
    l2_counts = []
    for row in events.itertuples(index=False):
        day = pd.Timestamp(row.breakout_date)
        l3_counts.append(
            _active_count(members, "l3_code", str(row.l3_code), day)
            if pd.notna(row.l3_code)
            else 0
        )
        l2_counts.append(
            _active_count(members, "l2_code", str(row.l2_code), day)
            if pd.notna(row.l2_code)
            else 0
        )
    events["l3_member_count"] = l3_counts
    events["l2_member_count"] = l2_counts
    use_l3 = events["l3_member_count"] >= 5
    use_l2 = (~use_l3) & (events["l2_member_count"] >= 8)
    events["peer_group_level"] = np.select([use_l3, use_l2], ["L3", "L2"], default="unavailable")
    events["peer_group_code"] = np.where(use_l3, events["l3_code"], np.where(use_l2, events["l2_code"], np.nan))
    events["peer_group_name"] = np.where(use_l3, events["l3_name"], np.where(use_l2, events["l2_name"], np.nan))
    events["peer_group_member_count"] = np.where(use_l3, events["l3_member_count"], np.where(use_l2, events["l2_member_count"], 0))

    connection = duckdb.connect(DB_PATH, read_only=True)
    try:
        sessions = connection.execute(
            "select distinct TradingDay from (select TradingDay from MarketData union all select TradingDay from DelistedMarketData) where TradingDay between ? and ? order by TradingDay",
            [start, end],
        ).df()
        codes = sorted(events["peer_group_code"].dropna().unique())
        placeholders = ",".join("?" for _ in codes)
        industry = connection.execute(
            f"select TradeDate, TSCode, PctChange from IndustryDailyData where TSCode in ({placeholders}) and TradeDate between ? and ?",
            [*codes, "2014-11-27", end],
        ).df() if codes else pd.DataFrame(columns=["TradeDate", "TSCode", "PctChange"])
    finally:
        connection.close()
    day_map = {
        pd.Timestamp(day): index
        for index, day in enumerate(pd.to_datetime(sessions["TradingDay"]))
    }
    events["day_index"] = events["breakout_date"].map(day_map)
    events["peer_breakout_count5"] = _peer_counts(events)
    events["peer_breakout_density5"] = (
        events["peer_breakout_count5"] / events["peer_group_member_count"].replace(0, np.nan)
    )

    industry["TradeDate"] = pd.to_datetime(industry["TradeDate"])
    industry = industry.drop_duplicates(["TradeDate", "TSCode"], keep="last").sort_values(["TSCode", "TradeDate"])
    industry["index_value"] = industry.groupby("TSCode", sort=False)["PctChange"].transform(
        lambda series: (1.0 + series.fillna(0.0) / 100.0).cumprod()
    )
    industry["peer_group_return20"] = industry.groupby("TSCode", sort=False)["index_value"].transform(
        lambda series: series / series.shift(20) - 1.0
    )
    industry["peer_group_ma20"] = industry.groupby("TSCode", sort=False)["index_value"].transform(
        lambda series: series.rolling(20, min_periods=20).mean()
    )
    industry["peer_group_above_ma20"] = industry["index_value"] > industry["peer_group_ma20"]
    context_index = industry.rename(columns={"TradeDate": "breakout_date", "TSCode": "peer_group_code"})[
        ["breakout_date", "peer_group_code", "peer_group_return20", "peer_group_above_ma20"]
    ]
    events = events.merge(context_index, on=["breakout_date", "peer_group_code"], how="left")
    events["cluster_confirmed"] = [
        cluster_confirmed(
            int(count),
            float(density) if np.isfinite(density) else -1.0,
            float(group_return) if np.isfinite(group_return) else -1.0,
            bool(above) if pd.notna(above) else False,
        )
        for count, density, group_return, above in zip(
            events["peer_breakout_count5"],
            events["peer_breakout_density5"],
            events["peer_group_return20"],
            events["peer_group_above_ma20"],
            strict=True,
        )
    ]
    metadata = {
        "events": len(events),
        "group_available_rate": float((events["peer_group_level"] != "unavailable").mean()),
        "cluster_confirmed_events": int(events["cluster_confirmed"].sum()),
        "start": start,
        "end": end,
    }
    return events, metadata


def decide(events: pd.DataFrame) -> tuple[dict, dict]:
    executed = events[events["execution_reason"] == "executed"]
    clustered = executed[executed["cluster_confirmed"]]
    all_metrics = event_metrics(executed, 20)
    cluster_metrics = event_metrics(clustered, 20)
    mean_uplift = cluster_metrics["mean"] - all_metrics["mean"]
    win_uplift = cluster_metrics["win_rate"] - all_metrics["win_rate"]
    checks = {
        "count": cluster_metrics["count"] >= 50,
        "mean": cluster_metrics["mean"] >= 0.01,
        "median": cluster_metrics["median"] > 0,
        "win_rate": cluster_metrics["win_rate"] > 0.52,
        "positive_folds": sum(fold["mean"] > 0 for fold in cluster_metrics["folds"].values()) >= 2,
        "bootstrap": cluster_metrics["bootstrap_95"][0] > 0,
        "uplift": mean_uplift >= 0.01 or win_uplift >= 0.05,
    }
    if all(checks.values()):
        verdict = "GO"
    elif mean_uplift > 0:
        verdict = "MARGINAL"
    else:
        verdict = "NO-GO"
    failure_table = (
        events.groupby(["cluster_confirmed", "terminal_reason"]).size().unstack(fill_value=0).to_dict(orient="index")
    )
    return {
        "verdict": verdict,
        "checks": checks,
        "all_executed20": all_metrics,
        "cluster_confirmed20": cluster_metrics,
        "mean_uplift": mean_uplift,
        "win_rate_uplift": win_uplift,
    }, {str(key): value for key, value in failure_table.items()}


def render_markdown(payload: dict) -> str:
    base = payload["decision"]["all_executed20"]
    cluster = payload["decision"]["cluster_confirmed20"]
    return "\n".join(
        [
            "# 突破回踩板块内聚集效应结果",
            "",
            f"- verdict: **{payload['decision']['verdict']}**",
            f"- cluster-confirmed executed events: {cluster['count']}",
            "",
            "| Sample | Mean active20 | Median | Win rate | Bootstrap 95% |",
            "| --- | ---: | ---: | ---: | --- |",
            f"| all | {base['mean']:.2%} | {base['median']:.2%} | {base['win_rate']:.2%} | "
            f"[{base['bootstrap_95'][0]:.2%}, {base['bootstrap_95'][1]:.2%}] |",
            f"| peer cluster | {cluster['mean']:.2%} | {cluster['median']:.2%} | {cluster['win_rate']:.2%} | "
            f"[{cluster['bootstrap_95'][0]:.2%}, {cluster['bootstrap_95'][1]:.2%}] |",
        ]
    )


def run(events_path: str, members_path: str, ledger: str, start: str, end: str) -> dict:
    events, metadata = build_enriched(events_path, members_path, start, end)
    events.to_csv(ledger, index=False, date_format="%Y-%m-%d")
    decision, failure_table = decide(events)
    return _clean(
        {
            "study": "a-share-breakout-retest-peer-cluster-v1",
            "data": metadata,
            "decision": decision,
            "failure_table": failure_table,
            "ledger": ledger,
            "limitations": [
                "SW2021 L2/L3 membership is current-vintage and may contain taxonomy revision bias",
                "peer clustering uses breakout events, not intraday return correlations",
                "the sample is not virgin OOS",
            ],
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", default="overall/a-share-breakout-retest-v2-events.csv")
    parser.add_argument("--members", default="overall/a-share-sw2021-members.csv")
    parser.add_argument("--ledger", default="overall/a-share-breakout-retest-v2-cluster-events.csv")
    parser.add_argument("--start", default="2016-01-01")
    parser.add_argument("--end", default="2026-08-25")
    parser.add_argument("--out-json", default="overall/a-share-breakout-retest-cluster.json")
    parser.add_argument("--out-md", default="overall/a-share-breakout-retest-cluster.md")
    args = parser.parse_args(argv)
    payload = run(args.events, args.members, args.ledger, args.start, args.end)
    Path(args.out_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = render_markdown(payload)
    Path(args.out_md).write_text(markdown + "\n", encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
