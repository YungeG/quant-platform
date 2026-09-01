# A-share portfolio target-stream Backtest Full Implementation Packet

Status: **READY for fixture-level contract implementation; real-data execution remains NOT_READY**

## Outcome

Expose one Backtest-owned public preparation operation for multi-instrument A-share cash portfolios. It must consume a verified precomputed target-stream ref and immutable market/rule authorities, then return the same deep `PreparedBacktestExecution` interface used by existing Research integration. It must not authorize Shadow or Live.

## Authority

| ID | Source | Requirement or invariant |
| --- | --- | --- |
| C1 | `.agents/skills/quant-strategy-research/SKILL.md` | Backtest exclusively owns fills, fees, settlement, accounting, PnL and evidence; callers may use only a concrete public preparation operation. |
| C2 | `backtest/packages/backtest-runtime/src/crypto_quant_backtest/__init__.py` | The public root currently exports only cash-development preparation operations, not an A-share portfolio operation. |
| C3 | `backtest/packages/backtest-runtime/src/crypto_quant_backtest/cash_development_provider.py:_case_inputs` | Existing cash provider requires exactly one instrument, one target event and one bar event. |
| C4 | `backtest/packages/backtest-runtime/src/crypto_quant_backtest/cash_development_provider.py:_planned_order` | Existing provider requires exactly one positive BUY order and cannot express rebalance sells, failures or retained cash. |
| C5 | `overall/a-share-low-turnover-buffer-v18-order-replay-capability-review.md` | V18 requires T+1, 100-share lots, price-limit failures, delayed sells, minimum commission and cash residue. |
| C6 | `overall/a-share-dividend-growth-cash-coverage-target-v1.json` | Dividend state produces a 56-instrument equal-weight target; no custom simulator may consume it. |

## Ownership

- Owner module: Backtest
- Candidate worktree: separate `quant-backtest` worktree at the accepted submodule SHA
- Shared-file owner: one Backtest writer
- Platform integration owner: controlling agent after Backtest candidate validation

## Flow and seam

Before:

```text
Research target stream -> no public A-share portfolio preparation seam -> NO BACKTEST
```

Required after:

```text
BacktestTargetStreamRef + A-share provider inputs
  -> public prepare_cn_a_share_portfolio_target_stream_backtest(...)
  -> Backtest request registration / semantic run / execution bundle
  -> PreparedBacktestExecution
  -> BacktestRuntime + BacktestEvidenceRepository
```

The operation name above is a proposed interface, not an accepted symbol.

## Current reusable modules

- `BacktestTargetStreamRepository` already verifies durable target-stream refs.
- `PrecomputedTargetStreamAdapter` already validates scheduled decision batches.
- `CnAShareProfileComposer` already resolves A-share market, simulation and cash-account profiles.
- Trading-kernel order rules, quantity lattice, settlement availability, corporate actions and fee bindings already have focused fixtures.
- `BacktestRuntime` and evidence publication already own completed/terminal results and replay.

## Missing contract decisions

1. Exact public request/provider input types and canonical identities for a multi-instrument A-share portfolio.
2. Immutable MarketBundle schema for many instruments and sessions, including daily open/valuation bars, status, limits and corporate actions.
3. Target semantics: absolute weights, cash target, decision schedule, expiry, sell-before-buy ordering and partial rebalance behavior.
4. Failure precedence for missing bars, suspension, upper-limit buys, lower-limit sells, T+1 unavailable quantities, insufficient cash and minimum commission.
5. Historical fee/tax authority and terminal coverage across the requested sample.
6. Whether one execution request contains the whole portfolio timeline or a bounded set of Backtest-owned cases; Platform may not choose this architecture.

These decisions affect request hashes, semantic run identity, evidence bytes and accounting behavior. A writer cannot safely infer them from the single-instrument provider.

## Forbidden paths

| Authority | Forbidden path | Required route |
| --- | --- | --- |
| C1 | New simulator under `experiments/` or Platform | Backtest public preparation operation |
| C2-C4 | Calling private `ExecutionCaseComposer`, engine, facade internals or fee binders from Platform | Public root only |
| C5 | Treating failed limit/suspension orders as immediate fills or dropping them | Backtest-owned durable order outcomes |
| C6 | Calculating portfolio PnL from the 56-target CSV locally | Verified Backtest evidence |

## Sentinel and validation required after contract approval

- Public-root import test for the exact preparation symbol and public values.
- Multi-symbol fixture: at least two buys, one retained holding, one sell and residual cash.
- Upper-limit buy fails and remains cash.
- Lower-limit sell delays; subsequent eligible open executes.
- T+1 blocks same-day sale.
- 100-share rounding never rounds exposure upward.
- Minimum commission and sell tax are charged by accepted historical authority.
- Replay reuses semantic evidence and produces identical ledger/lot hashes.
- Target-stream tamper, market-bundle tamper and retention loss fail before an attempt.
- Existing cash-development and fixed-singleton suites remain byte/hash stable.

## Approved contract decision

The controlling agent approves `CnAShareRebalanceExecutionPolicyV1` for fixture-level implementation with these indivisible semantics:

1. sell orders are GTC and remain working after lower-limit/suspension blocks;
2. buy orders are DAY and failed buys expire to cash;
3. sells are planned before buys;
4. buy sizing uses settled, unreserved cash only and never expected sell proceeds;
5. T+1-unavailable quantities cannot be sold;
6. a newer complete target snapshot deterministically supersedes stale working orders.

The decision is supported by the frozen V18 execution requirements, the first oracle review in `a-share-portfolio-target-stream-oracle-review.md`, and the expanded V2 runtime decision in `a-share-portfolio-runtime-v2-oracle-decision.md`.

## Readiness decision

**READY for fixture-level contract implementation.** The expanded oracle decision freezes a parallel V2 portfolio execution path, execution-input bundle V7, terminal/cancellation evidence, decision-time snapshot refresh, availability/fee-aware capping, atomic supersession and an additive multi-instrument portfolio profile. Implementation must follow Phases 0—7 in order and stop at each preservation gate. Existing cash/fixed-singleton identities must remain byte/hash stable.

**Real-data execution remains NOT_READY** until full-market MarketBundle, historical fee/tax, status, price-limit and corporate-action authorities are terminal complete. V18 and dividend-growth remain `backtest_ready=false` and `trade_authorized=false`.

## Implementation progress

- Phase 0–1 implementation: `8beb324`, repaired by `9a6c8a1`; handoff commits `0555296` and `7362772`.
- Independent re-review: **ACCEPT Phase 1**, recorded in `a-share-portfolio-phase1-independent-rereview.md`.
- Controlling-agent confirmation: focused 5 passed; clean-tree preservation gate 127 passed; LSP clean.
- Remote branch: `quant-backtest/feature/cn-a-share-portfolio-provider-v1`.
- Phase 2 implementation: `c52b5d1`, repaired by `be813af`.
- Phase 2 independent re-review: **ACCEPT**, recorded in `a-share-portfolio-phase2-independent-rereview.md`.
- Controlling-agent confirmation: Phase 2 focused 10 passed; clean-tree preservation gate 137 passed; LSP clean.
- Phase 3 implementation: `7f616ed`, repaired by `567fb7b`.
- Phase 3 independent re-review: **ACCEPT**, recorded in `a-share-portfolio-phase3-independent-rereview.md`.
- Controlling-agent confirmation: focused portfolio/engine 21 passed; clean-tree preservation gate 147 passed; LSP clean.
- Next authorized phase: Phase 4 atomic cancellation/replacement supersession only.
