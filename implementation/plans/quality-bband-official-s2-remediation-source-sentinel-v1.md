# QB-S2-OFFICIAL-SRC-01 — eight-issuer official S2 remediation source sentinel v1

- **Status:** `IMPLEMENTATION_PACKET_FROZEN / USER_APPROVED / SOURCE_ONLY / PLAN_ONLY`
- **Owner:** Backtest acquisition tooling
- **Implementation base:** `33f7320bd3f1e81c6a985f2fdeea39aedb7bc01e`
- **Purpose:** retain the one official FY2014 filing and fourteen official non-filing/terminal documents needed by QB-S2-NONFILE-01
- **Authority snapshot:** Platform commit `8974f7d`, packet SHA-256 `29a18e4af2108598d2876f410a61efbeef6f7f850251b343a14adcfd80994d72`

## 1. Exact write set

1. `tools/acquisition/cn_a_share_official_s2_remediation_source_bounded_v1.py`
2. `tests/tools/acquisition/test_cn_a_share_official_s2_remediation_source_bounded_v1.py`
3. `tests/architecture/test_g12a_official_s2_remediation_source_bounded_v1_boundary.py`

All predecessor bytes remain unchanged.

## 2. Network boundary

No credential or provider token is read. Allowed network calls are exactly:

- six POSTs to `https://www.cninfo.com.cn/new/hisAnnouncement/query`;
- fifteen GETs to the exact HTTPS PDF URLs in section 4.

No redirect, endpoint failover, cookies, browser automation or alternate mirror is allowed. The injected test seams are:

```text
Post(url, ordered_form, ordered_headers) -> (status, response_headers, raw_bytes, final_url)
Get(url, ordered_headers) -> (status, response_headers, raw_bytes, final_url)
Sleep(seconds)
Clock() -> epoch_nanoseconds
```

The production adapters own transport buffering. They validate `Content-Length` when present, reject invalid/negative/over-ceiling lengths before reading, and read at most the remaining logical ceiling plus one byte. The extra byte proves overflow without unbounded buffering. Test seams may return bytes directly; the acquisition function applies the same semantic ceiling check.

Production uses stdlib `urllib`, a local `_NoRedirect` and exact URL allowlists. HTTP 429/500/502/503/504 and transport errors retry at most three attempts with deterministic delays `(1.0, 2.0)` seconds; other statuses fail immediately. Retry attempts do not change logical request order.

## 3. Metadata POSTs

Form key order is exact:

```text
pageNum, pageSize, column, tabName, plate, stock, searchkey, secid,
category, trade, seDate, sortName, sortType, isHLtitle
```

Fixed values are `pageNum=1`, `pageSize=30`, `tabName=fulltext`, `secid=""`, `trade=""`, `sortName=""`, `sortType=""`, `isHLtitle=true`.

Exact requests and retained member keys:

| Key | column/plate | stock/searchkey | category | seDate | selected IDs | expected total |
|---|---|---|---|---|---|---:|
| `000046` | `szse/sz` | `000046,gssz0000046` / empty | `category_ndbg_szsh` | `2015-01-01~2015-12-31` | `1200788303` | 2 |
| `000693` | `szse/sz` | `000693,gssz0000693` / empty | empty | `2019-04-25~2019-05-20` | `1206163240`, `1206283352` | 4 |
| `000038` | `szse/sz` | `000038,gssz0000038` / empty | empty | `2023-04-25~2023-06-15` | `1216782869`, `1217029890` | 7 |
| `000976-initial` | `szse/sz` | `000976,gssz0000976` / empty | empty | `2024-05-01~2024-05-31` | `1220037786` | 14 |
| `000976-terminal` | `szse/sz` | `000976,gssz0000976` / empty | empty | `2024-08-20~2024-08-30` | `1220964685` | 4 |
| `000622` | `szse/sz` | `000622,gssz0000622` / empty | empty | `2025-04-20~2025-06-25` | `1223449834`, `1223910946` | 18 |
| `601028` | `sse/sh` | empty / `玉龙股份` | empty | `2025-04-20~2025-05-31` | `1223364517`, `1223607424` | 14 |

Member keys are:

```text
response/cninfo/announcement-query/{key}-v1.json
```

Metadata response object keys are exact:

```text
classifiedAnnouncements, totalSecurities, totalAnnouncement, totalRecordNum,
announcements, categoryList, hasMore, totalpages
```

