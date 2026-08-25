# Binance USD-M TradFi perpetual Bar preparation capability candidate

- **Status:** CANDIDATE — owner approval required before implementation
- **Initial instrument:** `KORUUSDT`
- **Product identity:** exact Binance `TRADIFI_PERPETUAL`
- **Grade ceiling:** `development`
- **Consumer:** frozen KORUUSDT closed-market range research plan

## 1. Problem and seam

The accepted Binance USD-M instrument module currently requires exact `contract_type == "PERPETUAL"`. KORUUSDT is `TRADIFI_PERPETUAL`, so it correctly fails as `UNSUPPORTED_CONTRACT_TYPE`. The public Backtest root also exposes no preparation operation for an immutable Binance TradFi Bar experiment.

The smallest deep module is one new public preparation interface:

```python
prepare_binance_usdm_tradifi_bar_backtest(
    *,
    request_intent: BinanceUsdmTradifiBarRequestIntent,
    provider_inputs: BinanceUsdmTradifiProviderInputs,
    artifact_reader: ArtifactEnvelopeReader,
    artifact_publisher: ArtifactEnvelopePublisher,
    market_reader: MarketBundleReader,
    publication_root: Path,
) -> PreparedBacktestExecution | BinanceUsdmTradifiPreparationFailure
```

The caller supplies intent plus one exact retained `MarketBundleRef`. The implementation owns metadata/rule/profile resolution, calendar and corporate-action qualification, strategy target-stream construction, profile composition, request registration, input materialization, and publication. Platform callers must not assemble private Backtest objects.

Deletion of this module would force every consumer to reproduce TradFi product qualification, calendar closure, split safety, funding/account/profile composition, and next-eligible-trade-event causality. The interface therefore earns its depth.

## 2. Public intent

```python
BinanceUsdmTradifiBarRequestIntent@1 = {
    experiment_id: str | None,
    timeline_window: TimelineWindow,
    execution_account_id: str,
    reporting_currency: CurrencyId("USDT"),
    master_random_seed: int >= 0,
    expected_market_bundle_ref: MarketBundleRef,
    strategy_definition_ref: ArtifactRef,
    strategy_parameter_set_ref: ArtifactRef,
    requested_result_grade: "development",
}
```

Exact-type construction is required. Unknown fields, schema versions, currencies, grades, negative seeds, or foreign refs fail before storage or market reads.

The intent does not expose profile parts, request hashes, semantic run IDs, resolved cases, target streams, fee engines, or simulation modules. The common strategy-definition ref owns the algorithm; the exact parameter-set ref owns one of the eight precommitted combinations and changes per Trial.

```python
BinanceUsdmTradifiProviderInputs@1 = {
    base_build_artifact_manifest: BuildArtifactManifest,
    synthetic_initial_equity: Money(10000, "USDT"),
}
```

The caller supplies the base build manifest as immutable build authority. Preparation may enrich it only through the accepted deterministic build-manifest operation and must bind the enriched hash into the Backtest request. Synthetic initial equity is a development ledger input, not Binance wallet or exposure-capacity evidence.

## 3. Exact product identity

V1 adds a **separate** TradFi instrument module and component key, reusing only private parsing helpers. It must not widen or branch inside the existing immutable `BinanceUsdmInstrumentModel` whose digest binds `supported_contract_type = PERPETUAL`.

```text
existing model: crypto.binance_usdm.instrument-metadata.v1 → PERPETUAL only, unchanged
new model:      crypto.binance_usdm.tradifi.instrument-metadata.v1 → TRADIFI_PERPETUAL only
other values:   UNSUPPORTED_CONTRACT_TYPE
```

TradFi identity must preserve:

- raw `contractType = TRADIFI_PERPETUAL` in source and profile digest;
- stable caller-supplied instrument lineage;
- `symbol`, `pair`, base/quote/margin currencies, listing interval, and lifecycle revisions;
- exact historical quantity-unit convention and every effective rule revision;
- reference-asset declaration and source identity without claiming ownership of the underlying ETF.

The new resolution type and component digest remain disjoint from the existing `PERPETUAL` model and profile. No existing canonical bytes, failures, refs, component hashes, or tests may change.

## 4. Required MarketBundle evidence

