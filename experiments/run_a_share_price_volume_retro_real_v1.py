"""P3 admitted-Adapter engineering harness; real packages A/B are NOT admitted.

--synthetic exercises public governance, bounded CSV/DB capture and the same
snapshot Views under a6GiB user worker. --replay verifies saved outputs only.
--real always refuses before creating outputs, governance or a source Reader.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import re
import socket
import stat
import sys
import tempfile
import threading
from collections.abc import Callable
from dataclasses import asdict, replace
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from crypto_quant_domain import (
    ArtifactEnvelope,
    ArtifactRef,
    canonical_bytes,
    canonical_sha256,
)
from crypto_quant_foundation import LocalFoundation, LogCheckpoint, LogEntryRef
from crypto_quant_research import (
    PublishedRetrospectiveArtifact,
    RetrospectiveReadTask,
    RetrospectiveSourceSlice,
    RetrospectiveStudyDeclaration,
    RetrospectiveStudyProtocol,
    publish_retrospective_protocol,
    publish_retrospective_read_task,
    publish_retrospective_study,
)
from crypto_quant_validation import (
    RetrospectiveReservationReceipt,
    SampleConsumptionLedger,
    reserve_retrospective_read,
)

from experiments import a_share_price_volume_retro_inputs_v1 as inputs
from experiments import a_share_price_volume_retro_v1 as core
from experiments import run_a_share_price_volume_retro_v1 as fixture_math
from experiments.a_share_price_volume_retro_resources_v1 import (
    RetroResourceError,
    RetroResourceLimits,
    run_bounded_worker,
    worker_resource_evidence,
)

MODULE = "experiments.run_a_share_price_volume_retro_real_v1"
LOG = "research.artifacts.v1"
SAMPLE = "validation.sample-consumption.v1"
MARKER = "CURRENT_SNAPSHOT_RETROSPECTIVE / NOT_UNTOUCHED / NOT_CAUSAL_PIT"
MAX_REPLAY_BYTES = 16 * 1024**2
SOURCE_FILES = {
    "source.csv",
    "source.duckdb",
    "snapshot.json",
    "calendar.json",
    "cohort.json",
    "input-manifest.json",
}


OUTPUT_FILES = frozenset(
    {
        "qualification.json",
        "features-TRAIN.json",
        "features-DEVELOPMENT.json",
        "features-RETROSPECTIVE_EVAL.json",
        "labels-TRAIN.json",
        "labels-DEVELOPMENT.json",
        "labels-RETROSPECTIVE_EVAL.json",
        "model-cards.json",
        "predictions.json",
        "packet.json",
        "report.md",
        "execution-order.jsonl",
    }
)
EXPECTED_PHASES = frozenset(
    {
        "INPUT_QUALIFICATION",
        "SNAPSHOT_FREEZE",
        "TRAIN_FEATURE",
        "TRAIN_FIT",
        "DEVELOPMENT_FEATURE",
        "RETROSPECTIVE_EVAL_FEATURE",
        "DEVELOPMENT_OUTCOME",
        "RETROSPECTIVE_EVAL_OUTCOME",
    }
)


def now():
    return datetime.now(UTC)


def _pub_wire(pub):
    return {
        "ref": pub.ref.to_canonical_dict(),
        "entry": asdict(pub.entry_ref),
        "checkpoint": asdict(pub.checkpoint),
    }


def _record_wire(receipt):
    return {
        "task_ref": receipt.read_task_ref.to_canonical_dict(),
        "record": asdict(receipt.record),
        "entry": asdict(receipt.reservation_entry_ref),
    }


class _FixtureSession:
    def __init__(self, root, budget, clock, protocol):
        self.root = root
        self.budget = budget
        self.clock = clock
        self.protocol = protocol
        self.foundation = LocalFoundation(
            root / "governance", clock=lambda: inputs.utc(clock())
        )
        self.ledger = SampleConsumptionLedger(self.foundation)
        self.protocol_pub = publish_retrospective_protocol(protocol, self.foundation)
        self.study_pub: PublishedRetrospectiveArtifact | None = None
        self.publications = [_pub_wire(self.protocol_pub)]
        self.reservations = []
        self.stages = []
        self.anchors = {}

    def stage(self, name):
        event = {"stage": name, "recorded_at": inputs.utc(self.clock())}
        self.budget.append_event("execution-order.jsonl", event)
        self.stages.append(event)

    def reserve(self, phase, source, **hashes):
        context = self.protocol_pub if self.study_pub is None else self.study_pub
        task = RetrospectiveReadTask(context.ref, phase, source, **hashes)
        publication = publish_retrospective_read_task(task, self.foundation)
        consumed = self.foundation.checkpoint(SAMPLE).as_of
        study_publication = (
            None if self.study_pub is None else self.study_pub.publication
        )
        receipt = reserve_retrospective_read(
            self.foundation,
            self.ledger,
            self.protocol_pub.publication,
            publication.publication,
            consumed,
            study_publication,
        )
        self.publications.append(_pub_wire(publication))
        self.reservations.append(_record_wire(receipt))
        self.stage(phase + "_RESERVED")

        def authorize():
            # Composition-root fixture policy, never an approval=True switch.
            inputs.require(
                self.protocol.study_key == "SYNTHETIC-ADAPTER-ENGINEERING-ONLY",
                "REAL_INPUT_NOT_ADMITTED",
            )
            actual = reserve_retrospective_read(
                self.foundation,
                self.ledger,
                self.protocol_pub.publication,
                publication.publication,
                receipt.record.consumed_at,
                study_publication,
            )
            inputs.require(actual == receipt, "RESERVATION_IDENTITY_CONFLICT")
            for key, filename in (
                ("feature_rows_hash", "features-TRAIN.json"),
                ("model_cards_hash", "model-cards.json"),
                ("predictions_hash", "predictions.json"),
            ):
                expected = hashes.get(key)
                if expected is not None:
                    descriptor = self.budget.files.get(filename)
                    inputs.require(
                        descriptor is not None
                        and "sha256:" + descriptor["sha256"] == expected,
                        "FREEZE_ANCHOR_MISSING",
                    )
                    self.budget.read(
                        descriptor, lambda: None
                    )  # Already-observed owned result, not a market-source grant.

        return inputs.ReadAdmission(phase, receipt, source, authorize)


def _make_plan(snapshot, descriptor, splits):
    observed = datetime.fromisoformat(snapshot["observed_at"])
    captured = datetime.fromisoformat(snapshot["captured_at"])

    def provenance(event):
        return core.SnapshotProvenance(
            snapshot["capture_revision"],
            "derived_snapshot",
            descriptor["sha256"],
            event,
            captured,
            observed,
            None,
        )

    first = date.fromisoformat(snapshot["calendar"][0][0])
    cal_provenance = provenance(datetime.combine(first, time(), core.SHANGHAI))
    days = tuple(
        core.CalendarDay(date.fromisoformat(day), is_open, cal_provenance)
        for day, is_open in snapshot["calendar"]
    )
    classes = tuple(
        core.SnapshotClassification(
            row["instrument_id"],
            row["venue"],
            row["industry_code"],
            row["ordinary_a_share"],
            row["selected"],
            provenance(captured),
        )
        for row in snapshot["cohort"]
    )
    return core.RetrospectivePlan(
        snapshot["capture_revision"],
        (("derived_snapshot", descriptor["sha256"]),),
        days,
        splits,
        "SYNTHETIC post-hoc two-stock engineering cohort, not real/PIT membership",
        observed,
        tuple(row.instrument_id for row in classes),
        True,
        classes,
    )


def run_fixture(
    output: Path, *, source_format="csv", clock=now, resource_evidence=None
):
    """Only internally generated fixtures; no caller-supplied source location."""
    root = Path(output).absolute()
    inputs.no_links(root)
    inputs.require(not root.exists(), "OUTPUT_CONFLICT")
    root.mkdir(mode=0o700, parents=True)
    budget = inputs.ArtifactBudget(root)
    fit_attempts = 0
    session = None
    try:
        days = inputs.fixture_calendar()
        splits = inputs.select_calendar_splits(days)
        recipe = {
            "origin": inputs.FIXTURE_ORIGIN,
            "calendar": tuple((d.isoformat(), o) for d, o in days),
            "ids": inputs.IDS,
            "source_format": source_format,
            "scope": "new generated files in this owned fixture root only",
            "number_policy": "exact declared text or exact preserved binary64; not provider precision",
        }
        scope_hash = "sha256:" + core.identity(recipe)
        protocol = RetrospectiveStudyProtocol(
            "SYNTHETIC-ADAPTER-ENGINEERING-ONLY",
            "sha256:"
            + core.identity(
                {"design": "RETRO-V1", "schedule": "calendar-only4:1:2-remainderTRAIN"}
            ),
            inputs.wire_hash(Path(core.__file__).read_bytes()),
            inputs.wire_hash(Path(__file__).read_bytes()),
            scope_hash,
            "sha256:"
            + core.identity(
                {
                    "known_observations": "synthetic fixture only",
                    "global_untouched": False,
                }
            ),
            (
                (
                    "capture",
                    inputs.instant(days[0][0]),
                    inputs.instant(days[-1][0] + timedelta(days=1)),
                ),
            ),
        )
        session = _FixtureSession(root, budget, clock, protocol)
        qual = session.reserve("INPUT_QUALIFICATION", protocol.source_slices[0])
        captured = clock()
        source = inputs.write_fixture_source(budget, days, source_format)
        rows = (
            inputs.read_csv_rows(budget, source, qual.authorize)
            if source_format == "csv"
            else inputs.read_duckdb_rows(budget, source, qual.authorize)
        )
        check = {
            "origin": inputs.FIXTURE_ORIGIN,
            "rows": len(rows),
            "source": source,
            "source_kind": "SYNTHETIC_GENERATED_INPUT",
            "db_physical_io_bytes": None,
            "limits_note": "SQL row cap is not internal scan/physical-I/O cap",
        }
        check_desc = budget.write("qualification.json", core.canonical_bytes(check))
        session.stage("QUALIFICATION_COMPLETE_NO_Y_OR_FIT")
        freeze = session.reserve(
            "SNAPSHOT_FREEZE",
            protocol.source_slices[0],
            input_check_hash="sha256:" + check_desc["sha256"],
        )
        freeze.authorize()
        observed = clock()
        cohort = tuple(
            {
                "instrument_id": i,
                "venue": i.rsplit(".", 1)[1],
                "industry_code": "801150",
                "ordinary_a_share": True,
                "selected": True,
                "classification_basis": "ARTIFICIAL_FIXED_POSTHOC_FIXTURE",
            }
            for i in inputs.IDS
        )
        snapshot = {
            "origin": inputs.FIXTURE_ORIGIN,
            "capture_revision": protocol.capture_revision,
            "source_scope_hash": scope_hash,
            "captured_at": inputs.utc(captured),
            "observed_at": inputs.utc(observed),
            "provider_available_at": None,
            "original_provider_acquired_at": None,
            "capture_basis": "ACTUAL_LOCAL_CAPTURE_OF_GENERATED_FIXTURE",
            "calendar": tuple((d.isoformat(), o) for d, o in days),
            "cohort": cohort,
            "rows": rows,
        }
        snap_desc = budget.write("snapshot.json", core.canonical_bytes(snapshot))
        cal_desc = budget.write(
            "calendar.json", core.canonical_bytes(snapshot["calendar"])
        )
        cohort_desc = budget.write("cohort.json", core.canonical_bytes(cohort))
        manifest = {
            "origin": inputs.FIXTURE_ORIGIN,
            "capture_revision": protocol.capture_revision,
            "source_scope_hash": scope_hash,
            "snapshot": snap_desc,
            "calendar": cal_desc,
            "cohort": cohort_desc,
            "source": source,
            "captured_at": inputs.utc(captured),
            "observed_at": inputs.utc(observed),
            "frozen_at": inputs.utc(clock()),
            "raw_vs_derived": "derived normalized synthetic capture; hashes do not claim provider raw bytes",
        }
        manifest_desc = budget.write(
            "input-manifest.json", core.canonical_bytes(manifest)
        )
        input_hash = "sha256:" + manifest_desc["sha256"]
        plan = _make_plan(snapshot, snap_desc, splits)
        parts = tuple(
            (
                split.partition,
                RetrospectiveSourceSlice(
                    "capture",
                    protocol.capture_revision,
                    scope_hash,
                    inputs.instant(split.read_from),
                    inputs.instant(split.read_to),
                    input_hash,
                ),
                inputs.instant(split.decision_from),
                inputs.instant(split.decision_to),
            )
            for split in splits
        )
        study = RetrospectiveStudyDeclaration(
            session.protocol_pub.ref,
            input_hash,
            "sha256:" + cal_desc["sha256"],
            "sha256:" + cohort_desc["sha256"],
            "sha256:"
            + core.identity(
                {
                    "protocol": protocol.prior_observation_hash,
                    "limitations": "synthetic-only, no alias completeness claim",
                }
            ),
            parts,
        )
        study_pub = publish_retrospective_study(study, session.foundation)
        session.study_pub = study_pub
        session.publications.append(_pub_wire(study_pub))
        session.stage("INPUTS_PHYSICALLY_FROZEN_STUDY_PUBLISHED")
        reader = inputs.SnapshotReader(
            budget, {**manifest, "input_manifest_hash": input_hash}, plan
        )
        features = []
        labels = []
        predictions = []
        a = session.reserve("TRAIN_FEATURE", parts[0][1])
        train_features = core.make_retrospective_features(
            plan, reader.views(a, splits[0])
        )
        features.extend(train_features)
        feature_desc = budget.write(
            "features-TRAIN.json", core.canonical_bytes(train_features)
        )
        session.stage("TRAIN_FEATURES_FROZEN")
        a = session.reserve(
            "TRAIN_FIT",
            parts[0][1],
            feature_rows_hash="sha256:" + feature_desc["sha256"],
        )
        train_labels = core.make_retrospective_labels(
            plan, reader.views(a, splits[0], outcome=True), computed_at=clock()
        )
        labels.extend(train_labels)
        budget.write("labels-TRAIN.json", core.canonical_bytes(train_labels))
        train_panel = core.TrainPanel(train_features, train_labels)
        fitted_at = clock()
        fit_attempts += 1
        cards = core.fit_retrospective_models(plan, train_panel, fitted_at=fitted_at)
        model_desc = budget.write("model-cards.json", core.canonical_bytes(cards))
        session.stage("MODEL_CARDS_PHYSICALLY_FROZEN")
        for i, split in enumerate(splits):
            if i == 0:
                rows_features = train_features
            else:
                a = session.reserve(
                    split.partition + "_FEATURE",
                    parts[i][1],
                    model_cards_hash="sha256:" + model_desc["sha256"],
                )
                rows_features = core.make_retrospective_features(
                    plan, reader.views(a, split)
                )
                features.extend(rows_features)
                budget.write(
                    "features-" + split.partition + ".json",
                    core.canonical_bytes(rows_features),
                )
            predictions.append(
                core.predict_retrospective_models(
                    plan, cards, rows_features, predicted_at=clock()
                )
            )
            session.stage(split.partition + "_PREDICTED_WITHOUT_Y")
        combined = core.PredictionRows(
            cards.plan_identity,
            core.identity(cards),
            cards.training_count,
            cards.training_weeks,
            clock(),
            tuple(
                sorted(
                    (row for p in predictions for row in p.rows),
                    key=lambda row: row.key,
                )
            ),
            tuple(row for p in predictions for row in p.shuffle),
            tuple(
                sorted(
                    (row for p in predictions for row in p.feature_scope),
                    key=lambda row: row[1],
                )
            ),
            core._all_facts(tuple(p.feature_facts for p in predictions)),
        )
        prediction_desc = budget.write(
            "predictions.json", core.canonical_bytes(combined)
        )
        session.stage("ALL_F_PREDICTIONS_AND_MOTHER_LINEAGE_PHYSICALLY_FROZEN")
        # Score exact serialized p12, with no second predict or fit.
        saved = json.loads(budget.read(prediction_desc, lambda: None))
        scored = replace(
            combined,
            rows=tuple(
                replace(
                    row, probabilities=tuple(Decimal(p) for p in obj["probabilities"])
                )
                for row, obj in zip(combined.rows, saved["rows"], strict=True)
            ),
        )
        inputs.require(
            core.identity(scored) == core.identity(combined),
            "PERSISTED_PREDICTION_CONFLICT",
        )
        for i, split in enumerate(splits[1:], 1):
            a = session.reserve(
                split.partition + "_OUTCOME",
                parts[i][1],
                model_cards_hash="sha256:" + model_desc["sha256"],
                predictions_hash="sha256:" + prediction_desc["sha256"],
            )
            outcome = reader.views(a, split, outcome=True)
            rows_labels = core.make_retrospective_labels(
                plan, outcome, computed_at=clock()
            )
            labels.extend(rows_labels)
            budget.write(
                "labels-" + split.partition + ".json", core.canonical_bytes(rows_labels)
            )
            session.stage(split.partition + "_LABELS_AFTER_PREDICTION_FREEZE")
        all_features = tuple(sorted(features, key=lambda row: row.key))
        all_labels = tuple(sorted(labels, key=lambda row: row.key))
        grid = fixture_math.fixture_week_grid(plan, all_features)
        report = core.evaluate_retrospective_predictions(
            plan, scored, all_labels, grid, evaluated_at=clock()
        )
        session.stage("EVALUATED_ONCE_WITHOUT_REFIT")
        packet = {
            "format": "RETRO-V1-ADAPTER-ENGINEERING-PACKET",
            "origin": inputs.FIXTURE_ORIGIN,
            "data_mode": "CURRENT_SNAPSHOT_RETROSPECTIVE",
            "untouched_claim": False,
            "causal_pit_claim": False,
            "source_qualified": False,
            "formal_validation_report": False,
            "clock_basis": "ACTUAL_LOCAL_GOVERNANCE_AND_COMPUTE_TIMES_ON_SYNTHETIC_INPUTS",
            "provider_available_at": None,
            "plan": plan,
            "features": all_features,
            "labels": all_labels,
            "models": cards,
            "predictions": combined,
            "calendar_grid": grid,
            "diagnostics": report,
            "protocol": json.loads(canonical_bytes(protocol.payload)),
            "study": json.loads(canonical_bytes(study.payload)),
            "protocol_ref": session.protocol_pub.ref.to_canonical_dict(),
            "study_ref": study_pub.ref.to_canonical_dict(),
            "publications": session.publications,
            "reservations": session.reservations,
            "execution_order": session.stages,
            "fit_calls": fit_attempts,
            "source_open_calls": reader.open_calls,
            "controlled_input_read_debit": budget.read_debit,
            "controlled_write_debit_before_packet": budget.write_debit,
            "resource_evidence": resource_evidence,
            "resource_mode": "ACTUAL_OWNED_USER_UNIT"
            if resource_evidence is not None
            else "IN_PROCESS_SYNTHETIC_TEST_NOT_HARD_CAPPED",
            "real_source_reads": 0,
            "http_requests": 0,
            "real_entry": "DENIED_UNTIL_QUALIFIED_FINITE_INPUT_PACKAGE_AND_EXPLICIT_A_B",
        }
        budget.write("packet.json", core.canonical_bytes(packet))
        budget.write("report.md", render_report(packet).encode())
        outputs = {
            name: {"sha256": d["sha256"], "bytes": d["bytes"]}
            for name, d in budget.files.items()
            if name not in SOURCE_FILES
        }
        final = {
            "format": "RETRO-V1-ADAPTER-OUTPUTS",
            "origin": inputs.FIXTURE_ORIGIN,
            "files": outputs,
            "replay_scope": "owned outputs and existing exact owner/sample entries only; no source files, no checkpoint refresh, no fit/score",
        }
        budget.write("output-manifest.json", core.canonical_bytes(final))
        # Metadata storage is measured separately; not presented as a filesystem quota.
        total = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
        inputs.require(total <= 24 * 1024**2, "FIXTURE_RETAINED_STORAGE_CAP")
        return packet
    except Exception as error:
        raw = core.canonical_bytes(
            {
                "state": "LOCAL_BLOCKED",
                "origin": inputs.FIXTURE_ORIGIN,
                "error_code": str(getattr(error, "code", type(error).__name__))[:160],
                "fit_attempts_started": fit_attempts,
                "execution_order": [] if session is None else session.stages,
                "read_debit": budget.read_debit,
                "write_debit": budget.write_debit,
                "real_source_reads": 0,
                "http_requests": 0,
            }
        )
        with (root / "failure.json").open("xb") as stream:
            stream.write(raw)
        raise


def render_report(packet):
    value = core.json_value(packet)
    report = value["diagnostics"]
    return "\n".join(
        [
            "# RETRO-V1 Adapter — SYNTHETIC ENGINEERING ONLY",
            "",
            MARKER,
            "Generated fixtures are not real market evidence or a ValidationReport.",
            "Timestamps record actual local capture/publication/computation on synthetic inputs, not historical provider availability.",
            "Fixture verdict: " + report["verdict"] + ".",
            "Reasons: " + ", ".join(report["verdict_reasons"]) + ".",
            "One fit; four controls; full mother-sample lineage; original104/26/52 effective-week and65/5 window rules.",
            "Real A/B packages remain unapproved; real entry refuses before source/resource I/O.",
            "",
        ]
    )


def _read_owned(path: Path, limit_bytes=MAX_REPLAY_BYTES):
    inputs.no_links(path)
    info = path.stat(follow_symlinks=False)
    inputs.require(info.st_size <= limit_bytes, "REPLAY_CAP")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        actual = os.fstat(fd)
        inputs.require(
            stat.S_ISREG(actual.st_mode)
            and (actual.st_dev, actual.st_ino, actual.st_size, actual.st_mtime_ns)
            == (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns),
            "REPLAY_NOT_REGULAR",
        )
        raw = b""
        while len(raw) <= info.st_size:
            chunk = os.read(fd, min(65536, info.st_size + 1 - len(raw)))
            if not chunk:
                break
            raw += chunk
        inputs.require(len(raw) == info.st_size, "REPLAY_IDENTITY_CONFLICT")
        return raw
    finally:
        os.close(fd)


def _json_owned(path):
    raw = _read_owned(path)
    value = json.loads(raw)
    inputs.require(core.canonical_bytes(value) == raw, "REPLAY_NONCANONICAL")
    return value


def _ref_wire(value):
    inputs.require(
        isinstance(value, dict)
        and set(value) == {"type", "artifact_type", "schema_version", "content_hash"},
        "REPLAY_REF_INVALID",
    )
    result = ArtifactRef(
        value["artifact_type"], value["schema_version"], value["content_hash"]
    )
    inputs.require(result.to_canonical_dict() == value, "REPLAY_REF_INVALID")
    return result


def _verify_governance(root, packet, files):
    # Legacy Foundation reads pathnames. Copy only bounded, pinned regular
    # metadata into an owned private verifier root; never copy source inputs.
    source = root / "governance"
    inputs.no_links(source)
    inputs.require(source.is_dir(), "REPLAY_METADATA_MISSING")
    with tempfile.TemporaryDirectory(prefix="retro-output-metadata-") as temporary:
        private = Path(temporary)
        used = 0
        for count, path in enumerate(source.rglob("*"), 1):
            inputs.require(count <= 256, "REPLAY_CAP")
            inputs.no_links(path)
            info = path.stat(follow_symlinks=False)
            relative = path.relative_to(source)
            target = private / relative
            if stat.S_ISDIR(info.st_mode):
                target.mkdir(mode=0o700, parents=True, exist_ok=True)
            else:
                inputs.require(stat.S_ISREG(info.st_mode), "REPLAY_METADATA_NONREGULAR")
                raw = _read_owned(path, 8 * 1024**2 - used)
                used += len(raw)
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with target.open("xb") as stream:
                    stream.write(raw)
        _verify_governance_snapshot(LocalFoundation(private), packet, files)


def _verify_governance_snapshot(f, packet, files):
    publications = packet["publications"]
    reservations = packet["reservations"]
    inputs.require(
        len(publications) == 10 and len(reservations) == 8, "REPLAY_PROOF_COVERAGE"
    )
    entries = {}
    tasks = {}
    phases = {}
    protocol_ref = _ref_wire(packet["protocol_ref"])
    study_ref = _ref_wire(packet["study_ref"])
    anchors = {
        "input_check_hash": "qualification.json",
        "feature_rows_hash": "features-TRAIN.json",
        "model_cards_hash": "model-cards.json",
        "predictions_hash": "predictions.json",
    }
    for pub in publications:
        ref = _ref_wire(pub["ref"])
        entry_ref = LogEntryRef(**pub["entry"])
        inputs.require(
            entry_ref.log_name == LOG and ref.content_hash not in entries,
            "REPLAY_OWNER_CONFLICT",
        )
        entry = f.entries(LOG, entry_ref)[-1]
        source = f.read(ref=ref)
        body = source.envelope.payload
        inputs.require(
            entry.payload == source.source_bytes
            and type(source.envelope.schema_version) is int
            and source.envelope.schema_version == 1,
            "REPLAY_OWNER_CONFLICT",
        )
        if ref.artifact_type.endswith("_read_task"):
            phase = body["phase"]
            inputs.require(
                phase in EXPECTED_PHASES and phase not in phases,
                "REPLAY_PHASE_CONFLICT",
            )
            context = _ref_wire(dict(body["context_ref"]))
            inputs.require(
                context
                == (
                    protocol_ref
                    if phase in ("INPUT_QUALIFICATION", "SNAPSHOT_FREEZE")
                    else study_ref
                ),
                "REPLAY_CONTEXT_CONFLICT",
            )
            event = canonical_sha256(
                (
                    "retrospective-read-task-publication-v1",
                    context,
                    phase,
                    body["source_slice"]["scope_key"],
                )
            )
            for name, filename in anchors.items():
                if body[name] is not None:
                    inputs.require(
                        body[name] == "sha256:" + files[filename]["sha256"],
                        "REPLAY_FREEZE_ANCHOR_CONFLICT",
                    )
            phases[phase] = ref
            tasks[ref.content_hash] = (body, entry)
        else:
            inputs.require(ref in (protocol_ref, study_ref), "REPLAY_OWNER_CONFLICT")
            payload = packet["protocol"] if ref == protocol_ref else packet["study"]
            kind = (
                "retrospective_study_protocol"
                if ref == protocol_ref
                else "retrospective_study_declaration"
            )
            inputs.require(
                ref.artifact_type == kind
                and canonical_bytes(ArtifactEnvelope.create(kind, 1, payload))
                == source.source_bytes,
                "REPLAY_DECLARATION_CONFLICT",
            )
            event = canonical_sha256(("artifact-publication-v1", LOG, ref))
        inputs.require(
            event == entry.event_id
            and asdict(
                LogCheckpoint(
                    LOG, entry.accepted_at, entry.log_sequence, entry.receipt_hash
                )
            )
            == pub["checkpoint"],
            "REPLAY_OWNER_CONFLICT",
        )
        entries[ref.content_hash] = entry
    inputs.require(
        set(phases) == EXPECTED_PHASES
        and protocol_ref.content_hash in entries
        and study_ref.content_hash in entries
        and packet["study"]["protocol_ref"] == packet["protocol_ref"],
        "REPLAY_PROOF_COVERAGE",
    )
    seen = set()
    purposes = {
        "retrospective_input_read_task": "discovery",
        "retrospective_feature_read_task": "feature_build",
        "retrospective_training_read_task": "model_training",
        "retrospective_outcome_read_task": "validation",
    }
    for reservation in reservations:
        ref = _ref_wire(reservation["task_ref"])
        inputs.require(
            ref.content_hash in tasks and ref.content_hash not in seen,
            "REPLAY_PROOF_COVERAGE",
        )
        seen.add(ref.content_hash)
        body, producer = tasks[ref.content_hash]
        record = reservation["record"]
        s = body["source_slice"]
        entry_ref = LogEntryRef(**reservation["entry"])
        inputs.require(entry_ref.log_name == SAMPLE, "REPLAY_RESERVATION_CONFLICT")
        entry = f.entries(SAMPLE, entry_ref)[-1]
        expected = ArtifactEnvelope.create(
            "sample_consumption_append", 1, {"record": record, "producer_ref": ref}
        )
        inputs.require(
            entry.payload == canonical_bytes(expected)
            and producer.ledger_sequence < entry.ledger_sequence
            and record["dataset_revision"] == s["capture_revision"]
            and record["interval_start"] == s["interval_start"]
            and record["interval_end"] == s["interval_end"]
            and record["purpose"] == purposes[ref.artifact_type]
            and record["consumer_id"] == canonical_sha256(("sample-consumer-v1", ref))
            and producer.accepted_at <= record["consumed_at"] <= entry.accepted_at,
            "REPLAY_RESERVATION_CONFLICT",
        )
        event = canonical_sha256(
            (
                "sample-consumption-append-v1",
                ref,
                record["dataset_revision"],
                record["interval_start"],
                record["interval_end"],
                record["purpose"],
            )
        )
        inputs.require(entry.event_id == event, "REPLAY_RESERVATION_CONFLICT")
    inputs.require(seen == set(tasks), "REPLAY_PROOF_COVERAGE")


def _verify_result_panels(root, packet, pred, cards):
    for role in core.RETRO_PARTITIONS:
        for kind in ("features", "labels"):
            saved = _json_owned(root / (kind + "-" + role + ".json"))
            expected = [row for row in packet[kind] if row["partition"] == role]
            inputs.require(
                core.canonical_bytes(saved) == core.canonical_bytes(expected),
                "REPLAY_PANEL_CONFLICT",
            )
    train = [row for row in packet["features"] if row["partition"] == "TRAIN"]
    inputs.require(
        core.identity(train) == cards["training_features_identity"],
        "REPLAY_TRAIN_INPUT_CONFLICT",
    )
    labels = {core.identity(row["key"]): row for row in packet["labels"]}
    predictions = {core.identity(row["key"]): row for row in pred["rows"]}
    evaluations = packet["diagnostics"]["evaluation_rows"]
    inputs.require(
        len(labels) == len(packet["labels"])
        and len(predictions) == len(pred["rows"])
        and len(evaluations) == len(predictions),
        "REPLAY_JOIN_CONFLICT",
    )
    seen = set()
    for row in evaluations:
        key = core.identity(row["prediction"]["key"])
        expected_label = labels.get(key)
        inputs.require(
            key in predictions
            and key not in seen
            and core.canonical_bytes(row["prediction"])
            == core.canonical_bytes(predictions[key])
            and core.canonical_bytes(row["label"])
            == core.canonical_bytes(expected_label)
            and type(row["evaluated"]) is bool
            and row["evaluated"]
            == (expected_label is not None and expected_label["y"] is not None),
            "REPLAY_JOIN_CONFLICT",
        )
        seen.add(key)


def replay(output: Path):
    root = Path(output).absolute()
    inputs.no_links(root)
    inputs.require(not (root / "failure.json").exists(), "INCOMPLETE_OUTPUT")
    manifest = _json_owned(root / "output-manifest.json")
    inputs.require(
        manifest["format"] == "RETRO-V1-ADAPTER-OUTPUTS"
        and manifest["origin"] == inputs.FIXTURE_ORIGIN,
        "REPLAY_IDENTITY_CONFLICT",
    )
    files = manifest["files"]
    inputs.require(
        isinstance(files, dict) and set(files) == OUTPUT_FILES,
        "REPLAY_SCOPE_CONFLICT",
    )
    inputs.require(
        all(
            isinstance(item, dict)
            and set(item) == {"bytes", "sha256"}
            and type(item["bytes"]) is int
            and item["bytes"] >= 0
            and type(item["sha256"]) is str
            and re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) is not None
            for item in files.values()
        ),
        "REPLAY_MANIFEST_INVALID",
    )
    inputs.require(
        sum(item["bytes"] for item in files.values()) <= MAX_REPLAY_BYTES, "REPLAY_CAP"
    )
    inputs.require(
        not {p.name for p in root.iterdir()}
        - OUTPUT_FILES
        - SOURCE_FILES
        - {"governance", "output-manifest.json"},
        "INCOMPLETE_OUTPUT",
    )
    for name, descriptor in files.items():
        inputs.require(Path(name).name == name, "REPLAY_SCOPE_CONFLICT")
        raw = _read_owned(root / name)
        inputs.require(
            len(raw) == descriptor["bytes"]
            and inputs.digest(raw) == descriptor["sha256"],
            "REPLAY_FILE_CONFLICT",
        )
    packet = _json_owned(root / "packet.json")
    cards = _json_owned(root / "model-cards.json")
    pred = _json_owned(root / "predictions.json")
    diagnostic = packet["diagnostics"]
    inputs.require(
        packet["origin"] == inputs.FIXTURE_ORIGIN
        and packet["format"] == "RETRO-V1-ADAPTER-ENGINEERING-PACKET"
        and packet["untouched_claim"] is False
        and packet["causal_pit_claim"] is False
        and packet["source_qualified"] is False
        and packet["formal_validation_report"] is False
        and packet["fit_calls"] == 1
        and packet["real_source_reads"] == packet["http_requests"] == 0
        and packet["models"] == cards
        and packet["predictions"] == pred
        and cards["plan_identity"]
        == pred["plan_identity"]
        == diagnostic["plan_identity"]
        == core.identity(packet["plan"])
        and pred["model_identity"]
        == diagnostic["model_identity"]
        == core.identity(cards)
        and diagnostic["predictions_identity"] == core.identity(pred)
        and diagnostic["calendar_grid_identity"]
        == core.identity(packet["calendar_grid"]),
        "REPLAY_IDENTITY_CONFLICT",
    )
    journal = _read_owned(root / "execution-order.jsonl")
    events = [json.loads(line) for line in journal.splitlines()]
    inputs.require(
        b"".join(core.canonical_bytes(event) + b"\n" for event in events) == journal
        and events == packet["execution_order"],
        "REPLAY_JOURNAL_CONFLICT",
    )
    _verify_result_panels(root, packet, pred, cards)
    _verify_governance(root, packet, files)
    text = _read_owned(root / "report.md").decode()
    inputs.require(text == render_report(packet), "REPLAY_REPORT_CONFLICT")
    return text


CATALOG_GOVERNANCE_SOURCE_BYTES = 256 * 1024
CATALOG_GOVERNANCE_PRIVATE_BYTES = 640 * 1024
CATALOG_GOVERNANCE_ACCOUNT_BYTES = 128 * 1024
CATALOG_GOVERNANCE_CLOCK_CALLS = 8
CATALOG_GOVERNANCE_APPEND_RESERVE = 16 * 1024
CATALOG_GOVERNANCE_PREFIX_BYTES = 280 * 1024
CATALOG_GOVERNANCE_READ_BYTES = 256 * 1024**2
CATALOG_GOVERNANCE_WRITE_BYTES = 64 * 1024**2
CATALOG_GOVERNANCE_SDK_CALLS = 128
CATALOG_GOVERNANCE_CODE_PINS = {
    "foundation/src/crypto_quant_foundation/storage.py": "a33939d07f34d9a2b2beec491512a822c025a5279a8750ff3fc89540f45774e7",
    "research-platform/src/crypto_quant_research/retrospective_study.py": "31497d3917bd5da6b395a1db4e2c8f550d392b195fc9c041cdb400980092738e",
    "research-platform/src/crypto_quant_research/statistical_study.py": "9b8f726936f17ea8e46815ae0afd25006b7df8fa0bf81f2df30b6e5ebade26b0",
    "strategy-validation/src/crypto_quant_validation/retrospective_reservation.py": "bd9ba06528f53e0071bffe5190536214f403f44a80920f2173795ce84b6d72fb",
    "strategy-validation/src/crypto_quant_validation/statistical_reservation.py": "5bd9f097bb7eb329bc458972876f901a90b34a383a667a589bdd2ce21ceceb23",
    "strategy-validation/src/crypto_quant_validation/sample_consumption.py": "082f9f4629cf15d707d97cbd1a85c440708d3ad80b1edba899e72db1a4ce3234",
    "strategy-validation/src/crypto_quant_validation/ledger.py": "94c4beabba6d6583837b7b5a607fa63a84266c33b01b3964ecbc8e18f0e2a4f3",
}


class CatalogGovernanceBudget:
    """One durable account; SDK reservations are pinned-program UPPER BOUNDS.

    Exact LocalFoundation instances and all domain semantics remain untouched.
    Each fixed ISSUE/VERIFY program reserves64 public calls before executing.
    The pinned Foundation reads<=4 complete prefixes and writes<=1 per call.
    This is not measured/physical I/O or a general filesystem quota.
    """

    def __init__(
        self,
        root: Path,
        *,
        source_path: Path,
        governance_root: Path,
        runtime_authorize: Callable[[], None] | None = None,
        read_limit=CATALOG_GOVERNANCE_READ_BYTES,
        write_limit=CATALOG_GOVERNANCE_WRITE_BYTES,
    ):
        if runtime_authorize is None:
            raise inputs.InputError("REAL_INPUT_NOT_ADMITTED")
        runtime_authorize()
        for value, maximum in (
            (read_limit, CATALOG_GOVERNANCE_READ_BYTES),
            (write_limit, CATALOG_GOVERNANCE_WRITE_BYTES),
        ):
            inputs.require(
                type(value) is int and 0 < value <= maximum,
                "CATALOG_GOVERNANCE_LIMIT_INVALID",
            )
        inputs.require(
            write_limit >= CATALOG_GOVERNANCE_ACCOUNT_BYTES, "CATALOG_GOVERNANCE_IO_CAP"
        )
        self.root = Path(root).absolute()
        self.source = str(Path(source_path))
        self.governance = str(Path(governance_root).absolute())
        self.policy = runtime_authorize
        governance = Path(self.governance)
        inputs.require(
            self.root != governance
            and self.root not in governance.parents
            and governance not in self.root.parents
            and self.root != Path(self.source)
            and governance != Path(self.source),
            "CATALOG_GOVERNANCE_ROOT_OVERLAP",
        )
        self.read_limit, self.write_limit = read_limit, write_limit
        self.read_debit = self.sdk_calls_reserved = self.journal_bytes = 0
        self.write_debit = (
            CATALOG_GOVERNANCE_ACCOUNT_BYTES  # Includes ALL account writes.
        )
        self.programs: set[str] = set()
        self.bound = self.closed = self.poisoned = self.close_verified = False
        inputs.require(
            all(len(p) <= 4096 for p in (str(self.root), self.source, self.governance)),
            "CATALOG_GOVERNANCE_PATH_CAP",
        )
        inputs.require(
            str(self.root) == os.path.abspath(self.root)
            and self.governance == os.path.abspath(self.governance),
            "CATALOG_GOVERNANCE_PATH_CAP",
        )
        scope = inputs.catalog_scope_hash(source_path)
        inputs.no_links(self.root)
        inputs.require(not self.root.exists(), "CATALOG_GOVERNANCE_ACCOUNT_EXISTS")
        self.root.mkdir(mode=0o700)
        raw = canonical_bytes(
            {
                "scope": scope,
                "source": self.source,
                "governance": self.governance,
                "read_limit": read_limit,
                "write_limit": write_limit,
                "close_reserve": 16 * 1024,
                "no_refund": True,
            }
        )
        inputs.require(len(raw) <= 16 * 1024, "CATALOG_GOVERNANCE_ACCOUNT_CAP")
        self._write("reserve.json", raw)

    def _write(self, name, raw, *, append=False):
        flags = os.O_WRONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CREAT
        flags |= os.O_APPEND if append else os.O_EXCL
        fd = os.open(self.root / name, flags, 0o600)
        try:
            info = os.fstat(fd)
            inputs.require(
                stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid(),
                "CATALOG_GOVERNANCE_ACCOUNT_NONREGULAR",
            )
            if append:
                inputs.require(
                    info.st_size == self.journal_bytes - len(raw)
                    and info.st_nlink == 1,
                    "CATALOG_GOVERNANCE_ACCOUNT_CHANGED",
                )
            with os.fdopen(fd, "ab" if append else "wb", closefd=False) as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            os.close(fd)

    def reserve(self, event, *, read=0, write=0, sdk_calls=0):
        self.policy()
        inputs.require(
            not self.closed and not self.poisoned, "CATALOG_GOVERNANCE_ACCOUNT_CLOSED"
        )
        inputs.require(
            type(event) is str
            and 0 < len(event) <= 64
            and all(type(v) is int and v >= 0 for v in (read, write, sdk_calls)),
            "CATALOG_GOVERNANCE_DEBIT_INVALID",
        )
        allowed = (
            self.read_debit + read <= self.read_limit
            and self.write_debit + write <= self.write_limit
            and self.sdk_calls_reserved + sdk_calls <= CATALOG_GOVERNANCE_SDK_CALLS
        )
        if allowed:
            self.read_debit += read
            self.write_debit += write
            self.sdk_calls_reserved += sdk_calls
        raw = (
            canonical_bytes(
                {
                    "event": event,
                    "allowed": allowed,
                    "request": (read, write, sdk_calls),
                    "reserved": (
                        self.read_debit,
                        self.write_debit,
                        self.sdk_calls_reserved,
                    ),
                }
            )
            + b"\n"
        )
        try:
            inputs.require(
                self.journal_bytes + len(raw) <= 96 * 1024,
                "CATALOG_GOVERNANCE_ACCOUNT_CAP",
            )
            self.journal_bytes += len(raw)  # Partial failures are not refunded.
            self._write("debits.jsonl", raw, append=True)
        except BaseException:
            self.poisoned = True
            raise
        if not allowed:
            self.poisoned = True
            raise inputs.InputError("CATALOG_GOVERNANCE_IO_CAP")

    def begin_binding(self, source, governance, policy):
        inputs.require(
            str(Path(source)) == self.source
            and str(Path(governance).absolute()) == self.governance
            and policy is self.policy,
            "CATALOG_GOVERNANCE_ACCOUNT_CONFLICT",
        )
        inputs.require(not self.bound, "CATALOG_GOVERNANCE_BIND_ALREADY_ATTEMPTED")
        self.bound = True
        self.reserve("BIND_ATTEMPT")

    def reserve_program(self, name):
        inputs.require(
            name in ("ISSUE", "VERIFY") and name not in self.programs,
            "CATALOG_GOVERNANCE_PROGRAM_REUSE",
        )
        self.programs.add(name)
        code_root = Path(__file__).absolute().parent.parent
        origins = (
            (LocalFoundation, "foundation/src/crypto_quant_foundation/storage.py"),
            (
                RetrospectiveStudyProtocol,
                "research-platform/src/crypto_quant_research/retrospective_study.py",
            ),
            (
                reserve_retrospective_read,
                "strategy-validation/src/crypto_quant_validation/retrospective_reservation.py",
            ),
            (
                SampleConsumptionLedger,
                "strategy-validation/src/crypto_quant_validation/ledger.py",
            ),
        )
        for symbol, relative in origins:
            inputs.require(
                Path(inspect.getfile(symbol)).absolute() == code_root / relative,
                "CATALOG_GOVERNANCE_CODE_PIN",
            )
        for relative, expected in CATALOG_GOVERNANCE_CODE_PINS.items():
            self.reserve("CODE_PIN", read=64 * 1024 + 1)
            raw = _read_owned(code_root / relative, 64 * 1024)
            inputs.require(
                hashlib.sha256(raw).hexdigest() == expected,
                "CATALOG_GOVERNANCE_CODE_PIN",
            )
        p = CATALOG_GOVERNANCE_PREFIX_BYTES
        self.reserve(name, read=64 * 4 * p, write=64 * p, sdk_calls=64)

    def summary(self):
        return {
            "read_upper_debit": self.read_debit,
            "write_upper_debit": self.write_debit,
            "sdk_calls_reserved": self.sdk_calls_reserved,
            "read_limit": self.read_limit,
            "write_limit": self.write_limit,
            "programs": sorted(self.programs),
            "account_content_reserve": CATALOG_GOVERNANCE_ACCOUNT_BYTES,
            "bound": self.bound,
            "closed": self.closed,
            "poisoned": self.poisoned,
            "close_verified": self.close_verified,
            "basis": "PREDEBIT_PINNED_PROGRAM_UPPER_BOUND_NOT_MEASURED_IO",
        }

    def close(self, state):
        self.closed = True
        try:
            summary = self.summary()
            summary.pop(
                "close_verified"
            )  # Only the caller can observe this write's fsync result.
            raw = canonical_bytes({"state": state, **summary})
            inputs.require(len(raw) <= 16 * 1024, "CATALOG_GOVERNANCE_ACCOUNT_CAP")
            self._write("close.json", raw)
            self.close_verified = True
            return True
        except Exception:  # noqa: BLE001 - Any close failure poisons this account; stops propagate.
            self.poisoned = True
            return False


def _copy_catalog_governance(
    source: Path, target: Path, io_budget: CatalogGovernanceBudget
) -> dict[str, Any]:
    """Pinned owned metadata only, bounded BEFORE legacy Foundation can read it."""
    inputs.no_links(source)
    inputs.require(source.is_dir(), "CATALOG_GOVERNANCE_MISSING")
    pending = [(source, target)]
    nodes = used = reads = 0
    while pending:
        parent, destination = pending.pop()
        with os.scandir(parent) as entries:
            for entry in entries:
                nodes += 1
                inputs.require(nodes <= 128, "CATALOG_GOVERNANCE_NODE_CAP")
                path = Path(entry.path)
                info = entry.stat(follow_symlinks=False)
                inputs.require(
                    info.st_uid == os.getuid() and not stat.S_ISLNK(info.st_mode),
                    "CATALOG_GOVERNANCE_NONREGULAR",
                )
                relative = path.relative_to(source)
                inputs.require(
                    relative.parts[0]
                    in ("artifacts", "registries", ".staging", ".foundation.clock"),
                    "CATALOG_GOVERNANCE_LAYOUT",
                )
                if stat.S_ISDIR(info.st_mode):
                    out = destination / entry.name
                    out.mkdir(mode=0o700)
                    pending.append((path, out))
                else:
                    inputs.require(
                        stat.S_ISREG(info.st_mode), "CATALOG_GOVERNANCE_NONREGULAR"
                    )
                    inputs.require(
                        relative.parts[0] != ".staging", "CATALOG_GOVERNANCE_PARTIAL"
                    )
                    inputs.require(
                        used + info.st_size <= CATALOG_GOVERNANCE_SOURCE_BYTES,
                        "CATALOG_GOVERNANCE_CONTENT_CAP",
                    )
                    if relative.parts[0] == "registries":
                        inputs.require(
                            len(relative.parts) == 2
                            and entry.name
                            in (
                                "research.artifacts.v1.jsonl",
                                "validation.sample-consumption.v1.jsonl",
                            ),
                            "CATALOG_GOVERNANCE_LAYOUT",
                        )
                    io_budget.reserve(
                        "SNAPSHOT_COPY", read=info.st_size + 1, write=info.st_size
                    )
                    raw = _read_owned(path, info.st_size)
                    used += len(raw)
                    reads += 1
                    with (destination / entry.name).open("xb") as stream:
                        stream.write(raw)
    return {
        "source_content_bytes": used,
        "source_content_read_debit": used + reads,
        "nodes": nodes,
        "source_content_cap": CATALOG_GOVERNANCE_SOURCE_BYTES,
        "private_peak_reserve": CATALOG_GOVERNANCE_PRIVATE_BYTES,
        "total_retained_and_temporary_reserve": 1024**2,
    }


def _bind_catalog_admission(
    source_path: Path,
    *,
    governance_root: Path,
    protocol_publication: PublishedRetrospectiveArtifact,
    task_publication: PublishedRetrospectiveArtifact,
    source_slice: RetrospectiveSourceSlice,
    reservation: RetrospectiveReservationReceipt,
    io_budget: CatalogGovernanceBudget,
    runtime_authorize: Callable[[], None] | None = None,
) -> inputs.ReadAdmission:
    """Verify a bounded snapshot of existing real owner/sample proofs, not a grant.

    No writes/checkpoints on the original store. The private verifier may issue
    at most8 lookup checkpoints but MUST reuse an already verified sample append;
    it never publishes Protocol/Task or manufactures a real reservation. Original
    content<=256KiB, private reserve640KiB and account128KiB total1MiB.
    The exact pinned SDK runs unchanged;64 calls are reserved for this fixed
    verification program before any public SDK reads. This is an upper debit,
    not measured I/O, and excludes arbitrary work performed by the trusted host policy.
    """
    if runtime_authorize is None:
        raise inputs.InputError("REAL_INPUT_NOT_ADMITTED")
    runtime_authorize()
    expected_path = str(Path(source_path))
    scope_hash = inputs.catalog_scope_hash(source_path)
    inputs.require(
        type(source_slice) is RetrospectiveSourceSlice
        and source_slice.source_scope_hash == scope_hash,
        "CATALOG_ROOT_BINDING_CONFLICT",
    )
    expected_slice = canonical_bytes(source_slice.payload)
    clock_calls = 0

    def verification_clock():
        nonlocal clock_calls
        inputs.require(
            clock_calls < CATALOG_GOVERNANCE_CLOCK_CALLS, "CATALOG_GOVERNANCE_CLOCK_CAP"
        )
        clock_calls += 1
        return inputs.utc(
            now()
        )  # Lookup time in private verifier only; not republished original time.

    io_budget.reserve_program("VERIFY")
    with tempfile.TemporaryDirectory(prefix="retro-catalog-proof-") as temporary:
        private = Path(temporary)
        evidence = _copy_catalog_governance(Path(governance_root), private, io_budget)
        f = LocalFoundation(private, clock=verification_clock)
        task = f.read(ref=task_publication.ref)
        protocol = f.read(ref=protocol_publication.ref)
        inputs.require(
            len(task.source_bytes) <= 16 * 1024
            and len(protocol.source_bytes) <= 16 * 1024,
            "CATALOG_GOVERNANCE_BODY_CAP",
        )
        body = task.envelope.payload
        inputs.require(
            task.envelope.artifact_type == "retrospective_input_read_task"
            and body["phase"] == "INPUT_QUALIFICATION"
            and canonical_bytes(body["source_slice"]) == expected_slice
            and canonical_bytes(body["context_ref"])
            == canonical_bytes(protocol_publication.ref)
            and protocol.envelope.payload["source_scope_hash"] == scope_hash
            and len(protocol.envelope.payload["source_intervals"]) == 1,
            "CATALOG_ROOT_BINDING_CONFLICT",
        )
        inputs.require(
            type(reservation) is RetrospectiveReservationReceipt
            and reservation.protocol_ref == protocol_publication.ref
            and reservation.read_task_ref == task_publication.ref
            and reservation.protocol_publication_entry_ref
            == protocol_publication.entry_ref
            and reservation.producer_publication_entry_ref == task_publication.entry_ref
            and reservation.study_ref is None,
            "CATALOG_RESERVATION_CHANGED",
        )
        # Prove original append exists BEFORE calling the idempotent public
        # validator in the copy. Missing append must never be repaired here.
        before = f.entries(SAMPLE)
        inputs.require(
            len(before) == 1 and len(f.entries(LOG)) == 2,
            "CATALOG_GOVERNANCE_PREFIX_SHAPE",
        )
        original = f.entries(SAMPLE, reservation.reservation_entry_ref)[-1]
        envelope = ArtifactEnvelope.create(
            "sample_consumption_append",
            1,
            {
                "record": asdict(reservation.record),
                "producer_ref": task_publication.ref,
            },
        )
        inputs.require(
            original.payload == canonical_bytes(envelope), "CATALOG_RESERVATION_CHANGED"
        )
        actual = reserve_retrospective_read(
            f,
            SampleConsumptionLedger(f),
            protocol_publication.publication,
            task_publication.publication,
            reservation.record.consumed_at,
        )
        inputs.require(
            actual == reservation and f.entries(SAMPLE) == before,
            "CATALOG_RESERVATION_CHANGED",
        )
        private_content = sum(
            p.stat().st_size for p in private.rglob("*") if p.is_file()
        )
        growth = (
            CATALOG_GOVERNANCE_CLOCK_CALLS * 1024 + CATALOG_GOVERNANCE_APPEND_RESERVE
        )
        inputs.require(
            private_content <= CATALOG_GOVERNANCE_SOURCE_BYTES + growth,
            "CATALOG_GOVERNANCE_PRIVATE_CAP",
        )
        evidence["private_final_content_bytes"] = private_content
        evidence["private_clock_calls"] = clock_calls
        evidence["verification_clock_basis"] = (
            "CURRENT_LOOKUP_IN_PRIVATE_COPY_NOT_REPUBLICATION"
        )
        # Pinned Foundation stages one full replacement. <=8 fixed-log
        # checkpoints(<1KiB each), plus16KiB failure/append reserve:
        # 2*(256+8+16)KiB=560KiB, inside640KiB. The actual sample prefix
        # must be unchanged on success; reserve is not permission to repair it.
        evidence["private_peak_content_upper_bound"] = 2 * (
            CATALOG_GOVERNANCE_SOURCE_BYTES + growth
        )
        inputs.require(
            evidence["private_peak_content_upper_bound"]
            <= CATALOG_GOVERNANCE_PRIVATE_BYTES,
            "CATALOG_GOVERNANCE_PRIVATE_CAP",
        )
    checks = 0

    def authorize():
        nonlocal checks
        runtime_authorize()
        inputs.require(checks < 32, "CATALOG_GOVERNANCE_RECHECK_CAP")
        checks += 1
        # Immutable proof was pinned above; no original SDK checkpoint growth.

    def assertion(
        path: Path,
        candidate: RetrospectiveSourceSlice,
        receipt: RetrospectiveReservationReceipt,
    ):
        inputs.require(
            str(Path(path)) == expected_path
            and canonical_bytes(candidate.payload) == expected_slice
            and receipt == reservation,
            "CATALOG_ROOT_BINDING_CONFLICT",
        )

    return inputs.ReadAdmission(
        "INPUT_QUALIFICATION", reservation, source_slice, authorize, assertion, evidence
    )


def bind_catalog_admission(
    source_path: Path,
    *,
    governance_root: Path,
    protocol_publication: PublishedRetrospectiveArtifact,
    task_publication: PublishedRetrospectiveArtifact,
    source_slice: RetrospectiveSourceSlice,
    reservation: RetrospectiveReservationReceipt,
    io_budget: CatalogGovernanceBudget | None = None,
    runtime_authorize: Callable[[], None] | None = None,
) -> inputs.ReadAdmission:
    if runtime_authorize is None:
        raise inputs.InputError("REAL_INPUT_NOT_ADMITTED")
    runtime_authorize()
    inputs.require(
        type(io_budget) is CatalogGovernanceBudget, "CATALOG_GOVERNANCE_ACCOUNT_MISSING"
    )
    assert io_budget is not None
    try:
        io_budget.begin_binding(source_path, governance_root, runtime_authorize)
        result = _bind_catalog_admission(
            source_path,
            governance_root=governance_root,
            protocol_publication=protocol_publication,
            task_publication=task_publication,
            source_slice=source_slice,
            reservation=reservation,
            io_budget=io_budget,
            runtime_authorize=runtime_authorize,
        )
    except BaseException as original:
        try:
            io_budget.close("FAILED_OR_INTERRUPTED")
        except BaseException as cleanup:
            raise original from cleanup
        raise
    inputs.require(
        io_budget.close("VERIFIED_NOT_SOURCE_QUALIFIED"),
        "CATALOG_GOVERNANCE_CLOSE_FAILED",
    )
    return replace(
        result,
        catalog_governance={
            **(result.catalog_governance or {}),
            "io_account": io_budget.summary(),
        },
    )


def issue_catalog_admission(
    source_path: Path,
    *,
    governance_root: Path,
    budget_root: Path,
    protocol: RetrospectiveStudyProtocol,
    source_slice: RetrospectiveSourceSlice,
    runtime_authorize: Callable[[], None] | None = None,
) -> inputs.ReadAdmission:
    """One fixed issuer program using the ACTUAL public SDK, never a grant.

    Namespace/budget paths and known prior-observation hashes must already be
    within trusted host permission. No fallback namespace, CLI source mode,
    sample use, market read or claim of untouched data is created here.
    """
    if runtime_authorize is None:
        raise inputs.InputError("REAL_INPUT_NOT_ADMITTED")
    runtime_authorize()
    inputs.require(
        type(protocol) is RetrospectiveStudyProtocol
        and type(source_slice) is RetrospectiveSourceSlice,
        "CATALOG_ROOT_BINDING_CONFLICT",
    )
    inputs.require(
        protocol.source_scope_hash
        == source_slice.source_scope_hash
        == inputs.catalog_scope_hash(source_path)
        and len(protocol.source_intervals) == 1
        and len(protocol.study_key.encode("utf-8")) <= 128
        and len(source_slice.scope_key.encode("utf-8")) <= 128
        and len(source_slice.interval_start) <= 32
        and len(source_slice.interval_end) <= 32
        and canonical_bytes(source_slice.payload)
        == canonical_bytes(protocol.source_slices[0].payload),
        "CATALOG_ROOT_BINDING_CONFLICT",
    )
    envelope = ArtifactEnvelope.create(
        "retrospective_study_protocol", 1, protocol.payload
    )
    inputs.require(
        len(canonical_bytes(envelope)) <= 16 * 1024, "CATALOG_GOVERNANCE_BODY_CAP"
    )
    io = CatalogGovernanceBudget(
        budget_root,
        source_path=source_path,
        governance_root=governance_root,
        runtime_authorize=runtime_authorize,
    )
    clock_calls = 0

    def issuer_clock():
        nonlocal clock_calls
        inputs.require(clock_calls < 16, "CATALOG_GOVERNANCE_CLOCK_CAP")
        clock_calls += 1
        return inputs.utc(now())

    try:
        inputs.no_links(governance_root)
        inputs.require(
            not governance_root.exists(), "CATALOG_GOVERNANCE_NAMESPACE_EXISTS"
        )
        io.reserve_program(
            "ISSUE"
        )  # Includes ALL internal public-SDK calls and staging.
        governance_root.mkdir(mode=0o700)
        f = LocalFoundation(governance_root, clock=issuer_clock)
        pp = publish_retrospective_protocol(protocol, f)
        task = RetrospectiveReadTask(pp.ref, "INPUT_QUALIFICATION", source_slice)
        inputs.require(
            len(
                canonical_bytes(
                    ArtifactEnvelope.create(task.artifact_type, 1, task.payload)
                )
            )
            <= 16 * 1024,
            "CATALOG_GOVERNANCE_BODY_CAP",
        )
        tp = publish_retrospective_read_task(task, f)
        receipt = reserve_retrospective_read(
            f,
            SampleConsumptionLedger(f),
            pp.publication,
            tp.publication,
            inputs.utc(now()),
        )
        return bind_catalog_admission(
            source_path,
            governance_root=governance_root,
            protocol_publication=pp,
            task_publication=tp,
            source_slice=source_slice,
            reservation=receipt,
            io_budget=io,
            runtime_authorize=runtime_authorize,
        )
    except BaseException as original:
        if not io.closed:
            try:
                io.close("ISSUANCE_FAILED_OR_INTERRUPTED")
            except BaseException as cleanup:
                raise original from cleanup
        raise


def run_source_catalog_probe(
    output: Path, *, source_path: Path, admission: inputs.ReadAdmission | None = None
):
    """Trusted-root integration seam only; deliberately not a CLI source mode.

    A human grant and actual public governance must already be enforced by the
    admission callback. This operation does not publish, fit, follow discovered
    tables, or grant new permissions. Its owned-output budget is separate from
    the caller's governance and resource-controller budgets.
    """
    if admission is None:
        raise inputs.InputError("REAL_INPUT_NOT_ADMITTED")
    inputs.validate_catalog_admission(source_path, admission)
    inputs.catalog_resource_evidence()
    root = Path(output).absolute()
    inputs.no_links(root)
    inputs.require(not root.exists(), "OUTPUT_CONFLICT")
    root.mkdir(mode=0o700, parents=True)
    budget = inputs.ArtifactBudget(root, write_bytes=inputs.CATALOG_WRITER_BYTES)
    return inputs.inspect_lake_catalog(source_path, budget, admission)


class _CatalogHostAuthority:
    """Local live callback bridge, NOT a serialized approval flag or OS sandbox.

    The trusted bounded policy remains in the parent; each child authorization
    must contact it. Only one exact source/protocol/output request is served.
    AF_UNIX only,128 bounded requests, no HTTP/credential/provider transport.
    """

    REQUEST_CAP = 128
    STOP_CODE = "CATALOG_HOST_STOP_UNVERIFIED"

    def __init__(self, request_hash: str, policy: Callable[[], None]):
        self.request = request_hash.encode("ascii") + b"\n"
        self.policy = policy
        self.stop = threading.Event()
        self.requests = 0
        self.failure: BaseException | None = None
        self.temporary = tempfile.TemporaryDirectory(prefix="retro-ca-")
        self.path = Path(self.temporary.name) / "authority.sock"
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.thread = threading.Thread(target=self._serve, daemon=True)

    def __enter__(self):
        try:
            self.listener.bind(str(self.path))
            os.chmod(self.path, 0o600)
            self.listener.listen(1)
            self.listener.settimeout(0.2)
            self.thread.start()
        except BaseException:
            self.listener.close()
            self.temporary.cleanup()
            raise
        return self

    def _serve(self):
        while not self.stop.is_set() and self.requests < self.REQUEST_CAP:
            try:
                conn, _ = self.listener.accept()
            except TimeoutError:
                continue
            except OSError as error:
                if not self.stop.is_set():
                    self.failure = error
                return
            self.requests += 1
            with conn:
                conn.settimeout(0.5)
                try:
                    with conn.makefile("rb") as stream:
                        request = stream.readline(256)
                    allowed = False
                    if request == self.request:
                        try:
                            self.policy()
                        except BaseException as error:  # noqa: BLE001 - Relay the original stop to the parent.
                            self.failure = error
                            self.stop.set()
                        else:
                            allowed = True
                    conn.sendall(b"ALLOW\n" if allowed else b"DENY\n")
                except OSError:
                    continue

    def __exit__(self, kind, original, traceback):
        try:
            self.stop.set()
            self.listener.close()
            self.thread.join(timeout=1)
            inputs.require(not self.thread.is_alive(), self.STOP_CODE)
            self.temporary.cleanup()
        except BaseException as cleanup:
            if original is not None:
                raise original from cleanup
            raise
        return False


def _catalog_packet(text):
    inputs.require(
        type(text) is str and len(text.encode("utf-8")) <= 16 * 1024,
        "CATALOG_PACKET_CAP",
    )

    def unique(pairs):
        result = {}
        for key, value in pairs:
            inputs.require(key not in result, "CATALOG_PACKET_DUPLICATE_KEY")
            result[key] = value
        return result

    value: dict[str, Any] = json.loads(text, object_pairs_hook=unique)
    inputs.require(
        type(value) is dict
        and set(value) == {"version", "source", "output", "protocol"}
        and type(value["version"]) is int
        and value["version"] == 1
        and type(value["source"]) is str
        and type(value["output"]) is str,
        "CATALOG_PACKET_INVALID",
    )
    source = Path(value["source"])
    output = Path(value["output"])
    data: dict[str, Any] = value["protocol"]
    inputs.require(
        type(data) is dict
        and type(data.get("source_intervals")) is list
        and len(data["source_intervals"]) == 1,
        "CATALOG_PACKET_INVALID",
    )
    protocol = RetrospectiveStudyProtocol(
        data["study_key"],
        data["research_design_hash"],
        data["core_code_hash"],
        data["adapter_code_hash"],
        data["source_scope_hash"],
        data["prior_observation_hash"],
        tuple(tuple(row) for row in data["source_intervals"]),
    )
    selected = protocol.source_slices[0]
    inputs.require(
        canonical_bytes(protocol.payload) == canonical_bytes(data)
        and len(protocol.study_key.encode("utf-8")) <= 128
        and len(selected.scope_key.encode("utf-8")) <= 128
        and len(selected.interval_start) <= 32
        and len(selected.interval_end) <= 32
        and protocol.source_scope_hash == inputs.catalog_scope_hash(source)
        and output.is_absolute()
        and str(output) == os.path.abspath(output)
        and len(str(output)) <= 4096,
        "CATALOG_PACKET_INVALID",
    )
    request = canonical_sha256(("catalog-host-request-v1", value))
    return source, output, protocol, request


def _catalog_remote_policy(path: Path, request_hash: str):
    def authorize():
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(1)
            client.connect(str(path))
            client.sendall(request_hash.encode("ascii") + b"\n")
            with client.makefile("rb") as stream:
                answer = stream.readline(32)
        inputs.require(answer == b"ALLOW\n", "REAL_INPUT_NOT_ADMITTED")

    return authorize


def _catalog_worker(packet, host_path):
    # Kernel resource evidence precedes ALL possible original-source operations.
    inputs.catalog_resource_evidence()
    source, output, protocol, request = _catalog_packet(packet)
    inputs.require(host_path is not None, "REAL_INPUT_NOT_ADMITTED")
    policy = _catalog_remote_policy(Path(host_path), request)
    policy()  # No host or mismatched request => no governance/source creation.
    admission = issue_catalog_admission(
        source,
        governance_root=output / "governance",
        budget_root=output / "governance-account",
        protocol=protocol,
        source_slice=protocol.source_slices[0],
        runtime_authorize=policy,
    )
    result = run_source_catalog_probe(
        output / "catalog", source_path=source, admission=admission
    )
    print(
        json.dumps(
            {
                "state": result["state"],
                "source_qualified": False,
                "catalog_columns": len(result["columns"]),
                "fit_calls": 0,
            }
        )
    )
    return result


def launch_catalog_probe(
    source_path: Path,
    output: Path,
    *,
    protocol: RetrospectiveStudyProtocol,
    runtime_authorize: Callable[[], None] | None = None,
):
    """One admitted-by-HOST operation, not permission inferred from plan/ref/data.

    Root must already own an actual human grant for these exact arguments and
    a pure bounded host policy. Only this function supplies the live callback;
    the worker cannot obtain authority from its JSON or a filesystem marker.
    """
    if runtime_authorize is None:
        raise inputs.InputError("REAL_INPUT_NOT_ADMITTED")
    runtime_authorize()
    inputs.require(
        type(protocol) is RetrospectiveStudyProtocol, "CATALOG_PACKET_INVALID"
    )
    wire = canonical_bytes(
        {
            "version": 1,
            "source": str(source_path),
            "output": str(Path(output).absolute()),
            "protocol": protocol.payload,
        }
    ).decode("utf-8")
    source, root, parsed, request = _catalog_packet(wire)
    inputs.require(
        source == source_path and parsed == protocol, "CATALOG_PACKET_INVALID"
    )
    inputs.no_links(root)
    inputs.require(not root.exists(), "OUTPUT_CONFLICT")
    root.mkdir(mode=0o700, parents=True)
    limits = RetroResourceLimits(
        memory_bytes=6 * 1024**3,
        deadline_seconds=30,
        total_seconds=40,
        output_bytes=64 * 1024,
        storage_bytes=256 * 1024,
        max_attempts=1,
    )
    with _CatalogHostAuthority(request, runtime_authorize) as host:
        try:
            result = run_bounded_worker(
                MODULE,
                (
                    "--catalog-worker",
                    "--catalog-packet",
                    wire,
                    "--catalog-host",
                    str(host.path),
                ),
                root / "control",
                limits,
            )
        except BaseException as executor_error:
            if host.failure is not None and not isinstance(host.failure, Exception):
                raise host.failure from executor_error
            raise
    if host.failure is not None:
        raise host.failure
    inputs.require(result["state"] == "COMPLETE", "CATALOG_WORKER_FAILED")
    return {
        "controller": result,
        "host_authorization_requests": host.requests,
        "source_qualified": False,
        "scope_hash": protocol.source_scope_hash,
    }


class _SourceCaptureHostAuthority(_CatalogHostAuthority):
    """Distinct fixed raw-source profile; same private bounded transport only."""

    REQUEST_CAP = 16384
    STOP_CODE = "SOURCE_CAPTURE_HOST_STOP_UNVERIFIED"


def _source_capture_packet(text):
    from experiments.a_share_ingestion import retro_capture_v1 as source

    source.require(
        type(text) is str and len(text.encode("utf-8")) <= 32 * 1024,
        "SOURCE_CAPTURE_PACKET_CAP",
    )

    def unique(pairs):
        value = {}
        for k, v in pairs:
            source.require(k not in value, "SOURCE_CAPTURE_PACKET_DUPLICATE")
            value[k] = v
        return value

    value: dict[str, Any] = json.loads(text, object_pairs_hook=unique)
    source.require(
        type(value) is dict
        and set(value) == {"version", "spec", "output", "protocol"}
        and type(value["version"]) is int
        and value["version"] == 1,
        "SOURCE_CAPTURE_PACKET",
    )
    spec = source.CaptureSpec.from_payload(value["spec"])
    protocol = source.protocol_from_payload(value["protocol"])
    source.require(
        value["output"] == spec.output
        and protocol.source_scope_hash == source.capture_scope_hash(spec)
        and protocol.prior_observation_hash == spec.prior_observation_hash
        and len(protocol.source_intervals) == 1
        and protocol.source_slices[0].interval_start == spec.start + "T00:00:00.000000Z"
        and protocol.source_slices[0].interval_end == spec.end + "T00:00:00.000000Z",
        "SOURCE_CAPTURE_PACKET",
    )
    return spec, protocol, canonical_sha256(("source-capture-live-request-v1", value))


def _source_capture_worker(packet, host_path):
    from experiments.a_share_ingestion import retro_capture_v1 as source

    evidence = source.capture_resource_evidence()
    spec, protocol, request = _source_capture_packet(packet)
    source.require(host_path is not None, "REAL_INPUT_NOT_ADMITTED")
    policy = _catalog_remote_policy(Path(host_path), request)
    policy()
    admission = source.issue_capture_admission(spec, protocol, runtime_authorize=policy)
    admission.governance["resource_entry"] = evidence
    manifest = source.capture_source(spec, admission=admission)
    print(
        json.dumps(
            {
                "state": "CAPTURED_NOT_STUDY_QUALIFIED",
                "mode": spec.mode,
                "manifest_sha256": manifest.sha256,
                "transport_attempts": manifest.payload["transport_attempts"],
                "source_qualified": False,
                "model_calls": 0,
            }
        )
    )
    return manifest


def launch_source_capture(spec, *, protocol, runtime_authorize=None):
    """Root-owned actual grant required; neither packet nor publication grants it."""
    from experiments.a_share_ingestion import retro_capture_v1 as source

    if runtime_authorize is None:
        raise source.CaptureError("REAL_INPUT_NOT_ADMITTED")
    runtime_authorize()
    source.require(
        type(spec) is source.CaptureSpec
        and type(protocol) is RetrospectiveStudyProtocol,
        "SOURCE_CAPTURE_PACKET",
    )
    wire = canonical_bytes(
        {
            "version": 1,
            "spec": spec.payload,
            "output": spec.output,
            "protocol": protocol.payload,
        }
    ).decode("utf-8")
    parsed, verified, request = _source_capture_packet(wire)
    source.require(parsed == spec and verified == protocol, "SOURCE_CAPTURE_PACKET")
    source._protocol_check(spec, protocol)
    root = Path(spec.output)
    inputs.no_links(root)
    source.require(not root.exists(), "OUTPUT_CONFLICT")
    source._make_directory(root)
    with _SourceCaptureHostAuthority(request, runtime_authorize) as host:
        try:
            result = run_bounded_worker(
                MODULE,
                (
                    "--source-capture-worker",
                    "--source-capture-packet",
                    wire,
                    "--source-capture-host",
                    str(host.path),
                ),
                root / "control",
                spec.resources,
            )
        except BaseException as executor_error:
            if host.failure is not None and not isinstance(host.failure, Exception):
                raise host.failure from executor_error
            raise
    if host.failure is not None:
        raise host.failure
    source.require(result["state"] == "COMPLETE", "SOURCE_CAPTURE_WORKER_FAILED")
    return {
        "controller": result,
        "scope_hash": source.capture_scope_hash(spec),
        "host_authorization_requests": host.requests,
        "source_qualified": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--synthetic", action="store_true")
    modes.add_argument("--real", action="store_true")
    modes.add_argument("--fixture-worker", action="store_true")
    modes.add_argument("--catalog-worker", action="store_true", help=argparse.SUPPRESS)
    modes.add_argument(
        "--source-capture-worker", action="store_true", help=argparse.SUPPRESS
    )
    modes.add_argument("--replay", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--format", choices=("csv", "duckdb"), default="csv")
    parser.add_argument("--catalog-packet", help=argparse.SUPPRESS)
    parser.add_argument("--catalog-host", help=argparse.SUPPRESS)
    parser.add_argument("--source-capture-packet", help=argparse.SUPPRESS)
    parser.add_argument("--source-capture-host", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.real:
            raise inputs.InputError("REAL_INPUT_NOT_ADMITTED")
        if args.source_capture_worker:
            inputs.require(
                args.output is None
                and args.catalog_packet is None
                and args.catalog_host is None,
                "MODE_CONFLICT",
            )
            _source_capture_worker(args.source_capture_packet, args.source_capture_host)
            return 0
        inputs.require(
            args.source_capture_packet is None and args.source_capture_host is None,
            "MODE_CONFLICT",
        )
        if args.catalog_worker:
            inputs.require(args.output is None, "MODE_CONFLICT")
            _catalog_worker(args.catalog_packet, args.catalog_host)
            return 0
        inputs.require(
            args.catalog_packet is None and args.catalog_host is None, "MODE_CONFLICT"
        )
        if args.replay is not None:
            inputs.require(args.output is None, "MODE_CONFLICT")
            print(replay(args.replay), end="")
            return 0
        inputs.require(args.output is not None, "OUTPUT_REQUIRED")
        if args.fixture_worker:
            evidence = worker_resource_evidence()
            evidence.pop(
                "allocated_bytes", None
            )  # P2's allocation marker is not this workload's peak.
            evidence["readback_scope"] = (
                "kernel setting at worker entry; workload peak reported by controller"
            )
            inputs.require(
                evidence["memory_max"] == 6 * 1024**3, "RESOURCE_NOT_ENFORCED"
            )
            p = run_fixture(
                args.output, source_format=args.format, resource_evidence=evidence
            )
            print(
                json.dumps(
                    {
                        "fixture": True,
                        "fit_calls": p["fit_calls"],
                        "real_source_reads": 0,
                        "http_requests": 0,
                    }
                )
            )
            return 0
        root = args.output.absolute()
        inputs.no_links(root)
        inputs.require(not root.exists(), "OUTPUT_CONFLICT")
        root.mkdir(mode=0o700, parents=True)
        cap = RetroResourceLimits(
            memory_bytes=6 * 1024**3,
            deadline_seconds=120,
            total_seconds=130,
            output_bytes=1024**2,
            storage_bytes=2 * 1024**2,
            max_attempts=1,
        )
        result = run_bounded_worker(
            MODULE,
            (
                "--fixture-worker",
                "--output",
                str(root / "study"),
                "--format",
                args.format,
            ),
            root / "control",
            cap,
        )
        inputs.require(result["state"] == "COMPLETE", "FIXTURE_WORKER_FAILED")
        print(replay(root / "study"), end="")
        return 0
    except (
        inputs.InputError,
        RetroResourceError,
        core.RetrospectiveContractError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ) as error:
        print(
            "LOCAL_BLOCKED: " + str(getattr(error, "code", type(error).__name__)),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
