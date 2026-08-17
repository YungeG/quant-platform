# P00-BTA-01 Acceptance Receipt

- **Status:** PASSED
- **Accepted Platform revision:** `7aa76dc2de65fb713a146e27651538dd755d5231`
- **Accepted Backtest dependency source revision:** `e3c04fb612d6798aef1420b60864d4f315ed12ac`
- **Backtest acceptance-record checkout:** `92810375fdf6c0c48c1edaeade74b97755f20220` — documentation-only receipt whose parent is the source revision; not a dependency pin or second Platform receipt
- **Backtest package-code revision:** `a014e9389f36b6696653606c5ebcb845cabe9f24`
- **Foundation revision:** `9d88ed67a84d06c558276f8bae2206b069bcec8f`
- **Acceptance environment:** fresh clone at `/tmp/platform-p00-bta-clean`
- **Pre/post validation status:** clean

## Bound public roots

- `CashDevelopmentRequestIntent`
- `CashDevelopmentProviderInputs`
- `prepare_cash_development_backtest`
- `BacktestRequestRef`
- `PreparedBacktestExecution`
- `BacktestRuntime`
- `BacktestEvidenceRepository`
- `BacktestAnalysisRuntime`

Platform supplies only opaque Trial/Validation context and public provider facts. Backtest constructs and persists the request and v2 bundle, owns request/semantic-run/execution identities, and returns executable prepared authority without exposing resolved internals.

## Evidence

- real completed development run, replay-stable with no additional Attempt records;
- opaque context changes request ref and semantic-run identity;
- exact completed repository loading and completed-only analysis;
- adverse `simple_period_return = "-0.1"`, `trade_count = 1`, grade `development`;
- real durable `BLOCKED` and `CANCELLED` plus replay;
- Backtest-owned durable FAILED graph accepted at `e3c04fb612d6798aef1420b60864d4f315ed12ac`;
- execution-input not-found, retention, integrity, and substitution failures occur before Attempt creation;
- repository wrong-type, missing, tamper, retention, malformed-manifest, terminal-analysis, and valid-foreign-link rejection;
- public package roots only, with no Platform verifier, metric implementation, fifth adapter, or resolved Backtest object.

## Executed acceptance

```bash
git clone --no-local --no-hardlinks . /tmp/platform-p00-bta-clean
git -C /tmp/platform-p00-bta-clean submodule update --init --recursive
uv lock --check
uv sync --all-packages --locked
uv run --locked pytest -q -p no:cacheprovider --import-mode=importlib foundation/tests research-platform/tests strategy-validation/tests promotion-gate/tests tests/architecture tests/integration
```

Results: nine public imports passed; `257 passed`; clean status before and after validation.

## Hashes

| Artifact | SHA-256 |
| --- | --- |
| `pyproject.toml` | `cd3ce8cb653e8ba11ff4a24cd26d216a87e6a220197eb338d2daa64e7ba989bb` |
| `uv.lock` | `d96c6ebf36bbb9baf332e956be220c9d01bbb7d2010b82e9568d54ddcd6d39b6` |
| `tests/integration/test_backtest_public_binding.py` | `65748e030e3118cb82a968c809f3019144289c3a623a42e93e040392c4b76795` |

This is the canonical Platform receipt for `P00-BTA-01`; the Backtest gitlink records its separate acceptance record. Platform governance admission and module thin receipts remain separate nodes.
