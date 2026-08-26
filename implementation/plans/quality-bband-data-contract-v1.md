# QB-DATA-01 — Quality + B-Band A-share data contract v1

- **Status:** `STAGED_FUNNEL_FROZEN / NOT_READY / SOURCE_AUTHORITY_BLOCKED`
- **Owner:** Backtest G12 acquisition + Market Bundle Builder
- **Consumer:** future A-share portfolio preparation operation
- **Strategy scope:** `cn-a-share.quality-bband-breakout.manual4.v1`
- **Authority audit:** [`research/quality-bband-data-authority-audit.md`](../../research/quality-bband-data-authority-audit.md)
- **Source matrix:** [`research/quality-bband-financial-governance-source-matrix.md`](../../research/quality-bband-financial-governance-source-matrix.md)
- **First acquisition sentinel:** [`quality-bband-financial-source-sentinel-v1.md`](quality-bband-financial-source-sentinel-v1.md)
- **Availability policy:** [`quality-bband-financial-availability-policy-v1.md`](quality-bband-financial-availability-policy-v1.md)
- **Revision lineage:** [`quality-bband-financial-revision-lineage-v1.md`](quality-bband-financial-revision-lineage-v1.md)
- **Presentation selection:** [`quality-bband-financial-presentation-selection-v1.md`](quality-bband-financial-presentation-selection-v1.md)
- **Industrial field mapping:** [`quality-bband-industrial-financial-field-mapping-v1.md`](quality-bband-industrial-financial-field-mapping-v1.md)
- **Formula-input acquisition successor:** [`quality-bband-financial-source-sentinel-v2.md`](quality-bband-financial-source-sentinel-v2.md)
- **Staged funnel:** [`quality-bband-staged-data-funnel-v1.md`](quality-bband-staged-data-funnel-v1.md)

## 1. Outcome

Publish one immutable final A-share research authority per Fold by composing exact-covered staged manifests: broad lightweight authority, structural eligibility, minimal financial qualification, governance/valuation qualification, then market/corporate-action coverage. Provider acquisition, feature calculation and strategy policy remain outside Backtest Runtime.

Each stage is deep and atomic: callers provide one exact upstream manifest plus scoped source snapshots; the Builder owns normalization, identity, stage exact-cover, publication bytes and structured failure. The final declaration binds stage refs rather than requiring every heavy capability for every broad-Universe Instrument.

## 2. Authority

| ID | Source | Requirement |
| --- | --- | --- |
| A1 | `backtest/docs/implementation/plans/g12/README.md` | G12A-L own acquisition, normalization, publication and provider qualification; Runtime may not acquire provider data. |
| A2 | `backtest/docs/research/g12k-universe-corporate-action-coverage.md` | General Universe and corporate-action coverage remain blocked until catalog body, normalized revisions and closure declarations exist. |
| A3 | `backtest/docs/research/g12l-tushare-listing-corporate-action-revision-authority-v1.md` | Tushare public interfaces do not provide immutable revision/correction closure; source-bounded limitations must remain explicit. |
| A4 | `backtest/docs/architecture/backtest-system-design.md` | Event time and availability time are distinct; execution prices cannot use ex-post adjusted observations. |
| A5 | `research/investment-book-strategy-ideas.md` | Quality filtering requires five-year capital-return, cash-flow, leverage, audit/governance and valuation history; technical entry requires daily OHLCV and tradability evidence. |
| A6 | Quant Strategy Research authority rules | Execution must consume immutable retained MarketBundles through public seams; no network, mutable provider read or second simulator is permitted. |
| A7 | `research/quality-bband-financial-governance-source-matrix.md` | Tushare raw statements/audit/pledge and official documents are `SOURCE_BOUNDED_ONLY`; full financial/governance authority is `MISSING` because availability, revision and terminal-set closure are absent. |
| A8 | `implementation/plans/quality-bband-financial-source-sentinel-v1.md` | The smallest honest next slice is one fixed issuer/period raw SourceSnapshot; it terminates before Builder normalization or Strategy execution. |
| A9 | `implementation/plans/quality-bband-financial-availability-policy-v1.md` | Provider-only dates cannot create `available_at`; date-only official evidence maps conservatively to the first declared next Session. |
| A10 | `implementation/plans/quality-bband-financial-revision-lineage-v1.md` | Economic fact, presentation basis and source-bound revision identity are separate; no supersession is inferred from `update_flag`, row order or date. |
| A11 | `implementation/plans/quality-bband-financial-presentation-selection-v1.md` | Feature inputs use the latest visible eligible presentation; pre-adjustment is audit-only and incoherent statement trios fail. |
| A12 | `implementation/plans/quality-bband-industrial-financial-field-mapping-v1.md` | Canonical formulas require expanded raw interest/equity/debt/depreciation/amortization fields plus official unit authority; vendor EBIT/EBITDA/FCF are advisory only. |
| A13 | `implementation/plans/quality-bband-financial-source-sentinel-v2.md` | Formula-ready acquisition requires an additive successor with expanded fields and official publication confirmation; PR #1 remains immutable. |

