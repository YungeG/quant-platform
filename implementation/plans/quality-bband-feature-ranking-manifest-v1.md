# QB-RANK-01 — Quality + B-Band interval-aware feature and ranking manifest v1

- **Status:** `CONTRACT_FROZEN / INDEPENDENTLY_ACCEPTED / PLAN_ONLY / FULL_MARKET_INPUTS_MISSING`
- **Strategy:** `cn-a-share.quality-bband-breakout.manual4.v1`
- **Consumer:** future deterministic Strategy Build and precomputed target-stream authority

## 1. Outcome

Freeze exact canonical rank factors, valuation interpretation, candidate-vector ambiguity handling and top-slot cutoff semantics.

Ranking applies only to non-held issuers that:

- are quality-qualified under QB-ELIG-01;
- pass new-entry valuation, FCF-yield and liquidity filters;
- have a complete T-close B-Band breakout signal for the active precommitted volume multiple;
- remain eligible for slots not occupied by actually held positions at T close.

Existing continued holdings are never reranked against new entries.

This is a Strategy Build stock-ranking artifact. It does not extend, reuse or reinterpret Research Platform `SelectionPolicy`, which remains limited to completed Experiment-trial selection by admitted metrics such as `simple_period_return` and `trade_count`.

## 2. Canonical feature manifest

Provisional artifact name:

```text
cn_a_share_quality_feature_manifest@1
```

One issuer/decision manifest exact-binds:

- Strategy/build identity and parameter set;
- decision `SimulationInstant`;
- final composite QB-DATA authority plus relevant S1 structural, S2 financial, S3 governance/valuation and S4 market/action manifest refs;
- issuer Instrument identity;
- quality/continuation/entry disposition refs;
- exact source observation/revision refs;
- evidence-supported interpretation domains;
- hard-filter outcomes;
- canonical rank-factor values or intervals;
- manifest hash and limitations.

Provider-computed ROIC, FCF, leverage, PE or composite scores cannot become canonical without exact formula/source lineage.

## 3. Canonical rank factors

Exactly three equal-weight factors:

| Factor key | Canonical value | Better direction |
| --- | --- | --- |
| `roic_median_5y` | median of the five frozen annual ROIC values | higher |
| `valuation_percentile_5y` | current canonical annual PE's issuer-history percentile | lower |
| `net_debt_to_ebitda` | latest available annual canonical net debt / EBITDA | lower |

### ROIC

Use the already frozen industrial-company ROIC formula and point-in-time selected statement refs. Evidence-supported debt/presentation interpretations produce candidate ROIC vectors and a retained median interval. No preferred midpoint is canonical.

### Canonical PE

For v1 ranking, canonical PE is self-recomputed annual PE:

```text
annual_pe(D)
= total_market_value_cny(D)
  / latest annual attributable profit available at D
```

Requirements:

- numerator and denominator are exact-bound retained observations;
- both are positive;
- denominator availability is not later than `D`;
- no quarterly/TTM provider denominator is imported;
- provider `pe`/`pe_ttm` may be advisory only.

This prospective choice is based on denominator lineage and avoidance of provider-formula ambiguity. It applies only to the precommitted future full-market Experiment. It does not rewrite the earlier fixed-issuer assessment, collapse that assessment's annual/TTM interval or authorize a retrospective exact Gree rank.

### Five-year valuation percentile

Window:

```text
[D minus five calendar years, D]
```

inclusive on both endpoints, using the same February-29→February-28 Strategy convention as QB-UNIV-CA-01.

Use every complete eligible valuation observation in the window. Calendar/status coverage must explain sessions without an observation, such as suspension; unexplained gaps are authority failures.

For current value `x` among `N` positive canonical annual-PE observations:

```text
less = count(value < x)
equal = count(value = x)
valuation_percentile_5y
= (less + equal / 2) / N
```

Exact rational/Decimal arithmetic is required. The current observation is included. `N > 0` is required. The new-entry hard filter is exactly:

```text
valuation_percentile_5y < 0.60
```

The earlier Gree assessment used nearest-rank boundaries and empirical rank bounds rather than this canonical midrank formula; every retained method passed, so its threshold decision remains invariant while its historical interpretation interval remains unchanged.

### Net debt / EBITDA

Use the latest available annual canonical values:

```text
net_debt_to_ebitda
= (interest_bearing_debt - cash_and_cash_equivalents) / EBITDA
```

EBITDA must be positive. Negative ratios are valid and rank ahead of positive ratios. Any evidence-supported numerator/denominator interpretations remain candidate values; no clipping or winsorization is permitted.

## 4. Interpretation domains

The ambiguity policy permits finite candidate sets and exact-bounded continuous intervals. Neither may be discarded.

One issuer `feature_interpretation_domain` is exactly one of:

- `FINITE_VECTORS`: correlated exact factor triples with stable interpretation keys;
- `CONSTRAINED_INTERVAL_SET`: exact factor bounds plus preserved correlation/equality/ordering constraints and source explanation.

Each domain retains source/declaration/observation refs, shared interpretation-group identities and ambiguity classification. Values affected by the same debt/presentation explanation remain correlated. Cross-issuer shared interpretations are constrained jointly; otherwise issuer domains vary independently.

