# Quality + B-Band active A-share strategy — Full implementation-readiness packet

**Status: NOT_READY**

The research design is approved for continued planning. Fixed-scope acquisition, declarations, normalization and current-only trio selection are published as stacked Backtest PRs #1–#5, and the availability, revision, presentation and ordinary-industrial field contracts are frozen for review. Full strategy implementation still cannot start because the stack is unaccepted, only one issuer/period is selected, broad source authority, general A-share coverage, a portfolio authority artifact and repository-owner approvals are missing.

## Outcome

One accepted public flow must eventually produce:

```text
immutable point-in-time A-share data
→ deterministic quality + B-Band target stream
→ public A-share portfolio Backtest preparation
→ Research Experiment selection
→ precommitted Validation holdout
→ supported | rejected | inconclusive
```

No second simulator, private Backtest composition, custom PnL, Shadow/Live capability or deployment authority is part of the outcome.

## Authority

| ID | Source | Requirement or invariant |
| --- | --- | --- |
| C1 | Quant Strategy Research skill | Execute only through accepted public package roots and a concrete public preparation operation. |
| C2 | `research/investment-book-strategy-ideas.md` | Quality filter and B-Band entry are hypotheses; maximum four positions, T+1 and no forced exposure. |
| C3 | `research/quality-bband-data-authority-audit.md` | General data/Profile and financial/governance authority are absent; mutable local data is not Platform evidence. |
| C4 | `implementation/plans/quality-bband-data-contract-v1.md` | Builder contract is source-authority blocked and must remain pure, atomic and fail closed. |
| C5 | `implementation/plans/quality-bband-a-share-preparation-seam-v1.md` | Reuse generic request intent and prepared result; add one deep public A-share portfolio PREP seam only after data qualification. |
| C6 | `implementation/backtest-provider-handoff.md` | Backtest exclusively owns request, Semantic Run, Profile resolution, execution transport, evidence and analysis. |
| C7 | `backtest/docs/research/g12k-universe-corporate-action-coverage.md` | General Universe/corporate-action coverage remains blocked. |
| C8 | `strategy-validation/src/crypto_quant_validation/integration.py:353-438` | Validation supports only `simple_period_return`, `trade_count`, one exact grade and precommitted Holdout semantics. |
| C9 | Existing immutable Integration v1-v5 and fixed-singleton receipts | Existing public signatures, bytes, hashes, grades and fixed-singleton route must not change. |
| C10 | `research/quality-bband-financial-governance-source-matrix.md` | Raw statements and known official documents are finite-capture candidates only; no reviewed source supplies full availability, revision or terminal-set closure. |
| C11 | `implementation/plans/quality-bband-financial-source-sentinel-v1.md` | One exact `000651.SZ`/2023 annual-report SourceSnapshot acquisition tool is PR #1 and terminates before Bundle/Strategy authority. |
| C12 | `implementation/plans/quality-bband-financial-availability-policy-v1.md` | Current PR lacks official publication metadata/confirmation, so its availability outcome is blocked. |
| C13 | `implementation/plans/quality-bband-financial-revision-lineage-v1.md` | Tushare has no provider revision closure; source-bound identities must not impersonate provider revisions. |
| C14 | `implementation/plans/quality-bband-financial-presentation-selection-v1.md` | Latest visible eligible presentation and coherent statement trio are separate point-in-time feature-input authority. |
| C15 | `implementation/plans/quality-bband-industrial-financial-field-mapping-v1.md` | PR #1 fields are insufficient for formula authority; official CNY-yuan unit evidence and expanded raw fields are required. |
| C16 | `implementation/plans/quality-bband-financial-source-sentinel-v2.md` | Additive v2 successor is open stacked PR #2 and remains acquisition-only/unaccepted. |
| C17 | `research/quality-bband-real-capture-readiness.md` | Approved-proxy capture produced verified five-member SourceSnapshot `sha256:dec0abb1828f8b87256347e72b6ccfe2f84a2ca13f36aa1415c9a53e96a0c7d5`. |
| C18 | `implementation/plans/quality-bband-financial-declaration-implementation-v1.md` | Stacked PR #3 and real declaration candidate `sha256:59e09eb542a6e2ec480a7b8ed322d9ae9106416460f0999216fd5564f7278007` resolve fixed-report publication/unit/debt/D&A semantics but remain unaccepted/non-decision-grade. |
| C19 | `implementation/plans/quality-bband-financial-normalization-implementation-v1.md` | Stacked PR #4 publishes exact source-bounded revisions and observation set `sha256:632206f85bcff71dbcccfd20a3593e14fb895b33bd138ac25bbf9b947e4a4a7c`; closure/decision-grade/deployment remain false. |
| C20 | `implementation/plans/quality-bband-financial-presentation-selection-implementation-v1.md` | Stacked PR #5 publishes fixed current-only trio selection `sha256:34d09c7649143ee784f95f25873dd462ee56fc37cae91fa8bc7a604ef37f890c`; generic comparative-adjustment and revision-chain coverage remain out of scope. |
| C21 | `implementation/plans/quality-bband-financial-history-source-sentinel-v3.md` | Stacked PR #6 publishes 19-member historical SourceSnapshot `sha256:aee2ea78f3d51185110bc927836ce77ed51f590a9c7b4c26ee7ecd951cbf8d4b`, completing raw fixed-issuer 2018–2022 source coverage only. |

