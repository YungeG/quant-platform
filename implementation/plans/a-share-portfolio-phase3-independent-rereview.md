# Phase 3 Independent Re-review — ACCEPT

## Review

- **Correct:** Buy budget now uses `min(settled, tradable)` and subtracts active cash reservations, active fee reservations, and exact SELL fees before BUY sizing (`packages/trading-kernel/src/crypto_quant_trading/portfolio_order_sizing.py:444-450`). The `settled < tradable` regression is covered in `tests/kernel/portfolio/test_portfolio_order_sizing.py` by `test_settled_cash_is_hard_cap_when_tradable_is_higher`.
- **Correct:** `ResolvedPortfolioDecisionCycleV2.materialize_portfolio_plans()` exact-maps each resolved cancellation through its working stream into the same canonical `CancelIntent` identity used by the legacy coordinator, then passes all intents to `PortfolioRebalanceCoordinatorV2` (`packages/backtest-runtime/src/crypto_quant_backtest/engine.py:722-751`; canonical identity reference at `packages/trading-kernel/src/crypto_quant_trading/rebalance.py:1146-1167`).
- **Correct:** Cancellation-first ordering remains explicit: cancellation stages rank 90, SELL rank 100, BUY rank 110 (`packages/trading-kernel/src/crypto_quant_trading/portfolio_rebalance.py:184-224`). Cycle-level propagation and exact intent identity are tested by `test_cycle_materialization_maps_resolved_cancellations_first` (`tests/runtime/engine/test_order_terminal_lifecycle_v2.py:527-578`).
- **Correct:** Phase 3 is mandatory for every `ResolvedPortfolioDecisionCycleV2`: the engine invokes portfolio sizing after raw `PositionSizer` output and before legacy `RebalanceCoordinator` planning (`packages/backtest-runtime/src/crypto_quant_backtest/engine.py:2760-2871`). Ordering is asserted by `test_portfolio_snapshot_refresh_v2.py:354-368`.
- **Correct:** Multi-BUY common-scale sizing recomputes exact notional and minimum commission for every candidate vector (`portfolio_order_sizing.py:456-485`). `test_multi_buy_common_scale_recomputes_each_minimum_commission` covers two instruments and commission discontinuities; `test_settled_cash_cap_rounds_lots_and_keeps_preallocated_identity` verifies the reconstructed approved order quantity equals the final capped quantity (`tests/kernel/portfolio/test_portfolio_order_sizing.py`).
- **Correct:** Phase 4 remains excluded. `TARGET_SUPERSEDED` is reserved but not emitted, no `PortfolioOrderPlanV2` implementation exists, and Phase 3 does not admit its planned orders. Legacy admission continues through the existing `OrderPlan` path after the V2-only branch (`engine.py:2872-2908`).
- **Correct:** Legacy cycles are protected by explicit `isinstance(cycle, ResolvedPortfolioDecisionCycleV2)` branches; the raw sizing, legacy rebalance, and admission paths remain intact.
- **Correct:** Cancellation failure atomicity prepares and validates every stream plus projected reservation/settlement/availability state before committing any mutation (`engine.py:2950-3058`). The two-order late-failure regression verifies streams, trace, reservations, availability, and settlement remain unchanged (`tests/runtime/engine/test_order_terminal_lifecycle_v2.py:691-714`).

### Blockers

- None.

### Notes

- Static review accepts the repair. This environment provided no command runner, so commit identity, working-tree state, and test execution were not independently attested.
- Supervisor should run the focused portfolio and engine tests, followed by the full suite.

**Verdict: ACCEPT**
