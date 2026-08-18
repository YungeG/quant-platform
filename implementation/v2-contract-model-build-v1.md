# Integration v2 model-build contract approval

- **Contract:** `integration-v2-model-build-v1`
- **Protected fixture:** [`tests/contracts/integration-v2-model-build-v1.json`](../tests/contracts/integration-v2-model-build-v1.json)
- **Fixture SHA-256:** `9aa07f82f76527e331ba8c9e2dcbca772f69cc316190f4d5d2fbd9ab7f950bc3`
- **Normative design:** [`overall/integration-v2.md`](../overall/integration-v2.md)
- **Predecessor receipt:** [`FI-01`](fi-01-receipt.md)
- **Status:** APPROVED

## Owner approvals

| Repository owner | Name | Status | Approved at |
| --- | --- | --- | --- |
| Platform | `YungeG` | APPROVED | `2026-08-18T02:06:30.933955Z` |
| Backtest | `YungeG` | APPROVED | `2026-08-18T02:06:30.933955Z` |

Both approvals bind the exact fixture hash above. Any byte change creates a new contract candidate and requires both approvals again.

## Frozen decisions

- Platform reuses Backtest `ModelArtifactRef` and `ModelRevisionTimeline`; no duplicate model identity type is permitted.
- One Experiment has zero or one ModelBuildPlan ref and zero or one logical model lineage; ModelBuildPlan omits `experiment_ref` to avoid a recursive content-reference cycle.
- A non-null plan adds exactly `FEATURE_BUILD` and `MODEL_TRAINING`, yielding ten golden tasks.
- Feature/Trainer are immutable recipe contracts, not callable/plugin/framework interfaces.
- Feature and training reservations remain Validation-owned append-before-read evidence.
- Backtest must bind the selected model identity into request, invocation, and SemanticRun evidence before Attempts.
- Validation methods/report vocabulary and negative-only Promotion decisions remain unchanged.

## Exclusions

The approval does not authorize feature/model byte formats, model loading/inference, tuning/search, multiple model plans, positive Promotion, Shadow/Live, credentials, deployment, database, queue, service, or distributed workers.
