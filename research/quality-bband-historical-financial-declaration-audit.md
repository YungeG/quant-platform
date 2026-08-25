# Quality + B-Band historical financial declaration audit

- **Status:** `SOURCE_FACTS_AUDITED / 2021_DEBT_SCOPE_INCOMPLETE / DECLARATION_IMPLEMENTATION_PACKET_FROZEN`
- **Checked:** 2026-08-25
- **Issuer:** 珠海格力电器股份有限公司 / `000651.SZ` / `xshe:000651`
- **Historical SourceSnapshot:** `sha256:aee2ea78f3d51185110bc927836ce77ed51f590a9c7b4c26ee7ecd951cbf8d4b`
- **Existing 2023 SourceSnapshot:** `sha256:dec0abb1828f8b87256347e72b6ccfe2f84a2ca13f36aa1415c9a53e96a0c7d5`

## 1. Outcome

Audit the official 2018–2022 annual reports and captured Tushare rows needed to declare:

- statement currency/unit;
- audit opinion and presentation-transition facts;
- complete ending interest-bearing debt;
- combined depreciation and separate amortization additions;
- raw-null versus report-specific zero/not-applicable semantics.

This report freezes source facts only. It emits no declaration object, normalized revision, selected trio, formula, feature, MarketBundle, Strategy, Validation or deployment authority.

## 2. Source documents

| Period | CNINFO ID | PDF SHA-256 | Pages |
| --- | --- | --- | ---: |
| `20181231` | `1206125365` | `sha256:b147eb6b8a4aaf093f3b83550c70e8526415b5b54fe24e4258ce7bfd11d5406a` | 206 |
| `20191231` | `1207685438` | `sha256:1b4869caab122969b322738df69955d788c8dc19b4c6d57188619177e922e708` | 216 |
| `20201231` | `1209855305` | `sha256:0d3c39090adf97fede39149a731a5636bd0eca2002606fb942ca70121dba9072` | 220 |
| `20211231` | `1213262535` | `sha256:96065ec44285bce7a9c0cbee25dfeb2368ec4552d72f06ebf3ecab35136e2444` | 248 |
| `20221231` | `1216702261` | `sha256:7cfc80c2badbf4cd74c5adc080d5072b02cd6c700b04fa7ca0ac44cb8b8fe987` | 232 |

Native PDF text was extracted with `pdftotext -layout`; no OCR was needed. Wide debt/bond tables were reconciled arithmetically against independent statement/note totals.

## 3. Statement, unit and audit facts

| Period | Consolidated balance | Income | Cash flow | Currency/unit authority | Audit opinion |
| --- | --- | --- | --- | --- | --- |
| `20181231` | report/PDF pp.85–86 | p.89 | p.91 | each face states `单位：人民币元` | p.77 `标准的无保留意见` |
| `20191231` | report pp.82–83 / PDF pp.83–84 | report p.86 / PDF p.87 | report p.89 / PDF p.90 | faces state `单位：元`; report p.5 states `单位：人民币元`; note states RMB functional currency | report p.77 / PDF p.78 `标准的无保留意见` |
| `20201231` | report pp.94–95 / PDF pp.95–96 | report p.98 / PDF p.99 | report p.100 / PDF p.101 | faces state `单位：元`; report p.137 says `如无特殊说明，金额单位为人民币元` | report p.87 / PDF p.88 `标准的无保留意见` |
| `20211231` | report pp.117–118 / PDF pp.118–119 | report p.119 / PDF p.120 | report p.120 / PDF p.121 | faces state `单位：人民币元`; note p.160 repeats RMB yuan | report p.111 / PDF p.112 `标准的无保留意见` |
| `20221231` | pp.117–118 | p.119 | p.120 | faces state `单位：元`; note p.130 states RMB functional currency; report p.151 / PDF p.152 states `如无特殊说明，金额单位为人民币元` | p.113 `标准的无保留意见` |

All normalized values therefore require `accounting_currency="CNY"` and `accounting_unit="yuan"` under period-specific document declarations.

## 4. Presentation-transition facts

