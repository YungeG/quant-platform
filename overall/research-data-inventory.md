# Research data inventory

Read-only inventory of the datasets most relevant to the proposed strategy directions. This file records existing local artifacts; it does not qualify a provider, authorize a Backtest, or promote exploratory results to Platform evidence.

## Existing research priorities (not executed by dependency alignment)

1. Preserve the untracked A-share artifacts before running new research.
2. Use the five-ETF stock/bond/gold panel as the first bounded pilot.
3. Treat analyst/PEAD data as the next alpha candidate.
4. Do not start global, FX, options, or multi-coin research until data is acquired.

## A-share exploratory datasets

Root: `/home/ygguo/agent-projs/ai-crypt/platform-a-share-research`

| Dataset | Coverage / shape | SHA-256 | Git state | Usable for |
| --- | --- | --- | --- | --- |
| `overall/a-share-size-etf-daily.csv` | 5 ETFs; 11,914 rows; 2016-11-04—2026-08-25 | `00b1c1da101b60a67fa8ee21bb1eb4b8d261806262103ea1f1097f72ce352ca0` | **untracked** | Stock/bond/gold allocation, size rotation, trend |
| `overall/a-share-sector-etf-raw-v2/fund_daily.parquet` | 258 ETFs; 251,668 rows; 2018-01-02—2026-08-27 | `f0088ccf67b1f2e0f20eb54af9fa7cde2d5afa512548d0ef509fe99114647acb` | **untracked** | Sector ETF momentum/rotation |
| `overall/a-share-sector-etf-raw-v2/fund_adj.parquet` | 258 ETFs; 252,324 rows | `eb4ed5f3d9365697a664f067b4eefecd29474a6ab66a603e434c4507ff0e8124` | **untracked** | ETF adjustment factors |
| `overall/a-share-sector-etf-raw-v2/fund_share.parquet` | 263 ETFs; 239,025 rows | `10d6bbb24fd57ebba2d401312e23872b80e83e313c7f553bfc93bf4845552429` | **untracked** | ETF share-flow research |
| `overall/a-share-pit-quality.csv` | 139,506 rows; 6,734 securities; announcements 2013-01-19—2026-08-27 | `500a7e5251a17bfde125b5d5637bd2a7063006cbdd8f02a71335ddaa9f38036e` | **untracked** | PIT ROE, margin, leverage quality |
| `overall/a-share-quarterly-statements-raw/fina_indicator_vip.csv` | 413,566 rows; 6,729 securities; 2015-04-07—2026-08-28 | `c1662888300b371e282bde4fa38c1d956443b2a4a9398b349e07a28324ee6838` | **untracked** | Fundamental momentum and quality |
| `overall/a-share-analyst-revision-signals.csv` | 51,114 rows; 1,330 securities; 2017-01-26—2026-08-26 | `a6ddcccd108700b38d57867072505207634bf6e97406aee2451263ee7fae43d4` | **untracked** | Analyst revision strategies |
| `overall/a-share-earnings-surprise-events.csv` | 3,791 events; 884 securities; 2017-01-25—2026-04-30 | `415bda5aff6b8725e0c267f2634ce829a981fd4f29235ce06ee36d8ec45f0850` | **untracked** | PEAD / earnings surprise |

### Verified locations — 2026-09-21

The source `/srv/bcache-8t/ygguo/duckdb/quant-a50/quant_a50.duckdb` exists (1,720,987,648 bytes at inspection). Searching only `/home/ygguo` cannot establish that this database is absent. Its tables, date coverage, input compatibility and provider-availability authority were **not** read or qualified in this check. Presence does not authorize a rerun or reuse of old result claims.

The size-ETF CSV, sector-ETF daily Parquet and PIT-quality CSV above were also verified to exist (1,043,401; 6,214,947; and 7,104,412 bytes respectively). Coverage and hashes in the table are the original inventory's recorded values, not newly revalidated sample evidence. The old relative path `platform/overall/a-share-multi-asset-etf-daily.csv` is absent; this is a path mismatch, not proof that all reusable data is missing.

