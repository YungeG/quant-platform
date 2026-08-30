# A股大盘低波策略回测结果

- verdict: **NO-GO**
- data: 2018-01-02—2026-08-25
- rebalances: 34

| Variant | CAGR | Sharpe | Max drawdown | Excess CAGR | Avg positions | Turnover |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| balanced_30 | 2.38% | 0.232 | -30.49% | -2.15% | 29.5 | 1.28 |
| naive_30 | 4.70% | 0.394 | -24.46% | 0.18% | 30.5 | 0.88 |
| balanced_50 | 3.64% | 0.325 | -29.76% | -0.88% | 46.6 | 1.05 |
| top300_cap | 4.53% | 0.330 | -38.73% | 0.00% | 300 | 0.00 |
| top300_equal | 4.08% | 0.297 | -40.48% | 0.00% | 300 | 0.00 |

## Gate

- FAIL `cagr_margin`
- FAIL `sharpe_margin`
- PASS `drawdown_improvement`
- FAIL `positive_excess_folds`
- FAIL `best_year_independence`
- FAIL `cost_retention`
- PASS `turnover`
- PASS `execution`
