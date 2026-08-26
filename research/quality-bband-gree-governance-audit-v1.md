# Quality + B-Band Gree governance/audit assessment v1

- **Status:** `FIXED_ISSUER_SOURCE_BOUNDED / AUDIT_PASS / PENALTY_PASS_WITH_MINOR_ADVISORY / PLEDGE_NOT_APPLICABLE_WITH_MAJOR_HOLDER_ADVISORY`
- **Checked:** 2026-08-26
- **Issuer:** `xshe:000651`
- **Policy:** [`quality-bband-reasoned-ambiguity-policy-v1.md`](quality-bband-reasoned-ambiguity-policy-v1.md)

## 1. Outcome

For the fixed issuer, the currently frozen annual-report evidence supports:

```text
latest audit opinion gate = pass
confirmed major financial-fraud/severe issuer-penalty gate = source-bounded pass
controlling-shareholder pledge gate = not applicable, because no controlling shareholder exists
largest-shareholder pledge = material advisory risk, not a post-hoc hard failure
major acquisition history = material comparability/thesis advisory
```

This does not prove cross-regulator or full-market terminal-set completeness.

## 2. Audit opinions

Every retained annual report states `标准的无保留意见`; the internal-control opinion is also standard unqualified.

| Period | Official report hash | Audit result |
| --- | --- | --- |
| `20181231` | `sha256:b147eb6b8a4aaf093f3b83550c70e8526415b5b54fe24e4258ce7bfd11d5406a` | standard unqualified |
| `20191231` | `sha256:1b4869caab122969b322738df69955d788c8dc19b4c6d57188619177e922e708` | standard unqualified |
| `20201231` | `sha256:0d3c39090adf97fede39149a731a5636bd0eca2002606fb942ca70121dba9072` | standard unqualified |
| `20211231` | `sha256:96065ec44285bce7a9c0cbee25dfeb2368ec4552d72f06ebf3ecab35136e2444` | standard unqualified |
| `20221231` | `sha256:7cfc80c2badbf4cd74c5adc080d5072b02cd6c700b04fa7ca0ac44cb8b8fe987` | standard unqualified |
| `20231231` | `sha256:32ebc475a2291ce4f1b5c1a9f9da55227e03192f07e75041e976c29d213ec8aa` | standard unqualified |

The strategy's `最近审计意见非保留` condition is therefore an exact fixed-report pass.

## 3. Company penalty/fraud evidence

The 2019–2023 annual reports each state that the company had no report-period penalty/remediation matter. No retained report identifies confirmed major financial fraud, a severe issuer securities penalty or a qualified audit opinion.

Known official regulatory facts include:

- a 2017 SZSE public censure of then-director 徐自发 for sensitive-period and short-swing trading;
- a warning letter/regulatory letter concerning supervisor 段秀峰's 2021 share reduction without advance plan disclosure, reported in the 2023 annual report.

These are individual trading/disclosure matters. They do not establish company financial fraud or a severe issuer-level securities penalty under the frozen filter.

Official CSRC/SZSE searches did not identify a later confirmed major fraud/issuer penalty for `000651`, but search absence is not terminal-set proof. Classification:

```text
major issuer fraud/severe penalty discovered = no
minor individual governance actions discovered = yes
filter decision = source-bounded pass
advisory = retain individual actions
```

## 4. Control status and pledge

The annual reports state that, after the January 2020 ownership transfer, the company has **no controlling shareholder and no actual controller**. They explain that first shareholder 珠海明骏 and concert party 董明珠 cannot determine shareholder resolutions or elect more than half of the board.

The frozen filter is specifically `控股股东质押比例 < 20%`. With no controlling shareholder:

```text
controlling-shareholder pledge predicate = not applicable
literal filter result = pass / N.A.
```

However, the largest shareholder's position is fully pledged in the retained reports:

| Report period | Holder | Shares held | Shares pledged | Pledge ratio of holder position |
| --- | --- | ---: | ---: | ---: |
| `20201231` | 珠海明骏 | `902,359,632` | `902,359,632` | `100%` |
| `20211231` | 珠海明骏 | `902,359,632` | `902,359,632` | `100%` |
| `20221231` | 珠海明骏 | `902,359,632` | `902,359,632` | `100%` |
| `20231231` | 珠海明骏 | `902,359,632` | `902,359,632` | `100%` |

This is a material governance advisory. It cannot be converted after observation into a new hard `largest shareholder <20%` filter because the precommitted rule names the controlling shareholder. A future strategy version may explicitly broaden the rule before seeing validation results.

## 5. Major acquisitions and comparability

Material diversification occurred during the formula window:

- 2021: acquisition of `30.47%` of 格力钛新能源 for `1,828,275,113.56 CNY`, obtaining control on `2021-10-31`; disclosed goodwill `612,777,583.92 CNY`;
- 2022: acquisition/control of 盾安环境, expanding into refrigeration components and automotive thermal management;
- 2023: the annual report continues to describe integration of 盾安环境 and 格力钛.

Consequences:

- annual financial statements remain auditable and consolidated;
- the ROIC series contains real business-mix and consolidation changes;
- high historical ROIC should not be interpreted as a perfectly stationary single-business process;
- the frozen initial filter has no acquisition-frequency threshold, so these facts are advisory rather than an automatic exclusion;
- future exit/thesis monitoring must treat a major acquisition that makes the quality thesis unverifiable as a decision-material event.

## 6. Fixed-issuer governance decision

```text
audit opinion = pass
major fraud/severe issuer penalty = source-bounded pass
controlling-shareholder pledge = N.A. / pass
largest-shareholder pledge = advisory risk
major acquisitions = advisory comparability risk
full governance terminal set = unavailable
```

The governance evidence does not presently block continued fixed-issuer research. It remains insufficient for a general full-market `audit_governance_revision@1` or deployment-grade claim.

## 7. Next blocker

Historical valuation authority remains missing. The next useful fixed-issuer step is a source-bounded daily market-value/price capture that recomputes valuation from retained numerator and point-in-time financial denominator rather than trusting provider PE/EV ratios.
