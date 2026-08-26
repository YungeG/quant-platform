# QB-S2-OFFICIAL-SRC-SUP-01 — non-filing effective-boundary source supplement v1

- **Status:** `IMPLEMENTATION_PACKET_FROZEN / USER_APPROVED / SOURCE_ONLY / PLAN_ONLY`
- **Backtest base:** PR #13 commit `7276c69`
- **Purpose:** retain the missing pre/deadline non-filing proofs for `000038.SZ` and `000976.SZ`, plus the later NEEQ sponsor terminal confirmation for `601028.SH`

## 1. Exact write set

1. `tools/acquisition/cn_a_share_official_s2_remediation_supplement_source_bounded_v1.py`
2. `tests/tools/acquisition/test_cn_a_share_official_s2_remediation_supplement_source_bounded_v1.py`
3. `tests/architecture/test_g12a_official_s2_remediation_supplement_source_bounded_v1_boundary.py`

All PR #13 predecessor bytes remain unchanged.

## 2. Exact requests

Logical order:

1. CNINFO POST `000038-predeadline`;
2. CNINFO POST `000976-predeadline`;
3. NEEQ disclosure JSON GET;
4. `000038` PDF GET;
5. `000976` PDF GET;
6. `601028` NEEQ sponsor PDF GET.

No credentials, proxy environment, redirects, cookies or endpoint fallback.

### CNINFO forms

Reuse PR #13 exact endpoint, ordered form keys and public POST headers with `pageNum=1`, `pageSize=30`.

| key | stock | seDate | expected total | selected ID |
|---|---|---|---:|---|
| `000038-predeadline` | `000038,gssz0000038` | `2023-04-25~2023-04-30` | 3 | `1216706117` |
| `000976-predeadline` | `000976,gssz0000976` | `2024-04-20~2024-04-30` | 10 | `1219960138` |

Both use `column=szse`, `plate=sz`, empty category/searchkey and retain all extras.

Selected facts:

| ID | title | epoch ms | adjunct URL |
|---|---|---:|---|
| `1216706117` | `关于无法在法定期限内披露定期报告致股票可能被终止上市暨停牌的风险提示公告` | 1682701857000 | `finalpage/2023-04-29/1216706117.PDF` |
| `1219960138` | `关于无法在法定期限内披露定期报告暨股票停牌的公告` | 1714474662000 | `finalpage/2024-04-30/1219960138.PDF` |

Member keys:

```text
response/cninfo/announcement-query/000038-predeadline-v1.json
response/cninfo/announcement-query/000976-predeadline-v1.json
```

Envelope/type/title-normalization rules equal PR #13. `hasMore=false`, `totalpages=0`, totals exact.

### NEEQ JSON

Exact GET:

```text
https://neeq.cs.com.cn/xsb/v1/xsb_search/&gs=R%E9%91%AB%E5%8D%871&st=2026-04-01&ed=2026-05-10&1.json
```

Headers:

```text
Accept: application/json,*/*
Referer: https://neeq.cs.com.cn/
User-Agent: Mozilla/5.0
```

Member:

```text
response/neeq/disclosure-search/400267-202604-v1.json
```

Exact envelope:

```text
outer: code=0, errorMessage=null, data
inner: code=0, errorMessage=null, data, currentPage=1, size=30, total=27
```

Selected row occurs exactly once:

```text
seccode = 400267
secname = R鑫升1
f001d = 2026-04-29T00:00:00.000+00:00
f002v = [券商公告]R鑫升1:中泰证券股份有限公司关于山东鑫升矿业股份有限公司无法披露2025年年度报告的风险提示性公告
f003v = http://dataclouds.cninfo.com.cn/sjother2/neeqs/2026/20260429/5e69266176024a6dae6eb9392c5e22b5.pdf
f004v = PDF
```

All 26 other rows are retained extras. Response change fails; no pagination inference.

## 3. Exact PDFs

