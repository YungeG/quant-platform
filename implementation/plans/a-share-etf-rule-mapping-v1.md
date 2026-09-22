# ETF-RULE-01 — XSHG three-ETF rule mapping v1

> Archive note (2026-09-22): This preserves the original design/status record, not a new implementation or execution approval. Frozen terms, status labels, hashes and reported checks below keep their original scope; no source authority, live-smoke result or holdout-consumption status was revalidated for this commit. Referenced local evidence and submodule work are not published by this document commit. Historical paths may have moved; see the [data inventory](../../overall/research-data-inventory.md). The [dependency alignment](../dependency-alignment-20260921.md) and callable ordinary-stock preparation do not establish an accepted three-ETF portfolio route. All readiness and separate authorization gates remain in force.

- **Status:** `FROZEN_MAPPING / FUTURE_REVISION_CLOSURE_OPEN`
- **Scope:** secondary-market cash trading of `510300.SH`, `511010.SH`, and `518880.SH`
- **Prospective interval:** `[2026-09-01, 2027-09-01)`
- **Evidence root:** `backtest/evidence/etf-data-01/rules/20260901-capture`
- **Evidence manifest:** `sha256:2f6c8979aa7bcbd15a6a84f38a5e11b1260159ab7c178a4c4224f79d6a6d832f`

The capture retains 18 first-party source bodies plus request URLs, response headers, receipts, and per-member hashes. It is source evidence, not decision-grade qualification or deployment authority.

## Frozen instrument mapping

| Instrument | Product class | Secondary-market resale | Exchange handling fee | Stamp duty |
| --- | --- | --- | ---: | ---: |
| `xshg:510300` | `DOMESTIC_EQUITY_ETF` | bought on T, sellable from the next trading session | `0.004%` each side | not applicable |
| `xshg:511010` | `BOND_ETF` | T+0 | waived | not applicable |
| `xshg:518880` | `GOLD_ETF` | T+0 | `0.004%` each side | not applicable |

Product identities are bound by the retained SSE product documents:

- `510300`: `sha256:c58a800bd564014e2d49826a0e9ccd965fdee8333a37f138e41442ad71dfe0ad`;
- `511010`: `sha256:29e7b43bb5441f29ca3871c68a98718051e3515cac912e0f596dc0652f5b2d68`;
- `518880`: `sha256:9780e7080a42fa7935ddae16cd69db3c8721df5f80c8537170e4eae5f1874938`.

The 2026 SSE trading rules expressly enumerate bond and gold ETFs as same-day round-trip products. Ordinary domestic equity ETFs are not in that enumeration, so `510300` remains non-sellable until the next trading session. No product is represented as ordinary `EQUITY` or generic `SPOT`.

## Shared order and session rules

For all three instruments:

- venue: `XSHG`;
- currency: CNY quote and settlement;
- trading days: frozen exchange calendar, not weekday inference;
- opening call: `09:15–09:25` Asia/Shanghai;
- opening pause: `09:25–09:30`;
- continuous trading: `09:30–11:30` and `13:00–14:57`;
- closing call: `14:57–15:00`;
- buy lot: 100 shares and integer multiples;
- quantity step: 1 share;
- an odd-lot sell residual below 100 shares must be closed in one order;
- maximum limit-order quantity: 1,000,000 shares;
- maximum market-order quantity: 1,000,000 shares;
- price tick: CNY `0.001` (`Scale(3)`, one unit);
- daily price limit: `10%` around the previous close, rounded to the price tick;
- position direction: long-only; no margin, shorting, creation/redemption, pledge/repo, or physical delivery.

Authority:

- SSE 2026 rule notice: `sha256:190b4a04fa1fb4f50f68666bcc2d444e54db8a08730b552e4c9d8ce1257bbd6b`;
- attached rule document: `sha256:fc922c433438b2636cb631eab25cca405209712acbb6aaded768c45456ff8888`;
- effective date stated by the notice: `2026-07-06`;
- the retained deferred-article list does not defer the session, lot, tick, maximum-quantity, price-limit, or T+0 clauses used here.

