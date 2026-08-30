"""Fetch full-market cyq_perf snapshots for each month end."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from threading import Event

import pandas as pd
import requests


PROXY_ENDPOINT = "https://fast.xiaodefa.cn"
def run(start: str, end: str, calendar_path: str, token_file: str, output: str, manifest: str) -> dict:
    calendar = pd.read_csv(calendar_path, parse_dates=["trade_date"])
    sessions = calendar.loc[
        calendar["trade_date"].between(start, end), "trade_date"
    ].drop_duplicates().sort_values()
    dates = sessions.groupby(sessions.dt.to_period("M")).max()
    token = Path(token_file).read_text(encoding="utf-8").strip()
    records = []
    counts = []
    for day in dates:
        trade_date = pd.Timestamp(day).strftime("%Y%m%d")
        offset = 0
        date_rows = []
        while True:
            for attempt in range(15):
                response = requests.post(
                    PROXY_ENDPOINT,
                    headers={"x-api-key": token},
                    json={"api_name": "cyq_perf", "params": {"trade_date": trade_date, "offset": offset}, "fields": ""},
                    timeout=120,
                )
                response.raise_for_status()
                payload = response.json()
                if payload.get("code") == 0:
                    break
                if "超速" not in str(payload.get("msg", "")):
                    raise RuntimeError(str(payload.get("msg", "proxy API error")))
                Event().wait(30)
            else:
                raise RuntimeError("proxy rate-limit cooldown did not clear")
            data = payload.get("data") or {}
            fields = list(data.get("fields") or [])
            rows = list(data.get("items") or [])
            date_rows.extend(rows)
            if len(rows) < 6_000:
                break
            offset += len(rows)
        Event().wait(0.2)
        records.extend(dict(zip(fields, row, strict=True)) for row in date_rows)
        counts.append({"trade_date": trade_date, "row_count": len(date_rows)})
    output_path = Path(output)
    frame = pd.DataFrame(records).drop_duplicates(["ts_code", "trade_date"], keep="last")
    frame.to_csv(output_path, index=False)
    result = {
        "endpoint": PROXY_ENDPOINT,
        "api": "cyq_perf",
        "dates": counts,
        "row_count": len(frame),
        "output": {"path": str(output_path), "sha256": hashlib.sha256(output_path.read_bytes()).hexdigest()},
    }
    Path(manifest).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2018-01-01")
    parser.add_argument("--end", default="2026-08-26")
    parser.add_argument("--calendar", default="overall/a-share-multi-asset-etf-daily.csv")
    parser.add_argument("--token-file", default="/home/ygguo/.config/ai-crypt/xiaodefa-token")
    parser.add_argument("--output", default="overall/a-share-cyq-month-ends.csv")
    parser.add_argument("--manifest", default="overall/a-share-cyq-month-ends-manifest.json")
    args = parser.parse_args(argv)
    print(json.dumps(run(args.start, args.end, args.calendar, args.token_file, args.output, args.manifest), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
