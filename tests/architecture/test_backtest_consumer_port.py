from __future__ import annotations

import ast
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from tests.support.backtest_consumer_port import (
    CONTRACT_PATH,
    CONTRACT_V2_PATH,
    FAILURE_PRECEDENCE,
    FAILURE_PRECEDENCE_V2,
    InMemoryBacktestConsumerPort,
    PortFailure,
    load_contract_fixture,
)

PLATFORM_ROOT = Path(__file__).resolve().parents[2]
SUPPORT_PATH = PLATFORM_ROOT / "tests/support/backtest_consumer_port.py"
INTEGRATION_PATH = PLATFORM_ROOT / "overall/integration-v1.md"
HANDOFF_PATH = PLATFORM_ROOT / "implementation/backtest-provider-handoff.md"
GAP_REGISTER_PATH = PLATFORM_ROOT / "implementation/backtest-integration-gap-register.md"
ROADMAP_PATH = PLATFORM_ROOT / "implementation/roadmap.md"
PROTECTED_P00 = PLATFORM_ROOT / "foundation/tests/fixtures/architecture/p00-contract-v1.json"


def _case(contract: dict[str, Any], case_id: str) -> dict[str, Any]:
    matches = [case for case in contract["cases"] if case["case_id"] == case_id]
    assert len(matches) == 1
    return matches[0]


def _assert_failure(code: str, action: Any) -> PortFailure:
    with pytest.raises(PortFailure) as caught:
        action()
    assert caught.value.code == code
    assert str(caught.value) == code
    return caught.value


def _all_values(value: object):
    yield value
    if isinstance(value, dict):
        for item in value.values():
            yield from _all_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _all_values(item)


def test_contract_fixture_freezes_the_consumer_surface_and_encodings() -> None:
    contract = load_contract_fixture()

    assert CONTRACT_PATH == PLATFORM_ROOT / "tests/contracts/backtest-consumer-port-v1.json"
    assert contract["contract_id"] == "BT-PORT-01"
    assert hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest() == (
        "5f9971573154a92aa83f6ac6edbb36024721ad5b54a35f0f14414c1e393f69fa"
    )
    assert contract["schema_version"] == 1
    assert contract["status"] == "frozen"
    assert contract["test_support_only"] is True
    expected_operations = [
        "run",
        "derive",
        "load_completed",
        "load_terminal",
        "load_analysis",
    ]
    assert contract["operations"] == expected_operations
    assert contract["terminal_statuses"] == ["BLOCKED", "FAILED", "CANCELLED"]
    assert contract["failure_precedence"] == list(FAILURE_PRECEDENCE)
    assert contract["encodings"] == {
        "decimal_string": (
            "canonical ordinary decimal JSON string; no exponent, negative zero, "
            "or trailing fractional zero"
        )
    }
    assert [case["case_id"] for case in contract["cases"]] == [
        "adverse_completed",
        "terminal_blocked",
        "terminal_failed",
        "terminal_cancelled",
        "provider_failure",
    ]
    assert not any(type(value) is float for value in _all_values(contract))
    assert "observed_at" not in json.dumps(contract, sort_keys=True)

    protected_hash = hashlib.sha256(PROTECTED_P00.read_bytes()).hexdigest()
    assert protected_hash == "aebb1be1894d739b06856e012e4343d7835fc1ed0306d8c28a4bfb1d8025b782"


