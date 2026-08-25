# QB-FIN-HISTORY-DECL-IMPL-01 — Gree 2018–2022 period declarations

- **Status:** `IMPLEMENTATION_AUTHORITY_FROZEN / APPROVED_FOR_STACKED_CANDIDATE / NOT_ACCEPTED`
- **Owner:** Backtest Market Bundle Builder
- **Base:** stacked PR #6 head `64159f81fa6f831990690dd133587b96533a0362`
- **SourceSnapshot:** `sha256:aee2ea78f3d51185110bc927836ce77ed51f590a9c7b4c26ee7ecd951cbf8d4b`
- **Audit:** [`research/quality-bband-historical-financial-declaration-audit.md`](../../research/quality-bband-historical-financial-declaration-audit.md)
- **Reviewed at:** `UtcInstant(1787668131165592196)`

## 1. Outcome

Declare exact source-bound publication/unit/debt/D&A facts for one requested Gree annual period.

- `20181231`, `20191231`, `20201231`, `20221231`: return one exact declaration.
- `20211231`: return typed `DEBT_SCOPE_INCOMPLETE` with both exact debt candidates and no declaration.

The operation is period-atomic. It emits no partial declaration, `available_at`, normalized revision, selected trio, formula, MarketBundle, Strategy, Validation or deployment authority.

## 2. Minimal seam

```python
class GreeHistoricalFinancialDeclarationFailureCode(str, Enum): ...
class GreeHistoricalDebtScopeConflictV1: ...
class GreeHistoricalFinancialDeclarationFailure: ...
class GreeHistoricalFinancialPeriodDocumentDeclarationsV1: ...
class GreeHistoricalFinancialDeclarationOutcome: ...


def declare_gree_historical_financial_period_v1(
    source_snapshot: SourceSnapshot,
    report_period: str,
    *,
    reviewed_at: UtcInstant,
) -> GreeHistoricalFinancialDeclarationOutcome: ...
```

No filesystem, PDF parsing, network, environment, Calendar, clock or Runtime access.

## 3. Fixed source authority

```text
source_snapshot_id = sha256:aee2ea78f3d51185110bc927836ce77ed51f590a9c7b4c26ee7ecd951cbf8d4b
content_tree_hash = sha256:d5375befd81c5fb1ab2832a48bb7c3d0b4fc7dcf9b4ea64700f837dc624ce3d9
provenance_hash = sha256:5495fbee8d8668e324be8263f49f9f556ea6a4324b5f530c13a2176f148ad2e5
metadata_member = response/cninfo/announcement-query/000651.SZ-2019-2023-annual-reports-v3.json
metadata_hash = sha256:3292c3b1bd89f01cb41e09401ad306b6ec8e769cac402317817fe395ff0e918e
reviewer_identity = platform.a-share-research-orchestrator.v1
reviewed_at = UtcInstant(1787668131165592196)
```

The review instant is after all snapshot-member acquisition instants. Constructors exact-reconstruct `UtcInstant`; exact-class mutation cannot bypass review-time validation.

Immutable period document facts:

| Period | Member | Full content hash |
| --- | --- | --- |
| `20181231` | `response/cninfo/annual-report/1206125365.pdf` | `sha256:b147eb6b8a4aaf093f3b83550c70e8526415b5b54fe24e4258ce7bfd11d5406a` |
| `20191231` | `response/cninfo/annual-report/1207685438.pdf` | `sha256:1b4869caab122969b322738df69955d788c8dc19b4c6d57188619177e922e708` |
| `20201231` | `response/cninfo/annual-report/1209855305.pdf` | `sha256:0d3c39090adf97fede39149a731a5636bd0eca2002606fb942ca70121dba9072` |
| `20211231` | `response/cninfo/annual-report/1213262535.pdf` | `sha256:96065ec44285bce7a9c0cbee25dfeb2368ec4552d72f06ebf3ecab35136e2444` |
| `20221231` | `response/cninfo/annual-report/1216702261.pdf` | `sha256:7cfc80c2badbf4cd74c5adc080d5072b02cd6c700b04fa7ca0ac44cb8b8fe987` |

## 4. Failure values

Exact codes:

```python
INPUT_MISMATCH
SOURCE_SNAPSHOT_IDENTITY_MISMATCH
PERIOD_UNSUPPORTED
DOCUMENT_IDENTITY_MISMATCH
REVIEW_TIME_INVALID
DEBT_SCOPE_INCOMPLETE
DECLARATION_RECONSTRUCTION_MISMATCH
```

