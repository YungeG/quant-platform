# Koscom／KRX 实时 KOSPI Composite（K1）数据许可：价格简报

> 归档说明（2026-09-22，非重新检索日期）：下文保留原调研记录；产品、资费、准入、接口和许可条件未在本次联网复核，未注明日期的断言不能当作现行报价或已获权限。URL 仅作原始来源定位，实际采购或接入前须重新核对一手条款并取得相应批准。本次只归档，不发送询价、不开户、不采集数据，也不授予交易或再分发权。

---

> **结论（供预算决策）：不要把该数据按“公开 API 单价”采购。** 本次核查到的 Koscom/KRX 一手公开页面能确认 K1 实时接口、测试流程和 KRX 实时市场信息的产品/许可框架，但**未发现可公开核验的韩元金额价目表**。对一家中国（PRC）注册公司，须取得 Koscom 的书面报价及 KRX 许可确认；在此之前，六种使用情形均应按“报价待定”，而不是按免费或某个网络报价入账。

## 1. 先确认标的与公开价格结论

Koscom 的“시세 서비스 v3 (라이센스별)”页面列出 KOSPI 指数实时端点 `/v3/market/realtime/index/kospi/K1`，因此这里讨论的是 **KOSPI Composite 指数 K1 的实时市场数据**，不是 KRX Data Marketplace 的日终/历史下载数据。[Koscom：V3 市价服务（按许可）](https://koscom.gitbook.io/open-api/api/marketv3)

| 目标使用方式 | 是否找到一手公开、可核验的数字价格 | 结论 / 要取得的报价 |
| --- | ---: | --- |
| Koscom Open API：K1 实时读取 | **否** | API 接入费与“信息市价（market-data）许可”须分别/合并由 Koscom 报价；接口页面本身不是价目表。 |
| 机构原始/专线 feed | **否** | KRX 实时市场信息产品资料确认有实时产品和数据接收架构；具体 feed、接入/线路及许可费未公开列价。[KRX《实时市场信息产品及服务构成》](https://data.krx.co.kr/inc/datasale/Market%20Data%20Product%20Brochure.pdf?v=20250732) |
| 内部 display（员工/内部屏幕） | **否** | 要报：内部终端/用户（及是否按并发、地点或组织计数）的 K1 实时 display 权利。 |
| non-display 自动化使用（模型、信号、风控、交易、存储/再处理） | **否** | 要报：non-display / system processing 权利，明确算法、自动下单、缓存和派生指标是否纳入。不可把 API 访问理解为该权利已获授。 |
| 对外展示或再分发（网站、App、客户 API/feed） | **否** | 要报：外部 display、终端/MAU/客户数、地区、API/feed 再分发和任何二次分销权；须明确能否向中国境内用户提供。 |
| sandbox / test | **否** | Koscom 公开有 API 测试流程，但未找到 K1 **实时** sandbox 的公开数字价格、数据是否实时或模拟、测试时长及生产转换费用。[Koscom：API 测试流程](https://koscom.gitbook.io/open-api/how-to-use/devcenter) |

**“无公开数字”的含义。** KRX 的公开入口提供《[信息利用政策](https://data.krx.co.kr/inc/datasale/Market%20Data%20Usage%20Polices_ko.pdf?v=20250732)》和上述实时产品资料；其公开检索结果与 Koscom 的费用/许可页都将实际费用导向按用途询价，而没有可供下载后直接套用的 K1 金额表。[Koscom：使用对象及费用说明](https://koscom.gitbook.io/open-api/how-to-use/procedure/charge) 这不是“零费用”结论，也不能排除向已签约客户门户发放非公开费表。

## 2. 许可链和所有可见的成本驱动项

KRX 是交易所市场信息的权利方，Koscom 是其市场数据服务/平台渠道之一；Koscom 的 K1 API 页明确标注服务按许可区分，KRX 则公开“信息利用政策”和“实时产品及服务构成”。因此报价应至少拆成下列行项目，避免只取得 API 调用价而缺少市场数据权利：

1. **数据与市场范围**：只要 K1 指数，还是 KOSPI 全部股票实时字段；实时、延迟或收盘数据；快照、全量/增量、历史回补。
2. **交付路径**：Koscom Open API 或机构 feed；API key/环境、接入、网络/专线、带宽、安装及支持费；生产与 test/sandbox 是否分别收费。
3. **使用性质**：display（内部或外部）与 non-display（服务器处理/算法）必须逐项勾选。K1 进入量化研究、信号或自动交易即应要求对方书面界定。
4. **受许可对象与计量单位**：法人实体、关联公司、员工/终端/并发、服务器或应用实例、客户/终端用户、调用量及地区。请求供应商说明每一项的计费单位、最低收费和阶梯。
5. **分发及地域**：内部使用、面向客户显示、网页/App、客户 API/feed、再分销/子许可、是否允许 PRC 境内接收或展示、跨境传输/托管地点；每种通常对应不同合同权利，不能以“内部 API”替代。
6. **合同与合规成本**：KRX 最终用户/信息使用合同、Koscom 平台/数据许可、审计/报表（用户数、usage report）、商标/归属声明、保密、税费（VAT/跨境预提或反向收费）、汇兑和年度涨价/最低承诺。上述具体金额和适用性均须由报价/合同确认。

> **重要边界：** 上表是为取得完整报价而列的合同维度，不把每一维都断言为已公布的单独收费项。公开资料可确认“按许可/产品构成”而非可自助购买的 K1 固定单价；精确计费基数须以 Koscom/KRX 的书面答复为准。

## 3. PRC 法人和减免/创业支持

- Koscom Open API 的公开“使用对象及费用说明”以**法人**为使用主体（不面向个人/学生）；公开页未给出可核验的“中国注册法人可直接签约”条款、PRC 数据落地/展示许可或制裁/出口管制结论。[使用对象及费用说明](https://koscom.gitbook.io/open-api/how-to-use/procedure/charge) 因而 PRC 法人不是公开资料中已确认的合格类别，也不是已确认被拒绝的类别：**资格未知，必须先做 vendor legal/compliance pre-clearance。**
- Koscom 的公开平台说明中有一项创业支持：对**成立未满 7 年的中小企业**提供 **36 个月平台使用费减免**（公开页面/FAQ 的表述）。[Koscom Open API FAQ](https://koscom.gitbook.io/open-api/faq/oppf) 该项最多可说明“平台使用费”可能减免；**没有公开证据表明它豁免 KRX 的 K1 实时市价许可、外部展示、non-display、再分发、网络接入或税费。**
- 对 PRC 法人尤其不能自行套用该计划：公开资料没有说明韩国《中小企业》认定是否接受境外注册主体、7 年起算日、控制/关联企业规则、36 个月从注册还是首个生产密钥起算，或是否必须韩国境内实体。要求 Koscom 书面确认资格和“被豁免的精确费用行”。

## 4. 二手资料与预算处理

只保留了有日期、可追溯的二手背景资料：**2020-01-15** Koscom 新闻稿及多家报道说明其以 Open API 支持金融科技/创新金融服务，但不含 K1 实时许可的可验证金额。[Koscom 新闻稿（2020-01-15）](https://www.koscom.co.kr/portal/bbs/B0000064/view.do?nttId=29398&menuNo=200629)；[联播稿，Yonhap（2020-01-15）](https://www.yna.co.kr/view/AKR20200115085200008)。

**没有找到可作为预算数字的可靠二手价格。** 搜索中出现的论坛、博客、聚合商或未附供应商费表的“每用户/每月”说法均未纳入；也不应把交易手续费、Trade Repository 费用、第三方终端订阅费或 KRX 历史数据价格混入本项目。故本简报不提供虚假的 KRW 区间。若内部必须预留预算，应把它列作“供应商待报价/高不确定性”采购项目，而非把未经验证报价当作事实。

## 5. 可直接发出的报价请求清单（中/英要点）

向 **Koscom 市场数据团队（公开资料指向 `fintechdata@koscom.co.kr`）** 及必要时 KRX 同时发送；要求回复包含生效日期、币种、税前/税后、最短合同期、每项计费单位及所有一次性费用。[KRX 实时产品资料](https://data.krx.co.kr/inc/datasale/Market%20Data%20Product%20Brochure.pdf?v=20250732)

1. **主体与地域**：PRC 注册全称、统一社会信用代码、注册地址、最终控制方、是否有韩国子公司；数据处理/云区在何地，用户/客户在哪些国家（明确 PRC）。请确认可否直接签约、是否需韩国实体/本地代理、KYC/制裁/跨境数据条件。
2. **精确产品**：`KOSPI Composite index K1`, **real-time**, 所需字段、毫秒/秒级、快照或 streaming；确认仅 K1 是否可单独订购，及是否被强制捆绑 KOSPI 股票/其他市场数据。
3. **交付与环境**：Koscom Open API 与 direct/institutional feed 分别报价；开发、UAT/sandbox、production 各自的数据时效（真实/延迟/模拟）、免费额度、期限、限流、上线/迁移和支持 SLA。
4. **三套必分开报价的 use case**： (a) 内部 display（员工/屏幕数量）；(b) non-display 自动研究、实时信号、风控、自动交易、缓存及派生数据；(c) 外部网页/App display、B2B API/feed、每月活跃用户/客户数和再分发。请就每套写明允许/禁止事项和 KRX 合同名称。
5. **全部费用表**：市场数据许可、API/平台、feed/接入/网络、initial setup、monthly minimum、终端/用户/服务器/application/调用量/客户/区域阶梯、审计/报表、support、续约/上调、提前终止、税和货币；注明是否可抵扣。
6. **权利与限制**：PRC 分发、关联公司共享、云托管、缓存时限、数据留存、派生指标/指数、展示须署名、再分发审批；要求 KRX/Koscom 对 K1 逐项书面确认，而非泛称 “market data”。
7. **减免**：附成立日期和公司规模证明；询问“7 年内中小企业 36 个月减免”是否适用 PRC 法人、何日起算、豁免哪些明确行项目，以及 KRX 实时 K1 许可是否仍收费。
8. **文件**：索取现行 price schedule、产品说明、最终用户/供应商/non-display/redistribution 协议模板、审计与 usage reporting 规则、近一次价格生效/调整通知。

## 6. 资料来源（保留与排除）

### 保留（一手）

- [Koscom Open API：V3 市价服务（按许可）](https://koscom.gitbook.io/open-api/api/marketv3) — 直接确认实时 KOSPI 指数 K1 端点及“按许可”性质。
- [Koscom Open API：使用对象及费用说明](https://koscom.gitbook.io/open-api/how-to-use/procedure/charge) — 法人/费用及平台资格的直接入口。
- [Koscom Open API：API 测试流程](https://koscom.gitbook.io/open-api/how-to-use/devcenter) — 仅证明存在测试流程，不能推定实时 sandbox 免费。
- [KRX：《信息利用政策》](https://data.krx.co.kr/inc/datasale/Market%20Data%20Usage%20Polices_ko.pdf?v=20250732) — KRX 的市场信息许可政策一手文件。
- [KRX：《实时市场信息产品及服务构成》](https://data.krx.co.kr/inc/datasale/Market%20Data%20Product%20Brochure.pdf?v=20250732) — 实时产品、交付和使用场景的官方组成资料；公开入口未见 K1 数字价目。
- [Koscom 市场数据服务（英文）](https://www.koscom.co.kr/eng/main/contents.do?menuNo=300126) — Koscom 的市场数据服务一手介绍。

### 仅作背景（非约束性、无价格）

- [Koscom 新闻稿，2020-01-15](https://www.koscom.co.kr/portal/bbs/B0000064/view.do?nttId=29398&menuNo=200629)；[Yonhap，2020-01-15](https://www.yna.co.kr/view/AKR20200115085200008) — 说明创业/创新金融支持的历史背景；不构成现价或资格证明。

### 排除

- 博客、论坛、数据聚合商、搜索摘要中无原始供应商费表的“报价” — 日期、产品范围、许可权利或来源不可核验。
- KRX Trade Repository、股票交易手续费、券商终端和历史/收盘数据产品 — 不是 K1 实时市场数据许可，不能类比。

## 7. 未决缺口与下一步

1. 公开资料不足以验证**当前**金额、K1 是否有单独 SKU、最小承诺、PRC 直签资格及跨境分发范围；这些是签约前阻断项。
2. 36 个月创业减免的当前有效性、适用地域和覆盖费用范围，需 Koscom 以书面报价/合同确认。
3. 本次环境对 Koscom/KRX 部分 PDF/页面的直接抓取受到站点网络地址限制；已保留官方原始链接，但不能将页面不可访问误解为“存在或不存在非公开客户费表”。

**建议下一步：** 用第 5 节清单要求 Koscom 在同一封回复中对 API、机构 feed、内部 display、non-display、外部分发和 sandbox 分列正式报价；未经该答复，不作采购金额或 PRC 可售承诺。
