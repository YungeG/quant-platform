# Platform Integration v1

- **Status:** Accepted and released as `integration-v1`; Platform-owned v1 decisions, including `PLAT-REC-01`, `PLAT-REC-02`, and `PLAT-REC-03`, remain frozen. Additive model-build work is specified separately in [Integration v2](integration-v2.md).
- **Version:** 1.0
- **Scope:** the first integrated Research → Validation → negative Promotion path
- **Authority:** This document is the authoritative integration contract. It supersedes only the *Integration Draft* portions of the overview and module designs. `RP-THIN-01`, `SV-00A-core`, and `PG-SYN-1` remain separately Frozen exactly as documented in their module designs.

“Frozen” here means that no unresolved Platform-owned v1 design choice remains. It does **not** assert that a usable Backtest execution binding or Platform runtime receipts exist. Those are implementation prerequisites, not design gaps. `P00-CON-02` is approved with both repository-owner approvals recorded; it changes only the static-legacy gate described below.

Backtick schema labels in this document describe normative ownership and behavior unless the Backtest acceptance matrix records their exact public names and canonical bytes. Backtest owns every `BT-GAP-*` name/wire freeze; BT-GAP-02B now freezes the execution-input names used below.

## 1. Boundaries and P00-CON-02

The legacy pilot is immutable static historical evidence only. It is not a callable adapter, economic authority, parity proof, reproducibility prerequisite, or source of canonical Backtest evidence.

`P00-CON-02` / `p00-contract-v2` supersedes **only** the two machine-named downstream conditions in approved `p00-contract-v1`:

| Human work package | Frozen JSON condition key |
| --- | --- |
| `P00-LEG-01` | `P00_LEG_01` |
| `P00-CUT-01` | `P00_CUT_01` |

`P00-LEG` and `P00-CUT` are gate-family shorthand, never work-package IDs or lifecycle states.

Its sole decision is:

```text
Existing immutable static historical capture + retirement receipt
is sufficient evidence for P00-LEG-01/P00-CUT-01.

Hermetic replay is neither required nor permitted as a P00-PLAT prerequisite.
```

The receipts retain the evidence classification `static_historical_evidence`; that classification is not a lifecycle status. P00-CON-02 does not alter `ArtifactEnvelope` v1, `ArtifactRef`, the Backtest seam, lock rules, ownership, or the approved P00-CON-01 fixture. Both required repository-owner approvals are recorded, so the static receipts satisfy the clarified legacy gate without hermetic replay.

The integrated system has one non-package `platform/` workspace and one root `uv.lock`. The root dependency files pin all Backtest packages to accepted BT-GAP-09 source revision `e3c04fb612d6798aef1420b60864d4f315ed12ac` (package code `a014e9389f36b6696653606c5ebcb845cabe9f24`). The Backtest gitlink instead records acceptance receipt `92810375fdf6c0c48c1edaeade74b97755f20220`, the documentation-only child of that source revision, and is not a dependency source; the four Platform module submodules remain workspace members. Research and Validation consume the public Backtest preparation/facade/repository/analysis roots directly. Validation owns sample-consumption semantics; Foundation owns only generic CAS, append, receipt, checkpoint, and log-chain mechanics.

## 2. Identity, time, and publication

Every Platform schema below is an `ArtifactEnvelope(..., schema_version=1, ...)` payload unless it is explicitly a Foundation receipt/checkpoint wire record.

### 2.1 Immutable identity

```text
ArtifactRef = (artifact_type, schema_version, content_hash)
content_hash = sha256(canonical({artifact_type, schema_version, payload}))
source_hash = sha256(canonical-UTF-8 Envelope source bytes)
payload_source_hash = sha256(exact owner-log payload bytes)
```

- Envelope v1 has exactly `artifact_type`, `schema_version`, `payload`, and `content_hash`.
- A payload never contains its own ref/hash, `source_hash`, a path, worker, attempt, cache fact, lock fact, or `published_at`; it does not duplicate `schema_version`.
- `source_hash` protects the complete canonical Envelope source bytes; it is not an address component. For an artifact-publication entry, the payload is exactly those source bytes, so `payload_source_hash == source_hash`. `content_hash`, `source_hash`, and `payload_source_hash` are distinct hashes with those distinct preimages.
- `Ref[T]` validates the exact artifact type and schema version.

### 2.2 Reference ownership

| Reference | Owner and v1 handling |
| --- | --- |
| `ArtifactRef` / `Ref[T]` | Domain-owned typed coordinate for Platform artifacts. |
| `CashDevelopmentRequestIntent@1` / `BacktestExecutionRequest@2` | Platform constructs only the public intent with opaque Trial/Validation context and supplies public provider facts. Backtest derives, registers, and persists `BacktestRequest@1`, publishes the v2 execution-input Envelope through Foundation, and returns the executable transport by value. Platform never constructs resolved internals or decodes the bundle. |
| `BacktestRequestRef`, `BacktestCanonicalPublicationRef`, `AnalysisArtifactRef`, `BacktestMarketBundleRef`, `BacktestModelRef` | Nominal opaque Backtest refs. Platform stores and passes them only; it never fabricates, downcasts, or substitutes a general `ArtifactRef`. |
| `BacktestMetricProfileRef` | A Backtest-owned, type/version-constrained Domain `ArtifactRef`; it is opaque to Platform. The public `derive()` parameter remains the underlying `ArtifactRef`. |
| `ActorRef` | Domain-owned opaque identity coordinate. Equality is exact canonical wire equality only. |
| `LogEntryRef` / `LogCheckpoint` | Foundation wire values defined in §3. They are not artifacts and are valid only for their named log. |
| `PublicationFactRef` | Tagged union of a Platform artifact owner-log entry and an integration-owned Backtest-evidence admission entry. It identifies the original Platform governance fact and its accepted time; a later status event cannot replace it or refresh evidence age. |

`PublicationFactRef` has one canonical tagged union:

