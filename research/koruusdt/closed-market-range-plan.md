# KORUUSDT closed-market range research plan

## 1. Mode and market

- **Mode:** Plan
- **Market:** Binance USDⓈ-M `KORUUSDT`
- **Live contract identity:** `TRADIFI_PERPETUAL`, USDT margined/settled
- **Requested strategy family:** closed-cash-market range mean reversion
- **Requested result grade:** `development` only
- **Promotion/Shadow/Live:** excluded

### Falsifiable hypothesis

After both the Korean cash market and the US cash market have closed, a low-width initial KORUUSDT mark-price range contains enough short-horizon mean reversion that a symmetric range-fade strategy has **nonnegative** holdout `simple_period_return` after accepted fees, funding, slippage, and liquidation treatment, with at least 8 completed holdout trades.

Scientific outcomes are separated from operational failures:

1. **Discovery no-selection:** no completed discovery trial satisfies the predeclared selection filters; no Candidate is published.
2. **Rejected:** a valid completed holdout with at least 8 trades has `simple_period_return < 0`.
3. **Supported:** a valid completed holdout with at least 8 trades has `simple_period_return >= 0`, matching the current Validation `gte` capability.
4. **Inconclusive:** insufficient trades, or an accepted `BLOCKED`/`CANCELLED` disposition.
5. **No report / provider failure:** failed execution, missing authority, tamper, retention, storage, or provider failure. These do not count as scientific rejection.

The earlier descriptive check is not the acceptance criterion. It only showed lower closed-market volatility; it did not prove a profitable fixed range.

## 2. Capability decision

**Decision: plan-only; not executable through the accepted Platform today.**

Exact blockers:

1. The accepted Binance USD-M instrument metadata model permits only exact `contract_type == "PERPETUAL"`; live KORUUSDT metadata is `TRADIFI_PERPETUAL` and therefore resolves to `UNSUPPORTED_CONTRACT_TYPE`.
2. The public `crypto_quant_backtest` root exposes cash-development preparation operations, but no accepted public preparation operation for a Binance USD-M TradFi perpetual closed-market Bar strategy.
3. The pinned research snapshot is not an accepted Backtest `MarketBundle`. Its external Yahoo factors are explicitly secondary/non-decision-grade.
4. No accepted historical KORUUSDT profile currently binds TradFi contract-size adjustments, cash-market calendars, fees, margin tiers, capacity, liquidation, and slippage for this strategy.

The missing seam is an accepted **public Binance USD-M `TRADIFI_PERPETUAL` Bar preparation operation and compatible profile set**. Exact scenario, template, calendar, fee, and slippage refs cannot be constructed until that contract publishes them; therefore this document is a precommitted design, not yet an authoritative `ExperimentSpec`. Private composers, engines, repositories, or a custom profit-and-loss simulator must not be used as a workaround.

## 3. Research design

### Frozen exploratory source

- **Dataset revision:** `koruusdt-factor-dataset-v1:sha256:066c775e60ba402b631b406fd8138da200d7e30a136e0efb7c2c13b196680d64`
- **Manifest:** `research/koruusdt/data/manifest.json`
- **Raw/aligned snapshot:** `research/koruusdt/data/`
- **Corporate-action boundary:** discovery begins at `2026-07-15T10:00:00.000000Z`, after the documented adjustment/resumption; no authoritative Trial may use pre-adjustment or split-window bars

This revision is suitable for planning and exploratory comparison only. Before execution, an accepted provider must publish a retained immutable MarketBundle covering the same semantics.

### Half-open slices

| Role | Interval |
| --- | --- |
| Discovery/selection | `[2026-07-15T10:00:00.000000Z, 2026-08-24T11:00:00.000000Z)` |
| Frozen future holdout | `[2026-08-24T11:00:00.000000Z, 2026-10-05T00:00:00.000000Z)` |

The existing descriptive check observed the full pinned snapshot, so no interval inside that snapshot can honestly serve as an untouched holdout. The future holdout above is precommitted now and must be published with `role = HOLDOUT` and `selection_observed = false`. Its observations must not be used for feature work, parameter changes, manual selection, or date revision. There is no adaptive extension or result-driven date change.

### Required immutable data semantics

