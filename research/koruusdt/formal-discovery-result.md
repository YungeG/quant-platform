# KORUUSDT Formal Discovery Result

- Experiment: `rp-core:experiment_spec@1:sha256:121bed61e4b17c3fbd50b14eb3eff5ac73542b6f68710cdfdd7c1f9aef27572d`
- Execution manifest: `sha256:0ba345e469eeee66b10ddc7b8cb3237c64f985a1fdf90a1fed080c96b5b43919`
- Candidate family: `sha256:d59c94602bd943d7f05e5c3176aa1bd5f70ad8ed66c9fd16cd48b983ebf7d518`
- Selection: `NO_ELIGIBLE_TRIAL`
- Summary manifest: `sha256:f9edac999e69a061c64b0e57b5edeefdfd48ecb04aadfb0ce3cdfb04664e7977`
- Holdout touched: `false`

| Arm | Simple return | Trades | Completed publication | Analysis |
|---|---:|---:|---|---|
| p01 | -0.003392766564 | 8 | `sha256:c8ffee22fac10752acd982f0be259a89b6f8613232f281bb0f8b563021882c5c` | `sha256:546aa4926315262e22c39f292e744d8f07fa79dd4963a4e4cc2fc2a011aa9552` |
| p02 | -0.004869892632 | 8 | `sha256:a9b6bdf17b0286cb7570f0be0508460a41c2739221784408183833192a0867a9` | `sha256:c3d95b0a7ff5dec2c410c38eeb4bef680ddcf692f32821f6f032c2392c9d20ba` |
| p03 | -0.003583165601 | 12 | `sha256:49d61863a40ecc488a2d70b34cc84e49a1344da1c4bb979704766cac8741a9fd` | `sha256:f3d8fa0202d35b8a18d2fb0254d0692a4efc86fb7ce611ee3fb1640804c1cbdf` |
| p04 | -0.004005330452 | 12 | `sha256:55a4f1fd06a0f5ada2bf310382051c7215caf59198f676c9567ad7b43574852d` | `sha256:d87c23971693f31e6a02b8af86424adde8e5b28a066801bdd9d4efd0cbed8f86` |
| p05 | -0.000867107615 | 6 | `sha256:3275da5734b4902be4657e3389f3de1d7db7ff4a1ee865889dc93dba5c1b7592` | `sha256:05ea3b60ad9af9c686b823764f887906da370d10d0873806857192945a755e73` |
| p06 | -0.001444316497 | 6 | `sha256:46aeacf1b24c40697a3a275a62f204d73214ee9bf829a65216af1f6fc34606ea` | `sha256:4dee61e311d190a4469a904afc587b3bae61350902755358a466db15fecc5881` |
| p07 | -0.002889771606 | 12 | `sha256:1be032aa5500053a4eba2c814bf884f9d19f0a2b4f1f72636be7bd155ccf6319` | `sha256:fa4ca8f6ebb32bb7432d8602395865594c49a578f2dfd56d89ad5215f96f5cd7` |
| p08 | -0.002412019271 | 12 | `sha256:f855f9eebef95b5df36e013fa72c3c35fbaea0fa75301c75731995bb55993caf` | `sha256:0436f236f84b258d4fa18cffb4389f36a5a17a0c92bcb8415bb311a93b178ffe` |

All eight trials and analyses completed. Every simple return was negative, so the predeclared positive-return filter produced no `StrategyCandidate`.

## Diagnostic cost decomposition

The prior local report provides the Backtest-owned realized PnL, fees, and funding decomposition for the same exact executions:

| Arm | Realized PnL (USDT) | Fees (USDT) | Funding (USDT) |
|---|---:|---:|---:|
| p01 | -29.93247 | 3.99519564 | 0 |
| p02 | -44.71112 | 3.98780632 | 0 |
| p03 | -29.82957 | 6.00208601 | 0 |
| p04 | -34.06388 | 5.98942452 | 0 |
| p05 | -5.68018 | 2.99089615 | 0 |
| p06 | -11.74376 | 2.98786436 | 0.28845939 |
| p07 | -22.94112 | 5.95659606 | 0 |
| p08 | -18.46036 | 5.94829210 | 0.28845939 |

Every arm loses before fees; funding is negligible. Removing execution costs would not make any arm profitable. The rejected result therefore reflects a negative strategy edge in this discovery window, not merely fee or funding drag. Do not widen the parameter search or consume the holdout for this hypothesis.

This document summarizes formal Research evidence. The underlying gitignored evidence tree must be retained for verification.
