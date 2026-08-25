# Quality + B-Band SZSE calendar/session authority v1

- **Status:** `EVIDENCE_FROZEN_FOR_IMPLEMENTATION / SOURCE_BOUNDED / ACCEPTANCE_PENDING`
- **Checked:** 2026-08-26
- **Scope:** fixed `000651.SZ` annual-report publication dates from 2019 through 2023 and their first strictly later SZSE continuous-auction opens
- **Consumer:** QB-FIN-AVAIL-01 and the historical normalization packet

## 1. Outcome

Official SZSE notices, archived trading rules and daily market-overview responses are sufficient to freeze the five finite Calendar/Session facts needed by the current fixed-issuer history:

| Official publication date | First declared later session | Asia/Shanghai continuous-auction open | UTC / canonical instant |
| --- | --- | --- | --- |
| `2019-04-29` | `2019-04-30` | `2019-04-30T09:30:00+08:00` | `2019-04-30T01:30:00Z` / `UtcInstant(1556587800000000000)` |
| `2020-04-30` | `2020-05-06` | `2020-05-06T09:30:00+08:00` | `2020-05-06T01:30:00Z` / `UtcInstant(1588728600000000000)` |
| `2021-04-29` | `2021-04-30` | `2021-04-30T09:30:00+08:00` | `2021-04-30T01:30:00Z` / `UtcInstant(1619746200000000000)` |
| `2022-04-30` | `2022-05-05` | `2022-05-05T09:30:00+08:00` | `2022-05-05T01:30:00Z` / `UtcInstant(1651714200000000000)` |
| `2023-04-29` | `2023-05-04` | `2023-05-04T09:30:00+08:00` | `2023-05-04T01:30:00Z` / `UtcInstant(1683163800000000000)` |

This freezes a finite planning authority only. It does not publish an accepted Calendar artifact, an `available_at`, normalized observations, a MarketBundle, Strategy evidence or deployment authority.

## 2. Official closure notices

The exact official JSON response bytes were retrieved from SZSE and hashed without transformation.

