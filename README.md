# Quant Platform Design

`platform/` is the independent implementation root for Foundation, Research Platform, Strategy Validation, and Promotion Gate. The sibling `crypto-quant-platform/` pilot is retained only as immutable static historical evidence; it is not callable or an authority for Backtest economics.

## Documents

- [Integration v1 — accepted cross-module contract](overall/integration-v1.md)
- [Integration v2 — additive model-build contract](overall/integration-v2.md)
- [Integration v3 — positive Promotion governance contract](overall/integration-v3.md)
- [Overall design](overall/design.md)
- [Foundation](foundation/design.md)
- [Research Platform](research-platform/design.md)
- [Strategy Validation](strategy-validation/design.md)
- [Promotion Gate](promotion-gate/design.md)
- [Platform glossary](CONTEXT.md#platform-glossary)
- [Implementation roadmap](implementation/roadmap.md)
- [Module implementation plans](implementation/plans/README.md#plan-map)
- [Backtest Platform integration extension register](implementation/backtest-integration-gap-register.md)
- [Backtest provider handoff](implementation/backtest-provider-handoff.md)
- [P00-CON-01 receipt](implementation/p00-contract-v1.md)
- [P00-CON-02 proposal](implementation/p00-contract-v2.md)

## Current status

Integration v1 and Integration v2 are accepted, published, and tagged `integration-v1` and `integration-v2`. V2 adds immutable Feature/Trainer recipes, one optional ModelBuildPlan, and Backtest model identity binding without adding a plugin framework or deployment path. The evidence-only Integration v3 positive Promotion contract, pure core, and runtime publication are accepted; integrated positive acceptance against real supported Validation evidence remains pending. The sole mutable node state is in the [implementation roadmap](implementation/roadmap.md#2-status-registry).

P00-CON-01 is immutable. P00-CON-02 approval details live in its [proposal](implementation/p00-contract-v2.md), while mutable gate state lives only in the roadmap registry. The narrow rule remains unchanged: existing static capture plus retirement evidence satisfies `P00-LEG-01`/`P00-CUT-01`, and hermetic replay is not a P00-PLAT prerequisite.

Root workspace/lock creation rules and their current gate state live in [P00-PLAT-01](implementation/plans/foundation.md#p00-plat-01--package-and-root-workspace-acceptance) and the roadmap registry. No leaf lock is a Platform lock.

## Integrated flow

```text
Research Platform core + optional ModelBuild provenance
→ accepted model-bound Backtest public evidence and analysis
→ Strategy Validation
→ Promotion Gate
→ rejected | needs_more_evidence
```

Feature/model byte formats, callable/plugin/framework ABI, actual model loading/inference, tuning/search, `shadow_ready`, ShadowSpec, Live authorization, deployment, and a second historical simulator remain outside v2.
