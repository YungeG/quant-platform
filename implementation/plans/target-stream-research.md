# Integration v6 target-stream research execution

- **Contract maturity:** APPROVED
- **Implementation readiness:** READY_FOR_TSR_BT_01
- **Node:** `TSR-CON-01`
- **Normative contract:** [`overall/integration-v6.md`](../../overall/integration-v6.md)
- **Approval:** [`implementation/v6-contract-target-stream-research-v1.md`](../v6-contract-target-stream-research-v1.md)
- **Protected fixture:** [`tests/contracts/integration-v6-target-stream-research-v1.json`](../../tests/contracts/integration-v6-target-stream-research-v1.json), SHA-256 `0f9787350efd9302ce8362b73a93d72d9ddbb48450ea617aa9e2265bd6b73496`
- **Scope:** development-grade cash target-stream Research → Backtest → Validation only

`TSR-CON-01` freezes names, fields, ownership, identity, ordering, replay, failure precedence, repository isolation, and compatibility. Approval makes `TSR-BT-01` READY; it does not claim implementation.

## 1. Exact baselines

| Repository | Contract-approval SHA |
| --- | --- |
| Platform | `04b01a1db1408ab7277a116f02ce706243ac1499` |
| Backtest | `8de544e7794ee05b652355c9809b5454d7ace494` |
| Foundation | `9d88ed67a84d06c558276f8bae2206b069bcec8f` |
| Research | `1557ec1904de6f2a8f8a32c2f37ce038a0daa022` |
| Validation | `cd966d92dad2110af7d8b1bf580536f6c3cdb998` |
| Promotion | `8e6dddf5da0494b57cca6990d5024fe4198e6b44` |

Contract approval preserves these gitlinks, Backtest VCS pin `8de544e7794ee05b652355c9809b5454d7ace494`, `pyproject.toml` SHA-256 `fd91992418122cbce414ff5fa0c39878290df1d49f69b9758d5ca1ec64806024`, and `uv.lock` SHA-256 `75a91665859490d03544066d0585bceec9b6dbe7156cf322b4cb67f95a6a420f`.

## 2. Frozen authority and wires

- Backtest owns `backtest_target_stream@1`, `BacktestTargetStreamRef`, `BacktestTargetStreamRepository`, `VerifiedBacktestTargetStream`, `DeterministicTimelineV2`, `TimelineCursorV2`, bundle@6 preparation, economics, terminals, analysis, publication, retention, and replay.
- The target artifact payload is exactly `producer_context_ref` plus `target_stream`. Different producer contexts produce different refs even for equal streams. Backtest semantic request/run identity uses only the stream digest.
- The composition root supplies `strategy_artifact: BuildArtifactRef(role=DECISION_SOURCE, immutable identity)` and `materialize_target(request: Mapping[str, object]) -> Mapping[str, object]`.
- Materializer request/result fields are exactly those in the fixture. Only immutable MarketBundle reads are allowed; beyond required `strategy_artifact`, no owner/workflow/target ref, prepared/run value, or cache handle is allowed.
- Research owns `TargetRecipe@1`, one `TargetBuildTask@1` per Trial, task kind/witness `TARGET_BUILD`, `TargetMaterializationEvidence@1`, target `ExperimentSpec@2`, and `StrategyCandidate@3.selected_target_materialization_evidence_ref`.
- Validation owns `ValidationPlan@2`, `ValidationTargetMaterializationEvidence@1`, target-aware CaseResult@2/ValidationReport@2, and `validate_target_candidate`.
- Existing integrated `TrialDeclaration@1` and existing out-of-sample ValidationCase remain reservation producers.
- Promotion fails closed on Candidate@3/ValidationReport@2 until `TSR-PG-01`.

## 3. Required ordering and replay

```text
TargetRecipe@1 + target ExperimentSpec@2
→ one TargetBuildTask@1 per Trial
→ existing TrialDeclaration@1 reservation
→ materializer request/result verification
→ Backtest target publish + exact load
→ TargetMaterializationEvidence@1 commit
→ prepare_cash_target_stream_backtest
→ Backtest run/analysis
→ exact manifest/selection
→ StrategyCandidate@3

ValidationPlan@2 + existing out_of_sample ValidationCase
→ holdout reservation
→ independent materializer request/result verification
→ Backtest target publish + exact load
→ ValidationTargetMaterializationEvidence@1 commit
→ Backtest preparation/run/analysis
→ target-aware CaseResult@2 / ValidationReport@2
```

Reservation is idempotent. Evidence publication is the module commit preventing rematerialization. A target CAS orphan is not Research/Validation evidence. Replay recovers the first evidence/ref and then the prepared request/run, with no second read, materialization, economic run, or governance refresh.

## 4. Execution DAG

```text
TSR-CON-01 [APPROVED]
        ↓
TSR-BT-01 [READY]
        ↓
TSR-RP-01 [BLOCKED]
        ↓
TSR-SV-01 [BLOCKED]
        ↓
TSR-FI-01 [BLOCKED]
        ↓
TSR-PG-01 [DEFERRED]
```

