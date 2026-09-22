# Research: quantitative strategy ideas for liquid Binance USD-M crypto markets

> Archive note (2026-09-22): This file and its companion BTCUSDT plan/data inventory were recovered from `platform-strategy-ideas/research/`. Original bytes are retained in the directory-organization backup. Historical capability, data, and approval statements were not revalidated by this move; this is not a new experiment authorization.

## Summary

The best first strategy family is a deliberately small **daily time-series momentum test on BTCUSDT**, using only completed Binance USD-M bars, next-bar execution, explicit funding, and conservative taker-cost stresses. It has direct original-paper support, minimal strategy complexity, and the closest fit to the repository's Research → Backtest → Validation flow. However, the repository does not yet contain a continuous, causally available provider dataset sufficient to run that experiment honestly; the immediate next step is a bounded data-authority experiment, not a performance backtest.

Five falsifiable families are shortlisted below. Funding carry has strong mechanism-specific evidence but ranks lower for the current platform because credible implementation needs synchronized spot and perpetual legs, borrowing/capital treatment, leg-risk controls, and historical funding availability authority that the repository explicitly does not have.

## Scope and repository constraints

### Verified local facts

- The repository declares `platform/` as the independent implementation root and says the sibling pilot is historical evidence only, not callable or authoritative for Backtest economics ([`README.md`](../README.md)).
- The accepted flow is Research Platform (optionally model-bound) → Backtest public evidence/analysis → Strategy Validation → Promotion Gate, with outcomes no stronger than `rejected | needs_more_evidence | shadow_ready`; Shadow/Live/deployment remain excluded ([`README.md`](../README.md)).
- Decision-grade evidence is described as flowing through exact Admission, Research, Validation, and Promotion seams rather than through a side simulator ([`README.md`](../README.md)).

### Verified platform capabilities and authority limits

- The worktree's Git submodules were initialized before final review. The Backtest acceptance matrix records `PASSED` development-grade contracts for one-way linear-perpetual long/short positions, realized P&L, funding eligibility/accounting, margin projection, conservative liquidation audit, generic linear-perpetual composition, Binance USD-M profile composition, and layered parity (`G09A`–`G10H`) ([Backtest acceptance matrix](../backtest/docs/implementation/acceptance-matrix.md)).
- The Binance development profile supports a single USDT account/instrument journey with one-way cross mode, open/reduce/flip, fees, funding, margin and liquidation-audit evidence, but remains `decision_grade_eligible=false` and explicitly does not prove archive completeness, matching-engine parity, real liquidation, live operation, or deployment ([G10G/G10H](../backtest/docs/implementation/acceptance-matrix.md)).
- Strategy runtime has point-in-time named Bar windows and deterministic portfolio-strategy invocation seams; Strategy callbacks cannot read ambient provider/account/runtime state, and all G11 outputs remain development-only until G12 qualification ([G11D](../backtest/docs/research/g11d-named-bar-window.md), [G11I](../backtest/docs/research/g11i-portfolio-strategy-invocation.md)).
- Accepted provider slices are narrow and non-composable as a research history: BTCUSDT mark-price klines for one UTC day in 2024, aggregate trades for one UTC day in 2020, and rate-only funding rows for January 2020. The mark/trade rows use later acquisition availability and cannot establish historical intraday replay; the funding archive lacks funding marks; strict Funding History remains blocked ([G12L provider cards](../backtest/docs/implementation/acceptance-matrix.md)).
- The funding authority decision is `H3 — NO_CAUSAL_AUTHORITY`: retained 2024 Funding History rows are post-hoc only because exact first availability and complete revision lineage cannot be established. No prospective plan may backdate those rows ([funding authority decision](../backtest/docs/research/g12m-binance-funding-availability-authority-decision-v1.md)).
- No reviewed accepted slice supplies continuous BTCUSDT last-price daily bars, equivalent ETHUSDT history, a point-in-time multi-contract universe, premium/index histories, or synchronized spot/perpetual execution evidence. Consequently every strategy below is a research candidate, not a currently qualified run.

