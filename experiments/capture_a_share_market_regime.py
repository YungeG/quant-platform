"""Bounded public CSI/SSE snapshot capture for diagnostics, never Backtest evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal, DecimalException
from html.parser import HTMLParser
from pathlib import Path
from time import sleep
from urllib.request import HTTPRedirectHandler, Request, build_opener

from experiments.a_share_market_regime import CHINA_TZ, DEFAULT_CONFIG, INDEX_CODES

CALENDAR_URLS = {
    2025: "https://www.sse.com.cn/disclosure/dealinstruc/closed/c/c_20241223_10767110.shtml",
    2026: "https://www.sse.com.cn/disclosure/dealinstruc/closed/c/c_20251222_10802510.shtml",
}
INDEX_URL = "https://www.csindex.com.cn/csindex-home/perf/index-perf"
SSE_DAY_URL = "https://yunhq.sse.com.cn:32042/v1/sh1/dayk"
MAX_BYTES = 2_000_000
MAX_DAYS = 400
_DATE = r"(\d{1,2})月(\d{1,2})日（星期([一二三四五六日])）"
_HOLIDAY = re.compile(_DATE + r"(?:至" + _DATE + r")?休市，" + _DATE + r"起照常开市。")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _now() -> datetime:
    return datetime.now(CHINA_TZ)


def _fetch(url: str) -> bytes:
    index_pattern = re.escape(INDEX_URL) + r"\?indexCode=(000300|000905|000852)&startDate=[0-9]{8}&endDate=[0-9]{8}"
    sse_match = re.fullmatch(
        re.escape(SSE_DAY_URL) + r"/(000300|000905|000852)\?begin=-([1-9][0-9]{0,2})&end=-1&period=day", url,
    )
    try:
        allowed_sse = sse_match is not None and 2 <= int(sse_match[2]) <= MAX_DAYS + 1
    except ValueError as error:
        raise ValueError("unsupported public source URL") from error
    if url not in CALENDAR_URLS.values() and re.fullmatch(index_pattern, url) is None and not allowed_sse:
        raise ValueError("unsupported public source URL")
    request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "identity"})  # noqa: S310 -- exact pinned HTTPS URLs checked above
    # No credentials, automatic redirects, retry loop, or source fallback.
    with build_opener(_NoRedirect()).open(request, timeout=20) as response:  # noqa: S310 -- exact pinned HTTPS URLs checked above
        if response.status != 200:
            raise ValueError("source HTTP status must be 200")
        content = response.read(MAX_BYTES + 1)
    if not content or len(content) > MAX_BYTES:
        raise ValueError("source response is empty or exceeds byte limit")
    return content


class _Cells(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows: list[list[str]] = []
        self.row: list[str] = []
        self.cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag == "td":
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag == "td" and self.cell is not None:
            self.row.append("".join(self.cell).strip())
            self.cell = None
        elif tag == "tr":
            self.rows.append(self.row)
            self.row = []


def _stated_date(year: int, month: str, day: str, weekday: str) -> date:
    try:
        result = date(year, int(month), int(day))
    except (TypeError, ValueError) as error:
        raise ValueError("invalid calendar date") from error
    if result.weekday() != "一二三四五六日".index(weekday):
        raise ValueError("calendar date/weekday mismatch")
    return result


def parse_calendar(content: bytes, year: int) -> dict[date, bool]:
    """Parse the pinned annual holiday tables; unknown wording fails closed.

    This is an annual schedule, not proof that no exceptional closure occurred.
    Exact index/session coverage is checked separately during capture.
    """
    if year not in CALENDAR_URLS:
        raise ValueError("unsupported calendar year")
    text = content.decode("utf-8-sig")
    if f"{year}年休市安排" not in text:
        raise ValueError("calendar year/title mismatch")
    parser = _Cells()
    parser.feed(text)
    labels = {"元旦", "春节", "清明节", "劳动节", "端午节"}
    labels |= {"国庆节、中秋节"} if year == 2025 else {"中秋节", "国庆节"}
    seen: set[str] = set()
    closed: set[date] = set()
    for row in parser.rows:
        if not row or row[0].rstrip("：:") not in labels:
            continue
        label = row[0].rstrip("：:")
        if label in seen or len(row) != 2:
            raise ValueError("duplicate or malformed holiday row")
        seen.add(label)
        value = row[1].replace(" ", "").replace("\n", "").replace("\r", "")
        match = _HOLIDAY.match(value)
        if match is None:
            raise ValueError("unrecognized holiday wording")
        fields = match.groups()
        start = _stated_date(year, *fields[:3])
        end = _stated_date(year, *fields[3:6]) if fields[3] else start
        reopen = _stated_date(year, *fields[6:9])
        if end < start or (end - start).days > 15 or reopen <= end:
            raise ValueError("invalid holiday interval")
        expected_reopen = end + timedelta(days=1)
        while expected_reopen.weekday() >= 5:
            expected_reopen += timedelta(days=1)
        if reopen != expected_reopen:
            raise ValueError("unexplained gap before reopening")
        for n in range((end - start).days + 1):
            day = start + timedelta(days=n)
            if day in closed:
                raise ValueError("overlapping holiday intervals")
            closed.add(day)
        remainder = value[match.end():]
        if remainder:
            if not re.fullmatch(r"另外，" + _DATE + r"(?:、" + _DATE + r")*为周末休市。", remainder):
                raise ValueError("unrecognized additional closure wording")
            for month, day, weekday in re.findall(_DATE, remainder):
                if _stated_date(year, month, day, weekday).weekday() < 5:
                    raise ValueError("additional closure is not a weekend")
    if seen != labels:
        raise ValueError("annual holiday table is incomplete")
    start, end = date(year, 1, 1), date(year + 1, 1, 1)
    days = (start + timedelta(days=n) for n in range((end - start).days))
    return {day: day.weekday() < 5 and day not in closed for day in days}


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def parse_index(content: bytes, instrument: str, sessions: tuple[date, ...]) -> dict[date, Decimal]:
    if instrument not in INDEX_CODES or not sessions or len(set(sessions)) != len(sessions):
        raise ValueError("invalid index/session scope")
    try:
        payload = json.loads(content, parse_float=Decimal, object_pairs_hook=_unique_keys)
    except (UnicodeError, ValueError, DecimalException) as error:
        raise ValueError("invalid index JSON (including duplicate keys)") from error
    if type(payload) is not dict or payload.get("code") != "200" or type(payload.get("success")) is not bool or not payload["success"]:
        raise ValueError("index source did not report success")
    rows = payload.get("data")
    if type(rows) is not list:
        raise ValueError("index data must be a list")
    prices = {}
    for row in rows:
        if type(row) is not dict or row.get("indexCode") != instrument[:6]:
            raise ValueError("index identity mismatch")
        day_text = row.get("tradeDate")
        if type(day_text) is not str or re.fullmatch(r"[0-9]{8}", day_text) is None:
            raise ValueError("invalid index tradeDate")
        day = date.fromisoformat(day_text)
        close = row.get("close")
        if not isinstance(close, (int, Decimal)) or isinstance(close, bool):
            raise ValueError("index close must be finite and positive")
        if not Decimal(close).is_finite() or Decimal(close) <= 0:
            raise ValueError("index close must be finite and positive")
        if day in prices:
            raise ValueError("duplicate index trading date")
        prices[day] = Decimal(close)
    return _require_sessions(prices, sessions)


def parse_sse_index(content: bytes, instrument: str, sessions: tuple[date, ...]) -> dict[date, Decimal]:
    """Read SSE daily K-lines, not intraday quotes; retain the source's precision."""
    if instrument not in INDEX_CODES or not sessions or any(type(day) is not date for day in sessions) or len(set(sessions)) != len(sessions):
        raise ValueError("invalid index/session scope")
    try:
        payload = json.loads(content, parse_float=Decimal, object_pairs_hook=_unique_keys)
    except (UnicodeError, ValueError, DecimalException) as error:
        raise ValueError("invalid SSE index JSON (including duplicate keys)") from error
    if type(payload) is not dict or payload.get("code") != instrument[:6]:
        raise ValueError("SSE index identity mismatch")
    rows = payload.get("kline")
    total, begin, end = (payload.get(key) for key in ("total", "begin", "end"))
    if type(rows) is not list or type(total) is not int or type(begin) is not int or type(end) is not int:
        raise ValueError("invalid SSE daily K-line page")
    if not 0 <= begin <= end == total or end - begin != len(rows):
        raise ValueError("inconsistent SSE daily K-line page")
    prices = {}
    for row in rows:
        if type(row) is not list or len(row) != 7:
            raise ValueError("SSE daily row must contain date, OHLC, volume and amount")
        if type(row[0]) is not int or re.fullmatch(r"[0-9]{8}", str(row[0])) is None:
            raise ValueError("invalid SSE daily date")
        day = date.fromisoformat(str(row[0]))
        if any(type(value) not in (int, Decimal) or not Decimal(value).is_finite() for value in row[1:]):
            raise ValueError("SSE daily values must be finite numbers")
        open_, high, low, close, volume, amount = map(Decimal, row[1:])
        if low <= 0 or not low <= open_ <= high or not low <= close <= high or volume < 0 or amount < 0:
            raise ValueError("invalid SSE daily OHLC or turnover")
        if day in prices:
            raise ValueError("duplicate index trading date")
        prices[day] = close
    return _require_sessions(prices, sessions)


