"""Synthetic resource mechanisms only. Never read market data or allocate6GiB."""

from __future__ import annotations

import json

import pytest

from experiments.a_share_price_volume_retro_resources_v1 import (
    RetroResourceError,
    RetroResourceLimits,
    probe_resource_control,
    run_bounded_worker,
)

MIB = 1024 * 1024
MODULE = "experiments.a_share_price_volume_retro_resources_v1"


def limits(**changes):
    values = {
        "memory_bytes": 64 * MIB,
        "deadline_seconds": 3,
        "total_seconds": 40,
        "output_bytes": 65536,
        "storage_bytes": 1024 * 1024,
        "max_attempts": 2,
    }
    return RetroResourceLimits(**(values | changes))


def test_invalid_limits_fail_before_host_work():
    for change in (
        {"memory_bytes": True},
        {"deadline_seconds": 0},
        {"total_seconds": 1},
        {"storage_bytes": 1},
        {"output_bytes": 0},
        {"max_attempts": 0},
        {"memory_bytes": 7 * 1024**3},
    ):
        with pytest.raises(RetroResourceError):
            limits(**change)


def require_backend():
    value = probe_resource_control()
    if not value["backend_available"]:
        pytest.skip(
            "user systemd/cgroup backend unavailable; fail-closed is separately tested"
        )


def test_actual_small_worker_reads_6gib_kernel_limit_without_allocating_it(tmp_path):
    require_backend()
    result = run_bounded_worker(
        MODULE,
        ("--probe-worker", "ok"),
        tmp_path / "resource",
        limits(memory_bytes=6 * 1024**3, max_attempts=1),
    )
    assert result["state"] == "COMPLETE"
    assert result["worker_evidence"]["memory_max"] == 6 * 1024**3
    assert result["worker_evidence"]["allocated_bytes"] == 4096
    assert result["worker_evidence"]["blas_threads"] == "1"
    assert (
        result["resource_limit_kind"]
        == "cgroup-v2-memory.max-includes-children-and-cache"
    )
    assert result["source_reads"] == result["http_requests"] == 0


@pytest.mark.parametrize(
    "scenario,category",
    [("memory", "MEMORY_LIMIT"), ("deadline", "DEADLINE"), ("output", "OUTPUT_LIMIT")],
)
def test_small_negative_workers_retain_failures_and_debit(tmp_path, scenario, category):
    require_backend()
    root = tmp_path / scenario
    result = run_bounded_worker(
        MODULE, ("--probe-worker", scenario), root, limits(deadline_seconds=1)
    )
    assert result["state"] == "FAILED" and result["stop_category"] == category
    state = json.loads((root / "budget.json").read_bytes())
    assert state["attempts_reserved"] == 1 and state["seconds_reserved"] == 11
    assert (root / "attempt-1.json").is_file()
    assert result["memory_bytes_requested"] == 64 * MIB


def test_cumulative_attempt_budget_has_no_retry_refund(tmp_path):
    require_backend()
    root = tmp_path / "one"
    cap = limits(max_attempts=1)
    run_bounded_worker(MODULE, ("--probe-worker", "ok"), root, cap)
    before = (root / "budget.json").read_bytes()
    with pytest.raises(RetroResourceError, match="BUDGET_EXHAUSTED"):
        run_bounded_worker(MODULE, ("--probe-worker", "ok"), root, cap)
    assert (root / "budget.json").read_bytes() == before
    with pytest.raises(RetroResourceError, match="BUDGET_CONFLICT"):
        run_bounded_worker(
            MODULE, ("--probe-worker", "ok"), root, limits(max_attempts=2)
        )


def test_unsupported_backend_and_low_host_memory_never_launch_worker(
    tmp_path, monkeypatch
):
    from experiments import a_share_price_volume_retro_resources_v1 as module

    monkeypatch.setattr(
        module,
        "probe_resource_control",
        lambda: {"backend_available": False, "reason": "synthetic-unavailable"},
    )
    with pytest.raises(RetroResourceError, match="RESOURCE_UNAVAILABLE"):
        run_bounded_worker(
            MODULE, ("--probe-worker", "ok"), tmp_path / "none", limits()
        )
    monkeypatch.setattr(
        module,
        "probe_resource_control",
        lambda: {"backend_available": True, "reason": None},
    )
    monkeypatch.setattr(module, "available_memory_bytes", lambda: 0)
    with pytest.raises(RetroResourceError, match="HOST_MEMORY_LOW"):
        run_bounded_worker(MODULE, ("--probe-worker", "ok"), tmp_path / "low", limits())


