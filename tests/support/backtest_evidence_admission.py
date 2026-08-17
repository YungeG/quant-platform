from __future__ import annotations

from crypto_quant_backtest import (
    AnalysisArtifactRef,
    BacktestAnalysisRuntime,
    BacktestCanonicalPublicationRef,
)
from crypto_quant_domain import (
    ArtifactEnvelope,
    ArtifactRef,
    canonical_bytes,
    canonical_sha256,
)
from crypto_quant_foundation import LocalFoundation, LogEntryRef

ADMISSION_LOG = "platform.backtest-evidence-admission.v1"


def admit_backtest_evidence(
    subject_ref: BacktestCanonicalPublicationRef | AnalysisArtifactRef | ArtifactRef,
    repository: object,
    foundation: LocalFoundation,
) -> LogEntryRef:
    """Verify and admit one Backtest subject at its immutable first governance time."""

    if type(foundation) is not LocalFoundation:
        raise TypeError("foundation must be an exact LocalFoundation")
    if type(subject_ref) is BacktestCanonicalPublicationRef:
        repository.load_completed(subject_ref)  # type: ignore[attr-defined]
    elif type(subject_ref) is AnalysisArtifactRef:
        repository.load_analysis(subject_ref)  # type: ignore[attr-defined]
    elif type(subject_ref) is ArtifactRef and (
        subject_ref.artifact_type,
        subject_ref.schema_version,
    ) == ("backtest_metric_profile", 1):
        if BacktestAnalysisRuntime(foundation).publish_metric_profile() != subject_ref:
            raise ValueError("metric profile ref does not bind accepted Backtest profile")
    else:
        raise ValueError("subject_ref must be completed, analysis, or metric-profile ref")

    envelope = ArtifactEnvelope.create(
        "backtest_evidence_admission",
        1,
        {"subject_ref": subject_ref},
    )
    ref = foundation.put(envelope=envelope)
    receipt = foundation.append(
        log_name=ADMISSION_LOG,
        event_id=canonical_sha256(("backtest-evidence-admission-v1", subject_ref)),
        payload=canonical_bytes(envelope),
    )
    stored = foundation.read(ref=ref)
    if stored.source_bytes != canonical_bytes(envelope):
        raise ValueError("admission ref does not bind stored envelope")
    return receipt.entry_ref
