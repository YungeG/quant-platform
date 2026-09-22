# Bloomberg、LSEG/Refinitiv 与「StockTV」：KOSPI Composite 市场数据审计

> 归档说明（2026-09-22，非重新检索日期）：下文保留原调研记录；产品、资费、准入、接口和许可条件未在本次联网复核，未注明日期的断言不能当作现行报价或已获权限。URL 仅作原始来源定位，实际采购或接入前须重新核对一手条款并取得相应批准。本次只归档，不发送询价、不开户、不采集数据，也不授予交易或再分发权。
>
> 文末 `acceptance-report` 为原调研交付记录，其中命令、检查结果和 `noStagedFiles` 只描述原交付时状态，不是本次重新出具的验收或 Platform 权威发布。

---

> **决策结论（2026-04-21 核查）**：若需要可用于生产的 KOSPI Composite（KOSPI）实时数据，Bloomberg 和 LSEG 均是可进入询价/权限核验阶段的供应商；但公开资料没有给出该指数、该用途的价格、延迟 SLA 或中国分发权。**不要以 Terminal/Workspace/API 登录权限推定可用于服务器自动化或对外展示。** 名称为 StockTV 的服务至少有两个不相同的实体；用户提供的 Postman URL 已识别为 `api.stocktv.top`，但其公开材料仍未证明具有「已获 KRX 许可的 KOSPI Composite API/feed」或可再分发权，因此不可作为合规采购候选，除非取得其书面许可链。

## 1. 标的与证据强度

