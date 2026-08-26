# Platform Integration v6 — Target-stream research execution

- **Scope:** additive development-grade cash Research → Backtest → Validation execution from precomputed portfolio targets
- **Predecessor:** [Integration v5](integration-v5.md) and [`FI-04`](../implementation/fi-04-receipt.md)
- **Contract approval:** [`TSR-CON-01`](../implementation/v6-contract-target-stream-research-v1.md)
- **Protected fixture:** [`integration-v6-target-stream-research-v1.json`](../tests/contracts/integration-v6-target-stream-research-v1.json), SHA-256 `dcae07677fc0c0a68c034310f2183c192f9b46ad4002a5293a88213966d28ae2`
- **Status authority:** [roadmap registry](../implementation/roadmap.md#2-status-registry)
- **Status:** accepted development-grade implementation through `TSR-FI-01`; target-aware Promotion deferred

## 1. Outcome and authority

```text
TargetRecipe@1 + exact composition-root materializer
→ reserved discovery TargetBuildTask@1
→ BacktestTargetStreamRef
→ Backtest development execution and analysis
→ StrategyCandidate@3
→ independently reserved Validation target materialization
→ ValidationReport@2
```

Backtest remains the sole economic, terminal, analysis, publication, retention, target-storage, and timeline authority. Research owns discovery declarations and evidence. Validation owns holdout reservation, independent target evidence, and reports. The composition root supplies the exact materializer object. Foundation remains generic CAS/log mechanics. Promotion gains no v6 support.

## 2. Backtest target artifact and repository

The Backtest artifact envelope is `backtest_target_stream@1`. Its payload is exactly:

```python
{
  "producer_context_ref": ArtifactRef,
  "target_stream": PrecomputedTargetStream@1,
}
```

Its nominal ref wire is exactly:

```python
BacktestTargetStreamRef = {
  "type": "backtest_target_stream_ref",
  "artifact_ref": ArtifactRef,
}
```

Backtest exposes:

```text
BacktestTargetStreamRepository.publish(
  producer_context_ref, target_stream
) -> BacktestTargetStreamRef
BacktestTargetStreamRepository.load(
  ref
) -> VerifiedBacktestTargetStream
```

The repository is CAS/exact-read only. There is no Platform owner log for this input artifact. `VerifiedBacktestTargetStream` exposes exactly `ref`, `producer_context_ref`, `target_stream`, and `digest`.

The producer context is part of artifact identity: equal streams with different producer contexts have different refs. Backtest semantic request/run identity binds the target-stream digest, not the producer context or target ref.

## 3. Structural materializer

The composition root supplies an object with exactly:

```text
strategy_artifact: BuildArtifactRef(role=DECISION_SOURCE, immutable identity)
materialize_target(request: Mapping[str, object]) -> Mapping[str, object]
```

The canonical request wire is:

```python
target_materialization_request@1 = {
  "type": "target_materialization_request",
  "schema_version": 1,
  "consumer_ref": ArtifactRef,
  "target_recipe_ref": ArtifactRef,
  "market_bundle_ref": MarketBundleRef,
  "dataset_revision": object,
  "interval_start": object,
  "interval_end": object,
  "parameter_values": object,
  "seed": object,
}
```

The canonical result wire is:

```python
target_materialization_result@1 = {
  "type": "target_materialization_result",
  "schema_version": 1,
  "request_hash": object,
  "strategy_artifact": BuildArtifactRef,
  "input_data_hash": object,
  "target_stream": PrecomputedTargetStream@1,
}
```

No additional request/result fields are permitted. Apart from the required immutable `strategy_artifact` identity, the result contains no owner/workflow/target ref, prepared request, run result, or cache handle. Materialization may read only the immutable cited MarketBundle; network and current/latest APIs are forbidden.

## 4. Research artifacts and dispatch

Research additively defines:

```python
TargetRecipe@1 = {
  "target_key": object,
  "strategy_artifact": BuildArtifactRef,
  "target_schema_hash": object,
  "input_names": object,
}

TargetBuildTask@1 = {
  "experiment_ref": ArtifactRef,
  "trial_declaration_ref": ArtifactRef,
  "target_recipe_ref": ArtifactRef,
}

TargetMaterializationEvidence@1 = {
  "target_build_task_ref": ArtifactRef,
  "trial_declaration_ref": ArtifactRef,
  "target_recipe_ref": ArtifactRef,
  "materialization_request_hash": object,
  "input_data_hash": object,
  "target_stream_ref": BacktestTargetStreamRef,
  "target_stream_digest": object,
  "event_count": object,
}
```

There is one `TargetBuildTask@1` per Trial. Research adds task kind and TaskOutcome witness `TARGET_BUILD`. The existing integrated `TrialDeclaration@1` remains the discovery reservation producer.

Target experiments publish `ExperimentSpec@2`, adding only `target_recipe_ref`. Ordinary and model `ExperimentSpec@1` bytes remain unchanged. `StrategyCandidate@3` adds selected `target_materialization_evidence_ref`. CandidateFamily and ExperimentExecutionManifest field sets remain unchanged. Target-mode dispatch is by exact type/schema only; no inference, coercion, or fallback is permitted.

## 5. Validation artifacts and independence

The existing `out_of_sample` ValidationCase remains the holdout reservation producer. Validation additively defines `ValidationPlan@2`, binding `target_recipe_ref` and `strategy_artifact`, and:

```python
ValidationTargetMaterializationEvidence@1 = {
  "validation_case_ref": ArtifactRef,
  "candidate_ref": ArtifactRef,
  "target_recipe_ref": ArtifactRef,
  "materialization_request_hash": object,
  "input_data_hash": object,
  "target_stream_ref": BacktestTargetStreamRef,
  "target_stream_digest": object,
  "event_count": object,
}
```

Target-aware CaseResult and ValidationReport use schema version 2. The additive public operation is exactly:

```python
validate_target_candidate(
    candidate_ref,
    policy,
    reservation_at,
    foundation,
    sample_ledger,
    materializer,
    backtest,
)
```

The structural `backtest` port adds `publish_target`, `load_target`, and `prepare_target(validation_case_ref, target_ref)` to the existing run/derive/load operations. The composition root may pre-bind the public cash request intent, provider inputs, readers, publisher, and publication root behind `prepare_target`; no generic preparation-input ABI is added. Existing `validate_candidate` and every v1 byte remain unchanged.

Validation must independently materialize after the holdout reservation. Substituting the discovery target ref as OOS is invalid even when the stream values are equal.

## 6. Source-neutral Backtest execution

Backtest additively defines `DeterministicTimelineV2` and `TimelineCursorV2`. V2 consumes market-only `MarketBundleReader` streams plus an embedded verified target stream. Timeline identity binds exactly:

```text
market_bundle_ref,
sorted market stream keys,
target_stream_digest,
window
```

`backtest_execution_input_bundle@6` embeds the canonical target-stream value and uses source-neutral v2 timeline/decision injection. It does not embed the Backtest target ref. Existing execution-input bundles v1-v5, request v1, completed, terminal, analysis, and publication bytes remain unchanged.

The first public profile-specific development operation is:

```text
prepare_cash_target_stream_backtest(
  CashDevelopmentRequestIntent,
  CashDevelopmentProviderInputs,
  BacktestTargetStreamRef,
)
```

There is no strategy-specific preparation operation. Future qualified market adapters may reuse the same Backtest target/timeline authority only under separate contracts.

## 7. Promotion compatibility

Until a separately approved `TSR-PG-01`, every `StrategyCandidate@3` and `ValidationReport@2` ref fails closed as unsupported. Promotion must not coerce, unwrap, reinterpret, or fall back to an older supported version.

## 8. Failure precedence

The exact high-level precedence is:

1. public arg/type;
2. reservation;
3. materializer artifact/request/result;
4. target publish/load/ref/tamper/retention/context/digest;
5. evidence publication;
6. preparation;
7. Backtest terminal/provider;
8. analysis/link;
9. manifest/selection;
10. Validation target substitution/holdout;
11. report;
12. Promotion unsupported.

Each module preserves its existing internal precedence inside the applicable high-level group.

## 9. Commit points and replay

- Reservation is idempotent and remains the gate before materialization/read.
- Research or Validation materialization-evidence publication is that module's commit and prevents rematerialization.
- A target CAS orphan is not Research or Validation evidence.
- Replay recovers and exact-load verifies the first committed evidence/ref, then reconstructs the prepared request/run.
- Replay performs no second sample/materializer-input read, target materialization, economic run, or governance refresh.
- Exact immutable target-CAS loads are required during recovery, and idempotent Backtest preparation may be repeated from the committed target ref solely to reconstruct cache access.

## 10. Repository execution

Each Backtest, Research, and Validation leaf uses an isolated clean branch/worktree and one clean implementation commit. Leaf work does not modify root gitlinks, remote VCS pins, or `uv.lock`. Root fan-in alone updates exact gitlinks, every matching VCS pin, and `uv.lock` together.

Contract approval changes no submodule code, gitlink, VCS pin, or lockfile.

## 11. Compatibility and initial scope

V6 is strictly additive. Initial scope is one development-grade cash golden with fixed one-slice portfolio targets and only `simple_period_return`/`trade_count`. It includes no model combination, decision-grade path, real Binance qualification, real A-share qualification, or Promotion support.

Integration v1-v5 artifacts, schemas, requests, execution bundles, publications, analyses, receipts, decisions, and released behavior remain unchanged.

## 12. Contract acceptance

`TSR-CON-01` is approved by Platform, Backtest, Research, Validation, and Promotion owners at `2026-08-26T03:14:51Z`. Every approval binds exact fixture SHA-256 `dcae07677fc0c0a68c034310f2183c192f9b46ad4002a5293a88213966d28ae2` and the fixture's exact baseline SHAs.

Approval originally made only `TSR-BT-01` READY. The accepted leaf revisions and root fan-in now close the development-grade implementation through `TSR-FI-01`; this remains no market qualification, decision-grade, or target-aware Promotion claim.