```text
platform_owner_log(entry_ref: LogEntryRef)
| backtest_admission(entry_ref: LogEntryRef("platform.backtest-evidence-admission.v1"))
```

`platform_owner_log` resolves the exact Platform artifact published by its designated owner-log entry. `backtest_admission` resolves the exact Backtest canonical-publication, analysis, or metric-profile ref named by `BacktestEvidenceAdmission@1`. Both use the immutable original `AppendReceipt.accepted_at`; neither accepts a caller-supplied time. Backtest proves the admitted subject's identity, integrity, retention, and lineage before admission, while Foundation remains generic append mechanics.

`BacktestResultGrade` is the one Backtest-owned grade domain. `SelectionPolicy@1.accepted_backtest_grades`, `ValidationPlan@1.accepted_backtest_grades`, and `PromotionPolicy@1.accepted_backtest_grades` all use it; the v1 golden grade is `development`.

### 2.3 Time

| Time | Owner | In artifact payload? |
| --- | --- | --- |
| Market interval / model availability | semantic | yes |
| `consumed_at` | Validation record | yes; logical pre-read reservation instant, not physical I/O completion |
| Snapshot `as_of` | Foundation-assigned checkpoint cutoff | yes |
| Attempt start/end, worker, cache | operational receipt/diagnostic | no |
| `published_at` | Foundation append receipt as `accepted_at` | no |

All Platform instants use canonical UTC `YYYY-MM-DDTHH:MM:SS.ffffffZ`. The composition root injects Foundation's explicit UTC governance clock. Foundation assigns non-decreasing `accepted_at`; global/log sequences order equal instants. A clock value earlier than the previous accepted instant fails closed with `CLOCK_NOT_MONOTONIC`; callers cannot supply or backfill time.

### 2.4 Publication

```text
CAS put
→ immutable ref exists but is not published
→ owner appends canonical Envelope bytes to its owner log
→ AppendReceipt.accepted_at is the owner-log publication fact
```

A CAS orphan is not downstream evidence. An append failure may retry the same event ID and bytes; it may not rewrite them. Promotion-owned `EvidenceStatusEvent@1`, not Foundation, determines current evidence status. Foundation never defines business labels such as `PUBLISHED`, `REVOKED`, or `SUPERSEDED`.

Verified Backtest evidence enters Platform governance through one integration-owned artifact and owner log:

```python
BacktestEvidenceAdmission@1 = {
  subject_ref: BacktestCanonicalPublicationRef
             | AnalysisArtifactRef
             | BacktestMetricProfileRef,
}
```

The composition root first resolves and verifies `subject_ref` through the Backtest public repository, then stores the canonical admission Envelope and appends it to `platform.backtest-evidence-admission.v1`. Its event ID is `H("backtest-evidence-admission-v1", subject_ref canonical wire)`. Repeating the same admission is idempotent and returns the first entry and `accepted_at`; the same event ID with different bytes is `LOG_CONFLICT`. The artifact contains no timestamp.

## 3. Foundation contract (`P00-PLAT-01`)

Foundation is a deep local module, not a service or adapter layer:

```python
class LocalFoundation:
    def put(self, *, envelope: ArtifactEnvelope) -> ArtifactRef: ...
    def read(self, *, ref: ArtifactRef) -> ArtifactReadResult: ...

    def append(
        self, *, log_name: str, event_id: str, payload: bytes
    ) -> AppendReceipt: ...

    def entries(
        self,
        *,
        log_name: str,
        through: LogCheckpoint | LogEntryRef | None = None,
    ) -> tuple[LogEntry, ...]: ...

    def checkpoint(self, *, log_name: str) -> LogCheckpoint: ...
```

`read()` is structurally compatible with the Backtest-owned input port:

```python
class ArtifactEnvelopeReader(Protocol):
    def read(self, *, ref: ArtifactRef) -> ArtifactReadResult: ...
```

Foundation validates only generic Envelope/source-byte/ref and log-chain structure. `ArtifactReadResult.artifact` is not a semantic authority; Backtest ignores it and decodes `source_bytes` itself. Backtest owns all Backtest decoding, hydration, semantic validation, and evidence verification. Promotion reconstructs its owned status projection from generic `entries()`; Foundation has no status reader or business-status vocabulary.

### 3.1 Canonical owner logs and entry identity

Platform call sites use exactly these owner logs. `LocalFoundation` remains generic—it accepts a log name and bytes—but it does not make a caller-selected name authoritative outside this table.

| Log | Owner | Allowed payloads |
| --- | --- | --- |
| `research.artifacts.v1` | Research | `ExperimentSpec@1`, `TrialDeclaration@1`, `AnalysisTask@1`, `BacktestTrialSpec@1`, `SelectionPolicy@1`, `SelectionDeclaration@1`, `CandidateFamily@1`, `StrategyCandidate@1` |
| `research.execution.v1` | Research | `TaskAttemptStarted@1`, `TaskAttemptClosed@1`, `TaskOutcome@1`, `ExperimentExecutionManifest@1` |
| `platform.backtest-evidence-admission.v1` | Platform Integration composition root | `BacktestEvidenceAdmission@1` |
| `validation.sample-consumption.v1` | Strategy Validation | `SampleConsumptionAppend@1` |
| `validation.artifacts.v1` | Strategy Validation | `SampleConsumptionLedgerSnapshot@1`, `SampleIntegrityAssessment@1`, `ValidationPlan@1`, `ValidationCase@1`, `ValidationCaseResult@1`, `ValidationReport@1` |
| `promotion.evidence-status.v1` | Promotion | `EvidenceStatusEvent@1` |
| `promotion.reviews.v1` | Promotion | `PromotionReview@1` |
| `promotion.artifacts.v1` | Promotion | `EvidenceStatusSnapshot@1`, `PromotionPolicy@1`, `PromotionCase@1`, `PromotionEvaluation@1`, `PromotionDecision@1` |

Every listed artifact publication appends its canonical Envelope source bytes. The generic event ID is:

