# ETF-DATA-01 — A-share ETF prospective data contract v1

> Archive note (2026-09-22): This preserves the original design/status record, not a new implementation or execution approval. Frozen terms, status labels, hashes and reported checks below keep their original scope; no source authority, live-smoke result or holdout-consumption status was revalidated for this commit. Referenced local evidence and submodule work are not published by this document commit. Historical paths may have moved; see the [data inventory](../../overall/research-data-inventory.md). The [dependency alignment](../dependency-alignment-20260921.md) and callable ordinary-stock preparation do not establish an accepted three-ETF portfolio route. All readiness and separate authorization gates remain in force.

- **Status:** `DEFERRED / NOT REQUIRED FOR CURRENT HISTORICAL BACKTEST`
- **Owner:** Backtest G12 acquisition + Market Bundle Builder
- **Consumer:** future A-share ETF profile and portfolio preparation operation
- **Strategy scope:** secondary-market trading of `510300.SH`, `511010.SH`, and `518880.SH`
- **Formal interval:** prospective holdout `[2026-09-01, 2027-09-01)`

## 1. Outcome

Deferred objective: publish one immutable, source-bounded, development-grade MarketBundle for the exact three-ETF catalog and one finite interval. Runtime receives only retained artifacts and never reads Tushare, exchange pages, CSV files, credentials, or the system clock.

This contract covers secondary-market buy/sell only. It excludes ETF creation/redemption, physical-gold delivery, pledge/repo, lending, margin, shorting, market making, queue claims, and live/deployment authority.

The existing historical CSV remains exploratory input only:

- path: `/home/ygguo/agent-projs/ai-crypt/platform-a-share-research/overall/a-share-multi-asset-etf-daily.csv`;
- SHA-256: `a6b128c8a049e60e48d82c242c1a94502a5dbdefd2346bc870449bb18fbcafdd`;
- 7,800 rows, 2,600 common dates per ETF, `2015-12-14` through `2026-08-25`;
- no retained raw responses, acquisition receipts, request scopes, pagination proof, availability instants, or revision lineage.

It must not be relabelled as a formal MarketBundle or OOS dataset.

## 2. Authority

