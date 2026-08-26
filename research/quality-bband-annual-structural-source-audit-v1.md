# Quality + B-Band annual structural source audit v1

- **Status:** `SOURCE_BOUNDED_S1_CANDIDATE_AVAILABLE_FROM_2017 / FORMAL_S1_AUTHORITY_MISSING`
- **Checked:** 2026-08-26
- **Scope:** annual primary-screen membership/industry/listing-age inputs

## 1. Sources reviewed

- Tushare [`bak_basic`](https://tushare.pro/document/2?doc_id=262): historical daily stock list, documented from 2016, maximum `7,000` rows, formal access threshold `5,000` points; no revision, absence, pagination-terminal or completeness authority.
- Tushare [`trade_cal`](https://tushare.pro/document/2?doc_id=131): venue calendar fields `exchange,cal_date,is_open,pretrade_date`; no correction/finality identity.
- Tushare [`stock_basic`](https://tushare.pro/document/2?doc_id=25): current listed/delisted metadata, not historical-as-of state.
- CSRC [listed-company industry classification results](https://www.csrc.gov.cn/csrc/c100103/common_list.shtml), including official quarterly PDFs visible for at least 2013–2021.
- CSRC [`上市公司行业分类指引（2012年修订）`](https://www.csrc.gov.cn/csrc/c101864/c1024632/content.shtml).

## 2. Annual primary-screen dates

A source-bounded SSE `trade_cal` probe over `20160430..20250510` returned `3,298` terminal rows. The first returned open date strictly after April 30 is:

| Year | Screen date |
| --- | --- |
| 2016 | `20160503` |
| 2017 | `20170502` |
| 2018 | `20180502` |
| 2019 | `20190506` |
| 2020 | `20200506` |
| 2021 | `20210506` |
| 2022 | `20220505` |
| 2023 | `20230504` |
| 2024 | `20240506` |
| 2025 | `20250506` |

These are provider calendar observations, not accepted general Calendar authority.

## 3. Full-date `bak_basic` probe

Exact requested fields:

```text
trade_date,ts_code,name,industry,list_date
```

| Screen date | Returned rows | Unique codes | Null industry | Result |
| --- | ---: | ---: | ---: | --- |
| `20160503` | `0` | `0` | `0` | explicit source-bounded gap |
| `20170502` | `3,232` | `3,232` | `0` | usable bounded response |
| `20180502` | `3,518` | `3,518` | `0` | usable bounded response |
| `20190506` | `3,622` | `3,622` | `0` | usable bounded response |
| `20200506` | `3,850` | `3,850` | `0` | usable bounded response |
| `20210506` | `4,326` | `4,326` | `3` | bounded response with nulls |
| `20220505` | `4,719` | `4,719` | `0` | usable bounded response |
| `20230504` | `4,994` | `4,994` | `0` | usable bounded response |
| `20240506` | `5,364` | `5,364` | `0` | includes BSE rows |
| `20250506` | `5,415` | `5,415` | `0` | includes BSE rows |

`20161230` returned `3,071` rows, confirming that the documented 2016 history does not mean every 2016 trading date is populated.

Returned `list_date="0"` occurs for prelisting/provider-unknown rows: `26,5,12,17,39,10,22,3,5` rows respectively from 2017 through 2025. It must be retained as an unknown sentinel, not rejected or interpreted as a listing date.

## 4. Provider roster is not listing authority

Joining each `bak_basic` response to the retained 2026 S0 `stock_basic` capture leaves unmatched SSE/SZSE codes. Examples include:

- historical renamed/restructured names such as `601313.SH 江南嘉捷`, `000022.SZ 深赤湾A`, `000043.SZ 中航地产/中航善达`;
- rows such as `688688.SH 蚂蚁集团`, `603361.SH 浙江国祥` and other names that were not normal listed trading members on the queried date;
- recurring `300114.SZ 中航电测`, absent from the current S0 response identity set.

Therefore `bak_basic` row presence is a provider historical-list observation, not proof of exchange listing/tradability. Missing S0 join identity is not automatically an error or exclusion.

## 5. Advisory staged funnel

Using current S0 `market`, `bak_basic.list_date`, and provider `industry` only as nonauthority approximations:

| Screen | Raw rows | Current-S0 mainboard match | Listed five years | Excluding `银行/保险/证券/多元金融` |
| --- | ---: | ---: | ---: | ---: |
| 2017 | `3,232` | `2,591` | `2,052` | `1,995` |
| 2018 | `3,518` | `2,791` | `2,098` | `2,034` |
| 2019 | `3,622` | `2,861` | `2,119` | `2,053` |
| 2020 | `3,850` | `2,934` | `2,218` | `2,143` |
| 2021 | `4,326` | `3,083` | `2,300` | `2,224` |
| 2022 | `4,719` | `3,152` | `2,526` | `2,434` |
| 2023 | `4,994` | `3,203` | `2,705` | `2,612` |
| 2024 | `5,364` | `3,199` | `2,738` | `2,635` |
| 2025 | `5,415` | `3,181` | `2,776` | `2,667` |

This demonstrates useful workload reduction but cannot become an S1 manifest because board and industry inputs are not historical authorities.

## 6. CSRC industry evidence

Official quarterly CSRC PDFs can supply authoritative classifications for the companies and quarter shown. Public search located results from 2013 through 2021, including 2013 Q3, 2014 Q1/Q2, 2016 Q1/Q2/Q4, 2017 Q4, 2018 Q4, 2019 Q4, 2020 Q1–Q4 and 2021 Q1–Q3.

Remaining gaps:

- no reviewed complete machine index/terminal declaration for every required quarter;
- publication date and classification reference/effective date must remain separate;
- no reviewed official 2022–2025 company-assignment series was found;
- PDFs include A/B and multiple boards, so exact product filtering and canonical Instrument mapping are still required.

## 7. Decision

PR #11 and SourceSnapshot `sha256:22585fa4c2070d87544f0ba977be757770aeeaad5bead30188317c1794680ee8` now freeze `trade_cal` plus the ten annual `bak_basic` responses, including the explicit 2016 zero-row gap and retained `list_date="0"` unknowns. They support development-only historical funnel estimates for 2017–2025.

It cannot support formal Fold A/B S1 because:

- `bak_basic` has no usable 2010–2015 annual screens and returns zero at the 2016 screen;
- returned rows do not equal exchange-listed membership;
- board history is absent;
- provider industry is not official historical CSRC classification;
- revision and terminal closure remain missing.
