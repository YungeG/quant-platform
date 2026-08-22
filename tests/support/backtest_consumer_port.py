from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, NoReturn

CONTRACT_PATH = Path(__file__).resolve().parents[1] / "contracts/backtest-consumer-port-v1.json"
CONTRACT_V2_PATH = Path(__file__).resolve().parents[1] / "contracts/backtest-consumer-port-v2.json"
FAILURE_PRECEDENCE = (
    "PORT_REF_TYPE_MISMATCH",
    "PORT_REF_NOT_FOUND",
    "PORT_EVIDENCE_TAMPERED",
    "PORT_MANIFEST_INVALID",
    "PORT_RETENTION_UNAVAILABLE",
    "PORT_TERMINAL_NOT_ANALYZABLE",
    "PORT_ANALYSIS_LINK_MISMATCH",
)
FAILURE_PRECEDENCE_V2 = (
    "PORT_REF_TYPE_MISMATCH",
    "PORT_REF_NOT_FOUND",
    "PORT_EVIDENCE_TAMPERED",
    "PORT_MANIFEST_INVALID",
    "PORT_STATIC_PROOF_MISMATCH",
    "PORT_COMPLETED_VERSION_MISMATCH",
    "PORT_ANALYSIS_VERSION_MISMATCH",
    "PORT_RETENTION_UNAVAILABLE",
    "PORT_TERMINAL_NOT_ANALYZABLE",
    "PORT_ANALYSIS_LINK_MISMATCH",
)

_TERMINAL_STATUSES = {"BLOCKED", "FAILED", "CANCELLED"}
_TERMINAL_REFS = {
    ("backtest_resolution_failure", 1),
    ("evidence_manifest", 1),
}
_HASH = re.compile(r"sha256:[0-9a-f]{64}")
_RUN = re.compile(r"run_[0-9a-f]{64}")
_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?")
_RUN_FAILURES = {"PORT_RETENTION_UNAVAILABLE"}
_INJECTABLE_FAILURES_V1 = {
    "PORT_EVIDENCE_TAMPERED",
    "PORT_MANIFEST_INVALID",
    "PORT_RETENTION_UNAVAILABLE",
}
_INJECTABLE_FAILURES_V2 = _INJECTABLE_FAILURES_V1 | {
    "PORT_STATIC_PROOF_MISMATCH",
    "PORT_COMPLETED_VERSION_MISMATCH",
    "PORT_ANALYSIS_VERSION_MISMATCH",
}
_ALL_FAILURES = set(FAILURE_PRECEDENCE_V2)


