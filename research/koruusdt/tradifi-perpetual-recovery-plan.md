# KORU TradFi Backtest Recovery Plan

Status: **ACTIVE — discovery execution blocked until Phase 3 acceptance**

## Goal

Deliver an exact, reproducible Binance USD-M `KORUUSDT` `TRADIFI_PERPETUAL` discovery Backtest for the frozen eight-parameter closed-market strategy, then run the untouched holdout only after its precommitted close.

This plan replaces the prior debug loop: no more retained full rebuild or actual p01 run may be used to discover ordinary price-shape, role, schema, or identity defects.

## Authorities and invariants

| ID | Source | Requirement |
| --- | --- | --- |
| R1 | `research/koruusdt/closed-market-range-plan.md` | Eight frozen parameter sets, seed 0, discovery and holdout half-open windows, deterministic selection. |
| R2 | `research/koruusdt/tradifi-perpetual-capability-contract.md` and amendments | Exact TradFi identity; no ordinary alias/fallback; Backtest owns economics. |
| R3 | `research/koruusdt/tradifi-perpetual-implementation-packet.md` | Public preparation and durable replay; ordinary V1 behavior remains immutable. |
| R4 | `research/koruusdt/data/execution_gap_impact.json` | Retained aggTrade gap is admissible only while all parameter impact checks remain clear. |
| R5 | `.agents/skills/quant-strategy-research/SKILL.md` | Formal discovery must use public Research publication/execution seams; local Engine output is not Experiment/Analysis/Candidate evidence. |
| R6 | `~/.pi/agent/AGENTS.md` | Run representative same-path smoke tests before high-cost or large-data work. |

### Hard stops

- No network, credential, order, capital, Shadow, Live, or holdout activity.
- No `p01` or all-eight retained run until its phase gate passes.
- No V1 profile/wire/dispatcher/input artifact byte changes.
- No custom PnL, funding, margin, liquidation, metric, or selection simulator.
- A local direct-run report is diagnostic only until public Research integration publishes governed trial evidence.

## Recovery baseline

- Research branch: `research/koruusdt`; Backtest branch: `feature/tradifi-perpetual-preparation`.
- Prior actual p01 attempts produced no report and fail-closed on sequential implementation defects. They are diagnostic evidence only.
- Completed runtime capabilities include BundleV2 authority, public preparation, Schema7 mutation-aware batch liquidation audit, and raw exact valuation/margin/funding/strategy/liquidation model lanes. Their final integrated acceptance is not yet complete.
- Retained data stays immutable under `research/koruusdt/data/`; no production data is moved to fixtures.

## Dependency DAG

```text
P0 Freeze & classify current diff
  └─ P1 Retained-shape preflight matrix
       └─ P2 Runtime correctness matrix
            ├─ P2a raw price-purpose authority/model closure
            ├─ P2b mutation-window batch audit + Schema7 durable closure
            └─ P2c multiple-funding identity/role closure
                 └─ P2d thin funding-evidence Schema8 closure
                      └─ P2e V2 authority-reverification throughput closure
                           └─ P3 Integrated public smoke acceptance
                      ├─ P4 one retained context rebuild + canonical validation
                      │    └─ P5 actual p01 single-arm gate
                      │         └─ P6 same-context eight-arm local diagnostic run
                      └─ P7 public Research execution/publication integration
                           └─ P8 formal frozen discovery and deterministic selection
                                └─ P9 holdout after 2026-10-05T00:00:00Z
```

`P3` requires P2a–P2e; `P4` requires `P3`; `P5` requires `P4`; `P6` requires a successful `P5`; `P8` requires `P7`. No phase may skip an unmet upstream gate.

## Phases

### P0 — Freeze and classify

**Outcome:** One clean Backtest candidate commit and one clean Research candidate commit; current retained artifacts identified as either current or stale.

**Acceptance:**
- `git status --short` clean in both worktrees after commits.
- Current commits and artifact hashes recorded in the plan receipt/update.
- No active writer or background workflow.

### P1 — Retained-shape preflight matrix

**Outcome:** Fast read-only preflight proves every retained price shape used by the strategy is covered by an explicit model policy before retained Backtest execution.

**Coverage:**
- execution aggTrade price sample: tick-aligned;
- strategy mark close: raw scale allowed under explicit KORU authority;
- valuation mark: raw scale allowed under explicit KORU authority;
- margin mark: raw scale allowed under explicit KORU authority;
- liquidation low/high: raw scale allowed under explicit KORU authority;
- funding mark: exact V2 profile evidence reused, not reparsed/scaled;
- index data is evidence-only for the target strategy and is not substituted for a Mark purpose.

