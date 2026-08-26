# QB-S2-PANHAI-BAL-01 — `000046.SZ` FY2014 official balance-sheet backfill v1

- **Status:** `IMPLEMENTATION_PACKET_FROZEN / PLAN_ONLY / SOURCE_CANDIDATE_ACCEPTED`
- **Backtest base:** `33f7320bd3f1e81c6a985f2fdeea39aedb7bc01e`
- **Purpose:** exact-cover the one missing provisional S2 key `(balancesheet_vip, xshe:000046, 20141231)` from the official audited annual report without impersonating a provider row or industrial qualification
- **Authority snapshot:** Platform commit `650418f`, packet SHA-256 `3e3300d349f9517e72e9d6b687a7c17f6d90e11b7296a38c6b32f4949b91eb22`; conservative-availability amendment `43edeea` independently marked READY

## 1. Exact write set

1. `packages/market-bundle-builder/src/crypto_quant_bundle_builder/pan_hai_2014_official_balance_backfill_v1.py`
2. `tests/bundle_builder/providers/tushare/test_pan_hai_2014_official_balance_backfill_v1.py`
3. `tests/architecture/test_pan_hai_2014_official_balance_backfill_v1_boundary.py`

All predecessor bytes remain unchanged; no public-root export is added.

## 2. Accepted source candidate

The operation accepts only the full verified SourceSnapshot:

```text
snapshot_id = sha256:8195e9d9e99949802c829f218929bdbf740b336152d83ad789a060e0355d116e
content_tree_hash = sha256:c315b9b36d5817fc058da240b50e2c170f530f2b2b4b49808554ef6ddedac15b
provenance_hash = sha256:cbce2903c280938647526abfc0511cc497d85d61f5486e79469ab0714a9c05a2
```

Required members:

```text
response/cninfo/announcement-query/000046-v1.json
response/official/000046/1200788303.pdf
```

PDF identity:

```text
bytes = 4,164,254
sha256 = sha256:0a5bce6a608fcc444d5405c29e81428efe349370c6d8cc4ba72dca26272bec1c
announcement_id = 1200788303
title = 2014年年度报告
announcement_time_epoch_milliseconds = 1428076800000
adjunct_url = finalpage/2015-04-04/1200788303.PDF
```

`verify_source_snapshot` must succeed before any semantic field work. The operation consumes retained bytes only to verify exact member identities/hashes; it does not parse PDF text.

## 3. Reviewed statement evidence

```text
PanHai2014ReviewedBalanceEvidenceV1
```

Exact fields:

```text
type = "pan_hai_2014_reviewed_balance_evidence"
schema_version = 1
reviewer_key = "quality-bband-pan-hai-2014-balance-review-v1"
reviewed_at_epoch_nanoseconds
pdf_member_key
metadata_member_key
statement_pages = (77, 78, 79)
audit_page = 76
statement_title = "合并资产负债表"
issuer_name = "泛海控股股份有限公司"
provider_code = "000046.SZ"
fiscal_period_end_date = 2014-12-31
publication_date = 2015-04-04
currency = "CNY"
unit_text = "人民币元"
unit_multiplier = Decimal("1")
consolidation = "CONSOLIDATED"
company_layout = "MIXED_REAL_ESTATE_SECURITIES_CONSOLIDATION"
audit_opinion = "STANDARD_UNQUALIFIED"
audit_report_date = 2015-04-03
audit_report_number = "信会师报字[2015]第310292号"
field_reviews: tuple[PanHai2014BalanceFieldReviewV1, ...]
limitations: tuple[str, ...]
```

Evidence limitations are exact and ordered:

```text
REVIEWED_PDF_PAGES_ONLY
NO_PDF_PARSER_AUTHORITY
MIXED_REAL_ESTATE_SECURITIES_LAYOUT
SHORT_TERM_BONDS_NOT_SEPARATELY_PRESENT
```

The reviewed evidence is immutable typed input; the Builder does not own OCR/PDF parsing. `reviewed_at_epoch_nanoseconds` must not precede source acquisition.

## 4. Exact field reviews

```text
PanHai2014BalanceFieldReviewV1
```

Exact schema:

```text
type = "pan_hai_2014_balance_field_review"
schema_version = 1
field_key: str
source_label: str | null
pdf_page: int
applicability: VALUE | NOT_SEPARATELY_PRESENT
value_decimal_text: str | null
```

