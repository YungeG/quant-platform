# Quant Platform Design

`platform/` is the independent implementation root for Foundation, Research Platform, Strategy Validation, and Promotion Gate. The sibling `crypto-quant-platform/` pilot is retained only as immutable static historical evidence; it is not callable or an authority for Backtest economics.

## Documents

- [Integration v1 — authoritative cross-module contract](overall/integration-v1.md)
- [Overall design](overall/design.md)
- [Foundation](foundation/design.md)
- [Research Platform](research-platform/design.md)
- [Strategy Validation](strategy-validation/design.md)
- [Promotion Gate](promotion-gate/design.md)
- [Platform glossary](CONTEXT.md#platform-glossary)
- [Implementation roadmap](implementation/roadmap.md)
- [Module implementation plans](implementation/plans/README.md#integration-v1-implementation-plans)
- [Backtest Platform integration extension register](implementation/backtest-integration-gap-register.md)
- [Backtest provider handoff](implementation/backtest-provider-handoff.md)
- [P00-CON-01 receipt](implementation/p00-contract-v1.md)
- [P00-CON-02 proposal](implementation/p00-contract-v2.md)

## Current status

Platform-owned Integration v1 decisions are frozen and accepted; no integrated runtime is claimed. `PLAT-REC-01` fixes Platform request construction with Backtest-owned validation/identity, and `PLAT-REC-02` fixes integration-owned Backtest evidence admission time. The sole mutable node state and immediate Ready queue are in the [implementation roadmap](implementation/roadmap.md#2-status-registry).

P00-CON-01 is immutable. P00-CON-02 approval details live in its [proposal](implementation/p00-contract-v2.md), while mutable gate state lives only in the roadmap registry. The narrow rule remains unchanged: existing static capture plus retirement evidence satisfies `P00-LEG-01`/`P00-CUT-01`, and hermetic replay is not a P00-PLAT prerequisite.

Root workspace/lock creation rules and their current gate state live in [P00-PLAT-01](implementation/plans/foundation.md#p00-plat-01--package-and-root-workspace-acceptance) and the roadmap registry. No leaf lock is a Platform lock.

## Integrated v1 flow

```text
Research Platform core + accepted Backtest public binding
→ Backtest public evidence and analysis
→ Strategy Validation
→ Promotion Gate
→ rejected | needs_more_evidence
```

`shadow_ready`, ShadowSpec, Live authorization, deployment, and a second historical simulator are explicitly outside v1.
