# PLAT-ADM-01 Acceptance Receipt

- **Status:** PASSED
- **Accepted Platform revision:** `bb68146da4b188e4da114ff7adaaa594c47a49f7`
- **P00-SEAM input:** [`p00-seam-01-receipt.md`](p00-seam-01-receipt.md)
- **Backtest dependency source revision:** `e3c04fb612d6798aef1420b60864d4f315ed12ac`
- **Backtest acceptance-record checkout:** `92810375fdf6c0c48c1edaeade74b97755f20220`
- **Foundation revision:** `9d88ed67a84d06c558276f8bae2206b069bcec8f`
- **Acceptance environment:** fresh clone at `/tmp/platform-plat-adm-clean`
- **Pre/post validation status:** clean

## Accepted behavior

`admit_backtest_evidence()` verifies completed publications and analyses through the Backtest repository, verifies the fixed metric profile through Backtest publication authority, then stores and appends exactly one `backtest_evidence_admission@1` Envelope to `platform.backtest-evidence-admission.v1`.

The first Foundation-assigned `accepted_at` is immutable. Exact replay returns the first `LogEntryRef`; wrong subject kinds, forged refs, Backtest missing/tamper/retention failures, conflicting bytes, and wrong-owner-log publication fail closed. The payload contains only `subject_ref`; later Promotion status publication cannot refresh admission time.

## Acceptance

```bash
uv lock --check
uv sync --all-packages --locked
uv run --locked pytest -q -p no:cacheprovider --import-mode=importlib tests/integration/test_backtest_evidence_admission.py
uv run --locked pytest -q -p no:cacheprovider --import-mode=importlib foundation/tests research-platform/tests strategy-validation/tests promotion-gate/tests tests/architecture tests/integration
```

Results: focused `8 passed`; full Platform `266 passed`; clean status before and after validation.

## Hashes

| Artifact | SHA-256 |
| --- | --- |
| `uv.lock` | `d96c6ebf36bbb9baf332e956be220c9d01bbb7d2010b82e9568d54ddcd6d39b6` |
| `tests/support/backtest_evidence_admission.py` | `c1fc5ae645cefd11c301a4dff4f8c4f77c2692eeb026b7f04c1557ac70d2f92f` |
| `tests/integration/test_backtest_evidence_admission.py` | `3c4f1b4d138b5377bc37222c775b1b640da62053fb8e5d8f23aa0cf82e009a8e` |

This receipt closes `PLAT-ADM-01`. It does not produce Research, Validation, Promotion, or FI receipts.