```text
event_id = H("artifact-publication-v1", log_name, ArtifactRef canonical wire)
```

`SampleConsumptionAppend@1` and `BacktestEvidenceAdmission@1` use their narrower semantic event-ID rules, but each log payload is still its exact canonical Envelope source bytes. A ref may appear in one designated owner log only. Thus an artifact is published only when a verified entry in that log has exact payload bytes and `payload_source_hash == source_hash`; a CAS orphan, an entry in another log, or merely a matching ref is not evidence.

```text
LogEntryRef = (log_name, log_sequence, receipt_hash)
```

`LogEntry` returns the `LogEntryRef`, `event_id`, exact `payload` bytes, `payload_source_hash`, `ledger_sequence`, `log_sequence`, `previous_receipt_hash`, `receipt_hash`, and `accepted_at`. The ref is canonical by that three-field wire tuple; a consumer validates that its log name and receipt hash match the returned entry before following it. `AppendReceipt.entry_ref` is this derived ref, not an additional receipt field.

### 3.2 Receipt and checkpoint wire

```json
{
  "log_name": "validation.sample-consumption.v1",
  "event_id": "...",
  "payload_source_hash": "sha256:...",
  "ledger_sequence": 17,
  "log_sequence": 4,
  "previous_receipt_hash": "sha256:...",
  "receipt_hash": "sha256:...",
  "accepted_at": "2026-08-12T14:24:11.000000Z"
}
```

`payload_source_hash` hashes the exact payload bytes. `receipt_hash` hashes all preceding receipt fields, excluding itself. Foundation reads its injected UTC governance clock under the global lock. `accepted_at` is non-decreasing; sequence numbers order ties. A backward clock fails with `CLOCK_NOT_MONOTONIC`. Callers cannot supply or backfill receipt/checkpoint time.

```json
{
  "log_name": "validation.sample-consumption.v1",
  "as_of": "2026-08-12T14:24:11.000000Z",
  "upper_log_sequence": 4,
  "head_receipt_hash": "sha256:..."
}
```

`checkpoint(log_name=...)` takes the global write lock, reads the injected clock, and binds the current `upper_log_sequence` and head hash. It has no caller-provided `as_of`. Foundation durably records every issued tuple; `entries(..., through=checkpoint)` rejects a syntactically valid tuple that Foundation did not issue. A later append cannot enter the checkpoint even when it shares the same `accepted_at`, because the immutable upper sequence is authoritative. An empty prefix uses `upper_log_sequence = 0` and `head_receipt_hash = null`. `entries(..., through=checkpoint)` verifies and returns exactly that prefix; `through=entry_ref` verifies and returns the prefix ending at that entry. Reuse a returned checkpoint for repeatable reconstruction. A checkpoint never claims that an uninstrumented read did not occur.

### 3.3 Storage and failure contract

```text
.foundation.write.lock
.staging/
artifacts/sha256/<two-hex>/<digest>
registries/<canonical-log-name>.jsonl
```

Foundation uses one cooperative, same-filesystem global write lock; staging → structural read-back → atomic rename; and contiguous global and per-log append sequences. It does not support stale-lock deletion, automatic truncation, NFS, object storage, or hostile writers.

Typed Foundation failures are:

```text
UNSUPPORTED_FILESYSTEM
WRITE_LOCK_UNAVAILABLE
CLOCK_NOT_MONOTONIC
ARTIFACT_NOT_FOUND
ARTIFACT_INTEGRITY
ARTIFACT_PUBLICATION_FAILED
LOG_CONFLICT
LOG_INTEGRITY
LOG_PUBLICATION_FAILED
SNAPSHOT_PUBLICATION_FAILED
```

Bad public arguments remain `TypeError` or `ValueError`. A Foundation exception is never converted to a fake Backtest terminal or domain event.

## 4. Research integration (`RP-THIN-02`)

### 4.1 Experiment and task universe

```python
ExperimentSpec@1 = {
  hypothesis_ref,
  strategy_definition_ref,
  data_slices,
  parameter_combinations,
  seeds,
  scenario_refs,
  backtest_template_ref,
  model_build_plan,       # null in integrated v1
  metric_profile_refs,
  budget,
}
```

Each `data_slice` is:

```python
{
  market_bundle_ref: BacktestMarketBundleRef,
  dataset_revision: str,
  interval_start: UtcInstant,
  interval_end: UtcInstant,  # [start, end)
}
```

All task-producing axes are explicit, finite, nonempty canonical sequences. `parameter_combinations` contains unique canonical parameter maps, sorted by canonical map wire; each map has unique, lexicographically sorted names. `data_slices` are unique and sorted by their full canonical wire. `scenario_refs` and `metric_profile_refs` are unique and sorted by their canonical ref wire. `seeds` are non-negative, unique, and ascending. Duplicate coordinates fail construction; no axis has labels, implicit defaults, range, Cartesian, or adaptive expansion.

The spec has no selection policy, retry policy, worker data, timestamps, or results. `model_build_plan is None` is mandatory in the thin slice; non-null ModelBuild is reserved and unimplemented.

```text
U(E) = ModelBuild(E) ∪ Trial(E) ∪ Analysis(E)
Trial(E) = parameters × slices × scenarios × seeds
Analysis(E) = Trial(E) × metric profiles
```

Each generated coordinate has one canonical declaration/task ref; therefore `U(E)` is a determinate exact-cover set. The golden thin fixture has `0 ModelBuild + 4 Trial + 4 Analysis = 8` tasks.

### 4.2 Task artifacts and execution evidence

```python
TrialDeclaration@1 = {
  experiment_ref,
  parameter_values,
  data_slice,
  scenario_ref,
  seed,
  backtest_template_ref,
  model_input_bindings,
}

AnalysisTask@1 = {
  experiment_ref,
  trial_declaration_ref,
  metric_profile_ref: BacktestMetricProfileRef,
}

BacktestTrialSpec@1 = {
  trial_declaration_ref,
  resolved_model_refs,
  backtest_request_ref,
}
```

