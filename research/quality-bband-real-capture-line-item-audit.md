# Quality + B-Band real capture line-item audit

- **Status:** `SOURCE_VERIFIED / FORMULA_MAPPING_REQUIRES_SUCCESSOR`
- **SourceSnapshot:** `sha256:dec0abb1828f8b87256347e72b6ccfe2f84a2ca13f36aa1415c9a53e96a0c7d5`
- **Official report:** CNINFO `1219928418.PDF`, report pages 113–116 and 210
- **Scope:** `000651.SZ`, annual period `20231231`

## Capture integrity

The persisted five-member candidate was rebuilt from exact members/provenance and passed `verify_source_snapshot()`. All files are mode `0600`; credential scan is clean.

Provider rows:

- income: one `report_type=1` row;
- balance: two `report_type=1` rows whose economic fields are identical; only `update_flag` differs (`0` and `1`);
- cash flow: one `report_type=1` row.

The two balance rows are presentation duplicates for formula inputs, not two different economic values. Raw rows remain retained and `update_flag` remains non-authoritative.

## Debt findings

Captured nulls:

- `bond_payable = null`;
- `st_bonds_payable = null`.

The official annual-report financing-liability movement table on report page 210 shows:

- bonds began at zero;
- cash issuance `899,737,500.00`;
- non-cash increase `12,087,909.84`;
- cash repayment `911,825,409.84`;
- ending bonds balance is blank/zero.

Therefore these two null fields may be declared zero for this exact report only after a source-bound debt declaration. Tushare null alone still cannot mean zero globally.

The same page shows ending:

- `银行借款及其他 = 87,676,167,515.47`;
- `租赁负债（含一年内到期的租赁负债） = 856,833,971.52`;
- `应付债券 = 0`.

The standard Tushare balance fields requested in v2 do not fully reconcile to the official `银行借款及其他` total. Their sum misses other financing classified inside the official note. Canonical net debt must therefore use an exact source-bound financing-liability declaration or additional structured note fields; it must not silently rely on the incomplete standard-field sum.

## Depreciation and amortization findings

Captured values:

- `depr_fa_coga_dpba = 4,808,144,624.82`;
- `amort_intang_assets = 475,186,591.56`;
- `use_right_asset_dep = null`;
- `lt_amort_deferred_exp = null`.

The official cash-flow supplement on report page 210 states:

- `固定资产折旧、投资性房地产折旧及使用权资产摊销 = 4,808,144,624.82`;
- `无形资产摊销 = 475,186,591.56`.

Thus, for this exact issuer/report, Tushare `depr_fa_coga_dpba` already maps to the combined official line including right-of-use asset depreciation. Adding `use_right_asset_dep` would double count. The official supplement does not expose a separate long-term deferred-expense amortization line.

Exact v1 D&A input for this report should be:

```text
4,808,144,624.82 + 475,186,591.56
```

subject to a source-bound line-item declaration. The generic field mapping must be corrected; null optional subcomponents cannot be treated as required when the authoritative combined line already includes them.

## Required contract changes

1. Change `use_right_asset_dep` and `lt_amort_deferred_exp` from universally required additive D&A inputs to optional/advisory fields.
2. Require a source-bound declaration describing what `depr_fa_coga_dpba` represents for each accepted report/layout.
3. Add a debt-scope declaration binding the official financing-liability movement ending balances.
4. Permit bond null→zero only under the exact declaration; never as a provider-wide null rule.
5. Keep the real SourceSnapshot immutable; corrections belong in declarations/normalization policy, not acquisition bytes.

## Decision

The real capture is valid and materially useful, but the current generic formula mapping is not correct enough to calculate canonical net debt/EBITDA or ROIC. Builder/formula execution remains blocked until the declarations and mapping successor are frozen and accepted.
