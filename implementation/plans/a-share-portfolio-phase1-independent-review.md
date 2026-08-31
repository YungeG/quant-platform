# Phase 1 Independent Blocker Review

**Range reviewed:** `f73d068..0555296`
**Recommendation:** **DO NOT ACCEPT Phase 1** until both blockers below are resolved.

## Review

- **BLOCKER — Cancellation ordering is not canonical across multiple instruments.**
  `ResolvedOrderCancellationPlanV1` only requires increasing phase ranks; it does not enforce authoritative phases 90/91 or canonical source sequences (`packages/backtest-runtime/src/crypto_quant_backtest/engine.py:376-405`). `_apply_target_cancellations` then emits request and completion per order inside one loop (`engine.py:2505-2566`). For orders A and B this produces `A-request(90), A-cancelled(91), B-request(90), B-cancelled(91)`, rather than all phase-90 requests followed by all phase-91 completions. `ExecutionTrace` checks contiguous sequence numbers but not monotonic `SimulationInstant` ordering (`engine.py:1457-1504`). This contradicts the architecture decision’s **Event ordering** contract: phase 90 cancellation requests, phase 91 completions, canonical instrument ordering within each phase. The sole cancellation test covers only one order and therefore cannot detect this (`tests/runtime/engine/test_order_terminal_lifecycle_v2.py:365-421`).

- **BLOCKER — Multi-order cancellation can partially mutate lifecycle state before a later plan fails validation.**
  `_apply_target_cancellations` validates and immediately appends both terminal events for each order (`packages/backtest-runtime/src/crypto_quant_backtest/engine.py:2505-2566`). If a later order fails the checks at `engine.py:2510-2530`, earlier streams and traces have already been mutated, while `_refresh_resources` is not reached until after the complete loop (`engine.py:2567-2574`). This leaves order-stream state and reservation state inconsistent during the failure path and violates the architecture decision’s preflight-before-mutation/no-partial-commit safeguard. `_failed` hashes the already-mutated trace (`engine.py:3216-3237`). No test exercises a two-order cancellation where the later plan fails; the focused test verifies only successful single-order mutation (`tests/runtime/engine/test_order_terminal_lifecycle_v2.py:365-427`).

- **NOTE — The implemented single-order lifecycle happy paths otherwise match the Phase 1 sentinel.**
  DAY expiry appends `ORDER_EXPIRED`, replaces the stream, refreshes reservations/availability, and returns without journal mutation (`packages/backtest-runtime/src/crypto_quant_backtest/engine.py:2919-2956`). GTC without a terminal plan remains working, and focused tests check reservation persistence (`tests/runtime/engine/test_order_terminal_lifecycle_v2.py:307-361`). Successful cancellation checks terminal events, reservation release, and unchanged cash/positions (`tests/runtime/engine/test_order_terminal_lifecycle_v2.py:365-427`).

- **NOTE — Additive identities, exact-cover checks, and public exports are present.**
  The V2 cycle/bar carriers use distinct canonical type identities (`packages/backtest-runtime/src/crypto_quant_backtest/engine.py:528-532,664-668`). Lifecycle event IDs are checked for global uniqueness and cancellation orders must reference known orders (`engine.py:1217-1267`); cancellation plans must exact-cover generated cancellation intents (`engine.py:2492-2504`). All four new public types are imported and listed in `__all__` (`packages/backtest-runtime/src/crypto_quant_backtest/__init__.py:72-75,627-630`).

- **NOTE — Preservation evidence is recorded but was not independently rerun in this read-only review.**
  `phase1-terminal-lifecycle-handoff.md` reports a clean-tree 125-test preservation gate and frozen legacy fixture hashes. The reported changed source set is limited to the engine and additive exports, but Git/test commands were unavailable to this reviewer.
