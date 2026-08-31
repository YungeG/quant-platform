"""Capture official CSI300/500/1000 rebalance notices and attachments."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

BASE_URL = "https://www.csindex.com.cn/csindex-home"
SEARCH_PATH = "/announcement/queryAnnouncementByVo"
DETAIL_PATH = "/announcement/queryAnnouncementById"
QUERIES = ("沪深300", "中证500", "中证1000")
TARGETS = {"沪深300": "000300", "中证500": "000905", "中证1000": "000852"}
_DATE_RE = re.compile(r"(?:于|自)(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日(?:收市|收盘)?后?(?:生效|调整|起)")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _effective_dates(content: str, publish_date: str) -> list[str]:
    publish_year = int(publish_date[:4])
    return sorted({
        f"{int(year) if year else publish_year:04d}-{int(month):02d}-{int(day):02d}"
        for year, month, day in _DATE_RE.findall(re.sub(r"<[^>]+>", "", content or ""))
    })


def _search(session: requests.Session, query: str) -> list[dict]:
    notices: list[dict] = []
    page = 1
    while True:
        payload = {
            "lang": "cn",
            "searchInput": query,
            "classList": ["index"],
            "typeList": ["announcement"],
            "relatedTopics": ["index_rebalance"],
            "indexList": [],
            "page": {"desc": "", "key": "", "page": page, "rows": 100, "sortBy": "publish_date"},
        }
        response = session.post(BASE_URL + SEARCH_PATH, json=payload, timeout=30)
        response.raise_for_status()
        body = response.json()
        if body.get("code") != "200":
            raise RuntimeError(f"CSI search failed for {query}: {body.get('msg')}")
        notices.extend(body["data"])
        if page * 100 >= int(body["total"]):
            return notices
        page += 1


def _detail(session: requests.Session, notice_id: int) -> dict:
    response = session.get(BASE_URL + DETAIL_PATH, params={"id": notice_id}, timeout=30)
    response.raise_for_status()
    body = response.json()
    if body.get("code") != "200" or not body.get("data"):
        raise RuntimeError(f"CSI detail failed for notice {notice_id}")
    return body["data"]


def _attachment_name(notice_id: int, enclosure: dict) -> str:
    suffix = Path(unquote(urlparse(enclosure["fileUrl"]).path)).suffix.lower() or ".bin"
    return f"{notice_id}-{enclosure['id']}{suffix}"


def run(start_date: str, end_date: str, out_dir: str, delay_seconds: float = 1.0) -> dict:
    if delay_seconds < 0:
        raise ValueError("delay_seconds must be nonnegative")
    start, end = str(start_date), str(end_date)
    output = Path(out_dir)
    attachments = output / "attachments"
    record_dir = output / "records"
    attachments.mkdir(parents=True, exist_ok=True)
    record_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "quant-platform-csi-source-audit/1"})
    search_counts: dict[str, int] = {}
    summaries: dict[int, dict] = {}
    for query in QUERIES:
        found = _search(session, query)
        search_counts[query] = len(found)
        for notice in found:
            if start <= notice["publishDate"] <= end:
                summaries[int(notice["id"])] = notice
    records = []
    current_notice_id = None
    try:
        for notice_id in sorted(summaries, key=lambda value: (summaries[value]["publishDate"], value)):
            current_notice_id = notice_id
            cached = record_dir / f"{notice_id}.json"
            if cached.exists():
                records.append(json.loads(cached.read_text(encoding="utf-8")))
                continue
            time.sleep(delay_seconds)
            detail = _detail(session, notice_id)
            content = detail.get("content") or ""
            searchable = detail.get("title", "") + re.sub(r"<[^>]+>", "", content)
            indices = {name: code for name, code in TARGETS.items() if name in searchable}
            if not indices:
                continue
            captured_enclosures = []
            for enclosure in detail.get("enclosureList") or []:
                time.sleep(delay_seconds)
                response = session.get(enclosure["fileUrl"], timeout=60)
                response.raise_for_status()
                name = _attachment_name(notice_id, enclosure)
                data = response.content
                (attachments / name).write_bytes(data)
                captured_enclosures.append({
                    "source_id": enclosure["id"],
                    "file_name": enclosure["fileName"],
                    "source_url": enclosure["fileUrl"],
                    "create_at": enclosure.get("createAt"),
                    "update_at": enclosure.get("updateAt"),
                    "local_file": f"attachments/{name}",
                    "size": len(data),
                    "sha256": _sha256(data),
                })
            canonical_detail = json.dumps(detail, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
            record = {
                "notice_id": notice_id,
                "title": detail["title"],
                "publish_date": detail["publishDate"],
                "notice_status": detail.get("noticeStatus"),
                "indices": indices,
                "effective_dates": _effective_dates(content, detail["publishDate"]),
                "detail_sha256": _sha256(canonical_detail),
                "content_html": content,
                "enclosures": captured_enclosures,
                "source_detail_url": f"{BASE_URL}{DETAIL_PATH}?id={notice_id}",
            }
            cached.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            records.append(record)
    except Exception as exc:
        (output / "failure.json").write_text(json.dumps({
            "failed_notice_id": current_notice_id,
            "captured_notice_count": len(records),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise
    output.mkdir(parents=True, exist_ok=True)
    with (output / "notices.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    manifest = {
        "source": "CSI official announcement API",
        "base_url": BASE_URL,
        "search_path": SEARCH_PATH,
        "detail_path": DETAIL_PATH,
        "capture_time_utc": datetime.now(timezone.utc).isoformat(),
        "requested_interval": [start, end],
        "queries": list(QUERIES),
        "search_counts": search_counts,
        "notice_count": len(records),
        "attachment_count": sum(len(record["enclosures"]) for record in records),
        "exact_effective_date_count": sum(bool(record["effective_dates"]) for record in records),
        "earliest_publish_date": records[0]["publish_date"] if records else None,
        "latest_publish_date": records[-1]["publish_date"] if records else None,
        "records_sha256": _sha256((output / "notices.jsonl").read_bytes()),
        "trade_authorized": False,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "failure.json").unlink(missing_ok=True)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", default="2016-01-01")
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.start_date, args.end_date, args.out_dir, args.delay_seconds), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
