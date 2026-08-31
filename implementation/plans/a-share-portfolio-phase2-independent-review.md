# Phase 2 Independent Blocker Review — commit `c52b5d1`

## Verdict

**REJECT Phase 2**

The refresh implementation is substantially aligned with the architecture, but mandatory refresh enforcement and decision-mark authority remain incomplete.

## Review

### Correct

- **Additive implementation:** New refresh contracts live in `packages/trading-kernel/src/crypto_quant_trading/portfolio_snapshots.py:38-351`; legacy `snapshots.py` is reused through `PortfolioSnapshotProjector` rather than widened.
- **No caller-supplied native valuations:** `PortfolioSnapshotRefreshInputV1` accepts ledger, lot, settlement, reservation, order, mark and graph authorities—not `ReportingCurrencyValuation` inputs (`portfolio_snapshots.py:69-168`). Native and reporting values are derived internally (`portfolio_snapshots.py:181-344`).
- **Current financial state is used:** Cash, positions, realized P&L, fees and financing come from the current `LedgerState`; position market value and unrealized P&L come from current lots and decision marks (`portfolio_snapshots.py:217-289`).
- **Resource identities are bound:** The refresh input and artifact bind lot books, working orders, reservations and settlement (`engine.py:510-552`, `2482-2526`).
- **Correct execution ordering when a plan exists:** `_refresh_decision_snapshot` executes immediately before `PortfolioAllocator.allocate` (`engine.py:2602-2610`).
- **Artifact identity and trace:** Decision ordinal appears in both payload and `decision-snapshot:{ordinal}` source identity. The trace binds the resulting artifact hash (`engine.py:510-614`, `2510-2535`).
- **Valuation graph binding:** The graph is included in the refresh input hash, while the resulting snapshot also carries its graph hash.
- **Second-decision sentinel exists:** `tests/runtime/engine/test_portfolio_snapshot_refresh_v2.py:30-219` executes a fill, refreshes at a second decision, and verifies changed cash, positions, fees, lots, artifact hashes and refresh-before-allocation ordering.
- **Legacy artifact coverage remains separated:** Decision snapshots are filtered from the legacy expected financial-artifact-role comparison (`engine.py:2137-2145`).

### Blockers

1. **P1 — A V2 decision can omit refresh and allocate from a stale snapshot.**

   `ResolvedPortfolioDecisionCycleV2.snapshot_refresh_plan` is optional, accepts `None`, and omits the field canonically when absent (`engine.py:618-665`). The engine then silently returns without refreshing (`engine.py:2449-2453`) and proceeds to allocation.

   This directly contradicts the authority decision:

   > “Every portfolio decision cycle contains one refresh plan. The engine executes it immediately before allocation.”

   It also violates the requested guarantee of no stale precomputed snapshot. Make the plan mandatory for every `ResolvedPortfolioDecisionCycleV2`, and reject missing refresh evidence before runtime allocation.

2. **P1 — The supplied mark set is not globally validated as decision-time valuation authority.**

   `ResolvedDecisionSnapshotRefreshPlanV1.__post_init__` validates the valuation graph time and purpose, but does not require every `resolved_mark` to have:
   - `resolved_at == occurred_at.instant`
   - `price_purpose == PricePurpose.VALUATION`
   - unique instrument identity

   See `engine.py:566-590`. The legacy projector only requires an exact current-time mark for each currently held position. Consequently, an empty portfolio or extra marks can carry stale, wrong-purpose or duplicate mark evidence into `decision_mark_set_hash` while still producing a snapshot.

   The architecture requires authoritative “decision-time resolved marks,” not merely a graph with the correct timestamp. Validate the complete mark set at the refresh-plan/input boundary.

3. **P1 — Some refresh evidence failures escape the structured runtime failure contract.**

   `PortfolioSnapshotRefreshInputV1(...)` is constructed outside the guarded `try` (`engine.py:2482-2494`). Its account, graph, resource and type validations can raise `TypeError` or `ValueError`. Only `PortfolioSnapshotRefresherV1.refresh()` is caught and translated to `SNAPSHOT_PROJECTION_FAILURE` (`engine.py:2495-2506`).

   This violates the prescribed runtime failure precedence for snapshot-refresh evidence/valuation failures and weakens failure atomicity by allowing an exception after decision-batch state and trace entries have already been appended. Construct the refresh input inside the same guarded boundary.

### Notes

- The refresh itself does not mutate financial state until projection succeeds; snapshot/artifact/trace publication happens afterward. That portion is acceptably atomic.
- Before refresh, `_decision_cycle` updates `latest_sleeve_state`, appends the decision batch and writes its trace. This appears intended as failure evidence, but no test documents the expected state after refresh failure.
- The main runtime test uses private engine methods and computes expected allocation evidence using the same refresher under test. It intentionally ends in a later failure rather than proving a successful two-decision `run()` journey.
- Missing focused tests:
  - V2 cycle rejects a missing refresh plan.
  - stale/wrong-purpose/duplicate marks are rejected.
  - refresh-input construction failures return structured engine failures.
  - failed refresh leaves snapshot and financial artifacts unchanged.
  - nonempty working orders and changed reservations/settlement are captured.
  - multi-currency valuation graph conversion.
  - duplicate decision ordinal/artifact identity rejection through public `run()`.
- No test or Git commands could be executed with the available read-only review tools. Legacy hash/golden preservation and repository staging state therefore remain unattested.
