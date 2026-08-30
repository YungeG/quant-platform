# Research: A 股策略版图缺口复核

> 研究目的：判断现有研究是否已覆盖有意义的策略空间，并找出仍值得测试、且与“技术预警 / 行业技术轮动 / 全市场地量择时” materially distinct 的方向。
>
> 本文是研究审阅，不构成投资建议。学术多空收益、事件窗口异常收益和指数回测不等于可交易净收益；没有统一的 point-in-time（PIT）数据、成交约束和成本模型前，不把任何异常称为已部署策略。

## Summary

**现有研究远未穷尽有意义的策略版图。** 仓库已经实证否定或弱化的主要是三类“价格/成交量驱动的方向性择时”：技术提前预警、行业技术轮动、市场级地量加减仓；它们不能代表横截面基本面、公告信息、公司行动、衍生品、跨资产配置或市场中性策略。

最值得继续测试的是：**(1) 可交易大中盘的价值×盈利质量×低波多因子纯多头；(2) 分析师盈利预测修正与 PEAD；(3) 股债金 ETF 的简单风险预算/趋势配置；(4) 流动性约束下的短期反转；(5) 可转债的低溢价/债底/质量复合纯多头。** 其中前两项最可能提供股票选择 alpha，第三项主要拥有组合分散与风险控制价值，不应混称为 alpha。

## Findings

### 1. 版图层面的结论