| Period | Source-bound treatment |
| --- | --- |
| `20181231` | Current 2018 presentation is audited. Comparative statements were retrospectively recast for statement-format changes and common-control combination; no material prior-error correction. |
| `20191231` | 2019 opening balances were adjusted for first application of the financial-instrument standard; 2018 measurements were not restated. Comparative presentation was recast for statement format. |
| `20201231` | 2020 opening classification was adjusted for the new revenue standard; 2019 comparative measurements were not restated. |
| `20211231` | 2021 opening balances were adjusted for the revised lease standard; 2020 comparative information was not adjusted. |
| `20221231` | 2022 opening balances were adjusted for first application of a new policy; 2021 comparative financial statements were not adjusted. |

The captured provider rows are each period's current annual filing. No separate comparative-adjusted provider revision is captured. Historical normalization must not fabricate a cross-presentation supersession chain from opening-balance transition columns.

## 5. Raw provider row identities

All two-row sets are economically identical except for `update_flag`, **except** the 2022 cash-flow rows described below.

| Period | Statement | Canonical row hashes |
| --- | --- | --- |
| `20181231` | balance | `sha256:0c8f5e8a8c6107573be52e29afcf5d03adf544c55a7f705a2d37dc41cdbbadf1`, `sha256:436143a5f528e7c61ff71a43486258f5efe6121b5b810b61a9d769188d576456` |
| `20191231` | income | `sha256:2d74a71e7390fac916705537f15f1cd29aeaa4aed4b9f4724d9ec7a0625c3d12`, `sha256:cff83cb7e3ea02f44ad667e1baf2748c0e9d434f74d8096f04116e7fc4410b2e` |
| `20191231` | balance | `sha256:0eede15c1f9033a38ee0b41ef3a279d3fd24dfb84bff78c91795b684c2fdad54`, `sha256:3e82d2ec45dd7e9afc931f7e80c14b39da7cc5026db11705e091eb151b253a2a` |
| `20191231` | cash flow | `sha256:125f686ad284aaec663439be6369e4ae2ca112d225d109abe3a212368a638a28`, `sha256:fedce59f03b3958c7fdb4d01851b2189245cba5ebd2d44ba3cfef1bbd1ee8f3d` |
| `20201231` | income | `sha256:526c9a14945d0ec256f6b521ce2b13ba4a942e60f0a8d9b39f27cd5e77a0b249`, `sha256:76d72b36d08d121b5ef12b037c723d4e70c79450804defce13191cf6cddbcde3` |
| `20201231` | balance | `sha256:3e1c1256838e8e1e03bad1e19fba81134bf1376896a39907e5fe58cb83638adb`, `sha256:dccef36e8378b78c76efea167a8354bba0f520403c58ff33de3c43b86e988069` |
| `20201231` | cash flow | `sha256:1b1c7295f057a39d7c8d0ffc18e719381b8857d2526daa9fbb246caa81484037`, `sha256:f2441ea67e9231a4b612f9deef05825d71d2c3ff7ce299add0ae26cb35f62e11` |
| `20211231` | income | `sha256:4c809186ba7ce81a973c5b307fd35fcf95fb09d3ebb8ebc7c12e6fb8f8ca2c7c`, `sha256:fe00358d8ffd7e604e4bbdd3153b3a651a0432815bf67a725139f5b1d115054d` |
| `20211231` | balance | `sha256:2476482d61d8c458ab7d469f7e42d2af04841fe451bf15e0c360bd69600e39a4`, `sha256:64cd7a1d09c46ad400cc987d4e7eec3cd9b9b341241fffc4f7724fa94c3adb8a` |
| `20211231` | cash flow | `sha256:311783c125d6c5176e0a0708638fff739182608944a8ab55fd40143b96c386bf`, `sha256:887506206c96e67b9af38a6f6ad90919da51e8f6273c3b5de0a1abfeafcd5948` |
| `20221231` | income | `sha256:d9b6c258c86cd517d0174a6e2c45ef6c9835310c78735df0d08a728ed6329be4` |
| `20221231` | balance | `sha256:62a2c5212905023399073dd0ea8fecdf92d00e86e59bc2a80ad18308ea2d24fe`, `sha256:fb4471d6a17c7184eb39834d04f6606c4c95ef94b7d0b3fbf651b0fab3b606b2` |
| `20221231` | cash flow | `sha256:336f90eb45f8cc80df7da6968751d7ec503e2bea203557ecfc1a0a841d94914b`, `sha256:9dc0456482960fa746c74c6e693d5497ecaa01e6a972a2c56f92f98794614438` |

### 2022 advisory-field conflict

