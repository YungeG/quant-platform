# Research: Minimal credible A-share long-only baseline

## Summary

Recommend a **CSI 300 constituent low-volatility baseline**: at each quarter-end, rank the point-in-time eligible CSI 300 universe by trailing 252-trading-day daily-return volatility, hold the lowest-volatility 100 names with capped inverse-volatility weights, and submit the resulting target for execution no earlier than the next eligible trading-day open. This is the smallest credible family because it needs only point-in-time membership, daily prices, trading status/rules, and corporate actions—unlike value/quality, it does not require historically available financial statements; unlike conventional monthly momentum, China-specific evidence is materially weaker and more horizon-dependent.

This should initially be treated as **development-grade research, not a decision-grade claim**. The repository’s Backtest design already models the required execution path, T+1 availability, price-limit liquidity blocking, lots, settlement, and corporate-action lifecycle, but its current A-share data receipts explicitly do **not** establish general historical universe/survivorship, corporate-action, provider-completeness, or rule-history closure ([Backtest acceptance matrix](../backtest/docs/implementation/acceptance-matrix.md)).

## Platform fit

1. The strategy is a deterministic `PortfolioStrategy`/target-stream use case with no model build, training, tuning, or new ML infrastructure. The platform is designed for immutable declarations, exact task outcomes, candidate selection, and later validation rather than in-runtime search ([Research Platform design](../research-platform/design.md)).
2. The target must enter the existing authoritative path—portfolio target, sizing, order planning, market rules, execution, settlement, accounting, evidence—and must not compute returns in a side simulator ([Backtest system design §§4, 7](../backtest/docs/architecture/backtest-system-design.md)).
3. Validation should reserve and protect the final holdout before reading it, then run the unchanged public Backtest seam and emit `supported | rejected | inconclusive` ([Strategy Validation design](../strategy-validation/design.md)).
4. The existing A-share Backtest profile already defines Asia/Shanghai sessions, point-in-time rule books, T+1 sellable quantity, board-specific price limits, suspension handling, 100-share sizing/odd-lot closure, corporate-action lifecycle, and conservative next-eligible-open execution. It also states that a buy at an upper-limit open or sell at a lower-limit open is liquidity-blocked rather than filled ([Backtest system design §§11.5–11.14, 12.1](../backtest/docs/architecture/backtest-system-design.md)). Reuse these semantics; do not duplicate them in strategy code.

## Candidate-family comparison

