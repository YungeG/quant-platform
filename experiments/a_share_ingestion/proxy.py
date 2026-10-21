"""Pinned Xiaodefa transport (ADR0010); no credential I/O until explicitly selected."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import stat
import threading
from dataclasses import dataclass
from decimal import Decimal
from http.client import HTTPException
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .runtime import PipelineError, dependency

TRANSPORT = "xiaodefa.approved-tushare-proxy.v1"
ENDPOINTS = ("https://fast.xiaodefa.cn/", "https://tt.xiaodefa.cn/")
DEFAULT_RESPONSE_CAP = 1024 * 1024
API_FIELDS = {
    "daily": "ts_code,trade_date,open,high,low,close,vol,amount,pct_chg",
    "stock_basic": "ts_code,symbol,name,market,list_date",
    "index_classify": "index_code,industry_name,parent_code,level,industry_code,is_pub",
    "index_member_all": "l1_code,l1_name,l2_code,l2_name,l3_code,l3_name,ts_code,name,in_date,out_date,is_new",
    "sw_daily": "ts_code,trade_date,name,open,low,high,close,change,pct_change,vol,amount,pe,pb,float_mv",
    "trade_cal": "exchange,cal_date,is_open,pretrade_date",
    "stk_limit": "trade_date,ts_code,pre_close,up_limit,down_limit",
}
# Additive explicit selections only: old callers keep their original defaults.
API_OPTIONAL_FIELDS = {
    "daily": frozenset({"pre_close"}),
    "stock_basic": frozenset({"delist_date", "exchange", "curr_type"}),
    "stk_limit": frozenset({"asset_type", "exchange"}),
}
API_PARAMS = {
    "daily": {"ts_code", "trade_date", "start_date", "end_date", "offset", "limit"},
    "stock_basic": {"ts_code", "exchange", "list_status", "market"},
    "index_classify": {"index_code", "level", "parent_code", "src"},
    "index_member_all": {"l1_code", "l2_code", "l3_code", "ts_code", "is_new"},
    "sw_daily": {"ts_code", "trade_date", "start_date", "end_date"},
    "trade_cal": {"exchange", "start_date", "end_date", "is_open"},
    "stk_limit": {"ts_code", "trade_date", "start_date", "end_date"},
}


@dataclass(frozen=True, slots=True)
class ProxyCapture:
    """One checked response, not authority, provider revision or qualification."""

    api_name: str
    request_body: bytes
    http_status: int
    business_code: int
    content_encoding: str
    wire_body: bytes
    decoded_body: bytes
    fields: tuple[str, ...]
    items: tuple[tuple[str | int | Decimal | None, ...], ...]

    @property
    def wire_sha256(self) -> str:
        return hashlib.sha256(self.wire_body).hexdigest()

    @property
    def decoded_sha256(self) -> str:
        return hashlib.sha256(self.decoded_body).hexdigest()


class ProxyError(PipelineError):
    """Only controlled redacted categories; never provider or credential prose."""


def endpoint_url(value: str) -> str:
    for endpoint in ENDPOINTS:
        if value in (endpoint, endpoint[:-1]):
            return endpoint
    raise ProxyError("xiaodefa_endpoint_not_approved")


def validate_token(value: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 56
        or not value.isascii()
        or any(c.isspace() for c in value)
    ):
        raise ProxyError("xiaodefa_credential_format_rejected")
    return value


def validate_limits(max_requests: int, timeout: int, max_response_bytes: int) -> None:
    if type(max_requests) is not int or max_requests < 1:
        raise ProxyError("xiaodefa_positive_request_cap_required")
    if type(timeout) is not int or not 1 <= timeout <= 60:
        raise ProxyError("xiaodefa_timeout_out_of_bounds")
    if (
        type(max_response_bytes) is not int
        or not 1 <= max_response_bytes <= 16 * 1024 * 1024
    ):
        raise ProxyError("xiaodefa_response_cap_out_of_bounds")


def read_proxy_token(path: Path | None = None) -> str:
    if path is None:
        return validate_token(os.environ.get("TUSHARE_PROXY_TOKEN", ""))
    absolute = path.expanduser().absolute()
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    parent_fd = None
    primary: BaseException | None = None
    try:
        parent_fd = os.open(absolute.anchor, flags)
        for part in absolute.parts[1:-1]:
            following = os.open(part, flags, dir_fd=parent_fd)
            previous, parent_fd = parent_fd, following
            os.close(previous)
        before = os.stat(absolute.name, dir_fd=parent_fd, follow_symlinks=False)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_uid != os.getuid()
            or before.st_nlink != 1
            or before.st_size > 4096
        ):
            raise ProxyError("xiaodefa_credential_file_policy_rejected")
        identity = lambda info: (
            info.st_dev,
            info.st_ino,
            info.st_size,
            info.st_mtime_ns,
            info.st_mode,
            info.st_uid,
            info.st_nlink,
        )
        fd = os.open(
            absolute.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd
        )
        file_primary: BaseException | None = None
        try:
            opened = os.fstat(fd)
            if (
                not stat.S_ISREG(opened.st_mode)
                or stat.S_IMODE(opened.st_mode) != 0o600
                or opened.st_uid != os.getuid()
                or opened.st_nlink != 1
                or identity(before) != identity(opened)
            ):
                raise ProxyError("xiaodefa_credential_changed_or_oversize")
            # Descriptor policy is checked before any read, even after a path swap.
            with os.fdopen(fd, "rb", closefd=False) as stream:
                raw = stream.read(4097)
            after = os.fstat(fd)
        except BaseException as error:
            file_primary = error
            raise
        finally:
            try:
                os.close(fd)
            except BaseException as cleanup:
                if file_primary is not None:
                    raise file_primary from cleanup
                raise
        if (
            len(raw) > 4096
            or after.st_nlink != 1
            or identity(before) != identity(after)
        ):
            raise ProxyError("xiaodefa_credential_changed_or_oversize")
        return validate_token(raw.decode("ascii").rstrip("\n"))
    except (OSError, UnicodeError):
        primary = ProxyError("xiaodefa_credential_unavailable")
        raise primary from None
    except BaseException as error:
        primary = error
        raise
    finally:
        if parent_fd is not None:
            try:
                os.close(parent_fd)
            except BaseException as cleanup:
                if primary is not None:
                    raise primary from cleanup
                if isinstance(cleanup, OSError):
                    raise ProxyError("xiaodefa_credential_unavailable") from None
                raise


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProxyError("xiaodefa_duplicate_json_key")
        result[key] = value
    return result


def _nonfinite(_):
    raise ProxyError("xiaodefa_nonfinite_json")


class ProxyAPI:
    """Seven fixed APIs; one pinned endpoint and one physical call cap."""

    def __init__(
        self,
        token: str,
        max_requests: int,
        *,
        endpoint: str = ENDPOINTS[0],
        timeout: int = 15,
        max_response_bytes: int = DEFAULT_RESPONSE_CAP,
        opener: Any = None,
    ):
        self._endpoint = endpoint_url(endpoint)
        self._capture_endpoint = self._endpoint
        validate_limits(max_requests, timeout, max_response_bytes)
        self._token = validate_token(token)
        self.max_requests = max_requests
        self.timeout = timeout
        self.max_response_bytes = max_response_bytes
        self._attempts = 0
        self._attempt_lock = threading.Lock()
        self._opener = opener if opener is not None else build_opener(NoRedirect())
        self.last_http_status: int | None = None
        self.last_business_code: int | None = None

    @property
    def endpoint(self) -> str:
        return self._endpoint

    @property
    def http_attempts(self) -> int:
        return self._attempts

    def __getattr__(self, name: str) -> Any:
        if name not in API_FIELDS:
            raise AttributeError(name)

        def call(**params: Any) -> Any:
            return self.query(name, **params)

        return call

    def query(self, api_name: str, **params: Any) -> Any:
        captured = self.capture(api_name, **params)
        return dependency("pandas").DataFrame(captured.items, columns=captured.fields)

    def capture(self, api_name: str, **params: Any) -> ProxyCapture:
        endpoint = endpoint_url(self._endpoint)  # Recheck before every credential send.
        if endpoint != self._capture_endpoint:
            raise ProxyError("xiaodefa_endpoint_changed_within_capture")
        if api_name not in API_FIELDS:
            raise ProxyError("xiaodefa_api_not_supported")
        fields = params.pop("fields", API_FIELDS[api_name])
        if not isinstance(fields, str):
            raise ProxyError("xiaodefa_fields_rejected")
        expected = fields.split(",")
        if (
            not expected
            or len(set(expected)) != len(expected)
            or not set(expected)
            <= set(API_FIELDS[api_name].split(","))
            | API_OPTIONAL_FIELDS.get(api_name, frozenset())
        ):
            raise ProxyError("xiaodefa_fields_rejected")
        if not set(params) <= API_PARAMS[api_name] or any(
            type(value) not in (str, int, type(None)) for value in params.values()
        ):
            raise ProxyError("xiaodefa_parameters_rejected")
        if any(
            isinstance(value, str) and self._token in value for value in params.values()
        ):
            raise ProxyError("xiaodefa_credential_in_request_parameters")
        body = json.dumps(
            {"api_name": api_name, "params": params, "fields": fields},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        if len(body) > 4096:
            raise ProxyError("xiaodefa_request_body_too_large")
        if self._token.encode() in body:
            raise ProxyError("xiaodefa_credential_in_request_body")
        request = Request(
            endpoint,
            data=body,
            method="POST",
            headers={
                "x-api-key": self._token,
                "Content-Type": "application/json",
                "Accept-Encoding": "gzip",
            },
        )
        with self._attempt_lock:
            if self._attempts >= self.max_requests:
                raise ProxyError("xiaodefa_http_request_cap_exhausted")
            self._attempts += 1  # Reserved before sending; failures are never refunded.
            self.last_http_status = None
            self.last_business_code = None
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                http_status = int(response.status)
                self.last_http_status = http_status
                wire = response.read(self.max_response_bytes + 1)
                encoding = response.headers.get("Content-Encoding", "identity").lower()
        except HTTPError as error:
            self.last_http_status = int(error.code)
            error.close()
            raise ProxyError("xiaodefa_http_response_rejected") from None
        except (OSError, URLError, TimeoutError, HTTPException):
            raise ProxyError("xiaodefa_transport_failure") from None
        if http_status != 200:
            raise ProxyError("xiaodefa_http_response_rejected")
        if len(wire) > self.max_response_bytes:
            raise ProxyError("xiaodefa_compressed_response_too_large")
        try:
            if encoding == "gzip":
                with gzip.GzipFile(fileobj=io.BytesIO(wire)) as stream:
                    raw = stream.read(self.max_response_bytes + 1)
            elif encoding in ("", "identity"):
                raw = wire
            else:
                raise ProxyError("xiaodefa_content_encoding_rejected")
        except (OSError, EOFError):
            raise ProxyError("xiaodefa_invalid_gzip") from None
        if len(raw) > self.max_response_bytes:
            raise ProxyError("xiaodefa_decoded_response_too_large")
        if self._token.encode() in raw or self._token.encode() in wire:
            raise ProxyError("xiaodefa_credential_echo_blocked")
        try:
            payload = json.loads(
                raw,
                parse_float=Decimal,
                object_pairs_hook=_unique,
                parse_constant=_nonfinite,
            )
        except (ValueError, TypeError, UnicodeError):
            raise ProxyError("xiaodefa_invalid_json") from None
        # JSON escapes can hide echoed credentials from the raw-byte check.
        pending = [payload]
        while pending:
            value = pending.pop()
            if isinstance(value, str) and self._token in value:
                raise ProxyError("xiaodefa_credential_echo_blocked")
            if isinstance(value, dict):
                pending.extend(value.keys())
                pending.extend(value.values())
            elif isinstance(value, list):
                pending.extend(value)
        if type(payload) is not dict or type(payload.get("code")) is not int:
            raise ProxyError("xiaodefa_business_shape_rejected")
        business_code = payload["code"]
        self.last_business_code = business_code
        if business_code != 0:
            raise ProxyError("xiaodefa_business_response_rejected")
        data = payload.get("data")
        if type(data) is not dict or type(data.get("fields")) is not list:
            raise ProxyError("xiaodefa_data_shape_rejected")
        returned = data["fields"]
        if (
            any(type(name) is not str for name in returned)
            or len(returned) != len(expected)
            or len(set(returned)) != len(returned)
            or set(returned) != set(expected)
        ):
            raise ProxyError("xiaodefa_response_fields_rejected")
        items = data.get("items")
        if type(items) is not list or any(
            type(row) is not list
            or len(row) != len(returned)
            or any(type(cell) not in (str, int, Decimal, type(None)) for cell in row)
            for row in items
        ):
            raise ProxyError("xiaodefa_response_rows_rejected")
        # Optional proxy count/has_more claims do not override actual items.
        # Do not expose buffers until every credential-echo and protocol check passed.
        return ProxyCapture(
            api_name=api_name,
            request_body=body,
            http_status=http_status,
            business_code=business_code,
            content_encoding=encoding or "identity",
            wire_body=wire,
            decoded_body=raw,
            fields=tuple(returned),
            items=tuple(tuple(row) for row in items),
        )
