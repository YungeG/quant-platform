# QB-FIN-REV-01 — A-share financial-statement revision lineage v1

- **Status:** `CONTRACT_FROZEN_FOR_REVIEW / CURRENT_CAPTURE_UNAVAILABLE`
- **Owner:** Backtest Market Bundle Builder normalization
- **Availability prerequisite:** [`quality-bband-financial-availability-policy-v1.md`](quality-bband-financial-availability-policy-v1.md)
- **Consumer:** future `financial_statement_observations@1` Builder sentinel

## 1. Outcome

Preserve each immutable financial-statement row as one source-bound observation revision without claiming provider revision authority that Tushare does not supply.

V1 separates:

1. one economic statement fact;
2. one provider presentation basis;
3. one immutable captured version;
4. explicit source correction/supersession evidence;
5. point-in-time visibility;
6. later cross-presentation economic selection.

Builder normalizes and retains observations. It does not silently pick “latest”, discard adjustment rows, infer correction parents from row order or use `update_flag` as finality.

## 2. Authority

| ID | Authority | Requirement |
| --- | --- | --- |
| R1 | G11B point-in-time observation revision contract | One logical observation lineage needs one root, unique revisions, existing parents, no fork/cycle and strictly increasing availability. |
| R2 | Tushare statement documentation | `report_type` distinguishes current/adjusted/pre-adjustment presentations; `update_flag` is not an immutable revision or supersession ID. |
| R3 | Source matrix | Tushare exposes no provider revision ID, deletion record, correction history or terminal-set closure. |
| R4 | QB-FIN-AVAIL-01 | No revision becomes Strategy-visible without a defensible `available_at`. |
| R5 | Backtest architecture | Immutable old versions remain retained; future corrections cannot rewrite an earlier Decision Context. |

## 3. Identity layers

### Economic statement key

Stable across provider presentations and corrections:

```text
{
  instrument_id,
  statement_kind,
  report_period_end,
  period_kind,
  consolidation_scope,
  accounting_currency,
  accounting_unit
}
```

V1 statement kinds:

- `INCOME_STATEMENT`;
- `BALANCE_SHEET`;
- `CASH_FLOW_STATEMENT`.

V1 period kind is `ANNUAL`. Consolidation scope must be `CONSOLIDATED`. Separate-company, bank, insurance and securities-company layouts are unsupported until explicit field contracts exist.

### Presentation basis

Tushare `report_type` is mapped only as documented:

| Provider code | V1 presentation basis | Meaning |
| --- | --- | --- |
| `1` | `CURRENT_CONSOLIDATED` | Current/latest consolidated presentation returned by the provider. |
| `4` | `COMPARATIVE_ADJUSTED` | Adjusted comparative consolidated presentation. |
| `5` | `COMPARATIVE_PRE_ADJUSTMENT` | Comparative consolidated presentation before adjustment. |
| other | unsupported | Retained in raw SourceSnapshot but normalization fails for v1. |

`report_type=4` and `report_type=5` are parallel presentation evidence. If they share one availability instant, they cannot form a legal G11B parent/child revision chain because child availability would not be strictly later.

### Observation lineage key

```text
observation_lineage_key = canonical_sha256({
  economic_statement_key,
  presentation_basis,
})
```

This prevents adjusted/pre-adjustment rows from becoming a false fork in one revision chain.

### Captured revision identity

Tushare provides no revision identity, so Builder emits a clearly derived source-bound identity:

```text
revision_id = canonical_sha256({
  type="financial_statement_source_bounded_revision",
  schema_version=1,
  observation_lineage_key,
  source_snapshot_id,
  source_member_key,
  source_row_index,
  source_row_hash,
  official_document_hash,
  publication_evidence_hash,
  available_at_utc,
  report_type,
  comp_type,
  update_flag,
})
```

The output separately keeps:

```text
provider_revision_id = null
provider_revision_closure_complete = false
```

