# A-share Portfolio Seam Oracle Review

## Inherited decisions

- Backtest exclusively owns fills, fees, settlement, accounting, PnL and evidence.
- Platform/research code must not import private Backtest modules or create a simulator.
- V18 requires delayed lower-limit exits; failed buys remain cash.
- Dividend strategy currently produces a 56-stock equal-weight target.
- Existing public cash preparation remains immutable and replay/hash compatible.
- No strategy is trade-authorized.

## Diagnosis

Two placements were compared:

### A. Dedicated A-share portfolio provider — selected

Add a deep provider module beside `cash_development_provider.py`. It verifies the target-stream ref, composes A-share authorities, constructs the full portfolio timeline and returns existing `PreparedBacktestExecution`.

This preserves existing interfaces and concentrates A-share execution semantics in Backtest.

### B. Generalize `cash_development_provider.py` — rejected

The existing module hardcodes one instrument and one positive BUY:

- `cash_development_provider.py:358`
- `cash_development_provider.py:545`

Generalizing it would change existing request identities, semantic hashes, bundle bytes and cash-provider golden fixtures.

### C. Put preparation in `cn_a_share_profile.py` — rejected

`CnAShareProfileComposer` owns profile composition, not requests, target execution, runtime construction or evidence publication.

## Drift / contradiction check

The plan correctly rejects a Platform-side simulator. The remaining contradiction is that it suggests the public provider interface might be frozen while the kernel exposes only one `TimeInForce` for every order in a rebalance:

- `trading-kernel/src/crypto_quant_trading/rebalance.py:74-116`

This cannot express the inherited requirement:

- SELL: retain/retry after lower-limit or suspension failure.
- BUY: DAY-only; failure leaves cash and is not retried.

Choosing provider-managed multiple cycles versus extending the kernel is an unapproved architecture decision.

## Proposed public interface

After the missing lifecycle decision is approved:

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
    resolved_profile: CnAShareResolvedProfile
    instrument_catalog: InstrumentCatalog
    strategy_id: str
    sleeve_id: StrategySleeveId
    initial_cash: Money
    quantity_lattices: tuple[QuantityLattice, ...]
    order_capabilities: OrderCapabilitySet
    rebalance_execution_policy: CnAShareRebalanceExecutionPolicyV1
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

Reuse without modification:

- `BacktestTargetStreamRef`
- `PrecomputedTargetStream`
- `PreparedBacktestExecution`
- `BacktestRuntime`
- `BacktestEvidenceRepository`

## Proposed identities

```text
profile market:     equity.cn_a_share.portfolio.market.v1
profile simulation: bar.next_eligible_open.cn_a_share.portfolio.development.v1
profile account:    equity.cn_a_share.cash.portfolio.long-only.v1

semantic spec: cn_a_share.portfolio.precomputed-target.execution-case.v1
case key:      cn_a_share.portfolio.precomputed-target.development.v1
```

Semantic identity must bind:

- target-stream digest;
- resolved A-share profile digest;
- instrument-catalog hash;
- quantity-lattice hashes;
- rebalance-execution-policy hash;
- MarketBundle manifest hash and source coverage identities;
- execution-case semantic hash;
- build-artifact manifest hash;
- timeline window, account identity, currency and seed.

## Target semantics

Existing `TargetExposureFraction` and `TargetSnapshot` are sufficient:

- canonical scale 12;
- targets are nonnegative absolute fractions of allocated sleeve NAV;
- sum must be `<= 1`;
- residual is cash;
- omitted instruments mean zero target, not “retain”;
- each event is a complete portfolio snapshot;
- empty target tuple means all cash;
- no shorting or leverage;
- `effective_time` must be the exact next eligible session open;
- a newer target supersedes the prior target and its remaining working orders.

Existing target-stream schema and V6 embedding should remain unchanged.

## Required execution policy

The smallest missing contract is:

```python
CnAShareRebalanceExecutionPolicyV1
```

It must approve all of these together:

1. Sells are planned before buys.
2. Lower-limit/suspension-blocked sells remain working until filled, expired or superseded.
3. Buys use DAY lifetime; failed buys expire and remain cash.
4. Buy sizing uses only settled, unreserved cash after fees—not expected sell proceeds.
5. T+1-unavailable quantities cannot be sold.
6. The next target cancels or supersedes stale working orders deterministically.
7. Minimum commission applies per actual order/fill according to the accepted authority.

The current single-TIF `RebalancePolicy` cannot represent this.

## Failure precedence

### Preparation, before an attempt

1. Wrong exact public type or schema version.
2. Target ref missing, wrong type/version, tampered or retention-unavailable.
3. MarketBundle/catalog identity mismatch.
4. Resolved-profile or source-coverage mismatch.
5. Invalid target-stream structure, identity or causality.
6. Negative targets, sum above one, unknown/out-of-universe instruments.
7. Missing required market/rule/fee/corporate-action streams.
8. Build/profile key conflict.
9. Publication or readback identity failure.

### Runtime

1. Durable cancellation or target supersession.
2. Target expiry.
3. T+1/settlement availability.
4. Suspension, closed session or absent authoritative bar.
5. Price-limit liquidity block.
6. Quantity-lattice/zero-lot rejection.
7. Cash and fee-reserve insufficiency.
8. Capability, market-rule and risk rejection.
9. Fill, fee/tax accounting, settlement and final valuation.

Missing authoritative data must fail closed, not become a zero return or order rejection.

## Preserved identities and fixtures

Must remain byte/hash stable:

- `cash_development_provider.py`
- cash profile/spec/case keys;
- cash target-stream V6 fixtures;
- `tests/runtime/providers/test_cash_development_provider.py`
- `tests/runtime/target_stream/test_backtest_target_stream_execution.py`
- fixed-singleton A-share profile fixtures and goldens;
- existing `PreparedBacktestExecution` signature;
- target-stream schema version 1.

All new profile keys, semantic keys and fixtures must be additive.

## Exact write set after approval

Minimum:

- `backtest-runtime/src/crypto_quant_backtest/cn_a_share_portfolio_provider.py`
- `backtest-runtime/src/crypto_quant_backtest/__init__.py`
- `tests/runtime/providers/test_cn_a_share_portfolio_provider.py`
- `tests/architecture/test_cn_a_share_portfolio_provider_boundary.py`

If side-specific lifetime is kernel-owned, additionally:

- `trading-kernel/src/crypto_quant_trading/rebalance.py`
- `trading-kernel/src/crypto_quant_trading/__init__.py`
- focused rebalance contract/golden tests.

No Platform production file belongs in the execution write set.

## Sentinel tests

- Two buys, one retained holding, one sell and residual cash.
- Lower-limit sell persists and fills later.
- Upper-limit buy expires and remains cash.
- Same-day sale fails under T+1.
- 100-share rounding never increases exposure.
- Sell orders precede buy sizing.
- Minimum commission and sell tax use accepted historical rules.
- New target supersedes stale sell and buy orders deterministically.
- Replay ledger, lot-book and evidence hashes are stable.
- Target/bundle tamper and retention loss fail before attempt.
- All existing cash and fixed-singleton golden hashes remain unchanged.

## Recommendation

Keep the dedicated-provider placement. Do not generalize the cash provider.

Status remains **NOT_READY** solely because the repository has not approved side-specific rebalance order lifetimes and supersession semantics. Real-data execution remains separately blocked by historical source authority, but fixture-level implementation can proceed once this kernel contract is approved.

## Risks

- A provider-local sell/buy workaround would bypass the kernel’s policy hash and create hidden semantics.
- Treating omitted instruments as retain instead of zero changes every rebalance.
- Using expected sell proceeds to fund buys creates impossible fills.
- Updating existing cash provider keys would invalidate accepted replay evidence.
- Fixture readiness does not qualify the real MarketBundle or authorize trading.

## Need from main agent

Approve this single contract decision:

> Introduce `CnAShareRebalanceExecutionPolicyV1` with sell-GTC, buy-DAY, sell-before-buy, settled-cash-only sizing and deterministic target supersession.

Without that approval, a writer would be choosing money/accounting architecture.

## Suggested execution prompt

No executor handoff yet. The contract is NOT_READY pending the decision above.