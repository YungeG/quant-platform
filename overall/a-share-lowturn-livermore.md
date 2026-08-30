# 低换手 × Livermore 回测结果

- verdict: **MARGINAL**
- data: 2016-01-04—2026-08-25
- candidate signal days: 298

| Variant | CAGR | Sharpe | Max drawdown | Excess CAGR | Avg exposure | Trades |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| livermore | 4.02% | 0.297 | -41.93% | 3.34% | 43.10% | 682 |
| no_pyramid | 2.42% | 0.221 | -55.79% | 1.75% | 67.81% | 458 |
| fixed_20 | -8.74% | -0.288 | -66.99% | -9.41% | 57.42% | 610 |
| benchmark | 0.67% | 0.148 | -48.74% | 0.00% | 100.00% | 0 |

## Gate

- FAIL `positive_and_sharpe`
- FAIL `drawdown_20pct_improvement`
- PASS `positive_folds`
- PASS `beats_fixed_management`
- PASS `pyramiding_increment`
- PASS `cost_retention`
- PASS `execution_coverage`
