# A-share early-reporting peer-diffusion v1 conclusion

## Verdict: NO-GO

`trade_authorized: false`

The bounded same-path smoke completed with one event per arm: unreported peer stocks returned **-3.3021632592%** after costs (2 of 7 peers priced), while direct industry ETF `159662.SZ` returned **-5.8365901981%** after costs. These synthetic-signal smoke returns validate execution and output handling; they are not full-study evidence.

The full PIT run through 2026-08-28 was stopped by the required 600-second limit before metrics were produced. Loading 245,404 first-announcement rows and 5,897 membership rows took 0.97 seconds. A 60-second stack diagnostic located the bottleneck in `build_signals` at `experiments/run_early_reporting_peer_diffusion.py:58`: each announcement-day/period and industry repeatedly scans all announcement rows via `events.Symbol.isin(symbols)`.

Therefore full stock, ETF, and 2025 holdout metrics are unavailable and remain `null` in the result JSON. The study cannot authorize trading. The smallest next step is to pre-index announcement events by report period and symbol so each iteration scans only its period subset, without changing thresholds, ordering, PIT rules, or arm semantics.
