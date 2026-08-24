# DG-THIN-01 real decision-grade fan-in acceptance receipt

- **Protected V5 fixture SHA-256:** `1bd5ec02c990b87521f26ef42f309dc4dadfe1a62a0739a649040a935e513695`
- **BT-PORT-02 fixture SHA-256:** `8884f7595a62995eaf296a7ad5f0518745146905da3e2fd69a92587a9423c4a8`
- **Platform implementation revision:** `2b21c8df40174d5a9a5b9def9a9646c34c587832`
- **Foundation revision:** `9d88ed67a84d06c558276f8bae2206b069bcec8f`
- **Research revision:** `1557ec1904de6f2a8f8a32c2f37ce038a0daa022`
- **Validation revision:** `cd966d92dad2110af7d8b1bf580536f6c3cdb998`
- **Promotion revision:** `8e6dddf5da0494b57cca6990d5024fe4198e6b44`
- **Backtest fan-in revision:** `8de544e7794ee05b652355c9809b5454d7ace494`
- **Status:** ACCEPTED

## Real decision-grade fan-in

One root integration test composes the accepted package operations in a single Foundation:

```text
Research exact V2 execution
  → BT-PORT-02 completed-v3 / analysis-v2
  → singleton decision_grade Validation
  → Admission@2 publication + analysis / Admission@1 metric profile
  → Promotion ELIGIBLE / shadow_ready
```

Research retains the exact V2 publication and analysis refs. The Backtest consumer evidence binds:

```text
simple_period_return = 0.02392
trade_count = 1
result_grade = decision_grade
```

Completed-v3 also retains the exact protected rebuild-verification and proof-publication-manifest refs. Validation persists the exact metric value, trade count, and grade while omitting both proof refs from Platform case evidence. Promotion consumes only the admitted governed refs and publishes the unchanged `PromotionEvaluation@2` and `PromotionDecision@2` field sets with `ELIGIBLE` and `shadow_ready`.

The test-only typed admission bridge performs only canonical nominal-ref wire conversion before invoking the frozen BT-PORT-02 V2 load operations. It performs no proof decoding, fallback, downgrade, unwrap, grade synthesis, or additional verification authority.

Replay returns the same Candidate, Validation report, admissions, Evaluation, and Decision. Provider run/derive counts and every Research, Validation, admission, status, review, Evaluation, and Decision log length remain unchanged.

## Verification

- focused DG-THIN integration: `1 passed`;
- V1-V3 and V5 compatibility subset: `6 passed`;
- full local Platform workspace: `359 passed`;
- fresh remote recursive clone at exact Platform revision `2b21c8df40174d5a9a5b9def9a9646c34c587832`: `359 passed`;
- stale V3 Promotion and historical Backtest binding guards were tightened to require the current accepted gitlinks plus ancestry of their protected predecessor revisions;
- `uv lock --check`: passed locally and in the fresh clone;
- LSP, Ruff `E4,E7,E9,F,I`, pi-lens, and diff guards: clean;
- independent read-only review found one missing persisted-evidence value assertion; exact `0.02392`, one trade, and `decision_grade` assertions were added before acceptance;
- the fresh recursive clone ended with empty `git status --short`.

## Exclusions

`shadow_ready` remains evidence only. This receipt adds no Platform proof decoder, proof ownership, provider qualification, grade synthesis, ShadowSpec implementation, Shadow runtime, Live/deployment authority, RBAC, credentials, order routing, infrastructure, or Backtest code/schema/fixture/gitlink change.
