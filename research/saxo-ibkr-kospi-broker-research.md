# Saxo 与 IBKR：KOSPI 综合指数（非 KOSPI 200）及韩国市场可行性

> 归档说明（2026-09-22，非重新检索日期）：下文保留原调研记录；产品、资费、准入、接口和许可条件未在本次联网复核，未注明日期的断言不能当作现行报价或已获权限。URL 仅作原始来源定位，实际采购或接入前须重新核对一手条款并取得相应批准。本次只归档，不发送询价、不开户、不采集数据，也不授予交易或再分发权。

---

> **结论等级：阻断（用于“精确的 KOSPI Composite 数据”）；可行（仅 IBKR 的韩国交易所股票/ETF 交易）。** 本文只接受 Saxo/IBKR 第一方资料；“KOSPI/韩国市场”文字出现、韩国股票交易权限或 KOSPI 200 衍生品均**不**被当作 KOSPI Composite 数据存在的证据。资料页面和资费可随账户主体/地区改变，实施前应在拟开户账户的交易权限、合约搜索和数据订阅界面复核。

## 决策摘要

- **Saxo：不建议作为中国大陆开发者的路线。** Saxo 的服务国家清单不列中国大陆；其公开产品/数据订阅资料中也没有找到 KRX 或 KOSPI Composite 的可交易合约、UIC、数据包或报价。OpenAPI 的能力本身很完整，但不能弥补开户和标的证据的缺口。
- **IBKR：可作为“韩国上市股票/ETF 执行”候选，但不是已验证的 KOSPI Composite 数据源。** IBKR 将中国列为可开户国家，并明确宣传 KRX 股票、ETF 和期货交易；其资费页列出韩国股票 L1 bundle 和韩国衍生品 L2。但这些均没有把 **KOSPI Composite** 列为指数/合约，亦未给出 symbol/conid，故不可据此声称取得了综合指数（更不能以 KOSPI 200 期货替代）。
- **公共产品：两者均不应直接使用。** 第一方公开资料未给出将该数据公开展示、再传输或再分发的权利；IBKR 的协议检索结果明确要求再分发另行签署 Market Data Distribution Agreement。内部自动化亦须先确认准确合约和交易所数据权利；不得把 API 可访问误读成再分发许可。

## 口径与判断规则

- **目标**：韩国综合股价指数 KOSPI Composite，而非 KOSPI 200、韩国单股、韩国 ETF、ADR 或泛韩国指数 ETF。
- **“已证实”**指第一方页面明确列出目标合约/指数或明确授权；**“未知”**不是“没有”，而是当前第一方公开资料不足，不能作为产品承诺。
- **账户可开 ≠ 市场许可 ≠ 数据权限 ≠ 再分发权。** 四项分别验证。

## 1. Saxo（单独分析）