The exact MarketBundle must retain immutable source bytes, hashes, revisions, coverage, event/effective/available/captured times, and gap reports for:

1. **Instrument metadata** — initial `exchangeInfo` revision plus every listing, status, symbol, delivery, and rule-relevant revision. USD-M `exchangeInfo` supplies no `contractSize` field.
2. **Order rules** — exact historical `PRICE_FILTER`, `LOT_SIZE`, `MARKET_LOT_SIZE`, `MIN_NOTIONAL`, admission state, order/TIF capabilities, and known deferred keys.
3. **Margin tiers** — initial bracket state and every bracket revision with finite coverage.
4. **Execution reference** — aggregate trades or another separately approved historical trade source.
5. **Mark purposes** — closed mark-price bars for valuation, margin, and conservative liquidation audit.
6. **Index feature stream** — closed index-price bars retained separately from mark purposes; no price-purpose substitution.
7. **Funding** — exact Funding Rate History rows, associated funding marks, rate types, slot times, and source revisions.
8. **Account profile** — archived exact account/symbol commission, one-way/single-asset/cross mode, selected leverage, no fee burn, capacity, and effective intervals.
9. **Calendars** — versioned `XKRX` regular-session and `ARCX` KORU core-session calendars with holidays, DST, early closes, and source provenance.
10. **Corporate actions** — Binance and underlying-issuer split notices, suspension/cancel-only/resumption times, rule revisions, and a derived post-adjustment unit-regime identity. No fabricated `exchangeInfo.contractSize` field is permitted.
11. **Bar strategy inputs** — completed one-hour mark and index bars with availability not earlier than close.

Current REST responses, the system clock, mutable network calls, file modification time, neighboring rows, or Yahoo data cannot fill historical gaps during preparation or execution.

## 5. TradFi strategy feature semantics

The initial public operation supports only the frozen closed-market range strategy definition and one versioned next-eligible-trade-event execution convention. It does not add a generic formula engine.

The preparation implementation constructs the deterministic target stream from:

```text
premium = log(completed mark close / completed index close)
closed interval = neither accepted XKRX regular session nor accepted ARCX core session open
formation range = high/low of the first N completed mark bars
entry/exit decision = completed mark close only
fill eligibility = first retained aggregate-trade event at or after the next eligible hourly boundary
```

Invariants:

- mark and index bars share exact instrument, interval, timestamp, coverage, and availability context;
- no bar is visible before close/availability;
- no signal fills on its source Bar;
- the fill event is the first retained aggregate trade at or after the eligible boundary; its event time and availability equal the retained trade time, never the nominal bucket boundary or an archived kline open;
- no intrabar stop, limit, midpoint touch, or OHLC-path inference;
- premium is not substituted by the premium-index endpoint or recomputed from current data;
- the target stream exact-covers the declared decision schedule and contains at most one entry per closed interval;
- algorithm semantics come from the exact strategy-definition ref and one Trial's values come from its exact strategy-parameter-set ref; `experiment_id` is never decoded as parameter authority.

A future strategy requires a new strategy-definition identity and explicit acceptance; this operation is not a general user-supplied callback seam.

## 6. Corporate-action boundary

V1 does not implement generic position transformation or pointwise cross-revision profile composition. Every prepared timeline must begin on or after `2026-07-15T10:00:00.000000Z`, after the documented adjustment/resumption, and must fit wholly inside one exact visible metadata, order-rule, margin-tier, account/fee, and unit-regime coverage band.

The bundle still retains the split notices and prior regime as provenance, but V1 preparation rejects:

- any timeline overlapping or preceding the adjustment window;
- any run whose rule/profile band changes before timeline end;
- any initial position/order state;
- any attempt to synthesize adjusted pre-split execution data or carry positions across regimes.

This removes generic corporate-action and pointwise-composer work from V1. A future pre-split or cross-revision study requires a separate profile version and contract.

## 7. Funding boundary

Existing regular-funding semantics are reused exactly. V1 accepts only one visible immutable `Regular` funding row per slot.

Any `Special` funding row—such as an additional stock-dividend funding event—returns a structured `SPECIAL_FUNDING_UNSUPPORTED` preparation failure for the affected coverage. V1 does not drop, merge, net, relabel, or zero-fill it. Supporting multiple same-time funding events requires a separate generic funding-contract version.

