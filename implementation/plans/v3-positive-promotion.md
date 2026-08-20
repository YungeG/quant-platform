# Integration v3 positive Promotion implementation plan

- **Normative contract:** [Integration v3](../../overall/integration-v3.md)
- **Mutable status authority:** [Roadmap §2](../roadmap.md#2-status-registry)
- **Protected fixture:** [`integration-v3-positive-promotion-v1.json`](../../tests/contracts/integration-v3-positive-promotion-v1.json)

This plan owns the approved contract and the additive pure Promotion core. Runtime publication and integrated acceptance remain separate future nodes.

## Execution DAG

```text
FI-02 ─→ V3-CON-01 [APPROVED] ─→ PG-POS-01
```

## `V3-CON-01` — positive Promotion governance contract

### Outcome

Platform and Promotion owners approved one additive contract that maps an otherwise fully satisfied supported Promotion case to `PromotionEvaluation@2(ELIGIBLE)` and `PromotionDecision@2(shadow_ready)` without granting an operational capability.

### Dependencies

- accepted [`FI-02`](../fi-02-receipt.md);
- accepted v1/v2 Promotion governed closure, publication facts, freshness, review, and negative decision rules;
- no new Backtest dependency.

### Interface

The contract reuses `PromotionPolicy@1`, `PromotionCase@1`, `PromotionReview@1`, and `EvidenceStatusSnapshot@1`. It adds only `PromotionEvaluation@2` and `PromotionDecision@2` with unchanged field sets and additive result vocabularies.

### Invariants

1. Positive evaluation accepts only a policy requiring `supported` Validation.
2. `ELIGIBLE` requires current/fresh exact governed closure and complete independent approving reviews.
3. `shadow_ready` is evidence only and grants no Shadow, Live, deployment, credential, or order capability.
4. Every v1 artifact and `POSITIVE_PATH_DEFERRED` behavior remains unchanged.
5. No Backtest schema, code, fixture, revision, import, or runtime changes.

### Failure precedence

1. existing malformed case/closure/status/publication/checkpoint failures;
2. `PROMOTION_POLICY_NOT_POSITIVE` before Evaluation publication;
3. existing revoked/policy-failed mapping to `NOT_ELIGIBLE`;
4. existing missing/superseded/stale/review-insufficient mapping to `NEEDS_MORE_EVIDENCE`;
5. no remaining reason permits `ELIGIBLE`.

### Write set

- `overall/integration-v3.md`;
- `tests/contracts/integration-v3-positive-promotion-v1.json`;
- `implementation/v3-contract-positive-promotion-v1.md`;
- roadmap, plan-map, README, and contract architecture guard only.

### Acceptance

```bash
uv run pytest -q -p no:cacheprovider tests/architecture/test_integration_v3_design.py
```

The guard must bind the exact fixture hash and owner approvals, additive schemas, deterministic decision mapping, unchanged v1 behavior, Backtest independence, and absence of operational authorization.

### Exclusions

Promotion implementation, real positive evidence, ShadowSpec/runtime, Live/deployment, RBAC, decision supersession, and any Backtest change.

## `PG-POS-01` — additive positive Promotion core

### Outcome

The existing governed-evidence core exposes one additive interface that returns `ELIGIBLE` only for the accepted v1 `POSITIVE_PATH_DEFERRED` condition under a policy requiring `supported`, then maps it to evidence-only `shadow_ready`.

### Dependencies

- approved `V3-CON-01` fixture and owner approvals;
- accepted `PG-CORE-01` closure, status, freshness, policy, review, and negative mapping;
- no runtime, ledger, sibling implementation, or Backtest dependency.

### Interface

```text
evaluate_positive(case, policy, status_snapshot, review_result) -> PositiveEvaluation
decide_positive(PositiveEvaluation) -> rejected | needs_more_evidence | shadow_ready
```

The implementation calls the accepted v1 evaluator first. It converts only the sole `POSITIVE_PATH_DEFERRED` result to `ELIGIBLE`; every negative result and failure remains owned by the existing core.

### Invariants

1. `evaluate()` and `decide()` remain negative-only and byte/behavior compatible.
2. A policy not requiring `supported` fails as `PROMOTION_POLICY_NOT_POSITIVE` and produces no positive Evaluation.
3. `ELIGIBLE` has empty reason codes and maps only to `shadow_ready`.
4. `shadow_ready` remains a string decision value, never a field or capability handle.
5. No runtime publication, ledger change, sibling import, or Backtest change.

### Failure precedence

1. accepted v1 malformed case/closure/status/publication/checkpoint failures;
2. `PROMOTION_POLICY_NOT_POSITIVE`;
3. accepted `NOT_ELIGIBLE` and `NEEDS_MORE_EVIDENCE` mappings;
4. sole reason-free positive path to `ELIGIBLE`.

### Write set

- `promotion-gate/src/crypto_quant_promotion/integration.py`;
- `promotion-gate/tests/test_promotion_core.py`.

### Acceptance

```bash
uv run pytest -q -p no:cacheprovider promotion-gate/tests/test_promotion_core.py
```

Required evidence covers `ELIGIBLE → shadow_ready`, all existing negative mappings, non-positive policy rejection, and unchanged v1 `POSITIVE_PATH_DEFERRED` behavior. Published implementation revision: `de10a535b8c6a4da79a3b0f29e1dddd925d23586`; package acceptance remains separate.

### Exclusions

Promotion runtime/publication, public shell exports, integrated supported evidence, ShadowSpec/runtime, Live/deployment, RBAC, decision supersession, and any Backtest change.
