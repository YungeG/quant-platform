# QB-DATA-STAGE-01 — Quality + B-Band staged exact-cover data funnel v1

- **Status:** `CONTRACT_FROZEN / USER_APPROVED / PLAN_ONLY / SOURCE_AUTHORITY_BLOCKED`
- **Supersedes:** one-shot acquisition of every heavy capability for every broad-Universe Instrument
- **Preserves:** QB-DATA failure precedence, immutable evidence, complete disposition closure and no silent issuer removal

## 1. Outcome

Reduce acquisition work without introducing provider-coverage or survivorship bias.

Each stage consumes one immutable, exact-covered upstream manifest and produces exactly one complete downstream scope. A missing issuer or required field blocks that stage; it is never reclassified as an exclusion. Downstream source requests are scoped only by deterministic prior-stage results, never by which provider rows happen to exist.

No stage by itself authorizes Strategy, Backtest, Validation, Live or deployment use.

## 2. Stage sequence

```text
S0 broad lightweight authority
→ S1 structural eligibility
→ S2 minimal financial qualification
→ S3 governance + valuation qualification
→ S4 market + corporate-action entry/holding coverage
→ final composite QB-DATA authority
```

Provisional names remain subject to Backtest-owner approval.

## 3. S0 — broad lightweight authority

### Input scope

Every ordinary CNY A-share Instrument on `xshg` or `xshe` whose economic listing interval intersects either Fold's required S0 interval, including Instruments listed before the Fold and delisted during/after it.

### Required lightweight capabilities

- canonical Instrument catalog and aliases;
- listing/delisting revisions;
- board/product revisions;
- official CSRC industry revisions;
- status/risk-warning/suspension revisions;
- source/export closure and explicit empty scopes.

### Output

Accepted `broad_universe_authority_manifest@1` exact-binds the complete catalog/member set and all lightweight revision/coverage refs.

The first source-bounded plumbing output is instead provisionally named `s0_lightweight_source_capture_manifest@1`; every completeness, historical-as-of, survivorship, decision-grade and deployment qualification remains false. It must not impersonate accepted S0 authority.

S0 does not apply Main Board, non-financial or five-year filters.

## 4. S1 — structural eligibility

Pure deterministic Strategy qualification over S0:

```text
ordinary A-share
and active listing
and SSE/SZSE Main Board
and CSRC major category != J
and fifth listing anniversary <= decision date
```

Output `structural_eligibility_manifest@1` contains one disposition for every S0 member at every exact annual primary-screen instant declared by the Fold manifest. The date/instant set is immutable input and cannot be inferred from available rows:

- `STRUCTURALLY_ELIGIBLE`; or
- `STRUCTURALLY_OUT_OF_SCOPE` with exact first reason and input refs.

Mechanical closure:

```text
S0 members = eligible + out of scope
```

Only the exact eligible set may enter S2.

## 5. S2 — minimal financial qualification

### Request scope

The logical S2 scope is the union of all S1-eligible issuer/report periods required by annual decision dates and financial lookbacks. Each annual S2 qualification becomes effective only at its conservative financial availability boundary and remains the active financial roster until the next accepted annual S2 boundary.

When an approved provider endpoint cannot batch-filter the exact Instrument set, acquisition may retain declared full-market period or announcement-date-slice `SOURCE_SUPERSET` snapshots. A separate deterministic extraction manifest must then exact-bind the S1 expected set, select only matching Instrument/period rows, count every extra source row and fail on any missing expected member. Provider extras never enter S2 scope or define eligibility.

### Minimum authoritative fields

Only fields needed for frozen hard filters and ranking inputs:

- EBIT/operating profit and tax inputs;
- equity, interest-bearing debt, cash and EBITDA inputs;
- invested-capital opening/closing inputs;
- operating cash flow and capital expenditure;
- attributable profit for canonical annual PE;
- currency, unit, consolidation, statement identity, revision and availability.

No unrelated full-report field expansion is required.

### Output

`financial_qualification_manifest@1` assigns every S1-eligible issuer/date:

- `FINANCIAL_QUALIFIED_POINT`;
- `FINANCIAL_QUALIFIED_INTERVAL`;
- `FINANCIAL_HARD_FILTER_FAILED`; or
- `UNRESOLVED_DECISION_MATERIAL`.

Missing source/lineage/payload blocks S2 and emits no downstream scope. A complete invariant hard failure may stop later data acquisition for that issuer/date.

## 6. S3 — governance and valuation qualification

### Request scope

Every S2 financial-qualified point/interval issuer across every trading session in its active annual qualification interval. S3 must cover governance events continuously and canonical market-value/annual-PE observations for every status-eligible session before any B-Band signal is observed.

### Required capabilities

