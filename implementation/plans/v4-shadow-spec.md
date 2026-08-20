# Integration v4 ShadowSpec contract plan

- **Normative candidate:** [Integration v4](../../overall/integration-v4.md)
- **Mutable status authority:** [Roadmap §2](../roadmap.md#2-status-registry)
- **Protected fixture:** [`integration-v4-shadow-spec-v1.json`](../../tests/contracts/integration-v4-shadow-spec-v1.json)

This plan owns only the contract approval node. No Shadow package or runtime implementation is authorized before exact owner approval.

## Execution DAG

```text
FI-03 ─→ V4-CON-01
```

## `V4-CON-01` — immutable observe-only ShadowSpec contract

### Outcome

Platform, Promotion, and Shadow owners approve one additive `ShadowSpec@1` contract that cites an accepted limitation-free `PromotionDecision@2(shadow_ready)` and precommits a bounded observation window without granting an operational capability.

### Dependencies

- accepted [`FI-03`](../fi-03-receipt.md);
- accepted Promotion v3 Decision/Evaluation schemas and exact provenance chain;
- unchanged Domain ArtifactRef/Envelope and Foundation generic storage/log interfaces;
- no new Backtest dependency.

### Interface

The candidate adds only:

```text
ShadowSpec@1(
  promotion_decision_ref,
  proposed_by_ref,
  observation_start,
  observation_end,
)
```

Candidate and Validation provenance resolve through the Decision chain. Observe-only mode is fixed and therefore not a configuration field.

### Invariants

1. Decision is owner-log-published `PromotionDecision@2(shadow_ready)` with empty limitations.
2. Evaluation is owner-log-published `PromotionEvaluation@2(ELIGIBLE)` with empty reason codes.
3. Policy requires `supported` Validation and every linkage resolves exactly.
4. ShadowSpec publication precedes the start, and the whole window ends within the Promotion policy age horizon measured from `evaluation_at`.
5. ShadowSpec publishes only to `shadow.artifacts.v1` through the Domain Envelope/Foundation interface.
6. No runtime, market-data, fill, position, capital, Live/deploy, credential, or order authority.
7. No Backtest change.

### Failure precedence

1. malformed, unpublished, foreign, or substituted Decision/Evaluation chain;
2. Decision not `shadow_ready` or Evaluation not `ELIGIBLE`;
3. nonempty Decision limitations or Evaluation reason codes;
4. invalid proposer or canonical timestamp;
5. stale, past, open-ended, reversed, or post-publication window;
6. wrong owner log or publication failure.

Every failure produces no ShadowSpec publication.

### Write set

- `overall/integration-v4.md`;
- `tests/contracts/integration-v4-shadow-spec-v1.json`;
- `implementation/v4-contract-shadow-spec-v1.md`;
- roadmap, plan map, README, glossary, and contract architecture guard only.

### Acceptance

```bash
uv run pytest -q -p no:cacheprovider tests/architecture/test_integration_v4_design.py
```

The guard must bind the exact fixture hash, pending owner approvals, schema field set, exact decision/time rules, v1-v3 compatibility, Backtest independence, and absence of operational authority.

### Exclusions

Shadow package/runtime, monitoring/outcomes, market-data subscription, fills/accounting/P&L, capital/risk allocation, Live/deployment, RBAC, decision supersession, infrastructure, and any Backtest change.
