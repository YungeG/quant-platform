---
name: quant-strategy-research
description: Repository-specific execution skill for operating this codebase's existing Research, Backtest, Validation, and Promotion flow. Use only when planning, executing, or auditing a concrete crypto/Binance USD-M or A-share strategy experiment, explicit parameter and seed trials, model-bound backtests, holdout/OOS validation, candidate selection, or walk-forward study with this Platform. Never use for discovering, comparing, recommending, installing, or creating skills (use find-skills or creating-skill), generic market commentary, standalone VectorBT/Backtrader work, or live deployment.
---

# Quant Strategy Research

Use the Platform as the authority. This skill plans and coordinates research; it never implements a second simulator, market rules, accounting, metrics, evidence verification, or deployment policy.

## Route the request

If the user is asking to discover, compare, recommend, install, or create a skill, this skill is the wrong route; use `find-skills` or `creating-skill` instead.

Choose exactly one mode:

- **Plan** — turn an idea into a finite, precommitted research design.
- **Execute** — run the design only when a concrete accepted public Backtest preparation operation exists.
- **Review** — audit existing Experiment, Candidate, Backtest, or Validation evidence.

Identify the market before proceeding. Read [Binance USD-M](references/binance-usdm.md) for crypto perpetuals or [A-share](references/cn-a-share.md) for China equities. Read [Research protocol](references/research-protocol.md) before Execute or Review, and during Plan when exact Platform seams or failure handling matter.

## Non-negotiable authority rules

1. Import sibling modules only through their public package roots: `crypto_quant_research`, `crypto_quant_backtest`, `crypto_quant_validation`, `crypto_quant_foundation`, and `crypto_quant_promotion` when Promotion is explicitly in scope.
2. Never import Backtest implementation modules such as `facade`, `runner`, `engine`, `composition`, private resolvers, publishers, or repositories.
3. Never use VectorBT, Backtrader, JoinQuant results, spreadsheets, or custom PnL code as Platform evidence. They may be explicitly labelled exploratory comparisons only.
4. Backtest exclusively owns fills, fees, funding, settlement, accounting, PnL, result grade, terminal outcomes, evidence integrity, and derived analysis.
5. Research exclusively owns the finite Experiment, task universe, selection declaration, manifest, family, and candidate.
6. Validation exclusively owns sample-consumption semantics, holdout admission, OOS interpretation, and `ValidationReport`.
7. A Backtest run must not access the network, mutable provider APIs, the system clock for economic behavior, or unfrozen market data.
8. Only verified completed publications may enter analysis. Preserve `BLOCKED`, `FAILED`, and `CANCELLED`; never convert them to zero metrics.
9. A backtest never authorizes Shadow, Live, credentials, orders, or deployment.

## Plan mode

Produce a research plan with all of the following:

1. A falsifiable hypothesis and rejection condition.
2. The requested market and the exact accepted provider/profile capability needed.
3. Immutable data slices with dataset revision and half-open intervals.
4. Explicit, finite, canonically sortable parameter combinations. Expand ranges before constructing an authoritative `ExperimentSpec`; no adaptive or result-driven search.
5. Explicit nonnegative seeds, scenario refs, Backtest template/strategy identity, metric profile refs, grade, and budget.
6. A predeclared `SelectionPolicy` using only eligible completed analyses.
7. A holdout frozen before selection observation and a `ValidationPolicy` compatible with current Validation capabilities.
8. Known limitations, unsupported capabilities, and whether the request is **executable** or **plan-only**.

If no concrete accepted public preparation operation exists for the requested strategy and market, stop at Plan. Name the missing public seam; do not compose private Backtest objects as a workaround.

## Execute mode

Follow this order without skipping commit points:

1. Verify the working tree, accepted package pins, MarketBundle retention, provider/profile availability, and requested result grade.
2. Construct only existing public immutable values. Let their constructors reject malformed, duplicate, unsorted, implicit, or foreign axes before I/O.
3. Publish and reserve through existing Research and Validation operations. Every sample reservation must be accepted before its corresponding read or Backtest call.
4. Prepare each trial only through a concrete accepted public Backtest preparation operation. Platform code must not derive Backtest request hashes, semantic run IDs, resolved cases, or bundle semantics.
5. Execute through `execute_experiment()` or `execute_model_experiment()` and consume the returned published refs.
6. Resolve Backtest observations through the public evidence repository. Call analysis derivation only for verified completion.
7. Select deterministically from the exact completed Experiment manifest.
8. Freeze the sample ledger and Validation plan before OOS work; reserve the holdout before the OOS read/run.
9. Run `validate_candidate()` and report the exact `supported | rejected | inconclusive` result or explicit no-report failure.
10. Replay once when practical. Replay must reuse semantic evidence and must not perform a second economic run or refresh governance time.

## Review mode

Check, in precedence order:

1. Exact ref type/version and owner-log publication.
2. Candidate → Family → Manifest → Experiment → Trial provenance.
3. Trial request/publication and Analysis source-publication/execution-hash links.
4. Sample reservation coverage and holdout contamination.
5. Accepted Backtest grade and metric profile.
6. Terminal/provider/tamper/retention handling.
7. Deterministic selection, tie break, replay, and absence of manual winners.
8. Validation case exact-cover and no zero-filling of missing metrics or insufficient trades.
9. Promotion, if requested, consumes only governed evidence and grants no deployment authority.

## Walk-forward default

Represent walk-forward as multiple independent existing Experiment + Validation flows, one per fold. Each fold must train/discover, select, and validate without observing its holdout. A cross-fold table or Markdown summary is advisory only and must not enter Promotion. Do not invent `WalkForwardPlan`, aggregate grades, or canonical cross-fold evidence until a separate accepted contract requires them.

## Output

Return these sections:

1. **Mode and market**
2. **Capability decision** — executable or plan-only, with the exact provider/profile reason
3. **Research design or published refs**
4. **Validation result**
5. **Limitations and blockers**
6. **Next safe action**

Plan is complete only when every axis and holdout is explicit. Execute is complete only with published Research refs and a Validation result/no-report reason. Review is complete only when every finding cites an exact ref, artifact, log entry, source path, or verified operation.
