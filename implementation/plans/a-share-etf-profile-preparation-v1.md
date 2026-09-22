# ETF-PREP-01 — China ETF profile and portfolio preparation v1

> Archive note (2026-09-22): This preserves the original design/status record, not a new implementation or execution approval. Frozen terms, status labels, hashes and reported checks below keep their original scope; no source authority, live-smoke result or holdout-consumption status was revalidated for this commit. Referenced local evidence and submodule work are not published by this document commit. Historical paths may have moved; see the [data inventory](../../overall/research-data-inventory.md). The [dependency alignment](../dependency-alignment-20260921.md) and callable ordinary-stock preparation do not establish an accepted three-ETF portfolio route. All readiness and separate authorization gates remain in force.

Status: **DEFERRED / NOT REQUIRED FOR CURRENT HISTORICAL BACKTEST**

## Outcome

Deferred objective: expose one deep public Backtest preparation operation for a retained three-ETF secondary-market portfolio:

```python
prepare_cn_etf_portfolio_development_backtest(
    *,
    request_intent: CashDevelopmentRequestIntent,
    provider_inputs: CnEtfPortfolioDevelopmentProviderInputs,
    target_stream_ref: BacktestTargetStreamRef,
    artifact_reader: ArtifactEnvelopeReader,
    artifact_publisher: ArtifactEnvelopePublisher,
    market_reader: MarketBundleReader,
    publication_root: Path,
) -> PreparedBacktestExecution
```

The operation owns authority loading, profile resolution, request/semantic identity, execution-case composition, transport publication, and failure mapping. Callers never supply resolved profiles, rule books, per-instrument marks, execution cases, hashes, or private Runtime objects.

No second simulator, generic Engine market branch, live route, creation/redemption workflow, margin, shorting, pledge/repo, or deployment capability is added.

## Authority

| ID | Source | Requirement |
| --- | --- | --- |
| P1 | `overall/a-share-multi-asset-prospective-validation-design.md` | Exact three instruments, fixed 30/50/20 target, conservative two-session liquidation/purchase execution, CNY 400,000, no leverage/shorting, prospective holdout. |
| P2 | `implementation/plans/a-share-etf-data-contract-v1.md` | Runtime integration waits for a retained three-ETF Bundle and product-specific rule/account authority. |
| P3 | `backtest/packages/backtest-runtime/src/crypto_quant_backtest/cash_development_provider.py:349-441` | Existing cash provider is fixed to one SPOT Instrument, one target, and one bar; preserve it unchanged. |
| P4 | `backtest/packages/backtest-runtime/src/crypto_quant_backtest/cn_a_share_profile.py:768-833` | Existing profile accepts one ordinary A-share EQUITY and explicitly rejects funds/bonds; do not alias ETFs through it. |
| P5 | `backtest/packages/backtest-runtime/src/crypto_quant_backtest/target_stream.py` | Reuse the existing complete, canonical, multi-instrument target-stream seam unchanged. |
| P6 | `backtest/tests/kernel/integration/test_target_materialization_journey.py` | Generic validation/allocation/risk/sizing already supports multi-instrument complete targets. |
| P7 | `backtest/packages/trading-kernel/src/crypto_quant_trading/rebalance.py:640-940` | Existing planner creates one order per Instrument and canonicalizes by Instrument ID; it does not promise sell-before-buy funding order. |
| P8 | `backtest/docs/architecture/backtest-system-design.md` | Session, order admission, T+0/T+1, cash availability, fees, settlement, and corporate actions remain market/account Profile authorities. |
| P9 | `implementation/plans/quality-bband-a-share-preparation-seam-v1.md` | Reuse the compact authority-ref preparation pattern, but not its ordinary-stock product assumptions. |
| P10 | `implementation/plans/a-share-etf-rule-mapping-v1.md` | Bind the frozen initial product/session/order/settlement/fee/tax mapping and retained source manifest; future revision closure remains open. |
| P11 | `implementation/plans/a-share-etf-lifecycle-source-contract-v1.md` | Require retained pre-open status plus post-close listing/announcement/distribution evidence and explicit action closure. |

## Design decision

Choose a separate ETF product model.