**Acceptance:**
- A research test reads only retained CSV/ZIP samples and records these invariants.
- A Backtest fixture covers one non-tick value for each raw-enabled purpose and one tick-aligned aggTrade price.
- Any unclassified raw numeric field blocks P4/P5.

### P2 — Runtime correctness matrix

#### P2a — Price-purpose/model identity

**Outcome:** Explicit KORU profile-wire authorities select V2 raw-exact models only for the declared purposes. V1 requests omit every new flag and retain exact bytes/hashes.

**Acceptance:**
- V1 profile/wire/component/dispatcher golden suites pass.
- KORU source-profile authority, profile wire, BundleV2 request, and dispatcher specs bind every true raw-purpose flag.
- Unknown/nonexact V2 component refs fail closed; the frozen dynamic V1 component path is documented as a legacy compatibility baseline whose trust boundary is ProfileResolver/composition.

#### P2b — Mutation-window liquidation and durable replay

**Outcome:** Each non-flat hourly interval has ordered mutation-delimited audit subwindows, uses the same retained full hourly bar as conservative evidence, and uses exact Engine before/after checkpoints.

**Acceptance:**
- Schema7 / plan@3 batch payload round-trips and V7-to-V6 downgrade fails.
- V1–V6 canonical fixtures remain exact.
- A public tiny BundleV2 flow covers entry, exit, funding, two or more subwindows, atomic failure, Schema7 fresh durable rebuild, and final flat result.

#### P2c — Multiple funding events

**Outcome:** V2 funding artifacts are derived exactly from settlement identity and are globally unique; V1 names and funding identity ordinals remain frozen.

**Acceptance:**
- At least two valid V2 funding slots during a non-flat interval execute successfully.
- Roles are exactly derived from settlement identity; no prefix, absent-role, or arbitrary-role fallback.
- All retained KORU funding resolutions preflight to unique settlement identities and role pairs.
- V1 funding source and ordinary profile golden suites pass.

#### P2d — Thin funding-evidence Schema8 closure

**Outcome:** KORU V2 funding eligibility/settlement evidence no longer embeds a growing full ledger replay in every one of 120 slots.

**Required versioned seam:**
- `LinearFundingEligibilityPositionSnapshotV2` carries exact snapshot/series/revision/slot/timing identity, availability and cutoff cursors, ledger-state hashes, replay hashes, and immutable position states; it never carries an `AccountingJournal` or `LinearDerivativeLedgerProjection` object.
- A distinct V2 eligibility and settlement/accounting lane validates those thin attestations, preserves the existing funding formula/rate/mark/journal semantics, and is selected only by explicit KORU V2 financing authority.
- `execution_input_bundle@8` with `execution_case_plan@4` persists the thin evidence; schemas 1–7 remain byte-compatible and reject V2 thin funding authority.
- Dispatcher and durable rebuild independently derive thin snapshots from the full current ledger replay. The cache is process-local optimization only and is never persisted/trusted.

**Acceptance:**
- Actual 120-slot source-profile wire resolves one-record V2 funding books and preserves bounded V2 funding-resolution cache counters.
- A public two-slot Schema8 execution has thin funding artifacts, exact current/cutoff replay counters, and hash/cursor/position-state tamper failure before funding accounting.
- Schema8 fresh durable rebuild preserves funding journals and final result hash.
- V1 funding/profile/input golden hashes remain exact.

#### P2e — V2 authority-reverification throughput closure

**Outcome:** Repeated KORU V2 source-projection and Bundle authority verification no longer reconstructs and canonical-hashes the same immutable authority object at every internal seam.

**Evidence and diagnosis:** The accepted 8-slot hour-aligned same-path public-preparation preflight completed, but cProfile measured 236 seconds and 950M calls; a 120-slot preparation-only test timed out fail-closed at 900 seconds before Engine execution. Dominant work is repeated V2 `_trusted_result` rebuild/canonical validation (source projection: 25 calls / 73.5s; execution bundle: 2 calls / 42s), not thin funding replay validation.

**Required seam:**
- Add only V2, bounded, process-local, successful-result identity caches to the source-projection and execution-bundle `_trusted_result` helpers.
- Cache entries retain the original object and use `is` identity checks, never digest/canonical bytes as a key. A miss runs the full existing reconstruct-and-canonical verification before insertion; cache hit returns only that verified reconstruction.
- No V1 cache, wire byte change, cross-process persistence, or caching of funding/journal/cutoff/state attestation is allowed.

