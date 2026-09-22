import csv
import hashlib
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from http.client import HTTPMessage
from io import BytesIO
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request

import pytest

from experiments import capture_a_share_market_regime as capture
from experiments.a_share_market_regime import CHINA_TZ, INDEX_CODES
from experiments.run_a_share_market_regime import main as diagnose

HOLIDAYS = {
    2025: [("元旦", (1, 1), (1, 1)), ("春节", (1, 28), (2, 4)),
           ("清明节", (4, 4), (4, 6)), ("劳动节", (5, 1), (5, 5)),
           ("端午节", (5, 31), (6, 2)), ("国庆节、中秋节", (10, 1), (10, 8))],
    2026: [("元旦", (1, 1), (1, 3)), ("春节", (2, 15), (2, 23)),
           ("清明节", (4, 4), (4, 6)), ("劳动节", (5, 1), (5, 5)),
           ("端午节", (6, 19), (6, 21)), ("中秋节", (9, 25), (9, 27)),
           ("国庆节", (10, 1), (10, 7))],
}


def calendar_html(year):
    def text(day):
        return f"{day.month}月{day.day}日（星期{'一二三四五六日'[day.weekday()]}）"

    rows = []
    for label, start, end in HOLIDAYS[year]:
        start, end = date(year, *start), date(year, *end)
        reopen = end + timedelta(days=1)
        while reopen.weekday() >= 5:
            reopen += timedelta(days=1)
        interval = text(start) + ("至" + text(end) if end != start else "")
        extra = "另外，2月14日（星期六）、2月28日（星期六）为周末休市。" if year == 2026 and label == "春节" else ""
        rows.append(f"<tr><td>{label}：</td><td>{interval}休市，{text(reopen)}起照常开市。{extra}</td></tr>")
    return f"<title>{year}年休市安排</title><table>{''.join(rows)}</table>".encode()


def source_index(code, days):
    return {"code": "200", "success": True, "data": [
        {"tradeDate": day.strftime("%Y%m%d"), "indexCode": code, "close": 1000 + i}
        for i, day in enumerate(days)
    ]}


@pytest.fixture
def fake_source(monkeypatch):
    now = datetime(2026, 1, 6, 16, tzinfo=CHINA_TZ)
    calls = []
    calendar = {day: flag for year in HOLIDAYS
                for day, flag in capture.parse_calendar(calendar_html(year), year).items()}

    def fetch(url):
        calls.append(url)
        if url in capture.CALENDAR_URLS.values():
            year = next(year for year, value in capture.CALENDAR_URLS.items() if value == url)
            return calendar_html(year)
        query = parse_qs(urlsplit(url).query)
        start = date.fromisoformat(query["startDate"][0])
        end = date.fromisoformat(query["endDate"][0])
        days = sorted(day for day, flag in calendar.items() if flag and start <= day <= end)
        return json.dumps(source_index(query["indexCode"][0], days)).encode()

    monkeypatch.setattr(capture, "_now", lambda: now)
    monkeypatch.setattr(capture, "_fetch", fetch)
    monkeypatch.setattr(capture, "sleep", lambda _: None)
    return now, calls


