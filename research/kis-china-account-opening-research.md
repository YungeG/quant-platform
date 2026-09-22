# Research: KIS—中国大陆个人开立账户及 Open API（官方资料核查）

> 归档说明（2026-09-22，非重新检索日期）：下文保留原调研记录；产品、资费、准入、接口和许可条件未在本次联网复核，未注明日期的断言不能当作现行报价或已获权限。URL 仅作原始来源定位，实际采购或接入前须重新核对一手条款并取得相应批准。本次只归档，不发送询价、不开户、不采集数据，也不授予交易或再分发权。

---

> 结论基于本次检索到的 KIS 英文/韩文官网、KIS Developers 及韩国金融委员会（FSC）一手页面。仅把官网明确写出的内容视为已证实；不把“外国人可投资”推断成“可在中国大陆远程开户”。

## Summary

**不能据现有官方资料认定中国大陆的非居民个人可以远程开立 KIS 券商账户。** KIS 明确排除外国人使用智能手机开户，且其合作银行/上门 BanKIS 路线均限韩国境内居住的韩国国民；非居民个人的官方入口是联系 KIS 的 Global Investment Sales Department，由其确认个案开户，而不是一个公布的跨境线上开户流程。[KIS English](https://securities.koreainvestment.com/eng/guide/stock01.shtm) [KIS 手机开户](https://securities.koreainvestment.com/main/customer/guide/_static/TF04aa090000.jsp)

可投资韩国上市证券、能否被 KIS 接纳为经纪客户、以及能否申请生产 Open API/实时数据是三件不同的事：前者原则上可行；后两者均不能由前者推出，须由 KIS 确认。

## Findings

1. **(a) 投资韩国证券的监管资格：原则上可以，但有证券层面的限制。** KIS 英文指南称非韩国居民可投资韩国股票和债券（部分上市股票有少数限制）。FSC 已自 **2023-12-14** 废除外国投资者事前登记；个人以护照号码作为识别手段即可投资韩国上市证券。该改革取消的是监管事前登记，**不是**要求任何一家券商接受客户或提供远程 KYC。[KIS English](https://securities.koreainvestment.com/eng/guide/stock01.shtm) [FSC, 2023-12-14 measures](https://www.fsc.go.kr/eng/pr010101/81237) [FSC, 2024 status](https://www.fsc.go.kr/eng/pr010101/82511)

2. **(b) KIS 券商账户：没有发现面向中国大陆非居民外国人的官方远程开户路径；已公布的线上/替代路径反而排除该人群。** KIS 手机开户页面明确写明“外国人不可智能手机开户”；远程 KYC 所列材料是韩国居民身份证/驾驶证及本人名下手机。合作银行账户的目标客户是“韩国国内居住的韩国国民个人”，排除外国人、在外侨民等。所谓 BanKIS Direct 上门开户同样仅限韩国境内居住的韩国国民，且只在部分区域提供；不能作为在中国大陆开户方案。[手机开户](https://securities.koreainvestment.com/main/customer/guide/_static/TF04aa090000.jsp) [合作银行开户](https://securities.koreainvestment.com/main/customer/guide/_static/TF04aa020000.jsp) [BanKIS Direct](https://securities.koreainvestment.com/main/customer/guide/BankisDirect.jsp)

3. **非居民个人的 KIS 官方开户入口及已公布要求：联系 Global Investment Sales Department；未公布可从中国邮寄/视频完成开户。** KIS 英文页专门要求有意投资韩国股票的非居民个人联系 **Global Investment Sales Department**（机构则联系 International Business Department）。KIS 的线下营业网点开户页明确要求携带：实名确认文件、交易印鉴或签名、以及金融交易目的证明，并到附近 KIS 营业网点；要做网上交易还须申请 Internet Banking/HTS 约定。该页没有针对“中国大陆非居民个人”逐项列出护照公证、地址证明、税务表、韩国内账户、翻译/认证或代理授权的完整清单，故这些不能臆测为已公开的固定要求。[非居民入口](https://securities.koreainvestment.com/eng/guide/stock01.shtm) [营业网点开户](https://securities.koreainvestment.com/main/customer/guide/_static/TF04aa010000.shtm)

4. **地点要求：公开资料支持“到韩国 KIS 营业网点”的线下路线，不支持在中国大陆完成。** 营业网点页要求访问“附近的 KIS 营业网点”；其有限地区的员工上门服务不适用于外国人/非居民。KIS 公开的客户中心页列有外国人电话 **1588-1251**、海外来电 **+82-2-2090-4000**；这可作为先确认渠道，但页面并未承诺该电话可完成开户或专门负责 Global Investment Sales。[营业网点开户](https://securities.koreainvestment.com/main/customer/guide/_static/TF04aa010000.shtm) [KIS 客户中心](https://securities.koreainvestment.com/main/customer/guide/branch/_view/branch_eng_center.jsp)

5. **(c) KIS Developers/Open API：生产服务的公开前提是已有 KIS 账户及 KIS ID，而非仅有护照或外国投资资格。** KIS 的官方 `koreainvestment/open-trading-api` 指南列出的顺序为：开立并连接 KIS 账户和 ID → 在 KIS 网站或 App 申请 Open API 服务 → 获得 App Key/App Secret；KIS Developers 也把个人客户定义为用本人资产自行交易者，并指向 KIS 主页申请服务。因此，若 KIS 不接受该非居民账户或无法完成 ID/认证，便无法由公开流程取得个人生产 API。KIS Developers 中没有找到明确允许/拒绝“中国大陆居住外国人”申请个人 API 的规则，故**不能承诺可申请**。[官方 GitHub 指南](https://github.com/koreainvestment/open-trading-api/blob/main/README.md) [KIS Developers—个人服务申请](https://apiportal.koreainvestment.com/provider-info) [KIS Developers—服务介绍](https://apiportal.koreainvestment.com/intro)

6. **实时行情：文档显示生产 WebSocket 可接收实时数据，但不等于该申请人已获准。** KIS Developers 将国内/海外股票等“实时市价”列为 API 类别，并说明服务申请完成后可取得接入键、以 WebSocket 收取实时数据；测试床明确不提供实时市价功能。个人公开指引没有找到针对外国非居民的实时行情地域资格、费用或额外交易所合约条件。页面中“与 KRX/海外交易所签订信息使用合同”的要求是写给**合作机构/法人向其应用用户提供数据**的规则，不能擅自套用到个人自用账户。[API 类别](https://apiportal.koreainvestment.com/apiservice) [实时 WebSocket 说明](https://apiportal.koreainvestment.com/intro) [测试床限制](https://apiportal.koreainvestment.com/testbed) [合作机构行情规则](https://apiportal.koreainvestment.com/provider-info)

## 必须直接向 KIS 确认

- 持中国护照、税务及常住地均在中国大陆的**非居民个人**是否可被 Global Investment Sales 接纳，以及是否必须亲赴哪一家韩国营业网点；是否存在 KIS 书面批准的领事认证/邮寄/视频 KYC 例外。
- 针对此身份的完整文件、有效期及认证/韩文翻译要求：护照、住址/税务居住地、资金来源与交易目的证明、FATCA/CRS、自身名义结算/入金路径、印鉴/签名及代理安排。
- 是否可获 Internet Banking/HTS、KIS ID、所需认证书及短信/手机号验证；这直接决定个人 Open API 申请能否完成。
- 开户后，生产 App Key/Secret、韩国/海外品种交易权限，以及个人自用实时 WebSocket 行情是否可开通、是否收费、是否因居住地/数据再分发而受限。不要用测试床结果替代此确认。

## Sources

- Kept: [KIS English—Korean Stocks](https://securities.koreainvestment.com/eng/guide/stock01.shtm) — KIS 对非居民个人的明确联系部门及市场可投资表述。
- Kept: [KIS—Smartphone account opening](https://securities.koreainvestment.com/main/customer/guide/_static/TF04aa090000.jsp) — 明确排除外国人手机开户。
- Kept: [KIS—Branch account opening](https://securities.koreainvestment.com/main/customer/guide/_static/TF04aa010000.shtm) — 线下地点、已公布文件类别及 HTS 约定。
- Kept: [KIS—Partner-bank account opening](https://securities.koreainvestment.com/main/customer/guide/_static/TF04aa020000.jsp) and [BanKIS Direct](https://securities.koreainvestment.com/main/customer/guide/BankisDirect.jsp) — 两个看似替代渠道的资格排除。
- Kept: [KIS customer center](https://securities.koreainvestment.com/main/customer/guide/branch/_view/branch_eng_center.jsp) — 已公布外国人/海外电话。
- Kept: [FSC—measures effective 2023-12-14](https://www.fsc.go.kr/eng/pr010101/81237) and [FSC—2024 implementation status](https://www.fsc.go.kr/eng/pr010101/82511) — 外国人投资者登记废除与护照识别。
- Kept: [KIS Developers](https://apiportal.koreainvestment.com/intro), [service categories](https://apiportal.koreainvestment.com/apiservice), [testbed](https://apiportal.koreainvestment.com/testbed), and [official guide](https://github.com/koreainvestment/open-trading-api/blob/main/README.md) — API 账户/ID 前提及实时数据的范围。
- Dropped: 媒体、博客、第三方 SDK 和通用“外国人可投资”页面 — 不是 KIS 具体开户或个人 API 资格的一手证据。

## Gaps

KIS 官网没有公开检索到非居民个人（尤其中国大陆税务居民）的完整开户文件矩阵、是否接受跨境远程 KYC、或个人生产 API/实时行情的国籍和居住地限制。以上是决定性缺口，应通过上述 KIS 官方渠道取得书面答复后再安排赴韩、资金汇出或开发。