Market qualification is separate: `TSR-BIN-Q-01` remains H3 and `TSR-ASH-Q-01` remains H2. Neither qualification branch feeds the common development-grade fan-in.

## 5. Node packets

### `TSR-BT-01` — target authority and source-neutral cash preparation

**State:** READY.

**Consumes:** approved v6 contract and exact Backtest baseline.

**Produces:** context-bound target artifact/ref round-trip; CAS/exact-read repository; verified view; source-neutral `DeterministicTimelineV2`/`TimelineCursorV2`; value-embedding `backtest_execution_input_bundle@6`; public `prepare_cash_target_stream_backtest` using existing cash intent/provider inputs plus target ref; durable replay without the materializer.

**Must prove:** different producer contexts produce different refs for equal streams; semantic identity remains digest-only; market readers remain market-only; timeline identity binds market ref/sorted keys/digest/window; existing bundle v1-v5, request v1, completed/terminal/analysis/publication bytes are exact; target ref/tamper/retention/context/digest failures preserve frozen precedence; no strategy-specific operation.

**Write boundary:** isolated Backtest branch/worktree and one clean leaf commit. No root pin or gitlink writes.

### `TSR-RP-01` — discovery target provenance

**State:** BLOCKED on accepted `TSR-BT-01` receipt/commit.

**Produces:** exact target recipe/spec/task/evidence artifacts, one target-build task per Trial, reservation-before-materialization, exact target-mode dispatch, Candidate@3 selected evidence, and replay without second read/materialization/run.

**Must preserve:** ordinary/model ExperimentSpec@1 bytes; TrialDeclaration@1 reservation identity; CandidateFamily and ExperimentExecutionManifest fields; module-local failure precedence.

**Write boundary:** isolated Research branch/worktree and one clean leaf commit. No root pin or gitlink writes.

### `TSR-SV-01` — independent OOS target evidence

**State:** BLOCKED on accepted `TSR-RP-01` candidate provenance and `TSR-BT-01` authority.

**Produces:** ValidationPlan@2, independent post-reservation target materialization, ValidationTargetMaterializationEvidence@1, target-aware CaseResult@2/ValidationReport@2, and exact `validate_target_candidate(candidate_ref, policy, reservation_at, foundation, sample_ledger, materializer, backtest)`.

**Must prove:** existing `validate_candidate` and all v1 bytes unchanged; discovery target-ref substitution fails even for equal stream values; recovery exact-loads committed target evidence and may repeat only idempotent Backtest preparation, with no second sample/materializer read, target materialization, or economic run.

**Write boundary:** isolated Validation branch/worktree and one clean leaf commit. No root pin or gitlink writes.

### `TSR-FI-01` — root fan-in

**State:** BLOCKED on clean accepted Backtest, Research, and Validation leaf commits/receipts.

**Produces:** one development-grade cash golden using fixed one-slice portfolio targets and `simple_period_return`/`trade_count`, exact cross-module provenance, replay proof, and root dependency closure.

**Write boundary:** root-only exact gitlinks, every matching VCS pin, `uv.lock`, integration support/test, and receipt. No leaf code edits.

### `TSR-PG-01` — Promotion closure

**State:** DEFERRED. Existing Promotion must fail closed as unsupported on all Candidate@3/ValidationReport@2 refs, with no coercion or fallback.

## 6. Failure precedence

1. public arg/type;
2. reservation;
3. materializer artifact/request/result;
4. target publish/load/ref/tamper/retention/context/digest;
5. evidence publication;
6. preparation;
7. Backtest terminal/provider;
8. analysis/link;
9. manifest/selection;
10. Validation target substitution/holdout;
11. report;
12. Promotion unsupported.

Existing module-specific precedence remains exact inside each group.

## 7. Proof budget

| Node | Minimum evidence |
| --- | --- |
| `TSR-BT-01` | target round-trip/identity, exact-read/tamper/retention/context/digest mutations, v2 timeline identity, bundle@6/rebuild golden, existing-byte guards, public import guard |
| `TSR-RP-01` | one finite target experiment, per-Trial task exact cover, reservation barrier, materializer/result/target/evidence failures, manifest/selection/candidate links, replay counters |
| `TSR-SV-01` | independent OOS golden, holdout barrier, discovery substitution rejection including equal values, evidence/ref/tamper/retention mutations, replay counters, v1 compatibility |
| `TSR-FI-01` | clean leaf SHAs, public-root discovery/OOS golden, no second read/materialization/economic run/governance refresh, exact gitlink/VCS-pin/lock parity |
| `TSR-PG-01` | deferred rejection fixtures only; no positive target-aware dispatch |

## 8. Explicit exclusions

No model combination, decision-grade execution, real Binance qualification, real A-share qualification, target-aware Promotion support, strategy-specific preparation API, dynamic loader/plugin registry, second simulator/verifier, Foundation target semantics, Shadow, Live, deployment, credentials, orders, database, queue, service, scheduler, object-store abstraction, or distributed worker.

## 9. Completion rule

The approved contract is complete and `TSR-BT-01` is READY. The v6 implementation is not complete until clean Backtest, Research, and Validation leaves plus root fan-in satisfy their receipts. No implementation claim is made by this plan revision.
