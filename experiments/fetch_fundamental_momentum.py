"""Fetch quarterly PIT fundamental-momentum fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from threading import Event

import pandas as pd
import requests


PROXY_ENDPOINT = "https://fast.xiaodefa.cn"
FIELDS = "ts_code,ann_date,end_date,q_sales_yoy,q_roe,q_ocf_to_sales,update_flag"


def run(start_year: int, end_period: str, token_file: str, output: str, manifest: str) -> dict:
    token = Path(token_file).read_text(encoding="utf-8").strip()
    periods = [
        f"{year}{suffix}"
        for year in range(start_year, int(end_period[:4]) + 1)
        for suffix in ("0331", "0630", "0930", "1231")
        if f"{year}{suffix}" <= end_period
    ]
    records = []
    counts = []
    for period in periods:
        offset = 0
        period_rows = []
        while True:
            for attempt in range(15):
                response = requests.post(
                    PROXY_ENDPOINT,
                    headers={"x-api-key": token},
                    json={"api_name": "fina_indicator_vip", "params": {"period": period, "offset": offset}, "fields": FIELDS},
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
            period_rows.extend(rows)
            if len(rows) < 12_000:
                break
            offset += len(rows)
        Event().wait(0.2)
        records.extend(dict(zip(fields, row, strict=True)) for row in period_rows)
        counts.append({"period": period, "row_count": len(period_rows)})
    output_path = Path(output)
    frame = pd.DataFrame(records).drop_duplicates(keep="last")
    frame.to_csv(output_path, index=False)
    result = {
        "endpoint": PROXY_ENDPOINT,
        "api": "fina_indicator_vip",
        "periods": counts,
        "row_count": len(frame),
        "output": {"path": str(output_path), "sha256": hashlib.sha256(output_path.read_bytes()).hexdigest()},
    }
    Path(manifest).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year", type=int, default=2015)
    parser.add_argument("--end-period", default="20260630")
    parser.add_argument("--token-file", default="/home/ygguo/.config/ai-crypt/xiaodefa-token")
    parser.add_argument("--output", default="overall/a-share-fundamental-momentum.csv")
    parser.add_argument("--manifest", default="overall/a-share-fundamental-momentum-manifest.json")
    args = parser.parse_args(argv)
    print(json.dumps(run(args.start_year, args.end_period, args.token_file, args.output, args.manifest), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
