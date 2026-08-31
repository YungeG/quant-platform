# A-share portfolio target-stream Backtest Full Implementation Packet

Status: **NOT_READY**

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

## Open decision

**Material blocker:** no accepted Backtest contract defines the six missing decisions above, and real full-market A-share rule/fee/corporate-action authority is not terminal complete. The packet cannot name exact new symbols, preimages or failure codes without inventing Backtest architecture.

## Readiness decision

**NOT_READY.** The next owner is the Backtest contract owner, who must first approve a public multi-instrument provider contract and immutable source profile. Until then, V18 and dividend-growth remain research target states with `backtest_ready=false` and `trade_authorized=false`.
