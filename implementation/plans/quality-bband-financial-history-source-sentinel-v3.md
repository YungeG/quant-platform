# QB-FIN-HISTORY-SENTINEL-03 — Gree 2018–2022 historical financial source expansion

- **Status:** `IMPLEMENTATION_AUTHORITY_FROZEN / APPROVED_FOR_STACKED_CANDIDATE / NOT_ACCEPTED`
- **Owner:** Backtest G12A acquisition
- **Base:** stacked PR #5 commit `5338d8046fa0f304d4a9590989c59ceffb51270b`
- **Existing 2023 source:** `sha256:dec0abb1828f8b87256347e72b6ccfe2f84a2ca13f36aa1415c9a53e96a0c7d5`
- **Purpose:** add the minimum earlier source periods required for six balance endpoints and five annual statement trios
- **Immutable probe:** `/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/probes/000651.SZ/2018-2022/v3-probe-01/probe-manifest.json`
- **Probe file SHA-256:** `sha256:2240d65b0533f5cb0898d406d2113df3ea48e31b6cda3e500eba25ee2de2d1a0`

## 1. Outcome

Publish one additive source-bounded SourceSnapshot for fixed issuer `000651.SZ` containing:

- balance-sheet responses for 2018–2022;
- income and cash-flow responses for 2019–2022;
- official CNINFO annual-report PDFs for 2018–2022;
- one raw official CNINFO annual-report query response that binds each report ID, URL and publication date.

Combined with the existing 2023 v2 SourceSnapshot, this supplies:

- balance endpoints `20181231` through `20231231` — six endpoints;
- complete annual statement trios `20191231` through `20231231` — five trios.

V3 is acquisition-only. It publishes no declaration, `available_at`, normalized revision, selected trio, formula, feature, MarketBundle, Strategy, Backtest request, grade or deployment authority.

## 2. Minimal seam

```python
ProxyPost = Callable[
    [str, dict[str, object], dict[str, str]],
    tuple[int, bytes],
]
CninfoPost = Callable[
    [str, tuple[tuple[str, str], ...], dict[str, str]],
    tuple[int, bytes],
]
Get = Callable[[str], tuple[int, bytes, str]]

class FinancialHistorySentinelV3FailureCode(str, Enum):
    INPUT_MISMATCH = "INPUT_MISMATCH"
    CREDENTIAL_INPUT_INVALID = "CREDENTIAL_INPUT_INVALID"
    PROVIDER_TRANSPORT_FAILURE = "PROVIDER_TRANSPORT_FAILURE"
    PROVIDER_RESPONSE_INVALID = "PROVIDER_RESPONSE_INVALID"
    PROVIDER_FIELDS_MISMATCH = "PROVIDER_FIELDS_MISMATCH"
    FINANCIAL_ROW_SCOPE_MISMATCH = "FINANCIAL_ROW_SCOPE_MISMATCH"
    CREDENTIAL_LEAK_DETECTED = "CREDENTIAL_LEAK_DETECTED"
    OFFICIAL_METADATA_TRANSPORT_FAILURE = "OFFICIAL_METADATA_TRANSPORT_FAILURE"
    OFFICIAL_METADATA_INVALID = "OFFICIAL_METADATA_INVALID"
    OFFICIAL_DOCUMENT_TRANSPORT_FAILURE = "OFFICIAL_DOCUMENT_TRANSPORT_FAILURE"
    ANNUAL_REPORT_MISMATCH = "ANNUAL_REPORT_MISMATCH"
    PUBLICATION_FAILURE = "PUBLICATION_FAILURE"

class FinancialHistorySentinelV3AcquisitionError(AcquisitionError):
    code: FinancialHistorySentinelV3FailureCode | SourceSnapshotFailureCode
    # constructor exact-requires one enum and exposes only code.value in the message

@dataclass(frozen=True, slots=True)
class TushareCnAShareFinancialHistorySentinelRequestV3:
    schema_version: int = 3


def acquire_tushare_cn_a_share_financial_history_sentinel_v3(
    request: TushareCnAShareFinancialHistorySentinelRequestV3,
    *,
    token: str,
    endpoint: str,
    output_dir: str | Path,
    proxy_post: ProxyPost,
    cninfo_post: CninfoPost,
    get: Get,
    time_ns: Callable[[], int] = time.time_ns,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, object]: ...
```

