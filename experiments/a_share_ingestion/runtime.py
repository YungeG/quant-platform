"""Project-local plumbing. Importing this module performs no data/credential I/O."""

from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class PipelineError(RuntimeError):
    pass


def dependency(name: str) -> Any:
    if name in {"pandas", "duckdb"}:
        # Native thread control precedes numerical-library imports, not module import.
        os.environ["OPENBLAS_NUM_THREADS"] = "1"
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError:
        raise PipelineError(
            f"Missing local dependency {name}; install this tool's requirements "
            "into the current project's environment before execution."
        ) from None


class _LazyPandas:
    def __getattr__(self, name: str) -> Any:
        return getattr(dependency("pandas"), name)


pd: Any = _LazyPandas()


@dataclass(frozen=True)
class Paths:
    data_root: Path
    db_path: Path | None = None

    def get(self, name: str) -> Path:
        directories = {
            "market_data_dir": "market_data",
            "fundamentals_dir": "fundamentals",
            "static_dir": "static",
            "extended_dir": "extended",
            "industry_evidence_dir": "industry",
        }
        if name == "duckdb_path":
            if self.db_path is None:
                raise PipelineError("--db is required for database operations")
            return self.db_path
        if name not in directories:
            raise PipelineError("unknown local data path")
        return self.data_root / directories[name]


_paths: Paths | None = None


def configure_paths(data_root: Path, db_path: Path | None = None) -> Paths:
    global _paths
    _paths = Paths(data_root.absolute(), db_path.absolute() if db_path else None)
    return _paths


def provider_path(name: str) -> Path:
    if _paths is None:
        raise PipelineError("configure project-local paths before I/O")
    return _paths.get(name)


def validate_symbol(value: str) -> str:
    if not re.fullmatch(r"[0-9]{6}", value):
        raise PipelineError("stock CSV identity must be six digits")
    return value


def parse_symbols(value: str) -> tuple[str, ...]:
    codes = tuple(value.split(","))
    if (
        not codes
        or len(set(codes)) != len(codes)
        or any(not re.fullmatch(r"[0-9]{6}\.(?:SH|SZ|BJ)", code) for code in codes)
    ):
        raise argparse.ArgumentTypeError(
            "symbols must be distinct six-digit TS codes with SH/SZ/BJ suffixes"
        )
    return codes


def date_text(value: str) -> str:
    if re.fullmatch(r"[0-9]{8}|[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        try:
            return date.fromisoformat(value).strftime("%Y%m%d")
        except ValueError:
            pass
    raise argparse.ArgumentTypeError("date must be YYYYMMDD or YYYY-MM-DD")


def local_now() -> datetime:
    # Preserve local acquisition/import semantics, not historical availability.
    return datetime.now(UTC).astimezone()


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def add_io_arguments(
    parser: argparse.ArgumentParser,
    *,
    database: bool = False,
    replace: bool = False,
    network: bool = False,
) -> None:
    parser.add_argument(
        "--data-root",
        type=Path,
        required=True,
        help="Explicit local input/output root; never an external project manifest",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform I/O instead of the default plan. Not a substitute for human authorization.",
    )
    if database:
        parser.add_argument("--db", type=Path, required=True)
    if replace:
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Explicitly acknowledge replacement of selected tables",
        )
    if network:
        parser.add_argument(
            "--max-requests",
            type=positive_int,
            required=True,
            help="Cumulative logical API calls; Xiaodefa also enforces a physical HTTP cap",
        )
        from .proxy import ENDPOINTS

        parser.add_argument(
            "--transport", choices=("official", "xiaodefa"), default="official"
        )
        parser.add_argument(
            "--proxy-token-file",
            type=Path,
            default=None,
            help="Explicit mode-0600 credential file; never read in plan mode",
        )
        parser.add_argument("--proxy-endpoint", choices=ENDPOINTS, default=None)
        parser.add_argument("--proxy-timeout", type=positive_int, default=None)
        parser.add_argument(
            "--proxy-max-response-bytes", type=positive_int, default=None
        )


def execution_guard(args: argparse.Namespace, operation: str) -> bool:
    configure_paths(args.data_root, getattr(args, "db", None))
    options = transport_options(args) if hasattr(args, "transport") else {}
    if not args.execute:
        print(
            json.dumps(
                {
                    "state": "plan_only",
                    "operation": operation,
                    "data_root": str(args.data_root),
                    "db": str(args.db) if getattr(args, "db", None) else None,
                    "network_requests": 0,
                    "database_connections": 0,
                    "source_qualified": False,
                    **(
                        {
                            "transport": args.transport,
                            "endpoint": options.get("proxy_endpoint"),
                        }
                        if hasattr(args, "transport")
                        else {}
                    ),
                },
                ensure_ascii=False,
            )
        )
        return False
    if operation == "import" and not getattr(args, "replace", False):
        raise PipelineError("database import requires explicit --replace")
    return True