`totalAnnouncement == totalRecordNum == expected total == len(announcements)`, `hasMore=false`, and `totalpages=0`. Every selected ID must occur exactly once. Title normalization removes only literal `<em>` and `</em>` markers before comparison; raw bytes remain unchanged. Other returned records are retained source extras and counted. Zero/missing/duplicate selected records fail.

Selected facts are exact:

| ID | title | epoch ms | adjunct URL |
|---|---|---:|---|
| `1200788303` | `2014年年度报告` | 1428076800000 | `finalpage/2015-04-04/1200788303.PDF` |
| `1206163240` | `关于无法在法定期限内披露2018年年度报告及公司股票可能被终止上市的风险提示公告` | 1556553600000 | `finalpage/2019-04-30/1206163240.PDF` |
| `1206283352` | `关于公司股票终止上市的公告` | 1558108800000 | `finalpage/2019-05-18/1206283352.PDF` |
| `1216782869` | `关于收到深圳证券交易所《事先告知书》暨公司股票可能被终止上市的风险提示性公告` | 1683648000000 | `finalpage/2023-05-10/1216782869.PDF` |
| `1217029890` | `关于收到股票终止上市决定的公告` | 1686326400000 | `finalpage/2023-06-10/1217029890.PDF` |
| `1220037786` | `关于公司股票交易被叠加实施其他风险警示的公告` | 1715502229000 | `finalpage/2024-05-12/1220037786.PDF` |
| `1220964685` | `关于公司未在规定期限内披露定期报告的风险提示公告` | 1724428800000 | `finalpage/2024-08-24/1220964685.PDF` |
| `1223449834` | `关于无法在法定期限内披露定期报告致股票可能被终止上市暨停牌的风险提示公告` | 1746460800000 | `finalpage/2025-05-06/1223449834.pdf` |
| `1223910946` | `关于收到股票终止上市决定的公告` | 1750262400000 | `finalpage/2025-06-19/1223910946.PDF` |
| `1223364517` | `关于无法在法定期限内披露2024年年度报告及2025年第一季度报告的公告` | 1745856000000 | `finalpage/2025-04-29/1223364517.PDF` |
| `1223607424` | `关于股票终止上市暨摘牌的公告` | 1747756800000 | `finalpage/2025-05-21/1223607424.PDF` |

## 4. Official PDF members

