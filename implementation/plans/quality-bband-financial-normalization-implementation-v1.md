# QB-FIN-NORM-IMPL-01 — Gree 2023 financial normalization packet

- **Status:** `STACKED_CANDIDATE_PUBLISHED / NOT_ACCEPTED`
- **Owner:** Backtest Market Bundle Builder
- **Base:** stacked PR #3 commit `b4124d5985a6f9cbd39221fd55286abf5608b6b8`
- **Candidate:** Backtest PR [#4](https://github.com/YungeG/quant-backtest/pull/4), commit `fa58e68d7b51ee5517e5a14c87c3590d1bda2976`
- **SourceSnapshot:** `sha256:dec0abb1828f8b87256347e72b6ccfe2f84a2ca13f36aa1415c9a53e96a0c7d5`
- **Declarations:** `sha256:59e09eb542a6e2ec480a7b8ed322d9ae9106416460f0999216fd5564f7278007`

## 1. Outcome

Purely normalize the exact real Tushare income/balance/cash-flow members into three source-bounded financial statement observation revisions plus declared debt/D&A supplement facts.

This sentinel emits no `MarketEvent`, MarketBundle, Strategy feature, ratio, rank, target, Backtest request or grade.

## 2. Minimal seam

```python
class Gree2023FinancialStatementKind(str, Enum): ...
class Gree2023FinancialNormalizationFailureCode(str, Enum): ...
class Gree2023FinancialStatementObservationRevisionV1: ...
class Gree2023FinancialStatementObservationSetV1: ...
class Gree2023FinancialNormalizationOutcome: ...

def normalize_gree_2023_financial_statements_v1(
    source_snapshot: SourceSnapshot,
    declarations: Gree2023FinancialDocumentDeclarationsV1,
) -> Gree2023FinancialNormalizationOutcome: ...
```

Both inputs are exact in-memory values. No filesystem/network/clock/provider/PDF access.

## 3. Exact source members and rows

| Statement | Member | Real row hashes |
| --- | --- | --- |
| Income | `response/tushare/income/000651.SZ-20231231-20240430-v2.json` | `sha256:7650431917f2c6d302075cb08265e2c0993681bff2e964f793d179476792e4a0` |
| Balance | `response/tushare/balancesheet/000651.SZ-20231231-20240430-v2.json` | `sha256:42558caf71776422ea55d8c54f5cbe20c5a5869c6a72e44b37d7d8662adb37e3`, `sha256:f891a94138f37fb1dad697354f9278a45e779a2b8c700ffafa0ea34090a00688` |
| Cash flow | `response/tushare/cashflow/000651.SZ-20231231-20240430-v2.json` | `sha256:7765c5315c9e65a9799af793050520dc2a7f21dd4dc9e410820b0b326ccbeba7` |

Balance rows have identical economic fields and differ only by `update_flag` (`0`/`1`). Normalization:

- retains both row hashes and update flags as source evidence;
- collapses them to one economic observation;
- never treats `update_flag=1` as provider revision/finality authority;
- fails if any non-`update_flag` field differs.

## 4. Parsing rules

- duplicate-key/non-finite rejecting UTF-8 JSON;
- exact provider envelope and field tuple;
- JSON numbers parsed directly to canonical decimal strings, never binary float;
- `null` preserved as null until exact declaration substitution;
- exact issuer/date/period/report type `1`/company type `1`;
- exact row count `1/2/1` and frozen real row hashes computed from canonical rows whose JSON numeric tokens are preserved as strings;
- input order cannot affect normalized identity.

## 5. Availability

The aggregate declaration confirms date-only disclosure `20240430`. QB-FIN-AVAIL-01 plus the official 2024 SZSE Calendar produces the fixed conservative boundary:

```text
2024-05-06T09:30:00+08:00
= 2024-05-06T01:30:00Z
= UtcInstant(1714959000000000000)
```

The fixed normalization sentinel exact-requires:

```text
available_at_utc = UtcInstant(1714959000000000000)
```

This is source-bounded candidate visibility, not provider exact intraday publication time.

## 6. Observation identity

Economic key:

```text
canonical_sha256({
  instrument_id="xshe:000651",
  statement_kind,
  report_period_end="20231231",
  period_kind="ANNUAL",
  consolidation_scope="CONSOLIDATED",
  accounting_currency="CNY",
  accounting_unit="yuan",
})
```

Observation lineage key adds presentation basis `CURRENT_CONSOLIDATED`.

Revision body binds:

- economic/lineage keys;
- statement kind and exact line items;
- source snapshot/tree/provenance;
- source member and all source row hashes/update flags;
- report/confirmation/declaration hashes;
- `available_at_utc`;
- `provider_revision_id=None`;
- `supersedes_revision_id=None`;
- `source_bounded=true`;
- closure/grade/deployment false.

`revision_id = canonical_sha256(revision body without revision_id)`.

## 7. Declaration substitutions and supplements

Raw balance nulls remain visible in source evidence. Normalized resolved line items may set:

```text
bond_payable = "0.00"
st_bonds_payable = "0.00"
```

only because declaration hash `sha256:59e09eb542a6e2ec480a7b8ed322d9ae9106416460f0999216fd5564f7278007` exact-binds the official ending-zero bond evidence.

Observation set additionally binds:

```text
ending_interest_bearing_debt = "88533001486.99"
ending_depreciation_and_amortization = "5283331216.38"
```

No generic null→zero behavior is introduced.

## 8. Proposed values

```python
Gree2023FinancialStatementObservationRevisionV1 = {
  schema_version,
  statement_kind,
  economic_statement_key,
  observation_lineage_key,
  instrument_id="xshe:000651",
  report_period_end="20231231",
  period_kind="ANNUAL",
  consolidation_scope="CONSOLIDATED",
  accounting_currency="CNY",
  accounting_unit="yuan",
  presentation_basis="CURRENT_CONSOLIDATED",
  announcement_date="20240430",
  actual_announcement_date="20240430",
  available_at_utc,
  source_snapshot_id,
  source_member_key,
  source_row_hashes,
  provider_update_flags,
  official_document_hash,
  publication_confirmation_hash,
  declaration_hash,
  raw_null_fields,
  line_items,
  line_items_hash,
  provider_revision_id=None,
  supersedes_revision_id=None,
  revision_id,
  source_bounded=true,
  revision_closure_complete=false,
  decision_grade_eligible=false,
  deployment_authorized=false,
}

Gree2023FinancialStatementObservationSetV1 = {
  schema_version,
  source_snapshot_id,
  declaration_hash,
  available_at_utc,
  revisions=(income,balance,cashflow),
  ending_interest_bearing_debt,
  ending_depreciation_and_amortization,
  source_bounded=true,
  revision_closure_complete=false,
  decision_grade_eligible=false,
  deployment_authorized=false,
  observation_set_hash,
}
```

Constructors recompute all nested identities, substitutions, arithmetic and hashes.

## 9. Failure precedence

| Priority | Predicate | Code |
| ---: | --- | --- |
| 1 | input exact type/schema mismatch | `INPUT_MISMATCH` |
| 2 | SourceSnapshot verification/identity mismatch | nested `SourceSnapshotFailureCode` or `SOURCE_IDENTITY_MISMATCH` |
| 3 | declaration reconstruction/source binding mismatch | `DECLARATION_MISMATCH` |
| 4 | member/envelope/field/row shape mismatch | `SOURCE_RESPONSE_INVALID` |
| 5 | real row hash/cardinality mismatch | `SOURCE_ROW_SET_MISMATCH` |
| 6 | issuer/date/period/report/company context mismatch | `STATEMENT_CONTEXT_MISMATCH` |
| 7 | balance economic rows differ beyond update flag | `BALANCE_PRESENTATION_CONFLICT` |
| 8 | required nondeclared line item null/missing | `REQUIRED_LINE_ITEM_MISSING` |
| 9 | declaration substitution/source value mismatch | `DECLARATION_SUBSTITUTION_MISMATCH` |
| 10 | availability identity mismatch | `AVAILABILITY_MISMATCH` |
| 11 | revision/result reconstruction mismatch | `RESULT_RECONSTRUCTION_MISMATCH` |

One failure emits no partial revision/set.

## 10. Exact write set

Stacked Backtest worktree from PR #3:

- `packages/market-bundle-builder/src/crypto_quant_bundle_builder/gree_2023_financial_statement_normalization_v1.py`;
- `tests/bundle_builder/providers/tushare/test_gree_2023_financial_statement_normalization_v1.py`;
- `tests/architecture/test_gree_2023_financial_statement_normalization_v1_boundary.py`.

No root export. Protect PRs #1–#3 files, locks and all Runtime/Trading/Market Data sources.

## 11. Acceptance

1. synthetic fixed-scope success/golden;
2. opt-in real SourceSnapshot + real declaration success/golden;
3. exact decimal-token preservation;
4. balance duplicate collapse and economic-conflict failure;
5. row hash/cardinality/field/envelope/context mutations;
6. null bond substitution only under declaration;
7. required nondeclared null failure;
8. exact availability/revision/set identities;
9. forged nested revisions/set/hash rejected;
10. input order noninterference;
11. no I/O/PDF parser/provider/Runtime/Trading/Market Data import;
12. Builder-wide/full regression and independent review.

## 12. Implementation evidence

Stacked Backtest PR [#4](https://github.com/YungeG/quant-backtest/pull/4):

- base: `research/qb-fin-declarations-v1` / PR #3;
- commit: `fa58e68d7b51ee5517e5a14c87c3590d1bda2976`;
- focused: `19 passed, 1 skipped`;
- real opt-in SourceSnapshot + declaration: `1 passed`;
- Builder-wide: `346 passed, 2 skipped`;
- broad regression: `2526 passed, 2 skipped, 1 deselected`; the deselected predecessor PR #3 exact-write-set guard cannot accept a stacked successor by construction;
- independent re-review: `ACCEPTED`, no blocking/high/medium/low findings;
- LSP/lens: clean.

Published real source-bounded candidate:

```text
/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/
  normalized-observation-sets/000651.SZ/20231231/v1-candidate-01
```

- observation-set hash: `sha256:632206f85bcff71dbcccfd20a3593e14fb895b33bd138ac25bbf9b947e4a4a7c`;
- observation-set file SHA-256: `sha256:857a57058d790f83b8d227e6afb676b13d2f3ab2a784b132e3c1bc7486468ef0`;
- income revision: `sha256:8957590f45f32ed9b285e940f2fa0c0524cb28377e86c745ab39aa3875ba63e8`;
- balance revision: `sha256:3e64ee623ca3676f1ec10daf56588dceabdd77a41ba0419d4c9010241313f45d`;
- cash-flow revision: `sha256:71f4428e79d3bd7638cc9c1d98c1471f9802e9a90d25f7fa06b739bc57f0f986`;
- canonical readback, repeated normalization and credential-exclusion checks passed;
- source-bounded `true`; closure/decision-grade/deployment remain `false`.

## 13. Next handoff

After candidate acceptance, QB-FIN-SELECT-01 can consume the normalized revision set at a Decision instant. Formula calculation still requires at least six annual balance endpoints and five annual statement trios; this one-year sentinel cannot satisfy the Strategy quality filter.
