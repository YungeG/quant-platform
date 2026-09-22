# Lawful alternatives for A-share propane/PDH price research

> Archive note (2026-09-22; not a new research date): This preserves an earlier source brief. Products, prices, access/eligibility and rights below were not rechecked online for this commit; undated statements must not be treated as current offers or entitlements. URLs remain source locators, not proof of present availability. Before procurement or implementation, revalidate the exact first-party terms and obtain the required approvals. This archival task sends no inquiry, opens no account, acquires no data and grants no trading or redistribution rights.

**Scope and rule.** This ranks lawful acquisition routes for imported-propane physical-cost research—not investment recommendations. “Price” below is deliberately separated into (A) Saudi CP, (B) CFR North Asia/China propane, (C) China import CIF unit value, (D) domestic LPG proxy (DCE PG), (E) PP output price, and (F) shipping/flow data. No public webpage, screen scrape, trial, or third-party repost is assumed to grant redistribution, bulk-history, API, or commercial-model rights.

## Decision summary

The only defensible route that directly tests an imported-PDH physical-cost hypothesis is a **written vendor licence for the specified propane physical assessments** (Saudi CP and/or CFR North Asia/China), with publication timestamps and correction history. Argus and S&P Global Commodity Insights/Platts are the strongest first enquiries; ICIS is the strongest China-focused cross-check. Their public methodology/product pages establish that assessed-price services exist, but do **not** publish a universal plan, price, permitted history depth, or redistribution threshold—obtain those terms in writing.

For a low-cost historical exploration, use official customs aggregates to calculate a monthly China imported-propane CIF unit value and public DCE PG/PP settlements, labelled as proxies. For forward monitoring, add a licensed current physical benchmark and licensed flow data if it changes a defined decision. Neither customs unit values nor futures settlements are seller CP; flows are quantities/route observations, not prices.

## Ranked route table