The 2022 cash-flow rows have identical formula-authoritative fields and differ only in:

- `update_flag`: `0` versus `1`;
- provider-computed advisory `free_cashflow`:
  - flag `0`: `27066951494.8798`;
  - flag `1`: `30735381659.7498`.

`free_cashflow` is `ADVISORY_ONLY` under QB-FIN-FIELDS-01. Historical normalization must retain both raw row hashes and both advisory values but must not let that vendor-derived conflict invalidate identical authoritative `n_cashflow_act`, capex, depreciation, amortization and cash values. It also must not select either advisory value as canonical FCF.

## 6. Financing-liability declarations

Standard Tushare borrowing fields understate the issuer's explicit interest-bearing-liability scope in every audited period.

| Period | Official interest-bearing table | Lease addition | Ending bonds | Non-debt dividends | Canonical ending interest-bearing debt |
| --- | ---: | ---: | ---: | ---: | ---: |
| `20181231` | component arithmetic `22,383,629,781.83` | report-specific pre-adoption `0.00` | `0.00` | `707,913.60` | `22,383,629,781.83` |
| `20191231` | printed total `17,344,021,324.26` | report-specific pre-adoption `0.00` | `0.00` | `707,913.60` | `17,344,021,324.26` |
| `20201231` | printed total `23,201,159,352.29` | report-specific pre-adoption `0.00` | `0.00` | `6,986,645.96` | `23,201,159,352.29` |
| `20211231` | printed total `43,546,910,016.46` | full lease including current `14,785,264.79` | short bonds already included `4,048,840,948.73`; long bonds `0.00` | `2,367,112.94` | **unavailable — `DEBT_SCOPE_INCOMPLETE`** |
| `20221231` | printed total `85,813,338,534.63` | full lease including current `213,791,544.62` | ending short/long bonds `0.00` | `5,620,664,762.67` | `86,027,130,079.25` |

### Exact debt sources

- **2018 report p.182:** `公司有息负债情况如下` contains `短期借款 22,067,750,002.70` and `吸收存款及同业存放 315,879,779.13`; no printed total, exact sum `22,383,629,781.83`.
- **2019 report p.189 / PDF p.190:** official total `17,344,021,324.26`, including deposits/interbank and `拆入资金` omitted by standard fields.
- **2020 report p.195 / PDF p.196:** official total `23,201,159,352.29`, including deposits/interbank, `拆入资金` and repo liabilities omitted by standard fields.
- **2021 report p.222 / PDF p.223:** official total `43,546,910,016.46` includes short bonds/current financial liabilities and long payable, but excludes lease liabilities. Note 39 proves full lease liability `14,785,264.79` (`11,471,812.27` current + `3,313,452.52` non-current). This produces candidate reconciliation `43,561,695,281.25`.
- **2021 report p.187 / PDF p.188 conflict:** other payables separately label `企业借款及利息 2,731,680,114.20`, but the issuer's p.222 interest-bearing table omits it. Including that financing-labelled item produces a second candidate `46,293,375,395.45`. No frozen precedence proves either candidate complete, so canonical 2021 debt is unavailable.
- **2022 report p.212:** official total `85,813,338,534.63` includes enterprise borrowing/interest and long payable, but excludes lease liabilities. Note 43 proves full lease liability `213,791,544.62` (`66,954,923.96` current + `146,836,620.66` non-current).

Dividends are recorded for audit/reconciliation only and are not added or subtracted because each official interest-bearing table already excludes them. The 2021/2022 lease addition is explicit because the issuer's table omits lease debt while QB-FIN-FIELDS-01 requires post-adoption lease liabilities.

Raw provider nulls for `bond_payable`/`st_bonds_payable` may resolve only under these exact period/document facts. In particular, 2021 `st_bonds_payable` is not zero: the official short-bond ending balance is `4,048,840,948.73` and is already included in the p.222 total. A declaration must record that balance while using a zero **additional** bond amount in any total reconciliation to avoid double counting.

## 7. Depreciation and amortization declarations

