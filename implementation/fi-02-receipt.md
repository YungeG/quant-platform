# FI-02 whole-Platform model-build acceptance receipt

- **Contract fixture SHA-256:** `4d6c764b6e0b6374daab462b8b74ce8c9f75b73b68d96979d3e7d3a99bd441bb`
- **Platform golden revision:** `92f320affa1c41afdadab1cb1c0a7ec6b7672105`
- **Backtest accepted revision:** `033344172b24847e73941bb97a06da0490527edf`
- **Foundation revision:** `9d88ed67a84d06c558276f8bae2206b069bcec8f`
- **Research revision:** `d2dd913a1efd23728c7889bd15c894d6cf22ad4e`
- **Validation revision:** `41c35219d227fe5cdb736747b917144f6b8a8c65`
- **Promotion revision:** `966b5984c430ec61c53b15761099d2620ed028e6`
- **Root `uv.lock` SHA-256:** `dcfeab99dfdf28daa9206d8f94315740d288c7f43df89d6ccc21e415e25101ef`
- **Status:** ACCEPTED

## Whole-flow evidence

One Experiment publishes immutable Feature/Trainer recipes and one ModelBuildPlan, reserves the same training interval as two distinct append-before-read events, and closes FeatureBuild and ModelTraining before Backtest request preparation.

The accepted golden proves:

- exactly `2 ModelBuild + 4 Trial + 4 Analysis = 10` outcomes;
- one Backtest-owned `artifact_ref_hash` across ModelBuildEvidence, Trial binding, TrialSpec, request binding, completed engine context, and SemanticRun;
- CandidateFamily remains exactly two fields and StrategyCandidate@2 adds only `model_build_evidence_ref`;
- three completed Trials, one durable BLOCKED Trial, and matching Analysis outcomes;
- unchanged adverse Validation result `rejected`;
- unchanged negative Promotion decision `needs_more_evidence`;
- replay creates no second feature read, training read, Backtest request preparation, economic run, analysis, Validation plan/report, evidence admission, status, review, evaluation, or decision.

## Leaf receipts

- [`BT-MODEL-01`](bt-model-01-receipt.md)
- [`V2-SEAM-01`](v2-seam-01-receipt.md)
- [`RP-MODEL-01`](rp-model-01-receipt.md)
- [`SV-MODEL-01`](sv-model-01-receipt.md)
- [`PG-MODEL-01`](pg-model-01-receipt.md)

## Verification

- Focused whole-Platform v2 golden: `1 passed`.
- Full local Platform workspace at the golden revision: `310 passed`.
- Fresh remote recursive clone at the exact golden revision: `310 passed`.
- Receipt/status guard suite after acceptance documentation: `311 passed`.
- Remote clone checked out every recorded submodule SHA and passed `uv lock --check` without `PYTHONPATH`.
- LSP, pi-lens, Ruff `E4,E7,E9,F,I`, diff, lock, staged Gitleaks, and generated-environment guards: clean.
- Protected Integration v1 fixture SHA remains `aebb1be1894d739b06856e012e4343d7835fc1ed0306d8c28a4bfb1d8025b782`.

## Exclusions

Integration v2 accepts provenance and governance only. It adds no feature/model byte standard, actual model loading or inference, generic callable/plugin/framework ABI, tuning/search, multiple model plans, model registry, positive Promotion, Shadow/Live runtime, credentials, deployment, database, queue, distributed worker, or service.