## 3. External seam

Proposed final-composition Builder interface; names remain provisional until Backtest owner approval:

```python
build_cn_a_share_quality_research_bundle_v1(
    declaration: CnAShareQualityResearchBundleDeclarationV1,
    stage_manifests: tuple[ArtifactRef, ...],
    instrument_catalog: InstrumentCatalog,
) -> CnAShareQualityResearchBundleOutcomeV1
```

Stage-specific builders consume one exact upstream manifest and one or more scoped SourceSnapshots. Their names and schemas remain Backtest-owned provisional vocabulary.

Properties:

- pure and deterministic;
- imports no Backtest Runtime or Trading Kernel implementation;
- performs no network, filesystem discovery, clock read or mutable provider query;
- returns exactly one Result or one structured Failure;
- publishes through existing G12C/D repository operations after successful construction;
- feature formulas remain Strategy/Build authority, not Builder authority.

## 4. Declaration

`CnAShareQualityResearchBundleDeclarationV1` freezes:

1. `bundle_key`;
2. `coverage_start` and `coverage_end_exclusive`;
3. exact `instrument_catalog_hash`;
4. exact ordered S0–S4 stage-manifest refs/hashes;
5. required final capability tuple;
6. source limitations/result-grade ceiling;
7. schema version `1`.

Source-member, closure-declaration and stage-scope identities are derived exclusively from the stage manifests. If any caller-supplied compatibility projection repeats them, exact equality is mandatory.

The declaration contains no provider token, local path, current timestamp, Strategy parameters, selected stocks, Backtest request identity or result-grade claim.

## 5. Required Bundle capabilities

Reuse existing accepted capabilities where applicable:

- `tushare_cn_a_share.daily-publications@1`;
- `bar_open@1` only in the later execution Bundle projection;
- `universe@1` after G12K general coverage is accepted;
- `corporate_actions@1` after lifecycle closure is accepted.

New provisional source capabilities; exact public names remain subject to Backtest-owner approval:

| Capability | Purpose | Minimum payload authority |
| --- | --- | --- |
| `industry_membership_revision@1` | Point-in-time official industry classification used by structural eligibility | Instrument, classification-standard identity, category code, effective/available interval, revision/supersedes identity and source hash. |
| `financial_statement_observations@1` | Raw point-in-time annual/quarterly statements | Instrument, statement kind, accounting period, announcement/available instant, revision/supersedes identity, source hash, required line items. |
| `audit_opinion_observations@1` | Audit and report-quality facts | Instrument, report identity, opinion kind, announcement/available instant, revision and source. |
| `issuer_governance_observations@1` | Penalty/fraud/pledge/major capital-allocation facts | Competent issuer/source identity, Instrument, fact kind, effective and available instant, revision and source. |
| `valuation_observations@1` | Point-in-time PE/EV-style observations | Instrument, valuation kind, exact numerator/denominator authority, event/available instant, revision and source. |

