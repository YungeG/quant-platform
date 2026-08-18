# RP-MODEL-01 acceptance receipt

- **Contract fixture SHA-256:** `4d6c764b6e0b6374daab462b8b74ce8c9f75b73b68d96979d3e7d3a99bd441bb`
- **Research accepted revision:** `f05c91b2fa75826fb0439ccdcb0d2ae507bff013`
- **Validation ledger revision:** `256e17c2f528f374e1041cd16d7e829f1f120556`
- **Backtest accepted revision:** `033344172b24847e73941bb97a06da0490527edf`
- **Status:** ACCEPTED

## Accepted operation

`execute_model_experiment` is one public Research operation that:

1. publishes immutable Feature/Trainer recipes, ModelBuildPlan, Experiment, tasks, and selection precommit;
2. appends distinct `feature_build` and `model_training` reservations before either builder read;
3. publishes FeatureDatasetManifest and ModelBuildEvidence and closes both build tasks before Backtest request preparation;
4. prepares four model-bound TrialSpecs through the accepted public Backtest seam;
5. exact-covers two build, four Trial, and four Analysis outcomes;
6. publishes a schema-v2 StrategyCandidate carrying the exact ModelBuildEvidence ref;
7. replays the same reservations, build evidence, Backtest requests, outcomes, manifest, and candidate without a second build or economic run.

Feature failure or reservation failure blocks ModelTraining and all Trials without creating a Backtest request. A transient training failure retries through the existing append-only Attempt chain without duplicating either reservation.

## Verification

- Focused model shell/core/ledger suite: `49 passed`.
- Full Research package: `90 passed`.
- Full Platform workspace: `301 passed`.
- LSP, pi-lens, Ruff `E4,E7,E9,F,I`, lock, diff, and generated-environment guards: clean.
- Research and Validation revisions are remotely reachable on their `main` branches.
- Protected Integration v1 fixture SHA remains `aebb1be1894d739b06856e012e4343d7835fc1ed0306d8c28a4bfb1d8025b782`.

## Exclusions

The internal fixture builder is not a public plugin ABI. This receipt adds no standardized feature/model bytes, model loading/inference, framework integration, tuning/search, multiple plans, model registry, fifth adapter package, Shadow/Live runtime, positive Promotion, deployment, database, queue, or service.
