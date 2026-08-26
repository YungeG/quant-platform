# QB-S0-SRC-01 — Tushare broad lightweight catalog source sentinel v1

- **Status:** `IMPLEMENTED / PR_10_OPEN / REAL_CANDIDATE_INDEPENDENTLY_ACCEPTED / SOURCE_BOUNDED`
- **Owner:** Backtest acquisition tooling
- **Purpose:** first S0 plumbing capture for staged acquisition; not an S0 member set or authority
- **Implementation base:** Backtest PR #9 head `5b99e50826a526cfd81ea8a28d2a1d1bf3daf52c`

## 1. Exact provider-response scope

Through one caller-selected approved xiaodefa endpoint, issue exactly three requests in order:

```text
api_name = stock_basic
params = {"list_status": "L"}
params = {"list_status": "D"}
params = {"list_status": "P"}
```

Exact field order:

```text
ts_code,symbol,name,area,industry,fullname,enname,cnspell,
market,exchange,curr_type,list_status,list_date,delist_date,
is_hs,act_name,act_ent_type
```

All returned rows are retained unchanged, including BSE rows, null fields and special provider codes. No exchange/currency/market filtering occurs in the sentinel.

The output is a frozen provider-response capture only. It is not `s0_lightweight_source_capture_manifest@1`, a normalized broad-Universe member set, structural eligibility or accepted S0 authority. SSE/SZSE/CNY counts are computed later by a separate research assessment.

`capture_key = 20260826-s0-candidate-01` is local identity, not provider event/as-of time.

## 2. Probe-frozen expectations

Authorized probe on 2026-08-26 observed:

| Status | Rows | Terminal envelope |
| --- | ---: | --- |
| `L` | `5,550` | `has_more=false`, `count=0` |
| `D` | `339` | `has_more=false`, `count=0` |
| `P` | `0` | `has_more=false`, `count=0` |

Production exact-validates these counts. Provider drift fails before publication and requires a new reviewed packet; it is not accepted silently.

## 3. Exact three-file write set

1. `tools/acquisition/cn_a_share_tushare_s0_lightweight_catalog_source_bounded_v1.py`
2. `tests/tools/acquisition/test_cn_a_share_tushare_s0_lightweight_catalog_source_bounded_v1.py`
3. `tests/architecture/test_g12a_s0_lightweight_catalog_source_bounded_v1_boundary.py`

Architecture test freezes:

```text
PREDECESSOR = 5b99e50826a526cfd81ea8a28d2a1d1bf3daf52c
ALLOWED = exactly the three files above
```

It checks committed plus worktree differences. All predecessor bytes remain unchanged.

## 4. Exact production symbols and reuse

Add exactly:

```text
TushareS0LightweightCatalogSourceBoundedRequestV1
_timestamp
_validate_rows
acquire_tushare_s0_lightweight_catalog_source_bounded_v1
_parser
main
```

Reuse, do not copy:

```text
ProxyPost
_ALLOWED_ENDPOINTS
_MINIMUM_DELAY_SECONDS
_PROXY_KEY
_headers
_post_with_retries
_request_body
_stdlib_post
_authority_rows
_is_real_historical_date
_common.publish_directory
```

The request type has no caller-configurable scope fields and canonicalizes type/schema, capture key, ordered statuses and exact field tuple.

## 5. Output and snapshot

One absent output directory contains exactly:

```text
response/tushare/stock_basic/listed-v1.json
response/tushare/stock_basic/delisted-v1.json
response/tushare/stock_basic/suspended-listing-v1.json
source-snapshot.json
acquisition-receipt.json
```

The three raw files are the exact helper-returned HTTP entities after gzip content decoding, with no later JSON rewrite or row reordering.

Freeze three `RawSourceMember`s with:

- exact member keys above;
- logical mode `0644`;
- individual immediate post-response timestamps;
- `declared_sha256=None`.

Exact provenance:

```text
vendor_key = tushare.pro
source_key = tushare.pro.via.xiaodefa.approved-proxy.stock_basic.s0-lightweight.20260826
license_ref = tushare.pro.terms
retention_policy_ref = backtest.acquisition.candidate
```

`source-snapshot.json` and receipt are not snapshot members. Disk files are `0600` through existing publisher behavior.

## 6. Exact receipt schema