One `TrialDeclaration` materializes at most one `BacktestTrialSpec`. Two declarations must not map to one Backtest request or semantic run (`TRIAL_REQUEST_COLLISION`). A Research dependency block before request materialization is a local `dependency_blocked`; it never fabricates a Backtest terminal.

The Research integrated shell constructs `CashDevelopmentRequestIntent@1` from `TrialDeclaration` coordinates and encodes the opaque canonical `TrialDeclarationRef` in `experiment_id`. Validation does the same with `ValidationCaseRef`. The composition root supplies only public `CashDevelopmentProviderInputs@1` external authorities. Backtest imports no Platform type: `prepare_cash_development_backtest()` derives, validates, registers, and persists the immutable `BacktestRequest@1`; returns its opaque `BacktestRequestRef` and `SemanticRunId`; publishes and verifies the execution-input Envelope through Foundation; and returns an executable `BacktestExecutionRequest@2` inside `PreparedBacktestExecution`. Platform never derives Backtest IDs or constructs a Resolver, Registry, `ResolvedBacktestRequest`, `ResolvedExecutionCase`, or execution plan.

`PLAT-REC-03` — Additive executable transport: accepted v1 request and bundle bytes remain immutable, while BT-GAP-09 adds the executable v2 provider-preparation seam:

```python
PreparedBacktestExecution = {
  request_ref: BacktestRequestRef,
  semantic_run_id: str,
  execution_request: BacktestExecutionRequest@2,
  runtime: BacktestRuntime,
}
```

The v2 transport still embeds exactly one immutable `BacktestRequest@1` plus one Domain-owned `backtest_execution_input_bundle@2` `ArtifactRef`. Backtest alone constructs both after resolving public intent/provider inputs. Foundation supplies the structural reader/publisher; Platform neither separately stores the transport nor decodes, fabricates, or reconstructs its bundle, request identity, semantic run, profiles, financial state, or execution case.

Backtest validates and exact-read verifies the persisted request and bundle before returning prepared authority. Missing, tampered, mismatched, or unavailable inputs are pre-Attempt failures, not terminal runs. The accepted development cash provider proves real COMPLETED, BLOCKED, and CANCELLED behavior. P00 does not manufacture an internal defect to obtain FAILED; Backtest must provide accepted `BacktestEvidenceRepository.load_terminal()` evidence for one durable FAILED graph before P00-BTA/P00-SEAM close. Any real provider FAILED ref remains supported by the unchanged `backtest_terminal(FAILED, ...)` contract. G12E remains the MarketBundle read authority and market bytes are never copied into Platform artifacts.

```text
TaskRef =
  { kind: "TRIAL", task_artifact_ref: Ref[TrialDeclaration@1] }
| { kind: "ANALYSIS", task_artifact_ref: Ref[AnalysisTask@1] }
```

A `TaskRef` has exactly one tagged artifact ref and canonical-sorts by `(kind, task_artifact_ref wire)`. It resolves to the same Experiment as its manifest.

```python
TaskOutcome@1 = {
  task_ref,
  state: "COMPLETED" | "BLOCKED" | "FAILED" | "CANCELLED",
  witness,
}
```

`witness` is exactly one tagged value:

```text
trial_completed_publication(publication_ref: BacktestCanonicalPublicationRef)
analysis_derivation(analysis_ref: AnalysisArtifactRef,
                    source_publication_ref: BacktestCanonicalPublicationRef)
backtest_terminal(status: BLOCKED | FAILED | CANCELLED,
                  durable_evidence_ref: ArtifactRef)
upstream_task_outcome(task_outcome_ref: Ref[TaskOutcome@1])
dependency_block(reason_code, dependency_ref | null)
local_failure(failure_code)
```

A completed Trial uses `trial_completed_publication`; a completed Analysis uses `analysis_derivation`. A direct Backtest terminal uses `backtest_terminal` with equal TaskOutcome state. An Analysis blocked by a non-completed Trial uses `upstream_task_outcome`; a pre-request dependency block uses `dependency_block`; a retry-exhausted local error uses `local_failure` and state `FAILED`. These are the only TaskOutcome witnesses.

```python
TaskAttemptStarted@1 = {
  task_ref,
  ordinal,
  parent_closed_attempt_ref | null,
  selection_declaration_refs,
  dispatch_ref | null,
}

TaskAttemptClosed@1 = {
  started_attempt_ref,
  disposition: "RETRYABLE_FAILURE" | "ABANDONED" | "TERMINAL",
  task_outcome_ref | null,
  failure_code | null,
}
```

| Disposition | `task_outcome_ref` | `failure_code` | Effect |
| --- | --- | --- | --- |
| `RETRYABLE_FAILURE` | null | required | The attempt is closed and another ordinal may start. |
| `ABANDONED` | null | required (`WORKER_LOSS` or another closed local code) | The attempt is closed before retry. |
| `TERMINAL` | required `Ref[TaskOutcome@1]` for the same `TaskRef` | null | The task is permanently closed. |

Ordinals begin at one, are contiguous, and form one chain; each task has at most one open attempt. Retries reuse the declaration, trial spec, and request ref. `TERMINAL` here means a terminal **task closure**, not a Backtest terminal ref. Backtest returns a bare Domain `ArtifactRef` for non-completed runs; repository loading recovers its `BLOCKED | FAILED | CANCELLED` status for the `backtest_terminal` witness.

```python
ExperimentExecutionManifest@1 = {
  experiment_ref,
  task_outcome_refs,  # one per TaskRef, canonical by TaskRef
}

CandidateFamily@1 = {
  experiment_ref,
  execution_manifest_ref,
}
```

