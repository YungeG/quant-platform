# Integration v6 target-stream research contract approval

- **Node:** `TSR-CON-01`
- **Contract:** `integration-v6-target-stream-research-v1`
- **Normative contract:** [`overall/integration-v6.md`](../overall/integration-v6.md)
- **Protected fixture:** [`tests/contracts/integration-v6-target-stream-research-v1.json`](../tests/contracts/integration-v6-target-stream-research-v1.json)
- **Fixture SHA-256:** `0f9787350efd9302ce8362b73a93d72d9ddbb48450ea617aa9e2265bd6b73496`
- **Plan:** [`implementation/plans/target-stream-research.md`](plans/target-stream-research.md)
- **Status:** APPROVED
- **Approval time:** `2026-08-26T03:14:51Z`

## Owner approvals

| Repository owner | Name | Status | Approved at |
| --- | --- | --- | --- |
| Platform | `YungeG` | APPROVED | `2026-08-26T03:14:51Z` |
| Backtest | `YungeG` | APPROVED | `2026-08-26T03:14:51Z` |
| Research | `YungeG` | APPROVED | `2026-08-26T03:14:51Z` |
| Validation | `YungeG` | APPROVED | `2026-08-26T03:14:51Z` |
| Promotion | `YungeG` | APPROVED | `2026-08-26T03:14:51Z` |

All five approvals bind the exact fixture hash and exact baseline SHAs. Approval changes no submodule code, gitlink, VCS pin, `pyproject.toml`, or `uv.lock`.

## Frozen decisions

- Backtest owns the context-bound `backtest_target_stream@1` CAS/exact-read repository and nominal `BacktestTargetStreamRef`; there is no Platform owner log.
- The composition root supplies the exact structural materializer and immutable decision-source `strategy_artifact`; it reads only the cited immutable MarketBundle.
- Research adds `TargetRecipe@1`, one `TargetBuildTask@1` per Trial, `TARGET_BUILD`, `TargetMaterializationEvidence@1`, target `ExperimentSpec@2`, and `StrategyCandidate@3` selected evidence.
- Validation preserves the existing out-of-sample reservation producer and adds `ValidationPlan@2`, `ValidationTargetMaterializationEvidence@1`, target-aware CaseResult@2/ValidationReport@2, and optional `validate_target_candidate`.
- Backtest adds source-neutral `DeterministicTimelineV2`/`TimelineCursorV2`, value-embedding `backtest_execution_input_bundle@6`, and profile-specific `prepare_cash_target_stream_backtest` while preserving all existing request/publication/evidence bytes.
- Promotion fails closed on every Candidate@3/ValidationReport@2 ref until `TSR-PG-01`.
- Materialization-evidence publication is the replay commit; a target CAS orphan is not module evidence.
- Leaf implementation uses isolated clean commits; exact root gitlinks/VCS pins/`uv.lock` change only in root fan-in.

## Readiness and exclusions

`TSR-BT-01` is READY. `TSR-RP-01`, `TSR-SV-01`, and `TSR-FI-01` remain blocked on their predecessor receipts; `TSR-PG-01` remains deferred.

Approval authorizes no implementation claim, model combination, decision-grade execution, real Binance/A-share qualification, target-aware Promotion, Shadow, Live, deployment, credential, order, service, queue, database, or distributed-worker capability.
