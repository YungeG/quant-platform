# BT-TRADIFI-01 Full Implementation Packet

Status: **READY — BT-TRADIFI-DISPATCH-01 approved by the Platform owner**

## Outcome

Backtest exposes one additive public preparation interface that accepts exact KORUUSDT `TRADIFI_PERPETUAL` evidence and returns the existing `PreparedBacktestExecution` shape for the frozen post-adjustment closed-market strategy, without changing ordinary `PERPETUAL` identities or generic Research/Validation interfaces.

## Authority

| ID | Source | Requirement or invariant |
| --- | --- | --- |
| C1 | `research/koruusdt/tradifi-perpetual-capability-contract.md` | Candidate public interface, profile identities, evidence closure, failure precedence, and compatibility |
| C2 | `research/koruusdt/closed-market-range-plan.md` | Post-adjustment discovery/holdout, eight parameter sets, causal decision/fill semantics, development grade |
| B1 | `backtest/docs/research/binance-usdm-instrument-metadata-primary-sources.md` | Existing `PERPETUAL` model remains immutable; USD-M exchangeInfo has no contractSize |
| B2 | `backtest/docs/research/binance-usdm-profile-composition-primary-sources.md` | G10B-G10G authority, single-band profile composition, development limitations |
| B3 | `backtest/docs/research/binance-usdm-price-purpose-streams-primary-sources.md` | Aggregate-trade execution reference, closed mark bars, exact event/availability time, no kline-open lookahead |
| B4 | `backtest/docs/research/binance-usdm-funding-source-semantics-primary-sources.md` | Exact Regular funding rows; Special rows fail closed |
| B5 | `backtest/docs/research/binance-usdm-fee-account-profile-primary-sources.md` | Account-specific maker/taker rates, standard cross/one-way/single-asset account, no fee-burn synthesis |
| B6 | `backtest/docs/research/binance-usdm-order-rules-primary-sources.md` | Historical price/quantity/min-notional rules and no current fallback |
| B7 | `backtest/docs/research/binance-usdm-margin-tiers-primary-sources.md` | Historical finite tier coverage and separate selected leverage |
| P1 | `backtest/packages/backtest-runtime/src/crypto_quant_backtest/__init__.py` | Only public-root exports are callable by Platform |
| P2 | `backtest/packages/backtest-runtime/src/crypto_quant_backtest/execution.py` | Existing next-eligible model and `FullFillBuilder` hashes/behavior remain unchanged |
| A1 | `research/koruusdt/tradifi-perpetual-capability-amendment-01.md` | Bundle-owned target streams, SourceSnapshot retention, KORU source modules, and versioned durable fill-liquidity input path |
| A2 | `research/koruusdt/tradifi-perpetual-dispatch-amendment-02.md` | Production derivative financial dispatcher, exact selector, durable profile-wire codec, and multi-order derivative Case planner |

## Ownership

- **Owner/session:** one Backtest writer after approval; parent Platform session integrates/reviews only.
- **Worktree/branch:** dedicated Backtest worktree or branch `feature/tradifi-perpetual-preparation`; do not write on Backtest `main` directly.
- **Shared-file owner:** the Backtest writer exclusively owns public roots and `execution.py` during implementation.
- **Platform integration owner:** parent session binds the accepted Backtest revision only after Backtest receipt and remote reachability.

## Exact write set

### New modules

1. `backtest/packages/trading-kernel/src/crypto_quant_trading/profiles/binance_usdm/tradifi_instrument_metadata.py`
2. `backtest/packages/backtest-runtime/src/crypto_quant_backtest/binance_usdm_tradifi_profile.py`
3. `backtest/packages/backtest-runtime/src/crypto_quant_backtest/binance_usdm_tradifi_preparation.py`
4. `backtest/packages/market-bundle-builder/src/crypto_quant_bundle_builder/binance_usdm_tradifi_execution_bundle_v1.py`
5. KORU source-bounded aggregate-trade, mark/index, and funding-history normalizer modules

### Additive shared-file edits