`SourceSnapshotFailureCode` is preserved unchanged.

### 2021 debt conflict

```python
GreeHistoricalDebtScopeConflictV1 = {
  source_snapshot_id,
  report_period="20211231",
  source_member_key="response/cninfo/annual-report/1213262535.pdf",
  source_document_hash="sha256:96065ec44285bce7a9c0cbee25dfeb2368ec4552d72f06ebf3ecab35136e2444",
  official_table_report_page=222,
  official_table_pdf_page=223,
  official_interest_bearing_total="43546910016.46",
  short_bonds_payable="4048840948.73",
  short_bonds_already_in_official_total=true,
  lease_liabilities_including_current="14785264.79",
  omitted_financing_report_page=187,
  omitted_financing_pdf_page=188,
  omitted_financing_label="企业借款及利息",
  omitted_financing_amount="2731680114.20",
  narrow_candidate="43561695281.25",
  broad_candidate="46293375395.45",
  source_bounded=true,
  revision_closure_complete=false,
  decision_grade_eligible=false,
  deployment_authorized=false,
  conflict_hash,
}
```

Conflict body type is `gree_2021_debt_scope_conflict`; `conflict_hash = canonical_sha256(body without conflict_hash)`:

```text
sha256:8cb5ef55e745b6e3858eef5bb1806ebf22c9123490764e79e68f2928ffb66c6f
```

`GreeHistoricalFinancialDeclarationFailure` fields are:

```python
code: GreeHistoricalFinancialDeclarationFailureCode | SourceSnapshotFailureCode
report_period: str | None
debt_scope_conflict: GreeHistoricalDebtScopeConflictV1 | None
```

Failure body:

```python
{
  "type": "gree_historical_financial_declaration_failure",
  "schema_version": 1,
  "code": self.code.value,
  "report_period": self.report_period,
  "debt_scope_conflict": None if conflict is None else conflict.to_canonical_dict(),
}
```

Rules:

- if `report_period` is not exact `str`, `INPUT_MISMATCH` stores period/conflict as `None`;
- if `report_period` is exact `str`, that exact string is preserved in every later failure, including SourceSnapshot failure, `PERIOD_UNSUPPORTED`, document/review failure and reconstruction failure;
- only `DEBT_SCOPE_INCOMPLETE` stores the exact conflict; every other code stores conflict `None`;
- an invalid/forged `reviewed_at` with an exact-string period therefore preserves the period while returning `INPUT_MISMATCH`;
- `to_canonical_dict()` adds `failure_hash`.

Frozen 2021 failure hash:

```text
sha256:2c5b90d0cbd89ccd584c0a33234d796ec9b039abe683ad897b7a5fe61cac5792
```

## 5. Declaration fields

```python
@dataclass(frozen=True, slots=True)
class GreeHistoricalFinancialPeriodDocumentDeclarationsV1:
    source_snapshot_id: str
    content_tree_hash: str
    provenance_hash: str
    report_period: str
    reviewer_identity: str
    reviewed_at: UtcInstant
    confirmed_disclosure_date: str
    accounting_currency: str
    accounting_unit: str
    official_total_kind: str
    official_interest_bearing_total: str
    lease_scope: str
    lease_liabilities_including_current: str
    short_bonds_payable: str
    long_bonds_payable: str
    non_debt_dividends_payable: str
    ending_interest_bearing_debt: str
    combined_depreciation_amount: str
    intangible_amortization_amount: str
    separate_use_right_addition: str
    separate_long_term_deferred_addition: str
    ending_depreciation_and_amortization: str
    source_bounded: bool
    revision_closure_complete: bool
    decision_grade_eligible: bool
    deployment_authorized: bool
    declaration_hash: str
```

All money fields are exact canonical decimal strings. Constructors exact-bind the period facts below, recompute component/debt/D&A arithmetic and reject coherent forgery before computing the declaration hash.

## 6. Canonical body

