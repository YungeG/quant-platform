# Quality + B-Band S0 lightweight catalog assessment v1

- **Status:** `SOURCE_BOUNDED_CAPTURE_VALID / FUNNEL_SIZE_ADVISORY / S0_AUTHORITY_FALSE`
- **Checked:** 2026-08-26
- **Implementation:** Backtest PR #10 / commit `ea17ccf93f6242222800c298d6aab39177b8455d`

## 1. Candidate

```text
/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/
  s0-lightweight-source-snapshots/stock-basic/20260826/v1-candidate-01
```

| Identity | Value |
| --- | --- |
| SourceSnapshot | `sha256:b5b7a9243439146181ef07acd07c09e79d16f605bc6cfdc3148746e64359e198` |
| Content tree | `sha256:5533ce876c38ff320b69ca876dff57af763168d654f82142e9c53c90ecca2418` |
| Provenance | `sha256:953aecfb488562177a51392283d8dace326470041cc0594d8982fb3482849c36` |
| `L` raw | `sha256:e20377596b5c3e6150d57a113f612a1f5d21d3965b1746d51315b6d7a2039fe2` / `1,282,726` bytes / `5,550` rows |
| `D` raw | `sha256:b41e1d8c39260e3768018def10522d5e0bf916ed5c8f8115382577aa9be9725e` / `76,654` bytes / `339` rows |
| `P` raw | `sha256:62ac08161a278087a96000da49aaaba85b3c04b0d1cdcf5278678ad9d736ff4b` / `324` bytes / `0` rows |

All five files are mode `0600`; the receipt and snapshot agree on member hashes, sizes and individual post-response timestamps.

## 2. Advisory current-snapshot funnel

These counts are research summaries recomputed from retained raw rows. They are not normalized S0/S1 manifests.

| Step | Rows |
| --- | ---: |
| All returned `L/D/P` rows | `5,889` |
| SSE/SZSE + CNY, all returned statuses | `5,546` |
| Current `L` SSE/SZSE + CNY | `5,212` |
| Current Main Board | `3,193` |
| Current Main Board with `list_date <= 20210826` | `2,955` |
| Above, excluding provider industries `银行/保险/证券/多元金融` | `2,841` |

The staged funnel therefore has material workload-reduction potential: current heavy financial acquisition would target roughly `2,841` provisional structural survivors rather than every `5,889` returned row.

## 3. Why the count is advisory only

- `stock_basic` is current metadata, not historical-as-of revisions;
- current board and provider industry cannot be projected backward;
- `industry` is not frozen CSRC historical authority;
- `328` of `334` delisted SSE/SZSE rows have null current `industry`;
- one delisted row uses provider code `T600018.SH` and null `market`, so code continuity/canonical Instrument mapping is unresolved;
- `P=0` proves only that this request returned zero rows at acquisition time;
- the provider exposes no revision, supersession or terminal completeness identity.

No row may be officially excluded from a historical Fold using these current fields alone.

## 4. Fixed nonclaims

The candidate remains:

```text
historical_as_of_qualified = false
provider_completeness_qualified = false
revision_closure_complete = false
survivorship_bias_safe = false
industry_history_qualified = false
trade_status_history_qualified = false
decision_grade_eligible = false
deployment_authorized = false
absence_authority = false
```

It grants no S0 authority, S1 structural eligibility, Strategy, Backtest, Validation or trading authority.

## 5. Decision

The S0 plumbing capture succeeded and demonstrates that staged acquisition can avoid obvious heavy-data overcollection. Formal S1 cannot start until a competent historical listing/board/CSRC-industry source or an explicitly lower-grade source-bounded S1 contract is approved.
