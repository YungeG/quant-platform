# Platform Integration v2 — Model-build provenance

- **Scope:** one non-null Research model-build plan, immutable Feature/Trainer recipes, point-in-time Backtest model identity, and unchanged negative Validation/Promotion fan-in
- **Predecessor:** [Integration v1](integration-v1.md) and [`FI-01`](../implementation/fi-01-receipt.md)
- **Status authority:** [roadmap registry](../implementation/roadmap.md#2-status-registry)

## 1. Outcome and ceiling

```text
Frozen Experiment
→ one predeclared FeatureBuild task
→ one predeclared ModelTraining task
→ one Backtest-owned ModelArtifactRef
→ Trials whose execution evidence binds that exact model identity
→ existing Analysis / Candidate / Validation / negative Promotion chain
```

V2 adds model-build provenance, not a general machine-learning platform. It supports exactly zero or one `ModelBuildPlan` per Experiment, one immutable Feature recipe, one immutable Trainer recipe, and one logical model lineage. It adds no plugin registry, framework ABI, model loader, remote trainer, hyperparameter search, adaptive/range search, cross-Experiment family, positive Promotion, Shadow, Live, credentials, deployment, database, queue, or object-store writer.

Backtest remains the sole authority for runtime model visibility and point-in-time revision selection. Platform never duplicates `ModelArtifactRef` or `ModelRevisionTimeline`; it publishes Research evidence that contains the accepted Backtest public value.

## 2. Ownership

| Module | Owns in v2 | Does not own |
| --- | --- | --- |
| Research | Feature/Trainer recipes, ModelBuildPlan, build tasks/outcomes, FeatureDatasetManifest, ModelBuildEvidence, Trial dependency binding | runtime model visibility, Backtest economics, Validation conclusion |
| Validation | `feature_build` and `model_training` sample reservations and existing holdout integrity | feature computation or training semantics |
| Backtest | `ModelArtifactRef`, `ModelRevisionTimeline`, model-aware request/runtime evidence, SemanticRun identity | offline build orchestration or candidate selection |
| Foundation | unchanged generic CAS, append, receipts, checkpoints | Feature/Trainer decoding or model semantics |
| Promotion | governed status/review projection over the expanded immutable graph | model building, model loading, positive eligibility |

## 3. Research declarations

### 3.1 FeatureRecipe@1

```python
FeatureRecipe@1 = {
  feature_key: str,
  feature_code_hash: "sha256:<64 lowercase hex>",
  feature_schema_hash: "sha256:<64 lowercase hex>",
  input_names: tuple[str, ...],  # nonempty, unique, lexicographically sorted
}
```

A FeatureRecipe identifies one immutable feature transformation contract. It contains no callable, module path, framework object, data bytes, endpoint, filesystem path, or mutable registry handle.

### 3.2 TrainerRecipe@1

```python
TrainerRecipe@1 = {
  trainer_key: str,
  training_code_hash: "sha256:<64 lowercase hex>",
  model_key: str,
  hyperparameters: canonical object,
}
```

A TrainerRecipe identifies one immutable training contract and one logical Backtest model lineage. Hyperparameters are explicit canonical values; no defaults, range, search space, callback, estimator object, or framework loader is permitted.

### 3.3 ModelBuildPlan@1

```python
ModelBuildPlan@1 = {
  feature_recipe_ref,
  trainer_recipe_ref,
  training_slice: DataSlice,
  seed: int,
}
```

An Experiment has `model_build_plan = null | Ref[ModelBuildPlan@1]`. V2 permits at most one non-null plan. Recipes and the Plan are published before the Experiment, so the Experiment content-addresses the immutable Plan without a recursive `ExperimentRef ↔ ModelBuildPlanRef` identity cycle. FeatureBuild/ModelTraining tasks bind both `experiment_ref` and `model_build_plan_ref`.

The training slice must be one of the consuming Experiment's declared data slices. Its exact interval is reserved before each read under Validation-owned sample semantics. A content-identical Plan may be referenced by another Experiment; execution/task identity remains Experiment-specific.

## 4. Build evidence and task universe

```python
FeatureBuildTask@1 = {
  experiment_ref,
  model_build_plan_ref,
}

ModelTrainingTask@1 = {
  experiment_ref,
  model_build_plan_ref,
  feature_build_task_ref,
}
```

```text
ModelBuild(E) =
  {}                                              if model_build_plan is null
  {FeatureBuildTask(E), ModelTrainingTask(E)}     otherwise

U(E) = ModelBuild(E) ∪ Trial(E) ∪ Analysis(E)
```

A non-null v2 golden with four Trials and one metric profile therefore has `2 ModelBuild + 4 Trial + 4 Analysis = 10` exact-cover tasks.

The existing `TaskRef`, attempt chain, failure precedence, manifest cutoff, and exact-cover rules remain additive. `TaskRef.kind` adds only `FEATURE_BUILD` and `MODEL_TRAINING`.

Two completed witnesses are added:

```text
feature_dataset_manifest(feature_dataset_manifest_ref)
model_build_evidence(model_build_evidence_ref)
```

Feature failure blocks ModelTraining through the existing `upstream_task_outcome` witness. ModelTraining failure blocks every model-bound Trial through the same witness. No failed build may produce a Backtest request or a fabricated Backtest terminal.

## 5. Published build artifacts

### 5.1 FeatureDatasetManifest@1

```python
FeatureDatasetManifest@1 = {
  model_build_plan_ref,
  dataset_revision,
  interval_start,
  interval_end,
  feature_schema_hash,
  training_data_hash,
  row_count,
}
```

The manifest is provenance evidence, not a feature matrix transport. V2 does not standardize model/feature bytes or an object-store format. `training_data_hash` binds the exact data consumed by the Trainer recipe; `row_count` is a positive integer and is never used as proof of sample completeness.

### 5.2 ModelBuildEvidence@1

```python
ModelBuildEvidence@1 = {
  model_build_plan_ref,
  feature_dataset_manifest_ref,
  model_artifact: Backtest.ModelArtifactRef,
}
```

The embedded Backtest public value must satisfy:

- `model_key == TrainerRecipe.model_key`;
- `training_data_hash == FeatureDatasetManifest.training_data_hash`;
- training interval exactly equals the Plan training slice;
- `training_code_hash == TrainerRecipe.training_code_hash`;
- `feature_schema_hash == FeatureRecipe.feature_schema_hash`;
- `available_at` is not before ModelTraining publication;
- v2 genesis uses `supersedes_revision_id = null`.

The Platform artifact is owner-log evidence. The embedded Backtest value is not a second Domain `ArtifactRef` and is not separately admitted as Backtest run evidence.

## 6. Sample reservations

The existing Validation-owned vocabulary already includes `feature_build` and `model_training`; v2 activates it:

| Producer | Coverage | Purpose |
| --- | --- | --- |
| `FeatureBuildTask@1` | exact Plan training slice before feature input read | `feature_build` |
| `ModelTrainingTask@1` | exact Plan training slice before training-data read | `model_training` |

Both reservations are append-before-read and replay-idempotent. Feature and training reservations are distinct events even when their intervals match. Missing, conflicting, or failed append blocks the corresponding read. Neither reservation proves absence of uninstrumented reads.

## 7. Trial and Backtest binding

A model-bound TrialDeclaration carries exactly one binding:

```python
model_input_bindings = ((TrainerRecipe.model_key, model_build_evidence_ref),)
```

`BacktestTrialSpec.resolved_model_refs` carries the exact embedded Backtest `ModelArtifactRef` selected from that evidence. The Backtest public preparation seam must:

1. accept only public `ModelArtifactRef` / `ModelRevisionTimeline` values;
2. select point-in-time visibility using the existing Backtest authority;
3. bind selected `artifact_ref_hash` and `timeline_hash` into request/runtime evidence and SemanticRun identity;
4. reject missing, future, conflicting, wrong-key, wrong-schema, or substituted model evidence before Attempt creation;
5. expose no model bytes, loader, callback, framework object, private Resolver, or mutable registry.

V2 acceptance requires Backtest evidence that the selected model identity is part of Strategy invocation evidence. It does not claim a generic model-inference ABI; model loading/execution waits until a second concrete strategy requires a real seam.

## 8. Candidate, Validation, and Promotion

`ExperimentExecutionManifest` exact-covers all ten tasks. `CandidateFamily` remains exactly `{experiment_ref, execution_manifest_ref}`.

`StrategyCandidate@2` is additive only by provenance:

```python
StrategyCandidate@2 = {
  # unchanged v1 fields
  model_build_evidence_ref,
}
```

The selected Trial's binding, TrialSpec resolved model ref, completed ModelTraining outcome, and Candidate model ref must all resolve to the same `ModelBuildEvidence` and Backtest `artifact_ref_hash`.

Validation adds no new method. Admission verifies the model-build chain and both training reservations before publishing the existing evidence-integrity and OOS cases. OOS thresholds and report vocabulary remain unchanged.

Promotion's governed closure additionally follows:

```text
StrategyCandidate
→ ModelBuildEvidence
→ ModelBuildPlan
→ FeatureRecipe + TrainerRecipe
→ FeatureDatasetManifest
→ completed FeatureBuild / ModelTraining outcomes
```

All are Platform owner-log facts. Promotion remains negative-only and cannot interpret model quality beyond the accepted ValidationReport and policy.

## 9. Failure precedence

1. `MODEL_BUILD_PLAN_INVALID` — malformed, foreign, duplicate, or result-tuned declaration.
2. `SAMPLE_RESERVATION_FAILED` — required feature/training append failed; no corresponding read.
3. `FEATURE_BUILD_FAILED` — feature observation or manifest fails its recipe/Plan links.
4. `MODEL_TRAINING_BLOCKED` — FeatureBuild did not complete.
5. `MODEL_TRAINING_FAILED` — Trainer output or ModelArtifactRef provenance mismatch.
6. `MODEL_BINDING_INVALID` — Trial/Candidate/TrialSpec/build evidence disagree.
7. Backtest public model failure code — point-in-time model evidence rejected before Attempt.
8. Existing v1 Trial, Analysis, Validation, Promotion, Foundation, and repository precedence.

A v2 build failure is never rewritten as a Backtest terminal, zero-valued metric, Validation success, or Promotion status.

## 10. Acceptance golden

```text
1 ModelBuildPlan
1 FeatureBuild completed
1 ModelTraining completed
4 Trials: 3 COMPLETED, 1 durable BLOCKED
4 Analysis tasks: 3 COMPLETED, 1 upstream BLOCKED
selected Trial binds the one ModelBuildEvidence
OOS simple_period_return = -0.1, trade_count = 1
ValidationReport = rejected
PromotionDecision = needs_more_evidence
```

Whole-flow replay returns the same build, model, Candidate, Validation, admission, and Promotion refs without a second feature read, training read, economic run, or refreshed governance time.

## 11. Explicit exclusions

- actual feature matrix wire format or model byte format;
- Python callable/Protocol/plugin ABI, registry, factory, dynamic import, framework SDK, remote trainer, model server, filesystem/object-store loader;
- more than one ModelBuildPlan or model lineage per Experiment;
- tuning, hyperparameter/range/adaptive search, cross-Experiment ranking/family, walk-forward training, feature selection, capacity/bootstrap/selection-bias methods;
- positive Promotion, Shadow, Live, credentials, deployment, database, queue, distributed workers;
- any claim that v2 model identity changes economic behavior before a concrete model-consuming strategy seam is separately accepted.
