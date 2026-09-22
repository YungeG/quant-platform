# 000703.SZ authority-matrix smoke — v1

> Archive note (2026-09-22): Preserved research/probe record, not a fresh authority or readiness assessment. “Current/now” and reported passes refer to the original task; external sources, entitlements, retained artifacts and historical availability were not revalidated for this archival commit. Referenced `backtest/evidence/` files are local and are not published here. No new sample consumption, capture, Backtest, qualification or trading authorization follows.

**Date:** 2026-09-02\
**Scope:** bounded proxy capability probes plus two retained one-day development smoke captures. This is an upstream authority inventory, not a public profile, complete coverage declaration, Backtest preparation, or strategy result.

## Retained smoke captures

| Authority | Retained path | Result |
| --- | --- | --- |
| SZSE calendar, 2024-01-02 | `backtest/evidence/tushare-calendar-szse-development-smoke-20240102/` | `trade_cal` returned one exact row with `is_open=true`; receipt/snapshot written without credential material. |
| 000703 5-minute price session, 2024-01-02 | `backtest/evidence/tushare-minute-000703-development-smoke-20240102/` | `stk_mins` returned 49 raw labels / 48 regular closed bars; raw response was descending and is now canonically normalized to chronological order. |

Tushare documents [`trade_cal`](https://tushare.pro/document/2?doc_id=26) as exchange calendar data and [`stock_basic`](https://tushare.pro/document/2?doc_id=25) as current basic/listing information. Neither documentation establishes historical-as-of revision closure.

## Bounded proxy capability probes

| API | Request scope | Result | Authority use / limitation |
| --- | --- | --- | --- |
| `trade_cal` | SZSE, 2024-01-02 | code `0`, exact four requested fields, one row, open | Usable source candidate for a monthly calendar worklist after a dedicated proxy source contract. |
| `stock_basic` | 000703.SZ | code `0`, requested fields, one row | Current/basic identity candidate only; does not close historical status revisions. |
| `namechange` | 000703.SZ | code `0`, requested fields, seven rows | Name/history input candidate; needs point-in-time and terminal-revision treatment. |
| `suspend_d` | 000703.SZ, 2024-01-02, `S` | code `0`, requested fields, zero rows | A one-day empty response is not a historical completeness or suspension-absence authority. |
| `stk_limit` | 000703.SZ, 2024-01-02 | code `0`, one row, provider fields were `trade_date,ts_code,up_limit,down_limit` | Candidate daily limit source; a future adapter must bind this observed field order and historical coverage. |
| `dividend` | 000703.SZ | code `0`, 87 rows, **requested field list not returned exactly** | Not ingestible under the current strict contract; requires a documented response-schema/terminal-pagination investigation before use. |

All probes used the approved proxy and confirmed no credential echo. No response payloads beyond the two retained smoke captures were persisted.

## Current authority status

The following remain unresolved for a public `000703.SZ` development profile and must not be inferred from the probes:

1. exact calendar coverage for every session in discovery/OOS;
2. historical listing/board/risk/suspension state with point-in-time revision closure;
3. historical order-rule, lot, tick, and limit authority across the windows;
4. corporate-action lifecycle/register and explicit-empty authority;
5. fee/stamp books aligned to the same coverage and a public prepared-execution route;
6. month-level source pagination/terminal-envelope contracts;
7. public `000703` profile/preparation composition.

## Next bounded step

Design and test a proxy-backed monthly `trade_cal` capture contract before any month-scale request. Use the captured calendar as the only minute-session worklist. Stop on nonterminal pagination, source schema drift, duplicate/gapped calendar dates, or any unclassified open session.
