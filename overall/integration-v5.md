# Platform Integration v5 — Decision-grade durable evidence

- **Scope:** exact consumption and governance of Backtest canonical-v3 decision-grade evidence
- **Predecessor:** [Integration v3](integration-v3.md), [`FI-03`](../implementation/fi-03-receipt.md), and protected [`BT-PORT-02`](../tests/contracts/backtest-consumer-port-v2.json)
- **Orthogonal contract:** [Integration v4](integration-v4.md) remains approved and deliberately unimplemented
- **Contract approval:** [`V5-CON-01`](../implementation/v5-contract-decision-grade-proof-v1.md)
- **Status authority:** [roadmap registry](../implementation/roadmap.md#2-status-registry)
- **Status:** accepted by [`FI-04`](../implementation/fi-04-receipt.md) and released as `integration-v5`

## 1. Outcome and ceiling

```text
BacktestCanonicalPublicationRefV2
→ load_completed_v3 (decision_grade + exact durable proof refs)
→ derive
→ AnalysisArtifactRefV2
→ load_analysis_v2
→ Platform admission + Validation + Promotion
```

V5 activates Backtest-owned `decision_grade` evidence in the existing Platform governance chain. It does not reinterpret Backtest proof artifacts, create a second verifier, qualify a provider, establish a trusted copied-tree origin, authorize Live/deployment, or change Backtest.

## 2. Accepted Backtest authority

The protected `BT-PORT-02` vector fixes exact dispatch:

```text
V1 nominal completion → load_completed → derive → load_analysis
V2 nominal completion → load_completed_v3 → derive → load_analysis_v2
raw ArtifactRef → terminal/evaluation handling only
```

The V2 loaded views are:

```python
VerifiedCompletedPublicationV3 = {
  publication_ref: BacktestCanonicalPublicationRefV2,
  semantic_run_id,
  execution_result_hash,
  result_grade: "decision_grade",
  rebuild_verification_ref: Ref[deterministic_rebuild_verification@1],
  proof_publication_manifest_ref:
    Ref[deterministic_rebuild_verification_publication_manifest@1],
}

VerifiedBacktestAnalysisV2 = {
  analysis_ref: AnalysisArtifactRefV2,
  metric_profile_ref,
  source_publication_ref: BacktestCanonicalPublicationRefV2,
  source_execution_result_hash,
  simple_period_return,
  trade_count,
  result_grade: "decision_grade",
}
```

Platform treats these as opaque verified Backtest views. It never decodes the proof artifacts or fabricates their refs.

## 3. BacktestEvidenceAdmission@2

```python
BacktestEvidenceAdmission@2 = {
  subject_ref:
    BacktestCanonicalPublicationRefV2
    | AnalysisArtifactRefV2,
}
```

Admission@2 reuses `platform.backtest-evidence-admission.v1` and its original-time semantics. It verifies the subject through exact `load_completed_v3` or `load_analysis_v2` before append. The metric-profile ref remains admitted through the unchanged `BacktestEvidenceAdmission@1` path.

Admission@1 and its event ids remain unchanged. Admission@2 uses a version-distinct canonical event id, is replay-idempotent, and cannot unwrap a nominal ref, accept a raw manifest/analysis ArtifactRef, downgrade to v1, or recover from a v2 failure through a v1 method.

## 4. Research and candidate binding

Existing Research artifact field sets remain unchanged. Trial outcomes, Analysis outcomes, and StrategyCandidate selected refs may carry the exact V2 nominal variants.

Research provider dispatch must:

1. choose operations by exact nominal type/version;
2. retain the V2 publication and analysis refs unchanged through TaskOutcome and StrategyCandidate;
3. bind the completed/analysis execution-result hash and `decision_grade` exactly;
4. fail closed on unknown wrapper/schema, static-proof mismatch, version mismatch, retention failure, malformed manifest, tamper, or analysis-link mismatch;
5. never unwrap, infer, retry through v1, or downgrade.

## 5. Validation activation

`ValidationPolicy@1` and `ValidationPlan@1` keep their existing field sets. V5 permits exactly one accepted-grade mode per Plan:

```text
("development",) | ("decision_grade",)
```

Mixed grade sets are invalid. Existing development behavior is unchanged.

For `decision_grade`, Validation requires exact V2 dispatch and verifies:

- completed and analysis refs are the selected Candidate refs;
- completed and analysis grades are both `decision_grade`;
- analysis source publication and execution-result hash match the completed view;
- metric profile is accepted and the metric/trade-count wire is canonical;
- the completed view includes exact typed rebuild-verification and proof-publication-manifest refs.

Backtest has already verified the proof graph. Platform does not duplicate those proof refs into `CompletedCaseEvidence` or add them to ValidationReport; the admitted V2 publication content-addresses the verified graph.

Any V2 port, proof, version, manifest, retention, or link failure stops before a ValidationReport. It is never rewritten as a terminal, zero metric, development grade, or inconclusive success.

## 6. Promotion governance

Promotion's governed-ref union additively recognizes `BacktestCanonicalPublicationRefV2` and `AnalysisArtifactRefV2`. Their publication facts resolve only through exact owner-log-published `BacktestEvidenceAdmission@2` entries in the existing admission log.

`PromotionPolicy@1.accepted_backtest_grades` may select `decision_grade`. Existing Evaluation/Decision schemas and mappings remain unchanged. A supported decision-grade report may reach `PromotionDecision@2(shadow_ready)` only after the same status, freshness, review, and limitation rules accepted in v3.

Admission@1 cannot publish a V2 subject, Admission@2 cannot publish a V1 subject, and a V1/V2 publication-fact substitution fails closed.

## 7. Failure precedence

1. exact BT-PORT-02 ref/type/version and evidence failures;
2. Admission@2 subject/version/publication mismatch;
3. Research Candidate/TaskOutcome provenance mismatch;
4. Validation grade mode, completed proof-view, or analysis-link mismatch;
5. existing Validation sample/threshold/report precedence;
6. existing Promotion status/review/policy precedence.

No failure causes heuristic dispatch, v1 fallback, grade downgrade, fabricated proof evidence, or partial governance publication.

## 8. Compatibility

- Integration v1-v4 artifact bytes, decisions, logs, receipts, and release tags remain unchanged.
- `BT-PORT-01` stays protected and every v1 operation/disposition remains exact.
- Existing development-grade Research/Validation/Promotion behavior remains unchanged.
- Domain ArtifactRef/Envelope and Foundation interfaces remain unchanged.
- Backtest remains pinned to the accepted DRP-03 code commit; later Backtest governance commits are docs-only.
- No Backtest code, schema, fixture, branch, gitlink, or runtime change is required.

## 9. Contract acceptance

`V5-CON-01` is approved by Platform, Backtest, Validation, and Promotion owners against the exact protected fixture hash. Approval freezes the contract.

[`V5-PIN-01`](../implementation/v5-pin-01-receipt.md), [`DG-ADM-01`](../implementation/dg-adm-01-receipt.md), [`RP-DG-01`](../implementation/rp-dg-01-receipt.md), [`SV-DG-01`](../implementation/sv-dg-01-receipt.md), [`PG-DG-01`](../implementation/pg-dg-01-receipt.md), and [`DG-THIN-01`](../implementation/dg-thin-01-receipt.md) accept the exact pin, admission, package, and real fan-in leaves. [`FI-04`](../implementation/fi-04-receipt.md) accepts the whole-Platform remote-clone golden and release closure.

Accepted Backtest fan-in `8de544e7794ee05b652355c9809b5454d7ace494` descends from both model-seam revision `033344172b24847e73941bb97a06da0490527edf` and durable-proof revision `cebb9b033b7eeffbbff712715fc017708ac5a247`.

## 10. Explicit exclusions

- provider qualification, trusted/copied-tree origin, future or remote durability guarantees;
- proof-artifact decoding or semantic verification in Platform/Foundation;
- new metrics, Validation methods, thresholds, model-quality interpretation, or grade synthesis;
- ShadowSpec implementation/runtime, Live/deployment, credentials/order routing, RBAC, or decision supersession;
- database, queue, object store, service, scheduler, distributed worker, or generic workflow engine;
- any Backtest change.
