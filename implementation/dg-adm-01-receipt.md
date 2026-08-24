# DG-ADM-01 BacktestEvidenceAdmission@2 acceptance receipt

- **Platform implementation revision:** `bc396ab6763298bb3cec3e28edab9e2a72186d95`
- **Backtest fan-in revision:** `8de544e7794ee05b652355c9809b5454d7ace494`
- **Admission owner log:** `platform.backtest-evidence-admission.v1`
- **Status:** ACCEPTED

## Accepted admission behavior

The existing `admit_backtest_evidence()` operation now selects admission schema and verification solely by the exact subject type:

```text
BacktestCanonicalPublicationRef   → load_completed    → Admission@1
AnalysisArtifactRef               → load_analysis     → Admission@1
BacktestCanonicalPublicationRefV2 → load_completed_v3 → Admission@2
AnalysisArtifactRefV2             → load_analysis_v2  → Admission@2
Backtest metric profile ArtifactRef@1                → Admission@1
```

Admission@1 and Admission@2 reuse the existing owner log but use version-distinct canonical event ids. Exact replay retains the first governance entry/time. Raw V2 manifest/analysis ArtifactRefs, wrong subject kinds, repository failures, and V1/V2 substitution fail before admission.

## Verification

- focused local admission plus V5 architecture gate: `22 passed`;
- fresh remote recursive clone at the exact implementation revision: `22 passed`;
- `uv lock --check`: passed locally and remotely;
- LSP and Ruff `E4,E7,E9,F,I`: clean;
- diff guard: clean;
- remote clone ended with empty `git status --short`.

## Exclusions

This receipt does not accept Research V2 dispatch, decision-grade Validation, Promotion publication facts, proof decoding, grade synthesis, provider qualification, Shadow implementation, Live/deployment, or any Backtest change.
