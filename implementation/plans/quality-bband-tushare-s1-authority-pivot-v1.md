# Quality-BBAND Tushare S1 authority pivot v1

- **Status:** `OWNER_APPROVED / IMPLEMENTATION_PACKET_FROZEN / TUSHARE_CONTROLLING_AUTHORITY`
- **Approved:** 2026-08-27
- **Strategy:** `cn-a-share.quality-bband-breakout.manual4.v1`
- **Owner decision:** when Tushare supplies the required field, use the retained Tushare observation as the controlling S1 source
- **Supersedes for S1 execution:** procurement-only blocking under `quality-bband-formal-s1-authority-feasibility-v1.md`
- **Backtest implementation base:** `0d373b71b263a53b6b00e50b26ae1508dcfc986f`
- **Preserves:** official SSE/SZSE/CSRC authority remains false; all source limitations remain explicit
- **Packet body hash:** `sha256:b10001ff7fdc6e9f952ba49ea66e29990cd5aa6a0454476cebb20cc521db8a9d` (SHA-256 of this UTF-8 file with this entire line removed)

## 1. Outcome

Permit formal project S1 construction from the already accepted immutable Tushare source snapshots rather than waiting for licensed official historical reference files.

This is an owner-approved source-authority pivot, not a claim that Tushare is an exchange or CSRC official archive. `formal_s1_qualified=true` means exact compliance with this frozen provider-authority contract only.

It does not authorize S2 qualification, S3, S4, final QB-DATA, Strategy, Target, Backtest, Validation, promotion or deployment.

### Scoped contract supersession

For only the two pinned SourceSnapshots and nine screens in this packet, the owner decision narrowly supersedes:

- staged-funnel §10 prohibition on current/provider data controlling historical S0/S1 membership;
- missing-data policy §§2 and 7 prohibition on current classification projection and provider absence authority;
- immutable-Universe contract §§2–4 requirement for official historical listing, board and CSRC-industry sources.

The supersession accepts retained Tushare catalog/market/roster/industry observations and exact retained roster absence as controlling project facts. It does not apply to any other snapshot, query, date, stage or provider, and does not change official-authority, decision-grade or beyond-provider-scope flags.

## 2. Pinned inputs

### S0 catalog

```text
path:
/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/
  s0-lightweight-source-snapshots/stock-basic/20260826/v1-candidate-01

snapshot_id:
sha256:b5b7a9243439146181ef07acd07c09e79d16f605bc6cfdc3148746e64359e198
```

The accepted S0 artifact contains 5,889 unique rows. The independently frozen broad catalog for this contract is exactly the 5,545 rows whose provider code is a legal six-digit `.SH/.SZ` code and whose retained `exchange` agrees with the suffix. The 343 `.BJ` rows and malformed `T600018.SH` row are audited S0 source extras, not fatal catalog identities.

### Historical annual rosters

```text
path:
/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/
  annual-structural-roster-source-snapshots/2016-2025/20260826/v1-candidate-01

snapshot_id:
sha256:22585fa4c2070d87544f0ba977be757770aeeaad5bead30188317c1794680ee8
```

Consume only the nine retained terminal `bak_basic` observations:

```text
20170502
20180502
20190506
20200506
20210506
20220505
20230504
20240506
20250506
```

The `20160503` zero-row observation remains retained but is outside the approved nine-screen S1 scope.

## 3. Accepted provider-authority semantics

The following previously nonauthority observations become controlling under the owner decision:

| S1 fact | Controlling Tushare field/source |
|---|---|
| broad catalog membership | exact 5,545 canonical `.SH/.SZ` identities from retained `stock_basic` `L/D/P`; 344 other rows are audited source extras |
| venue and product identity | `stock_basic.exchange`, `stock_basic.market`, `stock_basic.curr_type`, provider code suffix |
| historical active membership | exact `bak_basic` row presence at the screen |
| listing date for age | screen-local `bak_basic.list_date` |
| board predicate | current retained `stock_basic.market` accepted as the controlling board label for every approved screen |
| non-financial predicate | screen-local `bak_basic.industry` |
| screen dates | retained `trade_cal`-derived dates accepted as the controlling Calendar boundary for this nine-screen contract |

Provider row absence is accepted as absence from the Tushare-defined screen roster. This permission applies only to the exact retained terminal response and request identity; it does not generalize to arbitrary zero-row queries.

## 4. Canonical Instrument mapping

Only exact current-catalog codes matching these forms are legal:

