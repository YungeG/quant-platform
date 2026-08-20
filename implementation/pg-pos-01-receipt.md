# PG-POS-01 positive Promotion core acceptance receipt

- **Contract fixture SHA-256:** `2f826867f54f8c083f9d3574702a8ccaac8c7ebea5e64f57fff791a6b0e500d9`
- **Platform implementation revision:** `5e309f87edbbf5460b2c1e2d3664d22b67791c47`
- **Promotion accepted revision:** `de10a535b8c6a4da79a3b0f29e1dddd925d23586`
- **Promotion v2 predecessor revision:** `966b5984c430ec61c53b15761099d2620ed028e6`
- **Status:** ACCEPTED

## Accepted behavior

Promotion adds one pure interface without widening or replacing the accepted v1 interface:

```text
evaluate_positive(case, policy, status_snapshot, review_result) -> PositiveEvaluation
decide_positive(PositiveEvaluation) -> rejected | needs_more_evidence | shadow_ready
```

The implementation first executes the accepted v1 governed-closure, publication-fact, freshness, policy, and review evaluation. Only the sole v1 `POSITIVE_PATH_DEFERRED` result under a policy requiring `supported` becomes `ELIGIBLE`; `decide_positive()` then maps it to evidence-only `shadow_ready`.

Existing `evaluate()` and `decide()` remain negative-only. Missing evidence remains `NEEDS_MORE_EVIDENCE`; demonstrated policy failure remains `NOT_ELIGIBLE`; a policy not requiring `supported` fails closed as `PROMOTION_POLICY_NOT_POSITIVE` without a positive Evaluation.

## Verification

- Focused Promotion core: `19 passed`.
- Full Promotion package: `67 passed`.
- Full Platform workspace: `315 passed`.
- Contract/plan architecture guard subset: `23 passed`.
- Promotion and Platform implementation revisions are remotely reachable on their `main` branches.
- LSP, pi-lens, Ruff `E4,E7,E9,F,I`, `uv lock --check`, and diff guards: clean.
- Root Backtest gitlink remains the accepted `033344172b24847e73941bb97a06da0490527edf`; no Backtest change is part of this node.

## Exclusions

PG-POS-01 publishes no `PromotionEvaluation@2` or `PromotionDecision@2` artifact, changes no Promotion ledger/runtime shell, grants no Shadow/Live/deployment capability, and adds no RBAC, decision supersession, credentials, order routing, storage infrastructure, Validation method, or Backtest behavior.
