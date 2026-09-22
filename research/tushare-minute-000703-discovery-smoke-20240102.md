# 000703.SZ Tushare historical-minute discovery smoke — 2024-01-02

> Archive note (2026-09-22): Preserved research/probe record, not a fresh authority or readiness assessment. “Current/now” and reported passes refer to the original task; external sources, entitlements, retained artifacts and historical availability were not revalidated for this archival commit. Referenced `backtest/evidence/` files are local and are not published here. No new sample consumption, capture, Backtest, qualification or trading authorization follows.

**Purpose:** one-session, development-only source-bound smoke for the planned discovery period. This is not full-period acquisition, a published production Bundle, a public Backtest preparation, or a strategy result.

## Capture

- Retained output: `backtest/evidence/tushare-minute-000703-development-smoke-20240102/`
- API: `stk_mins`
- Request: `000703.SZ`, `5min`, `2024-01-02 09:30:00` through `15:00:00`
- Receipt outcome: source-bounded and development-only; 49 source rows; 48 strategy-eligible closed-bar labels; raw response SHA-256 matched the receipt.
- Credential material was not persisted or echoed.

## Source-order finding and repair

The real provider response was strictly descending by `trade_time` (`15:00` to `09:30`), while the source contract requires the exact label set rather than a provider ordering guarantee. The minute normalizer now validates the complete 49-label set and canonicalizes valid rows into chronological order before excluding the raw-only `09:30` anchor.

A replay from the real retained snapshot succeeded after the repair:

- 48 normalized regular bars, `09:35` through `15:00`
- 48 private `bar_close@1` events
- each close event has `event_time == available_time ==` its 5-minute interval end
- bundle validation succeeded for an event-inclusive half-open smoke range ending one nanosecond after the final close event; no durable Bundle publication was performed.

## Boundaries

This capture establishes only that one historical session can be acquired, frozen, normalized, and projected as development-only closed bars. It does **not** establish gap-free calendar coverage, historical listing/board/risk status, order-rule/price-limit coverage, corporate-action closure, broker pass-through, a public 000703 preparation operation, or decision/live/deployment authority.