def atomic_csv(frame: Any, path: Path) -> None:
    """Publish one CSV only after its complete write; preserve the old file on failure."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(fd)
    pending = Path(temporary)
    try:
        frame.to_csv(pending, index=False)
        pending.replace(path)
    finally:
        pending.unlink(missing_ok=True)


def setup_logging(data_root: Path) -> None:
    directory = data_root / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            logging.FileHandler(directory / "daily.log"),
            logging.StreamHandler(),
        ],
    )


class BoundedAPI:
    """One shared logical API-call cap. SDK-internal HTTP behavior is separate."""

    def __init__(self, api: Any, limit: int):
        if type(limit) is not int or limit < 1:
            raise PipelineError("positive request budget required")
        self.api = api
        self.limit = limit
        self.attempts = 0
        self.transport_identity = "tushare.official-sdk"
        self.endpoint: str | None = None

    def usage(self) -> dict[str, Any]:
        physical = (
            self.api.http_attempts
            if self.transport_identity == "xiaodefa.approved-tushare-proxy.v1"
            else None
        )
        return {
            "semantic_provider": "tushare.pro",
            "transport": self.transport_identity,
            "endpoint": self.endpoint,
            "logical_api_attempts": self.attempts,
            "physical_http_attempts": physical,
            "request_cap": self.limit,
            "source_qualified": False,
        }

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        method = getattr(self.api, name)

        def call(*args: Any, **kwargs: Any) -> Any:
            if self.attempts >= self.limit:
                raise PipelineError("logical API request budget exhausted")
            self.attempts += 1  # Failed calls are never refunded.
            return method(*args, **kwargs)

        return call


def transport_options(args: argparse.Namespace) -> dict[str, Any]:
    names = (
        "proxy_token_file",
        "proxy_endpoint",
        "proxy_timeout",
        "proxy_max_response_bytes",
    )
    if args.transport == "official":
        if any(getattr(args, name, None) is not None for name in names):
            raise PipelineError("proxy options require explicit --transport xiaodefa")
        return {}
    if args.transport != "xiaodefa":
        raise PipelineError("unsupported transport")
    from .proxy import DEFAULT_RESPONSE_CAP, ENDPOINTS, endpoint_url, validate_limits

    timeout = args.proxy_timeout if args.proxy_timeout is not None else 15
    maximum = (
        args.proxy_max_response_bytes
        if args.proxy_max_response_bytes is not None
        else DEFAULT_RESPONSE_CAP
    )
    validate_limits(args.max_requests, timeout, maximum)
    return {
        "transport": "xiaodefa",
        "proxy_token_file": args.proxy_token_file,
        "proxy_endpoint": endpoint_url(args.proxy_endpoint or ENDPOINTS[0]),
        "request_timeout": timeout,
        "max_response_bytes": maximum,
    }


def init_tushare(
    max_requests: int,
    *,
    transport: str = "official",
    proxy_token_file: Path | None = None,
    proxy_endpoint: str | None = None,
    request_timeout: int = 15,
    max_response_bytes: int = 1024 * 1024,
) -> BoundedAPI:
    if transport == "xiaodefa":
        from .proxy import (
            ENDPOINTS,
            TRANSPORT,
            ProxyAPI,
            endpoint_url,
            read_proxy_token,
            validate_limits,
        )

        selected = endpoint_url(proxy_endpoint or ENDPOINTS[0])
        validate_limits(max_requests, request_timeout, max_response_bytes)
        client = ProxyAPI(
            read_proxy_token(proxy_token_file),
            max_requests,
            endpoint=selected,
            timeout=request_timeout,
            max_response_bytes=max_response_bytes,
        )
        bounded = BoundedAPI(client, max_requests)
        bounded.transport_identity = TRANSPORT
        bounded.endpoint = selected
        return bounded
    if (
        transport != "official"
        or proxy_token_file is not None
        or proxy_endpoint is not None
    ):
        raise PipelineError("proxy credentials require the Xiaodefa transport")
    token = os.environ.get("TUSHARE_TOKEN", "").strip()
    if not token:
        raise PipelineError("TUSHARE_TOKEN must be provided for authorized execution")
    sdk = dependency("tushare")
    # Do not call set_token: that writes credentials into the user's home directory.
    return BoundedAPI(sdk.pro_api(token=token), max_requests)


def open_database(path: Path) -> Any:
    driver = dependency("duckdb")
    if driver.__version__ != "1.5.4":
        raise PipelineError("this importer requires locally installed DuckDB 1.5.4")
    return driver.connect(
        str(path),
        config={
            "threads": "4",
            "memory_limit": "2GiB",
            "max_temp_directory_size": "0B",
            "enable_external_access": "false",
            "allow_unsigned_extensions": "false",
            "autoinstall_known_extensions": "false",
            "autoload_known_extensions": "false",
        },
    )


def strip_exchange_symbol(value: Any) -> str:
    return validate_symbol(str(value).split(".")[0]) if value else ""


def pad_symbol(value: Any) -> str:
    return str(value).zfill(6)
