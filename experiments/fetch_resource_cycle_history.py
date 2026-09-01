"""Fetch resumable futures, warehouse receipts, and roll lineage for resource products."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
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
QUERY_COLUMNS = [
    "api",
    "product",
    "start",
    "end",
    "status",
    "rows",
    "error",
    "retrieved_at_utc",
    "raw_path",
    "response_sha256",
]


def call(token: str, api: str, params: dict) -> tuple[list[dict], str, bytes]:
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
                return rows, "", response.content
            raise RuntimeError(str(payload.get("msg", "proxy error")))
        except Exception as error:
            last = f"{type(error).__name__}: {error}"
            delay = min(8, 0.5 * 2**attempt)
            if "超速" in last:
                delay = 30
            if "429" in last:
                delay = 30
            Event().wait(delay)
    return [], last, b""


def year_chunks(start: str, end: str) -> list[tuple[str, str]]:
    first, last = pd.Timestamp(start), pd.Timestamp(end)
    if first > last:
        raise ValueError(f"start must not exceed end: {start} > {end}")
    return [
        (
            max(first, pd.Timestamp(f"{year}-01-01")).strftime("%Y%m%d"),
            min(last, pd.Timestamp(f"{min(year + 1, last.year)}-12-31")).strftime("%Y%m%d"),
        )
        for year in range(first.year, last.year + 1, 2)
    ]


def month_chunks(start: str, end: str) -> list[tuple[str, str]]:
    first, last = pd.Timestamp(start), pd.Timestamp(end)
    if first > last:
        raise ValueError(f"start must not exceed end: {start} > {end}")
    return [
        (max(first, period.start_time).strftime("%Y%m%d"), min(last, period.end_time).strftime("%Y%m%d"))
        for period in pd.period_range(first, last, freq="M")
    ]


def append(path: Path, rows: list[dict], keys: list[str]) -> None:
    old = pd.read_parquet(path) if path.exists() else pd.DataFrame()
    data = pd.concat([old, pd.DataFrame(rows)], ignore_index=True)
    if len(data):
        duplicates = data[data.duplicated(keys, keep=False)]
        for _, group in duplicates.groupby(keys, dropna=False, sort=False):
            if len(group.drop_duplicates()) > 1:
                raise ValueError(f"conflicting duplicate source rows for {keys}: {group.iloc[0][keys].to_dict()}")
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _raw_receipt_digest(out: Path) -> tuple[int, str | None]:
    files = sorted((out / "raw").rglob("*.json")) if (out / "raw").exists() else []
    digest = hashlib.sha256()
    for path in files:
        digest.update(str(path.relative_to(out)).encode())
        digest.update(path.read_bytes())
    return len(files), digest.hexdigest() if files else None


def _validate_existing_capture(out: Path, manifest: dict) -> None:
    if not {"query_ledger", "outputs", "raw_responses"}.issubset(manifest):
        raise ValueError("existing manifest lacks required integrity sections")

    query = manifest["query_ledger"]
    query_path = out / "queries.csv"
    if Path(query["path"]) != query_path:
        raise ValueError("existing query ledger path does not match output directory")
    if not query_path.exists() or _sha256(query_path) != query["sha256"] or len(pd.read_csv(query_path)) != query["rows"]:
        raise ValueError("existing query ledger failed integrity validation")

    outputs = manifest["outputs"]
    actual_output_names = {path.stem for path in out.glob("*.parquet")}
    if actual_output_names - outputs.keys():
        raise ValueError("existing capture contains unmanifested Parquet outputs")
    for name, record in outputs.items():
        path = out / f"{name}.parquet"
        if Path(record["path"]) != path:
            raise ValueError(f"existing output path does not match output directory: {name}")
        if record.get("sha256"):
            if not path.exists() or _sha256(path) != record["sha256"] or len(pd.read_parquet(path)) != record["rows"]:
                raise ValueError(f"existing output failed integrity validation: {path}")
        elif path.exists():
            raise ValueError(f"existing output is present without a manifest digest: {path}")

    raw = manifest["raw_responses"]
    if Path(raw["path"]) != out / "raw":
        raise ValueError("existing raw-response path does not match output directory")
    count, digest = _raw_receipt_digest(out)
    if count != raw["files"] or digest != raw["sha256"]:
        raise ValueError("existing raw responses failed integrity validation")


def run(
    start: str,
    end: str,
    token_file: str,
    out_dir: str,
    products: list[str] | tuple[str, ...] | None = None,
) -> dict:
    selected = _selected_products(products)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"
    if not manifest_path.exists() and any(out.iterdir()):
        raise ValueError("existing capture artifacts require a manifest")
    if manifest_path.exists():
        try:
            existing_manifest = json.loads(manifest_path.read_text())
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"invalid existing manifest: {manifest_path}") from error
        existing_scope = (existing_manifest.get("start"), existing_manifest.get("end"), existing_manifest.get("products"))
        requested_scope = (start, end, selected)
        if existing_scope != requested_scope:
            raise ValueError(f"output directory scope mismatch: existing={existing_scope}, requested={requested_scope}")
        _validate_existing_capture(out, existing_manifest)
    token = Path(token_file).read_text().strip()
    query_path = out / "queries.csv"
    queries = pd.read_csv(query_path, dtype=str) if query_path.exists() else pd.DataFrame(columns=QUERY_COLUMNS)
    for column in QUERY_COLUMNS:
        if column not in queries:
            queries[column] = pd.NA
    queries = queries[QUERY_COLUMNS]

    for product, continuous in selected.items():
        done = {
            (row.api, row.product, row.start, row.end)
            for row in queries.itertuples(index=False)
            if row.status == "success"
            and isinstance(row.raw_path, str)
            and isinstance(row.response_sha256, str)
            and (out / row.raw_path).exists()
            and hashlib.sha256((out / row.raw_path).read_bytes()).hexdigest() == row.response_sha256
        }
        updates: list[dict] = []
        continuous_rows: list[dict] = []
        warehouse_rows: list[dict] = []
        mapping_rows: list[dict] = []
        native_rows: list[dict] = []

        def fetch(log_api: str, api: str, key: str, chunk_start: str, chunk_end: str, params: dict) -> list[dict]:
            if (log_api, key, chunk_start, chunk_end) in done:
                return []
            rows, error, raw = call(token, api, params)
            relative_raw = Path("raw") / log_api / re.sub(r"[^A-Za-z0-9_.-]+", "_", key) / f"{chunk_start}-{chunk_end}.json"
            if raw:
                raw_path = out / relative_raw
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                raw_path.write_bytes(raw)
            updates.append(
                {
                    "api": log_api,
                    "product": key,
                    "start": chunk_start,
                    "end": chunk_end,
                    "status": "success" if not error else "failed",
                    "rows": len(rows),
                    "error": error,
                    "retrieved_at_utc": datetime.now(UTC).isoformat(),
                    "raw_path": str(relative_raw) if raw else "",
                    "response_sha256": hashlib.sha256(raw).hexdigest() if raw else "",
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
                if native_rows:
                    allowed = mapping[["mapping_ts_code", "trade_date"]].rename(columns={"mapping_ts_code": "ts_code"})
                    native_rows = pd.DataFrame(native_rows).merge(allowed, on=["ts_code", "trade_date"], how="inner").to_dict("records")

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

    if LINEAGE_PRODUCTS.intersection(selected):
        mapping = _existing(out / "fut_mapping.parquet")
        native = _existing(out / "fut_native_daily.parquet")
        selected_codes = set(selected.values())
        mapping = mapping[mapping.ts_code.isin(selected_codes)].copy()
        mapping["trade_date"] = mapping.trade_date.astype(str)
        mapping = mapping[mapping.trade_date.between(pd.Timestamp(start).strftime("%Y%m%d"), pd.Timestamp(end).strftime("%Y%m%d"))]
        expected = set(mapping[["mapping_ts_code", "trade_date"]].itertuples(index=False, name=None))
        actual = set(native[["ts_code", "trade_date"]].astype(str).itertuples(index=False, name=None))
        missing, extra = expected - actual, actual - expected
        if missing or extra:
            raise RuntimeError(f"mapping/native exact-cover failure: missing={len(missing)}, extra={len(extra)}")

    successful = queries[queries.status.eq("success")]
    manifest = {
        "endpoint": PROXY_ENDPOINT,
        "start": start,
        "end": end,
        "products": selected,
        "retrieved_at_utc": successful.retrieved_at_utc.dropna().max() if len(successful) else None,
        "successful_queries": len(successful),
        "failed_queries": queries[queries.status.ne("success")].to_dict("records"),
        "outputs": {},
    }
    for name in ["fut_daily", "fut_wsr", "fut_mapping", "fut_native_daily"]:
        path = out / f"{name}.parquet"
        data = pd.read_parquet(path) if path.exists() else pd.DataFrame()
        manifest["outputs"][name] = {
            "path": str(path),
            "rows": len(data),
            "sha256": _sha256(path) if path.exists() else None,
        }
    manifest["query_ledger"] = {
        "path": str(query_path),
        "rows": len(queries),
        "sha256": _sha256(query_path) if query_path.exists() else None,
    }
    raw_files, raw_digest = _raw_receipt_digest(out)
    manifest["raw_responses"] = {
        "path": str(out / "raw"),
        "files": raw_files,
        "sha256": raw_digest,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
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