```python
{
  "type": "gree_historical_financial_period_document_declarations",
  "schema_version": 1,
  "source_snapshot_id": self.source_snapshot_id,
  "content_tree_hash": self.content_tree_hash,
  "provenance_hash": self.provenance_hash,
  "issuer_name": "珠海格力电器股份有限公司",
  "provider_security_code": "000651.SZ",
  "instrument_candidate": "xshe:000651",
  "report_period": self.report_period,
  "reviewer_identity": self.reviewer_identity,
  "reviewed_at": self.reviewed_at,
  "publication_evidence": _publication_body(self.report_period),
  "statement_unit": _statement_unit_body(self.report_period),
  "financing_liability": _financing_body(self.report_period),
  "depreciation_and_amortization": _depreciation_body(self.report_period),
  "source_bounded": self.source_bounded,
  "revision_closure_complete": self.revision_closure_complete,
  "decision_grade_eligible": self.decision_grade_eligible,
  "deployment_authorized": self.deployment_authorized,
}
```

`to_canonical_dict()` adds `declaration_hash`. The four `_..._body(period)` helpers return fresh dictionaries/lists from immutable tuple constants and exact-raise for any non-success period. Their complete key sets and literal values are sections 7–10; no writer-selected fallback or reuse of 2023 values is allowed.

## 7. Publication evidence

Each nested body exact-contains:

```text
source_member_key,source_content_hash,announcement_id,
announcement_time_epoch_milliseconds,publication_date,adjunct_url,precision
```

`precision="DATE_ONLY"`.

| Period | Announcement ID | Epoch milliseconds | Date | Adjunct URL |
| --- | --- | ---: | --- | --- |
| `20181231` | `1206125365` | `1556467200000` | `20190429` | `finalpage/2019-04-29/1206125365.PDF` |
| `20191231` | `1207685438` | `1588176000000` | `20200430` | `finalpage/2020-04-30/1207685438.PDF` |
| `20201231` | `1209855305` | `1619625600000` | `20210429` | `finalpage/2021-04-29/1209855305.PDF` |
| `20211231` | `1213262535` | `1651248000000` | `20220430` | `finalpage/2022-04-30/1213262535.PDF` |
| `20221231` | `1216702261` | `1682697600000` | `20230429` | `finalpage/2023-04-29/1216702261.PDF` |

No `available_at` is emitted.

## 8. Statement-unit bodies

Exact keys:

```text
source_member_key,source_document_hash,
balance_report_pages,balance_pdf_pages,
income_report_pages,income_pdf_pages,
cashflow_report_pages,cashflow_pdf_pages,
accounting_currency,accounting_unit,unit_evidence
```

`unit_evidence` is an ordered list of `{report_page,pdf_page,text}`.

| Period | Report member/hash | Statement report pages | Statement PDF pages | Unit evidence |
| --- | --- | --- | --- | --- |
| `20181231` | `1206125365.pdf` / `sha256:b147...5406a` | balance `[85,86]`, income `[89]`, cash `[91]` | same | p.85/PDF85 `单位：人民币元` |
| `20191231` | `1207685438.pdf` / `sha256:1b48...e708` | balance `[82,83]`, income `[86,87]`, cash `[89,90]` | balance `[83,84]`, income `[87,88]`, cash `[90,91]` | p.82/PDF83 `单位：元`; p.5/PDF6 `单位：人民币元`; p.97/PDF98 `本公司以人民币为记账本位币` |
| `20201231` | `1209855305.pdf` / `sha256:0d3c...9072` | balance `[94,95]`, income `[98]`, cash `[100]` | balance `[95,96]`, income `[99]`, cash `[101]` | p.137/PDF138 `如无特殊说明，金额单位为人民币元` |
| `20221231` | `1216702261.pdf` / `sha256:7cfc...e987` | balance `[117,118]`, income `[119]`, cash `[120]` | same | p.151/PDF152 `如无特殊说明，金额单位为人民币元` |

All exact values use `CNY` / `yuan`. Ellipses above are documentation abbreviations only; production constants use full hashes.

## 9. Financing bodies

Exact keys:

```text
source_member_key,source_document_hash,report_page,pdf_page,
official_total_kind,official_components,official_interest_bearing_total,
lease_scope,lease_liabilities_including_current,
short_bonds_payable,long_bonds_payable,
non_debt_dividends_payable,ending_interest_bearing_debt
```

`official_components` is an ordered list of `{label,amount}`.

### 2018

- page/PDF `182`; `official_total_kind="COMPONENT_ARITHMETIC"`;
- components: `短期借款 22067750002.70`, `吸收存款及同业存放 315879779.13`;
- total/debt `22383629781.83`;
- `lease_scope="PRE_ADOPTION_NOT_RECOGNIZED"`, lease `0.00`;
- short/long bonds `0.00`/`0.00`; dividends `707913.60`.

