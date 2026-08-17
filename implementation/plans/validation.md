# Strategy Validation implementation plan

- **Normative contract:** [Integration v1 §5, §7, §9](../../overall/integration-v1.md#5-validation-integration-sv-thin-01)
- **Mutable status authority:** [Roadmap §2](../roadmap.md#2-status-registry)
- **Module design:** [Strategy Validation design](../../strategy-validation/design.md)

Validation is one deep decision module plus one shared sample-ledger module. It owns reservation semantics, authoritative sample snapshots, candidate admission, OOS interpretation, and the report. It does not select candidates, verify Backtest economics, or recommend deployment.

## Execution DAG

```text
SV-00A-core + BT-PORT + Research wires ─→ SV-CORE-01
PF-CORE-01 + SV-00A-core ───────────────→ SV-LEDGER-01
SV-CORE-01 + SV-LEDGER-01 + PF-CORE-01 + BT-PORT-01
                                      └─→ SV-SHELL-01
SV-SHELL-01 + RP-THIN-02 + P00-SEAM-01 ─→ SV-THIN-01
```

`SV-LEDGER-01` is separated because Research and Validation both need one authoritative reservation interface. Removing it would duplicate event-id, owner-log, cutoff, and reconstruction rules across callers.

## `SV-CORE-01` — implemented admission, OOS, and report core

### Caller-visible result

```text
build_validation_plan(candidate_ref, ledger_snapshot_ref, policy) -> ValidationPlan
assess_admission(plan, candidate_graph, sample_integrity) -> CaseResult
assess_oos(plan, completed_or_terminal, analysis_or_failure) -> CaseResult
aggregate_validation_report(plan, case_results) -> ValidationReport | no report
```

The core consumes immutable values only. It performs no publication, checkpoint acquisition, sample append, Backtest call, or Promotion recommendation.

### Frozen invariants

1. The Plan carries candidate identity once and is frozen before OOS evidence is read.
2. Candidate, family, manifest, selection, Trial, publication, and analysis links resolve through declared refs; cross-plan/cross-case duplicates fail closed.
3. Admission uses the authoritative supplied snapshot/assessment and required reservation coverage.
4. OOS analysis must match the case context, accepted grade/profile, source publication, and source execution-result hash.
5. Valid missing metrics or insufficient trade count are `INCONCLUSIVE`, never zero.
6. Required case types exact-cover the Plan. Failed execution produces no Report.

### Failure precedence

1. `VALIDATION_PLAN_INVALID`
2. `CANDIDATE_PROVENANCE_INVALID`
3. `SAMPLE_LEDGER_CONFLICT`
4. `SAMPLE_RESERVATION_COVERAGE_MISSING`
5. `HOLDOUT_CONTAMINATED`
6. `BACKTEST_TERMINAL_BLOCKED`
7. `BACKTEST_TERMINAL_FAILED`
8. `BACKTEST_TERMINAL_CANCELLED`
9. `ANALYSIS_LINK_INVALID`
10. `RESULT_GRADE_UNACCEPTED`
11. `METRIC_MISSING_OR_INSUFFICIENT`
12. `CASE_COVER_INVALID`

### Existing implementation evidence

- Production: `strategy-validation/src/crypto_quant_validation/integration.py`
- Frozen sample semantics: `strategy-validation/src/crypto_quant_validation/sample_consumption.py`
- Tests: `strategy-validation/tests/test_validation_core.py`

```bash
uvx --python 3.13.5 --from pytest==8.4.2 \
  --with ./backtest/packages/trading-domain \
  --with-editable ./foundation \
  --with-editable ./strategy-validation \
  pytest -q -p no:cacheprovider strategy-validation/tests/test_validation_core.py
```

The suite fixes adverse completed evidence (`-0.1`, one trade, development → rejected), the terminal matrix, inconclusive missing/insufficient metrics, deterministic case cover, and forged candidate/case/profile/publication/execution-hash rejection. The core imports neither Foundation nor Backtest runtime.

## `SV-LEDGER-01` — authoritative sample-consumption ledger

### Outcome

Research and Validation use one interface to publish append-before-read reservations, freeze an authoritative ledger cutoff, reconstruct its verified prefix, and publish an integrity assessment. Callers do not derive event ids, manipulate Foundation entries, or reinterpret overlap semantics.

### Inputs

- completed `PF-CORE-01` store;
- Frozen `SampleConsumptionRecord`, `build_snapshot()`, and `assess_untouched_holdout()` semantics;
- Integration v1 `SampleConsumptionAppend@1`, snapshot, assessment, event-id, producer, and owner-log rules.

### Module interface

```text
reserve(record, producer_ref) -> LogEntryRef
freeze_snapshot() -> SampleConsumptionLedgerSnapshotRef
assess_holdout(snapshot_ref, holdout) -> SampleIntegrityAssessmentRef
```

This is a real shared interface: TrialDeclaration and SelectionDeclaration producers call `reserve()`, while Validation additionally calls all three operations. It consumes the concrete Foundation interface directly; there is no pass-through storage adapter.

### Invariants

1. `reserve()` embeds the canonical six-field record and exact producer ref in one `SampleConsumptionAppend@1` Envelope.
2. `consumer_id` and event id are derived exactly from canonical producer/revision/interval/purpose wires.
3. The append to `validation.sample-consumption.v1` succeeds before the corresponding read. Failure or conflict means no read.
4. Exact replay returns the first entry. Same event id with different bytes is `LOG_CONFLICT`.
5. `record.consumed_at <= receipt.accepted_at`; violation fails closed and cannot authorize a read.
6. `freeze_snapshot()` publishes one snapshot binding one Foundation-assigned checkpoint; it never accepts caller time.
7. Reconstruction uses exactly the verified checkpoint prefix, including no later equal-time entry.
8. Integrity assessment delegates overlap semantics to the Frozen pure functions and publishes exact conflicting append-entry refs.
9. An untouched result claims only no conflict in the authoritative prefix; it never claims proof of uninstrumented reads.

### Failure precedence

1. invalid record/producer/holdout → `TypeError` or `ValueError`, before append/read;
2. Foundation append conflict/integrity/publication failure → propagate unchanged; no read;
3. reservation time later than receipt → `SAMPLE_LEDGER_CONFLICT`; no read;
4. invalid/mismatched snapshot checkpoint or entry payload → `SAMPLE_LEDGER_CONFLICT`;
5. missing required producer coverage → `SAMPLE_RESERVATION_COVERAGE_MISSING`;
6. exact-revision interval overlap → `HOLDOUT_CONTAMINATED` result, not storage failure.

### Write set

- `strategy-validation/src/crypto_quant_validation/ledger.py`
- minimal Validation public-root exports for the ledger interface/results
- `strategy-validation/tests/test_ledger_integration.py`

### Acceptance

```bash
uvx --python 3.13.5 --from pytest==8.4.2 \
  --with ./backtest/packages/trading-domain \
  --with-editable ./foundation \
  --with-editable ./strategy-validation \
  pytest -q -p no:cacheprovider strategy-validation/tests/test_ledger_integration.py
```

Required evidence:

- Trial, Selection, and OOS ValidationCase reservation wires and event ids;
- append accepted before a controlled test read is released;
- exact replay and conflicting replay;
- producer/purpose/interval mismatch and missing coverage;
- immutable checkpoint prefix with later equal-time append exclusion;
- canonical conflicting entry refs and contamination result;
- tampered/truncated/wrong-log prefix fails without an assessment;
- no separate `SampleConsumptionRecord` artifact or duplicate snapshot semantics.

## `SV-SHELL-01` — contract-first Validation shell implementation

### Outcome

One Validation operation freezes admission evidence and a candidate-specific Plan before OOS work, executes exactly the required cases, and publishes `ValidationReport(result = supported | rejected | inconclusive)` only when aggregation permits it.

### Inputs

- completed `SV-CORE-01` and `SV-LEDGER-01`;
- canonical frozen Research candidate graph fixtures;
- accepted Foundation store and frozen BT-PORT behavior;
- frozen Validation policy and OOS holdout.

### Module interface

Equivalent behavior to:

```text
validate_candidate(candidate_ref, policy, holdout, foundation, backtest) ->
  PublishedValidationReport | NoReport
```

The result exposes published refs and explicit failure/no-report state. It does not expose mutable case registries, Backtest internals, or Promotion recommendations. Default replay finds the existing canonical candidate/policy Plan and reuses its snapshot; a caller requests a new validation explicitly with `fresh=True`.

### Publication order and commit points

1. Resolve and verify the candidate graph through public refs; invalid input performs no new publication.
2. Freeze and publish the authoritative `SampleConsumptionLedgerSnapshot`.
3. Build and publish `ValidationPlan` before reading any OOS result.
4. Reconstruct the frozen prefix; publish `SampleIntegrityAssessment` and the `evidence_integrity` case/result. This case emits no holdout reservation.
5. Publish the `out_of_sample` ValidationCase.
6. Append its holdout reservation through `SV-LEDGER-01`; append failure means no OOS read or Backtest call.
7. Forward the frozen BT-PORT selector request unchanged and consume only frozen behavior. Opaque `ValidationCaseRef` request-context binding is owned by `P00-SEAM-01`; the fixture-backed shell derives no provider identity.
8. Branch completed versus terminal before analysis. Only a completed publication enters `derive()`.
9. Run `SV-CORE-01` mappings, publish CaseResults, and publish a Report only if exact-cover aggregation returns one.

The original snapshot checkpoint is reused throughout; a later or equal-time append cannot alter admission.

### Observation mapping

| Observation | Case/report effect |
| --- | --- |
| completed + verified linked metric passes threshold | OOS `PASS`; aggregate normally |
| completed + verified linked metric below threshold | OOS `FAIL`; Report `rejected` |
| valid missing metric or insufficient trades | OOS `INCONCLUSIVE`; Report `inconclusive` |
| Backtest `BLOCKED` | OOS `BLOCKED`; Report `inconclusive` |
| Backtest `CANCELLED` | OOS `INCONCLUSIVE`; Report `inconclusive` |
| Backtest `FAILED` | OOS `FAILED`; no Report |
| exhausted facade/repository/tamper/retention failure | OOS `FAILED`; no Report |
| missing reservation or contamination | admission/OOS blocked; never a successful untouched claim |

### Write set

- `strategy-validation/src/crypto_quant_validation/runtime.py`
- minimal Validation public-root exports for the orchestration result
- `strategy-validation/tests/test_validation_shell.py`

No “Backtest adapter” package, production Protocol package, or duplicate evidence verifier is introduced. BT-PORT remains test-only.

### Acceptance

```bash
uvx --python 3.13.5 --from pytest==8.4.2 \
  --with ./backtest/packages/trading-domain \
  --with-editable ./foundation \
  --with-editable ./strategy-validation \
  pytest -q -p no:cacheprovider strategy-validation/tests/test_validation_shell.py
```

Required evidence:

- snapshot and Plan are published before OOS evidence is read;
- authoritative checkpoint is reused exactly and excludes later equal-time entries;
- OOS reservation precedes the controlled read/Backtest call;
- canonical adverse completed fixture publishes `ValidationReport(result="rejected")`;
- BLOCKED/CANCELLED map to inconclusive, FAILED/local provider/storage errors produce no Report;
- missing metric/trade count remain inconclusive and are never zero-filled;
- forged candidate/family/manifest/case/profile/publication/execution-hash/cache links fail;
- no Shadow, Live, recommendation, credential, or deployment field/import exists.

Passing this node proves package-local orchestration against frozen wires only. It is not `SV-THIN-01`, real Research provenance, real provider evidence, or an integrated receipt.

## `SV-THIN-01` — real Validation acceptance

### Outcome

Prove `SV-SHELL-01` consumes the actual `RP-THIN-02` candidate and accepted provider seam unchanged, then publish the SV-THIN-01 receipt required by Promotion.

### Inputs

- completed `SV-SHELL-01`;
- accepted `RP-THIN-02` StrategyCandidate graph;
- accepted `P00-SEAM-01` and root workspace/lock.

### Allowed changes

- `strategy-validation/tests/test_integrated_validation.py`;
- SV-THIN-01 acceptance receipt;
- at most package-local public-name/type reconciliation in `runtime.py`. Any admission, ordering, mapping, report, or schema change returns to `SV-SHELL-01` and its focused suite.

### Acceptance

This command applies only after `P00-SEAM-01` has created the declared root workspace and lock.

```bash
uv run --locked pytest -q \
  strategy-validation/tests/test_validation_shell.py \
  strategy-validation/tests/test_integrated_validation.py
```

The real test proves exact Research provenance resolution, immutable snapshot reuse, reservation-before-read, adverse rejected OOS, terminal/provider/tamper/retention mappings, no-report failures, replay, accepted provider SHA, and root lock hash.

## Dependencies

| Type | Node/artifact | Why |
| --- | --- | --- |
| Contract | `SV-00A-core` and `SV-CORE-01` | Own record overlap semantics and case/report interpretation. |
| Contract | `PF-CORE-01` and `SV-LEDGER-01` | Supply exact publication, reservation, checkpoint, and assessment behavior. |
| Contract | frozen Research wires + `BT-PORT-01` | Supply fixture-backed candidate/provider behavior for `SV-SHELL-01`. |
| Contract | `RP-THIN-02` StrategyCandidate graph | Replaces frozen candidate wires only for `SV-THIN-01`. |
| Contract | `P00-SEAM-01` | Replaces BT-PORT behavior only for real acceptance. |
| Evidence | adverse completed and all terminal provider records | Required only by `SV-THIN-01`. |
| Write conflict | Validation public root, ledger/runtime | `SV-LEDGER-01` completes before one writer owns `SV-SHELL-01`. |
| Write conflict | integrated test/receipt | `SV-THIN-01` is serialized by the fan-in owner. |

## Exclusions

- candidate selection or Research task execution;
- Backtest request identity, economics, terminal semantics, verification, or metrics;
- Promotion recommendation, positive eligibility, Shadow/Live/deployment;
- extra validation methods, model/trainer/feature interface, database, queue, or mutable case registry.
