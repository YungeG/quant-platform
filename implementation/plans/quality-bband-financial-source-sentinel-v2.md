# QB-FIN-SENTINEL-02 — Formula-input financial source successor v2

- **Status:** `STACKED_PR_OPEN / NOT_MERGED / NOT_ACCEPTED`
- **Owner:** Backtest G12A acquisition
- **Predecessor:** [`quality-bband-financial-source-sentinel-v1.md`](quality-bband-financial-source-sentinel-v1.md)
- **Availability policy:** [`quality-bband-financial-availability-policy-v1.md`](quality-bband-financial-availability-policy-v1.md)
- **Field mapping:** [`quality-bband-industrial-financial-field-mapping-v1.md`](quality-bband-industrial-financial-field-mapping-v1.md)

## 1. Outcome

Create one additive successor SourceSnapshot for the same fixed issuer/period that captures:

1. expanded raw Tushare statement fields needed by QB-FIN-FIELDS-01;
2. the unchanged official annual-report PDF;
3. one later official issuer confirmation of the report's publication date.

V2 remains acquisition-only. It publishes no unit declaration, normalized observation, availability result, formula, MarketBundle or Strategy evidence.

## 2. Immutable predecessor

PR [`YungeG/quant-backtest#1`](https://github.com/YungeG/quant-backtest/pull/1) at commit `e7e874fc58e0911b7df1cd0463387526afcb845d` remains unchanged.

V2 must not modify:

- v1 request, response fields, receipt, tests or hashes;
- v1 four-member SourceSnapshot semantics;
- v1 source-bounded limitations;
- existing fixed-singleton G12 artifacts.

V2 uses a new request/receipt/schema/module and direct predecessor identity.

## 3. Exact source scope

| Value | Frozen value |
| --- | --- |
| Issuer | 珠海格力电器股份有限公司 |
| Tushare code | `000651.SZ` |
| Instrument candidate | `xshe:000651` |
| Company type | `1` ordinary industrial |
| Period | `20231231` |
| Tushare announcement date | `20240430` |
| Annual-report document | CNINFO `1219928418.PDF` |
| Annual-report bytes/hash | `3911496` / `sha256:32ebc475a2291ce4f1b5c1a9f9da55227e03192f07e75041e976c29d213ec8aa` |
| Retrospective confirmation | CNINFO `1220300051.PDF` |
| Confirmation bytes/hash | `302155` / `sha256:a78a67865a7ea989c4fd8b053fad1aa75f36d22c10d14387800ff16b698dbc60` |
| Purpose scope | `cn-a-share.financial-source-sentinel.fixed-singleton.v2` |
| Grade/deployment | `false` / `false` |

The confirmation states that the issuer disclosed the 2023 annual report on `2024-04-30`. It proves a date-only retrospective statement, not an exact historical timestamp.

## 4. Exact Tushare parameters

Each request uses:

```json
{
  "ts_code": "000651.SZ",
  "ann_date": "20240430",
  "period": "20231231",
  "comp_type": "1"
}
```

No `report_type`, `update_flag` or `is_calc` filter is allowed. Every returned row is retained in source order.

## 5. Expanded exact field tuples

### `income`

```text
ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,
revenue,operate_profit,total_profit,income_tax,n_income,n_income_attr_p,
minority_gain,fin_exp_int_exp,
ebit,ebitda,update_flag
```

`ebit` and `ebitda` remain advisory source observations only.

### `balancesheet`

```text
ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,
money_cap,total_assets,total_liab,
total_hldr_eqy_inc_min_int,total_hldr_eqy_exc_min_int,minority_int,
total_liab_hldr_eqy,
st_borr,non_cur_liab_due_1y,lt_borr,bond_payable,st_bonds_payable,lease_liab,
update_flag
```

### `cashflow`

```text
ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,
n_cashflow_act,c_pay_acq_const_fiolta,
depr_fa_coga_dpba,use_right_asset_dep,amort_intang_assets,
lt_amort_deferred_exp,c_cash_equ_end_period,
free_cashflow,update_flag
```

`free_cashflow` remains advisory source observation only.

## 6. Exact snapshot members

| Order | Member key | Authority |
| ---: | --- | --- |
| 1 | `response/tushare/income/000651.SZ-20231231-20240430-v2.json` | exact provider response |
| 2 | `response/tushare/balancesheet/000651.SZ-20231231-20240430-v2.json` | exact provider response |
| 3 | `response/tushare/cashflow/000651.SZ-20231231-20240430-v2.json` | exact provider response |
| 4 | `response/cninfo/annual-report/1219928418.pdf` | exact official report bytes |
| 5 | `response/cninfo/publication-confirmation/1220300051.pdf` | exact later official confirmation bytes |

The receipt is written last and remains outside the content-addressed archive, following existing G12A mechanics.

## 7. Confirmation authority boundary

The acquisition succeeds only when the confirmation PDF exact URL, byte count and SHA-256 match the frozen official document identity. The acquisition receipt records raw member/hash/provenance only; it does **not** publish or attest the semantic claim contained in the PDF.

V2 does not parse PDF text or derive `available_at`. It publishes the raw confirmation for a later pure `FinancialPublicationConfirmationDeclarationV1` that must separately bind:

- confirmation PDF hash and page 1;
- issuer/security `000651`;
- report title `2023 年年度报告`;
- exact quoted statement that it was disclosed on `2024 年 4 月 30 日`;
- declaration/reviewer identity;
- confirmation's own later publication/acquisition evidence.

The declaration is a separate Builder input and is not fabricated into raw SourceSnapshot bytes or the acquisition receipt.

## 8. Accounting-unit boundary

The annual-report PDF states `单位：人民币元` for the consolidated balance sheet, consolidated income statement and consolidated cash-flow statement (report pages 113–116).

V2 only retains the exact PDF. It does not parse PDF pages or publish unit authority. A future immutable `FinancialStatementUnitDeclarationV1` must bind:

- report hash;
- page range 113–116;
- issuer and consolidated statement titles;
- exact source phrase `单位：人民币元`;
- currency `CNY` and unit `yuan`;
- declaration/reviewer identity.

Builder fails if that declaration is absent or mismatched.

## 9. Proposed acquisition seam

```python
TushareCnAShareFinancialSourceSentinelRequestV2
acquire_tushare_cn_a_share_financial_source_sentinel_v2(...)
```

Reuse v1/common:

- exact credential confinement;
- POST/GET retry and redaction;
- duplicate-key/non-finite rejection;
- URL/redirect confinement;
- safe output/no clobber;
- atomic publication;
- SourceSnapshot freeze/verify;
- ordered failure codes.

No shared abstraction extraction is authorized unless v1/v2 exact duplication makes one existing helper materially clearer without changing v1 bytes/behavior.

## 10. Failure precedence

| Priority | Condition | Proposed code |
| ---: | --- | --- |
| 1 | request/input exact mismatch | `INPUT_MISMATCH` |
| 2 | credential input/conflict | `CREDENTIAL_INPUT_INVALID` |
| 3 | unsafe output/no-clobber | existing path/publication failure |
| 4 | provider/document transport exhaustion | `PROVIDER_TRANSPORT_FAILURE` |
| 5 | response JSON/envelope/row invalid | `PROVIDER_RESPONSE_INVALID` |
| 6 | exact field tuple mismatch | `PROVIDER_FIELDS_MISMATCH` |
| 7 | issuer/period/company-type/date/row scope mismatch | `FINANCIAL_ROW_SCOPE_MISMATCH` |
| 8 | credential in any source/evidence/output | `CREDENTIAL_LEAK_DETECTED` |
| 9 | annual report bytes/hash mismatch | `ANNUAL_REPORT_MISMATCH` |
| 10 | confirmation URL/bytes/hash identity mismatch | `PUBLICATION_CONFIRMATION_MISMATCH` |
| 11 | SourceSnapshot failure | exact `SourceSnapshotFailureCode` |
| 12 | receipt/publication failure | existing G12A failure |

One failure yields no successful receipt and no accepted smaller capture.

## 11. Required limitations

The v2 receipt repeats v1 limitations and adds:

- expanded fields do not prove accounting unit without an accepted declaration;
- confirmation is retrospective date-only evidence, not exact historical timestamp;
- provider EBIT/EBITDA/FCF are advisory only;
- debt classification may remain incomplete;
- no normalized revision, presentation selection or formula evidence;
- no five-year history/full-market/terminal-set closure;
- no decision/live/deployment authority.

## 12. Expected implementation write set after approval

- `backtest/tools/acquisition/cn_a_share_tushare_financial_sentinel_v2.py`;
- `backtest/tests/tools/acquisition/test_cn_a_share_tushare_financial_sentinel_v2.py`;
- `backtest/tests/architecture/test_g12a_tushare_financial_sentinel_v2_boundary.py`;
- plan/Acceptance Matrix updates only by governance fan-in owner.

V1 files are protected and not in the v2 write set.

## 13. Acceptance

1. exact five-member SourceSnapshot and receipt-last publication;
2. exact expanded fields/params and all report types retained;
3. annual-report and confirmation URL/bytes/hash identities independently mutate/fail;
4. credential/path/transport/JSON/field/row precedence parity with v1;
5. SourceSnapshot exact reopen and content/provenance identity;
6. v1 files, commit and PR diff remain unchanged;
7. no semantic confirmation claim, unit/availability/normalized/formula/Bundle output;
8. focused, acquisition, SourceSnapshot and architecture regressions;
9. clean full-suite/static/import/security evidence;
10. independent review.

## 14. Implementation and readiness decision

The explicit stacked-successor lane is implemented and open as [`YungeG/quant-backtest#2`](https://github.com/YungeG/quant-backtest/pull/2):

- base: `research/qb-fin-sentinel-v1` / PR #1;
- head: `research/qb-fin-sentinel-v2`;
- commit: `23f2fbdfd2a95a66513097b9ab1c2ba66cfe0a52`;
- focused tests: `22 passed`;
- final adjacent selection: `149 passed, 1 deselected`;
- broad regression: `2486 passed, 7 deselected`;
- independent review: no blocking, high or medium findings;
- LSP clean; URL scanner warning dispositioned false-positive.

PR #2 is not accepted or merged. Credentialed capture still requires explicit permission to use `TUSHARE_TOKEN` and an approved output root.