```text
type = tushare_s0_lightweight_catalog_source_bounded_acquisition_receipt_v1
schema_version = 1
request
provider_key = tushare.pro
transport_proxy_key
transport_endpoint
provider_requests = [L, D, P]
acquired_at_epoch_nanoseconds = max(member timestamps)
snapshot
limitations
source_bounded = true
provider_revision_id = null
historical_as_of_qualified = false
provider_completeness_qualified = false
revision_closure_complete = false
survivorship_bias_safe = false
industry_history_qualified = false
trade_status_history_qualified = false
decision_grade_eligible = false
deployment_authorized = false
absence_authority = false
```

Each `provider_requests` member exact-binds:

```text
api_name
params
fields
member_key
auth_mode = x-api-key
attempts
response_received_at_epoch_nanoseconds
response_byte_count
response_sha256
returned_row_count
observed_envelope = {has_more:false,count:0}
provider_revision_id = null
declared_sha256 = null
```

No optional advisory summaries belong in v1.

## 7. Validation and failure order

Order:

1. exact request type;
2. new-output/no-clobber check;
3. exact 56-character token validation;
4. one approved endpoint;
5. callable post/sleep/time callbacks;
6. for `L`, `D`, `P`: request → bounded transport → immediate clock → envelope/schema → cardinality → row validation;
7. wrapped `0.5` second inter-request sleep before `D` and before `P`;
8. cross-status conflict validation;
9. snapshot freeze;
10. credential scan;
11. publication.

Reused `_authority_rows` envelope/schema/row-width validation precedes cardinality. Cardinality then precedes semantic row checks; intra-response duplicate checks precede cross-status conflicts.

Row validation:

- exact row width;
- `list_status` equals request;
- nonempty string `ts_code`, `symbol`, `name`, `exchange`, `curr_type`, `list_date`;
- real `list_date`;
- null or real `delist_date >= list_date`;
- every other field is string or null;
- unique `ts_code` within one response;
- no `ts_code` across status responses.

Do not reject null `industry`, `market`, controller or English-name fields. `T600018.SH` is retained, not normalized.

Duplicate-key JSON, `NaN`, non-finite/exponent-overflow row values, wrong field order, terminal mismatch and changed cardinality fail closed.

## 8. Transport, redaction and timestamps

- one endpoint, no failover;
- canonical POST and disabled redirects through reused helper;
- existing bounded retry semantics;
- explicit inter-request delays must record `[0.5, 0.5]` in tests;
- transport, retry, sleep and clock exceptions are wrapped generically with `raise ... from None`;
- each clock result is exact non-boolean, nonnegative `int`;
- token is absent from request bodies, exceptions, stdout and all files.

## 9. Publication claim

Bind v1 to `_common.publish_directory` only:

- write-once/no-clobber;
- receipt written last;
- file and directory fsync;
- cleanup after ordinary validation/write/fsync exceptions.

No crash-safe or concurrent-reader atomic-visibility claim is made. A stronger rename protocol would require `_common.py` in a separately approved write set.

## 10. Fixed nonclaims

The capture does not prove complete historical inventory, as-of identity, code-change continuity, board/industry/status history, revisions, terminal closure, survivorship safety, S0 authority, S1 eligibility or later-stage qualification.

## 11. Implementation evidence

- Backtest commit: `ea17ccf93f6242222800c298d6aab39177b8455d`
- PR: <https://github.com/YungeG/quant-backtest/pull/10>
- Focused validation: `40 passed`
- Builder/acquisition validation: `589 passed, 5 skipped`
- Independent code and real-candidate review: accepted
- Real SourceSnapshot: `sha256:b5b7a9243439146181ef07acd07c09e79d16f605bc6cfdc3148746e64359e198`

## 12. Test and acceptance matrix

Focused tests cover:

- exact bodies/order/headers/endpoint and no failover;
- `[0.5,0.5]` spacing;
- retryable 429/5xx/transport and non-retry 3xx/4xx;
- three post-response clocks and max receipt timestamp;
- duplicate keys, `NaN`, `1e999`, fields/envelope/cardinality;
- row typing/dates/intra- and cross-status conflicts;
- exact raw-byte equality and row-order preservation;
- snapshot keys/modes/hashes/timestamps/provenance;
- receipt schema and every false/null qualification;
- token leakage through transport/sleep/time failures;
- file modes, no-clobber, file-fsync/directory-fsync failure cleanup;
- exact three-file branch diff.

Implementation must use a clean worktree based directly on `5b99e50826a526cfd81ea8a28d2a1d1bf3daf52c`.