| Member key | Exact URL | Bytes | SHA-256 |
|---|---|---:|---|
| `response/official/000046/1200788303.pdf` | `https://static.cninfo.com.cn/finalpage/2015-04-04/1200788303.PDF` | 4,164,254 | `sha256:0a5bce6a608fcc444d5405c29e81428efe349370c6d8cc4ba72dca26272bec1c` |
| `response/official/000693/1206163240.pdf` | `https://static.cninfo.com.cn/finalpage/2019-04-30/1206163240.PDF` | 250,606 | `sha256:6578ea31d44ca91fc596ce72c27e66953bd90e2c4bbda77b927957e4f1c1e7b5` |
| `response/official/000693/1206283352.pdf` | `https://static.cninfo.com.cn/finalpage/2019-05-18/1206283352.PDF` | 238,020 | `sha256:7f83246f3b971d2f0eaf7c3abb2548005e0126b2b351a7660142195add46e5f6` |
| `response/official/600090/a38770503b904cf88f85ebe52a75ad36.pdf` | `https://www.sse.com.cn/disclosure/credibility/supervision/inquiries/enquiry/c/10111560/files/a38770503b904cf88f85ebe52a75ad36.pdf` | 125,353 | `sha256:cdcdb05206c914e643eb39abc12aaf435b6763d332557c36fda986ce4e699ffe` |
| `response/official/600090/16e8ccc4577d410891dfba7e2a691af0.pdf` | `https://www.sse.com.cn/disclosure/credibility/supervision/measures/focus/c/10107770/files/16e8ccc4577d410891dfba7e2a691af0.pdf` | 349,016 | `sha256:f2bcc3e0b18aa974c1b52922d96d30d507ca82826c042fc64c662ae8fa74686d` |
| `response/official/600146/514dd89bf3c24c4a95afb42c4aa7cfba.pdf` | `https://www.sse.com.cn/disclosure/credibility/supervision/inquiries/enquiry/c/10111562/files/514dd89bf3c24c4a95afb42c4aa7cfba.pdf` | 129,449 | `sha256:7d7a6cc76001b950075f8a4bfcd4c1477f9fe998ffb05d8834ef72ccfca09c73` |
| `response/official/600146/8f60b5e2db23462e84d9ef368cb683ac.pdf` | `https://www.sse.com.cn/disclosure/credibility/supervision/measures/focus/c/10107748/files/8f60b5e2db23462e84d9ef368cb683ac.pdf` | 341,493 | `sha256:7a14ec4babb3ae73211bb7a0cb775ae010563071c454c56df34a9f97b6bdb5fa` |
| `response/official/000038/1216782869.pdf` | `https://static.cninfo.com.cn/finalpage/2023-05-10/1216782869.PDF` | 91,169 | `sha256:3cdd32ebbf332aa65a344ab1163c453a9329cbc165d807e182a210b14da62db6` |
| `response/official/000038/1217029890.pdf` | `https://static.cninfo.com.cn/finalpage/2023-06-10/1217029890.PDF` | 107,944 | `sha256:6167f546f845c8d5cf52cc20874387b3e7072cb5e8fb44950a10cb7f4068ff6f` |
| `response/official/000976/1220037786.pdf` | `https://static.cninfo.com.cn/finalpage/2024-05-12/1220037786.PDF` | 204,419 | `sha256:dc9a031017f6a610084814bf953e2fbdc84623dbf56a9c5e61abb8da4bc7c833` |
| `response/official/000976/1220964685.pdf` | `https://static.cninfo.com.cn/finalpage/2024-08-24/1220964685.PDF` | 155,897 | `sha256:94849b146f85130caf0a839a1819318d5ea308029027aef79d823cf95e272839` |
| `response/official/000622/1223449834.pdf` | `https://static.cninfo.com.cn/finalpage/2025-05-06/1223449834.pdf` | 75,386 | `sha256:2b6b64ab65162384089c9dfa3155c56ceda4f4694e9f755d50f7f3a4241a8747` |
| `response/official/000622/1223910946.pdf` | `https://static.cninfo.com.cn/finalpage/2025-06-19/1223910946.PDF` | 412,757 | `sha256:6d428f36a27ec29a21953dfef08dca180fc1b6194e92df7964c1e08ab938a2fa` |
| `response/official/601028/1223364517.pdf` | `https://static.cninfo.com.cn/finalpage/2025-04-29/1223364517.PDF` | 70,480 | `sha256:a25fda7dca2204bb9929188f47428edfde884233431ab62680e75f537ee56d1d` |
| `response/official/601028/1223607424.pdf` | `https://static.cninfo.com.cn/finalpage/2025-05-21/1223607424.PDF` | 96,288 | `sha256:627c57066b5b494b35f571150b26e91faafd03b44bd574506e70a65bddf59c75` |

Every GET requires status 200, unchanged final URL, `application/pdf`, `%PDF-` magic, exact byte count and exact SHA-256. Any remote byte change fails atomically and requires a new version/candidate; no hash update is automatic.

## 5. Request order and ceilings

Order is exact:

1. seven metadata POSTs in table order;
2. fifteen PDF GETs in table order.

Ceilings:

```text
MAX_LOGICAL_REQUESTS = 22
MAX_METADATA_MEMBER_BYTES = 1 MiB
MAX_PDF_MEMBER_BYTES = 8 MiB
MAX_TOTAL_BYTES = 32 MiB
```

The request ceiling is checked before transport; byte ceilings run immediately after transport and before parsing/retention. The tool reads no environment credential and sends only frozen public HTTP headers; receipt headers are an exact allowlisted public subset.

## 6. SourceSnapshot

All 22 raw members enter one SourceSnapshot with logical mode `0644` and immediate post-transport acquisition timestamp. The receipt preserves logical request order; `freeze_source_snapshot` canonical member-key order is authoritative for SourceSnapshot identity. Provenance is exact:

```text
vendor_key = "cninfo.com.cn-sse.com.cn"
source_key = "official.s2-remediation.000046-000693-600090-600146-000038-000976-000622-601028.v1"
license_ref = "official.public-disclosure"
retention_policy_ref = "backtest.acquisition.candidate"
```

The tool reconstructs and verifies the SourceSnapshot before publication.

## 7. Receipt and output

Output contains exactly 24 regular files, all disk mode `0600`:

```text
7 metadata JSON
15 PDF members
source-snapshot.json
acquisition-receipt.json
```