1. `backtest/packages/trading-kernel/src/crypto_quant_trading/profiles/binance_usdm/__init__.py`
2. `backtest/packages/backtest-runtime/src/crypto_quant_backtest/__init__.py`
3. `backtest/packages/market-bundle-builder/src/crypto_quant_bundle_builder/__init__.py`
4. `backtest/packages/backtest-runtime/src/crypto_quant_backtest/execution.py` — existing additive role-aware builder retained; do not edit `FullFillBuilder` behavior or canonical output.
5. `backtest/packages/backtest-runtime/src/crypto_quant_backtest/engine.py` — select legacy or role-aware builder from the new versioned execution plan.
6. `backtest/packages/backtest-runtime/src/crypto_quant_backtest/execution_inputs.py` — add a new durable schema/materializer/decoder version while preserving legacy bytes.

### Tests and docs

- new focused test modules under the corresponding package test roots;
- compatibility guards for existing ordinary Binance component/profile hashes;
- one public-preparation integrated test and replay test;
- one Backtest acceptance receipt and implementation-plan update.

No `Fill`, Research, Validation, Foundation, Promotion, or existing MarketBundle schema edit is planned. A new additive execution-plan/input schema version is now required; every legacy schema and byte identity remains unchanged.

## Flow and seam

Before:

```text
Platform Research
  -> no public TradFi preparation operation
  -> exact TRADIFI_PERPETUAL metadata fails unsupported_contract_type
```

After:

```text
Research TrialExecution
  -> prepare_binance_usdm_tradifi_bar_backtest(intent, provider_inputs, ports)
       -> verify exact MarketBundleRef + BuildArtifactManifest
       -> resolve separate TradFi instrument model
       -> resolve one post-adjustment G10B-F evidence band
       -> decode one preparation-authority event
       -> select/verify the bundle-owned target stream mapped to parameter ref
       -> qualify calendars/funding/account/fees/slippage
       -> compose TradFi market/simulation/account profiles
       -> register request + materialize existing execution input bundle
       -> publish request/input artifacts
  -> PreparedBacktestExecution
  -> existing execute_experiment / BacktestRuntime / evidence repository / analysis
```

## Symbol plan

| Symbol | Action | Exact responsibility | Consumer |
| --- | --- | --- | --- |
| `BinanceUsdmTradifiInstrumentMetadataResolution` | add | Exact `TRADIFI_PERPETUAL` identity, lifecycle, currencies, unit regime, source/ref/model digest | TradFi profile composer |
| `BinanceUsdmTradifiInstrumentModel` | add | Resolve only exact TradFi revisions; separate component key; reject PERPETUAL/unknown | preparation |
| `BinanceUsdmTradifiProfileCompositionRequest` | add | Exact single-band TradFi instrument + G10B-F resolutions, calendars, timeline, simulation authority | composer |
| `BinanceUsdmTradifiProfileComposer` | add | Produce `crypto.binance_usdm.tradifi.v1` market profile and standard account profile without calling ordinary G10G composer | resolver registry |
| `BinanceUsdmTradifiSimulationProfile` | add | Bind `bar.next_eligible_trade_event.tradifi.v1`, exact slippage calibration, latency, liquidity, closeout, liquidation components | registry/runtime |
| `LiquidityRoleFullFillBuilder` | added (`315d8f7`) | Reuse accepted decision/slippage validation, construct the existing `Fill` with caller-frozen exact liquidity role `taker` | TradFi Engine path |
| `ResolvedBarExecutionV2` or equivalent new version | add after amendment approval | Persist exact optional fill-liquidity role without changing legacy plan bytes | Engine/input materializer |
| new execution-input materializer/decoder version | add after amendment approval | Round-trip role-aware TradFi execution plans and durable rebuild identity | runtime/rebuild |
| `TradifiPreparationAuthorityEvent` | add after amendment approval | Bind profile request, strategy ref, eight parameter-to-target mappings, calendars/unit refs, SourceSnapshots, normalization hashes | preparation decoder |
| `BinanceUsdmTradifiBarRequestIntent` | add | Experiment/window/account/currency/seed/bundle/strategy/parameter refs and development grade | public preparation |
| `BinanceUsdmTradifiProviderInputs` | add | Caller-owned base `BuildArtifactManifest` and 10,000 USDT synthetic initial equity | public preparation |
| `BinanceUsdmTradifiPreparationFailureCode` | add | Structured preparation failures in contract precedence | caller/tests |
| `BinanceUsdmTradifiPreparationFailure` | add | Canonical failure identity and evidence subjects | caller/tests |
| `prepare_binance_usdm_tradifi_bar_backtest` | add | Deep public seam; returns prepared execution or structured failure, no network | Research provider adapter |
| `BinanceUsdmTradifiExecutionBundleRequest` | add | Frozen post-adjustment source revisions, coverage, calendars, corporate-action provenance, account evidence | bundle builder |
| `build_binance_usdm_tradifi_execution_bundle_v1` | add | Bind retained SourceSnapshot refs/checksums/gaps, project required streams, compute eight targets, publish one immutable MarketBundleRef | preparation/data owner |

