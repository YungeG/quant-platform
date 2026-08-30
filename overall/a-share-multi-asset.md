# A股股债金多资产配置结果

- verdict: **GO**
- preferred: **erc**
- data: 2017-01-03—2026-08-25

| Strategy | CAGR | Sharpe | Max drawdown | Turnover | Eq/Bond/Gold avg |
| --- | ---: | ---: | ---: | ---: | --- |
| all_equity | 5.31% | 0.368 | -42.16% | 0.05 | 100%/0%/0% |
| 60_40 | 4.71% | 0.465 | -24.72% | 0.12 | 60%/40%/0% |
| fixed_30_50_20 | 6.42% | 0.955 | -9.49% | 0.13 | 30%/50%/20% |
| equal_1n | 8.13% | 0.953 | -12.51% | 0.13 | 33%/33%/33% |
| inverse_vol | 4.96% | 1.655 | -3.18% | 0.15 | 9%/78%/13% |
| erc | 4.93% | 1.686 | -3.17% | 0.15 | 10%/78%/12% |

## Gate

- PASS `drawdown_improvement`
- PASS `sharpe_improvement`
- PASS `cagr_floor`
- PASS `positive_folds`
- PASS `stress_years`
- PASS `cost_retention`
- PASS `turnover`
- PASS `lot_feasibility`
- PASS `inverse_vol_complexity`
- PASS `erc_complexity`