def test_v2_contract_fixture_freezes_exact_shape_and_backtest_golden_values() -> None:
    contract = load_contract_fixture(CONTRACT_V2_PATH)

    assert CONTRACT_V2_PATH == (
        PLATFORM_ROOT / "tests/contracts/backtest-consumer-port-v2.json"
    )
    assert hashlib.sha256(CONTRACT_V2_PATH.read_bytes()).hexdigest() == (
        "8884f7595a62995eaf296a7ad5f0518745146905da3e2fd69a92587a9423c4a8"
    )
    assert list(contract) == [
        "contract_id",
        "schema_version",
        "status",
        "test_support_only",
        "operations",
        "terminal_statuses",
        "failure_precedence",
        "encodings",
        "cases",
    ]
    assert contract["contract_id"] == "BT-PORT-02"
    assert contract["schema_version"] == 2
    assert contract["status"] == "frozen"
    assert contract["test_support_only"] is True
    assert contract["operations"] == [
        "run",
        "derive",
        "load_completed",
        "load_completed_v3",
        "load_terminal",
        "load_analysis",
        "load_analysis_v2",
    ]
    assert contract["terminal_statuses"] == ["BLOCKED", "FAILED", "CANCELLED"]
    assert contract["failure_precedence"] == list(FAILURE_PRECEDENCE_V2)
    assert contract["encodings"] == load_contract_fixture()["encodings"]
    assert len(contract["cases"]) == 1

    case = contract["cases"][0]
    assert list(case) == [
        "case_id",
        "request_spec",
        "run",
        "completed_v3",
        "derive",
        "analysis_v2",
    ]
    assert case["case_id"] == "decision_grade_completed_v3"
    assert case["request_spec"] == {"fixture_case": "decision_grade_completed_v3"}
    assert list(case["run"]) == ["kind", "ref"]
    assert case["run"]["kind"] == "completed_v3"
    assert list(case["completed_v3"]) == [
        "publication_ref",
        "semantic_run_id",
        "execution_result_hash",
        "result_grade",
        "rebuild_verification_ref",
        "proof_publication_manifest_ref",
    ]
    assert list(case["derive"]) == ["metric_profile_ref", "analysis_ref"]
    assert list(case["analysis_v2"]) == [
        "analysis_ref",
        "metric_profile_ref",
        "source_publication_ref",
        "source_execution_result_hash",
        "simple_period_return",
        "trade_count",
        "result_grade",
    ]
    assert case["run"]["ref"] == case["completed_v3"]["publication_ref"]
    assert case["completed_v3"]["publication_ref"] == {
        "type": "backtest_canonical_publication_ref_v2",
        "artifact_ref": {
            "type": "artifact_ref",
            "artifact_type": "canonical_publication_manifest",
            "schema_version": 2,
            "content_hash": (
                "sha256:bedebcbaaf59f40a6ff797bc9e3f23cb2eeac5e5984dcc75bf98d1796ec37d01"
            ),
        },
    }
    assert case["completed_v3"]["semantic_run_id"] == (
        "run_978a2650090b81d853bec35921173c628162a487eac9878347bc1ffe3c4cc609"
    )
    assert case["completed_v3"]["execution_result_hash"] == (
        "sha256:882a42741e0b682dfa1c7221f080b73ffac3bd9afcb3ae6dbf2b3773a74dabd1"
    )
    assert case["completed_v3"]["result_grade"] == "decision_grade"
    assert case["completed_v3"]["rebuild_verification_ref"] == {
        "type": "artifact_ref",
        "artifact_type": "deterministic_rebuild_verification",
        "schema_version": 1,
        "content_hash": (
            "sha256:cf7c30f15c511488538c87422a961048e69b27cc1a2c6ba10b8d830f2fcbebf0"
        ),
    }
    assert case["completed_v3"]["proof_publication_manifest_ref"] == {
        "type": "artifact_ref",
        "artifact_type": (
            "deterministic_rebuild_verification_publication_manifest"
        ),
        "schema_version": 1,
        "content_hash": (
            "sha256:8caaae753a18556bc0fdc017381bae0973c4b73398637257433b62fecd796a59"
        ),
    }
    assert case["derive"]["metric_profile_ref"]["content_hash"] == (
        "sha256:bced4dbef8bbf6e1ec9821ae3b68e8c6ce2bbed953f95fe1214c8e21676dbd6a"
    )
    assert case["derive"]["analysis_ref"] == case["analysis_v2"]["analysis_ref"]
    assert case["derive"]["analysis_ref"] == {
        "type": "analysis_artifact_ref_v2",
        "artifact_ref": {
            "type": "artifact_ref",
            "artifact_type": "backtest_analysis",
            "schema_version": 2,
            "content_hash": (
                "sha256:f620d21d6372814d63f77e4f0a3506d2cb44bdc5a62c42f71b8abdccdfc5f50a"
            ),
        },
    }
    assert case["analysis_v2"]["source_publication_ref"] == case["run"]["ref"]
    assert case["analysis_v2"]["source_execution_result_hash"] == (
        case["completed_v3"]["execution_result_hash"]
    )
    assert case["analysis_v2"]["simple_period_return"] == "0.02392"
    assert case["analysis_v2"]["trade_count"] == 1
    assert case["analysis_v2"]["result_grade"] == "decision_grade"
    assert not any(type(value) is float for value in _all_values(contract))


