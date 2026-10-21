"""Independent CLI: python -m experiments.a_share_ingestion <command> ..."""

from __future__ import annotations

import argparse
import json
import sys
from importlib import import_module

from .runtime import PipelineError

COMMANDS = {
    "daily": "daily",
    "industry": "industry",
    "init": "schema",
    "import": "importer",
}


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        description="Project-local A-share source collection and import. Plan-only by default.",
        epilog="Use <command> --help for its explicit paths, scope and execution options.",
    )
    parser.add_argument("command", choices=tuple(COMMANDS))
    if not arguments or arguments[0] in {"-h", "--help"}:
        parser.parse_args(arguments)
        return 0
    command = parser.parse_args(arguments[:1]).command
    module = import_module(f"{__package__}.{COMMANDS[command]}")
    try:
        return int(module.main(arguments[1:]) or 0)
    except PipelineError as error:
        print(
            json.dumps({"state": "refused", "reason": str(error)}, ensure_ascii=False)
        )
        return 2
    except Exception as error:  # noqa: BLE001 -- public boundary emits error type only
        # Never print third-party error prose, credentials or response bodies.
        print(json.dumps({"state": "failed", "error_type": type(error).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
