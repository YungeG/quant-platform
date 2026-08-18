# SV-MODEL-01 acceptance receipt

- **Contract fixture SHA-256:** `4d6c764b6e0b6374daab462b8b74ce8c9f75b73b68d96979d3e7d3a99bd441bb`
- **Validation accepted revision:** `acf2e36ed009deeee399744508e83af16cdc90d9`
- **Research observation revision:** `9251222d4fa2f3ec548161e6949bf117e30d9348`
- **Backtest accepted revision:** `033344172b24847e73941bb97a06da0490527edf`
- **Status:** ACCEPTED

## Accepted admission

The existing `validate_candidate()` interface now resolves StrategyCandidate@2 and verifies, without caller-supplied duplicate facts:

- FeatureRecipe, TrainerRecipe, ModelBuildPlan, FeatureBuildTask, ModelTrainingTask, FeatureDatasetManifest, and ModelBuildEvidence owner-log nodes;
- completed FeatureBuild and ModelTraining outcomes included exactly once in the ten-task manifest;
- exact `feature_build` and `model_training` reservation records at the original snapshot cutoff;
- selected Trial predeclared Plan binding and TrialSpec resolved Backtest ModelArtifactRef;
- ModelBuildEvidence recipe/data/interval/hash consistency;
- completed Backtest `ModelRequestBinding` equality with the exact `artifact_ref_hash`.

The accepted real model candidate still produces the unchanged adverse out-of-sample `rejected` report and replays the first plan, snapshot, and provider run. Missing training reservation or substituted model-build evidence produces no report.

## Verification

- Focused model admission/core/shell suite: `29 passed`.
- Full Validation package: `53 passed`.
- Full Platform workspace: `305 passed`.
- LSP, pi-lens, Ruff `E4,E7,E9,F,I`, diff, lock, and generated-environment guards: clean.
- Validation and Research revisions are remotely reachable on their `main` branches.
- Protected Integration v1 fixture SHA remains `aebb1be1894d739b06856e012e4343d7835fc1ed0306d8c28a4bfb1d8025b782`.

## Exclusions

Validation adds no model score, quality interpretation, recommendation, threshold, method, feature/trainer execution, positive eligibility, Shadow/Live runtime, deployment, registry, database, queue, service, or model loader/inference behavior.