def test_v2_exact_journey_and_adjacent_v1_dispatch_are_stable() -> None:
    v2_port = InMemoryBacktestConsumerPort(contract_path=CONTRACT_V2_PATH)
    v2_case = v2_port.case("decision_grade_completed_v3")

    completed_ref = v2_port.run(v2_case["request_spec"])
    completed = v2_port.load_completed_v3(completed_ref)
    analysis_ref = v2_port.derive(
        completed_ref, v2_case["derive"]["metric_profile_ref"]
    )
    analysis = v2_port.load_analysis_v2(analysis_ref)

    assert completed == v2_case["completed_v3"]
    assert analysis_ref == v2_case["derive"]["analysis_ref"]
    assert analysis == v2_case["analysis_v2"]
    assert analysis["source_publication_ref"] == completed_ref
    assert analysis["source_execution_result_hash"] == completed["execution_result_hash"]
    assert analysis["result_grade"] == completed["result_grade"]

    v1_port = InMemoryBacktestConsumerPort()
    v1_case = v1_port.case("adverse_completed")
    v1_completed_ref = v1_port.run(v1_case["request_spec"])
    assert v1_port.load_completed(v1_completed_ref) == v1_case["completed"]
    v1_analysis_ref = v1_port.derive(
        v1_completed_ref, v1_case["derive"]["metric_profile_ref"]
    )
    assert v1_port.load_analysis(v1_analysis_ref) == v1_case["analysis"]


def test_v2_refs_fail_closed_without_unwrap_cross_version_or_downgrade() -> None:
    v2_port = InMemoryBacktestConsumerPort(contract_path=CONTRACT_V2_PATH)
    v2_case = v2_port.case("decision_grade_completed_v3")
    v2_completed_ref = v2_case["completed_v3"]["publication_ref"]
    v2_analysis_ref = v2_case["analysis_v2"]["analysis_ref"]
    v1_port = InMemoryBacktestConsumerPort()
    v1_case = v1_port.case("adverse_completed")
    v1_completed_ref = v1_case["completed"]["publication_ref"]
    v1_analysis_ref = v1_case["analysis"]["analysis_ref"]

    for action in (
        lambda: v2_port.load_completed(v2_completed_ref),
        lambda: v2_port.load_completed_v3(v1_completed_ref),
        lambda: v2_port.load_analysis(v2_analysis_ref),
        lambda: v2_port.load_analysis_v2(v1_analysis_ref),
        lambda: v2_port.load_completed_v3(v2_completed_ref["artifact_ref"]),
    ):
        _assert_failure("PORT_REF_TYPE_MISMATCH", action)

    unknown_wrapper = deepcopy(v2_completed_ref)
    unknown_wrapper["type"] = "backtest_canonical_publication_ref_v3"
    _assert_failure(
        "PORT_REF_TYPE_MISMATCH",
        lambda: v2_port.load_completed_v3(unknown_wrapper),
    )
    unknown_version = deepcopy(v2_completed_ref)
    unknown_version["artifact_ref"]["schema_version"] = 3
    _assert_failure(
        "PORT_REF_TYPE_MISMATCH",
        lambda: v2_port.load_completed_v3(unknown_version),
    )
    raw_manifest_v2 = deepcopy(v2_completed_ref["artifact_ref"])
    _assert_failure(
        "PORT_REF_TYPE_MISMATCH",
        lambda: v2_port.load_completed_v3(raw_manifest_v2),
    )
    _assert_failure(
        "PORT_REF_NOT_FOUND",
        lambda: v2_port.load_terminal(raw_manifest_v2),
    )

    no_downgrade = InMemoryBacktestConsumerPort(contract_path=CONTRACT_V2_PATH)
    no_downgrade.inject_failures(
        v2_completed_ref, "PORT_COMPLETED_VERSION_MISMATCH"
    )
    _assert_failure(
        "PORT_COMPLETED_VERSION_MISMATCH",
        lambda: no_downgrade.run(v2_case["request_spec"]),
    )


