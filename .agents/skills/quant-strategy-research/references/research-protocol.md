# Research Protocol

Read this reference for Execute and Review, or when a Plan needs exact Platform behavior.

## Source of truth

Use repository-root-relative paths when inspecting implementation and contracts:

- System ownership and flow: `README.md`, `overall/design.md`, `CONTEXT.md`
- Accepted integration contracts: `overall/integration-v1.md`, `overall/integration-v2.md`, `overall/integration-v5.md`
- Current completion state: `implementation/roadmap.md`
- Research design and plan: `research-platform/design.md`, `implementation/plans/research.md`
- Validation design and plan: `strategy-validation/design.md`, `implementation/plans/validation.md`
- Backtest architecture: `backtest/docs/architecture/backtest-system-design.md`
- Backtest consumer seam: `implementation/plans/backtest-port.md`

Contract documents and public package roots outrank examples, test fixtures, build outputs, and old plans. Treat `build/lib` copies as generated artifacts, never edit them.

## Public seams

Import only from public package roots.

### Research

`crypto_quant_research` exposes the orchestration operations and common declarations, including:

- `DataSlice`
- `FrozenExperimentInputs`
- `FrozenModelExperimentInputs`
- `TrialExecution`
- `execute_experiment`
- `execute_model_experiment`

Detailed Experiment, selection, and manifest values currently live in the accepted Research integration implementation. Inspect the public root and accepted integration contract before use; do not guess constructor fields from memory.

### Backtest

`crypto_quant_backtest` exposes accepted public operations and values, including:

- concrete `prepare_*_backtest` operations
- `BacktestRuntime`
- `BacktestEvidenceRepository`
- `BacktestAnalysisRuntime`
- nominal completed, terminal, analysis, metric-profile, request, and model refs

A preparation operation is strategy/provider authority. If the public root does not expose a concrete preparation operation for the requested strategy, the request is plan-only. Never substitute direct `ExecutionCaseComposer`, `DeterministicBarEngine`, `AuditableBacktestRunner`, private hydration, or private publication code.

### Validation

`crypto_quant_validation` exposes:

- `SampleConsumptionLedger`
- `Holdout`
- `OosRule`
- `ValidationPolicy`
- `validate_candidate`

Current accepted OOS rule support is deliberately narrow. Inspect `strategy-validation/src/crypto_quant_validation/integration.py` before promising a metric or operator. Do not calculate an unsupported metric locally and attach it to a Validation result.

### Foundation and Promotion

- `crypto_quant_foundation.LocalFoundation` owns generic CAS, append, receipts, entries, and checkpoints.
- `crypto_quant_promotion` consumes governed evidence only when Promotion is explicitly requested.

A CAS write is not published evidence until its designated owner-log append succeeds. Promotion never authorizes Live or deployment.

## Canonical execution sequence

1. Verify accepted workspace pins and use source files, not generated build copies.
2. Freeze all input axes before I/O: hypothesis, strategy definition, data slices, explicit parameter combinations, seeds, scenarios, metric profiles, grade, budget, selection, and holdout.
3. Construct immutable values through existing constructors so duplicate, unsorted, implicit, foreign, or malformed inputs fail before publication.
4. Publish the Experiment declarations and selection declaration before attempts.
5. Reserve each sample through `SampleConsumptionLedger` before the corresponding read or Backtest call.
6. Prepare trials only through concrete public Backtest preparation operations. Backtest owns request registration, request hash, semantic run ID, execution transport, resolved profiles, and bundle semantics.
7. Execute Research. Preserve direct Backtest terminal status and durable evidence; local/provider/storage errors are not fabricated Backtest terminals.
8. Call analysis derivation only for a verified completed publication. Verify metric profile, source publication, and execution-result links.
9. Close the exact Experiment manifest, derive the family, and select deterministically from eligible completed analyses. No manual winner.
10. Freeze the sample ledger and publish the Validation plan before OOS work.
11. Assess holdout integrity, publish the OOS case, reserve the holdout, then run the OOS Backtest.
12. Publish the exact Validation result or an explicit no-report reason.
13. Replay once when practical. Reuse canonical refs and governance time; do not repeat economic execution.

## Failure mapping

Keep these categories distinct:

| Observation | Research/Validation treatment |
| --- | --- |
| Backtest `COMPLETED` | verify, then analysis may run |
| Backtest `BLOCKED` | preserve terminal; downstream analysis blocks; Validation is normally inconclusive |
| Backtest `CANCELLED` | preserve terminal; Validation is normally inconclusive |
| Backtest `FAILED` | preserve durable terminal when returned by Backtest; Validation publishes no successful report |
| Provider/storage/tamper/retention error | local/provider failure; never fabricate a Backtest terminal |
| Missing metric or insufficient trades | inconclusive, never zero |
| Holdout conflict or missing reservation | stop before OOS success |
| Unknown ref/type/version/profile | fail closed; no fallback or downgrade |

Follow the exact failure precedence in the current accepted Research, Backtest, and Validation contracts when producing a formal review.

## Walk-forward without a new contract

Use one independent existing flow per fold:

```text
Fold N discovery/training slice
→ Experiment N
→ Candidate N
→ precommitted Holdout N
→ ValidationReport N
```

Rules:

- Each fold has its own immutable Experiment and candidate selection.
- A fold may not inspect its holdout during feature work, training, parameter selection, or manual review.
- Parameter combinations remain explicit and finite within each fold.
- Model-bound folds use at most the currently accepted model-build capability; do not invent a model loader or adaptive search.
- Cross-fold summaries cite the exact Experiment/Candidate/Validation refs.
- The cross-fold summary is advisory and cannot be admitted to Promotion as a synthetic aggregate.

## Review evidence checklist

A review is evidence-backed only when it verifies:

- exact public nominal or typed refs;
- designated owner-log entries and immutable cutoff/checkpoint;
- Experiment task exact-cover and no post-close reopening;
- candidate selection declaration predates execution;
- completed publication and analysis source links match;
- accepted result grade and metric profile;
- sample reservation coverage and holdout non-overlap;
- no terminal-to-analysis path or zero-filled missing value;
- replay stability and no refreshed governance time;
- no private Backtest imports, mutable provider read, network access, or second simulator.
