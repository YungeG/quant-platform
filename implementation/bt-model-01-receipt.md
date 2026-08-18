# BT-MODEL-01 acceptance receipt

- **Contract fixture SHA-256:** `4d6c764b6e0b6374daab462b8b74ce8c9f75b73b68d96979d3e7d3a99bd441bb`
- **Backtest implementation revision:** `82c83c2f0822bd7a3cff736757f64f29f1fdf94b`
- **Backtest accepted revision:** `033344172b24847e73941bb97a06da0490527edf`
- **Remote branch:** `platform-v2-model-seam`
- **Backtest owner:** `YungeG`
- **Status:** ACCEPTED

## Accepted evidence

- Public `prepare_model_bound_cash_development_backtest` performs point-in-time `ModelRevisionTimeline` selection before request publication or Attempt creation.
- `ModelRequestBinding` records the exact strategy/input name, model key, `timeline_hash`, and Backtest-owned `artifact_ref_hash` without duplicating `ModelArtifactRef`.
- The binding enters request hash, SemanticRun identity, completed engine execution context, canonical cache replay, and repository reconstruction.
- One completed and one durable BLOCKED model-bound run pass; a changed visible revision changes request/SemanticRun identity while a hidden future revision does not.
- Missing, wrong-key, and substituted model evidence fail before any request authority or Attempt directory exists.

## Verification

- Focused provider/model suite: `45 passed`.
- Provider/model/resolution/evidence/integrity/architecture suite: `112 passed`.
- Full isolated Backtest worktree: `1861 passed`.
- LSP and pi-lens diagnostics: clean on all changed files.
- Ruff `E4,E7,E9,F`: clean on all changed Python files.
- Gitleaks working-tree scan: no leaks found.
- Accepted revision is reachable at `refs/heads/platform-v2-model-seam`.

The local `platform/backtest` checkout was not used as acceptance evidence and was not reset. The superproject gitlink pins the remote accepted revision above.

## Exclusions

No model bytes, loading, deserialization, inference callback, training, feature computation, generic plugin ABI, mutable model registry, private resolved-object exposure, Shadow/Live, or deployment is accepted.