| ID | Source | Requirement |
| --- | --- | --- |
| D1 | `overall/a-share-multi-asset-prospective-validation-design.md` | Freeze the three instruments, prospective interval, conservative two-session liquidation/purchase execution, and no historical OOS relabelling. |
| D2 | `backtest/docs/research/g12a-source-snapshot-contract.md` | Retain exact source members and acquisition provenance before normalization. |
| D3 | `backtest/docs/research/g12i-price-availability-revision-coverage.md` | Event time, availability, absence classification, and revision closure remain separate authorities. |
| D4 | `backtest/docs/research/g12k-universe-corporate-action-coverage.md` | Catalog, listing lifecycle, and fund distributions require normalized revisions and explicit closure. |
| D5 | `backtest/docs/research/g12l-cn-a-share-daily-numeric-mapping-v1.md` | Reuse only the exact-lexeme and purpose-separation pattern. Its stock `daily` units do not authorize ETF `fund_daily` units; ETF mapping needs a separate frozen source case. |
| D6 | [Tushare `fund_daily`](https://tushare.pro/document/2?doc_id=127) | Candidate source for post-close raw ETF OHLCV; maximum 5,000 rows per request. |
| D7 | [Tushare `fund_adj`](https://tushare.pro/document/2?doc_id=199) | Adjustment-factor candidate only; not execution or corporate-action lifecycle authority. |
| D8 | [Tushare `fund_basic`](https://tushare.pro/document/2?doc_id=19) | Candidate source for current listed-fund identity; no immutable historical revision closure is documented. |
| D9 | [SSE ETF rules](https://www.sse.com.cn/assortment/fund/etf/rules/) | Product-specific trading, settlement, order, and lifecycle rules must be first-party and effective-dated. |
| D10 | [SSE bond ETF guide](https://etf.sse.com.cn/ruleguide/guide/c/5287915.shtml) | `511010.SH` supports T+0 secondary-market trading, 100-share lots, and bond-ETF-specific rules. |
| D11 | [SSE gold ETF guide](https://www.sse.com.cn/assortment/fund/etf/rules/c/c_20150911_3985190.shtml) | `518880.SH` supports T+0 secondary-market trading, 0.001 CNY tick, 100-share lots, and 10% price limits. |
| D12 | [SSE fee schedule](https://www.sse.com.cn/services/tradingservice/charge/ssecharge/) | Exchange fees differ by ETF product; bond ETFs may be waived. Account commission remains a separate Profile authority. |
| D13 | `implementation/plans/a-share-etf-rule-mapping-v1.md` | Freeze the initial product/session/order/settlement/fee/tax mapping and bind the retained 18-source evidence manifest. Future revision closure remains open. |
| D14 | `implementation/plans/a-share-etf-lifecycle-source-contract-v1.md` | Freeze bounded daily listing/status, suspension, announcement, and distribution source capture plus lifecycle closure semantics. |
| D15 | `backtest/docs/adr/0010-xiaodefa-is-approved-tushare-transport-proxy.md` | Authorize Tushare-compatible calls only through one pinned Xiaodefa HTTPS endpoint with `x-api-key`, no redirects/failover, redaction, and retained transport identity. |

## 3. Exact instrument scope

| Instrument | Venue | Product class | Secondary-market availability |
| --- | --- | --- | --- |
| `xshg:510300` | XSHG | domestic equity ETF | same-day resale not authorized by the ordinary ETF rule |
| `xshg:511010` | XSHG | bond ETF | T+0 secondary-market trading |
| `xshg:518880` | XSHG | gold ETF | T+0 secondary-market trading |

All instruments use CNY quote and settlement for this strategy. Product class is authority-significant; none may be represented as an ordinary A-share equity or as a generic SPOT alias.

## 4. Required retained source members

Each capture writes response bytes first and a no-clobber receipt last. Tushare-compatible calls use the ADR-0010 proxy; its exact 56-character credential remains environment/file-only and is sent only as `x-api-key`.

Minimum prospective daily capture:

1. `fund_daily` point response for each exact ETF and trading date;
2. `fund_adj` point response for each exact ETF and trading date, reconciliation-only;
3. SSE trading-calendar/session evidence for the date;
4. listing/trading-status evidence for each ETF;
5. effective ETF session/order-phase, order-admission, settlement, price-limit, fee, and tax source revisions;
6. execution-account evidence separating sellable position, tradable cash, withdrawable cash, and unsettled obligations;
7. fund distribution, split, merger, suspension, and termination announcements in scope;
8. request coordinates, response/acquisition times, source URL/API, pagination state, member hashes, and predecessor capture identity.

A successful HTTP/API response proves only the returned bytes. Zero rows do not prove `NO_SESSION`, `SUSPENDED`, `NO_TRADES`, delisting, or source outage.

## 5. Proposed normalized data

Names are frozen for this proposal but require Backtest-owner approval before production export.

### `EtfInstrumentRevision@1`

- stable Instrument ID and symbol;
- venue, CNY currencies, ETF product class;
- list/delist effective interval and availability;
- trading status and status availability;
- source key/hash, revision ID, optional predecessor;
- closure declaration and explicit qualification flags.

### `TushareEtfDailyRawBar@1`

- Instrument ID and trading date;
- exact raw `open/high/low/close/pre_close/change/pct_chg/vol/amount` lexemes;
- source-declared units retained without conversion until a separate ETF `fund_daily` numeric-mapping fixture is accepted;
- session start/end, finality, event time, available time;
- source row/member/snapshot/revision identities.

Only after ETF numeric mapping is frozen may normalization produce CNY/share prices, share quantities, and CNY amounts. Purpose projections are separate:

- raw next-session open → `bar_open@1` execution reference;
- raw close → valuation close;
- `adj_factor` → research reconciliation observation only.

Adjusted open/close must never become fills. A cash distribution or unit change must be represented by a retained lifecycle event and accounting authority, not inferred from `adj_factor`.

### `EtfTradingRuleRevision@1`

- product class and venue;
- effective and available interval;
- versioned session phases and eligible order-admission windows;
- minimum price tick, buy lot, sell residual rule, maximum quantity;
- price-limit rule and listing-day exception;
- T+0/T+1 sellability;
- supported order/time-in-force set;
- source revision and closure identity.

A separate execution-account settlement/availability Profile must bind sellable position, tradable cash, withdrawable cash, and unsettled obligations for each product. Market data alone cannot authorize those balances.

### `EtfFeeTaxRevision@1`

- product class, access route, side, basis, rate/minimum/rounding;
- exchange fee/waiver and tax disposition;
- effective and available interval;
- source revision and closure identity.

Broker commission and slippage are not data-source facts. They belong to a later versioned execution-account/simulation Profile.

### `EtfCorporateActionRevision@1`

- action ID, Instrument, action kind, lifecycle status;
- announcement, record, ex, payment/effective dates and availability;
- cash/share terms and currency;
- revision/predecessor/source identity;
- explicit terminal or still-open disposition.

## 6. MarketBundle requirements

The final Bundle must exact-bind:

- a three-instrument `InstrumentCatalog` body and hash;
- raw daily observations and purpose-specific projections;
- calendar/session and status coverage;
- ETF trading-rule and fee/tax revisions;
- corporate-action revisions and closure declarations;
- source, normalization, Builder, publication, and retention identities;
- limitations and `decision_grade_eligible=false` until separately qualified.

No missing date or instrument may be silently removed, forward-filled, or replaced with adjusted price.

## 7. Availability and revision policy

- The prospective collector runs only after the declared exchange session is final.
- `available_at` is the retained response availability, never the economic trading date.
- A target decision may consume an observation only after its accepted availability instant.
- Repeated captures are append-only. Changed bytes require a new revision with an explicit predecessor.
- Current Tushare responses do not prove provider-global terminality; that limitation remains visible.
- Historical exploratory CSV values cannot be backdated into the prospective authority.

## 8. Failure precedence

Only the bounded acquisition sentinel freezes failure order in this proposal:

| Priority | Condition | Sentinel outcome |
| ---: | --- | --- |
| 1 | request type/date/instrument/endpoint/callable/credential mismatch | `INPUT_MISMATCH` |
| 2 | output already exists | `OUTPUT_EXISTS` |
| 3 | transport exhausted or returned an invalid response tuple | `TRANSPORT_FAILURE` |
| 4 | credential echo, invalid JSON, duplicate key, or provider rejection | `SOURCE_INTEGRITY_FAILURE` |
| 5 | response fields, row shape, request coordinate, or terminal-page mismatch | `SOURCE_SCOPE_INCOMPLETE` |
| 6 | G12A snapshot freeze failure | `SNAPSHOT_FAILURE` |
| 7 | receipt-last durable publication failure | `PUBLICATION_FAILURE` |

Normalized catalog, availability, price, rule, fee, action, Bundle, and reopen failure codes and precedence remain provisional until their schemas and closure declarations are separately approved. All future failures remain atomic; no partial Bundle or qualification downgrade may be published.

## 9. First bounded sentinel

After the `2026-09-01` session is final, run one exact seven-request manifest in this order:

1. three `fund_daily` point requests in canonical Instrument order;
2. three `fund_adj` point requests in canonical Instrument order;
3. one SSE calendar request.

One capture selects exactly one approved endpoint from `https://fast.xiaodefa.cn` or `https://tt.xiaodefa.cn`; there is no failover. Credential-free canonical JSON is sent to `POST /` with `Accept-Encoding: gzip` and `x-api-key`. Calls are spaced by at least `0.5s`.

Each request permits at most three attempts and a 30-second transport timeout per attempt. The maximum is 21 transport calls; retry delays are at least `1s, 2s`. Every observed proxy response must declare `has_more=false` and the approved-proxy sentinel value `count=0`, plus exact request parameters/fields, response byte count/hash, attempt count, and response receipt time. The no-clobber receipt binds the semantic provider `tushare.pro`, transport key `xiaodefa.approved-tushare-proxy.v1`, exact endpoint, `auth_mode=x-api-key`, all seven coordinates/member hashes, the G12A snapshot/content-tree/provenance hashes, and is published last.

The sentinel stops before numeric mapping, normalization, rule/status classification, or Bundle publication. It proves acquisition plumbing only and keeps all provider/rule/lifecycle/decision-grade flags false.

## 10. Readiness gate

`ETF-DATA-01` remains `NOT_READY` until:

1. the first bounded sentinel is retained and reproducible;
2. normalized ETF price and product-lifecycle schemas are approved;
3. first-party rule/settlement/fee sources are captured and initially mapped; append-only future revision closure remains required through the requested interval;
4. the accepted lifecycle sentinel retains pre-open status and post-close announcement/distribution evidence, and normalized corporate-action closure exists for all three ETFs;
5. one pure Builder candidate proves deterministic validation, publication, reopen, and every failure precedence branch;
6. Backtest owner approves capability names, public exports, fixtures, and write set.

## 11. Forbidden paths

- Runtime or Strategy reads Tushare, SSE pages, CSV/Parquet, credentials, or wall clock.
- `InstrumentType.SPOT` or ordinary `InstrumentType.EQUITY` is used to bypass ETF product qualification.
- Adjusted prices create fills or replace missing raw opens.
- Current rules/status/listing values are projected backward.
- Funding, stamp duty, T+0/T+1, or action absence is fabricated as zero/default.
- A second simulator or private Backtest composition path is introduced.

## 12. Next safe implementation

Implement only the bounded acquisition sentinel in §9. Do not add Runtime/Profile/preparation code until the readiness gate is met.
