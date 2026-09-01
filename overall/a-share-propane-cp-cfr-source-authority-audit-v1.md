# A-share imported-propane CP/CFR source-authority audit v1

## Scope

Audit a point-in-time (PIT), first-party historical input-cost series for A-share propane/PDH causal research. The required series must be continuous, carry exact historical publication timestamps, preserve the originally published document/response, and avoid current-page backfill. Three different objects are kept separate:

- **Saudi/Qatari CP:** a seller-set monthly contract price, normally quoted in USD/t on an export basis.
- **China import unit value:** Customs import value divided by quantity for liquefied propane; this is a monthly realized border statistic, not CP. China Customs values imports on a **CIF** basis, so it is only CFR-like and includes insurance.
- **DCE PG:** a RMB/t domestic exchange price for a deliverable LPG product. It is a market proxy, not Donghua Energy's physical imported-propane purchase cost.

No margin coefficient, trading rule, strategy run, or backtest is authorized by this audit.

## Candidate sources

### 1. Saudi Aramco monthly propane CP — first-party seller

- **Owner / seam checked:** Saudi Arabian Oil Company; official [news archive](https://www.aramco.com/en/news-media/news), [customer resources](https://www.aramco.com/en/workingwithus/customers), and official-domain searches for `propane`, `LPG`, `contract price`, and `Saudi Aramco CP`.
- **Coverage / frequency:** CP is understood externally as monthly, but no official public historical price archive, API, or stable monthly-notice document seam was located on Aramco's site.
- **Definition / currency / unit / basis:** propane CP, generally described by market infrastructure as USD/t and FOB Saudi Arabia; those decisive details were found only in non-first-party market sources, not an Aramco-retained notice series.
- **Timestamp / revisions / retention:** no demonstrable official archive of immutable notices with publication timestamps or revision history. Current official pages cannot reconstruct historical PIT observations.
- **Licence:** no series-specific reuse or redistribution permission located.
- **Assessment:** **blocked**. Reuters articles saying Aramco “set” a monthly CP and ICE's [Propane, Argus Saudi CP Future](https://www.ice.com/products/6590316/Propane-Argus-Saudi-CP-Future) corroborate market usage but are third-party/commercial authority and cannot substitute for seller originals.

### 2. QatarEnergy monthly LPG seller prices — first-party alternative seller

- **Owner / seam checked:** QatarEnergy; official [media centre](https://www.qatarenergy.qa/en/MediaCenter/Pages/default.aspx), [publications](https://www.qatarenergy.qa/en/MediaCenter/Pages/Publications.aspx), and official-domain searches for monthly propane/LPG prices.
- **Coverage / frequency:** no public continuous monthly propane-price notice archive or API was located. Annual reviews establish QatarEnergy as an LPG producer/exporter but do not supply a PIT monthly price series.
- **Definition / currency / unit / basis:** not established by an official retained series.
- **Timestamp / revisions / retention:** not established; no immutable monthly originals or historical version ledger found.
- **Licence:** no price-series redistribution permission found.
- **Assessment:** **blocked** and not usable to fill Aramco CP history.

### 3. General Administration of Customs of China (GACC) — monthly propane import value and quantity

- **Owner / exact seams:** GACC [statistical query platform](http://stats.customs.gov.cn); official [2023 access-address notice](http://gdfs.customs.gov.cn/customs/302249/302266/302267/4835768/index.html); official [platform introduction](http://www.customs.gov.cn/chengdu_customs/519425/fdzdgknr1/zcjd20/bg88/5581624/index.html); annual publication schedules, e.g. [2024](http://www.customs.gov.cn/customs/2024-02/22/article_2025121120022936465.html) and [2025](http://gdfs.customs.gov.cn/customs/302249/zfxxgk/2799825/302274/tjzd/6335643/index.html); [2024 monthly-report compilation note](http://www.customs.gov.cn/customs/2024-03/07/article_2025121120023033741.html).
- **Coverage / frequency:** the official platform introduction states that monthly data can be queried from **January 2015**. Earlier annual schedules exist, but the inspected online query seam does not expose an immutable historical response for every original release.
- **Commodity:** China tariff code **27111200, 液化丙烷 (liquefied propane)**; official tariff evidence: [2022 MFN tariff table](http://gszgs.customs.gov.cn/gss/fileDir/resource/cms/article/2692452/4119473/2022011216271628613.pdf). The comparable international HS6 is 271112.
- **Currency / unit:** platform output provides import value and quantity; USD value and mass quantity can be used to calculate USD/t after unit normalization. Exact selected fields and units must be retained with each raw response.
- **Delivery basis:** the compilation note's decisive rule is: **“进口货物按到岸价格统计，出口货物按离岸价格统计”** (imports are recorded at CIF; exports at FOB). Therefore value/quantity is a **CIF China import unit value**, not seller CP and not strictly CFR.
- **Publication timestamps:** annual schedules provide planned dates for quick reports, monthly reports, and online-query releases. They do not by themselves bind a specific HS 27111200 response to its exact first publication time or preserve what that response contained on that date.
- **Revision behavior:** Customs statistics can be corrected/recompiled under the [Customs Statistical Work Administrative Provisions, GACC Order 242](http://www.customs.gov.cn/customs/2019-01/17/article_2025121120022519818.html). The live query returns the current database state; no public per-observation revision ledger or vintage endpoint was demonstrated.
- **Licence / retention:** saving a bounded query response is technically feasible, but a clear bulk-reuse/redistribution licence for the platform output was not located. Automated access also returned HTTP 412/session-oriented endpoints during this audit. More importantly, saving today's response cannot recreate unretained historical vintages.
- **Assessment:** **authoritative for current official CIF unit values, but PIT-blocked** for causal backtesting. It could support future prospective capture once timestamp, retention, revision, and reuse controls are resolved.

### 4. UN Comtrade — official intergovernmental re-dissemination of reporter data

- **Owner / seams:** UN Statistics Division; [UN Comtrade API documentation](https://uncomtrade.org/docs/un-comtrade-api), [data availability](https://uncomtrade.org/docs/data-availability), [content of data](https://uncomtrade.org/docs/content-of-data), [trade valuation](https://uncomtrade.org/docs/trade-valuation), and public API pattern `https://comtradeapi.un.org/public/v1/preview/C/M/HS?period=YYYYMM&reporterCode=156&flowCode=M&partnerCode=0&cmdCode=271112`.
- **Coverage / frequency / definition:** reporter-dependent monthly merchandise trade, HS6 271112 “Propane, liquefied,” with reported trade value and net weight/quantity fields. China is reporter 156; imports are flow `M`.
- **Currency / unit / basis:** trade value is in USD and weight is normally kg; UN guidance applies CIF-type valuation to imports. It is an import unit value, not CP.
- **Timestamp / revisions:** the official [`getDa` data-availability endpoint](https://comtradeapi.un.org/public/v1/getDa/C/M/HS?reportercode=156&period=202401) exposes dataset-level `firstReleased`, `lastReleased`, checksum and record count. A retained direct smoke found China 2024-01 first/last releases at `2025-06-12T01:47:07.73` / `2025-07-05T01:13:58.7`, and 2024-12 at `2025-06-12T21:27:01.16` / `2025-07-04T23:51:36.4233333`. The official Python client implements these fields in [`DataAvailability.py`](https://github.com/uncomtrade/comtradeapicall/blob/main/src/comtradeapicall/DataAvailability.py). This is useful release metadata, but the public seam returns the current dataset and does not reproduce the values of each earlier release. Current values therefore cannot be assigned to `firstReleased`; a retained response is usable no earlier than `max(lastReleased, observed_at)` and only for that frozen response.
- **Timeliness / continuity smoke:** at the audit cutoff the China monthly availability seam ended at `202412`; `202501` returned zero availability and trade rows. The 2024-12 propane aggregate also stored mass in `altQty` while `netWgt` was missing, requiring explicit field/unit normalization. Tracked attestation is in [`a-share-propane-cp-cfr-source-smoke-v1.json`](a-share-propane-cp-cfr-source-smoke-v1.json); exact raw responses and the 2024-01 HTTP headers are retained locally under the Git-ignored `overall/a-share-propane-cp-cfr-source-smoke-v1-raw/`. Even a prospective Comtrade proxy would therefore be stale relative to the 2026-08 research cutoff and is not an uninterrupted physical-cost series.
- **Licence / retention:** JSON/CSV responses are retainable, and UN Comtrade publishes use/re-dissemination guidance ([FAQ](https://uncomtrade.org/docs/faqs-on-use-and-re-dissemination)); compliance still requires applying its attribution and redistribution conditions. UN Comtrade is also a re-disseminator, not the first-party Chinese reporter or propane seller.
- **Assessment:** useful delayed cross-check and prospective capture seam; **not accepted** as the requested first-party historical PIT authority.

### 5. Dalian Commodity Exchange PG — official exchange proxy only

- **Owner / seams:** DCE [PG contract and delivery-quality standard](http://www.dce.com.cn/dalianshangpin/sspz/yhsyq/hyygz7622/6210766/index.html) and [official contract-rule explanation](http://www.dce.com.cn/dalianshangpin/zt/cydhzt62/zghgcyqhdh/6221598/6221602/6221664/index.html).
- **Coverage / frequency / definition:** exchange futures quotations; deliverable LPG quality under DCE rules. The official contract page specifies **20 t/lot**, **RMB/t**, and a **RMB 1/t** minimum tick. The rule explanation also shows that deliverability depends on propane composition and grade adjustments; it is not a bill for a named import cargo.
- **Basis / timestamp / revisions:** exchange-traded domestic market price with exchange timestamps; neither FOB seller CP nor CIF/CFR China Customs import value.
- **Licence / retention:** official contract/rule documents are retainable; market-data redistribution terms must be checked separately.
- **Assessment:** **excluded by definition**. PG may remain explicitly labelled as a domestic fuel-LPG proxy, never as Donghua Energy physical imported-propane cost.

## Evidence table

| Source family | Decisive evidence / location | Continuous PIT from first-party originals? | Audit result |
| --- | --- | ---: | --- |
| Saudi Aramco CP | Official news/customer seams contain no located monthly CP archive; only Reuters/Argus/ICE corroboration was found | No | Blocked |
| QatarEnergy seller price | Official media/publication seams contain no located continuous monthly propane-price archive | No | Blocked |
| GACC HS 27111200 | Platform supports monthly data from Jan-2015; compilation note says imports are CIF; annual schedules exist | No — live state lacks historical response vintages and observation-level first-release/revision ledger | Authoritative current statistic, PIT-blocked |
| UN Comtrade HS 271112 | Official API provides monthly reporter data plus dataset-level first/last-release metadata | No — current/revised state is not a value-vintage archive; China monthly data stopped at 2024-12 at the audit cutoff | Delayed cross-check only |
| DCE PG | Official contract is RMB/t exchange LPG with its own delivery standard | Not the target economic object | Excluded |
| Commercial CP vendors/news | ICE/Argus/Reuters identify Saudi CP market usage | No — third-party authority and licence restrictions | Blocker documentation only |

## PIT and licensing assessment

A valid causal input must preserve `(economic_month, value, exact_publication_timestamp, source_owner, original_bytes/hash, revision/vintage, definition, unit, currency, basis)`. None of the inspected families satisfies all fields historically:

1. Seller CP originals and their publication timestamps were not publicly demonstrated.
2. GACC provides the strongest first-party China import statistic, but its live query is a current-state backfill; annual release calendars are not a historical vintage store.
3. GACC's statistic is CIF unit value and cannot be silently renamed CFR or CP.
4. UN Comtrade responses are retainable and expose dataset-level first/last-release timestamps, but are secondary dissemination, were only available through 2024-12 at the audit cutoff, and do not preserve each released value vintage. Any prospective use must retain the contemporaneous response and delay availability until `max(lastReleased, observed_at)`.
5. Clear redistribution rights were not established for Aramco/QatarEnergy notices or GACC query output; commercial CP histories remain licence-gated.

## Decision

# **SOURCE-BLOCKED / NO BACKTEST**

**ACCEPTED is not warranted.** No continuous first-party series was demonstrated with exact historical publication dates, retainable original releases, and sufficient revision/licensing evidence. The research must remain plan-only. No margin coefficient or trading rule may be inferred from DCE PG, current GACC backfill, search snippets, Reuters stories, or commercial vendor histories.

## Next safe action

Obtain the smallest missing authority/access, then re-audit only that seam:

1. **For CP:** written access to a Saudi Aramco (or QatarEnergy) official monthly notice archive containing propane value, USD/t, delivery basis, exact publication timestamp, immutable original files, revision policy, and research retention/redistribution permission.
2. **For China import unit value:** GACC confirmation or an official archive/API that supplies HS 27111200 monthly quantity/value **as originally released**, exact release timestamp per vintage, correction history, field/unit definitions, stable downloadable originals, and reuse terms. Accept explicitly as **CIF China unit value**, not CP/CFR.
3. If neither is available, document the commercial vendor licence and provenance as an unresolved blocker; do not purchase or ingest a large history under this task.