Funding interval is derived only from exact historical rows, never from a fixed eight-hour assumption or current Funding Info.

## 8. Profile composition

A successful operation composes:

```text
market profile:   crypto.binance_usdm.tradifi.v1
simulation:       bar.next_eligible_trade_event.tradifi.v1
account profile:  binance.usdm.standard-cross.v1
```

A separate TradFi composer consumes the new TradFi instrument resolution plus one exact active post-split order, margin, account/fee, capacity, price-purpose, funding, and calendar band covering the whole run. It may reuse existing private composition helpers but does not call or widen the immutable ordinary G10G composer.

The simulation key binds concrete component identities for next-eligible aggregate-trade execution, an additive taker-liquidity fill role, the exact nonzero slippage model/calibration, latency, liquidity, closeout, and conservative liquidation audit. It reuses generic position accounting, funding, margin, pre-trade risk, fee assessment, run-end closeout, and conservative liquidation logic. The taker-role addition must be versioned so existing full-fill behavior and hashes remain unchanged.

Required limitations remain embedded in the profile digest:

- development grade only;
- first-retained-trade full-fill simulation, not matching-engine parity;
- an additive versioned fill-liquidity role fixed to `taker` for this simulation profile;
- deterministic calibrated nonzero slippage, never implicit zero;
- one-way, single-asset, crossed USDT account only;
- no BNB discount, negative rebate, Hedge Mode, isolated margin, Multi-Assets, Portfolio Margin, ADL, bankruptcy, or insurance-fund execution;
- no settlement-price authority or live/deployment authorization.

## 9. Fee, sizing, and execution rules

The initial strategy profile requires:

- exact historical per-symbol maker/taker commission evidence;
- `feeBurn = false`;
- a versioned execution result carrying exact `taker` liquidity role for every simulated entry/exit fill;
- fixed 10,000 USDT **synthetic initial equity** deposited into the development ledger, distinct from Binance account order/exposure-capacity evidence;
- fixed 1,000 USDT target position notional;
- selected leverage 1x;
- quantity calculated causally from the completed decision-time mark close and rounded down to the active historical step; realized fill notional may drift at the later execution event;
- below-minimum quantity/notional produces no order;
- exact active market-quantity maximum and exposure ceilings;
- an exact `SlippageCalibrationRef` applicable to KORUUSDT, 1-hour decisions, first-retained-trade fills, the declared notional, and market state.

The preparation operation never invents a public fee table, VIP rate, account snapshot, slippage rate, or current-rule fallback.

## 10. Failure precedence

Preparation fails before Backtest execution in this order:

1. intent/provider-input type, schema, ref, currency, grade, base build manifest, or synthetic-equity value invalid;
2. MarketBundle ref, manifest, publication, retention, hash, or reader mismatch;
3. instrument lineage, listing, exact `TRADIFI_PERPETUAL` identity, or lifecycle invalid;
4. calendar, post-adjustment start, single-regime coverage, or empty initial-state requirement invalid;
5. order-rule or quantity/price/notional revision invalid;
6. execution-reference, mark-purpose, index-feature, funding, or availability coverage invalid;
7. `Special` funding encountered;
8. margin-tier, account-mode, leverage, commission, fee-burn, capacity, or currency context invalid;
9. slippage calibration missing or outside applicability;
10. strategy definition ref, strategy parameter-set ref, decision schedule, premium formula, or target exact-cover invalid;
11. profile composition or deferred-rule qualification invalid;
12. request registration, input materialization, artifact publication, or storage failure.

No failure causes a contract-type alias, latest-value fallback, forward fill, future-open sizing, zero metric, fabricated terminal, partial prepared result, or lower-grade synthesis.

## 11. Output and replay

Success returns one ordinary public `PreparedBacktestExecution` compatible with `execute_experiment()`. Existing Backtest run, publication, repository, analysis, Research, and Validation interfaces remain unchanged.

Replay with identical intent, provider inputs, base build manifest, bundle ref, strategy ref, parameter-set ref, source revisions, and publication root must return the same prepared request/ref identities and must not:

