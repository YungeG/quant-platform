# Cn A-share portfolio provider implementation handoff

Status: **BLOCKED — no production implementation attempted**

Scope reviewed: fixture-level A-share portfolio provider only. No real-data readiness, deployment, or trading claim is made.

## Authorities read

- `/home/ygguo/agent-projs/ai-crypt/platform-sector-trend/implementation/plans/a-share-portfolio-target-stream-backtest-v1.md`
- `/home/ygguo/agent-projs/ai-crypt/platform-sector-trend/implementation/plans/a-share-portfolio-target-stream-oracle-review.md`

The approved provider placement and policy are clear, but the current runtime cannot realize the policy through the oracle's exact write set without additional engine and profile contract decisions. The supervisor directed a blocker-only handoff rather than widening scope or weakening semantics.

## Blocking runtime behavior

### 1. DAY expiry is a decision only; it does not expire the order or release its reservation

- `packages/backtest-runtime/src/crypto_quant_backtest/engine.py:2592-2601`
- `NextEligibleBarOpenModel` can return `NoEligibleBarAction.EXPIRE`, but `_bar_execution` returns immediately for every non-`FULL_FILL` action.
- No `ORDER_EXPIRED` event is appended, the order remains in `state.order_streams`, and `_refresh_resources` is not called.
- Result: an upper-limit/otherwise ineligible DAY buy remains working and reserved instead of expiring to cash. This directly violates buy-DAY and failed-buy-remains-cash semantics.

The isolated execution-model test only proves the returned action:

- `tests/runtime/execution/test_next_eligible_bar_open.py:138-145`

It does not prove engine order-state or reservation mutation.

### 2. Target supersession is rejected by the engine

- `packages/trading-kernel/src/crypto_quant_trading/rebalance.py:735-820` produces cancellation intents for expired/conflicting working orders.
- `packages/backtest-runtime/src/crypto_quant_backtest/engine.py:2236-2243` converts any non-empty `plan.cancel_intents` into `EngineFailureCode.ORDER_PLAN_MISMATCH`.
- Result: a newer complete target cannot durably supersede a stale GTC sell or stale buy. The kernel can describe cancellation, but the runtime cannot execute it.

The kernel test confirms cancellation intents are expected values:

- `tests/kernel/rebalance/test_rebalance_coordinator.py:123-156`

There is no runtime path that appends `ORDER_CANCEL_REQUESTED` / `ORDER_CANCELLED`, releases reservations, and continues deterministically.

### 3. The engine keeps the initial portfolio snapshot during intermediate fills

- Decision allocation reads `state.snapshot`: `packages/backtest-runtime/src/crypto_quant_backtest/engine.py:2135-2140`.
- Rebalance planning also reads `state.snapshot`: `packages/backtest-runtime/src/crypto_quant_backtest/engine.py:2208-2216`.
- Fill accounting updates the journal and ledger, but only replaces `state.snapshot` when a dispatch result contains a snapshot: `packages/backtest-runtime/src/crypto_quant_backtest/engine.py:2049-2061`.
- `DefaultCashFinancialDispatcher.book_fill` returns journal entries/lots/artifacts without a snapshot: `packages/backtest-runtime/src/crypto_quant_backtest/financial_dispatch.py:930-969`.

Result: later target cycles cannot reliably observe holdings and cash created by earlier fills. A retained holding, subsequent sell, residual cash, T+1 availability, and supersession across a portfolio timeline therefore cannot be implemented faithfully by a provider alone.

### 4. The rebalance public contract has one TIF and canonicalizes by instrument, not side

- `RebalancePolicy` has one `time_in_force`: `packages/trading-kernel/src/crypto_quant_trading/rebalance.py:60-145`.
- Every planned order receives it: `packages/trading-kernel/src/crypto_quant_trading/rebalance.py:1176-1191`.
- `OrderPlan` accepts only `RebalancePolicy`: `packages/trading-kernel/src/crypto_quant_trading/rebalance.py:381-382`.
- Planned orders are sorted only by instrument: `packages/trading-kernel/src/crypto_quant_trading/rebalance.py:400-404`.
- `ResolvedDecisionCycle` also accepts only `RebalancePolicy`: `packages/backtest-runtime/src/crypto_quant_backtest/engine.py:375-415`.

An additive side-specific policy is required, but accepting it propagates into the resolved execution-case/input contract and engine, not only `rebalance.py`.

### 5. T+1 and cash availability are evidence but not planning constraints

- `AvailabilityState` exposes settled/tradable cash and sellable position quantities: `packages/trading-kernel/src/crypto_quant_trading/settlement.py:770-892`.
- `RebalanceCoordinator` binds only the availability hash/context; its planned delta is target minus current quantity and does not cap sells by `PositionAvailability.sellable` or buys by settled, unreserved cash plus fee reserve.
- Pre-trade can reject an overcommitted order, but rejection terminates the backtest; it is not deterministic partial sizing that leaves residual cash.

Result: T+1-unavailable quantities and settled-cash-only buy sizing cannot be expressed as the approved planning semantics without a new additive planning input/decision contract.

