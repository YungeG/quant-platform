# Quality-BBAND S2A VIP financial source assessment v1

Status: source-superset candidate accepted; not S2-qualified and not decision-grade  
Assessment date: 2026-08-26  
Implementation commit: `a4b58ab3c92eea7d05cbfd8e5785ed7b1b48213b`  
Backtest PR: <https://github.com/YungeG/quant-backtest/pull/12>

## Selected candidate

`/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/s2a-vip-financial-source-snapshots/2012-2024/20260826/v1-candidate-02`

- SourceSnapshot: `sha256:4e6574363c36f6cebe7f0ad46585a3a9e31b623546240196a2b8bcf55ec57160`
- content tree: `sha256:3316ea2f6c71f092f5bd803aad6731039b2bc6956c7f176c67183ecaded3e199`
- provenance: `sha256:fb1bfdc0646988d4881bb8a7c1abef61ebce91f46844b6cc83eb6925dc560e09`
- snapshot file: `sha256:f0f1d394e98b298d0bb59990370c6ffb26ad70b89cb99aade3026f732aa1cba3`
- receipt file: `sha256:30afdba09e0a04da1257489a7e13fcee062f41233006fe1d5d8bc33c748791a9`

Candidate 01 remains an auditable earlier capture from commit `789c342`, but candidate 02 is selected because it binds the final accepted source-code contract.

## Capture facts

| Fact | Result |
|---|---:|
| Exact regular files | 247 |
| Raw provider pages / snapshot members | 245 / 245 |
| Root trees | 39 |
| Terminal leaves | 142 |
| Maximum split depth | 7 |
| Terminal rows | 302,446 |
| Retained raw bytes | 180,898,524 |
| File modes | all `0600` |

| API | Pages | Terminal leaves | Terminal rows |
|---|---:|---:|---:|
| `income_vip` | 43 | 28 | 92,920 |
| `balancesheet_vip` | 121 | 67 | 115,592 |
| `cashflow_vip` | 81 | 47 | 93,934 |

Independent review accepted the exact file set, page-to-snapshot hash/size/timestamp bindings, receipt/snapshot equality, root reachability, disjoint gap-free terminal-leaf covers and all explicit false authority flags. Focused tests passed `32`; the final locked broad regression passed `2468`, with `5` configured real-artifact skips.

The capture retained provider source anomalies rather than redefining scope: `4920017.BJ` occurred 20 times and `833243!1.BJ` occurred 9 times across retained pages. Canonical Instrument mapping remains deferred to S2B.

## Provisional S1 exact-cover audit

This audit is development-only because the annual roster and current `stock_basic` mapping do not establish historical official S1 authority. It uses the previously frozen provisional 2017–2025 annual screens, whose issuer union is 2,845.

For every screen year, the expected financial periods are its five preceding annual periods. Across 2012–2024 this yields 32,179 expected `(InstrumentId, period)` pairs and 96,537 expected `(api_name, InstrumentId, period)` triples.

Terminal leaves contain at least one row for 96,515 triples. Twenty-two triples across eight issuers are absent:

| Period | Instrument | Missing APIs | Provisional screens needing it |
|---|---|---|---|
| 2014-12-31 | `000046.SZ` | balance sheet | 2017, 2018, 2019 |
| 2018-12-31 | `000693.SZ` | income, balance sheet, cash flow | 2019 |
| 2021-12-31 | `600090.SH` | all three | 2022 |
| 2021-12-31 | `600146.SH` | all three | 2022 |
| 2022-12-31 | `000038.SZ` | all three | 2023 |
| 2023-12-31 | `000976.SZ` | all three | 2024 |
| 2024-12-31 | `000622.SZ` | all three | 2025 |
| 2024-12-31 | `601028.SH` | all three | 2025 |

All eight have current provider status `D`; that current status is not historical eligibility authority and cannot silently remove them from an earlier screen.

## Authority boundary

This candidate proves only source-bounded S2A capture and deterministic page-tree retention. It does **not** prove:

- exact historical S1 eligibility;
- complete S2B expected-set extraction;
- provider completeness or no-row authority for the 22 missing triples;
- accounting unit/currency qualification;
- financial availability or revision closure;
- coherent presentation selection;
- lease-liability or financing-debt scope;
- hard-filter qualification, ranking, Strategy, Target, execution or deployment authority.

S2B must consume terminal leaves only, retain all matching revisions and fail closed on the 22 missing provisional triples unless accepted upstream authority removes an issuer-period from the immutable expected set or a separately accepted source fills it.
