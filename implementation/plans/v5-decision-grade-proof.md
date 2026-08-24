# Integration v5 decision-grade durable evidence contract plan

- **Normative candidate:** [Integration v5](../../overall/integration-v5.md)
- **Mutable status authority:** [Roadmap §2](../roadmap.md#2-status-registry)
- **Protected fixture:** [`integration-v5-decision-grade-proof-v1.json`](../../tests/contracts/integration-v5-decision-grade-proof-v1.json)
- **Backtest consumer authority:** [`BT-PORT-02`](../../tests/contracts/backtest-consumer-port-v2.json)

This plan owns only the contract approval node. Production Research/Validation/Promotion work remains unauthorized before exact owner approval.

## Execution DAG

```text
FI-03 + BT-PORT-02 ─→ V5-CON-01
```

The approved/deferred V4 ShadowSpec contract is orthogonal and does not block this evidence lane.

## `V5-CON-01` — decision-grade durable evidence contract

### Outcome

Platform, Backtest, Validation, and Promotion owners approve one additive contract for exact canonical-v3 completion, analysis-v2, Admission@2, and decision-grade governance without duplicating Backtest proof semantics.

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

The guard must bind the exact candidate and BT-PORT-02 hashes, pending owner approvals, dispatch/admission/grade rules, v1-v4 compatibility, exact remote pins, and Backtest independence.

### Exclusions

Production implementation, provider qualification, proof decoding, new metrics/methods, Shadow implementation, Live/deployment, RBAC, infrastructure, and any Backtest change.