```text
([0-9]{6}).SZ -> InstrumentId(VenueId("xshe"), code)
([0-9]{6}).SH -> InstrumentId(VenueId("xshg"), code)
```

Within the frozen 5,545-member catalog, duplicate identities or venue/suffix disagreement fail `CATALOG_IDENTITY_MISMATCH`. The 343 `.BJ` rows and `T600018.SH` are classified before canonical mapping as audited S0 source extras.

Historical `bak_basic` rows absent from the retained S0 catalog are source extras. They are counted and hashed but do not enter the independently defined broad catalog or S1 scope.

## 5. Exact structural predicate and precedence

For every retained S0 catalog member and screen, assign the first applicable disposition in this order:

1. `STRUCTURALLY_OUT_OF_SCOPE / NOT_PRESENT_IN_TUSHARE_SCREEN_ROSTER` when no exact `bak_basic` row exists;
2. `STRUCTURALLY_OUT_OF_SCOPE / NON_CNY_OR_NON_MAIN_BOARD` unless retained S0 has exact `curr_type="CNY"`, `market="主板"`, and matching SSE/SZSE venue;
3. `STRUCTURALLY_OUT_OF_SCOPE / LIST_DATE_UNKNOWN` when screen-local `list_date="0"` or malformed;
4. `STRUCTURALLY_OUT_OF_SCOPE / LISTING_AGE_LT_FIVE_YEARS` when the fifth calendar anniversary is after the screen date;
5. `STRUCTURALLY_OUT_OF_SCOPE / FINANCIAL_INDUSTRY` when screen-local industry is exactly one of:

```text
银行
保险
证券
多元金融
```

6. `STRUCTURALLY_ELIGIBLE` otherwise.

No current name, ST marker, suspension, later delisting, financial-row availability or price-bar presence participates in this S1 predicate.

## 6. Board and age amendments

### Historical SME Board

The pre-2021 SME Board is accepted as Main-Board-equivalent for this strategy because retained Tushare current `market="主板"` is the controlling label after the owner-approved pivot. No separate historical SME exclusion is applied.

### Fifth anniversary

Use calendar anniversary, not `365 * 5` days or trading sessions. February 29 maps to February 28 in a non-leap fifth-anniversary year.

The screen-local valid `bak_basic.list_date` controls age. It is not silently replaced by current S0 `list_date`.

## 7. Missing, duplicate and conflict rules

- duplicate or conflicting canonical S0 `.SH/.SZ` identities fail at failure priority 2;
- duplicate `bak_basic` rows for one screen/code fail at failure priority 5 before any industry conflict;
- S0 venue/suffix disagreement fails;
- a roster code absent from S0 is an audited source extra, not a new Instrument;
- `list_date="0"` is explicit unknown and structurally out of scope;
- null industry after all earlier predicates is `UNRESOLVED_STRUCTURAL_AUTHORITY`, blocks that screen and does not become non-financial;
- conflicting non-null roster industries for one screen/code fail;
- provider zero rows outside the exact retained annual requests remain nonauthority.

## 8. Expected real results

The accepted real artifacts must reproduce exactly:

| Screen | Eligible count |
|---|---:|
| `20170502` | `1,995` |
| `20180502` | `2,034` |
| `20190506` | `2,053` |
| `20200506` | `2,143` |
| `20210506` | `2,224` |
| `20220505` | `2,434` |
| `20230504` | `2,612` |
| `20240506` | `2,635` |
| `20250506` | `2,667` |

Frozen aggregate values:

```text
eligible Instrument union = 2,845
required financial pairs = 32,179
required S2 member keys = 96,537
```

Expected-set identities must equal the already accepted provisional S2B values:

```text
screen_membership_hash = sha256:00b6f4487ffd946ca1db05a4fc353f45ba9da235cc954e1248902da3103a8f2b
period_requirements_hash = sha256:87f0ad15a76bc01561e0347f59a720e26b657829198774bf14893df7ef4fe846
instrument_union_hash = sha256:25d69f75295afe13549269e96d9fbeb726605ac5c93e78d9cfe46ecf48f30ab0
expected_pairs_hash = sha256:336efc4e947062036b1c98add7977653c48abdab8f33350516626a521b9b2b3e
expected_member_keys_hash = sha256:0269e22c9f45b24b827e98a91515ac31ae5486ba0fda668f69112400b088e44b
```

Additional frozen identities and closure values:

