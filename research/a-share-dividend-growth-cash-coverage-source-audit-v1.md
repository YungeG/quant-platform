# A-share dividend-growth and cash-coverage source audit v1

- **Strategy id:** `cn-a-share.dividend-growth-cash-coverage.v1`
- **Decision:** **`SOURCE-BLOCKED`** — no outcome metrics, backtest, or implementation are permitted.
- **Scope:** domestic ordinary A shares; no analyst forecasts; 2025 is the untouched holdout.

## Frozen rule (before outcomes)

On the first eligible session after each calendar month-end, use only information whose
`available_at` is no later than the prior session close.  An instrument is eligible only
when it is listed, liquid, non-ST and tradable at that cutoff, and when all of the
following are complete and point-in-time available:

1. its three latest completed fiscal-year **cash** dividends have strictly increasing
   per-share `cash_div` values;
2. for each of those fiscal years, annual `n_cashflow_act / (cash_div * base_share) >= 1.20`;
3. the associated dividend declaration, record, ex-date and payment lifecycle is complete
   without a correction/replacement conflict.

Hold every eligible name equally, rebalance monthly at the next eligible open, buy in
100-share lots, sell only T+1-available shares, and charge the resolved historical
commission, transfer fee and sell tax.  Missing data excludes neither a name nor a period:
it blocks the run.  The rule must be applied unchanged to the 2025 holdout.

`cash_div` and `base_share` above are the provider fields, not inferred adjusted prices or
vendor yield.  Their units and corporate-action treatment must be bound by the missing
source contract before calculation.

## Audit evidence

The repository has only a source-bounded fixed-singleton Tushare dividend capture:
`000001.SZ`, 96 rows, with coverage `2026-07-06` through `2026-07-30`
(`backtest/tools/acquisition/cn_a_share_tushare_g12k_fixed_instrument.py`; the G12K plan).
It cannot establish historical all-A-share dividend completeness, availability, or absence.
The financial-history sentinel is likewise a fixed issuer (`000651.SZ`) probe, not a
full-market statement authority (`implementation/plans/quality-bband-financial-history-source-sentinel-v3.md`).

The existing authority audits independently confirm that current Tushare dividend and
financial responses are `SOURCE_BOUNDED_ONLY`, historical ST/status is missing, and general
corporate-action closure is blocked (`research.md`,
`implementation/plans/quality-bband-universe-corporate-action-coverage-v1.md`, and
`research/quality-bband-data-authority-audit.md`).

## Exact missing data required to unblock

1. An immutable, complete historical ordinary-A-share dividend lifecycle revision set for
   every eligible instrument and the full research/2025-holdout interval: fiscal period,
   cash-per-share and base-share units, declaration/publication availability timestamp,
   record, ex, payment and listing dates, cancellation/correction/replacement lineage, and
   explicit empty-scope/terminal completeness declaration.
2. An immutable annual cash-flow-statement revision set for the same issuer-period scope:
   `n_cashflow_act`, report identity/type, announcement publication availability timestamp,
   revision/supersession lineage, units, and terminal completeness declaration.
3. A point-in-time catalog/listing, historical ST/risk-warning/suspension, and liquidity
   observation set with revisions and availability timestamps for the same intervals.
4. Purpose-separated daily open execution and valuation bars, historical calendar, and
   resolved historical A-share fee/tax/account-route authority sufficient for T+1 and
   100-share-lot execution.
5. A public multi-instrument A-share preparation operation binding those immutable inputs
   to the frozen rule and a 2025 holdout reservation.

Until all five are accepted, dividend growth cannot be reconstructed from ex-post annual
values, a zero dividend query cannot mean no dividend, and no performance metric or verdict
other than `SOURCE-BLOCKED` is valid.

## Verdict

**`SOURCE-BLOCKED`**.  No strategy code, backtest artifact, metrics, or 2025 result was
created; doing so would replace announcement availability and lifecycle authority with
ex-post or incomplete data.
