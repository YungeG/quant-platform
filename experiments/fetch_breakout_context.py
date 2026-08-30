"""Fetch proxy context data for frozen breakout-retest events."""

from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta
from pathlib import Path
from threading import Event

import pandas as pd
import requests


PROXY_ENDPOINT = "https://fast.xiaodefa.cn"
APIS = ("cyq_perf", "moneyflow_ths", "moneyflow_dc", "limit_list_d", "hm_detail", "report_rc")


def ts_code(symbol: str) -> str:
    symbol = str(symbol).zfill(6)
    if symbol.startswith(("4", "8", "9")):
        return f"{symbol}.BJ"
    if symbol.startswith(("5", "6", "68")):
        return f"{symbol}.SH"
    return f"{symbol}.SZ"


def _truthy(value: object) -> bool:
    return value is True or str(value).lower() == "true"


def request_api(token: str, api_name: str, params: dict) -> tuple[list[str], list[list]]:
    last_error = ""
    for attempt in range(5):
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


def build_requests(events_path: str) -> list[dict]:
    events = pd.read_csv(events_path, parse_dates=["signal_date"])
    executed = events[events["execution_reason"] == "executed"].copy()
    executed["symbol"] = executed["symbol"].astype(str).str.zfill(6)
    requests_to_make = []
    for row in executed.itertuples(index=False):
        signal = pd.Timestamp(row.signal_date)
        code = ts_code(row.symbol)
        exact = signal.strftime("%Y%m%d")
        start5 = (signal - timedelta(days=10)).strftime("%Y%m%d")
        start180 = (signal - timedelta(days=180)).strftime("%Y%m%d")
        params = {
            "cyq_perf": {"ts_code": code, "trade_date": exact},
            "moneyflow_ths": {"ts_code": code, "trade_date": exact},
            "moneyflow_dc": {"ts_code": code, "trade_date": exact},
            "limit_list_d": {"ts_code": code, "start_date": start5, "end_date": exact},
            "hm_detail": {"ts_code": code, "start_date": start5, "end_date": exact},
            "report_rc": {"ts_code": code, "start_date": start180, "end_date": exact},
        }
        for api in APIS:
            requests_to_make.append(
                {"event_id": row.event_id, "api": api, "params": params[api]}
            )
    return requests_to_make


def _fetch(token: str, request: dict) -> dict:
    try:
        fields, rows = request_api(token, request["api"], request["params"])
        records = [
            {"event_id": request["event_id"], **dict(zip(fields, row, strict=True))}
            for row in rows
        ]
        return {**request, "ok": True, "records": records, "error": ""}
    except Exception as exc:  # noqa: BLE001
        return {**request, "ok": False, "records": [], "error": str(exc)}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(events: str, token_file: str, output_dir: str, workers: int) -> dict:
    token = Path(token_file).read_text(encoding="utf-8").strip()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    query_path = output / "queries.csv"
    prior = pd.read_csv(query_path, dtype=str) if query_path.exists() else pd.DataFrame()
    completed = {
        (str(row.event_id), str(row.api))
        for row in prior.itertuples(index=False)
        if _truthy(row.ok)
    } if len(prior) else set()
    requests_to_make = build_requests(events)
    pending = [
        request
        for request in requests_to_make
        if (request["event_id"], request["api"]) not in completed
    ]
    results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_fetch, token, request) for request in pending]
        for future in as_completed(futures):
            results.append(future.result())

    query_records = (prior.to_dict("records") if len(prior) else []) + [
        {
            "event_id": result["event_id"],
            "api": result["api"],
            "params": json.dumps(result["params"], ensure_ascii=False, sort_keys=True),
            "ok": result["ok"],
            "row_count": len(result["records"]),
            "error": result["error"],
        }
        for result in results
    ]
    query_frame = pd.DataFrame(query_records).drop_duplicates(
        ["event_id", "api"], keep="last"
    ).sort_values(["event_id", "api"])
    query_frame.to_csv(query_path, index=False)

    paths = {api: output / f"{api}.csv" for api in APIS}
    for api, path in paths.items():
        old = pd.read_csv(path).to_dict("records") if path.exists() else []
        new = [
            record
            for result in results
            if result["api"] == api
            for record in result["records"]
        ]
        frame = pd.DataFrame(old + new)
        if len(frame):
            frame = frame.drop_duplicates(keep="last")
        frame.to_csv(path, index=False)

    success = query_frame["ok"].map(_truthy)
    manifest = {
        "endpoint": PROXY_ENDPOINT,
        "event_count": len(requests_to_make) // len(APIS),
        "query_count": len(requests_to_make),
        "query_success_rate": float(success.mean()),
        "api_success_rates": {
            api: float(success[query_frame["api"] == api].mean()) for api in APIS
        },
        "outputs": {
            "queries": {"path": str(query_path), "sha256": sha256(query_path)},
            **{
                api: {"path": str(path), "sha256": sha256(path)}
                for api, path in paths.items()
            },
        },
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", default="overall/a-share-breakout-retest-v2-events.csv")
    parser.add_argument("--token-file", default="/home/ygguo/.config/ai-crypt/xiaodefa-token")
    parser.add_argument("--output-dir", default="overall/a-share-breakout-context-raw")
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.events, args.token_file, args.output_dir, args.workers), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
