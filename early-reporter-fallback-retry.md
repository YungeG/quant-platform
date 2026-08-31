# Early-reporter peer-diffusion fallback retry

## Outcome

**Verdict: NO-GO**

**trade_authorized: false**

The frozen v1 study completed through 2026-08-28. The implementation keeps PIT announcement dates and SW membership, T+1 entry, a 20-session horizon, 31 bp round-trip cost, missing-price handling, and separate stock/ETF arms.

## Full metrics

| Arm | Signals | Complete | Mean 20d | Median 20d | Win rate | 2025 count | 2025 mean | 2025 win rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Unreported peer stocks | 190 | 187 | 0.0015084362245098757 | 0.006180557989006447 | 0.5454545454545454 | 13 | -0.01375206637621734 | 0.5384615384615384 |
| Direct industry ETF | 190 | 83 | -0.0010974483117361061 | -0.0005219421369234783 | 0.4819277108433735 | 11 | -0.021578861103236088 | 0.36363636363636365 |

Both 2025 holdout means are negative; the pre-registered Gate therefore fails. Full annual folds are stored in `overall/a-share-early-reporting-peer-diffusion-v1-result.json`.

## Performance fix

- Price histories remain indexed once per symbol from commit `445a613`.
- Signal construction now maintains incremental visible-symbol sets per report period and caches active PIT industry symbol sets per announcement day.
- A regression test compares the optimized output with the original semantics across multiple periods, dates, industries, and a non-member event.
- Full runtime fell from a 600-second timeout in `build_signals` to 79 seconds end-to-end.

## Evidence

- `experiments/run_early_reporting_peer_diffusion.py`
- `tests/research/test_early_reporting_peer_diffusion.py`
- `overall/a-share-early-reporting-peer-diffusion-v1-design.md`
- `overall/a-share-early-reporting-peer-diffusion-v1-result.json`
- `overall/a-share-early-reporting-peer-diffusion-v1-full-summary.csv`
- `overall/a-share-early-reporting-peer-diffusion-v1-smoke-evidence.csv`
- `overall/a-share-early-reporting-peer-diffusion-v1-conclusion.md`

## Validation

- Focused tests: `3 passed`.
- Primary LSP diagnostics: no errors.
- Bounded same-path smoke preserved exact prior returns: stock `-0.03302163259218811`, ETF `-0.05836590198123038`.
- Full run: exit `0`, elapsed `79s`, 190 signals.
- JSON parsing, CSV schema checks, compilation, `git diff --check`, and no-staged-files check: passed.

## Residual risks

- Results are research-grade event returns, not a formal account-level Backtest entry or virgin OOS.
- ETF coverage is incomplete: 83 of 190 signals had a complete direct-industry ETF expression.
- Historical results do not authorize live trading or shadow deployment.
