from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

CONTRACT_PATH = Path(__file__).resolve().parents[1] / "contracts/backtest-consumer-port-v1.json"
FAILURE_PRECEDENCE = (
    "PORT_REF_TYPE_MISMATCH",
    "PORT_REF_NOT_FOUND",
    "PORT_EVIDENCE_TAMPERED",
    "PORT_MANIFEST_INVALID",
    "PORT_RETENTION_UNAVAILABLE",
    "PORT_TERMINAL_NOT_ANALYZABLE",
    "PORT_ANALYSIS_LINK_MISMATCH",
)

_TERMINAL_STATUSES = {"BLOCKED", "FAILED", "CANCELLED"}
_TERMINAL_ARTIFACT_TYPES = {
    "evidence_manifest",
    "backtest_resolution_failure",
}
_HASH = re.compile(r"sha256:[0-9a-f]{64}")
_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?")
_RUN_FAILURES = {"PORT_RETENTION_UNAVAILABLE"}
_INJECTABLE_FAILURES = {
    "PORT_EVIDENCE_TAMPERED",
    "PORT_MANIFEST_INVALID",
    "PORT_RETENTION_UNAVAILABLE",
}


class PortFailure(RuntimeError):
    def __init__(self, code: str) -> None:
        if code not in FAILURE_PRECEDENCE:
            raise ValueError(f"unknown port failure: {code}")
        self.code = code
        super().__init__(code)


