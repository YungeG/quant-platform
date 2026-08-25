# BT-TRADIFI-AMEND-01 target ownership and durable execution-role amendment

- **Status:** APPROVED — implementation authorized by the Platform owner
- **Amends:** [`tradifi-perpetual-capability-contract.md`](tradifi-perpetual-capability-contract.md)
- **Reason:** implementation discovery proved four approved assumptions incompatible with existing Backtest architecture
- **Existing accepted commits retained:** `af45a2f`, `315d8f7`, `3e8c913`

## 1. Discovered incompatibilities

1. `PrecomputedTargetStream` events must already exist in the immutable supplied MarketBundle. Preparation cannot mutate that reader or publish a derived bundle through the approved interface.
2. The Engine always uses `FullFillBuilder`; a taker builder stored only in provider profile evidence cannot affect actual fills.
3. `ResolvedBarExecution` and current execution-input codecs do not persist a fill-liquidity choice.
4. Existing Binance archive acquisition/normalization modules are frozen BTCUSDT fixtures and cannot be relabeled as KORUUSDT.

No private workaround, mutable reader, ambient cache, or runtime callback is permitted.

## 2. Frozen public preparation interface

The already approved public operation remains unchanged:

```python
prepare_binance_usdm_tradifi_bar_backtest(
    *,
    request_intent: BinanceUsdmTradifiBarRequestIntent,
    provider_inputs: BinanceUsdmTradifiProviderInputs,
    artifact_reader: ArtifactEnvelopeReader,
    artifact_publisher: ArtifactEnvelopePublisher,
    market_reader: MarketBundleReader,
    publication_root: Path,
) -> PreparedBacktestExecution | BinanceUsdmTradifiPreparationFailure
```

Preparation remains a deep verification/composition seam. It does not perform network acquisition or strategy calculation.

## 3. Target-stream ownership amendment

**Bundle construction owns deterministic strategy calculation.**

The immutable discovery MarketBundle contains exactly eight target streams, one for each precommitted parameter-set ref. The bundle builder computes them from exact completed mark/index bars, calendars, unit regime, and strategy-definition/parameter artifacts before MarketBundle publication.

Preparation:

1. resolves the exact `strategy_parameter_set_ref` from intent;
2. reads one authority event mapping that ref to one target stream key and digest;
3. verifies the target stream exists, exact-covers its declared decision schedule, binds the strategy-definition/parameter refs, and matches the recorded digest;
4. selects that existing stream without recomputing targets or mutating the MarketBundle.

Unknown, duplicate, foreign, or unmapped parameter refs fail before request registration.

## 4. Preparation authority stream

Add one required stream:

```text
stream key: binance_usdm.tradifi.preparation_authority.v1
capability: binance_usdm.tradifi.preparation-authority@1
```

It contains exactly one immutable authority event for the bundle:

```python
TradifiPreparationAuthorityEvent@1 = {
    profile_composition_request: canonical wire,
    strategy_definition_ref: ArtifactRef,
    parameter_target_map: [
        {
            strategy_parameter_set_ref: ArtifactRef,
            target_stream_key: str,
            target_stream_digest: sha256,
        },  # exactly eight, canonically sorted
    ],
    xkrx_calendar_ref: ArtifactRef,
    arcx_calendar_ref: ArtifactRef,
    post_adjustment_unit_regime_ref: ArtifactRef,
    source_snapshot_refs: [SourceSnapshotRef, ...],
    normalization_hashes: [sha256, ...],
}
```

The event payload is canonical JSON data. Preparation uses one exact decoder owned by the new preparation module. It reconstructs only approved public immutable values and requires every reconstructed ref/value to match the MarketBundle manifest, profile request, and selected target stream.

## 5. Source retention amendment

Original ZIP/CSV/JSON bytes remain in immutable `SourceSnapshot` retention, not inside MarketBundle event payloads.

The MarketBundle binds:

- exact `SourceSnapshotRef` values;
- member path and source SHA-256;
- capture and availability provenance;
- normalization request/result hashes;
- finite coverage and gap classification;
- projected MarketEvent stream hashes.

A MarketBundle manifest/event-stream hash without retained source snapshot lineage is insufficient.

## 6. Required KORU source-bounded modules

Existing BTCUSDT archive modules remain unchanged. Add KORU-specific, source-bounded modules or a new exact parameterized version whose identity includes KORUUSDT and the post-adjustment coverage. V1 requires separate accepted outputs for:

1. aggregate trades;
2. mark-price bars;
3. index-price strategy bars;
4. Funding Rate History;
5. instrument/order/margin/account/profile source revisions;
6. XKRX and ARCX calendar artifacts;
7. post-adjustment unit-regime/corporate-action artifact.

No BTC fixture hash, date, row count, stream key, or source path may be reused as KORU authority.

## 7. Minimum MarketBundle streams

The TradFi bundle contains at least:

1. retained aggregate-trade source events;
2. projected `bar_open@1` events, each representing the first retained aggregate trade at/after one eligible boundary, with event/available time equal to trade time;
3. completed one-hour mark strategy bars;
4. completed one-hour index strategy bars;
5. purpose-specific mark streams for valuation, margin, and liquidation;
6. funding publication/application streams;
7. eight precomputed target streams;
8. one preparation-authority stream;
9. existing account financial-event and snapshot inputs required by the composed Case.

Nominal hourly bucket time is not execution availability.

## 8. Durable execution-role amendment

Add a new versioned execution-input path; do not change existing canonical bytes.

```python
ResolvedBarExecutionV2 = existing fields + {
    fill_liquidity_role: None | "maker" | "taker",
}
```

Rules:

- legacy materializers/decoders/cases retain the existing schema and bytes and imply `None`;
- TradFi materialization uses a new envelope/schema version and stores `"taker"`;
- Engine selects `FullFillBuilder` when the field is `None`;
- Engine selects `LiquidityRoleFullFillBuilder(role)` when `maker` or `taker`;
- unknown roles fail during decoding/construction;
- the role is bound into execution-case identity, input-bundle bytes, rebuild proof, Fill identity, fee assessment, and replay.

This is an additive durable identity change, not a provider-only profile note.

## 9. Revised write set

In addition to already accepted files/commits:

- `packages/backtest-runtime/src/crypto_quant_backtest/engine.py`;
- `packages/backtest-runtime/src/crypto_quant_backtest/execution_inputs.py`;
- new execution-input materializer/decoder version and tests;
- KORU source-bounded aggregate-trade module;
- KORU source-bounded mark/index strategy-bar module;
- KORU source-bounded funding-history module;
- TradFi preparation authority/target bundle builder;
- TradFi preparation decoder/case builder/public operation;
- durability/rebuild/replay fixtures and mutation tests if the new input schema enters durable proof closure.

Existing schemas/functions remain present and unchanged for ordinary runs.

## 10. Failure precedence additions

Insert before profile composition/request registration:

1. source snapshot/member/hash/normalization retention mismatch;
2. authority stream missing, duplicate, malformed, or foreign;
3. strategy-definition or parameter-target map mismatch;
4. selected target stream missing, digest mismatch, or exact-cover failure;
5. projected first-trade event missing or nominal-boundary substitution;
6. execution-input liquidity role missing/unknown/mismatched with TradFi simulation profile;
7. new execution-input round-trip or durable-rebuild decode mismatch.

No failure may trigger target recomputation, derived bundle publication, role defaulting to `full`, or legacy execution-input downgrade.

## 11. Compatibility

- existing ordinary Binance component/profile hashes unchanged;
- existing `FullFillBuilder` and legacy execution inputs unchanged;
- existing `ResolvedBarExecution` canonical bytes unchanged;
- legacy Engine cases continue using `FullFillBuilder`;
- no Research, Validation, Foundation, Promotion, or Platform schema change;
- no current/network data read during preparation or execution;
- no second simulator, intrabar execution, Shadow, Live, or deployment authority.

## 12. Revised acceptance

1. Eight parameter refs map bijectively to eight immutable target streams.
2. Changing only parameter ref selects a different recorded target stream/digest and prepared request identity.
3. Preparation cannot add streams to the supplied reader and never calculates targets.
4. First retained aggregate trade projects to exact `bar_open@1` event time/availability; missing trade means no fill candidate.
5. New execution-input schema round-trips `fill_liquidity_role="taker"` and changes Case/input/rebuild identity.
6. Runtime TradFi fills carry `taker`; legacy fills remain `full`.
7. Fee assessment accepts TradFi taker fills and ordinary fee/hash fixtures remain unchanged.
8. Rebuild/replay preserves role, target stream, profile, refs, and no second execution.
9. BTC source-bounded fixtures cannot satisfy KORU requests.
10. Full Backtest and recursive Platform compatibility gates remain green.

## 13. Revised DAG

```text
BT-TRADIFI-AMEND-01 approval
  ├─→ BT-TRADIFI-EXEC-ROLE-01 durable role/input path
  ├─→ BT-TRADIFI-SOURCE-01 KORU source-bounded normalizers
  └─→ BT-TRADIFI-BUNDLE-01 authority + eight targets + event streams
          └─→ BT-TRADIFI-PREP-01 public preparation operation
                  └─→ BT-TRADIFI-FANIN-01
```

One sequential Backtest writer remains required. Already accepted commits are inputs to the revised DAG, not discarded work.

## 14. Explicit exclusions

- runtime target calculation;
- mutable/derived MarketBundle during preparation;
- generic formula/plugin/callback interface;
- changing legacy execution-input bytes;
- relabeling BTC archives as KORU;
- raw source bytes embedded directly in MarketBundle events;
- order-book, queue, partial-fill, intrabar, or matching-engine simulation;
- decision-grade, Shadow, Live, deployment, or capital movement.