def test_v2_records_links_and_failure_precedence_fail_closed() -> None:
    contract = load_contract_fixture(CONTRACT_V2_PATH)
    case = _case(contract, "decision_grade_completed_v3")
    completed_ref = deepcopy(case["completed_v3"]["publication_ref"])
    analysis_ref = deepcopy(case["analysis_v2"]["analysis_ref"])

    port = InMemoryBacktestConsumerPort(contract)
    port.inject_failures(
        completed_ref,
        "PORT_RETENTION_UNAVAILABLE",
        "PORT_COMPLETED_VERSION_MISMATCH",
        "PORT_STATIC_PROOF_MISMATCH",
        "PORT_MANIFEST_INVALID",
        "PORT_EVIDENCE_TAMPERED",
    )
    _assert_failure(
        "PORT_EVIDENCE_TAMPERED", lambda: port.load_completed_v3(completed_ref)
    )

    completed_port = InMemoryBacktestConsumerPort(contract)
    completed_port.inject_failures(
        completed_ref,
        "PORT_STATIC_PROOF_MISMATCH",
        "PORT_COMPLETED_VERSION_MISMATCH",
        "PORT_RETENTION_UNAVAILABLE",
    )
    _assert_failure(
        "PORT_STATIC_PROOF_MISMATCH",
        lambda: completed_port.load_completed_v3(completed_ref),
    )

    analysis_port = InMemoryBacktestConsumerPort(contract)
    analysis_port.inject_failures(
        analysis_ref,
        "PORT_ANALYSIS_VERSION_MISMATCH",
        "PORT_RETENTION_UNAVAILABLE",
    )
    _assert_failure(
        "PORT_ANALYSIS_VERSION_MISMATCH",
        lambda: analysis_port.load_analysis_v2(analysis_ref),
    )

    malformed = load_contract_fixture(CONTRACT_V2_PATH)
    _case(malformed, "decision_grade_completed_v3")["completed_v3"]["extra"] = True
    _assert_failure(
        "PORT_MANIFEST_INVALID",
        lambda: InMemoryBacktestConsumerPort(malformed).load_completed_v3(completed_ref),
    )

    forged = load_contract_fixture(CONTRACT_V2_PATH)
    forged_case = _case(forged, "decision_grade_completed_v3")
    forged_case["analysis_v2"]["source_execution_result_hash"] = "sha256:" + "0" * 64
    _assert_failure(
        "PORT_ANALYSIS_LINK_MISMATCH",
        lambda: InMemoryBacktestConsumerPort(forged).load_analysis_v2(analysis_ref),
    )


def test_v1_fault_and_malformed_link_dispositions_remain_exact() -> None:
    port = InMemoryBacktestConsumerPort()
    completed_ref = port.case("adverse_completed")["completed"]["publication_ref"]
    with pytest.raises(ValueError):
        port.inject_failures(completed_ref, "PORT_STATIC_PROOF_MISMATCH")

    contract = load_contract_fixture()
    case = _case(contract, "adverse_completed")
    analysis_ref = deepcopy(case["analysis"]["analysis_ref"])
    case["completed"].pop("publication_ref")
    _assert_failure(
        "PORT_REF_TYPE_MISMATCH",
        lambda: InMemoryBacktestConsumerPort(contract).load_analysis(analysis_ref),
    )