### Existing symbols explicitly preserved

- `BinanceUsdmInstrumentModel`
- `BinanceUsdmProfileComposer`
- `FullFillBuilder`
- `prepare_cash_development_backtest`
- `prepare_model_bound_cash_development_backtest`
- `Fill.to_canonical_dict()`
- existing profile/component keys and hashes

## Exact value and identity closure

| Value/artifact | Exact type/schema | Identity/preimage | Consumer |
| --- | --- | --- | --- |
| Product model | `crypto.binance_usdm.tradifi.instrument-metadata.v1` | exact source revisions + stable lineage + model payload | TradFi composer |
| Market profile | `crypto.binance_usdm.tradifi.v1` | TradFi resolution + exact G10B-F/calendar/corporate sources | Backtest registry |
| Simulation profile | `bar.next_eligible_trade_event.tradifi.v1` | existing next-eligible execution model + role-aware fill builder + exact nonzero slippage/latency/liquidity/closeout/audit refs | Backtest registry |
| Account profile | `binance.usdm.standard-cross.v1` | exact archived account/commission/leverage/mode/capacity evidence | Backtest registry |
| Strategy definition | future exact `ArtifactRef` | immutable algorithm rules | preparation |
| Parameter set | eight exact future `ArtifactRef`s | one canonical parameter row each | one Trial each |
| Metric profile | `backtest_metric_profile@1` | `sha256:bced4dbef8bbf6e1ec9821ae3b68e8c6ce2bbed953f95fe1214c8e21676dbd6a` | Research/Validation |
| MarketBundle | `MarketBundleRef` | manifest hash over retained source artifacts/coverage | preparation/runtime |
| Build manifest | `BuildArtifactManifest` | caller base + deterministic registry enrichment | request/resolution |
| Synthetic equity | exact USDT `Money` | 10,000 USDT development deposit | initial ledger state |
| Target quantity | exact `Quantity` | floor(1,000 USDT / completed decision-time mark, active step) | Order intent |
| Fill event | existing `bar_open@1` event with REAL kind | first retained aggregate trade at/after eligible boundary; event/available time = trade time | existing next-eligible model |
| Fill liquidity | existing `Fill.liquidity` | exact string `taker` from new simulation profile/builder | final fee rules |

## Failure precedence

| Priority | Condition | Outcome |
| ---: | --- | --- |
| 1 | Intent/provider-input type/schema/ref/currency/grade/build/equity invalid | structured input failure |
| 2 | Bundle ref/manifest/hash/publication/reader/retention invalid | bundle failure |
| 3 | Lineage/listing/exact TradFi product/lifecycle invalid | instrument failure |
| 4 | Timeline before post-adjustment start, cross-band revision, nonempty initial state, or calendar coverage invalid | regime failure |
| 5 | Order-rule/quantity/price/notional evidence invalid | rule failure |
| 6 | Execution/mark/index/funding/availability incomplete or conflicting | market evidence failure |
| 7 | `Special` funding row present | `SPECIAL_FUNDING_UNSUPPORTED` |
| 8 | Margin/account/leverage/commission/fee-burn/capacity invalid | account/profile failure |
| 9 | Slippage calibration missing/outside applicability | simulation failure |
| 10 | Strategy/parameter ref, premium formula, schedule, or target exact-cover invalid | strategy failure |
| 11 | Profile/deferred-rule/registry composition invalid | profile failure |
| 12 | Request/materialization/round-trip/publication/storage invalid | publication failure |

