# RP-DG-01 Research decision-grade dispatch acceptance receipt

- **Platform implementation revision:** `6290aad7237ea322a2b20c013f7a772312acb27b`
- **Research accepted revision:** `1557ec1904de6f2a8f8a32c2f37ce038a0daa022`
- **Backtest fan-in revision:** `8de544e7794ee05b652355c9809b5454d7ace494`
- **Status:** ACCEPTED

## Accepted Research behavior

Existing Research artifact schemas and public orchestration remain unchanged. Private exact nominal dispatch now routes:

```text
BacktestCanonicalPublicationRef   → load_completed
BacktestCanonicalPublicationRefV2 → load_completed_v3
AnalysisArtifactRef               → load_analysis
AnalysisArtifactRefV2             → load_analysis_v2
raw ArtifactRef                   → terminal loading only
```

TrialCompletedPublication, AnalysisDerivation, and VerifiedAnalysis accept only the paired V1 or V2 nominal type/schema combinations. Analysis and source publication versions must match. Completed-v3 observations require decision grade plus exact rebuild-verification and proof-publication-manifest ArtifactRefs before a Trial outcome can complete.

The decision-grade shell retains exact V2 publication/analysis refs through TaskOutcome and StrategyCandidate, selects the one decision-grade Trial, and replays without a second run or derivation. A V2 completed-version failure stays the exact provider failure and never retries through V1.

## Verification

- focused Research shell: `39 passed`;
- full Research package: `92 passed`;
- root Research + V2/V5 architecture gate: `105 passed`;
- fresh remote recursive clone at the exact Platform/Research revisions: `105 passed`;
- `uv lock --check`: passed locally and remotely;
- LSP and Ruff `E4,E7,E9,F,I`: clean;
- diff guards: clean;
- remote clone ended with empty `git status --short`.

## Exclusions

This receipt does not accept decision-grade Validation, Promotion governance, real Backtest economic execution through the V2 path, proof decoding, grade synthesis, provider qualification, Shadow implementation, Live/deployment, or any Backtest change.