def test_completed_evidence_alone_derives_exact_verified_analysis() -> None:
    port = InMemoryBacktestConsumerPort()
    case = port.case("adverse_completed")

    completed_ref = port.run(case["request_spec"])
    completed = port.load_completed(completed_ref)
    analysis_ref = port.derive(completed_ref, case["derive"]["metric_profile_ref"])
    analysis = port.load_analysis(analysis_ref)

    assert completed == case["completed"]
    assert set(completed) == {
        "publication_ref",
        "semantic_run_id",
        "execution_result_hash",
        "result_grade",
    }
    assert completed["semantic_run_id"] == "opaque-backtest-run-fixture-001"
    assert completed["result_grade"] == "development"

    assert analysis == case["analysis"]
    assert analysis["analysis_ref"] == case["derive"]["analysis_ref"]
    assert analysis["metric_profile_ref"] == case["derive"]["metric_profile_ref"]
    assert analysis["source_publication_ref"] == completed_ref
    assert analysis["source_execution_result_hash"] == completed["execution_result_hash"]
    assert analysis["simple_period_return"] == "-0.1"
    assert type(analysis["simple_period_return"]) is str
    assert analysis["trade_count"] == 1
    assert type(analysis["trade_count"]) is int
    assert analysis["result_grade"] == completed["result_grade"]

    assert port.run(case["request_spec"]) == completed_ref
    assert port.load_completed(completed_ref) == completed
    assert port.derive(completed_ref, case["derive"]["metric_profile_ref"]) == analysis_ref
    assert port.load_analysis(analysis_ref) == analysis

    analysis["simple_period_return"] = "0"
    assert port.load_analysis(analysis_ref)["simple_period_return"] == "-0.1"


def test_fixture_selector_observes_but_does_not_own_opaque_experiment_context() -> None:
    port = InMemoryBacktestConsumerPort()
    case = port.case("adverse_completed")
    request = dict(case["request_spec"])
    request["experiment_id"] = '{"type":"artifact_ref"}'

    assert port.run(request) == case["run"]["ref"]
    _assert_failure(
        "PORT_MANIFEST_INVALID",
        lambda: port.run({**case["request_spec"], "experiment_id": 1}),
    )


@pytest.mark.parametrize(
    ("case_id", "status"),
    [
        ("terminal_blocked", "BLOCKED"),
        ("terminal_failed", "FAILED"),
        ("terminal_cancelled", "CANCELLED"),
    ],
)
def test_all_terminals_are_durable_metric_free_and_not_analyzable(
    case_id: str, status: str
) -> None:
    port = InMemoryBacktestConsumerPort()
    case = port.case(case_id)

    terminal_ref = port.run(case["request_spec"])
    terminal = port.load_terminal(terminal_ref)

    assert terminal == case["terminal"]
    assert terminal["status"] == status
    assert terminal["durable_evidence_ref"] == terminal_ref
    assert set(terminal) == {"status", "durable_evidence_ref"}
    assert port.run(case["request_spec"]) == terminal_ref
    assert port.load_terminal(terminal_ref) == terminal
    assert {
        "semantic_run_id",
        "execution_result_hash",
        "result_grade",
        "simple_period_return",
        "trade_count",
    }.isdisjoint(terminal)
    metric_profile_ref = port.case("adverse_completed")["derive"][
        "metric_profile_ref"
    ]
    _assert_failure(
        "PORT_TERMINAL_NOT_ANALYZABLE",
        lambda: port.derive(terminal_ref, metric_profile_ref),
    )


def test_completed_and_terminal_refs_are_not_interchangeable() -> None:
    port = InMemoryBacktestConsumerPort()
    completed = port.case("adverse_completed")
    terminal = port.case("terminal_blocked")
    completed_ref = completed["completed"]["publication_ref"]
    terminal_ref = terminal["terminal"]["durable_evidence_ref"]

    _assert_failure(
        "PORT_REF_TYPE_MISMATCH", lambda: port.load_terminal(completed_ref)
    )
    _assert_failure(
        "PORT_REF_TYPE_MISMATCH", lambda: port.load_completed(terminal_ref)
    )

    contract = load_contract_fixture()
    terminal = _case(contract, "terminal_blocked")
    wrong_kind = deepcopy(completed_ref["artifact_ref"])
    terminal["run"]["ref"] = wrong_kind
    terminal["terminal"]["durable_evidence_ref"] = wrong_kind
    mutated = InMemoryBacktestConsumerPort(contract)
    _assert_failure(
        "PORT_REF_TYPE_MISMATCH", lambda: mutated.run(terminal["request_spec"])
    )


