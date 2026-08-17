# Backtest consumer contract and production binding

## `BT-PORT-01` — consumer contract

```yaml
id: BT-PORT-01
status_source: ../roadmap.md#2-status-registry
owner: Platform integration contract
type: contract-only
produces:
  - canonical consumer fixture
  - test-only in-memory adapter
consumes:
  - Integration v1 Backtest observations
  - Backtest Platform Integration Extension Register
fan_in: P00-SEAM-01
```

### Outcome

Research and Validation core logic can exercise completed, terminal, analysis, tamper, and retention observations without importing Backtest internals or inventing production Backtest types.

### Interface and invariants

The behavioral port is:

```text
run(request_spec) -> completed_ref | terminal_ref
derive(completed_ref, metric_profile_ref) -> analysis_ref
load_completed(completed_ref) -> verified completed evidence
load_terminal(terminal_ref) -> verified terminal evidence
load_analysis(analysis_ref) -> verified analysis evidence
```

The contract fixture remains selector-only (`request_spec.fixture_case`) while BT-PORT is frozen. Its test helper may carry an opaque canonical `experiment_id` for shell observation, but that field never selects or changes fixture evidence. The future real binding must use the now-frozen `BacktestExecutionRequest@1` additive transport approved by PLAT-REC-03 and BT-GAP-02B.

The contract fixture must represent:

- completed publication ref, semantic-run identity, execution-result hash, and result grade;
- terminal ref with exact `BLOCKED | FAILED | CANCELLED` status and durable evidence ref;
- analysis ref, metric-profile ref, source publication ref, source execution-result hash, `simple_period_return`, `trade_count`, and grade;
- stable errors for missing, wrong type/version, tampered bytes, invalid manifest/hash chain, and unavailable retention.

No production `PortRunOutcome`, Python Protocol package, or duplicate `ArtifactRef` class is created. The first artifact is JSON contract evidence plus one root test-only adapter under `tests/support`; module suites consume that shared helper instead of creating sibling adapters. The production binding exercises the accepted Backtest public types directly. Domain owns `ArtifactEnvelope`/`ArtifactRef`; Backtest owns execution transport and bundle schema/encoding/validation; Foundation owns generic CAS; Platform passes the transport by value and does not decode bundle semantics.

### Failure precedence

1. `PORT_REF_TYPE_MISMATCH`
2. `PORT_REF_NOT_FOUND`
3. `PORT_EVIDENCE_TAMPERED`
4. `PORT_MANIFEST_INVALID`
5. `PORT_RETENTION_UNAVAILABLE`
6. `PORT_TERMINAL_NOT_ANALYZABLE`
7. `PORT_ANALYSIS_LINK_MISMATCH`

Module cores receive only successful verified observations or one stable port failure. They never parse provider exceptions.

### Exclusions

- Backtest execution or evidence verification implementation
- production runtime Protocol/package
- production request construction/registration semantics beyond context-to-request (`PLAT-REC-01`)
- production Backtest evidence admission and governance time
- metrics calculation

### Expected write set

- `tests/contracts/backtest-consumer-port-v1.json`
- `tests/support/backtest_consumer_port.py`
- `tests/architecture/test_backtest_consumer_port.py`

### Acceptance

- Focused command: `uvx --python 3.13.5 --from pytest==8.4.2 pytest -q -p no:cacheprovider tests/architecture/test_backtest_consumer_port.py`
- Contract fixture: `tests/contracts/backtest-consumer-port-v1.json`
- Structural guard: `tests/architecture/test_backtest_consumer_port.py`
- Shared test adapter: `tests/support/backtest_consumer_port.py`; it imports no sibling checkout.
- Mutation coverage includes all three terminals, tamper, retention loss, forged analysis link, and terminal-to-analysis rejection.

## `P00-BTA-01` — production Backtest binding

```yaml
id: P00-BTA-01
status_source: ../roadmap.md#2-status-registry
owner: Platform integration binding tests
produces:
  - provider-conformance receipt satisfying BT-PORT-01 behavior
consumes:
  - accepted P00-DOM-01/P00-BT-01 public roots
  - accepted Backtest SHA
fan_in: P00-SEAM-01
```

### Outcome

Prove the accepted Backtest facade/repository satisfies the consumer contract directly. No fifth Platform package or shared pass-through adapter is introduced. Research and Validation integrated shells receive the public Backtest deep module at composition time and perform only their accepted `PLAT-REC-01` context-to-request mapping.

### Implementation rules

- Binding tests import only `crypto_quant_domain` and `crypto_quant_backtest` public roots.
- Module shells construct public Backtest requests with opaque canonical Platform context; Backtest validates/registers them and owns all request identities.
- Preserve the opaque Platform producer/context coordinate in deterministic request/evidence lineage without Backtest importing Platform modules.
- Receive the opaque `backtest_execution_input_bundle@1` Domain `ArtifactEnvelope` produced when Backtest-owned provider code calls `materialize_execution_input_bundle`; Platform must not construct or understand its internal financial-state template. Store only that envelope with `Foundation.put()`, then construct/pass `BacktestExecutionRequest@1` by value with the exact embedded `BacktestRequest@1` and returned ref.
- Reject missing/tampered/mismatched/unavailable bundle preflight outcomes as provider/storage failures; no preemptive terminal publications.
- Delegate run publication, terminal evidence, completed evidence, analysis, tamper checks, and retention checks to Backtest.
- Do not translate provider exceptions into terminal publications; provider/storage failures remain failures.
- Add no production package, shared gateway, metrics helper, or evidence wrapper.
- Do not store the transport in CAS, create a second transport ref, decode/derive from execution-input bundle contents in Platform, or add hidden path/registry logic.

### Acceptance

- Focused command after the root lock exists: `uv run --locked pytest -q tests/integration/test_backtest_public_binding.py tests/architecture/test_backtest_consumer_port.py`
- Expected write set is integration tests plus a receipt only; no production adapter package.
- Consumer contract suite passes unchanged against the real Backtest public binding.
- Public-import AST guard rejects private Backtest modules.
- The same consumer fixture passes against the test adapter and real Backtest binding using the additive transport envelope when available.
- Platform binding code contains no return, trade-count, profit/loss, terminal, hash-chain, or request-ID derivation algorithm.
- Accepted source is one clean lowercase 40-character SHA.
