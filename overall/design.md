# 量化研究与策略晋级系统整体设计

- **实现状态：** 以 [Roadmap status registry](../implementation/roadmap.md#2-status-registry) 为唯一可变权威；本文只维护系统设计
- **日期：** 2026-08-14
- **权威集成契约：** [Integration v1](integration-v1.md)
- **适用范围：** Research、可信 Backtest、Validation 和 negative-only Promotion

本文件说明系统边界、模块责任和当前状态；它不重复 Integration v1 的 wire schema、Foundation interface、状态机、failure mapping 或 storage contract。`RP-THIN-01`、`SV-00A-core`、`PG-SYN-1` 的 Frozen 行为仍分别由模块设计和现有测试定义。

## 1. 系统目标与边界

```text
可证伪假设
→ 冻结 Experiment
→ Backtest public evidence
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
| Foundation mechanics | [Foundation design](../foundation/design.md) | [roadmap registry](../implementation/roadmap.md#2-status-registry) |
| Research declaration compiler | [Research design](../research-platform/design.md) and source/tests | frozen source/tests |
| Validation sample projection | [Validation design](../strategy-validation/design.md) and source/tests | frozen source/tests |
| Promotion synthetic evaluator | [Promotion design](../promotion-gate/design.md) and source/tests | frozen source/tests |
| Module implementation and receipts | [Implementation plans](../implementation/plans/README.md) | [roadmap registry](../implementation/roadmap.md#2-status-registry) |

A frozen Platform design does not self-certify integration. Backtest now provides the accepted deep facade, verified evidence repository, analysis runtime, terminal refs, and clean package revision `9e5937895d7559b8537a4595d73b6aabc94f6f13`; Foundation generic storage also exists. Pure Research, Validation, and Promotion cores still proceed against the frozen consumer contract and fixtures until `P00-BTA-01` and `P00-SEAM-01` prove the real request/context binding, Foundation transport, unchanged consumer behavior, remaining approval/root-lock closure, and traceable Platform source revision.

## 3. Module ownership

| Module | Owns | Does not own |
| --- | --- | --- |
| Backtest | public request validation/registration and identities, run/publish facade, canonical evidence repository, analysis, all simulation semantics | Platform request composition and Research/Validation/Promotion policy |
| Foundation | generic CAS, generic append, receipts, entry refs, checkpoints | Backtest decoding, sample semantics, status projection |
| Research | Experiment/task universe, execution evidence, ExperimentExecutionManifest, CandidateFamily, SelectionDeclaration, StrategyCandidate | profit/loss simulation, validation conclusion |
| Strategy Validation | sample consumption semantics, admission, OOS cases, report | candidate selection, Backtest mutation |
| Promotion Gate | evidence-status semantics, policy, reviews, negative evaluation/decision | Research/Validation implementation, deployment |

Foundation only appends generic payload bytes idempotently; it defines neither a sample-consumption event nor a projection. Validation is the sole semantic owner of `SampleConsumptionRecord`, `SampleConsumptionSnapshot`, and supplied-snapshot projection semantics.

## 4. Public boundary

Research and Validation integrated shells receive the deep `BacktestFacade` and `CanonicalEvidenceRepository` directly from the accepted public Backtest binding; Platform adds no fifth adapter package. They construct public `BacktestRequest` values with opaque Platform context, while Backtest owns validation, registration, request refs, semantic identities, execution, and evidence. They branch `BacktestPublicationOutcome`; only `CompletedPublication.publication_ref` reaches `derive()`. Verified Backtest subjects enter Platform governance through integration-owned `BacktestEvidenceAdmission@1` and generic Foundation append mechanics. Promotion reads immutable wire contracts and generic Foundation entries/checkpoints to construct its own status snapshot; it does not import Research or Validation implementation.

`ArtifactEnvelope` v1 and `ArtifactRef` remain Domain-owned. Foundation validates generic structure only; Backtest validates Backtest semantics. Owner-log publication, rather than a CAS write, makes an immutable ref usable as downstream evidence. See [Integration v1 §2–3](integration-v1.md#2-identity-time-and-publication).

## 5. Workspace state

`platform/` remains the independent system root. `P00-PLAT-01` has created one non-package root `pyproject.toml` workspace coordinator and one root `uv.lock`, pinning Backtest packages to accepted SHA `9e5937895d7559b8537a4595d73b6aabc94f6f13`; no leaf lock is retained or treated as a Platform lock. Its acceptance receipt still waits for a traceable Platform revision.

The eventual package dependency direction is:

```text
domain → foundation
domain + market-data + trading → backtest
foundation + domain + backtest → validation
foundation + domain + backtest + validation → research
foundation + domain + backtest → promotion
```

## 6. Non-goals

v1 excludes Feature/model/trainer ABI, non-null `model_build_plan`, range/adaptive search, walk-forward/stress/capacity/bootstrap/selection-bias methods, positive Promotion, Shadow or Live runtime, cryptographic RBAC, DB/queue/distributed/object-store writers, proof of uninstrumented reads, physical sibling-pilot deletion, and pilot economic parity.

## 7. Completion evidence

The integrated golden path and mutation coverage are defined by [Integration v1 §9](integration-v1.md#9-acceptance-cards-and-golden-path). No component reports an integrated implementation receipt, a Backtest commit identity, or a clean-root lock before the corresponding external prerequisite and acceptance card are actually complete.
