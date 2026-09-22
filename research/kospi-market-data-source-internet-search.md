# KOSPI 综合指数（Composite，非 KOSPI 200）市场数据来源检索

> 归档说明（2026-09-22，非重新检索日期）：下文保留原调研记录；产品、资费、准入、接口和许可条件未在本次联网复核，未注明日期的断言不能当作现行报价或已获权限。URL 仅作原始来源定位，实际采购或接入前须重新核对一手条款并取得相应批准。本次只归档，不发送询价、不开户、不采集数据，也不授予交易或再分发权。

---

> **检索范围与口径**：仅纳入本次能以一手运营商/供应商页面明确证明为 **KOSPI Composite**（也常简称 KOSPI；不是 KOSPI 200）的来源，或能证明其 KOSPI 专用 API 路径/可检索标识的来源。检索时点为本报告生成时。`实时`只表示供应商将该产品称作 real-time；除非合同 SLA 明示，**不能从网页、轮询频率或“real-time”字样推断毫秒级/固定延迟**。价格、地域准入和再分发权必须以询价合同为准。

## 结论摘要

对中国大陆开发者，按目的分层最稳妥：**研究/日频回测**先选金融委员会公共数据门户的免费 REST 数据，辅以 KRX Data Marketplace 的日频/历史数据做交叉核验；**内部实时看板或生产信号**优先向 Koscom 申请 KOSPI 实时 API/机构行情服务，并把 KRX 指数/行情许可、SLA、跨境交付和内部展示权写进订单；若已有全球终端/数据合同，则 Bloomberg `KOSPI:IND` 或 LSEG/Reuters `.KS11` 是可采购的全球整合路径。

免费网页（Reuters `.KS11`）明确是至少 15 分钟延迟，适合人工核对/低风险研究，**不应抓取后当作生产或公开展示数据源**。官方免费/开放 API 也不等于实时交易级数据，且韩国公共门户曾就该类 API 发布数据延迟通知。

## 决策矩阵

标记：✅ = 文档与许可确认后可用；⚠️ = 技术上可用但须合同/权利确认；❌ = 不适合该用途。`公开展示`指把数值/图表展示给外部用户，而非仅提供到原站链接。

