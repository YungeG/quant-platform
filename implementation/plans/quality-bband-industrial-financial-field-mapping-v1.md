# QB-FIN-FIELDS-01 — Ordinary-industrial financial field mapping v1

- **Status:** `CORRECTED_AFTER_REAL_CAPTURE / NOTE_DECLARATIONS_BLOCKED`
- **Owner:** Strategy Feature Manifest + pure Builder line-item normalization
- **Scope:** ordinary non-financial industrial issuers only (`comp_type=1`)
- **Selection prerequisite:** [`quality-bband-financial-presentation-selection-v1.md`](quality-bband-financial-presentation-selection-v1.md)

## 1. Outcome

Freeze the minimum raw statement inputs required to calculate auditable annual FCF, net debt, EBIT, EBITDA, NOPAT and invested capital for the Quality + B-Band strategy without using Tushare's vendor ratios or vendor-computed `free_cashflow`, `ebit` and `ebitda` as formula authority.

V1 supports only annual consolidated ordinary-industrial statements. Banks, insurers, securities firms, parent-only statements, quarters/TTM and sector-specific substitutions fail closed.

## 2. Numeric and unit boundary

- Raw SourceSnapshot JSON bytes are authority.
- Builder parses JSON number tokens to exact decimal strings/`Decimal`, never binary float.
- `null` means missing; numeric zero is a real value and is never converted to missing.
- Every chosen statement trio must exact-bind one accounting currency and one accounting unit from competent official report/XBRL metadata.
- Tushare public field pages do not explicitly establish one uniform unit for every required field. Provider response magnitude and PDF examples cannot substitute for unit metadata.
- V1 expected currency/unit is CNY yuan, but Builder returns `ACCOUNTING_UNIT_AUTHORITY_MISSING` until exact official metadata binds that fact.

## 3. Required identity fields

All three statements require:

```text
ts_code, ann_date, f_ann_date, end_date,
report_type, comp_type, update_flag
```

Additionally:

- `comp_type` must be exact `1`;
- `report_type` must be accepted by QB-FIN-REV-01;
- `end_date` must be an annual period end;
- all values bind the chosen SourceSnapshot/member/row/document/publication evidence.

## 4. Income-statement inputs

| Field | Meaning | Formula role | Rule |
| --- | --- | --- | --- |
| `revenue` | operating revenue | FCF margin/scale evidence | required |
| `operate_profit` | operating profit | advisory operating-quality reconciliation | required |
| `total_profit` | profit before income tax | EBIT/tax input | required |
| `income_tax` | income-tax expense | effective-tax input | required |
| `n_income` | consolidated net profit including minority interest | reconciliation | required |
| `n_income_attr_p` | parent-attributable net profit | shareholder-quality evidence | required |
| `minority_gain` | minority profit/loss | reconciliation | required |
| `fin_exp_int_exp` | finance-expense interest expense | EBIT input | required |

Tushare `ebit` and `ebitda` may be captured as provider observations but are `ADVISORY_ONLY`. They cannot fill missing raw inputs or become canonical feature evidence because the public page supplies no formula/version/lineage.

## 5. Balance-sheet inputs

| Field | Meaning | Formula role | Rule |
| --- | --- | --- | --- |
| `money_cap` | monetary funds | net debt/invested capital | required |
| `total_assets` | total assets | reconciliation | required |
| `total_liab` | total liabilities | reconciliation | required |
| `total_hldr_eqy_inc_min_int` | equity including minority interests | invested capital | required |
| `total_hldr_eqy_exc_min_int` | equity excluding minority interests | reconciliation/shareholder evidence | required |
| `minority_int` | minority interests | reconciliation | required |
| `total_liab_hldr_eqy` | liabilities and equity total | balance reconciliation | required |
| `st_borr` | short-term borrowings | debt reconciliation | required |
| `non_cur_liab_due_1y` | non-current liabilities due within one year | debt reconciliation | required |
| `lt_borr` | long-term borrowings | debt reconciliation | required |
| `bond_payable` | bonds payable | debt reconciliation | nullable only under exact note declaration |
| `st_bonds_payable` | short-term bonds payable | debt reconciliation | nullable only under exact note declaration |
| `lease_liab` | non-current lease liabilities | debt reconciliation | required for post-adoption periods |

