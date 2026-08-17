# Integration fan-in implementation plan

- **Normative contract:** [Integration v1 §7–10](../../overall/integration-v1.md#7-state-and-failure-mappings)
- **Mutable status authority:** [Roadmap §2](../roadmap.md#2-status-registry)
- **Provider handoff:** [Backtest Provider Handoff](../backtest-provider-handoff.md)

Fan-in owns composition evidence only. It does not repair leaf modules, add a pass-through adapter, copy Backtest evidence, or record an acceptance receipt before the required provider and package revisions exist.

## Execution DAG

```text
P00-BTA-01 + P00-PLAT-01 ───────────────→ P00-SEAM-01
P00-SEAM-01 + PF-CORE-01 ───────────────→ PLAT-ADM-01

RP-CORE-02 + SV-LEDGER-01 + PF-CORE-01 + BT-PORT-01 ─→ RP-SHELL-01
SV-CORE-01 + SV-LEDGER-01 + PF-CORE-01 + BT-PORT-01 ─→ SV-SHELL-01
PG-CORE-01 + PG-LEDGER-01 + PF-CORE-01 + frozen wires ─→ PG-SHELL-01

RP-SHELL-01 + P00-SEAM-01 ─────────────────────────────→ RP-THIN-02
SV-SHELL-01 + RP-THIN-02 + P00-SEAM-01 ───────────────→ SV-THIN-01
PG-SHELL-01 + SV-THIN-01 + PLAT-ADM-01 ───────────────→ PG-THIN-01

RP-THIN-02 + SV-THIN-01 + PG-THIN-01 ─────────────────→ FI-01
```

`PLAT-ADM-01` freezes the integration-owned evidence-admission behavior once. Research and Validation do not each invent an admission format, and Promotion never creates the fact it later evaluates.

## `P00-SEAM-01` — real public provider seam

### Outcome

Prove the accepted Platform environment can construct/register a public request, execute through the Backtest deep public module, carry exact Envelope bytes through Foundation, reload them through the Backtest verified repository, and derive analysis only from completed publication.

### Inputs

- accepted `P00-BTA-01` public binding and clean Backtest SHA;
- accepted `P00-PLAT-01` Foundation package and root lock;
- existing BT-PORT consumer fixture as the behavioral oracle.

### Golden interface path

```text
Platform-constructed CashDevelopmentRequestIntent with opaque context + public provider facts
→ Backtest preparation/registration and BacktestRequestRef
→ executable BacktestExecutionRequest@2 + configured facade run
→ CompletedPublication | TerminalPublication
→ Foundation exact structural storage/read
→ CanonicalEvidenceRepository verification
→ derive(completed only)
```

No Platform type crosses into Backtest, and no Backtest private Resolver/Runner/Publisher object crosses into Platform.

### Write set

- `tests/integration/test_backtest_public_binding.py`
- P00-SEAM-01 acceptance receipt

No package public root, Foundation interface, provider source, or lockfile changes occur in this node.

### Acceptance

```bash
uv run --locked pytest -q \
  tests/architecture/test_backtest_consumer_port.py \
  tests/integration/test_backtest_public_binding.py
```

Required evidence:

- one completed development run plus real durable `BLOCKED` and `CANCELLED`; Backtest-owned accepted repository evidence must load one durable `FAILED` graph without Platform manufacturing an internal defect;
- opaque Platform context is hash-bound by Backtest without Platform deriving identity;
- completed-only analysis and terminal rejection;
- exact metric profile/publication/execution-result linkage;
- missing, tampered, wrong-type/version, manifest, hash-chain, and retention failures close;
- request replay/cache returns identical semantic evidence without a second economic run;
- imports use accepted public roots only and no evidence/metric logic is copied.

The receipt records the exact Platform revision, accepted Backtest SHA, root lock hash, provider artifact hashes, commands, and result counts. A dirty sibling worktree is never evidence.

## `PLAT-ADM-01` — Backtest evidence admission composition

### Outcome

The integration composition root can admit one verified Backtest publication, analysis, or metric-profile ref into Platform governance exactly once and return its immutable first `LogEntryRef`/`accepted_at`.

### Interface behavior

```text
admit_backtest_evidence(subject_ref, repository, foundation) -> LogEntryRef
```

The operation is intentionally one function at the composition seam:

1. resolve and verify `subject_ref` through the accepted Backtest public repository;
2. construct canonical `BacktestEvidenceAdmission@1 = {subject_ref}`;
3. store its exact Envelope bytes in Foundation;
4. append them to `platform.backtest-evidence-admission.v1` with
   `H("backtest-evidence-admission-v1", subject_ref canonical wire)`;
5. return the first entry; exact replay is idempotent.

There is no caller timestamp. Same event id with different bytes is `LOG_CONFLICT`. Repository verification failure, Foundation failure, wrong subject kind, or ref/subject mismatch returns no admission result.

### Ownership and write set

This is integration composition, not a fifth installable package and not Foundation, Promotion, or Backtest semantics. In this non-deployment v1 slice, the executable composition proof lives only in:

- `tests/support/backtest_evidence_admission.py`
- `tests/integration/test_backtest_evidence_admission.py`
- PLAT-ADM-01 acceptance record

A later deployable application may move the same composition into its entrypoint; that is outside v1 and must not change the wire contract.

### Acceptance

```bash
uv run --locked pytest -q tests/integration/test_backtest_evidence_admission.py
```

Required evidence:

- completed publication, analysis, and metric-profile admission;
- repository verification occurs before Foundation publication;
- exact replay returns the first entry and time;
- conflicting bytes, wrong owner log, wrong ref kind, forged subject, tamper, and retention failure close;
- artifact payload contains only `subject_ref` and no timestamp;
- delayed/replayed later Promotion `PUBLISH` cannot alter the first admission time.

## Contract-first shell fan-out and real fan-in

After Foundation and both ledger interfaces are frozen, the three shell implementations may run concurrently in isolated package worktrees:

| Shell node | Fixture-backed inputs | Produces | Not claimed |
| --- | --- | --- | --- |
| `RP-SHELL-01` | RP core, concrete Foundation/sample ledger, BT-PORT | Research runtime + focused shell tests | real provider or RP-THIN receipt |
| `SV-SHELL-01` | SV core/ledger, frozen Research wires, BT-PORT | Validation runtime + focused shell tests | real Research provenance or SV-THIN receipt |
| `PG-SHELL-01` | PG core/ledger, frozen Validation/admission wires | Promotion runtime + focused shell tests | real admission/report or PG-THIN receipt |

One fan-in owner then serializes real acceptance:

| Acceptance node | Consumes | Produces | Failure returns to |
| --- | --- | --- | --- |
| `RP-THIN-02` | RP shell + provider seam | real Experiment/task/manifest/family/candidate receipt | RP shell or provider seam |
| `SV-THIN-01` | SV shell + real Research candidate + provider seam | real admission/cases/report receipt | SV shell, RP acceptance, or provider seam |
| `PG-THIN-01` | PG shell + real Validation report + admission facts | real status/review/negative-decision receipt | PG shell, SV acceptance, or admission seam |

A fan-in failure does not add duplicate guards to a sibling package. Semantic changes return to the owning SHELL node and focused suite; public spelling reconciliation may remain in the THIN node. Then rerun only the smallest affected fan-in path.

## `FI-01` — whole Platform golden

### Outcome

Prove one immutable chain from frozen Experiment through real Backtest evidence, rejected OOS Validation, and a negative Promotion decision under one clean root lock.

### Golden fixture

```text
2 parameters × 2 seeds = 4 TrialDeclarations
3 completed, 1 durable BLOCKED
4 AnalysisTasks; blocked Trial Analysis is BLOCKED
selected T10-1
OOS simple_period_return = -0.1, trade_count = 1
ValidationReport = rejected
PromotionDecision = needs_more_evidence
```

### FI-specific assertions

FI does not duplicate every leaf mutation. Its own test proves only cross-module facts:

1. every Research/Validation/Promotion ref resolves through the preceding module's published artifact, never a copied fixture record;
2. all admitted Backtest refs resolve through the accepted repository and their first admission entry;
3. the Validation snapshot checkpoint used by the Plan is the same immutable cutoff reconstructed during admission;
4. Promotion governed closure reaches the selected Trial/publication/analysis and the rejected Report without repeated candidate fields;
5. replay of the whole orchestration returns identical semantic artifacts and append receipts without a second economic run or refreshed freshness;
6. one root lock and public-import graph contain no sibling path/editable source, leaf lock, private provider import, or deployment capability.

Detailed malformed task, ledger, terminal, status, review, and admission mutations remain authoritative in their focused leaf/seam suites and run as part of the full release suite.

### Write set

- `tests/integration/test_integration_v1.py`
- FI-01 acceptance receipt

No leaf production source is edited in FI-01.

### Release acceptance

```bash
uv lock --check
uv sync --all-packages --locked
uv run --locked pytest -q
```

Also run JSON/Markdown link/fence guards, public-import/AST guards, LSP/Lens diagnostics, protected-fixture hashes, and cleanliness checks.

The FI-01 receipt records:

- Platform revision and accepted lowercase 40-character Backtest SHA;
- root lock hash and package artifact hashes;
- exact executed commands and per-suite result counts;
- P00-SEAM, PLAT-ADM, RP-THIN, SV-THIN, and PG-THIN receipt refs;
- golden artifact/ref hashes and replay result;
- explicit deferred scope and any residual limitation.

Acceptance fails if a venv, cache, leaf lock, `PYTHONPATH`, sibling path/editable source, dirty provider tree, positive Promotion field, Shadow/Live/deployment import, or unapproved receipt remains.

## Proof ownership

| Risk | Owning proof |
| --- | --- |
| CAS/log/clock/checkpoint integrity | `PF-LOG-01`, `PF-CORE-01` |
| sample reservation and immutable ledger cutoff | `SV-LEDGER-01` |
| task exact cover and deterministic selection | `RP-CORE-02`, `RP-SHELL-01`; real binding in `RP-THIN-02` |
| OOS mapping and report/no-report behavior | `SV-CORE-01`, `SV-SHELL-01`; real provenance/binding in `SV-THIN-01` |
| status/review/freshness and negative decision | `PG-CORE-01`, `PG-LEDGER-01`, `PG-SHELL-01`; real facts in `PG-THIN-01` |
| provider execution/repository/analysis | `P00-SEAM-01` |
| first Backtest governance admission | `PLAT-ADM-01` |
| cross-module provenance, replay, lock/import closure | `FI-01` |

## Exclusions

- provider implementation or approval work;
- a fifth adapter package, deployable application, service, database, queue, or generic DAG;
- copied Backtest evidence, Platform metrics, positive Promotion, Shadow/Live/deployment;
- acceptance from a dirty worktree, unpinned revision, planned receipt, or fixture-only provider simulation.