## Ownership

- **Orchestrator:** current Platform planning session.
- **Planning worktree:** `/home/ygguo/agent-projs/ai-crypt/platform-a-share-strategy` / `research/a-share-strategy`.
- **Implementation worktrees:** not created until packet becomes `READY`.
- **Data acquisition/Builder owner:** Backtest repository owner.
- **Backtest public PREP owner:** Backtest Runtime repository owner.
- **Platform integration owner:** Platform repository owner after accepted Backtest SHA exists.
- **Research/Validation owner:** respective package owners; no changes before public PREP acceptance.
- **Shared registry/status owner:** one serialized governance fan-in writer.

## Current and proposed flow

Before:

```text
mutable local A-share lake / exploratory scripts
→ non-authoritative research results

accepted Backtest A-share route
→ fixed xshe:000001 + July-2026 + zero target/no trade only
```

After:

```text
Backtest-owned finite acquisition
→ G12A SourceSnapshot
→ QB-DATA pure Bundle construction + coverage
→ retained cn_a_share_portfolio_development_authority@1
→ deterministic public target-stream build
→ prepare_cn_a_share_portfolio_development_backtest
→ PreparedBacktestExecution
→ execute_experiment
→ verified completed analysis
→ deterministic candidate
→ frozen holdout + validate_candidate
```

## Symbol plan

### Backtest data/Builder lane

| Symbol | Action | Exact responsibility | Consumer |
| --- | --- | --- | --- |
| `CnAShareQualityResearchBundleDeclarationV1` | add after contract approval | Freeze coverage, catalog, source members, closure refs and capabilities. | Builder operation. |
| `CnAShareQualityResearchBundleOutcomeV1` | add | Exactly one result/failure; constructor recomputes identity. | G12C/D publication lane. |
| `build_cn_a_share_quality_research_bundle_v1` | add | Pure normalization, exact cover and Bundle construction. | Acquisition/governance caller. |
| financial/audit/governance/valuation observation payloads | add | Preserve raw normalized point-in-time facts and revisions only. | MarketBundle observation views. |
| financial/governance/valuation coverage reports | add | Mechanical exact-cover and structured failure. | Portfolio authority qualification. |

### Backtest Runtime lane

| Symbol | Action | Exact responsibility | Consumer |
| --- | --- | --- | --- |
| `CnASharePortfolioDevelopmentProviderInputs` | add | Compact caller facts: Build manifest, authority ref, strategy/sleeve, initial CNY cash. | Public PREP. |
| `CnASharePortfolioPreparationFailureCode` | add | Stable ordered public failure vocabulary. | Research/Validation failure mapping. |
| `CnASharePortfolioPreparationFailure` | add | Carries code without private object leakage. | Public caller. |
| `prepare_cn_a_share_portfolio_development_backtest` | add | Sole deep preparation operation; owns request/semantic identity/Profile/execution transport. | Platform. |
| `crypto_quant_backtest.__init__` | export | Export only approved public names. | Cross-package callers. |

### Strategy target-stream lane

