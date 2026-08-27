# Research: Quality-BBAND 2017–2025 formal historical S1 authority feasibility

- **Official-public decision:** `PUBLICLY_DATA_INFEASIBLE`
- **Owner amendment, 2026-08-27:** retained Tushare fields are approved as the controlling project S1 authority where present; see `quality-bband-tushare-s1-authority-pivot-v1.md`
- **Official exchange/CSRC S1 authority:** `false`
- **Strategy / Fold / Validation authority:** `false`
- **Scope:** frozen source-bounded screen dates `2017-05-02`, `2018-05-02`, `2019-05-06`, `2020-05-06`, `2021-05-06`, `2022-05-05`, `2023-05-04`, `2024-05-06`, `2025-05-06`; these are not accepted general Calendar authority, and exact decision instants remain Fold-manifest/Calendar inputs

## Summary

Public official SSE/SZSE pages and announcements can strongly prove individual listing, delisting, A/B-share and board facts, while official daily reference-file specifications show that the exchanges internally publish the right product/type/list-date/status fields. No documented public unauthenticated historical daily reference-file archive with complete pagination, revisions and terminal/absence semantics for both venues was located in the reviewed official sources.

The decisive gap is official issuer-level CSRC industry history after `2021 Q3`: the newest issuer-level quarterly result located in the reviewed CSRC directory is `2021年3季度上市公司行业分类结果`. No later complete issuer-assignment series with revision and terminal semantics was located in the cited official public sources; the directory itself does not prove that no later page exists elsewhere. The 2024 replacement standard defines a taxonomy but does not publish historical issuer assignments. Therefore no accepted public source currently supports complete point-in-time exclusion of CSRC major category `J 金融业` for the 2022–2025 screens. A licensed/procured official-source contract is required; current Tushare/S0/annual-roster artifacts remain useful discovery evidence only.

## Existing-repo comparison

The repository already reaches the correct boundary:

- `platform/research/quality-bband-annual-structural-roster-assessment-v1.md` retains source-bounded 2017–2025 annual rosters and a provisional 2,845-Instrument union, but explicitly keeps `FORMAL_S1_FALSE`.
- `platform/implementation/plans/quality-bband-annual-structural-roster-source-sentinel-v1.md` states that `bak_basic` row presence is not exchange listing authority, `market` is not historical board authority, provider industry is not official CSRC history, and completeness/absence/revision closure are false.
- `platform/research/quality-bband-s0-lightweight-catalog-assessment-v1.md` correctly refuses to project current board and industry backward.
- `platform/research/quality-bband-full-market-data-infeasibility-v1.md` already identifies historical listed/delisted catalog, board and CSRC-industry closure as irreducible blockers.

This research confirms those nonclaims using only official/public primary sources. It does not upgrade Tushare, current state, bars, names or local artifacts into authority.

## Findings

### 1. Public exchange sources contain the right facts, but not a complete historical public contract