def test_inconsistent_cumulative_counters_cannot_replenish_budget(tmp_path):
    require_backend()
    root = tmp_path / "corrupt"
    cap = limits()
    run_bounded_worker(MODULE, ("--probe-worker", "ok"), root, cap)
    state = json.loads((root / "budget.json").read_bytes())
    state["seconds_reserved"] = 0
    (root / "budget.json").write_bytes(
        (json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n").encode()
    )
    with pytest.raises(RetroResourceError, match="BUDGET_INVALID"):
        run_bounded_worker(MODULE, ("--probe-worker", "ok"), root, cap)


def test_stubborn_descendant_is_killed_and_terminal_state_is_verified(tmp_path):
    require_backend()
    result = run_bounded_worker(
        MODULE,
        ("--probe-worker", "stubborn"),
        tmp_path / "stubborn",
        limits(deadline_seconds=1),
    )
    assert result["state"] == "FAILED" and result["stop_category"] == "DEADLINE"
    assert result["termination_verified"] is True
    assert result["elapsed_ms"] < 11000


def test_running_low_host_memory_stops_only_owned_worker(tmp_path, monkeypatch):
    require_backend()
    from experiments import a_share_price_volume_retro_resources_v1 as module

    values = iter(
        [module.MIN_AVAILABLE, module.MIN_AVAILABLE, module.MIN_AVAILABLE - 1]
    )
    monkeypatch.setattr(
        module, "available_memory_bytes", lambda: next(values, module.MIN_AVAILABLE - 1)
    )
    result = run_bounded_worker(
        MODULE, ("--probe-worker", "deadline"), tmp_path / "low-running", limits()
    )
    assert (
        result["stop_category"] == "HOST_MEMORY_LOW"
        and result["termination_verified"] is True
    )


def test_cleanup_exception_keeps_receipt_and_unresolved_durable_lease(
    tmp_path, monkeypatch
):
    require_backend()
    from experiments import a_share_price_volume_retro_resources_v1 as module

    root = tmp_path / "cleanup"

    def broken(*args):
        raise RuntimeError("synthetic cleanup failure")

    monkeypatch.setattr(module, "_finish", broken)
    with pytest.raises(RetroResourceError, match="WORKER_STATUS_UNRESOLVED"):
        run_bounded_worker(MODULE, ("--probe-worker", "ok"), root, limits())
    receipt = json.loads((root / "attempt-1.json").read_bytes())
    assert receipt["termination_verified"] is False and receipt["state"] == "FAILED"
    assert (
        json.loads((root / "budget.json").read_bytes())["active_unit"]
        == receipt["unit"]
    )
    # A released descriptor is not a released logical lease. No second worker.
    with pytest.raises(RetroResourceError, match="WORKER_STATUS_UNRESOLVED"):
        run_bounded_worker(MODULE, ("--probe-worker", "ok"), root, limits())


def test_full_counter_reset_is_detected_by_immutable_reservation_marker(tmp_path):
    require_backend()
    root = tmp_path / "reset"
    run_bounded_worker(MODULE, ("--probe-worker", "ok"), root, limits())
    state = json.loads((root / "budget.json").read_bytes())
    for field in ("attempts_reserved", "seconds_reserved", "bytes_reserved"):
        state[field] = 0
    (root / "budget.json").write_bytes(
        (json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n").encode()
    )
    with pytest.raises(RetroResourceError, match="BUDGET_INVALID"):
        run_bounded_worker(MODULE, ("--probe-worker", "ok"), root, limits())


def test_symlink_unknown_worker_and_existing_artifact_refused(tmp_path):
    alias = tmp_path / "alias"
    alias.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(RetroResourceError, match="SYMLINK"):
        run_bounded_worker(MODULE, ("--probe-worker", "ok"), alias / "root", limits())
    with pytest.raises(RetroResourceError, match="WORKER_NOT_ALLOWED"):
        run_bounded_worker("os", (), tmp_path / "bad", limits())