### 6. The reusable Cn A-share profile is fixed-singleton and one-order capacity

- `CnAShareInstrumentScopeDeclaration` contains one `instrument`: `packages/backtest-runtime/src/crypto_quant_backtest/cn_a_share_profile.py:187-205`.
- `CnAShareProfileCompositionRequest` contains one `instrument_scope`: `packages/backtest-runtime/src/crypto_quant_backtest/cn_a_share_profile.py:415-432`.
- The composed account risk policy has `order_capacity_limit=1`: `packages/backtest-runtime/src/crypto_quant_backtest/cn_a_share_profile.py:858-866`.

The approved provider input has one `CnAShareResolvedProfile`, while the required fixture must admit at least two buys and potentially a simultaneous working GTC sell. Reusing the singleton registration unchanged would reject the second order or silently apply one instrument's authority to other instruments. Generalizing the existing fixed-singleton profile would violate the preservation requirement.

## Required additive contract decisions before implementation

1. **Engine order-lifecycle evidence**
   - Define resolved, identity-bound event plans for DAY expiry and target-driven cancellation.
   - Decide whether one cancel intent emits both `ORDER_CANCEL_REQUESTED` and `ORDER_CANCELLED` in the same deterministic cycle for this fixture contract.
   - Specify reservation release timing and trace/evidence roles.

2. **Supersession execution**
   - Decide whether cancellation and replacement may occur atomically in one order plan, or cancellation completes in one cycle and replacement waits for a later explicit cycle.
   - The current kernel forbids cancel-and-replace for one instrument in one plan and emits `CANCELLATION_PENDING`.

3. **Current portfolio snapshot authority between decisions**
   - Add an immutable per-decision snapshot/valuation projection contract, or require financial dispatch to publish an updated portfolio snapshot after each fill/fee/settlement event.
   - Bind exact marks, cash, lots, fees, and settlement availability used by allocation and rebalance.

4. **Side-specific rebalance policy ownership**
   - Add `CnAShareRebalanceExecutionPolicyV1` (or an equivalently named kernel value) without changing legacy `RebalancePolicy` canonical bytes/hashes.
   - Approve sell-GTC, buy-DAY, sell-before-buy ordering, and deterministic supersession representation in `OrderPlan` and `ResolvedDecisionCycle`.

5. **Cash- and availability-aware sizing**
   - Decide whether capping belongs in `PositionSizer`, `RebalanceCoordinator`, or a new additive portfolio order-sizing stage.
   - The stage needs settled unreserved cash, position sellability, resolved prices, and exact fee-reservation/minimum-commission authority. It must omit/resize orders rather than fail the whole run.

6. **Additive portfolio profile authority**
   - Preserve `CnAShareResolvedProfile` and its fixed-singleton hashes.
   - Define how one provider input authorizes every catalog instrument: an additive `CnASharePortfolioResolvedProfile`, a tuple of independently composed singleton profiles, or another explicit portfolio authority.
   - Define an additive account registration with deterministic capacity for multiple orders while preserving the fixed-singleton account identity.

## Smallest proposed implementation write set after decisions

The original provider files remain necessary:

- `packages/backtest-runtime/src/crypto_quant_backtest/cn_a_share_portfolio_provider.py` (new)
- `packages/backtest-runtime/src/crypto_quant_backtest/__init__.py`
- `tests/runtime/providers/test_cn_a_share_portfolio_provider.py` (new)
- `tests/architecture/test_cn_a_share_portfolio_provider_boundary.py` (new)

The discovered minimum additional files are:

- `packages/trading-kernel/src/crypto_quant_trading/rebalance.py`
- `packages/trading-kernel/src/crypto_quant_trading/__init__.py`
- `tests/kernel/rebalance/test_rebalance_coordinator.py` or a new focused A-share policy test
- `tests/kernel/rebalance/test_rebalance_coordinator_golden.py` to prove legacy hashes remain unchanged
- `packages/backtest-runtime/src/crypto_quant_backtest/engine.py`
- focused runtime engine tests for expiry, cancellation/supersession, reservation release, and current-snapshot refresh
- execution-input codec/catalog files and tests **only if** resolved cycle/bar event-plan fields change
- an additive portfolio-profile module/tests, or an explicitly approved provider-local additive registration, depending on the profile decision

`cash_development_provider.py` must remain untouched.

## Failing sentinels to add first on relaunch

1. Engine upper-limit DAY buy: action is `EXPIRE`, order state becomes `EXPIRED`, reservation is released, cash is unchanged.
2. Engine lower-limit GTC sell: first bar keeps order active; later eligible bar fills the same order.
3. Runtime supersession: newer complete target cancels stale working orders without `ORDER_PLAN_MISMATCH`, with deterministic cancellation evidence and released reservations.
4. Runtime state refresh: a second target sees cash/holdings/lots produced by the first fill.
5. Kernel side policy: sells sort before buys; sell intent is GTC; buy intent is DAY; legacy rebalance golden remains byte/hash stable.
6. Kernel availability policy: T+1-unavailable quantity is not planned for sale; settled/unreserved cash and exact fee reserve cap buys.
7. Portfolio profile: two buys plus a working sell can be admitted without altering fixed-singleton profile hashes.
8. Provider end-to-end: two buys, retained holding, sell, residual cash, lot rounding, minimum commission and sell tax, delayed sell, expired upper-limit buy, T+1 block, supersession, replay stability.
9. Preparation failures: target tamper, bundle tamper, and retention loss fail before attempt creation.
10. Preservation: existing cash-development, target-stream V6, fixed-singleton A-share, and rebalance golden suites remain unchanged.