`CandidateFamily@1` has exactly those two fields, and `execution_manifest_ref` must resolve to a Manifest whose `experiment_ref` exactly equals the Family's `experiment_ref`. The manifest's designated owner log is `research.execution.v1`; its verified publication `LogEntryRef` is the audit cutoff. Reconstruct the verified shared log prefix through that entry, then project only entries that claim or resolve to this Experiment. Unrelated Experiments may legitimately be interleaved and are ignored after generic chain verification. Exact-cover validation requires: every `TaskRef` in `U(E)` has exactly one published `TaskOutcome`; exactly one matching `TERMINAL` closure points to it; all entries for this Experiment form valid chains; and no entry claiming this Experiment references a foreign, duplicate, pending, or unaccounted task. A later execution entry claiming the closed Experiment is invalid. Retry and selection-precommit mechanics remain append-only execution evidence, not CandidateFamily identity.

### 4.3 Selection and candidate

```python
SelectionPolicy@1 = {
  metric_profile_ref: BacktestMetricProfileRef,
  eligible_trial_statuses: ["COMPLETED"],
  accepted_backtest_grades,
  hard_filters,
  ordering,                       # primary → secondary
  max_selections,
  tie_break: "trial_declaration_ref_ascending",
}

SelectionDeclaration@1 = {
  experiment_ref,
  selection_policy_ref,
  universe_kind: "candidate_trial_declarations_v1",
  declared_by_ref,
}
```

All SelectionDeclarations used by an execution are published before its first task attempt, and starts reference that predeclared set. A later SelectionPolicy cannot select an already-started CandidateFamily.

```python
StrategyCandidate@1 = {
  candidate_family_ref,
  selection_declaration_ref,
  selected_trial_declaration_ref,
  selected_trial_spec_ref,
  selected_publication_ref,
  selected_analysis_ref,
  selection_rank,
  validated: false,
}
```

Selection is replayed from CandidateFamily, ExperimentExecutionManifest, and SelectionPolicy. Missing completed analysis is `SELECTION_INPUT_INCOMPLETE`; no eligible trial yields `NoSelection`, never a manual winner.

## 5. Validation integration (`SV-THIN-01`)

### 5.1 Validation-owned sample consumption

The Frozen six-field record remains unchanged:

```python
SampleConsumptionRecord@1 = {
  dataset_revision,
  interval_start,
  interval_end,
  purpose,
  consumer_id,
  consumed_at,
}

SampleConsumptionAppend@1 = {
  record: SampleConsumptionRecord@1,
  producer_ref,
}
```

`SampleConsumptionRecord@1` is an embedded canonical value in this integration artifact, not a separately addressable/published Artifact. One atomic append therefore publishes both the reservation record and its producer without creating an unpublished `record_ref` CAS orphan.

```text
consumer_id = H("sample-consumer-v1", producer_ref wire)
event_id = H("sample-consumption-append-v1",
             producer_ref wire, revision, interval, purpose)
```

For this append-before-read integration protocol, `consumed_at` is the producer's canonical **logical reservation instant** for the imminent market-sample consumption. It is not a claim about physical I/O completion or proof that a read ultimately happened. It remains the unchanged Frozen field used to order supplied records. The producer chooses it before append, so `record.consumed_at <= receipt.accepted_at`; Foundation accepts the append before the read. A retry reuses the identical append. Reusing an event ID with different bytes is `LOG_CONFLICT`; append conflict/failure blocks the read.

| Producer | Required reservation coverage | Purpose |
| --- | --- | --- |
| `TrialDeclaration@1` | Its declared `data_slice`, before it materializes or reads input for a Backtest request. A documented pre-request `dependency_block` has no market read and no append. | `discovery` |
| `SelectionDeclaration@1` | Each distinct `data_slice` in its Experiment before it reads completed trial/analysis evidence for selection. | `selection` |
| `ValidationCase@1` with `case_type = "out_of_sample"` | Its ValidationPlan holdout, before OOS request/input read. | `validation` |
| Future Feature/Model task | Its declared interval before read. | `feature_build` / `model_training` |

`StrategyCandidate@1` and `CandidateFamily@1` are provenance artifacts, not sample consumers; they produce no append. The `evidence_integrity` ValidationCase reconstructs the precommitted ledger and also produces no holdout append. Missing required reservation coverage is `BLOCKED`, never “untouched.”

```python
SampleConsumptionLedgerSnapshot@1 = {
  checkpoint: LogCheckpoint("validation.sample-consumption.v1"),
}

SampleIntegrityAssessment@1 = {
  snapshot_ref,
  dataset_revision,
  interval_start,
  interval_end,
  untouched,
  conflicting_append_entry_refs: tuple[LogEntryRef, ...],
}
```

The append-entry refs are canonical by `LogEntryRef` and resolve to the conflicting `SampleConsumptionAppend@1` payloads. Validation reconstructs records only through the verified checkpoint, then invokes the Frozen `build_snapshot()` and `assess_untouched_holdout()` semantics. The integration artifact is distinct from the Frozen in-memory `SampleConsumptionSnapshot`; neither proves absence of uninstrumented reads.

### 5.2 Thin plan, cases, and report

```python
ValidationPlan@1 = {
  candidate_ref,
  sample_consumption_snapshot_ref,

  accepted_backtest_grades: ["development"],
  accepted_metric_profile_refs,

  holdout: {
    market_bundle_ref,
    dataset_revision,
    interval_start,
    interval_end,
    role: "HOLDOUT",
    selection_observed: false,
  },

  oos_rule: {
    metric_profile_ref: BacktestMetricProfileRef,
    metric_key: "simple_period_return",
    unit: "fraction",
    operator: "gte",
    threshold,
    minimum_trade_count,
  },

  decision_rule: {
    required_case_types: ["evidence_integrity", "out_of_sample"],
    required_fail: "rejected",
    blocked_or_inconclusive: "inconclusive",
    failed_execution: "no_report",
  },
}

ValidationCase@1 = {
  validation_plan_ref,
  case_type,
}
```

