# A股横截面低换手因子复核结果

- verdict: **MARGINAL**
- periods: 514
- net active edge / 5 sessions: 0.111%
- net active Sharpe: 0.478
- absolute CAGR: 9.17%
- annual turnover: 16.44
- selected return missing rate: 1.00%
- placebo median Sharpe: -1.287

| Fold | Periods | Active edge | Active Sharpe |
| --- | ---: | ---: | ---: |
| 2016-2019 | 191 | 0.063% | 0.410 |
| 2020-2022 | 146 | 0.053% | 0.210 |
| 2023-2026 | 177 | 0.213% | 0.751 |

## Gate

- PASS `active_edge_positive`
- FAIL `active_sharpe`
- PASS `positive_folds`
- PASS `placebo_margin`
- FAIL `turnover`
- PASS `missing_rate`
- PASS `absolute_cagr`
