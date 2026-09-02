# KORUUSDT Directional Discovery Plan v1

## Status

**PLAN-ONLY.** The prior formal closed-market range-fade Experiment completed with `NO_ELIGIBLE_TRIAL`. This document pre-registers four independent replacement hypotheses. It authorizes no Backtest, Holdout read, network access, Shadow, Live, Promotion, or deployment.

## Fixed scope

- Market: Binance USD-M `KORUUSDT` `TRADIFI_PERPETUAL`, USDT settled, development grade only.
- Discovery: `[2026-07-15T10:00:00Z, 2026-08-24T11:00:00Z)`.
- Future Holdout: `[2026-08-24T11:00:00Z, 2026-10-05T00:00:00Z)`; untouched and unavailable to all four designs.
- Execution: completed causal observations only; target changes fill at the first retained aggregate trade on the next eligible hourly boundary.
- Economics: Backtest exclusively owns fills, fees, funding, margin, liquidation, PnL, result grade, and analysis.

## Independent hypotheses

### 1. Closed-market range breakout

**Hypothesis:** a completed closed-market range break continues after next-boundary execution.

- Build the range from the preceding 6 or 12 eligible completed 1h Mark bars while both XKRX and ARCX are closed.
- Long above `high × (1 + buffer)`; short below `low × (1 - buffer)`.
- Exit on return into range, adverse Mark stop, four eligible hours, pre-funding, or before either cash market opens.
- Fixed rows: `formation_hours ∈ {6,12}`, `buffer_bps ∈ {0,10}`, `stop_bps ∈ {50,100}`.

### 2. Mark/Index premium mean reversion

**Hypothesis:** extreme completed `10,000 × (Mark / Index - 1)` premiums revert after costs.

- Short at positive extreme; long at negative extreme.
- Exit on zero/crossing compression, 5 bps compression, 12 completed hours, or opposite signal.
- Fixed rows: `entry_bps ∈ {20,30,40,60}`; `exit_bps = 5`; `max_hold_hours = 12`.

### 3. Funding carry

**Hypothesis:** an extreme final funding rate persists into subsequent settled slots strongly enough to overcome price movement and costs.

- Decide only after immutable funding publication availability.
- Short after positive extreme funding; long after negative extreme funding.
- Enter/exit only through next-boundary aggTrade execution; retain one or two settled slots.
- Fixed rows: `absolute_rate_threshold ∈ {5,10}` bps × `leverage ∈ {1x,2x}` × `retained_slots ∈ {1,2}`.

**Restriction:** current 120 funding rows are sufficient only for feasibility evidence, not selection. This direction is deferred.

### 4. Cash-session-open momentum

**Hypothesis:** a large signed KORU Mark move during the first completed hourly bar overlapping an XKRX or ARCX opening continues briefly after next-boundary execution.

- Use accepted calendar open instant only when available by the decision bar close.
- Enter in the completed bar return direction; exit after 2 or 4 hours, or after a 3% adverse completed-Mark move.
- Never overlap positions across cash-session opening events.
- Fixed rows: calendar `{XKRX, ARCX}` × threshold `{0.50%, 1.00%}` × hold `{2h,4h}`.

## Global anti-data-snooping protocol

1. Each direction receives an independent Experiment identity.
2. Before any run, predeclare a global maximum of **12 completed discovery trials** across the slate. Blocked/incomplete work does not authorize new parameter rows.
3. Conditional launch slate: Premium rows `{20,30,40,60}` bps (4); Opening rows `{XKRX,ARCX} × 0.50% × {2h,4h}` (4); Breakout rows `{(6h,0bp,50bp),(6h,0bp,100bp),(12h,10bp,50bp),(12h,10bp,100bp)}` (4). Funding is deferred.
4. Family eligibility gates apply first. At most one global candidate may be selected by normalized net PnL after all costs, then lower maximum drawdown, then slate order and canonical row order.
5. The future Holdout remains unread until exactly one global candidate exists. It can be used once only.

## Current execution blocker

The public premium-only compiler, V3 bundle/preparation route, and deferred Backtest operations now exist. Breakout/opening remain calendar-fail-closed; funding remains unsupported.

The four premium trials are still **not executable** against retained KORU discovery evidence because:

1. `crypto_quant_bundle_builder` does not publicly expose the V2 source-projection constructor needed to reconstruct the retained source authority;
2. no four premium recipe/parameter artifacts or published premium target authorities have been pre-registered; and
3. no complete, immutable V2 execution/economics authority has been published for the V3 hybrid bundle.

The eight retained closed-market-range targets are not substitutes. No private composition, callback, custom simulator, Experiment, or Holdout read is authorized while these inputs are absent.

## Required next artifact

Publish a public Builder-owned retained-source/economics authority seam, then pre-register and publish the four fixed premium recipe authorities and their V3 bundle readers. Only after those exact inputs pass the public preflight may the four-trial premium Experiment execute.
