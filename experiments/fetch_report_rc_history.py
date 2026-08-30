"""Fetch complete report_rc history with one bounded request per calendar date."""

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


def request_date(token: str, date: str) -> tuple[list[str], list[list]]:
    fields: list[str] = []
    rows: list[list] = []
    offset = 0
    while True:
        last_error = ""
        for attempt in range(5):
            try:
                response = requests.post(
                    PROXY_ENDPOINT,
                    headers={"x-api-key": token},
                    json={
                        "api_name": "report_rc",
                        "params": {"report_date": date, "offset": offset},
                        "fields": "",
                    },
                    timeout=90,
                )
                response.raise_for_status()
                payload = response.json()
                if payload.get("code") != 0:
                    raise RuntimeError(str(payload.get("msg", "proxy API error")))
                data = payload.get("data") or {}
                page_fields = list(data.get("fields") or [])
                page_rows = list(data.get("items") or [])
                if fields and page_fields != fields:
                    raise RuntimeError("report_rc field schema changed between pages")
                fields = page_fields
                rows.extend(page_rows)
                if len(page_rows) < 5000:
                    return fields, rows
                offset += len(page_rows)
                break
            except Exception as exc:  # noqa: BLE001
                last_error = f"{type(exc).__name__}: {exc}"
                Event().wait(0.5 * (2**attempt))
        else:
            raise RuntimeError(last_error)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _flush(output: Path, query_path: Path, results: list[dict]) -> None:
    if not results:
        return
    by_year: dict[str, list[dict]] = {}
    for result in results:
        if result["ok"]:
            by_year.setdefault(result["date"][:4], []).extend(result["records"])
    for year, records in by_year.items():
        if not records:
            continue
        path = output / f"report_rc_{year}.csv"
        pd.DataFrame(records).to_csv(path, mode="a", header=not path.exists(), index=False)
    query_records = [
        {
            "date": result["date"],
            "ok": result["ok"],
            "row_count": len(result["records"]),
            "error": result["error"],
        }
        for result in results
    ]
    pd.DataFrame(query_records).to_csv(
        query_path, mode="a", header=not query_path.exists(), index=False
    )


def _fetch(token: str, date: str) -> dict:
    try:
        fields, rows = request_date(token, date)
        return {
            "date": date,
            "ok": True,
            "records": [dict(zip(fields, row, strict=True)) for row in rows],
            "error": "",
        }
    except Exception as exc:  # noqa: BLE001
        return {"date": date, "ok": False, "records": [], "error": str(exc)}


def run(start: str, end: str, token_file: str, output_dir: str, workers: int) -> dict:
    token = Path(token_file).read_text(encoding="utf-8").strip()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    query_path = output / "queries.csv"
    completed = set()
    if query_path.exists():
        prior = pd.read_csv(query_path, dtype={"date": str})
        completed = set(prior.loc[prior["ok"].astype(str).str.lower() == "true", "date"])
    dates = [date.strftime("%Y%m%d") for date in pd.date_range(start, end, freq="D")]
    pending = [date for date in dates if date not in completed]
    batch = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_fetch, token, date) for date in pending]
        for future in as_completed(futures):
            batch.append(future.result())
            if len(batch) >= 25:
                _flush(output, query_path, batch)
                batch.clear()
    _flush(output, query_path, batch)

    queries = pd.read_csv(query_path, dtype={"date": str}).drop_duplicates("date", keep="last")
    year_paths = sorted(output.glob("report_rc_[0-9][0-9][0-9][0-9].csv"))
    manifest = {
        "endpoint": PROXY_ENDPOINT,
        "start": start,
        "end": end,
        "date_count": len(dates),
        "success_rate": float(queries["ok"].astype(str).str.lower().eq("true").mean()),
        "row_count": int(queries.loc[queries["ok"].astype(str).str.lower().eq("true"), "row_count"].sum()),
        "outputs": {
            "queries": {"path": str(query_path), "sha256": sha256(query_path)},
            **{
                path.stem: {"path": str(path), "sha256": sha256(path)} for path in year_paths
            },
        },
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2016-01-01")
    parser.add_argument("--end", default="2026-08-26")
    parser.add_argument("--token-file", default="/home/ygguo/.config/ai-crypt/xiaodefa-token")
    parser.add_argument("--output-dir", default="overall/a-share-report-rc-raw")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.start, args.end, args.token_file, args.output_dir, args.workers), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
