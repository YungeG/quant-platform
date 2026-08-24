# V5-PIN-01 Backtest compatibility pin acceptance receipt

- **Platform implementation revision:** `6e82e4dc1187752f021097e9d21aaa7cf7e3c96e`
- **Backtest fan-in revision:** `8de544e7794ee05b652355c9809b5454d7ace494`
- **Model-seam ancestor:** `033344172b24847e73941bb97a06da0490527edf`
- **Durable-proof ancestor:** `cebb9b033b7eeffbbff712715fc017708ac5a247`
- **Root `uv.lock` SHA-256:** `75a91665859490d03544066d0585bceec9b6dbe7156cf322b4cb67f95a6a420f`
- **Status:** ACCEPTED

## Accepted pin closure

The Platform gitlink and every Backtest-owned root package source resolve the same immutable compatibility fan-in revision. The fan-in is a descendant of both accepted capability lines and exposes together:

```python
from crypto_quant_backtest import (
    AnalysisArtifactRefV2,
    BacktestCanonicalPublicationRefV2,
    VerifiedCompletedPublicationV3,
    prepare_model_bound_cash_development_backtest,
)
```

No mixed Backtest revision, editable/path override, nominal-ref shim, or Platform proof implementation is used.

## Verification

- independent Backtest full suite: `2438 passed`;
- local Platform Research suite against the fan-in: `90 passed`;
- local clean-clone Research + V2/V5 architecture gate: `103 passed`;
- fresh remote recursive clone at the exact Platform revision: `103 passed`;
- local and remote `uv lock --check`: passed;
- public import smoke: passed locally and in the remote clone;
- remote clone checked out exact Backtest gitlink and ended with empty `git status --short`;
- all five Backtest-owned package sources and the gitlink use the same SHA.

## Exclusions

This receipt accepts package/version compatibility only. It does not accept Admission@2, Research V2 dispatch, decision-grade Validation, Promotion governance, provider qualification, proof decoding, Shadow implementation, Live/deployment, or any new Backtest change.
