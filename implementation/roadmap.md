# Platform implementation roadmap

> **Status:** Integration v1 is released at `integration-v1`; Integration v2 model-build contract work is active.

This file is the sole mutable status registry and release DAG. Normative schemas/state rules live in [Integration v1](../overall/integration-v1.md) and additive [Integration v2](../overall/integration-v2.md); node instructions live in the [implementation plan map](plans/README.md#plan-map).

## 1. Outcome and non-goals

```text
Frozen Experiment
→ optional FeatureBuild / ModelTraining provenance
→ model-bound public Backtest evidence
→ exact CandidateFamily
→ precommitted admission + OOS ValidationReport(rejected)
→ PromotionDecision(needs_more_evidence)
```

Integration v1 acceptance is complete. Fixture-backed shell proofs remain distinct from the real P00, THIN, admission, and FI receipts that close the release DAG.

V2 adds immutable Feature/Trainer recipes, one optional ModelBuildPlan, and Backtest model identity binding. It adds no second simulator, fifth adapter package, callable/plugin/framework ABI, model loader/inference, tuning/search, queue, database, service, generic DAG engine, positive Promotion, Shadow runtime, or deployment.

`PLAT-REC-01` fixes Platform intent/context construction with Backtest-owned request registration and identity. `PLAT-REC-02` fixes integration-owned first Backtest evidence admission. `PLAT-REC-03` fixes the additive executable v2 transport. BT-GAP-09 plus durable FAILED repository evidence PASS at source revision `e3c04fb612d6798aef1420b60864d4f315ed12ac`; P00, admission, all three THIN nodes, and FI-01 have clean receipts.

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
| `RP-SHELL-01` | DONE | fixture-backed Research runtime, durable partial replay, and focused shell suite pass; real binding is recorded separately by RP-THIN-02 |
| `SV-SHELL-01` | DONE | fixture-backed Validation runtime, canonical replay reuse, and focused shell suite pass; real binding is recorded separately by SV-THIN-01 |
| `PG-SHELL-01` | DONE | fixture-backed Promotion runtime, exact-Case decision replay, and focused shell suite pass; real binding is recorded separately by PG-THIN-01 |
| `P00-SEAM-01` | DONE | real Foundation/Backtest fan-in accepted in [`p00-seam-01-receipt.md`](p00-seam-01-receipt.md) |
| `PLAT-ADM-01` | DONE | clean-clone governance admission accepted in [`plat-adm-01-receipt.md`](plat-adm-01-receipt.md) |
| `RP-THIN-02` | DONE | real Research golden accepted in [`rp-thin-02-receipt.md`](rp-thin-02-receipt.md) |
| `SV-THIN-01` | DONE | real Validation rejection accepted in [`sv-thin-01-receipt.md`](sv-thin-01-receipt.md) |
| `PG-THIN-01` | DONE | real negative Promotion accepted in [`pg-thin-01-receipt.md`](pg-thin-01-receipt.md) |
| `FI-01` | DONE | whole-Platform golden accepted in [`fi-01-receipt.md`](fi-01-receipt.md) at revision `c525cb522b5a869565a7261f42d5592144cb5e63` |
| `RP-THIN-01`, `SV-00A-core`, `PG-SYN-1` | FROZEN | existing local slices remain authoritative and distinct from integrated artifacts |
| `V2-CON-01` | ACTIVE | freeze protected model-build contract fixture and record Platform/Backtest owner approvals |
| `MB-CORE-01` | WAITING_CONTRACT | waits for V2-CON schemas and Backtest model type ownership |
| `BT-MODEL-01` | WAITING_CONTRACT | waits for V2-CON; Backtest owner implements additive model-aware public preparation |
| `RP-MODEL-01` | WAITING_CORE_SEAM | waits for MB-CORE, BT-MODEL, and accepted build evidence |
| `V2-SEAM-01` | WAITING_PROVIDER | waits for MB-CORE, BT-MODEL accepted revision, root lock, and real binding |
| `SV-MODEL-01` | WAITING_RESEARCH | waits for RP-MODEL and V2-SEAM real candidate |
| `PG-MODEL-01` | WAITING_VALIDATION | waits for SV-MODEL governed graph |
| `FI-02` | WAITING_LEAVES | waits for V2-SEAM, RP-MODEL, SV-MODEL, and PG-MODEL receipts |

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

Integration v2 adds this acyclic DAG:

```text
FI-01 ─→ V2-CON-01 ─┬─→ MB-CORE-01 ───────────────┐
                     └─→ BT-MODEL-01 ────────┐     │
                                             ├─→ V2-SEAM-01 ─┐
MB-CORE-01 + existing Foundation/SV ledger ──┴─→ RP-MODEL-01 ┤
                                                              ↓
                                                        SV-MODEL-01
                                                              ↓
                                                        PG-MODEL-01
                                                              ↓
                                                            FI-02
```

The graphs are acyclic:

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
| `V2-CON-01` | FI-01 + Backtest public model values | owner approvals and protected fixture | contract docs/fixture/registry |
| `MB-CORE-01` | V2 Feature/Trainer/Plan/build schemas | pure ten-task golden | Research integration/public root |
| `BT-MODEL-01` | V2 contract + Backtest G11H | accepted model-aware provider evidence | Backtest public runtime/provider root |
| `RP-MODEL-01` | MB core + BT model seam + existing ledger | accepted build observation and real model binding | Research runtime/public root |
| `V2-SEAM-01` | MB core + BT model public seam | accepted Backtest revision/root lock | root lock/gitlink/integration receipt |
| `SV-MODEL-01` | real model-bound candidate | build/reservation/Backtest binding evidence | Validation runtime/integrated receipt |
| `PG-MODEL-01` | real model-aware Validation report | owner-log status/review evidence | Promotion runtime/integrated receipt |
| `FI-02` | all v2 receipts | remote clean replay and provenance | integration golden/receipt/release |

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
| 8 | `RP-THIN-02` | Validation real acceptance | integrated Research test/receipt | DONE |
| 9 | `SV-THIN-01` | Promotion real acceptance | integrated Validation test/receipt | DONE |
| 10 | `PG-THIN-01` | FI-01 | integrated Promotion test/receipt | DONE |
| 11 | `FI-01` | Integration v1 release | integration golden/receipt | DONE |

### Integration v2 ready queue

| Priority | Node | Unblocks | Write set | State |
| --- | --- | --- | --- | --- |
| 1 | `V2-CON-01` | MB-CORE and BT-MODEL | contract docs/fixture/registry | ACTIVE |
| 2 | `MB-CORE-01` | RP-MODEL and V2-SEAM | Research pure core/public root | WAITING_CONTRACT |
| 3 | `BT-MODEL-01` | RP-MODEL and V2-SEAM | Backtest public provider/runtime | WAITING_CONTRACT |
| 4 | `RP-MODEL-01` | SV-MODEL | Research runtime/integrated receipt | WAITING_CORE_SEAM |
| 5 | `V2-SEAM-01` | SV-MODEL/FI-02 | root lock/gitlink/integration receipt | WAITING_PROVIDER |
| 6 | `SV-MODEL-01` | PG-MODEL | Validation runtime/integrated receipt | WAITING_RESEARCH |
| 7 | `PG-MODEL-01` | FI-02 | Promotion runtime/integrated receipt | WAITING_VALIDATION |
| 8 | `FI-02` | Integration v2 release | root golden/receipt/release | WAITING_LEAVES |

Keep one active writer. After V2-CON freezes, MB-CORE and Backtest owner work may proceed independently because their write sets are disjoint; root pinning and all fan-in remain serialized.

## 7. Integration v1 accepted

P00-PLAT, P00-BTA, and P00-SEAM are accepted. The authoritative receipts are:

- [`P00-PLAT-01`](p00-plat-01-receipt.md)
- [`P00-BTA-01`](p00-bta-01-receipt.md)
- [`P00-SEAM-01`](p00-seam-01-receipt.md)

P00-PLAT owns one non-package `platform/pyproject.toml` workspace coordinator and one root `platform/uv.lock`; no leaf lock is retained or treated as a Platform lock. `PLAT-ADM-01`, `RP-THIN-02`, `SV-THIN-01`, `PG-THIN-01`, and [`FI-01`](fi-01-receipt.md) are accepted. The serialized release DAG is complete.

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

## 9. Integration v2 golden and deferred scope

```text
1 FeatureBuild + 1 ModelTraining + 4 Trials + 4 Analysis = 10 tasks
one Backtest ModelArtifactRef bound through build evidence, TrialSpec, invocation evidence, and SemanticRun
3 completed Trials, 1 durable BLOCKED
ValidationReport = rejected
PromotionDecision = needs_more_evidence
```

V2 excludes feature/model byte formats, callable/plugin/framework ABI, model loading/inference, multiple model plans, tuning/range/adaptive search, walk-forward/stress/capacity/bootstrap/selection-bias methods, positive Promotion, ShadowSpec/Runtime, Live authorization, credentials, deployment, cryptographic RBAC, database/queue/distributed/object-store writers, and any deployable application/service.