`platform-a-share-research` contained 25,520 untracked files at the 2026-09-21 inspection, 25,391 under `overall/`. They remain in place. The dependency-alignment operation did not open those market samples or verify an independent full backup. The separate directory-organization operation verified an independent-disk snapshot on **2026-09-22**, as recorded below. This does not authorize removing the original worktree or imply that merging its branch copies its data.

D004's frozen diagnostic CSVs remain at `/home/ygguo/agent-projs/ai-crypt/platform/research/evidence/a-share-market-regime-20260921/public-full-v2/` (`prices.csv` and `calendar.csv`). They are untracked original-worktree artifacts, not automatically present in another checkout. A verified recovery archive of the original Platform worktree's 84 untracked files is retained in `/home/ygguo/agent-projs/ai-crypt/.dependency-alignment-safety-20260921/platform-untracked.tar.gz`; this is a recovery copy, not Backtest publication or historical availability evidence.

### Verified independent backups

On **2026-09-22**, the two retained A-share workspaces were archived under `/srv/bcache-8t/ygguo/ai-crypt-backups/organization-20260921-hW0Sw8/`, on a different local filesystem/device from their source directories. Each workspace has its own `working-tree.tar`, Git administrative archive, patches, `SHA256SUMS`, and verification record.

| Workspace | Working-tree archive bytes | Recorded archive SHA-256 | Verification time (+08:00) |
| --- | ---: | --- | --- |
| `platform-a-share-research` | 2,275,307,520 | `159af334127619e0882583b0e5272e2800327b2d6f361153dfc3ee006416bc46` | 2026-09-22 09:03:59 |
| `platform-sector-trend` | 5,488,814,080 | `5c9e69e91b524f4c605928870147777ef53034c46428d9c99745c0cbfd68cc15` | 2026-09-22 09:04:25 |

Both archives were compared against their source files, with matching before/after file metadata and Git status, then checksum-verified. The representative CSV/Parquet smoke also passed extraction and byte comparison, and rejected a missing input. Snapshot bytes include ignored research data; they exclude Git metadata from the working-tree tar (archived separately), virtual environments, reproducible caches/egg-info, and live `.pi/`/`.omx/` state. Both source directories are retained; `platform-sector-trend` also owns the portfolio worktree's Git metadata.

