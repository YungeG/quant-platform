# 量化研究与策略晋级系统整体设计

- **实现状态：** 以 [Roadmap status registry](../implementation/roadmap.md#2-status-registry) 为唯一可变权威；本文只维护系统设计
- **日期：** 2026-08-14
- **权威集成契约：** [Integration v1](integration-v1.md)；additive [Integration v2](integration-v2.md)
- **适用范围：** Research、offline ModelBuild provenance、可信 Backtest、Validation 和 negative-only Promotion

本文件说明系统边界、模块责任和当前状态；它不重复 Integration v1 的 wire schema、Foundation interface、状态机、failure mapping 或 storage contract。`RP-THIN-01`、`SV-00A-core`、`PG-SYN-1` 的 Frozen 行为仍分别由模块设计和现有测试定义。

## 1. 系统目标与边界

```text
可证伪假设
→ 冻结 Experiment
→ optional FeatureBuild / ModelTraining provenance
→ model-bound Backtest public evidence
→ 完整 CandidateFamily
→ 冻结 Validation Plan / OOS report
→ PromotionDecision(rejected | needs_more_evidence)
```

Backtest 是历史 fills、journals、accounting、profit/loss、canonical publication、terminal outcomes、verified evidence 和 derived analysis 的唯一权威。Platform 不实现第二套经济模拟，不组合 Backtest 私有 Resolver/Runner/Publisher，也不复制 canonical Backtest evidence。

Legacy pilot 是 immutable static historical evidence，不是可调用 adapter、经济权威、canonical Backtest evidence 或可复现性前置条件。P00-CON-02 proposal 说明现有 static capture + retirement receipt 足以满足 `P00-LEG-01`/`P00-CUT-01`，且 hermetic replay is not a P00-PLAT prerequisite；当前审批状态只在 roadmap registry 维护。

Integrated v1 的 Promotion 只能产生 `rejected | needs_more_evidence`。`shadow_ready`、ShadowSpec、Live authorization、deployment 和 decision supersession 均在 v1 外。

## 2. Integration authority and status

| Surface | Authority | State source |
| --- | --- | --- |
| Cross-module v1 schemas, identity, time, publication, states, failures | [Integration v1](integration-v1.md) | accepted contract text |
| Additive model-build schemas, task kinds, Backtest model binding, downstream provenance | [Integration v2](integration-v2.md) | roadmap registry |
| Foundation mechanics | [Foundation design](../foundation/design.md) | [roadmap registry](../implementation/roadmap.md#2-status-registry) |
| Research declaration compiler | [Research design](../research-platform/design.md) and source/tests | frozen source/tests |
| Validation sample projection | [Validation design](../strategy-validation/design.md) and source/tests | frozen source/tests |
| Promotion synthetic evaluator | [Promotion design](../promotion-gate/design.md) and source/tests | frozen source/tests |
| Module implementation and receipts | [Implementation plans](../implementation/plans/README.md) | [roadmap registry](../implementation/roadmap.md#2-status-registry) |

Integration v1 is accepted by [`FI-01`](../implementation/fi-01-receipt.md) and released as `integration-v1`. Backtest now provides BT-GAP-09 public cash-development intent/preparation, persisted request refs, executable v2 transport, verified repository evidence, and analysis authority. Integration v2 starts from those immutable receipts. Existing Backtest `ModelArtifactRef` and `ModelRevisionTimeline` are reused; the additive model-aware preparation seam remains a Backtest-owned v2 node and cannot be claimed from Platform fixtures.

## 3. Module ownership

| Module | Owns | Does not own |
| --- | --- | --- |
| Backtest | public intent preparation, request construction/registration and identities, executable transport, point-in-time model visibility, run/publish facade, canonical evidence repository, analysis, all simulation semantics | offline ModelBuild orchestration, Platform Trial/Validation context and Research/Validation/Promotion policy |
| Foundation | generic CAS, generic append, receipts, entry refs, checkpoints | Backtest decoding, sample semantics, status projection |
| Research | Experiment/task universe, Feature/Trainer recipes, ModelBuildPlan/evidence, execution evidence, ExperimentExecutionManifest, CandidateFamily, SelectionDeclaration, StrategyCandidate | runtime model visibility, profit/loss simulation, validation conclusion |
| Strategy Validation | sample consumption semantics, admission, OOS cases, report | candidate selection, Backtest mutation |
| Promotion Gate | evidence-status semantics, policy, reviews, negative evaluation/decision | Research/Validation implementation, deployment |

Foundation only appends generic payload bytes idempotently; it defines neither a sample-consumption event nor a projection. Validation is the sole semantic owner of `SampleConsumptionRecord`, `SampleConsumptionSnapshot`, and supplied-snapshot projection semantics.

## 4. Public boundary

Research and Validation integrated shells construct public `CashDevelopmentRequestIntent` values with opaque Platform context and supply only public provider facts. `prepare_cash_development_backtest()` returns the persisted `BacktestRequestRef`, semantic run, executable v2 transport, and configured `BacktestRuntime`; Platform adds no fifth adapter and sees no resolved Backtest objects. Only verified completed publications reach `BacktestAnalysisRuntime.derive()`. Verified Backtest subjects enter Platform governance through integration-owned `BacktestEvidenceAdmission@1` and generic Foundation append mechanics. Promotion reads immutable wire contracts and generic Foundation entries/checkpoints to construct its own status snapshot; it does not import Research or Validation implementation.

`ArtifactEnvelope` v1 and `ArtifactRef` remain Domain-owned. Foundation validates generic structure only; Backtest validates Backtest semantics. Owner-log publication, rather than a CAS write, makes an immutable ref usable as downstream evidence. See [Integration v1 §2–3](integration-v1.md#2-identity-time-and-publication).

## 5. Workspace state

`platform/` is the independent public superproject at `YungeG/quant-platform`. Integration v1 is tagged and released; one non-package root `pyproject.toml` coordinates the workspace and one root `uv.lock` pins accepted package revisions. No Platform leaf lock is retained or treated as a release lock. V2 must preserve remote-reachable submodule pins and clean-clone acceptance.

The eventual package dependency direction is:

```text
domain → foundation
domain + market-data + trading → backtest
foundation + domain + backtest → validation
foundation + domain + backtest + validation → research
foundation + domain + backtest → promotion
```

## 6. Non-goals

V2 admits immutable Feature/Trainer recipe contracts, one non-null ModelBuildPlan, build provenance, and Backtest model identity binding. It still excludes model/feature byte formats, callable/plugin/framework ABI, actual model loader/inference, multiple model plans, tuning/range/adaptive search, walk-forward training, additional validation methods, positive Promotion, Shadow or Live runtime, cryptographic RBAC, DB/queue/distributed/object-store writers, and deployment.

## 7. Completion evidence

The integrated golden path and mutation coverage are defined by [Integration v1 §9](integration-v1.md#9-acceptance-cards-and-golden-path). No component reports an integrated implementation receipt, a Backtest commit identity, or a clean-root lock before the corresponding external prerequisite and acceptance card are actually complete.