def test_provider_failure_stays_a_stable_failure_not_a_terminal() -> None:
    port = InMemoryBacktestConsumerPort()
    case = port.case("provider_failure")

    assert case["run"]["failure"] == {"code": "PORT_RETENTION_UNAVAILABLE"}
    failure = _assert_failure(
        "PORT_RETENTION_UNAVAILABLE", lambda: port.run(case["request_spec"])
    )
    assert not hasattr(failure, "status")
    assert not hasattr(failure, "durable_evidence_ref")


def test_reference_failures_and_provider_faults_follow_frozen_precedence() -> None:
    port = InMemoryBacktestConsumerPort()
    completed_ref = port.case("adverse_completed")["completed"]["publication_ref"]
    terminal_ref = port.case("terminal_blocked")["terminal"]["durable_evidence_ref"]

    _assert_failure(
        "PORT_REF_TYPE_MISMATCH", lambda: port.load_completed(terminal_ref)
    )

    wrong_version = deepcopy(completed_ref)
    wrong_version["artifact_ref"]["schema_version"] = 2
    _assert_failure(
        "PORT_REF_TYPE_MISMATCH", lambda: port.load_completed(wrong_version)
    )

    missing = deepcopy(completed_ref)
    missing["artifact_ref"]["content_hash"] = "sha256:" + "f" * 64
    port.inject_failures(missing, "PORT_EVIDENCE_TAMPERED")
    _assert_failure("PORT_REF_NOT_FOUND", lambda: port.load_completed(missing))

    port.inject_failures(
        completed_ref,
        "PORT_RETENTION_UNAVAILABLE",
        "PORT_MANIFEST_INVALID",
        "PORT_EVIDENCE_TAMPERED",
    )
    _assert_failure(
        "PORT_EVIDENCE_TAMPERED", lambda: port.load_completed(completed_ref)
    )

    for code in (
        "PORT_EVIDENCE_TAMPERED",
        "PORT_MANIFEST_INVALID",
        "PORT_RETENTION_UNAVAILABLE",
    ):
        mutated = InMemoryBacktestConsumerPort()
        mutated.inject_failures(completed_ref, code)
        _assert_failure(
            code, lambda mutated=mutated: mutated.load_completed(completed_ref)
        )

    terminal_port = InMemoryBacktestConsumerPort()
    terminal_port.inject_failures(terminal_ref, "PORT_RETENTION_UNAVAILABLE")
    metric_profile_ref = terminal_port.case("adverse_completed")["derive"][
        "metric_profile_ref"
    ]
    _assert_failure(
        "PORT_RETENTION_UNAVAILABLE",
        lambda: terminal_port.derive(terminal_ref, metric_profile_ref),
    )


def test_forged_analysis_links_are_failures() -> None:
    for mutation in (
        "source_publication_ref",
        "source_execution_result_hash",
        "metric_profile_ref",
        "result_grade",
    ):
        contract = load_contract_fixture()
        case = _case(contract, "adverse_completed")
        analysis_ref = deepcopy(case["analysis"]["analysis_ref"])
        if mutation in {"source_publication_ref", "metric_profile_ref"}:
            if mutation == "source_publication_ref":
                case["analysis"][mutation]["artifact_ref"]["content_hash"] = (
                    "sha256:" + "a" * 64
                )
            else:
                case["analysis"][mutation]["content_hash"] = "sha256:" + "b" * 64
        elif mutation == "source_execution_result_hash":
            case["analysis"][mutation] = "sha256:" + "c" * 64
        else:
            case["analysis"][mutation] = "decision_grade"

        port = InMemoryBacktestConsumerPort(contract)
        _assert_failure(
            "PORT_ANALYSIS_LINK_MISMATCH",
            lambda port=port, analysis_ref=analysis_ref: port.load_analysis(analysis_ref),
        )