This closes the previously unknown independent backup status **for these snapshots only**. It is not offsite coverage, a guarantee about subsequent writes, or a new consistency-verified snapshot of the active KORU formal-discovery tree. Backup checks did not qualify market-data coverage, historical availability, a provider, or a strategy result. See the [retirement follow-up](../implementation/dependency-alignment-20260921.md#worktree-retirement-follow-up) and the backup's `DIRECTORY-INDEX.md` for recovery boundaries.

## A-share retained dividend authority

Root: `/home/ygguo/agent-projs/ai-crypt/platform-sector-trend`

| Dataset | Coverage / shape | SHA-256 | Git state | Limitation |
| --- | --- | --- | --- | --- |
| `overall/a-share-cninfo-dividend-2022-2025-normalized.csv` | 15,652 announcements; 4,398 securities; 14,691 ordinary-A cash lifecycles reported complete for the research slice | `0e381e5755ec18e1bba00e136aae8e4a64cd95d2d4c7d1e55a90d4dfbe6c0a55` | tracked | One payment date uses a captured supplemental vendor source; no formal multi-stock Backtest |
| `overall/a-share-dividend-growth-cash-coverage-state-v1.csv` | 2,371 three-year states; 299 pass the frozen growth/coverage rule | `f76e64aadc4d2fdd4d9e409066af27865350ee6a4d3351a350c7192ea0eccc9c` | tracked | Target state only; `NO_BACKTEST`, `trade_authorized=false` |

## Crypto datasets

### KORUUSDT narrow research slice

Root: `/home/ygguo/agent-projs/ai-crypt/platform-koru-research`

| Dataset | Coverage / shape | SHA-256 | Git state | Limitation |
| --- | --- | --- | --- | --- |
| `research/koruusdt/data/aligned_hourly.csv` | 1,509 hourly rows; 2026-06-22—2026-08-24 | `ca6d2b068b5233a5c3387425a966e3a502872692e75835a5b2f20a28b5357251` | tracked | Single instrument, short sample, secondary Yahoo factors |
| `research/koruusdt/data/manifest.json` | Source and transformation manifest | `c20ab7e8444e4f2a60e6e2b10e9faf57345e68c6cd10a4682c744f3fe4f91a80` | tracked | Exploratory; `TRADIFI_PERPETUAL` is outside the accepted Binance `PERPETUAL` identity |
| `research/koruusdt/data/execution_data_manifest.json` | Aggregate trades/mark/index/funding execution-data inventory | `6dae2b8182aaaa26e71be5d3a2462cd75562a2142cdf43b6962268ab7d618977` | tracked | Development-only; not official Experiment or decision-grade evidence |

### Binance BTC fixtures

Root: `/home/ygguo/agent-projs/ai-crypt/platform/backtest`

| Dataset | Scope | SHA-256 | Git state | Limitation |
| --- | --- | --- | --- | --- |
| `tests/fixtures/market_data/providers/binance_usdm/aggtrades-v1/BTCUSDT-aggTrades-2020-01-01.zip` | 71,359 trades; one day | `638e72c179e4965c2a6521bb27295930d09126433efe0cc3acd4e925ada955ac` | tracked | Not enough for a strategy study |
| `tests/fixtures/market_data/providers/binance_usdm/mark-price-klines-v1/BTCUSDT-1m-2024-01-01.zip` | 1,440 one-minute marks; one day | `660efeefdc875f052051b94c2976babd013f64c6633bf58ba030764771747b90` | tracked | Different date from trades/funding |
| `tests/fixtures/market_data/providers/binance_usdm/funding-rate-v1/BTCUSDT-fundingRate-2020-01.zip` | 93 funding rows; one month | `7f81b2f3694d13779e7e896b69d60cd61e9444d7b9f9e90df761935e1c1b76e2` | tracked | No matching funding marks; no G12M qualification |

## Missing strategy-scale datasets

- Global equity constituent history and point-in-time fundamentals.
- FX forward/rate panels across currencies.
- Commodity futures curves, expiry/roll metadata, margin and fee histories.
- Option chains, implied volatility surfaces, settlements and margin rules.
- Multi-coin spot/perpetual/futures/funding panels and venue/account histories.

## Platform capability boundary

- Backtest `8cc5b874c31c38a6ec7526d1dbf345b93998a39f` exports `prepare_cn_a_share_development_backtest` in addition to the three generic cash preparation functions. The earlier claim that only cash preparation existed described the old installed `f73d068d` environment, not the newer source tree.
- This public A-share route is the bounded `000703.SZ` development path, with closed-bar fills, fees and T+1 behavior; it is **not** a general multi-instrument portfolio or decision-grade seam. Its existing two-session public fixture was executed successfully in the isolated aligned environment; no user strategy or live market study was run.
- The separate `quant-backtest-a-share-portfolio` branch has accepted Phases 1–4 and a Phase 5 repair at `75d8f8a`; a subsequent Phase 5 acceptance was not found. Its profile/public-provider phases remain separate work. Both it and the published line use `backtest_execution_input_bundle@7` for different payloads: preserve the published format and resolve protocol ownership before integration. Code presence is not acceptance.
- On 2026-09-21, the validated commit `611b573` was fast-forwarded into the original `platform` worktree, whose environment was rebuilt offline at its final path. At that cutover, all five installed Backtest-family packages matched `8cc5b874`; post-cutover alignment/integration and D004 unit checks passed. The `platform-dependency-alignment` candidate worktree was subsequently retired on 2026-09-21 after recovery archives and its module histories were preserved; its branch remains. The old original-worktree environment and original untracked inventory are also retained. See [the cutover receipt and retirement follow-up](../implementation/dependency-alignment-20260921.md#worktree-retirement-follow-up) for the historical checks, later directory state and recovery boundaries.

- `implementation/roadmap.md` retains broad A-share qualification as `TSR-ASH-Q-01 / SEPARATE_H2` and Binance causal qualification as `TSR-BIN-Q-01 / SEPARATE_H3`.

No dataset in this inventory by itself authorizes decision-grade, live, or deployment use.