**Acceptance:**
- Exact-object cache hit/miss and bounded-eviction tests prove reconstructed authority is reused only after full validation; `replace`-forged authorities miss and fail closed.
- Existing source projection and execution bundle V2 tamper/round-trip suites pass with V1 golden suites unchanged.
- The 8-slot public preparation completes after a fresh-process cache reset. A 120-slot preparation-only smoke completes under a declared 15-minute cap before P3/P4.

### P3 — Integrated public smoke acceptance

**Outcome:** One tiny public KORU BundleV2 execution crosses the same production seams as discovery:

```text
prepare_binance_usdm_tradifi_bar_backtest
→ Schema7 input
→ DeterministicBarEngine
→ fees/funding/margin/batch liquidation
→ durable fresh rebuild
→ exact final result hash
```

**Acceptance:**
- Raw values for all P1 purposes are present.
- Two taker fills, final flat position, funding accounting, unique artifact roles, and batch checkpoint evidence are asserted.
- Independent read-only review has no blocker/high finding.
- No retained source reconstruction occurred during P1–P3.

### P4 — One retained context rebuild

**Outcome:** After P3 code is frozen and committed, regenerate `execution_gap_impact.json` then write and validate `discovery_source_targets_v2.json` once.

**Acceptance:**
- Gap audit remains clear for p01–p08.
- Write and `--validate-only` hashes match exactly.
- Build output binds the final Backtest commit and source/profile/Bundle authority hashes.

### P5 — Actual p01 single-arm gate

**Outcome:** Run p01 once against the retained discovery context.

**Acceptance:**
- No planner/preparation/Engine failure.
- Exact first-retained aggTrade fills, raw-purpose evidence, all funding artifacts, unique roles, batch audits, and final snapshot are checked.
- A failure produces a canonical code/subject and returns to the earliest unmet phase; it does not trigger another full run until a small same-path regression test proves the repair.

### P6 — Eight-arm local diagnostic run

**Outcome:** Run all p01–p08 inside the one already-verified retained context process; do not reconstruct the 6.6M-row source per arm.

**Acceptance:**
- One deterministic context reconstruction, eight seed-0 arms, and no holdout reads.
- Every arm is completed or preserved as an explicit failure; never zero-filled.
- Output remains a clearly labeled local diagnostic report, not formal Research evidence.

### P7 — Public Research execution/publication integration

**Outcome:** Add the minimum approved public adapter so frozen Backtest preparation/execution enters `execute_experiment()` / evidence repository / analysis through public package roots.

**Acceptance:**
- Trial declarations, sample reservations, publications, terminal preservation, analysis, and deterministic selection use public Research/Backtest seams.
- No private Engine/composer/import route crosses into Research.
- This is a separate vertical slice from P1–P6 and requires its own readiness packet.

### P8 — Formal discovery and selection

**Outcome:** Publish the exact eight-arm Experiment, execute, analyze only verified completions, and select under the frozen policy.

**Acceptance:**
- `max_trials=8`, seed 0, frozen refs/metric profile, and p01–p08 exact-cover.
- Hard filters: `fill_count >= 8` and `simple_period_return > 0`.
- Ordering: return descending, fill count descending, declaration ref ascending.
- Explicit `discovery_no_selection` is valid; no manual winner.

### P9 — Holdout

**Outcome:** Only after `2026-10-05T00:00:00Z`, reserve and evaluate the untouched `[2026-08-24T11:00:00Z, 2026-10-05T00:00:00Z)` holdout through Validation.

**Acceptance:**
- Candidate parameters/dates remain unchanged.
- Sample ledger reservation precedes holdout read.
- Result is `supported`, `rejected`, or explicit no-report/inconclusive; no promotion or deployment authority.

## Execution policy

- **One writer** in the Backtest worktree. Reviewers are read-only.
- Start every phase with its listed smallest smoke test; only then run broader focused tests.
- Commit only an accepted vertical slice. Rebuild retained context only after a clean committed slice.
- Do not use a retained p01 run as a debugging step. Failures return to P1–P3 with a regression test.
- Run `--validate-only` exactly once per newly written retained context, not after every local test edit.
- At P6, keep one process/context alive across eight arms. If a reusable serialized context is needed, design a canonical, source-authority-bound reader/codec first; never use pickle or unverified cache data.

## Current next gate

**P2d is active.** Implement thin V2 funding evidence and Schema8 durable replay before any more retained reconstruction or p01 run.
