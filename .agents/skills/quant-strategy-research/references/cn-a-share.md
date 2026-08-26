# A-Share Research

Read this reference when the requested market is mainland China A-share equities, including fixed-instrument timing studies and later portfolio or cross-sectional strategies supported by an accepted A-share provider/profile.

## Scope

Appropriate research includes:

- fixed-instrument daily or minute target strategies;
- momentum, trend, mean-reversion, rotation, or factor studies when point-in-time universe and required fundamentals are available;
- development or decision-grade runs only when the requested instrument scope, rules, data, and provider capabilities qualify.

Do not claim multi-asset factor, index-constituent, intraday, auction, queue, or corporate-action correctness merely because a fixed-singleton or daily development route exists. Match the requested study to the exact accepted capability.

## Required authorities

Inspect the accepted Backtest public root, A-share profile composition, and source-bounded evidence before execution. A credible A-share run may require:

- immutable trading calendar and session model;
- point-in-time listing, delisting, suspension, identity, and universe membership revisions;
- daily/minute price data with event time and availability semantics;
- quantity lattice, board lot, order-rule, price-limit, and settlement/T+1 authorities;
- route- and product-specific commission, minimum commission, tax, and fee evidence;
- corporate-action announcement, entitlement, effective, and payment lifecycle where relevant;
- immutable MarketBundle retention and registered compatible market-semantics, simulation, and execution-account profiles;
- an accepted concrete public preparation operation for the requested strategy and instrument scope.

Primary source and profile documents live under `backtest/docs/research/`, especially the `cn-a-share-*`, `g12h-*`, `g12i-*`, `g12k-*`, `g12l-*`, and `g12m-tushare-*` files. Current status and accepted revisions live in `backtest/docs/implementation/` and `implementation/roadmap.md`.

## Research preflight

Before declaring Execute mode, verify:

1. Exchange, board/product class, instrument scope, bar frequency, trading dates, and requested access route are explicit.
2. Discovery/training and holdout intervals use canonical instants and valid trading-calendar/session semantics.
3. A point-in-time instrument or index universe exists. Current constituents cannot be projected backward, and future listings cannot appear early.
4. Suspensions, ST or other status changes, delistings, missing sessions, and source outages are classified rather than forward-filled.
5. T+1 and availability apply to the actual account/instrument semantics. The strategy cannot sell quantities that are not available.
6. Quantity conversion respects the accepted lot/step lattice without rounding up approved exposure.
7. Decision-grade Bar orders cannot fill on the signal Bar. The accepted next-eligible-Bar-open model uses a real eligible open and no future high/low/close/volume.
8. An upper-limit open buy and lower-limit open sell follow the accepted conservative liquidity-block convention; do not rewrite that result as a market-rule rejection.
9. Commission, minimum commission, transfer/route charges, and sell-side tax use the exact historical route/product authority. Current fees cannot backfill historical gaps.
10. Corporate actions use point-in-time lifecycle evidence and historical entitlement. Ex-post adjusted prices are not execution evidence.
11. The requested result grade matches rule, universe, availability, price, fee, and corporate-action coverage.
12. The public preparation operation exists for the requested strategy and scope. Otherwise return plan-only with the missing seam.

## Common fail-closed conditions

Stop rather than approximate when decision-grade is requested and any of these applies:

- Historical listing, suspension, universe, rule, fee, tax, settlement, or corporate-action evidence is missing, overlapping, or ambiguous.
- Current rules, current constituent lists, or current status are used for historical periods.
- Ex-post adjusted price series is used to create fills.
- A signal fills on the same Bar or a synthetic/forward-filled Bar.
- T+1, lot size, minimum commission, or price-limit liquidity behavior is omitted.
- A fixed-singleton route is represented as multi-asset or full-market capability.
- The strategy or Backtest reads a live provider API during execution.

Development-grade approximations are permitted only when Backtest accepts them and records the exact limitation. The skill must not synthesize a higher grade.

## Plan output additions

For A-share studies, include:

- exchange, board/product class, instrument or point-in-time universe;
- trading calendar/session and bar definition;
- listing/status/universe revision sources;
- settlement/T+1 and quantity-lattice requirements;
- route/product fee and tax authorities;
- price-limit, suspension, and corporate-action handling;
- provider/profile/preparation capability decision;
- development/decision-grade blockers.
