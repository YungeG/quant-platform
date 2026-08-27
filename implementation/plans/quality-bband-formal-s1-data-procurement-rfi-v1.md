# Quality-BBAND formal S1 data procurement RFI v1

- **Status:** `RFI_READY / USER_PURCHASE_APPROVAL_REQUIRED / NO_EXTERNAL_SEND`
- **Strategy:** `cn-a-share.quality-bband-breakout.manual4.v1`
- **Authority:** [`quality-bband-formal-s1-authority-feasibility-v1.md`](../../research/quality-bband-formal-s1-authority-feasibility-v1.md)
- **Decision preserved:** `PUBLICLY_DATA_INFEASIBLE / FORMAL_S1_FALSE / STRATEGY_AUTHORITY_FALSE`

## 1. Purpose

Request a contractually complete, immutable and auditable historical source package sufficient to build formal point-in-time S1 structural eligibility without current-state projection, provider-row survivorship or search-absence inference.

This RFI does not authorize a purchase, credentialed probe, redistribution, Strategy run, Backtest, Validation or deployment. Sending the RFI and accepting commercial terms require explicit owner approval.

## 2. Candidate recipients

The same requirements may be sent separately or as a coordinated request to:

1. SSE Info / the official SSE historical-data service;
2. SZSE or its officially authorized market-data service;
3. CSRC and CSDC, or an officially authorized provider if identified, for issuer-level historical CSRC industry assignments and identity continuity;
4. a licensed vendor only when it can contractually identify the official upstream source, revision lineage and terminal completeness for every delivered field.

No secondary web scraper, current-only security master or undocumented vendor reconstruction qualifies.

## 3. Requested scope options

### Option A — minimum nine-screen formal S1

Exact source-bounded screen dates to be replaced by accepted Calendar/Session instants:

```text
2017-05-02
2018-05-02
2019-05-06
2020-05-06
2021-05-06
2022-05-05
2023-05-04
2024-05-06
2025-05-06
```

Deliver the complete reference state at every screen plus all predecessor listing, restructure, code/name, product/board and industry events required to establish canonical identity and fifth-anniversary age.

### Option B — complete Fold A/B S0 authority

Option B requests the source scope required for:

```text
Fold A: [2010-01-04, 2024-01-02)
label: cn-a-share-quality-bband-fold-a-v1

Fold B: [2013-01-04, 2026-04-01)
label: cn-a-share-quality-bband-fold-b-v1
```

Each Fold must bind its separately accepted manifest identity/hash and closure; neither Fold may substitute for the other. The union delivery interval is `[2010-01-04, 2026-04-01)`. Option B must include every applicable daily reference file or complete event lineage needed to reconstruct every consumed instant. Option A must not be represented as complete Fold A/B authority.

## 4. Required deliverables

### 4.1 SSE/SZSE security master and product history

Provide every listed, suspended, delisting-period and terminated product in scope, including:

- venue-native security ID and every historical code/name alias;
- stable issuer identity and sufficient lineage to derive a canonical `InstrumentId` independent of code/name changes;
- ordinary A share, B share, CDR and other product type/subtype;
- quote and settlement currency;
- Main Board, historical SME Board, ChiNext, STAR and other board/market-layer state;
- first listing date, last trading date, delisting/effective date and listing interval;
- normal, suspension, resumption, risk-warning/ST and delisting-terminal status history;
- source-file applicable date and publication/availability evidence.

Required historical file families include the official equivalents of SSE product-basic-information files such as `cpxx0201MMDD.txt` and SZSE `securities.xml`, or a contractually equivalent complete export.

### 4.2 Identity and event lineage

For code/name changes, mergers, absorptions, re-listings, board changes, replacement securities and restructurings, provide:

- predecessor and successor source identities;
- economic `effective_at` interval or instant;
- exact customer/public `available_at`; where only date-level evidence exists, immutable official publication evidence sufficient for the accepted Calendar/Session rule to derive one exact conservative `available_at`;
- immutable source file/member hashes;
- provider-native revision ID when available, otherwise null;
- correction/supersedes relation or enough immutable evidence to derive one canonical revision chain;
- explicit treatment of code reuse and a new security issued after restructuring.

### 4.3 Official CSRC industry assignments

For every in-scope issuer/security and screen, provide the then-visible assignment under the then-operative regime/standard:

- issuer and security identity;
- classification category code, including major category `J`;
- classification reference/effective interval;
- exact customer/public `available_at`; where only date-level evidence exists, immutable official publication evidence sufficient for the accepted Calendar/Session rule to derive one exact conservative `available_at`;
- regime/guidance identity and statistical-standard identity;
- immutable source hashes;
- provider-native revision ID when available, otherwise null;
- correction/supersedes relation and explicit unassigned/empty scope.

The response must distinguish the then-operative 2012 listed-company issuer-classification guidance from the `JR/T 0020—2004` to `JR/T 0020—2024` statistical-standard lineage. A taxonomy without issuer assignments is insufficient.

### 4.4 Calendar and session authority

Provide or identify accepted official authority for:

- each decision session and exact decision instant;
- mapping date-only publication evidence to conservative `available_at`;
- holidays, special closures and corrections affecting the annual screen boundary.

## 5. Export and closure requirements

Every delivery must include:

- contract/product/version identity;
- requested venue, product and interval scope;
- schema/version and field dictionary;
- generation timestamp;
- total file, page and record counts;
- ordered file/page manifest and SHA-256 checksums;
- stable pagination/export continuation rules;
- explicit empty scopes;
- correction, reissue and retry rules;
- provider declaration that the delivered export is complete for the contracted scope;
- notification and replacement procedure for later corrections.

