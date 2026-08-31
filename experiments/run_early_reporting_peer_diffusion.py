"""Frozen PIT early-reporter peer-diffusion study; no analyst inputs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

QUANT_REPO = Path("/home/ygguo/agent-projs/quant-claude")
if str(QUANT_REPO) not in sys.path:
    sys.path.insert(0, str(QUANT_REPO))

import numpy as np
import pandas as pd

COST = 0.0031  # Round-trip cost deducted from every completed 20-session trade.
HORIZON = 20
MIN_REPORTERS = 3
MIN_EARLY_FRACTION = 0.10
MAX_EARLY_FRACTION = 0.35
MIN_POSITIVE_SHARE = 0.60


def _members_at(members: pd.DataFrame, day: pd.Timestamp) -> pd.DataFrame:
    active = members[(members.in_date <= day) & (members.out_date.isna() | (members.out_date >= day))]
    active = active[active.ts_code.str.endswith((".SH", ".SZ")) & ~active.name.fillna("").str.contains("ST", case=False)]
    return active.sort_values(["Symbol", "in_date"]).drop_duplicates("Symbol", keep="last")


def load_announcements(path: str) -> pd.DataFrame:
    data = pd.read_csv(path, dtype={"ts_code": str, "ann_date": str, "end_date": str})
    data["Symbol"] = data.ts_code.str[:6]
    data["ann_date"] = pd.to_datetime(data.ann_date, errors="coerce")
    data["end_date"] = pd.to_datetime(data.end_date, errors="coerce")
    for column in ("tr_yoy", "netprofit_yoy", "update_flag"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.dropna(subset=["Symbol", "ann_date", "end_date"])
    data["period"] = data.end_date.dt.to_period("Q")
    # The first dated record is the only announcement eligible to start diffusion.
    return data.sort_values(["Symbol", "period", "ann_date", "update_flag"]).drop_duplicates(["Symbol", "period"], keep="first")


def build_signals(members: pd.DataFrame, announcements: pd.DataFrame) -> pd.DataFrame:
    """Create at most one signal per industry/reporting period from visible reports."""
    prior = announcements[["Symbol", "period", "ann_date", "tr_yoy", "netprofit_yoy"]].copy()
    prior["period"] = prior.period + 1
    prior = prior.rename(columns={"ann_date": "prior_ann_date", "tr_yoy": "prior_revenue_yoy", "netprofit_yoy": "prior_profit_yoy"})
    events = announcements.merge(prior, on=["Symbol", "period"], how="left")
    events["revenue_acceleration"] = events.tr_yoy - events.prior_revenue_yoy
    events["profit_acceleration"] = events.netprofit_yoy - events.prior_profit_yoy
    events["positive"] = (events.revenue_acceleration > 0) & (events.profit_acceleration > 0) & (events.prior_ann_date <= events.ann_date)
    event_values = {
        period: frame.set_index("Symbol")[["revenue_acceleration", "profit_acceleration", "positive"]].to_dict("index")
        for period, frame in events.groupby("period", sort=False)
    }
    visible_symbols = {period: set() for period in event_values}
    rows: list[dict] = []
    emitted: set[tuple[str, pd.Period]] = set()
    active_day: pd.Timestamp | None = None
    active_industries: list[tuple[str, set[str]]] = []
    for (day, period), batch in events.groupby(["ann_date", "period"], sort=True):
        visible_symbols[period].update(batch.Symbol)
        if day != active_day:
            active = _members_at(members, day)
            active_industries = [
                (industry, set(industry_members.Symbol))
                for industry, industry_members in active.groupby("l1_name", sort=True)
            ]
            active_day = day
        values = event_values[period]
        for industry, symbols in active_industries:
            reported_symbols = sorted(symbols & visible_symbols[period])
            valid = [
                values[symbol]
                for symbol in reported_symbols
                if pd.notna(values[symbol]["revenue_acceleration"])
                and pd.notna(values[symbol]["profit_acceleration"])
            ]
            fraction = len(reported_symbols) / len(symbols) if symbols else 0.0
            positive_share = float(np.mean([row["positive"] for row in valid])) if valid else np.nan
            key = (industry, period)
            if key in emitted or len(valid) < MIN_REPORTERS or not MIN_EARLY_FRACTION <= fraction <= MAX_EARLY_FRACTION or not positive_share >= MIN_POSITIVE_SHARE:
                continue
            emitted.add(key)
            rows.append({
                "signal_date": day,
                "report_period": str(period),
                "industry": industry,
                "industry_members": len(symbols),
                "reported_count": len(reported_symbols),
                "valid_reporter_count": len(valid),
                "early_fraction": fraction,
                "positive_share": positive_share,
                "median_revenue_acceleration": float(np.median([row["revenue_acceleration"] for row in valid])),
                "median_profit_acceleration": float(np.median([row["profit_acceleration"] for row in valid])),
                "reported_symbols": json.dumps(reported_symbols),
                "peer_symbols": json.dumps(sorted(symbols - set(reported_symbols))),
            })
    return pd.DataFrame(rows)


def _stock_prices(end: str) -> tuple[pd.DataFrame, list[pd.Timestamp], str]:
    from factormine.config import Config
    from factormine.data.db import connect
    from factormine.data.panel import load_or_build_panel
    from factormine.research.combination import repair_point_in_time_size

    config = Config()
    connection = connect(config, read_only=True)
    try:
        built = load_or_build_panel(config, "2015-01-01", end, con=connection)
    finally:
        connection.close()
    panel = repair_point_in_time_size(built.df)
    panel["TradingDay"] = pd.to_datetime(panel.TradingDay)
    panel = panel.sort_values(["Symbol", "TradingDay"])
    practical = (~panel.is_st.fillna(True)) & (~panel.suspended.fillna(True)) & (panel.age >= 252) & (panel.Close >= 5) & (panel.Volume > 0)
    panel = panel.loc[practical, ["Symbol", "TradingDay", "adj_open", "adj_close"]].copy()
    return panel, sorted(panel.TradingDay.unique()), built.version_hash


def _price_histories(prices: pd.DataFrame, symbol_column: str, day_column: str) -> dict[str, pd.DataFrame]:
    return {str(symbol): group.set_index(day_column).sort_index() for symbol, group in prices.groupby(symbol_column, sort=False)}


def _forward_return(history: pd.DataFrame | None, entry: pd.Timestamp) -> float | None:
    if history is None or entry not in history.index:
        return None
    start = history.index.get_loc(entry)
    if start + HORIZON - 1 >= len(history):
        return None
    open_price, close_price = history.iloc[start].adj_open, history.iloc[start + HORIZON - 1].adj_close
    if not np.isfinite(open_price) or not np.isfinite(close_price) or open_price <= 0:
        return None
    return float(close_price / open_price - 1 - COST)


def evaluate_stock_arm(signals: pd.DataFrame, prices: pd.DataFrame, sessions: list[pd.Timestamp]) -> pd.DataFrame:
    histories = _price_histories(prices, "Symbol", "TradingDay")
    rows: list[dict] = []
    for signal in signals.itertuples(index=False):
        position = int(np.searchsorted(sessions, signal.signal_date, side="right"))
        if position >= len(sessions):
            continue
        entry = pd.Timestamp(sessions[position])
        peers = json.loads(signal.peer_symbols)
        returns = [_forward_return(histories.get(symbol), entry) for symbol in peers]
        returns = [value for value in returns if value is not None]
        rows.append({**signal._asdict(), "arm": "unreported_peer_stock", "entry_date": entry, "eligible_peers": len(peers), "priced_peers": len(returns), "return_20d": float(np.mean(returns)) if returns else np.nan})
    return pd.DataFrame(rows)


def evaluate_etf_arm(signals: pd.DataFrame, candidates_path: str, daily_path: str, adj_path: str, sessions: list[pd.Timestamp]) -> pd.DataFrame:
    candidates = pd.read_csv(candidates_path, dtype=str)
    candidates["list_date"] = pd.to_datetime(candidates.list_date, errors="coerce")
    candidates["delist_date"] = pd.to_datetime(candidates.delist_date, errors="coerce")
    daily, adj = pd.read_parquet(daily_path), pd.read_parquet(adj_path)
    for data in (daily, adj):
        data.trade_date = pd.to_datetime(data.trade_date.astype(str), format="mixed")
    prices = daily.merge(adj, on=["ts_code", "trade_date"], how="inner")
    prices["adj_open"] = prices.open * prices.adj_factor
    prices["adj_close"] = prices.close * prices.adj_factor
    histories = _price_histories(prices, "ts_code", "trade_date")
    rows: list[dict] = []
    for signal in signals.itertuples(index=False):
        position = int(np.searchsorted(sessions, signal.signal_date, side="right"))
        if position >= len(sessions):
            continue
        entry = pd.Timestamp(sessions[position])
        pool = candidates[(candidates.industry == signal.industry) & (candidates.list_date <= entry) & (candidates.delist_date.isna() | (candidates.delist_date >= entry))]
        best, code = -np.inf, None
        for candidate in pool.ts_code.unique():
            history = histories.get(candidate)
            if history is None:
                continue
            recent = history[history.index < entry].tail(20)
            amount = pd.to_numeric(recent.amount, errors="coerce").mean()
            if len(recent) >= 10 and pd.notna(amount) and amount > best:
                best, code = amount, candidate
        ret = _forward_return(histories.get(code), entry) if code is not None else None
        rows.append({**signal._asdict(), "arm": "direct_industry_etf", "entry_date": entry, "etf_code": code, "return_20d": ret})
    return pd.DataFrame(rows)


def summarize(events: pd.DataFrame) -> dict:
    complete = events.dropna(subset=["return_20d"]).copy()
    complete["year"] = pd.to_datetime(complete.signal_date).dt.year
    folds = {str(year): {"count": len(group), "mean_return_20d": float(group.return_20d.mean()), "win_rate": float((group.return_20d > 0).mean())} for year, group in complete.groupby("year")}
    holdout = complete[complete.year == 2025]
    return {"signals": len(events), "complete": len(complete), "mean_return_20d": float(complete.return_20d.mean()) if len(complete) else None, "median_return_20d": float(complete.return_20d.median()) if len(complete) else None, "win_rate": float((complete.return_20d > 0).mean()) if len(complete) else None, "folds": folds, "holdout_2025": {"count": len(holdout), "mean_return_20d": float(holdout.return_20d.mean()) if len(holdout) else None, "win_rate": float((holdout.return_20d > 0).mean()) if len(holdout) else None}}


def run(members_path: str, financials_path: str, candidates_path: str, daily_path: str, adj_path: str, end: str, output_dir: str) -> dict:
    members = pd.read_csv(members_path, dtype=str)
    members["Symbol"] = members.ts_code.str[:6]
    members["in_date"] = pd.to_datetime(members.in_date, errors="coerce")
    members["out_date"] = pd.to_datetime(members.out_date, errors="coerce")
    announcements = load_announcements(financials_path)
    signals = build_signals(members, announcements[announcements.ann_date <= pd.Timestamp(end)])
    prices, sessions, panel_version = _stock_prices(end)
    stock = evaluate_stock_arm(signals, prices, sessions)
    etf = evaluate_etf_arm(signals, candidates_path, daily_path, adj_path, sessions)
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    signals.to_csv(out / "signals.csv", index=False, date_format="%Y-%m-%d")
    stock.to_csv(out / "stock-events.csv", index=False, date_format="%Y-%m-%d")
    etf.to_csv(out / "etf-events.csv", index=False, date_format="%Y-%m-%d")
    payload = {"study": "a-share-early-reporting-peer-diffusion-v1", "trade_authorized": False, "frozen_rule": {"horizon_sessions": HORIZON, "round_trip_cost": COST, "min_reporters": MIN_REPORTERS, "early_fraction": [MIN_EARLY_FRACTION, MAX_EARLY_FRACTION], "min_positive_acceleration_share": MIN_POSITIVE_SHARE, "execution": "announcement-day close decision; next session open entry"}, "data": {"panel_version": panel_version, "financials": financials_path, "members": members_path}, "arms": {"unreported_peer_stock": summarize(stock), "direct_industry_etf": summarize(etf)}}
    payload["verdict"] = "NO-GO" if any(arm["holdout_2025"]["count"] == 0 or (arm["holdout_2025"]["mean_return_20d"] or 0) <= 0 for arm in payload["arms"].values()) else "GO"
    (out / "result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    research = "/home/ygguo/agent-projs/ai-crypt/platform-a-share-research/overall"
    parser = argparse.ArgumentParser()
    parser.add_argument("--members", default=f"{research}/a-share-sw2021-members.csv")
    parser.add_argument("--financials", default=f"{research}/a-share-quarterly-statements-raw/fina_indicator_vip.csv")
    parser.add_argument("--candidates", default=f"{research}/a-share-sector-etf-candidates.csv")
    parser.add_argument("--daily", default=f"{research}/a-share-sector-etf-raw-v2/fund_daily.parquet")
    parser.add_argument("--adj", default=f"{research}/a-share-sector-etf-raw-v2/fund_adj.parquet")
    parser.add_argument("--end", default="2026-08-28")
    parser.add_argument("--output-dir", default="overall/a-share-early-reporting-peer-diffusion")
    args = parser.parse_args(argv)
    print(json.dumps(run(args.members, args.financials, args.candidates, args.daily, args.adj, args.end, args.output_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
