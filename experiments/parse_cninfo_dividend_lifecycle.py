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
    "override_applied",
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


def _page_broken_date(pattern: str, text: str) -> str | None:
    match = re.search(pattern + r".{0,100}?(\d{4})年.{0,100}?(\d{1,2})月(\d{1,2})日", text)
    if match is None:
        match = re.search(pattern + r".{0,100}?(\d{4}).{0,100}?年(\d{1,2})月(\d{1,2})日", text)
    if match is None:
        match = re.search(pattern + r".{0,100}?(\d{4}).{0,100}?(\d{1,2})月(\d{1,2})日", text)
    return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}" if match else None


def parse_text(text: str) -> dict:
    normalized = text.replace("（", "(").replace("）", ")")
    normalized = re.sub(r"(\d{4})年(\d{1,2})年(\d{1,2})年", r"\1年\2月\3日", normalized)
    normalized = re.sub(r"(?m)^[ \t\f]*(?:证券代码|债券代码)[:：][^\n]*$", "", normalized)
    normalized = re.sub(r"(?m)^[ \t\f]*第?\s*\d+\s*页[^\n]*$", "", normalized)
    normalized = re.sub(r"(?m)^[ \t\f]*\d+\s*/\s*\d+\s*$", "", normalized)
    normalized = re.sub(r"(?m)^[ \t\f]*-\s*\d+\s*-\s*$", "", normalized)
    normalized = re.sub(r"(?m)^[^\n]{0,100}权益分派实施公告\s*$", "", normalized)
    normalized = re.sub(r"(?m)^\s*\d+\s*$", "", normalized)
    compact = re.sub(r"[ \t]+", " ", normalized)
    dense = re.sub(r"\s+", "", normalized)
    payment = None
    combined = re.search(r"(?:股权|权益)登记日(?:期)?为?[:：]?" + DATE + r".*?除权除息及红利发放日为?[:：]?" + DATE, dense)
    sentence = re.search(r"(?:股权|权益)登记日(?:期)?为?[:：]?" + DATE + r".*?(?:除权除息日|除息日|除权\(除息\)日|除权日\(除息日\))(?:\(红利发放日\))?为?[:：]?" + DATE, dense)
    if combined:
        groups = combined.groups()
        record = _date_from_groups(groups[:6])
        ex_date = _date_from_groups(groups[6:12])
        payment = ex_date
    elif sentence:
        groups = sentence.groups()
        record = _date_from_groups(groups[:6])
        ex_date = _date_from_groups(groups[6:12])
    else:
        table = re.search(r"(?:Ａ股|A\s*股|普通股)\s*" + DATE + r"\s*(?:－|/|-|—)*\s*" + DATE + r"\s*" + DATE, compact)
        table_payment_group = 12
        if table is None:
            table = re.search(r"股权登记日.*?除权\(息\)日.*?现金红利发放日\s*" + DATE + r"\s*" + DATE + r"\s*" + DATE + r"\s*" + DATE, compact, flags=re.S)
            table_payment_group = 18
        if table is None:
            table = re.search(r"股权登记日.*?除权\(息\)日.*?现金红利发放日\s*" + DATE + r"\s*" + DATE + r"\s*" + DATE, compact, flags=re.S)
            table_payment_group = 12
        if table:
            groups = table.groups()
            record = _date_from_groups(groups[:6])
            ex_date = _date_from_groups(groups[6:12])
            payment = _date_from_groups(groups[table_payment_group:table_payment_group + 6])
        else:
            record = _first_date(r"(?:股权|权益)登记日(?:期)?为?[:：]?", dense)
            ex_date = _first_date(r"(?:除权除息日|除息日|除权\(息\)日|除权\(除息\)日|除权日\(除息日\))(?:\(红利发放日\))?为?[:：]?", dense)
    if record is None:
        record = _page_broken_date(r"(?:股权|权益)登记日(?:期)?(?:为[:：]?|[:：])", dense)
    if ex_date is None:
        ex_date = _page_broken_date(r"(?:除权除息日|除息日|除权\(息\)日|除权\(除息\)日|除权日\(除息日\))(?:\(红利发放日\))?(?:为[:：]?|[:：])", dense)
    payment_date = payment or _first_date(r"(?:现金红利|现金股利|现金分红|红利|股息)[,，]?(?:发放日|将(?:于)?|于)\)?[:：]?", dense) or _first_date(r"现金红(?:.{0,60}?)?利(?:.{0,100}?)?将(?:于)?", dense) or _page_broken_date(r"现金红(?:.{0,60}?)?利(?:.{0,100}?)?将(?:于)?", dense)
    cash = None
    for pattern, divisor in (
        (r"A股每股(?:现金红利|现金股利)(?:人民币)?([0-9]+(?:\.[0-9]+)?)元", 1),
        (r"每股(?:派发)?(?:现金红利|现金股利)(?:人民币)?([0-9]+(?:\.[0-9]+)?)元", 1),
        (r"每10股(?:派|分配)(?:发)?(?:现金红利|现金股利)?(?:人民币)?([0-9]+(?:\.[0-9]+)?)元", 10),
        (r"每10股派现金([0-9]+(?:\.[0-9]+)?)元", 10),
    ):
        match = re.search(pattern, dense, flags=re.I)
        if match:
            cash = float(match.group(1)) / divisor
            break
    no_cash = cash in (None, 0.0) and ("不派发现金" in dense or "不进行现金分红" in dense or "本次不分红" in dense or re.search(r"(?:现金红利|现金股利)(?:为|=)?0(?:\.0+)?元", dense) or "转增股本方案" in dense or "每股转增" in dense or "每10股转增" in dense)
    return {
        "record_date": record,
        "ex_date": ex_date,
        "payment_date": payment_date,
        "cash_per_share": cash,
        "status": "NO_CASH_DIVIDEND" if no_cash else "COMPLETE" if all((record, ex_date, payment_date, cash is not None)) else "INCOMPLETE",
    }


