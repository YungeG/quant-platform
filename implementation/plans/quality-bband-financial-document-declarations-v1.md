# QB-FIN-DOC-01 — Financial document declarations v1

- **Status:** `CONTRACT_FROZEN_FOR_REVIEW / DECLARATIONS_NOT_PUBLISHED`
- **Owner:** Backtest G12 data-governance reviewer
- **Raw source prerequisite:** stacked PR #2 five-member SourceSnapshot
- **Consumers:** QB-FIN-AVAIL-01 and QB-FIN-FIELDS-01

## 1. Outcome

Provide two small immutable human-reviewed declarations that bind semantic facts to exact official PDF bytes without placing PDF parsing or unverified semantic claims inside acquisition receipts:

1. `FinancialPublicationConfirmationDeclarationV1`;
2. `FinancialStatementUnitDeclarationV1`.

The declarations are governance evidence over exact source documents. They are not raw provider members, MarketEvents, normalized statement rows or Strategy features.

## 2. Trust model

A declaration succeeds only when:

- the referenced PDF member exists in one verified SourceSnapshot;
- URL, byte count and SHA-256 exact-match the frozen document;
- page/excerpt/source context are reviewed against those exact bytes;
- reviewer identity and review time are immutable and non-secret;
- the declaration is content-addressed and independently reconstructed;
- acquisition time, review time and historical availability remain separate.

Builder does not parse arbitrary PDF text. It consumes the exact declaration and verifies its document/member/hash binding. A different PDF byte, page, excerpt or reviewer produces a new declaration identity.

## 3. Publication confirmation declaration

Exact source:

| Field | Value |
| --- | --- |
| Source member | `response/cninfo/publication-confirmation/1220300051.pdf` |
| URL | `https://static.cninfo.com.cn/finalpage/2024-06-08/1220300051.PDF` |
| Bytes | `302155` |
| SHA-256 | `sha256:a78a67865a7ea989c4fd8b053fad1aa75f36d22c10d14387800ff16b698dbc60` |
| Page | `1` |
| Issuer/security | 珠海格力电器股份有限公司 / `000651` |
| Confirmed report | `2023 年年度报告` |
| Confirmed disclosure date | `2024-04-30` |

Frozen semantic excerpt:

> 珠海格力电器股份有限公司（以下简称“公司”）已于 2024 年 4 月 30 日在巨潮资讯网（http://www.cninfo.com.cn）披露了《2023 年年度报告》。

Proposed canonical value:

```python
FinancialPublicationConfirmationDeclarationV1 = {
  schema_version=1,
  declaration_key="cn-a-share.000651.2023-annual-report-publication-confirmation.v1",
  source_snapshot_id,
  source_member_key,
  source_document_url,
  source_document_byte_count,
  source_document_hash,
  page_number=1,
  issuer_name,
  provider_security_code="000651.SZ",
  instrument_candidate="xshe:000651",
  report_title="2023 年年度报告",
  report_period="20231231",
  confirmed_disclosure_date="20240430",
  reviewed_excerpt,
  review_method="human_reviewed_exact_document_hash.v1",
  reviewer_identity,
  reviewed_at,
  declaration_hash,
}
```

This declaration confirms a historical date only. It does not claim an exact intraday publication instant. QB-FIN-AVAIL-01 applies the conservative next-declared-Session rule.

## 4. Statement unit declaration

Exact source:

| Field | Value |
| --- | --- |
| Source member | `response/cninfo/annual-report/1219928418.pdf` |
| URL | `http://static.cninfo.com.cn/finalpage/2024-04-30/1219928418.PDF` |
| Bytes | `3911496` |
| SHA-256 | `sha256:32ebc475a2291ce4f1b5c1a9f9da55227e03192f07e75041e976c29d213ec8aa` |
| Consolidated balance sheet | report pages `113–114` |
| Consolidated income statement | report page `115` |
| Consolidated cash-flow statement | report page `116` |
| Currency/unit | `CNY` / `yuan` |

Frozen reviewed facts:

- `合并资产负债表` — `编制单位：珠海格力电器股份有限公司` — `单位：人民币元`;
- `合并利润表` — `编制单位：珠海格力电器股份有限公司` — `单位：人民币元`;
- `合并现金流量表` — `编制单位：珠海格力电器股份有限公司` — `单位：人民币元`.