Each field exact-binds its Chinese source label, PDF page, applicability and canonical decimal text. Decimal text matches `0|[1-9][0-9]*(\.[0-9]+)?`, reconstructs exactly through `Decimal`, and is the only representation admitted to canonical hashes. Float input is forbidden. Tuple order is exact:

| field_key | source label | page | applicability | value |
|---|---|---:|---|---:|
| `money_cap` | `货币资金` | 77 | `VALUE` | `11473676835.21` |
| `total_assets` | `资产总计` | 78 | `VALUE` | `70889108573.14` |
| `total_liab` | `负债合计` | 79 | `VALUE` | `58374057829.63` |
| `total_hldr_eqy_inc_min_int` | `所有者权益合计` | 79 | `VALUE` | `12515050743.51` |
| `total_hldr_eqy_exc_min_int` | `归属于母公司所有者权益合计` | 79 | `VALUE` | `9273976463.95` |
| `minority_int` | `少数股东权益` | 79 | `VALUE` | `3241074279.56` |
| `total_liab_hldr_eqy` | `负债和所有者权益总计` | 79 | `VALUE` | `70889108573.14` |
| `st_borr` | `短期借款` | 78 | `VALUE` | `4316020932.89` |
| `non_cur_liab_due_1y` | `一年内到期的非流动负债` | 79 | `VALUE` | `8785180000.00` |
| `lt_borr` | `长期借款` | 79 | `VALUE` | `24359970013.75` |
| `bond_payable` | `应付债券` | 79 | `VALUE` | `2732689313.18` |
| `st_bonds_payable` | no separate line | 79 | `NOT_SEPARATELY_PRESENT` | null |

`VALUE` requires nonnull canonical decimal text and source label. `NOT_SEPARATELY_PRESENT` requires null text and null source label. It is N.A., never zero.

Required reconciliations are exact:

```text
total_assets = total_liab + total_hldr_eqy_inc_min_int
total_hldr_eqy_inc_min_int = total_hldr_eqy_exc_min_int + minority_int
total_liab_hldr_eqy = total_assets
```

## 5. Availability input

```text
PanHai2014BalanceAvailabilityV1
```

Exact fields:

```text
type = "pan_hai_2014_balance_availability"
schema_version = 1
availability_id: str
pdf_member_key = "response/official/000046/1200788303.pdf"
source_publication_date = 2015-04-04
source_visibility_at: UtcInstant
publication_boundary_at: UtcInstant
available_at: UtcInstant
calendar_authority_id: str
source_availability_id: str
```

All IDs are canonical SHA-256. The canonical availability body uses `source_publication_date="2015-04-04"`, canonical UtcInstant dictionaries and the exact PDF member key. `availability_id = canonical_sha256(body_without_availability_id)` and must reconstruct.

v1 deliberately uses a later conservative source-bounded boundary already covered by accepted candidates rather than inventing 2015 Calendar authority:

```text
source_visibility_at = 2017-05-02 09:30 Asia/Shanghai
publication_boundary_at = 2017-05-02 09:30 Asia/Shanghai
available_at = 1493688600000000000 epoch ns
calendar_authority_id = sha256:22585fa4c2070d87544f0ba977be757770aeeaad5bead30188317c1794680ee8
source_availability_id = sha256:8195e9d9e99949802c829f218929bdbf740b336152d83ad789a060e0355d116e
```

The calendar identity is the accepted annual-roster SourceSnapshot containing the 2017-05-02 primary screen; the source identity is the accepted official-remediation SourceSnapshot. All three instants and both authority IDs must equal these literals. This is conservative source-bounded development availability, not formal general Calendar authority. It is available at the 2017 screen open and before that screen's T-close.

## 6. Backfill result

```text
PanHai2014OfficialBalanceBackfillV1
```

Exact fields:

```text
type = "pan_hai_2014_official_balance_backfill"
schema_version = 1
backfill_id
instrument_id = InstrumentId(VenueId("xshe"), "000046")
provider_code = "000046.SZ"
api_name = "balancesheet_vip"
period = "20141231"
statement_kind = "BALANCE_SHEET"
source_snapshot_id
source_content_tree_hash
source_provenance_hash
reviewed_evidence: PanHai2014ReviewedBalanceEvidenceV1
availability: PanHai2014BalanceAvailabilityV1
field_reviews: tuple[PanHai2014BalanceFieldReviewV1, ...]
covered_member_key: tuple[str, str, str]
financial_payload_complete = false
financial_scope_qualified = false
scope_reason = "STATEMENT_SCOPE_UNSUPPORTED"
limitations: tuple[str, ...]
```

