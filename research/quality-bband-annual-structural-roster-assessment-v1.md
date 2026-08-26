# Quality + B-Band annual structural roster assessment v1

- **Status:** `SOURCE_BOUNDED_CAPTURE_VALID / 2017-2025_FUNNEL_ADVISORY / FORMAL_S1_FALSE`
- **Checked:** 2026-08-26
- **Implementation:** Backtest PR #11 / commit `1ba50ff69d1cdf37132e6e20ac1695bed0fbf685`

## 1. Candidate

```text
/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/
  annual-structural-roster-source-snapshots/2016-2025/20260826/v1-candidate-01
```

| Identity | Value |
| --- | --- |
| SourceSnapshot | `sha256:22585fa4c2070d87544f0ba977be757770aeeaad5bead30188317c1794680ee8` |
| Content tree | `sha256:7e4046b2ffc13993de8ab33ddbe4410aef2f464d8c16b19000998acbb20cbb9e` |
| Provenance | `sha256:7bb6d65da4702e6c34649cf52dc0285fb2e2115246fca0e978b434da6176af22` |
| Snapshot file | `sha256:ed7f01abb90c0b937078beb39739202ec80070e61c26e6d624dd70f8a6181ad1` |
| Receipt file | `sha256:9eab20190ae05c4a49a8763ad77cfc9d1ed874c7c56e2258f3a595e2a8b7c9d6` |

The candidate contains exactly eleven raw members plus snapshot and receipt. All files are mode `0600`; independent reconstruction exactly reproduced the snapshot.

## 2. First-attempt correction

The first real publication attempt failed atomically because historical `bak_basic` rows use `list_date="0"` for provider-unknown/prelisting records. No output directory survived.

The packet and implementation were corrected to retain `"0"` as unknown rather than treating it as a date or exclusion. The valid candidate was then published by the corrected commit.

## 3. Raw annual evidence

| Screen | Rows | `list_date="0"` |
| --- | ---: | ---: |
| `20160503` | `0` | `0` |
| `20170502` | `3,232` | `26` |
| `20180502` | `3,518` | `5` |
| `20190506` | `3,622` | `12` |
| `20200506` | `3,850` | `17` |
| `20210506` | `4,326` | `39` |
| `20220505` | `4,719` | `10` |
| `20230504` | `4,994` | `22` |
| `20240506` | `5,364` | `3` |
| `20250506` | `5,415` | `5` |

The retained trade calendar has `3,298` rows and source-bounded derives the frozen screen dates. It is not accepted general Calendar authority.

## 4. Advisory structural funnel

Joining annual rosters to the current S0 capture and applying only provisional current-market/provider-industry rules:

| Screen | Mainboard via current S0 | Valid listed five years | Provider non-financial candidate |
| --- | ---: | ---: | ---: |
| 2017 | `2,591` | `2,052` | `1,995` |
| 2018 | `2,791` | `2,098` | `2,034` |
| 2019 | `2,861` | `2,119` | `2,053` |
| 2020 | `2,934` | `2,218` | `2,143` |
| 2021 | `3,083` | `2,300` | `2,224` |
| 2022 | `3,152` | `2,526` | `2,434` |
| 2023 | `3,203` | `2,705` | `2,612` |
| 2024 | `3,199` | `2,738` | `2,635` |
| 2025 | `3,181` | `2,776` | `2,667` |

The union of provisional 2017–2025 candidates is `2,845` Instruments. This is the estimated maximum S2 minimal-financial workload for a source-bounded development path, not a formal S1 output.

## 5. Nonclaims

- 2010–2015 annual roster observations remain absent;
- 2016 screen is an explicit provider gap, not an empty market;
- `bak_basic` can contain never-listed/prelisting rows;
- current S0 `market` is not historical board authority;
- provider `industry` is not official CSRC history;
- unmatched/restructured codes remain unresolved;
- revision, completeness, absence and terminal authority are missing.

All receipt qualification, safety, grade and deployment flags remain false.

## 6. Decision

The annual capture materially bounds a source-bounded 2017–2025 funnel and shows that a minimal S2 financial request union would be about `2,845` issuers rather than every raw market row.

Formal Fold A/B S1 remains blocked. Proceeding to heavy S2 acquisition requires a separately approved source-bounded development contract and must not be represented as historical survivorship-safe evidence.
