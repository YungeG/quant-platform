# KORU Directional Target Compiler v1 Contract

## Recommended seam and ownership

**Owner:** `crypto_quant_bundle_builder`
**Public module:** `binance_usdm_koru_directional_target_compiler_v1`
**Seam:** an exact discovery-scoped immutable `SourceProjectionV2` plus explicit directional observation projections → pre-publication `PrecomputedTargetStream`s.

The compiler runs before `MarketBundle` publication. It does not read published bundles, invoke Runtime/Engine code, calculate fills/PnL/funding settlement, or accept callbacks.

- **Compiler:** validates evidence and emits absolute target events.
- **Bundle builder:** exact-binds and publishes compiled streams.
- **Backtest Runtime/Engine:** reconstructs published streams, applies existing next-eligible-real-bar execution rules, and owns execution and funding accounting.
- **Research:** selects a published bundle/stream binding through existing preparation; it cannot supply target events or compiler callbacks.

## Public API

```python
@dataclass(frozen=True)
class KoruDirectionalTargetRecipeV1: ...

@dataclass(frozen=True)
class KoruDirectionalTargetCompileRequestV1: ...

@dataclass(frozen=True)
class KoruDirectionalTargetCompileOutcomeV1: ...

def compile_binance_usdm_koru_directional_targets_v1(
    request: KoruDirectionalTargetCompileRequestV1,
) -> KoruDirectionalTargetCompileOutcomeV1: ...
```

`KoruDirectionalTargetCompileOutcomeV1` contains exactly one of:

- `result: KoruDirectionalTargetCompileResultV1`
- `failure: KoruDirectionalTargetCompileFailureV1`

Both are immutable, typed, and canonicalizable.

## Request and identity

`KoruDirectionalTargetCompileRequestV1` contains:

- accepted `SourceProjectionV2` result and its immutable ref/digest;
- `KoruDirectionalDiscoveryScopeV1`, fixed to `[2026-07-15T10:00:00Z, 2026-08-24T11:00:00Z)` with `scope_end_exclusive <= holdout_start`; every source event used by compilation must lie inside that discovery scope;
- optional immutable `KoruFundingPublicationProjectionV1` and `KoruCashOpenObservationProjectionV1` refs, each carrying its producer digest, source fragment digest, event identities, selected revisions, and availability times;
- non-empty, canonical-sort-order tuple of recipes;
- request schema version `"koru_directional_target_compile_v1"`;
- `request_digest`, computed from canonical request bytes.

Recipes are sorted strictly by `(family, recipe_id, parameter_ref.content_hash, target_stream_key)`. `recipe_id`, strategy/parameter-ref pair, and target stream key must each be globally unique. Result recipe bindings use that same order; target events use the existing full timeline ordering key; stream manifests are sorted by stream key.

A recipe includes:

- `family`: exactly one of:
  `breakout`, `mark_index_premium`, `funding_carry`, `cash_open_momentum`;
- `recipe_id`, `strategy_id`, `sleeve_id`;
- immutable strategy and parameter `ArtifactRef`s;
- target stream key;
- one KORU instrument identity;
- fixed target exposure as canonical decimal string;
- bar interval;
- required source-capability bindings and, where required, calendar revision ref;
- sealed family-specific parameters;
- explicit flat behavior.

No recipe field may contain executable code, callable values, class instances, Engine/Runtime handles, paths, arbitrary mappings, mutable registries, source bytes, metadata escape hatches, adaptive search fields, or inferred defaults.

Recipe artifact refs identify **strategy semantics**. Compiled stream digests identify **executable target payloads**. Compilation fails if the supplied source scope contains, requests, or references an observation at or after the frozen Holdout start; it does not trim, redact, or select from Holdout data.

## Recipe schemas

All decimal values are canonical strings. All windows are positive integers. All thresholds are non-negative unless the schema explicitly states otherwise.

### `breakout`

Required capabilities:

- completed KORU price bars at the declared interval;
- referenced calendar facts for XKRX and ARCX closed-state gating;
- next-boundary aggregate-trade evidence.

Fields:

```text
lookback_bars: int
entry_buffer_bps: decimal
stop_bps: decimal
max_hold_eligible_hours: int
target_exposure: decimal
flat_when_inside_range: true
flatten_before_funding: true
require_xkrx_closed: true
require_arcx_closed: true
```

Signal:

- long target when close exceeds the preceding `lookback_bars` high by `entry_buffer_bps`;
- short target when close is below the preceding low by `entry_buffer_bps`;
- otherwise explicit flat target.

Exit to flat after a completed Mark returns inside the formation range, reaches the declared adverse `stop_bps`, reaches `max_hold_eligible_hours`, before an eligible funding settlement, or before either cash market opens. Formation, decision, projected execution interval, and every forced-flat boundary must satisfy the declared XKRX/ARCX closed-state gates.

