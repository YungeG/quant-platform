from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest
from crypto_quant_backtest import (
    AnalysisArtifactRef,
    BacktestAnalysisRuntime,
    BacktestCanonicalPublicationRef,
    BacktestEvidenceError,
    BacktestEvidenceFailureCode,
)
from crypto_quant_domain import (
    ArtifactEnvelope,
    ArtifactRef,
    canonical_bytes,
    canonical_sha256,
)
from crypto_quant_foundation import FoundationFailure, LocalFoundation

from tests.support.backtest_evidence_admission import (
    ADMISSION_LOG,
    admit_backtest_evidence,
)

_FIRST = "2026-08-18T00:00:00.000000Z"
_LATER = "2026-08-18T00:00:01.000000Z"


def _completed_ref(digit: str = "1") -> BacktestCanonicalPublicationRef:
    return BacktestCanonicalPublicationRef.from_artifact_ref(
        ArtifactRef("canonical_publication_manifest", 1, "sha256:" + digit * 64)
    )


def _analysis_ref(digit: str = "2") -> AnalysisArtifactRef:
    return AnalysisArtifactRef(
        ArtifactRef("backtest_analysis", 1, "sha256:" + digit * 64)
    )


@dataclass
class _Repository:
    failure: BacktestEvidenceError | None = None
    completed: list[BacktestCanonicalPublicationRef] = field(default_factory=list)
    analyses: list[AnalysisArtifactRef] = field(default_factory=list)

    def load_completed(self, ref: BacktestCanonicalPublicationRef) -> object:
        self.completed.append(ref)
        if self.failure is not None:
            raise self.failure
        return object()

    def load_analysis(self, ref: AnalysisArtifactRef) -> object:
        self.analyses.append(ref)
        if self.failure is not None:
            raise self.failure
        return object()


def _foundation(tmp_path) -> LocalFoundation:
    values = iter((_FIRST, _LATER, _LATER, _LATER, _LATER))
    return LocalFoundation(tmp_path, clock=lambda: next(values))


def _admission_envelope(foundation: LocalFoundation) -> ArtifactEnvelope:
    entry = foundation.entries(log_name=ADMISSION_LOG)[0]
    return ArtifactEnvelope(**json.loads(entry.payload))


@pytest.mark.parametrize("subject", (_completed_ref(), _analysis_ref()))
def test_verified_subject_is_admitted_once_at_its_first_governance_time(
    tmp_path,
    subject,
) -> None:
    foundation = _foundation(tmp_path)
    repository = _Repository()

    first = admit_backtest_evidence(subject, repository, foundation)
    replay = admit_backtest_evidence(subject, repository, foundation)

    assert replay == first
    entries = foundation.entries(log_name=ADMISSION_LOG)
    assert len(entries) == 1
    assert entries[0].accepted_at == _FIRST
    assert entries[0].entry_ref == first
    envelope = _admission_envelope(foundation)
    assert envelope.artifact_type == "backtest_evidence_admission"
    assert envelope.schema_version == 1
    assert set(envelope.payload) == {"subject_ref"}
    assert canonical_bytes(envelope.payload["subject_ref"]) == canonical_bytes(subject)
    assert "accepted_at" not in envelope.payload
    if type(subject) is BacktestCanonicalPublicationRef:
        assert repository.completed == [subject, subject]
        assert repository.analyses == []
    else:
        assert repository.analyses == [subject, subject]
        assert repository.completed == []


def test_metric_profile_uses_backtest_publication_authority_before_admission(
    tmp_path,
) -> None:
    foundation = _foundation(tmp_path)
    repository = _Repository()
    profile_ref = BacktestAnalysisRuntime(foundation).publish_metric_profile()

    entry_ref = admit_backtest_evidence(profile_ref, repository, foundation)

    assert entry_ref.log_name == ADMISSION_LOG
    assert repository.completed == repository.analyses == []
    assert foundation.read(ref=profile_ref).envelope.artifact_type == (
        "backtest_metric_profile"
    )


@pytest.mark.parametrize(
    "code",
    (
        BacktestEvidenceFailureCode.PORT_REF_NOT_FOUND,
        BacktestEvidenceFailureCode.PORT_EVIDENCE_TAMPERED,
        BacktestEvidenceFailureCode.PORT_RETENTION_UNAVAILABLE,
    ),
)
def test_repository_failure_precedes_foundation_admission(tmp_path, code) -> None:
    foundation = _foundation(tmp_path)
    repository = _Repository(BacktestEvidenceError(code, code.value))

    with pytest.raises(BacktestEvidenceError) as raised:
        admit_backtest_evidence(_completed_ref(), repository, foundation)

    assert raised.value.code is code
    assert foundation.entries(log_name=ADMISSION_LOG) == ()


def test_wrong_subject_kind_and_forged_subject_fail_without_admission(tmp_path) -> None:
    foundation = _foundation(tmp_path)
    repository = _Repository(
        BacktestEvidenceError(
            BacktestEvidenceFailureCode.PORT_REF_NOT_FOUND,
            "forged publication",
        )
    )

    with pytest.raises(ValueError, match="completed, analysis, or metric-profile"):
        admit_backtest_evidence(
            ArtifactRef("evidence_manifest", 1, "sha256:" + "3" * 64),
            repository,
            foundation,
        )
    with pytest.raises(BacktestEvidenceError):
        admit_backtest_evidence(_completed_ref("4"), repository, foundation)
    assert foundation.entries(log_name=ADMISSION_LOG) == ()


def test_conflict_wrong_log_and_later_status_cannot_replace_first_admission(
    tmp_path,
) -> None:
    foundation = _foundation(tmp_path)
    repository = _Repository()
    subject = _completed_ref()
    envelope = ArtifactEnvelope.create(
        "backtest_evidence_admission",
        1,
        {"subject_ref": subject},
    )
    event_id = canonical_sha256(("backtest-evidence-admission-v1", subject))
    foundation.append(
        log_name="wrong.owner.log",
        event_id=event_id,
        payload=canonical_bytes(envelope),
    )

    entry_ref = admit_backtest_evidence(subject, repository, foundation)
    admitted = foundation.entries(log_name=ADMISSION_LOG)[0]
    first_time = admitted.accepted_at
    assert entry_ref == admitted.entry_ref

    conflicting = ArtifactEnvelope.create(
        "backtest_evidence_admission",
        1,
        {"subject_ref": _completed_ref("5")},
    )
    with pytest.raises(FoundationFailure) as conflict:
        foundation.append(
            log_name=ADMISSION_LOG,
            event_id=event_id,
            payload=canonical_bytes(conflicting),
        )
    assert conflict.value.code == "LOG_CONFLICT"

    foundation.append(
        log_name="promotion.evidence-status.v1",
        event_id="later-publish",
        payload=b"later status cannot refresh admission",
    )
    assert foundation.entries(log_name=ADMISSION_LOG)[0].accepted_at == first_time
