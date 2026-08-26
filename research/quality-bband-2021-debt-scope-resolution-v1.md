# Quality + B-Band 2021 debt-scope resolution attempt v1

- **Status:** `EXACT_VALUE_UNRESOLVED / BROAD_INTERPRETATION_PREFERRED / THRESHOLD_NONBLOCKING`
- **Checked:** 2026-08-26
- **Issuer/period:** `xshe:000651` / `20211231`
- **Existing conflict:** `sha256:8cb5ef55e745b6e3858eef5bb1806ebf22c9123490764e79e68f2928ffb66c6f`

## 1. Question

Does competent official authority establish whether the 2021 year-end line

```text
企业借款及利息 2,731,680,114.20
```

must be included in canonical interest-bearing debt?

## 2. Contemporaneous 2021 evidence

Official 2021 annual report:

- CNINFO announcement `1213262535`;
- document `sha256:96065ec44285bce7a9c0cbee25dfeb2368ec4552d72f06ebf3ecab35136e2444`;
- note 35, report page 187/PDF page 188 classifies `2,731,680,114.20` as `企业借款及利息` inside other payables;
- the same report states there is no separately presented interest payable at period end;
- report page 222/PDF page 223 explicitly introduces `截至2021年12月31日，公司有息负债情况如下` and prints total `43,546,910,016.46`;
- that explicit table omits other payables and therefore omits the enterprise-borrowing line.

Candidate results remain:

```text
narrow = 43,546,910,016.46 + full lease 14,785,264.79
       = 43,561,695,281.25

broad  = narrow + enterprise borrowing and interest 2,731,680,114.20
       = 46,293,375,395.45
```

The line label supports the broad candidate, while the exact contemporaneous interest-bearing table supports the narrow candidate. Neither can silently override the other.

## 3. Later 2022 evidence

Official 2022 annual report:

- CNINFO announcement `1216702261`;
- document `sha256:7cfc80c2badbf4cd74c5adc080d5072b02cd6c700b04fa7ca0ac44cb8b8fe987`;
- its other-payables note carries the exact `2,731,680,114.20` as the 2021 opening comparative under the same `企业借款及利息` label;
- its 2022 closing amount is `1,621,102,937.08`;
- its current-period interest-bearing table includes `其他应付款 1,621,102,937.08` and assigns `4.00%-5.00%` floating interest.

This is strong support that the category is interest-bearing in 2022. It is **not** an explicit correction or comparative classification of the 2021 balance:

- the 2022 interest-bearing table is current-period only;
- it supplies no comparative 2021 interest-bearing column or rate;
- it does not state that the 2021 table was erroneous, incomplete, corrected or restated;
- label continuity and later-period treatment cannot create an inferred supersession relation.

Therefore the later report strengthens the broad candidate but does not resolve the conflict.

## 4. Correction/inquiry search

CNINFO public announcement query:

```text
stock = 000651,gssz0000651
column = szse
range = 2022-04-01 through 2023-06-30
category = all
page size = 30
pages = 1..5
announcements = 135
```

Exact response hashes:

| Page | Rows | SHA-256 |
| ---: | ---: | --- |
| 1 | 30 | `sha256:9a1a768f8ca3c83390f3b731d0b7993601cc43643132899b9a94eafa0904e44d` |
| 2 | 30 | `sha256:b5a42f2c2d4db32f6fda4d0ef247144aacb5c96a89b5fe755a2806fb1bd96538` |
| 3 | 30 | `sha256:38cf45e999167ef9b5125682316d8d2bc2a8e1df2ae72072c053a148a3a79238` |
| 4 | 30 | `sha256:996a7dcd20a683b4b843606d319c4cf98c3725869a413a9ac6c229549b7cad93` |
| 5 | 15 | `sha256:ea9dff5b47ac0bf3544e00f36b332bae09dc1daa50bc5ba2c732b03d1f63d922` |

No announcement title identified a 2021 annual-report correction, supplement, annual-report inquiry/reply or explicit debt reclassification. Searches of SZSE/CNINFO/issuer public results also found no competent issuer or exchange answer addressing this exact 2021 balance.

Absence of a discovered correction is not proof that none can ever exist, but no qualifying authority is presently available.

## 5. Resolution standard

The conflict may be closed only by one of:

1. an explicit annual-report correction or restatement;
2. a comparative interest-bearing-debt disclosure that includes/excludes the exact 2021 amount;
3. an exchange inquiry/reply or issuer statement addressing the 2021 classification;
4. equivalent competent evidence exact-binding the amount and period.

A later current-period classification, generic accounting definition, provider ratio, analyst calculation or semantic reading of `借款及利息` is insufficient against the contradictory contemporaneous table.

## 6. Verdict

```text
2021 canonical debt = unavailable
source failure = DEBT_SCOPE_INCOMPLETE
preferred research interpretation = broad
retained interval = [43,561,695,281.25, 46,293,375,395.45]
ROIC >= 20% decision = invariant pass
```

The broad amount is the most reasonable economic interpretation, but the narrow amount remains evidence. Under [`quality-bband-reasoned-ambiguity-policy-v1.md`](quality-bband-reasoned-ambiguity-policy-v1.md), Research may continue for decisions invariant across both candidates. Any future exact resolution must publish new declaration/normalization identities and cannot rewrite existing failure evidence.

## 7. Next decision

No source-layer rewrite is warranted unless new competent evidence appears.

The contradiction is recorded and carried forward as an interval. It does not block the fixed `20%` financial-quality threshold because all reasonable interpretations pass, but it can block future cross-sectional ranking if another issuer's score overlaps the interval.