| Family | Evidence relevant to China A-shares | Minimum data | First-pass judgment |
| --- | --- | --- | --- |
| **Low volatility** | A China A-share study reports a strong, distinct and investable low-risk effect over 2000–2018, robust across sectors and time; volatility, rather than beta, is the main driver, and the effect remains among larger/liquid stocks with low turnover ([Blitz, Hanauer & van Vliet, 2021](https://link.springer.com/article/10.1057/s41260-021-00218-0)). A broader China anomaly study finds value, risk, and trading anomalies present, while past-return and quality evidence is weaker ([Jansen, Swinkels & Zhou working paper](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3810114)). CSI publishes an implementable low-volatility methodology using the CSI 300 universe, trailing one-year daily-return volatility, 100 constituents, sector quotas, inverse-volatility weighting, and semiannual reconstitution ([CSI 300 Sector Neutral Low Volatility methodology](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/527_930846_Index_Methodology_cn.pdf)). | Point-in-time membership, daily prices/returns, corporate actions, trading/rule status | **Recommend.** Strongest combination of China-specific evidence, official implementability precedent, low data burden, and modest expected turnover. |
| **Momentum** | Recent China research finds no robust weekly/monthly momentum but significant **daily** momentum associated with new-investor activity ([Gao, Jiang, W. A. Xiong & W. Xiong](https://www.nber.org/papers/w31839)); another recent working paper reports conventional winner-minus-loser profits before 2005 but dissipation later ([Zhang & Zi](https://czi.finance/assets/ChinaMom.pdf)). This makes a slow long-only 12–1 baseline poorly supported, while a daily strategy would require higher-fidelity execution and cost modeling. | Daily prices; practical version needs high-turnover execution quality | **Do not choose first.** Evidence is horizon/regime dependent and the supported daily effect is a poor fit for the smallest daily-bar cash-equity baseline. |
| **Value/quality** | China evidence supports value after removing the smallest shell-value stocks: Hu, Chen, Shao & Wang find size and value factors in China and emphasize the distortion from the smallest firms ([authors’ paper](https://web.mit.edu/wangj/www/pap/HuChenShaoWang19.pdf)). Quality evidence exists, but broader replication finds it less consistent than risk/value families ([Jansen, Swinkels & Zhou](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3810114)). | Point-in-time filings, publication timestamps/revisions, accounting normalization, shares and prices | **Defer.** Credible only after the platform has publication-time financial-statement data; otherwise six-month lags or current fundamentals would be unverified approximations. |

## Recommended baseline specification

### 1. Universe construction

**Sourced facts**

- CSI describes the CSI 300 as 300 large and liquid representative Shanghai/Shenzhen securities. Its methodology excludes ST/*ST from the sample space and applies listing-age and investability rules ([CSI 300 methodology](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/000300_Index_Methodology_cn.pdf)).
- The official low-volatility index uses the contemporaneous CSI 300 constituent set as its universe and selects 100 securities by trailing one-year daily-return volatility ([CSI low-volatility methodology](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/527_930846_Index_Methodology_cn.pdf)).

**Proposed assumptions**

- Base universe on the **official point-in-time CSI 300 constituent list effective at the decision date**, not today’s members reconstructed backward.
- Apply a conservative execution-eligibility screen at the decision instant: ordinary seasoned A-shares only; exclude current ST/*ST/risk-warning names, names without an unambiguous board/listing phase, delisted names after their effective removal, and names lacking 200 valid daily return observations in the preceding 252 trading sessions.
- Do not infer suspension, board, ST status, listing date, or membership from missing bars, zero volume, ticker patterns, or the latest security master. These must be point-in-time source facts.
- A security suspended on the decision date remains part of the ranked universe if its historical signal is valid, but no new order may fill until the existing rule/execution profile finds an eligible bar. Run a sensitivity that excludes decision-date suspensions; large divergence is a warning.

### 2. Point-in-time and survivorship controls

**Required, not optional**

1. Preserve stable instrument identity through ticker/name changes; retain delisted securities and their terminal history.
2. Version constituent membership with effective and publication/availability times. A later-restated list must not rewrite what was knowable at an earlier decision.
3. Use corporate-action-adjusted returns for the **signal only**, constructed from actions available/effective by each simulated instant. Never use a vendor’s present-day fully adjusted series as execution evidence.
4. Use raw executable OHLC/price-limit reference data for fills, rules, accounting, and valuation, consistent with the Backtest design’s explicit prohibition on retrospective adjustment of execution prices ([Backtest system design §11.14](../backtest/docs/architecture/backtest-system-design.md)).
5. If historical membership, listing lifecycle, risk-warning status, rule interval, suspension status, or a held-name corporate action is missing or ambiguous, mark the run `BLOCKED`; do not silently drop the security.

**Current repository gap**

The Backtest acceptance register says the accepted Tushare A-share slices prove only bounded/singleton observations and explicitly leave historical membership, dynamic universe, survivorship, corporate-action lifecycle, authoritative absence, and provider completeness unqualified ([Backtest acceptance matrix, G12L/G12M rows](../backtest/docs/implementation/acceptance-matrix.md)). Therefore a broad historical strategy result is not yet decision-grade even though the runtime semantics exist.

### 3. Signal and portfolio construction

**Proposed baseline**

- Decision dates: last trading session of March, June, September, and December.
- Observation cutoff: the close of the decision session; all inputs must have `available_time <= decision_time`.
- Return series: daily close-to-close total returns over the preceding 252 trading sessions, with point-in-time corporate-action treatment.
- Eligibility: at least 200 valid returns; no forward filling across suspension/no-trade gaps.
- Signal: sample standard deviation of valid daily total returns. Rank ascending; stable tie-break by canonical instrument ID.
- Selection: lowest-volatility 100 eligible names, or `BLOCKED` if fewer than 100 qualify.
- Raw weight: `1 / volatility`.
- Concentration control: iteratively cap each name at 2%; redistribute excess pro rata among uncapped selected names. Keep residual cash created by lot rounding; do not lever.
- No sector-neutralization in v1. It would require a separately qualified point-in-time industry taxonomy. Report ex-post sector weights only when such data is available without contaminating selection.

This deliberately simplifies the official CSI sector-neutral low-volatility method while retaining its core observable signal. The simplification must be labeled as a proposed research rule, not represented as replication of index 930846.

### 4. Rebalance cadence and execution delay

- Rebalance quarterly to reduce turnover while still refreshing a one-year signal. Semiannual (official-index-like) and monthly (academic-like) cadences are **precommitted robustness cases**, not parameters to optimize on holdout.
- Generate targets after the decision-date close. Submit orders at the next session’s planning phase; earliest fill is the **next eligible real bar open**, never the signal bar.
- Use the existing `next_eligible_bar_open.v1` convention: no same-bar fill, no forward-filled bar, and no use of future high/low/close/volume to decide an opening fill ([Backtest system design §12.1](../backtest/docs/architecture/backtest-system-design.md)).
- Add a mandatory delay stress test using the second eligible open. If the conclusion depends on one-day timing, reject practical robustness.

### 5. T+1, lots, price limits, and suspensions

**Sourced mechanics**

- Exchange rules state that securities bought before settlement generally cannot be sold unless the product is eligible for turnaround trading; ordinary A-shares therefore require T+1 sellability handling ([SZSE Trading Rules, art. 3.1.4](https://docs.static.szse.cn/www/lawrules/rule/allrules/bussiness/W020230217564423808793.pdf)).
- Main-board auction buy orders are in 100-share multiples; a remaining sell quantity below 100 shares is sold in one order ([SSE trading mechanism](https://english.sse.com.cn/start/trading/mechanism/); [SZSE investor rule explanation](https://investor.szse.cn/column/qa/t20230306_599093.html)).
- Main-board ordinary stocks generally have a 10% daily limit and risk-warning stocks 5%, while listing-phase and other exceptions exist; board-specific rules differ ([SZSE trading overview](https://www.szse.cn/English/services/trading/tradOverview/), [SZSE 2023 rule explanation](https://investor.szse.cn/column/qa/t20230306_599093.html)).

**Backtest treatment**

- T+1 must constrain **sellable quantity**, not merely delay settlement cash in a strategy-side rule.
- Size buys to valid lots; permit only rule-supported full odd-lot closure on sells. Cash left after lot rounding remains cash.
- Resolve historical board/risk/listing-phase price-limit bands from the point-in-time rule book. Do not apply today’s 10% rule over all history.
- At an upper-limit open, a buy remains unfilled; at a lower-limit open, a sell remains unfilled. Keep/expire according to the configured DAY/rebalance policy. This is the repository’s conservative daily-bar liquidity convention, not a claim that all limit-price orders are impossible to execute.
- Explicit suspension/no-session produces no fill. Missing status or missing bar without authoritative classification blocks the run.

### 6. Transaction costs and taxes

**Sourced facts**

- SSE publishes exchange handling fees and taxes collected for A-share trading; the A-share auction handling fee was reduced to 0.00341% of turnover on both sides from 28 August 2023 ([SSE fee schedule](https://english.sse.com.cn/start/taxes/), [SSE fee reduction notice](http://english.sse.com.cn/news/newsrelease/c/5725439.shtml)).
- China reduced securities transaction stamp tax by half from 28 August 2023; the tax is charged on the transfer/sell side ([Ministry of Finance notice/explanation](http://www.mof.gov.cn/zhengwuxinxi/caijingshidian/xinhuanet/202308/t20230830_3904782.htm)).

**Proposed cost model**

- Use the Backtest A-share fee/tax rule timeline where source-qualified; do not hard-code one current rate across history.
- Broker commission is account-specific, so v1 should declare rather than “source” it: **3 bps each side, CNY 5 minimum per order** as the base assumption.
- Add deterministic slippage of **5 bps each side** for the development baseline, separately identified from fees/taxes. This is an uncalibrated assumption and therefore cannot support decision-grade promotion.
- Precommit stress cases: broker commission 1.5/3/5 bps, slippage 0/5/10/20 bps, and double all non-tax trading costs. Preserve historical stamp tax and official fees in every case.
- Report gross return, each cost component, turnover, orders hitting minimum commission, and net return. A result that survives only the zero-slippage case is falsified for practical use.

### 7. Corporate actions

- Required event coverage includes announcements and revisions, record/eligibility dates, ex/effective dates, share-listing dates where applicable, and payment dates.
- Support at minimum cash dividends, bonus/capitalization shares, splits/consolidations, rights issues, mergers/delistings, and symbol migrations when they affect a held or eligible security.
- Capture entitlement from the historical registered position at the record boundary; do not use the current position. Book share changes and cash payments as separate lifecycle events.
- If an unsupported action affects an eligible/held name, block the run. Excluding the name after observing the action would introduce look-ahead and selection bias.
- Benchmark and strategy returns must use consistent total-return treatment.

### 8. Benchmark and reporting

- Primary benchmark: **CSI 300 Total Return Index, H00300**, which reinvests gross cash dividends; CSI identifies 000300 as the price index and H00300 as its total-return derivative ([CSI 300 factsheet](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/en/000300factsheeten.pdf); [CSI calculation rules](https://oss-ch.csindex.com.cn/contract/cms_add/20240726155157-Calculation%20Rules%20for%20Equity%20Indices%20of%20China%20Securities%20Index%20Company%20Limited.pdf)).
- Secondary diagnostics: CSI 300 price index, equal-weight eligible-universe portfolio, and cash.
- Report annualized total return, annualized volatility, Sharpe (with a declared CNY risk-free series or zero-rate diagnostic), maximum drawdown, downside deviation, beta, tracking error, information ratio, turnover, cost drag, cash drag, hit rate by calendar year, and sector/stock concentration.
- Do not compare a dividend-inclusive strategy with the CSI 300 price index as the sole benchmark.

### 9. Holdout and walk-forward design

**Proposed frozen split, subject to data coverage before any result is viewed**

- Warm-up: 2005–2006.
- Research/development: 2007–2016.
- Pre-holdout validation: 2017–2020.
- Untouched final holdout: 2021–2025.

If qualified data do not cover these dates, shift the boundaries once based only on coverage—not performance—while preserving roughly 50% development, 20% validation, and 30% final holdout and at least one major bull/bear cycle in the holdout.

Procedure:

1. Publish the exact strategy declaration, cost cases, data revision, metric profile, and split before reading final-holdout samples.
2. During development, compare only the three fixed cadences (monthly, quarterly, semiannual) and the fixed weighting variants (equal versus capped inverse-volatility). Select using development plus pre-holdout validation; do not tune volatility lookback or stock count.
3. Run expanding annual walk-forward diagnostics inside 2007–2020: form the rule from prior data, then evaluate the next calendar year without refitting.
4. Freeze one candidate and one metric profile; reserve the 2021–2025 sample through Validation before reading it.
5. Run the final holdout once. Any post-holdout modification creates a new candidate and requires a new untouched period.

### 10. Falsification criteria

Reject the baseline for further promotion if **any** of the following occurs on the untouched holdout:

1. Net annualized excess total return versus H00300 is `<= 0`.
2. Annualized volatility is not at least 10% below H00300, or maximum drawdown is worse than H00300. The strategy’s thesis is defensive equity; raw return alone is insufficient.
3. Net excess return becomes non-positive with 10 bps/side slippage or with doubled non-tax costs.
4. The second-eligible-open delay stress changes excess return from positive to non-positive.
5. More than 50% of cumulative excess return comes from one calendar year, or fewer than 3 of 5 holdout years have lower realized volatility than H00300.
6. Annualized one-way turnover exceeds 100%, or more than 10% of intended turnover remains unexecuted for five trading sessions because of suspensions/limits.
7. Removing the smallest 20% of eligible names by float market capitalization (diagnostic only, if point-in-time data are qualified) changes positive excess return to non-positive, indicating micro-cap dependence.
8. Any unresolved point-in-time membership, survivorship, corporate-action, rule-history, or availability issue is found to be result-relevant. In that case the result is `inconclusive`/`BLOCKED`, not supported.

Use block bootstrap confidence intervals for annualized excess return and volatility reduction as diagnostics. A positive point estimate with a 90% excess-return interval spanning zero should be reported as **inconclusive**, not promoted as evidence of alpha.

## Sourced facts versus assumptions checklist

| Item | Status |
| --- | --- |
| Exchange sessions, T+1, board lots, historical price-limit/suspension rules | Sourced market facts; must be resolved by effective date |
| CSI 300 membership and H00300 benchmark values | Sourced index data; historical snapshots/revisions required |
| One-year daily volatility and 100-name precedent | Sourced from official CSI low-volatility methodology |
| Low-volatility evidence in China | Sourced from original academic paper/working paper |
| Quarterly cadence, 200-observation minimum, 2% cap | Proposed assumptions |
| Capped inverse-volatility weighting without sector neutrality | Proposed simplified baseline |
| 3 bps commission/CNY 5 minimum and 5 bps slippage | Proposed account/simulation assumptions |
| Next-open, limit-open liquidity blocking, no forward fill | Existing Backtest simulation convention |
| Split dates and falsification thresholds | Proposed validation precommitments |

## Findings

1. **Low volatility is the decision-useful first baseline.** It has direct China A-share evidence, an official CSI implementation precedent, and only price/rule/corporate-action data requirements. [Blitz et al.](https://link.springer.com/article/10.1057/s41260-021-00218-0) [CSI methodology](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/527_930846_Index_Methodology_cn.pdf)
2. **Momentum should not be the first slow cash-equity candidate.** Recent evidence distinguishes significant daily momentum from absent/weak weekly and monthly momentum, creating an execution-quality burden outside the smallest credible baseline. [Gao et al.](https://www.nber.org/papers/w31839)
3. **Value/quality is data-blocked rather than disproved.** It is credible academically, but a point-in-time implementation needs filing availability and revision history that the current brief cannot establish. [Hu et al.](https://web.mit.edu/wangj/www/pap/HuChenShaoWang19.pdf)
4. **The platform semantics fit, but the broad A-share data authority does not yet.** Existing Backtest components cover the economic mechanics, while current receipts explicitly leave dynamic historical universe, survivorship, corporate actions, and provider completeness unresolved. [Backtest design](../backtest/docs/architecture/backtest-system-design.md) [Acceptance matrix](../backtest/docs/implementation/acceptance-matrix.md)
5. **The first engineering/data gate is not strategy code.** It is an immutable, point-in-time CSI 300 membership/security-master/corporate-action/rule-status bundle plus H00300 total-return benchmark data. Until then, only bounded development runs are honest.

## Sources

### Kept

- [SSE Trading Mechanism](https://english.sse.com.cn/start/trading/mechanism/) — official order, lot, and price-limit mechanics.
- [SZSE Trading Rules (2023 revision)](https://docs.static.szse.cn/www/lawrules/rule/allrules/bussiness/W020230217564423808793.pdf) — official T+1/turnaround and trading-rule authority.
- [SSE Fees and Taxes](https://english.sse.com.cn/start/taxes/) — official exchange fee schedule.
- [Ministry of Finance 2023 stamp-tax reduction](http://www.mof.gov.cn/zhengwuxinxi/caijingshidian/xinhuanet/202308/t20230830_3904782.htm) — official tax-policy source.
- [CSI 300 methodology](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/000300_Index_Methodology_cn.pdf) — official benchmark universe and corporate-action/index treatment.
- [CSI 300 Sector Neutral Low Volatility methodology](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/527_930846_Index_Methodology_cn.pdf) — official low-volatility implementation precedent.
- [Blitz, Hanauer & van Vliet, “The Volatility Effect in China”](https://link.springer.com/article/10.1057/s41260-021-00218-0) — original China A-share low-risk study with investability analysis.
- [Jansen, Swinkels & Zhou, “Anomalies in the China A-share Market”](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3810114) — original broad anomaly comparison.
- [Gao, Jiang, Xiong & Xiong, “Daily Momentum and New Investors in an Emerging Stock Market”](https://www.nber.org/papers/w31839) — original recent momentum evidence.
- [Hu, Chen, Shao & Wang, “Fama–French in China”](https://web.mit.edu/wangj/www/pap/HuChenShaoWang19.pdf) — original value/size evidence and micro-cap caveat.
- Repository designs and Backtest acceptance register — authoritative local platform constraints.

### Dropped

- Vendor/blog summaries of A-share factors — secondary commentary when original papers were available.
- Generic US/global factor papers — useful background but not direct China evidence for choosing the first family.
- Current-only data-provider documentation as proof of historical completeness — it does not establish point-in-time revisions, absence, or survivorship safety.
- SEO backtest examples using today’s constituent list or pre-adjusted price series — unsuitable for decision-useful evidence.

## Gaps and residual risks

1. No qualified historical CSI 300 constituent/revision dataset was identified in the repository materials reviewed.
2. General historical listing, ST/risk-warning, suspension, board/listing-phase, and rule-timeline completeness remains unresolved.
3. Corporate-action lifecycle completeness—including rights issues, merger/delisting treatment, and historical availability—is unresolved.
4. Broker commission/minimum and calibrated slippage are account/execution assumptions, not exchange facts.
5. H00300 historical values and their immutable source snapshot still need acquisition/qualification.
6. The proposed 2% cap and non-sector-neutral construction are simplifications and may create unintended sector exposures; they should not be described as replication of CSI 930846.
7. Without these data closures, broad results must remain development-grade or `BLOCKED`; no backtest number should be treated as promotion evidence.