| Period | Declared combined depreciation | Separate ROU addition | Cash-flow intangible amortization | Separate long-term deferred addition | Canonical reported D&A |
| --- | ---: | ---: | ---: | ---: | ---: |
| `20191231` | `2,977,103,353.04` | `0.00` | `215,796,437.95` | `1,519,448.66` | `3,194,419,239.65` |
| `20201231` | `3,377,378,887.04` | `0.00` | `211,327,446.74` | no separately reported line, `0.00` addition | `3,588,706,333.78` |
| `20211231` | `3,476,137,137.22` | already included, `0.00` addition | `168,287,721.43` | no separately reported line, `0.00` addition | `3,644,424,858.65` |
| `20221231` | `4,597,938,791.84` | already included, `0.00` addition | `372,007,224.51` | official note p.177 `27,739,400.53` | `4,997,685,416.88` |

2018 D&A is not needed for the five 2019–2023 formula years. For audit only, the report supports `3,110,329,271.82` = combined depreciation `2,859,799,547.55` + intangible amortization `249,550,269.72` + long-term deferred amortization `979,454.55`.

### Combined-line semantics

- 2019 combined depreciation exactly equals fixed-asset plus investment-property depreciation; no ROU asset exists.
- 2020 combined depreciation exactly equals fixed-asset plus investment-property depreciation; no ROU asset exists.
- 2021 combined depreciation exactly equals fixed-asset, investment-property and ROU depreciation. Adding `use_right_asset_dep` again would double count.
- 2022 the cash-flow label explicitly includes fixed assets, investment property and ROU assets. Adding the separate ROU note amount again would double count.

Use the cash-flow-supplement intangible-amortization values captured by Tushare, not larger gross asset-rollforward charges. The 2022 long-term deferred addition is separately declared because the official note prints exact current-period amortization; the raw provider null remains visible.

## 8. Official publication-date facts

The v3 raw CNINFO metadata exact-binds:

| Period | Official date | Candidate next-session open, pending accepted Calendar |
| --- | --- | --- |
| `20181231` | `2019-04-29` | `UtcInstant(1556587800000000000)` / 2019-04-30 09:30 Asia/Shanghai |
| `20191231` | `2020-04-30` | `UtcInstant(1588728600000000000)` / 2020-05-06 09:30 |
| `20201231` | `2021-04-29` | `UtcInstant(1619746200000000000)` / 2021-04-30 09:30 |
| `20211231` | `2022-04-30` | `UtcInstant(1651714200000000000)` / 2022-05-05 09:30 |
| `20221231` | `2023-04-29` | `UtcInstant(1683163800000000000)` / 2023-05-04 09:30 |

These values are candidate declarations only. No accepted multi-year Frozen SZSE Calendar/SessionModel evidence is yet bound, so historical `available_at` results remain blocked.

## 9. Fail-closed decisions

1. No provider-global null→zero rule for bonds, leases or deferred amortization.
2. Pre-2021 lease treatment is exact report-specific pre-adoption/not-applicable evidence, not a generic numeric provider observation.
3. 2021/2022 full lease additions must not double count the non-current raw `lease_liab` or current portions embedded in broad face fields.
4. 2021 `企业借款及利息 2,731,680,114.20` conflicts with its omission from the issuer's explicit interest-bearing table. It cannot be silently included or excluded; 2021 must return `DEBT_SCOPE_INCOMPLETE`. 2022 enterprise borrowing/interest is included because the issuer explicitly includes it.
5. 2022 provider `free_cashflow` conflict is advisory-only and cannot select or invalidate canonical FCF inputs.
6. Opening-balance standard transitions are retained as audit facts; the existing frozen formula still uses selected closing capital for year `Y-1`. No undocumented opening-capital substitution is authorized.
7. Historical availability remains blocked until exact Calendar/Session declarations are accepted.
8. This audit does not prove provider revision closure, comparative-presentation closure or full-market applicability.

## 10. Next implementation boundary

A period-specific declaration implementation may bind document/unit/D&A facts for 2018–2022 and debt facts for 2018–2020/2022. The 2021 declaration must preserve both debt candidates and return `DEBT_SCOPE_INCOMPLETE`; it must not publish `ending_interest_bearing_debt`. The implementation must remain a fixed-issuer source-bounded successor and preserve:

- existing 2023 declaration/normalization/selection identities;
- all raw row hashes/update flags/advisory conflicts;
- historical official metadata and candidate availability as non-accepted until Calendar authority exists;
- no formulas or Strategy features in the declaration/normalization lane.

Until a competent source resolves the 2021 debt conflict, five complete ROIC observations remain blocked even if the other historical periods normalize successfully.
