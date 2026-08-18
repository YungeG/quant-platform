# Integration v2 contract plan

> **Mutable status authority:** [roadmap registry](../roadmap.md#2-status-registry). This plan contains no editable node status.

## `V2-CON-01` — freeze the additive model-build contract

### Outcome

One accepted contract freezes the minimum Feature/Trainer recipe values, one optional ModelBuildPlan, two new Research task kinds/witnesses, ModelBuildEvidence, Backtest model binding, and downstream provenance rules in [Integration v2](../../overall/integration-v2.md).

### Inputs

- accepted Integration v1 / FI-01 receipts;
- Backtest public `ModelArtifactRef` and `ModelRevisionTimeline`;
- existing `model_build_plan = null`, `model_input_bindings`, `resolved_model_refs`, and Validation purpose vocabulary.

### Interface and invariants

- additive schema versions only; v1 bytes and receipts remain immutable;
- Platform never duplicates Backtest model identity types;
- exactly zero or one model plan and one model lineage per Experiment;
- declaration artifacts contain no callable, path, framework object, endpoint, registry, or mutable status;
- non-null model execution cannot start before contract fixture approval.

### Failure precedence

1. `V2_CONTRACT_MISMATCH` — protected fixture differs from normative text.
2. `V2_CONTRACT_UNAPPROVED` — required Platform/Backtest owner approvals are absent.
3. existing v1 contract and Foundation failures.

### Acceptance

- protected fixture: `tests/contracts/integration-v2-model-build-v1.json`;
- architecture test checks exact schema/ownership/exclusions and immutable v1 fixture hash;
- Platform and Backtest owner approvals are recorded against the fixture SHA.

### Dependencies

| Type | Node/artifact | Why |
| --- | --- | --- |
| Contract | FI-01 | v2 is additive to the accepted v1 graph. |
| Contract | Backtest `ModelArtifactRef` / `ModelRevisionTimeline` | model identity remains Backtest-owned. |
| Evidence | owner approvals | both repositories must accept the cross-repository seam. |
| Write conflict | overall design, glossary, roadmap, contract fixture | one contract writer freezes names and ownership. |

### Exclusions

- implementation, model bytes, plugin ABI, actual inference, Shadow/Live/deployment.
