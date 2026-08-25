# A 股 Quality + B-Band 财务与治理一手来源矩阵

- **研究目标**：判断第一方/主管机关来源能否支持 `cn-a-share.quality-bband-breakout.manual4.v1` 的财务、审计、治理、质押、上市状态与估值数据契约。
- **审阅基线**：`research/quality-bband-data-authority-audit.md`、`implementation/plans/quality-bband-data-contract-v1.md`、`implementation/plans/quality-bband-implementation-readiness-v1.md`。
- **判定口径**：`AVAILABLE` 表示来源本身足以建立有限区间的事件时间、可用时间、修订链和终止集；`SOURCE_BOUNDED_ONLY` 表示可保存“本次查询/本份公文确实返回了什么”，但不能声称全市场完整、永久无后续更正；`MISSING` 表示连所需字段或可验证时间语义都不能提供。当前页面、搜索无结果、可变供应商比率、非官方抓取及本地 DuckDB 均不作为权威。

## 摘要

结论是：**目前没有任何单一第一方或主管机关公开接口能令完整财务治理契约达到 `AVAILABLE`**。Tushare 官方接口最接近可实施的有限源切片：三张原始报表具有公告日期、实际公告日期、报告类型及调整前/调整后类型，审计和质押也有专门接口；但它没有不可变版本号、抓取时刻之前的发布修订日志、全局终止集或分钟级可用时间，因此只能是 `SOURCE_BOUNDED_ONLY`。[利润表](https://tushare.pro/document/2?doc_id=33) [资产负债表](https://tushare.pro/document/2?doc_id=36) [现金流量表](https://tushare.pro/document/2?doc_id=44)

巨潮、上交所、深交所、证监会和中国结算提供更强的原始法律/披露事实，但公开网页和公文目录缺少已公开、稳定、可分页穷举且带修订终止语义的数据接口文档。它们适合为已知公告、公文或名单建立不可变证据成员，不能用“搜索不到”证明无事件。

## 来源能力矩阵

| 必需字段组 | 来源所有者；精确接口/文档 | 查询键；返回字段 | 事件/生效时间；公开/可用时间 | 修订、更正、取代 | 行/页限制；认证 | 有限历史捕获与 Backtest 判定 |
| --- | --- | --- | --- | --- | --- | --- |
| **利润表：营业利润/EBIT、所得税、收入、净利润、EBITDA** | Tushare 官方 `income` / `income_vip`。[接口文档](https://tushare.pro/document/2?doc_id=33) | `ts_code` 必填；可按 `ann_date`、`f_ann_date`、公告日起止、`period`、`report_type`、`comp_type`。返回 `ann_date`、`f_ann_date`、`end_date`、`report_type`、`comp_type`、`operate_profit`、`total_profit`、`income_tax`、`n_income`、`n_income_attr_p`、`ebit`、`ebitda`、`revenue`、`update_flag` 等。 | 经济事件期为 `end_date`；披露日为 `ann_date`/`f_ann_date`，均仅到日。官方权限页称“全部历史，实时更新”，但未给每一行首次公开时刻或历史入库时刻。[权限表](https://tushare.pro/document/2?doc_id=109) | `report_type=4` 调整合并、`5` 调整前合并可保留部分变更前后数据；`update_flag` 仅标识更新状态。没有稳定 revision id、parent/supersedes、删除记录或“截至某时已终结”的声明。 | 普通接口至少 2000 积分且单股票；全市场季度 `income_vip` 需 5000 积分。文档未声明普通/VIP 单次行上限。HTTP 需 token，token 只能环境注入。[HTTP 文档](https://tushare.pro/document/2?doc_id=130) | 可按股票和公告日切片、保存原始响应与收据；**`SOURCE_BOUNDED_ONLY`**。日粒度可用时间、修订闭包和全市场覆盖仍阻止 `AVAILABLE`。 |
| **资产负债表：权益、现金、带息债务、固定资产、营运资本输入** | Tushare 官方 `balancesheet` / `balancesheet_vip`。[接口文档](https://tushare.pro/document/2?doc_id=36) | 同上；返回 `money_cap`、`total_cur_assets`、`fix_assets`、`cip`、`total_assets`、`st_borr`、`non_cur_liab_due_1y`、`bond_payable`、`lt_borr`、`total_liab`、`total_hldr_eqy_exc_min_int`、单位隐含为接口字段定义、`report_type`、`update_flag` 等。 | `end_date` 是报表日；`ann_date`/`f_ann_date` 是日粒度披露日。没有首次可查询的精确时刻。 | 报表类型 4/5 及 9/10/11/12能表达部分调整前后版本，但没有显式谱系、删除/撤回或终止集。 | 2000 积分；全市场季度 VIP 5000 积分；普通接口单股票。单次行上限未公开。 | 能有限抓取原始组成项，足以避免把供应商 `netdebt` 比率当原始事实；**`SOURCE_BOUNDED_ONLY`**。负债口径映射仍须 Feature Manifest 冻结。 |
| **现金流量表：经营现金流、资本开支、自由现金流输入** | Tushare 官方 `cashflow` / `cashflow_vip`。[接口文档](https://tushare.pro/document/2?doc_id=44) | 同利润表；关键返回 `n_cashflow_act`、`c_pay_acq_const_fiolta`、`n_cashflow_inv_act`、`c_cash_equ_end_period`、`free_cashflow`、`report_type`、`update_flag`。 | `end_date` 为报告期；`ann_date`/`f_ann_date` 为日粒度可用代理。 | 同样支持报表类型 4/5 等保留部分调整前数据；无完整 revision/supersedes 链。供应商 `free_cashflow` 不应直接成为策略权威，应由原始经营现金流和资本开支按冻结公式计算。 | 2000/5000 积分；普通单股票，VIP 全市场季度；行上限未声明。 | 原始字段有限捕获可行；**`SOURCE_BOUNDED_ONLY`**。 |
| **财务报表原件、公告时点和正式更正/重述** | 发行人提交，交易所/符合条件媒体发布；巨潮静态公告 PDF 是具体公告原件。深交所业务指南明确直通披露提交和发送至符合条件媒体的时段，并说明媒体确认发布后公告不得修改或撤销。[深交所业务指南](https://wltp.cninfo.com.cn/static/finalpage/2025-04-25/1223718360.pdf) 巨潮公开站提供公告入口及深证信数据服务/API 文档入口。[巨潮公告入口](https://www.cninfo.com.cn/new/commonUrl?url=disclosure%2Flist%2Fnotice) [CNINFO Data Service](https://webapi.cninfo.com.cn/) | 公开网页可按证券、类别、日期检索并指向静态 PDF；但本次未找到公开、稳定的官方 API 规范，无法可靠声明具体 query keys、返回 schema、分页上限和授权等级。商业数据服务页面列有“API 文档”，具体接口契约需登录/商务确认。 | 公告自身报告期/决议日为事件时间；网站展示公告日期或时间，深交所指南给出不同提交时段的媒体发送时点。要用于回测，必须保存公告列表元数据中的实际发布时间，而不能仅用 PDF 文件日期。 | 更正公告和更正后报告以新的独立公告发布；主管规则要求年度财报更正时披露更正后财报，并在广泛影响或盈亏性质改变时重新审计，不能及时完成时先发提示公告并在两个月内完成。[证监会第 19 号规则的实际披露示例](https://static.cninfo.com.cn/finalpage/2026-04-22/1225138999.PDF) 但公开目录没有机器可验证的 `supersedes` 字段，需根据公告编号、标题、被更正期间和正文构建谱系。 | 公告网页通常无需认证；商业 API 的授权、限流和历史包权限未在公开页明确。网页分页不是合格接口契约。 | 对**已知、枚举并固化的公告集合**可有限捕获；全市场终止集和“无更正”不能由搜索缺失证明。**`SOURCE_BOUNDED_ONLY`**。若要 `AVAILABLE`，需取得 CNINFO/交易所正式数据许可、稳定 API schema、分页闭包和更正关系规则。 |
| **五年 ROIC/ROCE、FCF、净债务/EBITDA** | 无第一方直接比率应成为策略权威。候选原始来源为上述三张 Tushare 报表并以巨潮/交易所公告原件校验。Tushare `fina_indicator` 虽返回 `roic`、`fcff`、`netdebt`、`interestdebt`、`ebitda` 等，但属于可变供应商计算值。[接口文档](https://tushare.pro/document/2?doc_id=79) | `fina_indicator` 按 `ts_code`、`ann_date`、报告期范围和 `period` 查询，单次最多 100 条；返回比率与派生量及 `update_flag`。 | 只有报告期和公告日，没有精确首次可用时间，也没有公式版本/分子分母引用。 | 无公式版本和修订谱系。 | 2000 积分；VIP 5000；普通单股票、100 行。 | 原始报表足以支持未来冻结公式；**原始组成项 `SOURCE_BOUNDED_ONLY`，供应商比率作为权威为 `MISSING`**。精确 ROIC/ROCE、FCF、净债务/EBITDA 公式、行业差异、缺失项失败规则仍是契约 blocker。 |
| **审计意见** | Tushare 官方 `fina_audit`；最终原件为发行人年度报告及审计报告公告。[接口文档](https://tushare.pro/document/2?doc_id=80) | `ts_code` 必填；`ann_date`、公告日起止、`period`。返回 `ts_code`、`ann_date`、`end_date`、`audit_result`、`audit_fees`、`audit_agency`、`audit_sign`。 | 报告期为 `end_date`，公开日为日粒度 `ann_date`。没有审计报告 id、PDF hash、首次可用时刻。 | 接口没有 `update_flag`、修订号、被撤回/重发审计报告或 supersedes 字段。更正后的审计意见必须靠新公告原件识别。 | 至少 2000 积分；文档未声明单次行上限或 VIP 全市场接口。 | 可对单股票已返回记录做有限快照；**`SOURCE_BOUNDED_ONLY`**。全市场历史、审计报告身份和重发谱系未闭合。 |
| **监管处罚、欺诈发行、财务造假、市场禁入** | 中国证监会主动公开目录：行政处罚决定书类别 `c101928`、市场禁入类别 `c101927`；决定书含索引号、文号、违法事实、涉案报告期、处罚结论和救济说明。[行政处罚示例](http://www.csrc.gov.cn/csrc/c101928/c7500946/content.shtml) [市场禁入目录](https://www.csrc.gov.cn/csrc/c101927/zfxxgk_zdgk.shtml) 上交所、深交所另有监管措施/纪律处分目录。[上交所纪律处分](http://www.sse.com.cn/regulation/listing/disposition/) [深交所纪律处分](https://www.szse.cn/disclosure/supervision/measure/pushish/index.html) | 公开目录可按页面浏览/站内检索，单份文书返回发布机构、发文日期、名称、文号、事实和决定；本次未找到主管机关公开 API 的 query schema、页上限或全量导出规范。 | 违法发生期间、报告披露日、立案/听证/决定事实在正文中；回测可用时间应取主管机关决定书**公开发布时间**，不能回填为违法发生日。 | 新决定、复议/诉讼或交易所复核可能改变可依赖状态；网页没有统一 supersedes/撤销字段。CSRC 索引号和文号可作稳定文书 identity，但不能单独证明后续终局。 | 公开网页无需 token；分页上限和历史完整性 SLA 未公开。地方证监局、交易所、自律处分与中央证监会多目录并存。 | 对已知公文可不可变保存，事实权威很强；但无法从目录搜索缺失推出“无处罚/无造假”。**`SOURCE_BOUNDED_ONLY`**。完整治理排除条件仍缺跨机关 terminal-set declaration。 |
| **控股股东/实际控制人质押历史** | Tushare `pledge_detail` 和 `pledge_stat`；中国结算官方页明确股票质押式回购总量、单一证券质押数量、每周质押率应查看沪深交易所相关信息。[明细接口](https://tushare.pro/document/2?doc_id=111) [统计接口](https://tushare.pro/document/2?doc_id=110) [中国结算股票质押信息](http://www.chinaclear.cn/zdjs/gpzyshg/center_scsj_gpztxx.shtml) | `pledge_detail`：`ts_code`、`ann_date`、公告日起止；返回 `holder_name`、`pledge_amount`、`start_date`、`end_date`、`is_release`、`release_date`、`holding_amount`、`pledged_amount`、比例等。`pledge_stat`：`ts_code`、`end_date`；返回周度质押次数/数量/比例。 | 明细事件时间为质押开始、结束、解押日；可用时间为 `ann_date`（日粒度）。周度统计 `end_date` 是截止日，不是公告/可用时间。 | 没有质押事件唯一 id、修订号或 supersedes。`is_release` 是当前行状态，可能随供应商更新；需按抓取批次保留变化。接口也不直接标识“控股股东/实控人”，必须用同日有效的控制关系证据匹配 `holder_name`。 | 两接口单次最多 1000，至少 2000 积分；官方权限页称明细自 2004 年、统计自 2014 年，每晚 21 点更新。[权限表](https://tushare.pro/document/2?doc_id=109) 中国结算公开页主要链接交易所信息，无公开逐事件历史 API。 | Tushare 可按股票和公告日分页有限捕获；**`SOURCE_BOUNDED_ONLY`**。控制人身份时序、事件 id、解押修订链和公开终止集仍阻止策略所需“控股股东质押比例”权威。 |
| **上市、退市、暂停上市、风险警示/状态** | Tushare `stock_basic`；上交所和深交所有暂停/终止上市官方历史页面，交易所风险警示页面主要展示当前名单。[Tushare 文档](https://tushare.pro/document/2?doc_id=25) [上交所暂停/终止上市](https://www.sse.com.cn/assortment/stock/list/delisting/) [深交所暂停/终止上市](https://www.szse.cn/market/stock/suspend/index.html) [上交所风险警示板](https://www.sse.com.cn/disclosure/listedinfo/riskplate/) | `stock_basic` 可按 `ts_code`、`market`、`list_status`、`exchange`；返回代码、名称、市场、交易所、币种、`list_status`、`list_date`、`delist_date`、当前实控人等。每次最多 6000 行。交易所终止页返回证券代码、简称、上市日期、暂停/终止上市日期。 | 上市/退市日期是生效时间；`stock_basic` 没有这些字段的首次发布/更正时间。当前风险警示名单不等于历史状态事件。 | 无版本号、名称/ST 状态区间、修订或删除记录。交易所终止上市页能证明列出的事件，不能证明风险警示历史完整。 | Tushare 2000 积分、每分钟 50 次、最多 6000 行；交易所网页公开但无稳定历史事件 API/分页契约。 | 上市/退市已知事件可有限固化；**`SOURCE_BOUNDED_ONLY`**。历史 ST/撤销 ST、暂停/复牌及所有状态转换仍为 **`MISSING`**，不得从名称或 K 线存在性推断。 |
| **历史估值观察与五年分位数** | Tushare `daily_basic` 返回逐日 PE/PB/PS/市值，官方说明交易日 15–17 点更新。[接口文档](https://tushare.pro/document/2?doc_id=32) 上交所公开的市盈率页面是市场/行业汇总，不是逐证券五年观测。[上交所 A 股市盈率](http://www.sse.com.cn/market/stockdata/price/sh/) | `daily_basic` 按 `ts_code` 或 `trade_date`，以及日期范围；返回 `trade_date`、`close`、`pe`、`pe_ttm`、`pb`、`ps`、`ps_ttm`、`total_share`、`total_mv` 等。单次最多 6000。 | 事件时间是 `trade_date`；文档只给整体更新窗口 15–17 点，没有逐行 `available_at`。 | 无公式版本、采用哪一版财报的 statement ref、历史回算/更正版本或 revision id。PE/PB 可能随供应商口径/财报修订变化。 | 至少 2000 积分；5000 积分无总量限制；单次 6000。 | 能保存某次有限查询的观察值；**`SOURCE_BOUNDED_ONLY`**，不能直接成为 `valuation_observation_revision@1` 的 `AVAILABLE` 权威。最小改进是保存分子（当日总市值）并用已绑定、当时可用的报表分母自行计算。 |

## 分组结论

1. **原始财务报表：`SOURCE_BOUNDED_ONLY`**。Tushare 三表字段覆盖 ROIC/ROCE、FCF 和杠杆计算所需的大部分原始组成项，且报表类型能保存部分调整前记录；但日粒度公告时间、缺乏稳定 revision identity 和终止集是硬缺口。
2. **公告时间与更正：`SOURCE_BOUNDED_ONLY`**。巨潮/交易所的单份公告和静态 PDF 可成为强证据成员，深交所业务指南也证明发布具有明确时段；但未取得正式机器接口和全量闭包前，不能以网页搜索作为完整性证明。
3. **审计意见：`SOURCE_BOUNDED_ONLY`**。字段存在，审计原件可校验；重发/更正谱系及报告 identity 缺失。
4. **处罚/欺诈：`SOURCE_BOUNDED_ONLY`**。单份主管机关决定书可作为权威事实；跨 CSRC、地方证监局、上交所、深交所目录的全量 terminal set 为 `MISSING`。
5. **控股股东质押：`SOURCE_BOUNDED_ONLY`，控制人时序关联为 `MISSING`**。质押明细可抓，但供应商没有稳定事件 id，且无法仅凭当前实控人判断历史质押是否属于控制人。
6. **上市/退市：`SOURCE_BOUNDED_ONLY`；历史 ST/风险警示全链：`MISSING`**。
7. **估值：供应商观察 `SOURCE_BOUNDED_ONLY`**。若策略要求可审计比率，应以已冻结当日市值和当时可用报表分母重算，而非接受可变 PE/PB。
8. **完整策略财务治理 authority：`MISSING`**。缺的是闭包和时序，不是简单字段数量。

## 最小可行首个 G12A 契约切片

最小且不虚构完整性的候选是：

> **固定单一 A 股、单一已披露年度报告期、三张原始合并报表的 source-bounded snapshot**，暂不含全市场、策略评分、处罚“无事件”声明或估值分位数。

建议精确成员：

1. 对一个固定 `ts_code`，分别调用 `income`、`balancesheet`、`cashflow`，限定一个窄 `ann_date` 区间和一个 `period`；显式请求身份字段、策略必需原始行项目、`report_type`、`update_flag`。
2. 不只保存 `report_type=1`；保留同一 `period` 返回的 1/4/5（以及适用的调整前/调整后）全部记录，禁止按 `update_flag` 静默去重。
3. 保存三份原始 HTTP 响应 bytes、请求参数（不含 token）、字段顺序、获取时间、内容 hash、接口文档版本/获取日和明确限制声明。
4. 绑定该年度报告在巨潮/交易所的**具体静态公告 PDF**与公告列表元数据；PDF hash 作为报告原件 identity，公告实际发布时间作为优先 `available_at`。若只能得到日期，契约必须声明时间不确定并采用经审批的 fail-safe（例如不早于下一交易日开盘）而不能自行猜测。
5. 该切片只发布 `financial_statement_observations@1` 的 fixed-singleton/source-bounded sentinel，不声称五年、全市场、无后续更正或策略可执行。

这是第一条最小可落地路径，因为它复用 Tushare 已文档化接口与巨潮静态原件，不引入新供应商，也避免先构建全市场爬虫。

## 精确剩余 blocker

### Blocker（阻止首个切片被接受）

1. **公告可用时刻契约未冻结**：Tushare 仅给日期；需要正式决定如何绑定巨潮/交易所发布时间，以及缺少时分秒时是否 fail closed。
2. **修订 identity/schema 未冻结**：需定义 `statement_id`、`revision_id`、`supersedes`、报告类型冲突优先级、撤回/删除表示及相同公告日多行规则。
3. **CNINFO/交易所公告元数据接口未取得正式契约**：当前公开网页可发现文件，但没有已确认的 query keys、schema、分页上限、授权和历史完整性声明。首个 fixed singleton 可手工声明精确文件，但一般化前必须解决。
4. **原始字段映射与单位未批准**：须冻结一般工商业、银行、保险、证券四类公司的可用字段、单位、合并范围及缺失失败规则；不得用 `fina_indicator` 填洞。
5. **SourceSnapshot 收据和凭证安全流程未实现/批准**：token 只能环境注入，不能进入请求快照、日志、异常或 fixture。

### Blocker（阻止五年/全市场 Quality + B-Band 数据包）

1. **没有全市场财报和更正 terminal set**：无法证明某报告期所有应有报表均已出现、某旧版已被最终取代、或查询零行代表永久不存在。
2. **审计报告重发谱系缺失**：`fina_audit` 没有报告 id 和 supersedes。
3. **处罚/欺诈跨机关闭包缺失**：CSRC 中央、派出机构和两交易所目录没有统一 issuer key、分页闭包和复议/诉讼后继状态。
4. **历史控制人身份缺失**：`stock_basic.act_name` 是当前字段，不能反向标记历史质押。
5. **历史风险警示/ST/暂停复牌事件流缺失**：当前名单或证券简称不能替代历史状态 revision。
6. **估值分母 lineage 缺失**：`daily_basic` 不返回所用财报版本；需自行由当时可用报表重算或取得有公式/version/ref 的正式数据产品。
7. **许可与容量未验证**：需以不暴露 token 的受控探针确认普通/VIP 接口实际行上限、频率、历史起点、零行语义及 Fold A/B 全量有限抓取耗时。

## 来源取舍

### 保留

- Tushare `income`、`balancesheet`、`cashflow`：官方接口文档，字段和部分调整类型最贴近原始财务契约。
- Tushare `fina_audit`、`pledge_detail`、`pledge_stat`、`stock_basic`、`daily_basic`：官方接口文档，可精确定义有限查询和已返回字段。
- 巨潮/深交所业务指南与静态公告 PDF：发行人正式披露原件及发布时间机制证据。
- CSRC 行政处罚/市场禁入决定书目录、SSE/SZSE 纪律处分目录：中国法定监管/自律事实的主管来源。
- 中国结算股票质押信息页：明确登记结算机构与交易所质押公开信息的职责边界。

### 放弃作为权威

- 当前风险警示页、当前股票列表：只能证明当前展示，不能外推历史区间。
- 站内搜索“无结果”：不能证明无处罚、无质押、无更正或数据已终结。
- Tushare `fina_indicator` 的 ROIC/FCF/净债务等派生比率：没有公式版本与底层报表引用。
- 本地 DuckDB/Parquet/pickle：可变、无来源修订闭包，不是 G12A authority。
- 未公开文档的网页内部接口和第三方抓取说明：即使技术上可调用，也不构成稳定来源契约。

## 残余风险

- 官方网页可能调整 URL、分页或展示时间；未签约 API 时只能保证已固化文件，不保证未来重抓。
- Tushare 的“全部历史/实时更新”是服务描述，不等价于不可变历史版本或全球完整性证明。
- 单份行政决定书具有强事实权威，但决定公开日晚于违法发生日；策略必须按公开时点排除，不能事后回填。
- 对日期级披露采用“下一交易日可用”仍需 Backtest owner 明确批准；未经批准应 fail closed。
