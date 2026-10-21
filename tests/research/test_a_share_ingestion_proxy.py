"""Offline protocol/security tests. Fake keys/responses only; never real HTTP."""

from __future__ import annotations

import gzip
import io
import json
import os
import stat
import threading
from concurrent.futures import ThreadPoolExecutor
from http.client import BadStatusLine, HTTPMessage
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from experiments.a_share_ingestion import daily, proxy, runtime
from experiments.a_share_ingestion.__main__ import main

KEY = "Z" * 56  # Synthetic fixture, never a credential from the host.


def forbidden(*args, **kwargs):
    pytest.fail("real network, real credential or unexpected I/O")


def response(api="daily", items=None, *, code=0, fields=None, msg=""):
    columns = fields if fields is not None else proxy.API_FIELDS[api].split(",")
    if items is None:
        items = [["000001.SZ", "20240102", 10, 11, 9, 10.5, 12.5, 2.5, 1.2]]
    return json.dumps(
        {
            "code": code,
            "msg": msg,
            "data": {"fields": columns, "items": items, "count": 0, "has_more": False},
        }
    ).encode()


class Reply:
    def __init__(self, raw, *, status=200, encoding="identity"):
        self.raw = raw
        self.status = status
        self.headers = {"Content-Encoding": encoding}
        self.read_sizes = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        self.read_sizes.append(size)
        return self.raw[:size]


class Opener:
    def __init__(self, *actions):
        self.actions = list(actions)
        self.calls = []

    def open(self, request, *, timeout):
        self.calls.append((request, timeout))
        if not self.actions:
            pytest.fail("unexpected physical request")
        action = self.actions.pop(0)
        if isinstance(action, BaseException):
            raise action
        return action


def fake_token_file(tmp_path, text=KEY):
    path = tmp_path / "fake-token"
    path.write_text(text + "\n", encoding="ascii")
    path.chmod(0o600)
    return path


def test_pinned_post_header_only_token_canonical_json_and_items_authority():
    reply = Reply(response())
    opener = Opener(reply)
    api = proxy.ProxyAPI(KEY, 1, opener=opener, max_response_bytes=4096)
    frame = api.daily(ts_code="000001.SZ", start_date="20240102", end_date="20240102")
    assert len(frame) == 1  # Proxy count=0 does not erase actual items.
    assert api.http_attempts == 1
    request, timeout = opener.calls[0]
    assert request.full_url == proxy.ENDPOINTS[0]
    assert request.method == "POST" and timeout == 15
    assert request.get_header("X-api-key") == KEY
    assert request.get_header("Accept-encoding") == "gzip"
    body = json.loads(request.data)
    assert "token" not in body and KEY.encode() not in request.data
    assert (
        request.data
        == json.dumps(
            body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    )
    assert reply.read_sizes == [4097]


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://fast.xiaodefa.cn/",
        "https://evil.invalid/",
        "https://fast.xiaodefa.cn/other",
        "https://fast.xiaodefa.cn.evil.invalid/",
    ],
)
def test_unapproved_endpoint_rejected(endpoint):
    with pytest.raises(proxy.ProxyError):
        proxy.ProxyAPI(KEY, 1, endpoint=endpoint, opener=Opener())


def test_endpoint_cannot_change_mid_capture_even_to_other_approved_host():
    opener = Opener()
    api = proxy.ProxyAPI(KEY, 1, opener=opener)
    api._endpoint = proxy.ENDPOINTS[1]
    with pytest.raises(proxy.ProxyError, match="changed_within_capture"):
        api.daily()
    assert not opener.calls and api.http_attempts == 0


@pytest.mark.parametrize(
    "failure",
    [
        URLError("untrusted-prose-must-not-escape"),
        BadStatusLine("untrusted-status-echo-" + KEY),
        HTTPError(
            proxy.ENDPOINTS[0],
            302,
            "untrusted redirect",
            HTTPMessage(),
            io.BytesIO(b"private"),
        ),
        HTTPError(
            proxy.ENDPOINTS[0],
            429,
            "untrusted rate message",
            HTTPMessage(),
            io.BytesIO(b"private"),
        ),
    ],
)
def test_failure_redacted_no_retry_no_failover_no_refund(failure):
    opener = Opener(failure)
    api = proxy.ProxyAPI(KEY, 1, opener=opener)
    with pytest.raises(proxy.ProxyError) as error:
        api.daily()
    assert "untrusted" not in str(error.value) and "private" not in str(error.value)
    assert KEY not in str(error.value)
    with pytest.raises(proxy.ProxyError, match="cap_exhausted"):
        api.daily()
    assert len(opener.calls) == 1 and api.http_attempts == 1
    assert opener.calls[0][0].full_url == proxy.ENDPOINTS[0]


