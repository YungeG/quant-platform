# V2-SEAM-01 acceptance receipt

- **Contract fixture SHA-256:** `4d6c764b6e0b6374daab462b8b74ce8c9f75b73b68d96979d3e7d3a99bd441bb`
- **Platform implementation revision:** `84693cfb62d7e5e22ad24701b7ce1893bde0dca1`
- **Backtest accepted revision:** `033344172b24847e73941bb97a06da0490527edf`
- **Research accepted revision:** `51897c2118828febc844e9b21980e31cf0760138`
- **Root `uv.lock` SHA-256:** `dcfeab99dfdf28daa9206d8f94315740d288c7f43df89d6ccc21e415e25101ef`
- **Status:** ACCEPTED

## Accepted binding

- Root Backtest package sources and the Backtest gitlink pin the same remote accepted revision.
- Research builds immutable `FeatureRecipe`, `TrainerRecipe`, `ModelBuildPlan`, `FeatureDatasetManifest`, and `ModelBuildEvidence` values through its public package root.
- The exact Backtest-owned `ModelArtifactRef.artifact_ref_hash` in `ModelBuildEvidence` equals the model request binding, persisted request, completed engine execution context, and verified publication SemanticRun.
- Model substitution fails with `MODEL_BINDING_MISMATCH` before request publication or Attempt creation.
- The existing null-plan and cash-development v1 paths remain unchanged.
- No duplicate model identity, fifth adapter package, private Backtest resolved object, or `PYTHONPATH` bridge is introduced.

## Verification

- Focused Platform model binding and architecture suite: `17 passed`.
- Full Platform workspace against the remote Backtest revision: `294 passed`.
- Root lock check, LSP, pi-lens, Ruff `E4,E7,E9,F,I`, diff checks, and staged Gitleaks: clean.
- Backtest revision is remotely reachable at `refs/heads/platform-v2-model-seam`.
- Research revision is remotely reachable at `refs/heads/main`.
- Protected Integration v1 fixture SHA remains `aebb1be1894d739b06856e012e4343d7835fc1ed0306d8c28a4bfb1d8025b782`.

## Exclusions

This receipt accepts provenance and identity binding only. It adds no feature/model bytes, model loading or inference, tuning/search, generic plugin ABI, model registry, Shadow/Live runtime, positive Promotion, deployment, database, queue, or service.