| 供应商/实体 | KOSPI Composite 识别符及可得性证据 | 可选接入产品 | 当前采购判断 |
| --- | --- | --- | --- |
| Bloomberg | **`KOSPI:IND`**；Bloomberg 的报价页标题为 “Korea Stock Exchange KOSPI Index”。[Bloomberg Quote](https://www.bloomberg.com/quote/KOSPI:IND) | Terminal/Terminal API（桌面、受用户订阅约束）；Server API（SAPI）；B-PIPE/Real-Time Market Data Feed。[SAPI](https://professional.bloomberg.com/products/data/data-connectivity/server-api)、[real-time feed](https://professional.bloomberg.com/products/data/enterprise-catalog/real-time-data-feed) | 可询价；须使 Bloomberg（及其 KRX 数据权利链）对 `KOSPI:IND`、用途和地域书面确认。 |
| LSEG/Refinitiv | **`.KS11`**；LSEG Developer Community 的 KOSPI 索引讨论直接将其标为 KOSPI，且提示实时订阅/权限可能决定可取数。[LSEG 社区](https://community.developers.lseg.com/discussion/103244/cant-get-constituent-ric-of-korean-index-via-python-api) | LSEG Workspace/RDP APIs（REST/streaming）；Real-Time Distribution System (RTDS)；Real-Time Direct/Full Tick feeds。[RDP APIs](https://developers.lseg.com/en/api-catalog/refinitiv-data-platform/refinitiv-data-platform-apis)、[RTDS](https://www.lseg.com/en/data-analytics/market-data/data-management/real-time-distribution-system)、[Direct](https://www.lseg.com/en/data-analytics/market-data/data-feeds/direct-feeds) | 可询价；`.KS11` 的实际字段/实时权限须用目标服务 ID 试订阅并由 LSEG 确认。 |
| StockTV（`stocktv.app`） | 面向电视的个人行情 dashboard/app；没有公开 KOSPI、API/feed、KRX 数据源或市场数据许可证据。[官网](https://stocktv.app)、[条款](https://stocktv.app/terms) | 电视 dashboard；未见机构 API/feed 产品页。 | **排除**。不是已证明的数据供应商。 |
| StockTV（`api.stocktv.top`，用户提供的 [Postman collection](https://documenter.getpostman.com/view/10940044/2sAYHxnPns)） | Postman 文档自称覆盖韩国，并发布 REST `/stock/indices`、`/stock/indicesById` 和 WebSocket 接入；但指数示例仅为印度 Nifty 50，未发布韩国 `countryId`、KOSPI Composite PID/代码、可复核返回或 KRX 数据来源/许可文件。 | API key 的 REST/JSON 与 `wss://ws-api.stocktv.top/connect`；未公开 KOSPI 价格、限频、延迟/SLA 或再分发条款。 | **技术 POC 候选，非合规采购候选**：先用测试 key 验证 KOSPI，再取得 KRX 权利链与用途许可。 |

**已确认的 URL：** 用户提供的 Postman collection 对应 `api.stocktv.top`；`stocktv.app` 仍是另一家电视看板产品。Postman 文档足以核验 API 形态，不足以完成数据许可尽调。

## 2. Bloomberg

1. **标的与产品。** `KOSPI:IND` 是 Bloomberg 可识别的 KOSPI 指数代码。人工查看适用 **Terminal**；桌面 API 随 Terminal 工作流，Bloomberg 的 API Library 是其官方开发入口。[Quote](https://www.bloomberg.com/quote/KOSPI:IND)、[API Library](https://professional.bloomberg.com/support/api-library) 服务器端应用应谈 **SAPI**；需要企业实时 feed 则谈 **B-PIPE/Real-Time Market Data Feed**，不要把桌面 API 当 feed 替代品。[SAPI](https://professional.bloomberg.com/products/data/data-connectivity/server-api)、[B-PIPE/real-time feed](https://professional.bloomberg.com/products/data/enterprise-catalog/real-time-data-feed)
2. **三类使用权必须拆单。** (a) 员工在 Terminal/获授权内部屏幕上的 **manual display**；(b) 服务器读取、研究、模型、风控、信号、自动交易、缓存或派生计算的 **internal automated non-display**；(c) 网站/App、客户屏幕、客户 API/feed 的 **external display/redistribution**。Bloomberg 把 Server API 描述为把数据接入专有或第三方应用的产品；这不等于公开授予任何下游再分发。其 Index Data Licensing 页面也说明数据许可/再分发须通过 licensing 获取。[SAPI](https://professional.bloomberg.com/products/data/data-connectivity/server-api)、[Index Data & Licensing](https://www.bloomberg.com/professional/products/indices/index-data-licensing)
3. **时效、频率、费用。** 官方产品页只可支持“real-time”产品定位；本轮未找到 `KOSPI:IND` 的公开延迟（秒数）、tick 更新频率、SLA，或 Terminal/SAPI/B-PIPE 及三类用途的公开数字价格。因此全部为 **quote-only**，不得填入 0、免费或估算单价。更不能从 `KOSPI:IND` 是可检索证券推出该客户必有实时 entitlement。
4. **中国。** 没有发现 Bloomberg 一手公开材料证明中国境内实体可取得 `KOSPI:IND` 的实时接收、云处理、非展示或外部分发权。结论是 **未知、待合同**，不是“允许”或“禁止”。要求书面确认：中国法人/关联方、用户所在地、云区域/跨境传输、客户所在地、终端/API 再分发和 KRX exchange fees/报表责任。

## 3. LSEG/Refinitiv

1. **标的与可得性。** `.KS11` 是 LSEG/Reuters 代码体系中的 KOSPI 证据；LSEG 开发者社区在处理韩国指数成分 API 问题时直接涉及该代码，并指出权限/订阅会阻断实时取数。[LSEG 社区](https://community.developers.lseg.com/discussion/103244/cant-get-constituent-ric-of-korean-index-via-python-api) 这证明“代码/目录存在”的实务证据，**不是**对每一账户、字段或实时状态的无条件承诺。
2. **接入路径。** 人工 display 可谈 LSEG Workspace；程序化小规模/云集成可谈 RDP APIs（LSEG 的平台 API 目录）；实时企业分发/低延迟路径为 RTDS、Real-Time Direct 或 Full Tick。[RDP APIs](https://developers.lseg.com/en/api-catalog/refinitiv-data-platform/refinitiv-data-platform-apis)、[RTDS](https://www.lseg.com/en/data-analytics/market-data/data-management/real-time-distribution-system)、[Direct](https://www.lseg.com/en/data-analytics/market-data/data-feeds/direct-feeds)、[Full Tick](https://www.lseg.com/en/data-analytics/market-data/data-feeds/real-time-full-tick-data)
3. **entitlement/使用限制。** RDP 的实时认证资料称访问权限取决于 RDP license；即 token/API credential 不等于市场数据 entitlement。[RDP 实时认证](https://developers.lseg.com/en/article-catalog/article/getting-started-with-version-2-authentication-for-refinitiv-real) 对外客户交付应进入 LSEG 的 Data Redistribution 项目，而非沿用内部 Workspace/RDP 权利。[LSEG Data Redistribution](https://www.lseg.com/en/data-analytics/market-data/data-redistribution) 因而同样把 manual display、internal non-display、external redistribution 分别报价/签约。
4. **时效、频率、费用和中国。** 产品名证明有 “Real-Time/Full Tick/Direct” 类能力；但本轮未找到 `.KS11` 专属的公开延迟、更新频率、最大吞吐、价格或中国条款。均为 **quote-only / China unknown**；须让 LSEG 对 Service ID 实测 entitlement、所购字段（last/close/实时）、non-display、缓存/历史、派生数据、客户端/API 再分发和 PRC 用户/基础设施逐项书面确认。

## 4. StockTV：先识别实体，再谈数据

- **`stocktv.app`** 是“Live stock market dashboard for your TV”型产品，和机构市场数据供应商不是同一已证实类别；其公开入口/条款未展示 KRX 数据许可或 API feed。不能用其显示的行情反推可商用、可抓取或可再分发。
- **`api.stocktv.top` 的公开 Postman 文档已核对。** 它自称支持韩国股票行情，并给出 API key 的 REST `/stock/indices`、`/stock/indicesById` 及 WebSocket `wss://ws-api.stocktv.top/connect`。WebSocket schema 有 `type=2`（指数）和时间戳字段。不过指数样例是印度 Nifty 50；文档未给出韩国 `countryId`、KOSPI Composite PID/代码、实际 KOSPI 返回、数据源或 KRX 许可。[Postman collection](https://documenter.getpostman.com/view/10940044/2sAYHxnPns)
- 因此对该实体的关键结论仍是：**“覆盖韩国”与“有指数 API”已由其自发布文档声明；KOSPI Composite licensed feed、实时延迟/频率、成本、内部/非展示用途、外部再分发及中国权利仍未证明。** 这不是对其侵权的指控，而是采购/合规证据不足。

## 5. 采购门槛与可直接发出的 RFQ

两家成熟供应商均要求在同一封报价请求中逐项回复：

1. 标的精确为 Bloomberg `KOSPI:IND` 或 LSEG `.KS11`，字段、real-time/delayed/close、snapshot/streaming、历史回补；确认 KOSPI Composite 而非 KOSPI 200 或韩国股票列表。
2. 三个互斥报价包：**内部人工 display**（用户/屏幕/地点）；**内部 automated non-display**（服务器、模型、信号、自动下单、缓存、派生）；**外部 display/redistribution**（网页/App、客户数、客户 API/feed）。
3. 所有费用：供应商订阅、KRX/exchange fees、一次性接入、最低承诺、用户/服务器/应用/调用量/外部用户计量、审计/usage reporting、支持、税和币种；附生效日。公开没有数字时，预算字段填“供应商待报价”。
4. 时效/频率：KOSPI 专属 delay、tick 或 conflation 规则、SLA、数据日历；若非实时，明确延迟秒/分钟。未书面答复前不要在产品文案写“实时”。
5. 中国：PRC 注册主体是否可签、韩国/中国/其他云区与跨境传输、PRC 内部用户和外部终端用户、制裁/KYC、数据留存与审计是否可行。

## 6. 保留与排除的资料

**保留（一手/直接供应商资料）**

- [Bloomberg KOSPI Quote](https://www.bloomberg.com/quote/KOSPI:IND) — 标识符直接证据。
- [Bloomberg SAPI](https://professional.bloomberg.com/products/data/data-connectivity/server-api)、[API Library](https://professional.bloomberg.com/support/api-library)、[real-time feed](https://professional.bloomberg.com/products/data/enterprise-catalog/real-time-data-feed) — 产品/接入层证据。
- [LSEG RDP APIs](https://developers.lseg.com/en/api-catalog/refinitiv-data-platform/refinitiv-data-platform-apis)、[RTDS](https://www.lseg.com/en/data-analytics/market-data/data-management/real-time-distribution-system)、[Direct](https://www.lseg.com/en/data-analytics/market-data/data-feeds/direct-feeds)、[Data Redistribution](https://www.lseg.com/en/data-analytics/market-data/data-redistribution) — API/feed/外部交付产品证据。
- [LSEG 开发者社区 `.KS11`](https://community.developers.lseg.com/discussion/103244/cant-get-constituent-ric-of-korean-index-via-python-api) — 供应商托管的代码与 entitlement 实务证据。
- [StockTV.app](https://stocktv.app)、[StockTV Postman collection](https://documenter.getpostman.com/view/10940044/2sAYHxnPns)、[CryptoRzz GitHub](https://github.com/CryptoRzz/stocktv-api-py) — Postman collection 证明其自发布的 REST/WS 接口形态；均不构成 KRX 市场数据权利证据。

**排除**

- Yahoo、CNBC、Investing、TradingView、博客聚合及搜索摘要：可佐证大众显示的代码，不是 Bloomberg/LSEG/StockTV 的许可或价格条款。
- 任何“免费 API”“实时”营销转述、论坛报价：没有 KRX 权利链、用途、日期及合同计量单位，不能用于采购或预算。

## 7. 剩余风险与下一步

- **高风险：StockTV 的 KOSPI 权利链为空。** Postman 文档确认了 `api.stocktv.top` 的接口形态，但仍应要求其提交法人名称、韩国 `countryId` 与 KOSPI Composite PID、测试 key 返回、数据来源、KRX 授权/转授权、现行 MSA/market-data schedule、三类用途和 PRC 书面许可。未收到前只能作技术 POC，不能采购上线。
- **中风险：Bloomberg/LSEG 的“可见代码”不等于此账户实时资格。** 在采购前由销售/entitlements 团队对目标法人、Service ID 和 `.KS11`/`KOSPI:IND` 给出书面确认，并以 test entitlement 验证。
- **中风险：中国。** 三家均无本轮可核验的一手公开 PRC 权利结论；不应上线跨境接收、云处理或对中国客户展示，直至合同确认。

> 本文只记录可核验的产品定位；凡未见供应商公开数字的 delay、frequency、cost 均明确标为 quote-only，未作推算。

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "已在 research/bloomberg-lseg-stocktv-kospi-research.md 给出 Bloomberg KOSPI:IND、LSEG .KS11、StockTV 实体歧义、三类用途、报价/中国风险及一手链接。"
    }
  ],
  "changedFiles": [
    "research/bloomberg-lseg-stocktv-kospi-research.md"
  ],
  "testsAddedOrUpdated": [],
  "commandsRun": [
    {
      "command": "focused web_search (Bloomberg/LSEG/StockTV first-party sources) and fetch_content",
      "result": "passed",
      "summary": "检索到官方产品与标识符页面；部分站点受运行环境 fake-IP SSRF 限制，已保留直接官方 URL。"
    }
  ],
  "validationOutput": [
    "已核查输出文件包含决策结论、来源链接、quote-only 边界及 StockTV URL 澄清要求。"
  ],
  "residualRisks": [
    "公开资料未披露 KOSPI 专属价格、延迟/频率、三类用途条款或中国权利；须由供应商书面报价/合同确认。",
    "用户指定的 Postman URL 已识别为 api.stocktv.top；但未获 KRX 许可链、KOSPI instrument 证据和用途权利文件前，不可作为获许可 KOSPI feed。"
  ],
  "noStagedFiles": true,
  "diffSummary": "新增 Bloomberg、LSEG/Refinitiv 与 StockTV 的 KOSPI Composite 许可/接入审计中文简报。",
  "reviewFindings": [
    "high: StockTV 的已获许可 KOSPI Composite API/feed 未获一手合同或 KRX 权利链证明；采购前应排除。",
    "medium: Bloomberg/LSEG 的可见标识符和 API 产品不构成实时、non-display、外部再分发或 PRC 权利。"
  ],
  "manualNotes": "未将未证实的延迟、频率或价格写成事实；全部留待 RFQ/合同确认。"
}
```
