"""P3 engineering fixtures only. No retained market data, credentials or HTTP."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from itertools import pairwise
from pathlib import Path

import pytest

from experiments import a_share_price_volume_retro_inputs_v1 as inputs
from experiments import run_a_share_price_volume_retro_real_v1 as runner


def calendar(start=date(2000, 1, 3), weeks=110, closed=()):
    return tuple(
        (
            start + timedelta(days=i),
            (start + timedelta(days=i)).weekday() < 5
            and not any(
                w <= start + timedelta(days=i) < w + timedelta(days=7) for w in closed
            ),
        )
        for i in range(weeks * 7)
    )


def test_calendar_only_split_geometry_and_ratio():
    days = calendar()
    splits = inputs.select_calendar_splits(days)
    counts = []
    for split in splits:
        opened = [
            day
            for day, is_open in days
            if is_open and split.read_from <= day < split.read_to
        ]
        prior = [day for day in opened if day < split.decision_from]
        assert len(prior) >= 65
        decisions = {
            inputs.week_start(day)
            for day in opened
            if split.decision_from <= day < split.decision_to
        }
        counts.append(len(decisions))
        last = max(day for day in opened if day < split.decision_to)
        assert len([day for day in opened if day > last]) >= 5
        assert split.decision_from.weekday() == split.decision_to.weekday() == 0
    assert counts[1] > 0 and counts[2] == 2 * counts[1]
    assert counts[0] == 4 * counts[1] + sum(counts) % 7
    assert all(a.read_to <= b.read_from for a, b in pairwise(splits))
    assert inputs.select_calendar_splits(days) == splits


def test_closed_natural_week_and_calendar_conflicts():
    closed = (date(2001, 1, 8),)
    days = calendar(weeks=130, closed=closed)
    splits = inputs.select_calendar_splits(days)
    assert any(s.decision_from <= closed[0] < s.decision_to for s in splits)
    with pytest.raises(inputs.InputError, match="CALENDAR"):
        inputs.select_calendar_splits(days[:20] + days[21:])
    with pytest.raises(inputs.InputError, match="CALENDAR"):
        inputs.select_calendar_splits((*days, days[0]))
    with pytest.raises(inputs.InputError, match="INSUFFICIENT"):
        inputs.select_calendar_splits(calendar(weeks=20))


def test_binary64_is_exact_and_distinct_from_original_decimal_text():
    atom = inputs.normalize_number(0.1)
    assert atom["decimal"] == str(Decimal.from_float(0.1))
    assert atom["binary64_hex"] == (0.1).hex()
    assert atom["basis"] == "BINARY64_EXACT_NOT_PROVIDER_PRECISION"
    assert inputs.normalize_number("0.1")["decimal"] == "0.1"
    assert inputs.normalize_number(0)["decimal"] == "0"
    assert inputs.normalize_number(None)["decimal"] is None
    for value in (True, float("nan"), float("inf"), "NaN", "invalid"):
        with pytest.raises(inputs.InputError):
            inputs.normalize_number(value)


@pytest.fixture(scope="module")
def frozen_output(tmp_path_factory):
    root = tmp_path_factory.mktemp("p3-source-fixture") / "study"
    runner.run_fixture(root)
    return root


def test_first_csv_public_path_capture_freeze_fit_and_replay(frozen_output):
    import json

    p = json.loads((frozen_output / "packet.json").read_bytes())
    assert p["fit_calls"] == 1 and p["real_source_reads"] == p["http_requests"] == 0
    assert p["source_open_calls"] == 6
    assert p["diagnostics"]["verdict"] == "insufficient"
    assert p["provider_available_at"] is None
    assert (
        p["clock_basis"]
        == "ACTUAL_LOCAL_GOVERNANCE_AND_COMPUTE_TIMES_ON_SYNTHETIC_INPUTS"
    )
    assert len(p["reservations"]) == 8
    assert runner.replay(frozen_output) == (frozen_output / "report.md").read_text()


@pytest.mark.parametrize("kind", ("csv", "duckdb"))
def test_same_normalizer_interface_on_owned_csv_and_real_library_db(tmp_path, kind):
    root = tmp_path / kind
    root.mkdir()
    budget = inputs.ArtifactBudget(root)
    descriptor = inputs.write_fixture_source(
        budget, inputs.fixture_calendar(weeks=2), kind
    )
    read = inputs.read_csv_rows if kind == "csv" else inputs.read_duckdb_rows

    def denied():
        raise inputs.InputError("PERMISSION_DENIED")

    with pytest.raises(inputs.InputError, match="PERMISSION_DENIED"):
        read(budget, descriptor, denied)
    assert budget.read_calls == 0
    rows = read(budget, descriptor, lambda: None)
    assert len(rows) == 30
    assert any(inputs.number(row["close"]) is not None for row in rows)
    if kind == "duckdb":
        assert all(
            row["close"]["basis"] == "BINARY64_EXACT_NOT_PROVIDER_PRECISION"
            for row in rows
        )
        import duckdb

        c = inputs.open_database(budget.path(descriptor["name"]), read_only=True)
        try:
            with pytest.raises(duckdb.Error):
                c.execute("CREATE TABLE forbidden_write(x INTEGER)")
        finally:
            c.close()
        assert budget.descriptor(descriptor["name"])["sha256"] == descriptor["sha256"]


def test_nullable_states_and_zero_are_not_filled_or_inferred():
    row = next(inputs.fixture_source_rows(inputs.fixture_calendar(weeks=1)))
    row.update(volume="0", listed=None, suspended=None, comparable=None)
    value = inputs.normalize_row(row)
    assert inputs.number(value["volume"]) == 0
    assert value["listed"] is value["suspended"] is value["comparable"] is None
    with pytest.raises(inputs.InputError, match="STATE"):
        inputs.normalize_row({**row, "suspended": "normal"})


def test_actual_freeze_before_views_one_fit_price_only_outcomes(tmp_path, monkeypatch):
    from experiments import a_share_price_volume_retro_v1 as core

    root = tmp_path / "ordered"
    original = inputs.SnapshotReader.views
    fit = core.fit_retrospective_models
    fits = 0

    def views(self, admission, split, **kwargs):
        if split.partition != "TRAIN":
            assert (root / "model-cards.json").is_file()
        if kwargs.get("outcome") and split.partition != "TRAIN":
            assert (root / "predictions.json").is_file()
        result = original(self, admission, split, **kwargs)
        if kwargs.get("outcome"):
            assert all(
                bar.volume is None
                and bar.quantity_unit is None
                and bar.up_limit is None
                and bar.down_limit is None
                for view in result
                for bar in view.stock
            )
        return result

    def once(*args, **kwargs):
        nonlocal fits
        fits += 1
        assert fits == 1
        return fit(*args, **kwargs)

    monkeypatch.setattr(inputs.SnapshotReader, "views", views)
    monkeypatch.setattr(core, "fit_retrospective_models", once)
    p = runner.run_fixture(root)
    assert fits == 1
    assert (
        len(p["predictions"].feature_scope)
        == len(p["features"])
        > len(p["predictions"].rows)
    )
    assert all(
        row.label_computed_at >= p["plan"].snapshot_observed_at for row in p["labels"]
    )
    assert all(
        row.label_computed_at > p["predictions"].predicted_at
        for row in p["labels"]
        if row.partition != "TRAIN"
    )


@pytest.mark.parametrize("failure", ("permission", "scope", "model"))
def test_bad_admission_or_anchor_never_opens_snapshot(tmp_path, monkeypatch, failure):
    from dataclasses import replace

    original = runner._FixtureSession.reserve
    read = inputs.ArtifactBudget.read
    opens = 0

    def reserve(self, phase, source, **hashes):
        a = original(self, phase, source, **hashes)
        target = "DEVELOPMENT_FEATURE" if failure == "model" else "TRAIN_FEATURE"
        if phase == target:
            if failure == "permission":

                def denied():
                    raise inputs.InputError("PERMISSION_DENIED")

                a = replace(a, authorize=denied)
            elif failure == "scope":
                a = replace(
                    a,
                    source_slice=replace(
                        source, input_manifest_hash="sha256:" + "f" * 64
                    ),
                )
            else:
                path = self.budget.path("model-cards.json")
                path.write_bytes(
                    path.read_bytes().replace(b"CLIMATOLOGY", b"xxxxxxxxxxx")
                )
        return a

    def counted(self, descriptor, authorize):
        nonlocal opens
        if descriptor["name"] == "snapshot.json":
            # Admission executes before this source bytes opener, not merely after parsing.
            authorize()
            opens += 1
        return read(self, descriptor, authorize)

    monkeypatch.setattr(runner._FixtureSession, "reserve", reserve)
    monkeypatch.setattr(inputs.ArtifactBudget, "read", counted)
    with pytest.raises(inputs.InputError):
        runner.run_fixture(tmp_path / failure)
    assert opens == (2 if failure == "model" else 0)
    assert (tmp_path / failure / "failure.json").is_file()


def test_replay_never_reopens_input_sources_or_refits(
    tmp_path, frozen_output, monkeypatch
):
    import shutil

    from crypto_quant_foundation import LocalFoundation

    from experiments import a_share_price_volume_retro_v1 as core

    root = tmp_path / "replay"
    shutil.copytree(frozen_output, root)
    for name in runner.SOURCE_FILES:
        path = root / name
        if path.exists():
            path.unlink()

    def forbidden(*a, **k):
        raise AssertionError("replay is output verification only")

    for name in (
        "make_retrospective_features",
        "make_retrospective_labels",
        "fit_retrospective_models",
        "predict_retrospective_models",
        "evaluate_retrospective_predictions",
    ):
        monkeypatch.setattr(core, name, forbidden)
    monkeypatch.setattr(inputs.SnapshotReader, "views", forbidden)
    monkeypatch.setattr(inputs, "open_database", forbidden)
    monkeypatch.setattr(LocalFoundation, "checkpoint", forbidden)
    before = {
        p.relative_to(root).as_posix(): (p.stat().st_mtime_ns, p.read_bytes())
        for p in root.rglob("*")
        if p.is_file()
    }
    assert runner.replay(root) == (root / "report.md").read_text()
    after = {
        p.relative_to(root).as_posix(): (p.stat().st_mtime_ns, p.read_bytes())
        for p in root.rglob("*")
        if p.is_file()
    }
    assert after == before


def _rewrite_packet_manifest(root, p):
    import json

    from experiments import a_share_price_volume_retro_v1 as core

    raw = core.canonical_bytes(p)
    (root / "packet.json").write_bytes(raw)
    manifest = json.loads((root / "output-manifest.json").read_bytes())
    manifest["files"]["packet.json"] = {"sha256": inputs.digest(raw), "bytes": len(raw)}
    (root / "output-manifest.json").write_bytes(core.canonical_bytes(manifest))


@pytest.mark.parametrize(
    "mutation",
    ("drop_publications", "drop_reservations", "protocol", "study", "diagnostic"),
)
def test_replay_internal_identity_and_proofs_cannot_be_rehashed_away(
    tmp_path, frozen_output, mutation
):
    import json
    import shutil

    root = tmp_path / mutation
    shutil.copytree(frozen_output, root)
    p = json.loads((root / "packet.json").read_bytes())
    if mutation == "drop_publications":
        p["publications"] = []
    elif mutation == "drop_reservations":
        p["reservations"] = []
    elif mutation == "protocol":
        p["protocol"]["prior_observation_hash"] = "sha256:" + "0" * 64
    elif mutation == "study":
        p["study"]["cohort_manifest_hash"] = "sha256:" + "0" * 64
    else:
        p["diagnostics"]["predictions_identity"] = "0" * 64
    _rewrite_packet_manifest(root, p)
    with pytest.raises(inputs.InputError, match="REPLAY"):
        runner.replay(root)


def test_full_db_adapter_preserves_binary64_and_governed_flow(tmp_path):
    import json

    root = tmp_path / "db"
    packet = runner.run_fixture(root, source_format="duckdb")
    snapshot = json.loads((root / "snapshot.json").read_bytes())
    assert all(
        row["close"]["basis"] == "BINARY64_EXACT_NOT_PROVIDER_PRECISION"
        for row in snapshot["rows"]
    )
    assert packet["fit_calls"] == 1 and packet["real_source_reads"] == 0
    assert runner.replay(root) == (root / "report.md").read_text()


def test_content_conflict_after_open_keeps_its_read_debit(tmp_path):
    import os

    root = tmp_path / "owned"
    root.mkdir()
    budget = inputs.ArtifactBudget(root, read_bytes=5, write_bytes=100)
    descriptor = budget.write("value.json", b"good")
    path = root / "value.json"
    before = path.stat()
    path.write_bytes(b"evil")
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    with pytest.raises(inputs.InputError, match="CONTENT_CONFLICT"):
        budget.read(descriptor, lambda: None)
    assert budget.read_calls == 1 and budget.read_debit == 5
    with pytest.raises(inputs.InputError, match="INPUT_CAP"):
        budget.read(descriptor, lambda: None)


def test_early_input_budget_failure_is_partial_and_has_no_fit_attempt(
    tmp_path, monkeypatch
):
    import json

    original = inputs.ArtifactBudget

    def capped(root, *args, **kwargs):
        return original(root, read_bytes=1)

    monkeypatch.setattr(inputs, "ArtifactBudget", capped)
    root = tmp_path / "limited"
    with pytest.raises(inputs.InputError, match="INPUT_CAP"):
        runner.run_fixture(root)
    failure = json.loads((root / "failure.json").read_bytes())
    assert failure["fit_attempts_started"] == 0
    assert not (root / "output-manifest.json").exists()
    with pytest.raises(inputs.InputError, match="INCOMPLETE"):
        runner.replay(root)


def test_fixture_worker_refuses_without_actual_owned_resource_unit(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.delenv("RETRO_RESOURCE_UNIT", raising=False)
    target = tmp_path / "no-unit"
    assert runner.main(("--fixture-worker", "--output", str(target))) == 2
    assert not target.exists() and "RESOURCE_NOT_ENFORCED" in capsys.readouterr().err


@pytest.mark.parametrize("unit", (0, 1, True, [], {}))
def test_quantity_unit_type_is_never_coerced_to_missing_or_normal(unit):
    row = next(inputs.fixture_source_rows(inputs.fixture_calendar(weeks=1)))
    with pytest.raises(inputs.InputError, match="UNIT"):
        inputs.normalize_row({**row, "quantity_unit": unit})


def test_duckdb_cannot_read_an_aba_substituted_path(tmp_path, monkeypatch):
    root = tmp_path / "a"
    root.mkdir()
    other = tmp_path / "b"
    other.mkdir()
    a = inputs.ArtifactBudget(root)
    b = inputs.ArtifactBudget(other)
    descriptor = inputs.write_fixture_source(
        a, inputs.fixture_calendar(weeks=2), "duckdb"
    )
    inputs.write_fixture_source(b, inputs.fixture_calendar(weeks=1), "duckdb")
    original = inputs.open_database

    def substituted(path, *, read_only):
        if not read_only:
            return original(path, read_only=read_only)
        source = a.path("source.duckdb")
        evil = b.path("source.duckdb")
        saved = root / "saved.duckdb"
        source.rename(saved)
        evil.rename(source)
        try:
            return original(path, read_only=True)
        finally:
            source.rename(evil)
            saved.rename(source)

    monkeypatch.setattr(inputs, "open_database", substituted)
    rows = inputs.read_duckdb_rows(a, descriptor, lambda: None)
    assert len(rows) == 30  # Original immutable bytes, not the15-row replacement.


def test_replay_label_file_cannot_contradict_packet_with_a_new_manifest(
    tmp_path, frozen_output
):
    import json
    import shutil

    from experiments import a_share_price_volume_retro_v1 as core

    root = tmp_path / "bad-label"
    shutil.copytree(frozen_output, root)
    raw = core.canonical_bytes([])
    (root / "labels-DEVELOPMENT.json").write_bytes(raw)
    manifest = json.loads((root / "output-manifest.json").read_bytes())
    manifest["files"]["labels-DEVELOPMENT.json"] = {
        "bytes": len(raw),
        "sha256": inputs.digest(raw),
    }
    (root / "output-manifest.json").write_bytes(core.canonical_bytes(manifest))
    with pytest.raises(inputs.InputError, match="REPLAY"):
        runner.replay(root)


def test_governance_fifo_is_rejected_without_a_blocking_storage_read(
    tmp_path, frozen_output
):
    import json
    import os
    import shutil
    import subprocess
    import sys

    root = tmp_path / "fifo"
    shutil.copytree(frozen_output, root)
    p = json.loads((root / "packet.json").read_bytes())
    wanted = p["protocol_ref"]["content_hash"]
    blobs = [f for f in (root / "governance" / "artifacts").rglob("*") if f.is_file()]
    target = next(
        f for f in blobs if json.loads(f.read_bytes()).get("content_hash") == wanted
    )
    target.unlink()
    os.mkfifo(target, 0o600)
    result = subprocess.run(
        [sys.executable, "-B", "-m", runner.MODULE, "--replay", str(root)],
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
    )
    assert result.returncode == 2 and "REPLAY_METADATA_NONREGULAR" in result.stderr


def test_closed_natural_week_stays_null_through_the_same_full_adapter(
    tmp_path, monkeypatch
):
    original = inputs.fixture_calendar

    def holiday():
        return tuple(
            (day, False if date(2001, 1, 8) <= day < date(2001, 1, 15) else opened)
            for day, opened in original(weeks=130)
        )

    monkeypatch.setattr(inputs, "fixture_calendar", holiday)
    p = runner.run_fixture(tmp_path / "closed-week")
    weeks = [week for part in p["diagnostics"].partitions for week in part.weeks]
    target = next(week for week in weeks if week.slot.week == date(2001, 1, 8))
    assert (
        target.slot.decision_session is None
        and target.slot.mother_count == 0
        and target.delta is None
    )


def test_replay_stage_journal_cannot_be_rehashed_away(tmp_path, frozen_output):
    import json
    import shutil

    from experiments import a_share_price_volume_retro_v1 as core

    root = tmp_path / "journal"
    shutil.copytree(frozen_output, root)
    raw = b""
    (root / "execution-order.jsonl").write_bytes(raw)
    manifest = json.loads((root / "output-manifest.json").read_bytes())
    manifest["files"]["execution-order.jsonl"] = {
        "bytes": 0,
        "sha256": inputs.digest(raw),
    }
    (root / "output-manifest.json").write_bytes(core.canonical_bytes(manifest))
    with pytest.raises(inputs.InputError, match="JOURNAL"):
        runner.replay(root)


def test_nonfixture_schema_does_not_create_host_authority(tmp_path):
    from types import SimpleNamespace
    from typing import cast

    from crypto_quant_validation import RetrospectiveReservationReceipt

    root = tmp_path / "denied"
    root.mkdir()
    budget = inputs.ArtifactBudget(root)
    reader = inputs.SnapshotReader(
        budget,
        {"origin": inputs.FROZEN_CAPTURE_ORIGIN},
        SimpleNamespace(fixture_only=False),
    )

    def deny():
        raise inputs.InputError("HOST_PERMISSION_DENIED")

    admission = inputs.ReadAdmission(
        "TRAIN_FEATURE", cast(RetrospectiveReservationReceipt, None), None, deny
    )
    with pytest.raises(inputs.InputError, match="HOST_PERMISSION_DENIED"):
        reader.views(admission, SimpleNamespace(partition="TRAIN"))
    assert reader.open_calls == budget.read_calls == 0


def test_manifest_memory_mutation_cannot_detach_it_from_owned_task_hash(
    tmp_path, monkeypatch
):
    original = inputs.SnapshotReader.__init__
    readers = []

    def changed(self, *args, **kwargs):
        original(self, *args, **kwargs)
        self.manifest["captured_at"] = "2026-01-01T00:00:00.000000Z"
        readers.append(self)

    monkeypatch.setattr(inputs.SnapshotReader, "__init__", changed)
    with pytest.raises(inputs.InputError, match="INPUT_MANIFEST_BINDING"):
        runner.run_fixture(tmp_path / "manifest-memory")
    assert readers and readers[0].open_calls == 0


def test_clock_failure_before_fit_does_not_claim_a_core_fit_attempt(
    tmp_path, monkeypatch
):
    import json

    from experiments import a_share_price_volume_retro_v1 as core

    original = core.make_retrospective_labels
    broken = False

    def labels(*args, **kwargs):
        nonlocal broken
        result = original(*args, **kwargs)
        broken = True
        return result

    def clock():
        if broken:
            raise inputs.InputError("CLOCK_UNAVAILABLE")
        return runner.now()

    def no_fit(*args, **kwargs):
        raise AssertionError("Core fit must not be entered")

    monkeypatch.setattr(core, "make_retrospective_labels", labels)
    monkeypatch.setattr(core, "fit_retrospective_models", no_fit)
    root = tmp_path / "clock"
    with pytest.raises(inputs.InputError, match="CLOCK_UNAVAILABLE"):
        runner.run_fixture(root, clock=clock)
    failure = json.loads((root / "failure.json").read_bytes())
    assert failure["fit_attempts_started"] == 0 and failure["execution_order"]
    assert not (root / "model-cards.json").exists()


def _catalog_admission(tmp_path, source, *, before_bind=None):
    from crypto_quant_foundation import LocalFoundation
    from crypto_quant_research import (
        RetrospectiveReadTask,
        RetrospectiveStudyProtocol,
        publish_retrospective_protocol,
        publish_retrospective_read_task,
    )
    from crypto_quant_validation import (
        SampleConsumptionLedger,
        reserve_retrospective_read,
    )

    f = LocalFoundation(tmp_path / "catalog-governance")
    ledger = SampleConsumptionLedger(f)
    h = "sha256:" + "1" * 64
    p = RetrospectiveStudyProtocol(
        "SYNTHETIC-CATALOG-ADAPTER-TEST-ONLY",
        h,
        h,
        h,
        inputs.catalog_scope_hash(source),
        h,
        (
            (
                "catalog-only",
                "2000-01-01T00:00:00.000000Z",
                "2000-01-02T00:00:00.000000Z",
            ),
        ),
    )
    pp = publish_retrospective_protocol(p, f)
    task = RetrospectiveReadTask(pp.ref, "INPUT_QUALIFICATION", p.source_slices[0])
    tp = publish_retrospective_read_task(task, f)
    consumed = f.checkpoint("validation.sample-consumption.v1").as_of
    receipt = reserve_retrospective_read(
        f, ledger, pp.publication, tp.publication, consumed
    )

    assert receipt.record.consumed_at == consumed
    if before_bind is not None:
        before_bind(f, tmp_path / "catalog-governance")
    policy = lambda: None  # Trusted synthetic-fixture policy only.
    account = runner.CatalogGovernanceBudget(
        tmp_path / "catalog-account",
        source_path=source,
        governance_root=tmp_path / "catalog-governance",
        runtime_authorize=policy,
    )
    return runner.bind_catalog_admission(
        source,
        governance_root=tmp_path / "catalog-governance",
        protocol_publication=pp,
        task_publication=tp,
        source_slice=p.source_slices[0],
        reservation=receipt,
        io_budget=account,
        runtime_authorize=policy,
    )


def test_catalog_denial_is_before_source_stat_or_owned_output(tmp_path, monkeypatch):
    from typing import cast

    from crypto_quant_validation import RetrospectiveReservationReceipt

    def denied():
        raise inputs.InputError("HOST_PERMISSION_DENIED")

    a = inputs.ReadAdmission(
        "INPUT_QUALIFICATION", cast(RetrospectiveReservationReceipt, None), None, denied
    )
    target = tmp_path / "no-output"
    with pytest.raises(inputs.InputError, match="HOST_PERMISSION_DENIED"):
        runner.run_source_catalog_probe(
            target, source_path=tmp_path / "not-opened.duckdb", admission=a
        )
    assert not target.exists()


def test_catalog_actual_guarded_module_on_fixture_only(tmp_path, monkeypatch):
    import json

    source = tmp_path / "fixture.duckdb"
    c = inputs.open_database(source, read_only=False)
    c.execute("CREATE TABLE CalendarFixture(cal_date DATE,is_open BOOLEAN)")
    c.close()
    a = _catalog_admission(tmp_path, source)
    monkeypatch.setattr(
        inputs,
        "catalog_resource_evidence",
        lambda: {
            "memory_max": 6 * 1024**3,
            "basis": "SYNTHETIC_RESOURCE_FIXTURE_NOT_HARD_CAP",
        },
    )
    target = tmp_path / "capture"
    result = runner.run_source_catalog_probe(target, source_path=source, admission=a)
    assert result["state"] == "CATALOG_OBSERVED_NOT_SOURCE_QUALIFIED"
    assert len(result["columns"]) == 2 and result["source_qualified"] is False
    close = json.loads((target / "catalog-close.json").read_bytes())
    assert close["state"] == "COMPLETE" and close["sql_attempts"] == 4
    assert close["connection_closed"] and close["fd_closed"]
    assert close["close_bytes_reserved"] == 128 * 1024


def _catalog_fixture(
    tmp_path,
    monkeypatch,
    ddl="CREATE TABLE CalendarFixture(cal_date DATE,is_open BOOLEAN)",
):
    source = tmp_path / "fixture.duckdb"
    c = inputs.open_database(source, read_only=False)
    try:
        c.execute(ddl)
    finally:
        c.close()
    a = _catalog_admission(tmp_path, source)
    monkeypatch.setattr(
        inputs,
        "catalog_resource_evidence",
        lambda: {"memory_max": 6 * 1024**3, "basis": "SYNTHETIC_NOT_HARD_CAPPED"},
    )
    return source, a


@pytest.mark.parametrize("failure", ("phase", "scope", "receipt"))
def test_catalog_bad_binding_precedes_source_lstat(tmp_path, monkeypatch, failure):
    from dataclasses import replace

    source, a = _catalog_fixture(tmp_path, monkeypatch)
    if failure == "phase":
        a = replace(a, phase="TRAIN_FEATURE")
    elif failure == "scope":
        a = replace(
            a,
            source_slice=replace(
                a.source_slice, source_scope_hash="sha256:" + "f" * 64
            ),
        )
    else:
        a = replace(a, receipt=replace(a.receipt, purpose="validation"))

    def forbidden(*args, **kwargs):
        raise AssertionError("source metadata before admission")

    monkeypatch.setattr(inputs.os, "lstat", forbidden)
    with pytest.raises(inputs.InputError, match="CATALOG_"):
        runner.run_source_catalog_probe(
            tmp_path / "out", source_path=source, admission=a
        )


@pytest.mark.parametrize("kind", ("wal", "symlink", "fifo"))
def test_catalog_nonregular_or_wal_has_zero_native_connections(
    tmp_path, monkeypatch, kind
):
    import json
    import os

    source, a = _catalog_fixture(tmp_path, monkeypatch)
    if kind == "wal":
        Path = type(source)
        Path(str(source) + ".wal").write_bytes(b"SYNTHETIC_PRESENCE_ONLY")
    else:
        moved = source.with_name("saved.duckdb")
        source.rename(moved)
        if kind == "symlink":
            source.symlink_to(moved)
        else:
            os.mkfifo(source)

    def forbidden(*args, **kwargs):
        raise AssertionError("must not open native connection")

    monkeypatch.setattr(inputs, "open_database", forbidden)
    out = tmp_path / "out"
    with pytest.raises(inputs.InputError, match="CATALOG_"):
        runner.run_source_catalog_probe(out, source_path=source, admission=a)
    close = json.loads((out / "catalog-close.json").read_bytes())
    assert close["state"] == "FAILED" and close["connection_attempts"] == 0
    assert close["connection_closed"] and close["fd_closed"]
    assert close["close_bytes_reserved"] == 128 * 1024


def test_catalog_path_aba_reads_pinned_fd_then_rejects_name_change(
    tmp_path, monkeypatch
):
    import json
    import os

    source, a = _catalog_fixture(tmp_path, monkeypatch)
    other = tmp_path / "other.duckdb"
    original = inputs.open_database
    c = original(other, read_only=False)
    c.execute("CREATE TABLE WrongFixture(is_open BOOLEAN)")
    c.close()
    seen = []

    def swapped(path, *, read_only):
        os.replace(source, tmp_path / "old.duckdb")
        os.replace(other, source)
        c = original(path, read_only=read_only)
        seen.extend(c.execute(inputs.CATALOG_SQL).fetchall())
        return c

    monkeypatch.setattr(inputs, "open_database", swapped)
    out = tmp_path / "out"
    with pytest.raises(inputs.InputError, match="SOURCE_CHANGED"):
        runner.run_source_catalog_probe(out, source_path=source, admission=a)
    assert {row[0] for row in seen} == {"CalendarFixture"}
    close = json.loads((out / "catalog-close.json").read_bytes())
    assert (
        close["sql_attempts"] == 4 and close["connection_closed"] and close["fd_closed"]
    )
    assert not (out / "catalog-columns.json").exists()


@pytest.mark.parametrize("fault", ("commit", "close"))
def test_catalog_native_failure_retains_attempts_and_closes_fd(
    tmp_path, monkeypatch, fault
):
    import json
    import os

    source, a = _catalog_fixture(tmp_path, monkeypatch)
    original = inputs.open_database
    captured = []

    class Connection:
        def __init__(self, c):
            self.c = c

        def execute(self, sql):
            if sql == "COMMIT" and fault == "commit":
                raise RuntimeError("SYNTHETIC_FAIL_NOT_PRINTED")
            return self.c.execute(sql)

        def close(self):
            self.c.close()
            if fault == "close":
                raise RuntimeError("SYNTHETIC_CLOSE_UNKNOWN")

    def faulty(path, *, read_only):
        captured.append(int(path.name))
        return Connection(original(path, read_only=read_only))

    monkeypatch.setattr(inputs, "open_database", faulty)
    out = tmp_path / "out"
    with pytest.raises(inputs.InputError, match="CATALOG_"):
        runner.run_source_catalog_probe(out, source_path=source, admission=a)
    close = json.loads((out / "catalog-close.json").read_bytes())
    assert close["state"] == "FAILED" and close["fd_closed"]
    assert close["sql_attempts"] == (5 if fault == "commit" else 4)
    assert close["connection_closed"] is (fault != "close")
    assert "SYNTHETIC_FAIL" not in (out / "catalog-close.json").read_text()
    with pytest.raises(OSError):
        os.fstat(captured[0])
    assert not (out / "catalog-columns.json").exists()
    with pytest.raises(inputs.InputError, match="OUTPUT_CONFLICT"):
        runner.run_source_catalog_probe(out, source_path=source, admission=a)


def test_catalog_output_cap_is_checked_before_any_source_call(tmp_path, monkeypatch):
    source, a = _catalog_fixture(tmp_path, monkeypatch)
    out = tmp_path / "out"
    out.mkdir()
    b = inputs.ArtifactBudget(out, write_bytes=inputs.CATALOG_WRITER_BYTES - 1)

    def forbidden(*args, **kwargs):
        raise AssertionError("source metadata")

    monkeypatch.setattr(inputs.os, "lstat", forbidden)
    with pytest.raises(inputs.InputError, match="OUTPUT_CAP"):
        inputs.inspect_lake_catalog(source, b, a)
    assert b.write_debit == 0


def test_catalog_no_admission_and_no_actual_worker_do_not_create_output(
    tmp_path, monkeypatch
):
    from experiments.a_share_price_volume_retro_resources_v1 import RetroResourceError

    out = tmp_path / "out"
    with pytest.raises(inputs.InputError, match="REAL_INPUT_NOT_ADMITTED"):
        runner.run_source_catalog_probe(out, source_path=tmp_path / "absent.duckdb")
    source, a = _catalog_fixture(tmp_path, monkeypatch)
    monkeypatch.undo()
    monkeypatch.delenv("RETRO_RESOURCE_UNIT", raising=False)
    with pytest.raises(
        (inputs.InputError, RetroResourceError), match="RESOURCE_NOT_ENFORCED"
    ):
        runner.run_source_catalog_probe(out, source_path=source, admission=a)
    assert not out.exists()


def test_catalog_row_cap_on_same_guarded_module(tmp_path, monkeypatch):
    import json

    source, a = _catalog_fixture(
        tmp_path, monkeypatch, "CREATE TABLE UnrelatedFixture(n INTEGER)"
    )
    c = inputs.open_database(source, read_only=False)
    try:
        for i in range(257):
            c.execute(f"CREATE TABLE Fixture{i:03d}(is_open BOOLEAN)")
    finally:
        c.close()
    out = tmp_path / "out"
    with pytest.raises(inputs.InputError, match="ROW_CAP"):
        runner.run_source_catalog_probe(out, source_path=source, admission=a)
    close = json.loads((out / "catalog-close.json").read_bytes())
    assert close["sql_attempts"] == 4 and close["state"] == "FAILED"
    assert close["connection_closed"] and close["fd_closed"]


def test_catalog_metadata_only_does_not_call_any_math(tmp_path, monkeypatch):
    from experiments import a_share_price_volume_retro_v1 as core

    source, a = _catalog_fixture(
        tmp_path, monkeypatch, "CREATE TABLE UnrelatedFixture(n INTEGER)"
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("no fit/feature/label/predict/score")

    for name in (
        "make_retrospective_features",
        "make_retrospective_labels",
        "fit_retrospective_models",
        "predict_retrospective_models",
        "evaluate_retrospective_predictions",
    ):
        monkeypatch.setattr(core, name, forbidden)
    result = runner.run_source_catalog_probe(
        tmp_path / "out", source_path=source, admission=a
    )
    assert result["columns"] == () and result["source_qualified"] is False


@pytest.mark.parametrize("bad", ("text", "bool-index", "int-nullable", "bytes"))
def test_catalog_result_shape_and_byte_caps_on_actual_seam(tmp_path, monkeypatch, bad):
    import json

    source, a = _catalog_fixture(tmp_path, monkeypatch)
    original = inputs.open_database
    rows = (
        [("A" * 129, "is_open", "BOOLEAN", 1, True)]
        if bad == "text"
        else [("Fixture", "is_open", "BOOLEAN", True, True)]
        if bad == "bool-index"
        else [("Fixture", "is_open", "BOOLEAN", 1, 1)]
        if bad == "int-nullable"
        else [("\U0001f642" * 128, "\U0001f642" * 128, "\U0001f642" * 128, 1, True)]
        * 256
    )

    class Cursor:
        def fetchall(self):
            return rows

    class Connection:
        def __init__(self, c):
            self.c = c

        def execute(self, sql):
            return Cursor() if sql == inputs.CATALOG_SQL else self.c.execute(sql)

        def close(self):
            self.c.close()

    monkeypatch.setattr(
        inputs,
        "open_database",
        lambda path, *, read_only: Connection(original(path, read_only=read_only)),
    )
    out = tmp_path / "out"
    with pytest.raises(inputs.InputError, match="RESULT_"):
        runner.run_source_catalog_probe(out, source_path=source, admission=a)
    close = json.loads((out / "catalog-close.json").read_bytes())
    assert close["state"] == "FAILED" and close["sql_attempts"] == 4
    assert close["connection_closed"] and close["fd_closed"]


def test_catalog_permission_expiry_after_connect_preserves_partial(
    tmp_path, monkeypatch
):
    import json
    from dataclasses import replace

    source, a = _catalog_fixture(tmp_path, monkeypatch)
    original = inputs.open_database
    connected = False
    authorize = a.authorize

    def open_db(path, *, read_only):
        nonlocal connected
        c = original(path, read_only=read_only)
        connected = True
        return c

    def expiring():
        if connected:
            raise inputs.InputError("HOST_PERMISSION_EXPIRED")
        authorize()

    monkeypatch.setattr(inputs, "open_database", open_db)
    out = tmp_path / "out"
    with pytest.raises(inputs.InputError, match="HOST_PERMISSION_EXPIRED"):
        runner.run_source_catalog_probe(
            out, source_path=source, admission=replace(a, authorize=expiring)
        )
    close = json.loads((out / "catalog-close.json").read_bytes())
    assert (
        close["source_open_attempts"]
        == close["connection_attempts"]
        == close["sql_attempts"]
        == 1
    )
    assert (
        close["state"] == "FAILED" and close["connection_closed"] and close["fd_closed"]
    )


def test_catalog_result_write_failure_keeps_reserved_close_and_no_success(
    tmp_path, monkeypatch
):
    import json

    source, a = _catalog_fixture(tmp_path, monkeypatch)
    original = inputs.ArtifactBudget.write

    def failed(self, name, raw):
        if name == "catalog-columns.json":
            raise OSError("SYNTHETIC_DISK_FAILURE")
        return original(self, name, raw)

    monkeypatch.setattr(inputs.ArtifactBudget, "write", failed)
    out = tmp_path / "out"
    with pytest.raises(inputs.InputError, match="OUTPUT_FAILED"):
        runner.run_source_catalog_probe(out, source_path=source, admission=a)
    close = json.loads((out / "catalog-close.json").read_bytes())
    assert (
        close["state"] == "FAILED"
        and close["close_bytes_reserved"] == inputs.CATALOG_CLOSE_BYTES
    )
    assert close["writer_bytes_debited"] >= inputs.CATALOG_CLOSE_BYTES
    assert close["connection_closed"] and close["fd_closed"]


def test_catalog_revocation_after_begin_never_executes_select(tmp_path, monkeypatch):
    import json
    from dataclasses import replace

    source, a = _catalog_fixture(tmp_path, monkeypatch)
    original = inputs.open_database
    revoked = False
    selected = []
    authorize = a.authorize

    class Connection:
        def __init__(self, c):
            self.c = c

        def execute(self, sql):
            nonlocal revoked
            if sql == inputs.CATALOG_SQL:
                selected.append(sql)
            result = self.c.execute(sql)
            if sql == "BEGIN TRANSACTION":
                revoked = True
            return result

        def close(self):
            self.c.close()

    def check():
        if revoked:
            raise inputs.InputError("HOST_PERMISSION_REVOKED")
        authorize()

    monkeypatch.setattr(
        inputs,
        "open_database",
        lambda path, *, read_only: Connection(original(path, read_only=read_only)),
    )
    out = tmp_path / "out"
    with pytest.raises(inputs.InputError, match="HOST_PERMISSION_REVOKED"):
        runner.run_source_catalog_probe(
            out, source_path=source, admission=replace(a, authorize=check)
        )
    assert selected == []
    close = json.loads((out / "catalog-close.json").read_bytes())
    assert (
        close["state"] == "FAILED" and close["connection_closed"] and close["fd_closed"]
    )


def test_catalog_forged_slice_cannot_retarget_an_original_public_reservation(
    tmp_path, monkeypatch
):
    from dataclasses import replace

    _source, a = _catalog_fixture(tmp_path, monkeypatch)
    other = tmp_path / "other.duckdb"
    c = inputs.open_database(other, read_only=False)
    c.execute("CREATE TABLE OtherFixture(is_open BOOLEAN)")
    c.close()
    forged = replace(
        a,
        source_slice=replace(
            a.source_slice, source_scope_hash=inputs.catalog_scope_hash(other)
        ),
    )
    with pytest.raises(inputs.InputError, match="CATALOG_"):
        runner.run_source_catalog_probe(
            tmp_path / "out", source_path=other, admission=forged
        )


@pytest.mark.parametrize("where", ("select", "rollback", "close"))
def test_catalog_interrupt_keeps_terminal_facts_and_fd_cleanup(
    tmp_path, monkeypatch, where
):
    import json
    import os

    source, a = _catalog_fixture(tmp_path, monkeypatch)
    original = inputs.open_database
    captured = []

    class Connection:
        def __init__(self, c):
            self.c = c

        def execute(self, sql):
            if sql == inputs.CATALOG_SQL:
                if where == "select":
                    raise KeyboardInterrupt()
                if where == "rollback":
                    raise RuntimeError("SYNTHETIC_TRIGGER_ROLLBACK")
            if sql == "ROLLBACK" and where == "rollback":
                raise KeyboardInterrupt()
            return self.c.execute(sql)

        def close(self):
            self.c.close()
            if where == "close":
                raise KeyboardInterrupt()

    def connected(path, *, read_only):
        captured.append(int(path.name))
        return Connection(original(path, read_only=read_only))

    monkeypatch.setattr(inputs, "open_database", connected)
    out = tmp_path / "out"
    with pytest.raises(KeyboardInterrupt):
        runner.run_source_catalog_probe(out, source_path=source, admission=a)
    close = json.loads((out / "catalog-close.json").read_bytes())
    assert close["state"] == "FAILED" and close["fd_closed"]
    assert close["connection_closed"] is (where != "close")
    assert not (out / "catalog-columns.json").exists()
    with pytest.raises(OSError):
        os.fstat(captured[0])


def test_catalog_root_governance_rechecks_are_bounded_without_refreshed_record(
    tmp_path, monkeypatch
):
    import json

    _source, a = _catalog_fixture(tmp_path, monkeypatch)
    original = a.receipt.record
    for _ in range(32):
        a.authorize()
    with pytest.raises(inputs.InputError, match="RECHECK_CAP"):
        a.authorize()
    assert a.receipt.record == original
    files = [p for p in (tmp_path / "catalog-governance").rglob("*") if p.is_file()]
    # An observed bounded fixture, not a global Foundation disk quota.
    assert sum(p.stat().st_size for p in files) < 1024**2
    from crypto_quant_foundation import LocalFoundation

    f = LocalFoundation(tmp_path / "catalog-governance")
    entries = f.entries("validation.sample-consumption.v1")
    assert len(entries) == 1
    assert (
        json.loads(entries[0].payload)["payload"]["record"]["consumed_at"]
        == original.consumed_at
    )


def test_catalog_root_binding_requires_host_policy_before_any_governance_access(
    tmp_path, monkeypatch
):
    from typing import Any, cast

    def forbidden(*args, **kwargs):
        raise AssertionError("no governance access without host policy")

    monkeypatch.setattr(runner, "_copy_catalog_governance", forbidden)
    with pytest.raises(inputs.InputError, match="REAL_INPUT_NOT_ADMITTED"):
        runner.bind_catalog_admission(
            tmp_path / "not-read.duckdb",
            governance_root=tmp_path / "not-created",
            protocol_publication=cast(Any, None),
            task_publication=cast(Any, None),
            source_slice=cast(Any, None),
            reservation=cast(Any, None),
        )
    assert not (tmp_path / "not-created").exists()


@pytest.mark.parametrize("stop", (KeyboardInterrupt, SystemExit))
@pytest.mark.parametrize("cleanup", ("rollback", "close", "close-record"))
def test_catalog_original_interrupt_is_not_swallowed_by_later_cleanup_error(
    tmp_path, monkeypatch, cleanup, stop
):
    import json

    source, a = _catalog_fixture(tmp_path, monkeypatch)
    original = inputs.open_database

    class Connection:
        def __init__(self, c):
            self.c = c

        def execute(self, sql):
            if sql == inputs.CATALOG_SQL:
                raise stop("SYNTHETIC_ORIGINAL_INTERRUPT")
            if sql == "ROLLBACK" and cleanup == "rollback":
                raise RuntimeError("SYNTHETIC_SECOND_ERROR")
            return self.c.execute(sql)

        def close(self):
            self.c.close()
            if cleanup == "close":
                raise RuntimeError("SYNTHETIC_SECOND_ERROR")

    monkeypatch.setattr(
        inputs,
        "open_database",
        lambda path, *, read_only: Connection(original(path, read_only=read_only)),
    )
    if cleanup == "close-record":
        original_open = type(source).open

        def failing_open(path, *args, **kwargs):
            if path.name == "catalog-close.json":
                raise OSError("SYNTHETIC_SECOND_ERROR")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(type(source), "open", failing_open)
    out = tmp_path / "out"
    with pytest.raises(stop, match="SYNTHETIC_ORIGINAL_INTERRUPT"):
        runner.run_source_catalog_probe(out, source_path=source, admission=a)
    if cleanup != "close-record":
        value = json.loads((out / "catalog-close.json").read_bytes())
        assert value["state"] == "FAILED" and value["fd_closed"]
        assert value["interruption_type"] == stop.__name__


def test_catalog_governance_rechecks_leave_original_store_byte_and_mtime_identical(
    tmp_path, monkeypatch
):
    _source, a = _catalog_fixture(tmp_path, monkeypatch)
    gov = tmp_path / "catalog-governance"
    before = {
        p.relative_to(gov).as_posix(): (p.stat().st_mtime_ns, p.read_bytes())
        for p in gov.rglob("*")
        if p.is_file()
    }
    for _ in range(4):
        a.authorize()
    after = {
        p.relative_to(gov).as_posix(): (p.stat().st_mtime_ns, p.read_bytes())
        for p in gov.rglob("*")
        if p.is_file()
    }
    assert after == before


@pytest.mark.parametrize("bad", ("bytes", "nodes", "fifo", "link", "partial"))
def test_catalog_governance_snapshot_rejects_unbounded_or_nonregular_input(
    tmp_path, monkeypatch, bad
):
    import os

    source = tmp_path / "NEVER_CREATED.duckdb"

    def corrupted(_f, gov):
        if bad == "bytes":
            target = gov / "artifacts" / "sha256" / "aa"
            target.mkdir(exist_ok=True)
            (target / ("a" * 64)).write_bytes(
                b"X" * (runner.CATALOG_GOVERNANCE_SOURCE_BYTES + 1)
            )
        elif bad == "nodes":
            for n in range(129):
                (gov / "artifacts" / f"fixture{n}").mkdir()
        elif bad == "partial":
            (gov / ".staging" / "partial").write_bytes(b"SYNTHETIC_PARTIAL")
        else:
            target = gov / "artifacts" / "sha256" / "ab"
            target.mkdir(exist_ok=True)
            p = target / ("b" * 64)
            if bad == "fifo":
                os.mkfifo(p)
            else:
                p.symlink_to(tmp_path / "not-followed")

    with pytest.raises(inputs.InputError, match="CATALOG_GOVERNANCE_"):
        _catalog_admission(tmp_path, source, before_bind=corrupted)
    assert not source.exists()


def test_catalog_governance_snapshot_does_not_repair_missing_original_append(tmp_path):
    source = tmp_path / "NEVER_CREATED.duckdb"

    def missing(_f, gov):
        (gov / "registries" / "validation.sample-consumption.v1.jsonl").unlink()

    with pytest.raises(ValueError):
        _catalog_admission(tmp_path, source, before_bind=missing)
    assert not (
        tmp_path
        / "catalog-governance"
        / "registries"
        / "validation.sample-consumption.v1.jsonl"
    ).exists()
    assert not source.exists()


def test_catalog_governance_total_content_and_private_peak_budget_are_explicit(
    tmp_path, monkeypatch
):
    source, a = _catalog_fixture(tmp_path, monkeypatch)
    evidence = a.catalog_governance
    assert evidence is not None
    assert evidence["source_content_bytes"] <= 256 * 1024
    assert evidence["source_content_read_debit"] <= 256 * 1024 + 128
    assert evidence["private_clock_calls"] <= 8
    assert evidence["private_peak_content_upper_bound"] <= 768 * 1024
    assert evidence["total_retained_and_temporary_reserve"] == 1024**2
    assert (
        256 * 1024 + 640 * 1024 + 128 * 1024 + inputs.CATALOG_WRITER_BYTES + 256 * 1024
        == 2 * 1024**2
    )
    gov = tmp_path / "catalog-governance"
    before = {
        p.relative_to(gov).as_posix(): (p.stat().st_mtime_ns, p.read_bytes())
        for p in gov.rglob("*")
        if p.is_file()
    }
    result = runner.run_source_catalog_probe(
        tmp_path / "out", source_path=source, admission=a
    )
    after = {
        p.relative_to(gov).as_posix(): (p.stat().st_mtime_ns, p.read_bytes())
        for p in gov.rglob("*")
        if p.is_file()
    }
    assert after == before and result["source_qualified"] is False


def test_catalog_governance_near_cap_observes_private_clock_staging_and_cleanup(
    tmp_path, monkeypatch
):
    import os
    from pathlib import Path

    from crypto_quant_domain import ArtifactEnvelope

    peaks = []
    copies = []
    original_replace = os.replace

    def observed_replace(src, dst, *args, **kwargs):
        private = Path(src).parent.parent
        if private.name.startswith("retro-catalog-proof-"):
            copies.append(private)
            peaks.append(
                sum(p.stat().st_size for p in private.rglob("*") if p.is_file())
            )
        return original_replace(src, dst, *args, **kwargs)

    monkeypatch.setattr(os, "replace", observed_replace)

    def padded(f, _gov):
        f.put(
            envelope=ArtifactEnvelope.create(
                "synthetic_unpublished_padding", 1, {"text": "X" * 230000}
            )
        )

    a = _catalog_admission(
        tmp_path, tmp_path / "NEVER_CREATED.duckdb", before_bind=padded
    )
    evidence = a.catalog_governance
    assert evidence is not None
    assert 230000 < evidence["source_content_bytes"] <= 256 * 1024
    assert (
        peaks
        and max(peaks) <= evidence["private_peak_content_upper_bound"] <= 768 * 1024
    )
    assert all(not p.exists() for p in copies)
    assert not (tmp_path / "NEVER_CREATED.duckdb").exists()


def test_catalog_issuer_requires_host_policy_before_governance_io(tmp_path):
    from typing import Any, cast

    with pytest.raises(inputs.InputError, match="REAL_INPUT_NOT_ADMITTED"):
        runner.issue_catalog_admission(
            tmp_path / "NEVER_CREATED.duckdb",
            governance_root=tmp_path / "gov",
            budget_root=tmp_path / "account",
            protocol=cast(Any, None),
            source_slice=cast(Any, None),
        )
    assert not (tmp_path / "gov").exists() and not (tmp_path / "account").exists()


def _catalog_issuer_case(tmp_path):
    from crypto_quant_research import RetrospectiveStudyProtocol

    source = tmp_path / "NEVER_CREATED.duckdb"
    h = "sha256:" + "1" * 64
    protocol = RetrospectiveStudyProtocol(
        "SYNTHETIC-CATALOG-ISSUER-ONLY",
        h,
        h,
        h,
        inputs.catalog_scope_hash(source),
        h,
        (
            (
                "catalog-only",
                "2000-01-01T00:00:00.000000Z",
                "2000-01-02T00:00:00.000000Z",
            ),
        ),
    )

    def policy():
        pass  # Trusted fixture policy only; no real source authority.

    return source, protocol, policy


def test_catalog_actual_public_issuer_and_verifier_use_one_bounded_account(
    tmp_path, monkeypatch
):
    import json

    from crypto_quant_foundation import LocalFoundation

    source, protocol, policy = _catalog_issuer_case(tmp_path)
    calls = []
    current = ["NONE"]
    original_program = runner.CatalogGovernanceBudget.reserve_program

    def program(self, name):
        original_program(self, name)
        current[0] = name

    monkeypatch.setattr(runner.CatalogGovernanceBudget, "reserve_program", program)
    for name in ("put", "read", "append", "entries", "checkpoint"):
        original = getattr(LocalFoundation, name)

        def spy(self, *args, _name=name, _original=original, **kwargs):
            assert type(self) is LocalFoundation
            calls.append((current[0], _name))
            return _original(self, *args, **kwargs)

        monkeypatch.setattr(LocalFoundation, name, spy)
    a = runner.issue_catalog_admission(
        source,
        governance_root=tmp_path / "gov",
        budget_root=tmp_path / "account",
        protocol=protocol,
        source_slice=protocol.source_slices[0],
        runtime_authorize=policy,
    )
    assert not source.exists()
    assert 0 < sum(p == "ISSUE" for p, _ in calls) <= 64
    assert 0 < sum(p == "VERIFY" for p, _ in calls) <= 64
    assert a.catalog_governance is not None
    account = a.catalog_governance["io_account"]
    assert account["programs"] == ["ISSUE", "VERIFY"]
    assert account["sdk_calls_reserved"] == 128
    assert account["read_upper_debit"] <= account["read_limit"]
    assert account["write_upper_debit"] <= account["write_limit"]
    assert account["closed"] and account["close_verified"] and not account["poisoned"]
    assert a.receipt.record.purpose == "discovery"
    assert a.receipt.record.consumed_at
    for _ in range(4):
        a.authorize()
    close = json.loads((tmp_path / "account" / "close.json").read_text())
    assert close["state"] == "VERIFIED_NOT_SOURCE_QUALIFIED"


def test_catalog_program_budget_denies_before_sdk_and_does_not_refund(tmp_path):
    source, _p, policy = _catalog_issuer_case(tmp_path)
    io = runner.CatalogGovernanceBudget(
        tmp_path / "account",
        source_path=source,
        governance_root=tmp_path / "gov",
        runtime_authorize=policy,
        read_limit=1,
    )
    with pytest.raises(inputs.InputError, match="CATALOG_GOVERNANCE_IO_CAP"):
        io.reserve_program("ISSUE")
    assert (
        io.read_debit == 0 and io.write_debit == runner.CATALOG_GOVERNANCE_ACCOUNT_BYTES
    )
    assert io.poisoned and io.programs == {"ISSUE"} and not source.exists()
    assert io.close("FAILED_NO_SOURCE")
    with pytest.raises(inputs.InputError, match="CATALOG_GOVERNANCE_ACCOUNT_EXISTS"):
        runner.CatalogGovernanceBudget(
            tmp_path / "account",
            source_path=source,
            governance_root=tmp_path / "gov",
            runtime_authorize=policy,
        )


@pytest.mark.parametrize("cost", [-1, True, 0.5])
def test_catalog_program_budget_rejects_non_natural_debits(tmp_path, cost):
    source, _p, policy = _catalog_issuer_case(tmp_path)
    io = runner.CatalogGovernanceBudget(
        tmp_path / "account",
        source_path=source,
        governance_root=tmp_path / "gov",
        runtime_authorize=policy,
    )
    before = io.summary()
    with pytest.raises(inputs.InputError, match="CATALOG_GOVERNANCE_DEBIT_INVALID"):
        io.reserve("TEST", read=cost)
    assert io.summary() == before
    assert io.close("TEST_FINISHED")


def test_catalog_program_and_binding_cannot_be_reused(tmp_path):
    source, _p, policy = _catalog_issuer_case(tmp_path)
    io = runner.CatalogGovernanceBudget(
        tmp_path / "account",
        source_path=source,
        governance_root=tmp_path / "gov",
        runtime_authorize=policy,
    )
    io.reserve_program("VERIFY")
    io.begin_binding(source, tmp_path / "gov", policy)
    before = io.summary()
    with pytest.raises(inputs.InputError, match="CATALOG_GOVERNANCE_PROGRAM_REUSE"):
        io.reserve_program("VERIFY")
    with pytest.raises(
        inputs.InputError, match="CATALOG_GOVERNANCE_BIND_ALREADY_ATTEMPTED"
    ):
        io.begin_binding(source, tmp_path / "gov", policy)
    assert io.summary() == before
    assert io.close("TEST_FINISHED")


def test_catalog_code_pin_failure_preserves_partial_account_without_namespace(
    tmp_path, monkeypatch
):
    import json

    source, protocol, policy = _catalog_issuer_case(tmp_path)
    pins = dict(runner.CATALOG_GOVERNANCE_CODE_PINS)
    pins[next(iter(pins))] = "0" * 64
    monkeypatch.setattr(runner, "CATALOG_GOVERNANCE_CODE_PINS", pins)
    with pytest.raises(inputs.InputError, match="CATALOG_GOVERNANCE_CODE_PIN"):
        runner.issue_catalog_admission(
            source,
            governance_root=tmp_path / "gov",
            budget_root=tmp_path / "account",
            protocol=protocol,
            source_slice=protocol.source_slices[0],
            runtime_authorize=policy,
        )
    assert not source.exists() and not (tmp_path / "gov").exists()
    close = json.loads((tmp_path / "account" / "close.json").read_text())
    assert close["state"] == "ISSUANCE_FAILED_OR_INTERRUPTED"
    assert (
        close["read_upper_debit"] == 64 * 1024 + 1 and close["sdk_calls_reserved"] == 0
    )


@pytest.mark.parametrize("signal", [KeyboardInterrupt, SystemExit])
def test_catalog_issuer_close_error_cannot_swallow_original_stop(
    tmp_path, monkeypatch, signal
):
    source, protocol, policy = _catalog_issuer_case(tmp_path)
    stop = signal("ORIGINAL_STOP")

    def interrupted(*args, **kwargs):
        raise stop

    def failed_close(*args, **kwargs):
        raise OSError("SECONDARY_CLOSE")

    monkeypatch.setattr(runner, "publish_retrospective_protocol", interrupted)
    monkeypatch.setattr(runner.CatalogGovernanceBudget, "close", failed_close)
    with pytest.raises(signal) as captured:
        runner.issue_catalog_admission(
            source,
            governance_root=tmp_path / "gov",
            budget_root=tmp_path / "account",
            protocol=protocol,
            source_slice=protocol.source_slices[0],
            runtime_authorize=policy,
        )
    assert captured.value is stop and not source.exists()


def test_catalog_budget_cannot_be_nested_inside_original_governance(tmp_path):
    source, _p, policy = _catalog_issuer_case(tmp_path)
    with pytest.raises(inputs.InputError, match="CATALOG_GOVERNANCE_ROOT_OVERLAP"):
        runner.CatalogGovernanceBudget(
            tmp_path / "gov" / "account",
            source_path=source,
            governance_root=tmp_path / "gov",
            runtime_authorize=policy,
        )
    assert not (tmp_path / "gov").exists()


def test_catalog_issuer_does_not_replace_an_existing_namespace(tmp_path):
    source, protocol, policy = _catalog_issuer_case(tmp_path)
    gov = tmp_path / "gov"
    gov.mkdir()
    sentinel = gov / "KEEP_EXISTING"
    sentinel.write_bytes(b"SYNTHETIC_OLD_PREFIX")
    with pytest.raises(inputs.InputError, match="CATALOG_GOVERNANCE_NAMESPACE_EXISTS"):
        runner.issue_catalog_admission(
            source,
            governance_root=gov,
            budget_root=tmp_path / "account",
            protocol=protocol,
            source_slice=protocol.source_slices[0],
            runtime_authorize=policy,
        )
    assert sentinel.read_bytes() == b"SYNTHETIC_OLD_PREFIX" and not source.exists()


def test_catalog_unrelated_registry_is_rejected_without_expanding_sdk_readset(tmp_path):
    def extra(f, _gov):
        f.append("fixture.unrelated.v1", "fixture-extra", b"fixture only")

    with pytest.raises(inputs.InputError, match="CATALOG_GOVERNANCE_LAYOUT"):
        _catalog_admission(
            tmp_path, tmp_path / "NEVER_CREATED.duckdb", before_bind=extra
        )


def test_catalog_gov_close_fifo_is_failure_not_a_block_or_authority(tmp_path):
    import os

    source, _p, policy = _catalog_issuer_case(tmp_path)
    io = runner.CatalogGovernanceBudget(
        tmp_path / "account",
        source_path=source,
        governance_root=tmp_path / "gov",
        runtime_authorize=policy,
    )
    os.mkfifo(tmp_path / "account" / "close.json")
    assert not io.close("TEST_FINISHED")
    assert io.closed and io.poisoned and not io.close_verified
    with pytest.raises(inputs.InputError, match="CATALOG_GOVERNANCE_ACCOUNT_CLOSED"):
        io.reserve("AFTER_FAILED_CLOSE")


def test_catalog_controller_requires_live_host_policy_before_output_or_launch(
    tmp_path, monkeypatch
):
    from typing import Any, cast

    def forbidden(*args, **kwargs):
        raise AssertionError("no worker without actual host policy")

    monkeypatch.setattr(runner, "run_bounded_worker", forbidden)
    with pytest.raises(inputs.InputError, match="REAL_INPUT_NOT_ADMITTED"):
        runner.launch_catalog_probe(
            tmp_path / "NEVER_CREATED.duckdb",
            tmp_path / "out",
            protocol=cast(Any, None),
        )
    assert not (tmp_path / "out").exists()


def test_catalog_live_authority_binds_request_and_revocation_not_a_data_flag(tmp_path):
    calls = []
    revoked = [False]

    def policy():
        calls.append("actual callback")
        if revoked[0]:
            raise inputs.InputError("REVOKED_FIXTURE_ONLY")

    request = "sha256:" + "1" * 64
    with runner._CatalogHostAuthority(request, policy) as host:
        wrong = runner._catalog_remote_policy(host.path, "sha256:" + "2" * 64)
        with pytest.raises(inputs.InputError, match="REAL_INPUT_NOT_ADMITTED"):
            wrong()
        assert calls == []
        authorized = runner._catalog_remote_policy(host.path, request)
        authorized()
        assert len(calls) == 1
        revoked[0] = True
        with pytest.raises(inputs.InputError, match="REAL_INPUT_NOT_ADMITTED"):
            authorized()
        assert len(calls) == 2
    assert host.requests == 3 and isinstance(host.failure, inputs.InputError)
    assert not host.path.exists()


def test_catalog_controller_and_worker_same_path_fixture_only(tmp_path, monkeypatch):
    import json
    from dataclasses import replace

    source, _old_admission = _catalog_fixture(tmp_path, monkeypatch)
    _absent, p, policy = _catalog_issuer_case(tmp_path)
    p = replace(p, source_scope_hash=inputs.catalog_scope_hash(source))
    seen = []

    def bounded(module, args, control, limits):
        assert module == runner.MODULE and limits.memory_bytes == 6 * 1024**3
        assert limits.deadline_seconds == 30 and limits.total_seconds == 40
        assert limits.output_bytes == 64 * 1024 and limits.storage_bytes == 256 * 1024
        assert limits.max_attempts == 1
        assert control == tmp_path / "out" / "control"
        wire = args[args.index("--catalog-packet") + 1]
        host = args[args.index("--catalog-host") + 1]
        seen.append(runner._catalog_worker(wire, host))
        return {"state": "COMPLETE", "fixture_resource_mock": True}

    monkeypatch.setattr(runner, "run_bounded_worker", bounded)
    result = runner.launch_catalog_probe(
        source, tmp_path / "out", protocol=p, runtime_authorize=policy
    )
    assert seen[0]["source_qualified"] is False
    assert 0 < result["host_authorization_requests"] <= 128
    assert result["controller"]["fixture_resource_mock"] is True
    close = json.loads(
        (tmp_path / "out" / "catalog" / "catalog-close.json").read_text()
    )
    assert (
        close["state"] == "COMPLETE"
        and close["connection_closed"]
        and close["fd_closed"]
    )


def test_catalog_worker_missing_host_has_no_governance_or_source_io(
    tmp_path, monkeypatch
):
    import json

    source, p, _policy = _catalog_issuer_case(tmp_path)
    monkeypatch.setattr(inputs, "catalog_resource_evidence", lambda: {"fixture": True})
    packet = json.dumps(
        {
            "version": 1,
            "source": str(source),
            "output": str(tmp_path / "out"),
            "protocol": dict(p.payload),
        }
    )
    with pytest.raises(inputs.InputError, match="REAL_INPUT_NOT_ADMITTED"):
        runner._catalog_worker(packet, None)
    assert not source.exists() and not (tmp_path / "out").exists()


@pytest.mark.parametrize("change", ["approved_flag", "wrong_source", "wrong_protocol"])
def test_catalog_packet_cannot_supply_approval_or_retarget_request(tmp_path, change):
    import json

    source, p, _policy = _catalog_issuer_case(tmp_path)
    data = {
        "version": 1,
        "source": str(source),
        "output": str(tmp_path / "out"),
        "protocol": dict(p.payload),
    }
    if change == "approved_flag":
        data["approved"] = True
    elif change == "wrong_source":
        data["source"] = str(tmp_path / "other.duckdb")
    else:
        data["protocol"]["untouched_claim"] = True
    with pytest.raises((inputs.InputError, ValueError)):
        runner._catalog_packet(json.dumps(data))
    assert not source.exists() and not (tmp_path / "out").exists()


def test_catalog_packet_duplicate_keys_are_not_hidden_by_json_parsing(tmp_path):
    with pytest.raises(inputs.InputError, match="CATALOG_PACKET_DUPLICATE_KEY"):
        runner._catalog_packet('{"version":1,"version":1}')


@pytest.mark.parametrize("signal", [KeyboardInterrupt, SystemExit])
def test_catalog_parent_preserves_policy_stop_over_executor_error(
    tmp_path, monkeypatch, signal
):
    source, p, _old_policy = _catalog_issuer_case(tmp_path)
    stop = signal("ORIGINAL_PARENT_STOP")
    calls = []

    def policy():
        calls.append(1)
        if len(calls) > 1:
            raise stop

    def executor(module, args, control, limits):
        wire = args[args.index("--catalog-packet") + 1]
        host = args[args.index("--catalog-host") + 1]
        _source, _output, _protocol, request = runner._catalog_packet(wire)
        try:
            runner._catalog_remote_policy(host, request)()
        except inputs.InputError as error:
            raise OSError("SECONDARY_EXECUTOR_FAILURE") from error
        raise AssertionError("stop must deny the child")

    monkeypatch.setattr(runner, "run_bounded_worker", executor)
    with pytest.raises(signal) as captured:
        runner.launch_catalog_probe(
            source, tmp_path / "out", protocol=p, runtime_authorize=policy
        )
    assert captured.value is stop and not source.exists()


def test_catalog_live_revocation_after_begin_prevents_select_and_keeps_cleanup(
    tmp_path, monkeypatch
):
    import json
    from dataclasses import replace

    source, _old = _catalog_fixture(tmp_path, monkeypatch)
    _absent, p, _policy = _catalog_issuer_case(tmp_path)
    p = replace(p, source_scope_hash=inputs.catalog_scope_hash(source))
    revoked = [False]
    statements = []

    def policy():
        if revoked[0]:
            raise inputs.InputError("REVOKED_SYNTHETIC_ONLY")

    original_open = inputs.open_database

    def wrapped_open(path, *, read_only):
        connection = original_open(path, read_only=read_only)

        class Wrapped:
            def execute(self, statement):
                statements.append(statement)
                connection.execute(statement)
                if statement == "BEGIN TRANSACTION":
                    revoked[0] = True
                return self

            def fetchall(self):
                return connection.fetchall()

            def close(self):
                connection.close()

        return Wrapped()

    monkeypatch.setattr(inputs, "open_database", wrapped_open)

    def executor(module, args, control, limits):
        return runner._catalog_worker(
            args[args.index("--catalog-packet") + 1],
            args[args.index("--catalog-host") + 1],
        )

    monkeypatch.setattr(runner, "run_bounded_worker", executor)
    with pytest.raises(inputs.InputError):
        runner.launch_catalog_probe(
            source, tmp_path / "out", protocol=p, runtime_authorize=policy
        )
    assert "BEGIN TRANSACTION" in statements and inputs.CATALOG_SQL not in statements
    assert "ROLLBACK" in statements
    close = json.loads((tmp_path / "out/catalog/catalog-close.json").read_text())
    assert (
        close["state"] == "FAILED" and close["connection_closed"] and close["fd_closed"]
    )


def test_catalog_authority_request_cap_does_not_refill_or_loop_callbacks():
    calls = []
    request = "sha256:" + "1" * 64

    def policy():
        calls.append(1)

    with runner._CatalogHostAuthority(request, policy) as host:
        authorize = runner._catalog_remote_policy(host.path, request)
        for _ in range(128):
            authorize()
        with pytest.raises((OSError, inputs.InputError)):
            authorize()
        assert len(calls) == host.requests == 128
    assert not host.thread.is_alive() and not host.path.exists()


def test_real_mode_refuses_before_resource_or_any_input_io(
    tmp_path, monkeypatch, capsys
):
    def forbidden(*a, **k):
        raise AssertionError("real must refuse before work")

    monkeypatch.setattr(runner, "run_fixture", forbidden)
    monkeypatch.setattr(runner, "run_bounded_worker", forbidden)
    target = tmp_path / "not-created"
    assert runner.main(("--real", "--output", str(target))) == 2
    assert not target.exists()
    assert "REAL_INPUT_NOT_ADMITTED" in capsys.readouterr().err


def test_source_capture_launcher_denies_before_output_or_sensitive_stat(
    tmp_path, monkeypatch
):
    from experiments.a_share_ingestion import retro_capture_v1 as source

    spec = source.make_synthetic_capture_spec(tmp_path / "fixture")
    protocol = source.synthetic_capture_protocol(spec)

    def forbidden(*args, **kwargs):
        pytest.fail("default source capture must deny before stat or worker")

    monkeypatch.setattr(Path, "stat", forbidden)
    monkeypatch.setattr(runner, "run_bounded_worker", forbidden)
    with pytest.raises(source.CaptureError, match="REAL_INPUT_NOT_ADMITTED"):
        runner.launch_source_capture(spec, protocol=protocol)


def test_source_capture_worker_missing_host_stops_before_governance(
    tmp_path, monkeypatch
):
    from experiments.a_share_ingestion import retro_capture_v1 as source

    spec = source.make_synthetic_capture_spec(tmp_path / "fixture")
    protocol = source.synthetic_capture_protocol(spec)
    wire = runner.canonical_bytes(
        {
            "version": 1,
            "spec": spec.payload,
            "output": spec.output,
            "protocol": protocol.payload,
        }
    ).decode()
    monkeypatch.setattr(
        source, "capture_resource_evidence", lambda: {"fixture_mock": True}
    )
    with pytest.raises(source.CaptureError, match="REAL_INPUT_NOT_ADMITTED"):
        runner._source_capture_worker(wire, None)
    assert not Path(spec.output).exists()


def test_source_capture_same_host_worker_path_fixture_only(tmp_path, monkeypatch):
    from experiments.a_share_ingestion import retro_capture_v1 as source

    spec = source.make_synthetic_capture_spec(tmp_path / "fixture", bulk=True)
    protocol = source.synthetic_capture_protocol(spec)
    monkeypatch.setattr(
        source,
        "capture_resource_evidence",
        lambda: {
            "memory_max": 6 * 1024**3,
            "scope": "MOCK_RESOURCE_UNIT_TEST_NOT_KERNEL_EVIDENCE",
        },
    )
    seen = []

    def bounded(module, args, control, limits):
        assert module == runner.MODULE and limits == spec.resources
        assert control == Path(spec.output) / "control"
        manifest = runner._source_capture_worker(
            args[args.index("--source-capture-packet") + 1],
            args[args.index("--source-capture-host") + 1],
        )
        seen.append(manifest)
        return {"state": "COMPLETE", "termination_verified": True, "fixture_mock": True}

    monkeypatch.setattr(runner, "run_bounded_worker", bounded)
    result = runner.launch_source_capture(
        spec, protocol=protocol, runtime_authorize=lambda: None
    )
    assert result["controller"]["fixture_mock"] and result["source_qualified"] is False
    assert 0 < result["host_authorization_requests"] <= 16384
    assert (
        seen[0].payload["transport_attempts"] == 17
        and seen[0].payload["real_HTTP_attempts"] == 0
    )
    assert source.verify_capture(Path(spec.output) / "data", seen[0])["verified"]


@pytest.mark.parametrize("change", ["approval", "output", "protocol", "duplicate"])
def test_source_capture_packet_cannot_approve_or_retarget(tmp_path, change):
    from experiments.a_share_ingestion import retro_capture_v1 as source

    spec = source.make_synthetic_capture_spec(tmp_path / "fixture")
    protocol = source.synthetic_capture_protocol(spec)
    value = {
        "version": 1,
        "spec": spec.payload,
        "output": spec.output,
        "protocol": dict(protocol.payload),
    }
    if change == "approval":
        value["approved"] = True
    if change == "output":
        value["output"] += "-retarget"
    if change == "protocol":
        value["protocol"]["source_scope_hash"] = "sha256:" + "0" * 64
    wire = runner.canonical_bytes(value).decode()
    if change == "duplicate":
        wire = '{"version":0,' + wire[1:]
    with pytest.raises((source.CaptureError, ValueError)):
        runner._source_capture_packet(wire)


def test_source_host_is_distinct_profile_not_catalog_cap():
    request = "sha256:" + "1" * 64
    with runner._SourceCaptureHostAuthority(request, lambda: None) as host:
        policy = runner._catalog_remote_policy(host.path, request)
        for _ in range(130):
            policy()
        assert host.requests == 130 and host.REQUEST_CAP == 16384
    assert not host.path.exists() and not host.thread.is_alive()