No fallback, alias, forward fill, future-open sizing, fabricated terminal, zero metric, or partial success.

## Compatibility and immutable artifacts

- Existing ordinary Binance model/component/profile digests must remain byte-identical.
- Existing `PERPETUAL` inputs must not route through the TradFi model.
- Existing public preparation signatures/outputs remain unchanged.
- Existing `FullFillBuilder` continues emitting `liquidity="full"`; only the new builder emits `taker`.
- Existing `Fill` schema already carries optional liquidity; no schema migration.
- Existing execution-input bundle codecs remain unchanged; a separate new version persists `fill_liquidity_role` for TradFi cases and changes only new-case bytes/identity.
- No retry/downgrade between ordinary and TradFi profiles.
- Replay preserves prepared refs, semantic run ID, target stream, profile digest, and source capture time.

## Security and trust boundaries

- Network acquisition is outside preparation/runtime and stores no credentials in artifacts.
- Authenticated fee/account snapshots are caller-supplied encrypted acquisition outputs; only normalized non-secret evidence enters MarketBundle/profile composition.
- Current exchange endpoints cannot backfill history.
- Artifact/source hashes, exact refs, capture/effective/available times, and gap reports are mandatory.
- No live order, credential, broker, Shadow, or deployment authority.

## Forbidden paths backed by authority

| Authority | Forbidden path | Required route |
| --- | --- | --- |
| C1/B1 | Change `BinanceUsdmInstrumentModel` to accept both contract types | separate TradFi model/component |
| B3 | Use archived hourly kline open at nominal boundary as fill | first retained aggregate trade event at/after boundary |
| C1 | Size using future fill price | completed decision-time mark, accept fill-notional drift |
| B4 | Drop/merge/zero `Special` funding | structured unsupported failure |
| B5 | Infer fee from VIP/public table | exact archived account-symbol commission |
| B6 | Use current exchangeInfo rules historically | immutable effective rule bands |
| C1 | Compose pre/post split in one V1 run | post-adjustment single-regime timeline only |
| P1 | Import private Engine/composer modules from Platform | public preparation operation only |

## Sentinel and validation

| Authority | Cheapest red-capable check |
| --- | --- |
| B1 | Existing ordinary model component hash fixture is unchanged after new module import |
| C1 exact product | TradFi model accepts exact KORU fixture; rejects PERPETUAL and raw/unknown types |
| C1 post-adjustment | Timeline beginning before `2026-07-15T10:00Z` fails before profile composition |
| B3 causality | Nominal boundary without retained trade cannot fill; first later trade event can fill |
| C1 sizing | Quantity equals decision-mark calculation and differs safely from later realized fill notional |
| B5 fee role | TradFi fill carries `taker` and final fee rule accepts it; old builder still carries `full` |
| C1 slippage | Missing/zero/out-of-envelope calibration fails; exact nonzero calibration changes execution price/profile digest |
| C1 parameters | Two parameter-set refs produce distinct target-stream/request identities; `experiment_id` changes do not alter parameters |
| Build authority | Foreign/missing base BuildArtifactManifest fails before request publication |
| Replay | Same inputs publish no conflicting request and return identical prepared refs |

### Candidate validation

- focused new instrument/profile/preparation/bundle/execution-role suites;
- protected existing ordinary Binance profile/hash suites;
- execution-input round-trip and durable-rebuild suites;
- Research BT-PORT-01/02 compatibility;
- full Backtest suite (baseline `2438 passed` plus new tests);
- root Platform full suite (baseline `359 passed`);
- fresh recursive clone at exact revisions;
- Ruff/LSP/pi-lens/diff/lock/remote reachability guards.

## Independent acceptance

- one read-only Backtest reviewer checks causality, fees/funding, accounting, and profile identity;
- one separate standards/spec reviewer checks exact contract and no scope drift;
- protected ordinary Binance hashes and Integration v1-v5 fixtures remain unchanged;
- no staged files after validation;
- residual limitations recorded in the Backtest receipt.

## Open decision

None. `BT-TRADIFI-DISPATCH-01` is approved. The next sentinel is exact production dispatcher selection: a sealed TradFi derivative Case must select the derivative dispatcher while every ordinary/cash Case retains its existing dispatcher and hashes.
