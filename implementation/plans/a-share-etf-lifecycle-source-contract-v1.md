# ETF-LIFECYCLE-01 — Three-ETF prospective lifecycle source contract v1

> Archive note (2026-09-22): This preserves the original design/status record, not a new implementation or execution approval. Frozen terms, status labels, hashes and reported checks below keep their original scope; no source authority, live-smoke result or holdout-consumption status was revalidated for this commit. Referenced local evidence and submodule work are not published by this document commit. Historical paths may have moved; see the [data inventory](../../overall/research-data-inventory.md). The [dependency alignment](../dependency-alignment-20260921.md) and callable ordinary-stock preparation do not establish an accepted three-ETF portfolio route. All readiness and separate authorization gates remain in force.

- **Status:** `FROZEN / SENTINEL_IMPLEMENTED / LIVE_PROXY_SMOKE_PASSED`
- **Scope:** `510300.SH`, `511010.SH`, and `518880.SH`
- **Prospective interval:** `[2026-09-01, 2027-09-01)`
- **Source-definition evidence:** `backtest/evidence/etf-data-01/lifecycle-source-contract/20260901`
- **Source-definition manifest:** `sha256:708fbe4542076ecafee37bcaa1868aa7169e2d15b8bb01594723d3a652630e0f`
- **Transport authority:** `backtest/docs/adr/0010-xiaodefa-is-approved-tushare-transport-proxy.md`

## Outcome

Retain enough structured and first-party source evidence to determine daily listing/trading status and to account for cash distributions, unit changes, suspensions, mergers, and termination without inferring events from adjusted prices.

This contract is acquisition and normalization authority only. It grants no decision-grade, broker, creation/redemption, live, or deployment authority.

## Source roles

| Source | Role | Authority ceiling |
| --- | --- | --- |
| Tushare `fund_basic` via approved Xiaodefa proxy | exact-code identity, list/delist fields, current status candidate | current snapshot only; cannot prove historical revision closure alone |
| Tushare `fund_div` via approved Xiaodefa proxy | structured distribution candidate and dates/terms | reconciliation candidate; not sufficient for accounting alone |
| SSE fund-announcement query and linked source bytes | official distributions, unit changes, mergers, termination, identity/status changes | primary lifecycle announcement authority |
| SSE fund suspension query | exact-date trading suspension/resumption state | primary session-status authority for the queried date |

`fund_adj` remains reconciliation-only. A changed adjustment factor cannot create a cash or quantity journal entry.

## Bounded request set

Each capture uses canonical Instrument order, one declared `capture_date`, and exactly one caller-selected approved proxy endpoint: `https://fast.xiaodefa.cn` or `https://tt.xiaodefa.cn`. No failover occurs within a capture.

1. three Tushare `fund_basic` requests, one exact `ts_code` each, `market=E`;
2. three Tushare `fund_div` requests, one exact `ts_code` each;
3. three SSE fund-announcement queries, one six-digit code each, covering `[2026-09-01, capture_date]`;
4. three SSE fund-suspension queries, one six-digit code each, covering `[capture_date, capture_date]`;
5. one exact GET for every SSE announcement URL returned by step 3.

SSE query page size is 100. V1 accepts only `pageCount <= 1`; more than 100 results for one Instrument in the bounded interval fails closed rather than silently truncating or introducing a pagination protocol after freeze.

Tushare-compatible calls send credential-free canonical JSON to the selected endpoint with `Accept-Encoding: gzip`; the exact 56-character `TUSHARE_PROXY_TOKEN` is sent only as `x-api-key`. Redirects are disabled, provider calls are spaced by at least `0.5s`, and token bytes are forbidden from request bodies, URLs, source members, receipts, logs, and exceptions.

Each logical request permits at most three transport attempts with a 30-second timeout and retry delays of at least `1s, 2s`. Linked announcement downloads use the same limit. The snapshot publishes no output until every required member succeeds.

## Exact fields

### `fund_basic`