Builder-derived `revision_id` is immutable observation identity, not a claim that the provider recognizes that revision.

## 4. Proposed normalized value

```python
FinancialStatementObservationRevisionV1 = {
  schema_version,
  economic_statement_key,
  observation_lineage_key,
  instrument_id,
  statement_kind,
  report_period_end,
  period_kind,
  consolidation_scope,
  accounting_currency,
  accounting_unit,
  presentation_basis,
  announcement_date,
  actual_announcement_date,
  available_at_utc,
  report_type,
  comp_type,
  update_flag,
  source_snapshot_id,
  source_member_key,
  source_row_index,
  source_row_hash,
  official_document_hash,
  publication_evidence_hash,
  provider_revision_id=None,
  revision_id,
  supersedes_revision_id,
  line_items,
  line_items_hash,
  source_bounded=true,
  revision_closure_complete=false,
  decision_grade_eligible=false,
  deployment_authorized=false,
}
```

`line_items` contains only exact requested raw fields with explicit currency/unit/consolidation authority. Provider-computed ROIC, FCF, leverage and valuation ratios are excluded.

## 5. Supersession rules

`supersedes_revision_id` is `None` unless one of these accepted binders exists:

1. an official correction/restatement/withdrawal publication exact-identifies the prior official document and report period;
2. a later SourceSnapshot exact-retains both parent and child source bytes and an accepted source-specific binder proves the relationship;
3. a migration contract explicitly maps an old normalized revision to a successor without changing old bytes.

Forbidden inference:

- response row order;
- `update_flag`;
- larger/newer `request_id`;
- acquisition time;
- matching or differing numeric values alone;
- `report_type=4` automatically supersedes `5`;
- later `ann_date` automatically supersedes an earlier row;
- current API omission means withdrawal/deletion.

A child must have the same observation lineage key, exact economic context and a strictly later `available_at_utc` than its parent.

## 6. Duplicate and conflict treatment

Within one SourceSnapshot/member:

- exact duplicate rows collapse only for normalized identity, while raw bytes and duplicate counts remain retained;
- same source-row identity with different canonical content is `SOURCE_ROW_IDENTITY_CONFLICT`;
- same observation lineage/revision identity with different content is `REVISION_ID_CONFLICT`;
- multiple roots, missing parent, fork, cycle or multiple terminal are revision-chain failures;
- two non-identical rows with the same lineage and availability but no explicit supersession are `SIMULTANEOUS_REVISION_CONFLICT`;
- adjusted and pre-adjustment rows are not conflicts because their presentation bases and lineage keys differ.

Input order, JSON object order and batch/page shape cannot choose a winner.

## 7. Withdrawal and deletion

Tushare current interfaces provide no authoritative deletion/tombstone record. V1 therefore has no successful tombstone payload.

An official withdrawal/cancellation document:

- is retained as correction evidence;
- blocks the affected economic statement lineage with `WITHDRAWAL_SEMANTICS_UNSUPPORTED`;
- does not create a zero-valued statement;
- does not expose the withdrawn predecessor as current after the withdrawal becomes available;
- requires a later contract before Strategy features can resume from a replacement.

## 8. Terminal-set and closure boundary

V1 can prove only exact closure of the finite supplied SourceSnapshot members. It cannot prove:

- all provider revisions were ever returned;
- an omitted row was deleted;
- no future correction will arrive;
- all official correction announcements were captured;
- one report period has reached global finality.

Therefore every normalized observation retains:

```text
source_bounded = true
revision_closure_complete = false
decision_grade_eligible = false
deployment_authorized = false
```

A future terminal-set declaration must bind a competent official record cutoff, exact enumerated announcement members, their acquisition receipts and a closure-evidence availability time.

## 9. Cross-presentation economic selection

Revision-chain resolution operates within one presentation basis. Selecting one economic value across:

- `CURRENT_CONSOLIDATED`;
- `COMPARATIVE_ADJUSTED`;
- `COMPARATIVE_PRE_ADJUSTMENT`

