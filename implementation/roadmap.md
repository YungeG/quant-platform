# Platform implementation roadmap — Integration v1

> **Status:** Platform cores and P00-PLAT are implemented; accepted Backtest source revision `e3c04fb612d6798aef1420b60864d4f315ed12ac` includes BT-GAP-09 plus durable FAILED repository acceptance; real P00-BTA/P00-SEAM binding is implemented and awaits clean committed revisions/receipts.

This file is the sole mutable status registry and release DAG. Normative schemas/state rules remain in [Integration v1](../overall/integration-v1.md); node instructions live in [implementation plans](plans/README.md#integration-v1-implementation-plans); Platform-specific provider extensions live in the [Backtest Platform Integration Extension Register](backtest-integration-gap-register.md).

## 1. Outcome and non-goals

```text
Frozen Experiment
→ public Backtest evidence
→ exact CandidateFamily
→ precommitted admission + OOS ValidationReport(rejected)
→ PromotionDecision(needs_more_evidence)
```

Platform work may advance generic Foundation logs and module-owned ledger plans while the provider lane is deferred. It may not claim a real provider seam, accepted SHA, root lock, thin-node receipt, or whole-flow acceptance from fixtures.

There is no second simulator, Pilot adapter, fifth provider adapter package, queue, database, service, generic DAG engine, Feature/Model interface, positive Promotion, Shadow runtime, deployment, or economic-parity claim in v1.

`PLAT-REC-01` fixes Platform intent/context construction with Backtest-owned request registration and identity. `PLAT-REC-02` fixes integration-owned first Backtest evidence admission. `PLAT-REC-03` fixes the additive executable v2 transport. BT-GAP-09 plus durable FAILED repository evidence PASS at source revision `e3c04fb612d6798aef1420b60864d4f315ed12ac`; Platform clean binding receipts remain the P00 fan-in step.

## 2. Status registry

These states are authoritative. Subplans link here rather than maintaining duplicate status fields.

| Item | State | Meaning / next unblock |
| --- | --- | --- |
| `P00-CON-01` | APPROVED_IMMUTABLE | v1 fixture/hash remains unchanged |
| `P00-CON-02` | APPROVED | both repository-owner approvals recorded; static legacy evidence gate clarified without hermetic replay |
| `P00-LEG-01`, `P00-CUT-01` | HISTORICAL_EVIDENCE | static capture/retirement retained; not runtime proof |
| `BT-PORT-01` | DONE | consumer fixture/support and mutation suite pass |
| `P00-BTA-01` | DONE | clean-clone binding accepted in [`p00-bta-01-receipt.md`](p00-bta-01-receipt.md) at Platform revision `7aa76dc2de65fb713a146e27651538dd755d5231` |
| `PF-LOG-01` | DONE | generic append/clock, issued-checkpoint membership, immutable-prefix implementation, and focused mutation suite pass |
| `PF-CORE-01` | DONE | exact Domain Envelope CAS, verified structural reads, idempotent replay, and failure mutations pass without Backtest decoding |
| `P00-PLAT-01` | DONE | clean-clone workspace/lock acceptance recorded in [`p00-plat-01-receipt.md`](p00-plat-01-receipt.md) at Platform revision `bb75f2d903111be55be23bcb2d730c8cdec3bf3a` |
| `RP-CORE-02` | DONE | pure Experiment/task/manifest/family/selection core passes |
| `SV-CORE-01` | DONE | pure admission/OOS/report core passes |
| `PG-CORE-01` | DONE | pure status/review/freshness/negative-decision core passes |
| `SV-LEDGER-01` | DONE | shared reservation/snapshot/assessment interface and focused mutation suite pass |
| `PG-LEDGER-01` | DONE | Promotion status/review append, immutable cutoff reconstruction, and focused mutation suite pass |
| `RP-SHELL-01` | DONE | fixture-backed Research runtime, durable partial replay, and focused shell suite pass; real provider acceptance remains blocked |
| `SV-SHELL-01` | DONE | fixture-backed Validation runtime, canonical replay reuse, and focused shell suite pass; real provider acceptance remains blocked |
| `PG-SHELL-01` | DONE | fixture-backed Promotion runtime, exact-Case decision replay, and focused shell suite pass; real validation/admission acceptance remains blocked |
| `P00-SEAM-01` | DONE | real Foundation/Backtest fan-in accepted in [`p00-seam-01-receipt.md`](p00-seam-01-receipt.md) |
| `PLAT-ADM-01` | READY | P00-SEAM and PF-CORE accepted; implement first evidence admission composition |
| `RP-THIN-02` | READY | RP-SHELL and P00-SEAM accepted; run real Research acceptance |
| `SV-THIN-01` | WAITING_RESEARCH | waits for SV-SHELL, RP-THIN, and P00-SEAM real acceptance |
| `PG-THIN-01` | WAITING_VALIDATION | waits for PG-SHELL, SV-THIN, and PLAT-ADM real acceptance |
| `FI-01` | WAITING_LEAVES | waits for all three integrated thin receipts |
| `RP-THIN-01`, `SV-00A-core`, `PG-SYN-1` | FROZEN | existing local slices remain authoritative and distinct from integrated artifacts |

## 3. Execution DAG

```text
Integration §3 log/clock contract
        └─→ PF-LOG-01 [DONE]
                └─→ PF-CORE-01 [DONE]
                        ├─→ SV-LEDGER-01 [DONE]
                        ├─→ PG-LEDGER-01 [DONE]
                        └─→ P00-PLAT-01 ────────────────┐
                                                       │
provider acceptance ─→ P00-BTA-01 ─────────────────────┤
                                                       ↓
                                                P00-SEAM-01
                                                       ├─→ PLAT-ADM-01
                                                       │
BT-PORT-01 ─┬─→ RP-CORE-02 [DONE]
            ├─→ SV-CORE-01 [DONE]
            └─→ PG-CORE-01 [DONE]

PF-CORE-01 + SV-LEDGER-01 + RP-CORE-02 + BT-PORT-01 ─→ RP-SHELL-01 ─┐
PF-CORE-01 + SV-LEDGER-01 + SV-CORE-01 + BT-PORT-01 ─→ SV-SHELL-01 ─┼─ parallel package fan-out
PF-CORE-01 + PG-LEDGER-01 + PG-CORE-01 + frozen wires ─→ PG-SHELL-01 ┘

RP-SHELL-01 + P00-SEAM-01 ─────────────────────────────→ RP-THIN-02
SV-SHELL-01 + RP-THIN-02 + P00-SEAM-01 ───────────────→ SV-THIN-01
PG-SHELL-01 + SV-THIN-01 + PLAT-ADM-01 ───────────────→ PG-THIN-01
                                                                  ↓
                                                                FI-01
```

The graph is acyclic:

- Validation owns the shared sample-ledger interface consumed by Research producers.
- Research produces the candidate later consumed by Validation.
- This is a package/interface dependency, not a runtime result cycle: `SV-LEDGER-01` does not consume a candidate or run Validation cases.
- RP/SV/PG SHELL nodes consume frozen fixture contracts, not sibling runtime receipts, so their package writes are independent.
- Real THIN acceptance remains sequential because Validation consumes the real Research candidate and Promotion consumes the real Validation report/admission facts.
- Promotion consumes admission facts but never creates them.

## 4. Typed dependencies

| Node | Contract dependency | Evidence dependency | Write conflict |
| --- | --- | --- | --- |
| `PF-LOG-01` | Integration §3 receipt/clock/checkpoint contract | none | Foundation public root and `storage.py` |
| `PF-CORE-01` | PF-LOG + Domain `ArtifactRef`/Envelope v1 | accepted Domain public type tests | same Foundation files |
| `SV-LEDGER-01` | PF-CORE + Frozen sample semantics | reservation/checkpoint golden | Validation public root/ledger |
| `PG-LEDGER-01` | PF-CORE + PG status/review wires | status/review checkpoint golden | Promotion public root/ledger |
| `RP-CORE-02` | Integration §4 + BT-PORT fixture | deterministic task/analysis fixtures | Research core module |
| `SV-CORE-01` | Integration §5 + BT-PORT/Research wires | adverse/terminal fixtures | Validation core module |
| `PG-CORE-01` | Integration §6 + BT-PORT/Research/Validation wires | governed status/review fixtures | Promotion core module |
| `P00-PLAT-01` | PF-CORE + accepted package roots | approvals, accepted SHA, clean install | root `pyproject.toml`/`uv.lock` |
| `RP-SHELL-01` | RP core + PF core + SV ledger + BT-PORT | fixture task/terminal/analysis observations | Research runtime/public root |
| `SV-SHELL-01` | SV core/ledger + PF core + frozen Research/BT-PORT wires | fixture candidate/OOS observations | Validation runtime/public root |
| `PG-SHELL-01` | PG core/ledger + PF core + frozen Validation/admission wires | fixture governed graph/reviews | Promotion runtime/public root |
| `P00-SEAM-01` | P00-BTA + P00-PLAT | completed/terminal/analysis provider records | integration binding test/receipt |
| `PLAT-ADM-01` | P00-SEAM repository + PF-CORE | admission replay/tamper evidence | integration support/test/receipt |
| `RP-THIN-02` | RP-SHELL + P00 seam | real provider observations | Research integrated test/receipt |
| `SV-THIN-01` | SV-SHELL + RP candidate + P00 seam | real adverse OOS evidence | Validation integrated test/receipt |
| `PG-THIN-01` | PG-SHELL + SV report + PLAT-ADM | real status/review/admission facts | Promotion integrated test/receipt |
| `FI-01` | all thin receipts | clean replay and cross-module provenance | integration golden/receipt |

## 5. Plan index

Node instructions, owned write areas, focused commands, and exclusions live only in the [implementation plan map](plans/README.md#plan-map). This roadmap does not duplicate those editable details.

## 6. Ready queue and WIP

| Priority | Node | Unblocks | Write set | State |
| --- | --- | --- | --- | --- |
| 1 | `PF-LOG-01` | PF-CORE and concrete ledger planning/tests | Foundation package | DONE |
| 2 | `PF-CORE-01` | SV/PG ledgers and P00-PLAT | Foundation package | DONE |
| 3 | `SV-LEDGER-01` | RP/SV shell fan-out | Validation package | DONE |
| 4 | `PG-LEDGER-01` | PG shell | Promotion package | DONE |
| 5 | `RP-SHELL-01` | RP real acceptance | Research package | DONE |
| 6 | `SV-SHELL-01` | SV real acceptance | Validation package | DONE |
| 7 | `PG-SHELL-01` | PG real acceptance | Promotion package | DONE |
| 8 | `RP-THIN-02` | Validation real acceptance | integrated Research test/receipt | WAITING provider seam |
| 9 | `SV-THIN-01` | Promotion real acceptance | integrated Validation test/receipt | WAITING RP/provider seam |
| 10 | `PG-THIN-01` | FI-01 | integrated Promotion test/receipt | WAITING SV/admission |

`RP-SHELL-01`, `SV-SHELL-01`, and `PG-SHELL-01` are DONE. Keep one writer per package. Root lock, status registry, real THIN tests, and receipts remain serialized. The parked provider lane consumes no Platform writer slot.

## 7. P00 fan-in complete

P00-PLAT, P00-BTA, and P00-SEAM are accepted. The authoritative receipts are:

- [`P00-PLAT-01`](p00-plat-01-receipt.md)
- [`P00-BTA-01`](p00-bta-01-receipt.md)
- [`P00-SEAM-01`](p00-seam-01-receipt.md)

P00-PLAT owns one non-package `platform/pyproject.toml` workspace coordinator and one root `platform/uv.lock`; no leaf lock is retained or treated as a Platform lock. The ready queue now advances to `PLAT-ADM-01` and `RP-THIN-02`. No thin or FI receipt is implied by P00 acceptance.

The approved P00-CON-02 clarification remains narrow: existing immutable static capture plus retirement evidence suffices for P00-LEG-01/P00-CUT-01; hermetic replay is not a P00-PLAT prerequisite. It does not approve runtime or provider work.

## 8. Golden path and proof ownership

```text
2 parameters × 2 seeds = 4 TrialDeclarations
3 completed, 1 durable BLOCKED
4 AnalysisTasks; blocked Trial Analysis is BLOCKED
selected T10-1
OOS simple_period_return = -0.1, trade_count = 1
ValidationReport = rejected
PromotionDecision = needs_more_evidence
```

Focused plans own malformed leaf behavior. `FI-01` owns only cross-module provenance, immutable cutoff reuse, first-admission linkage, whole-flow replay, and clean lock/import closure. See [fan-in proof ownership](plans/fan-in.md#proof-ownership).

## 9. Deferred scope

v1 excludes Feature/model/trainer interface; non-null model build; range/adaptive search; walk-forward/stress/capacity/bootstrap/selection-bias methods; positive Promotion, ShadowSpec/Runtime, Live authorization, credentials, and deployment; cryptographic RBAC; database/queue/distributed/object-store writers; proof of uninstrumented reads; physical legacy deletion; pilot parity; and any deployable application/service.
