# Quality-BBAND real non-filing declaration readiness v1

Status: `PURE_BUILDER_ACCEPTED / SIX_LANES_SOURCE_READY / 601028_POINT_IN_TIME_BLOCKED / S2B_NOT_READY`  
Date: 2026-08-26

## Builder candidate

Backtest PR #14 implements the independently accepted pure QB-S2-NONFILE-01 constructor:

<https://github.com/YungeG/quant-backtest/pull/14>

Commit: `427bee1`.

Focused tests passed `18`; provider regression passed `136`; LSP was clean. The implementation performs no source acquisition or publication.

## Source readiness

The accepted official-remediation SourceSnapshot is:

```text
sha256:8195e9d9e99949802c829f218929bdbf740b336152d83ad789a060e0355d116e
```

Its reviewed document pairs can support post-deadline initial/terminal construction work for:

```text
000693.SZ / FY2018
600090.SH / FY2021
600146.SH / FY2021
000038.SZ / FY2022
000976.SZ / FY2023
000622.SZ / FY2024
```

Calendar/Session identities and exact reviewed pages/excerpts remain to be published, so no real declaration artifact exists yet.

## Point-in-time boundaries

The frozen no-backdating rule remains material:

| Instrument | Primary screen | Earliest candidate definitive declaration boundary | Screen result |
|---|---|---|---|
| `000693.SZ` | 2019-05-06 | 2019-05-06 open | may be issuer-local unresolved by T-close |
| `600090.SH` | 2022-05-05 | 2022-05-05 open | may be issuer-local unresolved by T-close |
| `600146.SH` | 2022-05-05 | 2022-05-05 open | may be issuer-local unresolved by T-close |
| `000038.SZ` | 2023-05-04 | after definitive 2023-05-10 authority | screen remains blocked |
| `000976.SZ` | 2024-05-06 | after definitive 2024-05-12 authority | screen remains blocked |
| `000622.SZ` | 2025-05-06 | after definitive 2025-05-06 date-only authority | screen remains blocked conservatively |
| `601028.SH` | 2025-05-06 | no accepted post-deadline proof in candidate 01 | screen remains blocked |

A later declaration can close subsequent issuer-local dates but cannot repair an earlier primary screen.

## `601028.SH` follow-up

The retained 2025-04-29 issuer notice was published before the statutory deadline. QB-S2-NONFILE-01 correctly rejects a pre-deadline expectation as initial proof. The retained 2025-05-21 voluntary-delisting notice proves listing termination but does not itself affirm that FY2024 remained unfiled.

A later primary sponsor disclosure supplies retrospective terminal confirmation:

- NEEQ information-disclosure search result: 2026-04-29, code `400267`, `R鑫升1`;
- title: `中泰证券股份有限公司关于山东鑫升矿业股份有限公司无法披露2025年年度报告的风险提示性公告`;
- source PDF: <http://dataclouds.cninfo.com.cn/sjother2/neeqs/2026/20260429/5e69266176024a6dae6eb9392c5e22b5.pdf>;
- PDF bytes: `124,766`;
- PDF SHA-256: `sha256:a00a87a6b4e96e93c04d02bc3816fbe9b0488744fca65a53d3603bf509eaa464`;
- retained search response audit bytes: `11,090`, `sha256:644fb82a3c3cafbc2ecbd17d8910c3713f446e13b9cb4e0ca70578f6abec29c5`.

The sponsoring broker states that the company had not disclosed its 2024 annual report and 2025 half-year report. This is competent later confirmation, but its 2026 availability cannot be projected backward to the 2025-05-06 screen.

These bytes are a nonretained audit fetch, not an accepted SourceSnapshot.

## Decision

Under the currently approved strict availability rule:

1. official non-filing causes are now known;
2. the pure declaration operation exists;
3. later issuer-local unresolved intervals are representable;
4. several required primary screens remain point-in-time blocked;
5. full Fold execution and S2B decision-time authority remain unavailable.

Implementing a complete S2B publication now would not authorize the blocked screens. The strategy remains untested, not rejected.

## Material policy choice

Resuming the 2025 screen requires a new user-approved rule such as:

```text
A competent issuer notice published before the deadline that definitively states
"cannot disclose by the statutory deadline" becomes usable at the first accepted
session boundary after the deadline, provided no accepted filing supersedes it.
```

This is not current authority. It changes temporal missing-data semantics and must not be inferred from search absence or provider zero rows.
