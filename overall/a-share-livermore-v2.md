# A股 Livermore V2 回测结果

- verdict: **NO-GO**
- data: 2016-01-04—2026-08-25
- candidate signal days: 88

| Variant | CAGR | Sharpe | Max drawdown | Excess CAGR | Avg exposure |
| --- | ---: | ---: | ---: | ---: | ---: |
| entry_fixed_20 | -11.75% | -0.365 | -77.33% | -8.61% | 24.10% |
| risk_managed | -1.32% | -0.295 | -17.90% | 1.83% | 4.42% |
| full_livermore | -2.22% | -0.318 | -28.71% | 0.93% | 5.82% |
| benchmark | -3.15% | -0.003 | -54.75% | 0.00% | 100.00% |

## Staged gates

- FAIL `entry_gate`
- PASS `risk_management_gate`
- FAIL `pyramiding_gate`
- PASS `excess_cagr`
- FAIL `sharpe`
- PASS `max_drawdown`
- FAIL `positive_excess_folds`
- FAIL `best_year_independence`
- FAIL `cost_retention`
- FAIL `execution`
