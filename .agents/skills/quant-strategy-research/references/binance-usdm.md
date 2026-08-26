# Binance USD-M Research

Read this reference when the requested market is Binance USD-M perpetual futures or another crypto perpetual study intended to use the Binance USD-M Backtest profile.

## Scope

Appropriate research includes fixed-instrument or portfolio strategies involving:

- trend, momentum, mean reversion, carry, and funding effects;
- target exposure or position changes at declared decision times;
- model-bound signals when the accepted model seam is sufficient;
- development or decision-grade analysis only when the requested data/profile/provider capabilities actually qualify.

Market making, queue position, order-book replay, partial-fill calibration, or other microstructure claims require an accepted Microstructure Replay capability. Do not route them through the Bar Engine.

## Required authorities

Inspect the accepted Backtest public root and source evidence before execution. A credible Binance USD-M run may require:

- immutable instrument metadata and contract scales;
- aggregate trades or another accepted execution-reference stream;
- purpose-specific Mark observations for valuation, margin, liquidation, and funding where applicable;
- Funding Rate History publication, settlement slot, eligibility instant, and associated Funding Mark;
- historical account mode, leverage, capacity, fee schedule, and margin-tier evidence;
- immutable listing/availability coverage and MarketBundle retention;
- a registered compatible market-semantics, simulation, and execution-account profile set;
- an accepted concrete public preparation operation for the requested strategy.

Primary source and profile documents live under `backtest/docs/research/`, especially the `binance-usdm-*` files. Current status and accepted revisions live in `backtest/docs/implementation/` and `implementation/roadmap.md`.

## Research preflight

Before declaring Execute mode, verify:

1. Instrument, venue, quote/settlement currency, contract type, and requested interval are explicit.
2. Discovery/training and holdout intervals use canonical UTC and account for a 24/7 market rather than business-day assumptions.
3. The strategy states which price purpose each feature, signal, fill reference, valuation, margin check, liquidation audit, and funding calculation uses.
4. Funding knowledge time is not replaced by economic time; a rate or revision is invisible before its accepted availability instant.
5. Fees distinguish maker/taker when the execution profile can establish it. Unknown rebates, fee burn, multi-assets mode, hedge mode, or isolated margin must not silently map to the supported account profile.
6. Leverage, margin tier, account capacity, and liquidation applicability cover the requested period and position size.
7. Listing, delisting, source outage, revision, and liquidity regime limitations are explicit. Current exchange metadata cannot backfill historical authority.
8. Signal decisions cannot fill on their source Bar. Decision-grade Bar execution must use the accepted next-eligible-Bar-open convention.
9. Slippage has a versioned model and applicability/calibration evidence for the requested size and market state; implicit zero slippage is invalid.
10. The public preparation operation exists. Otherwise return plan-only with the missing seam.

## Common fail-closed conditions

Stop rather than approximate when decision-grade is requested and any of these applies:

- Funding publication, settlement, mark, or cutoff-position evidence is missing or ambiguous.
- Price-purpose streams are substituted or forward-filled across purposes.
- Historical account, leverage, fee, margin-tier, instrument, or listing coverage is incomplete.
- Current API responses are used as historical rules.
- The strategy or Backtest reads a live exchange endpoint during execution.
- Bar high/low/close/volume is used to decide a next-open fill.
- Required liquidation evidence is ambiguous.
- A strategy requests microstructure behavior from the Bar Engine.

Development-grade approximations are permitted only when Backtest accepts them and records the exact limitation. The skill must not synthesize a higher grade.

## Plan output additions

For Binance USD-M, include:

- instrument and contract identity;
- data streams by semantic purpose;
- funding and account-profile requirements;
- leverage/capacity and liquidation assumptions;
- fee and slippage profile identities;
- 24/7 training/discovery and holdout intervals;
- provider/profile/preparation capability decision;
- development/decision-grade blockers.
