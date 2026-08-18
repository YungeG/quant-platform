# Integration v2 Research model-build plan

> **Mutable status authority:** [roadmap registry](../roadmap.md#2-status-registry). This plan contains no editable node status.

## `MB-CORE-01` — pure declarations and exact task universe

### Outcome

Research can construct immutable FeatureRecipe, TrainerRecipe, ModelBuildPlan, FeatureBuildTask, ModelTrainingTask, FeatureDatasetManifest, and ModelBuildEvidence values and derive a deterministic ten-task Experiment universe.

### Interface and invariants

```text
build_task_universe(experiment) -> exact ordered TaskRefs
validate_model_build(plan, feature_recipe, trainer_recipe, feature_manifest, model_artifact)
  -> ModelBuildEvidence
```

The existing Research module remains deep: callers provide one Experiment and receive canonical values; they do not orchestrate validation steps. A null plan retains the v1 eight-task identity byte-for-byte. A non-null plan adds exactly one FEATURE_BUILD and one MODEL_TRAINING task before Trial/Analysis ordering.

### Failure precedence

1. `MODEL_BUILD_PLAN_INVALID`
2. `TASK_AXIS_DUPLICATE`
3. `MODEL_TRAINING_BLOCKED`
4. `MODEL_TRAINING_FAILED`
5. `MODEL_BINDING_INVALID`
6. existing Research core failures

### Acceptance

- pure golden for null-plan compatibility and one-plan ten-task exact cover;
- canonical ordering and hash mutation coverage;
- wrong recipe/interval/hash/model key/schema/revision failures;
- public surface contains values/functions only, no Protocol/registry/factory/framework.

### Dependencies

| Type | Node/artifact | Why |
| --- | --- | --- |
| Contract | V2-CON-01 schemas | freezes values consumed by shell/provider work. |
| Contract | Backtest `ModelArtifactRef` | ModelBuildEvidence embeds the owner type. |
| Write conflict | Research integration/public root | one writer extends the task universe and exports. |

### Exclusions

- I/O, sample ledger, Backtest run, actual feature matrix/model bytes, Validation or Promotion.

## `RP-MODEL-01` — offline build shell and model-bound Trials

### Outcome

One Research operation publishes the Feature/Trainer recipes and Plan before work, reserves the training slice before each read, closes FeatureBuild and ModelTraining tasks, binds the resulting model evidence into every Trial, and publishes an exact ten-task manifest/candidate.

### Interface and invariants

```text
execute_model_experiment(frozen_inputs, foundation, sample_ledger, builder, backtest)
  -> PublishedStrategyCandidate | PublishedNoSelection
```

This is one deep orchestration interface, not public step-by-step choreography. The builder seam is internal to the shell contract and remains fixture-backed until a second concrete implementation justifies a production port. Real fan-in consumes accepted build observations and the public Backtest model seam directly; no fifth adapter package is added.

Publication order:

1. Experiment, recipes, Plan, SelectionDeclaration;
2. FeatureBuild start → `feature_build` reservation → FeatureDatasetManifest/outcome;
3. ModelTraining start → `model_training` reservation → ModelBuildEvidence/outcome;
4. model-bound Trial/Analysis tasks;
5. exact manifest, family, selection, candidate.

A replay reuses the first reservations, build evidence, request refs, outcomes, and candidate. A failed FeatureBuild blocks ModelTraining and all Trials. A failed ModelTraining blocks all Trials. No blocked build produces a Backtest request.

### Acceptance

- fixture shell: ten-task golden, reservation-before-read, retry/replay, dependency-block mapping;
- real fan-in: Backtest-selected `artifact_ref_hash` equals ModelBuildEvidence and TrialSpec binding;
- null-plan v1 golden remains unchanged;
- import guard rejects private Backtest/model framework imports.

### Dependencies

| Type | Node/artifact | Why |
| --- | --- | --- |
| Contract | MB-CORE-01 | supplies immutable declarations and exact-cover rules. |
| Contract | existing Foundation and Validation ledger | supplies owner-log publication and reservation mechanics. |
| Contract | BT-MODEL-01 | supplies point-in-time model-aware Backtest execution. |
| Evidence | accepted model build observation | closes real rather than fixture-only acceptance. |
| Write conflict | Research runtime/public root | one package writer integrates build and trial execution. |

### Exclusions

- generic trainer/plugin ABI, tuning/search, multiple model plans, cross-Experiment family, model loading/inference implementation.
