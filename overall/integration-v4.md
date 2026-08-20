# Platform Integration v4 candidate — Immutable ShadowSpec proposal

- **Scope:** one immutable observe-only ShadowSpec that cites an accepted `shadow_ready` decision
- **Predecessor:** [Integration v3](integration-v3.md) and [`FI-03`](../implementation/fi-03-receipt.md)
- **Candidate approval:** [`V4-CON-01`](../implementation/v4-contract-shadow-spec-v1.md)
- **Status authority:** [roadmap registry](../implementation/roadmap.md#2-status-registry)
- **Status:** frozen candidate bytes; not approved or implemented

## 1. Outcome and ceiling

```text
accepted PromotionDecision@2(shadow_ready)
+ immutable future observation window
+ proposer provenance
→ ShadowSpec@1
```

`ShadowSpec@1` is an immutable proposal to observe a promoted strategy during a bounded future window. It creates no Shadow runtime, data subscription, simulated fill, position, capital allocation, alert, rollback action, Live authorization, credential, order, or deployment capability.

V4 adds one future Shadow-module artifact and owner log. Foundation remains generic, Promotion remains the decision authority, and Backtest remains unchanged.

## 2. Ownership

| Module | Owns in v4 | Does not own |
| --- | --- | --- |
| Shadow | `ShadowSpec@1`, exact decision/window validation, `shadow.artifacts.v1` publication | Promotion evaluation, market data, execution, monitoring, Live/deployment |
| Promotion | accepted `PromotionDecision@2` and its immutable provenance chain | ShadowSpec construction or runtime |
| Foundation | generic CAS, append, receipt, checkpoint, and verified structural reads | Shadow decoding or freshness policy |
| Backtest/Research/Validation | unchanged accepted evidence | Shadow proposal or runtime semantics |

The Shadow owner is a future module seam. This candidate creates no package, adapter, worker, or runtime implementation.

## 3. ShadowSpec@1

```python
ShadowSpec@1 = {
  promotion_decision_ref: Ref[PromotionDecision@2],
  proposed_by_ref: ActorRef,
  observation_start: canonical UTC microseconds,
  observation_end: canonical UTC microseconds,
}
```

Candidate v4 supports exactly one observe-only mode, so mode is an invariant rather than a configurable field. Candidate and Validation provenance resolve through the Decision → Evaluation → Case → ValidationReport chain and are never duplicated in the Spec.

## 4. Decision and publication validation

Before publishing a ShadowSpec, the Shadow owner must verify:

1. the Decision and Evaluation are exact owner-log-published schema-v2 artifacts;
2. `PromotionDecision@2.decision == "shadow_ready"`;
3. `PromotionEvaluation@2.result == "ELIGIBLE"` and `reason_codes == ()`;
4. `PromotionDecision@2.limitations == ()`;
5. Decision → Evaluation → PromotionCase → PromotionPolicy and ValidationReport links resolve exactly;
6. the cited policy requires `supported` Validation;
7. the ShadowSpec is published in `shadow.artifacts.v1` before its observation window starts.

Rejected, needs-more-evidence, malformed, unpublished, foreign, substituted, or limitation-bearing decisions cannot produce a ShadowSpec.

## 5. Time and freshness

Let `evaluation_at` be the cited Evaluation's `EvidenceStatusSnapshot.status_log_checkpoint.as_of`, and let `maximum_age` be its PromotionPolicy's `maximum_governed_evidence_age_microseconds`.

The canonical window must satisfy:

```text
shadow_spec_publication_accepted_at
  <= observation_start
  < observation_end
  <= evaluation_at + maximum_age
```

This forces a new positive Promotion evaluation before scheduling a window beyond the accepted policy horizon. Callers cannot choose a past start, open-ended window, alternative clock, or freshness override.

## 6. Compatibility

- Integration v1/v2/v3 artifacts, logs, receipts, schemas, and decisions remain unchanged.
- `shadow_ready` remains evidence only; citing it in a ShadowSpec still grants no operational capability.
- ShadowSpec uses the Domain-owned `ArtifactRef` and canonical Envelope; no nominal duplicate ref is added.
- Foundation gains no Shadow vocabulary or semantic validator.
- Promotion gains no ShadowSpec field, runtime hook, or decision-supersession behavior.
- No Backtest schema, code, fixture, gitlink, or runtime changes.

## 7. Candidate acceptance

`V4-CON-01` may become approved only when Platform, Promotion, and Shadow owners approve the exact protected fixture hash. Approval freezes the contract but does not authorize a package implementation or Shadow runtime.

The first implementation node, if separately authorized, must prove exact decision linkage, limitation rejection, time/freshness bounds, owner-log publication, replay, and structural absence of operational fields.

## 8. Explicit exclusions

- Shadow runtime, market-data subscription, simulated fills/accounting/P&L, monitoring, alerts, rollback, or outcome/report schemas;
- capital/notional/position/risk allocation or execution constraints;
- Live authorization, deployment, credentials, secrets, broker/exchange access, or order routing;
- organizational RBAC, cryptographic authority, reviewer-role proof, or decision supersession;
- database, queue, object store, service, scheduler, distributed worker, or generic workflow engine;
- new Validation methods, model loading/inference, tuning/search, or Backtest behavior.