def _date_from_groups(groups: tuple[str | None, ...]) -> str:
    year, month, day = groups[:3] if groups[0] else groups[3:6]
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def run(capture_dir: str, out_csv: str, out_manifest: str, overrides_path: str | None = None) -> dict:
    capture = Path(capture_dir)
    overrides = {}
    if overrides_path and Path(overrides_path).exists():
        overrides = json.loads(Path(overrides_path).read_text(encoding="utf-8"))["overrides"]
    rows = []
    for line in (capture / "notices.jsonl").read_text(encoding="utf-8").splitlines():
        notice = json.loads(line)
        path = capture / notice["local_file"]
        layout = subprocess.run(["pdftotext", "-layout", str(path), "-"], check=True, capture_output=True, text=True)
        raw = subprocess.run(["pdftotext", "-raw", str(path), "-"], check=True, capture_output=True, text=True)
        candidates = (parse_text(layout.stdout), parse_text(raw.stdout))
        parsed = max(candidates, key=lambda item: sum(item[field] not in (None, "") for field in ("record_date", "ex_date", "payment_date", "cash_per_share")))
        if "更正公告" in notice["title"]:
            parsed["status"] = "CORRECTION_NOTICE"
        elif "补充公告" in notice["title"]:
            parsed["status"] = "SUPPLEMENT_NOTICE"
        override = overrides.get(notice["announcement_id"])
        if override:
            if override["source_sha256"] != _sha256(path):
                raise ValueError(f"override source hash mismatch: {notice['announcement_id']}")
            for field, value in override["fields"].items():
                if parsed[field] not in (None, "", value):
                    raise ValueError(f"override conflicts with parsed {field}: {notice['announcement_id']}")
                parsed[field] = value
            if parsed["status"] == "INCOMPLETE" and all(parsed[field] not in (None, "") for field in ("record_date", "ex_date", "payment_date", "cash_per_share")):
                parsed["status"] = "COMPLETE"
        rows.append({
            "announcement_id": notice["announcement_id"],
            "security_code": notice["security_code"],
            "security_name": notice["security_name"],
            "publish_date": notice["publish_date"],
            **parsed,
            "title": notice["title"],
            "source_file": notice["local_file"],
            "source_sha256": _sha256(path),
            "override_applied": str(bool(override)).lower(),
        })
    output = Path(out_csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    cash_rows = [row for row in rows if row["status"] not in {"NO_CASH_DIVIDEND", "CORRECTION_NOTICE", "SUPPLEMENT_NOTICE"}]
    incomplete = [row["announcement_id"] for row in cash_rows if row["status"] != "COMPLETE"]
    in_scope = [row for row in cash_rows if row["security_code"].startswith(("0", "3", "6"))]
    in_scope_incomplete = [row["announcement_id"] for row in in_scope if row["status"] != "COMPLETE"]
    manifest = {
        "source_capture": str(capture),
        "row_count": len(rows),
        "cash_dividend_count": len(cash_rows),
        "non_cash_or_correction_count": len(rows) - len(cash_rows),
        "complete_count": len(cash_rows) - len(incomplete),
        "incomplete_announcement_ids": incomplete,
        "sh_sz_ordinary_count": len(in_scope),
        "sh_sz_ordinary_complete_count": len(in_scope) - len(in_scope_incomplete),
        "sh_sz_ordinary_incomplete_announcement_ids": in_scope_incomplete,
        "sh_sz_ordinary_parse_complete": bool(in_scope) and not in_scope_incomplete,
        "override_count": sum(row["override_applied"] == "true" for row in rows),
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
    parser.add_argument("--overrides", default="overall/a-share-cninfo-dividend-extraction-overrides-v1.json")
    args = parser.parse_args(argv)
    print(json.dumps(run(args.capture_dir, args.out_csv, args.out_manifest, args.overrides), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
