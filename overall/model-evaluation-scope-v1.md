# Model evaluation scope v1

**Scope authorized:** user reply `允许`, recorded in `implementation/ar-09-model-contract-authorization-20261023.md`. This additive contract is frozen by the controlling agent after the design check; this is not a claim that a human signed its future fixture hash. Implementation and acceptance remain separate.

Contract fixture: `tests/contracts/model-evaluation-scope-v1.json`, SHA-256 `4cd02832911dc83cb49c28f25a63a45a5533f4f07eda201bce0ff3a030cac192`.

## 1. Purpose and version dispatch

A model cannot causally evaluate samples preceding its availability. The legacy model Experiment rule also puts its training slice into every Trial axis. Preserve that historical rule; introduce an explicit new Experiment variant rather than changing the meaning of old bytes.

- Existing `ExperimentSpec@1`: ordinary/model; unchanged fields, constructor behavior, canonical bytes and refs.
- Existing `ExperimentSpec@2`: target mode; unchanged.
- New `ExperimentSpec@3`: model evaluation scope. This is not `StrategyCandidate@3` (the separate target candidate).
- Model candidates remain `StrategyCandidate@2`; `ModelBuildPlan`, `FeatureDatasetManifest`, `ModelBuildEvidence` remain @1. Ordinary model Validation remains Report/Plan/CaseResult @1. No new Promotion eligibility or Backtest grade.

The existing public immutable `ExperimentSpec` gains one appended optional field `evaluation_slices: tuple[DataSlice, ...] | None = None`. None emits **no new field** and selects the exact legacy variant. Explicit evaluations select @3 only when an exact ModelBuildPlan exists and target_recipe_ref is absent. Empty, malformed or incompatible inputs are rejected before I/O. No schema inference/downgrade during artifact decoding.

## 2. Declarations and Trial axis

For @3:

1. `data_slices` remains the canonical declaration set of all samples: **exact union** of the Plan training slice and evaluation_slices. Training membership is retained, not relaxed. No undeclared/unused extra slice.
2. evaluation_slices must be an exact nonempty tuple of DataSlice values, canonically sorted and duplicate-free, and each member must be declared in data_slices.
3. Every evaluation interval begins at or after the training interval end. This is necessary, not sufficient: actual model availability can be later, and Backtest still compares the complete actual target SimulationInstant.
4. One `ExperimentSpec.trial_data_slices` projection returns evaluations for @3, otherwise the existing full data_slices. All producer/verifier Trial/task generation reuses the existing `build_trial_declarations` and this projection. No second Trial compiler/checker.
5. Trial parameters, seeds, scenarios, Analysis task expansion, budget, exact cover, attempts, failure evidence, selection and manifest cutoff retain their existing rules.

Thus one Plan, two parameter combinations, two seeds, one evaluation slice and one metric profile produce **2 build +4 Trial +4 Analysis =10 tasks**, even though the declaration set contains both training and evaluation. Historical ten-task examples and existing schema1/2 rules are not rewritten.

## 3. Source, reservation and temporal authority

- FeatureBuild and ModelTraining reserve the exact Plan training slice before their callbacks. Trial reservations cover only generated evaluation Trials. Same-Foundation ledger identity guard remains first and performs no I/O/clock.
- Selection continues its existing reservation over all declared data_slices; this contract does not silently redefine that existing behavior.
- Model artifact training_start/end must still exactly equal the Plan/manifest interval; hashes/schema/model lineage bindings stay exact. Never backdate available_at or invent a shorter training interval.
- Actual request window, target/bar/mark clocks, bundle ref and the declared evaluation slice must agree. The unchanged Backtest public preparation rejects a future model before publishing its request/attempt; no manufactured request refs or new preparation-failure protocol.
- Model OOS has its own explicitly scoped policy/source/reader/window, not the ordinary fixture's unrelated dates. Both discovery/training and OOS remain pre-read reservations. Evaluation is **not automatically blind or independent OOS**.
- Synthetic tests prove source/ref/clock/protocol coherence only; they do not prove actual training/inference, provider/PIT qualification or financial effectiveness.

## 4. Reconstruction and consumers

- Research's existing read-only verifier explicitly decodes Experiment schemas1/2/3, reconstructs the exact canonical @3 value including evaluations, and uses the same task generator for full closure/selection. A legacy envelope containing the new field, or @3 missing it, is rejected; malformed values stay in the existing failure domain.
- Research local-reference parsing admits `experiment_spec@3` **only**; unchanged artifact kinds do not gain @3. Both frozen model inputs and the internal post-build FrozenExperimentInputs admit the explicit @3 model variant while preserving target-mode separation and exact execution/request checks.
- Validation's model Experiment loader and its exact field-set check dispatch explicitly between unchanged @1 and new @3. VerifiedCandidateProvenance may bind Experiment@3. Research remains the semantic reconstruction authority; no Validation→Research import or duplicate compiler.
- The six provenance identities, independently resolved manifest owner/cutoff, full source analyses, valid Backtest metrics, original OOS publication/reservation and original replay refs remain required. No repair/reissue/re-reservation or rerun on replay.

## 5. Failure precedence and compatibility

Existing type/argument, same-ledger, dependency and artifact failure ordering remains. New pure axis/union/chronology/type violations use existing `EXPERIMENT_SPEC_INVALID`; duplicate axes retain `TASK_AXIS_DUPLICATE`; invalid/missing Plan retains `MODEL_BUILD_PLAN_INVALID`. Actual availability rejection remains Backtest `MODEL_ARTIFACT_UNAVAILABLE`. Existing provenance/Validation failure normalization and infrastructure propagation are unchanged.

Old schema1 training membership, canonical payload/ref snapshots, target schema2 dispatch, immutable BT-PORT JSON and all old receipts/hashes remain frozen. Current executable model integration fixtures may use the new explicit variant, but must not advertise their results as re-accepting the old invalid future-model golden. Retain an actual-public old-target negative and legacy wire/membership tests.

## 6. Required acceptance

1. Small RED/GREEN: old wire/ref sentinels; new model-only version and axis/union/chronology rejection; selective local @3 parsing; exact model/ref/hash bindings; honest synthetic preparation and no-write future-model rejection.
2. Synthetic chain: truthful training [0,1000), evaluation [2000,3000), model availability1000; actual target2100/bar2200. OOS [4000,5000), target4100/bar4200. All source refs and declared windows agree; ordinary cash helpers and frozen artifacts remain unchanged.
3. Four-Trial/ten-task exact closure, adverse OOS return/trade count and applicable negative Promotion, replay with original refs/no new reads, missing/substituted evidence and unsupported target Promotion remain.
4. Affected Research/Validation/Promotion and installed-default Root tests; original98 PC and official self/offline-pc after source changes. Existing accepted full Backtest need not repeat for fixture-only/library-consumer changes unless its source changes.
5. Fresh independent review, parent independent execution, protected bytes and default installed cohort evidence; then authorized leaf branch publication, verified remote SHA and clean composition before Platform integration publication.

No real strategy/market/model job, AR10, Live/Shadow runtime, generic registry, DSL, duplicate financial formula or simulator is authorized by this contract.
