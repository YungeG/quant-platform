# Quality + B-Band real financial capture readiness

- **Status:** `BLOCKED / CREDENTIAL_AND_REPOSITORY_ACCEPTANCE_REQUIRED`
- **Checked:** 2026-08-25
- **Scope:** first credentialed QB-FIN-SENTINEL-02 capture only

## Current evidence

| Gate | Observed state | Decision |
| --- | --- | --- |
| PR #1 | <https://github.com/YungeG/quant-backtest/pull/1>, open, mergeable, no review/check decision | not accepted |
| PR #2 | <https://github.com/YungeG/quant-backtest/pull/2>, open stacked on PR #1, mergeable, no review/check decision | not accepted |
| v1 commit | `e7e874fc58e0911b7df1cd0463387526afcb845d` | remotely reachable |
| v2 commit | `23f2fbdfd2a95a66513097b9ab1c2ba66cfe0a52` | remotely reachable |
| `TUSHARE_TOKEN` | absent from current process environment | credentialed capture impossible |
| Artifact parent | `/srv/bcache-8t/ygguo/quant/artifacts` exists | candidate parent only |
| Proposed strategy subroot | `/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband` absent | not approved/created |
| Storage | `/srv/bcache-8t` has approximately 5.5 TiB free | capacity is not the blocker |

No credential value was read, logged or searched for.

## Required decisions

Before real capture:

1. Backtest owner accepts PR #1 and stacked PR #2, or explicitly permits executing the unmerged exact v2 commit as candidate evidence.
2. User provides `TUSHARE_TOKEN` through the process environment and explicitly authorizes its use by QB-FIN-SENTINEL-02.
3. User/owner approves one no-clobber output root, recommended:

```text
/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/
  source-snapshots/000651.SZ/20231231/v2-candidate-01
```

4. The capture remains source-bounded and non-decision-grade; it grants no Builder/Strategy/Live authority.

## Hard boundary

Without a token, Backtest cannot call the documented Tushare statement interfaces. CNINFO PDFs alone cannot provide the structured raw line items required by the frozen formula-input contract. Local DuckDB/Parquet or provider-ratio substitutions remain forbidden as Platform evidence.

The next executable action is credentialed five-member SourceSnapshot capture after the three approvals above. Until then, formal Quality + B-Band financial data preparation is blocked.