Receipt schema is exact:

```text
type = "official_s2_remediation_source_receipt"
schema_version = 1
capture_key = "20260826-official-s2-remediation-candidate-01"
acquired_at_epoch_nanoseconds
logical_requests
selected_metadata_facts
metadata_extra_record_count
snapshot
limitations
false flags
```

Each `logical_requests` entry records zero-based logical index, request kind/key, exact ordered form or URL, attempts, status, final URL, allowlisted response headers, content hash/size and immediate response timestamp. `selected_metadata_facts` follows selected-ID order from section 3. `limitations` is the exact tuple:

```text
SOURCE_BOUNDED_ONLY
OFFICIAL_EVIDENCE_NOT_REVIEWED_BY_BUILDER
NONFILING_DECLARATIONS_NOT_CONSTRUCTED
FINANCIAL_STATEMENT_NOT_EXTRACTED
FINANCIAL_AVAILABILITY_NOT_QUALIFIED
REVISION_CLOSURE_INCOMPLETE
S1_AUTHORITY_MISSING
S2B_EXACT_COVER_FALSE
DECISION_GRADE_FALSE
DEPLOYMENT_AUTHORIZED_FALSE
```

Exact false flags:

```text
official_evidence_reviewed
nonfiling_declarations_constructed
financial_statement_extracted
financial_payload_complete
financial_availability_qualified
revision_closure_complete
s2b_exact_cover_complete
decision_grade_eligible
deployment_authorized
```

All are false. Publication uses `_common.publish_directory`; every failure leaves no output directory.

## 8. Symbols

```text
MetadataRequest
PdfRequest
_METADATA_REQUESTS
_PDF_REQUESTS
_NoRedirect
_require_safe_output(output_dir: Path) -> Path
_post_with_retries(...)
_get_with_retries(...)
_read_bounded(response, member_limit, total_remaining) -> bytes
_parse_metadata(...)
_validate_pdf(...)
acquire_official_s2_remediation_source_v1(*, output_dir: Path, post: Post, get: Get, sleep: Sleep, clock: Clock) -> dict[str, object]
_build_output(...)
_parse_args()
main()
```

Public request headers are exact ordered tuples.

CNINFO POST/PDF:

```text
Accept: application/json, text/javascript, */*; q=0.01   # POST only
Accept: application/pdf,*/*                              # PDF GET only
Content-Type: application/x-www-form-urlencoded; charset=UTF-8  # POST only
Referer: https://www.cninfo.com.cn/
User-Agent: Mozilla/5.0
X-Requested-With: XMLHttpRequest                         # POST only
```

SSE PDF GET:

```text
Accept: application/pdf,*/*
Referer: https://www.sse.com.cn/
User-Agent: Mozilla/5.0
```

Only `Content-Type` and valid `Content-Length`, when present, are retained from response headers. Reuse `_common.publish_directory` and SourceSnapshot types/functions. `_NoRedirect` and safe-output preflight are local to the new module. Do not import private handlers, Tushare proxy/token helpers, financial normalization, PDF text extraction or declaration construction.

## 9. Tests

Unit tests independently freeze literal ordered forms/headers, envelope keys, totals, IDs, normalized titles/dates/adjunct URLs, PDF URLs/bytes/hashes, order, ceilings, provenance, receipt schema/limitations/false flags and 24-file layout. Cover:

- byte-identical successful fixture publication and snapshot reconstruction;
- metadata extras retained/counted but never selected;
- missing/duplicate selected IDs and `hasMore=true`;
- redirect, host/path/final-URL, content-type, PDF magic, size/hash failure;
- retry precedence and request/byte ceilings;
- rejection of unexpected request/receipt headers and any credential-environment access;
- output collision/symlink/nonregular/atomic cleanup;
- no declaration, statement extraction, Strategy or deployment output.

Architecture guard freezes the exact three-file diff and predecessor hashes, forbids writes outside output, network dependencies outside stdlib, credential reads, Tushare endpoints, Stage/Strategy/Target/Execution/Promotion construction and changes to accepted predecessor modules.

## 10. Nonclaims

This source candidate does not prove the reviewed excerpts, declaration eligibility, availability, terminal confirmation, statement mapping, S1/S2B closure or Strategy authority. In particular, `601028.SH` terminal-delisting bytes do not automatically prove continued non-filing; declaration construction must independently reject insufficient evidence.