`covered_member_key` is stored exactly as `("balancesheet_vip", "xshe:000046", "20141231")`. Result limitations equal the exact evidence limitations. Every date in the canonical body is an ISO string; every financial value is its canonical decimal string or null; InstrumentId/UtcInstant values use their canonical dictionaries. Raw Python `date` and `Decimal` never enter the hash body. `backfill_id = canonical_sha256(body_without_backfill_id)` and must reconstruct.

The result exact-covers one official-filing key in the later `O` set. It is not a Tushare row and emits no `report_type`, `comp_type`, `update_flag` or provider revision fiction.

## 7. Scope outcome

The statement includes client-fund deposits, settlement reserves, financing assets, repurchase liabilities and brokerage customer balances. Therefore v1 records:

```text
company_layout = MIXED_REAL_ESTATE_SECURITIES_CONSOLIDATION
financial_scope_qualified = false
reason = STATEMENT_SCOPE_UNSUPPORTED
```

This closes source-member availability but does not qualify the issuer or calculate ROIC/debt/rank. Later financial-quality handling remains fail-closed/issuer-local according to the accepted missing/scope policy.

## 8. Pure operation

```text
build_pan_hai_2014_official_balance_backfill_v1(
    request: PanHai2014OfficialBalanceBackfillRequestV1,
) -> PanHai2014OfficialBalanceBackfillOutcome
```

Request schema is exact:

```text
PanHai2014OfficialBalanceBackfillRequestV1
type = "pan_hai_2014_official_balance_backfill_request"
schema_version = 1
source_snapshot: SourceSnapshot
reviewed_evidence: PanHai2014ReviewedBalanceEvidenceV1
availability: PanHai2014BalanceAvailabilityV1
```

Outcome schema is exact:

```text
PanHai2014OfficialBalanceBackfillOutcome
backfill: PanHai2014OfficialBalanceBackfillV1 | null
failure: PanHai2014OfficialBalanceBackfillFailure | null
```

Exactly one is nonnull. Request exact-binds the accepted SourceSnapshot, reviewed evidence and availability. Operation is pure: no filesystem, network, clock, PDF parser, publication or public-root export.

Symbols:

```text
BalanceFieldApplicability
PanHai2014BalanceFieldReviewV1
PanHai2014ReviewedBalanceEvidenceV1
PanHai2014BalanceAvailabilityV1
PanHai2014OfficialBalanceBackfillRequestV1
PanHai2014OfficialBalanceBackfillV1
PanHai2014OfficialBalanceBackfillFailure
PanHai2014OfficialBalanceBackfillOutcome
build_pan_hai_2014_official_balance_backfill_v1
```

## 9. Failure mapping

| Condition | Existing failure |
|---|---|
| malformed/foreign exact type, date, decimal, tuple or instant | `INPUT_TYPE_MISMATCH` |
| Instrument/provider/API/period mismatch | `CATALOG_IDENTITY_MISMATCH` |
| snapshot/member/hash/byte/source metadata conflict | `SOURCE_MEMBER_CONFLICT` |
| publication/availability/review causality conflict | `FINANCIAL_REVISION_MISMATCH` |
| field tuple/applicability/reconciliation/covered-key mismatch | `FINANCIAL_PAYLOAD_INCOMPLETE` |
| result reconstruction/hash mismatch | `PUBLICATION_INTEGRITY_FAILURE` |

`PanHai2014OfficialBalanceBackfillFailure` is an exact string enum containing only the six values above. Failure precedence is table order. No partial result is returned.

## 10. Acceptance sentinels

1. accepted snapshot and exact two required members succeed with all 12 reviews;
2. PDF/metadata/snapshot mutation fails before semantic field work;
3. float, noncanonical decimal, null-as-zero, reordered/duplicate field or wrong page fails;
4. each reconciliation failure maps to payload incomplete;
5. availability hash/formula/causality failure maps to revision mismatch;
6. result reconstructs byte-identically and covers exactly one `O` key;
7. result keeps payload/scope qualification false and emits no provider row fiction;
8. pure module has no I/O/network/clock/PDF/publication imports;
9. optional real-fixture gate `QB_OFFICIAL_S2_REMEDIATION_ROOT` reconstructs the accepted SourceSnapshot and succeeds without monkeypatching source/availability authority constants.

## 11. Nonclaims

This backfill does not establish formal S1, industrial formula applicability, financial payload completeness, S2 qualification, ranking, Strategy, Target, execution or deployment authority.