### 2019

- report page `189`, PDF `190`; `official_total_kind="PRINTED_TOTAL"`;
- components: `短期借款 15944176463.01`, `吸收存款及同业存放 352512311.72`, `拆入资金 1000446666.67`, `长期借款 46885882.86`;
- total/debt `17344021324.26`;
- `lease_scope="PRE_ADOPTION_NOT_RECOGNIZED"`, lease `0.00`; bonds `0.00`/`0.00`; dividends `707913.60`.

### 2020

- report page `195`, PDF `196`; `official_total_kind="PRINTED_TOTAL"`;
- components: `短期借款 20304384742.34`, `吸收存款及同业存放 261006708.24`, `拆入资金 300020250.00`, `长期借款 1860713816.09`, `卖出回购金融资产款项 475033835.62`;
- total/debt `23201159352.29`;
- `lease_scope="PRE_ADOPTION_NOT_RECOGNIZED"`, lease `0.00`; bonds `0.00`/`0.00`; dividends `6986645.96`.

### 2022

- report/PDF page `212`; `official_total_kind="PRINTED_TOTAL"`;
- components: `短期借款 52895851287.92`, `吸收存款及同业存放 219111069.61`, `其他应付款 1621102937.08`, `一年内到期的非流动负债 188387613.61`, `长期借款 30784241211.21`, `长期应付款 104644415.20`;
- official total `85813338534.63`;
- `lease_scope="POST_ADOPTION_FULL_LIABILITY"`, full lease `213791544.62`;
- short/long bonds `0.00`/`0.00`; dividends `5620664762.67`;
- ending debt `86027130079.25`.

Dividends are audit-only exclusions and are not added/subtracted from these official totals. 2022 debt arithmetic is official total plus full lease exactly once.

## 10. D&A bodies

Exact keys:

```text
source_member_key,source_document_hash,report_pages,pdf_pages,
combined_depreciation_field,combined_depreciation_amount,
combined_depreciation_includes,intangible_amortization_field,
intangible_amortization_amount,separate_use_right_addition,
separate_long_term_deferred_addition,ending_depreciation_and_amortization
```

Exact literals:

```text
combined_depreciation_field = depr_fa_coga_dpba
intangible_amortization_field = amort_intang_assets
2018/2019/2020 combined_depreciation_includes = [fixed_assets, investment_property]
2022 combined_depreciation_includes = [fixed_assets, investment_property, right_of_use_assets]
```

| Period | Pages report/PDF | Combined/includes | Intangible | ROU add | Deferred add | Ending D&A |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `20181231` | `[165]` / `[165]` | `2859799547.55`; fixed + investment property | `249550269.72` | `0.00` | `979454.55` | `3110329271.82` |
| `20191231` | `[169]` / `[170]` | `2977103353.04`; fixed + investment property | `215796437.95` | `0.00` | `1519448.66` | `3194419239.65` |
| `20201231` | `[175]` / `[176]` | `3377378887.04`; fixed + investment property | `211327446.74` | `0.00` | `0.00` | `3588706333.78` |
| `20221231` | `[194,195,177]` / same | `4597938791.84`; fixed + investment property + ROU | `372007224.51` | `0.00` | `27739400.53` | `4997685416.88` |

The 2022 page tuple preserves cash-flow combined/intangible evidence before the separate deferred-amortization note page. Separate ROU addition is always zero because the combined line already covers every source-supported ROU amount or the report predates adoption.

## 11. Frozen declaration hashes

At the fixed review instant:

| Period | Declaration hash |
| --- | --- |
| `20181231` | `sha256:51b1ae41791336ead0487148e721c530ff0de8b5a718d81d4b3d2fe63a55a575` |
| `20191231` | `sha256:0f52ca93b04c25d2135a584d853198ad2655f0cec31cc161867c22010927aa96` |
| `20201231` | `sha256:14143974d80d622721ecf78e3eae1e3467815366dc9bd90657774bd8473ee099` |
| `20221231` | `sha256:1124c88497385f9233df6c4f8c6ece397379d382a18d27aeacead31b82539aba` |

## 12. Outcome serialization

`GreeHistoricalFinancialDeclarationOutcome` exact-contains one declaration or one failure. Canonical body:

```python
{
  "type": "gree_historical_financial_declaration_outcome",
  "schema_version": 1,
  "declaration": None if absent else declaration.to_canonical_dict(),
  "failure": None if absent else failure.to_canonical_dict(),
}
```

Nested values are reconstructed before storage.

## 13. Failure precedence

| Priority | Predicate | Result |
| ---: | --- | --- |
| 1 | input exact type/reconstruction mismatch | `INPUT_MISMATCH` |
| 2 | SourceSnapshot verification failure | nested `SourceSnapshotFailureCode` |
| 3 | snapshot/tree/provenance mismatch | `SOURCE_SNAPSHOT_IDENTITY_MISMATCH` |
| 4 | unsupported period | `PERIOD_UNSUPPORTED` |
| 5 | metadata/report member/hash mismatch | `DOCUMENT_IDENTITY_MISMATCH` |
| 6 | reviewed-at mismatch or before acquisition | `REVIEW_TIME_INVALID` |
| 7 | valid 2021 source reveals incompatible debt scopes | `DEBT_SCOPE_INCOMPLETE` with conflict evidence |
| 8 | declaration construction/reconstruction/hash mismatch | `DECLARATION_RECONSTRUCTION_MISMATCH` |

No failure returns a declaration.

## 14. Exact write set

Create one Backtest worktree/branch stacked on PR #6 and add only:

- `packages/market-bundle-builder/src/crypto_quant_bundle_builder/gree_historical_financial_document_declarations_v1.py`;
- `tests/bundle_builder/providers/tushare/test_gree_historical_financial_document_declarations_v1.py`;
- `tests/architecture/test_gree_historical_financial_document_declarations_v1_boundary.py`.

No root export, lock or dependency change. Every file from base `64159f81fa6f831990690dd133587b96533a0362` remains byte-identical.

Architecture protection algorithm:

1. parse `git ls-tree -r -z BASE` into exact `(mode,type,blob,path)` entries;
2. require every base path exists and no deletion is staged/committed;
3. compare current index mode from `git ls-files -s` with the base mode; for `100644`/`100755`, compare `git hash-object -- path` with the base blob; for `120000`, hash `os.readlink(path).encode()` through `git hash-object --stdin` and compare that link-target blob; reject any other mode;
4. require `git diff --name-only BASE..HEAD` plus `git status --short --untracked-files=all` to contain only, and collectively exactly, the three allowed new paths;
5. the temporary Platform fixture link is outside the Backtest worktree and is created/removed by the orchestrator command, so it never enters this status/diff set.

## 15. Acceptance

1. four exact success declarations and frozen hashes;
2. 2021 exact conflict/failure hashes and no declaration;
3. exact source/member/document/review-time precedence;
4. exact unit/publication/debt/D&A bodies and arithmetic;
5. exact-class SourceSnapshot/UtcInstant/declaration/failure forgery rejection;
6. period unsupported before document inspection;
7. input/source-member order cannot alter result;
8. no `available_at`, Calendar, normalization, selection or formula output/import;
9. existing PRs #1–#6 files and 2023 identities unchanged;
10. focused + opt-in real artifact + Builder-wide + broad regression;
11. independent review before commit/push;
12. real publication writes four declarations plus one canonical 2021 conflict/failure manifest to a fresh artifact directory.

## 16. Validation commands

### Fixture authority

The focused test owns one `_configure(...)` helper:

- creates exactly six synthetic `RawSourceMember` values: the metadata member plus five report members;
- synthetic metadata bytes: `b'{"synthetic":"metadata"}'`;
- synthetic report bytes: `f"%PDF-1.5\\n{period}\\n".encode()` in period order;
- modes `0644`, acquisition instants `10..15`, fixed synthetic provenance;
- freezes/verifies the synthetic SourceSnapshot;
- monkeypatches only snapshot/tree/provenance identity, metadata/report content hashes, fixed review instant and period document source hashes;
- leaves every economic/page/unit/debt/D&A/conflict value unchanged;
- can reverse the six input members to prove SourceSnapshot-order noninterference.

The real opt-in helper rebuilds the exact persisted snapshot from `acquisition-receipt.json` and member bytes; it does not import another test module.

Focused mutation matrix exact-covers:

1. wrong input outer type and forged exact-class `UtcInstant`;
2. nested SourceSnapshot verification before source identity;
3. exact-string unsupported period with period preserved in failure;
4. metadata missing/hash mutation and each selected report missing/hash mutation;
5. review instant mismatch and review-before-acquisition;
6. 2021 conflict values/hash/short-bond/page mutation;
7. success money/unit/page/body/hash and false-flag coherent forgery;
8. injected declaration-build/reconstruction failure last.

