# Early-reporter peer-diffusion fallback retry

## Outcome

**Verdict: NO-GO**
**trade_authorized: false**

The requested per-symbol price optimization is implemented and preserves the frozen thresholds, PIT rules, T+1 entry, 20-session horizon, costs, missing-data behavior, and separate stock/ETF arms. The bounded same-path smoke passed. The full study through 2026-08-28 was stopped at the required 600-second ceiling before producing metrics.

## Findings

1. **blocker — `experiments/run_early_reporting_peer_diffusion.py:58`: full study cannot complete within the execution ceiling.** `build_signals` repeatedly filters all 245,404 first-announcement rows for every announcement-day/report-period and active industry through `events.Symbol.isin(symbols)`. Data loading completed in 0.97 seconds; a 60-second stack dump remained in pandas/pyarrow `isin` at this line. The smallest next step is to pre-index events by report period and symbol so each loop scans only the relevant period subset, without changing signal ordering or thresholds.
2. **resolved performance issue — `experiments/run_early_reporting_peer_diffusion.py:103-164`: repeated full price-frame filtering.** Stock and ETF price histories are grouped and date-indexed once. The same synthetic stock-arm profile improved from 1.537 seconds / 1,984,191 calls to 0.305 seconds / 555,074 calls (about 5.0x faster) while the focused return-semantics test passed.
3. **execution fix — `experiments/run_early_reporting_peer_diffusion.py:7-12`: runtime source discovery.** The script now follows existing experiment convention by adding the local `quant-claude` source root before importing `factormine`; the first smoke attempt failed clearly with `ModuleNotFoundError`, and the rerun passed after this fix.

## Metrics

### Representative bounded smoke

| Arm | Signals | Complete | Exact mean/median 20d return | Win rate | Other |
| --- | ---: | ---: | ---: | ---: | --- |
| Unreported peer stocks | 1 | 1 | -0.03302163259218811 | 0.0 | 7 eligible peers; 2 priced |
| Direct industry ETF | 1 | 1 | -0.05836590198123038 | 0.0 | ETF `159662.SZ` |

Signal date was 2024-08-01, T+1 entry was 2024-08-02, and panel version was `e9ef44a4ef6b0e45`.

### Full study and explicit 2025 holdout

Full stock metrics: **unavailable (`null`)**.
Full ETF metrics: **unavailable (`null`)**.
2025 stock holdout metrics: **unavailable (`null`)**.
2025 ETF holdout metrics: **unavailable (`null`)**.

No full-study metric is inferred from the smoke. Missing full and holdout evidence forces NO-GO and leaves trading unauthorized.

## Changed files

- `experiments/run_early_reporting_peer_diffusion.py`
- `tests/research/test_early_reporting_peer_diffusion.py`
- `overall/a-share-early-reporting-peer-diffusion-v1-design.md`
- `overall/a-share-early-reporting-peer-diffusion-v1-result.json`
- `overall/a-share-early-reporting-peer-diffusion-v1-smoke-evidence.csv`
- `overall/a-share-early-reporting-peer-diffusion-v1-conclusion.md`
- `early-reporter-fallback-retry.md`

## Tests added or updated

- `tests/research/test_early_reporting_peer_diffusion.py`: frozen early-peer signal test plus T+1/cost/missing-peer return test for the indexed price path.

## Commands and validation

- `uv run --project /home/ygguo/agent-projs/quant-claude --with pytest pytest -q tests/research/test_early_reporting_peer_diffusion.py` — **passed: 2 tests**.
- `uv run --project /home/ygguo/agent-projs/quant-claude python -m py_compile experiments/run_early_reporting_peer_diffusion.py tests/research/test_early_reporting_peer_diffusion.py` — **passed**.
- Bounded smoke through `experiments/run_early_reporting_peer_diffusion.py` with real panel/ETF data and a 10-member synthetic announcement fixture — **passed**, emitted stock CSV, ETF CSV, signals CSV, and parseable JSON with `trade_authorized=false`.
- Full run through 2026-08-28 with default PIT announcements and SW members — **failed safely: exit 124 after 600 seconds**, no result claimed.
- 60-second `faulthandler` diagnostic — **identified `build_signals` at line 58** after loading 245,404 announcements and 5,897 member rows in 0.97 seconds.
- `python -m json.tool overall/a-share-early-reporting-peer-diffusion-v1-result.json` and CSV assertions — **passed**.
- `git diff --check` / cached diff check — **passed**.
- Final git status — **no staged files**.

