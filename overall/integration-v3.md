# Platform Integration v3 — Positive Promotion governance

- **Scope:** one additive evidence-only positive Promotion result and decision
- **Predecessor:** [Integration v2](integration-v2.md) and [`FI-02`](../implementation/fi-02-receipt.md)
- **Contract approval:** [`V3-CON-01`](../implementation/v3-contract-positive-promotion-v1.md)
- **Status authority:** [roadmap registry](../implementation/roadmap.md#2-status-registry)
- **Status:** approved contract; pure core revision published, package acceptance/runtime/integration pending

## 1. Outcome and ceiling

```text
supported ValidationReport
+ current and fresh governed-evidence closure
+ exact independent approving reviews
→ PromotionEvaluation@2(ELIGIBLE)
→ PromotionDecision@2(shadow_ready)
```

`shadow_ready` is an immutable governance conclusion only. It permits a future Shadow proposal to cite the Decision; it does not create a ShadowSpec, start a runtime, authorize Live trading or deployment, grant credentials, or route orders.

V3 reuses the accepted v1/v2 governed closure, publication facts, freshness calculation, review checkpoint, and failure precedence. It adds no Backtest type, field, import, implementation, or acceptance dependency.

## 2. Reused authority

The following accepted artifacts remain unchanged:

- `PromotionPolicy@1`;
- `PromotionCase@1`;
- `PromotionReview@1`;
- `EvidenceStatusSnapshot@1`;
- the v2 governed-evidence closure;
- Foundation CAS, append, receipt, and checkpoint interfaces;
- ValidationReport and Backtest evidence schemas.

A positive evaluation accepts only a `PromotionPolicy@1` whose `required_validation_result` is exactly `supported`. Any other policy is invalid for the v3 positive interface and produces no `PromotionEvaluation@2`.

## 3. Additive schemas

```python
PromotionEvaluation@2 = {
  promotion_case_ref,
  evidence_status_snapshot_ref: Ref[EvidenceStatusSnapshot@1],
  review_log_checkpoint: LogCheckpoint("promotion.reviews.v1"),
  result: "NOT_ELIGIBLE" | "NEEDS_MORE_EVIDENCE" | "ELIGIBLE",
  reason_codes,
}

PromotionDecision@2 = {
  promotion_evaluation_ref,
  decider_ref: ActorRef,
  decision: "rejected" | "needs_more_evidence" | "shadow_ready",
  rationale,
  limitations,
}
```

The schemas are versioned because their result vocabularies widen. Their field sets remain unchanged from `@1`.

## 4. Evaluation rules

Evaluation first applies every accepted v1/v2 structural, closure, publication-fact, cutoff, freshness, policy, and review check.

| Condition | `PromotionEvaluation@2.result` |
| --- | --- |
| recognized revoked evidence, policy mismatch, forbidden limitation, or approving-role review verdict `reject` | `NOT_ELIGIBLE` |
| missing, superseded, or stale evidence; incomplete reviews; or verdict `request_changes` | `NEEDS_MORE_EVIDENCE` |
| supported report, satisfied positive policy, every governed ref current and fresh, exact required-role cover, distinct independent reviewers, and every verdict `approve` | `ELIGIBLE` |

`ELIGIBLE` requires `reason_codes = ()`. It is never inferred from absent evidence, an unchecked actor claim, or a caller-supplied boolean.

Malformed graphs, status chains, publication facts, checkpoints, refs, or policy values remain fail-closed errors and produce no Evaluation or Decision. A policy whose `required_validation_result != "supported"` fails before evaluation as `PROMOTION_POLICY_NOT_POSITIVE`.

## 5. Decision mapping

| Evaluation | Decision |
| --- | --- |
| `NOT_ELIGIBLE` | existing `PromotionPolicy@1.decision_for_not_eligible` |
| `NEEDS_MORE_EVIDENCE` | `needs_more_evidence` |
| `ELIGIBLE` | `shadow_ready` |

The mapping is deterministic. `decider_ref` remains provenance in the trusted local-writer model, not cryptographic authority. `shadow_ready` grants no operational capability.

## 6. Compatibility

- `PromotionEvaluation@1`, `PromotionDecision@1`, and their negative-only implementation remain byte- and behavior-compatible.
- `POSITIVE_PATH_DEFERRED` remains the required v1 result when the old interface receives otherwise positive inputs.
- No existing fixture, receipt, owner-log name, Backtest ref, ValidationReport, Candidate, or model-build artifact changes.
- Implementations must expose the v3 behavior through an additive interface; they must not widen the accepted v1 interface in place.

## 7. Contract acceptance

`V3-CON-01` is approved by Platform and Promotion owners against the exact protected fixture hash. The approval freezes this contract but does not claim package implementation or a positive integrated receipt.

`PG-POS-01` implements the additive pure core and proves the three result mappings, unchanged v1 behavior, fail-closed malformed inputs, and structural absence of Shadow/Live/deployment capabilities. It does not publish `@2` artifacts or claim integrated positive evidence.

## 8. Explicit exclusions

- ShadowSpec, Shadow runtime, monitoring, rollback, or capital allocation;
- Live authorization, deployment, credentials, secrets, broker/exchange access, or order routing;
- cryptographic actor authority, organizational RBAC, or real-world reviewer independence;
- decision supersession or mutable promotion state;
- new Validation methods, thresholds, or report vocabulary;
- new model loader, inference, registry, tuning, or search behavior;
- any Backtest schema, code, fixture, submodule revision, or runtime change;
- database, queue, distributed worker, service, or generic workflow engine.
