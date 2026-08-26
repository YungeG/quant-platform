# QB-PREP-01 — A-share portfolio development preparation seam v1

- **Status:** `NOT_READY / DATA_AUTHORITY_AND_OWNER_APPROVAL_BLOCKED`
- **Owner:** Backtest Runtime public composition
- **Consumer:** Platform Research and Validation through `crypto_quant_backtest`
- **Data prerequisite:** [`quality-bband-data-contract-v1.md`](quality-bband-data-contract-v1.md)
- **Preserved provider pattern:** `prepare_cash_development_backtest(...) -> PreparedBacktestExecution`

## 1. Outcome

Expose one deep public Backtest preparation operation for a retained, qualified multi-instrument A-share cash portfolio Bundle. The operation owns request registration, semantic-run identity, profile resolution, execution-case composition, executable transport and all failure mapping. Platform callers supply only one generic request intent, one compact provider-input value and structural Foundation/MarketBundle ports.

No new simulator, Runner, Engine branch, metric implementation, Platform adapter or private-object transport is introduced.

## 2. Authority

| ID | Source | Requirement |
| --- | --- | --- |
| P1 | `implementation/backtest-provider-handoff.md` | Backtest exclusively owns request hash, semantic run, resolved profiles/cases, execution transport and evidence. |
| P2 | `backtest/packages/backtest-runtime/src/crypto_quant_backtest/cash_development_provider.py` | Reuse `CashDevelopmentRequestIntent` and `PreparedBacktestExecution`; preparation is a deep public operation. |
| P3 | `backtest/docs/implementation/plans/g08/g08h.md` | A-share Profile composition exists but is development-only and currently supports precomputed targets within declared scope. |
| P4 | `backtest/docs/research/g11j-precomputed-strategy-parity.md` | Precomputed target and Strategy entry share downstream economics only after validated TargetSnapshot normalization; no second downstream path is allowed. |
| P5 | `backtest/docs/implementation/plans/g12/g12m-tushare-fixed-singleton-qualification-v2.md` | Existing accepted A-share route is fixed-singleton/no-trade and cannot be generalized by claim. |
| P6 | Quant Strategy Research rules | Execute only through a concrete public preparation operation; never compose private Resolver/Runner/Publisher objects. |

## 3. Public interface

Proposed exports from `crypto_quant_backtest`:

```python
class CnASharePortfolioDevelopmentProviderInputs: ...
class CnASharePortfolioPreparationFailureCode(str, Enum): ...
class CnASharePortfolioPreparationFailure(Exception): ...

def prepare_cn_a_share_portfolio_development_backtest(
    *,
    request_intent: CashDevelopmentRequestIntent,
    provider_inputs: CnASharePortfolioDevelopmentProviderInputs,
    artifact_reader: ArtifactEnvelopeReader,
    artifact_publisher: ArtifactEnvelopePublisher,
    market_reader: MarketBundleReader,
    publication_root: Path,
) -> PreparedBacktestExecution: ...
```

Reuse unchanged:

- `CashDevelopmentRequestIntent@1`;
- `PreparedBacktestExecution`;
- `BacktestRequestRef`;
- `BacktestExecutionRequest@2`;
- `BacktestRuntime`;
- artifact reader/publisher structural ports;
- verified evidence and analysis repository interfaces.

## 4. Compact provider input

`CnASharePortfolioDevelopmentProviderInputs@1` exact fields:

1. `schema_version = 1`;
2. `build_artifact_manifest: BuildArtifactManifest`;
3. `portfolio_authority_ref: ArtifactRef` with type `cn_a_share_portfolio_development_authority@1`;
4. `strategy_id: str`;
5. `sleeve_id: StrategySleeveId`;
6. `initial_cash: Money` in CNY.

The caller does **not** supply:

- resolved Profile objects or component registries;
- per-Instrument quantity lattices, marks, rule books or fee rules;
- a resolved execution case;
- request/semantic-run hashes;
- local paths, provider credentials or current metadata;
- decoded financial features or selected stocks;
- grade or deployment flags.

## 5. Portfolio authority artifact

`cn_a_share_portfolio_development_authority@1` is a Backtest-owned immutable artifact published only after data/Profile qualification. Its payload exact-binds:

- `MarketBundleRef` and manifest/content hashes;
- exact full `InstrumentCatalog` artifact/ref/hash;
- listing/Universe, status, rule, price, corporate-action, financial, governance and valuation coverage report refs;
- accepted A-share resolved Profile composition identity and digest;
- execution account, Venue, CNY, domestic-direct access route and ordinary-A-share product scope;
- Build authority and supported `BuildArtifactRole` coverage;
- supported engine kind `bar`;
- supported strategy family `PRECOMPUTED_TARGET` only;
- required target stream capability/version;
- requested/result grade ceiling `development`;
- exact limitations;
- `decision_grade_eligible = false`;
- `deployment_authorized = false`.

The artifact contains refs and identities, not provider payload copies, Runtime implementations, filesystem paths or credentials.

## 6. Target/Strategy seam

QB-PREP-01 accepts one immutable validated precomputed target stream already included in or exact-bound to the retained Bundle.

Rules:

1. target events carry validated complete `TargetSnapshot` values, not deltas;
2. signal Decision instant and target availability precede execution;
3. each target Instrument exists in the exact catalog and point-in-time Universe;
4. target omission means zero target according to the existing complete-snapshot contract;
5. Build identity binds the exact decision-source Strategy implementation that generated the stream;
6. no target event is generated, modified or interpreted by Platform preparation code;
7. future direct G11 Strategy invocation support requires a separate accepted contract; QB-PREP-01 adds no Runner origin branch.

For `quality-bband-breakout.manual4.v1`, an upstream deterministic Strategy build consumes immutable point-in-time observation views and publishes the target stream. That build is not part of QB-PREP-01.

## 7. Preparation flow

```text
CashDevelopmentRequestIntent
+ compact CnASharePortfolioDevelopmentProviderInputs
+ ArtifactEnvelopeReader/Publisher
+ retained MarketBundleReader
        |
        v
load and verify portfolio authority
        |
        v
verify Bundle/catalog/coverage/build exact identity
        |
        v
resolve accepted A-share Profile registry internally
        |
        v
validate target stream causality and exact cover
        |
        v
construct/register/persist BacktestRequest@1
        |
        v
publish/verify BacktestExecutionInputBundle@2
        |
        v
PreparedBacktestExecution
```

Backtest Runtime executes only after successful preparation through `BacktestRuntime.run(request)`.

## 8. Failure precedence

| Priority | Condition | Code |
| ---: | --- | --- |
| 1 | exact input type/schema/currency mismatch | `INPUT_MISMATCH` |
| 2 | authority ref type/version/load failure | `AUTHORITY_REF_INVALID` |
| 3 | authority artifact reconstruction or owner/publication mismatch | `AUTHORITY_INTEGRITY_FAILURE` |
| 4 | Bundle ref, manifest, retention or reader provenance mismatch | `MARKET_BUNDLE_MISMATCH` |
| 5 | catalog body/hash or Instrument identity mismatch | `INSTRUMENT_CATALOG_MISMATCH` |
| 6 | required coverage report missing, failed or foreign | `COVERAGE_AUTHORITY_MISMATCH` |
| 7 | Profile/account/Venue/route/product/currency mismatch | `PROFILE_SCOPE_MISMATCH` |
| 8 | required capability, stream or Timeline coverage missing | `CAPABILITY_MISMATCH` |
| 9 | target stream duplicate, malformed, future, incomplete or foreign | `TARGET_STREAM_INVALID` |
| 10 | Strategy/build artifact role or content identity mismatch | `BUILD_IDENTITY_MISMATCH` |
| 11 | initial cash, lot feasibility or account-resource authority mismatch | `ACCOUNT_INPUT_MISMATCH` |
| 12 | request registration/publication/exact-read failure | `REQUEST_PUBLICATION_FAILURE` |
| 13 | PREP/Profile resolution incompatibility | existing structured preparation failure mapped without downgrade |

Provider/storage/tamper/retention errors remain local/provider failures. They are not fabricated Backtest terminals.

## 9. Identity closure

| Value | Exact identity/preimage owner |
| --- | --- |
| Provider inputs | Canonical fields in §4; no self hash. |
| Portfolio authority | Artifact Envelope type/version/content hash over §5 payload. |
| Backtest request | Backtest-owned canonical request including opaque `experiment_id`, authority ref, Bundle ref, Build identity and Timeline. |
| Semantic Run ID | Backtest-owned derivation from the registered request and resolved execution inputs. |
| Execution input bundle | Existing Backtest-owned `backtest_execution_input_bundle@2`. |
| Completed/terminal refs | Existing canonical publication/evaluation identities. |
| Analysis | Existing verified completed-only source publication and execution-result link. |

