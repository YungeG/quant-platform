# Backtest Platform Integration Extension Register

- **Status:** Backtest extension closure accepted; active input to Platform `P00-BTA-01` / `P00-SEAM-01`, not itself a Platform seam receipt
- **Assessment baseline:** accepted clean Backtest package revision `9e5937895d7559b8537a4595d73b6aabc94f6f13`; every `BT-GAP-*` row is Backtest-PASSED; real Foundation binding and Platform fan-in remain open
- **Prior assessed baselines:** `1bcec4e754b2ebc0a49ef4124cbc65c25c017951`, `b47409b54f6ba0cb112171b6c454c97bc803cca3`, `2a62b4af155a4e8d13d5afef04a0d4f6482fe7e6`
- **Scope:** capabilities required by Platform Integration v1 at the Backtest seam
- **Write boundary:** this document records Platform consumer needs only; Backtest implementation remains owned by the Backtest repository
- **Provider handoff:** [Backtest Provider Handoff](backtest-provider-handoff.md)

Backtest product completion and Platform integration acceptance are different scopes. The accepted revision now includes the shared ref, versioned execution-input hydration and production composition, deep public facade, publication refs, structural reader, completed-only analysis, verified repository, additive v2 completed-evidence closure, and clean package receipt. The maintainer worktree may remain dirty because of its pre-existing `.gitignore` change, but BT-GAP-08 was proved independently in a clean detached worktree at the accepted SHA. The historical `BT-GAP-*` identifiers name integration extensions, not defects in Backtest economics or its completed roadmap.

## 1. Existing capability we should reuse

Backtest already provides the hard economic and evidence foundations:

- canonical `ArtifactEnvelope` bytes with content/source hashes;
- deterministic `BacktestRequest`, semantic-run identity, isolated Attempts, retry-from-start, and validated cache hits;
- explicit `COMPLETED | BLOCKED | FAILED | CANCELLED` outcomes;
- atomic Attempt evidence and canonical completed-result publication;
- execution-result hashing, integrity evaluation, tamper detection, retention/rebuild evidence, and fail-closed publication;
- development/decision result grades and structurally false deployment authorization;
- installable Domain, Market Data, Trading, and Backtest packages in one workspace/lock.

Platform must not replace these with a second simulator, profit/loss implementation, evidence verifier, terminal model, or metrics implementation.

## 2. Platform-required extensions in Domain/Backtest public roots

| ID | Required capability | Current evidence | Gap / acceptance target |
| --- | --- | --- | --- |
| `BT-GAP-01` | Shared `ArtifactRef` | PASSED: Domain exports immutable `ArtifactRef`; exact Platform wire, golden, and unchanged Envelope v1 bytes are accepted. | P00 clean-SHA/package receipt only. |
| `BT-GAP-02` | Deep public execution facade | PASSED: `BacktestRuntime.run(request)` is the sole Platform-facing operation; orchestration, profile selection, execution, evidence, cache mirroring, and durable terminal refs remain Backtest-owned. | P00 real provider construction and Foundation binding only. |
| `BT-GAP-03` | Public verified evidence repository | PASSED: `BacktestEvidenceRepository` loads completed, terminal, and analysis refs from structural-reader `source_bytes`, verifies the full reachable graph, and freezes all seven `PORT_*` failures. | P00 Foundation reader conformance and real provider mutation suite only. |
| `BT-GAP-04` | Completed and terminal run refs | PASSED: completed returns `BacktestCanonicalPublicationRef`; terminals return bare Domain `ArtifactRef`; `RunPublicationRef` is their direct union. | P00 provider binding must recover `BLOCKED | FAILED | CANCELLED` through verified repository loading; provider/storage failures remain outside the union and terminals never fabricate metrics. |
| `BT-GAP-05` | Completed-only analysis runtime | PASSED: `BacktestAnalysisRuntime.derive()` accepts the explicit verified completed v1/v2 union, publishes immutable `backtest_analysis@1`, and returns only `AnalysisArtifactRef`. | P00 real completed/terminal binding only. |
| `BT-GAP-06` | Minimum v1 analysis fields | PASSED: the passive v1 profile and analysis schemas freeze canonical return/null, authoritative Fill count, result grade, metric-profile ref, source publication ref, and source execution-result hash. | P00 fixture-to-real-output comparison only. |
| `BT-GAP-07` | Structural reader injection | PASSED: Backtest exports the exact narrow `ArtifactEnvelopeReader.read(*, ref) -> ArtifactReadResult` Protocol. | Platform Foundation conformance and P00 fan-in remain; Backtest retains all semantic decoding and verification. |
| `BT-GAP-08` | P00 acceptance revision | PASSED: clean accepted revision `9e5937895d7559b8537a4595d73b6aabc94f6f13`; all five packages build/install from one lock, 1715 tests and 106 import-boundary files pass, and exact package hashes are recorded. | Platform consumes this immutable SHA in `P00-BTA-01`; a dirty sibling worktree is not evidence. |

## 3. Accepted Platform contract reconciliations

These decisions are normative in [Platform Integration v1](../overall/integration-v1.md). They do not ask Backtest to absorb Platform semantics and do not close any `BT-GAP-*` row.

