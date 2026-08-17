# PG-THIN-01 Acceptance Receipt

- **Status:** PASSED
- **Accepted Platform revision:** `d47ce3203f2e45d2369ae31e30b43c52733ac628`
- **Promotion revision:** `8a893f2439c77fdb83d7a70e75fee37dd63eb3ef`
- **SV-THIN input:** [`sv-thin-01-receipt.md`](sv-thin-01-receipt.md)
- **PLAT-ADM input:** [`plat-adm-01-receipt.md`](plat-adm-01-receipt.md)
- **Acceptance environment:** fresh clone at `/tmp/platform-pg-thin-clean`
- **Pre/post validation status:** clean

## Accepted behavior

The unchanged Promotion shell resolves the actual rejected SV-THIN ValidationReport graph and exact Research closure. The selected completed publication, analysis, and metric profile use their real first Platform admission entries; replaying those admissions returns the same `LogEntryRef` and cannot refresh governance time.

The integrated case publishes exact status and independent review checkpoints, then deterministically emits `NEEDS_MORE_EVIDENCE / needs_more_evidence` under the negative-only v1 policy. Exact replay publishes no second status, review, evaluation, or decision. Structural acceptance confirms no positive, Shadow, Live, credential, deployment, or supersession surface.

## Acceptance

```bash
uv lock --check
uv sync --all-packages --locked
uv run --locked pytest -q -p no:cacheprovider --import-mode=importlib promotion-gate/tests/test_promotion_shell.py promotion-gate/tests/test_integrated_promotion.py
uv run --locked pytest -q -p no:cacheprovider --import-mode=importlib foundation/tests research-platform/tests strategy-validation/tests promotion-gate/tests tests/architecture tests/integration
```

Results: focused `14 passed`; full Platform `278 passed`; clean status before and after validation.

## Hashes

| Artifact | SHA-256 |
| --- | --- |
| `uv.lock` | `d96c6ebf36bbb9baf332e956be220c9d01bbb7d2010b82e9568d54ddcd6d39b6` |
| `promotion-gate/tests/test_integrated_promotion.py` | `13819db1b21b47633cc3c8a3c72c223d32410c967c44f9e4b1520f02ee0de75a` |

This receipt closes `PG-THIN-01`. The whole-Platform `FI-01` receipt remains downstream.
