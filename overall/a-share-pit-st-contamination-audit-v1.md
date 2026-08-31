# A股历史策略PIT ST污染审计V1

- fix commit: `6b9ac8e`
- 结论：下列24个旧股票策略/事件篮子证据统一标记为`PIT_ST_CONTAMINATED`。
- 旧指标可作为失败研究档案引用，但不得进入Candidate、Validation、Shadow或Promotion。
- 已有修正后继者时必须使用后继者；其余仅在重新考虑晋级时用`NameChangeData`重跑。

| Strategy | Original verdict | Corrected successor | Action |
| --- | --- | --- | --- |
| `analyst-revision-v1` | MARGINAL / STRONG ALPHA, EXCESSIVE RISK | `a-share-analyst-revision-pit-st-v2` | `USE_CORRECTED_SUCCESSOR` |
| `analyst-breadth-v2` | MARGINAL / INFERIOR TO V1 | — | `RERUN_WITH_NAMECHANGEDATA_ONLY_IF_REVISITED` |
| `analyst-core-satellite` | MARGINAL | — | `RERUN_WITH_NAMECHANGEDATA_ONLY_IF_REVISITED` |
| `breakout-retest-v2` | NO-GO | — | `RERUN_WITH_NAMECHANGEDATA_ONLY_IF_REVISITED` |
| `chip-pressure` | NO-GO | — | `RERUN_WITH_NAMECHANGEDATA_ONLY_IF_REVISITED` |
| `earnings-surprise` | MARGINAL / STRONG EVENT SIGNAL | — | `RERUN_WITH_NAMECHANGEDATA_ONLY_IF_REVISITED` |
| `fundamental-momentum` | NO-GO | — | `RERUN_WITH_NAMECHANGEDATA_ONLY_IF_REVISITED` |
| `largecap-lowvol` | NO-GO / PASSIVE-ONLY MARGINAL | — | `RERUN_WITH_NAMECHANGEDATA_ONLY_IF_REVISITED` |
| `livermore-v2` | NO-GO | — | `RERUN_WITH_NAMECHANGEDATA_ONLY_IF_REVISITED` |
| `lowturn-livermore` | MARGINAL / NO DEPLOY | — | `RERUN_WITH_NAMECHANGEDATA_ONLY_IF_REVISITED` |
| `low-turnover-replication` | MARGINAL / SHADOW-ONLY | `a-share-low-turnover-pit-st-v17` | `USE_CORRECTED_SUCCESSOR` |
| `margin-crowding` | NO-GO AS FILTER | — | `RERUN_WITH_NAMECHANGEDATA_ONLY_IF_REVISITED` |
| `market-gated-analyst-v10` | NO-GO | — | `RERUN_WITH_NAMECHANGEDATA_ONLY_IF_REVISITED` |
| `revision-regime-analyst-v11` | NO-GO / SIGNIFICANT RETURN, EXCESSIVE RISK | `a-share-revision-regime-pit-st-v12` | `USE_CORRECTED_SUCCESSOR` |
| `pead` | NO-GO | — | `RERUN_WITH_NAMECHANGEDATA_ONLY_IF_REVISITED` |
| `pharma-chemical-rotation` | MARGINAL / NO-GO ACTIVE ROTATION | — | `RERUN_WITH_NAMECHANGEDATA_ONLY_IF_REVISITED` |
| `quality-overlay` | NO-GO | — | `RERUN_WITH_NAMECHANGEDATA_ONLY_IF_REVISITED` |
| `shareholder-events` | NO-GO | — | `RERUN_WITH_NAMECHANGEDATA_ONLY_IF_REVISITED` |
| `short-reversal` | NO-GO | — | `RERUN_WITH_NAMECHANGEDATA_ONLY_IF_REVISITED` |
| `technical-momentum` | NO-GO | — | `RERUN_WITH_NAMECHANGEDATA_ONLY_IF_REVISITED` |
| `three-industry-historical-validation` | NO-GO GENERAL STRATEGY | — | `RERUN_WITH_NAMECHANGEDATA_ONLY_IF_REVISITED` |
| `true-breakout-analyst-basket-v9` | NO-GO | — | `RERUN_WITH_NAMECHANGEDATA_ONLY_IF_REVISITED` |
| `true-breakout-stock-basket-v8` | NO-GO | — | `RERUN_WITH_NAMECHANGEDATA_ONLY_IF_REVISITED` |
| `value-composite` | NO-GO | — | `RERUN_WITH_NAMECHANGEDATA_ONLY_IF_REVISITED` |

ETF-only、多资产、纯行业分类和`SOURCE-BLOCKED`研究不属于本次“直接股票策略”清单；它们仍须遵守各自PIT来源约束。
