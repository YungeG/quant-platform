# Phase 4 Final Independent Re-review — 136bed5

**Verdict: ACCEPT**

## Review

- **Correct:** `PortfolioCancelReplaceV1` embeds `replacement_sizing_identity` and directly validates its instrument, preallocated order, source target, and recomputed identity hash. Forged direct construction is rejected at `packages/trading-kernel/src/crypto_quant_trading/portfolio_rebalance.py:32-83`, with regression coverage at `tests/runtime/engine/test_portfolio_supersession_v2.py:267-284`.
- **Correct:** Cumulative admission refresh occurs after every successful admission, so later pretrade checks observe earlier reservations. Final resources are reprojected before commit, and only isolated local state is committed at `packages/backtest-runtime/src/crypto_quant_backtest/engine.py:3080-3284`.
- **Correct:** The cumulative rollback regression proves admission one succeeds independently, identifies admission two and `tradable_cash:USD` as the exact failure subjects, and verifies rollback at `tests/runtime/engine/test_portfolio_supersession_v2.py:403-483`.
- **Correct:** The replacement-to-fill regression invokes `DeterministicBarEngine.run(case)` and verifies the replacement stream reaches `FILLED` with the scheduled fill at `tests/runtime/engine/test_portfolio_supersession_v2.py:509-565`.
- **Correct:** Replacement order identities participate in global uniqueness and known-order validation at `packages/backtest-runtime/src/crypto_quant_backtest/engine.py:1607-1656`. Replacement order/event bindings participate in manifest verification at `engine.py:1706-1760`, covered by `tests/runtime/engine/test_portfolio_supersession_v2.py:307-374`.
- **Correct:** Phase 4 exact-cover and ordinary/replacement disjointness are enforced both when constructing the cycle and again transactionally at `packages/backtest-runtime/src/crypto_quant_backtest/engine.py:759-803` and `engine.py:3160-3194`.
- **Correct:** Cancel-replacement causation remains direct from `ORDER_CANCELLED` to replacement `ORDER_INTENT_CREATED`, validated after admission at `packages/backtest-runtime/src/crypto_quant_backtest/engine.py:3195-3252`.
- **Correct:** Legacy behavior remains on the separate non-V2 branch, while the empty V2-plan regression preserves existing working streams at `tests/runtime/engine/test_portfolio_supersession_v2.py:568-607`.
- **Note:** The focused collision regression covers ordinary/replacement overlap and collision with an initial order identity. Event-ID collision behavior is enforced statically by the same global uniqueness collection but lacks a dedicated collision regression.
- **Note:** Git equivalence, staged state, and pytest execution could not be independently verified with the available read-only tools.

## Residual risks

- Commit `136bed5` equivalence to the inspected worktree was not independently verified.
- Tests were inspected but not executed.
- No focused replacement-event-ID collision test exists, although the implementation covers replacement event IDs globally.