def test_redirect_handler_never_returns_a_followup_request():
    assert (
        proxy.NoRedirect().redirect_request(
            Request(proxy.ENDPOINTS[0]),
            io.BytesIO(),
            302,
            "ignored",
            HTTPMessage(),
            "https://evil.invalid",
        )
        is None
    )


def test_gzip_success_and_separate_wire_decoded_caps():
    raw = response()
    opener = Opener(Reply(gzip.compress(raw), encoding="gzip"))
    api = proxy.ProxyAPI(KEY, 1, opener=opener, max_response_bytes=4096)
    assert len(api.daily()) == 1
    cap = len(gzip.compress(raw))
    assert cap < len(raw)
    api = proxy.ProxyAPI(
        KEY,
        1,
        opener=Opener(Reply(gzip.compress(raw), encoding="gzip")),
        max_response_bytes=cap,
    )
    with pytest.raises(proxy.ProxyError, match="decoded_response_too_large"):
        api.daily()
    api = proxy.ProxyAPI(KEY, 1, opener=Opener(Reply(b"x" * 11)), max_response_bytes=10)
    with pytest.raises(proxy.ProxyError, match="compressed_response_too_large"):
        api.daily()


@pytest.mark.parametrize(
    "reply,category",
    [
        (Reply(b"not-gzip", encoding="gzip"), "invalid_gzip"),
        (Reply(response(), encoding="br"), "content_encoding"),
        (Reply(response(code=2002, msg="private provider prose")), "business_response"),
        (Reply(response(msg=KEY)), "credential_echo"),
        (Reply(b'{"code":0,"code":0}'), "duplicate_json"),
        (
            Reply(response(fields=["ts_code", "ts_code"], items=[["a", "b"]])),
            "response_fields",
        ),
        (Reply(response(items=[["wrong-width"]])), "response_rows"),
        (Reply(b'{"code":0,"data":{"fields":[],"items":[[NaN]]}}'), "nonfinite"),
    ],
)
def test_bad_responses_fail_closed_without_provider_text(reply, category):
    api = proxy.ProxyAPI(KEY, 1, opener=Opener(reply))
    with pytest.raises(proxy.ProxyError, match=category) as error:
        api.daily()
    assert "private provider prose" not in str(error.value)
    assert KEY not in str(error.value)
    assert api.http_attempts == 1


@pytest.mark.parametrize(
    "params",
    [
        {"token": "must-not-be-sent"},
        {"endpoint": "https://evil.invalid"},
        {"fields": "not_a_daily_field"},
    ],
)
def test_bad_request_fields_rejected_before_send(params):
    opener = Opener()
    api = proxy.ProxyAPI(KEY, 1, opener=opener)
    with pytest.raises(proxy.ProxyError):
        api.daily(**params)
    assert api.http_attempts == 0 and not opener.calls


def test_concurrent_calls_cannot_exceed_one_physical_request():
    opener = Opener(Reply(response()))
    api = proxy.ProxyAPI(KEY, 1, opener=opener)

    def call():
        try:
            return len(api.daily())
        except proxy.ProxyError:
            return "refused"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: call(), range(2)))
    assert sorted(map(str, outcomes)) == ["1", "refused"]
    assert api.http_attempts == 1 and len(opener.calls) == 1


def test_proxy_token_file_valid_and_explicit_file_never_falls_back(
    tmp_path, monkeypatch
):
    path = fake_token_file(tmp_path)
    monkeypatch.setenv("TUSHARE_PROXY_TOKEN", "Y" * 56)
    assert proxy.read_proxy_token(path) == KEY
    path.chmod(0o644)
    with pytest.raises(proxy.ProxyError):
        proxy.read_proxy_token(path)
    assert proxy.read_proxy_token() == "Y" * 56


