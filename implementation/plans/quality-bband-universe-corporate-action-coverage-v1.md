# QB-UNIV-CA-01 — Quality + B-Band immutable Universe and corporate-action coverage v1

- **Status:** `CONTRACT_FROZEN / PLAN_ONLY / GENERAL_SOURCE_CLOSURE_MISSING`
- **Owner:** Backtest Market Bundle Builder coverage and source qualification
- **Consumer:** QB-DATA, QB-ELIG-01, future portfolio preparation

## 1. Outcome

Freeze the minimum immutable catalog, listing, board, industry, status, strategy-Universe and corporate-action evidence required for survivorship-safe research.

Current Tushare `stock_basic`, `bak_basic`, `namechange`, `dividend` and `adj_factor` captures remain source-bounded observations. They do not establish full historical listing, industry, status, action-revision or terminal-set authority.

## 2. Broad independent Universe identity

Provisional Universe key:

```text
cn-a-share.domestic-ordinary-listed.v1
```

At one decision instant, the broad Universe contains every complete-source Instrument whose visible revisions prove:

1. stable Instrument identity is an ordinary CNY A-share equity on `xshg` or `xshe`;
2. the listing interval contains the decision instant.

It is deliberately not prefiltered by Main Board, industry, five-year age, financial/governance coverage or signal data. QB-ELIG-01 applies board, CSRC non-financial and listing-age rules downstream and records every broad member's structural disposition.

Five-year age is a precommitted Strategy convention, not a source/Calendar fact: use calendar anniversary, not `365 * 5` days or a session count; February 29 maps to February 28 in a non-leap fifth-anniversary year.

ST/risk-warning and suspension state do not silently remove a broad member. They remain exact market-rule/tradability facts. Delisting ends active broad membership.

## 3. Canonical catalog body

A canonical immutable `InstrumentCatalog` artifact must equal the competent source's complete historical listed/delisted ordinary-A-share Instrument set for the declared interval, and include for every member:

- stable `InstrumentId` independent of code/name changes;
- venue, instrument type, quote/settlement currency and ordinary-A-share product identity;
- source/provider identifiers as aliases, never canonical identity;
- exact catalog schema/version and derived hash;
- source snapshot/provenance refs;
- retained historical Instruments, including delisted names.

G12C's `instrument_catalog_hash` must exact-match the full retained body. A current-only catalog is insufficient.

## 4. Required normalized capabilities

Provisional planning vocabulary, pending Backtest-owner G12B approval:

```text
instrument_listing_revision@1
instrument_board_revision@1
industry_membership_revision@1
trade_status_revision@1
universe_membership_revision@1
corporate_action_lifecycle_revision@1
```

### Common revision semantics

Every logical revision record retains:

- stable logical key;
- stable Instrument and context identity;
- economic effective interval or lifecycle instant;
- exact `available_at`;
- immutable `revision_id` and optional `supersedes_revision_id`;
- source member/content/provenance hashes;
- provider revision identity when available, otherwise null;
- derived canonical revision hash.

A legal visible lineage is one root and one linear terminal chain. Forks, cycles, missing parents, context changes, non-increasing availability and conflicting identity fail closed.

### Listing and board

Listing revisions express listed/delisted economic intervals separately from evidence availability. Board revisions express Main Board/STAR/ChiNext/other product intervals for downstream structural qualification. Code/name change does not create a new Instrument.

### Industry

Industry revisions use official CSRC listed-company industry classifications and retain classification-standard identity, major category code, reference/effective interval, publication evidence, availability and revision source.

When an official publication declares an explicit classification reference/effective date, use that economic date and a conservative first-later-session `available_at`; availability prevents backdating knowledge. If no economic reference date is explicit, set economic effect no earlier than `available_at`. A newly visible quarterly snapshot closes/revises prior classification only through a legal lineage; it does not rewrite prior ObservationViews.

`industry_membership_revision@1` and `IndustryMembershipCoverageReportV1` remain provisional names. No current `stock_basic.industry`, Shenwan current membership or analyst label may be projected backward.

### Trade status

Status revisions retain at least normal matching, suspension/resumption, risk-warning/ST class and delisting/terminal state needed by historical market rules. A suspension keeps Universe membership but blocks matching according to the resolved rule authority.

### Derived broad membership

`universe_membership_revision@1` is deterministically derived only from accepted catalog, ordinary-A-share product and listing facts. Board, industry and age remain downstream structural filters. The derivation binds its algorithm identity and all controlling input revision hashes; `available_at` is the maximum availability of every controlling input and the derivation-authority publication. Economic membership never becomes visible earlier than that maximum. Membership is not inferred from bars or provider coverage.

## 5. Closure declarations and reports

Successful QB-DATA publication exact-binds:

- `InstrumentCatalogCoverageReport`;
- `UniverseCoverageReport`;
- provisional `IndustryMembershipCoverageReportV1`;
- `TradeStatusCoverageReport`;
- `CorporateActionCoverageReport`.

Each report binds:

- Bundle ref and coverage interval;
- catalog body/hash;
- source and closure declaration refs;
- exact relevant and terminal revision hashes;
- canonical Instrument/action sets;
- explicit empty scopes;
- duplicate/omission counts;
- provider/source qualification and limitations;
- deterministic report hash.

