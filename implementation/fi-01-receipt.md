# FI-01 Whole-Platform Acceptance Receipt

- **Status:** PASSED
- **Accepted Platform revision:** `c525cb522b5a869565a7261f42d5592144cb5e63`
- **Backtest dependency source revision:** `e3c04fb612d6798aef1420b60864d4f315ed12ac`
- **Backtest acceptance-record checkout:** `92810375fdf6c0c48c1edaeade74b97755f20220`
- **Foundation revision:** `9d88ed67a84d06c558276f8bae2206b069bcec8f`
- **Research revision:** `330aa4539f6ddbb874e7f29f9125d075037c732f`
- **Validation revision:** `692f6ca1a471ec7ccf7e284a4a71ed30652b3661`
- **Promotion revision:** `8a893f2439c77fdb83d7a70e75fee37dd63eb3ef`
- **Acceptance environment:** fresh clone at `/tmp/platform-fi-clean`
- **Pre/post validation status:** clean

## Accepted inputs

- [`P00-SEAM-01`](p00-seam-01-receipt.md)
- [`PLAT-ADM-01`](plat-adm-01-receipt.md)
- [`RP-THIN-02`](rp-thin-02-receipt.md)
- [`SV-THIN-01`](sv-thin-01-receipt.md)
- [`PG-THIN-01`](pg-thin-01-receipt.md)

## Whole-Platform golden

The accepted chain is one Foundation-backed provenance graph:

```text
4 real Research Trials / 8 tasks
→ 3 COMPLETED + 1 durable BLOCKED
→ selected StrategyCandidate
→ real adverse OOS analysis (-0.1, trade_count 1)
→ ValidationReport(result = rejected)
→ first admissions for publication, analysis, and metric profile
→ PromotionEvaluation(NEEDS_MORE_EVIDENCE)
→ PromotionDecision(needs_more_evidence)
```

Every module ref resolves through the preceding module's published artifact. The selected Backtest publication and analysis resolve through `BacktestEvidenceRepository`; their admissions retain their first `LogEntryRef`. The Validation Plan binds the same snapshot used by its sample-integrity assessment. Promotion status closure reaches the selected publication, analysis, rejected report, and governed Research/Validation graph. Replaying Research, Validation, admission, and Promotion returns identical semantic refs with five total provider runs, unchanged Attempt files, three admission entries, and no refreshed freshness.

## Golden refs

| Artifact | Content hash |
| --- | --- |
| StrategyCandidate | `sha256:e3f9ab21cacf0abe908fd5ab810772259efd4a6d7248d3dd3e826bf796463777` |
| CandidateFamily | `sha256:6f7218cd9d4e42cc7bfdea1bb4f8e9aad819215eace10d78a7bae29b5a6bba7a` |
| ExperimentExecutionManifest | `sha256:5e650ed823984e0ca79b77f20592982cb7f8f012242e6dfcf98e2847ac592550` |
| selected Backtest publication | `sha256:81c99e8e275a2a6a6de3010d28a82b74bcc7900c298b28ea0c84cb9068197a85` |
| selected Backtest analysis | `sha256:bb66c7b36661886d47e1a6fa1ad5ffeea459fa557a5b26cd8801c2d44db638c7` |
| metric profile | `sha256:bced4dbef8bbf6e1ec9821ae3b68e8c6ce2bbed953f95fe1214c8e21676dbd6a` |
| ValidationPlan | `sha256:0e71123e72b731105f3eb053a7dfa927c6da1811478a1974b80602a1c5d001c4` |
| ValidationReport | `sha256:590e7a735b7d5483d0b9433aea92af0f419745637d4768f030869b4ce548bf18` |
| PromotionCase | `sha256:025f874242e1a5b20fee9dec5223c819bf0d93712e5770c569bab4812be19c6b` |
| Promotion status snapshot | `sha256:5d94f5bb0de1363665eb43bda39ce6508c2de81a25e8e6b280766296d477b14d` |
| PromotionEvaluation | `sha256:b32fccbe4848bc9f795e8e299f3c47b8dc6aee62dc09bb6f380a9e4b6b6a2ef5` |
| PromotionDecision | `sha256:58d9291757f3d49971b111b2fc048994bc339dd7c2c58c0eb0952772775b2bca` |

## Release acceptance

```bash
uv lock --check
uv sync --all-packages --locked
uv run --locked pytest -q
uvx ruff check <changed integration and receipt-guard Python files>
```

Results: `280 passed`; targeted Ruff clean; nine public imports; protected P00 fixture hash passed; Markdown fence/link guards passed; Lens/Gitleaks reported no blocking or secret findings; zero Platform leaf locks; clean status before and after acceptance. Lens retained non-blocking cross-module duplication warnings because v1 deliberately keeps semantic ownership in each module rather than introducing a shared adapter/helper package.

## File hashes

| Artifact | SHA-256 |
| --- | --- |
| `pyproject.toml` | `7fc055fd6bdf50fb6fe09b1f0edf23ce899b687d0b26053a9d88b3fd7a972ac3` |
| `uv.lock` | `d96c6ebf36bbb9baf332e956be220c9d01bbb7d2010b82e9568d54ddcd6d39b6` |
| `tests/integration/test_integration_v1.py` | `cb6013243f73fd8fd1aef953260eb89de5eee3270244e51c5ac61380b7af44f2` |
| protected P00 fixture | `aebb1be1894d739b06856e012e4343d7835fc1ed0306d8c28a4bfb1d8025b782` |

## Deferred scope and residual limitation

No fifth adapter, database, queue, service, positive Promotion, Shadow, Live, credential, deployment, or decision supersession is included. Platform has no configured remote, so this receipt proves a clean local superproject revision plus remote-reachable submodule revisions; publishing the Platform superproject itself remains an administrative action outside Integration v1.
