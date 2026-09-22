# Research: Tushare `stk_mins` for an A-share 5-minute source-bounded lane

> Archive note (2026-09-22): Preserved research/probe record, not a fresh authority or readiness assessment. “Current/now” and reported passes refer to the original task; external sources, entitlements, retained artifacts and historical availability were not revalidated for this archival commit. Referenced `backtest/evidence/` files are local and are not published here. No new sample consumption, capture, Backtest, qualification or trading authorization follows.
>
> The direct-Tushare facts below do not replace the separately accepted [proxy transport ADR](../backtest/docs/adr/0010-xiaodefa-is-approved-tushare-transport-proxy.md). The embedded `acceptance-report` is the original handoff, whose `research.md` path and `noStagedFiles` describe that delivery; the retained document is now `research/tushare-stk-mins-source-contract.md`, not a newly issued Platform acceptance report.

## Summary

Tushare’s first-party documentation identifies `stk_mins` as its **direct** historical A-share minute-bar API. A 5-minute lane must call it with one `ts_code`, `freq='5min'`, and optional datetime bounds; it requires the separately purchased historical-minute permission, not an integral/points threshold. [Historical minute API](https://tushare.pro/document/2?doc_id=370) · [Permission table](https://tushare.pro/document/1?doc_id=290)

The documentation is sufficient to bound requests (8,000 rows/request; 500 requests/minute under the historical-minute entitlement) and to interpret `vol` and `amount`, but does **not** document `trade_time` as a bar-start or bar-end timestamp, timezone, market-session filtering, price units, revision/correction policy, or a maximum date-span rule.

## Findings

1. **Direct API and exact request parameters.** The API page says: “接口：`stk_mins`” and “获取A股分钟数据”; required inputs are `ts_code` (`str`, e.g. `600000.SH`) and `freq` (`str`), while `start_date` and `end_date` are optional `datetime` values. The documented input formats are respectively `2023-08-25 09:00:00` for start and `2023-08-25 19:00:00` for end. The documented SDK form is:

   ```python
   pro.stk_mins(ts_code='600000.SH', freq='1min',
                start_date='2023-08-25 09:00:00',
                end_date='2023-08-25 19:00:00')
   ```

   For HTTP, Tushare’s general first-party guide specifies POST JSON to `http://api.tushare.pro`, with outer JSON members `api_name`, `token`, `params`, and optional `fields`; use `api_name: "stk_mins"` and put the four API inputs above in `params`. This is the generic direct-Tushare transport contract; the `stk_mins` page itself does not publish a distinct HTTP request example. [API parameters and example](https://tushare.pro/document/2?doc_id=370) · [HTTP transport contract](https://tushare.pro/document/1?doc_id=130)

2. **Allowed frequencies.** The exact permitted `freq` values are `1min`, `5min`, `15min`, `30min`, and `60min`; the table defines `5min` as “5分钟.” No other frequency is documented for this endpoint. [Frequency table](https://tushare.pro/document/2?doc_id=370)

3. **Returned fields and documented units.** The output table lists `ts_code` (`str`, stock code), `trade_time` (`str`, “交易时间”), `open`, `close`, `high`, and `low` (all `float`, described only as opening/closing/high/low prices), `vol` (`int`, “成交量(股)”), and `amount` (`float`, “成交金额（元）”). Therefore, `vol` is in **shares** and `amount` in **CNY yuan**. The page does **not** state price units for OHLC; do not assume yuan merely because `amount` is yuan. Its sample displays `vol` with decimal formatting despite the declared `int` type, so consumers should not rely on display formatting as a stronger type guarantee. [Output table and sample](https://tushare.pro/document/2?doc_id=370)

4. **`trade_time`, timezone, and session scope are undocumented for this endpoint.** The only field definition is “交易时间” (trading time). The sample contains 1-minute labels from `09:30:00` through `15:00:00`, but the documentation never labels them as bar **start** or **end**, never names a timezone, never states whether non-session input bounds are clipped or rejected, and never defines the eligible A-share exchanges/boards, auction treatment, lunch break, or holiday behavior. Treat the sample as illustrative, not a semantic contract. [Field definition and sample](https://tushare.pro/document/2?doc_id=370)

5. **Range, pagination, and row-rate limits.** The `stk_mins` page says “单次最大8000行数据，可以通过股票代码和时间循环获取” (maximum 8,000 rows per request; obtain data by looping stock codes and times). It does **not** document `offset`, `limit`, cursor, page token, ordering guarantee, or a maximum calendar/time range; chunk requests by time and keep each response below 8,000 rows. The first-party independent-permission table separately states for “历史分钟” (including 1/5/15/30/60 minutes): “每分钟500次，每次8000行数据，正常调取” (500 requests/minute; 8,000 rows/request). [Endpoint limit](https://tushare.pro/document/2?doc_id=370) · [Historical-minute entitlement table](https://tushare.pro/document/1?doc_id=290)

6. **Permission, points, and historical availability.** `stk_mins` says “需单独开权限” (separate permission required). The permissions page says minute permissions are “不在积分范畴内” and “单独分别开权限，且不加积分” (outside the points system; each opened separately and no points added). Its historical-minute row covers 1/5/15/30/60-minute data, gives historical start “2009年,” price “单独2000元,” and the 500/minute and 8,000-row limits above. The endpoint page says it “可以提供超过10年历史分钟数据” (can provide more than ten years of historical minute data). These are service/entitlement statements, not a guarantee that every symbol has complete bars from 2009. [Endpoint permission/history statement](https://tushare.pro/document/2?doc_id=370) · [Independent-permission table](https://tushare.pro/document/1?doc_id=290)

7. **Corrections, revisions, and adjustment policy.** No correction, restatement, revision, backfill, late-data, corporate-action adjustment, or versioning policy appears on the `stk_mins` documentation page. In particular, no `adj`/`fq` request parameter is documented for `stk_mins`; do not transfer the daily-only adjustment claims from Tushare’s separate adjustment documentation to minute bars. Revision-aware ingestion must therefore be an application decision (e.g., overlap/re-fetch recent windows) rather than a documented Tushare `stk_mins` guarantee. [Complete `stk_mins` API page](https://tushare.pro/document/2?doc_id=370) · [Separate adjustment page says “目前只支持A股的日线复权”](https://tushare.pro/document/2?doc_id=146)

8. **Direct Tushare only; no xiaodefa proxy inference.** Every operational fact above comes from `tushare.pro` first-party documentation and applies to direct Tushare SDK/HTTP use. No xiaodefa proxy documentation was used or found in this research; its request schema, authentication, limits, timestamp conversion, caching, data transformations, and permission propagation are **not documented here and must not be inferred** from direct-Tushare facts.

## Sources

- Kept: [股票历史分钟行情 / `stk_mins`](https://tushare.pro/document/2?doc_id=370) — primary endpoint specification: A-share scope, input/output fields, allowed frequencies, single-request cap, SDK example, and >10-year claim.
- Kept: [积分与频次权限对应表](https://tushare.pro/document/1?doc_id=290) — primary entitlement catalog: independent (non-points) minute permission, 2009 historical-start listing, price, rate, and row cap.
- Kept: [通过HTTP调取数据](https://tushare.pro/document/1?doc_id=130) — primary generic direct HTTP POST/JSON envelope and response-contract documentation.
- Kept: [A股复权行情](https://tushare.pro/document/2?doc_id=146) — primary evidence that the cited adjustment statement is daily-only, preventing an unsupported minute-bar adjustment claim.
- Dropped: Search-result excerpts and non-Tushare commentary — redundant or not first-party endpoint evidence.
- Dropped: xiaodefa proxy materials — out of scope; no proxy behavior may be inferred from Tushare documentation.

## Gaps

- First-party `stk_mins` documentation does not define whether `trade_time` marks an interval’s open or close, its timezone, session/auction/lunch/holiday rules, endpoint ordering, time-bound inclusivity, or a max datetime span.
- It gives no correction/revision/backfill SLA or historical-completeness guarantee by symbol.
- Before using this as a production source, obtain written Tushare confirmation or run a permitted, bounded empirical validation for 5-minute boundary timestamps and session coverage. Verify any xiaodefa proxy separately against its own contract.

## Acceptance report

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "Concrete first-party Tushare findings, documented unknowns, and direct-vs-proxy boundary recorded in /home/ygguo/agent-projs/ai-crypt/platform/research.md."
    }
  ],
  "changedFiles": [
    "/home/ygguo/agent-projs/ai-crypt/platform/research.md"
  ],
  "testsAddedOrUpdated": [],
  "commandsRun": [
    {
      "command": "Focused first-party web research: tushare.pro `stk_mins`, permission table, and HTTP guide",
      "result": "passed",
      "summary": "Primary documentation located and cross-checked; no credentials used."
    }
  ],
  "validationOutput": [
    "research.md contains source URLs, quoted/documented statements, explicit undocumented facts, and direct-Tushare-only scope."
  ],
  "residualRisks": [
    "trade_time start/end semantics, timezone, session rules, ordering, bounds inclusivity, and revision policy are not documented for stk_mins.",
    "Historical-minute entitlement lists 2009 but does not guarantee complete data for every symbol.",
    "xiaodefa proxy behavior remains unknown and must be verified from its own documentation."
  ],
  "noStagedFiles": true,
  "diffSummary": "Research-only addition of the required evidence brief at the authoritative output path.",
  "reviewFindings": [
    "high: /home/ygguo/agent-projs/ai-crypt/platform/research.md - Do not encode undocumented trade_time, timezone/session, revision, or xiaodefa-proxy assumptions into the 5-minute lane."
  ],
  "manualNotes": "No repository source changes or credentials were used; only the required research artifact was written."
}
```