| Member | HTTPS URL | Bytes | SHA-256 |
|---|---|---:|---|
| `response/official/000038/1216706117.pdf` | `https://static.cninfo.com.cn/finalpage/2023-04-29/1216706117.PDF` | 132,535 | `sha256:221bbba784c88dbe6deec97085033de38419fa78f5d6a9b08c2fa2f13bb55bab` |
| `response/official/000976/1219960138.pdf` | `https://static.cninfo.com.cn/finalpage/2024-04-30/1219960138.PDF` | 202,749 | `sha256:e57fa6e99f452b8e1eb59f0be39b44cfebbfc7775dd050f1050d754b190d1aec` |
| `response/official/601028/5e69266176024a6dae6eb9392c5e22b5.pdf` | `https://dataclouds.cninfo.com.cn/sjother2/neeqs/2026/20260429/5e69266176024a6dae6eb9392c5e22b5.pdf` | 124,766 | `sha256:a00a87a6b4e96e93c04d02bc3816fbe9b0488744fca65a53d3603bf509eaa464` |

Every PDF requires status 200, exact final URL, `application/pdf`, `%PDF-`, byte count and hash.

## 4. Transport and ceilings

Reuse from PR #13:

```text
_NoRedirect
_read_bounded
_require_safe_output
```

Production explicitly disables proxies with `ProxyHandler({})`. New URL allowlists are exact. Bounded reads precheck valid Content-Length and read at most ceiling+1.

```text
MAX_LOGICAL_REQUESTS = 6
MAX_METADATA_MEMBER_BYTES = 1 MiB
MAX_PDF_MEMBER_BYTES = 1 MiB
MAX_TOTAL_BYTES = 4 MiB
```

Retry statuses/delays equal PR #13; changed final URL fails before retry.

## 5. SourceSnapshot

Six raw members enter one canonical SourceSnapshot. Receipt preserves logical order; SourceSnapshot uses canonical member-key order.

Provenance:

```text
vendor_key = "cninfo.com.cn-neeq.cs.com.cn"
source_key = "official.s2-remediation.nonfiling-effective-boundary-supplement.v1"
license_ref = "official.public-disclosure"
retention_policy_ref = "backtest.acquisition.candidate"
```

Output has exactly eight regular files, all disk mode `0600`: six raw members plus snapshot and receipt.

## 6. Receipt

```text
type = "official_s2_remediation_supplement_source_receipt"
schema_version = 1
capture_key = "20260826-official-s2-remediation-supplement-candidate-01"
logical_requests
selected_cninfo_facts
selected_neeq_fact
metadata_extra_record_count = 37
snapshot
limitations
false flags
```

Limitations:

```text
SOURCE_BOUNDED_ONLY
OFFICIAL_EVIDENCE_NOT_REVIEWED_BY_BUILDER
NONFILING_DECLARATIONS_NOT_CONSTRUCTED
FINANCIAL_AVAILABILITY_NOT_QUALIFIED
REVISION_CLOSURE_INCOMPLETE
S2B_EXACT_COVER_FALSE
DECISION_GRADE_FALSE
DEPLOYMENT_AUTHORIZED_FALSE
```

All qualification/declaration/S2B/grade/deployment flags are false.

## 7. Symbols and tests

Production symbols:

```text
MetadataRequest
PdfRequest
_NoRedirect imported from predecessor
_METADATA_REQUESTS
_PDF_REQUESTS
_NEEQ_REQUEST
_parse_cninfo_metadata
_parse_neeq_metadata
acquire_official_s2_remediation_supplement_source_v1
_build_output
_parse_args
main
```

Exact injected signature mirrors PR #13 with Post/Get/Sleep/Clock. Reuse only accepted predecessor transport/safety helpers; no token/Tushare/provider-normalization/declaration imports.

Tests independently freeze forms, URLs, selected facts, totals/extras, PDF hashes, order, ceilings, provenance, receipt, eight-file layout, retries, redirect/proxy/security, bounded reads, snapshot reconstruction and atomic failures. Architecture guard freezes exact three-file write set and predecessor hashes.

## 8. Nonclaims

This supplement supplies source bytes only. It does not classify natural language, construct evidence/declarations, backdate availability, qualify S1/S2, authorize S2B or create Strategy/Target/execution authority.