class PortFailure(RuntimeError):
    def __init__(self, code: str) -> None:
        if code not in _ALL_FAILURES:
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
    """Model frozen Backtest consumer observations without provider semantics."""

    def __init__(
        self,
        contract: dict[str, Any] | None = None,
        *,
        contract_path: Path = CONTRACT_PATH,
    ) -> None:
        if contract is not None and contract_path != CONTRACT_PATH:
            raise ValueError("contract and contract_path are mutually exclusive")
        self._contract = deepcopy(
            load_contract_fixture(contract_path) if contract is None else contract
        )
        self._failure_precedence = (
            FAILURE_PRECEDENCE_V2
            if self._contract.get("contract_id") == "BT-PORT-02"
            and self._contract.get("schema_version") == 2
            else FAILURE_PRECEDENCE
        )
        self._injectable_failures = (
            _INJECTABLE_FAILURES_V2
            if self._failure_precedence is FAILURE_PRECEDENCE_V2
            else _INJECTABLE_FAILURES_V1
        )
        self._faults: dict[str, set[str]] = {}

    def case(self, case_id: str) -> dict[str, Any]:
        matches = [case for case in self._cases() if case.get("case_id") == case_id]
        if len(matches) != 1:
            raise KeyError(case_id)
        return deepcopy(matches[0])

    def inject_failures(self, ref: dict[str, Any], *codes: str) -> None:
        if not codes or any(
            type(code) is not str or code not in self._injectable_failures
            for code in codes
        ):
            raise ValueError("codes must be frozen provider-state port failures")
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
        elif kind == "completed_v3":
            self.load_completed_v3(ref)
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
        if self._is_expected_ref(completed_ref, "terminal"):
            self.load_terminal(completed_ref)
            _fail("PORT_TERMINAL_NOT_ANALYZABLE")
        if not _is_ref_kind(metric_profile_ref, "metric_profile"):
            _fail("PORT_REF_TYPE_MISMATCH")

        if _is_ref_kind(completed_ref, "completed"):
            self.load_completed(completed_ref)
            field = "completed"
            analysis_kind = "analysis"
        elif _is_ref_kind(completed_ref, "completed_v3"):
            self.load_completed_v3(completed_ref)
            field = "completed_v3"
            analysis_kind = "analysis_v2"
        else:
            _fail("PORT_REF_TYPE_MISMATCH")
        case, _ = self._find_record(
            completed_ref, field, "publication_ref", field
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
        if not _is_ref_kind(analysis_ref, analysis_kind):
            _fail("PORT_MANIFEST_INVALID")
        if analysis_kind == "analysis":
            self.load_analysis(analysis_ref)
        else:
            self.load_analysis_v2(analysis_ref)
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

    def load_completed_v3(self, completed_ref: dict[str, Any]) -> dict[str, Any]:
        case, record = self._find_record(
            completed_ref, "completed_v3", "publication_ref", "completed_v3"
        )
        if (
            set(record)
            != {
                "publication_ref",
                "semantic_run_id",
                "execution_result_hash",
                "result_grade",
                "rebuild_verification_ref",
                "proof_publication_manifest_ref",
            }
            or case.get("run") != {"kind": "completed_v3", "ref": completed_ref}
            or type(record.get("semantic_run_id")) is not str
            or _RUN.fullmatch(record["semantic_run_id"]) is None
            or type(record.get("execution_result_hash")) is not str
            or _HASH.fullmatch(record["execution_result_hash"]) is None
            or record.get("result_grade") != "decision_grade"
            or not _is_artifact_ref(
                record.get("rebuild_verification_ref"),
                "deterministic_rebuild_verification",
                1,
            )
            or not _is_artifact_ref(
                record.get("proof_publication_manifest_ref"),
                "deterministic_rebuild_verification_publication_manifest",
                1,
            )
        ):
            _fail("PORT_MANIFEST_INVALID")
        self._raise_faults(
            completed_ref,
            {
                "PORT_MANIFEST_INVALID",
                "PORT_STATIC_PROOF_MISMATCH",
                "PORT_COMPLETED_VERSION_MISMATCH",
                "PORT_RETENTION_UNAVAILABLE",
            },
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
        publication_ref = completed.get("publication_ref")
        if type(publication_ref) is not dict:
            _fail("PORT_REF_TYPE_MISMATCH")
        completed_view = self.load_completed(publication_ref)
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

    def load_analysis_v2(self, analysis_ref: dict[str, Any]) -> dict[str, Any]:
        case, record = self._find_record(
            analysis_ref, "analysis_v2", "analysis_ref", "analysis_v2"
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
            or record.get("result_grade") != "decision_grade"
        ):
            _fail("PORT_MANIFEST_INVALID")

        self._raise_faults(
            analysis_ref,
            {
                "PORT_MANIFEST_INVALID",
                "PORT_STATIC_PROOF_MISMATCH",
                "PORT_ANALYSIS_VERSION_MISMATCH",
                "PORT_RETENTION_UNAVAILABLE",
            },
        )
        completed = case.get("completed_v3")
        derivation = case.get("derive")
        if type(completed) is not dict or type(derivation) is not dict:
            _fail("PORT_ANALYSIS_LINK_MISMATCH")
        publication_ref = completed.get("publication_ref")
        if type(publication_ref) is not dict:
            _fail("PORT_ANALYSIS_LINK_MISMATCH")
        completed_view = self.load_completed_v3(publication_ref)
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
        if not self._is_expected_ref(ref, expected_kind):
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

    def _is_expected_ref(self, ref: object, kind: str) -> bool:
        return _is_ref_kind(ref, kind) or (
            kind == "terminal"
            and self._failure_precedence is FAILURE_PRECEDENCE_V2
            and _is_artifact_ref(ref, "canonical_publication_manifest", 2)
        )

    def _raise_faults(self, ref: dict[str, Any], eligible: set[str]) -> None:
        faults = self._faults.get(_ref_key(ref), set())
        for code in self._failure_precedence:
            if code in faults and code in eligible:
                _fail(code)


def _artifact_ref(value: object) -> dict[str, Any] | None:
    if type(value) is not dict:
        return None
    if value.get("type") in {
        "backtest_canonical_publication_ref",
        "backtest_canonical_publication_ref_v2",
        "analysis_artifact_ref",
        "analysis_artifact_ref_v2",
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
        or type(value.get("content_hash")) is not str
        or _HASH.fullmatch(value["content_hash"]) is None
    ):
        return None
    return value


def _is_artifact_ref(value: object, artifact_type: str, schema_version: int) -> bool:
    artifact_ref = _artifact_ref(value)
    return (
        type(value) is dict
        and value.get("type") == "artifact_ref"
        and artifact_ref is not None
        and artifact_ref["artifact_type"] == artifact_type
        and artifact_ref["schema_version"] == schema_version
    )


def _is_ref_kind(value: object, kind: str) -> bool:
    artifact_ref = _artifact_ref(value)
    if artifact_ref is None or type(value) is not dict:
        return False
    ref_type = value.get("type")
    target = (artifact_ref["artifact_type"], artifact_ref["schema_version"])
    if kind == "completed":
        return ref_type == "backtest_canonical_publication_ref" and target == (
            "canonical_publication_manifest",
            1,
        )
    if kind == "completed_v3":
        return ref_type == "backtest_canonical_publication_ref_v2" and target == (
            "canonical_publication_manifest",
            2,
        )
    if kind == "analysis":
        return ref_type == "analysis_artifact_ref" and target == (
            "backtest_analysis",
            1,
        )
    if kind == "analysis_v2":
        return ref_type == "analysis_artifact_ref_v2" and target == (
            "backtest_analysis",
            2,
        )
    if kind == "metric_profile":
        return ref_type == "artifact_ref" and target == (
            "backtest_metric_profile",
            1,
        )
    if kind == "terminal":
        return ref_type == "artifact_ref" and target in _TERMINAL_REFS
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


def _fail(code: str) -> NoReturn:
    raise PortFailure(code)