1. **Current stock lists distinguish A shares, B shares, board and listing date.** SZSE’s official stock list presents separate A-share and B-share columns, board and listing dates; its official suspended/terminated page presents security code, name, listing date and termination date. These are strong current/event facts, not an immutable as-of archive. [SZSE stock list](https://www.szse.cn/market/product/stock/list/index.html) [SZSE suspended/terminated list](https://www.szse.cn/market/stock/suspend/index.html)

2. **SSE similarly publishes current and terminated-company views and listing/delisting announcements.** Individual exchange notices are competent evidence for a known event, but the public pages do not document a full export identity, revision ID, page-count closure or a guarantee that an empty search means no event. [SSE stock list](https://www.sse.com.cn/assortment/stock/list/share/) [SSE suspended/terminated list](https://www.sse.com.cn/assortment/stock/list/delisting/) [SSE listing/delisting announcements](http://www.sse.com.cn/disclosure/announcement/listing/)

3. **The exchanges’ daily reference-file specifications would solve much of identity/type/date reconstruction if the files were procured.** SSE’s `cpxx0201MMDD.txt` is an opening-time product-basic-information file that includes suspended products and fields for market kind (`ASHR`/`BSHR`), security type, subtype, currency and SSE listing date; it is distributed through market-participant channels such as MDGW/ztDisk. [SSE market-data file specification](https://www.sse.com.cn/services/tradingtech/development/c/10822594/files/2096257019bf484f9b9935fa73f94721.pdf)

4. **SZSE’s `securities.xml` likewise contains all listed securities with listing date, security category, currency and security-status fields and is sent before market open.** The public document specifies the schema, not a complete public historical file archive. [SZSE data-file exchange specification](https://docs.static.szse.cn/www/marketServices/technicalservice/notice/W020180523596999490643.pdf)

5. **SSE historical data is an official subscription product, not a complete free public path.** SSE states that historical data is available on a yearly subscription basis and directs subscribers to an order form; SSE Info states that its historical-data service also supplies securities basic-information files. This is the clearest official procurement route for Shanghai historical daily identities. [SSE historical-data products](https://english.sse.com.cn/markets/dataservice/products/) [SSE Info historical data](https://www.sseinfo.com/services/assortment/historical/)

6. **Public yearbooks are useful controls, not screen-date rosters.** SSE and SZSE publish long yearbook series with board-level totals and company tables, but they are year-end/statistical publications and do not establish the exact full roster on each early-May screen. [SSE statistical yearbooks](https://star.sse.com.cn/aboutus/publication/yearly/) [SZSE statistical yearbooks](https://www.szse.cn/market/periodical/year/)

**Result:** items (1) ordinary CNY A-share identity, (2) exact listing/delisting interval and (3) board/product history are individually provable for known securities, but public pages do not provide a machine-verifiable, exhaustive historical closure for every potentially eligible security on every screen.

### 2. Board history is reconstructable in principle, but current labels cannot be projected backward

1. **SZSE’s official market history says the SME Board was created within the Main Board in May 2004 and formally merged with the Main Board on 2021-04-06.** The merger kept issuance/listing conditions, investor thresholds, trading mechanism, codes and abbreviations unchanged. Thus a present-day `主板` label does not by itself tell whether a code was an SME-Board security on the 2017–2020 screens. [SZSE market-system history](https://www.szse.cn/www/marketServices/listing/select/marketSystem/)

2. **STAR did not trade until 2019-07-22.** It cannot contaminate the 2017–2019 early-May screens, but must be excluded from 2020 onward through historical product/board evidence rather than current code heuristics alone. [SSE first STAR listings announcement](http://www.sse.com.cn/aboutus/mediacenter/hotandd/c/c_20190705_4858654.shtml)

3. **ChiNext has distinct official listing rules and issuer listing notices identify the board and A-share type.** These documents are reliable event evidence but are impractical as the sole full-market closure mechanism without a complete announcement inventory. [SZSE ChiNext Listing Rules (2018)](http://docs.static.szse.cn/www/aboutus/trends/news/W020180423508135188665.pdf)

**Result:** a licensed daily static/reference feed can establish Main Board/SME/ChiNext/STAR/B-share/product history deterministically. Public current labels plus code ranges are not enough for formal historical S1.

### 3. Fifth listing anniversary is arithmetic after authoritative listing identity is closed

The fifth-anniversary predicate itself needs no separate vendor field:

```text
eligible_on_screen D iff first ordinary-A-share listing date <= D minus 5 calendar years
```

It must use the first effective listing date of the same canonical Instrument and must not silently reset or inherit age across code changes, re-listings, absorbed companies, B-to-A changes or a different security issued after restructuring. SSE/SZSE listing notices and daily reference fields can prove known cases; the missing part is a complete canonical event inventory and issuer/security continuity contract.

Suspensions, ST/risk names and other status labels are **not** required merely to calculate age. They should only enter exception review where current names, missing rows, code reuse, re-listing or restructuring could otherwise cause a survivorship/identity error.

### 4. CSRC industry history is the decisive public blocker

1. **The newest issuer-level quarterly result located in the reviewed CSRC directory is 2021 Q3.** No later complete issuer-assignment series with revision and terminal semantics was located in the cited official public sources. The dynamic directory itself is not terminal-absence authority and does not prove that no later page exists elsewhere. [CSRC listed-company industry-result directory](https://www.csrc.gov.cn/csrc/c100103/common_list.shtml) [2021 Q3 result page](https://www.csrc.gov.cn/csrc/c100103/c1558619/content.shtml) [2021 Q3 PDF](https://www.csrc.gov.cn/csrc/c100103/c1558619/1558619/files/1638277734844_11692.pdf)

2. **Availability timing matters for the early screens.** The 2017 Q1 result was published only on 2017-06-01 and the 2018 Q1 result only on 2018-05-21, both after their source-bounded screen dates; those files cannot authorize the earlier screens. The exact latest pre-screen publications for 2017 and 2018 remain unpinned. The 2019 Q1 result was published 2019-04-19, the 2020 Q1 result 2020-04-14 and the 2021 Q1 result 2021-04-14, but date-only publication evidence must still map conservatively to `available_at` through accepted Calendar/Session authority. [2017 Q1](http://www.csrc.gov.cn/csrc/c100103/c1452007/content.shtml) [2018 Q1](https://www.csrc.gov.cn/csrc/c100103/c1452003/content.shtml) [2019 Q1](https://www.csrc.gov.cn/csrc/c100103/c1451999/content.shtml) [2020 Q1](https://www.csrc.gov.cn/csrc/c100103/c1451995/content.shtml) [2021 Q1](https://www.csrc.gov.cn/csrc/c100103/c29a6845e0d0b4912adcc1cdfa5f679eb/content.shtml)

3. **The 2024 standard does not repair the missing issuer history.** `JR/T 0020—2024` supersedes `JR/T 0020—2004` in the financial-industry statistical standard lineage. The CSRC announcement separately controls the effective/repeal transition from the then-operative 2012 listed-company issuer-classification guidance. The 2024 document is taxonomy authority, not a historical issuer-assignment/revision table, and it was published after the 2024-05-06 source-bounded screen date. [CSRC Announcement No. 16](http://www.csrc.gov.cn/csrc/c101954/c7520291/content.shtml) [JR/T 0020—2024 PDF](https://www.csrc.gov.cn/csrc/c101954/c7520291/7520291/files/%E9%99%84%E4%BB%B61%EF%BC%9A%E3%80%8A%E4%B8%8A%E5%B8%82%E5%85%AC%E5%8F%B8%E8%A1%8C%E4%B8%9A%E7%BB%9F%E8%AE%A1%E5%88%86%E7%B1%BB%E4%B8%8E%E4%BB%A3%E7%A0%81%E3%80%8B.pdf)

4. **Annual reports or exchange current `所属行业` columns cannot supply terminal closure.** They may confirm a known issuer’s category, but do not prove that every eligible issuer was assigned under one effective standard as of a screen, that no unpublished/revised assignment existed, or that missing records are non-financial.

**Result:** pinned official documents support bounded issuer-classification evidence for some 2019–2021 screens, subject to conservative `available_at`; the exact latest pre-screen 2017 and 2018 inputs remain unresolved. No reviewed public source completely establishes the issuer-level CSRC major-industry state and revision history for all nine screens. This forces `PUBLICLY_DATA_INFEASIBLE` under the current authority contract.

## Annual screen assessment

| Screen | Identity/listing/board public evidence | Latest usable public CSRC assignment evidence | Formal screen conclusion |
| --- | --- | --- | --- |
| 2017-05-02 | Known events provable; no public daily full-roster closure | Exact latest pre-screen publication remains unpinned; 2017 Q1 was not public until 2017-06-01 | `INCOMPLETE_PUBLIC` |
| 2018-05-02 | Same; current Main Board labels cannot absorb historical SME Board | Exact latest pre-screen publication remains unpinned; 2018 Q1 was not public until 2018-05-21 | `INCOMPLETE_PUBLIC` |
| 2019-05-06 | Known events provable; STAR not yet trading | 2019 Q1 published 2019-04-19 | `INCOMPLETE_PUBLIC` |
| 2020-05-06 | STAR/ChiNext/Main Board split needs historical reference records | 2020 Q1 published 2020-04-14 | `INCOMPLETE_PUBLIC` |
| 2021-05-06 | Must encode 2021-04-06 SME/Main Board merger | 2021 Q1 published 2021-04-14 | `INCOMPLETE_PUBLIC` |
| 2022-05-05 | Public listing pages/events still lack full daily terminal closure | No complete 2022 issuer roster was located; newest located directory item is 2021 Q3, and the directory is not terminal authority | `MISSING_INDUSTRY_AUTHORITY` |
| 2023-05-04 | Same | No complete 2023 issuer roster was located in the reviewed official sources; directory absence is nonterminal | `MISSING_INDUSTRY_AUTHORITY` |
| 2024-05-06 | Same | No complete pre-screen 2024 issuer roster was located; the replacement standard was not yet published and is not an assignment table | `MISSING_INDUSTRY_AUTHORITY` |
| 2025-05-06 | Same | No complete 2025 issuer-assignment/revision roster was located in the reviewed official sources; the new standard is taxonomy, not assignment authority | `MISSING_INDUSTRY_AUTHORITY` |

No annual screen reaches formal S1 because the listing/board side lacks public full-market closure; 2022–2025 additionally lack issuer-level official CSRC industry authority.

## Access, pagination, revision, archive and license assessment

- **Public current pages:** unauthenticated and useful for interactive verification, but dynamic/current; no official public contract located for request identity, immutable as-of date, total pages/export hash, correction lineage or zero-result semantics.
- **Official announcements/PDFs:** stable evidence for identified events; no public cross-venue canonical security identity, successor link or exhaustive event terminal set located.
- **Daily exchange files:** documented schemas contain the required fields, but distribution is framed as market-participant/market-data service rather than a complete public historical download.
- **SSE licensed path:** official historical data is subscription-based; SSE Info explicitly includes securities-basic-information files. Redistribution and derived-artifact rights must be negotiated rather than inferred from website availability.
- **SZSE path:** the public technical specification documents `securities.xml`; a historical static/reference-file supply and licensing agreement must be obtained directly from SZSE or its authorized data service.
- **CSRC:** public quarterly PDFs have strong document identity. The newest issuer-level result located in the reviewed directory is 2021 Q3, but the directory is not terminal-absence authority. The 2024 standard supplies taxonomy revision authority only.
- **CSDC:** its public securities-query service is aimed at investor account/holding queries and generally requires becoming a network user for most services; no public full-market historical security-master/industry-assignment API was located in the reviewed materials. [CSDC securities query service](http://www.chinaclear.cn/zdjs/sfwzq/201306/197c82ddec6a4dc58d5b953f19339c7d.shtml)

## Exact missing authority and required procured contract

Procure one contract, or a coordinated set of contracts, containing all of the following:

1. **SSE and SZSE historical daily security master/reference files.** For the nine-screen S1 task, require exact reference snapshots for every frozen screen plus complete predecessor/listing/restructure history needed to establish identity and fifth-anniversary age. If the same procurement is claimed to unblock complete Fold A/B S0 coverage, extend the contracted applicable interval to `[2010-01-04, 2026-04-01)` and the exact Fold manifests rather than using the narrower nine-screen scope.
2. Stable fields for a canonical `InstrumentId` independent of code/name changes, venue security ID, canonical issuer ID, security type/subtype, A/B/CDR/product class, currency, board/market layer, first listing date, last trading date, delisting/effective date, source-file applicable date, and normal/suspension/resumption/risk-warning/ST/delisting-terminal status history.
3. **Event lineage** for code/name changes, mergers, absorption, re-listing, board changes and replacement securities, with economic effective intervals, exact `available_at`, immutable source hashes and correction/supersession relations. Provider-native revision IDs may be null when immutable source identities and derived canonical revision IDs are retained.
4. **CSRC issuer-level industry assignments** covering every screen under the then-effective regime and standard. Required fields are issuer/security identity, category code including major category `J`, economic effective interval, exact `available_at`, source hashes, regime/standard version and correction/supersession relation. Distinguish the then-operative 2012 issuer-classification guidance from the `JR/T 0020—2004` to `JR/T 0020—2024` statistical-standard lineage.
5. Full export identities: requested scope, schema/version, generation timestamp, total record/file count, page/file manifests, checksums, explicit empty scopes, retry/reissue rules and provider declaration that the delivered snapshot is complete for the contracted interval.
6. Accepted Calendar/Session authority for converting date-only publication evidence to conservative `available_at` and exact decision instants.
7. A frozen SME-Board rule for the pre-2021 screens: the implementation packet must state whether the historically distinct SME Board satisfies the strategy’s `Main Board` predicate; current post-merger labels cannot decide this retroactively.
8. License terms permitting internal backtesting, immutable retention, hashing, audit/replay and storage of derived normalized facts; credentials must remain environment-only and excluded from artifacts/logs.

A contract that only supplies current master data, current industry, price bars, or “best available” vendor history without official-source lineage and terminal completeness does not close S1.

## Acquisition and validation sequence after procurement

1. Freeze contract/version, exact date range, venue scope and expected daily-file manifest.
2. Acquire raw SSE/SZSE reference files and industry-assignment exports; write raw bytes first and receipt last, no clobber.
3. Verify file/page totals, hashes, schema versions, applicable dates, explicit empty scopes and provider completion declaration.
4. Normalize security identities without code heuristics; preserve all raw codes/names and successor/restructure links.
5. Build non-overlapping effective intervals for listing, board/product, currency/type and industry assignment; reject forks, gaps and unclosed terminals.
6. For each annual screen, select only revisions with `available_at <= decision_instant`; preserve classification reference/effective time separately. Date-only publication evidence must map conservatively through accepted Calendar/Session authority. Then require: active ordinary CNY A share, the frozen eligible-board rule, fifth anniversary met and CSRC major category not `J`.
7. Reconcile screen totals and event counts against official yearbooks/current-event pages as controls only; controls may detect errors but cannot fill missing records.
8. Produce an exact-cover report listing every input Instrument, exclusion reason and source revision. Any unresolved code, restructure, industry gap or terminal mismatch fails the whole screen rather than silently dropping the security.

## Sources

### Kept

- [CSRC listed-company industry-result directory](https://www.csrc.gov.cn/csrc/c100103/common_list.shtml) — official discovery/index evidence; the newest issuer-level result located in the reviewed directory is 2021 Q3, but the directory is not terminal-absence authority.
- [CSRC 2017–2021 Q1 publication pages](http://www.csrc.gov.cn/csrc/c100103/c1452007/content.shtml) — authoritative date-level publication evidence; exact `available_at` still requires conservative Calendar/Session mapping, and separate exact URLs are cited above.
- [JR/T 0020—2024](https://www.csrc.gov.cn/csrc/c101954/c7520291/7520291/files/%E9%99%84%E4%BB%B61%EF%BC%9A%E3%80%8A%E4%B8%8A%E5%B8%82%E5%85%AC%E5%8F%B8%E8%A1%8C%E4%B8%9A%E7%BB%9F%E8%AE%A1%E5%88%86%E7%B1%BB%E4%B8%8E%E4%BB%A3%E7%A0%81%E3%80%8B.pdf) — authoritative taxonomy revision and effective date, but not assignments.
- [SSE market-data file specification](https://www.sse.com.cn/services/tradingtech/development/c/10822594/files/2096257019bf484f9b9935fa73f94721.pdf) — exact product-basic fields and restricted distribution channels.
- [SZSE data-file exchange specification](https://docs.static.szse.cn/www/marketServices/technicalservice/notice/W020180523596999490643.pdf) — exact `securities.xml` fields.
- [SSE/SSE Info historical-data product pages](https://www.sseinfo.com/services/assortment/historical/) — official licensed procurement route.
- SSE/SZSE stock, delisting and yearbook pages — official controls and event evidence.

### Dropped as authority

- Tushare `stock_basic`, `bak_basic`, provider `market` and provider `industry` — not official exchange/CSRC authority and no historical revision/terminal closure.
- Current stock lists projected backward — survivorship and historical-board error.
- Code-range-only board inference — fails SME/Main Board history, products, exceptional/restructured identities and formal source lineage.
- Bar presence or current/delisted status — cannot prove listing identity, absence or continuous interval.
- Annual-report self-description as full-market industry closure — issuer-specific and lacks complete revision/absence semantics.
- Search-engine absence — discovery aid only, never terminal authority.

## Gaps

The exact commercial product name, price, delivery mechanism and redistribution terms for the required SZSE historical static/reference files and post-2021 issuer-level CSRC industry assignment history were not located in the reviewed public materials. Next step is a procurement/RFI to SSE Info, SZSE’s authorized market-data service, and CSRC and CSDC—or an officially authorized provider if identified—using the required contract fields above; no credentialed probe is justified before that contract exists.

## Final conclusion

```text
PUBLICLY_DATA_INFEASIBLE
formal_s1_authority = false
strategy_authority = false
survivorship_bias_safe = false
absence_authority = false
revision_closure_complete = false
```

Public official material is sufficient to design and audit a procured S1 pipeline and to verify individual known events. It is not sufficient to publish complete, point-in-time, survivorship-safe annual S1 rosters for all nine screens.