The standard balance fields do not by themselves define complete interest-bearing debt. `lt_payable`, `oth_cur_liab`, `oth_ncl`, `trading_fl` and other broad liabilities are not silently classified. Canonical debt requires a source-bound financing-liability note declaration; missing declaration returns `DEBT_SCOPE_INCOMPLETE`.

## 6. Cash-flow inputs

| Field | Meaning | Formula role | Rule |
| --- | --- | --- | --- |
| `n_cashflow_act` | net operating cash flow | FCF | required |
| `c_pay_acq_const_fiolta` | cash paid to acquire/build fixed, intangible and other long-lived assets | capital expenditure | required |
| `depr_fa_coga_dpba` | provider depreciation/depletion field | D&A through exact source-bound semantic declaration | required |
| `use_right_asset_dep` | separate right-of-use depreciation observation | advisory/optional | never added when included in the declared combined depreciation line |
| `amort_intang_assets` | intangible-asset amortization | D&A | required |
| `lt_amort_deferred_exp` | separate long-term deferred-expense amortization | advisory/optional | added only when official declaration proves a separate line |
| `c_cash_equ_end_period` | ending cash and cash equivalents | cash reconciliation evidence | required |

Tushare `free_cashflow` is `ADVISORY_ONLY` and cannot substitute for operating cash flow minus capital expenditure.

## 7. Frozen formula-input definitions

These are exact intermediate definitions; final quality gates and thresholds remain a later Feature Manifest.

```text
capital_expenditure
  = c_pay_acq_const_fiolta

free_cash_flow
  = n_cashflow_act - capital_expenditure

reported_depreciation_and_amortization
  = declared_combined_depreciation
  + declared_separate_amortization_lines

interest_bearing_debt
  = financing_liability_note_declaration.ending_interest_bearing_debt

net_debt
  = interest_bearing_debt - money_cap

EBIT
  = total_profit + fin_exp_int_exp

EBITDA
  = EBIT + reported_depreciation_and_amortization

effective_tax_rate
  = income_tax / total_profit

NOPAT
  = EBIT * (1 - effective_tax_rate)

closing_invested_capital
  = total_hldr_eqy_inc_min_int
  + interest_bearing_debt
  - money_cap

average_invested_capital(year Y)
  = (closing_invested_capital(Y-1) + closing_invested_capital(Y)) / 2

ROIC(year Y)
  = NOPAT(Y) / average_invested_capital(Y)

net_debt_to_EBITDA
  = net_debt / EBITDA
```

Five annual ROIC observations require six annual balance-sheet endpoints. No first-year shortcut, ending-capital substitution or provider ROIC fallback is allowed.

## 8. Formula-domain failures

- `total_profit <= 0`: effective tax rate/NOPAT/ROIC unavailable for that year;
- `income_tax < 0` or `income_tax > total_profit`: effective-tax input unsupported; no clamp;
- `EBITDA <= 0`: net-debt/EBITDA unavailable;
- `average_invested_capital <= 0`: ROIC unavailable;
- missing/null required value: fail, except when an exact official note declaration proves zero/not-applicable for that field and report;
- numeric zero remains valid unless a denominator/strictly-positive rule rejects it;
- negative FCF/net debt/EBIT/NOPAT remain real outputs;
- no winsorization, clipping, sector median, forward fill or TTM substitution in v1.

## 9. Reconciliation checks

Before formulas:

1. exact `comp_type=1`, annual consolidated scope and selected trio coherence;
2. `total_hldr_eqy_inc_min_int = total_hldr_eqy_exc_min_int + minority_int` at the declared unit;
3. `total_assets = total_liab_hldr_eqy` at the declared unit;
4. `total_profit - income_tax = n_income` at the declared unit;
5. line-item currency/unit consistency across all three statements;
6. no duplicate field token or non-finite numeric value.

Any permitted reporting-rounding tolerance requires a later explicit unit/rounding contract. V1 does not invent epsilon.

## 10. Acquisition delta and real-capture correction