- Add `InstrumentType.ETF` only under an approved compatibility contract.
- Add a separate `crypto_quant_trading.profiles.cn_etf` package.
- Add a separate Runtime ETF profile composer and public preparation module.
- Do not treat ETF as `SPOT` or ordinary `EQUITY`.
- Do not widen existing stock/Binance/cash-provider behavior by fallback.

The three product classes are authority-significant:

- `DOMESTIC_EQUITY_ETF` — `510300.SH`;
- `BOND_ETF` — `511010.SH`;
- `GOLD_ETF` — `518880.SH`.

## Ownership

- Domain owner: `backtest/packages/trading-domain` for `InstrumentType.ETF` only.
- Market/account semantics owner: `backtest/packages/trading-kernel/src/crypto_quant_trading/profiles/cn_etf/`.
- Profile/preparation owner: `backtest/packages/backtest-runtime/src/crypto_quant_backtest/`.
- Data/Bundle owner: G12 acquisition and Market Bundle Builder.
- Platform consumer changes start only after an accepted Backtest revision is pinned.
- One writer owns each serial phase; no concurrent edits to shared public roots.

## Flow and seam

Before:

```text
exploratory CSV -> experiments/multi_asset.py -> advisory result
```

Accepted fixed-singleton route:

```text
one ordinary stock + zero target -> provider-specific no-trade route
```

Proposed:

```text
CashDevelopmentRequestIntent
+ compact ETF provider inputs
+ BacktestTargetStreamRef
+ retained ETF MarketBundleReader
        -> load/verify ETF portfolio authority
        -> compose ETF Profile registry internally
        -> validate complete target stream and exact catalog/coverage
        -> materialize sell/buy execution phases
        -> register/publish Backtest request and execution bundle
        -> PreparedBacktestExecution
```

## Public values

### `CnEtfPortfolioDevelopmentProviderInputs@1`

1. `schema_version = 1`;
2. `build_artifact_manifest: BuildArtifactManifest`;
3. `portfolio_authority_ref: ArtifactRef` of type `cn_etf_portfolio_development_authority@1`;
4. `strategy_id: str`;
5. `sleeve_id: StrategySleeveId`;
6. `initial_cash: Money` in CNY.

V1 initial state is exact: zero ETF positions, no working orders/reservations/unsettled obligations, and one CNY ledger cash balance equal to `initial_cash`. No second initial-state input or hidden cash buffer exists.

The caller does not supply an InstrumentCatalog, rule book, resolved mark, fee schedule, account state, profile registry, target payload, case, or hash.

### `cn_etf_portfolio_development_authority@1`

Backtest-owned immutable artifact binding:

- exact three-Instrument catalog/ref/hash;
- ETF-DATA-01 Bundle/ref/manifest/content/retention identities;
- per-product session, order, price-limit, T+0/T+1, quantity, fee/tax, corporate-action, and valuation authorities;
- execution-account CNY cash/position availability and settlement rules;
- Profile composition identity and digest;
- Build identity and accepted roles;
- `PRECOMPUTED_TARGET` strategy family and target capability/version;
- bar Engine and next-eligible-open execution;
- development result-grade ceiling and explicit limitations;
- `decision_grade_eligible=false` and `deployment_authorized=false` until separately qualified.

It contains canonical values/refs, not provider clients, local paths, credentials, or Runtime implementations.

## Internal profile modules

### Domain

`InstrumentType.ETF = "etf"` is additive. Existing enum values and all existing canonical bytes remain unchanged.

### Trading Kernel

New `crypto_quant_trading.profiles.cn_etf` interface hides product differences behind one Profile:

- `CnEtfProductClass`;
- `CnEtfInstrumentRuleContext`;
- `CnEtfCashQuantityLatticeModel`;
- `CnEtfCashOrderRuleModel`;
- `CnEtfCashSettlementModel`;
- ETF-specific quantity/order/settlement and cash-distribution/unit-change adapters;
- an additive `commission_tax_v2` scope extension limited to `XSHG + InstrumentType.ETF + CnAShareFeeProductClass.ETF`, preserving existing `XSHE + EQUITY` behavior;
- per-position pending sellability (`false` for `510300`, `true` for `511010` and `518880`);
- pending sale cash tradable immediately, non-withdrawable until next-trading-day settlement;
- explicit account availability projection.

