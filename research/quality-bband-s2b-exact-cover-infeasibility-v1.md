# Quality-BBAND S2B exact-cover infeasibility v1

Status: `DATA_INFEASIBLE_UNDER_ACCEPTED_S1/S2A_AUTHORITY / STRATEGY_NOT_REJECTED / IMPLEMENTATION_DEFERRED`  
Date: 2026-08-26

## Decision

Do not implement the proposed S2B extractor against the current accepted inputs.

The accepted S2A candidate is internally valid, but it does not exact-cover the immutable provisional S1 expected set. A v1 implementation bound only to those inputs would necessarily fail and could never publish. Building and freezing a successful-output schema for a production path that cannot succeed would add code without adding authority.

## Accepted inputs

- S0 SourceSnapshot: `sha256:b5b7a9243439146181ef07acd07c09e79d16f605bc6cfdc3148746e64359e198`
- annual-roster SourceSnapshot: `sha256:22585fa4c2070d87544f0ba977be757770aeeaad5bead30188317c1794680ee8`
- S2A SourceSnapshot: `sha256:4e6574363c36f6cebe7f0ad46585a3a9e31b623546240196a2b8bcf55ec57160`

The S2A candidate has 245 verified pages, 39 roots, 142 terminal leaves and 302,446 terminal rows. Its capture and page-tree integrity are accepted in `quality-bband-s2a-vip-financial-source-assessment-v1.md`.

## Exact-cover failure

The provisional 2017–2025 screens produce:

- 2,845-Instrument union;
- 32,179 required `(InstrumentId, period)` pairs;
- 96,537 required `(api_name, InstrumentId, period)` triples.

Terminal S2A leaves cover 96,515 triples. Twenty-two triples across eight Instruments are absent:

| Period | Instrument | Missing APIs |
|---|---|---|
| 2014-12-31 | `000046.SZ` | balance sheet |
| 2018-12-31 | `000693.SZ` | income, balance sheet, cash flow |
| 2021-12-31 | `600090.SH` | all three |
| 2021-12-31 | `600146.SH` | all three |
| 2022-12-31 | `000038.SZ` | all three |
| 2023-12-31 | `000976.SZ` | all three |
| 2024-12-31 | `000622.SZ` | all three |
| 2024-12-31 | `601028.SH` | all three |

A nonretained advisory probe then requested each exact Instrument/period from both VIP and standard Tushare statement endpoints with the frozen industrial filters. Every request returned zero rows. Repeating the standard endpoint queries without `report_type`/`comp_type` filters returned zero rows for 21 triples; only `000046.SZ` balance sheet 2014 returned one row, with `report_type="1"` and incompatible `comp_type="4"`.

These probes do not create completeness or no-report authority and are not promoted as source artifacts.

## Why upstream scope cannot be repaired by inference

All eight Instruments currently have provider `list_status="D"`, and several annual roster names contain `ST`, `*ST` or `退`. None can silently remove a historical expected member:

- current delisted status does not prove the historical delisting interval;
- a name string does not prove a complete risk-warning revision timeline;
- suspension/tradability history remains incomplete;
- provider no-row observations do not prove no filing or justify exclusion;
- current board mapping and provider industry remain nonofficial historical authority.

The frozen Universe contract also retains ST/risk-warning members in the broad universe and treats suspension as a matching fact rather than an inferred structural deletion.

## Readiness review

An implementation-readiness review rejected the proposed failure-only S2B packet because canonical Instrument serialization, independent expected-set hashes, exact reconstructed SourceSnapshot verification, output schemas/hashes, extra-row accounting and complete tree identity were not yet frozen. More importantly, the accepted v1 input identity made successful real publication impossible by construction.

The packet was therefore not committed, and no Backtest implementation task was started.

## Authority required to resume

At least one must happen before a new S2B packet is justified:

1. accepted point-in-time listing/board/status/tradability authority proves that an expected issuer-period is structurally outside the immutable screen;
2. accepted official filing/document authority supplies every missing statement member;
3. accepted provider completeness authority permits an explicit missing-member state under the frozen missing-data policy without treating absence as scope;
4. a new accepted S1 manifest changes the expected set for independently justified reasons.

Any resumed packet must freeze exact canonical Instrument identities, screen/period/union hashes, reconstructed upstream snapshot verification, terminal extra-row accounting and complete output schemas before implementation.

## Nonclaims

This result does not reject the quality/BOLL strategy and is not an economic backtest result. Formal S1, S2, S3, S4, Strategy, Target, execution, validation and deployment authority remain false. The strategy remains untested under the required historical full-market contract.
