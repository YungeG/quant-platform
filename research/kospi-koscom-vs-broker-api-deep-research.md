# Research: KOSCOM Open API vs. KIS and Kiwoom APIs for the KOSPI Composite

> Archive note (2026-09-22; not a new research date): This preserves an earlier source brief. Products, prices, access/eligibility and rights below were not rechecked online for this commit; undated statements must not be treated as current offers or entitlements. URLs remain source locators, not proof of present availability. Before procurement or implementation, revalidate the exact first-party terms and obtain the required approvals. This archival task sends no inquiry, opens no account, acquires no data and grants no trading or redistribution rights.
>
> Later correction: the [KIS primary audit](kis-apiportal-primary-audit.md) records both the specific KOSPI REST and WebSocket interfaces as unsupported in VTS; the open VTS-support question below is superseded by that dated audit, not newly verified here. The embedded handoff's phrase “Decision-grade Markdown brief” is ordinary prose, not Backtest `ResultGrade`, a `ValidationReport`, or Platform publication; its checks and `noStagedFiles` describe the original delivery.

**Scope.** Decision brief for a China-based developer that may have no Korean brokerage account. “KOSPI Composite” means the KRX main-board composite index, not KOSPI 200. Sources below are first-party KOSCOM, KIS, Kiwoom, and KRX documentation; where documentation does not establish a fact, this brief says so rather than extrapolating.

## Summary

