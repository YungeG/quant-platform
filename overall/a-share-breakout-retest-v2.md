# A股突破位回踩V2结果

- verdict: **NO-GO**
- events/executed: 4447/205

| Horizon | Mean active | Median | Win rate | Bootstrap 95% |
| --- | ---: | ---: | ---: | --- |
| 5d | -0.21% | -1.04% | 41.95% | [-0.83%, 0.44%] |
| 10d | -0.64% | -0.83% | 46.08% | [-1.46%, 0.18%] |
| 20d | -0.15% | 0.04% | 50.74% | [-1.45%, 1.14%] |

## Failure reasons

- `retest_volatility_expanded`: 1917
- `distribution_selloff`: 1006
- `support_break`: 551
- `retest_volume_not_contracted`: 316
- `no_retest_timeout`: 307
- `triggered`: 213
- `no_recovery_timeout`: 137