| Symbol | Action | Exact responsibility | Consumer |
| --- | --- | --- | --- |
| `QualityBbandStrategyDefinitionV1` | freeze in an approved owner module | Exact quality filter, two volume parameter values, sizing and exit state. | Deterministic target generation. |
| `QualityFeatureManifestV1` | add | Bind raw statement refs and exact ROIC/FCF/leverage/valuation formulas plus code identity. | Strategy build and target evidence. |
| target-stream builder operation | design/approve separately | Consume point-in-time views and publish complete target snapshots; no fills/accounting. | QB-PREP retained Bundle. |

### Platform lane after Backtest acceptance

| Symbol | Action | Exact responsibility | Consumer |
| --- | --- | --- | --- |
| existing `FrozenExperimentInputs` / `execute_experiment` | reuse | Execute finite explicit Trial declarations only. | Research manifest/candidate. |
| existing `SelectionPolicy` | reuse | `simple_period_return > 0`, `trade_count >= 20`, descending return/trade count, one selection. | Candidate selection. |
| existing `ValidationPolicy` / `validate_candidate` | reuse | Development grade, threshold `0.10`, minimum trade count `8`, exact Holdout. | ValidationReport. |
| Backtest consumer integration test | add | Public prepare→execute→repository→analysis evidence flow. | Platform acceptance. |

## Exact value and identity closure

| Value/artifact | Exact type/schema | Identity/preimage | Consumer |
| --- | --- | --- | --- |
| Fold A source | future `SourceSnapshot@1` | Exact source bytes, member paths/hashes, acquisition receipt and limitations. | QB-DATA. |
| Fold B source | independent `SourceSnapshot@1` | Must not reuse Fold A identity. | QB-DATA. |
| Research Bundle | future G12D `MarketBundleRef` | Manifest exact-cover of catalog/capability streams and content hashes. | Portfolio authority/PREP. |
| Portfolio authority | `cn_a_share_portfolio_development_authority@1` | Bundle/catalog/coverage/Profile/Build/account/grade/limitations refs. | Public PREP. |
| Strategy feature manifest | `quality_feature_manifest@1` | Raw observation refs, formula versions, Strategy code Build ref. | Target stream. |
| Target stream | accepted precomputed target capability | Complete TargetSnapshot events, Decision/availability instants and digest. | PREP/Engine. |
| Request/Semantic Run | existing Backtest-owned values | Derived only inside public PREP. | Runtime/evidence. |
| Analysis | existing verified analysis | Completed publication + execution-result + metric profile. | Research/Validation. |
| Candidate | existing Research artifact | Exact Experiment/manifest/selected Trial refs. | Validation. |
| Holdout | existing Validation value | Bundle ref, revision and half-open interval with `selection_observed=false`. | Validation plan. |

## Finite experiment closure

Per Fold:

- Candidate parameter tuples, canonically sorted:
  1. `((bandwidth_percentile,"0.10"),(entry_rule,"bband_breakout"),(volume_multiple,"1.50"))`
  2. `((bandwidth_percentile,"0.10"),(entry_rule,"bband_breakout"),(volume_multiple,"2.00"))`
- Benchmark diagnostic tuples:
  1. `annual_direct`
  2. `ma120_cross`
- Seed tuple: `(0,)`.
- Scenario ref: `a-share.domestic-cash.daily-next-open.base-cost.v1` after publication.
- Grade: `development`.
- Candidate SelectionPolicy: completed only; return `> 0`; trades `>= 20`; return descending; trades descending; one selection; Trial ref ascending tie-break.
- Validation: `simple_period_return gte 0.10`; minimum trade count `8`.
- Economic-run ceiling: six per Fold including OOS and replay; twelve total.

## Failure precedence

| Priority | Condition | Outcome/evidence |
| ---: | --- | --- |
| 1 | malformed plan/declaration/ref/version | constructor failure before I/O |
| 2 | source/catalog/Bundle authority mismatch | QB-DATA structured failure; no Bundle |
| 3 | Universe/status/rule/financial/governance/action coverage failure | qualification failure; no portfolio authority |
| 4 | authority/Profile/target/build mismatch | QB-PREP structured failure; no request |
| 5 | request publication/PREP failure | provider/local failure; no fabricated terminal |
| 6 | Backtest BLOCKED/CANCELLED/FAILED | preserve exact terminal/status |
| 7 | completed evidence verification/retention/tamper failure | local/provider failure; no analysis |
| 8 | missing metric or insufficient trades | no selection or Validation `inconclusive`, never zero |
| 9 | holdout conflict/reservation failure | stop before OOS success |
| 10 | OOS below threshold | Validation `rejected` |