### `mark_index_premium`

Required capabilities:

- completed, same-interval Mark bars;
- completed, same-interval Index bars;
- next-boundary aggregate-trade evidence.

Fields:

```text
entry_premium_bps: decimal
exit_premium_bps: decimal
max_hold_hours: int
target_exposure: decimal
flat_when_inside_band: true
```

`premium_bps = 10_000 * (mark - index) / index`.

Signal:

- long target when premium is at or below `-entry_premium_bps`;
- short target when premium is at or above `entry_premium_bps`;
- otherwise explicit flat target.

Exit to flat when premium crosses zero, contracts to `exit_premium_bps`, reaches `max_hold_hours`, or an opposite entry qualifies. Mark and Index observations must be an exact completed pair for the same interval and selected revision. No mixed-revision, as-of, inferred, or substituted pairing is valid.

### `funding_carry`

Required capabilities:

- final revisioned funding-publication observations from an accepted `KoruFundingPublicationProjectionV1`;
- declared KORU price/risk inputs;
- next-boundary aggregate-trade evidence.

`funding_carry` is an explicitly **unsupported family in v1** unless that projection is supplied and exact-binds final publication revision, `available_time`, settlement identity, and funding Mark. Current SourceProjectionV2 alone is insufficient.

Fields:

```text
funding_threshold_bps: decimal
target_exposure: decimal
flat_when_inside_band: true
```

Signal:

- short target when published funding is at or above `funding_threshold_bps`;
- long target when published funding is at or below `-funding_threshold_bps`;
- otherwise explicit flat target.

A funding timestamp alone is not publication evidence. The final selected publication revision must prove `available_time <= decision_time`. The compiler never models funding payment or settlement eligibility.

### `cash_open_momentum`

Required capabilities:

- completed KORU price bars;
- immutable calendar revision and an accepted `KoruCashOpenObservationProjectionV1` containing the declared XKRX or ARCX opening, opening-bar overlap identity, calendar availability, and source-bar evidence;
- next-boundary aggregate-trade evidence.

`cash_open_momentum` is an explicitly **unsupported family in v1** unless that projection is supplied. SourceProjectionV2 does not itself evidence in-session opening boundaries.

Fields:

```text
market: "XKRX" | "ARCX"
momentum_threshold_bps: decimal
hold_hours: int
adverse_stop_pct: decimal
target_exposure: decimal
flat_when_inside_band: true
non_overlapping_open_events: true
```

Signal uses the first completed declared-interval bar overlapping the referenced cash-market opening:

- long target when its open-to-close return is at or above `momentum_threshold_bps`;
- short target when return is at or below `-momentum_threshold_bps`;
- otherwise explicit flat target.

Exit at the next eligible boundary after `hold_hours`, or after a completed purpose-specific Mark observes the declared adverse `adverse_stop_pct`. A position may not span another declared XKRX/ARCX opening; overlapping opening windows emit flat rather than selecting an arbitrary priority. Calendar facts—including holidays, early closes, and ARCX DST—must come only from the referenced immutable calendar revision and be available by the decision.

## Knowledge-time and execution rules

For every target decision:

1. Every evidence item records event hash, selected revision hash, event time, and available time.
2. Every input must satisfy `available_time <= decision_time`.
3. Decision input bars must be completed. Incomplete, missing, duplicate, revision-inconsistent, or coverage-incomplete observations fail closed.
4. A source bar used for a decision is signal-only and is never a fill bar.
5. `effective_time == decision_time`.
6. A target change requires evidence for the next eligible execution boundary and the first retained aggregate trade with:

   ```text
   event_time >= boundary > decision_time
   ```

   That trade is execution evidence only; the compiler does not emit fill prices.
7. If a candidate target change occurs inside the declared executable discovery scope and required next-boundary evidence is absent, return `NEXT_BOUNDARY_EVIDENCE_MISSING`; no result is published. If the decision is at the normal terminal scope boundary where no later boundary is required, emit the recipe-defined canonical flat/end state.
8. No forward filling, as-of substitution, inferred calendar state, inferred funding availability, partial publication, or fallback stream is allowed.

Runtime’s existing next-real-bar-open/no-fill behavior remains authoritative.

## Deterministic result

A successful result contains, for each canonically ordered recipe:

- immutable recipe binding and `recipe_ref`;
- exact source-fragment digest;
- canonical ordered target events;
- `MarketStreamManifest`;
- target stream key;
- `target_stream_digest`;
- immutable evidence identity records.

The enclosing result has `result_digest`, computed from canonical result bytes.

The same accepted source projection, scope, projections, and recipes must produce byte-identical events, manifests, refs, and digests. “No signal” is successful: emit the canonical empty stream or the schema-required explicit flat event.

