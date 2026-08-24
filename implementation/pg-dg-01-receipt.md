# PG-DG-01 decision-grade Promotion acceptance receipt

- **Protected V5 fixture SHA-256:** `1bd5ec02c990b87521f26ef42f309dc4dadfe1a62a0739a649040a935e513695`
- **BT-PORT-02 fixture SHA-256:** `8884f7595a62995eaf296a7ad5f0518745146905da3e2fd69a92587a9423c4a8`
- **Platform binding revision:** `7263625315b71103ca65d6a861792e0687b4e2bb`
- **Promotion accepted revision:** `8e6dddf5da0494b57cca6990d5024fe4198e6b44`
- **Validation accepted revision:** `cd966d92dad2110af7d8b1bf580536f6c3cdb998`
- **Research accepted revision:** `1557ec1904de6f2a8f8a32c2f37ce038a0daa022`
- **Backtest fan-in revision:** `8de544e7794ee05b652355c9809b5454d7ace494`
- **Status:** ACCEPTED

## Accepted Promotion behavior

Existing Promotion public operations, status/review projections, `PromotionEvaluation@2`, and `PromotionDecision@2` field sets remain unchanged. Exact nominal reference identity selects the admission publication fact:

```text
BacktestCanonicalPublicationRef   → Admission@1
AnalysisArtifactRef               → Admission@1
BacktestCanonicalPublicationRefV2 → Admission@2
AnalysisArtifactRefV2             → Admission@2
Backtest metric profile@1         → Admission@1
```

Admission@1 and Admission@2 reuse `platform.backtest-evidence-admission.v1` but require version-distinct canonical event ids and envelope schemas. Substitution is rejected in both directions for completion and analysis subjects.

The governed closure accepts exact completed-v3 and analysis-v2 refs only as a paired V2 path. Completed-v3 must be `decision_grade` and carry typed rebuild-verification and proof-publication-manifest refs. Promotion validates those ref identities without adding them to Platform governed evidence or decoding Backtest proof artifacts.

A supported decision-grade Validation report can produce the existing `ELIGIBLE` → `shadow_ready` result. Policy mismatch remains `NOT_ELIGIBLE` → `rejected`. Positive and negative cases replay without a second admission, status, review, Evaluation, or Decision action. Existing V1-v4 package and integration behavior remains green.

## Verification

- focused PG-DG core/ledger/shell acceptance: `8 passed`;
- symmetric Admission@1/@2 substitution cases: `4 passed`;
- full Promotion package: `84 passed`;
- root V1-V3, Admission, and V5 architecture compatibility subset: `25 passed`;
- fresh remote recursive clone at the exact Platform and Promotion revisions: Promotion `84 passed`, root compatibility `25 passed`;
- `uv lock --check`: passed locally and in the fresh clone;
- LSP, Ruff `E4,E7,E9,F,I`, and diff guards: clean;
- independent read-only review found no correctness issue; its sole low-severity analysis-subject coverage gap was closed before acceptance;
- Promotion and Platform revisions are remotely reachable, and the fresh clone ended with empty `git status --short`.

## Exclusions

This receipt does not accept whole-Platform decision-grade fan-in, a Platform proof decoder, proof ownership, grade synthesis, provider qualification, ShadowSpec implementation, Shadow runtime, Live/deployment, RBAC, credentials, order routing, infrastructure, or any Backtest change.