## Commands run

```text
git status --short
git branch --show-current
git log -3 --oneline
```

Initial worktree was clean on branch `feature/cn-a-share-portfolio-provider-v1` at `f73d068d24ffb7ecc0b7d78194fcbc96908d3c04`.

```text
uv run pytest -q \
  tests/kernel/rebalance/test_rebalance_coordinator.py \
  tests/runtime/execution/test_next_eligible_bar_open.py \
  tests/runtime/providers/test_cash_development_provider.py \
  tests/architecture/test_cn_a_share_fixed_singleton_no_trade_profile_boundary.py
```

Result: `35 passed in 6.51s`.

```text
git diff --cached --stat
git diff --stat
git diff -- packages/backtest-runtime/src/crypto_quant_backtest/cash_development_provider.py tests/runtime/providers/test_cash_development_provider.py tests/runtime/target_stream/test_backtest_target_stream_execution.py
git status --porcelain=v1
```

Before writing this required handoff artifact: no staged files, no unstaged tracked changes, and no changes to preserved cash-provider files/tests.

## Implementation result

No production files or tests were changed, and no commit was created. This avoids silently weakening sell-GTC/buy-DAY, T+1, settled-cash-only sizing, supersession, profile authority, or evidence semantics.

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "not-satisfied",
      "evidence": "Implementation was intentionally stopped because the existing engine rejects cancellation intents, does not mutate order state for DAY expiry, retains an initial snapshot between fills/decisions, and the reusable A-share profile is single-instrument/order-capacity-one. Implementing only the approved write set would weaken required semantics."
    }
  ],
  "changedFiles": [
    "cn-a-share-portfolio-provider-handoff.md"
  ],
  "testsAddedOrUpdated": [],
  "commandsRun": [
    {
      "command": "uv run pytest -q tests/kernel/rebalance/test_rebalance_coordinator.py tests/runtime/execution/test_next_eligible_bar_open.py tests/runtime/providers/test_cash_development_provider.py tests/architecture/test_cn_a_share_fixed_singleton_no_trade_profile_boundary.py",
      "result": "passed",
      "summary": "35 passed in 6.51s"
    },
    {
      "command": "git status --short && git diff --cached --stat && git diff --stat",
      "result": "passed",
      "summary": "Before the required handoff file was written, the worktree had no staged or unstaged tracked changes."
    },
    {
      "command": "git diff -- packages/backtest-runtime/src/crypto_quant_backtest/cash_development_provider.py tests/runtime/providers/test_cash_development_provider.py tests/runtime/target_stream/test_backtest_target_stream_execution.py",
      "result": "passed",
      "summary": "No diff; preserved cash-provider identities and suites were untouched."
    }
  ],
  "validationOutput": [
    "Focused baseline validation: 35 passed in 6.51s.",
    "No production diff was created.",
    "Branch feature/cn-a-share-portfolio-provider-v1 at f73d068d24ffb7ecc0b7d78194fcbc96908d3c04."
  ],
  "residualRisks": [
    "DAY expiry has no durable engine state transition or reservation release.",
    "Engine rejects target-supersession cancellation intents.",
    "Later decision cycles use a stale initial portfolio snapshot.",
    "Rebalance planning does not enforce T+1 sellability or settled-cash/fee-aware buy capping.",
    "Existing CnAShareResolvedProfile is single-instrument with order capacity one."
  ],
  "noStagedFiles": true,
  "diffSummary": "Documentation-only blocker handoff; no production or test implementation changes.",
  "reviewFindings": [
    "blocker: packages/backtest-runtime/src/crypto_quant_backtest/engine.py:2600 - non-fill DAY expiry decisions do not mutate order state or release reservations",
    "blocker: packages/backtest-runtime/src/crypto_quant_backtest/engine.py:2236 - every rebalance cancellation intent is rejected as ORDER_PLAN_MISMATCH",
    "blocker: packages/backtest-runtime/src/crypto_quant_backtest/engine.py:2137 - later allocations use state.snapshot, which fill dispatch does not refresh",
    "blocker: packages/trading-kernel/src/crypto_quant_trading/rebalance.py:1186 - one policy TIF is applied to both buys and sells",
    "blocker: packages/backtest-runtime/src/crypto_quant_backtest/cn_a_share_profile.py:865 - fixed-singleton account capacity is one order"
  ],
  "manualNotes": "Supervisor directed a blocker-only handoff and explicitly prohibited widening implementation or weakening semantics. No commit or push was made."
}
```
