# Integration v1 implementation plans

This directory owns node-level implementation instructions. The [roadmap status registry and execution DAG](../roadmap.md#2-status-registry) are the sole mutable authority for node state and readiness; subplans intentionally do not repeat editable status fields.

## Outcome

Implement the accepted Platform flow as deep modules with small interfaces:

```text
Foundation exact storage/logs
→ Research exact Experiment closure and selection
→ Validation authoritative sample ledger and OOS report
→ Promotion governed-evidence negative decision
```

Provider execution remains an external seam. Deferring it does not require the Platform modules to stop refining or implementing contract-independent work, and it never permits fixture behavior to be called production integration.

## Global invariants

- Backtest remains the sole authority for simulation economics, canonical run/terminal evidence, integrity, and derived metrics.
- Platform creates no second `ArtifactRef`, Envelope, simulator, profit/loss calculation, metrics engine, or evidence verifier.
- Foundation is generic; Validation owns sample-consumption semantics; Promotion owns status/review semantics; integration composition owns Backtest evidence admission.
- Core modules consume immutable explicit values and return immutable results. I/O and publication stay in thin shells or their owning ledger module.
- Cross-package calls use accepted public roots. Internal pure-core interfaces may remain package-internal.
- One module exposes one deep orchestration operation rather than public step-by-step CAS/log/provider choreography.
- A CAS object is not evidence until exact owner-log publication. A failed append means no authorized sample read.
- Only completed Backtest publication reaches analysis. Missing metrics are missing/inconclusive, never zero.
- Positive Promotion, Shadow/Live authorization, deployment, database, queue, distributed writer, and generic DAG remain outside v1.

## Plan map

| Plan | Vertical nodes | Owned write area |
| --- | --- | --- |
| [Foundation](foundation.md) | `PF-LOG-01`, `PF-CORE-01`, `P00-PLAT-01` | Foundation package; root workspace only at P00-PLAT |
| [Research](research.md) | `RP-CORE-02`, `RP-SHELL-01`, `RP-THIN-02` | Research package and receipt |
| [Strategy Validation](validation.md) | `SV-CORE-01`, `SV-LEDGER-01`, `SV-SHELL-01`, `SV-THIN-01` | Validation package and receipt |
| [Promotion Gate](promotion.md) | `PG-CORE-01`, `PG-LEDGER-01`, `PG-SHELL-01`, `PG-THIN-01` | Promotion package and receipt |
| [Integration fan-in](fan-in.md) | `P00-SEAM-01`, `PLAT-ADM-01`, `FI-01` | integration tests/support and receipts only |
| [Backtest contract/binding](backtest-port.md) | `BT-PORT-01`, `P00-BTA-01` | consumer fixture/support; provider work remains external |

Provider-owner requirements are packaged separately in the [Backtest Provider Handoff](../backtest-provider-handoff.md). They are not duplicated into module plans.

## Node contract

Every future implementation node must state and preserve:

1. one caller-visible or independently verifiable outcome;
2. consumed frozen contracts/evidence;
3. one small module interface and its caller obligations;
4. identity, ordering, publication, and no-partial-success invariants;
5. per-operation failure precedence;
6. exact write set and single-writer owner;
7. focused acceptance command and mutation budget;
8. explicit exclusions and fan-in destination.

Implemented nodes record current interface and executable evidence instead of pretending completed work is still a future checklist. Acceptance records describe executed facts; plans never manufacture commits, hashes, or receipts.

## Dependency types

- **Contract:** a type, wire rule, interface, or invariant must exist first.
- **Evidence:** a fixture, accepted SHA, receipt, or provider proof is required to claim acceptance.
- **Write conflict:** work is logically independent but touches the same public root, runtime file, registry, root lock, or receipt.

Gate IDs alone are insufficient in subplans; each dependency table names the artifact or interface crossing the edge.

## WIP policy

- one active writer while shared Foundation and ledger interfaces are changing;
- after PF-CORE, SV-LEDGER, and PG-LEDGER reach focused GREEN, `RP/SV/PG-SHELL-01` may use up to three isolated module writers because their write sets are disjoint;
- each shell reaches focused GREEN in its own worktree before one named fan-in owner integrates them;
- shared public roots within one package, root workspace/lock, status registry, real THIN tests, and receipts remain serialized;
- read-only review may run in parallel, and a blocked external provider lane does not consume Platform WIP.

The immediate Ready node and all blocked reasons live only in the [roadmap ready queue](../roadmap.md#6-ready-queue-and-wip).

## Proof budget

| Risk | Required proof |
| --- | --- |
| canonical identity, receipt chain, time, publication, sample cutoff | focused golden + tamper/conflict/clock/checkpoint mutations |
| shared module interface or cross-module composition | interface-level focused test + import/ownership guard |
| money-derived observation | accepted provider evidence; Platform fixture only before real seam |
| pure task/selection/report/evaluation logic | one golden + targeted malformed/foreign/link cases |
| thin-node acceptance | focused real-seam test + owning receipt |
| release fan-in | one clean full suite + lock/import/hash/docs guards + cross-module golden |
| documentation/status only | link/fence/JSON/status-authority checks; no unrelated full provider suite |

FI runs every focused suite but its own test adds only cross-module assertions; it does not copy every leaf mutation into one giant test.