PR [`YungeG/quant-backtest#1`](https://github.com/YungeG/quant-backtest/pull/1) intentionally proves a smaller source-capture sentinel. Its field tuple is insufficient for canonical feature calculations.

Missing required fields include:

- income: `fin_exp_int_exp`, `minority_gain`;
- balance: `total_hldr_eqy_inc_min_int`, `minority_int`, `total_liab_hldr_eqy`, `st_bonds_payable`, `lease_liab`;
- cash flow: `depr_fa_coga_dpba`, `use_right_asset_dep`, `amort_intang_assets`, `lt_amort_deferred_exp`.

Captured provider `ebit`/`ebitda` cannot replace those omissions. PR #1 remains the minimal G12A sentinel; stacked PR #2 added the fields and produced real SourceSnapshot `sha256:dec0abb1828f8b87256347e72b6ccfe2f84a2ca13f36aa1415c9a53e96a0c7d5`.

Real-capture audit found:

- balance rows differ only by non-authoritative `update_flag`;
- official ending bond balance is zero, but null→zero requires an exact note declaration;
- standard balance fields do not exact-cover official `银行借款及其他` financing liabilities;
- captured `depr_fa_coga_dpba` exactly equals the official combined fixed/investment-property/right-of-use depreciation line;
- adding null `use_right_asset_dep` separately would double count;
- no separate long-term deferred-expense amortization line appears in the official cash-flow supplement.

These corrections are source-specific declaration rules, not provider-global null semantics.

## 11. Failure precedence

| Priority | Condition | Proposed code |
| ---: | --- | --- |
| 1 | exact input/schema/type mismatch | `INPUT_MISMATCH` |
| 2 | issuer/period/statement/source identity mismatch | `STATEMENT_IDENTITY_MISMATCH` |
| 3 | non-industrial/nonannual/nonconsolidated scope | `STATEMENT_SCOPE_UNSUPPORTED` |
| 4 | official accounting currency/unit absent or inconsistent | `ACCOUNTING_UNIT_AUTHORITY_MISSING` |
| 5 | required field absent/null or unsupported numeric token | `REQUIRED_LINE_ITEM_MISSING` |
| 6 | broad/ambiguous debt cannot be classified | `DEBT_SCOPE_INCOMPLETE` |
| 7 | equity/balance/profit reconciliation mismatch | `STATEMENT_RECONCILIATION_MISMATCH` |
| 8 | effective-tax domain invalid | `EFFECTIVE_TAX_DOMAIN_UNSUPPORTED` |
| 9 | EBITDA denominator nonpositive | `EBITDA_NONPOSITIVE` |
| 10 | invested-capital denominator nonpositive | `INVESTED_CAPITAL_NONPOSITIVE` |
| 11 | prior annual balance endpoint missing | `PRIOR_CAPITAL_ENDPOINT_MISSING` |
| 12 | result reconstruction/hash mismatch | `RESULT_RECONSTRUCTION_MISMATCH` |

No partial formula set or zero-filled quality evidence is returned.

## 12. Security and purity

- Pure normalization/formula-input code only; no provider call, PDF parsing at Runtime, filesystem, clock or account state.
- Raw provider bytes and official unit evidence remain retained outside Strategy execution.
- Decimal parsing is duplicate-key/non-finite safe.
- Formula evidence binds chosen trio/revision/document/source hashes.
- No vendor ratios, current pages, local mutable databases or Strategy-selected substitutions.

## 13. Acceptance

A future implementation must prove:

1. exact ordinary-industrial field mapping and unsupported company-type failures;
2. decimal-token preservation without float conversion;
3. unit/currency authority success and missing/conflicting unit failures;
4. provider EBIT/EBITDA/FCF never fills raw-field gaps;
5. exact formula intermediates and five-ROIC/six-balance coverage;
6. null versus zero behavior;
7. negative outputs preserved and invalid denominator/tax domains fail;
8. debt-scope ambiguity fails;
9. reconciliation failures preserve precedence;
10. input order/batch shape do not change formula hashes;
11. no feature threshold/ranking/target or Runtime I/O;
12. PR #1 identities remain unchanged.

## 14. Readiness decision

The real v2 capture corrected the generic mapping: standard debt fields are incomplete, and the captured depreciation field already equals the official combined line including right-of-use depreciation for this report. Formula execution now requires source-bound financing-liability and cash-flow line-item declarations; acquisition bytes remain immutable.
