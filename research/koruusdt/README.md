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

## Limitation

Current accepted Backtest instrument metadata accepts only `PERPETUAL`, while
`KORUUSDT` is reported as `TRADIFI_PERPETUAL` in Binance metadata. This dataset
is exploratory only and cannot support an approved `KORUUSDT` Backtest run.
