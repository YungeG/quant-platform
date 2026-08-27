# Quality-BBAND research-grade existing-data results v1

- **Status:** `ADVISORY / RELAXED_RESEARCH_STANDARD`
- **Evidence standard:** [`quality-bband-research-grade-existing-data-evidence-v1.md`](../implementation/plans/quality-bband-research-grade-existing-data-evidence-v1.md)
- **No new data:** true

## 1. Method

The analysis applies the approved research-only conventions:

- provider `f_ann_date`, then `ann_date`, controls research visibility;
- select the latest visible common three-statement date;
- prefer provider `update_flag="1"` within that common date, while conflicting preferred payloads remain unresolved;
- use the declared debt and D&A proxies with explicit null-as-zero proxy treatment;
- preserve accepted O/N unresolved precedence;
- use the frozen ROIC, OCF, FCF and leverage thresholds.

The complete 20,797-record output was reproduced twice byte-for-byte.

## 2. Research-grade result

| Disposition | Count |
|---|---:|
| `RESEARCH_GRADE_PROVISIONAL_FAIL` | 12,150 |
| `RESEARCH_GRADE_PROVISIONAL_PASS` | 433 |
| `RESEARCH_GRADE_UNRESOLVED` | 8,214 |
| total | 20,797 |

Canonical record hash:

```text
sha256:b6181fa3c228d7ff4e71fca1fc24aa0931e7da2d484042cfaf15e605c9b9e68f
```

### Screen history

| Screen | Provisional pass | Provisional fail | Unresolved | Total |
|---|---:|---:|---:|---:|
| 20170502 | 0 | 1,159 | 836 | 1,995 |
| 20180502 | 0 | 1,169 | 865 | 2,034 |
| 20190506 | 0 | 1,126 | 927 | 2,053 |
| 20200506 | 0 | 1,086 | 1,057 | 2,143 |
| 20210506 | 0 | 1,051 | 1,173 | 2,224 |
| 20220505 | 1 | 1,193 | 1,240 | 2,434 |
| 20230504 | 129 | 1,781 | 702 | 2,612 |
| 20240506 | 150 | 1,775 | 710 | 2,635 |
| 20250506 | 153 | 1,810 | 704 | 2,667 |

## 3. Unresolved causes

| Cause | Count |
|---|---:|
| required formula input missing | 6,028 |
| ROIC proxy domain unavailable | 1,268 |
| no common visible provider trio | 907 |
| official annual report nonfiling | 7 |
| unsupported official statement scope | 3 |
| prior balance unavailable | 1 |

These records are not converted to failures or passes.

## 4. Latest provisional-pass pool

The `20250506` screen contains 153 research-grade provisional passes.

The highest median `ROIC_proxy` observations include:

| Code | Name | Industry | Median ROIC proxy |
|---|---|---|---:|
| 600132 | 重庆啤酒 | 啤酒 | 4.4133 |
| 603288 | 海天味业 | 食品 | 0.9773 |
| 002932 | *ST明德 | 医疗保健 | 0.9225 |
| 000651 | 格力电器 | 家用电器 | 0.8893 |
| 600809 | 山西汾酒 | 白酒 | 0.6845 |
| 603605 | 珀莱雅 | 日用化工 | 0.6245 |
| 603444 | 吉比特 | 互联网 | 0.5913 |
| 600850 | 电科数字 | 软件服务 | 0.5845 |
| 000596 | 古井贡酒 | 白酒 | 0.5776 |
| 603551 | 奥普科技 | 家居用品 | 0.5391 |

The presence of `*ST明德` and the extreme 重庆啤酒 proxy demonstrate that relaxed assumptions can produce economically implausible or incomplete rankings. The list is diagnostic, not a four-stock recommendation.

## 5. Existing-price BOLL intersection

Using the immutable raw-price backup ending `2026-05-20`, the 153 latest provisional passes produced 12 BOLL/volume crossing events in the final 60 available sessions:

| Date | Code | Name |
|---|---|---|
| 2026-05-07 | 002264 | 新华都 |
| 2026-05-06 | 000792 | 盐湖股份 |
| 2026-04-29 | 603043 | 广州酒家 |
| 2026-04-29 | 000792 | 盐湖股份 |
| 2026-04-28 | 603127 | 昭衍新药 |
| 2026-04-27 | 603605 | 珀莱雅 |
| 2026-04-24 | 600846 | 同济科技 |
| 2026-04-23 | 000596 | 古井贡酒 |
| 2026-04-21 | 600618 | 氯碱化工 |
| 2026-04-20 | 002028 | 思源电气 |
| 2026-03-17 | 600285 | 羚锐制药 |
| 2026-02-24 | 601919 | 中远海控 |

There was no research-grade provisional-pass signal on the final available session, `2026-05-20`.

## 6. Conclusion

Relaxing the evidence standard creates a 153-member latest provisional-pass pool and historical technical intersections, but it still does not produce a current four-stock target:

- price coverage is stale after `2026-05-20`;
- no corporate-action adjustment authority exists;
- proxy accounting can admit obvious anomalies;
- no current T-close signal exists in the final available session.

Therefore:

```text
formal_s2_qualified = false
strategy_target_authorized = false
backtest_authorized = false
validation_authorized = false
deployment_authorized = false
```

No TargetSnapshot or execution request is produced.
