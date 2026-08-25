# BT-TRADIFI-DISPATCH-01 production derivative-dispatch amendment

- **Status:** APPROVED — implementation authorized by the Platform owner
- **Amends:** `tradifi-perpetual-capability-contract.md` and `tradifi-perpetual-capability-amendment-01.md`
- **Public preparation signature:** unchanged
- **Existing accepted Backtest work retained:** through Backtest commit `88573f1`

## 1. Discovered runtime blocker

The accepted TradFi profile publishes financial dispatcher identity:

```text
crypto.binance_usdm.tradifi.linear-financial-dispatch.v1
```

but production execution currently exposes only the cash dispatcher. The default runner and fresh durable-rebuild path instantiate the cash-dispatching Engine. A correctly prepared TradFi derivative Case would therefore fail its dispatcher-spec identity check before execution.

Preparation cannot work around this by injecting a private dispatcher, trusting a test helper, using a second simulator, or downgrading the derivative plan to cash accounting.

## 2. Authorized additive runtime capability

Add one production dispatcher for the exact accepted TradFi `FinancialDispatcherSpec`, reusing existing production domain plans and models:

- `LinearDerivativeFillAccountingPlan`;
- `FeeAccountingDispatchPlan`;
- `LinearFundingAccountEventPlan`;
- `LinearMarginLiquidationAuditPlan`;
- accepted final valuation/snapshot projection.

The dispatcher owns no strategy calculation and no source acquisition. It executes only plans already sealed in a resolved Case.

## 3. Exact dispatcher selection

Dispatcher selection is additive and fail-closed:

1. existing ordinary/cash specs continue selecting the existing cash dispatcher;
2. the complete accepted TradFi dispatcher spec selects the new derivative dispatcher;
3. selection verifies the complete `FinancialDispatcherSpec`, component refs, model key/version/digest, and profile identity;
4. no loose key-only match, alias, fallback, retry, caller-supplied dispatcher, or cash downgrade;
5. unknown, forged, mixed, or unsupported specs fail before execution.

Apply the same exact selection in:

- normal runner/facade execution;
- execution-input schema 6 hydration;
- fresh durable rebuild/replay.

## 4. Durable profile wire codec clarification

The final bundle contains a canonical TradFi profile-composition-request wire. Preparation must add an exact production decoder:

```python
decode_binance_usdm_tradifi_profile_composition_request_v1(
    wire: Mapping[str, object],
    expected_hash: str,
) -> BinanceUsdmTradifiProfileCompositionRequest
```

It reconstructs every nested public Binance resolution through real constructors, re-encodes to identical canonical bytes, and matches the authority hash. An in-memory Python object, pickle, test fixture import, partial mapping, or unchecked nested hash is forbidden.

## 5. Multi-order derivative Case planner clarification

Preparation may add one production planner for the selected immutable target stream:

- multiple decision cycles and entry/exit admissions;
- exact 10,000 USDT initial equity and full sleeve allocation;
- exact 0.1 target exposure, yielding 1,000 USDT decision-time target notional;
- causal quantity rounding from the completed decision mark;
- later fill-notional drift retained as evidence;
- `ResolvedBarExecution(fill_liquidity_role="taker")`;
- derivative fill/fee/funding/margin/liquidation/snapshot plans;
- no shadow PnL or duplicate simulator.

It must use existing allocation, risk, sizing, order, accounting, Engine, execution-input v6, publication, and rebuild paths.

## 6. Revised write set

Authorized additive edits/modules include:

- `packages/backtest-runtime/src/crypto_quant_backtest/financial_dispatch.py`;
- exact dispatcher selector used by `runner.py` and `facade.py`;
- `_durable_rebuild.py` exact selector reuse;
- `binance_usdm_tradifi_profile_wire.py`;
- TradFi public preparation/case-planner module;
- focused dispatcher, codec, execution, durable-rebuild, mutation, and compatibility tests.

No `Fill`, accounting-domain schema, MarketBundle schema, Research, Validation, Foundation, Promotion, or Platform contract change is authorized.

## 7. Compatibility

- existing cash dispatcher class/spec/behavior/bytes unchanged;
- existing ordinary Binance profile and component hashes unchanged;
- execution-input schemas 1–5 unchanged;
- schema 6 role bytes remain additive;
- no current API/network/system-clock economics during preparation or execution;
- no Shadow, Live, credentials, orders, deployment, or capital authority.

## 8. Acceptance

1. A sealed TradFi derivative Case selects the new production dispatcher and completes fill, taker fee, funding, margin/liquidation audit, closeout, and snapshot accounting.
2. The same Case fails with the cash dispatcher or any forged/mixed dispatcher spec.
3. Existing cash and ordinary recursive suites retain exact hashes/results.
4. Execution-input v6 round-trip and fresh rebuild select the same derivative dispatcher and reproduce result/proof hashes.
5. Canonical profile wire decodes byte-for-byte; nested mutation fails.
6. Multi-order entry/exit streams execute exactly once per planned event with no private simulator.
7. Full Backtest and recursive Platform compatibility gates remain green.

## 9. Revised dependency

```text
BT-TRADIFI-DISPATCH-01 approval
  ├─→ exact profile-wire codec
  ├─→ production derivative dispatcher + exact selector
  └─→ multi-order public preparation planner
          └─→ full fan-in and retained bundle publication
```