The existing `CnAShareCashSessionModel` phase table is byte-for-value equivalent to these session phases and may be reused only through an ETF parity fixture. Existing ordinary-stock order and quantity models remain unchanged because they reject `InstrumentType.ETF` and encode stock board classifications.

## Account availability and settlement

V1 freezes the following ledger semantics:

1. cash paid for a buy and position delivered for a sell are reserved/debited at fill;
2. sale proceeds are pending receivable until the next trading day at `16:00` Asia/Shanghai;
3. pending sale proceeds are tradable immediately but are not withdrawable or margin-eligible;
4. a bought `510300` position is not sellable while pending and becomes sellable from the next trading session;
5. bought `511010` and `518880` positions are sellable while pending, implementing T+0;
6. unsettled cash or position obligations remain explicit and cannot be treated as settled balances.

Authority:

- ChinaClear settlement rules: `sha256:637c99e28c2142296bd0b23719662d805f79617ac7e96d038a9024983928874a`;
- SSE ETF funds-availability evidence: `sha256:0d22c372fabc66ac53514fb43f81ec53fbeb8799004a8c99bcd2b990ab95934a`;
- SSE bond ETF guide: `sha256:0119edb0ef2904a2b279ba8e558704d43fb6c05bc753765cde00484a5b2dbae7`;
- SSE gold ETF directive: `sha256:4ee923a86896c49f1d613f5c2b741ed36d9c07f208f8d88299dc410909e2836b`.

Although sale proceeds are tradable on T, the strategy intentionally waits until the following eligible open. The paired zero-target/final-target protocol therefore does not depend on optimistic same-cycle funding.

## Fee and tax mapping

The retained SSE schedule sets the ETF auction handling fee to `0.004%` each side and waives it for bond ETFs. The Stamp Tax Law defines taxable securities transactions as stock and stock-based depositary-receipt transfers, so secondary-market ETF-unit trades are outside this stamp-duty scope.

- SSE fee schedule: `sha256:c3f762ca29f759c3b853f5c5310bbe6db9be344783a88edf261e7904d8090a53`;
- Stamp Tax Law: `sha256:b9c03f76774935b5bc40c46b88d69de5391128269d84cf9ee08df812de44f699`.

The frozen `8bp` one-way development scenario is an all-in simulation assumption, not a broker-price claim:

| Product | Exchange component | Account simulation component | Total |
| --- | ---: | ---: | ---: |
| `510300` / `518880` | `0.4bp` | `7.6bp` | `8bp` |
| `511010` | `0bp` | `8bp` | `8bp` |

V1 uses no minimum commission and CNY-cent half-up fee quantization. A real broker/account schedule requires a new effective-dated account authority and cannot inherit this development scenario.

## Minimum implementation delta

1. Add `InstrumentType.ETF = "etf"` without changing existing enum values or canonical bytes.
2. Reuse the existing China cash session model through a parity fixture.
3. Add ETF-specific quantity, order, settlement, and corporate-action adapters; do not widen ordinary-stock adapters.
4. Extend `commission_tax_v2` only additively so an `XSHG + InstrumentType.ETF + CnAShareFeeProductClass.ETF` scope can select per-instrument ETF rule books. Existing `XSHE + EQUITY` acceptance and failures remain unchanged.
5. Keep the generic target stream, allocation, risk, sizing, ledger, settlement book, rebalance planner, and Engine unchanged.

Per-instrument fee authorities are required because `511010` is fee-waived while `510300` and `518880` are not. Per-position availability rules are required because only `511010` and `518880` are T+0.

## Still-open closure

This mapping resolves the product/session/order/settlement/fee/tax design choices, but it does not authorize implementation yet. The remaining blockers are:

- accepted ETF `fund_daily` numeric mapping;
- retained daily listing/trading-status coverage;
- fund distribution, unit-change, merger, suspension, and termination lifecycle closure;
- append-only capture of rule revisions after `2026-09-01`; current evidence cannot prove no future rule change through `2027-09-01`;
- approved portfolio-authority schema and fixture.

Unknown or superseded rule revisions fail closed. No current source value may be projected across the full prospective interval without revision monitoring and final closure.
