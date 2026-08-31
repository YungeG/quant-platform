# Second-stage A-share Portfolio Architecture Decision

## Inherited decisions

- Keep the dedicated A-share portfolio provider; do not generalize `cash_development_provider.py`.
- Preserve all legacy cash-development, target-stream V6 and fixed-singleton A-share bytes and hashes.
- Full target snapshots: omitted instruments mean zero; residual exposure remains cash.
- Sell orders persist through lower-limit/suspension failures; failed DAY buys expire and remain cash.
- T+1, settled cash, minimum commission and fees must constrain planning—not terminate the run after over-planning.
- Scope is fixture-level development capability. Real-data readiness and trading authorization remain separate.

## Diagnosis

The handoff correctly found that provider-only work cannot implement the required semantics. Six lower contracts must be added:

1. Terminal order events and reservation release.
2. Atomic target supersession.
3. Current snapshot refresh.
4. Side-specific order lifetime.
5. Availability/fee-aware portfolio sizing.
6. Multi-instrument, multi-venue profile and account capacity.

These can be resolved additively without modifying legacy canonical types.

## Architecture decision

### Decision: parallel V2 portfolio execution path

Create a new portfolio-specific kernel/runtime path. Do not widen the legacy types in place.

Legacy types remain untouched:

- `RebalancePolicy`
- `OrderPlan`
- `ResolvedDecisionCycle`
- `ResolvedBarExecution`
- `ResolvedExecutionCase`
- `CnAShareProfileCompositionRequest`
- `CnAShareResolvedProfile`
- `CashDevelopment*`

New portfolio cases use execution-input bundle V7 and new V2 resolved-case types.

## 1. Engine terminal lifecycle contract

### New runtime types

```python
ResolvedOrderTerminalPlanV1
ResolvedOrderCancellationPlanV1
```

`ResolvedOrderTerminalPlanV1` fields:

- `order_id`
- `trigger_action: NoEligibleBarAction`
- `terminal_event_type: ORDER_EXPIRED`
- `event_id`
- `occurred_at`
- `reason_code`
- `source_evidence_hash`

`ResolvedOrderCancellationPlanV1` fields:

- `order_id`
- `cancel_requested_event_id`
- `cancel_requested_at`
- `cancelled_event_id`
- `cancelled_at`
- `reason_code`
- `source_target_hash`

### DAY expiry behavior

When `NextEligibleBarOpenModel` returns `EXPIRE`:

1. Validate the resolved terminal plan.
2. Append `ORDER_EXPIRED`.
3. Replace the order stream with its terminal stream.
4. Call `_refresh_resources`.
5. Trace the terminal stream hash and new reservation/availability hashes.
6. Cash and positions remain unchanged.

Reservation schedules need no terminal update: `ResourceReservationBook.project()` already derives active reservations from nonterminal order streams. Terminal stream plus `_refresh_resources` releases them.

### Cancellation behavior

A target-driven cancellation emits, in order:

1. `ORDER_CANCEL_REQUESTED`
2. `ORDER_CANCELLED`

Both occur at the same UTC decision time but strictly increasing `SimulationInstant` phases.

## 2. Supersession contract

### Decision: atomic cancel/replace transaction

Use atomic—not later-cycle—supersession.

New kernel types:

```python
PortfolioCancelReplaceV1
PortfolioOrderPlanV2
```

`PortfolioOrderPlanV2` may contain a cancellation and replacement for the same instrument only when linked by one `PortfolioCancelReplaceV1`.

Engine processing:

1. Preflight all cancellation source streams.
2. Build cancelled streams in a local state copy.
3. Project released reservations and availability locally.
4. Preflight replacement admissions against that local state.
5. Validate `CancelReplaceCausation`.
6. Commit all cancelled/replacement streams and reservation schedules together.
7. Refresh resources once.
8. Emit traces in canonical event order.

If any preflight fails, no cancellation or replacement mutation is committed.

A replacement `ORDER_INTENT_CREATED` is directly caused by the corresponding `ORDER_CANCELLED` event.

Working orders that still exactly cover the new target remain active; conflicting or obsolete orders are superseded.

## 3. Current snapshot refresh authority

### New kernel module

```python
PortfolioSnapshotRefreshPolicyV1
PortfolioSnapshotRefreshInputV1
PortfolioSnapshotRefresherV1
```

The refresher owns construction of current valuations from:

- current ledger;
- current lot books/cost basis;
- current settlement state;
- current reservation state;
- current working-order set;
- decision-time resolved marks;
- currency valuation graph;
- reporting currency and quantization policy.

It may internally produce the existing `ReportingCurrencyValuation` values and call `PortfolioSnapshotProjector`, but callers do not supply precomputed native values.

### New runtime type

```python
ResolvedDecisionSnapshotRefreshPlanV1
```

Every portfolio decision cycle contains one refresh plan. The engine executes it immediately before allocation.

The refreshed snapshot binds:

- journal-state hash;
- current cash and positions;
- lot-book hash;
- fee/realized/unrealized values;
- working-order-set hash;
- reservation-state hash;
- settlement-state hash;
- decision-time marks.

A `decision_snapshot` financial artifact and trace entry are emitted per decision. Artifact identity includes the decision ordinal, preventing role collisions.

A snapshot need not be rebuilt immediately after every fill. Ledger, settlement and reservation states refresh after each mutation; the next decision rebuilds the authoritative snapshot before allocation.

## 4. Side-specific rebalance contract

### New kernel type

```python
PortfolioRebalanceExecutionPolicyV1
```

Canonical semantics:

```text
sell_tif                 = GTC
buy_tif                  = DAY
order_sequence           = SELL_THEN_BUY
sell_retry               = UNTIL_FILL_EXPIRY_OR_SUPERSESSION
buy_retry                = NEVER_AFTER_DAY_EXPIRY
supersession             = ATOMIC_CANCEL_REPLACE
buy_cash_basis           = SETTLED_UNRESERVED_CASH_AFTER_FEES
sell_quantity_basis      = SELLABLE_POSITION
target_snapshot_semantics = COMPLETE_ABSOLUTE
```

This type does not subclass or alter `RebalancePolicy`.

New kernel coordinator:

```python
PortfolioRebalanceCoordinatorV2
```

New plans sort orders by:

```text
(stage_rank, side_rank, instrument_id)
```

where cancellations precede replacement admissions, SELL precedes BUY, and instruments use canonical order.

## 5. T+1 / settled-cash / fee-aware capping

### Ownership decision

Capping belongs in a new trading-kernel stage between `PositionSizer` and `PortfolioRebalanceCoordinatorV2`.

```python
PortfolioOrderSizingEvidenceV1
CappedPortfolioTargetV1
PortfolioOrderSizerV1
```

It does not belong in the provider, engine, legacy `PositionSizer`, or legacy `RebalanceCoordinator`.

### Sell capping

For each sell:

```text
capped_sell =
  min(requested_sell,
      AvailabilityState.position.sellable
      - retained_working_sell_coverage)
```

Apply the A-share lattice and whole-sell residual rules. T+1-unavailable quantity is omitted with durable evidence, not rejected later.

### Buy capping

Available budget is:

```text
CashAvailability.tradable
- active cash reservations
- active fee reservations
- exact sell-order fee reservations
```

Expected sell proceeds are never included.

For all requested buys:

1. Resolve notional and exact fee/minimum-commission reservation.
2. If fully affordable, retain requested quantities.
3. Otherwise find the largest common scale factor that is affordable.
4. Round every quantity toward zero on its instrument lattice.
5. Recompute exact minimum commissions after rounding.
6. Repeat until the canonical quantity vector is stable.
7. Leave all residual cash unallocated.

No “last instrument gets the residual” rule is allowed.

Output omissions distinguish:

- `T1_UNSELLABLE`
- `ZERO_AFTER_LATTICE`
- `SETTLED_CASH_CAPPED`
- `MINIMUM_COMMISSION_CAPPED`
- `ACTIVE_ORDER_COVERAGE`
- `TARGET_SUPERSEDED`

## 6. Additive portfolio profile/account contract

The existing singleton profile remains untouched.

### New profile declarations

```python
CnASharePortfolioInstrumentScopeDeclaration
CnASharePortfolioAccountScopeDeclaration
CnASharePortfolioAccountCapacityDeclaration
CnASharePortfolioProfileCompositionRequest
CnASharePortfolioProfileCompositionOutcome
CnASharePortfolioProfileCompositionFailure
CnASharePortfolioResolvedProfile
CnASharePortfolioProfileComposer
```

`CnASharePortfolioInstrumentScopeDeclaration` contains a canonical tuple of existing per-instrument scope declarations and requires:

