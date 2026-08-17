# Backtest Provider Handoff

- **Status:** READY FOR P00-BTA — Backtest public seam and clean package revision accepted; Platform provider binding and P00-SEAM receipt pending
- **Consumer contract:** [`BT-PORT-01`](plans/backtest-port.md)
- **Canonical fixture:** [`backtest-consumer-port-v1.json`](../tests/contracts/backtest-consumer-port-v1.json)
- **Current executable guard:** [`test_backtest_consumer_port.py`](../tests/architecture/test_backtest_consumer_port.py)
- **Authority:** [`Platform Integration v1`](../overall/integration-v1.md)
- **Accepted Backtest package revision:** `9e5937895d7559b8537a4595d73b6aabc94f6f13` — every BT-GAP extension is Backtest-PASSED; a fresh detached worktree built and installed all five packages from one lock, passed 1715 tests and 106 import-boundary files, and remained clean; the maintainer's dirty `.gitignore` was not used as evidence

This package tells the completed Backtest product what the Platform integration consumes. It is not a judgment on Backtest product completeness, accepted SHA, extension-closure receipt, or permission for Backtest to import Platform modules.

## 1. Reconciled boundaries

### `PLAT-REC-01` — request ownership

Research and Validation integrated shells construct the accepted public `BacktestRequest` value and encode the opaque canonical `TrialDeclarationRef` or `ValidationCaseRef` in its public context/`experiment_id`. Backtest imports no Platform type. Backtest validates, normalizes, registers, and persists the request; returns and owns `BacktestRequestRef`; and exclusively derives request hashes, `SemanticRunId`, execution, publications, and evidence.

### `PLAT-REC-02` — governance admission time

Backtest verifies evidence identity, integrity, retention, and lineage. The Platform composition root then publishes `BacktestEvidenceAdmission@1 = { subject_ref }` to `platform.backtest-evidence-admission.v1` through generic Foundation mechanics. Its first `AppendReceipt.accepted_at` is the immutable Platform-governance residency anchor. Replaying the same admission or delaying a Promotion `PUBLISH` event cannot refresh it.

### `PLAT-REC-03` — additive execution-input envelope: resolved

`BacktestExecutionRequest@1` adds exactly one required `execution_input_bundle_ref` to the existing public `BacktestRequest@1`:

```text
BacktestExecutionRequest@1 = {
  schema_version: 1,
  request: BacktestRequest,
  execution_input_bundle_ref: ArtifactRef,
}
```

The embedded `BacktestRequest` remains exact and hash-identical; no request fields, hash, path, repository, timestamp, reader, profile, or status are added on transport. BT-GAP-02B freezes the public names and canonical bytes.

Backtest owns `materialize_execution_input_bundle` and all bundle semantics. Backtest-owned provider code calls that authority; Platform does not construct or understand the internal initial-financial-state template. Platform receives the opaque Domain `ArtifactEnvelope`, stores only it through `Foundation.put()`, and embeds the returned Domain `ArtifactRef` in `BacktestExecutionRequest@1` passed by value. The transport itself is not stored in CAS. Platform must not decode bundle semantics, derive Backtest IDs, fabricate refs, or invent hidden path/registry conventions. Backtest validates the referenced bundle before Attempt creation and treats missing/tampered/mismatched/unavailable bundle inputs as pre-Attempt failures, not terminal outcomes.

The current `BT-PORT-01` fixture remains selector-only (`request_spec.fixture_case`) and does not yet materialize `BacktestExecutionRequest@1`; its test helper may observe an opaque `experiment_id` without using it for case selection so fixture-backed shells prove Trial/Validation ref binding. BT-GAP-02B now provides the accepted production transport/materializer/hydration seam, while the real Platform binding remains a later P00 fan-in step.

## 2. Gap-to-test matrix

| Gap | Required public capability | Existing BT-PORT evidence | Future P00-BTA provider test | Acceptance evidence |
| --- | --- | --- | --- | --- |
| `BT-GAP-01` | One Domain-owned `ArtifactRef` coordinate with exact type/version/hash validation and unchanged Envelope v1 bytes. | Fixture uses exact artifact-ref wires; wrong type/version mutations fail. | Import `ArtifactRef` from the Domain public root and run the consumer fixture unchanged against real refs. | Root export, canonical golden, unchanged P00 Envelope vector, focused tests. |
| `BT-GAP-02` | One deep public facade that validates/registers a public request and returns `BacktestCanonicalPublicationRef | ArtifactRef` without exposing orchestration internals; provider/storage failures remain outside the union. | `run()` covers completed, all three terminals, unknown request, ambiguous request, and provider failure. | Construct public requests with opaque Platform context and invoke only the Backtest public root/facade; load bare terminal refs to recover status. | Public API tests, no private imports, request/context lineage proof. |
| `BT-GAP-03` | Public verified repository for completed, terminal, and analysis refs with fail-closed evidence verification. | `load_completed`, `load_terminal`, and `load_analysis`; tamper, missing, wrong type/version, invalid manifest, retention, forged-link, and duplicate-record mutations. | Run the same load/mutation cases through the real repository and injected reader. | Verification outputs and rejection codes for every mutation. |
| `BT-GAP-04` | Nominal completed ref plus bare Domain terminal refs and their direct run-ref union, preserving `BLOCKED`, `FAILED`, and `CANCELLED` through verified loads. | One completed case and one case for each terminal; cross-kind refs and terminal metric fabrication fail. | Assert real facade returns `BacktestCanonicalPublicationRef | ArtifactRef` and repository loading recovers all three terminal statuses. | Accepted public ref types, terminal goldens, no zero-filled terminal metrics. |
| `BT-GAP-05` | `derive()` accepts only verified completed publications and publishes analysis linked to source publication and execution-result hash. | Completed derive/replay succeeds; terminal-to-analysis and forged source/profile links fail. | Run completed and terminal refs through real `derive()` and repository verification. | Completed-only analysis receipt and exact rejection evidence. |
| `BT-GAP-06` | v1 analysis exposes canonical `simple_period_return`, `trade_count`, result grade, metric profile, source publication, and source execution-result hash. | Adverse fixture fixes `-0.1`, `1`, and `development`; float/exponent/negative-zero/trailing-zero mutations fail. | Compare real analysis bytes and decoded public output with the fixture. | Golden artifact bytes/hash and metric linkage proof. |
| `BT-GAP-07` | Small read-only structural `ArtifactEnvelopeReader` injection while Backtest retains all semantic decoding and verification. | Test-support AST guard imports no provider/sibling package and implements no verifier. | Bind real repository to Foundation's structural reader through public roots only; inject missing/tampered reads. | Import-boundary guard, reader-conformance tests, no Backtest logic in Foundation. |
| `BT-GAP-08` | One accepted clean lowercase 40-character SHA containing Domain, Market Data, Trading, and Backtest package closure. | Not satisfiable by BT-PORT; fixture deliberately records no provider revision. | Install all pinned packages from the same SHA, run P00-BTA plus consumer tests, and verify a clean source tree. | Backtest-owner acceptance receipt, exact SHA, package hashes, clean-install output. |