is a separate Strategy Feature Manifest responsibility and is **not** implemented by QB-FIN-REV-01.

The later selector must, at minimum:

- use only revisions visible at the Decision instant;
- prefer neither row order nor `update_flag`;
- state whether adjusted comparatives replace originally filed values;
- fail if multiple eligible presentations remain economically ambiguous;
- include chosen revision/document/line-item hashes in feature evidence.

Until that selector is frozen, normalized statement revisions cannot produce ROIC/FCF/leverage features.

## 10. Failure precedence

| Priority | Condition | Proposed code |
| ---: | --- | --- |
| 1 | exact input/schema/type mismatch | `INPUT_MISMATCH` |
| 2 | SourceSnapshot/member/request identity mismatch | `SOURCE_MEMBER_MISMATCH` |
| 3 | unsupported statement kind/company layout/period/scope/unit | `STATEMENT_SCOPE_UNSUPPORTED` |
| 4 | provider response or row shape invalid | `SOURCE_ROW_INVALID` |
| 5 | official document/publication evidence mismatch | `DOCUMENT_BINDING_MISMATCH` |
| 6 | unresolved availability | `AVAILABILITY_UNRESOLVED` |
| 7 | unsupported `report_type`/`comp_type` | `PRESENTATION_UNSUPPORTED` |
| 8 | same source identity with conflicting content | `SOURCE_ROW_IDENTITY_CONFLICT` |
| 9 | same revision identity with conflicting content | `REVISION_ID_CONFLICT` |
| 10 | missing parent | `REVISION_PARENT_MISSING` |
| 11 | fork/cycle/multiple root/terminal | `REVISION_CHAIN_CONFLICT` |
| 12 | economic/lineage context changes within chain | `REVISION_CONTEXT_MISMATCH` |
| 13 | child availability not strictly later | `REVISION_AVAILABILITY_REGRESSION` |
| 14 | simultaneous non-identical revision without binder | `SIMULTANEOUS_REVISION_CONFLICT` |
| 15 | official withdrawal/cancellation | `WITHDRAWAL_SEMANTICS_UNSUPPORTED` |
| 16 | output reconstruction/hash mismatch | `RESULT_RECONSTRUCTION_MISMATCH` |

One failure returns no partial normalized revision or Bundle publication.

## 11. Current sentinel decision

PR [`YungeG/quant-backtest#1`](https://github.com/YungeG/quant-backtest/pull/1) is an acquisition tool candidate, not an executed credentialed capture. No real Tushare statement response rows or accepted availability evidence are currently retained.

Therefore:

```text
normalized revisions = unavailable
revision chain = unavailable
feature selection = unavailable
```

The PR remains valuable because it freezes exact raw fields, row preservation, source identity, PDF binding and failure behavior needed by the future Builder.

## 12. Acceptance

A future pure Builder sentinel must prove:

1. deterministic economic/lineage/revision identities;
2. exact `report_type` 1/4/5 mapping and rejection of unsupported types;
3. duplicate collapse without raw evidence loss;
4. presentation variants do not create revision-chain forks;
5. explicit later correction parent/child success;
6. inferred parent from update flag/order/date/value fails;
7. missing parent, fork, cycle, context drift, availability regression and simultaneous conflict fail at precedence;
8. provider revision and closure fields remain null/false;
9. withdrawal produces no zero statement or stale current value;
10. input order/batch/page changes do not alter output hashes;
11. no feature calculation, cross-presentation selection, Runtime import, network or filesystem I/O;
12. existing PR #1 and SourceSnapshot identities remain unchanged.

## 13. Readiness decision

The revision-lineage contract is frozen for review. Builder implementation remains blocked by:

- PR #1 acceptance and an executed SourceSnapshot;
- accepted availability evidence/policy output;
- exact accounting unit and ordinary-industrial field mapping;
- a cross-presentation feature-selection contract.