- unique instruments;
- venues limited to XSHG/XSHE;
- CNY quote/settlement;
- exact catalog coverage;
- common source-manifest lineage;
- full timeline coverage.

`CnASharePortfolioAccountScopeDeclaration` contains canonical `venue_ids`, allowing XSHG and XSHE under one cash account.

### Account risk

Reuse one existing `AccountRiskPolicy` per venue.

Add:

```python
PortfolioAccountCapacityPolicyV1
PortfolioPreTradeRiskEvaluatorV1
```

The global policy binds:

- account ID;
- venue-policy hashes;
- global active-order capacity;
- per-venue active-order capacity;
- exposure capacity;
- fee-reserve funding source.

Capacity for this contract is:

```text
global active orders <= instrument catalog size
per-venue active orders <= instruments at that venue
active orders per instrument <= 1
```

Atomic cancellation occurs before replacement admission, so replacement does not temporarily consume a second active-order slot.

### Additive profile identities

```text
market:
  equity.cn_a_share.portfolio.market.v1

simulation:
  backtest.cn_a_share.portfolio.simulation.v1

account:
  account.cn_a_share.portfolio.cash.v1

profile model:
  equity.cn_a_share.portfolio.resolved-profile-composition.v1
```

## Public provider interface

```python
@dataclass(frozen=True, slots=True)
class CnASharePortfolioRequestIntent:
    schema_version: int
    experiment_id: str | None
    timeline_window: TimelineWindow
    execution_account_id: str
    reporting_currency: CurrencyId
    master_random_seed: int
```

Canonical type:

```text
cn_a_share_portfolio_request_intent@1
```

```python
@dataclass(frozen=True, slots=True)
class CnASharePortfolioProviderInputs:
    schema_version: int
    build_artifact_manifest: BuildArtifactManifest
    resolved_profile: CnASharePortfolioResolvedProfile
    instrument_catalog: InstrumentCatalog
    strategy_id: str
    sleeve_id: StrategySleeveId
    initial_cash: Money
    quantity_lattices: tuple[QuantityLattice, ...]
    order_capabilities: OrderCapabilitySet
    rebalance_policy: PortfolioRebalanceExecutionPolicyV1
```

Canonical type:

```text
cn_a_share_portfolio_provider_inputs@1
```

```python
def prepare_cn_a_share_portfolio_target_stream_backtest(
    *,
    request_intent: CnASharePortfolioRequestIntent,
    provider_inputs: CnASharePortfolioProviderInputs,
    target_stream_ref: BacktestTargetStreamRef,
    artifact_reader: ArtifactEnvelopeReader,
    artifact_publisher: ArtifactEnvelopePublisher,
    market_reader: MarketBundleReader,
    publication_root: Path,
) -> PreparedBacktestExecution
```

Reuse existing `PreparedBacktestExecution`.

## V2 resolved runtime types

```python
ResolvedPortfolioDecisionCycleV2
ResolvedPortfolioBarExecutionV2
ResolvedPortfolioExecutionCaseV2
ResolvedDecisionSnapshotRefreshPlanV1
ResolvedOrderTerminalPlanV1
ResolvedOrderCancellationPlanV1
```

A V2 decision cycle contains policies and identity-bound evidence required for runtime materialization. It does not contain a fixed tuple of final order admissions whose quantities assume future fills.

Order IDs are preallocated by decision ordinal and instrument identity; order quantities remain runtime-derived and are bound into the resulting event/evidence hashes.

## Canonical identities

```text
semantic spec:
  cn_a_share.portfolio.precomputed-target.execution-case.v1

case:
  cn_a_share.portfolio.precomputed-target.development.v2

execution input bundle:
  backtest_execution_input_bundle@7

execution request schema:
  7

snapshot refresh policy:
  equity.cn_a_share.portfolio.snapshot-refresh.v1

rebalance execution policy:
  equity.cn_a_share.portfolio.rebalance-execution.v1

portfolio sizing policy:
  equity.cn_a_share.portfolio.order-sizing.v1

portfolio capacity policy:
  account.cn_a_share.portfolio.capacity.v1
```

Semantic preimage binds:

- target-stream digest;
- portfolio resolved-profile digest;
- catalog and quantity-lattice hashes;
- snapshot-refresh policy hash;
- capping/sizing policy and fee-rule hashes;
- rebalance-execution policy hash;
- MarketBundle manifest hash;
- decision/bar/terminal/cancellation identity plans;
- build-artifact manifest hash;
- timeline, account, currency and seed.