1. **high：现有经验测试只覆盖策略宇宙的一小部分。** `overall/a-share-early-warning-conclusion.md`、`overall/a-share-sector-rotation-conclusion.md`、`overall/a-share-ground-volume-validation-conclusion.md` 分别对技术预警、技术行业轮动和市场成交额择时给出 NO-GO/MARGINAL；它们没有测试 PIT 财务横截面、分析师修正、公告事件、可转债、ETF 多资产配置、期货基差或市场中性执行。
2. **high：已有综述识别了价值、低波、盈利能力等方向，但尚未完成本仓库可复现、含成本的纯多头验证。** `overall/a-share-strategy-research.md` 是证据综述，不等同于经验 Gate。严谨复制研究显示 A 股 value、risk、trading anomalies 相对稳健，但多数“因子动物园”异常在主板断点、价值加权和多重检验下失败，说明下一步应测试少数复合因子，而不是扩充指标库。[Liu, Stambaugh & Yuan, JFE](https://www.sciencedirect.com/science/article/pii/S0304405X19300625)；[Jansen, Swinkels & Zhou](https://pure.eur.nl/ws/files/58642799/Anomalies_in_the_China_A_share_market.pdf)；[Li et al., Management Science preprint](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4365416)
3. **high：学术上真实不等于可部署。** A 股异常常由多空、等权微盘、短周期换手或不可获得的融券腿放大。证监会自 2024-07-11 暂停转融券，融券保证金最低提高到 100%（私募 120%），当时融券余额仅约流通市值 0.05%；因此零成本多空结果必须拆解多头腿，并把市场中性策略视为机构级而非普通零售方案。[证监会](https://www.csrc.gov.cn/csrc/c100028/c7493852/content.shtml)

### 2. 策略家族逐项复核

| 家族 | 谁拥有 edge | 最强中国证据 | 证据是 pre-cost 还是 tradeable | 纯多头零售可行性 | PIT / 数据要求 | 最大实施损失 | 本仓库是否已测试 | 裁决 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **价值 / 低波 / 盈利能力 / 质量多因子纯多头** | 对壳价值、彩票偏好和高风险偏好的反向暴露；盈利现金流提供基本面锚；低波减少被高波垃圾股拖累 | CH-3 在剔除最小 30% 后以 EP 构造价值，2000–2016 的 SMB/VMG 均值分别 1.03%/1.14% 月度，但这是因子多空；更长复制认为 value、risk 较稳健，3 年波动率排序的低风险组合约 0.90%/月多空、持有 12 月仍约 0.85%。[JFE](https://www.sciencedirect.com/science/article/pii/S0304405X19300625)；[A-share anomalies](https://pure.eur.nl/ws/files/58642799/Anomalies_in_the_China_A_share_market.pdf)；[Volatility Effect](https://doi.org/10.1057/s41260-021-00218-0) | **主要 pre-cost 学术多空**；官方低波/红利指数提供可投资旁证，但指数收益不等于本策略净值 | **高**：月/季频，大中盘可做；适合作为核心增强 | 财报原始公告日、预告/快报/正式报告版本、当时可得一致预期；退市/ST/上市历史；自由流通市值与行业 PIT；分红和复权 | 财报未来函数、微盘污染、价值陷阱、行业集中、拥挤和估值制度变化 | **仅综述，未完成本仓库 PIT 含成本实测** | **TEST-NEXT #1** |
| **短期反转与个股流动性/低换手** | 零售追涨、注意力与换手情绪的过度反应；流动性补偿 | CH-4 的 turnover 因子可吸收反转/换手异常；综合 426 异常研究中低换手对高换手原始多空约 1.43%/月，CH3 alpha 1.14%，但加入 turnover 因子后不显著；更严格复制仍认为 reversal 是过去收益类的例外。[NBER CH-4](https://www.nber.org/system/files/working_papers/w24458/w24458.pdf)；[426 anomalies paper](http://cfrc.pbcsf.tsinghua.edu.cn/__local/1/28/BE/ECB6EDE9DA787BEA738415A420D_9BF29B07_1BA025.pdf?e=.pdf)；[A-share anomalies](https://pure.eur.nl/ws/files/58642799/Anomalies_in_the_China_A_share_market.pdf) | **pre-cost，多空且高换手**；低换手长腿可能与小盘/壳价值混杂 | **中低**：只能做“买入近期非极端下跌、流动性足够的相对输家”，不能复制空赢家腿 | 日行情、涨跌停和停牌、可成交开盘/收盘、逐日流通股、除权；最好有盘口/成交量以估冲击 | 印花税与冲击、高换手、跌停买不到/反弹卖不出、反转与价值/小盘重叠 | **未测试**；地量是市场级慢变量，不是个股横截面反转 | **TEST-NEXT #4**，必须低频化 |
| **盈利惊喜 / PEAD / 分析师修正** | 公告信息处理迟缓、有限注意、分析师私有基本面信息未及时入价 | 《金融研究》报告盈余预测修正和评级修正的三因子调整多空 alpha 分别 1.34%/0.92% 月度，收益集中在盈利公告窗口；2000–2020 研究继续支持中国 PEAD；2024 研究称基于公告隔夜信息的纯多头组合季度超市场 6.78%，但仍需独立含成本复核。[分析师修正原文页](http://www.jryj.org.cn/CN/abstract/abstract143.shtml)；[PEAD 2000–2020](https://ideas.repec.org/a/mes/emfitr/v58y2022i14p3985-4000.html)；[2024 PEAD](https://ideas.repec.org/a/eee/finana/v95y2024ipbs1057521924003922.html)；[Expectation disarray](https://ideas.repec.org/a/eee/pacfin/v82y2023ics0927538x23002639.html) | **大多 pre-cost 多空**；最新论文给纯多头表达，但未证明本地数据可复现和真实成交 | **中高**：做多上修/正惊喜，月/公告频；不需要融券 | 精确到分钟的公告发布时间、业绩预告/快报/季报版本；分析师逐笔预测和撤回、覆盖历史、复权；必须区分盘前/盘中/盘后 | 数据许可昂贵、公告后涨停无法买入、共识修订和幸存者偏差、业绩季拥挤 | **未测试**；行业研究仅建议加入分析师上修 | **TEST-NEXT #2** |
| **现金分红 / 回购 / 公司行动** | 可信现金分配、低估值信号或治理改善；但中国回购目的常含股权激励注销，分红受监管影响 | 早期并发公告研究发现现金分红本身没有清晰独立价格信息；较新研究认为分红变化主要传递短期盈利且无显著长期漂移。417 次回购公告研究显示公告后收益与增长/估值有关，但样本 2000–2012 且非统一净策略。[Dividend information](https://onlinelibrary.wiley.com/doi/10.1111/1467-646X.00080)；[Dividend signaling 2025](https://ideas.repec.org/a/eee/pacfin/v92y2025ics0927538x25001313.html)；[Repurchase announcements](https://businessperspectives.org/journals/investment-management-and-financial-innovations/issue-251/determinants-of-share-returns-following-repurchase-announcements-in-china) | 主要是事件研究、**pre-cost**；长期分红作为因子比公告交易更可行 | 分红质量筛选 **高**；公告追涨 **中低** | 分红预案/股东大会/实施日、税制与持有期；回购预案、用途、价格上限、实际执行进度与注销量 | 把预案当执行、一次性高分红、回购规模小或不完成、公告涨停 | 分红/低波仅综述，事件未测试 | **PASSIVE-ONLY**：并入质量因子；事件策略 defer |
| **指数调样 / ETF 资金流** | 被动资金机械需求与短期价格压力；可预测调样规则 | 现有本地研究综述已引用沪深 300 调入公告后约 40 日 15% CAR（旧样本）以及 300/500 交换公告后 3 日约 6%、执行后反转，说明是短期压力而非稳定基本面 alpha。[《金融研究》指数效应](http://www.jryj.org.cn/CN/Y2020/V480/I6/171) | **pre-cost 事件收益**，旧制度/旧拥挤状态；可预测性会被提前交易 | **中**，但需要抢跑且成交窗口拥挤；长期持有无 edge 保证 | 每期官方成分、编制规则版本、自由流通调整、市值缓冲区、公告与生效时间；ETF 份额/NAV/申赎 | 预测误差、公告前已反映、冲击成本、执行日反转 | 仅综述，未实测 | **DEFER**：排在 PEAD 后 |
| **可转债价值 / 动量 / optionality** | 债底、转股期权和条款复杂度导致定价分散；T+0 市场可能更快发现股票信息 | 中国负转股溢价事件超过 1% 的 bond-days 低于 -0.5%，隔夜转股卖出后平均仍保留超过一半价差；可转债订单不平衡预测股票收益，论文多空年化 17.54%。但这些是套利/高频信息证据，不是简单多头基金收益。[Negative conversion premium](https://www.sciencedirect.com/science/article/pii/S2405918820300155)；[CB order imbalance](https://ideas.repec.org/a/eee/pacfin/v79y2023ics0927538x23000926.html) | NCP 更接近可交易但依赖转股流程、库存和开盘成交；订单流结果 **pre-cost 多空** | **中高**：可做低价、低溢价、正股质量过滤的低频纯多头；不建议零售复制 delta hedge | 每只债券条款 PIT、转股价下修/赎回/回售触发计数、信用、剩余规模、正股停牌与涨跌停、分钟成交 | 强赎尾部、信用与流动性、条款解析错误、高频拥挤；股性暴露伪装成 alpha | **未测试** | **TEST-NEXT #5** |
| **股债金 ETF 多资产趋势 / carry / risk parity** | 边际收益主要来自低相关资产、再平衡和风险预算，不一定是预测 alpha；趋势可降低长期熊市暴露 | 中证/上证已有股债金或股债风险平价官方方法：用过去 6–12 个月协方差、季度调仓、等风险贡献；黄金与中国股票的尾部依赖较弱，研究显示加入黄金降低股票组合方差。[SSE Dividend Equity-Bond Risk Parity methodology](http://english.sse.com.cn/markets/indices/indexnews/c/10764676/files/8b509873347d42fd8ad6521906d3d73d.pdf)；[China stock-gold diversification](https://www.tu-chemnitz.de/wirtschaft/vwl1/RePEc/download/tch/wpaper/CEP012_SGE.pdf) | 官方方法可实现；绩效证据多为指数回溯/配置研究，不应称 alpha | **很高**：宽基 ETF、国债 ETF、黄金 ETF 均可低频实现 | ETF 上市/清盘 PIT、复权 NAV、分红、费率、折溢价；债券指数久期和信用暴露；现金收益 | 债券因低波被过度配置、相关性突变、趋势滞后、ETF 历史幸存偏差 | **未测试**；现有地量择时不等于跨资产配置 | **TEST-NEXT #3**，作为组合层而非选股 alpha |
| **股指期货基差 / carry / 跨期** | 套保需求、卖空约束、保证金与结构化产品对冲造成持续贴水；基差到期收敛 | 中国 IF/IC 研究证明基差偏离与情绪相关；早期分钟数据存在无套利区间外机会，但偏离平均约十余分钟收敛。论文自身强调融资、跟踪误差、冲击和融券决定净收益。[Sentiment and futures basis](https://www.acem.sjtu.edu.cn/ueditor/jsp/upload/file/20230705/1688558895949073353.pdf)；[High-frequency basis](https://www.scirp.net/journal/paperinformation?paperid=18372) | 旧样本、机构成本假设下部分可交易；对普通投资者不是无风险收益 | **低**：合约乘数、保证金、展期和适当性门槛；纯多头可用贴水期货替代 ETF，但仍有杠杆风险 | 逐合约盘口、到期与分红预测、资金利率、保证金、展期、ETF 跟踪误差 | 杠杆/追保、贴水扩大、模型分红误差、交易所政策变化 | **未测试** | **DEFER**：机构级；可先做只读基差监控 |
| **配对 / stat-arb / 市场中性** | 同行业或同现金流证券的相对错价与均值回归 | 中国单市场配对证据混合：网络研究显示协整关系脆弱，超过 45% 的配对 12 个月内不再出现；跨 A/H 配对在 1996–2017 含成本后年化异常约 9%，但单一内地/香港市场内不显著。[Network evidence](https://ideas.repec.org/a/eee/phsmap/v505y2018icp903-918.html)；[A/H pairs](https://eprints.whiterose.ac.uk/id/eprint/143981/3/Pairs%20Trading%20Across%20Mainland%20China%20and%20Hong%20Kong%20Stock%20Markets.pdf) | 跨市场论文声称含成本；仍依赖可卖空、外汇/跨境与稳定关系 | **很低**：A 股券源极少且不稳定；普通纯多头无法市场中性 | PIT 可融券名单、逐日券源/费率、A/H 公司行动和汇率、分钟成交、停牌/涨跌停 | 券源消失、强制回补、结构断裂、双边成本和基差长期不收敛 | **未测试** | **REJECT（零售）/ DEFER（机构）** |
| **日内 / 隔夜 / 微观结构** | T+1 对开盘价格的机械折价、订单不平衡、收盘价格压力 | Journal of Financial Markets 估计 A 股 T+1 平均开盘折价约 14bp，解释负隔夜收益；这证明制度性模式真实，但买入当天不能卖出，直接套利受规则本身约束。[Qiao & Dam](https://pure.rug.nl/ws/files/132141807/1_s2.0_S1386418120300033_main.pdf)；[Zhang](https://ideas.repec.org/a/eee/ecmode/v89y2020icp55-71.html) | **机制证据强，策略可交易性弱**；14bp 未扣价差、冲击和隔夜风险 | **低**：需要库存、精细开收盘执行；T+1 阻止普通日内回转 | tick/逐笔委托、集合竞价、停牌/涨跌停、精确费用和库存 | 价差与冲击吞噬、隔夜跳空、排队、数据/基础设施成本 | 未测试 | **REJECT** 作为当前仓库方向；仅用于执行模型 |
| **IPO / 涨停 / 注意力异常** | 新股稀缺、彩票偏好、注意力和涨跌停协调造成过度反应 | 注册制研究对 IPO 初始收益影响结论不完全一致，但共同指向制度变化显著、首日收益含过度反应；深交所账户级研究发现大户在涨停日买、次日卖，其净买入预测更强长期反转，说明“打板”利润可能来自破坏性价格压力而非持续信息。[Registration reform](https://doi.org/10.1080/00036846.2023.2212978)；[IPO policy](https://ideas.repec.org/a/eee/finlet/v47y2022ipas1544612321005602.html)；[Daily price limits](https://wxiong.mycpanel.princeton.edu/papers/PriceLimit.pdf) | IPO 多为事件研究；涨停证据说明异常真实但对跟随者未必可获利 | **低**：新股配售不可稳定获得，涨停无法保证成交 | IPO 申购中签与资金冻结、板块规则版本、逐笔封单/开板、上市与退市全样本 | 买不到、次日反转、制度频繁改变、尾部损失与操纵风险 | 未测试 | **REJECT** 作为系统核心；可作风险过滤 |
| **北向 / ETF / 公募等资金流与另类数据** | 部分跨境投资者的基本面信息优势，或后续跟随交易的价格压力；文本/搜索可能改善风险预测 | 北向持仓变化论文报告最高约 0.61%/周多空预测，但监管穿透后可预测性衰减；JEF 2024 仍报告 CH3 调整约 0.34%/周。更关键的是 2024 年沪深港交易所调整披露：不再实时披露北向买卖额，个股持仓改为季度披露，直接削弱公开数据策略。[Value of information](https://ideas.repec.org/a/eee/empfin/v78y2024ics0927539824000616.html)；[Homemade foreign trading](https://bfi.uchicago.edu/wp-content/uploads/2023/01/BFI_WP_2022-170.pdf)；[HKEX disclosure change](https://www.hkex.com.hk/News/Market-Communications/2024/2404122news?sc_lang=) | 历史信号 **pre-cost 多空**，且存在结构断点；公开实时实现性已下降 | 北向个股流 **低**；低频 ETF 份额/基金申赎 **中** | 数据供应商 PIT 持仓/流量、披露规则断点、基金份额/NAV、文本发布时间、网页存档 | 数据消失或定义改变、反向因果、跟随拥挤、另类数据许可/合规 | 未测试；行业结论仅建议研究资金流 | **DEFER**；只测试仍稳定公开的低频流量 |
| **传统个股中期动量 / 技术趋势** | 行为延续或风险暴露 | A 股 12–1 动量在长样本通常不显著，反转更强；仓库自己的技术预警与行业轮动已在成本后失败或不稳定。[A-share anomalies](https://pure.eur.nl/ws/files/58642799/Anomalies_in_the_China_A_share_market.pdf)；本地结论文件 | 学术上弱，仓库实测也未通过 | 中，但没有充分 edge | 日线即可，执行仍需涨跌停/T+1 | 状态依赖、高换手、参数过拟合 | **已测试相邻表达，失败** | **REJECT** 继续堆指标 |

### 3. “异常真实”与“策略可部署”的分界

- **异常较真实且较可部署：** 大中盘低波；行业内 EP/现金流价值；及时盈利能力；这些是慢信号，可用纯多头和低频调仓表达。
- **异常较真实但部署折损大：** 短期反转、换手/流动性、PEAD、指数调样、可转债订单流。共同问题是高换手、不可成交事件窗口或多空腿。
- **机制真实但不是零售 alpha：** T+1 开盘折价、期货基差、涨停价格压力、ETF/北向流冲击。它们更适合改善执行和风险建模。
- **主要是配置价值而非 alpha：** 股债金风险平价、黄金分散、债券久期配置。即使不能跑赢最强单资产，也可能显著改善组合回撤。
- **当前应拒绝：** 再次搜索技术指标、涨停追逐、纯 A 股零售配对/市场中性、依赖已停止公开实时数据的北向跟随。

## Ranked shortlist：最多五个下一步实验

### 1. 大中盘价值 × 盈利质量 × 低波纯多头

**为什么第一：** 中国证据跨论文、慢信号、纯多头可表达、容量和零售可行性最好；与已失败的技术择时完全不同。

**最小诚实验证：**

- 宇宙：历史时点中证全指中流动性前 70%，剔除上市不足 250 日、ST/退市整理、最小市值 30%；另报沪深 300/中证 500 子样本。
- 信号：行业内 EP 或经营现金流收益率、季度 ROE/ROA、3 年波动率；只比较等权三信号 composite 与单因子，不做参数搜索。
- 时点：财务数据在实际公告后下一交易日可用；月末形成、次月首个可成交开盘执行，季度换仓。
- 对照：同宇宙市值加权、红利低波官方指数代理、单纯 EP。
- 成本：佣金+卖出印花税+按成交额/ADV 分层冲击；涨跌停和停牌延迟成交。
- Gate：2008–2018 形成、2019–2022 验证、2023–最新锁定测试；测试期净超额、Sharpe、最大回撤三者至少两项优于基准，且不由最小市值十分位或单一行业贡献。

### 2. 分析师上修 × 盈利惊喜 / PEAD 纯多头

**为什么第二：** 信息源不同于价格技术指标，中国原始研究直接报告较强修正收益并指向盈利公告窗口；但 PIT 数据门槛高于多因子。

**最小诚实验证：**

- 宇宙：有至少 3 位分析师覆盖且日均成交额达门槛的非 ST A 股。
- 冻结信号：过去 30 日 FY1 EPS 共识上修幅度和上修分析师占比；公告后 SUE 只用当时可得预告/快报/正式报告。
- 组合：月度持有上修 top quintile；PEAD 另做公告后第一个可成交开盘进入、持有 20/60 日的两组预承诺窗口。
- 防作弊：保留逐笔预测版本、撤回和分析师新增/退出；盘后公告不得用当日收盘成交；涨停无法成交则记录 miss，不补用理论价。
- Gate：纯多头对覆盖股票等权基准的含成本超额为正，并在至少两个非重叠时期、公告季/非公告季拆分中同向。

### 3. A 股宽基 + 国债 ETF + 黄金 ETF 的简单风险预算/趋势层

**为什么第三：** 最容易实际部署，能补足仓库只有股票方向择时、没有组合层风险管理的缺口；目标是改善回撤与复利稳定性，不冒充选股 alpha。

**最小诚实验证：**

- 仅三只可获得长历史代理：沪深 300 全收益、中债国债总财富/可交易国债 ETF、上海金/黄金 ETF；实际 ETF 上市后切换为基金 NAV。
- 比较三条冻结规则：1/N、12 月波动率倒数、等风险贡献；季度再平衡。另加一个极简 10 月均线过滤，但不与风险平价组合调参。
- 对照：60/40 股债、全股票、固定 30/50/20 股债金。
- Gate：含基金费率、跟踪误差代理和 10bp 单边成本后，2008 年以来及 2015/2018/2022 压力期最大回撤显著低于全股票；同时长期 CAGR 不低于固定股债金 1 个百分点以上。重点检验“复杂风险平价是否真的优于固定权重”。

### 4. 流动性约束下的月度短期反转纯多头

**为什么第四：** 反转是 A 股过去收益异常中少数相对稳健者，但交易摩擦大，必须先证明长腿单独存在。

**最小诚实验证：**

- 宇宙：流动性前 50%，剔除过去 5 日触及跌停、停牌和事件驱动极端股。
- 信号：只用过去 20 日行业/市场残差收益，买最低 quintile，持有 20 日；不做空赢家。
- 执行：信号后下一交易日 VWAP/开盘保守价，涨跌停延迟；报告换手、ADV 占比和未成交率。
- Gate：净收益不仅高于同宇宙基准，还须在剔除最小市值 50% 后存在；若成本从 10bp 增到 30bp 即消失，则判 reject。

### 5. 可转债低价 × 低溢价 × 正股质量纯多头

**为什么第五：** 资产类型与现有股票择时完全不同，债底和期权可能提供凸性；但条款数据和强赎建模复杂，证据不如前四项直接。

**最小诚实验证：**

- 宇宙：可交易、未进入强赎最后窗口、剩余规模和成交额达门槛的转债。
- 信号：价格、转股溢价率、到期收益/债底、正股盈利质量四项固定打分；月度 top 20–30 等权。
- 必须模拟：转股价下修、强赎公告、停牌、到期/回售、正股涨跌停和债券实际成交；不用理论期权模型拟合参数。
- 对照：中证转债指数、低价等权、低溢价等权。
- Gate：含 20–50bp 冲击后改善 Sharpe/回撤，且收益不能主要来自高股性牛市 beta。

## 为什么其余方向没有进入前五

- **指数调样：** 证据明确但旧样本、拥挤且容量有限；可在 PEAD 管线建成后复用事件数据框架。
- **分红/回购事件：** 长期质量/分红因子可并入 #1，公告漂移证据不足以优先单独建设。
- **期货基差：** 可能有机构 carry，但杠杆、保证金、分红预测和合约执行超出当前零售长仓研究的最小范围。
- **市场中性/配对：** 当前融券结构使学术策略无法诚实映射；先不浪费回测工程。
- **日内/隔夜：** 主要用于执行基准；没有 tick 数据和库存机制时，日线回测必然夸大收益。
- **IPO/涨停/注意力：** 易把无法成交的价格路径当 alpha，且制度断点频繁。
- **北向资金流：** 历史证据存在，但 2018 身份穿透后衰减，2024 披露频率调整进一步降低公开实现性。

## Sources

### Kept

- [Size and Value in China, Journal of Financial Economics](https://www.sciencedirect.com/science/article/pii/S0304405X19300625) — 中国化价值/规模模型、壳价值过滤与 EP 选择的核心原始证据。
- [Anomalies in the China A-share Market](https://pure.eur.nl/ws/files/58642799/Anomalies_in_the_China_A_share_market.pdf) — 2000–2019、32 个异常的统一复核，支持 value/risk/trading，弱化传统 momentum/quality 泛化。
- [Replicating and Digesting Anomalies in the Chinese A-share Market](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4365416) — 469 异常、多重检验、主板断点与价值加权的严谨反证。
- [分析师修正信息、基本面分析与未来股票收益](http://www.jryj.org.cn/CN/abstract/abstract143.shtml) — 中国本地原始研究，给出修正组合 alpha 和收益集中窗口。
- [The overnight return puzzle and the T+1 trading rule](https://pure.rug.nl/ws/files/132141807/1_s2.0_S1386418120300033_main.pdf) — T+1 开盘折价的高质量市场微观结构证据。
- [Daily price limits and destructive market behavior](https://wxiong.mycpanel.princeton.edu/papers/PriceLimit.pdf) — 深交所账户级数据，揭示涨停价格压力与长期反转。
- [Negative conversion premium](https://www.sciencedirect.com/science/article/pii/S2405918820300155) — 可转债负溢价的频率、转股执行和剩余利润。
- [证监会暂停转融券](https://www.csrc.gov.cn/csrc/c100028/c7493852/content.shtml) — 当前做空与市场中性可行性的权威约束。
- [HKEX/SSE/SZSE Stock Connect data disclosure adjustment](https://www.hkex.com.hk/News/Market-Communications/2024/2404122news?sc_lang=) — 北向实时/个股持仓数据可获得性结构断点。
- 本地文件：`overall/a-share-strategy-research.md`、`overall/a-share-early-warning-conclusion.md`、`overall/a-share-sector-rotation-conclusion.md`、`overall/a-share-ground-volume-validation-conclusion.md` — 确定已覆盖范围、实测失败项和未测试缺口。

### Dropped or down-weighted

- 券商/媒体“ETF 轮动高收益回测” — 参数、基金幸存偏差和实际成交披露不足。
- 2025–2026 低声誉期刊的复杂 ML、动态配对或可转债定价回测 — 可作假设来源，不用于核心裁决。
- 早期 2010–2013 股指期货套利收益数字 — 市场结构、费用和监管已大幅变化，只保留机制判断。
- 只报告累计收益、不拆多头/空头、不含冲击或用收盘价假设涨停成交的研究 — 不足以判断部署价值。

## Gaps / uncertainty

1. **不能证明“已经穷尽”。** 本文按经济机制和资产类别覆盖主要家族，但策略空间无限，且中国制度持续变化；结论是“现有研究明显未穷尽”，不是数学意义上的完备证明。
2. **PIT 数据库存未知。** 若仓库没有原始财报版本、逐笔分析师预测、公告时间戳、历史成分和可转债条款，#1/#2/#5 的优先级可能因数据采购成本调整。
3. **交易成本缺少统一实测。** 学术论文成本口径差异大；下一步必须以本仓库同一执行器、相同税费/冲击模型比较。
4. **多因子可能只是已知风险暴露。** 即使纯多头跑赢，也需用行业、市值、beta、流动性分解，不能把低 beta 或小盘暴露全称为 alpha。
5. **未来制度断点风险高。** 融券、涨跌停、IPO、北向披露、程序化交易和可转债强赎规则均可能改变历史关系。

## Review findings

- **high — `overall/a-share-strategy-research.md`：** 方向综述较广，但容易被误读为“已测试”；实际上只有三项本地经验 Gate，基本面、公告、跨资产和可转债仍是实证空白。
- **high — `overall/a-share-early-warning-conclusion.md` / `overall/a-share-sector-rotation-conclusion.md`：** 已有结果足以停止继续堆叠技术指标；下一轮信息必须来自财务、分析师、公告、条款或跨资产，而非同源价格变换。
- **medium — 数据层：** 若没有 PIT 财务/公告/分析师历史，任何 #1/#2 回测都会有未来函数风险，应在建模前先做数据审计。
- **medium — 执行层：** 所有事件和反转实验必须记录不可成交率；否则涨停、跌停和停牌会制造虚假 alpha。

## Residual risks

- 研究依赖部分付费论文摘要和可访问预印本，未逐表复算全部统计量。
- 2024–2026 制度变化后的长期样本尚短，尤其是融券、北向披露和全面注册制。
- 本次没有检查 sibling research 目录的全部文件清单，可能存在未在指定四份结论中汇总的零散实验；核心判断以明确指定的本地结论文件为准。
