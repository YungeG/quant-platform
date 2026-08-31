"""Extract dividend lifecycle fields from captured CNINFO implementation PDFs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

FIELDS = (
    "announcement_id",
    "security_code",
    "security_name",
    "publish_date",
    "record_date",
    "ex_date",
    "payment_date",
    "cash_per_share",
    "title",
    "source_file",
    "source_sha256",
    "status",
)
DATE = r"(?:(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日|((?:19|20)\d{2})[/.\-](\d{1,2})[/.\-](\d{1,2}))"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _date(match: re.Match[str]) -> str:
    groups = match.groups()
    year, month, day = groups[:3] if groups[0] else groups[3:6]
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _first_date(pattern: str, text: str) -> str | None:
    match = re.search(pattern + DATE, text, flags=re.S)
    return _date(match) if match else None


def parse_text(text: str) -> dict:
    normalized = text.replace("（", "(").replace("）", ")")
    compact = re.sub(r"[ \t]+", " ", normalized)
    dense = re.sub(r"\s+", "", normalized)
    payment = None
    sentence = re.search(r"股权登记日为?[:：]?" + DATE + r".*?(?:除权除息日|除息日)为?[:：]?" + DATE, dense)
    if sentence:
        groups = sentence.groups()
        record = _date_from_groups(groups[:6])
        ex_date = _date_from_groups(groups[6:12])
    else:
        table = re.search(r"(?:Ａ股|A\s*股)\s*" + DATE + r"\s*(?:－|-)?\s*" + DATE + r"\s*" + DATE, compact)
        if table is None:
            table = re.search(r"股权登记日.*?除权\(息\)日.*?现金红利发放日\s*" + DATE + r"\s*" + DATE + r"\s*" + DATE, compact, flags=re.S)
        if table:
            groups = table.groups()
            record = _date_from_groups(groups[:6])
            ex_date = _date_from_groups(groups[6:12])
            payment = _date_from_groups(groups[12:18])
        else:
            record = _first_date(r"股权登记日为?[:：]?", dense)
            ex_date = _first_date(r"(?:除权除息日|除息日|除权\(息\)日)为?[:：]?", dense)
    payment_date = payment or _first_date(r"(?:现金红利|现金分红|红利)(?:发放日|将于)[:：]?", dense)
    cash = None
    for pattern, divisor in (
        (r"A股每股现金红利(?:人民币)?([0-9]+(?:\.[0-9]+)?)元", 1),
        (r"每股(?:派发)?现金红利(?:人民币)?([0-9]+(?:\.[0-9]+)?)元", 1),
        (r"每10股派(?:发)?(?:现金红利)?(?:人民币)?([0-9]+(?:\.[0-9]+)?)元", 10),
        (r"每10股派现金([0-9]+(?:\.[0-9]+)?)元", 10),
    ):
        match = re.search(pattern, dense, flags=re.I)
        if match:
            cash = float(match.group(1)) / divisor
            break
    return {
        "record_date": record,
        "ex_date": ex_date,
        "payment_date": payment_date,
        "cash_per_share": cash,
        "status": "COMPLETE" if all((record, ex_date, payment_date, cash is not None)) else "INCOMPLETE",
    }


def _date_from_groups(groups: tuple[str | None, ...]) -> str:
    year, month, day = groups[:3] if groups[0] else groups[3:6]
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def run(capture_dir: str, out_csv: str, out_manifest: str) -> dict:
    capture = Path(capture_dir)
    rows = []
    for line in (capture / "notices.jsonl").read_text(encoding="utf-8").splitlines():
        notice = json.loads(line)
        path = capture / notice["local_file"]
        result = subprocess.run(["pdftotext", "-layout", str(path), "-"], check=True, capture_output=True, text=True)
        parsed = parse_text(result.stdout)
        rows.append({
            "announcement_id": notice["announcement_id"],
            "security_code": notice["security_code"],
            "security_name": notice["security_name"],
            "publish_date": notice["publish_date"],
            **parsed,
            "title": notice["title"],
            "source_file": notice["local_file"],
            "source_sha256": _sha256(path),
        })
    output = Path(out_csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    incomplete = [row["announcement_id"] for row in rows if row["status"] != "COMPLETE"]
    in_scope = [row for row in rows if row["security_code"].startswith(("0", "3", "6"))]
    in_scope_incomplete = [row["announcement_id"] for row in in_scope if row["status"] != "COMPLETE"]
    manifest = {
        "source_capture": str(capture),
        "row_count": len(rows),
        "complete_count": len(rows) - len(incomplete),
        "incomplete_announcement_ids": incomplete,
        "sh_sz_ordinary_count": len(in_scope),
        "sh_sz_ordinary_complete_count": len(in_scope) - len(in_scope_incomplete),
        "sh_sz_ordinary_incomplete_announcement_ids": in_scope_incomplete,
        "sh_sz_ordinary_parse_complete": bool(in_scope) and not in_scope_incomplete,
        "output_sha256": _sha256(output),
        "lifecycle_parse_complete": bool(rows) and not incomplete,
        "backtest_ready": False,
        "trade_authorized": False,
    }
    Path(out_manifest).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture-dir", required=True)
    parser.add_argument("--out-csv", required=True)
    parser.add_argument("--out-manifest", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.capture_dir, args.out_csv, args.out_manifest), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