## Event ordering

At each decision time:

```text
10 target decode/validation
20 decision batch
30 snapshot refresh
40 allocation
50 portfolio risk
60 raw position sizing
70 availability/fee-aware capping
80 rebalance plan
90 cancel requested
91 cancel completed
100 SELL admission, canonical instrument order
110 BUY admission, canonical instrument order
120 resource refresh
```

At each bar:

```text
10 pretrade revalidation
20 execution decision
30 ORDER_EXPIRED if DAY expiry
40 slippage/fill
50 fill accounting
60 fee/tax accounting
70 settlement/resource refresh
```

Within equal phases, source sequence follows canonical instrument ID.

## Failure precedence

### Preparation

1. Exact public type/schema failure.
2. Target-ref type, retention or tamper failure.
3. Portfolio profile composition/coverage failure.
4. Catalog, lattice or venue exact-cover failure.
5. MarketBundle capability/source identity failure.
6. Target-stream structure, identity or causality failure.
7. V2 semantic-spec/identity-plan failure.
8. Bundle V7 codec round-trip failure.
9. Artifact publication/readback failure.

No attempt exists after any preparation failure.

### Runtime decision

1. Target decode/validation/batch failure.
2. Snapshot-refresh evidence or valuation failure.
3. Allocation and portfolio-risk failure.
4. Raw position-sizing failure.
5. Availability/fee-aware capping contract failure.
6. Rebalance/supersession preflight failure.
7. Atomic cancellation/replacement evidence failure.
8. SELL admission failure.
9. BUY admission failure.
10. Resource-refresh failure.

### Runtime bar

1. Market-rule data integrity failure.
2. Capability/translation mismatch.
3. Pretrade contract failure.
4. Execution-model failure.
5. DAY expiry terminal-evidence failure.
6. Slippage/fill construction failure.
7. Financial dispatch/accounting failure.
8. Settlement/resource projection failure.
9. Snapshot failure at the next decision.

Ordinary unavailability produces capping/omission or working-order persistence; it does not terminate the run.

## Codec and migration

- Preserve bundle V1–V6 decoders and canonical fixtures unchanged.
- Add `_DecodedExecutionInputBundleV7`.
- Add `materialize_execution_input_bundle_v7`.
- Register V7 in the existing execution-input catalog.
- Add V7 durable rebuild support.
- Dispatch V7 only to `ResolvedPortfolioExecutionCaseV2`.
- No V7-to-V6 fallback.
- Do not add V2 fields to legacy canonical bodies.
- Do not version-bump or rewrite existing cash/fixed-singleton profile keys.
- Existing `BacktestRequest@1` remains valid; new profile keys and semantic hash distinguish the run.

## Exact write set

### Trading kernel

New:

- `packages/trading-kernel/src/crypto_quant_trading/portfolio_rebalance.py`
- `packages/trading-kernel/src/crypto_quant_trading/portfolio_order_sizing.py`
- `packages/trading-kernel/src/crypto_quant_trading/portfolio_snapshots.py`
- `packages/trading-kernel/src/crypto_quant_trading/portfolio_pretrade_risk.py`

Changed additively:

- `packages/trading-kernel/src/crypto_quant_trading/__init__.py`

No canonical changes to legacy `rebalance.py`, `snapshots.py` or `pretrade_risk.py`.

### Backtest runtime

New:

- `packages/backtest-runtime/src/crypto_quant_backtest/cn_a_share_portfolio_profile.py`
- `packages/backtest-runtime/src/crypto_quant_backtest/cn_a_share_portfolio_provider.py`

Changed additively:

- `packages/backtest-runtime/src/crypto_quant_backtest/engine.py`
- `packages/backtest-runtime/src/crypto_quant_backtest/financial_dispatch.py`
- `packages/backtest-runtime/src/crypto_quant_backtest/execution_inputs.py`
- `packages/backtest-runtime/src/crypto_quant_backtest/_durable_rebuild.py`
- `packages/backtest-runtime/src/crypto_quant_backtest/facade.py`
- `packages/backtest-runtime/src/crypto_quant_backtest/__init__.py`

Must remain untouched:

- `cash_development_provider.py`
- `cn_a_share_profile.py`
- legacy target-stream schema and V6 fixtures.

### Tests

New focused suites:

