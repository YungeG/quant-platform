# Quality + B-Band historical selection/formula coverage v1

- **Status:** `EXACT_SOURCE_GAP_RETAINED / THRESHOLD_DECISION_INVARIANT / CONTINUATION_ALLOWED`
- **Checked:** 2026-08-26
- **Scope:** `xshe:000651`, annual periods `20181231` through `20231231`
- **Inputs:** Backtest PR #8 historical normalization candidate plus PR #5 2023 selection candidate

## 1. Decision

Do not rewrite the historical source/declaration/normalization artifacts. Apply [`quality-bband-reasoned-ambiguity-policy-v1.md`](quality-bband-reasoned-ambiguity-policy-v1.md) above them.

The exact source layer still cannot produce one point-valued 2021 debt result. The finite narrow/broad candidates can nevertheless support downstream research when every candidate produces the same required decision.

`20211231 / DEBT_SCOPE_INCOMPLETE` remains a source-exactness blocker, but it is not a blocker for the `ROIC >= 20%` financial-quality threshold.

## 2. Exact selected input map

Every valid historical observation set contains only fixed `CURRENT_CONSOLIDATED` revisions and no competing presentation. Their mechanically unique active inputs are:

| Period | Set / selection identity | Active revisions |
| --- | --- | --- |
| `20181231` | set `sha256:20638846aa5eb0c98e30efcae5693114553ef8794a2697783d740ec658d38c68` | balance `sha256:c3be5c3de8b458180a350e8e0c84ba3618fc23393c51817e1c2fd823f9cf4148` only |
| `20191231` | set `sha256:02bb2571ea9cef06465f0151b747004c34f4baa35b5d59b63e71f65c707fd7d1` | income `sha256:176122a6db10c8ee7ec20eb2862632dc19cbdae9d1e1537c0a98708d3ac5b231`; balance `sha256:c898675a1b7b5db86cf7d4db1cace6fb27045f4214ea351a3ef4974523f0e7b3`; cash flow `sha256:22438762ffb7532e9653d354686eae61b3812172e4868825f87691ccc5cd1349` |
| `20201231` | set `sha256:2c6110a07d2a7c80745a3cabf35b84b4aeb13f1cd4901d53c24cca619c40f4ce` | income `sha256:35d35b0856b6cecb8d8bb79c21d48058e44fcc51f6a7bd6c9c23a73a26b4a0ca`; balance `sha256:f883c487f930e3a58706965678bebabbb3fc5f200e2304fc521d3d4ace2ed7b6`; cash flow `sha256:7d991e01d78363478e53a95401156a9f035120ae393c96cfcbccd680d80393b1` |
| `20211231` | failure `sha256:2cedd67871396e99f324623540ac66f1b254d31020d0e81ba075c6b5876bbc82` | none |
| `20221231` | set `sha256:92d196719be464dc79938db432f442e2d56891effd04adb7e11031f6e31fe736` | income `sha256:ad1037c494eb4e79f215c4a342d814a5f3478ffcc1042bce61cc570b16ce761f`; balance `sha256:b3b9a5f5bf4dcdbfdeed4e9a2f53a6bfdc5f72655c7cbe3bdb521364bee5c396`; cash flow `sha256:7812b0f8fd492e70a6a4aaa23dff33dbd0a4db9bf347b19e403bc3d55eb0387b` |
| `20231231` | selection `sha256:34d09c7649143ee784f95f25873dd462ee56fc37cae91fa8bc7a604ef37f890c` | income `sha256:8957590f45f32ed9b285e940f2fa0c0524cb28377e86c745ab39aa3875ba63e8`; balance `sha256:3e64ee623ca3676f1ec10daf56588dceabdd77a41ba0419d4c9010241313f45d`; cash flow `sha256:71f4428e79d3bd7638cc9c1d98c1471f9802e9a90d25f7fa06b739bc57f0f986` |

This map is a planning fact, not an accepted general presentation selector. Comparative-adjustment and provider revision-chain coverage remain unexercised.

