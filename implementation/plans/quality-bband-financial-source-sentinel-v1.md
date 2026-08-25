# QB-FIN-SENTINEL-01 — Tushare + CNINFO financial source sentinel v1

- **Status:** `PR_OPEN / NOT_MERGED / NOT_ACCEPTED`
- **Owner:** Backtest G12A acquisition
- **Purpose:** prove one source-bounded raw financial capture; **not** prove Strategy data readiness
- **Source assessment:** [`research/quality-bband-financial-governance-source-matrix.md`](../../research/quality-bband-financial-governance-source-matrix.md)
- **Parent contract:** [`quality-bband-data-contract-v1.md`](quality-bband-data-contract-v1.md)

## 1. Outcome

Capture and freeze exactly one non-financial A-share issuer, one annual report period, three Tushare raw financial-statement responses and one CNINFO official annual-report PDF as a verified `SourceSnapshot`.

This sentinel answers only:

> Can G12A capture exact provider bytes, identities and declared limitations for one known financial disclosure without leaking a token or fabricating revision/availability closure?

It does not publish a MarketBundle, calculate a quality factor, enable a portfolio Backtest, establish a five-year history, prove all revisions are final or claim that no correction exists.

## 2. Exact source declaration

| Value | Frozen value |
| --- | --- |
| Issuer | 珠海格力电器股份有限公司 |
| Provider security code | `000651.SZ` |
| Platform Instrument candidate | `xshe:000651` |
| Issuer class | ordinary non-financial industrial issuer |
| Report period | `20231231` |
| Known disclosure date | `20240430` |
| Tushare APIs | `income`, `balancesheet`, `cashflow` |
| CNINFO report URL | `http://static.cninfo.com.cn/finalpage/2024-04-30/1219928418.PDF` |
| CNINFO PDF bytes | `3911496` |
| CNINFO PDF SHA-256 | `sha256:32ebc475a2291ce4f1b5c1a9f9da55227e03192f07e75041e976c29d213ec8aa` |
| Purpose scope | `cn-a-share.financial-source-sentinel.fixed-singleton.v1` |
| Decision grade eligible | `false` |
| Deployment authorized | `false` |

The PDF hash and byte count were independently retrieved from the official static URL while freezing this proposal. G12A implementation must retrieve and verify them again; the plan value is not an acquisition receipt.

## 3. Proposed acquisition interface

```python
class TushareCnAShareFinancialSourceSentinelRequestV1: ...

def acquire_tushare_cn_a_share_financial_source_sentinel_v1(
    request: TushareCnAShareFinancialSourceSentinelRequestV1,
    *,
    token: str,
    output_dir: str | Path,
    post: Post,
    get: Get,
    time_ns: Callable[[], int],
    sleep: Callable[[int], None],
) -> dict[str, object]: ...
```

`TushareCnAShareFinancialSourceSentinelRequestV1` has no caller-configurable economic scope. Its constructor accepts only `schema_version=1` and reconstructs every frozen value in §2 and §4. Subclasses, duck types and altered constructor state fail before I/O.

The operation reuses existing G12A atomic-write, retry, JSON safety, `RawSourceMember`, `SourceSnapshotProvenance`, `freeze_source_snapshot` and `verify_source_snapshot` behavior. It introduces no new generic HTTP framework.

## 4. Exact Tushare requests

Every provider request uses:

```json
{
  "params": {
    "ts_code": "000651.SZ",
    "ann_date": "20240430",
    "period": "20231231"
  }
}
```

No `report_type` or `update_flag` filter is allowed. All returned rows for the exact issuer/period/announcement date remain present and ordered by their response position.

Required field order:

### `income`

```text
ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,
revenue,operate_profit,total_profit,income_tax,n_income,n_income_attr_p,
ebit,ebitda,update_flag
```

### `balancesheet`

```text
ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,
money_cap,notes_receiv,accounts_receiv,inventories,prepayment,oth_receiv,
total_cur_assets,fix_assets,cip,total_assets,st_borr,non_cur_liab_due_1y,
lt_borr,bond_payable,total_liab,total_hldr_eqy_exc_min_int,update_flag
```

### `cashflow`

```text
ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,
n_cashflow_act,c_pay_acq_const_fiolta,n_cashflow_inv_act,
c_cash_equ_end_period,update_flag
```

The sentinel preserves nulls and original numeric JSON representations. It does not fill a missing field from `fina_indicator`, another report type, the PDF or a later response.

## 5. Exact snapshot members