| Purpose | Required source |
| --- | --- |
| Range/signal | completed KORUUSDT 1-hour mark-price bars |
| Entry/exit fill reference | first retained KORUUSDT aggregate-trade event at or after the next eligible hourly boundary; event time and availability equal retained trade time |
| Valuation, margin, liquidation | purpose-specific historical mark observations |
| Basis guard | `log(mark_close / index_close)` from exact completed hourly mark and index observations available before decision time |
| Funding | Funding Rate History publication, exact availability time, settlement slot, and associated funding mark |
| Closed-market schedule | exact versioned `XKRX` regular-session calendar (09:00-15:30 Asia/Seoul) and `ARCX` KORU core-session calendar (09:30-16:00 America/New_York), including holidays and DST |
| Corporate actions | versioned 20-for-1 contract-size adjustment and halt interval |
| Fees | historical accepted taker-fee schedule; no rebate assumption |
| Slippage | accepted versioned Bar slippage model with applicability evidence for the declared size |

No signal may fill on its source Bar. External market closes are invisible until their exact `available_at` time.

### Strategy rule

For each continuous interval in which both accepted cash-market calendars are closed:

1. Require at least `formation_hours + 1` complete eligible hours.
2. Observe the first `formation_hours` completed mark bars.
3. Set `range_high`, `range_low`, `midpoint`, and `range_width` from those bars.
4. Skip the interval when:
   - `range_width / midpoint` exceeds `max_formation_range`;
   - any required mark/index/funding/calendar observation is missing or not yet available;
   - absolute premium exceeds the fixed 2% guard;
   - the interval overlaps a split, halt, maintenance, or unsupported state.
5. After formation, permit at most one trade in the interval:
   - long when the last completed mark close is in the bottom 25% of the range;
   - short when it is in the top 25% of the range;
   - decide only after that Bar completes;
   - fill only at the first retained aggregate-trade event at or after the next eligible hourly boundary.
6. Evaluate exits only after a Bar completes; no intrabar stop/limit or OHLC-path inference is permitted:
   - for a long, decide to exit when the completed mark close is at/above the midpoint or at/below `range_low - range_width`;
   - for a short, decide to exit when the completed mark close is at/below the midpoint or at/above `range_high + range_width`;
   - also decide to exit after `max_hold_hours`, or when the next Bar would overlap either cash-market session.
7. Every exit fills only at the first retained aggregate-trade event at or after the next eligible hourly boundary. The boundary exit must be scheduled early enough that this fill occurs before either cash market opens. Never carry a position into an open cash-market session.

### Explicit parameter combinations

Fixed values in every combination:

```text
entry_zone_fraction = 0.25
stop_range_multiple = 1
max_abs_premium = 0.02
max_trades_per_closed_interval = 1
position_notional_usdt = 1000
```

Every `ParameterCombination` value is encoded as a canonical string (for example, `("formation_hours", "2")` and `("max_formation_range", "0.03")`). Finite combinations, canonically sorted by `(formation_hours, max_formation_range, max_hold_hours)`:

| # | formation_hours | max_formation_range | max_hold_hours |
| ---: | ---: | ---: | ---: |
| 1 | 2 | 0.03 | 2 |
| 2 | 2 | 0.03 | 4 |
| 3 | 2 | 0.05 | 2 |
| 4 | 2 | 0.05 | 4 |
| 5 | 3 | 0.03 | 2 |
| 6 | 3 | 0.03 | 4 |
| 7 | 3 | 0.05 | 2 |
| 8 | 3 | 0.05 | 4 |

There are no ranges to expand during execution and no adaptive parameter search.

### Remaining Experiment axes

