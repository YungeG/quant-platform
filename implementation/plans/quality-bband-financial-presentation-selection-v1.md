# QB-FIN-SELECT-01 — Financial presentation selection v1

- **Status:** `CONTRACT_FROZEN / FIXED_SCOPE_INPUT_EXISTS / GENERAL_SELECTOR_NOT_IMPLEMENTED`
- **Owner:** Strategy Feature Manifest / pure financial feature-input selection
- **Fixed-scope packet:** [`quality-bband-financial-presentation-selection-implementation-v1.md`](quality-bband-financial-presentation-selection-implementation-v1.md)
- **Revision prerequisite:** [`quality-bband-financial-revision-lineage-v1.md`](quality-bband-financial-revision-lineage-v1.md)
- **Availability prerequisite:** [`quality-bband-financial-availability-policy-v1.md`](quality-bband-financial-availability-policy-v1.md)

## 1. Outcome

At one exact Decision instant, select one coherent income/balance-sheet/cash-flow input trio for one issuer and annual report period from all source-bounded statement presentation revisions then legally visible.

This contract selects feature inputs only. It does not calculate ROIC, FCF, leverage, valuation, quality rank, target weights or trades.

## 2. Inputs

One request exact-binds:

- `decision_instant`;
- exact Instrument;
- annual `report_period_end`;
- required statement kinds `(INCOME_STATEMENT, BALANCE_SHEET, CASH_FLOW_STATEMENT)`;
- accepted revision-lineage policy/version;
- immutable visible `FinancialStatementObservationRevisionV1` tuple;
- requested source/grade limitations.

Only revisions with `available_at <= decision_instant` are visible. Future corrections and conflicts are discarded before validation so they cannot change an earlier selection/result hash.

## 3. Per-lineage revision resolution

For each `(economic_statement_key, presentation_basis)` lineage:

1. collapse exact duplicate revisions;
2. validate one root, unique IDs, existing parents, no fork/cycle/disconnected root and strictly increasing availability;
3. select its unique visible terminal revision;
4. preserve all visible candidate/rejected revision hashes in selection evidence.

QB-FIN-SELECT-01 does not repair an invalid revision chain or infer missing parents.

## 4. Presentation eligibility

| Presentation | Feature-input eligibility | Treatment |
| --- | --- | --- |
| `CURRENT_CONSOLIDATED` | eligible | Original/current consolidated presentation. |
| `COMPARATIVE_ADJUSTED` | eligible | Later adjusted comparative presentation for the same economic period. |
| `COMPARATIVE_PRE_ADJUSTMENT` | audit-only | Retained to show the prior comparison basis; never selected as active feature input. |

`update_flag`, response order, row index and provider request ID do not affect eligibility or rank.

## 5. Economic-view selection

For one exact economic statement key:

1. retain visible terminal revisions from eligible presentation bases;
2. if none remain, fail;
3. find the maximum complete `available_at` among eligible candidates;
4. retain only candidates at that maximum instant;
5. collapse candidates only when their exact economic line-item hash, official document hash and publication-evidence hash are equal;
6. require one unique remaining candidate;
7. select it.

Consequences:

- a later `COMPARATIVE_ADJUSTED` observation can replace an earlier current filing for feature use;
- a later corrected `CURRENT_CONSOLIDATED` observation can replace an earlier adjusted comparison;
- presentation names alone never outrank time;
- non-identical current/adjusted candidates at the same availability instant are ambiguous and fail;
- an adjusted and pre-adjustment pair at one instant selects only the adjusted candidate because pre-adjustment is audit-only;
- a future adjustment cannot alter a prior Decision result.

Selection is a point-in-time feature-view policy, not a claim that Tushare supplied an explicit cross-presentation `supersedes` relation.

## 6. Statement-trio coherence

After selecting one candidate for each required statement kind, v1 requires:

- same Instrument and annual period;
- same consolidation scope, accounting currency and accounting unit;
- same official document hash;
- same publication-evidence hash;
- same complete `available_at`;
- source members belong to the same accepted SourceSnapshot family;
- no chosen statement is audit-only, withdrawn, unsupported or missing a required line item.

V1 does not mix an income statement from one filing with balance/cash-flow statements from another. A future explicit partial-correction binder may relax this, but must carry official correction scope and a new policy version.

## 7. Proposed result

