# QB-FIN-SELECT-IMPL-01 — Gree 2023 statement-trio selection packet

- **Status:** `STACKED_CANDIDATE_PUBLISHED / NOT_ACCEPTED`
- **Owner:** Backtest Market Bundle Builder
- **Base:** stacked PR #4 commit `fa58e68d7b51ee5517e5a14c87c3590d1bda2976`
- **Candidate:** Backtest PR [#5](https://github.com/YungeG/quant-backtest/pull/5), commit `5338d8046fa0f304d4a9590989c59ceffb51270b`
- **Input observation set:** `sha256:632206f85bcff71dbcccfd20a3593e14fb895b33bd138ac25bbf9b947e4a4a7c`
- **Policy key:** `qb-fin-select-01.gree-fixed-current-consolidated.v1`

## 1. Outcome

At one caller-supplied exact Decision instant, select the exact Gree 2023 income/balance/cash-flow trio already normalized by QB-FIN-NORM-IMPL-01.

This is a fixed-scope source-bounded sentinel. It proves visibility and coherent trio binding for the one real observation set. It does not implement generic revision-chain or comparative-adjustment resolution and does not calculate any financial ratio, feature, rank, target, Backtest request or grade.

## 2. Minimal seam

```python
class Gree2023FinancialTrioSelectionFailureCode(str, Enum):
    INPUT_MISMATCH = "INPUT_MISMATCH"
    OBSERVATION_SET_MISMATCH = "OBSERVATION_SET_MISMATCH"
    NOT_VISIBLE = "NOT_VISIBLE"
    RESULT_RECONSTRUCTION_MISMATCH = "RESULT_RECONSTRUCTION_MISMATCH"

@dataclass(frozen=True, slots=True)
class Gree2023FinancialTrioSelectionFailure:
    code: Gree2023FinancialTrioSelectionFailureCode

@dataclass(frozen=True, slots=True)
class Gree2023FinancialStatementTrioSelectionV1: ...

@dataclass(frozen=True, slots=True)
class Gree2023FinancialTrioSelectionOutcome:
    selection: Gree2023FinancialStatementTrioSelectionV1 | None
    failure: Gree2023FinancialTrioSelectionFailure | None

def select_gree_2023_financial_statement_trio_v1(
    observation_set: Gree2023FinancialStatementObservationSetV1,
    decision_instant: UtcInstant,
) -> Gree2023FinancialTrioSelectionOutcome: ...
```

Both inputs are exact in-memory values. No filesystem, network, environment, clock, provider, PDF, Runtime, Trading or Market Data access.

## 3. Fixed input authority

The selector exact-reconstructs the PR #4 observation set and requires:

- source snapshot `sha256:dec0abb1828f8b87256347e72b6ccfe2f84a2ca13f36aa1415c9a53e96a0c7d5`;
- declaration `sha256:59e09eb542a6e2ec480a7b8ed322d9ae9106416460f0999216fd5564f7278007`;
- observation set `sha256:632206f85bcff71dbcccfd20a3593e14fb895b33bd138ac25bbf9b947e4a4a7c`;
- revisions, in statement order:
  1. income `sha256:8957590f45f32ed9b285e940f2fa0c0524cb28377e86c745ab39aa3875ba63e8`;
  2. balance `sha256:3e64ee623ca3676f1ec10daf56588dceabdd77a41ba0419d4c9010241313f45d`;
  3. cash flow `sha256:71f4428e79d3bd7638cc9c1d98c1471f9802e9a90d25f7fa06b739bc57f0f986`.

Every chosen revision must remain:

- `instrument_id="xshe:000651"`;
- `report_period_end="20231231"`;
- `period_kind="ANNUAL"`;
- `presentation_basis="CURRENT_CONSOLIDATED"`;
- `provider_revision_id=None` and `supersedes_revision_id=None`;
- source-bounded `true`;
- revision-closure/decision-grade/deployment `false`.

This candidate does not claim comparative-adjustment coverage or provider revision closure.

## 4. Visibility and coherence

The exact visibility boundary is:

```text
UtcInstant(1714959000000000000)
= 2024-05-06T01:30:00Z
```

- `decision_instant < available_at_utc` returns `NOT_VISIBLE` and no partial result.
- `decision_instant >= available_at_utc` selects all three exact revisions.

The constructor recomputes and requires one coherent trio:

- statement kinds exactly `(INCOME, BALANCE, CASH_FLOW)`;
- same Instrument, period, consolidation scope, currency and unit;
- same `available_at_utc`;
- same official document hash `sha256:32ebc475a2291ce4f1b5c1a9f9da55227e03192f07e75041e976c29d213ec8aa`;
- same publication-confirmation hash `sha256:a78a67865a7ea989c4fd8b053fad1aa75f36d22c10d14387800ff16b698dbc60`;
- same source snapshot/content-tree/provenance family;
- no active pre-adjustment presentation;
- all normalized line-item evidence remains exact under the PR #4 constructors.

Source-snapshot family hash:

```text
sha256:0d94a3298739339e6b54315f3193eba722604f0c354246abf06046c10dc6b6b9
```

It is `canonical_sha256` over exactly:

```python
{
  "source_snapshot_id": observation_set.source_snapshot_id,
  "source_content_tree_hash": revisions[0].source_content_tree_hash,
  "source_provenance_hash": revisions[0].source_provenance_hash,
}
```

## 5. Request identity

Request body:

```python
{
  "type": "gree_2023_financial_statement_trio_selection_request",
  "schema_version": 1,
  "policy_key": "qb-fin-select-01.gree-fixed-current-consolidated.v1",
  "decision_instant": decision_instant,
  "instrument_id": "xshe:000651",
  "report_period_end": "20231231",
  "required_statement_kinds": ("INCOME", "BALANCE", "CASH_FLOW"),
  "observation_set_hash": observation_set.observation_set_hash,
  "source_bounded_only": True,
}
```

`request_hash = canonical_sha256(request body)`.

At the exact first-visible instant, the frozen real request hash is:

```text
sha256:6c8e38908cbc77f0ba4bfac62d8381235489e667b592fd2702fa37833e49cc7d
```

## 6. Result identity

Exact selection fields:

```python
@dataclass(frozen=True, slots=True)
class Gree2023FinancialStatementTrioSelectionV1:
    schema_version: int
    policy_key: str
    request_hash: str
    decision_instant: UtcInstant
    instrument_id: str
    report_period_end: str
    observation_set: Gree2023FinancialStatementObservationSetV1
    chosen_revision_ids: tuple[str, ...]
    visible_candidate_revision_ids: tuple[str, ...]
    rejected_pre_adjustment_revision_ids: tuple[str, ...]
    maximum_available_at: UtcInstant
    official_document_hash: str
    publication_confirmation_hash: str
    source_snapshot_family_hash: str
    source_bounded: bool
    revision_closure_complete: bool
    decision_grade_eligible: bool
    deployment_authorized: bool
    selection_hash: str
```

Exact selection body (without `selection_hash`):

```python
{
  "type": "gree_2023_financial_statement_trio_selection",
  "schema_version": self.schema_version,
  "policy_key": self.policy_key,
  "request_hash": self.request_hash,
  "decision_instant": self.decision_instant,
  "instrument_id": self.instrument_id,
  "report_period_end": self.report_period_end,
  "observation_set": self.observation_set.to_canonical_dict(),
  "chosen_revision_ids": self.chosen_revision_ids,
  "visible_candidate_revision_ids": self.visible_candidate_revision_ids,
  "rejected_pre_adjustment_revision_ids": self.rejected_pre_adjustment_revision_ids,
  "maximum_available_at": self.maximum_available_at,
  "official_document_hash": self.official_document_hash,
  "publication_confirmation_hash": self.publication_confirmation_hash,
  "source_snapshot_family_hash": self.source_snapshot_family_hash,
  "source_bounded": self.source_bounded,
  "revision_closure_complete": self.revision_closure_complete,
  "decision_grade_eligible": self.decision_grade_eligible,
  "deployment_authorized": self.deployment_authorized,
}
```

`to_canonical_dict()` adds `"selection_hash": self.selection_hash`. The constructor reconstructs the embedded observation set from its exact dataclass fields, recomputes request/visibility/coherence/chosen IDs and then computes `selection_hash = canonical_sha256(body)`.

Exact failure body and serialization:

```python
{
  "type": "gree_2023_financial_trio_selection_failure",
  "schema_version": 1,
  "code": self.code.value,
}
```

`failure_hash = canonical_sha256(failure body)` and `to_canonical_dict()` adds `failure_hash`.

Exact outcome serialization:

```python
{
  "type": "gree_2023_financial_trio_selection_outcome",
  "schema_version": 1,
  "selection": None if self.selection is None else self.selection.to_canonical_dict(),
  "failure": None if self.failure is None else self.failure.to_canonical_dict(),
}
```

The outcome constructor exact-requires one and only one of `selection` or `failure` and reconstructs the nested value before storing it.

At the exact first-visible instant, the frozen real selection hash is:

```text
sha256:34d09c7649143ee784f95f25873dd462ee56fc37cae91fa8bc7a604ef37f890c
```

A later Decision instant keeps the same chosen revisions but intentionally changes request and selection identity.

## 7. Failure precedence

| Priority | Predicate | Code |
| ---: | --- | --- |
| 1 | either input is not the exact required type | `INPUT_MISMATCH` |
| 2 | observation-set reconstruction, hash, source binding, statement order, presentation, document/publication or source-family coherence fails | `OBSERVATION_SET_MISMATCH` |
| 3 | Decision instant precedes complete trio availability | `NOT_VISIBLE` |
| 4 | result construction/reconstruction/hash fails | `RESULT_RECONSTRUCTION_MISMATCH` |

One failure emits no partial selection or chosen revision. Because the PR #4 observation-set and revision constructors already exact-enforce all fixed trio coherence, no valid reconstructed input can reach a separate coherence failure. Direct forged result construction raises `TypeError`/`ValueError`; operation-level fixed-set mutations map to priority 2.

Generic coherence, chain conflict, parent, adjustment and ambiguity codes remain reserved for a later general QB-FIN-SELECT policy; this fixed sentinel must not pretend those cases were exercised.

## 8. Exact write set

Create one Backtest worktree/branch stacked on PR #4 and change only:

- `packages/market-bundle-builder/src/crypto_quant_bundle_builder/gree_2023_financial_statement_trio_selection_v1.py`;
- `tests/bundle_builder/providers/tushare/test_gree_2023_financial_statement_trio_selection_v1.py`;
- `tests/architecture/test_gree_2023_financial_statement_trio_selection_v1_boundary.py`.

No root export. PRs #1–#4 files, locks and all Runtime/Trading/Market Data sources remain byte-identical.

## 9. Fixture and test authority

The focused test file owns one `_exact_observation_set()` helper that directly constructs the exact PR #4 revision and observation-set dataclasses from frozen values. It does not monkeypatch production constants and does not invent an alternate observation set.

The opt-in real test uses the existing environment variables:

```text
QB_FIN_REAL_SNAPSHOT_ROOT
QB_FIN_REAL_DECLARATION_ROOT
```

Test-local readback helpers rebuild the persisted SourceSnapshot and declaration, call `normalize_gree_2023_financial_statements_v1(...)`, assert the exact PR #4 observation-set hash, then call the selector. No test imports another test module and no production code performs filesystem access.

Focused mapping:

| Test | Required proof |
| --- | --- |
| `test_first_visible_selection_pins_golden` | exact request hash, selection hash, chosen IDs, full embedded observation set and false authority flags |
| `test_one_nanosecond_before_is_not_visible` | `NOT_VISIBLE`, no partial selection |
| `test_later_decision_changes_request_and_selection_only` | chosen IDs/evidence unchanged; request and selection hashes changed |
| `test_observation_set_forgery_maps_to_mismatch` | forged set/nested revision/hash maps to `OBSERVATION_SET_MISMATCH` |
| `test_selection_constructor_rejects_coherent_forgery` | recomputed chosen/request/selection hashes cannot authorize changed fields |
| `test_input_and_result_failure_precedence` | exact input mismatch first; injected result-build failure maps last |
| `test_real_normalization_to_selection_when_explicitly_configured` | persisted source + declaration → PR #4 normalization → frozen selection golden |
| architecture boundary tests | exact write set; no forbidden imports/I/O; PRs #1–#4 protected bytes |

Focused command:

```text
uv run --locked pytest -q \
  tests/bundle_builder/providers/tushare/test_gree_2023_financial_statement_trio_selection_v1.py \
  tests/architecture/test_gree_2023_financial_statement_trio_selection_v1_boundary.py
```

## 10. Acceptance

1. exact first-visible direct-construction and opt-in real success with frozen request/selection hashes;
2. one-nanosecond-before visibility failure with no partial result;
3. later Decision instant keeps chosen IDs but changes request/selection hashes;
4. observation-set hash and nested revision forgery map to the frozen priority-2 failure;
5. coherent chosen-ID/request-hash/selection-hash result forgery rejection;
6. exact statement order, presentation, document/publication and source-family evidence;
7. empty rejected-pre-adjustment evidence for this current-only fixed set;
8. source-bounded true and closure/grade/deployment exact false;
9. deterministic reconstruction and canonical bytes for failure, selection and outcome;
10. no formula calculation, provider I/O or Runtime/Trading/Market Data import;
11. focused, real opt-in, Builder-wide and broad regression;
12. independent review before push.

## 11. Validation commands

Builder-wide:

```text
uv run --locked pytest -q \
  tests/bundle_builder \
  tests/architecture/test_gree_2023_financial_statement_trio_selection_v1_boundary.py
```

The sibling Backtest worktree must temporarily expose the Platform consumer fixture expected by inherited Runtime tests, without writing into either repository:

```bash
parent_tests="$(dirname "$PWD")/tests"
test ! -e "$parent_tests"
mkdir -p "$parent_tests"
ln -s "$(dirname "$PWD")/platform/tests/contracts" "$parent_tests/contracts"
cleanup() { rm -f "$parent_tests/contracts"; rmdir "$parent_tests" 2>/dev/null || true; }
trap cleanup EXIT
```

Broad regression exact command:

```bash
uv run --locked pytest -q \
  --deselect tests/architecture/test_gree_2023_financial_document_declarations_v1_boundary.py::test_declaration_candidate_write_set_is_exact \
  --deselect tests/architecture/test_gree_2023_financial_statement_normalization_v1_boundary.py::test_normalization_candidate_write_set_is_exact
```

Those two inherited predecessor guards intentionally assert that no stacked successor files exist. All other tests run. The selector boundary separately proves PRs #1–#4 files are byte-identical and the selector write set is exact. Record the two deselections explicitly; do not add a broader `-k` exclusion.

## 12. Implementation evidence

Stacked Backtest PR [#5](https://github.com/YungeG/quant-backtest/pull/5):

- base: `research/qb-fin-normalization-v1` / PR #4;
- commit: `5338d8046fa0f304d4a9590989c59ceffb51270b`;
- focused: `8 passed, 1 skipped`;
- real opt-in normalization-to-selection: `1 passed`;
- Builder-wide: `352 passed, 3 skipped`;
- broad regression: `2533 passed, 3 skipped, 2 deselected`; only the exact PR #3/#4 predecessor write-set guards were deselected;
- independent review: `ACCEPTED`, no remaining findings;
- LSP/lens: clean.

Published real fixed-scope candidate:

```text
/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/
  trio-selections/000651.SZ/20231231/v1-candidate-01
```

- request hash: `sha256:6c8e38908cbc77f0ba4bfac62d8381235489e667b592fd2702fa37833e49cc7d`;
- selection hash: `sha256:34d09c7649143ee784f95f25873dd462ee56fc37cae91fa8bc7a604ef37f890c`;
- selection file SHA-256: `sha256:b07c00e6608b4c6b95dfdce830593d304de743dd39dffffe2eb9a5c033f6c74a`;
- canonical readback, repeated selection and credential-exclusion checks passed;
- source-bounded `true`; closure/decision-grade/deployment remain `false`.

## 13. Next handoff

After candidate acceptance, the selector proves only one visible annual trio. Formula research still requires six annual balance endpoints and five annual trios. Generic comparative-adjustment/chain resolution requires a separate policy version and source evidence that actually contains those cases.