```text
owner_decision_id = sha256:629748197e0606baeff184a6eece576a2e7660cf5363d76d10a4e5577af6e1ed
canonical_catalog_count = 5,545
canonical_catalog_hash = sha256:84b8074dd213a5badfc74975bd179d8c08844e304197bad06e51546bc14bcbf3
s0_source_extra_count = 344
s0_source_extras_hash = sha256:dbbd8ecaea3e9a97b289678738bd662fbcafa04952d6873146c377929d14a4eb
all_disposition_count = 49,905
all_dispositions_hash = sha256:05287a1081e217d24d3911e5826dde980e4d941ce277bd462d379fb1e0333666
```

S0 extras comprise 343 `.BJ` codes and the literal malformed code `T600018.SH`.

| Screen | `decision_at` epoch ns | Eligible | Out of scope | Dispositions hash | Eligible IDs hash |
|---|---:|---:|---:|---|---|
| `20170502` | `1493688600000000000` | 1,995 | 3,550 | `sha256:fea08c7e48a65ab5234365170868a19e0efa664e78c3ddcd1120774ce9105378` | `sha256:277ce5c25c287d4166a3554bf7490c79e51862ac691ac493c54a77936d9ebb46` |
| `20180502` | `1525224600000000000` | 2,034 | 3,511 | `sha256:855d59f3043bd3d4ac2ae036db909d396d043b2cfe9e6ba69bb4291cd6a577f3` | `sha256:dbca60e545b16185960fcbfd3df0a2803137a7f2202314f0f47bba5411d38e0e` |
| `20190506` | `1557106200000000000` | 2,053 | 3,492 | `sha256:55fe4961f25e33b33bbfd72f9ae2e6bfbdb7eebd985daa808a939156c415a6d3` | `sha256:0e9ac5081536642836f53772ec5b787598646ec486e56911a1c37c8406b1958f` |
| `20200506` | `1588728600000000000` | 2,143 | 3,402 | `sha256:4df1da2531659ca1d83ddcbb0ed0c464988907f10bbb4f0a14cdb57f148fc225` | `sha256:515a898727f5529afe2141c9608385c1c06346a2286745cd9d2f70f8dc6e57b9` |
| `20210506` | `1620264600000000000` | 2,224 | 3,321 | `sha256:b7e5370610ef49cd9531461aad5c76c9f999a81cea85ad91c100b2fccf3796ad` | `sha256:b01fd4be16bb3b347d08b3703c9a24893ad725daa0d8e553b4d7db9af61d8ebc` |
| `20220505` | `1651714200000000000` | 2,434 | 3,111 | `sha256:b906f4465cea6499c5651e168546346df0dae0a2c87c91769f3b4a07060b9fd3` | `sha256:80b2040da451c5810f2c13cb4cad561b1db2ecf0f47d9be1aa35ae0622bfa256` |
| `20230504` | `1683163800000000000` | 2,612 | 2,933 | `sha256:fececcd7fe29852b9928b284b3f6a3254534d74a5513050b52659ad3f387d17c` | `sha256:ec803daa73eae7205ef943cf907840501f054e25d0bb754331fa81702fb206f3` |
| `20240506` | `1714959000000000000` | 2,635 | 2,910 | `sha256:69fc18da3540bfb085ad02bf7c4c7709caa6109eb427f74b15ad51029df08a5b` | `sha256:0767557ede35189e731c1695d94cb44d1d4bf32575854e155671d82130f7b034` |
| `20250506` | `1746495000000000000` | 2,667 | 2,878 | `sha256:264bb0d9fb29dc655a5f7ea0c4cab27bb1dfa1fd891b1a2ddc76155118ad7cba` | `sha256:5a0686e15872eeae6e569f3254aebb1504aa2ddafba7da0914c51520ab694036` |

Aggregate first-reason counts across all screens:

```text
NOT_PRESENT_IN_TUSHARE_SCREEN_ROSTER = 11,401
NON_CNY_OR_NON_MAIN_BOARD = 11,509
LIST_DATE_UNKNOWN = 60
LISTING_AGE_LT_FIVE_YEARS = 5,403
FINANCIAL_INDUSTRY = 735
STRUCTURALLY_ELIGIBLE = 20,797
UNRESOLVED_STRUCTURAL_AUTHORITY = 0
```

Any difference blocks publication. Counts are sentinels, not an alternative derivation rule.

## 9. Exact S1 manifest schema and serialization

Publish exactly one file:

```text
tushare-s1-structural-manifest.json
```

