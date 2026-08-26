# Quality + B-Band S2 financial batch-source audit v1

- **Status:** `VIP_BATCH_TRANSPORT_AVAILABLE / RECURSIVE_DATE_SLICING_REQUIRED / EXACT_S2_PAYLOAD_INCOMPLETE`
- **Checked:** 2026-08-26
- **Target provisional S1 union:** `2,845` issuers, annual periods `20121231..20241231`

## 1. Interfaces

Tushare statement documentation states that standard `income`, `balancesheet` and `cashflow` retrieve one stock's history, while `*_vip` variants accept the same parameters for a full-market period and require 5,000 points. The approved xiaodefa proxy successfully called:

```text
income_vip
balancesheet_vip
cashflow_vip
```

with `period`, `comp_type=1`, `report_type=1`.

## 2. Full-period probe results

Identifier-only probes over annual periods 2012–2024 show endpoint-specific hard caps and `has_more` behavior:

| Endpoint | Observed cap | Periods observed truncated |
| --- | ---: | --- |
| `income_vip` | `9,000` | 2019–2022 |
| `balancesheet_vip` | `7,000` | 2012–2020 and 2022–2023 |
| `cashflow_vip` | `6,400` | 2018–2024 |

Examples:

- 2024 income: `6,893` rows / `6,235` unique codes / terminal;
- 2024 balance: `6,919` rows / `6,235` unique codes / terminal;
- 2024 cash flow: `6,400` rows / `4,814` unique codes / `has_more=true`;
- 2012 balance: exactly `7,000` rows and `has_more=true`;
- 2019 income: exactly `9,000` rows and `has_more=true`.

A single period request is therefore not a reliable complete capture whenever `has_more=true`.

## 3. Date slicing is viable

The statement APIs accept announcement `start_date/end_date`. For 2024 cash flow:

| Announcement range | Rows | Terminal |
| --- | ---: | --- |
| `20250101..20250228` | `69` | yes |
| `20250301..20250331` | `1,297` | yes |
| `20250401..20250415` | `881` | yes |
| `20250416..20250430` | `5,899` | yes |
| `20250501..20260826` | `464` | yes |

The union has `8,610` rows, proving that the unsliced `6,400` response was truncated.

A deterministic recursive interval algorithm can start with `[period end, capture date]` and bisect any `has_more=true` interval into disjoint inclusive date ranges until every leaf is terminal. No provider pagination token is required.

## 4. Full-market superset versus exact S2 scope

VIP requests return full-market rows, not the provisional `2,845`-issuer S1 set. Direct per-stock acquisition would require approximately:

```text
2,845 issuers * 3 statement endpoints = 8,535 requests
```

because one single-stock request can return its full annual history. At the existing inter-request spacing this is operationally expensive and would produce thousands of raw members.

The efficient route is full-market VIP source capture followed by deterministic extraction against an immutable S1 scope. This requires a staged-contract amendment:

- acquisition may retain a provider superset when the endpoint cannot filter the exact stage set;
- extraction must exact-cover every expected S1 Instrument/period;
- extra rows are retained and explicitly counted/ignored by canonical identity;
- missing expected rows block; extra rows never define scope.

## 5. Field gap

`balancesheet_vip` omitted `lease_liab` from the returned field list even when requested. This is a real payload blocker for exact canonical interest-bearing debt and leverage.

Consequences:

- VIP capture can provide a coarse/minimal financial source layer;
- it cannot alone produce exact final S2 debt/ROIC/leverage qualification;
- later per-stock/official-note acquisition remains required for issuers whose decision is not invariant under a conservative debt interval.

Other provider-computed values such as `ebit`, `ebitda` and `free_cashflow` remain advisory unless recomputed from frozen raw inputs.

## 6. Recommended staged S2 route

### S2A — full-market source-bounded VIP capture

- annual periods `20121231..20241231`;
- three endpoints;
- frozen minimal formula fields;
- recursive announcement-date slicing for every nonterminal response;
- exact raw leaf responses and split tree in the receipt;
- no qualification claims.

### S2B — exact S1 extraction and coarse bounds

- bind the immutable provisional S1 issuer/date scope;
- select all source rows for those Instruments/periods;
- preserve duplicates/revisions and missing fields;
- compute only decision-invariant failures/passes under explicit bounded candidates;
- send unresolved issuers to per-stock/official-detail acquisition.

## 7. Decision

Batch transport is available and dramatically cheaper than 8,535 single-stock calls, but the current staged contract must explicitly allow source-superset capture and exact downstream extraction. S2 implementation should not begin until that amendment and a recursive-slicing packet are frozen.
