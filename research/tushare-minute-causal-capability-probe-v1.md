# Tushare minute causal-capability probe — 000703.SZ v1

> Archive note (2026-09-22): Preserved research/probe record, not a fresh authority or readiness assessment. “Current/now” and reported passes refer to the original task; external sources, entitlements, retained artifacts and historical availability were not revalidated for this archival commit. Referenced `backtest/evidence/` files are local and are not published here. No new sample consumption, capture, Backtest, qualification or trading authorization follows.

**Probe date:** 2026-09-02\
**Scope:** representative, no-persistence capability checks only. No full historical acquisition, Bundle publication, strategy implementation, or backtest was run.

## Result

**Tushare does not resolve the existing causal-next-bar-open blocker for the 2024–2026 historical study.**

- Historical `stk_mins` is available to the current proxy credential at both 5-minute and 1-minute frequency, but its archived OHLC rows do not document when the row’s open became observable. A historical `open` must not be projected as a `bar_open@1` event at the label/bucket start.
- `rt_min` is Tushare’s real-time minute interface, but the current proxy credential was denied (`provider_code=40203`) in the bounded probe. Its published schema accepts only symbol/frequency, not historical start/end dates; even with permission it cannot backfill the discovery/OOS interval.

## Official interfaces

| Interface | Officially documented scope | Relevant fields | Causal conclusion |
| --- | --- | --- | --- |
| `stk_mins` | A-share historical minute data; 1/5/15/30/60 minute; up to 8,000 rows/request; more than ten years of history. | `trade_time`, `open`, `close`, `high`, `low`, `vol`, `amount` | Historical bar facts only. The page does not define label boundary, timezone, row availability, revision closure, or that `open` was available at bar start. |
| `rt_min` | Real-time A-share minute data; 1–60 minute; up to 1,000 rows/request. | `time`, `open`, `close`, `high`, `low`, `vol`, `amount` | Potentially useful only for a future, timestamped capture program after entitlement. The documented input has no historical date range and cannot repair past availability evidence. |

Sources:

- Tushare, [股票历史分钟行情 (`stk_mins`)](https://tushare.pro/document/2?doc_id=370)
- Tushare, [A股实时分钟 (`rt_min`)](https://tushare.pro/document/2?doc_id=374)

## Bounded probes

| API | Request | Result | Interpretation |
| --- | --- | --- | --- |
| `stk_mins` | `000703.SZ`, `1min`, `[2026-08-31 09:30:00, 2026-08-31 15:00:00]` | HTTP 200; provider code `0`; documented OHLCV fields; 241 rows; labels range from `09:30:00` to `15:00:00`; no credential echo. | The current entitlement covers a one-day historical 1-minute sample. Higher frequency does not create point-in-time open availability. |
| `rt_min` | `000703.SZ`, `5MIN` | HTTP 200; provider code `40203`; no rows or fields; no credential echo. | Current proxy credential has no demonstrated real-time-minute entitlement. |

The first `rt_min` attempt correctly exposed gzip transport encoding; the retry used the existing acquisition path’s gzip handling and produced the result above. No raw payloads or credentials were persisted.

## What would resolve the execution blocker

A usable next-bar-open route needs **both**:

1. a provider source that records a real eligible opening observation with a defensible `event_time == available_time` (or a separately documented delayed availability); and
2. an accepted public `bar_open@1` Bundle/profile/preparation route compatible with that evidence.

A prospective `rt_min` capture, if later entitled, would still need to establish whether an in-progress bar exposes an opening observation, preserve local receipt timestamps and source revisions, and create a new source contract. It would start only after capture begins; it cannot establish those facts for 2024–2026 history.

Do not synthesize a causal open from `stk_mins`/`rt_min` final OHLC rows, and do not use a same-bar close as a substitute without separately approving and implementing a different execution model.
