# QB-FIN-NOTES-01 — Financing-liability and D&A note declarations v1

- **Status:** `CANDIDATE_PUBLISHED / STACKED_PR_OPEN / NOT_ACCEPTED`
- **Owner:** Backtest G12 data-governance reviewer
- **SourceSnapshot:** `sha256:dec0abb1828f8b87256347e72b6ccfe2f84a2ca13f36aa1415c9a53e96a0c7d5`
- **Source audit:** [`research/quality-bband-real-capture-line-item-audit.md`](../../research/quality-bband-real-capture-line-item-audit.md)

## 1. Outcome

Bind two report-note facts from the exact Gree 2023 annual-report PDF:

1. complete ending interest-bearing financing liabilities;
2. exact depreciation-and-amortization line semantics.

These declarations resolve source-specific null/coverage ambiguity without changing Tushare source bytes or inventing provider-wide null rules.

## 2. Exact official source

| Field | Value |
| --- | --- |
| Member | `response/cninfo/annual-report/1219928418.pdf` |
| URL | `http://static.cninfo.com.cn/finalpage/2024-04-30/1219928418.PDF` |
| Bytes | `3911496` |
| SHA-256 | `sha256:32ebc475a2291ce4f1b5c1a9f9da55227e03192f07e75041e976c29d213ec8aa` |
| Report page | `210` |
| Issuer | 珠海格力电器股份有限公司 / `000651.SZ` |
| Period | `20231231` |
| Unit | 人民币元 |

The declarations use human-reviewed exact-document-hash evidence. Builder does not parse arbitrary PDF text.

## 3. Financing-liability declaration

Official section:

```text
3) 筹资活动产生的各项负债变动情况
```

Reviewed ending balances:

| Official row | Ending balance |
| --- | ---: |
| 银行借款及其他 | `87,676,167,515.47` |
| 应付债券 | `0.00` |
| 租赁负债（含一年内到期的租赁负债） | `856,833,971.52` |
| 应付股利 | `5,572,388.92` |
| Table total | `88,538,573,875.91` |

Reconciliation:

```text
87,676,167,515.47
+ 0.00
+ 856,833,971.52
+ 5,572,388.92
= 88,538,573,875.91
```

`应付股利` is not interest-bearing financing debt. Exact declared interest-bearing debt is:

```text
87,676,167,515.47 + 0.00 + 856,833,971.52
= 88,533,001,486.99 CNY
```

Proposed value:

```python
FinancialDebtScopeDeclarationV1 = {
  schema_version=1,
  declaration_key="cn-a-share.000651.2023-financing-liability-scope.v1",
  source_snapshot_id,
  source_member_key,
  source_document_hash,
  report_page=210,
  issuer/instrument/report_period,
  accounting_currency="CNY",
  accounting_unit="yuan",
  official_section="筹资活动产生的各项负债变动情况",
  bank_borrowings_and_other="87676167515.47",
  bonds_payable="0.00",
  lease_liabilities_including_current="856833971.52",
  non_debt_dividends_payable="5572388.92",
  official_table_total="88538573875.91",
  ending_interest_bearing_debt="88533001486.99",
  reviewed_at,
  reviewer_identity,
  declaration_hash,
}
```

Consequences for the captured Tushare rows:

- `bond_payable=null` and `st_bonds_payable=null` may map to exact zero for this report only;
- standard balance-field sums remain reconciliation observations, not complete debt authority;
- `ending_interest_bearing_debt` comes from this declaration, not a silent sum of standard fields.

## 4. D&A line-item declaration

Official cash-flow supplement rows:

| Official row | Current amount |
| --- | ---: |
| 固定资产折旧、投资性房地产折旧及使用权资产摊销 | `4,808,144,624.82` |
| 无形资产摊销 | `475,186,591.56` |

Captured Tushare values exact-match:

| Tushare field | Captured value | Declared meaning for this report |
| --- | ---: | --- |
| `depr_fa_coga_dpba` | `4,808,144,624.82` | combined fixed/investment-property/right-of-use depreciation/amortization row |
| `amort_intang_assets` | `475,186,591.56` | intangible-asset amortization row |
| `use_right_asset_dep` | `null` | no separate addition; already included in combined row |
| `lt_amort_deferred_exp` | `null` | no separate official supplement row; no addition |

Exact declared D&A:

```text
4,808,144,624.82 + 475,186,591.56
= 5,283,331,216.38 CNY
```

Proposed value:

```python
FinancialDepreciationAmortizationDeclarationV1 = {
  schema_version=1,
  declaration_key="cn-a-share.000651.2023-da-line-item-scope.v1",
  source_snapshot_id,
  source_member_key,
  source_document_hash,
  report_page=210,
  issuer/instrument/report_period,
  accounting_currency="CNY",
  accounting_unit="yuan",
  combined_depreciation_field="depr_fa_coga_dpba",
  combined_depreciation_amount="4808144624.82",
  combined_depreciation_includes=("fixed_assets","investment_property","right_of_use_assets"),
  intangible_amortization_field="amort_intang_assets",
  intangible_amortization_amount="475186591.56",
  separate_use_right_addition="0.00",
  separate_long_term_deferred_addition="0.00",
  ending_depreciation_and_amortization="5283331216.38",
  reviewed_at,
  reviewer_identity,
  declaration_hash,
}
```

The zero additions describe absence of separate additions under this exact official combined-line mapping. They are not provider-global null→zero semantics.

## 5. Failure precedence

| Priority | Condition | Proposed code |
| ---: | --- | --- |
| 1 | exact input/schema/type mismatch | `INPUT_MISMATCH` |
| 2 | SourceSnapshot/member/PDF hash mismatch | `DOCUMENT_IDENTITY_MISMATCH` |
| 3 | issuer/period/page/unit mismatch | `DOCUMENT_CONTEXT_MISMATCH` |
| 4 | official row/value/reconciliation mismatch | `OFFICIAL_NOTE_EVIDENCE_MISMATCH` |
| 5 | captured Tushare row/field/value mismatch | `SOURCE_ROW_BINDING_MISMATCH` |
| 6 | debt component/table total mismatch | `DEBT_RECONCILIATION_MISMATCH` |
| 7 | D&A component/combined total mismatch | `DA_RECONCILIATION_MISMATCH` |
| 8 | reviewer identity/time invalid | `REVIEW_AUTHORITY_INVALID` |
| 9 | declaration reconstruction/hash mismatch | `DECLARATION_RECONSTRUCTION_MISMATCH` |

No partial debt/D&A authority is returned.

## 6. Security and scope

- Pure declarations over exact source/member/row hashes; no Runtime PDF parsing or network.
- Reviewer identity is non-secret; no credentials or local paths in canonical declarations.
- Applies only to `000651.SZ`/`20231231` and the exact report hash.
- Does not establish provider-wide Tushare field/null semantics.
- Does not publish ROIC, EBITDA, net debt/EBITDA, quality score or Strategy target.
- Remains source-bounded, non-decision-grade and non-deployment.

## 7. Acceptance

1. exact document/page/row/value reconstruction;
2. official debt components reconcile to table total and declared interest-bearing debt;
3. captured null bond fields map to zero only with this declaration;
4. Tushare D&A fields exact-match official rows;
5. right-of-use depreciation is not double counted;
6. wrong value/page/unit/source/reviewer fails at precedence;
7. no provider-global null rule or standard-field debt fallback;
8. declaration hashes bind every source/semantic/reviewer field;
9. no PDF parser/I/O in downstream pure module;
10. SourceSnapshot and acquisition receipts remain unchanged.

## 8. Readiness decision

The note facts are included in the aggregate candidate implemented by stacked PR [`YungeG/quant-backtest#3`](https://github.com/YungeG/quant-backtest/pull/3). Real declaration hash `sha256:59e09eb542a6e2ec480a7b8ed322d9ae9106416460f0999216fd5564f7278007` remains source-bounded, unaccepted and non-decision-grade. Formula normalization may proceed only as another stacked candidate.
