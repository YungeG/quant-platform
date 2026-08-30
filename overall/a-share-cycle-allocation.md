# 中国经济周期驱动股债金配置结果

- verdict: **MARGINAL**
- current fast state: **contraction**
- current slow state: **expansion**

| Strategy | CAGR | Sharpe | Max drawdown | Turnover |
| --- | ---: | ---: | ---: | ---: |
| fixed_quarterly | 6.42% | 0.955 | -9.49% | 0.13 |
| equal_1n | 8.13% | 0.953 | -12.51% | 0.13 |
| inverse_vol | 4.96% | 1.655 | -3.18% | 0.15 |
| cycle_fast | 4.69% | 0.583 | -18.09% | 2.01 |
| cycle_slow | 4.87% | 0.626 | -17.90% | 1.41 |
| fixed_monthly | 6.49% | 0.977 | -9.48% | 0.19 |

## Gate

- FAIL `cagr_margin`
- FAIL `sharpe_floor`
- FAIL `max_drawdown`
- FAIL `positive_excess_folds`
- FAIL `stress_years`
- PASS `best_year_independence`
- FAIL `cost_retention`
- FAIL `turnover`
- PASS `lot_feasibility`
