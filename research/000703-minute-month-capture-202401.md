# 000703.SZ January 2024 minute capture — bounded development chunk

> Archive note (2026-09-22): Preserved research/probe record, not a fresh authority or readiness assessment. “Current/now” and reported passes refer to the original task; external sources, entitlements, retained artifacts and historical availability were not revalidated for this archival commit. Referenced `backtest/evidence/` files are local and are not published here. No new sample consumption, capture, Backtest, qualification or trading authorization follows.

**Scope:** first discovery-month source chunk only. This is source-bounded development evidence, not a full discovery range, public MarketBundle, Backtest input, PnL result, or decision/live/deployment artifact.

## Inputs

- Frozen calendar: `backtest/evidence/tushare-calendar-szse-development-month-202401/`
  - target month: January 2024
  - 31 target calendar days, 22 SZSE open sessions
  - prior December 2023 calendar month retained as the `pretrade_date` validation anchor
- Output: `backtest/evidence/tushare-minute-000703-development-month-202401/`
  - one independently frozen `stk_mins` response and receipt per open session
  - `month-capture-summary.json` links each target session’s response hash and snapshot ID

## Results

- 22/22 calendar-open sessions captured successfully.
- Every capture passed the bounded acquisition gate: 49 raw labels, 48 regular closed bars, response hash matched receipt, and no credential echo.
- Offline replay over all retained sessions succeeded: **1,056** chronological normalized bars and **1,056** private `bar_close@1` events.
- The provider’s reverse chronological response order was accepted only after strict label-set validation and canonical chronological normalization.

## Boundaries

The retained calendar/minute bytes do not establish historical listing/risk status, order rules, corporate-action closure, broker fee pass-through, a public 000703 profile, an instrument catalog, or a public preparation route. No local immutable Bundle was published because no approved 000703 coverage/catalog/profile authority exists yet.

## Next stop condition

Do not capture further months merely to accumulate data. First establish the remaining 000703 authority matrix and a source-bound monthly Bundle/catalog contract. Any source schema drift, nonterminal page, missing/duplicate/off-grid minute session, or unclassified calendar-open session blocks that month.