| 问题 | 第一方证据与结论 | 风险/严重性 |
| --- | --- | --- |
| 1) 中国大陆居住者开户 | Saxo 的[服务国家清单](https://www.help.saxo/hc/en-us/articles/10611416570269-Which-countries-are-serviced-by-Saxo)的检索结果不列 China，并说明服务范围/新开户可能变化。故对**中国大陆税务/居住地址的个人开发者：不可按公开资料假定可开**；应先向 Saxo 取得书面准入确认。 | **阻断 / 高** |
| 2) 韩国市场产品访问 | Saxo 的[股票产品页](https://www.home.saxo/products/stocks)描述全球股票能力，但此次第一方公开资料中没有 KRX/Korea Exchange 的产品/市场清单或客户资格证据。不能从其韩国 ADR 页面、市场评论或“全球股票”宣传推断可买 KRX 标的。 | **未知，阻断执行 / 高** |
| 3) KOSPI Composite 精确标的/symbol | 未在 Saxo 面向客户的市场页、OpenAPI 参考资料或公开数据订阅页找到名为 `KOSPI Composite` 的 UIC、symbol、asset type 或 exchange。OpenAPI 的[Reference Data](https://www.developer.saxo/openapi/learn/reference-data)说明应以 instrument reference 查询 UIC；它不是目标标的已存在的证明。**精确标的：未知。** | **阻断数据/信号 / 高** |
| 4) 数据包、实时/延迟、价格、资格 | Saxo 的[Equity Market Data Subscriptions](https://www.home.saxo/products/market-data-subscriptions)是官方订阅入口，但其公开检索资料未列韩国/KOSPI Composite 的 package、月费、专业/非专业资格或延迟分钟数。官方 OpenAPI 支持页说明实时价须在 live 环境启用相应 market-data access（见[如何启用数据](https://openapi.help.saxo/hc/en-us/articles/4418427366289-How-do-I-enable-market-data)和[订阅后仍延迟](https://openapi.help.saxo/hc/en-us/articles/4416934340625-Why-are-quotes-still-delayed-after-I-subscribe-to-market-data)）。**目标指数的上述四项均未知，不能报价为“免费/实时”。** | **阻断商业估算 / 高** |
| 5) API 与内部/公开使用 | [Saxo OpenAPI](https://www.developer.saxo/openapi/learn/high-level-overview)及[交易 API](https://www.developer.saxo/openapi/learn/trade)提供账户相关的报价/交易能力，且 session capability 会暴露数据权限状态（[Session Capabilities](https://www.developer.saxo/openapi/learn/session-capabilities)）。可用于获准账户的内部集成在技术上可行；但第一方公开资料没有给予本项目 KOSPI Composite 报价的公开展示/再分发许可。故**内部自动化：仅在账户、标的、订阅和合同均确认后才可用；公开产品：不可以此为依据上线，须单独书面数据许可。** | **公开产品阻断 / 高** |
| 6) 模拟/纸面 | [Simulation Environment](https://www.developer.saxo/openapi/learn/environments)用于 API 测试；官方支持资料把实时数据权限与 live 环境/订阅相连。公开资料没有证实模拟环境提供同一条 KOSPI Composite 数据或相同延迟语义。**不可把模拟报价当成此指数的实时、许可或可交易性验证。** | **高** |
| 7) 限制与最终结论 | 开户和目标标的两道关键证据均缺失；API 不能改变市场数据许可。**研究：仅可把 Saxo 当“待书面核实”的接口候选，不能当数据源。内部看板/信号、执行、公开产品：当前均否。** | **阻断 / 高** |

## 2. Interactive Brokers（IBKR，单独分析）

