# Promotion Gate implementation plan

- **Normative contract:** [Integration v1 §6, §7, §9](../../overall/integration-v1.md#6-negative-promotion-integration-pg-thin-01)
- **Mutable status authority:** [Roadmap §2](../roadmap.md#2-status-registry)
- **Module design:** [Promotion Gate design](../../promotion-gate/design.md)

Promotion is one deep negative-decision module plus one Promotion-owned status/review ledger module. It owns governed closure, current status, freshness, review exact-cover, evaluation, and the negative decision. It never reruns sibling modules or authorizes deployment.

## Execution DAG

```text
BT-PORT + Research/Validation wires ─→ PG-CORE-01
PF-CORE-01 + PG-CORE-01 ────────────→ PG-LEDGER-01
PG-CORE-01 + PG-LEDGER-01 + PF-CORE-01 + frozen wires
                                        └─→ PG-SHELL-01
PG-SHELL-01 + SV-THIN-01 + PLAT-ADM-01 ─→ PG-THIN-01
```

The Backtest evidence-admission log is integration-owned, not Promotion-owned. Promotion only validates and consumes its immutable entries as publication facts.

## `PG-CORE-01` — implemented governed-evidence evaluation

### Caller-visible result

```text
project_evidence_status(entries, checkpoint) -> EvidenceStatusProjection
expand_governed_closure(case_graph) -> canonical governed refs
validate_reviews(case, policy, reviews, review_checkpoint) -> ReviewResult
evaluate(case, policy, status_snapshot, review_result) -> Evaluation
decide(evaluation) -> rejected | needs_more_evidence
```

The core consumes supplied immutable entries/records only. It performs no Foundation read, status/review append, sibling execution, or deployment action.

### Frozen invariants

1. Status chains are append-ordered and terminal per subject until an explicit separately published replacement.
2. `PUBLISH` binds the exact subject to its original `PublicationFactRef`; later status events never replace the age anchor.
3. Platform artifacts resolve through their designated owner-log entry. Backtest publication/analysis/profile refs resolve through `backtest_admission(entry_ref)` in `platform.backtest-evidence-admission.v1`.
4. First admission `accepted_at` measures Platform governance residency. Replaying admission or delaying/replaying `PUBLISH` cannot rejuvenate evidence.
5. Governed closure follows declared refs only and never imports Research or Validation implementation.
6. Reviews exact-cover required roles, use distinct actors, exclude the case opener, and bind one immutable review checkpoint.
7. v1 emits only `NOT_ELIGIBLE` or `NEEDS_MORE_EVIDENCE`, then `rejected | needs_more_evidence`. Future-positive inputs remain `POSITIVE_PATH_DEFERRED`.

### Failure precedence

1. `PROMOTION_CASE_INVALID`
2. `GOVERNED_CLOSURE_INVALID`
3. `STATUS_CHAIN_MALFORMED`
4. `PUBLICATION_FACT_MISMATCH`
5. `EVIDENCE_REVOKED`
6. `EVIDENCE_SUPERSEDED`
7. `EVIDENCE_STALE`
8. `EVIDENCE_MISSING`
9. `REVIEW_CHECKPOINT_INVALID`
10. `REVIEW_ROLE_COVER_INVALID`
11. `REVIEW_IDENTITY_NOT_INDEPENDENT`
12. `POLICY_NOT_SATISFIED`
13. `POSITIVE_PATH_DEFERRED`

Malformed chain, invalid checkpoint, storage failure, or unreadable evidence raises a fail-closed error and produces no Evaluation. Recognized revoked/policy-failed evidence is not eligible; missing, superseded, stale, insufficient review, and deferred-positive conditions need more evidence.

### Existing implementation evidence

- Production: `promotion-gate/src/crypto_quant_promotion/integration.py`
- Tests: `promotion-gate/tests/test_promotion_core.py`

```bash
uvx --python 3.13.5 --from pytest==8.4.2 \
  --with ./backtest/packages/trading-domain \
  --with-editable ./foundation \
  --with-editable ./promotion-gate \
  pytest -q -p no:cacheprovider promotion-gate/tests/test_promotion_core.py
```

The suite covers publish/supersede/revoke projection, forks and predecessor errors, owner-log/admission mismatch, first-admission replay, stale evidence, governed closure, review role/identity constraints, negative policy mapping, and structurally absent positive/deployment fields.

## `PG-LEDGER-01` — Promotion status and review ledger

### Outcome

Promotion writers use one interface to publish status events and reviews, freeze immutable status/review cutoffs, and reconstruct the exact verified prefixes consumed by `PG-CORE-01`. Callers do not derive Foundation event ids, manipulate receipt chains, or build ad hoc status snapshots.

### Inputs

- completed `PF-CORE-01` store;
- completed `PG-CORE-01` wire validation/projection;
- Integration v1 owner-log, `EvidenceStatusEvent@1`, `PromotionReview@1`, and checkpoint rules.

### Module interface

```text
publish_status(event) -> LogEntryRef
publish_review(review) -> LogEntryRef
freeze_status() -> EvidenceStatusSnapshotRef
freeze_reviews() -> LogCheckpoint("promotion.reviews.v1")
read_status(snapshot_ref) -> verified status entries
read_reviews(checkpoint) -> verified review entries
```

This interface is Promotion-owned because its event semantics and log names are domain-specific. It consumes the concrete Foundation interface directly; Foundation remains generic.

### Invariants

1. Status events append only to `promotion.evidence-status.v1`; reviews append only to `promotion.reviews.v1`.
2. The exact canonical Envelope source bytes are the append payload and owner-log publication fact.
3. Event replay is idempotent; conflicting bytes for one event id are `LOG_CONFLICT`.
4. Status snapshot time is the Foundation-assigned checkpoint time; callers cannot backfill it.
5. Review checkpoint must be at or before the later evaluation status checkpoint.
6. Prefix reads verify log name, sequence, head hash, receipt chain, payload source hash, artifact type/version, and exact cutoff before returning anything.
7. The module does not decide current status, freshness, review sufficiency, or eligibility; those remain in `PG-CORE-01`.

### Failure precedence

1. invalid event/review/checkpoint arguments → `TypeError` or `ValueError`;
2. Foundation lock/clock/integrity/publication failure → propagate unchanged;
3. wrong owner log, artifact type/version, ref, source hash, or cutoff → fail closed without a projection;
4. status-chain/review semantic failure → `PG-CORE-01` failure code, without snapshot/evaluation publication.

### Write set

- `promotion-gate/src/crypto_quant_promotion/ledger.py`
- minimal Promotion public-root exports for ledger results
- `promotion-gate/tests/test_ledger_integration.py`

### Acceptance

```bash
uvx --python 3.13.5 --from pytest==8.4.2 \
  --with ./backtest/packages/trading-domain \
  --with-editable ./foundation \
  --with-editable ./promotion-gate \
  pytest -q -p no:cacheprovider promotion-gate/tests/test_ledger_integration.py
```

Required evidence:

- status/review append, exact replay, and conflicting replay;
- immutable status and review cutoffs with later equal-time exclusion;
- wrong-log, wrong-type/version, forged ref/source hash, truncated chain, and future checkpoint rejection;
- review checkpoint after status checkpoint rejected;
- Foundation remains free of status/review vocabulary and projection logic.

## `PG-SHELL-01` — contract-first negative Promotion shell

### Outcome

One Promotion operation opens a case over a published ValidationReport, freezes governed status and independent reviews, and publishes one deterministic negative Evaluation and Decision. It cannot emit positive eligibility, Shadow readiness, Live authorization, credentials, or deployment instructions.

### Inputs

- completed `PG-CORE-01` and `PG-LEDGER-01`;
- canonical frozen rejected/development Validation graph fixtures;
- canonical Platform owner-log and first-admission fixtures;
- frozen Promotion policy, opener, reviews, and decider provenance.

### Module interface

Equivalent behavior to:

```text
evaluate_case(validation_report_ref, policy, actors, foundation) ->
  PublishedNegativeDecision
```

The result exposes case, snapshot, evaluation, and decision refs. It does not expose mutable status registries, sibling implementation objects, or a deployment handle.

### Publication order and commit points

1. Resolve the frozen ValidationReport graph and policy inputs through immutable canonical refs; invalid input performs no new publication.
2. Publish `PromotionPolicy` and `PromotionCase`.
3. For every governed ref, resolve its original Platform owner-log fixture or exact first-admission fixture before publishing its `PUBLISH` status event.
4. Publish supplied reviews only after exact case/policy/actor validation.
5. Freeze status and review checkpoints through `PG-LEDGER-01`; the review cutoff must not be later than evaluation time.
6. Expand closure, project status, validate reviews, and evaluate with `PG-CORE-01`.
7. Publish `PromotionEvaluation` and then `PromotionDecision` only after all fail-closed checks succeed.

No operation updates an existing Evaluation or Decision. Exact replay of one PromotionCase returns its existing valid Decision; reconsideration requires a distinct Case, such as one opened by a different opener. A later case is a new artifact chain; v1 has no decision supersession.

### Failure and decision rules

| Condition | Required effect |
| --- | --- |
| malformed graph/status/review/checkpoint or Foundation read failure | no Evaluation or Decision |
| publication fact names wrong log/ref/subject/time | no Evaluation or Decision |
| repeated identical Backtest admission | first entry/time retained; no freshness reset |
| delayed/replayed status `PUBLISH` | original publication/admission time retained |
| recognized revoked or policy-failed evidence | `NOT_ELIGIBLE` → policy-selected negative decision |
| missing, superseded, stale, or insufficiently reviewed evidence | `NEEDS_MORE_EVIDENCE` |
| all future-positive conditions satisfied | `NEEDS_MORE_EVIDENCE / POSITIVE_PATH_DEFERRED` |

### Write set

- `promotion-gate/src/crypto_quant_promotion/runtime.py`
- minimal Promotion public-root exports for the orchestration result
- `promotion-gate/tests/test_promotion_shell.py`

No production admission adapter or sibling implementation import is introduced.

### Acceptance

```bash
uvx --python 3.13.5 --from pytest==8.4.2 \
  --with ./backtest/packages/trading-domain \
  --with-editable ./foundation \
  --with-editable ./promotion-gate \
  pytest -q -p no:cacheprovider promotion-gate/tests/test_promotion_shell.py
```

Required evidence:

- canonical rejected/development ValidationReport graph and full governed closure;
- Platform owner-log and first-admission fixture facts resolve to the exact subject;
- admission replay and delayed/replayed status publication do not reset freshness;
- stale, missing, superseded, revoked, wrong-owner-log, wrong-subject, malformed-chain, and storage-failure cases;
- exact review-role cover, distinct reviewers, opener exclusion, and checkpoint ordering;
- deterministic `needs_more_evidence` golden and policy-selected rejected case;
- structural/AST guard proves positive, Shadow, Live, credential, deployment, and decision-supersession fields/imports are absent.

Passing this node proves package-local negative orchestration against frozen wires only. It is not `PG-THIN-01`, a real admission fact, a real Validation receipt, or an integrated decision receipt.

## `PG-THIN-01` — real negative Promotion acceptance

### Outcome

Prove `PG-SHELL-01` consumes the actual `SV-THIN-01` report and `PLAT-ADM-01` first-admission facts unchanged, then publish the PG-THIN-01 receipt.

### Inputs

- completed `PG-SHELL-01`;
- accepted `SV-THIN-01` ValidationReport graph;
- accepted `PLAT-ADM-01`, Foundation package, and root workspace/lock.

### Allowed changes

- `promotion-gate/tests/test_integrated_promotion.py`;
- PG-THIN-01 acceptance receipt;
- at most package-local public-name/type reconciliation in `runtime.py`. Any closure, status, review, freshness, mapping, or schema change returns to `PG-SHELL-01` and its focused suite.

### Acceptance

This command applies only after P00 has created the declared root workspace and lock.

```bash
uv run --locked pytest -q \
  promotion-gate/tests/test_promotion_shell.py \
  promotion-gate/tests/test_integrated_promotion.py
```

The real test proves exact Validation provenance, first-admission identity/time, replay/delayed-status freshness resistance, status/review checkpoint ordering, deterministic negative decisions, accepted revisions/lock, and structural absence of positive/deployment capabilities.

## Dependencies

| Type | Node/artifact | Why |
| --- | --- | --- |
| Contract | `PG-CORE-01` and `PG-LEDGER-01` | Own closure, projection, review, freshness, append, and cutoff behavior. |
| Contract | `PF-CORE-01` | Supplies exact generic publication, entries, and checkpoints. |
| Contract | frozen Research/Validation/admission wires | Supply fixture-backed graph/facts for `PG-SHELL-01`. |
| Contract | `SV-THIN-01` + `PLAT-ADM-01` | Replace frozen facts only for `PG-THIN-01`. |
| Evidence | governed rejected/development real graph and review/status mutations | Required only by real acceptance. |
| Write conflict | Promotion public root, ledger/runtime | `PG-LEDGER-01` completes before one writer owns `PG-SHELL-01`. |
| Write conflict | integrated test/receipt | `PG-THIN-01` is serialized by the fan-in owner. |

## Exclusions

- Backtest evidence admission creation or Backtest semantic verification;
- Research/Validation execution or result reinterpretation;
- cryptographic actor authority/RBAC or organizational independence proof;
- positive Promotion, ShadowSpec/Runtime, Live authorization, credentials, deployment, mutable decision, database, queue, or status cache.