`ProxyPost`, allowed proxy endpoints, proxy request-body/header/retry helpers and stdlib proxy POST are imported from `cn_a_share_tushare_listing_source_bounded_v2`. `_provider_response` and `_require_safe_output` are imported from financial sentinel v1. `_INCOME_FIELDS`, `_BALANCE_FIELDS` and `_CASHFLOW_FIELDS` are imported from financial sentinel v2. Do not import v2 fixed-period validators/document helpers, duplicate the field tuples, or create a new shared abstraction.

`CninfoPost` is one injected callable for the exact official form POST. `Get` matches v2's document seam. No generic issuer/period configuration is introduced.

## 3. Fixed source range

| Role | Periods |
| --- | --- |
| Beginning balance endpoint | `20181231` |
| Five formula-year trios | `20191231`, `20201231`, `20211231`, `20221231`, existing `20231231` |
| New v3 capture | `20181231` through `20221231` only |
| Existing v2 capture reused | `20231231` |

Do not reacquire or copy the 2023 members into v3. A later feature manifest must bind both immutable SourceSnapshot identities.

Request `to_canonical_dict()` is exactly:

```python
{
  "type": "tushare_cn_a_share_financial_history_sentinel_request",
  "schema_version": 3,
  "predecessor_commit": "5338d8046fa0f304d4a9590989c59ceffb51270b",
  "issuer": "珠海格力电器股份有限公司",
  "provider_security_code": "000651.SZ",
  "instrument_candidate": "xshe:000651",
  "company_type": "1",
  "historical_periods": ("20181231", "20191231", "20201231", "20211231", "20221231"),
  "existing_2023_source_snapshot_id": "sha256:dec0abb1828f8b87256347e72b6ccfe2f84a2ca13f36aa1415c9a53e96a0c7d5",
  "probe_manifest_file_sha256": "sha256:2240d65b0533f5cb0898d406d2113df3ea48e31b6cda3e500eba25ee2de2d1a0",
  "cninfo_metadata_endpoint": "https://www.cninfo.com.cn/new/hisAnnouncement/query",
  "cninfo_metadata_form": _CNINFO_FORM,
  "annual_reports": _ANNUAL_REPORT_REQUEST_FACTS,
  "purpose_scope": "cn-a-share.financial-history-source-sentinel.000651.sz.2018-2022.v3",
}
```

`_CNINFO_FORM` and `_ANNUAL_REPORT_REQUEST_FACTS` are exact tuples in the order frozen below. Constructor exact-requires `schema_version == 3`; the acquisition operation also requires equality with a newly constructed default request to reject mutated exact-class instances.

## 4. Exact Tushare requests

Every request exact-binds:

```text
ts_code = 000651.SZ
comp_type = 1
period = frozen period
ann_date = frozen announcement date
```

No `report_type`, `update_flag` or `is_calc` filter. Every returned row is retained in source order. `update_flag` remains raw evidence and never means provider finality or supersession.

| Period | `ann_date` | APIs | Expected row count / update-flag multiset |
| --- | --- | --- | --- |
| `20181231` | `20190429` | `balancesheet` | `2 / {0,1}` |
| `20191231` | `20200430` | `income`, `balancesheet`, `cashflow` | each `2 / {0,1}` |
| `20201231` | `20210429` | `income`, `balancesheet`, `cashflow` | each `2 / {0,1}` |
| `20211231` | `20220430` | `income`, `balancesheet`, `cashflow` | each `2 / {0,1}` |
| `20221231` | `20230429` | `income` | `1 / {1}` |
| `20221231` | `20230429` | `balancesheet`, `cashflow` | each `2 / {0,1}` |

These facts are bound by the immutable probe manifest. Validation uses v1 `_provider_response(...)` and then exact-requires:

- `data.has_more` is exact `false`;
- provider envelope `data.count` is exact integer `0`; this field is **not** item cardinality;
- `len(data.items)` equals the table's expected row count;
- every row is an exact list with the frozen field length;
- `ts_code`, `ann_date`, `f_ann_date`, `end_date`, `report_type`, `comp_type` and `update_flag` are exact strings;
- `ts_code`, both announcement dates, period, report type `1` and company type `1` equal the frozen request facts;
- the sorted update-flag tuple equals the frozen multiset and rows are byte-distinct after compact JSON serialization;
- every line-item primitive is exact `int`, finite `float` or `None`; booleans and quoted numeric strings fail;
- source order is retained in member bytes and receipt evidence, but is not interpreted as revision order.

Import and call `_source_bounded_rows_v2(...)` for duplicate-key/non-finite/source-field/credential checks. Do not collapse duplicate economic presentations or compare their numeric equality during acquisition.

The probe manifest canonically records all 13 response byte counts/SHA-256 values and the exact contexts above. Canonical readback, manifest-file SHA-256 and credential exclusion passed. Probe response hashes are evidence of the frozen scope but are not pre-required acquisition hashes; v3 SourceSnapshot identity binds the newly acquired exact bytes.

## 5. Exact field tuples

Reuse PR #2 v2 tuples byte-for-byte:

- `income`: `_INCOME_FIELDS`;
- `balancesheet`: `_BALANCE_FIELDS`;
- `cashflow`: `_CASHFLOW_FIELDS`.

Provider `ebit`, `ebitda` and `free_cashflow` remain advisory raw observations. Null debt/D&A fields remain null until exact official-note declarations exist.

## 6. Exact Tushare member order

```text
response/tushare/balancesheet/000651.SZ-20181231-20190429-v3.json
response/tushare/income/000651.SZ-20191231-20200430-v3.json
response/tushare/balancesheet/000651.SZ-20191231-20200430-v3.json
response/tushare/cashflow/000651.SZ-20191231-20200430-v3.json
response/tushare/income/000651.SZ-20201231-20210429-v3.json
response/tushare/balancesheet/000651.SZ-20201231-20210429-v3.json
response/tushare/cashflow/000651.SZ-20201231-20210429-v3.json
response/tushare/income/000651.SZ-20211231-20220430-v3.json
response/tushare/balancesheet/000651.SZ-20211231-20220430-v3.json
response/tushare/cashflow/000651.SZ-20211231-20220430-v3.json
response/tushare/income/000651.SZ-20221231-20230429-v3.json
response/tushare/balancesheet/000651.SZ-20221231-20230429-v3.json
response/tushare/cashflow/000651.SZ-20221231-20230429-v3.json
```

This order governs network calls and the `provider_requests` receipt array. `SourceSnapshot` retains its existing canonical member-key sorting and remains input-order independent.

## 7. Official CNINFO metadata

Exact endpoint:

```text
https://www.cninfo.com.cn/new/hisAnnouncement/query
```

Exact form fields:

```text
pageNum=1
pageSize=30
column=szse
tabName=fulltext
plate=sz
stock=000651,gssz0000651
searchkey=
secid=
category=category_ndbg_szsh
trade=
seDate=2019-01-01~2023-12-31
sortName=
sortType=
isHLtitle=true
```

`_CNINFO_FORM` is the exact ordered tuple of those 16 `(name, value)` pairs. Exact credential-free headers:

```python
{
  "Accept": "application/json, text/javascript, */*; q=0.01",
  "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
  "Referer": "https://www.cninfo.com.cn/",
  "User-Agent": "Mozilla/5.0",
  "X-Requested-With": "XMLHttpRequest",
}
```

No other header is allowed; case-insensitive names containing `authorization`, `cookie`, `token` or `x-api-key` fail before the callback.

Production `CninfoPost`:

1. exact-requires the endpoint, ordered form tuple and header dictionary;
2. encodes `urllib.parse.urlencode(form).encode("ascii")`;
3. sends stdlib `urllib.request.Request(..., method="POST")` through an opener whose redirect handler rejects every redirect;
4. uses timeout `30` seconds;
5. returns exact `(int_status, bytes_body)` and redacts `HTTPError` bodies from exception text.

Metadata attempts: maximum `3`. Retry only statuses `429, 500, 502, 503, 504` or callback exceptions, sleeping `0.5` then `1.0` seconds. Any other non-`200`, redirect, malformed callback return, sleep failure or exhausted retry maps to `OFFICIAL_METADATA_TRANSPORT_FAILURE`.

Raw response member:

```text
response/cninfo/announcement-query/000651.SZ-2019-2023-annual-reports-v3.json
```

Duplicate-key/non-finite UTF-8 JSON is rejected. Exact envelope keys:

```text
announcements,categoryList,classifiedAnnouncements,hasMore,
totalAnnouncement,totalRecordNum,totalSecurities,totalpages
```

Required envelope types/predicates:

- `announcements` exact list;
- `categoryList` and `classifiedAnnouncements` exact `None`;
- `hasMore` exact `False`;
- `totalAnnouncement`, `totalRecordNum`, `totalSecurities`, `totalpages` exact integers, not booleans;
- `totalAnnouncement == totalRecordNum == len(announcements)`;
- `totalSecurities == 0` and `totalpages >= 0`.

Every announcement is an exact dict with this key set:

```text
id,secCode,secName,orgId,announcementId,announcementTitle,
announcementTime,adjunctUrl,adjunctSize,adjunctType,storageTime,
columnId,pageColumn,announcementType,associateAnnouncement,important,
batchNum,announcementContent,orgName,tileSecName,shortTitle,
announcementTypeName,secNameList
```

Core fields `secCode`, `secName`, `orgId`, `announcementId`, `announcementTitle`, `adjunctUrl`, `adjunctType` are exact strings; `announcementTime` and `adjunctSize` are exact integers, not booleans. Other keys may retain their provider `None`/string/list/integer values and are not authority.

Title normalization removes only balanced literal `<em>` and `</em>` tokens and then rejects any remaining `<` or `>`. For each target year, select records by exact normalized title `{year}年年度报告`, then exact-require one record matching `secCode=000651`, `orgId=gssz0000651`, `adjunctType=PDF` and the frozen ID/time/path below. Zero or multiple matches fail. Summary, English and unrelated records remain raw but are never selected.

The response must contain these exact selected facts:

| Report period | Announcement ID | CNINFO local date | `announcementTime` | `adjunctUrl` |
| --- | --- | --- | ---: | --- |
| `20181231` | `1206125365` | `2019-04-29` | `1556467200000` | `finalpage/2019-04-29/1206125365.PDF` |
| `20191231` | `1207685438` | `2020-04-30` | `1588176000000` | `finalpage/2020-04-30/1207685438.PDF` |
| `20201231` | `1209855305` | `2021-04-29` | `1619625600000` | `finalpage/2021-04-29/1209855305.PDF` |
| `20211231` | `1213262535` | `2022-04-30` | `1651248000000` | `finalpage/2022-04-30/1213262535.PDF` |
| `20221231` | `1216702261` | `2023-04-29` | `1682697600000` | `finalpage/2023-04-29/1216702261.PDF` |

Each selected record must also exact-bind `secCode=000651`, `orgId=gssz0000651`, `adjunctType=PDF` and title `{year}年年度报告` after removing CNINFO highlight tags.

The endpoint's local-midnight millisecond value is retained as raw official metadata but classified as `OFFICIAL_DATE_ONLY`, not an exact publication instant.

An advisory probe produced `8937` bytes / `sha256:3292c3b1bd89f01cb41e09401ad306b6ec8e769cac402317817fe395ff0e918e`; v3 records but does not pre-require that whole-response fingerprint because unrelated annual-report entries may change.

## 8. Official annual-report PDFs