- reacquire network data;
- refresh source or governance time;
- publish a second conflicting request;
- change the profile digest or target stream;
- repeat economic execution when canonical evidence already exists.

## 12. Acceptance matrix

### Positive

1. Exact post-adjustment KORUUSDT TradFi metadata, one complete single-regime coverage band, calendars, regular funding, account/profile evidence, base build manifest, strategy ref, and parameter-set ref prepare successfully.
2. A timeline starting at/after `2026-07-15T10:00:00.000000Z` and ending before any profile/rule revision prepares with empty initial position/order state.
3. Mark/index completed-close premium and first-retained-trade entry/exit schedule exact-cover the timeline without using nominal kline-open availability.
4. Fixed 1,000 USDT sizing uses the decision-time completed mark, rounds down under the active quantity rule, and records realized-notional drift at fill.
5. The TradFi simulation emits taker-role fills and applies the exact nonzero slippage calibration.
6. Deterministic replay returns identical enriched build manifest, prepared refs, target stream, and profile digest.

### Negative

1. Existing `PERPETUAL` metadata sent to the TradFi operation fails exact product identity; existing ordinary Binance profile remains unchanged.
2. Raw/current/unknown contract type, wrong symbol lineage, missing listing revision, or current exchange-info fallback fails.
3. Missing/late calendar, holiday, early-close, mark, index, funding, fee, margin, order-rule, account, or slippage evidence fails before execution.
4. Same-Bar fill, nominal kline-open fill, intrabar midpoint/stop, future-open sizing, open-session carry, pre-adjustment/cross-revision timeline, nonempty initial state, or incomplete target stream fails.
5. Missing/foreign parameter-set ref, base build manifest, fill-liquidity role, or slippage calibration fails.
6. `Special` funding, BNB discount, negative rebate, unsupported margin/account mode, deferred execution rule, or above-cap notional fails.
7. Provider/storage/tamper/retention failure produces no prepared result and no fabricated Backtest terminal.

### Compatibility

- all existing Binance `PERPETUAL` profile tests and canonical hashes unchanged;
- `prepare_cash_development_backtest` and model-bound preparation unchanged;
- existing V1-V5 Platform suites remain green;
- no Research, Validation, Promotion, or Foundation schema change;
- additive versioned generic fill-liquidity/execution-result support leaves every existing Engine/Fill path and canonical hash unchanged;
- no Shadow/Live/deployment capability.

## 13. Proposed write set

Only after approval:

- one separate exact TradFi instrument model/resolution under `crypto_quant_trading.profiles.binance_usdm`, without changing the existing model/component;
- one separate single-regime TradFi profile composer and profile key;
- one new Backtest public preparation module, request/provider-input values, and public-root exports;
- one new versioned next-eligible-trade-event simulation profile with additive taker-role Fill/execution-result support and preserved old hashes;
- one immutable post-adjustment TradFi MarketBundle acquisition/build route with source/checksum/gap receipts;
- focused product, calendar, post-adjustment regime, funding, fee role, slippage, profile, preparation, replay, and mutation tests;
- Backtest capability receipt and later Platform pin/consumer receipt.

No change is authorized by this candidate itself.

## 14. Implementation DAG

```text
BT-TRADIFI-CON-01 contract approval
  ├─→ BT-TRADIFI-DATA-01 immutable bundle/acquisition route
  ├─→ BT-TRADIFI-PROFILE-01 exact product/profile qualification
  └─→ BT-TRADIFI-PREP-01 public preparation operation
          └─→ KORU-EXP-01 frozen 8-trial discovery
                  └─→ KORU-SV-01 future holdout Validation
```

Data and profile work may be implemented independently after contract approval, but one sequential writer per repository is required. Platform experiment execution remains blocked until all three Backtest leaves are accepted and remotely pinned.

## 15. Explicit exclusions

- generic corporate-action position transformation;
- `Special` funding support;
- order-book, queue, partial-fill, or market-making simulation;
- intrabar path reconstruction;
- provider qualification beyond the frozen sources named by the bundle;
- decision-grade or deployment qualification;
- Shadow, Live, credentials, orders, or capital movement;
- generic workflow, database, queue, scheduler, or service infrastructure.
