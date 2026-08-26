# QB-S1-SRC-01 — Tushare annual structural roster source sentinel v1

- **Status:** `IMPLEMENTATION_PACKET_FROZEN / USER_APPROVED / SOURCE_BOUNDED / PLAN_ONLY`
- **Owner:** Backtest acquisition tooling
- **Purpose:** retain annual provider roster/industry observations for 2016–2025 S1 development; not S1 authority
- **Implementation base:** Backtest PR #10 head `ea17ccf93f6242222800c298d6aab39177b8455d`

## 1. Exact requests

One caller-selected approved xiaodefa endpoint; no failover.

First:

```text
api_name = trade_cal
params = {exchange:SSE,start_date:20160430,end_date:20250510}
fields = exchange,cal_date,is_open,pretrade_date
```

Then exact `bak_basic` requests in order, each with:

```text
params = {trade_date:<date>}
fields = trade_date,ts_code,name,industry,list_date
```

Dates:

```text
20160503
20170502
20180502
20190506
20200506
20210506
20220505
20230504
20240506
20250506
```

All returned rows are retained unchanged. No exchange, board, industry, listing-age or S0-join filtering occurs in this sentinel.

## 2. Frozen expectations

| Request | Rows |
| --- | ---: |
| trade calendar | `3,298` |
| `20160503` | `0` |
| `20170502` | `3,232` |
| `20180502` | `3,518` |
| `20190506` | `3,622` |
| `20200506` | `3,850` |
| `20210506` | `4,326` |
| `20220505` | `4,719` |
| `20230504` | `4,994` |
| `20240506` | `5,364` |
| `20250506` | `5,415` |

Every response requires `has_more=false`, `count=0`. Drift fails and requires a new packet.

After reused calendar-range validation, derive each date as the chronological minimum `is_open=1` `cal_date` in `(April 30, May 10]`. The returned ordered tuple must equal the frozen ten-date tuple and that returned tuple drives the ten `bak_basic` requests; provider row order is irrelevant.

## 3. Output

One absent output directory contains exactly thirteen files:

```text
response/tushare/trade_cal/sse-20160430-20250510-v1.json
response/tushare/bak_basic/20160503-v1.json
response/tushare/bak_basic/20170502-v1.json
response/tushare/bak_basic/20180502-v1.json
response/tushare/bak_basic/20190506-v1.json
response/tushare/bak_basic/20200506-v1.json
response/tushare/bak_basic/20210506-v1.json
response/tushare/bak_basic/20220505-v1.json
response/tushare/bak_basic/20230504-v1.json
response/tushare/bak_basic/20240506-v1.json
response/tushare/bak_basic/20250506-v1.json
source-snapshot.json
acquisition-receipt.json
```

Raw files are exact helper-returned HTTP entities after gzip decoding. Exactly the eleven raw responses, and not `source-snapshot.json` or receipt, are `RawSourceMember`s with logical `0644`, individual post-response timestamps and null declared hashes; disk files are `0600`.

Exact provenance:

```text
vendor_key = tushare.pro
source_key = tushare.pro.via.xiaodefa.approved-proxy.annual-structural-roster.2016-2025.20260826
license_ref = tushare.pro.terms
retention_policy_ref = backtest.acquisition.candidate
```

## 4. Exact three-file write set

1. `tools/acquisition/cn_a_share_tushare_annual_structural_roster_source_bounded_v1.py`
2. `tests/tools/acquisition/test_cn_a_share_tushare_annual_structural_roster_source_bounded_v1.py`
3. `tests/architecture/test_g12a_annual_structural_roster_source_bounded_v1_boundary.py`

Architecture freezes predecessor `ea17ccf93f6242222800c298d6aab39177b8455d` and exact three-file committed/worktree differences.

## 5. Production symbols and reuse

Add exactly:

```text
TushareAnnualStructuralRosterSourceBoundedRequestV1
_timestamp
_validate_trade_calendar_rows
_validate_roster_rows
acquire_tushare_annual_structural_roster_source_bounded_v1
_parser
main
```

Reuse the same approved proxy, authority parsing, SourceSnapshot and `_common.publish_directory` helpers frozen by QB-S0-SRC-01, plus `_validate_trade_calendar_range_v2` from `cn_a_share_tushare_trade_calendar.py`. Required reused names include `ProxyPost`, `_ALLOWED_ENDPOINTS`, `_MINIMUM_DELAY_SECONDS`, `_PROXY_KEY`, `_headers`, `_post_with_retries`, `_request_body`, `_stdlib_post`, `_authority_rows`, `_is_real_historical_date`, `_validate_trade_calendar_range_v2`, and `_common.publish_directory`.

Do not copy transport/calendar validators, import direct HTTP clients, fail over endpoints or read prior S0 artifact files.

## 6. Validation

### Trade calendar

- exact field order/row width/cardinality;
- reuse `_validate_trade_calendar_range_v2(rows, exchange="SSE", start_date="20160430", end_date="20250510")`;
- therefore each `pretrade_date` is strictly earlier than `cal_date`, dates are unique/in-range and `is_open` is exact non-boolean integer `0/1`;
- derive chronological minimum opens in `(April 30, May 10]` and return/compare the fixed tuple used for roster calls.

