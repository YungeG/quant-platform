# TSR-FI-01 target-stream Research fan-in acceptance receipt

- **Platform parent revision:** `698a8bb349a750a1c7e0b7846d0a794f4ce00308`
- **Backtest revision:** `f73d068d24ffb7ecc0b7d78194fcbc96908d3c04`
- **Research revision:** `c06662449a8a13aed5824398b96bd21e889a9fee`
- **Validation revision:** `dad119842737fd06137914537fcc51df12996353`
- **Promotion revision:** `8e6dddf5da0494b57cca6990d5024fe4198e6b44`
- **Root `pyproject.toml` SHA-256:** `450328a2eea02f9fb14e36c096b9d27c25df4c8194553ff4903983d97b72c4f2`
- **Root `uv.lock` SHA-256:** `e72bad448708f7075ee8205ba90452db469306a099c010810496b422f75dceb9`
- **Status:** ACCEPTED

## Golden evidence

The root golden composes only public package roots and Backtest-owned target repository, cash preparation, execution, completed evidence, and analysis authority:

```text
fixed development cash target stream
→ StrategyCandidate@3 + exact discovery TargetMaterializationEvidence@1
→ independently materialized equal-valued OOS target with a distinct context-bound ref
→ ValidationReport@2(supported)
→ Promotion fail-closed for Candidate@3 and Report@2
```

Discovery and OOS evidence bind the exact recipe/task or case, materializer request hash, input-data hash, target digest, one event, development grade, `simple_period_return = -0.1`, and `trade_count = 1`. Replay returns identical Candidate and Report refs, adds only the required exact target-CAS loads, and performs no second materializer read/materialization, preparation, economic run, analysis derivation, sample append, or governance publication.

## Dependency closure

Exactly three gitlinks are advanced. All five Backtest VCS pins and every corresponding `uv.lock` source/metadata coordinate resolve to `f73d068d24ffb7ecc0b7d78194fcbc96908d3c04`; superseded Backtest revision `8de544e7794ee05b652355c9809b5454d7ace494` is absent from `pyproject.toml` and `uv.lock`.

## Verification

- focused v6 golden: `2 passed`;
- root architecture suite: `51 passed`;
- root integration suite: `36 passed`;
- Research target/public suites: `41 passed`;
- Validation target/public suites: `57 passed`;
- Backtest target-stream/public-boundary suites: `29 passed`;
- full root workspace: `464 passed`;
- `uv lock --check`, public imports, compileall, Ruff `E4,E7,E9,F,I`, and diff/pin/hash guards: passed.

## Exclusions

No leaf source was edited. This fan-in adds no Promotion support, decision-grade target execution, market qualification, model combination, Shadow/Live/deployment authority, service, queue, database, credentials, or orders.