Serialization is UTF-8 canonical JSON with `ensure_ascii=false`, `allow_nan=false`, sorted keys and separators `(",", ":")`, with no trailing newline.

Top-level exact fields:

```text
type: "quality_bband_tushare_s1_structural_manifest"
schema_version: 1
manifest_id: sha256
owner_decision_id: sha256
packet_body_hash: sha256
backtest_base_commit: str
inputs: object
screen_dates: list[str]
broad_catalog: list[CatalogMember]
broad_catalog_hash: sha256
source_extras: object
screens: list[ScreenDispositionSet]
instrument_union: list[InstrumentId]
period_requirements: list[object]
expected_pairs: list[object]
expected_member_keys: list[list]
hashes: object
counts: object
flags: object
limitations: list[str]
```

`manifest_id = canonical_sha256(body_without_manifest_id)`.

### CatalogMember

```text
instrument_id: canonical InstrumentId
provider_code: str
source_member_key: str
source_row_index: int
```

Order by `(instrument_id.venue, instrument_id.stable_key)`.

### StructuralDisposition

```text
screen_date: YYYYMMDD
decision_at: UtcInstant
instrument_id: canonical InstrumentId
provider_code: str
disposition: STRUCTURALLY_ELIGIBLE | STRUCTURALLY_OUT_OF_SCOPE | UNRESOLVED_STRUCTURAL_AUTHORITY
reason: null | NOT_PRESENT_IN_TUSHARE_SCREEN_ROSTER | NON_CNY_OR_NON_MAIN_BOARD | LIST_DATE_UNKNOWN | LISTING_AGE_LT_FIVE_YEARS | FINANCIAL_INDUSTRY
s0_source_member_key: str
s0_source_row_index: int
roster_source_member_key: str | null
roster_source_row_index: int | null
```

Order first by screen chronology, then `(venue, stable_key)`. Every screen has exactly 5,545 dispositions. Each per-screen `dispositions_hash` is `canonical_sha256` of the complete ordered `StructuralDisposition` objects above, including `decision_at`. `all_dispositions_hash` is the canonical hash of their complete screen-chronological flattened list. Duplicate catalog identity fails before duplicate roster rows; duplicate roster rows fail before industry evaluation.

### ScreenDispositionSet

```text
screen_date: YYYYMMDD
decision_at: UtcInstant
calendar_authority_id: annual-roster SourceSnapshot ID
dispositions: list[StructuralDisposition]
dispositions_hash: sha256
eligible_instrument_ids: ordered list[InstrumentId]
eligible_instrument_ids_hash: sha256
eligible_count: int
out_of_scope_count: int
unresolved_count: int
disposition_counts: object
closure_complete: true
```

### Source extras

```text
s0_total_row_count: 5,889
canonical_catalog_count: 5,545
source_extra_count: 344
bj_extra_count: 343
malformed_provider_codes: ["T600018.SH"]
source_extra_codes_hash: sha256:dbbd8ecaea3e9a97b289678738bd662fbcafa04952d6873146c377929d14a4eb
roster_extra_counts_by_screen: {"20170502":4,"20180502":3,"20190506":2,"20200506":1,"20210506":7,"20220505":2,"20230504":1,"20240506":250,"20250506":266}
roster_extra_row_count: 536
roster_extra_codes_hash: sha256:98394a9496d7438a6335cb195e7df37c34be591c72c67dafbabc5265d38a51a7
roster_extra_counts_hash: sha256:d317af4d07959c9a0d8927f03103689c5f94684a771e051d4580ef604dee1f65
```

S0 `source_extra_codes_hash` hashes the sorted list of raw provider-code strings. Roster extras are screen-local rows whose provider code is not in the 5,545-member catalog. `roster_extra_codes_hash` hashes the list of objects `{"screen_date": YYYYMMDD, "provider_code": str}` sorted by `(screen_date, provider_code)`. `roster_extra_counts_hash` hashes the screen-keyed count object shown above. Roster extras never create an Instrument.

### Financial requirements

For screen year `Y`, periods are exactly `(Y-5)1231` through `(Y-1)1231` in ascending order. Pairs order by `(venue, stable_key, period)` and retain chronological `required_by_screen_dates`. Member keys order by API first, then pair:

```text
income_vip
balancesheet_vip
cashflow_vip
```

The exact field name is `expected_member_keys_hash`.

### Inputs

