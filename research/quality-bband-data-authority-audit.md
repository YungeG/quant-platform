# Quality + B-Band A-share data-authority audit

- **Plan:** `cn-a-share.quality-bband-breakout.manual4.v1`
- **Market:** XSHG/XSHE domestic ordinary A-share cash auction
- **Account:** CNY 200,000, long-only, maximum four positions
- **Authority cutoff:** Platform `04b01a1`; Backtest gitlink `8de544e7794ee05b652355c9809b5454d7ace494`
- **Decision:** `PLAN_ONLY / DATA_AND_PREPARATION_BLOCKED`

This audit checks whether each strategy input is currently usable as Platform evidence. Local research data is evidence inventory only until Backtest owns an immutable G12A snapshot, normalization, publication, coverage result, compatible Profile, and concrete public preparation operation.

## 1. Capability matrix

| Requirement | Required semantics | Existing evidence | Status | Exact blocker / next authority |
| --- | --- | --- | --- | --- |
| Daily OHLCV and amount | Raw historical facts with event and availability time; execution and valuation purpose separation | Tushare daily normalization/publication exists; exact accepted source-bounded slice is one instrument and 19 July-2026 dates | `BOUNDED_ACCEPTED_ONLY` | General multi-instrument daily acquisition, immutable revisions, coverage, and retained Bundle refs are absent. |
| Bar-open execution projection | T-day close decision, next eligible real open, no future high/low/close/volume | Fixed-singleton G12M v2 publishes `bar_open@1` projections | `FIXED_SINGLETON_ONLY` | No general portfolio Bundle/projection publication and no portfolio preparation operation. |
| Instrument catalog body | Stable Instrument identity, venue, board/product, currencies and listing context | G12CD v2 binds a one-instrument catalog; G12C otherwise carries only opaque catalog hash | `FIXED_SINGLETON_ONLY` | Canonical full catalog artifact exact-bound to each MarketBundle is missing. |
| Point-in-time listing and delisting | Effective and available intervals, revisions and corrections | One `000001.SZ` listing-presence source-bounded observation exists | `GENERAL_BLOCKED` | General historical lifecycle, continuity, completeness and availability authority are not accepted. |
| Dynamic universe | Membership intervals and revisions, no survivorship projection | G11C can evaluate supplied revisions; SW2021 local files retain in/out dates | `NONAUTHORITY_INPUT_ONLY` | G12B normalized membership source contract, G12K closure declaration and provider completeness are missing. |
| ST/risk-warning and suspension history | Point-in-time status and classified no-trade/missing-data states | Local DuckDB contains current/historical-style fields; Backtest A-share rules can consume supplied status evidence | `GENERAL_BLOCKED` | No accepted provider revision/availability/closure for full historical status. Missing status must block, not infer from bars or names. |
| Board/listing-phase price limits | Historical board, risk class and listing phase exact rule bands | G08D order-rule model and development rule books exist | `ECONOMIC_MODEL_AVAILABLE` | General historical rule-source coverage and strict successor closure remain incomplete. |
| T+1 and lot lattice | Sellable quantity, 100-share buys, supported odd-lot close | G08B/G08C models are accepted | `MODEL_AVAILABLE` | Requested full account/instrument scope still needs compatible resolved Profile and public PREP binding. |
| Fees, minimum commission and sell tax | Exact route/product/time RuleBooks | Route/product V2 model exists; current-selected development path exists | `DEVELOPMENT_LIMITED` | Historical strict fee/tax successor closure remains blocked; account broker minimum commission requires immutable account authority. |
| Corporate actions | Announcement, record, effective/listing and payment lifecycle; entitlement and accounting | G08F/G08G economic models exist; one fixed-instrument dividend response is source-bounded | `GENERAL_BLOCKED` | No real closed action inventory, provider revision closure or general G12K lifecycle coverage. |
| Adjustment factors | Signal-only point-in-time adjusted observations, never execution fills | Tushare `adj_factor` acquisition is documented and local derived data exists | `NONAUTHORITY_INPUT_ONLY` | Provider revision/correction closure and point-in-time publication authority are absent. Ex-post adjusted series cannot create fills. |
| Five-year ROIC/ROCE | Complete annual statements with announcement/availability time and consistent calculation | External DuckDB has narrow `FinancialIndicatorData` and `IncomeData`; inventory found only ten covered symbols in extended tables | `INSUFFICIENT` | No broad raw statement source snapshot, normalized schemas, calculation identity, revision chain or availability coverage. |
| Operating/free cash flow | Five complete years and restatements | External research tables only | `INSUFFICIENT` | Cash-flow source bytes, announcement times, revisions and canonical calculation are missing. |
| Net debt / EBITDA | Point-in-time balance-sheet and income-statement composition | No accepted Backtest capability | `MISSING` | New financial-statement source and normalized feature authority required. |
| Audit opinion | Exact report opinion, announcement time, correction/reissue lineage | No accepted or inventoried full-market authority | `MISSING` | Provider/source contract and immutable historical capture required. |
| Regulatory penalties / fraud | Issuer-scoped official acts with record and availability time | No accepted dataset | `MISSING` | Competent official source acquisition and correction/successor closure required. |
| Controlling-shareholder pledge | Historical pledge ratio with announcement and effective time | No accepted dataset | `MISSING` | Point-in-time pledge source authority required. |
| Historical valuation percentile | Point-in-time valuation observations and five-year window | External DuckDB `FundamentalData` contains daily PE/PB/market value | `NONAUTHORITY_INPUT_ONLY` | Mutable lake has no provider revision/checksum/availability authority and is not a MarketBundle capability. |
| Industry diversification | Point-in-time L1 membership | Git-tracked SW2021 membership evidence and external DuckDB history exist | `NONAUTHORITY_INPUT_ONLY` | Must enter a G12A snapshot, normalized membership events and G12K coverage; current taxonomy cannot be projected backward silently. |
| Strategy observation inputs | Least-authority point-in-time views, windows and Universe selection | G11A-I runtime contracts exist | `RUNTIME_MODEL_AVAILABLE` | No accepted A-share portfolio composition/preparation binds these inputs to an executable request. |
| Public Backtest preparation | Concrete provider/strategy operation that owns request, semantic run and resolved profile | Public root exports only generic cash development and model-bound cash preparation | `MISSING` | Required accepted public portfolio A-share preparation operation does not exist. |

