# Integration v2 Backtest model seam plan

> **Mutable status authority:** [roadmap registry](../roadmap.md#2-status-registry). This plan contains no editable node status.

## `BT-MODEL-01` — additive public model-aware preparation

### Outcome

Backtest exposes one additive public preparation path that accepts already-built `ModelArtifactRef` evidence, applies `ModelRevisionTimeline` point-in-time selection, and binds the selected model identity into Strategy invocation evidence and SemanticRun identity before any Attempt.

### Interface behavior

Equivalent public behavior to:

```text
prepare_model_bound_backtest(
  request_intent,
  provider_inputs,
  model_timelines,
  structural_reader/publisher,
  market_reader,
  publication_root,
) -> PreparedBacktestExecution
```

The exact name is Backtest-owned. Platform passes only public immutable values. Backtest constructs requests, registries, resolved cases, execution transport, model visibility, and identities internally.

The seam verifies:

- each timeline has one unique model key and point-in-time terminal selection;
- selected `artifact_ref_hash` / `timeline_hash` are persisted in request/runtime evidence;
- model identity enters SemanticRun derivation only when the executed Strategy declares that model input;
- missing, future, conflicting, substituted, or wrong-key evidence fails before Attempt creation;
- replay/cache validates the same model evidence rather than trusting caller memory.

### Failure precedence

1. existing structural read/integrity/retention failures;
2. `MODEL_TIMELINE_INVALID`;
3. `MODEL_ARTIFACT_UNAVAILABLE`;
4. `MODEL_BINDING_MISMATCH`;
5. existing request/profile/hydration/execution failures.

### Acceptance

- one completed and one blocked model-bound public run;
- changed model revision changes request/SemanticRun identity;
- future revision does not alter an earlier run;
- wrong key/schema/hash/substitution fails before Attempt;
- repository and invocation evidence recover the exact selected model hash;
- public-root AST guard; no model bytes/loader/framework/runtime training.

### Dependencies

| Type | Node/artifact | Why |
| --- | --- | --- |
| Contract | V2-CON-01 | freezes Platform expectations without owning Backtest spelling. |
| Contract | accepted G11H model revision values | existing point-in-time authority is reused. |
| Evidence | Backtest owner acceptance commit | Platform cannot claim the seam from a dirty checkout. |
| Write conflict | Backtest public runtime/provider root | single Backtest owner controls implementation and release. |

### Exclusions

- offline training, feature computation, model deserialization, arbitrary inference ABI, private resolved-object exposure, deployment.

## `V2-SEAM-01` — Platform/Backtest model fan-in

### Outcome

A clean root lock proves one Research ModelBuildEvidence and one model-bound Trial execute through the accepted Backtest public seam with exact Foundation transport and no copied model identity.

### Acceptance

- root dependency pin and Backtest gitlink are remote-reachable accepted revisions;
- real ModelBuildEvidence ↔ Backtest selected model hash equality;
- model substitution/retention/tamper pre-Attempt failure;
- v1 cash-development binding remains unchanged;
- clean clone, public imports, lock check, and focused Research/Backtest integration suite.

### Dependencies

| Type | Node/artifact | Why |
| --- | --- | --- |
| Contract | MB-CORE-01 | supplies canonical Platform build evidence. |
| Contract | BT-MODEL-01 | supplies executable model-aware authority. |
| Evidence | accepted Backtest revision/root lock | required for a real seam receipt. |
| Write conflict | root lock/gitlink/integration receipt | serialized fan-in owner. |

### Exclusions

- Validation/Promotion acceptance, generic adapter package, second model identity type.