## 3. Formula-input availability

QB-FIN-FIELDS-01 requires:

```text
ROIC(Y) = NOPAT(Y) / average(closing_invested_capital(Y-1), closing_invested_capital(Y))
```

Therefore one ROIC year requires the current annual trio plus the immediately preceding closing balance endpoint.

| Formula year | Current trio | Prior balance endpoint | Earliest complete boundary | Decision |
| --- | --- | --- | --- | --- |
| `2019` | available | `2018` available | `2020-05-06 09:30 Asia/Shanghai` | complete input |
| `2020` | available | `2019` available | `2021-04-30 09:30 Asia/Shanghai` | complete input |
| `2021` | unavailable | `2020` available | none | `DEBT_SCOPE_INCOMPLETE` |
| `2022` | available | `2021` unavailable | none | `PRIOR_CAPITAL_ENDPOINT_MISSING` |
| `2023` | available | `2022` available | `2024-05-06 09:30 Asia/Shanghai` | complete input |

Exact source outcome:

```text
complete exact ROIC inputs = 2019, 2020, 2023
point-valued exact inputs missing = 2021, 2022
```

Ambiguity-qualified outcome:

```text
2021 ROIC interval = [118.8062%, 127.2984%]
2022 ROIC interval = [75.0674%, 78.2238%]
five-year median interval = [118.8062%, 127.2984%]
ROIC >= 20% = invariant pass
```

## 4. Same-year formula coverage

The four valid annual trios exact-cover the same-year raw inputs for:

- EBIT and EBITDA;
- NOPAT/effective tax rate;
- operating cash flow and source-derived FCF;
- ending invested capital;
- net debt and net-debt/EBITDA.

| Year | Same-year formulas | ROIC |
| --- | --- | --- |
| `2019` | input-complete | input-complete |
| `2020` | input-complete | input-complete |
| `2021` | unavailable | unavailable |
| `2022` | input-complete | unavailable: missing 2021 opening capital |
| `2023` | input-complete | input-complete |

The 2022 provider `free_cashflow` conflict does not block source-derived FCF because canonical FCF uses `n_cashflow_act - c_pay_acq_const_fiolta`; neither provider advisory value is selected.

## 5. Strategy-quality consequence

The point-valued exact five-year manifest remains unavailable. The ambiguity-qualified financial assessment can establish:

- five-year ROIC median is robustly above `20%`;
- operating cash flow is positive `5/5` years;
- cumulative source-derived FCF is `107,662,796,746.80 CNY` and positive;
- 2023 net debt/EBITDA is `-0.8663154`, below `1.5`.

```text
exact point-valued quality score = unavailable
financial-quality threshold result = robust pass
cross-sectional ranking value = interval
ranking at an overlapping cutoff = blocked
fixed-issuer financial research = may continue
```

Audit-opinion, governance/penalty, pledge, valuation, Universe and execution authority remain separate blockers.

## 6. Failure propagation

```text
2021 DEBT_SCOPE_INCOMPLETE
→ no exact 2021 declaration/set
→ retain narrow and broad candidates
→ calculate 2021/2022 ROIC under both
→ threshold decision identical
→ ambiguity-qualified robust pass
→ exact point ranking remains interval-sensitive
```

A 2021 balance-only exception is forbidden because PR #8 intentionally made the period atomic. Introducing one now would create a new architecture and weaken the accepted fail-closed boundary.

## 7. Next action

The source-resolution attempt is recorded in [`quality-bband-2021-debt-scope-resolution-v1.md`](quality-bband-2021-debt-scope-resolution-v1.md). It found no explicit correction, so exact source artifacts remain unchanged.

Next:

1. retain the broad interpretation as preferred and both candidates as evidence;
2. carry the ROIC/median intervals into the future feature assessment;
3. continue only while threshold and top-N membership are invariant across the interval;
4. move to the next missing data authority rather than continuing to search the same exhausted source lane.

No MarketBundle, Strategy, Validation, Live or deployment authority is granted.
