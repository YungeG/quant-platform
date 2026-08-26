# QB-FIN-DECL-IMPL-01 — Gree 2023 financial declarations implementation packet

- **Status:** `STACKED_PR_OPEN / REAL_CANDIDATE_PUBLISHED / NOT_ACCEPTED`
- **Owner:** Backtest Market Bundle Builder
- **Base:** stacked PR #2 head `146cd227b2fc707726e133dbbd08cde356f21dcd`
- **Contracts:** [`quality-bband-financial-document-declarations-v1.md`](quality-bband-financial-document-declarations-v1.md), [`quality-bband-financial-note-declarations-v1.md`](quality-bband-financial-note-declarations-v1.md)

## 1. Outcome

Add one pure fixed-scope Builder operation that verifies the real five-member SourceSnapshot and publishes one aggregate immutable candidate declaration containing:

- retrospective publication-date confirmation;
- consolidated CNY-yuan statement-unit evidence;
- ending interest-bearing debt scope;
- D&A line-item semantics.

The implementation performs no PDF parsing. The exact PDF hashes/pages/excerpts and reviewed financial values are frozen contract inputs. It proves source binding and arithmetic reconstruction, not automated extraction.

## 2. Minimal seam

```python
class Gree2023FinancialDeclarationFailureCode(str, Enum): ...
class Gree2023FinancialDeclarationFailure: ...
class Gree2023FinancialDocumentDeclarationsV1: ...
class Gree2023FinancialDeclarationOutcome: ...

def declare_gree_2023_financial_documents_v1(
    source_snapshot: SourceSnapshot,
    *,
    reviewed_at: UtcInstant,
) -> Gree2023FinancialDeclarationOutcome: ...
```

Fixed reviewer identity:

```text
platform.a-share-research-orchestrator.v1
```

This identity issues a source-bounded candidate only. It is not Backtest-owner acceptance and cannot set grade/deployment flags true.

No generic declaration framework, registry, PDF adapter or root export is added.

## 3. Exact source identity

| Value | Frozen identity |
| --- | --- |
| SourceSnapshot | `sha256:dec0abb1828f8b87256347e72b6ccfe2f84a2ca13f36aa1415c9a53e96a0c7d5` |
| Content tree | `sha256:d7e92674dd42a4eeabfde354922cfafa9d50837f2076c1ad88233da8c0456b13` |
| Provenance | `sha256:0fcef32df8c6b41ef0ce55121adc9c392cf483ca71134dc27175f6c9512cab17` |
| Report member | `response/cninfo/annual-report/1219928418.pdf` |
| Report hash | `sha256:32ebc475a2291ce4f1b5c1a9f9da55227e03192f07e75041e976c29d213ec8aa` |
| Confirmation member | `response/cninfo/publication-confirmation/1220300051.pdf` |
| Confirmation hash | `sha256:a78a67865a7ea989c4fd8b053fad1aa75f36d22c10d14387800ff16b698dbc60` |

The operation calls `verify_source_snapshot()` before member access and requires exact snapshot/tree/provenance/member identities.

## 4. Aggregate declaration body

```text
{
  type="gree_2023_financial_document_declarations",
  schema_version=1,
  source_snapshot_id,
  content_tree_hash,
  provenance_hash,
  issuer_name="珠海格力电器股份有限公司",
  provider_security_code="000651.SZ",
  instrument_candidate="xshe:000651",
  report_period="20231231",
  reviewer_identity="platform.a-share-research-orchestrator.v1",
  reviewed_at,

  publication_confirmation={
    source_member_key,
    source_document_hash,
    page=1,
    report_title="2023 年年度报告",
    confirmed_disclosure_date="20240430",
    reviewed_excerpt,
  },

  statement_unit={
    source_member_key,
    source_document_hash,
    balance_pages=(113,114),
    income_pages=(115,),
    cashflow_pages=(116,),
    accounting_currency="CNY",
    accounting_unit="yuan",
    unit_text="单位：人民币元",
  },

  financing_liability={
    source_member_key,
    source_document_hash,
    report_page=210,
    bank_borrowings_and_other="87676167515.47",
    bonds_payable="0.00",
    lease_liabilities_including_current="856833971.52",
    non_debt_dividends_payable="5572388.92",
    official_table_total="88538573875.91",
    ending_interest_bearing_debt="88533001486.99",
  },

  depreciation_and_amortization={
    source_member_key,
    source_document_hash,
    report_page=210,
    combined_depreciation_field="depr_fa_coga_dpba",
    combined_depreciation_amount="4808144624.82",
    combined_depreciation_includes=("fixed_assets","investment_property","right_of_use_assets"),
    intangible_amortization_field="amort_intang_assets",
    intangible_amortization_amount="475186591.56",
    separate_use_right_addition="0.00",
    separate_long_term_deferred_addition="0.00",
    ending_depreciation_and_amortization="5283331216.38",
  },

  source_bounded=true,
  revision_closure_complete=false,
  decision_grade_eligible=false,
  deployment_authorized=false,
  declaration_hash,
}
```

