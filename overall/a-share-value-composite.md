# A股PIT价值复合策略回测结果

- verdict: **NO-GO**
- data: 2016-01-04—2026-08-25
- rebalances: 40

| Variant | CAGR | Sharpe | Max drawdown | Excess CAGR | Avg positions | Turnover |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| composite_50 | 2.11% | 0.206 | -33.24% | -2.92% | 50.7 | 1.23 |
| ep_50 | 2.93% | 0.248 | -34.73% | -2.10% | 50.8 | 1.29 |
| bp_50 | 2.52% | 0.227 | -33.70% | -2.52% | 50.4 | 1.24 |
| top500_cap | 5.03% | 0.355 | -38.69% | 0.00% | 500 | 0.00 |
| top500_equal | 2.62% | 0.228 | -39.81% | 0.00% | 500 | 0.00 |

## Gate

- FAIL `cagr_margin`
- FAIL `sharpe_margin`
- PASS `drawdown`
- FAIL `positive_excess_folds`
- PASS `best_year_independence`
- FAIL `cost_retention`
- PASS `turnover`
- FAIL `execution`