| Period | URL / member ID | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| `20181231` | `https://static.cninfo.com.cn/finalpage/2019-04-29/1206125365.PDF` | `6718851` | `sha256:b147eb6b8a4aaf093f3b83550c70e8526415b5b54fe24e4258ce7bfd11d5406a` |
| `20191231` | `https://static.cninfo.com.cn/finalpage/2020-04-30/1207685438.PDF` | `7535725` | `sha256:1b4869caab122969b322738df69955d788c8dc19b4c6d57188619177e922e708` |
| `20201231` | `https://static.cninfo.com.cn/finalpage/2021-04-29/1209855305.PDF` | `3444361` | `sha256:0d3c39090adf97fede39149a731a5636bd0eca2002606fb942ca70121dba9072` |
| `20211231` | `https://static.cninfo.com.cn/finalpage/2022-04-30/1213262535.PDF` | `4110139` | `sha256:96065ec44285bce7a9c0cbee25dfeb2368ec4552d72f06ebf3ecab35136e2444` |
| `20221231` | `https://static.cninfo.com.cn/finalpage/2023-04-29/1216702261.PDF` | `3765397` | `sha256:7cfc80c2badbf4cd74c5adc080d5072b02cd6c700b04fa7ca0ac44cb8b8fe987` |

`_ANNUAL_REPORT_REQUEST_FACTS` is an exact period-ordered tuple of dictionaries with keys:

```text
period,announcement_id,url,member_key,byte_count,sha256
```

`member_key` is `response/cninfo/annual-report/{announcement_id}.pdf`. Exact host/path, redirect host/path, `%PDF-` prefix, byte count and SHA-256 are required.

`Get` exact-returns `(int_status, bytes_body, str_final_url)`. Production stdlib GET reuses v2's exact CNINFO host/path/redirect confinement and timeout `30`. Maximum `3` attempts; retry only statuses `429, 500, 502, 503, 504` or callback exceptions, sleeping `0.5` then `1.0` seconds. Redirect mismatch, malformed callback return, sleep failure, other non-`200` or exhaustion maps to `OFFICIAL_DOCUMENT_TRANSPORT_FAILURE`; a successful response with wrong PDF prefix/bytes/hash maps to `ANNUAL_REPORT_MISMATCH`.

## 9. Availability boundary

V3 retains official metadata and provider dates but emits no `available_at`.

A later declaration/availability step must:

1. exact-bind each selected CNINFO metadata record to its PDF hash;
2. require Tushare `ann_date`/`f_ann_date` agreement;
3. classify the official evidence as date-only;
4. use an accepted Frozen SZSE Calendar and SessionModel;
5. select the first declared trading-session open strictly after the official date.

Candidate next-session dates, pending accepted Calendar evidence, are:

| Official date | Candidate next session | Candidate UTC open |
| --- | --- | --- |
| `2019-04-29` | `2019-04-30` | `UtcInstant(1556587800000000000)` |
| `2020-04-30` | `2020-05-06` | `UtcInstant(1588728600000000000)` |
| `2021-04-29` | `2021-04-30` | `UtcInstant(1619746200000000000)` |
| `2022-04-30` | `2022-05-05` | `UtcInstant(1651714200000000000)` |
| `2023-04-29` | `2023-05-04` | `UtcInstant(1683163800000000000)` |

These candidates are not acquisition output and are not accepted availability authority.

## 10. Credential and transport boundary

Reuse the approved xiaodefa proxy seam exactly:

- token from environment/caller only, exact 56 non-whitespace characters;
- allowed endpoints `https://fast.xiaodefa.cn`, `https://tt.xiaodefa.cn`;
- credential-free JSON body and `x-api-key` header only;
- no redirects; retry/redaction parity with v2;
- exact network order from section 6;
- no delay before request 1; exact `sleep(0.5)` after each accepted response and before starts 2–13, satisfying ADR 0010's minimum spacing;
- spacing-sleep failure, proxy callback exception/malformed return, retry-sleep failure or invalid member timestamp maps to `PROVIDER_TRANSPORT_FAILURE`.

CNINFO metadata/PDF requests carry the exact credential-free headers frozen above and no token or authorization header. The token must not appear in request facts, paths, source bytes, receipt, exception text or published files.

