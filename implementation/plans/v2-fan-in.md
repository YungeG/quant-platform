# Integration v2 downstream and fan-in plan

> **Mutable status authority:** [roadmap registry](../roadmap.md#2-status-registry). This plan contains no editable node status.

## `SV-MODEL-01` — model-build provenance admission

### Outcome

Validation consumes the real model-bound StrategyCandidate, verifies its completed FeatureBuild/ModelTraining chain and exact training reservations, then runs the unchanged evidence-integrity/OOS plan and publishes the existing report vocabulary.

### Interface and invariants

`validate_candidate()` remains the deep external interface. V2 extends graph resolution only; callers do not supply duplicate model facts. Validation follows Candidate → ModelBuildEvidence → Plan/recipes/feature manifest/outcomes and requires:

- exact selected Trial binding and TrialSpec Backtest model ref;
- completed build outcomes in the Experiment manifest;
- exact `feature_build` and `model_training` reservations at the snapshot cutoff;
- no overlap with the declared OOS holdout;
- unchanged adverse OOS mapping and report result.

### Acceptance

- real model-bound Research candidate yields rejected adverse OOS report;
- missing/foreign/substituted build evidence or reservation yields no report;
- replay reuses the first snapshot/plan/provider run;
- no new Validation method, threshold, model score, recommendation, or model interpretation.

### Dependencies

| Type | Node/artifact | Why |
| --- | --- | --- |
| Contract | RP-MODEL-01 | supplies the real model-build graph. |
| Contract | existing Validation ledger/core | owns reservations and report semantics. |
| Evidence | V2-SEAM-01 | proves selected model identity is Backtest-bound. |
| Write conflict | Validation runtime/integrated test/receipt | one package writer. |

### Exclusions

- feature/trainer execution, model quality scoring, extra validation methods, positive eligibility.

## `PG-MODEL-01` — governed model-build closure

### Outcome

Promotion consumes the real SV-MODEL report and expands governed closure through ModelBuildEvidence, Plan, recipes, FeatureDatasetManifest, and completed build outcomes while preserving negative-only decisions and first-publication freshness.

### Acceptance

- exact model-build owner-log facts resolve once;
- delayed status publication cannot refresh recipe/build/model evidence age;
- missing/revoked/stale build evidence remains negative;
- deterministic `needs_more_evidence` golden;
- structural guard excludes positive/Shadow/Live/deployment and model interpretation.

### Dependencies

| Type | Node/artifact | Why |
| --- | --- | --- |
| Contract | SV-MODEL-01 | supplies accepted Validation provenance. |
| Contract | existing Promotion core/ledger | owns status/review/freshness semantics. |
| Evidence | model-build publication entries | required for real governed closure. |
| Write conflict | Promotion runtime/integrated test/receipt | one package writer. |

### Exclusions

- model approval score, deployment, registry, mutable status, decision supersession.

## `FI-02` — whole Platform model-build golden

### Outcome

One clean remote-reachable revision proves the v2 ten-task Experiment, exact build/Backtest model identity, adverse Validation, negative Promotion, and whole-flow replay under one root lock.

### FI-specific acceptance

1. FeatureRecipe/TrainerRecipe/Plan publish before build work.
2. Both training reservations precede their reads and reuse first entries.
3. ModelBuildEvidence, Trial binding, TrialSpec, Backtest invocation evidence, and SemanticRun bind one `artifact_ref_hash`.
4. Manifest exact-covers ten tasks; CandidateFamily remains two fields.
5. Validation uses the original build/reservation cutoff; Promotion closure reaches all model artifacts.
6. Replay creates no second feature read, training read, economic run, admission, status, review, or decision.
7. Root lock, public imports, fixture hashes, docs, LSP/Lens/Gitleaks, and remote clean clone pass.

Detailed malformed contracts remain in owning focused suites.

### Dependencies

| Type | Node/artifact | Why |
| --- | --- | --- |
| Contract | RP-MODEL-01, SV-MODEL-01, PG-MODEL-01 | all vertical module outcomes must exist. |
| Contract | V2-SEAM-01 | real Backtest model binding is mandatory. |
| Evidence | all v2 receipts and remote revisions | fixtures cannot close FI-02. |
| Write conflict | root golden/status/receipt/release | serialized release owner. |

### Exclusions

- model bytes/loader/inference ABI, tuning/search, walk-forward training, positive Promotion, Shadow/Live/deployment.