| Ordered acquisition | Member key | Content |
| ---: | --- | --- |
| 1 | `response/tushare/income/000651.SZ-20231231-20240430.json` | Exact successful HTTP response body. |
| 2 | `response/tushare/balancesheet/000651.SZ-20231231-20240430.json` | Exact successful HTTP response body. |
| 3 | `response/tushare/cashflow/000651.SZ-20231231-20240430.json` | Exact successful HTTP response body. |
| 4 | `response/cninfo/annual-report/1219928418.pdf` | Exact official PDF bytes matching §2. |

`acquisition-receipt.json` is written last and remains outside the content-addressed SourceSnapshot archive, following the accepted G12A acquisition pattern.

The receipt binds:

- schema/purpose scope;
- canonical request without token;
- provider API and parameter bodies without token;
- field order;
- each member key, acquired-at nanoseconds, byte count and SHA-256;
- PDF URL, expected and observed bytes/hash;
- SourceSnapshot identity, tree hash and provenance hash;
- source-bounded limitations in §8;
- exact `decision_grade_eligible=false` and `deployment_authorized=false`.

## 6. Response validation

Tushare JSON is accepted only when:

1. bytes decode as one UTF-8 JSON object with duplicate-key and non-finite rejection;
2. provider `code` is exact integer zero;
3. `data.fields` exactly equals the requested ordered field tuple;
4. `data.items` is a list of exact-length lists;
5. every row has `ts_code=000651.SZ`, `ann_date=20240430` and `end_date=20231231`;
6. `f_ann_date`, `report_type`, `comp_type` and `update_flag` are retained, not interpreted as closure;
7. at least one row exists for each API;
8. token text appears nowhere in the response, exception, member, receipt or output path.

Multiple rows, report types 1/4/5 and duplicate economic periods are retained. Exact duplicate response rows or conflicting rows do not get silently deduplicated; the sentinel reports them in receipt observations while preserving raw bytes.

The CNINFO response is accepted only when:

- final response is a PDF beginning with a valid PDF signature;
- observed length is `3911496`;
- observed hash is the exact §2 hash;
- redirects remain confined to approved `cninfo.com.cn` hosts;
- no HTML challenge/error body is substituted.

## 7. Failure precedence

| Priority | Condition | Proposed code |
| ---: | --- | --- |
| 1 | request exact-type/schema/frozen-value mismatch | `INPUT_MISMATCH` |
| 2 | token missing, empty, wrong type or present in canonical request | `CREDENTIAL_INPUT_INVALID` |
| 3 | unsafe output root, symlink, pre-existing member or no-clobber failure | existing G12A path/publication error |
| 4 | provider HTTP/retry exhaustion | `PROVIDER_TRANSPORT_FAILURE` |
| 5 | JSON duplicate/non-finite/shape/provider-code failure | `PROVIDER_RESPONSE_INVALID` |
| 6 | field tuple mismatch | `PROVIDER_FIELDS_MISMATCH` |
| 7 | row identity/period/date mismatch or zero required rows | `FINANCIAL_ROW_SCOPE_MISMATCH` |
| 8 | token detected in any captured/diagnostic value | `CREDENTIAL_LEAK_DETECTED` |
| 9 | CNINFO host/type/bytes/hash mismatch | `OFFICIAL_REPORT_MISMATCH` |
| 10 | SourceSnapshot freeze or verification failure | existing `SourceSnapshotFailureCode` mapped without downgrade |
| 11 | receipt construction or write-last failure | existing G12A acquisition failure |

Every failure is atomic. No successful receipt is written; no partial capture is accepted or renamed as a smaller scope.

## 8. Required limitations

The receipt and future evidence must state all of:

- `SOURCE_BOUNDED_ONLY`;
- one fixed issuer and one report period;
- Tushare disclosure time has day precision only;
- provider initial availability time is unknown;
- CNINFO page/API enumeration closure is not claimed;
- Tushare has no stable revision id, parent/supersedes or terminal set;
- all returned report types are observations, not a resolved final statement;
- no absence claim for corrections, audit problems, penalties, pledges or status events;
- no five-year history, Universe, valuation, corporate-action or execution coverage;
- no quality score, target stream, Backtest, Research Candidate or Validation authority;
- no decision/live/deployment eligibility.

## 9. Availability firewall

This sentinel records:

- economic/report period (`end_date`);
- source-reported announcement dates (`ann_date`, `f_ann_date`);
- local acquisition time;
- exact PDF path/date and bytes.

