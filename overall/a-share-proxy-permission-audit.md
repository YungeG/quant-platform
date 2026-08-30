# xiaodefa代理权限与A股数据缺口审计

- **日期：** 2026-08-27
- **结论：** 代理具有至少等价于Tushare 10,000积分的积分接口权限，行为与15,000积分高阶权限一致，但无法通过公开API直接证明精确积分余额。2026-08-27复核确认历史分钟和集合竞价独立权限已经开通；公告和券商研报PDF权限仍未开通。

## 官方权限规则

Tushare官方将权限分为：

1. 积分接口；
2. 与积分无关、逐项开通的独立权限。

15,000积分的官方权益是特色数据无总量限制；历史分钟、公告、新闻和集合竞价仍需分别购买。

- 权限说明：https://tushare.pro/document/1?doc_id=290
- 集合竞价：https://tushare.pro/document/2?doc_id=369
- 历史分钟：https://tushare.pro/wctapi/documents/370.md
- 游资明细：https://tushare.pro/wctapi/documents/312.md
- 筹码分布：https://tushare.pro/wctapi/documents/294.md
- 筹码胜率：https://tushare.pro/wctapi/documents/293.md

官方`hm_detail`明确要求10,000积分。代理成功返回该接口，因此可证明至少10,000积分等价权限。官方没有公开查询代理上游积分余额的API；15,000与10,000在大量接口上仅表现为每日总量差异，不能通过少量请求安全地区分。

## 实测积分接口

| 接口 | 结果 | 用途 |
| --- | --- | --- |
| forecast_vip / express_vip | 成功 | 业绩预告、快报 |
| income_vip / balancesheet_vip / cashflow_vip | 成功 | PIT财务报表 |
| fina_indicator_vip | 成功，含ann_date | PIT质量因子 |
| cyq_chips / cyq_perf | 成功 | 2018年以来筹码成本、胜率 |
| hm_detail / hm_list | 成功 | 2022-08以来游资交易 |
| broker_recommend | 成功 | 券商月度金股 |
| report_rc | 成功 | 逐券商、逐报告、逐预测期盈利预测历史 |
| stk_surv | 成功 | 机构调研 |
| limit_list_d | 成功 | 2020年以来涨跌停、炸板、封单 |
| moneyflow_ths | 成功 | 同花顺个股资金流 |
| moneyflow_dc | 成功 | 东方财富个股资金流；实测2024年以来有值 |
| dc_index / dc_member | 成功 | 东方财富概念；实测历史从2025开始 |
| ths_index / ths_member / ths_daily | 成功 | 同花顺指数和成员 |

`report_rc`实测字段包括报告日期、机构、作者、预测季度、收入、营业利润、净利润、EPS、PE、ROE、评级和目标价格，可用于构造PIT分析师一致预期及修正，而不再把该方向视为完全数据阻塞。

## 实测独立权限

| 接口 | 结果 | 官方规则 |
| --- | --- | --- |
| stk_auction_o / stk_auction_c | 已开通；实测2016、2018、2020、2022、2023、2024、2026均返回数据 | 独立开盘/收盘集合竞价权限 |
| stk_auction | 已开通；实测2025-02和2026-08返回数据，2024为空 | 当日集合竞价接口，官方历史从2025-01开始 |
| stk_mins | 已开通；1/5分钟实测成功，2010和2019均返回49根5分钟Bar | 独立历史分钟权限；可提供超过10年历史 |
| anns_d | 40203，没有接口权限 | 独立公告权限 |
| research_report | 40203，没有接口权限 | 独立券商研报PDF/摘要权限 |

## 更新后的数据缺口

### 已由代理补齐或可补齐

- PIT ROE/ROA/毛利率等质量因子：使用fina_indicator_vip的ann_date；
- 分析师预测修正：使用report_rc构造按报告日期、机构和预测季度的历史共识；
- 筹码成本和获利盘：cyq_chips/cyq_perf，2018年以来；
- 涨跌停、炸板和封单：limit_list_d，2020年以来；
- 游资和资金流：hm_detail、moneyflow_ths、moneyflow_dc；
- 机构关注：stk_surv、broker_recommend；
- 财务公告和报表版本：forecast/express及三张VIP报表。

### 仍然缺失

- 通用上市公司公告标题/PDF历史；
- 2025年前PIT东方财富概念成员；
- 盘口委托、封单变化和订单簿；
- 代理上游精确积分余额证明。

## 使用决策

后续所有Tushare类接口先通过xiaodefa代理探测。只有代理明确返回独立权限不足或历史为空时，才考虑原生Token、现有本地数据或新采购。不得将代理x-api-key传入`ts.pro_api()`。