- **Seeds:** `(0,)`; the strategy is deterministic and no other seed is permitted.
- **Scenario ref:** unavailable until a contract publishes an exact ref for one `koruusdt_both_cash_markets_closed_v1` scenario binding the `XKRX`/`ARCX` calendar revisions, split exclusion, completed-close basis formula, and no-carry boundary. This unavailable exact ref is an execution blocker.
- **Strategy ref:** unavailable until an exact `koruusdt_closed_market_range_v1` strategy-definition ref is published. It must bind every rule above, including close-triggered/next-event exits.
- **Strategy parameter-set refs:** eight unavailable exact artifact refs, one for each canonical row in the frozen parameter table. Every Trial supplies the common strategy ref plus exactly one parameter-set ref; Backtest must not decode parameters from `experiment_id`.
- **Backtest template ref:** unavailable until the missing public preparation contract publishes an exact Binance USD-M TradFi hourly first-retained-trade-event template ref and simulation profile. No intrabar execution capability is requested.
- **Metric profile ref:** exact existing canonical ref `{"type":"artifact_ref","artifact_type":"backtest_metric_profile","schema_version":1,"content_hash":"sha256:bced4dbef8bbf6e1ec9821ae3b68e8c6ce2bbed953f95fe1214c8e21676dbd6a"}` (`simple_period_return.fill_count.v1`).
- **Fee profile ref:** unavailable exact historical KORUUSDT taker-fee schedule ref; no rebate or BNB discount is assumed. This is an execution blocker.
- **Slippage profile refs:** public `DeterministicBpsSlippageModel` plus an unavailable exact `SlippageCalibrationRef` applicable to KORUUSDT, 1-hour decisions, first-retained-trade-event fills, and 1,000 USDT target notional. The calibration ref is an execution blocker; zero slippage is forbidden.
- **Budget:** `max_trials = 8`; one data slice, one seed, one scenario, one metric profile. Research may create exactly 8 Trial tasks and 8 Analysis tasks.
- **Account/sizing identity to bind in the future profile:** one-way USDT account, no multi-assets or hedge mode, 10,000 USDT synthetic initial equity, fixed 1,000 USDT target notional, effective leverage 1x. Quantity is determined causally from the completed decision-time mark close and rounded **down** to the historical quantity step; realized fill notional may drift at the later retained-trade event, and a result below historical minimum quantity/notional produces no order. Synthetic equity is distinct from Binance account order/exposure-capacity evidence. These are research bounds, not live instructions.

### Predeclared SelectionPolicy

```text
eligible_trial_statuses = (COMPLETED,)
accepted_backtest_grades = (development,)
hard_filters = (
  trade_count >= 8,
  simple_period_return > 0,
)
ordering = (
  simple_period_return descending,
  trade_count descending,
)
max_selections = 1
tie_break = trial_declaration_ref_ascending
```

Only verified completed analyses in the exact closed Experiment manifest are eligible. No manual winner or terminal-to-zero conversion is allowed.

### Frozen ValidationPolicy

```text
accepted_backtest_grades = (development,)
accepted_metric_profile_refs = ({type: artifact_ref, artifact_type: backtest_metric_profile, schema_version: 1, content_hash: sha256:bced4dbef8bbf6e1ec9821ae3b68e8c6ce2bbed953f95fe1214c8e21676dbd6a},)
holdout = the precommitted half-open holdout above
OosRule.metric_profile_ref = the same exact canonical ref
OosRule.metric_key = simple_period_return
OosRule.unit = fraction
OosRule.operator = gte
OosRule.threshold = 0
OosRule.minimum_trade_count = 8
```

Validation must reserve the holdout before read/execution and must publish the exact `supported | rejected | inconclusive` outcome or an explicit no-report failure.

## 4. Validation result

No Platform Experiment, Candidate, Backtest publication, Analysis, or ValidationReport exists for this plan. The descriptive report at `research/koruusdt/closed-market-range-check.md` is advisory evidence only and cannot be promoted or treated as a Validation result.

## 5. Limitations and blockers

- The admissible post-adjustment discovery interval contains only about forty days of Binance history and few independent cash-market regimes; the precommitted future holdout has not yet been captured.
- The sample contains one major split/contract adjustment.
- External factor inputs are secondary Yahoo data; they cannot establish decision grade.
- Minute/order-book data and an accepted slippage calibration are absent.
- TradFi reference-price mode, holidays, maintenance, margin tiers, liquidation, and historical rule revisions require accepted authority.
- Large closed-market counterexamples already exist; a closed interval is a lower-volatility regime, not a guaranteed fixed range.
- Even a future `supported` development ValidationReport would not authorize Shadow, Live, credentials, orders, or deployment.

## 6. Next safe action

Do not run a Platform backtest yet. Define and approve the missing Backtest contract for exact `TRADIFI_PERPETUAL` instrument/profile support and one public preparation operation. That contract must first prove historical instrument metadata, calendars, split adjustment, mark/index/funding semantics, fees, account/margin/liquidation, and slippage applicability. Independently preserve—but do not inspect for strategy decisions—the future holdout interval as it accrues. Once the preparation seam is accepted and the holdout closes, materialize the frozen slices and eight combinations above without changing dates, parameters, filters, or holdout.