Unsupported case types fail Plan construction; they are not silently skipped. A Case deliberately has no request ref, candidate ref, or candidate-family ref: those all resolve through its Plan and Candidate, preventing a Plan/Case/Request cycle and forged duplicate provenance. The Validation integrated shell constructs the public OOS `BacktestRequest` with opaque canonical `ValidationCaseRef` context, and Backtest validates/registers it and owns all resulting identities; a cached result from another case is invalid.

```text
each TrialDeclaration reservation append succeeds before its data read
→ the SelectionDeclaration reservations for its Experiment succeed before selection reads
→ authoritative SampleConsumptionLedgerSnapshot published
→ ValidationPlan published
→ evidence_integrity and out_of_sample ValidationCases published
→ out_of_sample ValidationCase holdout reservation append succeeds
→ OOS request containing ValidationCaseRef
→ Backtest / Analysis
→ CaseResults
→ Report
```

```python
ValidationCaseResult@1 = {
  case_ref,
  outcome: "PASS" | "FAIL" | "INCONCLUSIVE" | "BLOCKED" | "FAILED",
  reason_codes,
  limitations,
  evidence,
}

ValidationReport@1 = {
  validation_plan_ref,
  result: "supported" | "rejected" | "inconclusive",
  case_result_refs,
  threshold_evaluations,
  sample_integrity_ref,
  limitations,
}
```

Candidate and CandidateFamily provenance is resolved once from `ValidationPlan.candidate_ref → StrategyCandidate.candidate_family_ref`; Report and Case never restate it. Every referenced CaseResult must resolve to the Report’s Plan, and every candidate/selected trial/publication/analysis link must agree along that chain. Forged or cross-plan links fail closed.

No Validation artifact has deployment authorization, Shadow fields, recommendation fields, or mutable status.

## 6. Negative Promotion integration (`PG-THIN-01`)

`PG-SYN-1` remains Frozen and is not the integrated evaluator: it maps caller-supplied rejected facts differently. The integrated path is negative-only.

### 6.1 Evidence status and snapshots

```python
EvidenceStatusEvent@1 = {
  subject_ref: GovernedEvidenceRef,
  issuer_ref: ActorRef,
  action: "PUBLISH" | "SUPERSEDE" | "REVOKE",
  subject_publication_ref: PublicationFactRef | null,
  predecessor_entry_ref: LogEntryRef | null,
  replacement_ref: GovernedEvidenceRef | null,
  reason_code | null,
}

EvidenceStatusSnapshot@1 = {
  status_log_checkpoint: LogCheckpoint("promotion.evidence-status.v1"),
}
```

`GovernedEvidenceRef` is a Platform `ArtifactRef` or a nominal Backtest publication, analysis, or metric-profile ref in the governed-evidence closure below. `PUBLISH` requires the subject's original `PublicationFactRef` and has neither predecessor nor replacement. For a Platform Artifact this is its designated owner-log publication entry; for Backtest evidence it is the `backtest_admission` entry that first admitted that exact verified subject into Platform governance. The publication fact must resolve to the same subject ref. `SUPERSEDE` and `REVOKE` set `subject_publication_ref = null`, name the currently published `subject_ref`, and require its current status-entry ref as predecessor; supersession also requires a same-type/version replacement, while revocation requires a reason. The replacement gets its own `PUBLISH` event with its own original publication fact. Forks, unknown values, malformed chains, mismatched publication facts, or missing predecessors fail closed.

Promotion appends these events only to `promotion.evidence-status.v1`. `EvidenceStatusSnapshot@1` is an immutable binding to a verified checkpoint of that log, not a Foundation status projection cache. Promotion reconstructs the status chain from generic Foundation entries through that checkpoint. There is no expiry status; staleness is a Policy calculation. Actor refs provide provenance in the trusted local-writer model, not cryptographic authorization.

### 6.2 Policy, case, review, evaluation, decision

```python
PromotionPolicy@1 = {
  accepted_validation_plan_refs,
  required_validation_result,
  accepted_backtest_grades,
  accepted_metric_profile_refs,
  maximum_governed_evidence_age_microseconds,
  required_review_roles,
  forbidden_limitations,
  decision_for_not_eligible: "rejected" | "needs_more_evidence",
}

PromotionCase@1 = {
  validation_report_ref,
  promotion_policy_ref,
  opened_by_ref: ActorRef,
}

PromotionReview@1 = {
  promotion_case_ref,
  reviewer_ref: ActorRef,
  reviewer_role,
  independence_attested: true,
  verdict: "approve" | "reject" | "request_changes",
  finding_refs,
  rationale,
}

PromotionEvaluation@1 = {
  promotion_case_ref,
  evidence_status_snapshot_ref: Ref[EvidenceStatusSnapshot@1],
  review_log_checkpoint: LogCheckpoint("promotion.reviews.v1"),
  result: "NOT_ELIGIBLE" | "NEEDS_MORE_EVIDENCE",
  reason_codes,
}

PromotionDecision@1 = {
  promotion_evaluation_ref,
  decider_ref: ActorRef,
  decision: "rejected" | "needs_more_evidence",
  rationale,
  limitations,
}
```

PromotionCase deliberately does not repeat candidate or CandidateFamily. They resolve only through `validation_report_ref → ValidationPlan → StrategyCandidate → CandidateFamily`; a forged link anywhere in that path fails closed.

The review checkpoint includes only `promotion.reviews.v1` entries. It must contain exactly one valid review for every required role, no unknown or duplicate role, distinct reviewer refs, and `reviewer_ref != PromotionCase.opened_by_ref` under exact `ActorRef` wire equality. Each included review must have `independence_attested = true`. Attestation **alone** is insufficient: the identity and exact-role constraints are also required. Those checks are sufficient only for the trusted local-writer v1 model; verifying organizational roles, authority, or real-world independence is deferred RBAC scope. A decision's `decider_ref` is provenance, not an additional independence proof.

### 6.3 Governed-evidence closure, cutoff, and age

