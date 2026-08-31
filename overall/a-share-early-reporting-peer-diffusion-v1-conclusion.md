# A-share early-reporting peer-diffusion v1 conclusion

## Verdict: NO-GO

`trade_authorized: false`

The frozen PIT study completed through 2026-08-28 in 79 seconds after replacing repeated full-frame scans with incremental visible-symbol sets by report period. Thresholds and execution rules were unchanged.

| Arm | Complete events | Mean 20d return | Median 20d return | Win rate | 2025 events | 2025 mean | 2025 win rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Unreported peer stocks | 187 / 190 | +0.1508% | +0.6181% | 54.55% | 13 | -1.3752% | 53.85% |
| Direct industry ETF | 83 / 190 | -0.1097% | -0.0522% | 48.19% | 11 | -2.1579% | 36.36% |

Both pre-registered 2025 holdout means are negative, so the Trading Gate fails. The stock arm has a weak positive full-sample event mean, but it is unstable across years and turns negative in both 2025 and 2026. The ETF arm is negative overall and in the holdout.

These are cost-adjusted event returns, not an account-level portfolio CAGR. No threshold was tuned after observing outcomes, and no trading or shadow authorization is granted.