`declaration_hash` is `canonical_sha256` of the body without itself.

## 5. Constructor reconstruction

`Gree2023FinancialDocumentDeclarationsV1.__post_init__` must:

1. exact-validate every type/literal/value;
2. recompute source/document context;
3. recompute debt table total:
   `bank + bond + lease + non-debt dividend`;
4. recompute ending interest-bearing debt:
   `bank + bond + lease`;
5. recompute ending D&A:
   `combined depreciation + intangible amortization + separate additions`;
6. require exact false qualification flags;
7. recompute declaration hash.

Forged aggregates/hashes fail construction.

## 6. Failure precedence

| Priority | Predicate | Code |
| ---: | --- | --- |
| 1 | input is not exact `SourceSnapshot`/`UtcInstant` | `INPUT_MISMATCH` |
| 2 | SourceSnapshot verification fails | exact nested `SourceSnapshotFailureCode` |
| 3 | snapshot/tree/provenance identity mismatch | `SOURCE_SNAPSHOT_IDENTITY_MISMATCH` |
| 4 | required member missing or member hash/bytes mismatch | `DOCUMENT_IDENTITY_MISMATCH` |
| 5 | `reviewed_at` earlier than max source-member acquisition time | `REVIEW_TIME_INVALID` |
| 6 | declaration literal/context mismatch | `DECLARATION_CONTEXT_MISMATCH` |
| 7 | debt arithmetic mismatch | `DEBT_RECONCILIATION_MISMATCH` |
| 8 | D&A arithmetic mismatch | `DA_RECONCILIATION_MISMATCH` |
| 9 | declaration reconstruction/hash mismatch | `DECLARATION_RECONSTRUCTION_MISMATCH` |

One failure yields no declaration.

## 7. Exact write set

Stacked Backtest worktree from PR #2:

- `packages/market-bundle-builder/src/crypto_quant_bundle_builder/gree_2023_financial_document_declarations_v1.py`;
- `tests/bundle_builder/providers/tushare/test_gree_2023_financial_document_declarations_v1.py`;
- `tests/architecture/test_gree_2023_financial_document_declarations_v1_boundary.py`.

Protected:

- all v1/v2 acquisition files and PR diffs;
- Builder root exports;
- Runtime/Trading/Market Data packages;
- lock files and existing canonical artifacts.

## 8. Acceptance

1. real reconstructed SourceSnapshot success;
2. exact declaration golden/hash;
3. source snapshot/tree/provenance/member/report/confirmation mutations fail;
4. review-time boundary success/failure;
5. debt and D&A arithmetic mutation failures;
6. qualification flags remain exact false;
7. declaration reconstruction rejects forged values/hash;
8. input order cannot affect identity;
9. no PDF parser, filesystem, network, environment, clock or Runtime/Trading import;
10. acquisition v1/v2 protected bytes and stacked ancestry unchanged;
11. focused + Builder + architecture + full regression;
12. independent review.

## 9. Implementation evidence

Stacked PR [`YungeG/quant-backtest#3`](https://github.com/YungeG/quant-backtest/pull/3):

- base: `research/qb-fin-sentinel-v2` / PR #2;
- commit: `b4124d5985a6f9cbd39221fd55286abf5608b6b8`;
- focused: `14 passed, 1 skipped`;
- real opt-in SourceSnapshot test: `1 passed`;
- Builder-wide: `332 passed, 1 skipped`;
- full regression: `2500 passed, 1 skipped, 8 deselected`;
- independent review: no blocking, high or medium findings;
- LSP/lens clean.

Real candidate artifact:

```text
/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/
  declarations/000651.SZ/20231231/v1-candidate-01
```

- declaration hash: `sha256:59e09eb542a6e2ec480a7b8ed322d9ae9106416460f0999216fd5564f7278007`;
- declaration file SHA-256: `sha256:df76e4451c14d47ace241921aef074e582848bd02b269f58fbff2136d9f22aee`;
- readback verified; qualification/deployment flags false.

## 10. Next handoff

The next stacked pure Builder module may consume:

- the verified SourceSnapshot;
- this aggregate declaration;
- financial availability/revision/presentation contracts;

and emit normalized source-bounded financial statement observations. No formula/Strategy code starts in this declaration lane.