## 11. Snapshot and receipt

Expected SourceSnapshot members: `19`:

- 13 Tushare responses;
- 1 CNINFO metadata response;
- 5 annual-report PDFs.

Receipt schema/version: `3`. Purpose scope:

```text
cn-a-share.financial-history-source-sentinel.000651.sz.2018-2022.v3
```

Provenance:

```text
vendor_key = tushare.pro-via-xiaodefa-cninfo.com.cn
source_key = cn_a_share.financial_history_source_sentinel.000651.sz.2018-2022.v3.proxy
license_ref = tushare.pro.terms-cninfo.public-disclosure
retention_policy_ref = backtest.acquisition.candidate
```

`time_ns()` is called exactly `19` times, immediately after each accepted source response in network order: 13 provider, 1 metadata, 5 PDF. Each return must be exact nonnegative `int`, not `bool`. Receipt `acquired_at_epoch_nanoseconds` is the maximum of those member timestamps.

Exact receipt top-level keys/body:

```python
{
  "type": "tushare_cn_a_share_financial_history_sentinel_acquisition_receipt",
  "schema_version": 3,
  "request": request.to_canonical_dict(),
  "transport_proxy_key": "xiaodefa.approved-tushare-proxy.v1",
  "transport_endpoint": endpoint,
  "provider_requests": provider_requests,
  "official_metadata": official_metadata,
  "official_documents": official_documents,
  "acquired_at_epoch_nanoseconds": max(received_at.values()),
  "snapshot": snapshot.to_canonical_dict(),
  "limitations": list(_LIMITATIONS),
  "provider_revision_id": None,
  "revision_closure_complete": False,
  "decision_grade_eligible": False,
  "deployment_authorized": False,
}
```

Each ordered `provider_requests` item exact-contains:

```text
api_name,params,fields,auth_mode,member_key,attempts,
response_received_at_epoch_nanoseconds,response_byte_count,response_sha256,
observed_envelope,item_cardinality,contexts,update_flags,
declared_sha256,provider_revision_id
```

`auth_mode="x-api-key"`; `observed_envelope={"has_more":False,"count":0}`; `declared_sha256=None`; `provider_revision_id=None`.

`official_metadata` exact-contains endpoint, ordered form, exact headers, member key, attempts, response timestamp/bytes/hash, envelope summary, ordered five selected records and `declared_sha256=None`.

Each ordered `official_documents` item exact-contains period, requested URL, final URL, member key, attempts, response timestamp/bytes/hash and the equal frozen `declared_sha256`.

Persist exactly the 19 raw members plus `acquisition-receipt.json`; no probe manifest or 2023 bytes are copied into the output. PDF members use their frozen declared SHA-256; provider and metadata members use `declared_sha256=None`.

### Private v3 atomic publication

Do not call shared `publish_directory`. V3 owns this exact same-filesystem algorithm:

1. `_require_safe_output(final_dir)` exact-requires a fresh final path;
2. staging sibling is `final_dir.parent / f".{final_dir.name}.staging-v3"` and must also be absent;
3. create staging root mode `0700`;
4. write all 19 members, then receipt last, each through exclusive create, file mode `0600`, flush and `os.fsync(file_fd)`;
5. reopen every staged file and exact-compare bytes/hash; rebuild and verify SourceSnapshot from staged members;
6. `os.fsync(staging_dir_fd)`;
7. `os.replace(staging_dir, final_dir)` while final remains absent;
8. `os.fsync(parent_dir_fd)`;
9. on any exception before rename, recursively remove staging and leave final absent; after successful rename, return the receipt.

Tests must pause before rename and prove the final directory is invisible. Cleanup-on-error alone is not called atomic.

## 12. Failure precedence