### Annual roster

- exact field order/row width/cardinality;
- every row `trade_date` equals request;
- nonempty string `ts_code`, `name`, `list_date`;
- `industry` is string or null;
- real `list_date <= trade_date`;
- unique `ts_code` within the response;
- no assumption that row presence equals listing/tradability;
- no cross-date uniqueness requirement.

Reused `_authority_rows` envelope/schema/row-width checks precede cardinality; cardinality precedes semantic row validation.

## 7. Flow, spacing and redaction

1. exact request/new-output/token/endpoint/callback checks;
2. trade calendar request → immediate timestamp → validation;
3. `0.5` second delay;
4. each roster request → immediate timestamp → validation, with `0.5` delay before every later call;
5. snapshot freeze → credential scan → publication.

Eleven calls require exactly ten normal inter-request delays absent retries. Retry delays are additional and retain existing semantics.

Transport, retry, delay and clock exceptions are generic-redacted with `raise ... from None`; clock values are exact nonnegative non-boolean integers. Receipt acquisition time is the maximum member timestamp.

## 8. Request, CLI and receipt

`TushareAnnualStructuralRosterSourceBoundedRequestV1` has no caller-configurable scope fields. Exact canonical body keys/order-independent content:

```text
type = tushare_annual_structural_roster_source_bounded_request_v1
schema_version = 1
capture_key = 20260826-annual-structural-candidate-01
calendar_request = {exchange:SSE,start_date:20160430,end_date:20250510}
calendar_fields = [exchange,cal_date,is_open,pretrade_date]
roster_dates = [the frozen ordered ten dates]
roster_fields = [trade_date,ts_code,name,industry,list_date]
```

CLI accepts only `--endpoint` from approved choices and required `--output-dir`; token comes only from `TUSHARE_PROXY_TOKEN`.

Exact receipt type is `tushare_annual_structural_roster_source_bounded_acquisition_receipt_v1`, schema version `1`. Top-level keys are exactly:

```text
type,schema_version,request,provider_key,transport_proxy_key,
transport_endpoint,provider_requests,acquired_at_epoch_nanoseconds,
snapshot,limitations,source_bounded,calendar_authority_qualified,
historical_roster_qualified,listing_membership_qualified,
board_history_qualified,industry_history_qualified,
provider_completeness_qualified,revision_closure_complete,
survivorship_bias_safe,decision_grade_eligible,deployment_authorized,
absence_authority,provider_revision_id
```

Each ordered provider request contains exactly:

```text
api_name,params,fields,member_key,auth_mode,attempts,
response_received_at_epoch_nanoseconds,response_byte_count,
response_sha256,returned_row_count,observed_envelope,
provider_revision_id,declared_sha256
```

`fields` is the exact comma-delimited request-body string; `auth_mode="x-api-key"`; envelope is `{has_more:false,count:0}`; provider/declaration hashes are null.

Literal ordered limitations:

1. `2010-2015 annual primary-screen roster observations are unavailable in this capture`;
2. `20160503 zero rows are a bounded provider gap, not an empty Universe`;
3. `Tushare trade_cal is source-bounded and not accepted Calendar authority`;
4. `bak_basic row presence is not exchange listing or tradability authority`;
5. `board and official CSRC industry history are not established`;
6. `provider revision, absence, completeness, and terminal closure are not established`;
7. `formal S1, Fold, Strategy, Validation, and deployment authority are not granted`.

Fixed flags:

```text
source_bounded = true
calendar_authority_qualified = false
historical_roster_qualified = false
listing_membership_qualified = false
board_history_qualified = false
industry_history_qualified = false
provider_completeness_qualified = false
revision_closure_complete = false
survivorship_bias_safe = false
decision_grade_eligible = false
deployment_authorized = false
absence_authority = false
provider_revision_id = null
```

## 9. Publication claim

Reuse `_common.publish_directory`: no-clobber, receipt-last, fsync and cleanup after ordinary validation/write/fsync exceptions. No crash/concurrent-reader atomic-visibility claim.

## 10. Nonclaims

The explicit 2016 zero row is a bounded gap, not an empty Universe. Rows may include never-listed, other-board or BSE names. Provider industry is not official historical CSRC authority. Current S0 joins/code mappings remain later research assessments, not this capture.

No formal S1, Fold, Strategy, Validation or deployment authority is granted.

## 11. Tests

Cover exact eleven bodies/order/headers, ten delays, retry/nonretry, eleven clocks, chronological derived screen dates, cardinalities including zero, duplicate-key/nonfinite/schema/row/date failures, raw preservation, snapshot/receipt exactness, literal flags/limitations, token redaction, no-clobber/fsync cleanup and exact three-file diff. Positive cases retain null industry, BSE rows and the same `ts_code` on different roster dates.

Implementation uses a clean worktree based directly on `ea17ccf93f6242222800c298d6aab39177b8455d`.