No caller derives or supplies any hash in the last five rows.

## 10. Compatibility and preservation

- Existing `prepare_cash_development_backtest` and model-bound preparation signatures, bytes and behavior remain unchanged.
- Existing fixed-singleton G12M authority, route, Run, assessment, fixtures and hashes remain immutable.
- Existing Profile/Engine/Runner loops receive no A-share name matching or market-specific branch.
- Existing `PreparedBacktestExecution` is reused exactly; no subclass or union is added.
- No fallback from portfolio preparation to generic cash preparation or fixed singleton exists.
- Unknown authority/capability/version fails closed; no grade downgrade.
- Request replay and cache semantics remain Backtest-owned and deterministic.

## 11. Security and trust

- `publication_root` follows existing path/symlink/no-clobber protections.
- Structural readers return source bytes only; Backtest performs semantic decoding and verification.
- No provider token or network client enters Runtime preparation.
- Untrusted authority and Bundle bytes are exact-type, duplicate-safe and full-graph verified.
- Successful PREP grants execution authority for one development Backtest only; it grants no Shadow/Live/order-routing authority.

## 12. Forbidden paths

| Authority | Forbidden route | Required route |
| --- | --- | --- |
| P1/P6 | Platform derives `BacktestRequest`, Semantic Run, Profile registry or ExecutionCase | Call the new public preparation operation. |
| P3/P5 | Reuse fixed-singleton authority for multiple Instruments or nonzero targets | Publish a new portfolio authority after full data/Profile qualification. |
| P4 | Add a separate Engine/Runner path for G11 Strategy callbacks | Use validated precomputed target stream; direct Strategy entry is a later contract. |
| P1 | Caller supplies per-Instrument resolved rules/fees/marks | Authority ref + retained Bundle; Backtest resolves internally. |
| P6 | Direct import of `facade`, `runner`, `engine`, `composition`, private resolver/publisher | Public `crypto_quant_backtest` root only. |

## 13. Expected symbol and write plan after approval

| Symbol/file | Action | Responsibility |
| --- | --- | --- |
| `CnASharePortfolioDevelopmentProviderInputs` | add in one Backtest Runtime public-provider module | Compact canonical caller facts. |
| `CnASharePortfolioPreparationFailureCode` | add | Stable public preparation failure vocabulary. |
| `CnASharePortfolioPreparationFailure` | add | Carries code without leaking private objects or credentials. |
| `prepare_cn_a_share_portfolio_development_backtest` | add | Sole public deep preparation operation. |
| `crypto_quant_backtest.__init__` | export | Exact three types/function only after acceptance. |
| focused provider tests | add | Happy path, failure precedence, replay and no-private-transport. |
| architecture tests | add | Public-root-only, no generic Engine/Runner market branches, fixed-singleton hash protection. |
| integration consumer test | add in Platform after Backtest acceptance | Real public preparation/execute/repository/analysis flow. |

One Backtest writer owns the provider module and root exports. Platform integration changes begin only after a clean accepted Backtest revision is remotely reachable and pinned.

## 14. Independent acceptance

Focused Backtest acceptance must prove:

1. two or more Instruments, four-target maximum and nonzero target execution prepare successfully;
2. target event order and input order do not change semantic identity;
3. malformed/future/foreign target and coverage refs fail at the frozen precedence;
4. T+1, lot, price-limit block, suspension, fees/tax and corporate actions are supplied by the accepted Profile/Bundle rather than caller code;
5. exact replay returns the same request ref, semantic run and execution transport;
6. fixed-singleton artifacts/hashes remain unchanged;
7. public root exposes no resolved/private object;
8. full Backtest suite, import boundaries, static typing, lock and diff checks pass;
9. independent reviewer finds no private workaround or grade/live escalation.

Platform fan-in then proves Research and Validation can consume the operation without Backtest importing Platform packages.

## 15. Readiness gate

`NOT_READY` until:

- QB-DATA-01 is accepted with retained Fold Bundle refs;
- portfolio authority schema and exact fixture are approved;
- A-share Profile composition qualifies the requested multi-instrument/account scope;
- target-stream producer/build identity contract is frozen;
- Backtest repository owner approves public names, write set and failure codes;
- Platform owner approves the consumer contract fixture.

The next safe action is a Full implementation-readiness packet and owner review. No source implementation is authorized by this proposal alone.