For a PromotionCase, the governed-evidence closure is the immutable evidence required to establish the case and report: its Policy and ValidationReport; the Report’s Plan, CaseResults, SampleIntegrityAssessment, and SampleConsumptionLedgerSnapshot; the Plan’s StrategyCandidate; that Candidate’s CandidateFamily, SelectionDeclaration, selected TrialDeclaration, BacktestTrialSpec, canonical publication, and analysis; the Family’s ExperimentExecutionManifest and all TaskOutcomes; the Experiment, its relevant AnalysisTasks, SelectionPolicy, and accepted metric profile. It follows declared refs only. Raw market/model inputs are provenance inputs, not separately status-governed evidence in v1.

`evaluation_at` is `EvidenceStatusSnapshot.status_log_checkpoint.as_of`. The review checkpoint must be at or before `evaluation_at`, and every review used by the Evaluation must be in that checkpoint. For each governed ref, its status must be a verified current `PUBLISHED` chain at the snapshot. Its age anchor is the `accepted_at` of the original `PublicationFactRef`, never the later EvidenceStatusEvent append. For Backtest evidence this measures Platform governance residency from first admission, not Backtest execution age: a delayed first admission starts residency then, while replaying the admission or delaying/replaying a PUBLISH status event cannot rejuvenate it. A ref is fresh only when `evaluation_at - publication_accepted_at <= maximum_governed_evidence_age_microseconds`.

A recognized revoked governed ref is demonstrated policy failure (`NOT_ELIGIBLE`). A missing, superseded, or stale ref is insufficient evidence (`NEEDS_MORE_EVIDENCE`). Malformed status/review chains, invalid checkpoints, Foundation failures, or unreadable evidence are fail-closed exceptions and produce no fabricated Evaluation or Decision.

A demonstrated policy failure is `NOT_ELIGIBLE`; its decision uses `decision_for_not_eligible`. Missing/insufficient evidence and the deferred positive path are `NEEDS_MORE_EVIDENCE`. If all future-positive conditions happen to hold, evaluation returns `NEEDS_MORE_EVIDENCE: POSITIVE_PATH_DEFERRED`. It cannot produce a positive decision.

`shadow_ready`, `shadow_spec_ref`, `deployment_authorized`, Live/deploy fields, and decision-supersession fields are structurally absent.

## 7. State and failure mappings

```text
ExperimentSpec: DRAFT → FROZEN

Execution projection:
FROZEN → OPEN → CLOSED
          ↘ RECOVERING → OPEN

Task:
DECLARED → WAITING → READY → RUNNING
                         ├→ RETRY_WAIT → READY
                         ├→ COMPLETED | BLOCKED | FAILED | CANCELLED
                         └→ ATTEMPT_ABANDONED → RETRY_WAIT
```

`CLOSED` means ExperimentExecutionManifest exact-cover, not success.

```text
Validation:
PLAN_FROZEN → ADMISSION
  ├→ BLOCKED cases → inconclusive Report
  ├→ FAILED → no Report
  └→ OOS → aggregate → supported | rejected | inconclusive Report

Promotion:
CASE_OPEN → REVIEW_SNAPSHOT → NEGATIVE_EVALUATION → NEGATIVE_DECISION
```

| Observation | Trial TaskOutcome | Analysis TaskOutcome | Validation |
| --- | --- | --- | --- |
| Completed publication + verified analysis | `COMPLETED` / `trial_completed_publication` | `COMPLETED` / `analysis_derivation` | PASS/FAIL/INCONCLUSIVE from valid metric evidence |
| Terminal `ArtifactRef` resolving to `BLOCKED` | `BLOCKED` / `backtest_terminal` | `BLOCKED` / `upstream_task_outcome` | `BLOCKED` → inconclusive |
| Terminal `ArtifactRef` resolving to `CANCELLED` | `CANCELLED` / `backtest_terminal` | `BLOCKED` / `upstream_task_outcome` | `INCONCLUSIVE` |
| Terminal `ArtifactRef` resolving to `FAILED` | `FAILED` / `backtest_terminal` | `BLOCKED` / `upstream_task_outcome` | `FAILED`; no Report |
| Pre-request dependency block | `BLOCKED` / `dependency_block` | `BLOCKED` / `upstream_task_outcome` | `BLOCKED` → inconclusive |
| Facade/repository/tamper/retention error after retry exhaustion | `FAILED` / `local_failure` | `BLOCKED` if upstream; otherwise `FAILED` / `local_failure` | `FAILED`; no Report |

Only completed publications reach `derive()`. A valid missing metric or insufficient trade count is `INCONCLUSIVE`, never zero. Backtest/Foundation errors are exceptions, never terminal refs. A valid missing CandidateFamily item, missing required reservation coverage, or contamination is `BLOCKED`, not implementation failure.

## 8. Dependencies and workspace

The graph below governs integrated implementation receipts and remains unchanged. Pure pre-seam core nodes may proceed against frozen contract fixtures as described by the [implementation plans](../implementation/plans/README.md); they do not constitute `P00-SEAM-01`, `RP-THIN-02`, `SV-THIN-01`, or `PG-THIN-01` acceptance.

Delivery dependency graph:

```text
P00-CON-01 approved
├─ P00-CON-02 static-legacy clarification
├─ P00-DOM-01
│  └─ P00-BT-01 + accepted full SHA
└─ P00-LEG-01 / P00-CUT-01 static receipts
        │
P00-BT-01 accepted SHA + P00-CUT-01 + P00-CON-02
        └─ P00-PLAT-01
              └─ P00-SEAM-01
                    └─ RP-THIN-02
                          └─ SV-THIN-01
                                └─ PG-THIN-01
                                      └─ FI-01
```

```text
domain → foundation
domain + market-data + trading → backtest
foundation + domain + backtest → validation
foundation + domain + backtest + validation → research
foundation + domain + backtest → promotion
```

Promotion parses immutable wire contracts; it does not import Research or Validation implementation.

Only after an accepted P00-BT-01 SHA, P00-PLAT-01 may create this root coordinator and lock it:

