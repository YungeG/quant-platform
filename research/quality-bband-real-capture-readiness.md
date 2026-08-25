# Quality + B-Band real financial capture readiness

- **Status:** `HISTORICAL_CALENDAR_EVIDENCE_FROZEN / 2021_DEBT_SCOPE_INCOMPLETE / FORMULA_AUTHORITY_BLOCKED`
- **Checked:** 2026-08-26
- **Scope:** 000651.SZ 2018–2023 source/declaration candidates plus fixed 2023 normalization/selection and finite SZSE Calendar/Session evidence

## Repository state

| Gate | Observed state | Decision |
| --- | --- | --- |
| Backtest PR #1 | <https://github.com/YungeG/quant-backtest/pull/1>, open, mergeable | not accepted |
| Backtest PR #2 | <https://github.com/YungeG/quant-backtest/pull/2>, open stacked on PR #1 | proxy correction pushed at `146cd227b2fc707726e133dbbd08cde356f21dcd`; not accepted |
| Backtest PR #3 | <https://github.com/YungeG/quant-backtest/pull/3>, open stacked on PR #2 | declaration commit `b4124d5985a6f9cbd39221fd55286abf5608b6b8`; not accepted |
| Backtest PR #4 | <https://github.com/YungeG/quant-backtest/pull/4>, open stacked on PR #3 | normalization commit `fa58e68d7b51ee5517e5a14c87c3590d1bda2976`; not accepted |
| Backtest PR #5 | <https://github.com/YungeG/quant-backtest/pull/5>, open stacked on PR #4 | fixed trio-selection commit `5338d8046fa0f304d4a9590989c59ceffb51270b`; not accepted |
| Backtest PR #6 | <https://github.com/YungeG/quant-backtest/pull/6>, open stacked on PR #5 | historical-source head `64159f81fa6f831990690dd133587b96533a0362`; not accepted |
| Backtest PR #7 | <https://github.com/YungeG/quant-backtest/pull/7>, open stacked on PR #6 | historical-declaration commit `25b8dd12a8a62530ce2467e13d1bd0b55b34b0cf`; not accepted |
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

## Published trio-selection candidate

```text
/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/
  trio-selections/000651.SZ/20231231/v1-candidate-01
```

| Value | Identity |
| --- | --- |
| Request | `sha256:6c8e38908cbc77f0ba4bfac62d8381235489e667b592fd2702fa37833e49cc7d` |
| Selection | `sha256:34d09c7649143ee784f95f25873dd462ee56fc37cae91fa8bc7a604ef37f890c` |
| Canonical file | `sha256:b07c00e6608b4c6b95dfdce830593d304de743dd39dffffe2eb9a5c033f6c74a` |
| Decision instant | `UtcInstant(1714959000000000000)` |
| Grade/deployment | `false` / `false` |

Canonical readback, repeated selection and credential-exclusion checks passed. The selected trio is fixed-current-consolidated only; it does not exercise generic comparative-adjustment or provider revision-chain resolution.

## Published historical source candidate

```text
/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/
  source-snapshots/000651.SZ/2018-2022/v3-candidate-01
```

| Value | Identity |
| --- | --- |
| SourceSnapshot | `sha256:aee2ea78f3d51185110bc927836ce77ed51f590a9c7b4c26ee7ecd951cbf8d4b` |
| Content tree | `sha256:d5375befd81c5fb1ab2832a48bb7c3d0b4fc7dcf9b4ea64700f837dc624ce3d9` |
| Provenance | `sha256:5495fbee8d8668e324be8263f49f9f556ea6a4324b5f530c13a2176f148ad2e5` |
| Receipt file | `sha256:0a24a2f0d89f07f750d08e18905c43b79cd85ea81581b1f27c86c7e8b99cfd44` |
| Members | `19` |
| Grade/deployment | `false` / `false` |

The snapshot contains the 2018 balance endpoint, 2019–2022 statement trios, five official annual-report PDFs and one official CNINFO metadata response. Combined with the separate 2023 snapshot, raw source coverage now reaches six balance endpoints and five annual trios. Persisted rebuild/verify, file modes, receipt equality, staging cleanup and credential exclusion passed.

The first real publication attempt failed atomically before final visibility because the range parent was absent; the reviewed head fix created the validated parent and the retry succeeded. No partial output survived.

Historical official-report audit is recorded in [`quality-bband-historical-financial-declaration-audit.md`](quality-bband-historical-financial-declaration-audit.md). Unit and D&A facts are sufficient, but 2021 debt is not uniquely defensible: the issuer's explicit interest-bearing table omits separately labelled `企业借款及利息 2,731,680,114.20`. Both candidate debt reconciliations are retained and canonical 2021 debt fails `DEBT_SCOPE_INCOMPLETE`.

Published historical declaration candidate:

```text
/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/
  declarations/000651.SZ/2018-2022/v1-candidate-01
```

It contains four canonical declaration files for 2018–2020/2022, one canonical 2021 failure/conflict file and a manifest. Manifest SHA-256 is `sha256:a424edd19abc9b17d54f40bfc0e1c6f90e04690d7ba4c6bb10a99982e9531726`; readback, identities, file modes and credential exclusion passed.

## Frozen historical Calendar/Session evidence

[`quality-bband-szse-calendar-session-authority-v1.md`](quality-bband-szse-calendar-session-authority-v1.md) exact-records official SZSE holiday notices, archived rules and daily market-overview response hashes. It freezes the five finite next-session planning boundaries and the `09:30 Asia/Shanghai` continuous-auction open.

The 2019 annual notice's original `2019-05-02` reopen is not controlling: the official `2019-04-18` adjustment moved the effective Labour Day reopen to `2019-05-06`. The Gree 2018-report boundary remains `2019-04-30` because that is the first session strictly after its `2019-04-29` publication date.

No accepted Backtest historical availability artifact exists yet.

## Next executable gates

1. accept stacked PRs #1–#7;
2. freeze and implement historical normalization for 2018–2020/2022 with exact Calendar/Session binding;
3. preserve 2021 as unavailable;
4. five complete ROIC observations remain blocked until competent authority resolves 2021 debt.

The current capture grants no MarketBundle, Strategy, Validation, Live or deployment authority.