## 2. Existing local evidence that must not be mistaken for authority

The strongest local A-share research lake is:

```text
/srv/bcache-8t/ygguo/duckdb/quant-a50/quant_a50.duckdb
```

It contains broad daily prices, valuation snapshots, market values, industry data, margin data and limited financial statements. It is mutable, not Git-bound, and has no provider checksum, revision/correction closure or historical availability authority. Derived Parquet, DuckDB and pickle caches are downstream research products, not G12 source evidence.

A stable May-2021-style backup has a recorded local SHA-256 and is a better bounded acquisition candidate, but still needs a Backtest-owned exact query, canonical export, acquisition receipt, source snapshot and explicit nonclaims before use.

## 3. Minimum immutable data package

A future executable Fold must publish one exact Bundle family containing or binding:

1. `instrument_catalog@1` — canonical full body, not only a hash;
2. `listing_membership_revision@1` — listing, delisting and selected-Universe membership revisions;
3. `trade_status_revision@1` — ST/risk-warning, suspension and supported status transitions;
4. `daily_raw_bar@1` plus purpose-separated execution-reference and valuation projections;
5. `corporate_action_lifecycle_revision@1` — announcement, eligibility, adjustment/listing and payment states;
6. `financial_statement_revision@1` — annual/quarterly statement identity, announcement and availability time, revision/supersession lineage;
7. `quality_feature_manifest@1` — exact ROIC/ROCE, free-cash-flow and leverage calculation identity over statement refs;
8. `audit_governance_revision@1` — audit opinion, competent penalties/fraud acts and controlling-shareholder pledge observations;
9. `valuation_observation_revision@1` — point-in-time PE/EV-style values used for the five-year percentile;
10. exact historical order-rule, fee/tax and account-route authorities required by the resolved A-share Profile.

The names above are provisional planning vocabulary, not accepted public schemas. G12B/contract approval must freeze exact names, fields and failure precedence before implementation.

## 4. Fold slices and revision requirements

| Fold | Warmup | Discovery | Holdout | Required revision property |
| --- | --- | --- | --- | --- |
| A | `[2010-01-04, 2015-01-05)` | `[2015-01-05, 2021-01-04)` | `[2021-01-04, 2024-01-02)` | One immutable revision exact-covering all three intervals; holdout identity frozen before selection observation. |
| B | `[2013-01-04, 2018-01-02)` | `[2018-01-02, 2024-01-02)` | `[2024-01-02, 2026-04-01)` | Independent immutable revision and Validation flow; Fold-A refs cannot substitute. |

No dataset revision currently satisfies these requirements. Proposed labels such as `cn-a-share-quality-bband-fold-a-v1` are not refs until published with canonical content hashes.

## 5. Fail-closed precedence for data admission

1. Unknown or conflicting Instrument identity;
2. missing/overlapping listing or Universe revision;
3. missing status, rule or calendar coverage;
4. future or ambiguous financial/governance availability;
5. financial revision fork, missing parent or calculation-manifest mismatch;
6. missing corporate-action lifecycle coverage for an eligible/held Instrument;
7. missing fee/tax/account-route authority;
8. missing execution or valuation price-purpose coverage;
9. retention/tamper/publication failure.

Any applicable failure blocks preparation. It must not become an empty Universe, zero metric, fabricated Backtest terminal or silent removal of the affected stock.

## 6. Capability decision

The strategy is not executable today because both of these are absent:

- a qualified multi-instrument A-share data/Profile package for the requested intervals and feature set;
- a concrete accepted public Backtest preparation operation for that package and strategy scope.

The next implementation authority should first freeze a bounded data contract and publication/coverage plan. Strategy code and Research Experiment execution remain downstream and must not begin by reading the mutable lake directly.

## Sources

- [`backtest/docs/implementation/plans/g12/README.md`](../backtest/docs/implementation/plans/g12/README.md)
- [`backtest/docs/research/cross-project-market-data-inventory.md`](../backtest/docs/research/cross-project-market-data-inventory.md)
- [`backtest/docs/research/g12k-universe-corporate-action-coverage.md`](../backtest/docs/research/g12k-universe-corporate-action-coverage.md)
- [`backtest/docs/research/g12l-tushare-listing-corporate-action-revision-authority-v1.md`](../backtest/docs/research/g12l-tushare-listing-corporate-action-revision-authority-v1.md)
- [`backtest/docs/implementation/plans/g12/g12m-tushare-fixed-singleton-qualification-v2.md`](../backtest/docs/implementation/plans/g12/g12m-tushare-fixed-singleton-qualification-v2.md)
- [`research/investment-book-strategy-ideas.md`](investment-book-strategy-ideas.md)
