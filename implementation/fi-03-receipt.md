# FI-03 whole-Platform positive Promotion acceptance receipt

- **Contract fixture SHA-256:** `2f826867f54f8c083f9d3574702a8ccaac8c7ebea5e64f57fff791a6b0e500d9`
- **Platform golden revision:** `e5ef7093265206c6896972825fdbd0a86fd1a28c`
- **Foundation revision:** `9d88ed67a84d06c558276f8bae2206b069bcec8f`
- **Research revision:** `d2dd913a1efd23728c7889bd15c894d6cf22ad4e`
- **Validation revision:** `41c35219d227fe5cdb736747b917144f6b8a8c65`
- **Promotion revision:** `7210621bc56e3d6cc51bb38c0acea6ca6d5ecc03`
- **Backtest accepted revision:** `033344172b24847e73941bb97a06da0490527edf`
- **Root `uv.lock` SHA-256:** `dcfeab99dfdf28daa9206d8f94315740d288c7f43df89d6ccc21e415e25101ef`
- **Status:** ACCEPTED

## Whole-flow evidence

Integration v3 preserves the accepted Research, Backtest, Validation, and Promotion provenance chain while adding only evidence-level positive Promotion:

```text
real Backtest analysis: simple_period_return = -0.1, trade_count = 1
precommitted Validation rule: gte -0.2, minimum_trade_count = 1
ValidationReport = supported
PromotionEvaluation@2 = ELIGIBLE
PromotionDecision@2 = shadow_ready
```

The exact completed publication, analysis, and metric-profile refs enter Platform governance through the accepted admission seam. Promotion resolves the full governed closure, current/fresh status, and exact independent approving reviews before publishing the `@2` Evaluation and Decision.

Whole-flow replay returns the same Research candidate, Validation report, admission refs, status/review cutoffs, Evaluation, and Decision. It creates no second economic run or additional owner-log, execution, sample, admission, status, review, Evaluation, or Decision entries.

## Leaf receipts

- [`V3-CON-01`](v3-contract-positive-promotion-v1.md)
- [`PG-POS-01`](pg-pos-01-receipt.md)
- [`PG-POS-RUNTIME-01`](pg-pos-runtime-01-receipt.md)
- [`PG-POS-THIN-01`](pg-pos-thin-01-receipt.md)

## Verification

- Full local Platform workspace at the golden revision: `320 passed`.
- Fresh remote recursive clone at the exact golden revision: `320 passed`.
- Remote clone checked out every recorded submodule SHA, passed `uv lock --check`, and ended with empty `git status --short`.
- Focused real positive integration: `1 passed`.
- Contract/plan architecture and integration subset: `24 passed`.
- LSP, pi-lens, Ruff `E4,E7,E9,F,I`, and diff guards: clean.
- Protected Integration v1 and v2 behavior remains covered by the same full workspace suite.

## Exclusions

Integration v3 accepts an evidence-only `shadow_ready` decision. It adds no ShadowSpec/runtime, monitoring, capital allocation, Live/deployment authorization, credentials/order routing, cryptographic RBAC, decision supersession, database/queue/service/distributed worker, new Validation method, model-quality interpretation, or Backtest change.