|来源（已证实 KOSPI Composite）|数据类别与更新/延迟语义|接口/协议（已发布）|公开成本；账户、地域、许可门槛|研究|内部看板|生产信号|公开展示|
|---|---|---|---|---|---|---|---|
|**韩国金融委员会（FSC）公共数据门户：`금융위원회_지수시세정보`**|**日频/EOD**。官方目录将其列为“指数行情信息”，搜索结果明确为日更；请求按 `basDt`（基准日）取数。因此它不是盘中实时源。官方还发布过此 API 因数据问题延迟的通知，须做完整性/日期监测。|申请 service key 的 REST OpenAPI；资料说明支持 JSON/XML。[目录](https://www.data.go.kr/data/15094807/openapi.do)；[延迟公告](https://www.data.go.kr/bbs/ntc/selectNotice.do?originId=NOTICE_0000000004829)|目录搜索结果标示免费；需 data.go.kr 账户及活用申请/API key。未找到公开材料证明“大陆居民必然不能注册”，但韩文实名认证/审核、跨境网络可达性与服务可持续性应在小样本注册中验证。开放数据不自动授予交易所指数商标/外部再分发权。|✅|⚠️ 仅 EOD、内部且经条款确认|⚠️ 仅日频/收盘后模型，不能用于盘中|❌ 未见该 API 授予行情再分发/指数商业展示权|
|**KRX Data Marketplace / KRX OPEN API：指数服务**|**日频/历史为保守可证口径**。官方“指数”服务和服务清单明确覆盖 KOSPI/KOSDAQ 指数；实时指数另由 Koscom/单独许可处理，不能把本 API 误称实时。KRX 的 Information Data System 也提供指数数据下载/查询。|OPEN API；KRX 发布的数据接收说明为 **REST、JSON/XML**；须 API key。[指数服务](https://openapi.krx.co.kr/contents/OPP/USES/service/OPPUSES001_S1.cmd) / [服务清单](https://openapi.krx.co.kr/contents/OPP/INFO/service/OPPINFO004.cmd) / [接收方式](https://openapi.krx.co.kr/contents/OPP/DATA/OPPDATA003.jsp) / [IDS](https://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd?locale=en)|公开页面未给出 KOSPI API/历史数据的统一价目；账户、API key 与服务申请是已发布要求（key 页面说明有效期一年、可续）。KRX 有单独[指数许可页面](https://openapi.krx.co.kr/contents/OPP/DATA/OPPDATA005.jsp)，故产品化/展示不是“注册后免费即获许可”。大陆主体是否可直接签约、付款和接入没有公开承诺，按 quote/法务审查。|✅|⚠️ EOD/历史，内部许可确认后|⚠️ 只适合非盘中信号；以实际服务响应/完整性验收|❌/⚠️ 需 KRX 指数许可明确写入合同后才可|
|**Koscom Open API（行情服务 v3，KOSPI 专用实时路径）**|**实时**：官方文档检索到 KOSPI 指数路径 `/v3/market/realtime/index/kospi/K1`，并将该服务称“实时”。这不是“无延迟”或交易级 SLA 的证据；应在合同约定 source timestamp、可用性、丢包/重放及最大延迟。|HTTP API、API key；[KOSPI/指数实时页](https://koscom.gitbook.io/open-api/api/marketv3/index/realtime)，[v3（按 licence）](https://koscom.gitbook.io/open-api/api/marketv3)，[申请流程](https://koscom.gitbook.io/open-api/how-to-use/procedure)。|页面以 licence 分层，未公开 KOSPI 实时价格，故 **quote-only**。需开发者/商业申请和对应许可；公开资料未证明中国主体被排除，也未承诺可签跨境合同。需确认 KRX/Koscom source entitlement、部署 IP/地域和再分发权。|⚠️ 成本通常不划算，但可用|✅（许可覆盖员工/设备后）|✅（前提是取得实时许可和 SLA）|❌/⚠️ 只有合同明确 external redistribution/display 才可|
|**Koscom 机构 Market Data Service**|**实时及批量**。Koscom 官方服务页明确称为 KRX 与 OTC 的实时/批量行情分发；KOSPI 是该 KRX 指数行情范围内的可采购项目。网页未给出 KOSPI 的毫秒延迟/刷新周期。|专线、互联网、FTP（官方页列出）；没有把公共 REST/WebSocket 规格作为此机构服务公开。[官方服务说明](https://www.koscom.co.kr/eng/main/contents.do?menuNo=300126)|**quote-only**；机构合同、数据许可、网络接入与按用户/用途 entitlement 是实质门槛。中国团队还应事先确认跨境线路、发票/付款和中国合规责任；官方页面未作自动准入保证。|✅（若预算允许）|✅|✅（本地一级候选；SLA 必须询价）|⚠️ 必须采购/签署外部展示和再分发权|
|**Bloomberg（公开可检索标识 `KOSPI:IND`）**|产品族可提供实时和历史；[Bloomberg 的 KOSPI:IND 报价页](https://www.bloomberg.com/quote/KOSPI:IND)直接证明该标识是 KOSPI。B-PIPE 是其发布的实时行情 feed；具体 KOSPI entitlement、延迟和历史深度依合同，网页没有 KOSPI SLA。|Terminal API/Server API、B-PIPE 等；[B-PIPE 实时 feed 说明](https://www.bloomberg.com/professional/insights/markets/india-s-rbl-bank-adopts-bloomberg-b-pipe-for-real-time-market-data-access/)。|**quote-only**；终端/API 或企业数据合同、Korean exchange entitlement 和再分发 addendum。大陆可采购与否、网络交付和实体资格依销售/合规审查，非公开自助 API。|✅|✅（entitled users/系统）|✅（采购 B-PIPE/企业交付及 SLA 后）|⚠️ 要 Bloomberg + KRX 的外部再分发许可|
|**LSEG / Reuters（公开可检索标识 `.KS11`）**|Reuters [`.KS11` 页面](https://www.reuters.com/markets/quote/.KS11)明确对应 KOSPI，且页面注明**所有报价至少延迟 15 分钟**。付费 LSEG Real-Time 可提供实时/全 tick 数据，但 `.KS11` 的实时 entitlement 与延迟须订单确认。|网页免费查看无公共数据 API；企业产品为 LSEG Data Platform/Real-Time，发布 WebSocket 与实时 snapshot 文档，并由 DACS entitlement 控制：[Real-Time Optimized](https://www.lseg.com/en/data-analytics/market-data/data-management/real-time-optimized)、[实时 snapshot API](https://developers.lseg.com/en/api-catalog/refinitiv-data-platform/refinitiv-data-library-for-python/tutorials/content-tutorials/pricing/realtime-snapshot)、[DACS](https://developers.lseg.com/en/article-catalog/article/introduction-dacs-entitlement-system-opendacs-developers)。|Reuters 页面免费；LSEG 企业实时/历史为 **quote-only** + entitlement。中国实体、跨境数据交付和 KRX 外部展示须销售/法务确认。|✅（网页仅人工/低频；企业 API 可自动化）|⚠️ 网页不宜嵌入；企业合同后 ✅|❌ 网页；✅ 企业实时授权+SLA 后|❌ 网页数据再发布；⚠️ 企业合同明确许可后|
|**Reuters 免费延迟网页（`.KS11`）**|**免费、至少 15 分钟延迟**（Reuters 页面明示）。该说法只约束网页报价，不能外推至 LSEG 付费 feed 或精确 15:00。|无发布的免费开发者 API；仅网页。|免费访问不等于抓取、缓存或再分发许可；对中国开发者还存在网站连通性不确定性。|⚠️ 人工核验；自动抓取前先审条款|❌|❌|❌|

### 适用性判定的关键限制

1. **生产信号**：只有 Koscom 实时 API/机构 feed、或已采购 Bloomberg/LSEG 实时企业产品是候选。上线门槛不是“能拿到一个数”，而是合同中同时有 KOSPI entitlement、允许的 automated use、SLA、故障补数/重放、审计和目的地/用户限制。未取得 SLA 前，延迟只能写为“实时产品”，不能写具体毫秒数。
2. **内部看板与公开展示不同**：将数据显示给公司员工也可能计为 display/user entitlement；展示给公众几乎必然涉及 KRX 指数许可和供应商 redistribution 条款。任何“免费网页/API”均不应默认可公开显示。
3. **中国大陆特有的尽调**：本次的一手公开文档均没有给出“大陆开发者可无条件开户/接收 KOSPI 实时数据”的承诺，也没有提供固定跨境网络延迟。应以中国主体名义索取书面报价，明确接入地域/IP、数据存储地、可使用人员、是否可向大陆传输、币种/税务与对外展示；同时做一周小样本监控（timestamp、漏包、EOD 到达时间）再决定。

## 建议的最短采购路径

1. **立即做研究**：申请 FSC `15094807`，以 KRX 日频/API 做每日 OHLC/收盘值交叉校验；将“无数据/晚到/修订”作为正常状态处理，而非静默填充。
2. **需要实时但预算敏感**：先向 **Koscom Open API** 索取 KOSPI `K1` 的 licence tier、实时定义、月费、内部 display、automated signal、external display 和大陆交付条款。它是本次找到的唯一公开文档直接给出 KOSPI 实时 REST 路径的本地候选。
3. **需要机构级全球统一数据**：若公司已用 Bloomberg 或 LSEG，先让销售在订单中确认 `KOSPI:IND` / `.KS11`、延迟分类和所需 rights；否则向 Koscom 机构 feed 与这两家同时询价。不要因公开报价页存在而假设企业 API 含该指数。
4. **公开产品**：先取得 KRX index licence，再让 chosen vendor 在订单写入 website/app redistribution；这两项缺一不可。

## 已拒绝或未验证的候选

以下并非断言“绝不覆盖 KOSPI”，而是**本次没有找到满足“当前官方文档明确给出 KOSPI Composite/KS11 标识或可搜索 instrument”标准的证据**，故不作为可采购结论：

|候选|为什么拒绝/待证实|重新纳入所需证据|
|---|---|---|
|FactSet|其[Global Prices API](https://developer.factset.com/api-catalog/factset-global-prices-api)及 [Benchmarks API](https://developer.factset.com/api-catalog/factset-benchmarks-api)说明产品能力；KRX–FactSet thematic-index 合作也不证明 **KOSPI Composite** 可用。未找到公开的 KOSPI/KS11 instrument 查询结果。|销售/FactSet workstation 的带时间戳 instrument-search 截图或 API response，外加 real-time、history、display/redistribution entitlement 书面报价。|
|ICE Data|ICE 的 [KRX catalogue 页](https://developer.ice.com/fixed-income-data-services/catalog/korea-exchange-krx)证实其有 KRX catalog，但公开页没有明确 KOSPI Composite 字段/代码、延迟或 API entitlement。|ICE coverage list/API catalog 中 KOSPI Composite 的直接记录和所购产品的许可/SLA。|
|Twelve Data|其[全球指数 API 页面](https://twelvedata.com/indices)描述指数产品，且有 [KRX exchange 页面](https://twelvedata.com/exchanges/xkrx)，但公开页面未能给出 KOSPI Composite/KS11 的可检索 instrument/API 响应。|官方 symbol-search 结果或数据页明确返回 KOSPI Composite，及该 plan 的 realtime/delay 与商用展示条款。|
|EODHD、Tiingo、Polygon/Massive、Alpha Vantage|找到的是通用指数/交易所 API 或 KRX 股票/ETF 信息，未找到当前官方文档直接证明 KOSPI Composite/KS11。|同上：官方仪器记录、数据类/延迟、价格和用途权利。|
|Yahoo Finance、Google Finance、Investing.com、TradingView|这些站点可显示 KOSPI/`^KS11`/`KOSPI:KRX`，但本次未发现可用于再分发的正式公共 API/许可或 KOSPI 专属可依赖延迟 SLA；不能替代生产数据合同。|官方 developer product 的具体 symbol 查询、延迟语义和 commercial redistribution terms。|
|Korea Investment & Securities (KIS)|题目说明已有 KIS/Koscom 前序研究；本报告没有把 KIS 作为“替代来源”重复计入。|若要比较，需将前序 KIS 结论按同一四用途/许可矩阵复核。|

## 来源与证据质量

### 保留的一手来源

- [FSC 公共数据门户：金融委员会_指数行情信息](https://www.data.go.kr/data/15094807/openapi.do) — 官方免费 API 数据集、申请入口和服务描述。
- [FSC/公共数据门户 API 延迟公告](https://www.data.go.kr/bbs/ntc/selectNotice.do?originId=NOTICE_0000000004829) — 不能假设开放行情 API 永远准时的直接证据。
- [KRX OPEN API 指数服务](https://openapi.krx.co.kr/contents/OPP/USES/service/OPPUSES001_S1.cmd)、[服务清单](https://openapi.krx.co.kr/contents/OPP/INFO/service/OPPINFO004.cmd)、[数据接收方式](https://openapi.krx.co.kr/contents/OPP/DATA/OPPDATA003.jsp)、[指数许可](https://openapi.krx.co.kr/contents/OPP/DATA/OPPDATA005.jsp) — 运营方的服务、协议和许可入口。
- [Koscom Open API：KOSPI/指数实时](https://koscom.gitbook.io/open-api/api/marketv3/index/realtime)、[v3 licence 服务](https://koscom.gitbook.io/open-api/api/marketv3)、[Market Data Service](https://www.koscom.co.kr/eng/main/contents.do?menuNo=300126) — 本地实时 API 路径及机构分发方式。
- [Bloomberg KOSPI:IND](https://www.bloomberg.com/quote/KOSPI:IND)、[B-PIPE](https://www.bloomberg.com/professional/insights/markets/india-s-rbl-bank-adopts-bloomberg-b-pipe-for-real-time-market-data-access) — instrument 存在及实时 feed 产品。
- [Reuters `.KS11`](https://www.reuters.com/markets/quote/.KS11)、[LSEG Real-Time](https://www.lseg.com/en/data-analytics/market-data/data-management/real-time-optimized)、[LSEG DACS](https://developers.lseg.com/en/article-catalog/article/introduction-dacs-entitlement-system-opendacs-developers) — instrument、免费页“至少 15 分钟延迟”与企业 entitlement 模式。

### 丢弃的证据类型

- 博客、GitHub wrapper/scraper、搜索结果中无法回到供应商页面的宣称：没有被用来证明许可、延迟或覆盖范围。
- 将 “KOSPI market/KRX equities coverage” 自动等同于 “KOSPI Composite index coverage” 的营销页：没有被用来纳入 FactSet、ICE 或商业 API 候选。

## 未决缺口与下一步

1. 公开资料没有给出 Koscom、Bloomberg、LSEG 的 KOSPI 实时价格、精确延迟、SLA、历史粒度或大陆接入资格；只能询价取得书面答复。
2. KRX/FSC 页面可证明 API 存在和日频定位，但公开检索页未提供稳定的机器可读 sample response 字段字典；注册后应做单日 smoke test，核对是否为 Composite（而非 KOSPI 200）、时区、收盘值和修订规则。
3. 任何公开展示均缺少可公开验证的完整权利链；在 KRX index licence 与供应商 redistribution 条款签妥前，结论一律为不可用。
