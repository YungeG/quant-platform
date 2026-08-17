# P00-PLAT-01 Acceptance Receipt

- **Status:** PASSED
- **Accepted Platform revision:** `bb75f2d903111be55be23bcb2d730c8cdec3bf3a`
- **Accepted Backtest revision:** `9e5937895d7559b8537a4595d73b6aabc94f6f13`
- **Acceptance environment:** fresh clone at `/tmp/platform-p00-plat-clean`
- **Pre-validation status:** clean
- **Post-validation status:** clean

## Submodule closure

| Module | Revision |
| --- | --- |
| Backtest | `9e5937895d7559b8537a4595d73b6aabc94f6f13` |
| Foundation | `3b18b5bd9a9a13eaaa5bb40a69aade8215fa155a` |
| Promotion Gate | `97a11dc8d781e43a16b268b52832e9ea7034cc74` |
| Research Platform | `eaea195addf514586de71dac5ca7ff24df251c4c` |
| Strategy Validation | `168698ddfff4cb21d527dc1f370a04c4aac6e763` |

## Workspace hashes

| Artifact | SHA-256 |
| --- | --- |
| `pyproject.toml` | `8eb23bf50135257476e49e3795ebe4b8acb33ba17957cf45dc32262db426ad78` |
| `uv.lock` | `7dfc93cbd2f3f9993782142bed47e54151f620b04fad0a6599aef90dffdefb81` |
| `foundation/pyproject.toml` | `c0fcd145b7d7973605c8aa99e47e4f2e545063c7f4b20e4bd6a8fe9d5fde67b2` |
| `research-platform/pyproject.toml` | `85195a37500e75d095086e27ccdc5661cb46c1f110eea69cf0380cb814ae96df` |
| `strategy-validation/pyproject.toml` | `aa6d0cda8cf8d437bca6cb9d0187661bb44a8efd784f9228b38a624aeaabfc5e` |
| `promotion-gate/pyproject.toml` | `1badff14d2ffb087715b56bd6a919000180c33f3c3b53f2d26c5be0b752c3d6b` |
| Domain package descriptor | `6552f027631013c41073f394a3ac8c16326fe56f27313bcc864074255682f734` |
| Market Data package descriptor | `8e63e9a1ea212c3003da3a6e48776f76800d088915a100ae517251cbbe4980cb` |
| Trading package descriptor | `68dedd449a9aeb56c9fd547d675cd3029c7a4102af13ac000645913515e5acf2` |
| Backtest package descriptor | `2d8c0ffbc581ae4e8e75f974f6f4c3d897ca7f24620a8a8955568073f1749e5b` |
| Bundle Builder package descriptor | `ebde64b75bf939308ae2c010d8218df9b322d6c48e5260e6202b981beca97e7a` |

## Executed acceptance

```bash
git clone --no-local --no-hardlinks . /tmp/platform-p00-plat-clean
git -C /tmp/platform-p00-plat-clean submodule update --init --recursive
test -z "$(git status --porcelain)"
uv lock --check
uv sync --all-packages --locked
uv run --locked python -c 'import crypto_quant_domain, crypto_quant_market_data, crypto_quant_trading, crypto_quant_backtest, crypto_quant_bundle_builder, crypto_quant_foundation, crypto_quant_research, crypto_quant_validation, crypto_quant_promotion'
uv run --locked pytest -q -p no:cacheprovider --import-mode=importlib foundation/tests research-platform/tests strategy-validation/tests promotion-gate/tests tests/architecture
test -z "$(git status --porcelain)"
```

Results:

- all five Backtest packages resolved from immutable Git SHA `9e5937895d7559b8537a4595d73b6aabc94f6f13`;
- all four Platform packages built from their exact submodule revisions;
- nine public-root imports passed;
- `248 passed`;
- no leaf `uv.lock`, `PYTHONPATH`, external editable/path dependency, retained virtual environment, or cache was used as acceptance evidence;
- the maintainer Backtest worktree was not used as acceptance evidence.

## Scope boundary

This receipt closes `P00-PLAT-01` package/workspace acceptance only. It does not close `P00-BTA-01` or `P00-SEAM-01`: the Backtest provider preparation/request-registration seam remains externally blocked, and no fixture-backed run is promoted to a real provider receipt.