- audit opinion and reissue/correction lineage;
- competent severe-penalty/fraud acts or explicit no-event closure;
- point-in-time controlling-shareholder identity and pledge observations;
- material acquisition/governance facts required by frozen predicates;
- canonical market-value observations and annual-PE history for the five-year percentile;
- source, revision, availability and terminal/empty-scope authority.

### Output

`governance_valuation_qualification_manifest@1` assigns one complete disposition per S2-qualified issuer/date and exact-binds all retained intervals/advisories.

Only full quality/governance/valuation passes may enter S4.

## 7. S4 — market and corporate-action coverage

### Request scope

A deterministic pre-run union derived before ranking/execution:

- every Instrument that is S3-qualified on any entry-decision session;
- for each such Instrument, signal/action coverage from required warmup through Fold end or declared terminal continuation horizon;
- exact accounting lifecycle coverage sufficient for the Instrument to have been selected on any eligible session and then held through that horizon.

The experiment starts from the frozen empty-cash account state, so no unknown pre-Fold holding is injected. S4 never uses realized post-run holdings to authorize pre-run data.

### Required capabilities

- raw OHLCV/amount and status-aware session coverage;
- point-in-time adjusted signal observations derived from visible actions;
- corporate-action inventory/revision/lifecycle terms;
- raw execution-reference open data;
- explicit unsupported-action classification;
- Calendar/rule/action coverage reports.

S4 does not fetch market/action history for issuers that exact-failed before any S3-qualified session. An Instrument that qualified once remains S4-covered through the frozen continuation horizon even if later qualification changes.

## 8. Final composite authority

A final `CnAShareQualityResearchBundleDeclarationV1` does not duplicate source-member or closure authority identities. It exact-binds only:

- ordered S0–S4 manifest refs/hashes;
- final catalog hash and coverage interval;
- required final capability tuple;
- source limitations and result-grade ceilings.

Every source member, closure ref, stage input/output set and closure equation is derived from and verified against the stage manifests. Any independently repeated identity must equal the derived value exactly or construction fails.

Successful final composition proves that every broad member followed one legal path through the funnel. It does not allow a downstream stage to invent or omit an upstream member.

## 9. Stage failure rules

1. malformed/foreign upstream manifest blocks before source I/O;
2. normalized/extracted stage scope must equal the exact prior-stage output set;
3. in `EXACT_SCOPE` acquisition, provider rows outside scope fail; in explicitly approved `SOURCE_SUPERSET` acquisition, extras are retained and audited but excluded only by the deterministic extraction manifest; missing expected members always fail;
4. zero rows never imply threshold failure or event absence;
5. stage publication is atomic and immutable;
6. no downstream stage starts after an upstream block;
7. no blocked stage emits an empty eligible set, target or execution request.

Existing QB-DATA failure codes retain precedence. Exact stage-local reasons are:

```text
STAGE_INPUT_SCOPE_MISMATCH
OUT_OF_SCOPE_SOURCE_ROW
EXPECTED_MEMBER_MISSING
```

They nest under `BUNDLE_EXACT_COVER_MISMATCH`; malformed/foreign manifest types retain earlier `INPUT_TYPE_MISMATCH`/identity failures. No competing top-level error hierarchy is created.

## 10. Safe acquisition optimization

Permitted:

- request only lightweight S0 fields initially;
- request only frozen minimal financial fields; prefer exact S1 scope, or use explicitly declared full-market period/announcement-date-slice `SOURCE_SUPERSET` pages only when the provider cannot batch-filter the stage set;
- request governance/valuation only for exact S2 passes;
- request OHLCV/actions only for the deterministic pre-run S4 union of Instruments with any S3-qualified session, through the frozen continuation horizon;
- batch and page within each exact scope;
- use source-bounded captures for development while keeping all qualification flags false.

Forbidden:

- filtering because a provider has no row;
- using current data to define historical S0/S1 membership;
- screening with market cap, share price or convenience fields not in the frozen Strategy;
- removing an issuer because official documents are difficult to acquire;
- using a preliminary provider ratio as a final hard-filter fact;
- claiming final full-market support from any partial stage.

## 11. First implementation slice

The first useful slice is S0 source-bounded acquisition only:

- all Tushare current `L`, `D`, `P` ordinary-stock identity rows returned for SSE/SZSE;
- relevant lightweight company/industry fields;
- exact raw bytes, request/envelope/cardinality and immutable snapshot;
- explicit nonclaims for historical-as-of state, revisions, completeness and survivorship safety.

This slice estimates and tests the funnel plumbing. It cannot yet produce accepted S0 authority because public Tushare metadata lacks historical revision and terminal closure.

## 12. Readiness decision

The staged funnel is approved and reduces unnecessary heavy acquisition. Formal Experiment execution remains blocked until every consumed stage has competent source closure and accepted public Backtest schemas/operations.
