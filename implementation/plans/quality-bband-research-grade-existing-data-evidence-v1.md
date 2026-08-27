# Quality-BBAND research-grade existing-data evidence v1

- **Status:** `OWNER_APPROVED / RELAXED_RESEARCH_STANDARD`
- **Approval date:** `2026-08-28`
- **Owner decision:** `我们可以放宽证据标准，既然目前得到的资料是我们所能得到的所有资料。`
- **Scope:** existing immutable data only; no acquisition or procurement

## 1. Authority tier

Add one advisory tier:

```text
EXISTING_DATA_RESEARCH_GRADE
```

This tier may support provisional financial calculations, historical diagnostics and candidate ranking. It is not official/formal S2, decision-grade Validation, deployment, or trading authority.

## 2. Research availability convention

For research calculations only:

1. Use provider `f_ann_date` as the controlling declared visibility date when present.
2. Otherwise use provider `ann_date`.
3. A row is visible only when that date is not later than the screen decision date.
4. A missing/invalid provider date leaves the row unavailable.
5. This convention does not claim legal filing availability and never changes the earlier formal-S2 conclusion.

## 3. Research revision and trio convention

For each issuer/period/screen:

1. Find `(ann_date, f_ann_date)` candidates common to income, balance and cash-flow rows visible by the screen date.
2. Select the latest common pair by `(effective provider visibility date, f_ann_date, ann_date)`.
3. Within one API/common-date group, prefer `update_flag="1"` as the provider-declared updated row.
4. If more than one preferred row has conflicting economic payload, leave the pair unresolved.
5. If no preferred updated row exists, accept a single row or payload-identical rows; conflicting rows remain unresolved.
6. No common visible trio leaves the pair unresolved. Independent latest statements are not mixed.

Every retained row and rejected candidate remains auditable. These rules are project research conventions, not supersession facts.

## 4. Research accounting assumptions

For `comp_type="1"`, `report_type="1"` annual rows:

- treat captured statement amounts as one internally consistent CNY-yuan research unit;
- exact unit and consolidation authority remain false;
- calculate FCF from `n_cashflow_act - c_pay_acq_const_fiolta`;
- calculate debt proxy from:

```text
st_borr
+ non_cur_liab_due_1y
+ lt_borr
+ bond_payable
+ st_bonds_payable
```

- null among those enumerated debt fields is treated as zero for the proxy only;
- lease liabilities and broad ambiguous liabilities are excluded and the output is named `interest_bearing_debt_proxy`;
- calculate D&A proxy as `depr_fa_coga_dpba + amort_intang_assets`; null is zero for this proxy only;
- `use_right_asset_dep` and `lt_amort_deferred_exp` are not added separately;
- all proxy assumptions are explicit limitations.

## 5. Formula and domain rules

Use the frozen formulas with proxy names substituted where necessary:

```text
EBIT = total_profit + fin_exp_int_exp
EBITDA_proxy = EBIT + D&A_proxy
net_debt_proxy = interest_bearing_debt_proxy - money_cap
closing_invested_capital_proxy
  = total_hldr_eqy_inc_min_int
  + interest_bearing_debt_proxy
  - money_cap
ROIC_proxy = NOPAT / average_invested_capital_proxy
net_debt_to_EBITDA_proxy = net_debt_proxy / EBITDA_proxy
```

The approved formula-domain decision remains unchanged: nonpositive/unsupported denominators are unresolved unless another independent filter is already decision-invariantly failed.

## 6. Provisional research filters

For each screen/issuer record:

```text
median five annual ROIC_proxy >= 0.20
positive OCF in at least 4 of 5 years
five-year FCF sum > 0
latest net_debt_to_EBITDA_proxy < 1.5
```

Results are exactly one of:

```text
RESEARCH_GRADE_PROVISIONAL_PASS
RESEARCH_GRADE_PROVISIONAL_FAIL
RESEARCH_GRADE_UNRESOLVED
```

Accepted N and unsupported O evidence remain unresolved and numeric-free.

## 7. Existing market-data convention

The immutable local DuckDB backup may be used as advisory raw-price evidence:

```text
sha256:cdc6ce41dee3fe9903d8c27ec5cc584455ad423989cd79e3eb0187c5bba8bd41
coverage end: 2026-05-20
```

No corporate-action or point-in-time adjustment authority is claimed. Signals after the coverage end cannot be inferred. Raw-price diagnostics never produce a current TargetSnapshot.

## 8. Authority ceiling

The following remain false:

```text
formal_s2_qualified
decision_grade_eligible
strategy_target_authorized
backtest_authorized
validation_authorized
deployment_authorized
```

No real trading, T+1 order instruction, Promotion, Shadow or Live authority is granted.
