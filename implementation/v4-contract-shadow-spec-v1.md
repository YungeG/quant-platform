# Integration v4 ShadowSpec contract candidate

- **Contract:** `integration-v4-shadow-spec-v1`
- **Protected fixture:** [`tests/contracts/integration-v4-shadow-spec-v1.json`](../tests/contracts/integration-v4-shadow-spec-v1.json)
- **Fixture SHA-256:** `0f030a47ffb5ac3b64d40330ab72686e04e4e85feddec7d489c9ae34f5c7ece7`
- **Normative candidate:** [`overall/integration-v4.md`](../overall/integration-v4.md)
- **Predecessor receipt:** [`FI-03`](fi-03-receipt.md)
- **Status:** AWAITING_APPROVAL

## Owner approvals

| Repository owner | Name | Status | Approved at |
| --- | --- | --- | --- |
| Platform | — | PENDING | — |
| Promotion | — | PENDING | — |
| Shadow | — | PENDING | — |

Approval must bind the exact fixture hash above. No Shadow package, runtime, or operational capability is authorized by this candidate packet.

## Frozen candidate decisions

- Add only `ShadowSpec@1(promotion_decision_ref, proposed_by_ref, observation_start, observation_end)`.
- Resolve Candidate and Validation provenance through the accepted Promotion chain instead of duplicating refs.
- Require owner-log-published `shadow_ready` / `ELIGIBLE` artifacts with empty limitations and reason codes.
- Require publication before the start and the whole observation window within the cited PromotionPolicy age horizon.
- Use the Domain ArtifactRef/Envelope and generic Foundation publication; add no nominal Shadow ref.
- Treat observe-only as a fixed invariant, not a configurable mode.
- Require no Backtest change.

## Exclusions

Shadow runtime, monitoring/outcomes, market data, fills/accounting/P&L, positions, capital/risk allocation, Live/deployment, credentials/order routing, RBAC, decision supersession, infrastructure, and package implementation remain outside this contract candidate.