```text
ts_code,name,management,custodian,fund_type,found_date,due_date,list_date,
issue_date,delist_date,issue_amount,m_fee,c_fee,duration_year,p_value,
min_amount,exp_return,benchmark,status,invest_type,type,trustee,
purc_startdate,redm_startdate,market
```

The response must contain exactly one row for the requested `ts_code`; `market` must be `E`. Unknown/missing status or identity mismatch fails source scope.

### `fund_div`

```text
ts_code,ann_date,imp_anndate,base_date,div_proc,record_date,ex_date,
pay_date,earpay_date,net_ex_date,div_cash,base_unit,ear_distr,
ear_amount,account_date,base_year
```

Every successful proxy response requires `has_more=false` and the approved-proxy sentinel value `count=0`. Zero `items` rows are a valid source response but prove only that this endpoint returned no rows. Rows use exact source lexemes until a separate distribution numeric mapping is accepted.

### SSE announcements

Frozen query identity; the parameter set is exhaustive:

```text
endpoint=https://query.sse.com.cn/commonQuery.do
isPagination=true
pageHelp.pageSize=100
pageHelp.pageNo=1
pageHelp.beginPage=1
pageHelp.cacheSize=1
pageHelp.endPage=1
type=inParams
sqlId=COMMON_PL_JJXX_JJGG_NEW_L
TITLE=
SECURITY_CODE=<six-digit code>
BULLETIN_TYPE=
START_DATE=2026-09-01
END_DATE=<capture_date YYYY-MM-DD>
DATE_DESC=1
DATE_ASC=
CODE_DESC=
CODE_ASC=
```

The top-level response must contain `actionErrors` and `actionMessages` as empty arrays, `fieldErrors` as an empty object, `result` as an array, `pageHelp` as an object, and exact `sqlId`. `pageHelp.pageCount`, `pageHelp.total`, `pageHelp.pageNo`, and `pageHelp.pageSize` must be integers; `pageCount <= 1`, `pageNo == 1`, `pageSize == 100`, `total == len(result)`, and `pageHelp.data == result` are required.

Every result must contain string fields `NUM`, `SECURITY_CODE`, `SSEDATE`, `TITLE`, and `URL`; `NUM` must be decimal digits, `SECURITY_CODE` must equal the requested code, `SSEDATE` must lie inside the query interval, and `TITLE`/`URL` must be nonempty. `URL` must resolve under `https://www.sse.com.cn/`; off-host, credential-bearing, fragment-bearing, or non-HTTPS URLs fail closed. Linked bytes are mandatory snapshot members.

### SSE suspensions

Frozen query identity; the parameter set is exhaustive:

```text
endpoint=https://query.sse.com.cn/sseQuery/commonSoaQuery.do
isPagination=true
sqlId=SSE_PL_JYTS_TFPXX_JJ
secCode=<six-digit code>
stopReason=
order=startStopDate|desc,secCode|asc
startDate=<capture_date YYYYMMDD>
endDate=<capture_date YYYYMMDD>
pageHelp.pageSize=100
pageHelp.pageNo=1
pageHelp.beginPage=1
pageHelp.cacheSize=1
pageHelp.endPage=1
```

The top-level error, result, page, `sqlId`, equality, count, and integer requirements are identical to the announcement response. Every returned row must contain string fields `secCode`, `expandAbbr`, `startStopDate`, `endStopDate`, `stopTime`, `dateSource`, `startStopType`, `startStopReason`, and `endStopReason`; `secCode` must equal the requested code and any nonempty date must be `YYYYMMDD`. Zero rows may support `NO_REPORTED_SUSPENSION_FOR_DATE`; it does not prove that the Instrument traded or had a valid bar.

## Publication

The sentinel writes exact response bytes first and one receipt last. The receipt binds:

- capture date and prospective start;
- semantic provider `tushare.pro`, transport key `xiaodefa.approved-tushare-proxy.v1`, exact endpoint, and `auth_mode=x-api-key`;
- all logical request coordinates and attempt counts;
- response/member byte counts and SHA-256 hashes;
- SSE announcement download URLs and hashes;
- a G12A source snapshot/content-tree/provenance identity;
- predecessor lifecycle capture ref/hash when present;
- `decision_grade_eligible=false` and `deployment_authorized=false`.

