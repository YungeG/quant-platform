"""Capture official CNINFO A-share dividend implementation announcements."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

QUERY_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
PDF_ROOT = "https://static.cninfo.com.cn/"
KEYWORD = "权益分派实施公告"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _title(value: str) -> str:
    return re.sub(r"</?em>", "", value or "")


def _query(session: requests.Session, start_date: str, end_date: str) -> list[dict]:
    rows = []
    page = 1
    while True:
        payload = {
            "pageNum": page,
            "pageSize": 30,
            "column": "szse",
            "tabName": "fulltext",
            "plate": "",
            "stock": "",
            "searchkey": KEYWORD,
            "secid": "",
            "category": "",
            "trade": "",
            "seDate": f"{start_date}~{end_date}",
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true",
        }
        response = session.post(QUERY_URL, data=payload, timeout=30)
        response.raise_for_status()
        body = response.json()
        rows.extend(body.get("announcements") or [])
        if page * 30 >= int(body.get("totalAnnouncement") or 0):
            return rows
        page += 1


def run(start_date: str, end_date: str, out_dir: str, max_notices: int = 0) -> dict:
    if max_notices < 0:
        raise ValueError("max_notices must be nonnegative")
    output = Path(out_dir)
    pdf_dir = output / "pdf"
    record_dir = output / "records"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    record_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 quant-platform-dividend-source-audit/1",
        "Referer": "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search",
        "Origin": "http://www.cninfo.com.cn",
    })
    announcements = [row for row in _query(session, start_date, end_date) if KEYWORD in _title(row.get("announcementTitle", ""))]
    announcements.sort(key=lambda row: (int(row["announcementTime"]), row["announcementId"]))
    if max_notices:
        announcements = announcements[:max_notices]
    records = []
    current_id = None
    try:
        for row in announcements:
            current_id = str(row["announcementId"])
            cached = record_dir / f"{current_id}.json"
            if cached.exists():
                records.append(json.loads(cached.read_text(encoding="utf-8")))
                continue
            url = PDF_ROOT + row["adjunctUrl"]
            response = session.get(url, timeout=60)
            response.raise_for_status()
            data = response.content
            local_file = f"pdf/{current_id}.pdf"
            (output / local_file).write_bytes(data)
            record = {
                "announcement_id": current_id,
                "security_code": str(row["secCode"]).zfill(6),
                "security_name": row["secName"],
                "title": _title(row["announcementTitle"]),
                "announcement_time_ms": int(row["announcementTime"]),
                "publish_date": datetime.fromtimestamp(int(row["announcementTime"]) / 1000, tz=timezone.utc).astimezone(ZoneInfo("Asia/Shanghai")).date().isoformat(),
                "source_url": url,
                "source_path": row["adjunctUrl"],
                "source_size_reported_kb": row.get("adjunctSize"),
                "local_file": local_file,
                "size": len(data),
                "sha256": _sha256(data),
            }
            cached.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            records.append(record)
    except Exception as exc:
        (output / "failure.json").write_text(json.dumps({
            "failed_announcement_id": current_id,
            "captured_count": len(records),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise
    with (output / "notices.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    manifest = {
        "source": "CNINFO official disclosure platform",
        "query_url": QUERY_URL,
        "pdf_root": PDF_ROOT,
        "keyword": KEYWORD,
        "capture_time_utc": datetime.now(timezone.utc).isoformat(),
        "requested_interval": [start_date, end_date],
        "query_match_count": len(announcements),
        "captured_count": len(records),
        "earliest_publish_date": records[0]["publish_date"] if records else None,
        "latest_publish_date": records[-1]["publish_date"] if records else None,
        "records_sha256": _sha256((output / "notices.jsonl").read_bytes()),
        "availability_rule": "publication date only; conservatively available after that date close",
        "trade_authorized": False,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "failure.json").unlink(missing_ok=True)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--max-notices", type=int, default=0)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.start_date, args.end_date, args.out_dir, args.max_notices), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
