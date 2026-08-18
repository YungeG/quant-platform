# PG-MODEL-01 acceptance receipt

- **Contract fixture SHA-256:** `4d6c764b6e0b6374daab462b8b74ce8c9f75b73b68d96979d3e7d3a99bd441bb`
- **Promotion accepted revision:** `966b5984c430ec61c53b15761099d2620ed028e6`
- **Validation provenance revision:** `41c35219d227fe5cdb736747b917144f6b8a8c65`
- **Research provenance revision:** `d2dd913a1efd23728c7889bd15c894d6cf22ad4e`
- **Backtest accepted revision:** `033344172b24847e73941bb97a06da0490527edf`
- **Status:** ACCEPTED

## Accepted governance

Promotion keeps the existing `evaluate_case()` interface and negative-only decision vocabulary while extending governed closure through:

- ModelBuildEvidence, ModelBuildPlan, FeatureRecipe, TrainerRecipe, and FeatureDatasetManifest;
- FeatureBuildTask and ModelTrainingTask plus their completed manifest outcomes;
- Experiment model-plan binding, selected Trial plan binding, TrialSpec resolved model ref, and completed Backtest ModelRequestBinding;
- exact owner-log publication coordinates and first-publication freshness for every added node.

The real rejected model-aware Validation report deterministically yields `needs_more_evidence` and replays without new status, review, evaluation, or decision entries. Revoked model-build evidence remains negative (`NOT_ELIGIBLE` / `rejected`) with `EVIDENCE_REVOKED`; delayed status registration cannot rejuvenate the original owner-log publication time.

## Verification

- Focused integrated/core Promotion suite: `21 passed`.
- Full Promotion package: `65 passed`.
- Full Platform workspace: `308 passed`.
- LSP, pi-lens, Ruff `E4,E7,E9,F,I`, diff, lock, and generated-environment guards: clean.
- Promotion, Validation, and Research revisions are remotely reachable on their `main` branches.
- Protected Integration v1 fixture SHA remains `aebb1be1894d739b06856e012e4343d7835fc1ed0306d8c28a4bfb1d8025b782`.

## Exclusions

Promotion adds no model score, interpretation, approval threshold, recommendation, positive eligibility, decision supersession, Shadow/Live runtime, deployment, registry, credentials, database, queue, service, model bytes, or model loader/inference behavior.