| 问题 | 第一方证据与结论 | 风险/严重性 |
| --- | --- | --- |
| 1) 中国大陆居住者开户 | IBKR 的[Available Countries and Territories](https://www.interactivebrokers.com/en/accounts/open-account-country-list.php)将 China 列为可开户国家；[申请材料说明](https://www.interactivebrokers.com/en/general/what-you-need-inv.php)要求身份证明、住址证明等。故“可申请”有公开证据，但不等于审核必过、可入金、可获全部交易权限；以开户流程的实际实体/合规审核为准。 | **可行但需 KYC/跨境合规确认 / 中** |
| 2) 韩国市场产品访问 | IBKR 的[KRX 页面](https://www.interactivebrokers.com/en/trading/krx-exchange.php)明确宣传可交易韩国交易所的股票、ETF、期货；其[韩国股票收费页](https://www.interactivebrokers.com/en/accounts/fees/KOREA-StkFees.php)也证明存在韩国股票交易收费项目。**韩国交易所股票/ETF 执行：有第一方正面证据，仍需账户开通 Korea 权限和订单前的合约/资格检查。** | **可行 / 中** |
| 3) KOSPI Composite 精确标的/symbol | IBKR 第一方公开 KRX 页、市场数据资费页和 API 合约说明中未找到 `KOSPI Composite` 的 exact symbol、conid、交易所或指数数据 entitlement。KRX 股票/ETF 与 `Korea Equities Bundle` 不能推出它；`Korea Exchange - Derivatives` 更不能被改称 KOSPI Composite（尤其不可用 KOSPI 200 期货代替）。**精确标的：未知；未证实可通过 IBKR 获得。** | **阻断指数数据/信号 / 高** |
| 4) 数据包、实时/延迟、价格、资格 | [Market Data Pricing](https://www.interactivebrokers.com/en/pricing/market-data-pricing.php)列出：`Korea Equities Bundle (L1)`（South Korea，非专业/专业均 Fee Waived）和 `Korea Exchange - Derivatives (L2)`（非专业 USD 2/月、专业 USD 68/月）。同页延迟表把 `Korea Stock Exchange (KSE)` 写为 **20 分钟**，实时订阅名称为 `Korea Stock Exchange`；并规定一般个人订阅至少 USD 500 净值，专业/非专业由供应商分类。此为**韩国证券/衍生品**数据价格和延迟语义，**不是 KOSPI Composite 已被覆盖的证明**，也未显示该指数的费用/资格。 | **指数目标仍阻断 / 高** |
| 5) API 与内部/公开使用 | [TWS API 文档](https://www.interactivebrokers.com/campus/ibkr-api-page/trader-workstation-api)包含行情、历史数据和下单；[Client Portal/Web API 交易文档](https://www.interactivebrokers.com/campus/ibkr-api-page/web-api-trading)也支持账户交易集成。IBKR 定价页明确实时行情可在 TWS **或 API**显示，前提是订阅。故：**账户内内部采集/信号/执行在技术上可行，前提是精确合约存在且已获订阅、权限和 API entitlement。** 对外展示/再传输不在该事实内；[IBKR Market Data Subscriptions](https://www.interactivebrokers.com/campus/ibkr-api-page/market-data-subscriptions)要求 API 数据满足订阅条件，而其客户协议检索资料指出公开展示、redistribution/re-transmission 须另签 Market Data Distribution Agreement（见[IBKR Hong Kong Client Agreement](https://gdcdyn.interactivebrokers.com/Universal/servlet/Registration_v2.formSampleView?formdb=4144)）。**公共产品：无单独书面许可不得使用。** | **公开产品阻断 / 高** |
| 6) 模拟/纸面 | IBKR 的[Paper Trading Accounts](https://www.ibkrguides.com/clientportal/aboutpapertradingaccounts.htm)说明模拟账户用于无资金风险的模拟，并有与实盘不同的限制；[TWS API 流式行情文档](https://interactivebrokers.github.io/tws-api/market_data.html)说明纸面账户可按设置共享 live 数据订阅，未订阅时适用延迟数据规则。**可测试 API/订单流程，但不能用纸面证明 KOSPI Composite 合约存在、实时 entitlement 已获，或模拟成交等同实盘。** | **中** |
| 7) 限制与最终结论 | IBKR 是本题唯一有公开正面证据的韩国现货交易路线；但没有第一方公开证据把 KOSPI Composite 作为可取行情的具体合约。**研究：可用于核验账户中的合约搜索和数据 entitlement；内部看板/信号：仅在搜索得到该精确指数并书面/界面确认数据权利后可用；执行：可交易 KRX 股票/ETF，不等于交易指数本身；公开产品：否，先取得指数/交易所再分发许可。** | **混合：执行可行，指数数据/公开产品阻断** |

## 实施前的最小验证（不以推断替代）

1. **Saxo**：先要求书面回答“中国大陆居住地址可否开个人账户、是否可开 KRX、KOSPI Composite 的 UIC/asset type、数据供应商/延迟/月费、内部与外部展示许可”。任一项不能给出即淘汰。
2. **IBKR**：以拟开户的中国大陆 live 账户，在 Client Portal/TWS 的 *Contract Search* 搜索 `KOSPI Composite`（并记录 conid、secType、exchange、currency、tradingClass），再在 Market Data Assistant/订阅页确认该 **同一 conid** 的 L1/指数 entitlement、实时或延迟、专业状态和费用。搜索到 KOSPI 200 或股票，不通过。
3. 先在纸面账户做 API 连通/订单流程 smoke test；只有同一数据 entitlement 在实盘账户得到确认，才验证实时指数行情。不得把纸面价格、20 分钟 KSE 延迟表或 KRX 股票 bundle 作为指数实时数据证据。
4. 若面向用户展示、报警转发、导出、API 转售或网页嵌入，即使只给内部客户，也先取得 KRX/指数供应商和经纪商允许的**书面再分发许可**；否则只做受控的账户内研究，不发布。

## 研究结论矩阵