def test_valid_foreign_links_and_duplicate_records_fail_closed() -> None:
    contract = load_contract_fixture()
    original = _case(contract, "adverse_completed")
    analysis_ref = deepcopy(original["analysis"]["analysis_ref"])
    foreign = deepcopy(original)
    foreign["case_id"] = "foreign_completed"
    foreign["request_spec"] = {"fixture_case": "foreign_completed"}
    foreign_ref = deepcopy(foreign["completed"]["publication_ref"])
    foreign_ref["artifact_ref"]["content_hash"] = "sha256:" + "9" * 64
    foreign["run"]["ref"] = deepcopy(foreign_ref)
    foreign["completed"]["publication_ref"] = deepcopy(foreign_ref)
    foreign.pop("derive")
    foreign.pop("analysis")
    contract["cases"].append(foreign)
    original["analysis"]["source_publication_ref"] = deepcopy(foreign_ref)
    port = InMemoryBacktestConsumerPort(contract)
    assert port.load_completed(foreign_ref)["publication_ref"] == foreign_ref
    _assert_failure(
        "PORT_ANALYSIS_LINK_MISMATCH", lambda: port.load_analysis(analysis_ref)
    )

    duplicate_completed = load_contract_fixture()
    original = _case(duplicate_completed, "adverse_completed")
    completed_ref = deepcopy(original["completed"]["publication_ref"])
    duplicate = deepcopy(original)
    duplicate["case_id"] = "duplicate_completed"
    duplicate["request_spec"] = {"fixture_case": "duplicate_completed"}
    duplicate_completed["cases"].append(duplicate)
    port = InMemoryBacktestConsumerPort(duplicate_completed)
    _assert_failure("PORT_MANIFEST_INVALID", lambda: port.load_completed(completed_ref))

    duplicate_analysis = load_contract_fixture()
    original = _case(duplicate_analysis, "adverse_completed")
    analysis_ref = deepcopy(original["analysis"]["analysis_ref"])
    duplicate_analysis["cases"].append(
        {
            "case_id": "duplicate_analysis",
            "request_spec": {"fixture_case": "duplicate_analysis"},
            "analysis": deepcopy(original["analysis"]),
        }
    )
    port = InMemoryBacktestConsumerPort(duplicate_analysis)
    _assert_failure("PORT_MANIFEST_INVALID", lambda: port.load_analysis(analysis_ref))


def test_invalid_or_metric_fabricating_provider_records_fail_closed() -> None:
    terminal_contract = load_contract_fixture()
    terminal_case = _case(terminal_contract, "terminal_blocked")
    terminal_case["terminal"]["simple_period_return"] = "0"
    terminal_case["terminal"]["trade_count"] = 0
    terminal_port = InMemoryBacktestConsumerPort(terminal_contract)
    terminal_port.inject_failures(
        terminal_case["terminal"]["durable_evidence_ref"],
        "PORT_RETENTION_UNAVAILABLE",
    )
    _assert_failure(
        "PORT_MANIFEST_INVALID",
        lambda: terminal_port.run(terminal_case["request_spec"]),
    )

    for value in (-0.1, "-0.10", "-0", "-1e-1"):
        analysis_contract = load_contract_fixture()
        analysis_case = _case(analysis_contract, "adverse_completed")
        analysis_ref = deepcopy(analysis_case["analysis"]["analysis_ref"])
        analysis_case["analysis"]["simple_period_return"] = value
        analysis_port = InMemoryBacktestConsumerPort(analysis_contract)
        _assert_failure(
            "PORT_MANIFEST_INVALID",
            lambda analysis_port=analysis_port, analysis_ref=analysis_ref: (
                analysis_port.load_analysis(analysis_ref)
            ),
        )


def test_opaque_run_identity_and_fixture_failure_codes_fail_closed() -> None:
    contract = load_contract_fixture()
    completed = _case(contract, "adverse_completed")
    completed["completed"]["semantic_run_id"] = ""
    port = InMemoryBacktestConsumerPort(contract)
    _assert_failure(
        "PORT_MANIFEST_INVALID", lambda: port.run(completed["request_spec"])
    )

    contract = load_contract_fixture()
    failure = _case(contract, "provider_failure")
    failure["run"]["failure"]["code"] = "PORT_TERMINAL_NOT_ANALYZABLE"
    port = InMemoryBacktestConsumerPort(contract)
    _assert_failure(
        "PORT_MANIFEST_INVALID", lambda: port.run(failure["request_spec"])
    )


