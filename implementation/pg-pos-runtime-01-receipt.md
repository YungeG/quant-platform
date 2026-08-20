# PG-POS-RUNTIME-01 positive Promotion runtime acceptance receipt

- **Contract fixture SHA-256:** `2f826867f54f8c083f9d3574702a8ccaac8c7ebea5e64f57fff791a6b0e500d9`
- **Platform implementation revision:** `d691fd0a08254ba93afbd6e3c0491de2fd7ea06a`
- **Promotion accepted revision:** `7210621bc56e3d6cc51bb38c0acea6ca6d5ecc03`
- **Pure-core predecessor revision:** `de10a535b8c6a4da79a3b0f29e1dddd925d23586`
- **Status:** ACCEPTED

## Accepted runtime

Promotion adds one public-root operation and result without changing the accepted v1 operation:

```text
evaluate_positive_case(validation_report_ref, policy, actors, foundation, fixture_evidence)
  -> PublishedPositiveDecision
```

The operation reuses the existing runtime orchestration, Promotion ledger, Foundation publication, governed closure, status snapshot, and review checkpoint. Policy, Case, status, review, and snapshot artifacts remain schema version 1; only `PromotionEvaluation` and `PromotionDecision` are published at schema version 2.

A fully satisfied supported case publishes `ELIGIBLE` and `shadow_ready`. Demonstrated policy failure publishes `NOT_ELIGIBLE` and the configured negative decision; request changes or insufficient evidence publish `NEEDS_MORE_EVIDENCE`. Exact replay returns the same refs without new artifact, status, or review entries.

The v1 `evaluate_case()` and `PublishedNegativeDecision` remain unchanged. A non-positive policy fails before Policy or Case publication, and one PromotionCase cannot fork into both v1 and v2 decision chains.

## Verification

- Focused runtime shell: `16 passed`.
- Full Promotion package: `71 passed`.
- Full Platform workspace: `319 passed`.
- Contract/plan architecture guard subset: `23 passed`.
- Promotion and Platform implementation revisions are remotely reachable on their `main` branches.
- LSP, pi-lens, Ruff `E4,E7,E9,F,I`, `uv lock --check`, and diff guards: clean.
- Root Backtest gitlink remains the accepted `033344172b24847e73941bb97a06da0490527edf`; no Backtest change is part of this node.

## Exclusions

This node does not supply real supported Validation evidence, claim integrated positive acceptance, create ShadowSpec/runtime, authorize Live/deployment, add RBAC or decision supersession, expose credentials/order routing, add storage infrastructure, or change Backtest behavior.