| Priority | Condition | Code |
| ---: | --- | --- |
| 1 | request/callable/endpoint/output exact mismatch | `INPUT_MISMATCH` |
| 2 | credential type/length/path conflict | `CREDENTIAL_INPUT_INVALID` |
| 3 | unsafe or existing output | existing path/publication failure |
| 4 | proxy transport exhaustion | `PROVIDER_TRANSPORT_FAILURE` |
| 5 | provider JSON/envelope invalid | `PROVIDER_RESPONSE_INVALID` |
| 6 | provider exact field tuple mismatch | `PROVIDER_FIELDS_MISMATCH` |
| 7 | provider issuer/period/date/type/company/count/flag scope mismatch | `FINANCIAL_ROW_SCOPE_MISMATCH` |
| 8 | token found in any in-memory source/evidence | `CREDENTIAL_LEAK_DETECTED` |
| 9 | CNINFO metadata transport exhaustion | `OFFICIAL_METADATA_TRANSPORT_FAILURE` |
| 10 | metadata JSON/query/selected record mismatch | `OFFICIAL_METADATA_INVALID` |
| 11 | annual-report URL/redirect/bytes/hash mismatch | `ANNUAL_REPORT_MISMATCH` |
| 12 | SourceSnapshot freeze/verify failure | exact `SourceSnapshotFailureCode` |
| 13 | staging/write/readback/fsync/rename failure | `PUBLICATION_FAILURE` |

This is an exact **stage-local fail-fast** control flow, not a collect-all global ranking:

1. run input, credential and final/staging-path preflight once;
2. for each of the 13 provider requests in frozen order: pacing → transport → envelope → fields → row scope → credential scan → member timestamp; stop on first failure;
3. run metadata: transport → envelope/record selection → credential scan → member timestamp; stop on first failure;
4. for each of five PDFs in frozen order: transport/redirect → credential scan → PDF bytes/hash → member timestamp; stop on first failure;
5. freeze/verify snapshot → construct receipt → stage/readback/rename publication.

Provider spacing/retry/time callback failures map to `PROVIDER_TRANSPORT_FAILURE`; metadata equivalents map to `OFFICIAL_METADATA_TRANSPORT_FAILURE`; PDF equivalents map to `OFFICIAL_DOCUMENT_TRANSPORT_FAILURE`. Collaborator return types are exact-validated before use. The frozen request order is part of receipt identity, so no input-order noninterference claim is made for network execution.

One failure publishes no smaller period subset and no receipt.

## 13. Required limitations

The receipt must state:

- source-bounded finite capture only;
- existing 2023 SourceSnapshot is separate and unmodified;
- CNINFO metadata timestamp is date-only authority;
- no accepted Trading Calendar or `available_at` result;
- no official statement-unit, debt, D&A or revision-closure declarations;
- provider `update_flag` does not prove finality or supersession;
- no normalized revisions, selected trios, formulas or five-year feature manifest;
- no full-market, audit-opinion, penalty, pledge, Universe or corporate-action coverage;
- no decision-grade, Validation, Live or deployment authority.

## 14. Exact implementation write set

Create one Backtest worktree/branch stacked on PR #5 and change only:

- `tools/acquisition/cn_a_share_tushare_financial_history_sentinel_v3.py`;
- `tests/tools/acquisition/test_cn_a_share_tushare_financial_history_sentinel_v3.py`;
- `tests/architecture/test_g12a_tushare_financial_history_sentinel_v3_boundary.py`.

No package-root export and no dependency/lock change. PRs #1–#5 files remain byte-identical.

The architecture test obtains every tracked path from `git ls-tree -r --name-only 5338d8046fa0f304d4a9590989c59ceffb51270b`, requires each path still exists, and exact-compares current bytes with `git show BASE:path`. It then requires `git diff --name-only BASE..HEAD` plus worktree status to contain only, and collectively exactly, the three allowed v3 paths.

## 15. Acceptance

1. exact 19-member synthetic SourceSnapshot and receipt-last atomic publication;
2. exact 13 provider request bodies, field tuples, row contexts/counts/flag multisets;
3. exact CNINFO form POST and five selected official metadata records;
4. exact five PDF URL/redirect/byte/hash identities;
5. token/path/transport/JSON/field/row/metadata/document precedence and redaction;
6. one-period failure leaves no smaller output;
7. persisted reopen/verify and input-order determinism;
8. existing 2023 snapshot and PRs #1–#5 protected bytes unchanged;
9. no declaration/availability/normalization/selection/formula/Bundle output;
10. focused plus opt-in real capture, adjacent acquisition/SourceSnapshot and broad regression;
11. independent review before commit/push;
12. real publication only to a fresh approved candidate directory.

