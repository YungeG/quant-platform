# A-share stock/bond/gold prospective validation design

> Archive note (2026-09-22): This is the preserved deferred plan, not a new experiment or capture approval. “Current”, capability and no-consumption statements below refer to the original planning stage; this archival pass has not re-audited the sample ledger, source evidence or public ETF route. The original candidate, intervals and gates remain unchanged. Historical dataset paths are locations recorded at that stage; consult the [data inventory](research-data-inventory.md) and [dependency alignment](../implementation/dependency-alignment-20260921.md) before a separately authorized continuation.

## Mode and market

- Mode: **Deferred Plan**
- Market: mainland China exchange-traded ETFs
- Status: **DEFERRED / OUT OF CURRENT HISTORICAL-BACKTEST SCOPE**
- Candidate: fixed 30% equity / 50% government-bond / 20% gold allocation with conservative liquidation-then-purchase execution

The current goal is the historical 2017-01-03—2026-08-25 backtest. Its result has already been observed and remains development evidence, not a virgin holdout. No one-year waiting period or prospective capture is required for the current goal.

## Hypothesis and rejection

**Hypothesis:** a quarterly 30/50/20 allocation to `510300.SH`, `511010.SH`, and `518880.SH`, using a zero-target liquidation at the next eligible open followed by final-target purchases at the subsequent eligible open with 8bp one-way cost, produces a nonnegative prospective simple period return over one full year.

Formal Validation-v1 rule:

- metric: `simple_period_return`
- unit: `fraction`
- operator: `gte`
- threshold: `0`
- minimum trade count: `4`

A negative simple period return rejects the candidate. Fewer than four verified trades, missing metrics, or non-completed Backtest evidence is inconclusive rather than zero.

Sharpe, maximum drawdown, and benchmark-relative improvement remain advisory because the accepted Validation-v1 contract supports only `simple_period_return >= threshold` plus minimum trade count.

## Frozen candidate

- Strategy identity required from Backtest: `cn_etf_fixed_30_50_20_quarterly_liquidate_then_buy_v1`
- Assets:
  - equity: `510300.SH`
  - bond: `511010.SH`
  - gold: `518880.SH`
- Target weights: `0.30 / 0.50 / 0.20`
- Signal interval: every 63 common trading sessions
- Liquidation decision: complete zero target at the signal-session close
- Liquidation execution: next eligible session open
- Final allocation decision: complete `0.30 / 0.50 / 0.20` target after that session closes
- Purchase execution: following eligible session open
- If liquidation is incomplete, purchases fail/block through accepted cash/position availability; no borrowing, optimistic proceeds, or silent resizing
- Initial capital: CNY 400,000
- Quantity: 100-share ETF board lots for execution; no rounding up
- Cost: 8bp per traded side
- Leverage: none
- Shorting: none
- Forecasting or parameter search: none
- Seed: `0` (deterministic strategy; retained only as an explicit Research axis)
- Scenario ref required from Backtest: `cn_etf_two_session_rebalance_cost_8bp_v1`
- Parameter combinations: exactly one

Benchmarks `all_equity` and `60_40` are advisory comparisons only and do not enter candidate selection.

## Data slices

### Frozen observed development slice

- Dataset: `overall/a-share-multi-asset-etf-daily.csv`
- Dataset revision: `sha256:a6b128c8a049e60e48d82c242c1a94502a5dbdefd2346bc870449bb18fbcafdd`
- Interval: `[2015-12-14, 2026-08-26)`
- Dynamic-weight warmup is irrelevant to the fixed candidate but retained for historical replay compatibility.
- This slice is already observed and cannot be used as the prospective holdout.

### Precommitted prospective holdout

- Interval: `[2026-09-01, 2027-09-01)`
- Role: `holdout`
- `selection_observed = false`
- Required datasets: point-in-time `fund_daily`, `fund_adj`, trading calendar/session eligibility, listing/status, ETF quantity rules, and applicable fee evidence for all three instruments.
- Future MarketBundle and dataset revision: not yet available; must be frozen before the first OOS read or Backtest call.

## Experiment and selection

- Trial universe: one candidate × one seed × one scenario = **one trial**
- SelectionPolicy: the sole predeclared candidate may be selected only after a formal development Backtest of this exact two-session identity is verified completed; the historical exploratory same-open result does not satisfy this condition. There is no ranking or manual winner choice.
- Economic run budget: one development replay when the public seam exists, followed by one independently reserved OOS run.
- Replay: one semantic replay without a second economic execution when practical.

## Capability decision

The local CSV and exploratory simulator are sufficient for a research smoke test, but not for formal Platform evidence. The formal two-session execution is a distinct prospective candidate and must not inherit the historical same-open result.

Missing accepted public seam:

```text
prepare_cn_etf_portfolio_development_backtest(...)
```

The existing public preparation operations are generic cash-development operations and do not by themselves establish A-share multi-instrument T+1, ETF quantity, historical fee, status, or portfolio data authority. The accepted Tushare route is fixed-singleton and zero-target/no-trade only.

Therefore this design is **plan-only** until Backtest publishes:

1. an immutable three-ETF MarketBundle covering the requested interval;
2. an accepted A-share ETF portfolio Profile/Build authority;
3. the concrete public preparation operation above;
4. an accepted metric profile exposing `simple_period_return` and `trade_count`.

## Validation result

No formal ValidationReport exists. The prospective interval has begun, but no holdout data has been read, captured, or consumed by Research/Validation.

## Limitations

- ETF prices include fund fees, tracking error, premiums, and discounts.
- `511010.SH` is a duration-bearing bond ETF, not cash.
- A one-year holdout has limited power for long-horizon risk claims.
- Formal Validation-v1 cannot encode the historical drawdown and Sharpe gates.
- This plan grants no Shadow, Live, credential, order, or deployment authority.