Focused:

```bash
uv run --locked pytest -q \
  tests/bundle_builder/providers/tushare/test_gree_historical_financial_document_declarations_v1.py \
  tests/architecture/test_gree_historical_financial_document_declarations_v1_boundary.py
```

Real opt-in test variables:

```text
QB_FIN_HISTORY_REAL_SNAPSHOT_ROOT=/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/source-snapshots/000651.SZ/2018-2022/v3-candidate-01
```

Builder-wide:

```bash
uv run --locked pytest -q \
  tests/bundle_builder \
  tests/architecture/test_gree_historical_financial_document_declarations_v1_boundary.py
```

Create the candidate worktree directly under `/home/ygguo/agent-projs/ai-crypt/` as `/home/ygguo/agent-projs/ai-crypt/backtest-qb-fin-historical-declarations`; the sibling layout is required by the fixture command below.

Broad regression uses the exact temporary Platform fixture link:

```bash
parent_tests="$(dirname "$PWD")/tests"
test ! -e "$parent_tests"
mkdir -p "$parent_tests"
ln -s "$(dirname "$PWD")/platform/tests/contracts" "$parent_tests/contracts"
cleanup() { rm -f "$parent_tests/contracts"; rmdir "$parent_tests" 2>/dev/null || true; }
trap cleanup EXIT
```

Then exact node deselections:

```bash
uv run --locked pytest -q \
  --deselect tests/architecture/test_gree_2023_financial_document_declarations_v1_boundary.py::test_declaration_candidate_write_set_is_exact \
  --deselect tests/architecture/test_gree_2023_financial_statement_normalization_v1_boundary.py::test_normalization_candidate_write_set_is_exact \
  --deselect tests/architecture/test_gree_2023_financial_statement_trio_selection_v1_boundary.py::test_selection_candidate_write_set_is_exact \
  --deselect tests/architecture/test_g12a_tushare_financial_history_sentinel_v3_boundary.py::test_v3_write_set_is_exact
```

No broad `-k` exclusion.

## 17. Real candidate publication

Publication is an orchestrator one-off after review, candidate commit, adjacent/broad validation and stacked PR creation; it is not production-module I/O.

Target, which must not exist:

```text
/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/
  declarations/000651.SZ/2018-2022/v1-candidate-01
```

Exact files:

```text
20181231-declaration.json
20191231-declaration.json
20201231-declaration.json
20211231-failure.json
20221231-declaration.json
manifest.json
```

Every value file is canonical bytes from `to_canonical_dict()`. Manifest body:

```python
{
  "type": "gree_historical_financial_declaration_candidate_manifest",
  "schema_version": 1,
  "implementation_commit": exact_candidate_commit,
  "source_snapshot_id": "sha256:aee2ea78f3d51185110bc927836ce77ed51f590a9c7b4c26ee7ecd951cbf8d4b",
  "reviewed_at": UtcInstant(1787668131165592196),
  "declarations": {
    period: {
      "file": filename,
      "declaration_hash": declaration_hash,
      "file_sha256": canonical_file_sha256,
    }
    for period in ("20181231", "20191231", "20201231", "20221231")
  },
  "failures": {
    "20211231": {
      "file": "20211231-failure.json",
      "code": "DEBT_SCOPE_INCOMPLETE",
      "failure_hash": "sha256:2c5b90d0cbd89ccd584c0a33234d796ec9b039abe683ad897b7a5fe61cac5792",
      "conflict_hash": "sha256:8cb5ef55e745b6e3858eef5bb1806ebf22c9123490764e79e68f2928ffb66c6f",
      "file_sha256": canonical_file_sha256,
    }
  },
  "source_bounded": True,
  "revision_closure_complete": False,
  "decision_grade_eligible": False,
  "deployment_authorized": False,
}
```

Publish through a sibling temporary directory, canonical readback/hash checks and same-filesystem rename; no overwrite. Credential scan must pass even though no credential is required. Persisted files are mode `0600`.

## 18. Next handoff

After declaration candidate publication, historical normalization may proceed for 2018–2020 and 2022. The 2021 period must remain unavailable until competent source authority resolves the financing-scope conflict. Therefore five complete ROIC observations and formal strategy execution remain blocked.