It does **not** construct a canonical `available_at` for a MarketEvent. A separate owner-approved contract must choose one of:

1. official announcement metadata with exact publication instant;
2. conservative next-session availability rule with explicit uncertainty authority;
3. fail closed.

Until then, Builder normalization and Bundle publication are terminated after SourceSnapshot verification.

## 10. Security and compatibility

- Token is passed separately and never enters `to_canonical_dict()`.
- Provider request sent over HTTP contains the token as required by Tushare, but stored request evidence excludes it.
- Secret-sentinel mutation tests scan files, receipts, errors and serialized outcomes.
- Existing `acquire_tushare_cn_a_share_daily_source_bounded_v2`, authority/listing tools, SourceSnapshot types, fixed-singleton artifacts and protected hashes remain unchanged.
- No new root export from Runtime/Market Data/Trading is permitted.
- The acquisition tool may import Bundle Builder public SourceSnapshot values only; no Runtime import.

## 11. Exact write set after owner approval

Expected Backtest-only implementation lane:

- `backtest/tools/acquisition/cn_a_share_tushare_financial_sentinel_v1.py`;
- `backtest/tests/tools/acquisition/test_cn_a_share_tushare_financial_sentinel_v1.py`;
- `backtest/tests/architecture/test_g12a_tushare_financial_sentinel_v1_boundary.py`;
- static fake-response fixtures only if inline bytes are materially unwieldy;
- G12 plan/Acceptance Matrix updates by the sole governance fan-in owner after acceptance.

No Builder normalized payload, MarketBundle, Runtime PREP, Platform Research or Validation source file belongs to this sentinel.

## 12. Acceptance

Focused tests must prove:

1. exact four-member SourceSnapshot and receipt-last order;
2. request order, field order and token redaction;
3. report types/rows preserved without silent deduplication;
4. zero rows, foreign issuer/period/date and field drift fail at precedence;
5. duplicate JSON keys, NaN/Infinity, malformed rows and provider errors fail;
6. PDF wrong host, redirect, HTML, length and hash fail;
7. symlink, traversal, pre-existing output and write failure remain atomic;
8. snapshot reopens and verifies exact content/provenance identity;
9. output contains every §8 limitation and no Strategy-readiness claim;
10. existing acquisition, SourceSnapshot and fixed-singleton tests/hashes remain unchanged.

Repository acceptance additionally requires clean lock/static typing/import-boundary/full-suite evidence and independent review.

## 13. Implementation candidate and validation

The user approved the isolated Backtest implementation lane and local commit. The candidate is in:

- worktree: `/home/ygguo/agent-projs/ai-crypt/backtest-qb-fin-sentinel`;
- branch: `research/qb-fin-sentinel-v1`;
- PR: [`YungeG/quant-backtest#1`](https://github.com/YungeG/quant-backtest/pull/1), base `backtest-foundation-through-wp02a`;
- remote branch: `origin/research/qb-fin-sentinel-v1`;
- remotely reachable commit: `e7e874fc58e0911b7df1cd0463387526afcb845d` (`feat(acquisition): add A-share financial source sentinel`);
- production: `tools/acquisition/cn_a_share_tushare_financial_sentinel_v1.py`;
- focused tests: `tests/tools/acquisition/test_cn_a_share_tushare_financial_sentinel_v1.py`;
- architecture boundary: `tests/architecture/test_g12a_tushare_financial_sentinel_v1_boundary.py`.

Validated evidence:

- LSP: no diagnostics on all three files;
- focused sentinel tests: `33 passed`;
- final acquisition + SourceSnapshot + architecture selection: `344 passed, 6 deselected`;
- broader repository regression before the final parser-only precedence closure: `2463 passed, 6 deselected`;
- the six deselected legacy exact-write-set guards pass in the clean original Backtest checkout (`6 passed`) and are inapplicable to a dirty additive candidate worktree;
- live credential-free CNINFO GET: status `200`, `3911496` bytes, exact frozen SHA-256;
- independent reviewer: no blocking, high or medium findings remain;
- clean post-commit focused validation: `33 passed`; Backtest worktree clean;
- one URL scanner warning was dispositioned false-positive because the exact host/path and every redirect are validated before `urllib` opens the URL.

## 14. Readiness decision

The implementation candidate is under review in PR #1 and is **not accepted or merged**. Repository-owner review and a normal governance receipt remain required; no merge authority was granted.

Even after sentinel acceptance, the parent Quality + B-Band strategy remains `PLAN_ONLY / DATA_AND_PREPARATION_BLOCKED`.