## Diff summary

Adds the frozen v1 study and focused tests from the saved patch, replaces per-call full price DataFrame scans with one per-symbol indexed mapping for both arms, records `trade_authorized=false`, and adds versioned design, blocked-result, smoke evidence, and NO-GO conclusion artifacts. Thresholds were not tuned.

## Residual risks

- Full and 2025 holdout metrics remain unavailable until the independent `build_signals` scan bottleneck is mechanically indexed.
- The bounded smoke uses a synthetic announcement fixture to exercise real price and ETF execution; it is not efficacy evidence.
- No push or merge was performed.

## Commit

Isolated commit subject: `research: optimize early-reporting price lookup`. The exact commit hash is returned by the final acceptance response after committing this report.

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "Implemented one-time per-symbol indexed stock and ETF price mappings in experiments/run_early_reporting_peer_diffusion.py without changing frozen thresholds or execution semantics."
    },
    {
      "id": "criterion-2",
      "status": "satisfied",
      "evidence": "Versioned design/result/CSV/conclusion artifacts, exact smoke metrics, timeout evidence, stack-trace bottleneck, tests, validation, changed files, and residual risks are recorded in this report."
    }
  ],
  "changedFiles": [
    "experiments/run_early_reporting_peer_diffusion.py",
    "tests/research/test_early_reporting_peer_diffusion.py",
    "overall/a-share-early-reporting-peer-diffusion-v1-design.md",
    "overall/a-share-early-reporting-peer-diffusion-v1-result.json",
    "overall/a-share-early-reporting-peer-diffusion-v1-smoke-evidence.csv",
    "overall/a-share-early-reporting-peer-diffusion-v1-conclusion.md",
    "early-reporter-fallback-retry.md"
  ],
  "testsAddedOrUpdated": [
    "tests/research/test_early_reporting_peer_diffusion.py"
  ],
  "commandsRun": [
    {
      "command": "uv run --project /home/ygguo/agent-projs/quant-claude --with pytest pytest -q tests/research/test_early_reporting_peer_diffusion.py",
      "result": "passed",
      "summary": "2 passed in 0.23s"
    },
    {
      "command": "bounded smoke via experiments/run_early_reporting_peer_diffusion.py --end 2024-09-30",
      "result": "passed",
      "summary": "One complete event per arm; JSON/CSV outputs emitted; trade_authorized=false"
    },
    {
      "command": "timeout 600 full study via experiments/run_early_reporting_peer_diffusion.py --end 2026-08-28",
      "result": "failed",
      "summary": "Stopped with exit 124 at 600 seconds before metrics"
    },
    {
      "command": "60-second faulthandler build_signals diagnostic",
      "result": "passed",
      "summary": "Located repeated full announcement-frame isin scan at line 58"
    },
    {
      "command": "python compile, JSON parse, CSV assertions, and git diff checks",
      "result": "passed",
      "summary": "Compilation and artifact integrity checks passed"
    }
  ],
  "validationOutput": [
    "Focused tests: 2 passed in 0.23s",
    "Profile: 1.537s before versus 0.305s after on the same synthetic stock workload",
    "Smoke stock return: -0.03302163259218811; ETF return: -0.05836590198123038",
    "JSON valid; CSV rows=2; trade_authorized=false; blocked full metrics explicit",
    "Full run stopped at the 600-second guard; no fabricated full or 2025 metrics"
  ],
  "residualRisks": [
    "blocker: experiments/run_early_reporting_peer_diffusion.py:58 repeatedly scans all announcements inside build_signals; full and 2025 metrics remain unavailable",
    "Bounded smoke is execution evidence, not efficacy evidence"
  ],
  "noStagedFiles": true,
  "diffSummary": "Adds the frozen study and tests, pre-indexes stock/ETF prices once per symbol, and records versioned blocked-run evidence and NO-GO conclusion.",
  "reviewFindings": [
    "blocker: experiments/run_early_reporting_peer_diffusion.py:58 - repeated full announcement-frame filtering prevents the full study from completing within 10 minutes",
    "no blocker in the requested price-index optimization; focused semantics test and bounded smoke passed"
  ],
  "manualNotes": "No push or merge. Full and 2025 metrics are intentionally null rather than inferred."
}
```
