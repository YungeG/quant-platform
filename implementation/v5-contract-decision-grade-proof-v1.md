# Integration v5 decision-grade durable evidence contract approval

- **Contract:** `integration-v5-decision-grade-proof-v1`
- **Protected fixture:** [`tests/contracts/integration-v5-decision-grade-proof-v1.json`](../tests/contracts/integration-v5-decision-grade-proof-v1.json)
- **Fixture SHA-256:** `1bd5ec02c990b87521f26ef42f309dc4dadfe1a62a0739a649040a935e513695`
- **Normative contract:** [`overall/integration-v5.md`](../overall/integration-v5.md)
- **Predecessor receipt:** [`FI-03`](fi-03-receipt.md)
- **Backtest consumer fixture:** `BT-PORT-02` / `8884f7595a62995eaf296a7ad5f0518745146905da3e2fd69a92587a9423c4a8`
- **Status:** APPROVED

## Owner approvals

| Repository owner | Name | Status | Approved at |
| --- | --- | --- | --- |
| Platform | `YungeG` | APPROVED | `2026-08-24T02:48:28Z` |
| Backtest | `YungeG` | APPROVED | `2026-08-24T02:48:28Z` |
| Validation | `YungeG` | APPROVED | `2026-08-24T02:48:28Z` |
| Promotion | `YungeG` | APPROVED | `2026-08-24T02:48:28Z` |

All approvals bind the exact fixture hash above. Contract approval authorizes the specified Platform integration work but no Backtest change.

## Approved decisions

- Dispatch V1/V2 completed and analysis operations only by exact nominal type/version.
- Add `BacktestEvidenceAdmission@2` for V2 completion/analysis refs in the existing admission log; retain metric-profile Admission@1.
- Preserve Research artifact field sets while retaining V2 refs, hash, and grade exactly.
- Activate exactly one Validation grade mode per Plan: development or decision_grade; mixed modes are invalid.
- Require exact completed-v3 proof refs and analysis-v2 links without duplicating Backtest proof semantics in Platform evidence.
- Extend Promotion governed refs/publication facts to Admission@2 while preserving Evaluation/Decision schemas.
- Preserve BT-PORT-01 and Integration v1-v4 unchanged.
- Require no Backtest change.

## Exclusions

Provider qualification, trusted copied-tree origin, future/remote durability guarantees, proof decoding, new metrics or Validation methods, grade synthesis, Shadow implementation, Live/deployment, credentials/order routing, RBAC, infrastructure, and any Backtest change remain outside this contract.