| Rank / route | Covers | Owner/provider; object and delivery basis | Frequency / history visible publicly | Lawful access and commercial limit | PIT / revision quality | Supports |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Licensed physical-assessment bundle | A, B; optionally E | **Argus** or **S&P Global Commodity Insights/Platts**. Ask specifically for Saudi Aramco propane CP and physical CFR North Asia/China/East China propane symbols, plus PP if required. Platts’ published Asia methodology and its 2024 notices show that exact symbols/bases can change. [Platts methodology](https://www.spglobal.com/content/dam/spglobal/ci/en/documents/platts/en/our-methodology/methodology-specifications/refined-products/refined-products-asia-pacific-middle-east-specifications.pdf) [East China launch notice](https://www.spglobal.com/energy/en/pricing-benchmarks/our-methodology/subscriber-notes/090524-platts-to-launch-east-china-propane-butane-physical-assessments-oct-1) | Assessment cadence/history must be confirmed per symbol; do not infer it from news articles. | Vendor web/Excel/API delivery under negotiated subscription/licence. Argus Direct terms require a valid licence; S&P terms govern site/data use. [Argus Direct terms](https://www.argusmedia.com/en/solutions/how-we-deliver/argus-direct-for-spreadsheets-terms-and-conditions) [S&P Energy terms](https://www.spglobal.com/energy/en/overview/website-app-terms-of-use) | Best available if contract supplies publication timestamp, holiday calendar, corrected-value policy, and vintage/as-of export. Do not backfill a causal study with today’s corrected series without recording retrieval date/vintage. | **Research-grade direct physical-cost benchmark**, subject to confirming the precise assessment matches procurement terms. It remains a benchmark, not an individual buyer’s invoice/discount/freight exposure. |
| 2. Licensed China LPG + PP cross-check | B, E; domestic LPG context | **ICIS** China LPG Weekly Report and ICIS PP price-report/methodology products; ask for the exact propane basis and PP grade/basis. ICIS publicly lists the China LPG report and a PP methodology, rather than enough free observations to validate coverage. [ICIS China LPG](https://www.icis.com/compliance/reports/china-liquefied-petroleum-gas-lpg-weekly-report) [ICIS PP methodology](https://www.icis.com/compliance/documents/polypropylene-methodology-1-october-2024) | At least weekly for the named LPG report; historical start, exact series and revisions are not published on the product landing page—confirm. | Subscription/vendor request; ICIS describes pricing as a service. No reuse, internal redistribution, or machine-access assumption without the order form/licence. [ICIS pricing services](https://www.icis.com/explore/services/pricing) | Request date/time zone, methodology version, correction log and historical-as-published vintages. Weekly cadence can be insufficient for daily event studies. | **Research-grade secondary physical/output cross-check** if the purchased series is a matched grade/location; not proof of Saudi seller CP. |
| 3. Official China Customs micro/aggregate statistics; UN Comtrade mirror | C (and origin/flow controls) | **GACC** is the official compiler; customs statistical value of imports includes goods value plus pre-unloading transport/charges/insurance—i.e., a CIF-like statutory statistical value. Calculate value ÷ quantity for the selected liquid-propane tariff line(s), normally beginning with HS 271112, after confirming China’s period-specific code/unit. [GACC regulations, Arts. 6–8](http://english.customs.gov.cn/Statics/55dd0995-11de-4e05-a7e3-0dd5c4364f27.html) **UN Comtrade** republishes reporter data and offers portal/API/developer access. [UN Comtrade portal](https://comtradeplus.un.org/) [account help](https://uncomtrade.org/docs/how-to-create-an-account) | GACC releases regular statistics; the English site publishes monthly “major import commodities” releases. Comtrade availability and historical depth depend on reporter/submission/classification. [GACC statistics](http://english.customs.gov.cn/Statistics/Statistics?ColumnId=1) | GACC portal/public releases and Comtrade web/API/bulk routes, subject to their terms and any account/API quotas. Neither promises every desired China x origin x HS cut free on its public landing page; verify export entitlement and archive source files. | Good official provenance and monthly publication dates. Weak PIT unless each release/vintage is saved; reported data can be corrected/reclassified and monthly unit values mix contracts, origins, cargo timing and composition. | **Research-grade monthly import-cost proxy/control**, not a spot price and **not seller CP**. It cannot identify a particular PDH plant’s cargo, pricing month, term discount, demurrage or tax. |
| 4. ICE/CME Saudi-CP financial derivatives | A proxy / forward monitor | **ICE** lists “Propane, Argus Saudi CP Future”; **CME** lists Argus Propane (Saudi Aramco) swap futures. ICE’s contract name itself identifies the Argus reference, so settlement is a derivatives/benchmark-linked value, not the seller’s invoice or a free copy of Argus’ physical assessment. [ICE contract](https://www.ice.com/products/6590316/Propane-Argus-Saudi-CP-Future) [CME contract](https://www.cmegroup.com/markets/energy/petrochemicals/argus-propane-saudi-aramco-swap-futures.html) | Exchange contract/settlement history varies by venue and listing/expiry; check contract rulebook, dates, liquidity and continuous-series construction before use. | Public delayed displays may exist; reproducible historical settlements, real-time data, redistribution and derived-data use can require exchange/vendor permission. ICE identifies the contract, not a blanket free data licence. | Exchange settlement timestamps are usually stronger PIT than media reports, but a continuous series introduces roll choices; retain individual expiries and retrieval source. | **Forward expectation/hedging proxy only. Not seller CP.** Use only alongside a direct CP series, after liquidity and basis validation. |
| 5. DCE public PG and PP futures history | D, E proxy | **Dalian Commodity Exchange (DCE)** LPG futures (PG) and polypropylene futures (PP): exchange-deliverable financial/physical-futures contracts, not imported CFR propane or a plant’s PP realized selling price. DCE provides product, historical-data and delayed-quote pages. [LPG product](http://www.dce.com.cn/dceg/channel/list/2513.html) [LPG contract](http://www.dce.com.cn/dceg/content/2020/LPGhyzl/6211079.html) [historical data](http://www.dce.com.cn/dceg/channel/list/468.html) [PP contract/Q&A](http://www.dce.com.cn/dceg/content/2014/dceg_dssxw/1520943.html) | Daily exchange data; PG is a newer contract than long PP history (verify actual listing range/download before defining sample). | Website download for permitted historical data; delayed and real-time services are separate, and DCE publishes real-time information-service fees. Confirm commercial redistribution/API rights. [DCE data-fee page](http://www.dce.com.cn/content/clientDf.do?id=5000622) | Dated daily settlement is auditable if raw files are retained. Specify settlement versus close, contract, roll rule, trading calendar, and later corrections. | **Research-grade transparent market proxy** for domestic LPG/PP sensitivity, **not** imported physical cost or seller CP. PG’s delivery/specification, tax/location and futures basis may diverge materially from CFR cargo cost. |
| 6. China specialist assessment vendor | B, D, E | **SCI99 (卓创资讯)** and **Longzhong/OilChem (隆众资讯/OilChem)** may provide China LPG/PDH/PP assessments, market reports and data services. SCI publishes a price-assessment methodology page explaining that assessment methodology specifies delivery, payment and other price factors. [SCI methodology](https://intl.sci99.com/spas/methodology.aspx) OilChem publishes PDH/LPG market analysis. [OilChem PDH example](https://en.oilchem.net/25-0718-08-a994752ba86b54a8.html) | Frequency, historic depth and exact physical basis must be supplied in a vendor data dictionary; do not rely on visible article dates as a dataset history. | Vendor-request/subscription route only. Request a written data licence, methodology and permission for internal research/model outputs; no logged-in machine, scraping or subscription circumvention. | Potentially valuable local basis detail; PIT is adequate only if vendor provides contemporaneous timestamps and correction/vintage policy. | **Potential research-grade China basis/PP cross-check** after documentation and validation; unverified as a substitute for Saudi CP/CFR cargo benchmark. |
| 7. Licensed vessel-flow intelligence | F; controls for B/C | **Kpler** LPG and historical AIS; **Vortexa** LPG market analytics. These are vessel/cargo/flow datasets useful for origin, ETA, discharge and supply-shock controls, not price assessments. [Kpler LPG](https://www.kpler.com/market/lpg) [Kpler historical AIS](https://www.kpler.com/product/maritime/historical-ais) [Vortexa LPG](https://www.vortexa.com/product/energy/lpg-market-analytics-software) | Historical coverage, refresh/arrival estimation, cargo classification and backfill rules require a vendor statement of work. | Licensed web/API/export access; Kpler’s master agreement/terms govern use. Obtain Vortexa’s equivalent order-form terms rather than assuming API or redistributable history. [Kpler master agreement](https://www.kpler.com/company/master-agreement) | Critical PIT risks: AIS reception delays, destination changes, inferred cargo grade and retrospective matching/backfills. Store “known-at” timestamps and original extracts. | **Research-grade explanatory/control data**, not a physical price and not seller CP. Buy only if a pre-registered flow variable is needed. |

## Detailed evidence

### A. Saudi CP

1. **Best direct route: licence a vendor’s Saudi CP assessment/history.** Ask Argus and S&P Global/Platts for the exact series label, unit, currency, monthly effective period, publication time and whether the series represents the Saudi Aramco contract-price announcement or an assessed/derived value. The existence of ICE’s “Propane, Argus Saudi CP Future” demonstrates a named Argus-referenced financial contract, but it does not establish that ICE data is the underlying seller CP or grants rights to the Argus input. [ICE](https://www.ice.com/products/6590316/Propane-Argus-Saudi-CP-Future)
2. **Lawful derivative alternative: ICE/CME settlements.** This can monitor market-implied/financial exposure and provide timestamped daily observations, conditional on documented liquidity/roll construction. It is expressly **not seller CP**, and absent written market-data permission should not be bulk-downloaded or redistributed. [CME](https://www.cmegroup.com/markets/energy/petrochemicals/argus-propane-saudi-aramco-swap-futures.html)
3. **Do not treat press reports, blog tables or copied charts as a historical CP database.** They lack a transferable licence and a reproducible correction/PIT record. The recommended legal route is a vendor quotation or a customer-provided licensed extract under its licence.

### B. CFR North Asia/China propane

1. **First-choice evidence is physical assessed-price data from Argus or Platts; ICIS is the independent China-market cross-check.** S&P’s public refined-products methodology and subscriber notices document that assessment specifications and symbols are maintained products, while the October 2024 notice announces physical East China propane/butane assessments. This makes an exact-symbol, date-range request essential; “CFR North Asia” can refer to distinct physical and financial series across time. [Platts Asia methodology](https://www.spglobal.com/content/dam/spglobal/ci/en/documents/platts/en/our-methodology/methodology-specifications/refined-products/refined-products-asia-pacific-middle-east-specifications.pdf) [physical East China notice](https://www.spglobal.com/energy/en/pricing-benchmarks/our-methodology/subscriber-notes/090524-platts-to-launch-east-china-propane-butane-physical-assessments-oct-1) [North Asia financial launch](https://www.spglobal.com/energy/en/pricing-benchmarks/our-methodology/subscriber-notes/100124-platts-launches-north-asia-propane-derivatives-assessments-oct-1)
2. **ICIS/SCI99/Longzhong can improve local relevance but require procurement diligence.** ICIS publicly identifies a China LPG weekly report, and SCI publicly describes standardized assessment inputs such as delivery/payment terms. Neither public page proves a particular historic propane-CFR line or model-use permission; request the data dictionary and licence. [ICIS](https://www.icis.com/compliance/reports/china-liquefied-petroleum-gas-lpg-weekly-report) [SCI](https://intl.sci99.com/spas/methodology.aspx)

### C. China import CIF unit values

1. **GACC is the authoritative primary source.** Its regulations say GACC administers customs statistics, records quantity and statistical value, and defines import statistical value as value plus transport/associated charges/insurance paid before unloading at entry. That supports a monthly CIF-like all-import unit-value construction—not an assessed spot price. [GACC regulations](http://english.customs.gov.cn/Statics/55dd0995-11de-4e05-a7e3-0dd5c4364f27.html)
2. **Construction:** for each publication/vintage, select the valid liquid-propane code and matching quantity unit; calculate `CIF unit value = import statistical value / import quantity`; retain total, origin, customs district and transport cuts when available. Do not silently combine propane with butane/LPG mixtures, change tariff classifications, or convert units without saving the conversion rule.
3. **Comtrade is a lawful secondary delivery/validation channel, not a substitute for source vintage.** It is convenient for portal/API retrieval and exposes reporter data, but release lag, revisions and aggregation can differ from a saved GACC release. [UN Comtrade](https://comtradeplus.un.org/) [developer/account information](https://uncomtrade.org/docs/how-to-create-an-account)

### D. Domestic LPG proxy (DCE PG)

DCE’s LPG contract and historical-data pages make PG the cleanest lawful, repeatable domestic daily LPG proxy. Use raw contract settlements, not an undocumented continuous chart; convert only after documenting the contract unit, delivery quality/location, VAT and FX assumptions. It cannot be relabelled as CFR China propane, imported CIF, or CP. [DCE LPG contract](http://www.dce.com.cn/dceg/content/2020/LPGhyzl/6211079.html) [DCE history](http://www.dce.com.cn/dceg/channel/list/468.html)

### E. PP output price

1. **Preferred formal-output measure:** license a matched physical PP assessment from Argus/ICIS/SCI/Longzhong, stating grade (e.g., homopolymer/raffia/injection), incoterm, geography, tax status and cadence. Argus publishes a global PP methodology; ICIS publishes its PP methodology. [Argus PP methodology](https://www.argusmedia.com/-/media/Files/methodology/argus-global-polypropylene.ashx) [ICIS PP methodology](https://www.icis.com/compliance/documents/polypropylene-methodology-1-october-2024)
2. **Exploratory substitute:** DCE PP settlements are a transparent domestic output proxy. It is neither a PDH plant’s realised sales price nor automatically the physical grade/region needed for a margin calculation. [DCE PP material](http://www.dce.com.cn/dceg/content/2014/dceg_dssxw/1520943.html)

### F. Shipping/flow data

Kpler/Vortexa can identify LPG origin/destination, vessel movement, estimated cargo timing and aggregate flows. They are valuable as supply-shock controls or to align cargo-arrival lags, but they do not price the cargo. Historical AIS and inferred cargo fields are particularly vulnerable to later enrichment; procure a known-at timestamp and revision/backfill documentation. [Kpler historical AIS](https://www.kpler.com/product/maritime/historical-ais) [Vortexa LPG](https://www.vortexa.com/product/energy/lpg-market-analytics-software)

## Data, licence and PIT caveats

1. **Licence before ingestion.** A display subscription, a free article and an exchange webpage are not necessarily permissions for automated retrieval, storage, model training, published charts, affiliate sharing, vendor redistribution or derived indices. Argus explicitly places its spreadsheet delivery under a licence, and Kpler sets service use under its master agreement. Obtain written rights for the intended internal research and any output sharing. [Argus terms](https://www.argusmedia.com/en/solutions/how-we-deliver/argus-direct-for-spreadsheets-terms-and-conditions) [Kpler agreement](https://www.kpler.com/company/master-agreement)
2. **PIT means more than a date column.** Capture vendor publication timestamp/time zone, first-published value, correction flag/time, methodology version, assessment holiday calendar and file retrieval hash. For futures retain exchange date, individual expiry, settlement/close field and roll rule. For flows retain the data’s `known_at`/extract timestamp rather than only later-confirmed arrival.
3. **Basis is the main identification risk.** CP is a monthly contract benchmark; CFR is delivered cargo basis; GACC value is a realised aggregate statistical value; PG/PP futures are exchange contracts. Never substitute one for another without reporting the basis spread, lag, FX and freight/tax transformation.
4. **Customs values require auditability.** GACC’s definition includes pre-entry transport and insurance, which makes it useful for an import-cost proxy but creates differences versus a vendor’s assessed CFR benchmark; reclassification, quantity units and origin mix can dominate the ratio. [GACC Art. 8](http://english.customs.gov.cn/Statics/55dd0995-11de-4e05-a7e3-0dd5c4364f27.html)
5. **Do not invent commercial facts.** Published pages reviewed do not state a comparable price, plan, historic lookback, API entitlement or redistribution threshold for the required series. Those items remain vendor-quote uncertainties.

## Recommended minimum viable acquisition bundles

### 1. Historical exploratory study (lawful, lowest-cost)

- GACC/UN Comtrade monthly China liquid-propane import quantity and statistical value, saved by release/vintage; calculate the CIF unit value.
- DCE raw daily PG and PP settlements from official historical data, with individual-contract and roll documentation.
- Public FX and documented freight *proxies only if separately licensed/officially obtained*; otherwise do not manufacture a landed-cost series.
- Deliverable: monthly/weekly sensitivity study that labels all input costs as proxies. It can explore correlation and lag, not establish seller-CP causality.

### 2. Prospective forward monitoring

- A licensed current physical propane series: choose **one** exact CP or CFR China/North Asia benchmark that matches the monitored procurement convention; include rights for permitted internal dashboard/API use.
- DCE PG and PP for domestic market response; ICE/CME CP-linked derivative only as an explicitly financial forward indicator after liquidity check.
- Optional Kpler or Vortexa LPG flows only if arrival/origin changes are a prespecified signal; retain daily as-known snapshots.
- Deliverable: date-stamped dashboard with methodology/basis metadata and an exception alert for assessment/specification changes.

### 3. Formal causal cost research

- Contracted historical **and as-published/vintage** CP and CFR physical propane series from an approved price-reporting agency, plus matched physical PP output assessment; acquire methodology archives and correction history.
- Plant/company-level procurement, throughput, product-mix, realised PP revenue and hedge records only where lawfully authorised; no market proxy can replace these for causal claims.
- GACC origin-level values and licensed Kpler/Vortexa flow snapshots as validation/control variables; DCE PG/PP and FX as robustness checks, never relabelled as the treatment.
- Deliverable: a pre-specified basis/lag map, source ledger, rights register, vintage dataset, placebo/basis robustness tests and results limited to the data’s identification strength.

## Exact vendor inquiry template

```text
Subject: Request for lawful historical and prospective propane/PDH benchmark data licence — China research

We are conducting internal, non-public research on imported-propane/PDH cost exposure in China. Please quote and document the smallest licence that covers the following, if available:

1) Series requested (state exact symbol/name, not a generic category):
   A. Saudi Aramco propane CP: [currency/unit; monthly effective period; Far East/other convention]
   B. Physical propane CFR North Asia and/or CFR/Delivered East China: [each exact basis]
   C. Physical PP output assessment: [grade, geography, incoterm, tax status]
   Optional: methodology archives and correction/revision history for each series.

2) Period and delivery:
   Historical: [YYYY-MM-DD] through [YYYY-MM-DD].
   Prospective: daily/weekly/monthly delivery from [date].
   Preferred lawful delivery: vendor web export or Excel add-in; API only if separately licensed.

3) Point-in-time and metadata required:
   - publication timestamp and time zone;
   - first-published value, correction flag/time and policy; available historical vintages/as-of extracts;
   - methodology/specification version, holiday calendar, units, price range/midpoint convention;
   - assessment basis: location/port, incoterm, cargo size, delivery window, quality/specification, payment/tax treatment.

4) Permitted use to quote explicitly:
   Internal reproducible research, storage in our controlled research environment, calculation of non-redistributable derived statistics/models, and internal charts. Please identify any limits on automated retrieval, retention, affiliates/contractors, model/AI use, publication, redistribution, and disclosure of individual observations.

5) Commercial questions:
   Please provide the applicable product name, minimum contract term, historical lookback available, user/API/export entitlements, fees, currency, trial terms (if any), and whether a separate redistribution/derived-data licence is required. If an item is unavailable, please identify the nearest documented alternative and its basis difference.

We will not scrape, bypass access controls, download unlicensed paid data, or use the data outside the agreed licence. Please send the governing order form/licence and methodology documents with the quote.
```

## Next safe action

Send the template separately to Argus, S&P Global Commodity Insights/Platts, and ICIS, requesting a written symbol/basis/history/PIT/licence matrix. In parallel, download only the officially available GACC/Comtrade and DCE files permitted by their sites, preserve release timestamps and file hashes, and build a clearly labelled exploratory proxy panel. Do not use any logged-in 卓创 environment, third-party reposted values, paid-data downloads, or access-control workarounds.

## Source selection

- **Kept — GACC, Regulations of the PRC on Customs Statistics** (<http://english.customs.gov.cn/Statics/55dd0995-11de-4e05-a7e3-0dd5c4364f27.html>) — primary legal definition of China import statistical value and coverage.
- **Kept — DCE, LPG contract/product/historical data** (<http://www.dce.com.cn/dceg/content/2020/LPGhyzl/6211079.html>) — official exchange contract and public-data route.
- **Kept — ICE, Propane Argus Saudi CP Future** (<https://www.ice.com/products/6590316/Propane-Argus-Saudi-CP-Future>) — official proof of the financial, Argus-referenced alternative.
- **Kept — S&P Global/Platts methodology and subscriber notices** (<https://www.spglobal.com/content/dam/spglobal/ci/en/documents/platts/en/our-methodology/methodology-specifications/refined-products/refined-products-asia-pacific-middle-east-specifications.pdf>) — primary basis/specification-change evidence.
- **Kept — Argus/ICIS/SCI99 vendor methodology and terms pages** (<https://www.argusmedia.com/en/solutions/how-we-deliver/argus-direct-for-spreadsheets-terms-and-conditions>) — primary evidence for licensed assessed-data procurement.
- **Kept — UN Comtrade, Kpler, Vortexa official product/access pages** (<https://comtradeplus.un.org/>) — official alternative-delivery and flow-data evidence.
- **Dropped — Reuters, LinkedIn, social-media and generic data-vendor snippets** — useful leads only; they do not establish transferable data rights, complete coverage or PIT quality.
- **Dropped — search-result summaries where primary page access was blocked** — not used to assert undisclosed plan prices, history or permissions.

## Gaps

- Public sources reviewed do not establish a complete, transferable Saudi Aramco CP archive, the precise current physical CFR China/North Asia series identifiers, vendor historic lookback, API rights, cost, or redistribution/model rights. Obtain all from written vendor responses.
- Exact China tariff line, units and origin-level availability must be verified against the versioned GACC classification/query result for each study period; this brief intentionally does not assume a stable HS mapping.
- A physical benchmark alone cannot observe a PDH plant’s negotiated term formula, freight, FX hedge, inventory lag, yield, coproduct credit, tax or realised PP price. Formal causal conclusions need authorised plant/company records and a pre-specified mapping.