- `tests/kernel/portfolio/test_portfolio_order_sizing.py`
- `tests/kernel/portfolio/test_portfolio_rebalance.py`
- `tests/kernel/portfolio/test_portfolio_snapshot_refresh.py`
- `tests/kernel/portfolio/test_portfolio_pretrade_risk.py`
- `tests/runtime/engine/test_order_terminal_lifecycle_v2.py`
- `tests/runtime/engine/test_portfolio_supersession_v2.py`
- `tests/runtime/engine/test_portfolio_snapshot_refresh_v2.py`
- `tests/runtime/execution_inputs/test_execution_input_bundle_v7.py`
- `tests/runtime/profiles/cn_a_share/test_portfolio_profile.py`
- `tests/runtime/providers/test_cn_a_share_portfolio_provider.py`
- `tests/architecture/test_cn_a_share_portfolio_provider_boundary.py`

Existing legacy golden suites are required preservation gates.

## Vertical implementation phases

### Phase 0 — baseline freeze

- Record current V1–V6 fixture hashes.
- Run existing cash, target-stream, fixed-singleton and rebalance goldens.

Sentinel: zero baseline diff.

### Phase 1 — order terminal lifecycle

Implement expiry/cancellation plans and engine terminal transitions.

Sentinel:

- DAY order becomes `EXPIRED`;
- reservation disappears;
- cash unchanged;
- GTC order remains active.

### Phase 2 — snapshot refresh

Implement current-ledger snapshot refresh and decision artifact.

Sentinel: second decision sees the first fill’s cash, holdings, lots and fees.

### Phase 3 — capping and side policy

Implement portfolio sizing, T+1 sell cap, settled-cash buy cap, exact fee/minimum commission and side-specific TIF.

Sentinel:

- sell quantity never exceeds sellable;
- buy commitments never exceed tradable cash;
- SELL is GTC;
- BUY is DAY;
- legacy rebalance golden unchanged.

### Phase 4 — atomic supersession

Implement `PortfolioOrderPlanV2` and transactional engine application.

Sentinel:

- stale GTC order is cancelled;
- reservation released;
- replacement causation is exact;
- no `ORDER_PLAN_MISMATCH`;
- failed replacement preflight commits nothing.

### Phase 5 — case V2 and codec V7

Implement V2 resolved cases, materialization, catalog decoding and durable rebuild.

Sentinel: byte-stable V7 round trip, tamper rejection and replay rebuild.

### Phase 6 — portfolio profile

Implement multi-instrument/multi-venue composition and global capacity.

Sentinel: two buys plus one working sell admitted; singleton profile hashes unchanged.

### Phase 7 — public provider

Implement the public preparation operation and full fixture journey.

Sentinel journey:

- two buys;
- retained holding;
- T+1-blocked sell;
- delayed lower-limit sell;
- upper-limit DAY buy expiry;
- residual cash;
- board-lot rounding;
- minimum commission and sell tax;
- target supersession;
- replay-stable ledger/lot/evidence hashes.

## Drift / contradiction check

The previous proposed provider input used one `CnAShareResolvedProfile`; this is invalid for a cross-venue portfolio and is replaced by `CnASharePortfolioResolvedProfile`.

Provider-local capping, cancellation, snapshot refresh or TIF rewriting remains forbidden.

## Recommendation

**READY — fixture-level development implementation.**

All six additive contracts are now resolved with explicit ownership and identities. No remaining architecture choice needs to be made by the implementation writer.

**Real-data execution remains NOT_READY.** This decision does not qualify historical MarketBundle, rule, fee, tax or corporate-action authority and grants no trading authorization.

## Risks

- V2 engine mutation must be transactional; partial cancellation is unacceptable.
- Dynamic order quantities must remain bound to deterministic preallocated IDs and evidence.
- Minimum commissions make proportional buy capping discontinuous; the iterative result must be canonical and tested.
- Snapshot refresh must use current lot cost basis, not stale precomputed valuation values.
- Global capacity must cover both XSHG and XSHE without weakening venue-specific risk policies.
- Adding V7 catalog support can accidentally alter legacy decoder dispatch if not strictly version-gated.

## Need from main agent

No further architecture decision is required for fixture-level work. The main agent should enforce the phase order and preservation gates.

## Suggested execution prompt

Implement Phases 0–1 only in `quant-backtest-a-share-portfolio`. Add terminal expiry/cancellation evidence and reservation release without touching legacy canonical types or cash/fixed-singleton fixtures. Stop after focused and preservation sentinels pass; return the candidate commit and exact hashes.