## Security and trust boundaries

- **Untrusted:** provider responses, local lake exports, authority/Bundle bytes, target-stream bytes and all external refs.
- **Validation:** exact type/version/hash, duplicate-key/non-finite rejection, revision lineage, availability, catalog and coverage closure.
- **Secrets:** provider tokens environment-only; absent from files, refs, logs, fixtures and exceptions.
- **Money/data loss:** no live broker/account state; no destructive restore or provider DB mutation.
- **Side-effect authority:** acquisition may write only its approved snapshot root; publication uses existing atomic repository semantics; no push/merge/release without explicit authority.

## Compatibility and immutable artifacts

- Existing generic cash and model-bound PREP signatures remain byte/behavior compatible.
- Fixed-singleton Tushare v1/v2 authority, route, Run, assessment and protected hashes remain unchanged.
- Existing Domain/Engine/Runner/Profile generic loops gain no market-name branch.
- Existing Analysis metric profile remains `simple_period_return` + `trade_count`; no local Sharpe/drawdown metric enters formal evidence.
- No version fallback or grade downgrade exists.
- Cache/replay cannot refresh governance time or create a second economic run.

## Forbidden paths backed by authority

| Authority | Violating path | Required route |
| --- | --- | --- |
| C1/C6 | custom PnL/backtest script used as Platform evidence | public PREP → Backtest Runtime → verified repository/analysis |
| C1 | import private Backtest facade/runner/engine/composition | `crypto_quant_backtest` public root |
| C3/C4 | direct Runtime read of mutable DuckDB/Tushare/API | acquisition → SourceSnapshot → Builder → retained Bundle |
| C7 | final/current constituents projected backward | revisioned Universe + G12K coverage |
| C9 | modify fixed-singleton artifacts to generalize | additive portfolio authority and public seam |
| C8 | attach Sharpe/drawdown to Validation | exact supported OosRule only; other statistics advisory |

## Sentinel and validation

| Authority | Cheapest check that can fail |
| --- | --- |
| C3/C4 | Missing one required financial source member returns `FINANCIAL_PAYLOAD_INCOMPLETE` and writes no publication. |
| C5/C6 | Public PREP with foreign portfolio-authority ref returns `AUTHORITY_REF_INVALID` before request publication. |
| C7 | Universe revision gap fails coverage; affected Instrument is not silently dropped. |
| C8 | Validation rejects unsupported metric key and holdout with `selection_observed=true`. |
| C9 | Protected fixed-singleton file/hash guard remains exact after additive changes. |

Candidate acceptance tiers:

1. Builder focused schema, mutation, precedence, deterministic hash and reopen checks;
2. adjacent G12 catalog/Universe/action/price coverage and architecture boundaries;
3. PREP focused public operation, target causality, Profile scope, replay and failure checks;
4. full Backtest suite/static typing/import boundaries/lock/diff/gitleaks;
5. independent Backtest reviewer;
6. accepted remotely reachable Backtest revision;
7. Platform pin/fan-in integration tests;
8. Research/Validation focused and full Platform gates.

## Open decisions / blockers

