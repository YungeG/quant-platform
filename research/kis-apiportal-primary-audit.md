# KIS Developers（apiportal.koreainvestment.com）一手资料更正审计

> 归档说明（2026-09-22，非重新检索日期）：下文保留原调研记录；产品、资费、准入、接口和许可条件未在本次联网复核，未注明日期的断言不能当作现行报价或已获权限。URL 仅作原始来源定位，实际采购或接入前须重新核对一手条款并取得相应批准。本次只归档，不发送询价、不开户、不采集数据，也不授予交易或再分发权。

---

> 审计范围：仅把 KIS Developers 门户/API 指南当作规范依据；未把第三方 SDK、博客或 wrapper 当作功能证明。核查日：2026-08-24。门户的 API 明细是动态页面；下列 URL 是其直接、可复核的详情路由，页面外壳标题均为 **“KIS Developers : 한국투자증권 오픈API 개발자센터”**，并在条目中标出门户所显示的功能标题。

## 结论（修正）

1. **Testbed 不是 VTS（虚拟交易）环境。** Testbed 是已申请 API 的 REST 调用界面；页面明确说「实시간시세는 테스트베드 기능을 제공하지 않습니다. (REST 방식만 가능)」（实时行情不提供 Testbed 功能，仅 REST）。因此不能以 Testbed 能否调用来推断 VTS 能力，更不能用它测试 WebSocket。
2. **生产 KOSPI Composite 可用 REST 与实时 WS：** REST「国内业种当前指数」为 `GET /uapi/domestic-stock/v1/quotations/inquire-index-price`，`tr_id=FHPUP02100000`；KOSPI Composite 输入 `FID_COND_MRKT_DIV_CODE=U`、`FID_INPUT_ISCD=0001`。WS「国内指数实时成交」订阅 `tr_id=H0UPCNT0`、`tr_key=0001`。
3. **VTS 已明确不支持 KOSPI 指数接口：** 门户的两个指数 API 明细均将“模拟 Domain”和“模拟 TR ID”标为 **`모의투자 미지원`**（不支持模拟交易）：包括 REST `FHPUP02100000/U/0001` 与 WebSocket `H0UPCNT0/0001`。因此虚拟 KOSPI REST 查询与实时流均不能作为方案；VTS 对其他下单/账户或股票接口的支持不能外推到指数接口。

## 1. Testbed 与 VTS 的边界