Reuse unchanged generic allocation, risk, sizing, order, accounting, ledger, Engine, and target-stream modules. Reuse the existing China exchange calendar/session model only if an accepted parity fixture proves the ETF session phases are identical for the requested interval.

### Backtest Runtime

New modules:

- `cn_etf_profile.py` — pure composition of exact ETF authorities;
- `cn_etf_portfolio_provider.py` — sole public deep preparation operation.

Do not edit `cash_development_provider.py` to accept multiple Instruments. Do not edit the fixed-singleton route to generalize it.

## Rebalance sequencing

The existing `OrderPlan` canonicalizes planned orders by Instrument ID. That ordering is identity-stable but is not a funding policy, so one same-cycle rebalance cannot promise sale completion before buys.

ETF-PREP-01 therefore freezes a conservative two-session target protocol without changing generic Rebalance or Engine code:

1. signal-session close publishes a complete zero target for all three ETFs;
2. next eligible open executes liquidation orders;
3. after that session closes, a second complete `30/50/20` target becomes available;
4. the following eligible open executes purchases from projected tradable cash.

The paired target events, decision instants, source evidence, strategy/build identity, and target-stream digest are one precommitted strategy contract. A missing or failed liquidation does not authorize borrowing, resizing, or optimistic sale proceeds: the purchase cycle must fail/block through existing availability and pretrade evidence.

This formal prospective execution is intentionally more conservative than the historical exploratory same-open rebalance and must be reported as a distinct strategy identity. It reuses multiple existing target-stream decision cycles and needs no phase-aware generic Rebalance/Engine extension.

## Exact value and identity closure

| Value/artifact | Exact type/schema | Identity owner | Consumer |
| --- | --- | --- | --- |
| ETF target | `BacktestTargetStreamRef` | Backtest Target Repository | preparation/Runtime |
| Portfolio authority | `cn_etf_portfolio_development_authority@1` | Backtest | preparation |
| Market data | `MarketBundleRef` + catalog/coverage refs | G12/Builder | preparation/Runtime |
| Profile | ETF resolved Profile digest | Backtest | resolver/case |
| Request | existing `BacktestRequest@1` | Backtest | Runtime/evidence |
| Semantic Run | existing derivation | Backtest | publications/replay |
| Execution input | accepted execution-bundle schema selected by Backtest | Backtest | Runtime |
| Completed/terminal/analysis | existing refs | Backtest | Research/Validation |

No Platform caller derives identities in the last five rows.

## Failure precedence

| Priority | Condition | Code |
| ---: | --- | --- |
| 1 | exact public input type/schema/CNY mismatch | `INPUT_MISMATCH` |
| 2 | authority ref type/version/read failure | `AUTHORITY_REF_INVALID` |
| 3 | authority reconstruction, owner-log, or hash mismatch | `AUTHORITY_INTEGRITY_FAILURE` |
| 4 | Bundle/ref/manifest/retention/catalog mismatch | `MARKET_BUNDLE_MISMATCH` |
| 5 | ETF Instrument/product/venue/currency mismatch | `ETF_SCOPE_MISMATCH` |
| 6 | session/status/order/quantity/settlement/fee/action coverage gap | `PROFILE_AUTHORITY_MISMATCH` |
| 7 | execution-account availability/initial-state mismatch | `ACCOUNT_AUTHORITY_MISMATCH` |
| 8 | target ref/repository read/decode failure, capability, catalog, timing, completeness, or foreign Instrument | `TARGET_STREAM_INVALID` |
| 9 | verified target producer-context or Build/strategy/sleeve identity mismatch | `BUILD_IDENTITY_MISMATCH` |
| 10 | rebalance phase/supersession/funding-order mismatch | `REBALANCE_SEQUENCE_INVALID` |
| 11 | PREP/Profile resolution incompatibility | `PREPARATION_INCOMPATIBLE` |
| 12 | request/execution-bundle publication or exact-read failure | `PUBLICATION_FAILURE` |

Provider/storage/retention failures remain local/provider failures and never become fabricated Backtest terminals.

## Security and trust