def _require_sessions(prices: dict[date, Decimal], sessions: tuple[date, ...]) -> dict[date, Decimal]:
    if set(prices) != set(sessions):
        missing = sorted(set(sessions) - set(prices))
        extra = sorted(set(prices) - set(sessions))
        raise ValueError(
            "index dates do not exactly cover scheduled completed sessions; "
            f"missing={len(missing)} {missing[:3]}, unexpected={len(extra)} {extra[:3]}"
        )
    return prices


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, headers, rows) -> None:
    with path.open("x", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(rows)


def capture_snapshot(*, start: date, output: Path, source: str = "csi") -> dict:
    if type(source) is not str or source not in ("csi", "sse"):
        raise ValueError("source must be csi or sse; no automatic fallback")
    started = _now()
    through = started.date()
    if type(start) is not date or start > through or (through - start).days >= MAX_DAYS:
        raise ValueError("start must be within the last 400 calendar days")
    years = range(start.year, through.year + 1)
    if any(year not in CALENDAR_URLS for year in years):
        raise ValueError("requested calendar year is unsupported")
    output.mkdir(parents=True, exist_ok=False)  # Never overwrite any prior capture.
    receipt = {
        "strategy_input": "a_share_market_regime_v1", "price_source": source,
        "authority": "diagnostic_only", "trade_authorized": False,
        "status": "capturing", "started_at": started.isoformat(),
        "start": start.isoformat(), "through": through.isoformat(),
        "availability_basis": "local_acquisition_only",
        "historical_provider_availability": "unverified",
        "calendar_basis": "sse_annual_schedule",
        "exceptional_closure_completeness": "unverified",
        "requests": [],
    }
    receipt_path = output / "receipt.json"
    _write_json(receipt_path, receipt)

    def fetch(url: str, filename: str) -> tuple[bytes, datetime]:
        if receipt["requests"]:
            sleep(0.5)
        content = _fetch(url)
        acquired = _now()
        if acquired < started or acquired.date() != through:
            raise ValueError("clock moved backwards or capture crossed midnight; start a new capture")
        (output / filename).write_bytes(content)
        receipt["requests"].append({
            "url": url, "file": filename, "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(), "acquired_at": acquired.isoformat(),
            "provider_available_at": None,
        })
        _write_json(receipt_path, receipt)
        return content, acquired

    try:
        calendar = {}
        for year in years:
            content, _ = fetch(CALENDAR_URLS[year], f"calendar-{year}.html")
            calendar.update(parse_calendar(content, year))
        calendar = {day: is_open for day, is_open in calendar.items() if start <= day <= through}
        sessions = tuple(sorted(day for day, is_open in calendar.items()
                                if is_open and datetime.combine(day, time(15), CHINA_TZ) <= started))
        if not sessions:
            raise ValueError("no completed session in requested range")
        price_rows = []
        acquired = started
        for instrument in INDEX_CODES:
            if source == "csi":
                # CSI can insert a synthetic boundary on a closed start day.
                url = f"{INDEX_URL}?indexCode={instrument[:6]}&startDate={sessions[0]:%Y%m%d}&endDate={sessions[-1]:%Y%m%d}"
                parse = parse_index
            else:
                # SSE's negative cursor -1 is the exclusive end; request exactly n rows.
                # Any extra intraday bar or missing session is rejected, never trimmed.
                url = f"{SSE_DAY_URL}/{instrument[:6]}?begin=-{len(sessions) + 1}&end=-1&period=day"
                parse = parse_sse_index
            content, acquired = fetch(url, f"index-{instrument[:6]}.json")
            values = parse(content, instrument, sessions)
            price_rows.extend((instrument, day.isoformat(), str(values[day]), acquired.isoformat(),
                               "local_acquisition_only") for day in sessions)
        _write_csv(output / "calendar.csv", ("cal_date", "is_open"),
                   ((day.isoformat(), int(value)) for day, value in sorted(calendar.items())))
        _write_csv(output / "prices.csv", ("ts_code", "trade_date", "close", "available_at", "available_at_basis"), price_rows)
        completed = _now()
        if completed < acquired or completed.date() != through:
            raise ValueError("clock moved backwards or capture crossed midnight; start a new capture")
        receipt.update({
            "status": "captured", "completed_at": completed.isoformat(),
            "decision_date": sessions[-1].isoformat(), "sessions_per_index": len(sessions),
            "history_sufficient": len(sessions) >= DEFAULT_CONFIG.required_sessions,
            "strict_regime_evaluation": "not_run",
            "normalized_sha256": {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                                  for name in ("prices.csv", "calendar.csv")},
        })
    except (OSError, ValueError, UnicodeError) as error:
        receipt.update({"status": "failed", "error_type": type(error).__name__,
                        "strict_regime_evaluation": "not_run"})
        _write_json(receipt_path, receipt)
        raise
    _write_json(receipt_path, receipt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="无凭据、有限范围的中证/上交所公开快照获取（仅诊断，不回填历史发布时间）")
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--output", required=True, type=Path, help="必须不存在的新目录")
    parser.add_argument("--source", choices=("csi", "sse"), default="csi",
                        help="价格来源：csi 中证日线（默认）；sse 上交所日K，显式选择且不自动切换")
    args = parser.parse_args(argv)
    try:
        receipt = capture_snapshot(start=args.start, output=args.output, source=args.source)
    except (OSError, ValueError, UnicodeError) as error:
        parser.error(str(error))
    print(json.dumps({"output": str(args.output), **receipt}, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
