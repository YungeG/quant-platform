# KORUUSDT exploratory dataset (research)

This folder contains a first-pass, stdlib-only exploratory dataset for
`KORUUSDT`. The checked-in manifest and artifact SHA-256 values integrity-pin
this retrieval; the command below is a regeneration recipe, not a guarantee of
byte-identical output.

## Integrity-pinned regeneration recipe

Run from the repository root:

```bash
uv run python research/koruusdt/build_dataset.py \
  --start 2026-06-22T13:55:00Z \
  --end 2026-08-24T11:00:00Z \
  --out-dir research/koruusdt/data
```

The requested interval is `1h`; start is inclusive and end is exclusive. The
manifest records the exact request window and endpoint parameter identities,
builder path and SHA-256, Python/runtime and `zoneinfo` caveat, fetch times,
source identifiers, authoritative listing/split announcements, row counts, and
SHA-256 for every generated CSV.

Regeneration should be checked against the manifest rather than assumed equal.
In particular, Yahoo chart history is mutable vendor data: prior bars may be
revised or become unavailable, so a later retrieval can legitimately produce
different Yahoo artifacts and aligned values. The manifest hashes pin the
retrieved snapshot, not future Yahoo responses.

## Bounded execution-data capture

Daily aggregate trades, 1-minute mark-price klines, the Backtest-authority
1-hour mark/index price bars, and funding history for the discovery window are
captured separately from the frozen exploratory dataset and its base
`data/manifest.json`:

```bash
uv run python research/koruusdt/capture_execution_data.py --offline
uv run python research/koruusdt/capture_execution_data.py --validate-only
uv run pytest research/koruusdt/tests/test_capture_execution_data.py
```

The offline/resume capture validates every retained file before any possible
network access. Official Binance USD-M daily ZIPs and `.CHECKSUM` files for
2026-07-15 through 2026-08-23 are retained for aggregate trades, 1-minute mark
prices, and provider-named 1-hour mark/index prices. A non-offline run may fetch
only missing pre-holdout daily files after the complete preflight; official REST
is not needed for completion.

The bounded 2026-08-24 1-minute mark REST page and its deterministic derivatives
are reused byte-for-byte from commit `a61ef74` and hash-checked before use. The
retained bounded aggregate-trade REST pages remain unchanged. No full
2026-08-24 daily archive is downloaded or retained: `[2026-08-24T11:00:00Z,
...)` is holdout data and must never be requested, retained, or used.

The 2026-08-24 00:00-11:00 UTC 1-hour mark/index CSV/ZIP/checksum artifacts are
deterministically selected from the exact rows and lexemes in the frozen,
base-manifest-pinned `binance_mark_raw.csv` and `binance_index_raw.csv`.

Funding authority is the accepted Backtest provider capture at
`backtest/tests/fixtures/market_data/providers/binance_usdm/koru-funding-history-v1/`.
Offline capture hash-checks `funding-history.json` and
`acquisition-receipt.json`, then mirrors both byte-for-byte under
`data/binance_usdm/fundingHistory/accepted-capture/`. The response contains 120
ordered observations from 2026-07-15 16:00 UTC through 2026-08-24 08:00 UTC;
every row has the exact provider field `rateType: "Regular"`, with no Special
or missing values. The receipt binds the exact authority-window request and
holdout-exclusive end. No funding type is inferred, and the base funding CSV is
not an execution-data source.

Official files retain provider filenames under `data/binance_usdm/`. Local
price-bar derivations live under `priceBars/{mark,index}/1h/derived-bounded/`.
`data/execution_data_manifest.json` provides exact file cover, row/coverage
summaries, accepted-source hashes and paths, holdout checks, and a canonical
self-hash. Repeated offline capture reproduces the same mirrored bytes and
manifest hash.

## Scope notes

- Binance data comes from public USD-M `klines`, `markPriceKlines`,
  `indexPriceKlines`, `premiumIndexKlines`, and `fundingRate` endpoints.
- External factor series come from Yahoo chart API for `KORU`, `^KS200`,
  `005930.KS`, `000660.KS`, `MU`, `SNDK`, `KRW=X`, and `^SOX`. They are
  secondary/non-decision-grade research inputs.
- Raw observations are separate `<source>_raw.csv` files. Funding retains its
  numeric millisecond observation timestamp and leaves absent
  `fundingRateType` blank rather than inferring a type.
- Aligned hourly rows are keyed to a complete Binance mark-bar grid. Binance
  last/index/premium rows must have exactly the same timestamps; incomplete or
  mismatched source pages fail closed. Funding uses backward/as-of lookup and
  retains its observed UTC timestamp, numeric millisecond timestamp, and age.
- Yahoo timestamps are source bar starts. For KRX symbols, availability is the
  earlier of start plus one hour and 15:30 Asia/Seoul that date. For US exchange
  symbols, it is the earlier of start plus one hour and 16:00
  America/New_York that date. `KRW=X` uses start plus one hour. Values are never
  aligned before that availability timestamp.
- `is_krx_regular_weekday_clock` and `is_us_core_weekday_clock` encode only
  weekday regular/core clock windows using `zoneinfo`. Holidays are not encoded;
  these fields do not claim that an exchange was actually open.
- `adjustment_regime` is `pre_adjustment`, `adjustment_window`, or
  `post_adjustment`. Before 2026-07-15 00:15Z, normalized prices use `*0.05` and
  base quantities use `*20`; bars overlapping 00:15Z through 09:35Z have null
  normalized price/quantity fields; later bars are unchanged. Raw values remain
  intact.
- Premium-index klines are basis/premium values, not prices, and are never
  split-scaled.

## Limitations

- Official REST is currently unreachable. The Aug-24 1-hour mark/index
  artifacts are transparent derivations from immutable frozen base
  observations, not newly captured provider responses. Funding uses the
  accepted provider response and acquisition receipt bytes already retained by
  Backtest; offline regeneration does not refetch them.
- Aggregate trades remain unavailable for
  `[2026-08-24T00:00:00Z, 2026-08-24T06:34:20.640Z)` because the retained REST
  capture could not access that history; the manifest and gap audit preserve
  the impact rather than filling it from a holdout-day archive.
- Current accepted Backtest instrument metadata accepts only `PERPETUAL`, while
  `KORUUSDT` is reported as `TRADIFI_PERPETUAL` in Binance metadata. This
  dataset remains exploratory and does not itself authorize deployment.