```python
FinancialStatementTrioSelectionV1 = {
  schema_version,
  request_hash,
  decision_instant,
  instrument_id,
  report_period_end,
  chosen_income_revision,
  chosen_balance_revision,
  chosen_cashflow_revision,
  chosen_revision_hashes,
  visible_candidate_revision_hashes,
  rejected_pre_adjustment_revision_hashes,
  maximum_available_at,
  official_document_hash,
  publication_evidence_hash,
  source_snapshot_family_hash,
  source_bounded=true,
  revision_closure_complete=false,
  decision_grade_eligible=false,
  deployment_authorized=false,
  selection_hash,
}
```

The constructor recomputes visibility, lineage terminals, economic-view choices, trio coherence and all hashes. Callers cannot supply chosen hashes without the full embedded evidence.

## 8. Failure precedence

| Priority | Condition | Proposed code |
| ---: | --- | --- |
| 1 | request/value exact type/schema mismatch | `INPUT_MISMATCH` |
| 2 | Instrument/period/kind/scope mismatch | `REQUEST_SCOPE_MISMATCH` |
| 3 | revision identity/content conflict | `REVISION_ID_CONFLICT` |
| 4 | missing parent | `REVISION_PARENT_MISSING` |
| 5 | fork/cycle/multiple root/terminal | `REVISION_CHAIN_CONFLICT` |
| 6 | context changes inside lineage | `REVISION_CONTEXT_MISMATCH` |
| 7 | child availability regression | `REVISION_AVAILABILITY_REGRESSION` |
| 8 | no visible eligible presentation | `ELIGIBLE_PRESENTATION_MISSING` |
| 9 | multiple latest non-identical candidates | `PRESENTATION_AMBIGUOUS` |
| 10 | one required statement kind missing | `STATEMENT_KIND_MISSING` |
| 11 | chosen trio document/publication/availability mismatch | `STATEMENT_TRIO_COHERENCE_MISMATCH` |
| 12 | required line item/unit/currency missing | `FEATURE_INPUT_INCOMPLETE` |
| 13 | result reconstruction/hash mismatch | `RESULT_RECONSTRUCTION_MISMATCH` |

One failure returns no partial trio or chosen statement.

## 9. Noninterference and identity

- unauthorized Instrument/period revisions are removed before visibility and revision checks;
- revisions after the Decision instant cannot affect request/result/failure identity;
- exact duplicate input order and batch/page shape cannot alter selection;
- audit-only pre-adjustment values enter evidence hashes but never active feature values;
- no filesystem, network, provider query, current clock, account state or Strategy callback is allowed;
- no value from a withdrawn or unresolved lineage becomes zero/default input.

## 10. Five-year feature boundary

This contract selects one annual trio. A later `QualityFeatureManifestV1` must request five exact annual periods and prove:

- the required five period-end values are present;
- each period's trio was selected at the same Strategy Decision instant;
- no future filing entered an earlier period's selection;
- missing years do not get forward-filled or replaced with TTM/vendor ratios;
- formula inputs bind the exact trio selection hashes.

The feature manifest, not this selector, decides ROIC/ROCE/FCF/leverage formulas.

## 11. Current decision

A real source-bounded current-consolidated trio now exists in observation set `sha256:632206f85bcff71dbcccfd20a3593e14fb895b33bd138ac25bbf9b947e4a4a7c`, published by stacked Backtest PR #4. It is one issuer/one period, provider-revision-closure-incomplete and unaccepted.

```text
fixed current-only trio selection candidate = implementable
comparative/adjustment chain policy = unexercised
five-year quality features = unavailable
strategy execution = blocked
```

## 12. Acceptance

A future pure selector implementation must prove:

1. predecessor selected before a later adjustment becomes visible;
2. later adjusted/current candidate selected after visibility;
3. pre-adjustment rows are audit-only;
4. same-instant non-identical current/adjusted candidates fail;
5. future conflicts do not alter prior selection/hash;
6. revision-chain failures preserve frozen precedence;
7. income/balance/cash-flow from different documents or availability instants fail;
8. exact duplicates/input order/batch shape do not alter output;
9. missing kind/item/unit returns no partial trio;
10. result constructor rejects forged chosen revisions/hashes;
11. no feature calculation or provider/Runtime I/O;
12. existing SourceSnapshot, availability and revision identities remain unchanged.

## 13. Readiness decision

The general presentation-selection contract remains frozen and unimplemented. QB-FIN-SELECT-IMPL-01 is ready for a minimal stacked fixed-scope candidate over PR #4; it must not claim generic comparative-adjustment or revision-chain coverage. Five-year formula execution remains blocked by missing annual periods and accepted stack authority.