def load_contract_fixture(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AssertionError(f"invalid Backtest consumer fixture {path}: {error}") from error
    if type(value) is not dict:
        raise AssertionError("Backtest consumer fixture must be a JSON object")
    return value


class InMemoryBacktestConsumerPort:
    """Model BT-PORT-01 observations without verifying provider evidence."""

    def __init__(self, contract: dict[str, Any] | None = None) -> None:
        self._contract = deepcopy(
            load_contract_fixture() if contract is None else contract
        )
        self._faults: dict[str, set[str]] = {}

    def case(self, case_id: str) -> dict[str, Any]:
        matches = [case for case in self._cases() if case.get("case_id") == case_id]
        if len(matches) != 1:
            raise KeyError(case_id)
        return deepcopy(matches[0])

    def inject_failures(self, ref: dict[str, Any], *codes: str) -> None:
        if not codes or any(
            type(code) is not str or code not in _INJECTABLE_FAILURES
            for code in codes
        ):
            raise ValueError("codes must be provider-state BT-PORT-01 failures")
        self._faults.setdefault(_ref_key(ref), set()).update(codes)

    def run(self, request_spec: dict[str, Any]) -> dict[str, Any]:
        selector = deepcopy(request_spec)
        experiment_id = selector.pop("experiment_id", None)
        if experiment_id is not None and (
            type(experiment_id) is not str or not experiment_id
        ):
            _fail("PORT_MANIFEST_INVALID")
        matches = [
            case for case in self._cases() if case.get("request_spec") == selector
        ]
        if not matches:
            _fail("PORT_REF_NOT_FOUND")
        if len(matches) != 1:
            _fail("PORT_MANIFEST_INVALID")

        outcome = matches[0].get("run")
        if type(outcome) is not dict:
            _fail("PORT_MANIFEST_INVALID")
        kind = outcome.get("kind")
        if kind == "failure":
            if set(outcome) != {"kind", "failure"}:
                _fail("PORT_MANIFEST_INVALID")
            failure = outcome["failure"]
            if (
                type(failure) is not dict
                or set(failure) != {"code"}
                or failure["code"] not in _RUN_FAILURES
            ):
                _fail("PORT_MANIFEST_INVALID")
            _fail(failure["code"])
        if set(outcome) != {"kind", "ref"}:
            _fail("PORT_MANIFEST_INVALID")

        ref = outcome["ref"]
        if kind == "completed":
            self.load_completed(ref)
        elif kind == "terminal":
            self.load_terminal(ref)
        else:
            _fail("PORT_MANIFEST_INVALID")
        return deepcopy(ref)

    def derive(
        self,
        completed_ref: dict[str, Any],
        metric_profile_ref: dict[str, Any],
    ) -> dict[str, Any]:
        if _is_ref_kind(completed_ref, "terminal"):
            self.load_terminal(completed_ref)
            _fail("PORT_TERMINAL_NOT_ANALYZABLE")
        if not _is_ref_kind(completed_ref, "completed"):
            _fail("PORT_REF_TYPE_MISMATCH")
        if not _is_ref_kind(metric_profile_ref, "metric_profile"):
            _fail("PORT_REF_TYPE_MISMATCH")

        self.load_completed(completed_ref)
        case, _ = self._find_record(
            completed_ref, "completed", "publication_ref", "completed"
        )
        derivation = case.get("derive")
        if (
            type(derivation) is not dict
            or set(derivation) != {"metric_profile_ref", "analysis_ref"}
        ):
            _fail("PORT_MANIFEST_INVALID")
        if metric_profile_ref != derivation["metric_profile_ref"]:
            _fail("PORT_REF_NOT_FOUND")
        analysis_ref = derivation["analysis_ref"]
        if not _is_ref_kind(analysis_ref, "analysis"):
            _fail("PORT_MANIFEST_INVALID")
        self.load_analysis(analysis_ref)
        return deepcopy(analysis_ref)

    def load_completed(self, completed_ref: dict[str, Any]) -> dict[str, Any]:
        case, record = self._find_record(
            completed_ref, "completed", "publication_ref", "completed"
        )
        if (
            set(record)
            != {
                "publication_ref",
                "semantic_run_id",
                "execution_result_hash",
                "result_grade",
            }
            or case.get("run") != {"kind": "completed", "ref": completed_ref}
            or type(record.get("semantic_run_id")) is not str
            or not record["semantic_run_id"]
            or type(record.get("execution_result_hash")) is not str
            or _HASH.fullmatch(record["execution_result_hash"]) is None
            or type(record.get("result_grade")) is not str
            or record["result_grade"] not in {"development", "decision_grade"}
        ):
            _fail("PORT_MANIFEST_INVALID")
        self._raise_faults(
            completed_ref,
            {"PORT_MANIFEST_INVALID", "PORT_RETENTION_UNAVAILABLE"},
        )
        return deepcopy(record)

    def load_terminal(self, terminal_ref: dict[str, Any]) -> dict[str, Any]:
        case, record = self._find_record(
            terminal_ref, "terminal", "durable_evidence_ref", "terminal"
        )
        if (
            set(record) != {"status", "durable_evidence_ref"}
            or case.get("run") != {"kind": "terminal", "ref": terminal_ref}
            or type(record.get("status")) is not str
            or record["status"] not in _TERMINAL_STATUSES
        ):
            _fail("PORT_MANIFEST_INVALID")
        self._raise_faults(
            terminal_ref,
            {"PORT_MANIFEST_INVALID", "PORT_RETENTION_UNAVAILABLE"},
        )
        return deepcopy(record)

    def load_analysis(self, analysis_ref: dict[str, Any]) -> dict[str, Any]:
        case, record = self._find_record(
            analysis_ref, "analysis", "analysis_ref", "analysis"
        )
        if (
            set(record)
            != {
                "analysis_ref",
                "metric_profile_ref",
                "source_publication_ref",
                "source_execution_result_hash",
                "simple_period_return",
                "trade_count",
                "result_grade",
            }
            or not _is_decimal(record.get("simple_period_return"))
            or type(record.get("trade_count")) is not int
            or record["trade_count"] < 0
            or type(record.get("result_grade")) is not str
            or record["result_grade"] not in {"development", "decision_grade"}
        ):
            _fail("PORT_MANIFEST_INVALID")

        self._raise_faults(
            analysis_ref,
            {"PORT_MANIFEST_INVALID", "PORT_RETENTION_UNAVAILABLE"},
        )
        completed = case.get("completed")
        derivation = case.get("derive")
        if type(completed) is not dict or type(derivation) is not dict:
            _fail("PORT_ANALYSIS_LINK_MISMATCH")
        completed_view = self.load_completed(completed.get("publication_ref"))
        if (
            set(derivation) != {"metric_profile_ref", "analysis_ref"}
            or record["analysis_ref"] != derivation["analysis_ref"]
            or record["metric_profile_ref"] != derivation["metric_profile_ref"]
            or not _is_ref_kind(record["metric_profile_ref"], "metric_profile")
            or record["source_publication_ref"] != completed_view["publication_ref"]
            or record["source_execution_result_hash"]
            != completed_view["execution_result_hash"]
            or record["result_grade"] != completed_view["result_grade"]
        ):
            _fail("PORT_ANALYSIS_LINK_MISMATCH")
        return deepcopy(record)

    def _cases(self) -> list[dict[str, Any]]:
        cases = self._contract.get("cases")
        if type(cases) is not list or any(type(case) is not dict for case in cases):
            _fail("PORT_MANIFEST_INVALID")
        return cases

    def _find_record(
        self,
        ref: dict[str, Any],
        field: str,
        ref_field: str,
        expected_kind: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not _is_ref_kind(ref, expected_kind):
            _fail("PORT_REF_TYPE_MISMATCH")
        matches = [
            (case, record)
            for case in self._cases()
            if type(record := case.get(field)) is dict and record.get(ref_field) == ref
        ]
        if not matches:
            _fail("PORT_REF_NOT_FOUND")
        if len(matches) != 1:
            _fail("PORT_MANIFEST_INVALID")
        self._raise_faults(ref, {"PORT_EVIDENCE_TAMPERED"})
        return matches[0]

    def _raise_faults(self, ref: dict[str, Any], eligible: set[str]) -> None:
        faults = self._faults.get(_ref_key(ref), set())
        for code in FAILURE_PRECEDENCE:
            if code in faults and code in eligible:
                _fail(code)


def _artifact_ref(value: object) -> dict[str, Any] | None:
    if type(value) is not dict:
        return None
    if value.get("type") in {
        "backtest_canonical_publication_ref",
        "analysis_artifact_ref",
    }:
        if set(value) != {"type", "artifact_ref"}:
            return None
        value = value["artifact_ref"]
    if (
        type(value) is not dict
        or set(value) != {"type", "artifact_type", "schema_version", "content_hash"}
        or value.get("type") != "artifact_ref"
        or type(value.get("artifact_type")) is not str
        or not value["artifact_type"]
        or type(value.get("schema_version")) is not int
        or value["schema_version"] != 1
        or type(value.get("content_hash")) is not str
        or _HASH.fullmatch(value["content_hash"]) is None
    ):
        return None
    return value


def _is_ref_kind(value: object, kind: str) -> bool:
    artifact_ref = _artifact_ref(value)
    if artifact_ref is None or type(value) is not dict:
        return False
    if kind == "completed":
        return (
            value.get("type") == "backtest_canonical_publication_ref"
            and artifact_ref["artifact_type"] == "canonical_publication_manifest"
        )
    if kind == "analysis":
        return (
            value.get("type") == "analysis_artifact_ref"
            and artifact_ref["artifact_type"] == "backtest_analysis"
        )
    if kind == "metric_profile":
        return (
            value.get("type") == "artifact_ref"
            and artifact_ref["artifact_type"] == "backtest_metric_profile"
        )
    if kind == "terminal":
        return (
            value.get("type") == "artifact_ref"
            and artifact_ref["artifact_type"] in _TERMINAL_ARTIFACT_TYPES
        )
    raise ValueError(f"unknown ref kind: {kind}")


def _is_decimal(value: object) -> bool:
    return (
        type(value) is str
        and value != "-0"
        and _DECIMAL.fullmatch(value) is not None
    )


def _ref_key(ref: dict[str, Any]) -> str:
    try:
        return json.dumps(ref, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    except (TypeError, ValueError) as error:
        raise ValueError("ref must be canonical JSON data") from error


def _fail(code: str) -> None:
    raise PortFailure(code)
