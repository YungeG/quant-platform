"""Fetch resumable futures, warehouse receipts, and roll lineage for resource products."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from threading import Event

import pandas as pd
import requests

PROXY_ENDPOINT = "https://fast.xiaodefa.cn"
PRODUCTS = {
    "CU": "CUL.SHF",
    "AL": "ALL.SHF",
    "ZN": "ZNL.SHF",
    "PB": "PBL.SHF",
    "NI": "NIL.SHF",
    "SN": "SNL.SHF",
    "RB": "RBL.SHF",
    "HC": "HCL.SHF",
    "J": "JL.DCE",
    "MA": "MAL.ZCE",
    "PP": "PPL.DCE",
    "L": "LL.DCE",
    "V": "VL.DCE",
    "RU": "RUL.SHF",
    "FG": "FGL.ZCE",
    "SC": "SCL.INE",
}
LINEAGE_PRODUCTS = {"SC", "PP", "L"}
FIELDS = {
    "fut_daily": "ts_code,trade_date,open,high,low,close,settle,vol,amount,oi,oi_chg",
    "fut_wsr": "trade_date,symbol,fut_name,warehouse,pre_vol,vol,vol_chg,unit",
    "fut_mapping": "ts_code,trade_date,mapping_ts_code",
}
QUERY_COLUMNS = ["api", "product", "start", "end", "status", "rows", "error"]


def call(token: str, api: str, params: dict) -> tuple[list[dict], str]:
    last = ""
    for attempt in range(15):
        try:
            response = requests.post(
                PROXY_ENDPOINT,
                headers={"x-api-key": token},
                json={"api_name": api, "params": params, "fields": FIELDS[api]},
                timeout=120,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("code") == 0:
                data = payload.get("data") or {}
                rows = [
                    dict(zip(data.get("fields") or [], row, strict=True))
                    for row in (data.get("items") or [])
                ]
                return rows, ""
            raise RuntimeError(str(payload.get("msg", "proxy error")))
        except Exception as error:
            last = f"{type(error).__name__}: {error}"
            Event().wait(30 if "超速" in last or "429" in last else min(8, 0.5 * 2**attempt))
    return [], last


def year_chunks(start: str, end: str) -> list[tuple[str, str]]:
    first, last = pd.Timestamp(start), pd.Timestamp(end)
    return [
        (
            max(first, pd.Timestamp(f"{year}-01-01")).strftime("%Y%m%d"),
            min(last, pd.Timestamp(f"{min(year + 1, last.year)}-12-31")).strftime("%Y%m%d"),
        )
        for year in range(first.year, last.year + 1, 2)
    ]


def month_chunks(start: str, end: str) -> list[tuple[str, str]]:
    first, last = pd.Timestamp(start), pd.Timestamp(end)
    return [
        (max(first, period.start_time).strftime("%Y%m%d"), min(last, period.end_time).strftime("%Y%m%d"))
        for period in pd.period_range(first, last, freq="M")
    ]


def append(path: Path, rows: list[dict], keys: list[str]) -> None:
    old = pd.read_parquet(path) if path.exists() else pd.DataFrame()
    data = pd.concat([old, pd.DataFrame(rows)], ignore_index=True)
    if len(data):
        data = data.drop_duplicates(keys, keep="last")
    data.to_parquet(path, index=False, compression="zstd")


def _selected_products(products: list[str] | tuple[str, ...] | None) -> dict[str, str]:
    names = list(PRODUCTS) if products is None else [name.strip().upper() for name in products if name.strip()]
    unknown = sorted(set(names) - PRODUCTS.keys())
    if unknown:
        raise ValueError(f"unknown products: {','.join(unknown)}")
    return {name: PRODUCTS[name] for name in names}


def _existing(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path) if path.exists() else pd.DataFrame()


def run(
    start: str,
    end: str,
    token_file: str,
    out_dir: str,
    products: list[str] | tuple[str, ...] | None = None,
) -> dict:
    selected = _selected_products(products)
    token = Path(token_file).read_text().strip()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    query_path = out / "queries.csv"
    queries = pd.read_csv(query_path, dtype=str) if query_path.exists() else pd.DataFrame(columns=QUERY_COLUMNS)

    for product, continuous in selected.items():
        done = {
            (row.api, row.product, row.start, row.end)
            for row in queries.itertuples(index=False)
            if row.status == "success"
        }
        updates: list[dict] = []
        continuous_rows: list[dict] = []
        warehouse_rows: list[dict] = []
        mapping_rows: list[dict] = []
        native_rows: list[dict] = []

        def fetch(log_api: str, api: str, key: str, chunk_start: str, chunk_end: str, params: dict) -> list[dict]:
            if (log_api, key, chunk_start, chunk_end) in done:
                return []
            rows, error = call(token, api, params)
            updates.append(
                {
                    "api": log_api,
                    "product": key,
                    "start": chunk_start,
                    "end": chunk_end,
                    "status": "success" if not error else "failed",
                    "rows": len(rows),
                    "error": error,
                }
            )
            Event().wait(0.1)
            return rows

        for chunk_start, chunk_end in year_chunks(start, end):
            continuous_rows.extend(
                fetch(
                    "fut_daily",
                    "fut_daily",
                    product,
                    chunk_start,
                    chunk_end,
                    {"ts_code": continuous, "start_date": chunk_start, "end_date": chunk_end},
                )
            )
            if product in LINEAGE_PRODUCTS:
                mapping_rows.extend(
                    fetch(
                        "fut_mapping",
                        "fut_mapping",
                        product,
                        chunk_start,
                        chunk_end,
                        {"ts_code": continuous, "start_date": chunk_start, "end_date": chunk_end},
                    )
                )

        for chunk_start, chunk_end in month_chunks(start, end):
            warehouse_rows.extend(
                fetch(
                    "fut_wsr",
                    "fut_wsr",
                    product,
                    chunk_start,
                    chunk_end,
                    {"symbol": product, "start_date": chunk_start, "end_date": chunk_end},
                )
            )

        if product in LINEAGE_PRODUCTS:
            mapping = pd.concat([_existing(out / "fut_mapping.parquet"), pd.DataFrame(mapping_rows)], ignore_index=True)
            if len(mapping):
                mapping = mapping.drop_duplicates(["ts_code", "trade_date"], keep="last")
                mapping = mapping[mapping.ts_code.eq(continuous)].copy()
                mapping["trade_date"] = mapping.trade_date.astype(str)
                mapping = mapping[mapping.trade_date.between(pd.Timestamp(start).strftime("%Y%m%d"), pd.Timestamp(end).strftime("%Y%m%d"))]
                for contract, group in mapping.groupby("mapping_ts_code", sort=True):
                    chunk_start, chunk_end = group.trade_date.min(), group.trade_date.max()
                    native_rows.extend(
                        fetch(
                            "fut_daily_native",
                            "fut_daily",
                            f"{product}:{contract}",
                            chunk_start,
                            chunk_end,
                            {"ts_code": contract, "start_date": chunk_start, "end_date": chunk_end},
                        )
                    )

        if continuous_rows:
            append(out / "fut_daily.parquet", continuous_rows, ["ts_code", "trade_date"])
        if warehouse_rows:
            append(out / "fut_wsr.parquet", warehouse_rows, ["trade_date", "symbol", "warehouse", "unit"])
        if mapping_rows:
            append(out / "fut_mapping.parquet", mapping_rows, ["ts_code", "trade_date"])
        if native_rows:
            append(out / "fut_native_daily.parquet", native_rows, ["ts_code", "trade_date"])
        if updates:
            queries = pd.concat([queries, pd.DataFrame(updates)], ignore_index=True)
            queries = queries.drop_duplicates(["api", "product", "start", "end"], keep="last")
            queries = queries.sort_values(["api", "product", "start"])
            queries.to_csv(query_path, index=False)

    manifest = {
        "endpoint": PROXY_ENDPOINT,
        "start": start,
        "end": end,
        "products": selected,
        "successful_queries": int(queries.status.eq("success").sum()),
        "failed_queries": queries[queries.status.ne("success")].to_dict("records"),
        "outputs": {},
    }
    for name in ["fut_daily", "fut_wsr", "fut_mapping", "fut_native_daily"]:
        path = out / f"{name}.parquet"
        data = pd.read_parquet(path) if path.exists() else pd.DataFrame()
        manifest["outputs"][name] = {
            "path": str(path),
            "rows": len(data),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None,
        }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2018-01-01")
    parser.add_argument("--end", default="2026-08-27")
    parser.add_argument("--token-file", default="/home/ygguo/.config/ai-crypt/xiaodefa-token")
    parser.add_argument("--out-dir", default="overall/a-share-resource-cycle-raw")
    parser.add_argument("--products", help="comma-separated product roots; default: all")
    args = parser.parse_args(argv)
    result = run(
        args.start,
        args.end,
        args.token_file,
        args.out_dir,
        args.products.split(",") if args.products else None,
    )
    print(json.dumps({key: result[key] for key in ["successful_queries", "failed_queries", "outputs"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