Every BT-GAP row now has Backtest-owned PASSED evidence. Passing BT-PORT still proves only Platform consumer behavior: `P00-BTA-01` must bind the accepted public roots at SHA `9e5937895d7559b8537a4595d73b6aabc94f6f13`, and `P00-SEAM-01` must prove Foundation transport and fan-in without copied Backtest semantics.

## 3. Accepted Backtest package receipt

| Evidence | Accepted value |
| --- | --- |
| Backtest SHA | `9e5937895d7559b8537a4595d73b6aabc94f6f13` |
| Root lock SHA-256 | `a07106c285b2c454d0528411c79988881b3ff87c0a84d04228d94c186e9d3d8d` |
| Root `pyproject.toml` SHA-256 | `d06e6db31a4050ace93efad2c73c8da532cd4990612a7bcf69bb9e945fb51c4d` |
| Domain package descriptor | `6552f027631013c41073f394a3ac8c16326fe56f27313bcc864074255682f734` |
| Market Data package descriptor | `8e63e9a1ea212c3003da3a6e48776f76800d088915a100ae517251cbbe4980cb` |
| Trading package descriptor | `68dedd449a9aeb56c9fd547d675cd3029c7a4102af13ac000645913515e5acf2` |
| Backtest package descriptor | `2d8c0ffbc581ae4e8e75f974f6f4c3d897ca7f24620a8a8955568073f1749e5b` |
| Bundle Builder package descriptor | `ebde64b75bf939308ae2c010d8218df9b322d6c48e5260e6202b981beca97e7a` |
| Clean install | `uv sync --locked`; five workspace packages built and installed |
| Validation | `1715 passed`; import boundaries `106 files passed`; five public-root imports passed |
| Clean-tree proof | empty `git status --porcelain` before install and after all validation |

This receipt is a Backtest package handoff, not `P00-BTA-01` or `P00-SEAM-01` acceptance. Platform must consume the exact SHA and root lock above; it must not substitute the maintainer worktree, a sibling checkout, `PYTHONPATH`, a leaf lock, or copied evidence.

## 4. Required provider cases

The future `tests/integration/test_backtest_public_binding.py` must run the existing consumer vectors against the real public binding:

1. deterministic completed development-grade request;
2. durable `BLOCKED`, `FAILED`, and `CANCELLED` outcomes;
3. retry/cache identity parity for one request and opaque Platform context;
4. missing, tampered, wrong-type/version, invalid-manifest, hash-chain, and retention failures;
5. completed-only analysis with exact profile/publication/execution-hash linkage;
6. `simple_period_return = -0.1`, `trade_count = 1`, `development` grade;
7. terminal-to-analysis and valid-foreign-link rejection;
8. idempotent Backtest evidence admission with no caller-supplied timestamp;
9. public-root imports only and zero Backtest imports of Platform packages.

## 5. Acceptance commands

Current consumer contract:

```bash
uvx --python 3.13.5 --from pytest==8.4.2 \
  pytest -q -p no:cacheprovider tests/architecture/test_backtest_consumer_port.py
```

Future provider binding, only after the root lock and accepted SHA exist:

```bash
uv run --locked pytest -q \
  tests/architecture/test_backtest_consumer_port.py \
  tests/integration/test_backtest_public_binding.py
```

Acceptance additionally requires:

- Backtest repository owner approval;
- one clean lowercase 40-character accepted SHA;
- Domain, Market Data, Trading, and Backtest packages pinned to that same SHA;
- clean installation and public-root import proof;
- no copied evidence, path/editable dependency, sibling checkout, `PYTHONPATH`, or leaf lock.

## 6. Explicit exclusions

Backtest is not asked to own Research, Validation, Promotion, Foundation governance time, Platform status policy, or deployment. Platform is not allowed to implement simulation, fills, accounting, profit/loss, terminal semantics, evidence integrity, request IDs, semantic-run IDs, or analysis metrics.
