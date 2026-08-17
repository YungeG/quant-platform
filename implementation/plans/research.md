# Research implementation plan

- **Normative contract:** [Integration v1 §4, §7, §9](../../overall/integration-v1.md#4-research-integration-rp-thin-02)
- **Mutable status authority:** [Roadmap §2](../roadmap.md#2-status-registry)
- **Module design:** [Research design](../../research-platform/design.md)

Research is one deep experiment module: callers provide a frozen Experiment and execution dependencies; the module owns task identity, append-only attempt evidence, exact closure, family identity, and deterministic selection. It does not expose a scheduler, Backtest internals, or Validation policy.

## Execution DAG

```text
BT-PORT fixture + Integration §4 ─→ RP-CORE-02
RP-CORE-02 + PF-CORE-01 + SV-LEDGER-01 + BT-PORT-01
                                      └─→ RP-SHELL-01
RP-SHELL-01 + P00-SEAM-01 ─────────────→ RP-THIN-02
```

The completed core and fixture-backed shell are implementation inputs, not integrated receipts. `RP-THIN-02` remains after `P00-SEAM-01` as required by P00-CON-01.

## `RP-CORE-02` — implemented Experiment and selection core

### Caller-visible result

Given immutable explicit values, the core can:

```text
build_task_universe(experiment_spec) -> canonical TaskRef tuple
map_backtest_observation(task_ref, observation) -> TaskOutcome
validate_execution_prefix(experiment_spec, entries, manifest_cutoff) -> ExecutionProjection
build_execution_manifest(experiment_spec, outcomes, cutoff_ref) -> ExperimentExecutionManifest
build_candidate_family(experiment_ref, manifest_ref) -> CandidateFamily
select_candidate(family, manifest, policy, verified_analyses) -> Selected | NoSelection
```

Cross-package callers do not import this implementation. The later Research shell and its interface-level tests use it internally; published artifacts are the cross-module interface.

### Frozen invariants

1. Every task-producing axis is finite, canonical, nonempty, and duplicate-free.
2. One Experiment owns every generated Trial and Analysis task; foreign refs fail closed.
3. Attempt ordinals are contiguous and append-only; one task has at most one terminal outcome.
4. A manifest exact-covers the generated universe at its owner-log cutoff. Unrelated interleaved Experiments remain valid after generic chain verification.
5. `CandidateFamily` has exactly `experiment_ref` and `execution_manifest_ref`.
6. Selection uses only eligible completed analyses matching the declared profile, publication, trial, and execution-result links.
7. Rank and tie break are deterministic; no eligible item returns `NoSelection`, never a manual winner.

### Failure precedence

1. `EXPERIMENT_SPEC_INVALID`
2. `TASK_AXIS_DUPLICATE`
3. `TASK_REF_FOREIGN`
4. `ATTEMPT_CHAIN_INVALID`
5. `TASK_OUTCOME_INVALID`
6. `TASK_OUTCOME_MISSING_OR_DUPLICATE`
7. `MANIFEST_CUTOFF_INVALID`
8. `EXPERIMENT_REOPENED_AFTER_CLOSE`
9. `SELECTION_PRECOMMIT_MISSING`
10. `SELECTION_INPUT_INCOMPLETE`
11. `SELECTION_POLICY_MISMATCH`

### Existing implementation evidence

- Production: `research-platform/src/crypto_quant_research/integration.py`
- Tests: `research-platform/tests/test_integration_core.py`

```bash
uvx --python 3.13.5 --from pytest==8.4.2 \
  --with ./backtest/packages/trading-domain \
  --with-editable ./foundation \
  --with-editable ./strategy-validation \
  --with-editable ./research-platform \
  pytest -q -p no:cacheprovider research-platform/tests/test_integration_core.py
```

The suite fixes the 2×2 four-Trial/eight-task universe, three completed trials, one durable BLOCKED trial, blocked downstream Analysis, exact manifest cover, two-field family, valid interleaving, deterministic `T10-1`, stable `NoSelection`, and malformed/foreign/forged-link rejection. The core imports neither Foundation nor Backtest runtime.

## `RP-SHELL-01` — contract-first Research shell implementation

### Outcome

One synchronous Research operation publishes a frozen Experiment, records its task execution, closes an exact manifest, derives the family, and publishes either one deterministic `StrategyCandidate` or an explicit no-selection result. Callers do not coordinate individual CAS writes, log entries, task transitions, or Backtest internals.

### Inputs

- completed `RP-CORE-02`;
- accepted Foundation store from `PF-CORE-01`;
- Validation-owned reservation interface from `SV-LEDGER-01`;
- frozen BT-PORT run/repository/analysis behavior and test support;
- frozen `ExperimentSpec`, `SelectionPolicy`, `SelectionDeclaration`, and composition-root attempt policy.

Attempt policy is operational input only. It does not enter Experiment, task, family, or candidate identity. v1 needs no queue, worker registry, generic DAG, or distributed scheduler.

### Module interface

The package exposes one orchestration operation with equivalent behavior to:

```text
execute_experiment(frozen_inputs, foundation, sample_ledger, backtest) ->
  PublishedStrategyCandidate | PublishedNoSelection
```

The returned result contains published refs and the manifest cutoff; it does not expose mutable registries, Backtest Resolver/Runner/Publisher objects, or internal attempt state.

### Publication order and commit points

1. Validate all frozen inputs with `RP-CORE-02`; perform no I/O on invalid input.
2. Publish `ExperimentSpec`, TrialDeclarations, AnalysisTasks, SelectionPolicy, and SelectionDeclarations before the first relevant task attempt.
3. Before each Trial market-sample read, call `SV-LEDGER-01.reserve()` for that TrialDeclaration. Append failure means no read and no Backtest call.
4. Forward the frozen BT-PORT selector request unchanged and consume only its frozen run/repository/analysis behavior. Opaque `TrialDeclarationRef` request-context binding is owned by `P00-SEAM-01`; the fixture-backed shell derives no provider identity.
5. Append attempt start/close and exactly one terminal `TaskOutcome`. Completed publications alone may enter `derive()`; terminal or local-failure Trials block their Analysis task through `upstream_task_outcome`.
6. Publish `ExperimentExecutionManifest` only after exact-cover replay succeeds at its own `research.execution.v1` entry cutoff.
7. Publish the two-field `CandidateFamily` only after the manifest resolves back to the same Experiment.
8. Before selection reads completed Trial/Analysis evidence, call `SV-LEDGER-01.reserve()` once for every distinct Experiment data slice under the SelectionDeclaration.
9. Replay selection from published inputs and publish `StrategyCandidate`, or return no selection without fabricating a candidate.

All artifact publications use their designated owner log. A CAS write without the matching owner-log entry is not consumed as evidence.

### Failure and retry rules

| Failure | Required effect |
| --- | --- |
| invalid frozen input or foreign ref | no publication and no execution |
| reservation conflict/failure | no corresponding sample read; close started work only with the accepted local/dependency witness |
| pre-request dependency block | `BLOCKED / dependency_block`; no fabricated Backtest terminal |
| Backtest `BLOCKED`, `FAILED`, or `CANCELLED` | same-state Trial outcome with `backtest_terminal`; downstream Analysis is blocked |
| facade/repository/tamper/retention error after attempt policy exhaustion | `FAILED / local_failure`; never a Backtest terminal |
| completed publication with invalid/missing analysis link | Analysis task fails locally; candidate selection cannot consume it |
| manifest exact-cover failure | no manifest, family, selection, or candidate publication |
| selection reservation/read failure | no candidate publication |

Retry projects persisted starts, closes, and outcomes before work resumes. A durable `TaskOutcome` is closed if needed and never re-executed; an incomplete attempt resumes with the same declaration, request ref, reservation event ids, and task identity. Retry never rewrites prior entries or changes CandidateFamily identity.

### Write set

- `research-platform/src/crypto_quant_research/runtime.py`
- minimal Research public-root exports for the orchestration result
- `research-platform/tests/test_research_shell.py`

No fifth adapter package, production Protocol package, or generic workflow framework is introduced. The existing BT-PORT helper remains test-only.

### Acceptance

```bash
uvx --python 3.13.5 --from pytest==8.4.2 \
  --with ./backtest/packages/trading-domain \
  --with-editable ./foundation \
  --with-editable ./strategy-validation \
  --with-editable ./research-platform \
  pytest -q -p no:cacheprovider research-platform/tests/test_research_shell.py
```

Required evidence:

- concrete Foundation owner-log publication and exact replay;
- four Trials/eight tasks, three completed, one durable BLOCKED, and exact manifest cutoff;
- reservation-before-read for every Trial and SelectionDeclaration slice;
- frozen selector request is forwarded without deriving provider identity; `P00-SEAM-01` owns opaque request-context binding;
- completed-only analysis; all three terminal states and exhausted local failure preserve distinct witnesses;
- manifest/family/candidate links match canonical BT-PORT observations;
- hidden, extra, duplicate, foreign, reopened, forged-profile, forged-publication, and forged-execution-hash mutations fail;
- exact replay produces the same semantic artifacts without a second fixture execution;
- package imports only accepted public sibling roots; no private Backtest import.

Passing this node proves the package-local orchestration implementation only. It is not `RP-THIN-02`, real provider evidence, or an integrated receipt.

## `RP-THIN-02` — real Research acceptance

### Outcome

Prove `RP-SHELL-01` runs unchanged through the accepted public Backtest and Foundation seams and publish the RP-THIN-02 receipt required by downstream Validation.

### Inputs

- completed `RP-SHELL-01`;
- accepted `P00-SEAM-01` public binding and provider records;
- accepted root workspace/lock.

### Allowed changes

- `research-platform/tests/test_integrated_research.py`;
- RP-THIN-02 acceptance receipt;
- at most package-local public-name/type reconciliation in `runtime.py` if the accepted provider spelling differs from BT-PORT. Any orchestration, identity, ordering, failure, or schema change returns to `RP-SHELL-01` and its focused suite.

No pass-through adapter or provider wrapper may be added.

### Acceptance

This command applies only after `P00-SEAM-01` has created the declared root workspace and lock.

```bash
uv run --locked pytest -q \
  research-platform/tests/test_research_shell.py \
  research-platform/tests/test_integrated_research.py
```

The real test repeats the shell golden through public roots, proves reservation-before-read, request context binding, completed/terminal/local-failure mappings, provider verification/tamper/retention behavior, exact replay without a second economic run, and records the accepted provider SHA and root lock hash.

## Dependencies

| Type | Node/artifact | Why |
| --- | --- | --- |
| Contract | Integration v1 §4 and `RP-CORE-02` | Freezes task identity, witnesses, exact closure, family, and selection behavior for `RP-SHELL-01`. |
| Contract | `SV-LEDGER-01` | Research is a reservation producer but never owns event-id, append, cutoff, or overlap semantics. |
| Contract | `PF-CORE-01` | Supplies exact Research artifact publication and execution-log cutoffs. |
| Contract | `BT-PORT-01` | Supplies fixture-backed behavior for shell implementation without a provider claim. |
| Contract | `P00-SEAM-01` | Replaces fixture behavior only for `RP-THIN-02` real acceptance. |
| Evidence | accepted completed/terminal/analysis provider records | Required only by `RP-THIN-02`. |
| Write conflict | Research runtime/public root | One writer owns `RP-SHELL-01`; real acceptance follows after focused GREEN. |
| Write conflict | integrated test/receipt | `RP-THIN-02` is serialized by the fan-in owner. |

## Exclusions

- Foundation implementation, Backtest orchestration internals, or duplicate evidence verification;
- Validation conclusions or Promotion policy;
- ModelBuild, non-null model plan, feature/trainer interface, adaptive/range search, cross-Experiment family;
- queue, worker service, database, generic DAG engine, manual winner, Shadow/Live/deployment.