```toml
[project]
name = "crypto-quant-platform-workspace"
version = "0.0.0"
requires-python = ">=3.13,<3.14"
dependencies = [
  "crypto-quant-backtest==0.1.0",
  "crypto-quant-domain==0.1.0",
]

[tool.uv]
package = false

[tool.uv.workspace]
members = [
  "foundation",
  "research-platform",
  "strategy-validation",
  "promotion-gate",
]
```

The future VCS mappings are all pinned to the same accepted lowercase 40-character SHA:

```toml
[tool.uv.sources]
crypto-quant-backtest = { git = "https://github.com/YungeG/quant-backtest.git", rev = "<accepted-40-character-SHA>", subdirectory = "packages/backtest-runtime" }
crypto-quant-domain = { git = "https://github.com/YungeG/quant-backtest.git", rev = "<accepted-40-character-SHA>", subdirectory = "packages/trading-domain" }
crypto-quant-market-data = { git = "https://github.com/YungeG/quant-backtest.git", rev = "<accepted-40-character-SHA>", subdirectory = "packages/market-data-contracts" }
crypto-quant-trading = { git = "https://github.com/YungeG/quant-backtest.git", rev = "<accepted-40-character-SHA>", subdirectory = "packages/trading-kernel" }
```

No path source, editable dependency, branch/tag-only revision, `PYTHONPATH`, copied Backtest lock, leaf lock, or bundle-builder runtime source is allowed.

## 9. Acceptance cards and golden path

| Card | Owner / write boundary | Acceptance |
| --- | --- | --- |
| `P00-CON-02` | release/design; proposal and structural guard only | static receipts hash-verified; external evidence of both owner approvals; hermetic replay excluded |
| `P00-DOM-01` | Backtest Domain | root `ArtifactRef`; Envelope vector unchanged |
| `P00-BT-01` | Backtest Runtime | public request type/validation/registration and Backtest-owned identities; public facade/repository; run returns `BacktestCanonicalPublicationRef \| ArtifactRef`; repository loads recover three terminal statuses; derive restriction; tamper/retention failure |
| `P00-PLAT-01` | Foundation | CAS, receipt chain, append conflict/idempotency, entry refs, injected governance-clock behavior, Foundation-assigned checkpoints, generic entries, AST guard, clean root install |
| `P00-SEAM-01` | fan-in tests only | Platform-constructed `CashDevelopmentRequestIntent@1` with opaque context + public provider facts → Backtest-owned request/ref/identity and executable v2 transport → real Foundation reader/publisher → real facade/repository/analysis; real COMPLETED/BLOCKED/CANCELLED plus required Backtest-owned FAILED repository acceptance; no copied market bytes/evidence |
| `RP-THIN-02` | Research only | canonical finite axes; 4 trials/8 tasks; exact TaskOutcome manifest; two-field CandidateFamily; blocked declaration retained; forged links rejected |
| `SV-THIN-01` | Validation only | precommitted checkpoint/plan; reservation coverage; adverse OOS gives `rejected`; terminal and contamination mappings exact |
| `PG-THIN-01` | Promotion only | real rejected/development report, governed status snapshot/review cutoff, and `needs_more_evidence`; no positive/deploy fields |
| `FI-01` | integration test + receipt only | whole golden, mutations, replay idempotency, clean-install/import boundary |

Golden fixture:

```text
2 parameters × 2 seeds = 4 TrialDeclarations
3 completed, 1 durable BLOCKED
4 AnalysisTasks; blocked Trial’s Analysis is BLOCKED
selected T10-1
OOS simple_period_return = -0.1, trade_count = 1
ValidationReport = rejected
PromotionDecision = needs_more_evidence
```

Required mutations cover duplicate/cross-ordered task axes; hidden, extra, duplicate, foreign-with-same-Experiment, or unmatched TaskOutcomes while unrelated interleaved Experiments remain valid; forged analysis/profile links; Backtest tampering; all three terminals and local failure; sample-reservation contamination and append conflict; backward clocks and immutable checkpoint prefixes; stale/revoked/malformed status; delayed status publication that must not rejuvenate old evidence; review identity/independence; forged deployment fields; and replay idempotency.

## 10. External prerequisites and deferred scope

The completed Backtest capability baseline and Platform-specific seam extensions are recorded in the [Backtest Platform Integration Extension Register](../implementation/backtest-integration-gap-register.md). `PLAT-REC-01`, `PLAT-REC-02`, and `PLAT-REC-03` are normative decisions in this Accepted document; the register tracks their integration handoff only and does not redefine Backtest product completeness.

The following are external P00 implementation facts owned outside this design:

1. P00-DOM and Backtest clean-SHA/package receipts for the accepted public roots.
2. Platform P00-BTA/P00-SEAM binding to accepted BT-GAP-09 public preparation, request registration, executable v2 transport, repository, and analysis authorities.
3. Platform construction of only `CashDevelopmentRequestIntent@1` plus public provider facts; Backtest retains request, profile, semantic-run, execution-case, and transport authority while importing no Platform types.
4. Platform composition-root implementation of `BacktestEvidenceAdmission@1` after Backtest verification, using generic Foundation append mechanics and the immutable first admission `accepted_at`.
5. P00-BT analysis linkage and minimum output: profile ref, source publication, execution-result hash, `simple_period_return`, `trade_count`, and `BacktestResultGrade`.
6. P00-BT guarantee that one request cannot resolve to differing semantic runs across retries.
7. An accepted clean Backtest 40-character SHA and installable four-package closure.
8. A traceable Platform source revision before any receipt claims Platform commit identity.

Explicitly outside v1:

- Feature/model/trainer ABI and non-null `model_build_plan`;
- range/adaptive search;
- walk-forward, stress, capacity, bootstrap, and selection-bias methods;
- positive Promotion, `ShadowSpec`, Live authorization, and deployment;
- cryptographic actor authority/RBAC;
- database, queue, distributed, or object-store writers;
- proof of uninstrumented reads;
- physical deletion of the sibling legacy repository; and
- economic parity with the retired pilot.
