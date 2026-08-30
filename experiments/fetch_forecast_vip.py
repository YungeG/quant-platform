"""Fetch period-batched earnings forecasts through the approved xiaodefa proxy."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from threading import Event

import pandas as pd
import requests


END_MONTHS = ("0331", "0630", "0930", "1231")
PROXY_ENDPOINT = "https://fast.xiaodefa.cn"


def periods(start_year: int, end_year: int, final_period: str) -> list[str]:
    values = [f"{year}{ending}" for year in range(start_year, end_year + 1) for ending in END_MONTHS]
    return [value for value in values if value <= final_period]


def fetch_period(token: str, period: str) -> tuple[dict, bytes]:
    response = requests.post(
        PROXY_ENDPOINT,
        headers={"x-api-key": token, "Content-Type": "application/json", "Accept-Encoding": "gzip"},
        json={"api_name": "forecast_vip", "params": {"period": period}, "fields": ""},
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != 0:
        raise RuntimeError(f"forecast_vip {period}: {payload.get('msg') or payload.get('detail')}")
    return payload, response.content


def run(token_path: str, output: str, manifest_path: str) -> dict:
    token = Path(token_path).read_text(encoding="utf-8").strip()
    frames = []
    manifest_rows = []
    for period in periods(2015, 2026, "20260930"):
        last_error = None
        for attempt in range(3):
            try:
                payload, source = fetch_period(token, period)
                break
            except Exception as error:
                last_error = error
                if attempt == 2:
                    raise
                Event().wait(1.0)
        else:
            raise RuntimeError(str(last_error))
        data = payload["data"]
        frame = pd.DataFrame(data.get("items", []), columns=data.get("fields", []))
        frame["requested_period"] = period
        frames.append(frame)
        manifest_rows.append(
            {
                "period": period,
                "rows": len(frame),
                "has_more": bool(data.get("has_more")),
                "response_sha256": hashlib.sha256(source).hexdigest(),
            }
        )
        print(period, len(frame))
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(["end_date", "ts_code", "ann_date", "update_flag"])
    Path(output).write_text(combined.to_csv(index=False), encoding="utf-8")
    manifest = {
        "endpoint": PROXY_ENDPOINT,
        "api_name": "forecast_vip",
        "rows": len(combined),
        "periods": manifest_rows,
        "output_sha256": hashlib.sha256(Path(output).read_bytes()).hexdigest(),
    }
    Path(manifest_path).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--token-file", default="/home/ygguo/.config/ai-crypt/xiaodefa-token")
    parser.add_argument("--output", default="overall/a-share-forecast-vip.csv")
    parser.add_argument("--manifest", default="overall/a-share-forecast-vip-manifest.json")
    args = parser.parse_args(argv)
    manifest = run(args.token_file, args.output, args.manifest)
    print(json.dumps({"rows": manifest["rows"], "output_sha256": manifest["output_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