### `PLAT-REC-01` — request ownership: resolved

```text
Platform integrated shell constructs public BacktestRequest
→ opaque TrialDeclarationRef or ValidationCaseRef encoded in public context/experiment_id
→ Backtest validates, normalizes, registers, and returns BacktestRequestRef
→ Backtest owns request hash, SemanticRunId, execution, publication, and evidence
```

Backtest imports no Research or Validation type. Platform derives no Backtest identity and composes no Backtest internal object.

### `PLAT-REC-02` — governance publication time: resolved

Backtest proves evidence identity, integrity, retention, and lineage. The Platform composition root then publishes `BacktestEvidenceAdmission@1 = { subject_ref }` through generic Foundation mechanics to `platform.backtest-evidence-admission.v1`. The first Foundation-assigned `accepted_at` is the immutable Platform-governance residency anchor.

Freshness therefore measures Platform governance residency, not Backtest execution age. A delayed first admission begins residency when accepted; replayed admission or a delayed Promotion status event cannot rejuvenate it.

### `PLAT-REC-03` — additive execution-input transport: resolved

Platform preserves the embedded public `BacktestRequest@1` bytes and hashes and introduces one Backtest-owned additive execution request for transport:

```text
BacktestExecutionRequest@1 = {
  schema_version: 1,
  request: BacktestRequest,           # exact immutable BacktestRequest@1
  execution_input_bundle_ref: ArtifactRef,
}
```

BT-GAP-02B freezes the public names as `BacktestExecutionRequest@1`, `materialize_execution_input_bundle`, and `backtest_execution_input_bundle@1`. Domain owns `ArtifactEnvelope` and `ArtifactRef`; Backtest owns the bundle schema, public materializer, decoder, and semantic validation.

Backtest-owned provider code calls the materializer. Platform does not construct or understand the internal initial-financial-state template; it receives the opaque bundle envelope, stores only that envelope through `Foundation.put()`, and embeds the returned Domain `ArtifactRef` in the execution transport passed by value. The transport itself is not stored in CAS and has no second ref/hash. Platform may not:

- add request hash/path/repository metadata;
- fabricate refs, choose hidden paths, decode bundle semantics, or add registries;
- derive Backtest IDs or retry identity from it.

Backtest validates the bundle before Attempt creation, checking target digest, initial financial state, market/timeline bindings, and recomputed `execution_case_semantic_hash` against identities committed by the embedded request. Missing, tampered, mismatched, or unavailable bundle inputs remain storage/validation failures, not terminal outcomes. `MarketBundle` bytes remain bound through `MarketBundleRef` and are not copied into this bundle.

## 4. Preferred minimal consumer port

The executable plan is [BT-PORT-01 / P00-BTA-01](plans/backtest-port.md). Platform cores may proceed against its canonical fixture and deterministic test adapter. Exact Python names are not frozen here; the required behavior is:

```text
run(request_spec) -> completed_ref | terminal_ref
derive(completed_ref, metric_profile_ref) -> analysis_ref
load_completed(completed_ref) -> verified completed evidence
load_terminal(terminal_ref) -> verified terminal evidence
load_analysis(analysis_ref) -> verified analysis evidence
```

The accepted Backtest facade/repository satisfies this behavior directly; Platform adds no fifth pass-through package. Core Research, Validation, and Promotion tests use contract fixtures; the real public binding and fan-in receipt must now consume accepted Backtest SHA `9e5937895d7559b8537a4595d73b6aabc94f6f13`.

## 5. Backtest acceptance fixture minimum

The P00-BT acceptance fixture should cover:

1. one deterministic completed development-grade run;
2. one each durable `BLOCKED`, `FAILED`, and `CANCELLED` terminal;
3. retry/cache parity for the same semantic request;
4. tampered artifact, manifest, hash-chain, and missing-retention rejection;
5. completed-only analysis with exact source execution-result linkage;
6. `simple_period_return = -0.1`, `trade_count = 1`, and development grade for the Platform adverse fixture;
7. terminal-to-analysis rejection;
8. public-root imports only and no Platform/legacy dependency;
9. clean installation of all pinned packages from one accepted SHA.

## 6. Completion rule

Backtest extension closure is complete: every `BT-GAP-*` row has Backtest-owned acceptance and `PLAT-REC-01`, `PLAT-REC-02`, and `PLAT-REC-03` are reconciled. Platform closes the remaining handoff only when:

- the real Backtest public binding passes consumer contract tests against accepted SHA `9e5937895d7559b8537a4595d73b6aabc94f6f13`; and
- P00-SEAM fan-in proves completed, terminal, analysis, tamper, and replay paths without copied Backtest evidence.

## 7. Assessment sources

- `../backtest/docs/architecture/backtest-system-design.md` §§7, 15, 16, 20.2
- `../backtest/docs/implementation/acceptance-matrix.md` WP-07A/B/C/D/E and G07
- Backtest public roots `crypto_quant_domain` and `crypto_quant_backtest`
- `overall/integration-v1.md` §§7–10
- `implementation/roadmap.md`