Compilation result V1 is consumed only by additive `BinanceUsdmKoruDirectionalExecutionBundleV3` and `binance_usdm.tradifi.preparation_authority.koruusdt.v3`. Bundle V3 exact-binds compiler result ref/digest, scope ref, stream key, event bytes, manifest digest, recipe ref, source-fragment digest, and target-stream digest. Publication with only a CAS reference is invalid. Existing BundleV1/V2 and preparation authorities remain immutable. A new public `prepare_binance_usdm_tradifi_directional_bar_backtest(...)` consumes only V3 published bundle authority and returns the existing durable `PreparedBacktestExecution`; it never recompiles targets.

## Failure precedence

Return the first applicable typed failure in this order:

1. malformed request, unknown family, noncanonical recipe/order, invalid artifact refs, or identity/hash failure;
2. source-projection identity, trust, capability, schema, lineage, duplicate, revision-chain, or coverage failure;
3. causal availability, completion, paired-bar, calendar, funding-publication, chronology, or next-boundary evidence failure;
4. family parameter, source-kind, interval, or target-rule failure;
5. target-event, manifest, stream-digest, result-digest, bundle-binding, or reconstruction mismatch;
6. existing public preparation/publication authority failures after compilation.

Notably, absent contemporaneous funding authority is
`FUNDING_AVAILABILITY_UNPROVEN`, not a neutral funding signal.

## Fixed 12-trial v1 slate

This slate exactly supersedes the conditional launch rows in `research/koruusdt/directional-discovery-plan-v1.md`. All trials use one-hour bars, 0.25 target exposure, seed 0, and the declared KORU instrument from their recipe artifact.

| Trial | Family | Fixed parameters |
|---|---|---|
| `KORU-PRM-01` | mark/index premium | entry 20 bps, exit 5 bps, hold 12h |
| `KORU-PRM-02` | mark/index premium | entry 30 bps, exit 5 bps, hold 12h |
| `KORU-PRM-03` | mark/index premium | entry 40 bps, exit 5 bps, hold 12h |
| `KORU-PRM-04` | mark/index premium | entry 60 bps, exit 5 bps, hold 12h |
| `KORU-OPN-01` | cash-open momentum | XKRX, threshold 0.50%, hold 2h, adverse stop 3%, non-overlap |
| `KORU-OPN-02` | cash-open momentum | XKRX, threshold 0.50%, hold 4h, adverse stop 3%, non-overlap |
| `KORU-OPN-03` | cash-open momentum | ARCX, threshold 0.50%, hold 2h, adverse stop 3%, non-overlap |
| `KORU-OPN-04` | cash-open momentum | ARCX, threshold 0.50%, hold 4h, adverse stop 3%, non-overlap |
| `KORU-BRK-01` | breakout | lookback 6h, buffer 0 bps, stop 50 bps, hold 4h, pre-funding flat |
| `KORU-BRK-02` | breakout | lookback 6h, buffer 0 bps, stop 100 bps, hold 4h, pre-funding flat |
| `KORU-BRK-03` | breakout | lookback 12h, buffer 10 bps, stop 50 bps, hold 4h, pre-funding flat |
| `KORU-BRK-04` | breakout | lookback 12h, buffer 10 bps, stop 100 bps, hold 4h, pre-funding flat |

Funding carry is deferred and may not consume a trial in this slate. These are fixed parameter trials, not adaptive search inputs.

## Compatibility

This is additive.

- Existing range-fade V1/V2 generators, streams, bytes, and digests remain untouched.
- Existing Integration v1–v5 artifacts, logs, nominal refs, dispatch, admission, validation, promotion, and `DeferredTrialExecution` wire fields remain unchanged.
- Existing `PrecomputedTargetStream`, bundle assembly, and public TradFi preparation contracts remain the consumption path.
- Preparation reopens only a published `MarketBundleRef`; it must not recompile targets or downgrade v1/v2 contracts.
- A future range-fade adapter requires demonstrated byte-for-byte legacy-stream parity before publication replacement.

## Remaining implementation work

1. Define frozen canonical compiler, discovery-scope, funding-publication-projection, cash-open-observation-projection, BundleV3/preparation-authority V3 data types and typed failures.
2. Implement source-capability/evidence validation, discovery/holdout scope enforcement, canonical sorting, and canonical hashing.
3. Implement deterministic breakout and premium evaluators. Implement funding/opening only after their explicit supporting projections are accepted; until then they return `UNSUPPORTED_RECIPE_FAMILY`.
4. Bind compiler results into BundleV3 publication and `prepare_binance_usdm_tradifi_directional_bar_backtest` digest checks without changing BundleV1/V2 or existing preparation bytes.
5. Add golden, causality, Holdout-isolation, tamper, boundary-import, BundleV3, and compatibility sentinel tests.