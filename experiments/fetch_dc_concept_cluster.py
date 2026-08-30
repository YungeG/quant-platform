"""Fetch PIT Eastmoney concept data for breakout-retest event peers."""

from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Event

import pandas as pd
import requests


PROXY_ENDPOINT = "https://fast.xiaodefa.cn"


def _truthy(value: object) -> bool:
    return value is True or str(value).lower() == "true"


def ts_code(symbol: str) -> str:
    symbol = str(symbol).zfill(6)
    if symbol.startswith(("4", "8", "9")):
        return f"{symbol}.BJ"
    if symbol.startswith(("5", "6", "68")):
        return f"{symbol}.SH"
    return f"{symbol}.SZ"


def request_api(token: str, api_name: str, params: dict) -> tuple[list[str], list[list]]:
    last_error = ""
    for attempt in range(4):
        try:
            response = requests.post(
                PROXY_ENDPOINT,
                headers={"x-api-key": token},
                json={"api_name": api_name, "params": params, "fields": ""},
                timeout=90,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("code") != 0:
                raise RuntimeError(str(payload.get("msg", "proxy API error")))
            data = payload.get("data") or {}
            return list(data.get("fields") or []), list(data.get("items") or [])
        except Exception as exc:  # noqa: BLE001
            last_error = f"{type(exc).__name__}: {exc}"
            Event().wait(0.5 * (2**attempt))
    raise RuntimeError(last_error)


def build_requests(events_path: str) -> tuple[list[tuple[str, str]], list[str]]:
    events = pd.read_csv(events_path, parse_dates=["breakout_date"])
    events["symbol"] = events["symbol"].astype(str).str.zfill(6)
    executed = events[events["execution_reason"] == "executed"]
    by_day = {
        int(day): set(rows["symbol"])
        for day, rows in events.groupby("day_index")
    }
    pairs = set()
    dates = set()
    for row in executed.itertuples(index=False):
        date = row.breakout_date.strftime("%Y%m%d")
        dates.add(date)
        symbols = {row.symbol}
        for day_index in range(int(row.day_index) - 4, int(row.day_index) + 1):
            symbols.update(by_day.get(day_index, set()))
        for symbol in symbols:
            pairs.add((date, ts_code(symbol)))
    return sorted(pairs), sorted(dates)


def _fetch_member(token: str, item: tuple[str, str]) -> dict:
    date, symbol = item
    try:
        fields, rows = request_api(token, "dc_member", {"trade_date": date, "con_code": symbol})
        records = [dict(zip(fields, row, strict=True)) for row in rows]
        return {"date": date, "symbol": symbol, "ok": True, "records": records, "error": ""}
    except Exception as exc:  # noqa: BLE001
        return {"date": date, "symbol": symbol, "ok": False, "records": [], "error": str(exc)}


def _fetch_index(token: str, date: str) -> dict:
    try:
        fields, rows = request_api(token, "dc_index", {"trade_date": date})
        records = [dict(zip(fields, row, strict=True)) for row in rows]
        return {"date": date, "ok": True, "records": records, "error": ""}
    except Exception as exc:  # noqa: BLE001
        return {"date": date, "ok": False, "records": [], "error": str(exc)}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(
    events_path: str,
    token_path: str,
    members_path: str,
    index_path: str,
    queries_path: str,
    manifest_path: str,
    workers: int,
) -> dict:
    token = Path(token_path).read_text(encoding="utf-8").strip()
    pairs, dates = build_requests(events_path)
    prior_queries = (
        pd.read_csv(queries_path, dtype={"date": str, "symbol": str})
        if Path(queries_path).exists()
        else pd.DataFrame()
    )
    completed_members = {
        (str(row.date), str(row.symbol))
        for row in prior_queries.itertuples(index=False)
        if row.kind == "member" and _truthy(row.ok)
    } if len(prior_queries) else set()
    completed_indexes = {
        str(row.date)
        for row in prior_queries.itertuples(index=False)
        if row.kind == "index" and _truthy(row.ok)
    } if len(prior_queries) else set()
    pending_pairs = [item for item in pairs if item not in completed_members]
    pending_dates = [date for date in dates if date not in completed_indexes]
    member_results = []
    index_results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_fetch_member, token, item) for item in pending_pairs]
        for future in as_completed(futures):
            member_results.append(future.result())
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_fetch_index, token, date) for date in pending_dates]
        for future in as_completed(futures):
            index_results.append(future.result())

    existing_members = (
        pd.read_csv(members_path).to_dict("records") if Path(members_path).exists() else []
    )
    existing_indexes = (
        pd.read_csv(index_path).to_dict("records") if Path(index_path).exists() else []
    )
    member_records = existing_members + [
        record for result in member_results for record in result["records"]
    ]
    index_records = existing_indexes + [
        record for result in index_results for record in result["records"]
    ]
    query_records = (prior_queries.to_dict("records") if len(prior_queries) else []) + [
        {"kind": "member", "date": row["date"], "symbol": row["symbol"], "ok": row["ok"], "row_count": len(row["records"]), "error": row["error"]}
        for row in member_results
    ] + [
        {"kind": "index", "date": row["date"], "symbol": "", "ok": row["ok"], "row_count": len(row["records"]), "error": row["error"]}
        for row in index_results
    ]
    outputs = {
        "members": Path(members_path),
        "index": Path(index_path),
        "queries": Path(queries_path),
    }
    member_frame = pd.DataFrame(member_records).drop_duplicates(
        ["trade_date", "ts_code", "con_code"], keep="last"
    )
    index_frame = pd.DataFrame(index_records).drop_duplicates(
        ["trade_date", "ts_code"], keep="last"
    )
    query_frame = pd.DataFrame(query_records)
    query_frame["symbol"] = query_frame["symbol"].fillna("")
    query_frame = query_frame.drop_duplicates(
        ["kind", "date", "symbol"], keep="last"
    ).sort_values(["kind", "date", "symbol"])
    member_frame.to_csv(outputs["members"], index=False)
    index_frame.to_csv(outputs["index"], index=False)
    query_frame.to_csv(outputs["queries"], index=False)
    manifest = {
        "api": ["dc_member", "dc_index"],
        "endpoint": PROXY_ENDPOINT,
        "member_queries": len(pairs),
        "index_queries": len(dates),
        "member_query_success_rate": float(
            query_frame.loc[query_frame["kind"] == "member", "ok"].mean()
        ),
        "index_query_success_rate": float(
            query_frame.loc[query_frame["kind"] == "index", "ok"].mean()
        ),
        "member_rows": len(member_frame),
        "index_rows": len(index_frame),
        "outputs": {
            name: {"path": str(path), "sha256": sha256(path)} for name, path in outputs.items()
        },
    }
    Path(manifest_path).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", default="overall/a-share-breakout-retest-v2-correlation-events.csv")
    parser.add_argument("--token-file", default="/home/ygguo/.config/ai-crypt/xiaodefa-token")
    parser.add_argument("--members", default="overall/a-share-dc-concept-members.csv")
    parser.add_argument("--index", default="overall/a-share-dc-concept-index.csv")
    parser.add_argument("--queries", default="overall/a-share-dc-concept-queries.csv")
    parser.add_argument("--manifest", default="overall/a-share-dc-concept-manifest.json")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args(argv)
    manifest = run(args.events, args.token_file, args.members, args.index, args.queries, args.manifest, args.workers)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
