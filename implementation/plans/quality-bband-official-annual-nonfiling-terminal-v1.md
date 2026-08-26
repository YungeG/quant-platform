# QB-S2-NONFILE-01 — official annual-report non-filing terminal v1

- **Status:** `IMPLEMENTATION_PACKET_FROZEN / USER_APPROVED / PLAN_ONLY`
- **Approved:** 2026-08-26
- **Backtest implementation base:** `33f7320bd3f1e81c6a985f2fdeea39aedb7bc01e`
- **Purpose:** let competent-source confirmed annual-report non-filings exact-cover issuer-local S2 members without fabricated statements, silent issuer deletion, unrelated-issuer blocking or forced exits

## 1. Approved behavior

An accepted `official_annual_report_nonfiling_declaration@1`:

1. terminal-covers the expected income, balance-sheet and cash-flow member keys for one Instrument/fiscal period;
2. supplies no numeric value and never becomes a statement row or threshold failure;
3. produces issuer-local `UNRESOLVED_DECISION_MATERIAL / REQUIRED_ANNUAL_REPORT_NOT_FILED` from its conservative availability boundary;
4. excludes only that issuer/date from S3, valuation, ranking and new-entry evaluation;
5. does not trigger the date-global no-target rule for unrelated issuers;
6. does not force an existing holding to exit, release its slot or emit a replacement target;
7. does not backdate source publication, suspension, later delisting or later evidence.

Before declaration availability, that issuer/date remains active S2 QB-DATA blocked. A later accepted annual filing ends the unresolved interval only from the filing's own availability; no earlier decision is backfilled.

## 2. Existing identity and primitives

Implementation reuses public Backtest package types and functions:

```text
crypto_quant_domain.InstrumentId
crypto_quant_domain.UtcInstant
crypto_quant_domain.canonical_sha256
crypto_quant_bundle_builder.SourceSnapshot
crypto_quant_bundle_builder.verify_source_snapshot
```

Canonical provider-code mapping is exact:

```text
([0-9]{6}).SZ -> InstrumentId("xshe", code)
([0-9]{6}).SH -> InstrumentId("xshg", code)
```

Any other code or mapping disagreement returns `CATALOG_IDENTITY_MISMATCH`.

Dates are Python `date` values serialized as `YYYY-MM-DD`. Epoch nanoseconds are nonnegative integers; booleans are invalid integers. Hashes are lowercase `sha256:` plus 64 hexadecimal characters.

## 3. Source qualification

One declaration consumes one verified SourceSnapshot containing exactly two reviewed source documents:

```text
INITIAL_NONFILING_PROOF
TERMINAL_CONFIRMATION
```

Both members must be regular retained bytes declared by the SourceSnapshot. `verify_source_snapshot` must succeed against the snapshot archive before semantic evidence review. The declaration binds all three snapshot identities:

```text
snapshot_id
content_tree_hash
provenance_hash
```

The initial document must affirm that the issuer did not file the named annual report by the statutory deadline. A pre-deadline warning or expectation alone is insufficient.

The terminal document must affirm that the report remained unfiled through listing termination or that annual audit/report work remained incomplete at the last listed-state terminal. v1 accepts only:

```text
terminal_confirmation = "NOT_FILED_THROUGH_LISTING_TERMINATION"
```

`OPEN_ENDED` is unsupported.

## 4. Reviewed evidence schema

```text
ReviewedNonFilingDocumentV1
```

Exact fields:

```text
type: Literal["reviewed_nonfiling_document"]
schema_version: Literal[1]
role: INITIAL_NONFILING_PROOF | TERMINAL_CONFIRMATION
authority: ISSUER | SSE | SZSE | CSRC | CSRC_BRANCH
member_key: str
source_url: str
published_date: date
publication_precision: DATE_ONLY | EXACT_INSTANT
published_at_epoch_nanoseconds: int | null
content_hash: str
byte_count: int
reviewed_pages: tuple[int, ...]
reviewed_excerpt: str
issuer_assertion: str
period_assertion: str
supersedes_member_key: str | null
reviewer_key: Literal["quality-bband-eight-issuer-official-authority-audit-v1"]
reviewed_at_epoch_nanoseconds: int
```

Rules:

- `member_key`, URL, excerpt and assertions are nonempty trimmed strings;
- `byte_count > 0`; reviewed pages are positive, strictly increasing and nonempty;
- `content_hash` and byte count equal the verified snapshot member;
- `EXACT_INSTANT` requires `published_at_epoch_nanoseconds`; `DATE_ONLY` requires null;
- initial proof has `supersedes_member_key=null`;
- terminal confirmation has `supersedes_member_key` equal to the initial member key;
- exactly one of each role exists;
- input order is ignored; canonical order is role order above, then publication boundary, then member key;
- duplicate member keys or duplicate roles fail; no duplicate collapse is inferred.

