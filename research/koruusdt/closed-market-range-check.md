# KORUUSDT closed-market range check

- **Dataset:** `data/manifest.json`
- **Manifest SHA-256:** `sha256:066c775e60ba402b631b406fd8138da200d7e30a136e0efb7c2c13b196680d64`
- **Window:** 2026-06-22 13:55 UTC to 2026-08-24 11:00 UTC (exclusive)
- **Target:** split-normalized Binance KORUUSDT mark-price 1-hour OHLC
- **Scope:** descriptive exploratory check, not a trade signal or decision-grade conclusion

## Hypothesis

When either the Korean cash market or the US cash market is open, KORUUSDT should react more strongly to its reference markets. When both cash markets are closed, hourly movement should contract and price may move back and forth inside a narrower range.

The duplicated Korean-index factor is treated as one broad Korean-market factor. Market dates are inferred from the pinned `^KS200` and `KORU` source observations. The July 15 contract-adjustment window is excluded.

## Regular-session windows

During the June-August sample, the United States was on daylight-saving time:

| Market | UTC | Beijing time |
| --- | --- | --- |
| KRX regular session | 00:00-06:30 | 08:00-14:30 |
| US core session | 13:30-20:00 | 21:30-04:00 next day |

Therefore the regular weekday periods when both cash markets are closed are:

| Closed interval | UTC | Beijing time | Fully closed 1h bars used |
| --- | --- | --- | --- |
| KRX close → US open | 06:30-13:30 | 14:30-21:30 | 07:00-12:00 |
| US close → next KRX open | 20:00-24:00 | 04:00-08:00 | 20:00-23:00 |
| Weekend | Friday 20:00 → Monday 00:00 | Saturday 04:00 → Monday 08:00 | all complete bars |

After US daylight-saving time ends, the US session shifts to 14:30-21:00 UTC, so these intervals must shift with it rather than remain hard-coded.

## Hourly comparison

The sample contains 1,499 usable hourly bars after excluding 10 adjustment-window bars.

| Metric | Either cash market open | Both cash markets closed | Closed/open ratio |
| --- | ---: | ---: | ---: |
| Bars | 601 | 898 | — |
| Median absolute 1h return | 1.55% | 0.47% | 30% |
| 90th percentile absolute 1h return | 5.55% | 2.22% | 40% |
| Median 1h high-low range | 3.83% | 1.25% | 33% |
| Hourly return standard deviation | 3.41% | 1.62% | 48% |

This is strong descriptive evidence of **volatility compression** while both cash markets are closed.

## Continuous-window comparison

Only continuous windows of at least three complete hours are included.

| Window type | Segments | Median duration | Median absolute net move | Median total high-low range | Median directional efficiency | Median sign reversals |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Short closed windows | 78 | 6h | 2.46% | 5.44% | 0.43 | 2 |
| Long/weekend closed windows | 9 | 52h | 4.01% | 9.54% | 0.23 | 22 |
| Cash-market-open windows | 86 | 7h | 4.93% | 11.98% | 0.31 | 3 |

Directional efficiency is `abs(net log return) / sum(abs(hourly log returns))`. Values near zero indicate more back-and-forth movement; values near one indicate a directional move.

Long weekend closures show substantial back-and-forth movement, but short weekday closures are not uniformly mean-reverting. They are quieter, yet their median directional efficiency is not lower than open-market windows.

## Important counterexamples

The closed-market condition did not prevent large directional moves:

- 2026-06-24 20:00 UTC, 4-hour closed window: approximately **+20.12%** net move.
- 2026-07-30 07:00 UTC, 6-hour closed window: approximately **+14.92%** net move.
- 2026-07-16 20:00 UTC, 17-hour closed window: approximately **-10.01%** net move.

Therefore “both markets closed” does not by itself define a safe or fixed trading range.

## Conclusion

The proposed rule is **partly present**:

1. **Supported:** KORUUSDT volatility and hourly high-low range are materially smaller when both Korean and US cash markets are closed.
2. **Strongest on weekends:** long closed windows exhibit many reversals and low directional efficiency.
3. **Not established:** short weekday closed windows do not consistently remain inside a stable mean-reverting band.
4. **Failure mode:** Binance-specific price discovery, FX, news, basis changes, or stale/reference-mode repricing can still produce double-digit closed-market moves.

The simple hypothesis should therefore be phrased as a **closed-market volatility regime**, not as “price always stays in a fixed range.” Any range strategy would still require an entry-range definition, a volatility/basis filter, and a hard invalidation rule.

## Limitations

- Only about two months of KORUUSDT history are available.
- The sample covers US daylight-saving time only.
- Source market dates come from secondary Yahoo observations; holidays are inferred from whether those observations exist.
- Minute/order-book data are not used, so execution quality is not evaluated.
- No statistical claim of causality or future profitability is made.