The assessor must prove the decision over every admissible point in every domain. It may use interval dominance, constraint solving or exact finite enumeration, but inability to prove invariance returns `RANKING_AMBIGUOUS`; it never samples, chooses a midpoint or silently narrows the domain.

## 5. Cross-sectional factor scores

For one exact global interpretation, let `N` be the number of entry-eligible candidates.

For each factor and issuer, compute an exact midrank:

```text
better = count(strictly better factor values)
equal = count(equal factor values)
midrank = better + (equal + 1) / 2
```

Normalize so higher score is better:

```text
factor_score = 1                                  if N = 1
factor_score = 1 - (midrank - 1) / (N - 1)       if N > 1
```

Direction defines “better” from the table above. Factor equality is exact canonical Decimal equality. Midrank avoids injecting Instrument identity into factor economics.

Composite score:

```text
composite_score
= (roic_score + valuation_score + leverage_score) / 3
```

No extra weights, sector neutralization, price-level preference, winsorization, z-score, volatility term, momentum term or liquidity bonus is authorized.

## 6. Tie-break and ordering

For one exact interpretation, order by:

1. `composite_score` descending;
2. `roic_score` descending;
3. `valuation_score` descending;
4. `leverage_score` descending;
5. canonical `InstrumentId` ascending.

The tie-break is deterministic only; it does not alter factor scores.

## 7. Available slots and T-close selection

Pending exits still occupy positions until execution is confirmed. Holdings must be unique canonical Instruments and satisfy `0 <= actual_held_instrument_count <= 4`. At T close:

```text
available_slots = 4 - actual_held_instrument_count
K = min(available_slots, entry_eligible_count)
```

- `available_slots = 0`: publish no new-entry ranking.
- `entry_eligible_count <= available_slots`: select every entry-eligible issuer; ordering is retained only for deterministic identity.
- otherwise select the invariant top `K` under the frozen ordering.

T+1 gap, suspension/tradability and 100-share/50,000-CNY execution checks apply only to those T-close-selected names. If a selected name fails at T+1, do not promote a lower-ranked issuer at that same open; leave the slot in cash and wait for a later complete signal. QB-RANK-01 does not invent a same-open replacement or atomic sell-before-buy authority.

## 8. Decision invariance

The ranking assessor considers every admissible global interpretation-domain combination.

It may return success only when every admissible interpretation yields:

- the same actually occupied slot count;
- the same selected T-close new-entry membership;
- the same canonical tie-break result wherever ordering is consumed.

Different numeric scores are allowed when selected/trade decisions remain identical. The output retains score/rank intervals across interpretations.

If selected T-close membership changes, return:

```text
RANKING_AMBIGUOUS
```

No midpoint, preferred economic interpretation or provider value may break the ambiguity.

## 9. Provisional ranking manifest

Provisional artifact name:

```text
cn_a_share_quality_ranking_manifest@1
```

Fields include:

- Strategy/build/parameter identity;
- decision instant;
- final composite/S1–S4/eligibility/holding refs;
- available slots and active volume multiple;
- exact entry-candidate Instrument set;
- ordered factor definitions and formula version;
- per-issuer interpretation-domain refs;
- per-factor and composite score intervals;
- rank-position intervals;
- selected T-close top-`K` set/order when invariant;
- ambiguity witness pairs when blocked;
- canonical tie-break definition;
- source limitations;
- derived manifest hash.

A blocked assessment emits an immutable failure artifact/witness but no successful ranking manifest, target snapshot, target event or execution request.

## 10. Failure precedence

1. manifest/input/strategy/version mismatch;
2. MarketBundle, Universe, eligibility or holding-ref mismatch;
3. candidate set differs from exact S4 `ENTRY_ELIGIBLE_POINT`/`ENTRY_ELIGIBLE_INTERVAL` non-held output or contains duplicate/foreign Instruments;
4. missing or invalid source/feature interpretation domain;
5. factor formula, direction or Decimal-domain failure;
6. interpretation-domain/group inconsistency;
7. score/rank exact-cover mismatch;
8. `RANKING_AMBIGUOUS`;
9. successful thin/full invariant prefix.

Upstream QB-DATA or QB-ELIG failures retain precedence and never become ranking failures.

## 11. Gree implication

For the fixed issuer:

- canonical future valuation ranking uses self-recomputed annual PE, not provider TTM PE;
- 2021 debt interpretations retain the five-year ROIC median interval;
- 2023 net debt/EBITDA is point-valued under the retained fixed-report assessment;
- the `ROIC >= 20%` and valuation `< 60%` hard thresholds pass;
- no cross-sectional rank or top-four selection exists until complete peer manifests are available.

The fixed-issuer pass does not imply selection. If a peer domain can change top-`K` membership, the whole decision date blocks.

## 12. Readiness decision

The factor/ranking contract is independently accepted for planning. Implementation is blocked by canonical constrained-domain/proof-witness encoding, full-market immutable inputs, Backtest-owner artifact-name approval, exact T+1 selected-name execution semantics, public multi-stock preparation and accepted PRs #1–#9.