A zero-row result, search absence or undocumented page ending is not terminal closure.

## 6. License and operational requirements

The proposed license must explicitly permit:

- internal quantitative research and backtesting;
- immutable raw-byte retention;
- cryptographic hashing and manifests;
- normalized/derived internal facts;
- audit, replay and independent review;
- retention after subscription expiry for reproducibility, audit and replay;
- secure credential use through environment-only secrets;
- exclusion of credentials from repositories, logs and artifacts.

The supplier must state restrictions on redistribution, derived-output sharing, storage location, retention period and reviewer access.

## 7. Supplier response matrix

Require one explicit `YES | NO | PARTIAL` response and supporting document for every row:

| Requirement | Response | Product/file/API | Earliest date | Latest date | Revision/closure guarantee | License note |
|---|---|---|---|---|---|---|
| Canonical `InstrumentId`, issuer identity, aliases and code reuse |  |  |  |  |  |  |
| Exact or conservatively derived `available_at` |  |  |  |  |  |  |
| One-root linear revision/supersession lineage |  |  |  |  |  |  |
| Calendar/Session authority and date-only mapping |  |  |  |  |  |  |
| Post-expiry immutable retention, audit and replay |  |  |  |  |  |  |
| SSE complete historical security master |  |  |  |  |  |  |
| SZSE complete historical security master |  |  |  |  |  |  |
| Listed and terminated products retained |  |  |  |  |  |  |
| Historical board/product state |  |  |  |  |  |  |
| Historical SME Board state |  |  |  |  |  |  |
| Code/name/restructure lineage |  |  |  |  |  |  |
| Exact listing/delisting intervals |  |  |  |  |  |  |
| Suspension/risk-warning/ST history |  |  |  |  |  |  |
| Issuer-level CSRC industry assignments |  |  |  |  |  |  |
| Major category `J` available |  |  |  |  |  |  |
| Publication/availability evidence |  |  |  |  |  |  |
| Complete export/page manifest |  |  |  |  |  |  |
| Explicit empty-scope authority |  |  |  |  |  |  |
| Correction/reissue notifications |  |  |  |  |  |  |
| Immutable retention and hashing permitted |  |  |  |  |  |  |

## 8. Questions requiring written answers

1. Is the historical product a direct official-source archive, an official redistribution, or a vendor reconstruction?
2. Does the delivery include delisted, suspended and delisting-period products, not only active/current securities?
3. Is every date/file complete for the contracted scope, and how is completeness declared?
4. Are corrected or withdrawn historical files retained and linked to replacements?
5. How are code reuse, mergers, absorptions and replacement securities identified?
6. Does board history preserve the pre-2021 SME Board separately?
7. Are CSRC industry assignments issuer-level observations or vendor classifications?
8. What does a missing assignment mean, and can an explicit unassigned scope be certified?
9. What timestamp establishes public/customer availability, and what is available when only a date exists?
10. Can raw files and hashes be retained for audit after contract expiry?
11. What is the total price for Option A and Option B, including historical backfill, updates and retention rights?
12. What sample files can be supplied before purchase without weakening the final completeness guarantee?

## 9. Acceptance gates after a commercial response

A proposed source or coordinated source package is accepted for implementation planning only when:

1. all required fields have an identified official upstream owner;
2. the interval and terminal-set guarantee cover the selected option;
3. revision/correction and empty-scope semantics are explicit;
4. licensing permits immutable retention, hashing, audit and internal derived facts;
5. one bounded sample can be acquired without credentials entering artifacts;
6. the sample reconstructs source manifests and identity/availability semantics exactly;
7. every logical revision lineage has one root and one linear terminal chain; forks, cycles, missing parents, context changes, non-increasing availability and conflicting identity reject the affected scope;
8. `NO` or `PARTIAL` on a mandatory requirement rejects acceptance unless another identified contract exact-covers that gap and package-level closure is demonstrated;
9. an implementation-readiness review marks the source contract `READY`.

Purchase price, contract acceptance and credential activation remain owner decisions.

## 10. Automatic rejection conditions

Reject any proposal that relies on:

- current-only security master or industry state;
- bars or provider row presence as listing proof;
- code ranges as the sole board/product authority;
- current names or ST strings projected backward;
- undocumented vendor industry mappings;
- missing rows as non-financial or out-of-scope evidence;
- no revision lineage or no complete export declaration;
- a license that forbids immutable internal retention or audit replay.

## 11. Frozen downstream S1 rule boundary

After accepted procurement, S1 must still publish one disposition for every broad member and screen:

```text
ordinary CNY A share
and active listing interval contains decision instant
and frozen eligible-board rule passes
and fifth calendar anniversary <= decision date
and visible CSRC major category != J
```

The pre-2021 SME-Board treatment must be decided explicitly in the S1 implementation packet. No current post-merger label may decide it retroactively.

`STRUCTURALLY_OUT_OF_SCOPE` records the exact first reason and controlling input refs. Fifth anniversary means calendar anniversary, not `365 * 5` days or sessions; February 29 maps to February 28 in a non-leap fifth-anniversary year. Suspension does not terminate broad-Universe membership.

Mechanical closure remains:

```text
all broad members = structurally eligible + structurally out of scope
```

Any identity, listing, board, industry, availability, revision or terminal gap blocks the whole affected screen. It never becomes a silent issuer deletion, empty Universe, Strategy target or execution request.
