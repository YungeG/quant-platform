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
uv run python research/koruusdt/capture_execution_data.py --refresh-archive-metadata
uv run pytest research/koruusdt/tests/test_capture_execution_data.py
```

Normal, `--offline`, and `--validate-only` operation is network-free and fails
closed on missing retained files. The explicit metadata refresh mode is the only
network mode: it sends `HEAD` requests to the already-retained 2026-07-15
through 2026-08-23 Binance Vision ZIP and `.CHECKSUM` URLs for aggregate trades
and provider-named 1-hour mark/index prices. It never requests archive values or
a 2026-08-24 URL. Each response URL and `Content-Length` must match the retained
file; `ETag` is preserved when present and `Last-Modified` is normalized to UTC
seconds plus Unix nanoseconds in
`data/binance_usdm/official_archive_metadata_receipt.json`. The canonical,
self-hashed receipt is exact-cover bound into `execution_data_manifest.json`.
Official Binance USD-M daily ZIPs and `.CHECKSUM` files for the same retained
period also include 1-minute mark prices; those are validated offline but are
outside this metadata receipt. Official REST is not needed for completion.

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

## Retained discovery SourceProjectionV2, TargetV2, profile, and bundle

Build the canonical, summary-only discovery artifact from the retained execution
files and the checked-out Backtest production builder modules:

```bash
uv run python research/koruusdt/build_discovery_source_targets_v2.py
uv run python research/koruusdt/build_discovery_source_targets_v2.py --validate-only
uv run pytest research/koruusdt/tests/test_build_discovery_source_targets_v2.py
```

The build performs no network requests. It reconstructs and hash-checks the
official daily captures, retained Aug-24 authorities, accepted funding and
calendar/unit fixtures, the 611 audited boundary/cutoff pairs, the streaming
boundary index, SourceProjectionV2, all eight TargetV2 streams, the fixed
Development Profile V1, and ExecutionBundleV2. The output
`data/discovery_source_targets_v2.json` retains canonical hashes, stream
manifests and counts, profile and bundle limitations, authority refs, and
advisory flags only; it does not serialize the multi-million-row aggregate
stream, source events, profile wire, or bundle events. The profile and bundle
remain development-only and deployment-unauthorized, and are not backtest or
economics evidence. `--validate-only` rebuilds and byte-compares the checked-in
output.

`run_discovery_backtests_v1.py --parameter-id p01` is a bounded local Backtest
execution report only. It is not official Experiment, Analysis, or Candidate
evidence: public Research `execute_experiment` remains the authoritative
publishing path, and no such integration exists here. The runner emits a
retained-context reconstruction stage before any retained work and fails without
writing its output if preparation or engine execution fails.

## Public retained premium preflight

The immutable calendar/unit authority is
`data/public_preflight_sources_v1/manifest.json`. Its eight exact members are
repository copies; source-fixture paths are provenance only. The vendor HTML is
intentionally byte-exact (including malformed markup). Its pinned source hash
and the explicit scoped validator waiver are recorded in that manifest; the
narrowly scoped `.pi-lens.json` ignore protects integrity rather than
normalizing it.

```bash
uv run python research/koruusdt/run_public_koru_retained_preflight.py --smoke
uv run python research/koruusdt/run_public_koru_retained_preflight.py \
  --full --attempt-root .koru-retained-preflight-attempts --max-seconds 300
# A retry is a new retained-input replay, never a SourceProjection resume:
uv run python research/koruusdt/run_public_koru_retained_preflight.py \
  --full --attempt-root .koru-retained-preflight-attempts --max-seconds 300 \
  --retry-ordinal 1 --parent-attempt-id <timed-out-attempt-id>
```

`--smoke` hash-checks the authority and retained manifest interval, then stops
before economics without instantiating Foundation. With `--foundation-root`, it
leaves an absent path absent or accepts only an existing empty directory; it
rejects any Foundation state without mutation. `--full` requires an
`--attempt-root`. The parent catalogs then capability-probes Linux `FICLONE` in
staging and reflink-snapshots each held regular source/destination FD on the
same filesystem; there is no copy or hardlink fallback. It verifies catalog
hashes before making inputs read-only, then starts the replay child in its own
process group under the monotonic 1–300 second cap (300 by default and maximum).
Foundation and Market Bundle paths are initialized only after that snapshot
passes. Unsupported reflinks, cross-device inputs, and catalog mismatches write
only the canonical non-success snapshot receipt with `final_authority: []`; no
child starts. Complete and timeout state persist catalog/clone/verify/child
monotonic elapsed timings, which receipts bind. Full mode does not run an
Experiment, Backtest, Holdout read, or network operation. The full command is
documented here but has not been run.

### SourceProjection timeout diagnostics

The bounded diagnostic publication command persists `progress.json` in its
attempt container at completed phase boundaries. A timeout receipt records the
last completed/current phase, monotonic elapsed timings, input counts, and the
immutable raw-snapshot authority identity; `final_authority` remains empty.
It does not resume a partial publication or run an Experiment, Holdout, or
network operation. Review-approved later execution (not run here):

```bash
uv run python research/koruusdt/run_public_koru_retained_preflight.py \
  --diagnose-source-projection \
  --raw-snapshot-foundation-root <raw-snapshot-foundation-root> \
  --input-snapshot-authority '<canonical-raw-snapshot-authority-json>' \
  --source-projection-publication-root <source-projection-publication-root> \
  --source-projection-attempt-id <new-attempt-id> \
  --source-projection-max-seconds 900
```

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