The Bundle does **not** publish `ROIC`, `ROCE`, free-cash-flow quality, permanent-loss score, BOLL, ATR, breakout score or selected Universe. Those are deterministic Strategy/Build outputs derived through G11 point-in-time observations.

## 6. Minimum normalized financial fields

The statement payload must retain enough raw authority to reconstruct, without provider lookup:

- operating profit / EBIT;
- tax or effective tax inputs needed by the frozen ROIC formula;
- equity and interest-bearing debt;
- cash and cash equivalents;
- fixed and working-capital inputs;
- operating cash flow;
- capital expenditure;
- revenue and net profit;
- statement currency and unit;
- consolidation scope;
- audit/report identity.

Exact provider-field mappings and the ROIC/ROCE calculation formula must be frozen in a separate Strategy Feature Manifest before execution. Builder must not guess missing line items or substitute provider-computed ratios for absent raw facts.

## 7. Fold declarations

| Fold | Coverage | Expected Bundle label | Current ref |
| --- | --- | --- | --- |
| A | `[2010-01-04, 2024-01-02)` | `cn-a-share-quality-bband-fold-a-v1` | `UNAVAILABLE` |
| B | `[2013-01-04, 2026-04-01)` | `cn-a-share-quality-bband-fold-b-v1` | `UNAVAILABLE` |

Each label becomes usable only after G12D publication returns an exact `MarketBundleRef` and retained manifest/content hashes. Fold A and Fold B are independent; neither may substitute for the other.

## 8. Coverage reports

Final composite publication requires the reports below. Each upstream stage requires only the reports/capabilities declared for its exact prior-stage output scope:

- `InstrumentCatalogCoverageReport`;
- `UniverseCoverageReport`;
- `IndustryMembershipCoverageReportV1`;
- `TradeStatusCoverageReport`;
- `RuleCoverageReport`;
- `PriceStreamCoverageReport`;
- `CorporateActionCoverageReport`;
- `FinancialStatementCoverageReportV1`;
- `GovernanceObservationCoverageReportV1`;
- `ValuationObservationCoverageReportV1`.

New financial/governance reports must prove mechanical exact-cover only. Provider finality, global completeness and future corrections remain separate source-qualification claims.

## 9. Failure precedence

| Priority | Condition | Outcome code |
| ---: | --- | --- |
| 1 | declaration, snapshot or catalog type/schema mismatch | `INPUT_TYPE_MISMATCH` |
| 2 | catalog body/hash or Instrument identity mismatch | `CATALOG_IDENTITY_MISMATCH` |
| 3 | duplicate/conflicting source member or source hash | `SOURCE_MEMBER_CONFLICT` |
| 4 | listing/Universe revision fork, gap, overlap or missing terminal | `UNIVERSE_CLOSURE_MISMATCH` |
| 5 | status, calendar, rule or price coverage gap | `MARKET_COVERAGE_MISMATCH` |
| 6 | financial revision fork/missing parent/context mismatch | `FINANCIAL_REVISION_MISMATCH` |
| 7 | required statement line item/unit/consolidation scope missing | `FINANCIAL_PAYLOAD_INCOMPLETE` |
| 8 | audit/governance availability or competent-source mismatch | `GOVERNANCE_AUTHORITY_MISMATCH` |
| 9 | corporate-action lifecycle gap for in-scope Instrument | `CORPORATE_ACTION_CLOSURE_MISMATCH` |
| 10 | valuation revision/availability/identity mismatch | `VALUATION_AUTHORITY_MISMATCH` |
| 11 | capability/stream/manifest exact-cover mismatch | `BUNDLE_EXACT_COVER_MISMATCH` |
| 12 | publication, retention or reopen verification failure | `PUBLICATION_INTEGRITY_FAILURE` |

All failures are atomic. No partial Bundle, fabricated empty stream, silent stock removal or qualification downgrade is permitted.

## 10. Trust and security

