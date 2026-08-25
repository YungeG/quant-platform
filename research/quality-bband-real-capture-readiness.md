# Quality + B-Band real financial capture readiness

- **Status:** `CAPTURE_AND_NORMALIZATION_SUCCEEDED / PRESENTATION_AND_FORMULA_AUTHORITY_BLOCKED`
- **Checked:** 2026-08-25
- **Scope:** first credentialed QB-FIN-SENTINEL-02 capture, fixed declarations and source-bounded normalization candidate

## Repository state

| Gate | Observed state | Decision |
| --- | --- | --- |
| Backtest PR #1 | <https://github.com/YungeG/quant-backtest/pull/1>, open, mergeable | not accepted |
| Backtest PR #2 | <https://github.com/YungeG/quant-backtest/pull/2>, open stacked on PR #1 | proxy correction pushed at `146cd227b2fc707726e133dbbd08cde356f21dcd`; not accepted |
| Backtest PR #3 | <https://github.com/YungeG/quant-backtest/pull/3>, open stacked on PR #2 | declaration commit `b4124d5985a6f9cbd39221fd55286abf5608b6b8`; not accepted |
| Backtest PR #4 | <https://github.com/YungeG/quant-backtest/pull/4>, open stacked on PR #3 | normalization commit `fa58e68d7b51ee5517e5a14c87c3590d1bda2976`; not accepted |
| Platform research PR | <https://github.com/YungeG/quant-platform/pull/1>, open, mergeable | not accepted |
| v1 commit | `e7e874fc58e0911b7df1cd0463387526afcb845d` | remotely reachable |
| v2 commits | `23f2fbdfd2a95a66513097b9ab1c2ba66cfe0a52` + `146cd227b2fc707726e133dbbd08cde356f21dcd` | remotely reachable |

## Credential and transport

The user authorized the protected file `/home/ygguo/.config/ai-crypt/xiaodefa-token` for use as `TUSHARE_PROXY_TOKEN`. The file is owner-only mode `0600`; its value was never printed, logged, committed or copied into evidence.

A direct-Tushare attempt failed atomically with `PROVIDER_RESPONSE_INVALID` because the authorized credential is an approved xiaodefa proxy key, not a direct Tushare token. No output directory was created by that failed attempt.

A minimal probe through the existing approved proxy seam returned a valid Tushare code-zero envelope. QB-FIN-SENTINEL-02 was corrected to use:

- proxy key `xiaodefa.approved-tushare-proxy.v1`;
- endpoint `https://fast.xiaodefa.cn`;
- exact 56-character `TUSHARE_PROXY_TOKEN` validation;
- credential-free request body;
- `x-api-key` header only.

## Successful real capture

Output root:

```text
/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/
  source-snapshots/000651.SZ/20231231/v2-candidate-01
```

Evidence identity:

| Value | Identity |
| --- | --- |
| SourceSnapshot | `sha256:dec0abb1828f8b87256347e72b6ccfe2f84a2ca13f36aa1415c9a53e96a0c7d5` |
| Content tree | `sha256:d7e92674dd42a4eeabfde354922cfafa9d50837f2076c1ad88233da8c0456b13` |
| Provenance | `sha256:0fcef32df8c6b41ef0ce55121adc9c392cf483ca71134dc27175f6c9512cab17` |
| Members | `5` |
| Annual report | `3911496` bytes / `sha256:32ebc475a2291ce4f1b5c1a9f9da55227e03192f07e75041e976c29d213ec8aa` |
| Confirmation | `302155` bytes / `sha256:a78a67865a7ea989c4fd8b053fad1aa75f36d22c10d14387800ff16b698dbc60` |
| Grade/deployment | `false` / `false` |

The snapshot was rebuilt from persisted members and exact provenance, then passed `verify_source_snapshot()`. All persisted files are mode `0600`; credential scan was clean.

## Row observations

- Income: one `report_type=1` row; all expanded requested fields non-null.
- Balance sheet: two `report_type=1` rows. Economic fields are identical; only `update_flag` differs (`0` versus `1`). Raw rows remain retained.
- Cash flow: one `report_type=1` row.

Raw nulls remain evidence:

- balance: `bond_payable`, `st_bonds_payable` are null in the provider rows and resolve to exact declared `0.00` values only under declaration `sha256:59e09eb542a6e2ec480a7b8ed322d9ae9106416460f0999216fd5564f7278007`;
- cash flow: `use_right_asset_dep`, `lt_amort_deferred_exp` remain null; the declaration proves right-of-use depreciation is already included and adds no duplicate amount.

## Published normalized candidate

```text
/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/
  normalized-observation-sets/000651.SZ/20231231/v1-candidate-01
```

| Value | Identity |
| --- | --- |
| Observation set | `sha256:632206f85bcff71dbcccfd20a3593e14fb895b33bd138ac25bbf9b947e4a4a7c` |
| Canonical file | `sha256:857a57058d790f83b8d227e6afb676b13d2f3ab2a784b132e3c1bc7486468ef0` |
| Income revision | `sha256:8957590f45f32ed9b285e940f2fa0c0524cb28377e86c745ab39aa3875ba63e8` |
| Balance revision | `sha256:3e64ee623ca3676f1ec10daf56588dceabdd77a41ba0419d4c9010241313f45d` |
| Cash-flow revision | `sha256:71f4428e79d3bd7638cc9c1d98c1471f9802e9a90d25f7fa06b739bc57f0f986` |
| Grade/deployment | `false` / `false` |

Canonical readback, repeated normalization and credential-exclusion checks passed. This is still one issuer/one period, source-bounded and revision-closure-incomplete.

## Next executable gates

1. accept stacked PRs #1–#4;
2. run point-in-time presentation selection over the normalized revisions;
3. expand to six annual balance endpoints and five coherent annual statement trios;
4. only then calculate multi-year source-bounded formula inputs.

The current capture grants no MarketBundle, Strategy, Validation, Live or deployment authority.
