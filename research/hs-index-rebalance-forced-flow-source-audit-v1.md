# HS300 / CSI500 / CSI1000 rebalance forced-flow source audit v1

- **Status:** `SOURCE-BLOCKED / NO_BACKTEST_RUN`
- **Checked:** 2026-08-31
- **Scope:** pure-stock inclusion/exclusion flow for HS300 (`000300`), CSI500 (`000905`), and CSI1000 (`000852`).

## Decision

Do not implement or run this strategy. The available data has daily stock prices and SW industry membership, but no historical CSI index-rebalance event source. In particular, no source establishes what was announced when. Using current constituents, effective-date snapshots without publication timing, or a fetch timestamp would violate the point-in-time requirement and create look-ahead bias.

## Local audit

Repository-tracked files contain no DuckDB, Parquet, or CSV constituent-history dataset for these indices. The only tracked CSVs are `overall/*shadow-ledger.csv`; neither their paths nor contents concern index membership.

The read-only external lake was inspected at:

```text
/srv/bcache-8t/ygguo/duckdb/quant-a50/quant_a50.duckdb
sha256:21c1180178e8aa19c23aa1f0d5b37abe63de71bae1b32f43808817656799d8ce
size:1,714,171,904 bytes
```

Its tables are `MarketData`, `DelistedMarketData`, `StaticData`, `DelistedStaticData`, `FundamentalData`, `FinancialIndicatorData`, `IncomeData`, `IndustryDailyData`, `IndustryMemberData`, `IndustryMemberHistoryData`, `IndustryTaxonomyData`, `IntradayData`, `MarginDetailData`, `NameChangeData`, and macro tables. `IndustryMemberData` has `IndexCode`, `IndexName`, `Symbol`, `TSCode`, `InDate`, `OutDate`, `IsNew`, and `UpdateAt`; it is SW industry data, not CSI index membership. No table contains `000300`, `000905`, or `000852` constituent events, announcement/publication time, effective membership revisions, or source version lineage.

`backtest/docs/research/cross-project-market-data-inventory.md` independently records the same lake as mutable/non-Git-bound and describes its membership tables as SW industry taxonomy data. It also states that it has no provider checksum, exchange publication identity, correction terminal set, or historical availability authority. `research/a-share-strategy-baseline.md` records the same unresolved historical-membership gate and forbids reconstructing membership from current constituents.

## Exact missing seam

Before this strategy may be pre-registered or backtested, acquire a complete immutable event feed for all three indices with one record per announced constituent change and revision containing:

1. CSI index code and canonical security identifier;
2. inclusion/exclusion action and the announced effective trading date;
3. source-declared announcement/publication timestamp (including timezone or an unambiguous exchange-session interpretation);
4. immutable official/vendor source bytes, URI, content hash, acquisition receipt, and revision/supersession identity;
5. coverage and terminal-completeness authority across the proposed sample, including ad-hoc rebalances and corrections.

This seam is specifically **announcement availability**, not merely membership effective dates. It is required to map the announcement to the first eligible decision session; without it, the requested T+1 entry/exit rule cannot be evaluated causally.

Once that feed is qualified, pre-register the announcement-to-effective entry/exit mapping, T+1 handling, commissions/taxes/slippage, board-lot rounding, limit/suspension and liquidity rules, holding/exit horizon, and an untouched chronological holdout before implementation. No such assumptions or returns are fabricated here.

## Reproducibility commands

```bash
sha256sum /srv/bcache-8t/ygguo/duckdb/quant-a50/quant_a50.duckdb
/home/ygguo/agent-projs/cycle-rotation-platform-fresh-validate-20260513/venv/bin/python - <<'PY'
import duckdb
p = '/srv/bcache-8t/ygguo/duckdb/quant-a50/quant_a50.duckdb'
with duckdb.connect(p, read_only=True) as con:
    print(con.sql("select table_name from information_schema.tables where table_schema='main' order by table_name").fetchall())
PY
git ls-files | grep -Ei '\.(duckdb|db|parquet|csv)$|(^|/)(data|artifacts|evidence)/'
```