Proposed canonical value:

```python
FinancialStatementUnitDeclarationV1 = {
  schema_version=1,
  declaration_key="cn-a-share.000651.2023-annual-report-consolidated-unit.v1",
  source_snapshot_id,
  source_member_key,
  source_document_url,
  source_document_byte_count,
  source_document_hash,
  issuer_name,
  provider_security_code="000651.SZ",
  instrument_candidate="xshe:000651",
  report_period="20231231",
  statement_evidence=(
    {kind="BALANCE_SHEET", pages=(113,114), title="合并资产负债表", unit_text="单位：人民币元"},
    {kind="INCOME_STATEMENT", pages=(115,), title="合并利润表", unit_text="单位：人民币元"},
    {kind="CASH_FLOW_STATEMENT", pages=(116,), title="合并现金流量表", unit_text="单位：人民币元"},
  ),
  accounting_currency="CNY",
  accounting_unit="yuan",
  review_method="human_reviewed_exact_document_hash.v1",
  reviewer_identity,
  reviewed_at,
  declaration_hash,
}
```

The declaration applies only to the three consolidated statements and exact report hash. It does not establish units for Tushare-derived ratios, share counts, percentages or another issuer/report.

## 5. Reviewer and time rules

- `reviewer_identity` is a canonical repository-governance identity, not a display name or credential.
- `reviewed_at` is the actual immutable review/publication time; callers cannot backdate it.
- `reviewed_at` must be no earlier than acquisition of the exact source member.
- The later declaration review time does not become historical statement `available_at`.
- Re-review of unchanged bytes may produce a successor governance declaration but cannot refresh historical source time or change semantic facts silently.
- No declaration may contain tokens, local paths, mutable URLs, comments or unsupported extra facts.

## 6. Failure precedence

| Priority | Condition | Proposed code |
| ---: | --- | --- |
| 1 | exact input/schema/type mismatch | `INPUT_MISMATCH` |
| 2 | SourceSnapshot/member unavailable or unverified | `SOURCE_MEMBER_UNAVAILABLE` |
| 3 | URL/bytes/hash mismatch | `DOCUMENT_IDENTITY_MISMATCH` |
| 4 | issuer/security/report context mismatch | `DOCUMENT_CONTEXT_MISMATCH` |
| 5 | page/title/excerpt/unit evidence mismatch | `REVIEW_EVIDENCE_MISMATCH` |
| 6 | reviewer identity/method invalid | `REVIEW_AUTHORITY_INVALID` |
| 7 | review time before source acquisition | `REVIEW_TIME_INVALID` |
| 8 | duplicate declaration identity with conflicting content | `DECLARATION_IDENTITY_CONFLICT` |
| 9 | declaration reconstruction/hash mismatch | `DECLARATION_RECONSTRUCTION_MISMATCH` |

One failure returns no declaration and no availability/unit authority.

## 7. Security and purity

- Pure typed declaration construction/verification only.
- No PDF parser, subprocess, OCR, network, filesystem discovery, current clock or provider token in Builder/Runtime.
- Exact PDF bytes remain in the verified SourceSnapshot.
- Reviewer identity is non-secret; credentials and signatures are external governance mechanics.
- No semantic claim is copied into the acquisition receipt.
- No declaration can authorize decision/live/deployment grade.

## 8. Current state

PR #2 captures the required raw documents but has not been accepted or executed with credentials. Therefore:

```text
publication declaration = unavailable
unit declaration = unavailable
financial available_at = unavailable
formula-ready normalized statements = unavailable
```

## 9. Acceptance

1. exact reconstruction for both declarations;
2. wrong snapshot/member/URL/bytes/hash/page/excerpt/title/date/unit fails;
3. reviewer and review-time failures preserve precedence;
4. declaration identity changes for any semantic/source/reviewer change;
5. later review time never becomes historical Strategy availability;
6. acquisition receipt contains no semantic confirmation claim;
7. unit declaration applies only to exact consolidated statements/report hash;
8. no PDF parsing or I/O in declaration module;
9. no partial declaration on failure;
10. PR #1/#2 source identities remain unchanged.

## 10. Readiness decision

The declaration contracts are frozen for review. Publishing real declarations requires accepted PR #2, a credentialed five-member SourceSnapshot, and a named Backtest G12 data-governance reviewer.