| 项目 | 门户证据 | 审计结论 |
| --- | --- | --- |
| Testbed | [“API 테스트”](https://apiportal.koreainvestment.com/testbed)（页面标题：**KIS Developers : 한국투자증권 오픈API 개발자센터**）称“API 호출 테스트”；并明确“实时行情不提供 Testbed 功能（仅 REST）”，且警告请求会实际受理。 | 是门户 REST 调用测试 UI；不是模拟交易服务器，也不测试 WS。 |
| VTS / 模拟交易 | [“API 가이드 문서”](https://apiportal.koreainvestment.com/apiservice-apiservice)（同上标题）每个 API 的信息栏分别提供“实战 Domain / 模拟 Domain、实战 TR ID / 模拟 TR ID”字段。 | 是独立的虚拟交易 API 环境；是否支持某一 API 必须看该 API 自己的“模拟”列。 |

## 2. KOSPI Composite：生产端已文件化的接口

| 方式 | 门户功能标题与直接 URL | 精确值 |
| --- | --- | --- |
| REST | [“국내업종 현재지수 [국내주식-063]”（API guide detail）](https://apiportal.koreainvestment.com/apiservice-apiservice?%2Fuapi%2Fdomestic-stock%2Fv1%2Fquotations%2Finquire-index-price=)；页面标题：**KIS Developers : 한국투자증권 오픈API 개발자센터** | `GET /uapi/domestic-stock/v1/quotations/inquire-index-price`; `tr_id: FHPUP02100000`; `FID_COND_MRKT_DIV_CODE=U`; `FID_INPUT_ISCD=0001`（KOSPI Composite）。 |
| WebSocket | [“국내지수 실시간체결”（API guide detail）](https://apiportal.koreainvestment.com/apiservice-apiservice?%2Ftryitout%2FH0UPCNT0=)；页面标题：**KIS Developers : 한국투자증권 오픈API 개발자센터** | 先取 approval key，连接生产 WS 后订阅 `tr_id: H0UPCNT0`、`tr_key: 0001`。 |
| WS approval | [“WEBSOCKET실시간 (웹소켓) 접속키 발급[실시간-000]”](https://apiportal.koreainvestment.com/apiservice-apiservice?%2Foauth2%2FApproval=) | `POST /oauth2/Approval`，以 App Key/App Secret 取得 `approval_key`；它不同于 REST access token。 |

**重要限定。** 门户已在这两个指数明细的“模拟 Domain / 模拟 TR ID”栏明确写为 `모의투자 미지원`，所以 VTS 不能用于验证或承载 KOSPI Composite REST/WS；生产端认证与权限仍须另行取得。

## 3. 基址、认证与适用前提

| 环境 | REST 基址 | WebSocket 基址 | 凭据/认证 | 文档状态 |
| --- | --- | --- | --- | --- |
| 生产 | `https://openapi.koreainvestment.com:9443` | `ws://ops.koreainvestment.com:21000` | 账户申请服务后取得 production App Key/App Secret；REST 使用 `/oauth2/tokenP` 取得 bearer access token；WS 使用 `/oauth2/Approval` 取得 approval key。 | 门户的 [“한국투자증권 Open API”（REST/WS 方式说明）](https://apiportal.koreainvestment.com/intro)（页面标题：**KIS Developers : 한국투자증권 오픈API 개발자센터**）说明 REST 以“账户的 Appkey/App secret”换 token，WS 先发接入 key；API 详情表给出 production 栏。 |
| VTS / 模拟 | `https://openapivts.koreainvestment.com:29443` | `ws://ops.koreainvestment.com:31000` | 须使用门户为模拟环境发放/显示的 VTS App Key/App Secret；REST/WS 的 token/approval 流程同类但密钥和基址不可混用。 | 基址由门户链接的 KIS 官方样例配置 [“kis_devlp.yaml”](https://github.com/koreainvestment/open-trading-api/blob/main/kis_devlp.yaml)给出（第一方 KIS GitHub，非第三方 wrapper）。**这只证明环境端点存在，不证明 `FHPUP02100000` 或 `H0UPCNT0` 在 VTS 支持。** |

### 账户、资格、境外与第三方数据使用

* **账户/API 申请：** 门户 REST 说明明确把 App Key/App Secret称为“账户的”凭据；申请入口亦是 [“API신청”](https://securities.koreainvestment.com/main/customer/systemdown/RestAPIService.jsp)。因此生产使用应视为需要韩国投资证券账户及完成 API 服务申请，而不是无账户公共行情 API。
* **第三方向客户提供服务：** [“제휴안내”（Provider information）](https://apiportal.koreainvestment.com/provider-info)（页面标题：**KIS Developers : 한국투자증권 오픈API 개발자센터**）规定：为向第三方提供服务的法人须先判断/办理合作；仅法人自有账户、非向第三方提供服务可不合作。面向客户的订单还取决于受监管金融机构/投顾或全权委托资格。该页还明确：若合作机构要在其品牌 App 展示 KRX 或海外交易所行情，须先与 KRX/相应交易所签订信息使用合同；没有合同不得展示，相关争议由合作机构负责。
* **数据用途限制：** [“제휴사 API 시작하기”（Partner API start）](https://apiportal.koreainvestment.com/provider-doc1)（页面标题：**KIS Developers : 한국투자증권 오픈API 개발자센터**）称行情等信息仅允许在面向韩国投资证券交易客户的 Open API 服务中使用，不得用于其他目的，违规可能导致罚款。故“拉取后转售/给非客户的第三方数据服务”不可假定获准。
* **非居民/境外：** 本轮门户一手检索**未找到**针对 non-resident、overseas resident 或 foreign individual 的 Open API 可开户/可申请资格声明。不能据此说“非居民可以”或“不可以”；应以 KIS 开户/合规部门的书面答复为准。合作 API 文档里出现 `overseas_yn` 只表示海外股票申请参数，**不**是非居民资格证明。

## 4. 门户明确披露的限制

1. **Testbed：仅 REST，不提供实时行情/WS testbed。** 见 [“API 테스트”](https://apiportal.koreainvestment.com/testbed)。
2. **新客户 TPS：** 门户首页/使用页列有公告 **“[중요] 한국투자증권 Open API 신규 고객 초당 호출 제한 안내”（2026-03-20）**，见 [“한국투자증권 Open API”](https://apiportal.koreainvestment.com/howto-use)。本次公开抓取到公告标题但未取得公告正文的数值/适用 API，故**不编造每秒数**；实现必须以该公告全文或登录后当前限额为准。
3. **凭据生命周期（合作模式）：** [“제휴사 API 시작하기”](https://apiportal.koreainvestment.com/provider-doc1)写明 authorization code 5 分钟、access token `7,776,000` 秒（90 天）；refresh token 在投顾/全权委托合同期内有效。该项是合作认证限制，不能自动套用于个人/VTS token。
4. **WS/REST 配额：** 在本次可公开取得的门户页面中，未发现可引用的 `H0UPCNT0` 专属 VTS 配额、KOSPI 订阅数、或一般 WS 并发/订阅上限。不得用非门户传言（如“40 个品种”）冒充官方现行限制。

## 5. 实施判定

* **可做（有生产申请/资格且符合数据许可时）：** 生产 REST `FHPUP02100000/U/0001`；生产 WS `H0UPCNT0/0001`。
* **明确不支持：** VTS KOSPI Composite REST `FHPUP02100000/U/0001`，以及 VTS WebSocket `H0UPCNT0/0001`；门户均标注 `모의투자 미지원`。
* **下一步最小验证：** 将指数流视为 production-only。模拟环境仅验证与其明确支持的接口；KOSPI 适配器用录制数据/合成事件做集成测试，再以生产凭据做受控验收。

## 来源处置

### 保留（第一方）

* **KIS Developers : 한국투자증권 오픈API 개발자센터 — API 테스트**：<https://apiportal.koreainvestment.com/testbed> — 明确 Testbed 为 REST-only、无实时行情测试。
* **KIS Developers : 한국투자증권 오픈API 개발자센터 — API 가이드 문서**：<https://apiportal.koreainvestment.com/apiservice-apiservice> — 明确每项 API 有实战/模拟基址及 TR 分栏。
* **KIS Developers : 한국투자증권 오픈API 개발자센터 — 국내업종 현재지수 [국내주식-063]**：<https://apiportal.koreainvestment.com/apiservice-apiservice?%2Fuapi%2Fdomestic-stock%2Fv1%2Fquotations%2Finquire-index-price=> — REST path/TR/输入代码的规范路由。
* **KIS Developers : 한국투자증권 오픈API 개발자센터 — 국내지수 실시간체결**：<https://apiportal.koreainvestment.com/apiservice-apiservice?%2Ftryitout%2FH0UPCNT0=> — WS `H0UPCNT0` 的规范路由。
* **KIS Developers : 한국투자증권 오픈API 개발자센터 — WEBSOCKET실시간 (웹소켓) 접속키 발급[실시간-000]**：<https://apiportal.koreainvestment.com/apiservice-apiservice?%2Foauth2%2FApproval=> — approval-key 认证。
* **KIS Developers : 한국투자증권 오픈API 개발자센터 — 제휴안내 / 제휴사 API 시작하기**：<https://apiportal.koreainvestment.com/provider-info> 、<https://apiportal.koreainvestment.com/provider-doc1> — 第三方、行情许可、token 限制。
* **KIS 官方 GitHub — kis_devlp.yaml**：<https://github.com/koreainvestment/open-trading-api/blob/main/kis_devlp.yaml> — 仅用于交叉核对两套 endpoint，因由门户直接链接，仍属第一方；不用于功能支持结论。

### 排除

* 第三方 wrappers/SDK、博客、论坛与搜索摘要：不具备证明 KIS 当前 VTS 支持矩阵、额度、合规资格的权威性。

## 残余风险

* 门户 API 明细动态加载，但其公开详情 JSON 已明确把两个 KOSPI 指数接口标为 `모의투자 미지원`。
* 新客户 TPS 公告正文数值未公开抓到；不要在限流器中写死外部文章的数值。
* 非居民可否开户/API 申请在门户未见明确政策；在 KIS 书面确认前视为未知。
