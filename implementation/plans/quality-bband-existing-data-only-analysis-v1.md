# Quality-BBAND existing-data-only analysis v1

- **Status:** `OWNER_APPROVED / NO_NEW_DATA`
- **Approval date:** `2026-08-27`
- **Owner decision:** `我们只根据已有的数据进行分析，不再补充其他数据。`
- **Strategy:** `cn-a-share.quality-bband-breakout.manual4.v1`

## Acquisition boundary

Effective immediately:

- no new official or provider acquisition;
- no data purchase, procurement RFI, PDF/note capture, archive backfill, or supplemental declaration build;
- no later evidence may be used to backfill an earlier decision;
- existing immutable artifacts remain the complete analysis evidence set.

## Frozen evidence set

1. Preferred formal Tushare S1 candidate-02, manifest `dcd0fecb…`.
2. Preferred S1→S2B binding candidate-02, manifest `c54bac98…`.
3. S2B candidate-02: `96,537 = 96,515 P + 1 O + 21 N`.
4. Accepted S2A candidate-02, periods 2012–2024.
5. Accepted Stage-A 2011 balance snapshot `2bad8575…`.
6. Accepted prior-balance binding `1b34a721…`: `20,797 = 17,952 + 850 + 1,995`; augmented scope 99,382.
7. Accepted official O/N evidence already present in those artifacts.

## Analysis classification

All further financial analysis is:

```text
EXISTING_DATA_ONLY
PROVIDER_SCOPED
PROVISIONAL
NON_DECISION_GRADE
```

It is not formal S2 authority and does not establish official legal availability, revision supersession, unit/consolidation authority, financing-note scope, coherent official trio selection, Strategy targets, Backtest, Validation, Promotion, deployment, or trading authority.

## Permitted analysis

- Reproduce exact immutable input identities, row candidates, pair classes and hashes.
- Compute diagnostics and metric intervals only from existing retained rows.
- Preserve every revision candidate; `update_flag`, row order and provider dates are never automatic selectors.
- Use point values only when all retained admissible candidates produce the same result under the declared provider-scoped calculation.
- Use intervals when candidate rows differ and the result can be bounded.
- Emit `UNRESOLVED_DECISION_MATERIAL` when the available candidates cannot support a decision-invariant result.
- Accepted N and unsupported O records remain issuer-local, numeric-free unresolved records.
- Missing fields are never zero, hard failure, silent exclusion, slot release, or unrelated-issuer block.

## Existing pair diagnostics

The frozen existing-data partition is:

| Pair class | Count |
|---|---:|
| P/P/P | 32,171 |
| P/O/P | 1 |
| N/N/N | 7 |

Provider-only trio diagnostics:

| Candidate class | Count |
|---|---:|
| exactly one common provider date candidate | 31,213 |
| multiple common provider date candidates | 75 |
| no common provider date candidate | 883 |

These provider-date classes are diagnostic only and supply no legal availability or supersession authority.

## First existing-data-only cash-flow diagnostic

A deterministic double recomputation over all retained cash-flow revisions produced 20,797 screen/issuer records.

Method:

- accepted N or unsupported O evidence takes issuer-local unresolved precedence;
- for each provider-scoped record, retain every cash-flow revision across the five required years;
- compute the minimum/maximum possible count of years with `n_cashflow_act > 0`;
- compute `free_cash_flow = n_cashflow_act - c_pay_acq_const_fiolta` for every numeric candidate and a five-year sum interval only when every retained candidate is numeric;
- do not select by `update_flag`, row order or provider date;
- label a result a **provisional provider-scoped hard-filter failure** only when failure is decision-invariant across all retained candidates;
- otherwise remain unresolved because ROIC, leverage and authority inputs are unavailable.

Results:

| Existing-data-only disposition | Count |
|---|---:|
| provisional hard-filter failure | 10,462 |
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

Canonical diagnostic record hash:

```text
sha256:db8aadb7a9df211cc048fd8b8d2534e2e88d2c38486fd88491b9f40ef1e8f585
```

These are advisory existing-data-only results. `provisional hard-filter failure` is not a formal-S2 disposition, Strategy exclusion, target instruction or execution authority.

## Authority flags

All existing formal-S1 and exact-cover flags remain as accepted. The following remain false:

```text
formal_s2_qualified
financial_scope_qualified
decision_grade_eligible
strategy_authorized
strategy_target_authorized
backtest_authorized
validation_authorized
deployment_authorized
```

## Next artifact

The next permitted artifact is an existing-data-only diagnostic/interval analysis manifest. It must bind the exact evidence set, declare every calculation and ambiguity class, publish no Strategy target, and preserve all authority ceilings above.