**Use KOSCOM only for a corporate, licensed market-data product:** it explicitly documents a REST current-index endpoint with the KOSPI Composite code `K1`, says it is real-time, and requires a market-data licence plus a screened corporate onboarding process. It is a poor fit for an individual China-based developer and is not a push/WebSocket feed. [KOSCOM real-time index](https://koscom.gitbook.io/open-api/api/marketv3/index/realtime) · [KOSCOM eligibility/pricing](https://koscom.gitbook.io/open-api/how-to-use/procedure/charge)

**Use a broker API only if an eligible Korean brokerage account can actually be opened:** KIS offers both REST index queries and WebSocket real-time index trades; Kiwoom’s current REST API documents sector/index requests and a WebSocket real-time “industry index” type. Neither broker’s public material establishes that a mainland-China resident without a Korean account can self-onboard. For an externally facing product, neither is a safe default without a data-use contract/partner approval; KOSCOM is the data-rights-first route, subject to eligibility and commercial quotation. [KIS partner guidance](https://apiportal.koreainvestment.com/provider-info) · [Kiwoom REST terms/limits](https://openapi.kiwoom.com/intro?dummyVal=0)

## Findings

### 1. KOSCOM Open API — concrete KOSPI Composite product

| Topic | Published fact | Decision impact |
| --- | --- | --- |
| Product / instrument | KOSCOM’s **KRX industry real-time** product documents `marketcode=kospi`, `issuecode=K1`; KOSCOM’s KOSPI index response also identifies `isuSrtCd: "K1"`. This is the KOSPI Composite identifier in this API. [Real-time index](https://koscom.gitbook.io/open-api/api/marketv3/index/realtime) · [KOSPI index response](https://koscom.gitbook.io/open-api/api/marketv3/stocks/closeda) | Do not substitute a stock code or KOSPI 200 code. |
| Current value | `GET https://{APIGWAddr}/v3/market/realtime/index/kospi/K1/index`, API-key authenticated; the documentation labels it “real-time.” [Endpoint](https://koscom.gitbook.io/open-api/api/marketv3/index/realtime) | It is a REST snapshot to poll, not a published streaming subscription. |
| Intraday | `GET .../v3/market/realtime/index/kospi/K1/intraday`; the documentation says real-time intraday OHLC data in 10-second, 1-minute, and 10-minute units and at most 100 rows. [Endpoint](https://koscom.gitbook.io/open-api/api/marketv3/index/realtime) | Suitable for dashboard/chart polling; retain enough local history if more than 100 bars are needed. |
| Other related calls | `.../marketcap` and `.../prospectindex` are also documented for `kospi/K1`; delayed/closed index is `GET .../v3/market/closed/index/kospi/K1/closeindex` and history is documented separately. [Real-time endpoints](https://koscom.gitbook.io/open-api/api/marketv3/index/realtime) · [Closed endpoints](https://koscom.gitbook.io/open-api/api/marketv3/index/closed) | These are adjacent index products, not an execution API. |
| Protocol and real-time claim | KOSCOM explicitly describes its market-data service as **RESTful API** and labels the endpoints above “real-time.” The public docs reviewed expose GET/API-key semantics, not a WebSocket endpoint or an event-subscription protocol. [Market v3](https://koscom.gitbook.io/open-api/api/marketv3) · [Authentication](https://koscom.gitbook.io/open-api/how-to-use/devcenter) | “Real-time” here is a vendor claim for data freshness, **not** a published push/latency SLA. WebSocket availability: **not publicly documented**. |
| Onboarding/authentication | Data use requires a market-data licence first; applicants submit the Open API application, corporate registry extract, business registration, and service plan, then receive a sandbox API key after approval. API key is passed as a query parameter for GET. [Procedure](https://koscom.gitbook.io/open-api/how-to-use/devcenter) | No brokerage account is required, but this is not self-service developer signup. |
| Eligibility | The platform says it is for qualifying **corporate entities** (SME fintech/e-finance-related firms or entities KOSCOM approves); individuals, sole proprietors, and students cannot use it. [Eligibility](https://koscom.gitbook.io/open-api/how-to-use/procedure/charge) | A person in China is ineligible as an individual. Whether a PRC-incorporated company satisfies KOSCOM’s corporate/SME and documentation requirements is **not publicly documented**—ask KOSCOM before architecture work. |
| Sandbox/live | Sandbox API key follows approval; after test completion and service review, KOSCOM issues a production key. KOSCOM warns sandbox prices are development support data, may lack integrity/match the real-time feed, and may be interrupted without notice. [Sandbox](https://koscom.gitbook.io/open-api/how-to-use/devcenter) | Sandbox is interface testing, not a market-data validation feed. |
| Limits | Rate limiting is per API type; the daily limit resets at 09:00 (GMT+9) and remaining/limit values appear in `X-RateLimit-Remaining-Day` / `X-RateLimit-Limit-Day`. Documentation’s `50,000` header is an example, not a universal entitlement. Concurrency and per-second limits are **not publicly documented**. [Rate limiting](https://koscom.gitbook.io/open-api/rate-limiting) | Read response headers and build backoff; obtain the contracted limit. |
| Rights, redistribution, price | KOSCOM requires a market-data licence. It says sandbox data may not be processed or accumulated without that licence. Its price page says equity quote pricing depends on the information-quote licence and directs customers to sales; it mentions a 36-month base-fee waiver policy for qualifying firms under seven years old, but publishes no general numeric tariff. [Rights/sandbox](https://koscom.gitbook.io/open-api/how-to-use/devcenter) · [Pricing](https://koscom.gitbook.io/open-api/how-to-use/procedure/charge) | Redistribution/display/derived-data rights are contract-specific. KRX’s usage policy also explicitly restricts provision of tools that enable public users to process/store/redistribute quote data under the relevant option. [KRX policy PDF](https://data.krx.co.kr/inc/datasale/Market%20Data%20Usage%20Polices_ko.pdf) **Price: not publicly documented.** |

**KOSCOM update semantics:** call the current endpoint repeatedly (or fetch the 10-second intraday bar); no public document establishes an update interval for the `index` snapshot, a WebSocket channel, replay, sequence number, or recovery contract. Do not call this low-latency streaming.

### 2. Korea Investment & Securities (KIS) — concrete broker API

| Topic | Published fact | Decision impact |
| --- | --- | --- |
| Current KOSPI Composite | KIS publishes a domestic “current industry index” REST API, **`GET /uapi/domestic-stock/v1/quotations/inquire-index-price`**, TR ID **`FHPUP02100000`**. KIS’s public sample/documentation set identifies domestic index functionality and the KOSPI input code as **`0001`**. [Official API portal](https://apiportal.koreainvestment.com/apiservice) · [Official samples](https://github.com/koreainvestment/open-trading-api) | Query `0001` for KOSPI Composite, not `2001` (KOSPI 200). |
| Intraday | KIS documents index time and tick query APIs: `.../inquire-index-timeprice` (**`FHPUP02110200`**) and `.../inquire-index-tickprice` (**`FHPUP02110100`**); it also lists daily index data. [Official sample/API catalogue](https://github.com/koreainvestment/open-trading-api) | REST is request/response historical/intraday retrieval, not a replacement for a tick stream. Exact pagination/retention must be checked in the portal’s downloadable API document at implementation time. |
| Real-time KOSPI Composite | KIS categorizes **“domestic index real-time trade”** in its real-time API catalogue. The documented WebSocket TR ID is **`H0UPCNT0`**; use index code **`0001`** for KOSPI Composite. KIS says a WebSocket connection key is issued and the connected socket receives real-time data. [API catalogue](https://apiportal.koreainvestment.com/apiservice) · [WebSocket method](https://apiportal.koreainvestment.com/intro) | This is the only compared option with a publicly documented KOSPI-specific push route and no Windows/OCX requirement. |
| Protocol/auth | REST uses App Key/App Secret to obtain a token; WebSocket requires a separately issued connection key. KIS documents production REST `https://openapi.koreainvestment.com:9443`, production WS `ws://ops.koreainvestment.com:21000`, and distinct virtual endpoints. [Introduction](https://apiportal.koreainvestment.com/intro) · [Official endpoint config](https://github.com/koreainvestment/open-trading-api/blob/main/kis_devlp.yaml) | Preserve the REST token and WebSocket connection-key flows separately. The public pages reviewed establish push reception after a subscription but do **not** publish a numeric update cadence, latency, replay guarantee, or a stability SLA. |
| Subscription semantics | Persistent WebSocket subscription uses the real-time transaction ID (`H0UPCNT0`) and index code (`0001`); the portal describes receiving data after issuing the WS key and connecting. Exact register/unregister JSON frame fields, max codes/socket, reconnection/replay behavior, and simultaneous socket limit should be taken from the current downloadable KIS API document: **not publicly documented in the static portal pages reviewed.** [WebSocket overview](https://apiportal.koreainvestment.com/intro) | Implement reconnection/deduplication only after testing the live documented wire format; do not infer delivery guarantees. |
| Account and residency | KIS’s official setup says: open a KIS account and connect an ID, apply for Open API, then get App Key/App Secret; virtual and live keys are separate. [Official samples README](https://github.com/koreainvestment/open-trading-api) For non-residents, KIS says to contact its Global Investment Sales/International Business teams; its Korean mobile/Bankis direct account-opening routes explicitly exclude foreigners/non-residents. [KIS nonresident guide](https://securities.koreainvestment.com/eng/guide/stock01.shtm) · [Korean account-opening restrictions](https://securities.koreainvestment.com/main/customer/guide/_static/TF04aa090000.jsp) | A mainland-China developer without a KIS account cannot assume self-service access. Non-resident account availability may exist through the named desks, but KIS does **not** publish that it includes KIS Developers API eligibility. |
| Sandbox/live | KIS provides separate virtual (“VTS”) and production environments/app keys; the portal’s testbed says real-time quotes are not provided in the testbed (REST only). [Official endpoint config](https://github.com/koreainvestment/open-trading-api/blob/main/kis_devlp.yaml) · [Testbed](https://apiportal.koreainvestment.com/testbed) | Validate `H0UPCNT0` in a permitted live account/environment; do not treat REST testbed behavior as real-time validation. |
| Limits/fees | The public KIS materials reviewed do not publish a numeric REST throttle, concurrent WebSocket limit, KOSPI quote fee, or latency. | **Not publicly documented.** Obtain written limits/fees before capacity or cost commitments. |
| Commercial/display rights | KIS says its market-data APIs may be used only for KIS trading customers, and its affiliate guidance says an affiliate using KRX/overseas-exchange quotes in its own branded app must first contract for information use with KOSCOM/exchanges. Third-party services also fall into KIS’s partnership/regulatory process. [KIS partner policy](https://apiportal.koreainvestment.com/provider-info) | Personal/internal use on the owner’s account is materially different from public display/redistribution. Do not build a public KOSPI dashboard on an individual KIS key. |

### 3. Kiwoom — concrete broker API

| Topic | Published fact | Decision impact |
| --- | --- | --- |
| Current KOSPI Composite | Kiwoom’s current REST guide lists **`ka20001` 업종현재가요청** (industry current price) and **`ka20003` 전업종지수요청** (all-industry indices). KOSPI Composite is represented by the industry/index code **`001`** in Kiwoom’s published OpenAPI+ material. [Kiwoom REST guide](https://openapi.kiwoom.com/guide/apiguide) · [Kiwoom OpenAPI+ guide PDF](https://download.kiwoom.com/web/openapi/kiwoom_openapi_plus_devguide_ver_1.5.pdf) | The concrete REST request IDs establish current/all-index coverage; confirm the current REST request body/header schema in the logged-in Kiwoom portal before shipping. |
| Intraday | Current REST catalogue lists **`ka20004`** (industry tick chart), **`ka20005`** (minute), **`ka20006`** (daily), `ka20007` (weekly), `ka20008` (monthly), and `ka20009` (industry current price daily). [Kiwoom REST guide](https://openapi.kiwoom.com/guide/apiguide) | Kiwoom therefore documents KOSPI index intraday chart request capability, not merely individual-stock quotes. Retention/page limits: **not publicly documented** in accessible static documentation reviewed. |
| Real-time KOSPI Composite | Kiwoom’s REST guide lists real-time type **`0J` 업종지수** (“industry index”), which is the relevant subscription type for KOSPI Composite code `001`. [Kiwoom REST guide](https://openapi.kiwoom.com/guide/apiguide) | It is a documented index stream type. Numeric freshness/latency, update cadence, replay and sequence semantics are **not publicly documented**. |
| Protocol/auth | Kiwoom’s current API is JSON REST with OAuth client-credentials token at `POST /oauth2/token`; public docs list live `https://api.kiwoom.com` and mock `https://mockapi.kiwoom.com`. The guide also teaches WebSocket as a persistent two-way real-time channel. [OAuth guide](https://openapi.kiwoom.com/guide/apiguide) · [WebSocket guide](https://openapi.kiwoom.com/m/guide/index?guideNum=04) | The new REST API is cross-platform; do not confuse it with legacy OpenAPI+. |
| Legacy platform caveat | Kiwoom’s separately published **OpenAPI+** guide is an OCX-control interface registered with Windows; it documents real-time registration (`SetRealReg`) and an industry-index real-time section. [OpenAPI+ guide PDF](https://download.kiwoom.com/web/openapi/kiwoom_openapi_plus_devguide_ver_1.5.pdf) | Avoid OpenAPI+ for a Linux/cloud implementation unless Windows/OCX is deliberately acceptable. The current REST/WebSocket API removes that platform dependency. |
| Subscription semantics | The official guide establishes WebSocket real-time operation and type `0J`, but static public pages reviewed do not establish the exact `REG`/`REMOVE` message schema, per-socket code cap, reconnect/replay, or a delivery SLA. | **Not publicly documented** in the reviewed first-party pages; obtain the authenticated REST guide/spec and test before relying on stream recovery. |
| Account/KYC and access | Kiwoom says users must hold a Kiwoom account, link an HTS ID, and register through the API-use application page. It does not publish nationality/residency eligibility on that API page. [Kiwoom service requirements](https://openapi.kiwoom.com/intro?dummyVal=0) | An accountless China-based developer is blocked from self-service API use. Whether a mainland-China resident can open the required account/HTS ID is **not publicly documented** here; ask Kiwoom compliance/onboarding. |
| Sandbox/live | Live and mock domains are explicitly distinct; live use, not mock-only login, is required to avoid the stated three-month inactivity auto-cancellation. [OAuth domains](https://openapi.kiwoom.com/guide/apiguide) · [Service rules](https://openapi.kiwoom.com/intro?dummyVal=0) | Mock is available for API testing; index-stream parity and mock data fidelity are **not publicly documented**. |
| Limits / fees | For domestic stocks, Kiwoom publishes **5 order TR/s and 5 inquiry TR/s per account/token**. It states brokerage commission is the same as HTS (Hero4/Hero Global); it does not publish a separate KOSPI market-data/API price or a WebSocket concurrency/subscription cap on the reviewed page. [Kiwoom limits and fees](https://openapi.kiwoom.com/intro?dummyVal=0) | The 5/s figure is an account/token request ceiling, not a streaming-latency claim. Data-feed fee and WS caps: **not publicly documented**. |
| Commercial/display rights | No first-party public Kiwoom REST source reviewed states a KOSPI quote redistribution licence, external-display right, or price. The account-bound service requirement is not permission to redistribute. | **Not publicly documented; treat as prohibited until Kiwoom/market-data rights confirm otherwise.** |

### 4. Hours, after-hours, and what “real-time” should mean

KRX gives equity regular hours as **09:00–15:30 Korea time** and off-hours equity trading as **08:00–09:00 and 15:40–18:00**. [KRX KOSPI Market](https://global.krx.co.kr/contents/GLB/02/0201/0201010200.jsp) This does **not** establish that any of KOSCOM/KIS/Kiwoom KOSPI Composite feeds update during all off-hours. Each vendor’s index API/page must be tested for pre-open, closing auction, after-hours, holiday, and exchange outage behavior; such per-feed behavior is **not publicly documented** in the reviewed material.

### 5. Recommendation matrix

| Use case | Recommendation | Why / gate |
| --- | --- | --- |
| Personal dashboard | **KIS or Kiwoom, only after obtaining a valid broker account; prefer KIS** for a cross-platform WebSocket index stream (`H0UPCNT0` / `0001`). | KOSCOM excludes individuals. KIS and Kiwoom require their brokerage accounts; account eligibility is the first gate. Poll KIS/Kiwoom REST only if push is unnecessary. |
| Internal strategy/research | **KOSCOM for a qualifying corporate entity needing licensed data; otherwise KIS/Kiwoom only inside the account owner’s internal workflow.** | KOSCOM is expressly a licensed corporate market-data route. KIS says third-party/app display has separate data-contract constraints; no broker public source grants broad redistribution. |
| Low-latency execution | **KIS or Kiwoom WebSocket + their order APIs, but only for the same eligible brokerage client; neither has a published latency SLA.** | KOSCOM is data REST, not execution. Do not select based on claimed milliseconds: numeric latency, jitter, loss/replay and concurrency are not publicly documented. Kiwoom legacy OpenAPI+ adds Windows/OCX operational risk; use its REST/WebSocket offering if its authenticated spec meets the requirement. |
| Externally facing product | **KOSCOM first, subject to formal eligibility, data licence, product review, and a written display/redistribution scope.** | It is designed as a corporate data platform with explicit data licensing. KIS requires exchange/KOSCOM information-use contracts for an affiliate’s branded app; Kiwoom’s public docs do not grant redistribution rights. No option is “ship on a personal API key.” |

## Unresolved verification questions (obtain in writing)

1. **KOSCOM:** Can a PRC-incorporated company qualify as the required Korean-law SME/fintech corporate customer; which data licence permits a China-hosted/internal versus public KOSPI display; what are contracted daily/per-second/concurrent limits, rate, cache/history and redistribution rights?
2. **KIS:** Can a mainland-China resident/non-resident account holder activate KIS Developers; does virtual trading include `FHPUP021*` and `H0UPCNT0`; what are the current WebSocket register/unregister wire schema, caps, recovery semantics, KOSPI data fee, and display/redistribution licence?
3. **Kiwoom:** Can a mainland-China resident open the required account and HTS ID; what are exact authenticated REST route/body headers for `ka20001`–`ka20009`, real-time `0J` registration/removal/caps/replay, mock parity, and external display/republication rights?
4. **All providers:** Confirm treatment of KRX off-hours, auctions, holidays, corrections, data centre location/cross-border transfer, and China regulatory/data-export obligations with counsel and the vendor. None is established by the cited API pages.

## Sources

### Kept (primary/official)

- [KOSCOM Market Data Service v3](https://koscom.gitbook.io/open-api/api/marketv3) — REST service/product catalogue.
- [KOSCOM KRX industry real-time](https://koscom.gitbook.io/open-api/api/marketv3/index/realtime) — `K1`, exact live/index/intraday endpoints and real-time claim.
- [KOSCOM onboarding/sandbox](https://koscom.gitbook.io/open-api/how-to-use/devcenter) and [pricing/eligibility](https://koscom.gitbook.io/open-api/how-to-use/procedure/charge) — contractual gate, key process, pricing availability.
- [KOSCOM rate limiting](https://koscom.gitbook.io/open-api/rate-limiting) — daily-header semantics.
- [KRX Market Data Usage Policy](https://data.krx.co.kr/inc/datasale/Market%20Data%20Usage%20Polices_ko.pdf) — market-data reuse restrictions.
- [KIS Developers portal](https://apiportal.koreainvestment.com/apiservice), [official samples](https://github.com/koreainvestment/open-trading-api), and [KIS onboarding/partner policy](https://apiportal.koreainvestment.com/provider-info) — KIS API catalogue, environment/account flow, third-party data constraints.
- [KIS foreign-investor guide](https://securities.koreainvestment.com/eng/guide/stock01.shtm) — non-resident onboarding route/limitation evidence.
- [Kiwoom REST guide](https://openapi.kiwoom.com/guide/apiguide) and [Kiwoom service rules](https://openapi.kiwoom.com/intro?dummyVal=0) — index request IDs, real-time type, OAuth environments, account/HTS-ID requirement and request limits.
- [Kiwoom OpenAPI+ guide](https://download.kiwoom.com/web/openapi/kiwoom_openapi_plus_devguide_ver_1.5.pdf) — Windows OCX legacy distinction and KOSPI index code evidence.
- [KRX KOSPI trading hours](https://global.krx.co.kr/contents/GLB/02/0201/0201010200/GLB0202010200.jsp) — **dropped due to erroneous path**; retained working link is [here](https://global.krx.co.kr/contents/GLB/02/0201/0201010200/GLB0201010200.jsp).

### Dropped

- Third-party SDKs, blogs, wrappers, and GitHub wikis found during discovery — excluded as non-primary evidence, even when they exposed useful-looking KIS/Kiwoom wire details.
- Vendor marketing pages without an API/rules statement — excluded as insufficient for access, rights, or performance claims.

## Gaps

Numeric latency, jitter, quote update cadence, streaming replay/sequence guarantees, concurrent socket/subscription caps, and public data-fee schedules are **not publicly documented** in the reviewed primary pages. The important commercial question is not technical reachability but a written KRX/KOSCOM/KIS/Kiwoom data-use and redistribution grant matching the intended audience and China deployment.

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "Decision-grade Markdown brief written to research/kospi-koscom-vs-broker-api-deep-research.md with concrete endpoints, codes, account gates, limits, rights, recommendation matrix, citations, and unresolved questions."
    }
  ],
  "changedFiles": [
    "research/kospi-koscom-vs-broker-api-deep-research.md"
  ],
  "testsAddedOrUpdated": [],
  "commandsRun": [
    {
      "command": "Focused official-source web research across KOSCOM, KIS, Kiwoom, and KRX",
      "result": "passed",
      "summary": "Primary documentation reviewed; unavailable facts were explicitly marked not publicly documented."
    }
  ],
  "validationOutput": [
    "Verified the requested file was written and contains Markdown citations, recommendation matrix, gaps, and acceptance report."
  ],
  "residualRisks": [
    "Live entitlement, PRC/non-resident onboarding, data redistribution, pricing, stream recovery, and latency require vendor confirmation because public documents do not settle them.",
    "No numeric latency or fee was inferred from non-primary sources."
  ],
  "noStagedFiles": true,
  "diffSummary": "Added one research brief; no other files modified.",
  "reviewFindings": [
    "no blockers: claims without first-party public support are identified as not publicly documented.",
    "medium: KIS and Kiwoom exact authenticated WebSocket registration details require current portal/spec verification before implementation."
  ],
  "manualNotes": "One erroneous KRX URL is visibly marked dropped and immediately replaced with the working official URL; it is retained transparently rather than used as evidence."
}
```