- Provider tokens remain environment-only and absent from request bodies, receipts, snapshots, fixtures, logs and exceptions.
- Acquisition writes source bytes first and receipt last, with no clobber by default.
- Untrusted JSON/CSV is duplicate-key aware, non-finite rejecting and unit explicit.
- Local mutable DuckDB/Parquet/pickle files are acquisition candidates only; Builder receives exact snapshotted bytes, never a database handle.
- Source acquisition time never substitutes for provider availability time unless an accepted ADR explicitly permits it.

## 11. Forbidden paths

| Authority | Forbidden | Required route |
| --- | --- | --- |
| A1/A6 | Strategy or Runtime reads Tushare, DuckDB, CSV directories or current APIs | Backtest-owned acquisition → G12A SourceSnapshot → pure Builder → G12C/D publication. |
| A2 | Infer Universe completeness from final files or bar presence | Normalized membership revisions plus explicit closure declaration and G12K coverage. |
| A3 | Treat zero provider rows as permanent absence | Preserve acquisition-time bounded observation and false completeness flags. |
| A4 | Use adjusted prices as fills | Raw execution-reference/open stream for fills; adjusted observations are signal-only. |
| A5 | Publish provider ratios as canonical quality score | Strategy Feature Manifest computes features from exact statement refs. |

## 12. Exact write set after approval

This contract does not authorize implementation. Expected future ownership:

- Backtest acquisition: `backtest/tools/acquisition/`;
- Builder normalized payloads and construction: `backtest/packages/market-bundle-builder/src/crypto_quant_bundle_builder/`;
- Builder public exports only after contract acceptance;
- static fixtures under `backtest/tests/fixtures/market_data/providers/`;
- architecture and focused tests under `backtest/tests/`;
- Acceptance Matrix/plan status updated only by the governance fan-in owner.

No Platform Research, Validation or Promotion source change belongs to QB-DATA-01.

## 13. Readiness gate

`NOT_READY` until all are true:

1. accepted provider/source contracts exist for every consumed stage; current public sources remain `SOURCE_BOUNDED_ONLY` or `MISSING`;
2. exact finite stage captures/manifests exist for Fold A and B with complete S0→S4 scope equations;
3. catalog, Universe, industry, status and corporate-action prerequisite contracts are accepted;
4. financial/governance payload schemas, availability rules and closure declarations are approved;
5. one clean Builder candidate proves deterministic publication/reopen and coverage failures;
6. Backtest owner approves the capability names and write set.

## 14. First sentinels

The first acquisition sentinel is under review in [`YungeG/quant-backtest#1`](https://github.com/YungeG/quant-backtest/pull/1), remotely reachable commit `e7e874fc58e0911b7df1cd0463387526afcb845d`. It captures only `000651.SZ`, period `20231231`, the three raw Tushare statement responses and one exact CNINFO annual-report PDF. It stops at a verified source-bounded `SourceSnapshot`; it grants no Builder or Strategy authority.

QB-FIN-SENTINEL-02 is open stacked PR [`YungeG/quant-backtest#2`](https://github.com/YungeG/quant-backtest/pull/2) at head `146cd227b2fc707726e133dbbd08cde356f21dcd`. It adds expanded formula inputs and raw official publication-confirmation evidence through the approved proxy without modifying PR #1. A real five-member candidate SourceSnapshot now exists at `sha256:dec0abb1828f8b87256347e72b6ccfe2f84a2ca13f36aa1415c9a53e96a0c7d5`.

After accepted acquisition, availability, revision, presentation, unit and field contracts exist, the first Builder sentinel remains:

```text
Construct CnAShareQualityResearchBundleDeclarationV1 with a missing
financial_statement_observations@1 member and require
FINANCIAL_PAYLOAD_INCOMPLETE with no publication files.
```

The next safe additive work is the user-approved S0 source-bounded lightweight catalog sentinel described by QB-DATA-STAGE-01. It may estimate funnel scope and test plumbing, but all historical completeness/survivorship/decision-grade flags remain false. Builder/Strategy execution remains unauthorized.