def test_reconciled_request_and_admission_boundaries_are_normative() -> None:
    integration = INTEGRATION_PATH.read_text(encoding="utf-8")
    handoff = HANDOFF_PATH.read_text(encoding="utf-8")
    gap_register = GAP_REGISTER_PATH.read_text(encoding="utf-8")
    roadmap = ROADMAP_PATH.read_text(encoding="utf-8")

    for required in (
        "`CashDevelopmentRequestIntent@1`",
        "backtest_admission(entry_ref",
        "platform.backtest-evidence-admission.v1",
        "BacktestEvidenceAdmission@1",
        "Platform governance residency",
        "`PLAT-REC-03`",
        "BacktestRequestRef",
        "BacktestExecutionRequest@2",
        "prepare_cash_development_backtest()",
        "`ArtifactReadResult.artifact` is not a semantic authority",
        "G12E remains the MarketBundle read authority",
        "run returns `BacktestCanonicalPublicationRef \\| ArtifactRef`",
        "Platform never derives Backtest IDs",
        "`ResolvedBacktestRequest`",
        "pre-Attempt failures",
        "must provide accepted `BacktestEvidenceRepository.load_terminal()` evidence",
    ):
        assert required in integration
    assert "backtest_governance" not in integration
    assert "Backtest-owned request sealing" not in integration
    assert "proposed reconciliations" not in integration
    for gap in range(1, 9):
        assert f"`BT-GAP-0{gap}`" in handoff
    accepted_sha = "e3c04fb612d6798aef1420b60864d4f315ed12ac"
    assert accepted_sha in handoff
    assert "BT-GAP-09" in handoff
    assert "fixture remains selector-only" in handoff
    assert "returns `BacktestCanonicalPublicationRef | ArtifactRef`" in handoff
    assert "provider/storage failures remain outside the union" in handoff
    assert "BT-GAP-09 closes preparation, request-registration, metric-profile, and durable FAILED repository ownership" in handoff
    assert f"accepted BT-GAP-09 source revision `{accepted_sha}`" in gap_register
    assert "exact-read verifies both through Foundation" in gap_register
    assert "| `PF-CORE-01` | DONE |" in roadmap
    assert "| `SV-LEDGER-01` | DONE |" in roadmap
    assert "| `PG-LEDGER-01` | DONE |" in roadmap


def test_support_is_shared_test_only_and_imports_no_provider_or_sibling() -> None:
    source = SUPPORT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SUPPORT_PATH))
    imports = {
        name
        for node in ast.walk(tree)
        for name in (
            [alias.name for alias in node.names]
            if isinstance(node, ast.Import)
            else [node.module or ""]
            if isinstance(node, ast.ImportFrom)
            else []
        )
    }
    class_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}

    assert not any(name.startswith("crypto_quant") for name in imports)
    assert not any(name.startswith("backtest") for name in imports)
    assert "ArtifactRef" not in class_names
    assert "PortRunOutcome" not in class_names
    assert "Protocol" not in source
    assert "hashlib" not in source
    assert "Decimal" not in source
    assert "../backtest" not in source
    assert "../crypto-quant-platform" not in source

    production_roots = [
        PLATFORM_ROOT / "foundation/src",
        PLATFORM_ROOT / "research-platform/src",
        PLATFORM_ROOT / "strategy-validation/src",
        PLATFORM_ROOT / "promotion-gate/src",
    ]
    forbidden_classes = {
        "BacktestConsumerPort",
        "InMemoryBacktestConsumerPort",
        "PortRunOutcome",
    }
    for root in production_roots:
        for path in root.rglob("*.py") if root.exists() else ():
            production_source = path.read_text(encoding="utf-8")
            production_tree = ast.parse(production_source, filename=str(path))
            production_classes = {
                node.name
                for node in ast.walk(production_tree)
                if isinstance(node, ast.ClassDef)
            }
            assert forbidden_classes.isdisjoint(production_classes)
            forbidden_path = "backtest" in path.name.lower() and any(
                word in path.name.lower() for word in ("adapter", "gateway", "port")
            )
            assert not forbidden_path

    decoded = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    expected_contract = load_contract_fixture()
    assert decoded == expected_contract
    decoded_v2 = json.loads(CONTRACT_V2_PATH.read_text(encoding="utf-8"))
    expected_contract_v2 = load_contract_fixture(CONTRACT_V2_PATH)
    assert decoded_v2 == expected_contract_v2