| Coverage | Official SZSE source | Exact Labour Day fact | Bytes / SHA-256 |
| --- | --- | --- | --- |
| 2019 original | [doc 563695](https://www.szse.cn/disclosure/notice/general/t20181220_563695.json) | originally declared `2019-05-01` closed and `2019-05-02` reopening | `8128` / `sha256:5cafeaf34113445a427abbc4a9edce08e172c083931a5ec2a4b897446bab4082` |
| 2019 controlling adjustment | [doc 566376](https://www.szse.cn/disclosure/notice/general/t20190418_566376.json) | expressly adjusts 深证会〔2018〕569号: `2019-05-01` through `2019-05-04` closed, `2019-05-05` weekend-closed, `2019-05-06` reopening | `4815` / `sha256:3c7e0f3e0fa9851bdace2a0f3b617914e0c15ee9ff9d59603e4cf29538ace720` |
| 2020 | [doc 572766](https://www.szse.cn/disclosure/notice/general/t20191220_572766.json) | `2020-05-01` through `2020-05-05` closed; `2020-05-06` reopening | `7789` / `sha256:f386cf8cb0f9e3e9c288b231e3a07b190464917c191687026a29b07ab3ef18af` |
| 2021 | [doc 583950](https://www.szse.cn/disclosure/notice/general/t20201224_583950.json) | `2021-05-01` through `2021-05-05` closed; `2021-05-06` reopening | `8140` / `sha256:2ba52c098b1fb4b3dc96d171c0dfe37f2dac6b8e53b0152cf9795b75749178d1` |
| 2022 | [doc 590321](https://www.szse.cn/disclosure/notice/general/t20211220_590321.json) | `2022-04-30` through `2022-05-04` closed; `2022-05-05` reopening | `8149` / `sha256:b56254ff078f4d5d82d1a258aba98c21a49ee42ea40482590df101103925b6dc` |
| 2023 | [doc 598022](https://www.szse.cn/disclosure/notice/general/t20221227_598022.json) | `2023-04-29` through `2023-05-03` closed; `2023-05-04` reopening | `8374` / `sha256:a56a1050b2d516ad287ac1aa5edb7b9cde3e1e007a4e3d3917056bba24cedab8` |

### 2019 supersession decision

`2019-05-02` is not an effective historical reopen date. It appears in the December 2018 annual notice, but the later official April 2019 notice expressly adjusts that notice before the relevant Gree report publication. The frozen effective Labour Day reopen is `2019-05-06`.

That supersession does not change the 2018-report availability boundary: its official publication date is `2019-04-29`, and the first strictly later open session is `2019-04-30`, before the holiday closure.

## 3. Official open-session corroboration

SZSE's official market-overview report endpoint was queried with exact date parameter `txtQueryDate` and fixed catalog `1803_sczm`, tab `tab1`. A non-empty response contains the exchange's daily market statistics for that exact date. Response bytes are retained only by hash in this research packet; the future implementation must capture or exact-declare them through an accepted Backtest-owned seam.

| Exact date | Role | Rows / stock turnover | Exact official response | Bytes / SHA-256 |
| --- | --- | --- | --- | --- |
| `2019-04-30` | first session after `2019-04-29` publication | `14` / `2,720.52` 亿元 | [query](https://www.szse.cn/api/report/ShowReport/data?SHOWTYPE=JSON&CATALOGID=1803_sczm&TABKEY=tab1&txtQueryDate=2019-04-30) | `4723` / `sha256:e7d30c906216ebd7b2f0308c9ee0b609192fb3f9462c12ab938c64ff33be40b3` |
| `2020-05-06` | first session after the declared `2020-05-01..05` closure | `15` / `4,200.82` 亿元 | [query](https://www.szse.cn/api/report/ShowReport/data?SHOWTYPE=JSON&CATALOGID=1803_sczm&TABKEY=tab1&txtQueryDate=2020-05-06) | `4799` / `sha256:bc75da295c9857ed8d8fa50f00f3e783307649d548fbc2660bad227a11b0d835` |
| `2021-04-30` | first session after `2021-04-29` publication | `13` / `4,667.72` 亿元 | [query](https://www.szse.cn/api/report/ShowReport/data?SHOWTYPE=JSON&CATALOGID=1803_sczm&TABKEY=tab1&txtQueryDate=2021-04-30) | `4559` / `sha256:57cda17f2cdbfba82ddb10cbf595806cc34a498b22b9edc6d50da38dfe232ad7` |
| `2022-05-05` | first session after the declared `2022-04-30..05-04` closure | `14` / `4,924.78` 亿元 | [query](https://www.szse.cn/api/report/ShowReport/data?SHOWTYPE=JSON&CATALOGID=1803_sczm&TABKEY=tab1&txtQueryDate=2022-05-05) | `4683` / `sha256:3212214b8a1cc2b7e102fb3e68460ce037acb772fe9b715652175e0f76255251` |
| `2023-05-04` | first session after the declared `2023-04-29..05-03` closure | `14` / `6,225.27` 亿元 | [query](https://www.szse.cn/api/report/ShowReport/data?SHOWTYPE=JSON&CATALOGID=1803_sczm&TABKEY=tab1&txtQueryDate=2023-05-04) | `4685` / `sha256:d668beafd3aa475345e9c8f60210c9793de3868ef9da11312f1b1316c5b068d5` |

For notice interpretation only, the endpoint also returns non-empty official daily statistics on the adjusted `2019-05-06` reopen (`14` rows, `sha256:357ba1633aaa6bc267817cd96d1599ec820b547ca87ccdf8d3676c55c9af2698`) and the `2021-05-06` reopen (`13` rows, `sha256:a5fde5a3a93390c2fb471b6bf086f27986b520f6ec01d82556244ea58c986f8c`). These two later reopen dates are not the first sessions after the respective Gree publication dates.

## 4. Official 09:30 SessionModel authority

| Applicability | Official source | Controlling text | Bytes / SHA-256 |
| --- | --- | --- | --- |
| 2019 through 2020-03-12 | [2016-09 amendment and republished rules](https://www.szse.cn/lawrules/rule/repeal/rules/P020231230545157383432.pdf) | effective on publication `2016-09-30`; rule 2.4.1 declares Monday-Friday trading except statutory/announced closures; rule 2.4.2 declares continuous auction `09:30-11:30` and `13:00-14:57` | `286418` / `sha256:888302b51ee0f22713c20ac9afb08b72ba7d3fb01945c9f181eede1e4385ff4b` |
| 2020-03-13 through the 2023 transition | [2020 revised rules](https://www.szse.cn/lawrules/rule/repeal/rules/P020231230545338442079.pdf) | 深证上〔2020〕171号, effective on publication `2020-03-13`; rules 2.4.1/2.4.2 preserve the same closure and `09:30` continuous-auction boundary | `279523` / `sha256:348218aab3164083e52057f7313d7d9d7e29f3701b464bc3cc030b600fc23215` |
| from 2023-04-10 | [2023 rule announcement JSON](https://www.szse.cn/lawrules/rule/repeal/rules/t20230217_598773.json) and [attached rules PDF](https://www.szse.cn/lawrules/rule/repeal/rules/W020230217564423808793.pdf) | 深证上〔2023〕98号 makes the rules effective on the first registration-based main-board listing; rule 2.3.1 preserves closure semantics and rule 2.3.2 declares `09:30-11:30` continuous auction | JSON `5349` / `sha256:58ea091197cc7c95eae9c3a0dab2ae80f45a4d54f26a3755810b8672517cdea9`; PDF `620843` / `sha256:7018114a6e11deb239c2a72e71e49defc6e8841b3e2c093b3bbf809282c67222` |

The official [2023 SZSE events record](https://www.szse.cn/aboutus/sse/events/t20240110_605593.json) states that the first main-board registration-system enterprises listed on `2023-04-10`, establishing the transition date before the `2023-05-04` session. Exact response: `123018` bytes / `sha256:a5288222974e04cb25c52f1d2c04059217eee552cbce6e4e91fa7a792f07cf83`.

The SessionModel therefore declares `09:30:00 Asia/Shanghai` as the continuous-auction open for every finite next session above. It does not guess from provider data or a generic market convention.

## 5. Fixed resolution walk

| Report period | Official publication date | Dates excluded before first session | Frozen next session |
| --- | --- | --- | --- |
| `20181231` | `2019-04-29` | none; official daily statistics exist on the immediately following date | `2019-04-30` |
| `20191231` | `2020-04-30` | `2020-05-01..05`, exact official closure notice | `2020-05-06` |
| `20201231` | `2021-04-29` | none; official daily statistics exist on the immediately following date | `2021-04-30` |
| `20211231` | `2022-04-30` | `2022-05-01..04`, within the exact official `04-30..05-04` closure | `2022-05-05` |
| `20221231` | `2023-04-29` | `2023-04-30..05-03`, within the exact official `04-29..05-03` closure | `2023-05-04` |

The resolution is an exact finite enumeration. Runtime weekday arithmetic, guessed holidays and same-day open selection remain forbidden.

## 6. Fail-closed limits

1. The December 2018 declaration of `2019-05-02` must not survive the controlling April 2019 adjustment.
2. Empty market-overview data alone is not closure authority; closure comes from the exact official notices.
3. Non-empty market-overview data proves an exact date has published daily market statistics, not an intraday financial-report publication instant.
4. The trading rules define the continuous-auction boundary, not the financial document's disclosure time.
5. This evidence covers only the five enumerated report dates and next sessions. It is not a general SZSE Calendar provider or terminal-set proof.
6. A future implementation must exact-bind retained source bytes/hashes or an accepted immutable Calendar artifact. URL refetch without identity validation is insufficient.
7. No historical `available_at` exists until the Backtest-owned availability/normalization operation is implemented, reviewed and accepted.
8. The `20211231` financial declaration remains unavailable because of `DEBT_SCOPE_INCOMPLETE`; Calendar completeness cannot override that earlier typed failure.

## 7. Decision

The Calendar/Session evidence needed to freeze historical normalization is complete for this fixed issuer and finite period set. The next safe lane is a symbol-level historical normalization packet for `20181231`, `20191231`, `20201231` and `20221231`, preserving the canonical `20211231` failure and all predecessor identities.
