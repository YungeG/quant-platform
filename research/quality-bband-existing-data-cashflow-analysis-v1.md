# Quality-BBAND existing-data cash-flow analysis v1

- **Status:** `ADVISORY / EXISTING_DATA_ONLY / PROVIDER_SCOPED`
- **Strategy:** `cn-a-share.quality-bband-breakout.manual4.v1`
- **Evidence boundary:** [`quality-bband-existing-data-only-analysis-v1.md`](../implementation/plans/quality-bband-existing-data-only-analysis-v1.md)

## 1. Question

Using no new data, how much of the financial hard-filter decision can be determined from the retained operating-cash-flow and capital-expenditure candidates?

This analysis does not establish formal S2, official availability, revision supersession, coherent official trio selection, ROIC, leverage, Strategy targets, Backtest, Validation, deployment, or trading authority.

## 2. Evidence

- Preferred formal Tushare S1 manifest: `sha256:dcd0fecbfca29ce090b53462f3972174d4977116e52472309055b4110046df85`.
- S2B exact extraction: `96,537 = 96,515 P + 1 O + 21 N`.
- Prior-balance binding: `20,797 = 17,952 core + 850 S2A + 1,995 Stage A`; augmented member count `99,382`.
- All retained cash-flow provider revisions from S2B candidate-02.

## 3. Method

For each of 20,797 screen/issuer records:

1. Accepted N or unsupported O evidence takes issuer-local unresolved precedence.
2. Preserve every retained cash-flow row for the five required annual periods.
3. Never select by `update_flag`, provider date, row order or capture order.
4. For each year, bound whether `n_cashflow_act > 0` across all candidates.
5. Calculate candidate `FCF = n_cashflow_act - c_pay_acq_const_fiolta` and bound the five-year sum only when all retained candidates are numeric.
6. A **provisional hard-filter failure** is emitted only when every retained candidate fails at least one existing cash-flow condition:
   - maximum possible positive-OCF count `< 4`; or
   - maximum possible five-year FCF sum `<= 0`.
7. A **cash-flow-invariant pass** requires minimum positive-OCF count `>= 4` and minimum five-year FCF sum `> 0`.
8. Every other provider record is ambiguous. Even a cash-flow-invariant pass remains unresolved because ROIC, leverage and authority inputs are unavailable.

The complete 20,797-record diagnostic was recomputed independently twice with identical counts.

## 4. Full-period result

| Existing-data-only result | Count |
|---|---:|
| provisional cash-flow hard-filter failure | 10,462 |
| provider-scoped unresolved | 10,325 |
| official nonfiling unresolved | 7 |
| unsupported official scope unresolved | 3 |
| total | 20,797 |

Decision-invariant failure diagnostics:

| Diagnostic | Count |
|---|---:|
| OCF positive in fewer than 4 of 5 years | 5,913 |
| five-year FCF sum nonpositive | 9,162 |
| both | 4,613 |

Canonical diagnostic-record hash:

```text
sha256:db8aadb7a9df211cc048fd8b8d2534e2e88d2c38486fd88491b9f40ef1e8f585
```

## 5. Screen history

| Screen | Invariant pass | Hard fail | Ambiguous | O/N unresolved | Total |
|---|---:|---:|---:|---:|---:|
| 20170502 | 822 | 1,159 | 13 | 1 | 1,995 |
| 20180502 | 859 | 1,169 | 5 | 1 | 2,034 |
| 20190506 | 917 | 1,126 | 8 | 2 | 2,053 |
| 20200506 | 1,046 | 1,086 | 11 | 0 | 2,143 |
| 20210506 | 1,165 | 1,051 | 8 | 0 | 2,224 |
| 20220505 | 1,229 | 1,192 | 11 | 2 | 2,434 |
| 20230504 | 1,359 | 1,241 | 11 | 1 | 2,612 |
| 20240506 | 1,423 | 1,202 | 9 | 1 | 2,635 |
| 20250506 | 1,424 | 1,236 | 5 | 2 | 2,667 |

Additional stability facts:

- 1,111 instruments are cash-flow-invariant passes in each of the latest three screens.
- 362 instruments are cash-flow-invariant passes in all nine screens in which the full history is available.
- Latest-screen invariant-pass set hash: `sha256:48ecc472a19f26959a35abd7511527422c736eeb23041c508bc88269ca2a3e0f`.
- Latest-three-screen persistent set hash: `sha256:542b018adf9bb59ca0c103dc7554d5721356dc57d9e9e80d2843cbff4368f4d4`.

## 6. Why cash-flow ranking cannot select four stocks

A diagnostic ranking of the 1,424 latest-screen invariant passes by conservative five-year `FCF / revenue` lower bound was reproducible, but its top results were dominated by accounting/business-model effects:

- `600239` ST云城 and several property companies showed ratios distorted by low revenue denominators or asset cash flows;
- road/bridge concession companies occupied many top positions;
- the list also contained more conventionally cash-generative issuers such as 长江电力 (`600900`), 分众传媒 (`002027`) and 贵州茅台 (`600519`).

Ranking hash:

```text
sha256:b14e53f9c96fe814815c525acceba3a71b623cf4afaace46c7118a9185f57823
```

This mix demonstrates that cash-flow margin alone is not a substitute for the frozen ROIC, leverage, statement-scope and permanent-loss checks. Adding an ad hoc ST, sector, size or outlier rule would be a new strategy decision and is not permitted by the existing-data boundary.

## 7. Existing-price BOLL signal inventory

The strongest immutable local price source already present is:

```text
/srv/bcache-8t/ygguo/duckdb/quant-a50/
  quant_a50.duckdb.backup_20260521_daily_basic_2015
sha256:cdc6ce41dee3fe9903d8c27ec5cc584455ad423989cd79e3eb0187c5bba8bd41
```

Its daily `MarketData` coverage ends on `2026-05-20`. It has no accepted corporate-action lifecycle or point-in-time adjustment authority, so this section is raw-price advisory evidence only.

The 1,424 latest-screen cash-flow-invariant passes were scanned over the final 60 sessions using the frozen technical setup:

```text
BOLL(20,2)
current bandwidth <= rolling 120-session 10% quantile
close crosses from at/below the prior upper band to above the current upper band
volume >= 1.5 * rolling 20-session median volume
SMA20 slope positive
```

Results:

- 97 advisory crossing events in the final 60 available sessions;
- signal-set hash: `sha256:67dd2e4f6524ebc13df0d5aad4875510e2c0cd716ed13c879877ce7f26788c7a`;
- on the final available session, `2026-05-20`, exactly one event: `600237` 铜峰电子, volume multiple approximately `2.44`.

This is not a current signal. The price evidence is more than three months stale relative to the owner decision date, has no corporate-action closure, and cannot produce a T-close/T+1 instruction. No TargetSnapshot or execution request is emitted.

## 8. Conclusion

Existing data can conservatively identify 10,462 provisional cash-flow failures and a 1,424-member latest-screen cash-flow-invariant pass pool. It cannot determine a formal financial-qualified set or defensibly select four stocks.

The honest terminal result is therefore:

```text
formal_s2_qualified = false
strategy_target_authorized = false
backtest_authorized = false
validation_authorized = false
deployment_authorized = false
```

No TargetSnapshot, execution request or trading instruction is produced.
