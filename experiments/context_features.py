"""Frozen derivations for breakout context features."""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd


def analyst_eps_revision(rows: pd.DataFrame, signal_date: pd.Timestamp) -> dict:
    if rows.empty:
        return {"quarter": None, "current_count": 0, "prior_count": 0, "current_eps": np.nan, "prior_eps": np.nan, "revision": np.nan}
    frame = rows.copy()
    frame["report_date"] = pd.to_datetime(frame["report_date"].astype(str))
    parsed = frame["quarter"].astype(str).str.extract(r"^(\d{4})Q([1-4])$")
    frame["quarter_year"] = pd.to_numeric(parsed[0], errors="coerce")
    frame = frame[
        (frame["quarter_year"] >= signal_date.year)
        & frame["org_name"].notna()
        & frame["eps"].notna()
        & (frame["report_date"] <= signal_date)
    ].copy()
    if frame.empty:
        return {"quarter": None, "current_count": 0, "prior_count": 0, "current_eps": np.nan, "prior_eps": np.nan, "revision": np.nan}
    counts = frame.groupby("quarter")["org_name"].nunique().sort_values(ascending=False)
    max_count = int(counts.iloc[0])
    quarter = sorted(counts[counts == max_count].index)[0]
    frame = frame[frame["quarter"] == quarter]

    def consensus(cutoff: pd.Timestamp) -> tuple[int, float]:
        eligible = frame[frame["report_date"] <= cutoff].sort_values(
            ["org_name", "report_date", "create_time"]
        )
        latest = eligible.drop_duplicates("org_name", keep="last")
        return len(latest), float(latest["eps"].median()) if len(latest) else np.nan

    current_count, current_eps = consensus(signal_date)
    prior_count, prior_eps = consensus(signal_date - timedelta(days=30))
    revision = (
        current_eps / prior_eps - 1.0
        if current_count >= 3 and prior_count >= 3 and np.isfinite(prior_eps) and prior_eps != 0
        else np.nan
    )
    return {
        "quarter": quarter,
        "current_count": current_count,
        "prior_count": prior_count,
        "current_eps": current_eps,
        "prior_eps": prior_eps,
        "revision": revision,
    }


def holm_adjust(p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(p_values, key=lambda key: p_values[key])
    adjusted: dict[str, float] = {}
    running = 0.0
    total = len(ordered)
    for index, key in enumerate(ordered):
        running = max(running, min(1.0, (total - index) * p_values[key]))
        adjusted[key] = running
    return adjusted