Output is no-clobber and append-only. Credentials and authorization headers are never persisted.

## Normalized lifecycle state

### `EtfLifecycleRevision@1`

- stable Instrument identity and product class;
- revision kind: `LISTING_STATUS`, `TRADING_STATUS`, `CASH_DISTRIBUTION`, `UNIT_CHANGE`, `MERGER`, or `TERMINATION`;
- source lifecycle state and normalized terminal/open disposition;
- announcement, record, ex/effective, payment, list, or delist dates as applicable;
- exact raw terms plus accepted normalized cash/share terms when available;
- `available_at` from retained source receipt, never from event date;
- source member/hash, revision ID, and optional predecessor;
- explicit conflicts and closure limitations.

### Daily state rules

1. `fund_basic` status changes require an official SSE announcement before becoming lifecycle authority.
2. A `fund_div` row requires a matching official SSE announcement before accounting.
3. Unit changes, mergers, and termination are announcement-driven; title keywords may find candidates but cannot determine terms.
4. SSE suspension rows determine reported suspension/resumption intervals; a missing `fund_daily` row is not a substitute.
5. Previously announced future-effective actions remain active across daily snapshots until terminal accounting disposition.
6. Conflicting dates/terms remain unresolved and block the affected Instrument/session.

## Capture timing

- **Pre-open status capture:** after the SSE morning publication window and before order admission for the session.
- **Post-close lifecycle capture:** after the session is final, alongside the daily price source capture.

A post-close capture cannot retroactively authorize a same-day open. The first planned purchase or sale for a date requires a retained pre-open status snapshot available before that execution instant.

## Failure precedence

| Priority | Condition | Outcome |
| ---: | --- | --- |
| 1 | request type/date/instrument/endpoint/callable/credential/output/predecessor mismatch | `INPUT_MISMATCH` |
| 2 | output already exists | `OUTPUT_EXISTS` |
| 3 | transport exhausted or invalid response tuple | `TRANSPORT_FAILURE` |
| 4 | credential echo, invalid JSON, duplicate key, provider rejection, or SSE error collection | `SOURCE_INTEGRITY_FAILURE` |
| 5 | exact fields, row identity, query coordinate, page count/total, or linked URL mismatch | `SOURCE_SCOPE_INCOMPLETE` |
| 6 | linked SSE announcement download missing or hash failure | `ANNOUNCEMENT_MEMBER_FAILURE` |
| 7 | G12A snapshot freeze failure | `SNAPSHOT_FAILURE` |
| 8 | receipt-last durable publication failure | `PUBLICATION_FAILURE` |

No failure publishes a partial lifecycle snapshot or a false no-event disposition.

## Implementation

- Tool: `backtest/tools/acquisition/cn_a_share_tushare_etf_lifecycle_sentinel_v1.py`
- Focused test: `backtest/tests/tools/acquisition/test_cn_a_share_tushare_etf_lifecycle_sentinel_v1.py`
- Validation: 20 focused tests, 12 adjacent ETF price-sentinel tests, 117 acquisition/boundary tests, Ruff, LSP/auxiliary diagnostics, gitleaks, and independent review pass.
- The sentinel uses the accepted ADR-0010 proxy seam. A live `https://fast.xiaodefa.cn` smoke completed all six Tushare-compatible requests plus six SSE queries, retained 12 members, reproduced one G12A snapshot, and kept both authorization flags false. No announcement download was returned for the smoke interval.

## Readiness gate

`ETF-LIFECYCLE-01` is not ready for Profile use until:

1. one live sentinel capture proves the bounded transport path;
2. one pre-open and one post-close capture are retained for an eligible session;
3. distribution numeric mapping and official-announcement reconciliation are accepted;
4. normalized lifecycle state proves deterministic replay and predecessor handling;
5. all open actions affecting the requested interval reach an explicit terminal or blocking disposition.