### Deliberate non-overlap

This shortlist excludes A-share low-volatility/value/momentum baselines covered in `/home/ygguo/agent-projs/ai-crypt/platform/research/a-share-strategy-baseline.md` and excludes KORUUSDT/equity-index factor research covered in `/home/ygguo/agent-projs/ai-crypt/platform-koru-research/research/koruusdt-factor-map.md`.

## Source-backed market/data facts

1. Binance USD-M exposes contract klines (`/fapi/v1/klines`), index-price klines (`/fapi/v1/indexPriceKlines`), premium-index klines (`/fapi/v1/premiumIndexKlines`), realized funding history (`/fapi/v1/fundingRate`), current/adjusted funding metadata (`/fapi/v1/fundingInfo`), and current symbol/rule metadata (`/fapi/v1/exchangeInfo`). Klines are identified by open time; funding history accepts bounded timestamps and returns the associated mark price. These endpoints establish schemas, not historical completeness. [Binance kline docs](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Kline-Candlestick-Data) [funding history](https://developers.binance.com/legacy-docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History) [premium-index klines](https://developers.binance.com/legacy-docs/derivatives/usds-margined-futures/market-data/rest-api/Premium-Index-Kline-Data) [index-price klines](https://developers.binance.com/legacy-docs/derivatives/usds-margined-futures/market-data/rest-api/Index-Price-Kline-Candlestick-Data) [exchange information](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Exchange-Information)
2. Binance states that futures trading fees depend on maker/taker status and account tier and may change; a research run must bind an explicit fee schedule or stress assumption rather than assert a universal fee. [Binance futures fee explanation](https://www.binance.info/en/support/faq/detail/360033544231)
3. Original research reports cryptocurrency time-series momentum at daily and weekly frequencies, while later work warns that realistic transaction costs, liquidation risk, and daily price paths can remove apparent profitability. [Liu & Tsyvinski, NBER 24877](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf) [Han, Kang & Ryu](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4675565)
4. Original cross-sectional research finds one- through four-week momentum in a broad cryptocurrency universe, but its sample includes many assets unlike a liquid Binance-perpetual universe; recent realistic-assumption evidence describes cross-sectional momentum as weaker than time-series momentum. [Liu, Tsyvinski & Wu, NBER 25882](https://www.nber.org/system/files/working_papers/w25882/w25882.pdf) [Han, Kang & Ryu](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4675565)
5. Perpetual-futures research derives no-arbitrage bounds, documents economically meaningful futures/spot deviations, and emphasizes that perpetuals have no fixed expiry forcing convergence; funding/basis trades are therefore not risk-free. [He, Manela, Ross & von Wachter](https://arxiv.org/html/2212.06888v5) [Schmeling, Schrimpf & Todorov, BIS Working Paper 1087](https://www.bis.org/publ/work1087.pdf)
6. Intraday Bitcoin research finds negative return autocorrelation and stronger reversal after larger moves at one-, two-, and four-hour horizons, but its simple trading exercise omitted fees; this makes execution-cost falsification central. [Balduzzi et al., “On the Intraday Behavior of Bitcoin”](https://ledger.pitt.edu/ojs/ledger/article/download/213/212)

## Ranked shortlist

Scores are ordinal, 1 (weak/high burden) to 5 (strong/low burden). “Robustness” is an ex-ante judgment about likely resistance to reasonable specification changes, **not** an expected return claim.

| Rank | Family | Evidence quality | Data availability | Implementation ease | Expected robustness | Principal reason |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | Daily time-series momentum | 4 | 2 | 4 | 4 | Best evidence/complexity tradeoff; blocked mainly by continuous causal data authority |
| 2 | Delta-neutral funding carry | 5 | 1 | 1 | 4 | Strong mechanism, but spot leg, financing, leg risk and causal funding history are missing |
| 3 | Liquid-universe cross-sectional momentum | 4 | 1 | 2 | 3 | Direct evidence, but point-in-time universe, survivorship and portfolio turnover create the widest data seam |
| 4 | Premium/index dislocation mean reversion | 4 | 1 | 3 | 3 | Perpetual-specific mechanism, but no accepted premium/index history is currently present |
| 5 | Extreme-move intraday reversal | 3 | 2 | 3 | 2 | Simple and falsifiable, but highly cost-sensitive and existing intraday evidence is only one bounded day |

## 1. Daily time-series momentum on BTCUSDT and ETHUSDT

**Hypothesis.** A liquid crypto perpetual's trailing return sign contains incremental information about its next holding-period return after fees and funding. This is a proposed Binance USD-M replication of a published crypto effect, not a claim that the historical paper's magnitude transfers to this venue or era. [Liu & Tsyvinski](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf)

**Exact proposed signal and cadence.** At 00:00 UTC after daily bar `t` is complete, compute `m_t = log(close_t / close_{t-7})`. For each of BTCUSDT and ETHUSDT independently, target `+0.5` portfolio gross notional if `m_t > 0`, `-0.5` if `m_t < 0`, and zero if unavailable. Rebalance daily at the first executable event strictly after the signal timestamp; hold until the next rebalance. No volatility scaling or parameter search in experiment 1.

**Minimum data.** Point-in-time symbol metadata; 1-day USD-M last-price klines; realized funding cash flows/timestamps; executable price or conservative next-bar proxy; fee schedule/assumption. Mark-price klines are required for margin/liquidation diagnostics even if last-price bars drive the signal.

**Availability/causality traps.** Never use an incomplete daily bar; use only funding records published at or before each decision; do not infer past tick/quantity filters from current `/exchangeInfo`; do not fill before the decision; treat listing gaps and missing bars explicitly. UTC day boundaries are a proposed convention, not an economically privileged close.

**Execution/cost needs.** Linear-contract P&L, both-side commissions, funding transfers, quantity/tick rounding, margin and liquidation semantics, and next-event execution. Base case should use an explicitly declared taker fee plus 2 bps/side slippage; stresses: 0/2/5/10 bps slippage and doubled declared fees. These are proposed assumptions, not sourced Binance account rates.

**Validation/holdout.** Freeze one 7-day lookback. Use earliest qualified history through 2021-12-31 for development, 2022-01-01 through 2023-12-31 for pre-holdout diagnostics, and 2024-01-01 onward as untouched holdout, shifting boundaries once only for source coverage before inspecting results. Also report rolling calendar-year results and BTC/ETH separately.

**Falsification.** Reject if holdout net return is non-positive; if the combined result is positive but either symbol contributes over 80% of total P&L; if 5 bps/side makes net return non-positive; if a one-day execution delay flips the sign; or if maximum drawdown exceeds buy-and-hold BTCUSDT while net return does not. Mark inconclusive if required funding or execution evidence is incomplete.

**Repository fit/gaps.** This is the closest fit. G09A–G10G already cover one-way long/short positions, funding accounting, margin, conservative liquidation audit, next-eligible-open execution and Binance USD-M development composition; G11D/G11I provide point-in-time Bar windows and Strategy invocation. The blocker is provider authority: current accepted G12L slices do not supply continuous causally available daily last-price/mark/funding history, and no equivalent ETHUSDT slice is accepted ([acceptance matrix](../backtest/docs/implementation/acceptance-matrix.md), [G11D](../backtest/docs/research/g11d-named-bar-window.md)).

## 2. Delta-neutral spot/perpetual funding carry

**Hypothesis.** When a liquid USD-M perpetual trades sufficiently rich and realized/observable funding compensates shorts, long spot plus short equal-delta perpetual can earn net carry after fees, financing, leg risk, and adverse funding changes. Research documents crypto carry and perpetual deviations but explicitly rejects a risk-free interpretation. [He et al.](https://arxiv.org/html/2212.06888v5) [BIS Working Paper 1087](https://www.bis.org/publ/work1087.pdf)

**Exact proposed signal and cadence.** For BTC and ETH only, observe once hourly. Define `premium_t = perp_index_close_t / index_price_close_t - 1` from completed premium/index data and `f_t` as the last realized regular funding rate. Open equal-USDT long spot/short perpetual only when `premium_t > 10 bps`, `f_t > 0`, and the sum of the prior three realized funding rates is positive. Close when premium is `<= 0`, last funding is `<= 0`, or after seven days. The 10 bps/three-event/seven-day values are proposed fixed precommitments, not optimized thresholds.

**Minimum data.** Synchronized Binance spot and USD-M trades/klines; premium- and index-price klines; realized funding; spot and futures fees; symbol filters; funding interval/cap changes; financing/opportunity-cost assumption; both-leg fills and balances.

**Availability/causality traps.** A future funding estimate must not be substituted for a realized historical rate unless its point-in-time publication history is captured. Funding can change before settlement; spot and perpetual legs are not atomic; the index is not an executable spot price; current filters and funding caps do not prove historical values.

**Execution/cost needs.** A synchronized two-leg engine, legging slippage, spot custody/capital, perpetual margin, funding settlement eligibility, rebalancing as deltas drift, and failure handling if one venue/leg is unavailable. Stress one-leg delays of 1/5/30 seconds or the finest supported conservative proxy.

**Validation/holdout.** Use contiguous time splits and event-level attribution: gross basis convergence, funding, commissions, slippage, financing, and residual delta P&L. Reserve the latest 30% of funding events as holdout; embargo seven days between selection and holdout because positions can overlap.

**Falsification.** Reject if net holdout P&L is non-positive under taker fees plus 5 bps/leg; if over half of profits come from the largest five events; if the worst legged fill loses more than one year's median carry; if residual beta to spot is economically material; or if results require future funding estimates.

**Repository fit/gaps.** Funding settlement/accounting is implemented development-grade for one-way linear perpetuals, but the accepted profile is a single USDT derivative account/instrument and the reviewed platform does not establish synchronized spot+perp execution, spot custody/financing, or atomic two-leg accounting. Historical funding availability is additionally blocked by the H3 decision. Do not implement this in a side simulator merely because the economics are inconvenient.

## 3. Liquid-universe cross-sectional momentum

**Hypothesis.** Among point-in-time liquid, seasoned Binance USD-M perpetuals, recent winners outperform recent losers over the following week after funding and costs. Broad-market original evidence supports one- through four-week momentum, but later realistic work weakens confidence and motivates a liquid-only falsification. [Liu, Tsyvinski & Wu](https://www.nber.org/system/files/working_papers/w25882/w25882.pdf) [Han, Kang & Ryu](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4675565)

**Exact proposed signal and cadence.** Every Monday 00:00 UTC, form the eligible universe from contracts listed at least 180 days with complete prior 28-day daily bars. Rank by prior 21-day log return excluding the most recent 24 hours. Liquidity screen: top 20 by trailing 28-day median daily quote volume, computed only from completed data. Equal-weight long top quartile and short bottom quartile, total gross 1.0 and net zero; hold one week.

**Minimum data.** Point-in-time listing/delisting and symbol metadata; daily USD-M prices and quote volume; funding; fees; executable bars; missing/delist settlement treatment.

**Availability/causality traps.** Today's symbol list creates survivorship bias; trailing volume must be known before ranking; contracts near listing lack comparable histories; delisted losers must remain in results; symbol migrations and contract-type changes cannot be silently joined; the academic coin universe is not the same as Binance perpetuals.

**Execution/cost needs.** Portfolio-level leverage/netting, simultaneous rebalance semantics, short support, contract filters, funding by leg, turnover, concentration limits, and delisting/forced-close rules. Stress 5/10/20 bps per side because weekly cross-sectional turnover can be high.

**Validation/holdout.** Freeze universe and ranking rules before holdout. Use expanding yearly walk-forward diagnostics; final 30% of weeks is untouched holdout with a four-week embargo. Compare against equal-weight eligible-universe and market-neutral random-rank placebo distributions.

**Falsification.** Reject if net holdout long-short return is non-positive at 10 bps/side; if either long-only or short-only contribution explains over 90%; if excluding the least-liquid half flips the sign; if turnover exceeds 400% one-way annualized; or if missing/delisted names are result-relevant.

**Repository fit/gaps.** Portfolio Strategy invocation exists, but the accepted Binance development journey is single-account/single-instrument and G12 does not provide a point-in-time multi-contract listing/delisting universe or complete funding history. Dynamic universe authority, delisting treatment and simultaneous portfolio execution therefore remain material blockers.

## 4. Premium/index dislocation mean reversion

**Hypothesis.** Large deviations of perpetual price from its index/no-arbitrage region tend to contract, and the contraction remains exploitable after costs. The mechanism is directly tied to perpetual design, but no expiry guarantees convergence. [He et al.](https://arxiv.org/html/2212.06888v5)

**Exact proposed signal and cadence.** BTCUSDT and ETHUSDT, hourly. From completed premium-index bars, compute the rolling 30-day median and median absolute deviation (MAD) of hourly premium closes. Enter short perpetual when robust z-score `> +3`; enter long when `< -3`. Exit at z-score crossing zero or after 24 hours. Size each position to 25% gross notional; no averaging down. This first screen is unhedged and therefore tests predictive mean reversion, not arbitrage.

**Minimum data.** Hourly premium-index, index-price, last-price and mark-price klines; realized funding; symbol/funding-rule changes; fills, fees, margin/liquidation evidence.

**Availability/causality traps.** The completed premium bar is only available after its close; premium-index values are not executable; funding formulas/caps/intervals can change; a rolling standardization must use past data only; missing stress episodes must not be dropped.

**Execution/cost needs.** Next-hour-open or finer conservative execution, taker fees, 2/5/10 bps slippage, funding, mark-based margin, and gap/liquidation checks. A later hedged variant would become a separate candidate requiring spot support.

**Validation/holdout.** Event-based split with a 24-hour embargo; reserve latest 30% of events. Report by sign, symbol, year, volatility quartile, and distance from funding timestamp. Threshold robustness (`|z|` 2.5/3/4) is development-only; freeze one before holdout.

**Falsification.** Reject if net holdout return is non-positive at 5 bps/side; fewer than 100 independent entries occur; one event supplies over 25% of P&L; adverse excursion creates liquidation at 2x leverage; or sign/exit results are not stable across BTC and ETH.

**Repository fit/gaps.** Mark-based margin/liquidation semantics are implemented development-grade, but no accepted G12 provider slice supplies continuous premium-index and index-price histories. The strategy must not treat index/premium observations as fill prices, and current endpoint schemas cannot substitute for historical source authority.

## 5. Extreme-move intraday reversal

**Hypothesis.** Large one-hour BTCUSDT/ETHUSDT moves partially reverse over the next one to four hours after fees. Published Bitcoin evidence finds negative autocorrelation at one-, two-, and four-hour frequencies and stronger reversals after larger moves, while acknowledging omitted trading fees in its simple strategy. [Balduzzi et al.](https://ledger.pitt.edu/ojs/ledger/article/download/213/212)

**Exact proposed signal and cadence.** On each completed hourly bar, compute return and trailing 30-day hourly realized standard deviation. If the last return exceeds `+3σ`, short 25% gross at the next executable event; if below `-3σ`, long 25%; close exactly two hours later. One position per symbol; skip signals while already positioned.

**Minimum data.** Hourly last and mark-price bars, funding, fees, symbol filters, conservative fills; trades/order book are optional diagnostics, not minimum inputs.

**Availability/causality traps.** Volatility must exclude the signal bar when setting its threshold or explicitly include it consistently; entry cannot occur at the extreme bar's close unless that executable quote is recorded; overlapping events reduce independence; liquidation cascades are a proposed explanation, not observable causality from bars alone.

**Execution/cost needs.** High priority on spread/slippage and gap modeling. Run taker-only costs with 2/5/10/20 bps per side, delayed entry by one 1-hour bar, mark-price liquidation at 2x leverage, and no same-bar fills.

**Validation/holdout.** Chronological 60/20/20 split with a two-hour embargo; freeze `3σ` and two-hour hold. Block-bootstrap events by day and report positive/negative shocks separately.

**Falsification.** Reject if net holdout return is non-positive at 5 bps/side; either shock direction is materially negative; delayed entry removes the effect; fewer than 200 holdout events occur; or profit is confined to one volatility episode.

**Repository fit/gaps.** Existing economic accounting and conservative next-open execution are nearby, and one bounded BTCUSDT aggregate-trade day is accepted. That single 2020 day is insufficient for inference and is not aligned with the accepted 2024 mark-price day or 2020 monthly funding slice. Continuous causal intraday history and cost calibration must be added before a strategy result is meaningful.

## Smallest credible next experiment

The repository cannot yet run a credible strategy backtest from its accepted provider slices. The smallest honest next experiment is therefore a **BTCUSDT daily time-series-momentum data-authority slice**, followed by one frozen development run only after the slice closes.

### Phase A — data-authority acceptance

- **Scope:** BTCUSDT only; one explicit contiguous historical interval chosen before inspecting strategy returns. ETHUSDT is a later additive replication, not part of the first slice.
- **Required streams:** completed daily execution-reference/last-price bars, daily or finer mark-price data for valuation/margin/liquidation, every realized funding publication and funding mark needed by the run, and point-in-time instrument/order/margin/fee metadata covering the same interval.
- **Authority:** immutable source bytes and revision identity, causal `available_time`, gap/terminal coverage, exact source-row traces, and explicit blocked intervals. Current endpoint responses or late archive acquisition must not be relabeled as historically available.
- **Acceptance:** the assembled bundle must pass G12 validation/publication and expose the exact capabilities required by the Binance development profile. If funding first-availability/revision closure cannot be established, the run remains blocked rather than silently dropping funding.

### Phase B — frozen strategy run after Phase A

- **Candidate:** BTCUSDT daily time-series momentum, strategy 1 only.
- **Signal:** sign of trailing 7 completed daily-bar log return at 00:00 UTC; no parameter search.
- **Portfolio:** target `+1`, `-1`, or `0` gross direction in the single admitted contract; no volatility targeting or leverage optimization.
- **Execution:** first supported executable event strictly after the completed signal bar; no same-bar fill; stress a one-full-day delay.
- **Costs:** source-bound fee authority where available; otherwise visibly labeled fee assumptions. Slippage stresses 0/2/5/10 bps per side; include every authoritative realized funding cash flow.
- **Split:** define development/pre-holdout/untouched-holdout boundaries from qualified data coverage before viewing outcomes; preserve the latest approximately 30% as untouched holdout with no overlap.
- **Decision rule:** `supported` only if holdout net return is positive, remains positive at 5 bps/side, survives a one-day delay without a sign flip, and has zero liquidations under the frozen account profile. Otherwise `rejected`; incomplete funding/execution/metadata authority yields `inconclusive`/`BLOCKED`.
- **No promotion inference:** passing this development screen would justify an ETH replication and broader robustness candidate, not `shadow_ready`, live eligibility, or a trading recommendation.

## Data/platform blockers

1. **High — continuous causal market data:** accepted slices are isolated BTCUSDT day/month fixtures, not a contiguous strategy history; there is no accepted ETHUSDT history.
2. **High — historical metadata authority:** current `/exchangeInfo` does not establish historical listing status, filters, contract revisions, margin tiers, fee bands, or authoritative absence across a research window.
3. **High — funding availability/finality:** funding accounting exists, but the H3 decision rejects causal authority for retained 2024 Funding History rows and the accepted monthly archive is rate-only without funding marks.
4. **High — execution evidence:** the development profile intentionally uses conservative bar-open/full-fill/zero-latency conventions and does not claim matching-engine, queue, partial-fill or real-liquidation parity.
5. **High for funding carry — multi-leg support:** synchronized spot/perpetual execution, spot custody/financing, capital allocation and leg-risk handling are outside the accepted single-derivative journey.
6. **High for cross-sectional momentum — dynamic universe:** point-in-time contract listing/delisting, survivorship-safe membership and simultaneous multi-instrument execution are not qualified.
7. **Medium — premium/index histories:** endpoint schemas exist, but no accepted continuous premium/index provider slice was found.
8. **Medium — fee/slippage calibration:** account-specific fees and realized market impact are unknown; assumptions must remain visibly separate from sourced facts.

## Sources

### Kept

- [Liu & Tsyvinski, “Risks and Returns of Cryptocurrency”](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf) — original direct time-series momentum evidence.
- [Liu, Tsyvinski & Wu, “Common Risk Factors in Cryptocurrency”](https://www.nber.org/system/files/working_papers/w25882/w25882.pdf) — original cross-sectional factor definitions and horizons.
- [Han, Kang & Ryu, realistic momentum assessment](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4675565) — direct caution on costs, liquidation, and cross-sectional weakness.
- [He, Manela, Ross & von Wachter, “Fundamentals of Perpetual Futures”](https://arxiv.org/html/2212.06888v5) — original mechanism-specific theory and empirical bounds.
- [Schmeling, Schrimpf & Todorov, “Crypto Carry”](https://www.bis.org/publ/work1087.pdf) — primary empirical carry/frictions evidence.
- [Balduzzi et al., “On the Intraday Behavior of Bitcoin”](https://ledger.pitt.edu/ojs/ledger/article/download/213/212) — original intraday reversal evidence with explicit cost limitation.
- Binance USD-M API and fee documentation linked above — first-party endpoint schemas and mutable fee/rule warnings.
- [`README.md`](../README.md) — local integration and promotion boundary.
- [Backtest acceptance matrix](../backtest/docs/implementation/acceptance-matrix.md) — accepted development capabilities and exact G12 provider limitations.
- [Research Platform design](../research-platform/design.md) and [Strategy Validation design](../strategy-validation/design.md) — Experiment ownership, public Backtest seam and untouched-holdout semantics.
- [G11D named Bar windows](../backtest/docs/research/g11d-named-bar-window.md) and [G11I Portfolio Strategy invocation](../backtest/docs/research/g11i-portfolio-strategy-invocation.md) — Strategy-facing point-in-time data and deterministic invocation boundaries.
- [Funding availability authority decision](../backtest/docs/research/g12m-binance-funding-availability-authority-decision-v1.md) — authoritative H3 blocker for retained historical Funding History rows.

### Dropped

- Blog/vendor strategy summaries — secondary and often omit survivorship, funding, or execution assumptions.
- Open-interest predictors — not shortlisted because retrieved primary work questions reported open-interest consistency and did not provide a sufficiently direct robust return hypothesis for this scope.
- Low-volatility crypto — dropped because primary findings conflict materially across specifications and it risks duplicating the separate low-volatility research lane conceptually.
- Attention/social signals — dropped because they add provider/revision/availability problems without improving the smallest platform-adjacent experiment.
- KORUUSDT and A-share factors — excluded to respect existing worktree lanes.

## Residual uncertainties

- No empirical Binance dataset was downloaded or backtested; rankings are research-priority judgments, not performance results.
- The evidence samples often predate the latest market structure and may not survive on a liquid Binance-only holdout.
- Development-grade shorting, funding, margin and conservative liquidation-audit support is verified; decision-grade provider completeness, real matching/liquidation parity, spot legs, dynamic universes and broad multi-asset histories remain unsupported or unqualified.
- Binance endpoint documentation does not prove retention, completeness, or immutability of every historical field.