Bind exact S0 and annual-roster `snapshot_id`, `content_tree_hash`, `provenance_hash`, snapshot-file SHA-256, receipt-file SHA-256, request hashes and raw-member hashes. Bind the owner decision ID, packet body hash and Backtest base commit.

### Limitations

Exact sorted tuple:

```text
CURRENT_TUSHARE_MARKET_PROJECTED_AS_CONTROLLING_HISTORICAL_BOARD
OFFICIAL_CSRC_INDUSTRY_AUTHORITY_FALSE
OFFICIAL_EXCHANGE_AUTHORITY_FALSE
OWNER_APPROVED_TUSHARE_SCOPE_ONLY
PROVIDER_ROW_ABSENCE_ACCEPTED_ONLY_FOR_PINNED_SCREEN_RESPONSES
SURVIVORSHIP_SAFETY_BEYOND_TUSHARE_SCOPE_FALSE
```

### Required hashes and counts

`hashes` contains the catalog, source extras, all dispositions, every per-screen disposition/eligible hash, screen membership, period requirements, instrument union, expected pairs and `expected_member_keys_hash` values frozen in this packet.

`counts` contains exact S0 rows, catalog, source extras, screens, all dispositions, each reason total, eligible union, pairs and member keys.

Mechanical closure per screen:

```text
5,545 broad catalog members
= structurally eligible + structurally out of scope + unresolved
```

Current accepted inputs require unresolved count `0` on every screen.

## 10. Authority flags

Required successful output flags:

```text
owner_approved_tushare_authority = true
formal_s1_qualified = true
provider_scope_exact = true

official_exchange_authority = false
official_csrc_industry_authority = false
market_truth_completeness_claimed = false
survivorship_bias_safe_beyond_tushare_scope = false
formal_s2_qualified = false
decision_grade_eligible = false
strategy_authorized = false
strategy_target_authorized = false
backtest_authorized = false
validation_authorized = false
deployment_authorized = false
```

The manifest may unlock downstream source-bounded S2/S3/S4 work under this owner-approved provider contract. It does not upgrade the provider observations into official exchange/CSRC facts.

## 11. Failure precedence

1. malformed type/schema/path;
2. canonical S0 catalog duplicate, malformed in-scope identity or venue conflict;
3. SourceSnapshot/raw-member/receipt/hash reconstruction failure;
4. screen/Calendar request mismatch;
5. duplicate roster row for one screen/code;
6. unresolved industry after earlier predicates;
7. closure, count or frozen-hash mismatch;
8. canonical serialization/publication failure.

No failure emits an empty eligible set, Target, execution request or Strategy terminal.

## 12. Implementation boundary

Implement as an additive no-network Backtest artifact tool with an exact three-file write set:

1. `tools/acquisition/cn_a_share_quality_bband_tushare_s1_structural_v1.py`
2. `tests/tools/acquisition/test_cn_a_share_quality_bband_tushare_s1_structural_v1.py`
3. `tests/architecture/test_quality_bband_tushare_s1_structural_v1_boundary.py`

The tool consumes only the two accepted artifact roots and one fresh output path. It must reconstruct every input SourceSnapshot, publish atomically with bounded safe reads and no-clobber rename, and reproduce the frozen real values before final publication.

Exact public operation:

```python
build_quality_bband_tushare_s1_structural_v1(
    *,
    s0_root: Path,
    annual_roster_root: Path,
    output_dir: Path,
) -> dict[str, object]
```

Private symbols:

```text
QualityBbandTushareS1Failure
QualityBbandTushareS1Error
_FrozenSourceIdentity
_LoadedSourceRoot
_strict_json
_read_root_member
_load_source_root
_canonical_instrument
_fifth_anniversary
_derive_catalog_and_extras
_build_screen_dispositions
_build_financial_requirements
_validate_frozen_hashes
_rename_noreplace
_atomic_publish
_parse_args
main
```

Candidate publication target:

```text
/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/
  tushare-s1-structural-manifests/2017-2025/20260827/v1-candidate-01
```

The architecture test requires base ancestry from `0d373b71b263a53b6b00e50b26ae1508dcfc986f`, exactly these three changed files, no public-root export, no network imports, and no staged files.

## 13. Nonclaims

This pivot does not claim:

- official exchange or CSRC provenance;
- completeness outside the retained Tushare request scopes;
- correctness of current board labels as historical market truth;
- official industry classification;
- complete status/corporate-action history;
- financial, governance, valuation or execution authority;
- Strategy support, economic performance or deployment readiness.