def test_symlink_and_wrong_owner_credentials_rejected(tmp_path, monkeypatch):
    path = fake_token_file(tmp_path)
    link = tmp_path / "token-link"
    link.symlink_to(path)
    with pytest.raises(proxy.ProxyError):
        proxy.read_proxy_token(link)
    uid = os.getuid()
    monkeypatch.setattr(proxy.os, "getuid", lambda: uid + 1)
    with pytest.raises(proxy.ProxyError):
        proxy.read_proxy_token(path)


@pytest.mark.parametrize("key", ["", "x" * 55, "x" * 57, "x" * 55 + " ", "中" * 56])
def test_credential_format_rejected_without_echo(key):
    with pytest.raises(proxy.ProxyError, match="credential_format"):
        proxy.ProxyAPI(key, 1, opener=Opener())


@pytest.mark.parametrize(
    "command,extra",
    [
        (
            "daily",
            [
                "--start-date",
                "20240102",
                "--target-date",
                "20240102",
                "--symbols",
                "000001.SZ",
                "--limit",
                "1",
                "--max-requests",
                "1",
            ],
        ),
        (
            "industry",
            [
                "--start-date",
                "20240101",
                "--end-date",
                "20240105",
                "--max-requests",
                "4",
            ],
        ),
    ],
)
def test_proxy_plan_does_not_read_secret_or_import_sdk(
    tmp_path, monkeypatch, capsys, command, extra
):
    monkeypatch.setattr(proxy, "read_proxy_token", forbidden)
    monkeypatch.setattr(runtime, "dependency", forbidden)
    output = tmp_path / "not-created"
    assert (
        main(
            [
                command,
                "--data-root",
                str(output),
                "--transport",
                "xiaodefa",
                "--proxy-token-file",
                str(tmp_path / "must-not-be-read"),
                *extra,
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["transport"] == "xiaodefa"
    assert payload["endpoint"] == proxy.ENDPOINTS[0]
    assert not output.exists()


def test_proxy_credentials_never_go_to_official_client(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(runtime, "dependency", forbidden)
    monkeypatch.setattr(proxy, "read_proxy_token", forbidden)
    assert (
        main(
            [
                "daily",
                "--data-root",
                str(tmp_path / "not-created"),
                "--proxy-token-file",
                str(tmp_path / "not-read"),
                "--start-date",
                "20240102",
                "--target-date",
                "20240102",
                "--limit",
                "1",
                "--max-requests",
                "1",
            ]
        )
        == 2
    )
    assert "explicit --transport xiaodefa" in capsys.readouterr().out
    with pytest.raises(runtime.PipelineError):
        runtime.init_tushare(1, proxy_token_file=tmp_path / "not-read")


def test_actual_cli_single_stock_proxy_route_with_fake_http_only(tmp_path, monkeypatch):
    key_file = fake_token_file(tmp_path)
    opener = Opener(Reply(gzip.compress(response()), encoding="gzip"))
    monkeypatch.setattr(proxy, "build_opener", lambda *handlers: opener)
    monkeypatch.setattr(daily, "get_stock_list", forbidden)
    monkeypatch.setattr(daily.time, "sleep", lambda seconds: None)
    output = tmp_path / "owned"
    assert (
        main(
            [
                "daily",
                "--data-root",
                str(output),
                "--transport",
                "xiaodefa",
                "--proxy-token-file",
                str(key_file),
                "--proxy-max-response-bytes",
                "65536",
                "--symbols",
                "000001.SZ",
                "--start-date",
                "20240102",
                "--target-date",
                "20240102",
                "--limit",
                "1",
                "--max-requests",
                "1",
                "--execute",
            ]
        )
        == 0
    )
    assert len(opener.calls) == 1
    assert json.loads(opener.calls[0][0].data)["api_name"] == "daily"
    assert (output / "market_data/000001.csv").is_file()
    progress = json.loads((output / "download_progress_tushare.json").read_text())
    provenance = progress["source_transport"]
    assert provenance["transport"] == proxy.TRANSPORT
    assert provenance["endpoint"] == proxy.ENDPOINTS[0]
    assert (
        provenance["logical_api_attempts"] == provenance["physical_http_attempts"] == 1
    )
    assert provenance["source_qualified"] is False
    assert KEY not in (output / "download_progress_tushare.json").read_text()


@pytest.mark.parametrize(
    "returned",
    [
        ["000002.SZ", "20240102", 10, 11, 9, 10.5, 12.5, 2.5, 1.2],
        ["000001.SZ", "20240103", 10, 11, 9, 10.5, 12.5, 2.5, 1.2],
    ],
)
def test_daily_response_cannot_escape_requested_instrument_and_date(returned):
    api = proxy.ProxyAPI(KEY, 1, opener=Opener(Reply(response(items=[returned]))))
    with pytest.raises(runtime.PipelineError, match="scope mismatch"):
        daily.fetch_daily_data(api, "000001.SZ", "20240102", "20240102")


def test_credential_cannot_be_repeated_in_even_an_allowed_request_parameter():
    opener = Opener()
    api = proxy.ProxyAPI(KEY, 1, opener=opener)
    with pytest.raises(proxy.ProxyError, match="credential_in_request") as error:
        api.daily(ts_code=KEY)
    assert KEY not in str(error.value)
    assert not opener.calls and api.http_attempts == 0


def test_json_escaped_credential_echo_is_rejected_after_decoding():
    row = ["000001.SZ", "20240102", KEY, 11, 9, 10.5, 12.5, 2.5, 1.2]
    escaped = "".join(f"\\u{ord(char):04x}" for char in KEY).encode()
    raw = response(items=[row]).replace(KEY.encode(), escaped)
    assert KEY.encode() not in raw
    api = proxy.ProxyAPI(KEY, 1, opener=Opener(Reply(raw)))
    with pytest.raises(proxy.ProxyError, match="credential_echo") as error:
        api.daily()
    assert KEY not in str(error.value)
    assert api.http_attempts == 1


def test_concurrent_responses_validate_request_local_status():
    reading_first = threading.Event()
    release_first = threading.Event()

    class PausedReply(Reply):
        def read(self, size):
            reading_first.set()
            assert release_first.wait(timeout=5)
            return super().read(size)

    opener = Opener(PausedReply(response(), status=201), Reply(response(), status=200))
    api = proxy.ProxyAPI(KEY, 2, opener=opener)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(api.daily)
        assert reading_first.wait(timeout=5)
        try:
            second = pool.submit(api.daily)
            assert len(second.result(timeout=5)) == 1
        finally:
            release_first.set()
        with pytest.raises(proxy.ProxyError, match="http_response_rejected"):
            first.result(timeout=5)
    assert api.http_attempts == 2
    assert len(opener.calls) == 2


def test_replaced_credential_fifo_is_nonblocking_and_rejected_before_read(
    tmp_path, monkeypatch
):
    path = fake_token_file(tmp_path)
    real_open = os.open
    real_fdopen = os.fdopen
    opened_flags = []
    reads = []

    def swapped_open(name, flags, *args, **kwargs):
        if name == path.name:
            opened_flags.append(flags)
            # Old code fails here, rather than hanging on the actual FIFO open.
            assert flags & os.O_NONBLOCK
            path.unlink()
            os.mkfifo(path, 0o600)
        return real_open(name, flags, *args, **kwargs)

    class NoRead:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def fileno(self):
            return self.stream.fileno()

        def read(self, size):
            reads.append(size)
            pytest.fail("a replaced nonregular credential descriptor must not be read")

    monkeypatch.setattr(proxy.os, "open", swapped_open)
    monkeypatch.setattr(
        proxy.os, "fdopen", lambda fd, mode: NoRead(real_fdopen(fd, mode))
    )
    with pytest.raises(proxy.ProxyError):
        proxy.read_proxy_token(path)
    assert opened_flags and not reads


def test_capture_retains_exact_safe_bytes_without_pandas_or_second_request(monkeypatch):
    import hashlib
    from dataclasses import FrozenInstanceError
    from decimal import Decimal

    raw = response()
    wire = gzip.compress(raw)
    opener = Opener(Reply(wire, encoding="gzip"))
    api = proxy.ProxyAPI(KEY, 1, opener=opener)
    monkeypatch.setattr(proxy, "dependency", forbidden)
    captured = api.capture("daily", ts_code="000001.SZ")
    assert isinstance(captured, proxy.ProxyCapture)
    assert captured.api_name == "daily"
    assert captured.wire_body == wire and captured.decoded_body == raw
    assert captured.content_encoding == "gzip"
    assert captured.http_status == 200 and captured.business_code == 0
    assert captured.wire_sha256 == hashlib.sha256(wire).hexdigest()
    assert captured.decoded_sha256 == hashlib.sha256(raw).hexdigest()
    assert captured.fields == tuple(proxy.API_FIELDS["daily"].split(","))
    assert captured.items[0][5] == Decimal("10.5")
    assert isinstance(captured.items, tuple) and isinstance(captured.items[0], tuple)
    assert captured.request_body == opener.calls[0][0].data
    assert KEY.encode() not in captured.request_body
    assert api.http_attempts == len(opener.calls) == 1
    with pytest.raises(FrozenInstanceError):
        setattr(captured, "http_status", 201)  # noqa: B010 -- Exercise frozen-record rejection at runtime.


def test_capture_optional_daily_fields_do_not_change_legacy_defaults():
    legacy = "ts_code,trade_date,open,high,low,close,vol,amount,pct_chg"
    assert proxy.API_FIELDS["daily"] == legacy
    columns = ["ts_code", "trade_date", "close", "vol", "pre_close"]
    opener = Opener(
        Reply(response(fields=columns, items=[["000001.SZ", "20240102", 10, 1, 9]]))
    )
    api = proxy.ProxyAPI(KEY, 1, opener=opener)
    captured = api.capture("daily", fields=",".join(columns))
    assert captured.fields == tuple(columns)
    assert json.loads(captured.request_body)["fields"] == ",".join(columns)
    assert proxy.API_FIELDS["daily"] == legacy


@pytest.mark.parametrize(
    "name,params,columns,row",
    [
        (
            "trade_cal",
            {"exchange": "SSE", "start_date": "20240101", "end_date": "20240102"},
            ["exchange", "cal_date", "is_open", "pretrade_date"],
            ["SSE", "20240102", 1, "20231229"],
        ),
        (
            "stk_limit",
            {"ts_code": "000001.SZ", "start_date": "20240102", "end_date": "20240102"},
            ["trade_date", "ts_code", "pre_close", "up_limit", "down_limit"],
            ["20240102", "000001.SZ", 10, 11, 9],
        ),
    ],
)
def test_capture_only_adds_the_two_fixed_apis(name, params, columns, row):
    opener = Opener(Reply(response(name, items=[row], fields=columns)))
    api = proxy.ProxyAPI(KEY, 1, opener=opener)
    result = api.capture(name, **params)
    assert result.fields == tuple(columns)
    assert json.loads(result.request_body)["params"] == params
    assert api.http_attempts == 1
    with pytest.raises(proxy.ProxyError, match="api_not_supported"):
        api.capture("adj_factor")
    assert len(opener.calls) == 1


def test_capture_optional_static_fields_and_response_column_order():
    legacy = "ts_code,symbol,name,market,list_date"
    assert proxy.API_FIELDS["stock_basic"] == legacy
    fields = ["exchange", "delist_date", "curr_type", "ts_code"]
    opener = Opener(
        Reply(
            response(
                "stock_basic", items=[["SSE", None, "CNY", "600000.SH"]], fields=fields
            )
        )
    )
    api = proxy.ProxyAPI(KEY, 1, opener=opener)
    captured = api.capture(
        "stock_basic", fields="ts_code,exchange,delist_date,curr_type", list_status="L"
    )
    assert captured.fields == tuple(fields)
    assert captured.items == (("SSE", None, "CNY", "600000.SH"),)
    assert proxy.API_FIELDS["stock_basic"] == legacy


def test_h0_single_link_dummy_is_still_accepted(tmp_path, monkeypatch):
    monkeypatch.setattr(proxy, "build_opener", forbidden)
    path = fake_token_file(tmp_path)
    assert path.stat().st_nlink == 1
    assert proxy.read_proxy_token(path) == KEY


def test_h0_hardlink_is_rejected_before_target_open(tmp_path, monkeypatch):
    path = fake_token_file(tmp_path)
    os.link(path, tmp_path / "alias")
    real_open = os.open
    target_opens = []

    def opened(name, flags, *args, **kwargs):
        if name == path.name:
            target_opens.append(name)
        return real_open(name, flags, *args, **kwargs)

    monkeypatch.setattr(proxy.os, "open", opened)
    monkeypatch.setattr(proxy.os, "fdopen", forbidden)
    monkeypatch.setattr(proxy, "build_opener", forbidden)
    with pytest.raises(proxy.ProxyError, match="credential_file_policy") as error:
        proxy.read_proxy_token(path)
    assert not target_opens and KEY not in str(error.value)


def test_h0_link_added_before_open_is_rejected_before_read(tmp_path, monkeypatch):
    path = fake_token_file(tmp_path)
    real_open = os.open

    def opened(name, flags, *args, **kwargs):
        if name == path.name:
            os.link(path, tmp_path / "alias")
        return real_open(name, flags, *args, **kwargs)

    monkeypatch.setattr(proxy.os, "open", opened)
    monkeypatch.setattr(proxy.os, "fdopen", forbidden)
    monkeypatch.setattr(proxy, "build_opener", forbidden)
    with pytest.raises(proxy.ProxyError, match="credential_changed"):
        proxy.read_proxy_token(path)
    assert path.stat().st_nlink == 2


def test_h0_link_added_at_fd_stat_is_rejected_before_read(tmp_path, monkeypatch):
    path = fake_token_file(tmp_path)
    real_fstat = os.fstat
    linked = False

    def changed(fd):
        nonlocal linked
        info = real_fstat(fd)
        if stat.S_ISREG(info.st_mode) and not linked:
            os.link(path, tmp_path / "alias")
            linked = True
        return real_fstat(fd)

    monkeypatch.setattr(proxy.os, "fstat", changed)
    monkeypatch.setattr(proxy.os, "fdopen", forbidden)
    monkeypatch.setattr(proxy, "build_opener", forbidden)
    with pytest.raises(proxy.ProxyError, match="credential_changed"):
        proxy.read_proxy_token(path)
    assert linked


def test_h0_link_added_during_read_withholds_dummy(tmp_path, monkeypatch):
    path = fake_token_file(tmp_path)
    real_fdopen = os.fdopen
    reads = []

    class Reader:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()
            return False

        def read(self, size):
            reads.append(size)
            raw = self.stream.read(size)
            os.link(path, tmp_path / "alias")
            return raw

    monkeypatch.setattr(
        proxy.os, "fdopen", lambda *args, **kwargs: Reader(real_fdopen(*args, **kwargs))
    )
    monkeypatch.setattr(proxy, "build_opener", forbidden)
    with pytest.raises(proxy.ProxyError, match="credential_changed") as error:
        proxy.read_proxy_token(path)
    assert reads == [4097] and KEY not in str(error.value)


def _h0_track_fds(path, monkeypatch):
    real_open = os.open
    handles = {}

    def opened(name, flags, *args, **kwargs):
        fd = real_open(name, flags, *args, **kwargs)
        if name == path.name:
            handles.update(file=fd, parent=kwargs["dir_fd"])
        return fd

    monkeypatch.setattr(proxy.os, "open", opened)
    return handles


@pytest.mark.parametrize("stop_type", [KeyboardInterrupt, SystemExit])
@pytest.mark.parametrize("which_close", ["file", "parent"])
def test_h0_original_stop_outranks_cleanup(
    tmp_path, monkeypatch, stop_type, which_close
):
    path = fake_token_file(tmp_path)
    handles = _h0_track_fds(path, monkeypatch)
    real_close = os.close
    original = stop_type("synthetic stop")
    state = {"armed": False, "injected": False}

    class Reader:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size):
            assert size == 4097
            state["armed"] = True
            raise original

    def closed(fd):
        real_close(fd)
        if state["armed"] and fd == handles[which_close] and not state["injected"]:
            state["injected"] = True
            raise OSError("synthetic secondary close")

    monkeypatch.setattr(proxy.os, "close", closed)
    monkeypatch.setattr(proxy.os, "fdopen", lambda *args, **kwargs: Reader())
    monkeypatch.setattr(proxy, "build_opener", forbidden)
    with pytest.raises(stop_type) as error:
        proxy.read_proxy_token(path)
    assert error.value is original and state["injected"]


@pytest.mark.parametrize("which_close", ["file", "parent"])
def test_h0_close_failure_is_redacted_after_owned_fd_close(
    tmp_path, monkeypatch, which_close
):
    path = fake_token_file(tmp_path)
    handles = _h0_track_fds(path, monkeypatch)
    real_close = os.close
    injected = False

    def closed(fd):
        nonlocal injected
        real_close(fd)
        if handles and fd == handles[which_close] and not injected:
            injected = True
            raise OSError(KEY)

    monkeypatch.setattr(proxy.os, "close", closed)
    monkeypatch.setattr(proxy, "build_opener", forbidden)
    with pytest.raises(proxy.ProxyError, match="credential_unavailable") as error:
        proxy.read_proxy_token(path)
    assert injected and KEY not in str(error.value)