## 5. Accepted availability input

```text
OfficialNonFilingAvailabilityV1
```

Exact fields:

```text
type: Literal["official_nonfiling_availability"]
schema_version: Literal[1]
source_visibility_at: UtcInstant
deadline_boundary_at: UtcInstant
available_at: UtcInstant
calendar_authority_ref: str
source_availability_ref: str
```

`available_at` must equal:

```text
max(source_visibility_at, deadline_boundary_at)
```

`deadline_boundary_at` is the first exact accepted exchange-session open strictly after the statutory deadline. `source_visibility_at` follows the frozen financial availability policy: exact instant when retained, otherwise first exact later accepted exchange-session open after the publication date.

A pre-deadline expectation cannot qualify as initial proof. Source publication after a screen cannot authorize that screen.

Initial candidate availability audit:

| Instrument / period | definitive initial proof | candidate `available_at` boundary | primary screen |
|---|---|---|---|
| `000693.SZ` / 2018 | 2019-04-30 issuer non-filing notice | 2019-05-06 open | covered at 2019-05-06 T-close |
| `600090.SH` / 2021 | 2022-04-30 SSE/issuer non-filing authority | 2022-05-05 open | covered at 2022-05-05 T-close |
| `600146.SH` / 2021 | 2022-04-30 SSE/issuer non-filing authority | 2022-05-05 open | covered at 2022-05-05 T-close |
| `000038.SZ` / 2022 | 2023-05-09 definitive post-deadline authority | 2023-05-10 open | 2023-05-04 remains blocked |
| `000976.SZ` / 2023 | 2024-05-12 definitive post-deadline authority | 2024-05-13 open | 2024-05-06 remains blocked |
| `000622.SZ` / 2024 | 2025-05-06 definitive post-deadline authority | 2025-05-07 open | 2025-05-06 remains blocked |
| `601028.SH` / 2024 | terminal proof after 2025-04-30; exact source packet pending | exact boundary pending packet | 2025-05-06 remains blocked unless earlier definitive proof is accepted |

This table is a readiness target, not accepted availability evidence. Publication requires accepted Calendar/Session refs and retained source bytes.

## 6. Declaration schema

```text
OfficialAnnualReportNonFilingDeclarationV1
```

Exact fields:

```text
type: Literal["official_annual_report_nonfiling_declaration"]
schema_version: Literal[1]
declaration_id: str
instrument_id: InstrumentId
provider_code: str
fiscal_period_end_date: date
statutory_deadline_date: date
filing_status: Literal["NOT_FILED_BY_STATUTORY_DEADLINE"]
economic_effective_date: date
available_at: UtcInstant
active_interval_start: UtcInstant
active_interval_end: UtcInstant
covered_api_names: tuple[str, str, str]
covered_statement_kinds: tuple[str, str, str]
source_snapshot_id: str
source_content_tree_hash: str
source_provenance_hash: str
source_document_refs: tuple[ReviewedNonFilingDocumentV1, ReviewedNonFilingDocumentV1]
terminal_confirmation: Literal["NOT_FILED_THROUGH_LISTING_TERMINATION"]
terminal_confirmation_fact_date: date
terminal_confirmation_available_at: UtcInstant
limitations: tuple[str, ...]
```

Frozen tuples and bijection:

```text
income_vip       <-> INCOME_STATEMENT
balancesheet_vip <-> BALANCE_SHEET
cashflow_vip     <-> CASH_FLOW_STATEMENT
```

Tuple order is exactly income, balance sheet, cash flow. `limitations` is sorted lexicographically, unique and nonempty. `economic_effective_date == statutory_deadline_date`; `available_at == active_interval_start`.

`active_interval_end` is the earlier of:

1. an accepted later annual filing availability; or
2. the exact next accepted annual S2 boundary.

The interval is half-open `[start, end)` and `end > start`. For initial v1 declarations, terminal evidence proves no later listed-period filing; a later filing input still shortens the interval and cannot backfill it.

The declaration body excludes `declaration_id`. `canonical_sha256(body)` constructs the ID. Construction canonical-sorts source refs and limitations, then reconstructs and re-hashes before success.

## 7. Pure Builder operation

Exact Backtest write set:

1. `packages/market-bundle-builder/src/crypto_quant_bundle_builder/official_annual_report_nonfiling_v1.py`
2. `tests/bundle_builder/providers/tushare/test_official_annual_report_nonfiling_v1.py`
3. `tests/architecture/test_official_annual_report_nonfiling_v1_boundary.py`

All predecessor bytes remain unchanged. No public-root export is added in this candidate.

Symbols:

```text
NonFilingDocumentRole
NonFilingAuthority
ReviewedNonFilingDocumentV1
OfficialNonFilingAvailabilityV1
OfficialAnnualReportNonFilingDeclarationV1
OfficialAnnualReportNonFilingFailure
OfficialAnnualReportNonFilingOutcome
declare_official_annual_report_nonfiling_v1(...)
```

The operation consumes already verified immutable values. It performs no filesystem access, network request, clock read, PDF parsing, source acquisition or repository publication.

## 8. Exact-cover integration

Unique S2 member identity remains:

```text
(api_name, canonical InstrumentId, period)
```

Define disjoint unique key sets:

```text
E = P ⊎ O ⊎ N
```

- `E`: accepted-S1 expected keys;
- `P`: provider-resolved keys from S2A terminal leaves;
- `O`: official-filing backfill keys;
- `N`: official non-filing terminal keys.

Raw duplicate/revision rows do not increase key cardinality. A key in more than one set fails. Every S2B manifest binds the accepted-S1 expected-set hash, S2A snapshot/tree/provenance identities, extraction-manifest hash and all scanned/retained/extra row counts.

For the current provisional roster only, the target sentinel is:

```text
96,537 = 96,515 P + 1 O + 21 N
```

Any accepted-S1 membership change requires recomputation; the provisional counts are never hard-coded as formal S1 authority.

## 9. Issuer-local strategy semantics

`UNRESOLVED_DECISION_MATERIAL / REQUIRED_ANNUAL_REPORT_NOT_FILED` is a closed issuer-local noncandidate:

- it completes that issuer's quality disposition;
- it prevents that issuer from S3 and entry ranking;
- it does not trigger the date-global no-target rule;
- unrelated qualified issuers may continue through ranking;
- all other `UNRESOLVED_DECISION_MATERIAL` reasons retain global blocking behavior;
- an existing holding receives its independent continuation disposition and occupies its slot; the non-filing declaration alone emits no exit or slot release.

## 10. Failure mapping

No competing top-level hierarchy is created.

| Condition | Existing top-level failure |
|---|---|
| malformed/foreign type, enum, date, instant or tuple | `INPUT_TYPE_MISMATCH` |
| provider-code/Instrument disagreement | `CATALOG_IDENTITY_MISMATCH` |
| snapshot verification, source bytes/hash/size/member/ref conflict | `SOURCE_MEMBER_CONFLICT` |
| publication/availability, supersession, terminal confirmation or active-interval conflict | `FINANCIAL_REVISION_MISMATCH` |
| API-kind mapping, duplicate terminal, overlap or exact-cover mismatch | `BUNDLE_EXACT_COVER_MISMATCH` |
| declaration reconstruction/hash mismatch | `PUBLICATION_INTEGRITY_FAILURE` |

Failure precedence is table order. Declaration reconstruction occurs before later S2B semantic exact-cover evaluation. The pure operation does not publish repositories.

## 11. Acceptance sentinels

1. input source-ref order does not change `declaration_id`;
2. snapshot provenance or source-byte mutation fails;
3. pre-deadline evidence cannot create an early declaration;
4. wrong API-kind mapping, missing key, duplicate terminal or statement overlap fails;
5. later filing availability shortens the half-open interval without backfill;
6. a non-held non-filer is excluded locally while unrelated ranking proceeds;
7. a held non-filer emits no exit or slot release;
8. combined source corruption and cover mismatch returns the earlier source failure;
9. all seven initial declarations reconstruct byte-identically from accepted source/evidence inputs.

## 12. Initial issuer-period set

```text
000693.SZ / 2018-12-31
600090.SH / 2021-12-31
600146.SH / 2021-12-31
000038.SZ / 2022-12-31
000976.SZ / 2023-12-31
000622.SZ / 2024-12-31
601028.SH / 2024-12-31
```

## 13. Nonclaims

This contract does not establish S0/S1 authority, infer non-filing from absence, qualify an issuer, calculate metrics, create statement values, authorize a forced exit or permit Strategy/Backtest/Validation/Live execution. It only turns competent-source confirmed non-filing into an explicit issuer-local unresolved S2 outcome.
