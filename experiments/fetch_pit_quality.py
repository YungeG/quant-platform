"""Fetch annual PIT quality indicators through the approved proxy."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd
import requests


PROXY_ENDPOINT = "https://fast.xiaodefa.cn"
FIELDS = "ts_code,ann_date,end_date,roe_waa,grossprofit_margin,debt_to_assets,update_flag"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(start_year: int, end_year: int, token_file: str, output: str, manifest: str) -> dict:
    token = Path(token_file).read_text(encoding="utf-8").strip()
    records = []
    queries = []
    for year in range(start_year, end_year + 1):
        period = f"{year}1231"
        period_rows = []
        offset = 0
        while True:
            response = requests.post(
                PROXY_ENDPOINT,
                headers={"x-api-key": token},
                json={
                    "api_name": "fina_indicator_vip",
                    "params": {"period": period, "offset": offset},
                    "fields": FIELDS,
                },
                timeout=120,
            )
            response.raise_for_status()
            api_payload = response.json()
            if api_payload.get("code") != 0:
                raise RuntimeError(str(api_payload.get("msg", "proxy API error")))
            data = api_payload.get("data") or {}
            fields = list(data.get("fields") or [])
            rows = list(data.get("items") or [])
            period_rows.extend(rows)
            if len(rows) < 12_000:
                break
            offset += len(rows)
        records.extend(dict(zip(fields, row, strict=True)) for row in period_rows)
        queries.append({"period": period, "row_count": len(period_rows)})
    output_path = Path(output)
    pd.DataFrame(records).drop_duplicates(keep="last").to_csv(output_path, index=False)
    payload = {
        "endpoint": PROXY_ENDPOINT,
        "api": "fina_indicator_vip",
        "periods": queries,
        "row_count": len(records),
        "output": {"path": str(output_path), "sha256": sha256(output_path)},
    }
    Path(manifest).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year", type=int, default=2012)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--token-file", default="/home/ygguo/.config/ai-crypt/xiaodefa-token")
    parser.add_argument("--output", default="overall/a-share-pit-quality.csv")
    parser.add_argument("--manifest", default="overall/a-share-pit-quality-manifest.json")
    args = parser.parse_args(argv)
    print(json.dumps(run(args.start_year, args.end_year, args.token_file, args.output, args.manifest), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
