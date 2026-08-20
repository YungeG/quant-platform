# Integration v3 positive Promotion contract approval

- **Contract:** `integration-v3-positive-promotion-v1`
- **Protected fixture:** [`tests/contracts/integration-v3-positive-promotion-v1.json`](../tests/contracts/integration-v3-positive-promotion-v1.json)
- **Fixture SHA-256:** `2f826867f54f8c083f9d3574702a8ccaac8c7ebea5e64f57fff791a6b0e500d9`
- **Normative contract:** [`overall/integration-v3.md`](../overall/integration-v3.md)
- **Predecessor receipt:** [`FI-02`](fi-02-receipt.md)
- **Status:** APPROVED

## Owner approvals

| Repository owner | Name | Status | Approved at |
| --- | --- | --- | --- |
| Platform | `YungeG` | APPROVED | `2026-08-20T06:57:25Z` |
| Promotion | `YungeG` | APPROVED | `2026-08-20T06:57:25Z` |

Both approvals bind the exact fixture hash above. Contract approval does not claim package implementation or integrated acceptance.

## Approved decisions

- Reuse the accepted policy, case, review, status, governed-closure, freshness, and publication-fact contracts.
- Add only `PromotionEvaluation@2` and `PromotionDecision@2`; their field sets remain unchanged from `@1`.
- Require a policy whose `required_validation_result` is exactly `supported` before positive evaluation.
- Map a fully satisfied case to `ELIGIBLE`, then deterministically to `shadow_ready`.
- Preserve all v1 negative behavior, including `POSITIVE_PATH_DEFERRED` on the v1 interface.
- Treat `shadow_ready` as immutable evidence only, never operational authorization.
- Require no Backtest change.

## Exclusions

Shadow/Live runtime, deployment, credentials, order routing, RBAC, decision supersession, new Validation methods, model execution, storage infrastructure, and package implementation remain outside this contract.