## 16. CLI and validation commands

CLI matches v2:

```text
--endpoint {https://fast.xiaodefa.cn,https://tt.xiaodefa.cn}
--output-dir PATH
```

Credential comes only from `TUSHARE_PROXY_TOKEN`; there is no token argument. `main()` uses the stdlib proxy/CNINFO/PDF collaborators, prints only sorted receipt JSON on success, and raises redacted `SystemExit("acquisition failed: <CODE>")` on failure.

Focused:

```bash
uv run --locked pytest -q \
  tests/tools/acquisition/test_cn_a_share_tushare_financial_history_sentinel_v3.py \
  tests/architecture/test_g12a_tushare_financial_history_sentinel_v3_boundary.py
```

Adjacent:

```bash
uv run --locked pytest -q \
  tests/tools/acquisition \
  tests/bundle_builder/source_snapshots \
  tests/architecture/test_g12a_tushare_financial_history_sentinel_v3_boundary.py
```

Before broad regression in the sibling worktree, temporarily expose the Platform consumer fixture:

```bash
parent_tests="$(dirname "$PWD")/tests"
test ! -e "$parent_tests"
mkdir -p "$parent_tests"
ln -s "$(dirname "$PWD")/platform/tests/contracts" "$parent_tests/contracts"
cleanup() { rm -f "$parent_tests/contracts"; rmdir "$parent_tests" 2>/dev/null || true; }
trap cleanup EXIT
```

After the candidate commit, run:

```bash
uv run --locked pytest -q \
  --deselect tests/architecture/test_gree_2023_financial_document_declarations_v1_boundary.py::test_declaration_candidate_write_set_is_exact \
  --deselect tests/architecture/test_gree_2023_financial_statement_normalization_v1_boundary.py::test_normalization_candidate_write_set_is_exact \
  --deselect tests/architecture/test_gree_2023_financial_statement_trio_selection_v1_boundary.py::test_selection_candidate_write_set_is_exact
```

No broad `-k` exclusion. The v3 architecture test must compare every path from base commit `5338d8046fa0f304d4a9590989c59ceffb51270b` byte-for-byte and require that only the three allowed new paths exist in `git diff BASE..HEAD` plus worktree status.

Validation ownership/order:

1. writer: focused tests, opt-in synthetic collaborator tests, LSP/lens, `git diff --check`;
2. fresh read-only reviewer: spec/security/atomicity review before commit;
3. orchestrator: candidate commit, adjacent and broad commands in a clean worktree;
4. orchestrator: push and stacked PR creation;
5. orchestrator only, after prior gates pass: real capture to the fresh approved directory below;
6. orchestrator: persisted SourceSnapshot reopen/verify, exact member count, file modes, receipt identities and credential-exclusion scan.

Real capture:

```bash
cd /home/ygguo/agent-projs/ai-crypt/backtest-qb-fin-history
TUSHARE_PROXY_TOKEN="$(< /home/ygguo/.config/ai-crypt/xiaodefa-token)" \
uv run --locked python -m tools.acquisition.cn_a_share_tushare_financial_history_sentinel_v3 \
  --endpoint https://fast.xiaodefa.cn \
  --output-dir /srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/source-snapshots/000651.SZ/2018-2022/v3-candidate-01
```

The output directory must not exist before execution. Never echo, trace or persist the environment value.

## 17. Next handoff

After v3 source publication:

1. audit statement units and financing/D&A notes for 2018–2022;
2. freeze period-specific official metadata/unit/note declarations;
3. normalize the 2018 balance and 2019–2022 trios without changing 2023 identities;
4. run point-in-time selection for 2019–2022;
5. bind five annual selections plus six balance endpoints in a separate formula-feature manifest.