- Runtime preparation is offline and clock-free.
- Tokens and provider clients remain in acquisition tools only.
- Authority and Bundle bytes are duplicate-safe and exact-reconstructed.
- `publication_root` retains existing no-clobber/path protections.
- Successful preparation authorizes one development Backtest only.
- No Shadow, Live, broker, credential, order-routing, or deployment authority follows.

## Compatibility and immutable artifacts

- Existing `InstrumentType` values, stock/Binance profiles, cash-provider signatures, fixed-singleton artifacts, fixtures, hashes, and failure behavior remain unchanged.
- Existing target-stream and generic Kernel/Engine code receive no ETF name matching.
- Existing ordinary A-share Profile continues to reject ETFs.
- Unknown ETF product/rule/version fails closed; no alias or grade downgrade.
- No fallback from ETF preparation to generic cash or fixed-singleton preparation.

## Symbol plan after approval

| Symbol/file | Action | Responsibility |
| --- | --- | --- |
| `InstrumentType.ETF` | additive change | canonical ETF identity |
| `crypto_quant_trading.profiles.cn_etf` | add package | ETF product/session/order/settlement/fee/action adapters |
| `CnEtfProfileCompositionRequest` | add | exact pure authority input |
| `CnEtfResolvedProfile` / `CnEtfProfileComposer` | add | Profile registrations/digests/failure closure |
| `CnEtfPortfolioDevelopmentProviderInputs` | add | compact caller facts |
| `CnEtfPortfolioPreparationFailureCode` | add | stable preparation failures |
| `prepare_cn_etf_portfolio_development_backtest` | add | sole public preparation seam |
| `crypto_quant_backtest.__init__` | export | public values only after acceptance |
| Domain/Kernel/Runtime focused tests | add | identity, product differences, failures, replay |
| Platform integration test | later | public Research/Validation fan-in |

## Forbidden paths

- Reuse `InstrumentType.SPOT` or ordinary `EQUITY` to bypass ETF semantics.
- Modify generic cash preparation to accept multiple Instruments.
- Copy the exploratory simulator into Backtest.
- Supply Profile internals or execution cases from Platform.
- Assume all three ETFs share T+0, fees, tax, distributions, or sale-cash availability.
- Execute buys using unprojected sale proceeds.
- Relabel the conservative T+1 liquidation/T+2 purchase protocol as the historical same-open exploratory strategy.
- Fill from adjusted prices or the signal close.
- Import private Backtest Runtime modules from Research/Validation.

## Independent acceptance

Focused acceptance must prove:

1. existing Domain/profile/cash/fixed-singleton canonical fixtures remain byte-identical;
2. three ETF product classes resolve different settlement/account behavior correctly;
3. multi-instrument target input order does not change target/Profile/Run identity;
4. sell phase precedes buy phase and incomplete sells deterministically block buys without resizing;
5. T+0/T+1, lot, tick, price-limit, suspension, fees, distributions, and account availability come from authority, not caller constants;
6. repeat preparation returns the same request ref, semantic run, and execution transport;
7. malformed/foreign/future/missing evidence fails at the frozen precedence;
8. public root exposes no private/resolved implementation object;
9. full Backtest suite, typing, import architecture, secrets, lock, and diff checks pass;
10. fresh independent review finds no market-authority or grade escalation.

## Readiness gate

`ETF-PREP-01` remains `NOT_READY` until:

- ETF-DATA-01 publishes an accepted retained three-ETF authority;
- ETF `fund_daily` numeric mapping and product lifecycle schemas are accepted;
- the initial session/order/settlement/fee/tax mapping is frozen, and the accepted lifecycle sentinel plus future rule revisions provide daily status and corporate-action authority for all three products;
- the paired zero-target/final-target protocol and failure behavior are accepted;
- the portfolio authority schema and fixture are approved;
- Backtest owner approves `InstrumentType.ETF`, public names, failure codes, and exact write set;
- Platform owner approves the consumer fixture.

## Next safe action

Capture the first ETF-DATA-01 source sentinel after the `2026-09-01` session is final, then freeze the ETF `fund_daily` numeric mapping. Do not implement Domain/Kernel/Runtime ETF support before those evidence steps complete.
