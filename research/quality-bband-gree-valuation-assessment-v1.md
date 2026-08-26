# Quality + B-Band Gree valuation assessment v1

- **Status:** `EXPLAINED_DECISION_INVARIANT / FIXED_ISSUER_VALUATION_PASS / SOURCE_BOUNDED`
- **Checked:** 2026-08-26
- **Issuer:** `xshe:000651`
- **Assessment date:** `2024-05-06`
- **Policy:** [`quality-bband-reasoned-ambiguity-policy-v1.md`](quality-bband-reasoned-ambiguity-policy-v1.md)

## 1. Retained source candidate

Valid candidate:

```text
/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/
  valuation-source-snapshots/000651.SZ/20190506-20240506/v1-candidate-02
```

| Identity | Value |
| --- | --- |
| Implementation commit | `5b99e50826a526cfd81ea8a28d2a1d1bf3daf52c` |
| SourceSnapshot | `sha256:97120ac129e6bb8fb63b2dfdbb141e6501d281d01011fb1120bb1d29c8228c30` |
| Content tree | `sha256:e50d7d8dc5a8bf2877de6d8797ca4ec5e8e28e79f2cebc9d6c1e09f433c83ba9` |
| Provenance | `sha256:f1e9b0404f3bdcbe2ca1d3cdd9e094defb9e31704c42f30db7ba79af282cdd19` |
| Raw response | `sha256:7ead16909fa4884a8b90ea76093548a28b10c66c86f4b5d8146fb65c823a6793` / `103,568` bytes |
| Rows | `1,213` unique trading dates |
| Fixed window | `2019-05-06..2024-05-06` |
| Response-received timestamp | `1787714984624149882` epoch nanoseconds |

`v1-candidate-01` is retained as invalid evidence. Its raw data rows equal candidate 02, but its timestamp was captured before transport rather than after response receipt.

## 2. Why two valuation interpretations are retained

The frozen strategy permits positive `EV/EBIT` or PE below the issuer's five-year 60th percentile. PE is used for this fixed assessment because it avoids importing the unresolved 2021 debt interval into enterprise value.

Two evidence-supported PE interpretations are retained:

1. provider `pe_ttm`, advisory because denominator lineage and formula version are absent;
2. self-recomputed annual PE:

```text
annual_pe(date)
= daily_basic.total_mv(date) * 10,000
  / latest available annual n_income_attr_p
```

The latest annual denominator changes only at the conservative availability boundaries already frozen for the issuer:

| Effective session | Annual period | Attributable profit, CNY |
| --- | --- | ---: |
| window start through `2020-05-05` | `20181231` | `26,202,787,681.42` |
| `2020-05-06` | `20191231` | `24,696,641,368.84` |
| `2021-04-30` | `20201231` | `22,175,108,137.32` |
| `2022-05-05` | `20211231` | `23,063,732,372.62` |
| `2023-05-04` | `20221231` | `24,506,623,782.46` |
| `2024-05-06` | `20231231` | `29,017,387,604.18` |

The 2021 debt-scope conflict does not affect attributable profit and therefore does not affect this PE interpretation.

## 3. Current observation

The retained `2024-05-06` row states:

```text
close = 43.41 CNY
total_share = 5,631,405,741 shares
total_mv = 24,445,932.3217 * 10,000 CNY
market value = 244,459,323,217.00 CNY
provider pe = 8.4246
provider pe_ttm = 8.2634
```

Self-recomputed annual PE:

```text
244,459,323,217.00 / 29,017,387,604.18
= 8.424580687676558889...
```

This reproduces provider `pe = 8.4246` to its displayed precision.

## 4. Five-year percentile decision

All retained positive observations are used; the current observation is included. The nearest-rank 60th percentile and empirical current rank are:

| Interpretation | Current | 60th-percentile boundary | Current empirical percentile rank |
| --- | ---: | ---: | ---: |
| provider `pe_ttm` | `8.2634` | `12.3040` | `34.0478%..34.1303%` |
| self-recomputed annual PE | `8.4245806877` | `12.5214906931` | `26.2160%..26.2984%` |

The lower/upper rank bounds distinguish `< current` and `<= current`. Both are comfortably below `60%`; including/excluding the single current observation cannot change the decision.

```text
valuation percentile < 60% = invariant pass
```

## 5. Positive FCF yield

Using the frozen canonical annual formula rather than provider `free_cashflow`:

```text
2023 FCF
= n_cashflow_act - c_pay_acq_const_fiolta
= 56,398,426,354.17 - 5,425,734,302.92
= 50,972,692,051.25 CNY

FCF yield
= 50,972,692,051.25 / 244,459,323,217.00
= 20.8511957656%
```

The required positive-FCF-yield condition is an invariant pass. This is a research assessment, not an accepted `valuation_observation_revision@1` or feature manifest.

## 6. Decision

```text
provider PE interpretation = pass
self-recomputed annual PE interpretation = pass
positive FCF yield = pass
ambiguity classification = EXPLAINED_DECISION_INVARIANT
fixed-issuer valuation gate at 2024-05-06 = pass
```

Together with [`quality-bband-gree-governance-audit-v1.md`](quality-bband-gree-governance-audit-v1.md) and the existing financial-quality assessment, the fixed issuer passes the currently frozen quality, audit, literal pledge and valuation thresholds, with the recorded largest-shareholder pledge and acquisition advisories.

This does **not** authorize cross-sectional rank selection or a trade. The valuation score must remain an interval of at least `26.2160%..34.1303%`; overlapping score intervals at a top-four cutoff remain `RANKING_AMBIGUOUS`. General Universe, corporate-action, liquidity, technical-signal and public multi-stock preparation authority are still missing.
