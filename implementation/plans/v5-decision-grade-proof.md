# Integration v5 decision-grade durable evidence contract plan

- **Normative contract:** [Integration v5](../../overall/integration-v5.md)
- **Mutable status authority:** [Roadmap §2](../roadmap.md#2-status-registry)
- **Protected fixture:** [`integration-v5-decision-grade-proof-v1.json`](../../tests/contracts/integration-v5-decision-grade-proof-v1.json)
- **Backtest consumer authority:** [`BT-PORT-02`](../../tests/contracts/backtest-consumer-port-v2.json)

This plan owns the approved contract and implementation nodes. Backtest compatibility fan-in `8de544e7794ee05b652355c9809b5454d7ace494` closes the prior revision blocker.

## Execution DAG

```text
FI-03 + BT-PORT-02 ─→ V5-CON-01 [APPROVED]
                           └─→ V5-PIN-01
                                  ├─→ DG-ADM-01 ───────────────┐
                                  └─→ RP-DG-01 ─→ SV-DG-01 ───┼─→ PG-DG-01
                                                              └─→ DG-THIN-01 ─→ FI-04
```

The approved/deferred V4 ShadowSpec contract is orthogonal and does not block this evidence lane.

## Compatibility fan-in evidence

```text
model seam:   033344172b24847e73941bb97a06da0490527edf
proof seam:   cebb9b033b7eeffbbff712715fc017708ac5a247
fan-in:       8de544e7794ee05b652355c9809b5454d7ace494
Backtest:     2438 passed
Platform RP:  90 passed
```

Both accepted seams are ancestors of the fan-in. Platform may now repin every Backtest-owned package and the gitlink to this exact revision; mixed revisions, editable/path overrides, and Platform proof reimplementation remain forbidden.

## `V5-CON-01` — decision-grade durable evidence contract

### Outcome

Platform, Backtest, Validation, and Promotion owners approved one additive contract for exact canonical-v3 completion, analysis-v2, Admission@2, and decision-grade governance without duplicating Backtest proof semantics.

### Dependencies

- accepted [`FI-03`](../fi-03-receipt.md);
- immutable Platform `BT-PORT-02` commit `5948dd62f50d197f3e35d499a8e44e04b2257981`;
- immutable Backtest DRP-03 code commit `cebb9b033b7eeffbbff712715fc017708ac5a247`;
- Backtest Matrix `G07-DURABLE-REBUILD-PROOF-V2 = PASSED`;
- unchanged Domain/Foundation interfaces.

### Interface

The contract adds `BacktestEvidenceAdmission@2(subject_ref)` and activates exact V2 nominal refs plus `decision_grade` in existing Research, Validation, and Promotion field sets. It adds no Platform proof decoder or second Backtest repository.

### Invariants

1. Exact nominal type/version selects `load_completed_v3` and `load_analysis_v2`.
2. Raw refs, unknown versions, unwrap, retry, and downgrade fail closed.
3. Admission@2 reuses the existing admission log but cannot admit V1 subjects; Admission@1 cannot admit V2 subjects.
4. Research retains V2 refs/hash/grade exactly through outcomes and Candidate.
5. Validation accepts exactly one grade mode: development or decision_grade; mixed modes are invalid.
6. Decision-grade Validation requires exact completed/analysis links and typed durable-proof refs but does not duplicate proof semantics.
7. Promotion resolves V2 publication facts only through Admission@2 and otherwise reuses accepted v3 governance.
8. No Backtest change.

### Failure precedence

1. BT-PORT-02 ref/type/version/evidence failure;
2. Admission@2 version, subject, or owner-log mismatch;
3. Research outcome/Candidate provenance mismatch;
4. Validation grade/proof-view/analysis-link mismatch;
5. existing Validation and Promotion precedence.

Every failure produces no heuristic fallback, grade downgrade, fabricated proof, or partial governance result.

### Write set

- `overall/integration-v5.md`;
- `tests/contracts/integration-v5-decision-grade-proof-v1.json`;
- `implementation/v5-contract-decision-grade-proof-v1.md`;
- roadmap, plan map, README, glossary, and contract architecture guard only.

### Acceptance

```bash
uv run pytest -q -p no:cacheprovider tests/architecture/test_integration_v5_design.py
```

The guard must bind the exact candidate and BT-PORT-02 hashes, owner approvals, dispatch/admission/grade rules, v1-v4 compatibility, exact remote pins, and Backtest independence.

### Exclusions

Production implementation, provider qualification, proof decoding, new metrics/methods, Shadow implementation, Live/deployment, RBAC, infrastructure, and any Backtest change.

## `V5-PIN-01` — exact Backtest package/lock pin

### Outcome

The root workspace, lock, and Backtest gitlink all resolve accepted compatibility fan-in `8de544e7794ee05b652355c9809b5454d7ace494`, making both model-bound and durable-proof public surfaces available without editable/path overrides.

### Write set

- root `pyproject.toml` Backtest-owned package source revisions;
- root `uv.lock`;
- no package or Backtest source.

### Acceptance

Exact all-package SHA equality, `uv lock --check`, clean install/import of V2 public types, V1 protected hashes, and no mixed Backtest revisions. Accepted evidence: [`V5-PIN-01`](../v5-pin-01-receipt.md) at Platform revision `6e82e4dc1187752f021097e9d21aaa7cf7e3c96e`.

## `DG-ADM-01` — exact Admission@2

### Outcome

The integration-owned admission seam verifies V2 publication/analysis subjects with exact Backtest repository operations and appends one schema-v2 admission to the existing owner log.

### Interface

`admit_backtest_evidence()` remains the single operation. Exact subject type selects Admission@1 or @2; V1/V2 event ids and verifier methods never cross.

### Write set

- `tests/support/backtest_evidence_admission.py`;
- `tests/integration/test_backtest_evidence_admission.py`.

### Acceptance

Exact V2 verify/append/replay, V1 preservation, wrong-version/no-downgrade, repository-before-append, and first-governance-time tests. Accepted evidence: [`DG-ADM-01`](../dg-adm-01-receipt.md) at Platform revision `bc396ab6763298bb3cec3e28edab9e2a72186d95`.

## `RP-DG-01` — Research exact V2 dispatch

### Outcome

Research executes and replays Trial/Analysis tasks through exact V1/V2 nominal dispatch while retaining selected refs, execution-result hash, and grade unchanged.

### Interface

Existing `execute_experiment()` and artifact schemas remain unchanged. Private dispatch helpers select `load_completed`/`load_completed_v3` and `load_analysis`/`load_analysis_v2` only from exact nominal type/schema pairs.

### Write set

- `research-platform/src/crypto_quant_research/integration.py`;
- `research-platform/src/crypto_quant_research/runtime.py`;
- focused Research core/shell/integrated tests.

### Acceptance

V2 completed→analysis journey, exact Candidate/outcome refs, decision-grade selection, V1 parity, raw-terminal dispatch, unknown/cross-version/no-fallback failures, and replay. Accepted evidence: [`RP-DG-01`](../rp-dg-01-receipt.md) at Research revision `1557ec1904de6f2a8f8a32c2f37ce038a0daa022`.

## `SV-DG-01` — decision-grade Validation

### Outcome

Validation accepts one exact singleton grade mode and consumes completed-v3/analysis-v2 views without copying or interpreting Backtest proof semantics.

### Interface

Existing `ValidationPolicy`, `ValidationPlan`, `validate_candidate()`, CaseResult, and ValidationReport schemas remain unchanged.

### Write set

- `strategy-validation/src/crypto_quant_validation/integration.py`;
- `strategy-validation/src/crypto_quant_validation/runtime.py`;
- focused Validation core/shell/integrated tests.

### Acceptance

Singleton development/decision-grade modes, mixed-mode rejection, exact proof-ref/view/link checks, V2 port failure precedence/no report, V1 parity, supported/rejected threshold behavior, and replay. Accepted evidence: [`SV-DG-01`](../sv-dg-01-receipt.md) at Validation revision `cd966d92dad2110af7d8b1bf580536f6c3cdb998`.

## `PG-DG-01` — V2 Promotion governance

### Outcome

Promotion governs V2 nominal refs only through exact Admission@2 publication facts and reuses existing status, freshness, review, Evaluation, and Decision behavior.

### Interface

Existing Promotion public operations and artifact schemas remain unchanged. Private ref/admission-version helpers add exact V2 variants.

### Write set

- `promotion-gate/src/crypto_quant_promotion/integration.py`;
- `promotion-gate/src/crypto_quant_promotion/ledger.py`;
- `promotion-gate/src/crypto_quant_promotion/runtime.py`;
- focused Promotion core/ledger/shell tests.

### Acceptance

V2 ref identity/signature, Admission@2 event/schema resolution, @1/@2 substitution rejection, decision-grade policy, positive/negative decisions, V1 parity, and replay.

## `DG-THIN-01` — real decision-grade fan-in

### Outcome

One Platform integration test composes Research, V2 Backtest consumer, Admission@2, Validation, and Promotion through exact public seams and proves replay closure.

### Write set

- root V5 integration test/support adjustments;
- one thin receipt and roadmap status only.

### Acceptance

Golden values `0.02392`, one trade, decision_grade, exact proof refs, supported Validation, `shadow_ready`, immutable refs, no second run/admission/governance action, and no Backtest change.

## `FI-04` — whole-Platform V5 release

### Outcome

One remote recursive clone proves all V5 leaf receipts, protected hashes, package pins, full-suite compatibility, and release closure.

### Write set

- FI-04 receipt/status/tag only.

### Acceptance

Full local and fresh-clone suites, `uv lock --check`, remote reachability, empty clone status, protected V1-V5 hashes, and explicit exclusions.
