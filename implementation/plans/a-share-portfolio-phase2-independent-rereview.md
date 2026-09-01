# Phase 2 Independent Re-review — commit `be813af`

## Verdict

**ACCEPT Phase 2**

All three prior P1 blockers are resolved.

## Review

- **Correct — mandatory refresh plan:** `ResolvedPortfolioDecisionCycleV2.snapshot_refresh_plan` is now required and rejects non-plan values, including `None` (`packages/backtest-runtime/src/crypto_quant_backtest/engine.py:629-663`). Canonical output always includes it (`engine.py:669-676`).

- **Correct — complete mark-set validation at both boundaries:** Both `ResolvedDecisionSnapshotRefreshPlanV1` (`engine.py:577-594`) and `PortfolioSnapshotRefreshInputV1` (`packages/trading-kernel/src/crypto_quant_trading/portfolio_snapshots.py:106-123`) reject marks unless every mark:
  - resolves exactly at the decision instant;
  - uses `PricePurpose.VALUATION`;
  - has a unique instrument identity.

- **Correct — structured refresh failures:** Input construction and refresher execution are within the same `try` boundary and map validation failures to `EngineFailureCode.SNAPSHOT_PROJECTION_FAILURE` (`engine.py:2490-2513`).

- **Correct — atomic refresh publication:** Snapshot, financial artifact, and trace publication occur only after input construction, refresh, payload construction, and artifact construction succeed (`engine.py:2514-2544`). No refresh-side financial state is changed on the guarded failure path.

- **Correct — regression tests target old behavior:**
  - Missing-plan test would fail the old optional-plan implementation (`tests/runtime/engine/test_portfolio_snapshot_refresh_v2.py:78-108`).
  - Plan mark-set tests would fail the old plan validator (`test_portfolio_snapshot_refresh_v2.py:111-114`).
  - Input mark-set tests independently enforce the input boundary (`tests/kernel/portfolio/test_portfolio_snapshot_refresh.py:75-91`).
  - Input-construction failure test would raise an unstructured exception under the old placement and now verifies structured failure plus unchanged snapshot/artifacts (`test_portfolio_snapshot_refresh_v2.py:117-147`).

- **Correct — legacy preservation:** The mandatory field applies only to additive `ResolvedPortfolioDecisionCycleV2`; legacy `ResolvedDecisionCycle` behavior and serialization remain separate. Existing V2 lifecycle construction was updated with an explicit refresh plan (`tests/runtime/engine/test_order_terminal_lifecycle_v2.py:175-219`).

- **Note:** The atomicity regression test checks snapshot and financial artifacts rather than deep-comparing every `_EngineState` field. Source inspection establishes that `_refresh_decision_snapshot` does not mutate state before successful publication. The surrounding `_decision_cycle` intentionally records the accepted decision batch before invoking refresh (`engine.py:2583-2598`); therefore “unchanged state” should be understood as refresh-owned snapshot/financial state, not rollback of prior decision-batch evidence.

- **Note:** Test execution, exact Git diff, staging status, and commit ancestry could not be independently executed with the available read-only tools. The supervisor should run the focused and full suites before merging.