| 场景 | Saxo | IBKR | 决策 |
| --- | --- | --- | --- |
| 离线研究/回测（需要 KOSPI Composite 历史） | 未证实 | 未证实 | **不要选任一作为已确认的指数历史数据源** |
| 内部 dashboard / signal（实时或延迟的 KOSPI Composite） | 未证实，且开户阻断 | API/韩国数据能力存在，但目标指数未证实 | **暂停；先做 IBKR 同-conid 验证** |
| KRX 单股/ETF 执行 | 未证实 | 有正面证据 | **IBKR 可进入开户/权限验证** |
| 交易“指数本身” | 未证实 | 未证实 | **否；不要把 KOSPI 200 衍生品当替代** |
| 含指数价格的公共 SaaS/API/网页 | 无再分发证据 | 需另签再分发协议 | **否，先购/签数据再分发权** |

## 来源审计

### 保留（第一方）

- [Saxo — Which countries are serviced by Saxo?](https://www.help.saxo/hc/en-us/articles/10611416570269-Which-countries-are-serviced-by-Saxo) — 中国大陆准入的公开负面/待确认依据。
- [Saxo — Equity Market Data Subscriptions](https://www.home.saxo/products/market-data-subscriptions) — Saxo 官方订阅入口；未列目标包是“不可证明”的边界，而非绝对不存在声明。
- [Saxo OpenAPI — Reference Data](https://www.developer.saxo/openapi/learn/reference-data)、[Session Capabilities](https://www.developer.saxo/openapi/learn/session-capabilities)、[Simulation Environment](https://www.developer.saxo/openapi/learn/environments) — UIC 查询、权限与模拟环境边界。
- [IBKR — Available Countries and Territories](https://www.interactivebrokers.com/en/accounts/open-account-country-list.php) — 中国可申请账户。
- [IBKR — Trade Korean Equities on KRX](https://www.interactivebrokers.com/en/trading/krx-exchange.php) 与 [Korea stock fees](https://www.interactivebrokers.com/en/accounts/fees/KOREA-StkFees.php) — KRX 股票/ETF/期货的正面交易证据。
- [IBKR — Market Data Pricing](https://www.interactivebrokers.com/en/pricing/market-data-pricing.php) — 韩国 L1/L2 数据包、20 分钟延迟、最低净值和专业分类。
- [IBKR — TWS API](https://www.interactivebrokers.com/campus/ibkr-api-page/trader-workstation-api)、[Web API trading](https://www.interactivebrokers.com/campus/ibkr-api-page/web-api-trading)、[paper account guide](https://www.ibkrguides.com/clientportal/aboutpapertradingaccounts.htm) — 自动化和模拟边界。
- [IBKR Hong Kong Client Agreement](https://gdcdyn.interactivebrokers.com/Universal/servlet/Registration_v2.formSampleView?formdb=4144) — 再分发必须另行合同的风险依据；实际签约实体的协议为最终准据。

### 丢弃

- Yahoo Finance、TradingView、Wikipedia、MarketWatch、经纪商评测、论坛/Reddit — 非经纪商第一方资料，且 symbol/行情权限不能转化为 Saxo/IBKR 的数据权利。
- KOSPI 200、韩国期货或韩国股票/ETF宣传 — 标的不同，不能满足本题“Composite 非 200”的验收口径。
- Saxo/IBKR 市场评论中提到“KOSPI” — 新闻文本不是可交易合约、API entitlement 或数据许可。

## 未解问题与剩余风险

1. **最高风险：**两家均没有在本次公开第一方资料中给出 KOSPI Composite 的 exact instrument/symbol/conid/UIC；因此不能承诺数据存在、延迟、实时性、历史深度或价格。
2. Saxo 中国大陆的拒绝/未列服务范围应由当前书面答复最终确认；不同实体、居住地址与监管状态可能改变结果。
3. IBKR 的中国大陆开户可申请不保证 KRX 权限、汇款可行性、税务/外汇合规或数据供应商非专业资格。
4. IBKR 的韩国数据资费会变化，且 `Korea Equities Bundle` / `Korea Exchange - Derivatives` 不必然含指数；必须按精确 conid 验证。
5. 公共展示的“用户数”“延迟再展示”“派生指标是否可发布”均未获许可证文本确认；需法务与数据供应商书面确认。