A zero-row provider response is not an empty-scope declaration. Explicit empty scope requires competent closure authority over the exact Instrument/context/interval.

Universe closure proves mechanical exact-cover of the independently defined membership set; it does not let Builder choose stocks. Industry/status closure cannot be absorbed into bar presence.

## 6. Corporate-action lifecycle inventory

Every action receives a stable `corporate_action_id` and one complete revision/lifecycle history. The normalized payload retains:

- Instrument and action kind;
- announcement, record/entitlement, ex/effective, payment and share-listing instants when applicable;
- cash/share/ratio/base terms with exact units;
- cancellation, completion and correction state;
- revision/supersession/source identities;
- supported-semantics key or explicit unsupported classification.

The inventory must enumerate all action kinds returned by the competent source, not only actions already supported by the engine.

V1 accounting/adjustment support must at minimum cover the architecture-required set:

```text
cash_distribution
share_distribution_or_bonus
split_or_consolidation
ex_or_effective_price_adjustment
```

Rights offerings, merger share exchanges, cash-outs, delisting dispositions or any other action affecting price continuity, entitlement, cash or position quantity must be retained and classified. They may not be ignored. An unsupported action can exist in a mechanically complete Bundle, but consumption of an affected adjusted-series or held-position path returns public PREP `CAPABILITY_MISMATCH`; it is not misreported as `CORPORATE_ACTION_CLOSURE_MISMATCH`.

## 7. Price-purpose separation

- raw execution/fill/accounting prices are never rewritten;
- point-in-time adjusted signal series are derived only from actions visible and effective by the queried SimulationInstant;
- provider full-history adjusted prices or `adj_factor` may be bounded corroboration, not canonical lifecycle authority;
- valuation market value uses its retained numerator observation and does not inherit signal-price adjustment silently;
- corporate-action cash/share effects enter accounting only through the accepted G08F/G08G lifecycle and Journal path.

Future action knowledge cannot alter a prior BOLL, trend, volume or valuation observation.

## 8. Coverage ranges

Each Fold manifest must declare separately:

- economic evaluation interval;
- bar/signal warmup interval;
- financial lookback interval;
- Universe/listing/industry/status coverage interval;
- corporate-action observation and lifecycle interval;
- held-position accounting interval.

Coverage must include every instant actually queried or consumed. Evaluation start is not automatically sufficient for the 120-session signal window or five-year financial history.

An action announced before coverage but effective/paid/listed inside coverage is in scope. An action announced inside coverage whose economic triggers are all after coverage may remain an announcement-only in-Fold observation; Fold completion does not require economic completion beyond the Fold. Later lifecycle closure evidence may be retained retrospectively with its own `closure_evidence_available_at`, but ObservationView hides every term until that term's own availability and never leaks future closure backward.

## 9. Failure mapping

| Condition | Existing QB-DATA outcome |
| --- | --- |
| Catalog body/hash/Instrument mismatch | `CATALOG_IDENTITY_MISMATCH` |
| Listing, board, industry or derived Universe fork/gap/overlap/terminal mismatch | `UNIVERSE_CLOSURE_MISMATCH` |
| Status/Calendar/price-purpose coverage gap | `MARKET_COVERAGE_MISMATCH` |
| Corporate-action inventory, revision, lifecycle or explicit-empty mismatch | `CORPORATE_ACTION_CLOSURE_MISMATCH` |
| Report capability/member exact-cover mismatch | `BUNDLE_EXACT_COVER_MISMATCH` |
| Retention/reopen/tamper failure | `PUBLICATION_INTEGRITY_FAILURE` |

All are atomic. No affected Instrument is silently removed; no empty Universe or no-action result is fabricated.

## 10. Source qualification needed

General readiness requires a competent source or licensed feed that supplies:

- a source-declared complete historical listed and delisted ordinary-A-share Instrument inventory for each declared interval;
- board/product and CSRC industry history;
- status/risk-warning/suspension history;
- complete action inventory with corrections and lifecycle terms;
- stable pagination/export closure for each interval;
- immutable snapshot/publication identity or retained bytes plus source-declared terminal completeness;
- correction/revision/supersession semantics;
- explicit empty-scope authority.

The documented public Tushare interfaces do not currently provide this closure. Current exchange web lists and current provider metadata can corroborate known facts but cannot prove the full historical terminal set.

## 11. Sentinel and acceptance order

1. freeze G12B normalized schemas and declaration bodies;
2. obtain one finite licensed/competent full-market source slice;
3. publish exact catalog/listing/board/industry/status/action revisions;
4. build deterministic closure reports and mutation tests;
5. verify G11C point-in-time membership parity and G08F/G08G action semantics through test-only mappings;
6. prove unsupported-action failure on a consumed signal/holding path;
7. independently review hashes, closure, survivorship labels and predecessor bytes;
8. only then authorize the public multi-stock preparation seam.

## 12. Readiness decision

The contract is frozen; data authority is not. Full-market strategy execution remains blocked until a real immutable source closes historical Universe, industry, status and corporate-action inventories for both Fold manifests.