1. **Source authority:** no accepted full-market statement, audit, penalty or pledge provider contract; reviewed public sources are `SOURCE_BOUNDED_ONLY` or `MISSING`.
2. **Availability authority:** the policy is frozen, but PR #1 lacks official publication metadata/confirmation and therefore emits no `available_at`.
3. **Revision/selection authority:** contracts are frozen but unaccepted; provider terminal-set closure remains unavailable.
4. **Formula input:** raw 2018–2022 history and the selected 2023 trio exist, but period-specific 2018–2022 unit/note/availability declarations, normalization and selection do not.
5. **First sentinel acceptance:** QB-FIN-SENTINEL-01 is open PR [`YungeG/quant-backtest#1`](https://github.com/YungeG/quant-backtest/pull/1) at commit `e7e874fc58e0911b7df1cd0463387526afcb845d`, but remains unmerged/unaccepted; no merge authority was granted.
6. **Credentialed capture:** approved proxy capture succeeded; credentialed broad-market/Fold capture is still unauthorized and unavailable.
7. **Universe/action coverage:** general G12K remains blocked.
8. **Interface approval:** Backtest owner has not approved provisional capability/type/function names.
9. **Target-stream producer:** exact owner module and public operation are not frozen.
10. **Profile qualification:** multi-instrument ordinary-A-share account scope is not accepted.
11. **Scenario ref:** `a-share.domestic-cash.daily-next-open.base-cost.v1` is a proposed identity, not a published ref.
12. **Metric limitation:** formal Validation cannot enforce drawdown or benchmark-relative excess.
13. **Permissions:** commit/push, stacked PR creation and approved-proxy artifact publication were authorized; no merge, acceptance, deployment or real-trading authority was granted.

## Readiness decision

`NOT_READY`.

The source-discovery, financial contract-freeze and fixed-scope acquisition/declaration/normalization/selection/history-source candidate lanes are complete. PRs #1–#6 await **Backtest-owner review/acceptance**. The next safe research lane is historical PDF/unit/debt/D&A audit and period-specific declarations; broad QB-DATA-01 and QB-PREP-01 remain blocked.

## Next owner and first action

- **Next owner:** Backtest G12A repository owner/reviewer.
- **Candidate:** PR [`YungeG/quant-backtest#1`](https://github.com/YungeG/quant-backtest/pull/1), remote commit `e7e874fc58e0911b7df1cd0463387526afcb845d`; local worktree tracks it exactly.
- **Review set:** the three candidate files plus `implementation/plans/quality-bband-financial-source-sentinel-v1.md`.
- **Evidence:** 33 focused tests; 344 final adjacent/architecture tests; prior 2463-test broad regression; exact live PDF hash check; independent review with no blocking/high/medium findings.
- **First decision:** accept PR #1 and publish its governance receipt, or reject it with contract-level changes.
- **Stacked successor:** PR [`YungeG/quant-backtest#2`](https://github.com/YungeG/quant-backtest/pull/2), head `146cd227b2fc707726e133dbbd08cde356f21dcd`, base PR #1; 23 focused and 150 adjacent tests after proxy correction, independent review clean.
- **Real capture:** verified SourceSnapshot `sha256:dec0abb1828f8b87256347e72b6ccfe2f84a2ca13f36aa1415c9a53e96a0c7d5` at the approved artifact root.
- **Declarations:** stacked PR [`YungeG/quant-backtest#3`](https://github.com/YungeG/quant-backtest/pull/3), commit `b4124d5985a6f9cbd39221fd55286abf5608b6b8`; real candidate declaration `sha256:59e09eb542a6e2ec480a7b8ed322d9ae9106416460f0999216fd5564f7278007`.
- **Normalization:** stacked PR [`YungeG/quant-backtest#4`](https://github.com/YungeG/quant-backtest/pull/4), commit `fa58e68d7b51ee5517e5a14c87c3590d1bda2976`; real observation set `sha256:632206f85bcff71dbcccfd20a3593e14fb895b33bd138ac25bbf9b947e4a4a7c`.
- **Selection:** stacked PR [`YungeG/quant-backtest#5`](https://github.com/YungeG/quant-backtest/pull/5), commit `5338d8046fa0f304d4a9590989c59ceffb51270b`; real selection `sha256:34d09c7649143ee784f95f25873dd462ee56fc37cae91fa8bc7a604ef37f890c`.
- **History source:** stacked PR [`YungeG/quant-backtest#6`](https://github.com/YungeG/quant-backtest/pull/6), head `64159f81fa6f831990690dd133587b96533a0362`; real 2018–2022 SourceSnapshot `sha256:aee2ea78f3d51185110bc927836ce77ed51f590a9c7b4c26ee7ecd951cbf8d4b`.
- **Second decision:** accept PRs #2–#6 and authorize period-specific 2018–2022 official statement/unit/note declarations.
- **Acceptance gate:** accepted acquisition/declarations/normalization/selection plus five-year coherent statement evidence; none grants Strategy, Validation or deployment authority.