def test_capture_small_sample_smoke_and_hashes(tmp_path, fake_source):
    now, calls = fake_source
    output = tmp_path / "snapshot"
    receipt = capture.capture_snapshot(start=date(2026, 1, 5), output=output)
    assert receipt["status"] == "captured"
    assert receipt["sessions_per_index"] == 2
    assert receipt["price_source"] == "csi"
    assert receipt["history_sufficient"] is False
    assert receipt["historical_provider_availability"] == "unverified"
    assert receipt["strict_regime_evaluation"] == "not_run"
    assert receipt["trade_authorized"] is False
    assert len(calls) == 4
    assert all("endDate=20260106" in url for url in calls[1:])
    for source in receipt["requests"]:
        assert source["provider_available_at"] is None
        raw = (output / source["file"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == source["sha256"]
        assert source["acquired_at"] == now.isoformat()
    for name, digest in receipt["normalized_sha256"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
    with (output / "prices.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 6
    assert {row["ts_code"] for row in rows} == set(INDEX_CODES)
    assert all(row["available_at"] == now.isoformat() for row in rows)
    assert all(row["available_at_basis"] == "local_acquisition_only" for row in rows)


def test_full_history_is_still_not_historical_confirmation(tmp_path, fake_source, capsys):
    now, calls = fake_source
    output = tmp_path / "snapshot"
    receipt = capture.capture_snapshot(start=date(2025, 3, 1), output=output)
    assert receipt["history_sufficient"] is True
    assert len(calls) == 5
    args = ["--prices", str(output / "prices.csv"), "--calendar", str(output / "calendar.csv"),
            "--as-of", now.isoformat()]
    assert diagnose(args) == 1
    first = capsys.readouterr()
    report = json.loads(first.out)
    assert report["result"]["phase"] == "unknown"
    assert report["result"]["candidate_phase"] == "bull"
    assert any("close_not_available" in reason for reason in report["result"]["reasons"])
    assert diagnose(args) == 1
    assert capsys.readouterr().out == first.out


def test_capture_failed_source_keeps_failed_receipt_no_success_csv(tmp_path, fake_source, monkeypatch):
    fetch = capture._fetch

    def broken(url):
        return b'{"code":"500","success":false}' if url.startswith(capture.INDEX_URL) else fetch(url)

    monkeypatch.setattr(capture, "_fetch", broken)
    output = tmp_path / "snapshot"
    with pytest.raises(ValueError, match="did not report success"):
        capture.capture_snapshot(start=date(2026, 1, 5), output=output)
    receipt = json.loads((output / "receipt.json").read_text())
    assert receipt["status"] == "failed"
    assert len(receipt["requests"]) == 2
    assert not (output / "prices.csv").exists()
    assert not (output / "calendar.csv").exists()


def test_transport_failure_records_failure(tmp_path, fake_source, monkeypatch):
    def unavailable(url):
        raise OSError("synthetic transport failure")

    monkeypatch.setattr(capture, "_fetch", unavailable)
    output = tmp_path / "snapshot"
    with pytest.raises(OSError):
        capture.capture_snapshot(start=date(2026, 1, 5), output=output)
    assert json.loads((output / "receipt.json").read_text())["status"] == "failed"


def test_capture_refuses_existing_directory_before_network(tmp_path, fake_source):
    _, calls = fake_source
    output = tmp_path / "snapshot"
    output.mkdir()
    sentinel = output / "keep.txt"
    sentinel.write_text("keep")
    with pytest.raises(FileExistsError):
        capture.capture_snapshot(start=date(2026, 1, 5), output=output)
    assert sentinel.read_text() == "keep"
    assert calls == []


@pytest.mark.parametrize("start", [date(2024, 1, 1), date(2026, 1, 7), date(2024, 12, 10)])
def test_capture_rejects_bad_range_before_network(tmp_path, fake_source, start):
    _, calls = fake_source
    with pytest.raises(ValueError):
        capture.capture_snapshot(start=start, output=tmp_path / "snapshot")
    assert calls == []
    assert not (tmp_path / "snapshot").exists()


def test_intraday_capture_does_not_request_current_close(tmp_path, fake_source, monkeypatch):
    now, calls = fake_source
    monkeypatch.setattr(capture, "_now", lambda: now.replace(hour=10))
    receipt = capture.capture_snapshot(start=date(2026, 1, 5), output=tmp_path / "snapshot")
    assert receipt["decision_date"] == "2026-01-05"
    assert all("endDate=20260105" in url for url in calls[1:])


@pytest.mark.parametrize("start", [date(2026, 1, 1), date(2026, 1, 3)])
def test_closed_start_queries_first_real_session_keeps_full_calendar(tmp_path, fake_source, start):
    _, calls = fake_source
    output = tmp_path / "snapshot"
    receipt = capture.capture_snapshot(start=start, output=output)
    assert receipt["sessions_per_index"] == 2
    assert all("startDate=20260105&endDate=20260106" in url for url in calls[1:])
    with (output / "calendar.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0] == {"cal_date": start.isoformat(), "is_open": "0"}
    assert rows[-1] == {"cal_date": "2026-01-06", "is_open": "1"}


def test_capture_rejects_clock_reversal(tmp_path, fake_source, monkeypatch):
    now, _ = fake_source
    values = iter([now, now - timedelta(seconds=1)])
    monkeypatch.setattr(capture, "_now", lambda: next(values))
    output = tmp_path / "snapshot"
    with pytest.raises(ValueError, match="clock moved"):
        capture.capture_snapshot(start=date(2026, 1, 5), output=output)
    assert json.loads((output / "receipt.json").read_text())["status"] == "failed"


def test_calendar_holidays_weekends_and_year_boundary():
    a = capture.parse_calendar(calendar_html(2025), 2025)
    b = capture.parse_calendar(calendar_html(2026), 2026)
    assert len(a) == len(b) == 365
    assert a[date(2025, 1, 27)] and not a[date(2025, 1, 28)]
    assert not a[date(2025, 2, 4)] and a[date(2025, 2, 5)]
    assert a[date(2025, 12, 31)] and not b[date(2026, 1, 1)]
    assert not b[date(2026, 2, 23)] and b[date(2026, 2, 24)]
    assert not b[date(2026, 9, 20)]  # Government makeup Sunday is not a trading day.
    assert not b[date(2026, 9, 25)] and b[date(2026, 9, 28)]


@pytest.mark.parametrize(("old", "new"), [
    ("2026年休市安排", "2027年休市安排"),
    ("元旦：", "未知："),
    ("1月1日（星期四）", "1月1日（星期三）"),
    ("起照常开市", "正常营业"),
    ("1月5日（星期一）起", "1月6日（星期二）起"),
    ("2月14日（星期六）、2月28日（星期六）", "2月13日（星期五）"),
])
def test_calendar_bad_source_fails_closed(old, new):
    content = calendar_html(2026).decode().replace(old, new)
    with pytest.raises(ValueError):
        capture.parse_calendar(content.encode(), 2026)


def test_index_decimal_precision_and_order():
    days = (date(2026, 1, 5), date(2026, 1, 6))
    raw = b'{"code":"200","success":true,"data":[{"tradeDate":"20260106","indexCode":"000300","close":4507.3900000001},{"tradeDate":"20260105","indexCode":"000300","close":4460.16}]}'
    prices = capture.parse_index(raw, INDEX_CODES[0], days)
    assert prices[days[1]] == Decimal("4507.3900000001")
    assert capture.parse_index(raw, INDEX_CODES[0], tuple(reversed(days))) == prices


@pytest.mark.parametrize("problem", ["identity", "duplicate", "missing", "extra", "zero", "nan", "bool", "string", "success_int"])
def test_index_invalid_scope_or_price_rejected(problem):
    days = (date(2026, 1, 5), date(2026, 1, 6))
    data = source_index("000300", days)
    row = data["data"][0]
    if problem == "identity":
        row["indexCode"] = "000905"
    elif problem == "duplicate":
        data["data"].append(dict(row))
    elif problem == "missing":
        data["data"].pop()
    elif problem == "extra":
        data["data"].append({**row, "tradeDate": "20260107"})
    elif problem == "success_int":
        data["success"] = 1
    else:
        row["close"] = {"zero": 0, "nan": float("nan"), "bool": True, "string": "4507.39"}[problem]
    with pytest.raises(ValueError):
        capture.parse_index(json.dumps(data).encode(), INDEX_CODES[0], days)


@pytest.mark.parametrize("content", [b'{"code":"200","code":"200"}', b'not json', b'[]'])
def test_index_malformed_json_rejected(content):
    with pytest.raises(ValueError):
        capture.parse_index(content, INDEX_CODES[0], (date(2026, 1, 5),))


@pytest.mark.parametrize("url", ["file:///etc/passwd", "http://www.csindex.com.cn/", "https://evil.example/", capture.INDEX_URL + "?indexCode=000300&token=secret"])
def test_transport_rejects_unpinned_url_before_open(url, monkeypatch):
    def unexpected(*args):
        pytest.fail("must not open network")

    monkeypatch.setattr(capture, "build_opener", unexpected)
    with pytest.raises(ValueError, match="unsupported public source URL"):
        capture._fetch(url)


@pytest.mark.parametrize("url", [capture.CALENDAR_URLS[2026],
    capture.SSE_DAY_URL + "/000300?begin=-2&end=-1&period=day",
    capture.SSE_DAY_URL + "/000852?begin=-401&end=-1&period=day"])
@pytest.mark.parametrize("case", ["ok", "empty", "oversized", "http_error"])
def test_transport_response_bounds_and_no_credentials(case, url, monkeypatch):
    body = {"ok": b"{}", "empty": b"", "oversized": b"x" * (capture.MAX_BYTES + 1), "http_error": b"{}"}[case]

    class Response:
        status = 503 if case == "http_error" else 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit):
            assert limit == capture.MAX_BYTES + 1
            return body

    class Opener:
        def open(self, request, timeout):
            assert timeout == 20
            assert request.full_url == url
            assert request.data is None
            assert {key.lower() for key, _ in request.header_items()} == {"user-agent", "accept-encoding"}
            return Response()

    monkeypatch.setattr(capture, "build_opener", lambda handler: Opener())
    if case == "ok":
        assert capture._fetch(url) == b"{}"
    else:
        with pytest.raises(ValueError):
            capture._fetch(url)


def test_transport_rejects_redirect():
    request = Request("https://www.sse.com.cn/")
    assert capture._NoRedirect().redirect_request(request, BytesIO(), 302, "", HTTPMessage(), "https://evil.example") is None


def test_cli_invalid_range_has_no_success_json(tmp_path, fake_source, capsys):
    with pytest.raises(SystemExit) as error:
        capture.main(["--start", "2027-01-01", "--output", str(tmp_path / "unused")])
    assert error.value.code == 2
    output = capsys.readouterr()
    assert output.out == "" and "start must be" in output.err


def source_sse_index(code, days):
    rows = [[int(day.strftime("%Y%m%d")), 1000 + i, 1001 + i, 999 + i, 1000 + i, 100, 100000]
            for i, day in enumerate(days)]
    return {"code": code, "total": 100 + len(rows), "begin": 100, "end": 100 + len(rows), "kline": rows}


@pytest.fixture
def fake_sse_source(fake_source, monkeypatch):
    now, calls = fake_source
    calendar_fetch = capture._fetch
    calendar = {day: flag for year in HOLIDAYS
                for day, flag in capture.parse_calendar(calendar_html(year), year).items()}
    days = sorted(day for day, flag in calendar.items() if flag and day <= now.date())

    def fetch(url):
        if url in capture.CALENDAR_URLS.values():
            return calendar_fetch(url)
        calls.append(url)
        assert url.startswith(capture.SSE_DAY_URL + "/")  # No CSI fallback.
        parts = urlsplit(url)
        query = parse_qs(parts.query)
        assert query["end"] == ["-1"] and query["period"] == ["day"]
        count = -int(query["begin"][0]) - 1
        return json.dumps(source_sse_index(parts.path.rsplit("/", 1)[-1], days[-count:])).encode()

    monkeypatch.setattr(capture, "_fetch", fetch)
    return now, calls


def test_sse_cli_capture_smoke_and_diagnostic_replay(tmp_path, fake_sse_source, capsys):
    now, calls = fake_sse_source
    output = tmp_path / "sse"
    assert capture.main(["--start", "2026-01-03", "--source", "sse", "--output", str(output)]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["status"] == "captured" and receipt["price_source"] == "sse"
    assert receipt["sessions_per_index"] == 2 and receipt["history_sufficient"] is False
    assert receipt["decision_date"] == "2026-01-06"
    assert receipt["historical_provider_availability"] == "unverified"
    assert receipt["trade_authorized"] is False and len(calls) == 4
    assert all("begin=-3&end=-1&period=day" in url for url in calls[1:])
    for source in receipt["requests"]:
        assert hashlib.sha256((output / source["file"]).read_bytes()).hexdigest() == source["sha256"]
        assert source["provider_available_at"] is None
    for name, digest in receipt["normalized_sha256"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
    with (output / "prices.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 6 and {row["ts_code"] for row in rows} == set(INDEX_CODES)
    assert all(row["available_at"] == now.isoformat() for row in rows)
    assert all(row["available_at_basis"] == "local_acquisition_only" for row in rows)
    args = ["--prices", str(output / "prices.csv"), "--calendar", str(output / "calendar.csv"),
            "--basis", "snapshot", "--as-of", now.isoformat()]
    assert diagnose(args) == 1
    first = capsys.readouterr().out
    assert json.loads(first)["result"]["phase"] == "unknown"
    assert diagnose(args) == 1 and capsys.readouterr().out == first


def test_sse_full_history_snapshot_not_historical(tmp_path, fake_sse_source, capsys):
    now, calls = fake_sse_source
    output = tmp_path / "sse"
    receipt = capture.capture_snapshot(start=date(2025, 3, 1), output=output, source="sse")
    assert receipt["history_sufficient"] and len(calls) == 5
    args = ["--prices", str(output / "prices.csv"), "--calendar", str(output / "calendar.csv"),
            "--as-of", now.isoformat()]
    assert diagnose(args + ["--basis", "snapshot"]) == 0
    first = capsys.readouterr().out
    report = json.loads(first)
    assert report["result"]["phase"] == "bull"
    assert report["historical_confirmation_claimed"] is False
    assert diagnose(args + ["--basis", "snapshot"]) == 0
    assert capsys.readouterr().out == first
    assert diagnose(args) == 1
    assert json.loads(capsys.readouterr().out)["result"]["phase"] == "unknown"


@pytest.mark.parametrize("issue", ["missing", "intraday"])
def test_sse_failed_capture_never_trims_or_falls_back(tmp_path, fake_sse_source, monkeypatch, issue):
    now, calls = fake_sse_source
    fetch = capture._fetch
    if issue == "intraday":
        monkeypatch.setattr(capture, "_now", lambda: now.replace(hour=10))
    else:
        def missing(url):
            raw = fetch(url)
            if url.startswith(capture.SSE_DAY_URL):
                data = json.loads(raw)
                data["kline"].pop()
                data["end"] -= 1
                data["total"] -= 1
                return json.dumps(data).encode()
            return raw
        monkeypatch.setattr(capture, "_fetch", missing)
    output = tmp_path / "failed"
    with pytest.raises(ValueError, match="do not exactly cover"):
        capture.capture_snapshot(start=date(2026, 1, 5), output=output, source="sse")
    receipt = json.loads((output / "receipt.json").read_text())
    assert receipt["status"] == "failed" and receipt["price_source"] == "sse"
    assert len(calls) == 2 and not any(url.startswith(capture.INDEX_URL) for url in calls)
    assert not (output / "prices.csv").exists() and not (output / "calendar.csv").exists()


def test_sse_index_preserves_decimal_precision_and_order():
    raw = b'{"code":"000300","total":2,"begin":0,"end":2,"kline":[[20260106,4500,4600,4400,4544.5875000001,10,20],[20260105,4400,4600,4300,4539.5650,10,20]]}'
    days = (date(2026, 1, 5), date(2026, 1, 6))
    result = capture.parse_sse_index(raw, INDEX_CODES[0], days)
    assert result[days[1]] == Decimal("4544.5875000001")
    assert capture.parse_sse_index(raw, INDEX_CODES[0], tuple(reversed(days))) == result


@pytest.mark.parametrize("problem", ["identity", "cursor_type", "cursor_range", "cursor_length", "rows",
    "row_shape", "day_type", "day_invalid", "duplicate", "missing", "extra", "zero", "nan", "bool",
    "string", "ohlc", "negative_volume", "negative_amount"])
def test_sse_index_rejects_bad_source(problem):
    days = (date(2026, 1, 5), date(2026, 1, 6))
    data = source_sse_index("000300", days)
    row = data["kline"][0]
    if problem == "identity":
        data["code"] = "000905"
    elif problem == "cursor_type":
        data["begin"] = True
    elif problem == "cursor_range":
        data["end"] += 1
    elif problem == "cursor_length":
        data["begin"] -= 1
    elif problem == "rows":
        data["kline"] = {}
    elif problem == "row_shape":
        row.pop()
    elif problem == "day_type":
        row[0] = "20260105"
    elif problem == "day_invalid":
        row[0] = 20260230
    elif problem in ("duplicate", "missing", "extra"):
        if problem == "duplicate":
            data["kline"].append(list(row))
        elif problem == "missing":
            data["kline"].pop()
        else:
            data["kline"].append([20260107, *row[1:]])
        data["total"] = data["end"] = data["begin"] + len(data["kline"])
    elif problem == "ohlc":
        row[2] = row[3] - 1
    elif problem in ("negative_volume", "negative_amount"):
        row[5 if problem == "negative_volume" else 6] = -1
    else:
        row[4] = {"zero": 0, "nan": float("nan"), "bool": True, "string": "1000"}[problem]
    with pytest.raises(ValueError):
        capture.parse_sse_index(json.dumps(data).encode(), INDEX_CODES[0], days)


@pytest.mark.parametrize("raw", [b'not json', b'[]', b'{"code":"000300","code":"000300"}'])
def test_sse_index_rejects_malformed_json(raw):
    with pytest.raises(ValueError):
        capture.parse_sse_index(raw, INDEX_CODES[0], (date(2026, 1, 5),))


@pytest.mark.parametrize("source", ["auto", "SSE", None, True])
def test_invalid_source_rejected_before_files_or_network(tmp_path, fake_source, source):
    _, calls = fake_source
    output = tmp_path / "unused"
    with pytest.raises(ValueError, match="source must"):
        capture.capture_snapshot(start=date(2026, 1, 5), output=output, source=source)
    assert calls == [] and not output.exists()


@pytest.mark.parametrize("suffix", ["/000300?begin=-1&end=-1&period=day", "/000300?begin=-402&end=-1&period=day",
    "/000300?begin=-1000&end=-1&period=day", "/000300?begin=3&end=-1&period=day",
    "/600000?begin=-3&end=-1&period=day", "/000300?begin=-3&end=0&period=day",
    "/000300?begin=-3&end=-1&period=minute", "/000300?begin=-3&end=-1&period=day&token=secret"])
def test_sse_url_rejects_unbounded_or_foreign_scope(suffix, monkeypatch):
    monkeypatch.setattr(capture, "build_opener", lambda *_: pytest.fail("network must not open"))
    with pytest.raises(ValueError, match="unsupported public source URL"):
        capture._fetch(capture.SSE_DAY_URL + suffix)


def test_cli_source_choice_is_explicit(tmp_path, fake_source, capsys):
    _, calls = fake_source
    with pytest.raises(SystemExit) as error:
        capture.main(["--start", "2026-01-05", "--source", "auto", "--output", str(tmp_path / "unused")])
    assert error.value.code == 2 and calls == []
    assert "invalid choice" in capsys.readouterr().err
