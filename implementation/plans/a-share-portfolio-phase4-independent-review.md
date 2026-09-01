# Phase 4 Independent Blocker Review — e7432c1

**Verdict: REJECT**

## Review

### Blocker — Replacement admission exact-cover is not enforced

`ResolvedPortfolioDecisionCycleV2.__post_init__` validates only replacement admissions that happen to be supplied. It does not require `replacement_admissions` to exact-cover `portfolio_order_plan.cancel_replacements`, reject duplicate replacement IDs, or remain disjoint from ordinary `cycle.admissions`.

At execution, set union further masks overlap, and an omitted replacement wrapper may be supplied as an ordinary admission. The corresponding cancel-replace link is never checked because final causation validation iterates only `replacement_by_order`.

- `packages/backtest-runtime/src/crypto_quant_backtest/engine.py:759-779`
- `packages/backtest-runtime/src/crypto_quant_backtest/engine.py:3133-3180`

Consequently, a linked replacement can bypass `ORDER_INTENT_CREATED -> ORDER_CANCELLED` causation. This violates exact-cover and exact causation requirements.

### Blocker — Multiple admissions are evaluated against stale reservation state

After cancellations, resources are refreshed once. The engine then admits every planned order sequentially, but `_admit_order` adds reservation schedules without refreshing `reservation_state` before the next admission. Each subsequent pretrade gate therefore sees resources before earlier admissions in the same transaction.

- Initial post-cancellation refresh: `packages/backtest-runtime/src/crypto_quant_backtest/engine.py:3129-3131`
- Admission loop without intermediate resource projection: `engine.py:3145-3162`
- Reservation schedule mutation: `engine.py:3440-3460`
- Final refresh only after every admission: `engine.py:3180-3189`

Two instruments can each pass against the same available cash or sellable resources. The final projected resources are committed without a final pretrade-risk evaluation. This fails the requirement to preflight all new/replacement admissions and final resources in isolated cumulative state.

### Blocker — Replacement identities are absent from execution-case global validation

`ResolvedExecutionCase` includes only `cycle.admissions` when validating globally unique event IDs and order IDs. It does not include `cycle.replacement_admissions[*].admission`.

- Event identity coverage: `packages/backtest-runtime/src/crypto_quant_backtest/engine.py:1587-1600`
- Order identity and known-order coverage: `engine.py:1601-1621`
- Identity-manifest enumeration likewise starts from ordinary admissions: `engine.py:1697-1702`

Effects:

1. Replacement event IDs are not checked against initial or ordinary order events.
2. Replacement order IDs are not globally checked at case construction.
3. A later bar execution cannot reference a replacement-only order because it is absent from `known_orders`.
4. Duplicating the admission into the legacy `admissions` tuple is the apparent workaround, but creates precisely the ordinary/replacement overlap that runtime currently accepts.

Thus the V2 replacement path is not a complete first-class path and cannot safely satisfy “V2 bypasses legacy path/no legacy drift.”

### Blocker — Canonical constructors permit bypass of ordering and exact-cover invariants

`PortfolioOrderPlanV2.create()` sorts and performs partial relationship checks, but public direct construction invokes a `__post_init__` that verifies only `schema_version` and `plan_hash`.

- `packages/trading-kernel/src/crypto_quant_trading/portfolio_rebalance.py:240-276`
- Factory-only ordering/exact-cover checks: `portfolio_rebalance.py:284-335`

A caller can directly construct a hash-consistent plan containing unsorted tuples or invalid cancel-replacement coverage. Similarly, `PortfolioCancelReplaceV1.__post_init__` does not enforce the replacement sizing/source context enforced by `create()`.

- `portfolio_rebalance.py:32-53`
- Factory-only context validation: `portfolio_rebalance.py:55-79`

Therefore canonical identity, canonical order and constructor-bypass exact-cover are not frozen by the types themselves.

### Note — What is correct

- The V2 branch returns directly into `_apply_portfolio_order_plan_v2`, bypassing the legacy rebalance/admission block: `packages/backtest-runtime/src/crypto_quant_backtest/engine.py:2930-2978`.
- `_apply_portfolio_order_plan_v2` stages stream, trace, reservation and availability changes in a copied local state and commits only after successful processing: `engine.py:3032-3190`.
- For a correctly covered replacement, `_admit_order(... created_causation_id=replacement.cancelled_event_id)` makes `ORDER_INTENT_CREATED` directly caused by `ORDER_CANCELLED`: `engine.py:3150-3157`, `engine.py:3420-3438`.
- Both DAY and GTC fixture variants exercise successful direct causation in `tests/runtime/engine/test_portfolio_supersession_v2.py:176-205`.
- The manually empty plan retains existing working streams in `test_portfolio_supersession_v2.py:253-293`.

### Note — Test coverage is insufficient for acceptance

`test_failed_replacement_rolls_back_every_mutation` covers only one replacement instrument:

- `tests/runtime/engine/test_portfolio_supersession_v2.py:208-227`

`test_multi_instrument_cancellation_commits_atomically` tests successful cancellations, not a later-instrument failure and rollback:

- `test_portfolio_supersession_v2.py:230-250`

The only multi-instrument rollback test invokes the older `_apply_target_cancellations` helper rather than the new Phase 4 transaction:

- `tests/runtime/engine/test_order_terminal_lifecycle_v2.py:735-761`

Missing tests include:

- second replacement/new admission failure after the first succeeds;
- cumulative cash/resource exhaustion across multiple admissions;
- omitted replacement wrapper;
- ordinary/replacement admission overlap;
- duplicate replacement order or event identities;
- direct-constructor ordering/exact-cover rejection;
- full `ResolvedExecutionCase` run with a replacement followed by bar execution.

## Residual risks

- Tests were not executable with the available read-only review tools.
- Git diff/index commands were unavailable; review was anchored to HEAD log entry `e7432c16761029b0bfc7a5702dedd2d34ac8d566` and the affected source/test seams.
- Exact approved field ordering should additionally be frozen with explicit dataclass-field and canonical-key-order tests.
