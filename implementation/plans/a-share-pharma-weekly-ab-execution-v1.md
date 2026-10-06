# 医药开发分析：本会话完成记录

这里只保留本轮简单收益/NAV段落；完整历史方案和其它增量不属于此提交。当前分支仅保存分析增量，标准组合执行前置尚未提交，不能据此声称干净克隆可执行完整NAV或正式Validation通过。

## 本轮开发路径与资格边界更正（2026-10-04；9/29既有假设持续有效）

- 已取回原会话两条用户原话：9/29“只要是这种带有日期的数据，没有更细粒度的时间，我们就认为当天收盘后可见”，随后“我们就认为这个数据是准确的，当时可见的”；Main当时承诺不再以日线历史首次发布时间阻断假设性回测。原计划`research/a-share-pharma-regime-gated-turnover-top10-v1-plan.md:9`已固定每日市场观测数值准确、D日上海23:59:59盘后可见、只用于下一合格开盘。
- **开发门已解除且不重问**：`daily_basic.turnover_rate_f`和SW日收盘数据按这一假设用于条件化开发；次日open只作事先订单的实现价，全天vol不作开盘流动性。2026回执/PIT未知仍保留事实，但**不是该日线假设路径的未决门禁**。成员生效日、上市退市/停牌、公司行动及费用不自动套用EOD假设。
- **费用亦按声明分层**：已有Oct运行的沪深费税明确为`hypothesis.october2024.diagnostic.rates`，佣金为3bps/terminal filled Order最低CNY5、市场法定组件另列、零滑点。可对该已完成模型派生明确标注的Backtest开发分析，不称真实券商账户或Jan官方费投影跨期授权；新场景/官方适用证据和高等级结论另核。没有自动放行holdout、成对回撤规则或ValidationReport。
- **最小执行路径已冻结**：仅从既有完整A/B COMPLETED原文→Domain exact Envelope→既有LocalFoundation**分析CAS镜像**→public BacktestEvidenceRepository.load_completed→BacktestAnalysisRuntime.publish_metric_profile/derive→repository.load_analysis并回验同源和幂等ref，生成现有simple_period_return/fill-count；不重跑Engine、不另算PnL、也不把没有接受的每日NAV/MaxDD填入旧Analysis。分析CAS不是医药Research的Foundation/样本账本绑定，复制CAS不产生新owner-log证据年龄或未见样本。
- 单writer Main411；仅新增Root实验驱动/聚焦测试并更正此原台账。完整性失败必须早于分析，不发布伪造0；原manifest/失败根/receipt/hash/包源码、Root锁/环境、正式来源/费用/交易资格不改。现有两股Root烟测未留全CAS档案，因此先最小exact-copy/失败守卫，再用单臂≤64MiB完整图作有界样本，通过后才另一臂；无需为分析重新跑两股或全A/B。

## 已有A/B完成物的公开开发收益分析完成（2026-10-04）

**实际结果／模式**：A股Review，复用已消费的2024-10-14—25十日/两调仓周、同`lookback1/top10/seed0/MA200-60-3`及各臂独立纸面CNY100000。公开`BacktestAnalysisRuntime`的**现有**`simple_period_return.fill_count.v1`已返回并经公开Repository核验；本轮没有新Backtest经济运行，没有修改参数、费用/滑点、原目标或旧原文。结果仅是`assumption_bound_development`，不是未见样本效果或真实券商净收益。

| 臂／策略 | Backtest原生simple_period_return | 展示为百分比 | fill-count（不是订单数） | Analysis@1 content hash |
|---|---|---|---|---|
| A：周换手率Top10，无阶段门控 | `0.0850647` | **8.50647%** | 18 | `4bc0400326e6cc6ab48656cda9a5bd391f217f087ed13b5317b6933b30bcb28f` |
| B：相同名册，仅bull持有／其余现金目标 | `0.0339121` | **3.39121%** | 20 | `6c39ff9e34256ea41c99644ae645a866181e4ff5d810b5b7bddf7b7a47703a5e` |

**解释边界**：这段已见两周样本中B收益低于A，不能据此宣称门控有效、无效或优化规则；不改变预冻结参数/失败阈值。两臂交易与实际退出来自原生Fill而非目标权重推断。最大回撤**未计算，保持null而不是0**；现有Profile明确drawdown_sampling=not_applicable，未调用私有draft算式、手工PnL或把两份单臂收益伪装成成对Validation。

**执行与材料位置**：
- 新Root驱动`experiments/analyze_a_share_pharma_completed_development.py`仅进口Domain/Foundation/Backtest public roots，使用已接受`ArtifactEnvelope`/`LocalFoundation.put/read`镜像规范原文，依序`repository.load_completed → runtime.publish_metric_profile/derive → repository.load_analysis`；强制DEVELOPMENT、exact Analysis@1、原publication/execution hash/profile/grade四重绑定，重复derive同ref。没有`Runtime.run`、sample reserve、owner-log append或当前行情/provider访问。
- 原两股Root烟测没有导出完整CAS图，不能仅凭canonical文件分析，也不为此重跑Engine。先最小Envelope exact-copy/replay+篡改失败路径，随后**单臂A**18份完整原图/40,407,936 bytes（≤64MiB）通过，再同代码处理B的18份/41,434,990 bytes。各原档案在操作结束逐字节再对照，保持不变；所有旧FAILED根保留。
- 新输出为`research/evidence/a-share-pharma-october-2024-acquisition-20260930/development-analysis-v1/{A,B}/summary.json`及各自`analysis-cas/`。这仅是**Backtest开发分析CAS镜像**，不是原Research的Foundation composition、样本账本或新的owner-log publication/admission；不产生Experiment/Candidate、留出记录或证据年龄刷新。
- 同一metric profile@1 hash=`bced4dbef8bbf6e1ec9821ae3b68e8c6ce2bbed953f95fe1214c8e21676dbd6a`。原A/B canonical manifests仍分别`5024e049...457c0`/`127dcda2...29d`，execution hashes仍`754d0260...77c7`/`610c69e2...3df`，全值在新summary与上文旧完成记录，未伪造两臂publication/MarketBundle相同。

**实际验收**：
- 新聚焦测试`tests/research/test_analyze_a_share_pharma_completed_development.py`共**10个不同检查最终通过**：1 exact-copy/replay（0.64s），6类档案拒绝、未核证completion拒绝和输出根隔离共8（0.54s），public-only/无run-reserve-append静态守卫修正后1（0.55s）。首次Pyright联合返回类型1错已通过exact Analysis@1守卫修复；首次静态测试把普通`sources.append`误判owner append，只允许该确切list receiver后通过，不放宽治理append。两个增量文件新鲜Pyright **0 errors**；未重复已过Root/native/full A/B测试，也未跑不相关全仓套件。
- A/B实际完整分析与同臂derive ref幂等均通过。另一个**新Root进程**只凭新CAS与AnalysisArtifactRef调用公开`load_analysis`，再次核验两份分析及其原completion/run binding，返回同收益/成交数；两CAS registry均无owner-log文件、`.foundation.clock`不存在。没有使用先前typed结果绕过档案冷读。
- 当前14个purelib dist-info version/direct_url/RECORD、Root pyproject/uv.lock及四实际加载source path/源码SHA/旧Engine SHA均与`/tmp/pharma-root-sync.pYY6eJ/after-sync.json`一致；不安装、改包或提升source/PIT/broker/formal/Validation/trade/deployment资格。`maximum_drawdown/validation_report=null`，本操作holdout_reserved=false，不对全局未知账本作“无人读取”断言。

**此阶段后续（已由下节公共NAV/MaxDD验收记录闭合）**：Main411已实现新版本Profile/Analysis公共seam及原生日快照、完整Journal/Mark/日期exact-cover绑定，并完成小样本与失败检查；不从私有draft或调用方填写的权益直接造正式指标、不改旧Analysis@1/MetricProfile@1字节。成对Validation规则、真正未触碰样本及其前置producer/revision/ledger绑定仍另有验收，不由当前两份简单收益授予。无需用户重复批准日线假设、当前分析或安装；新认证取数仍按批冻结精确预算后询许可。

## 公共Backtest每日NAV/MaxDD验收完成（2026-10-04；DEVELOPMENT）

**实际结果**：仅分析旧标准COMPLETED的Oct14—25十个收盘，不重跑交易/改参或成本。

| 臂 | 模型净收益 | **收盘采样**最大回撤 | NAV点／Fill数 | 新NAV Analysis@1 hash |
|---|---|---|---|---|
| A：周Top10 | 8.50647% | **1.2790327456866677%** | 10／18 | `65e3d3362e82f58135454dda7760ad48c0a790729359278a6a7abf60f7bdf992` |
| B：同榜单+行业bull门控 | 3.39121% | **1.2790327456866677%** | 10／20 | `636b0335a0cfc156a29c0f6f6c0046b677f2f90ca5d840ef2926dd11458a82e8` |

**解释边界**：B在此已见窗口收益更低且收盘回撤未降低；两臂首5日曲线完全相同，共同最深收盘跌落在首周，B退出后净值固定。不是盘中全时点回撤、长期效果或正式Validation结论；不据结果改MA/选择规则。回撤fraction=`0.012790327456866677`，期初权益纳入峰值、18位half-even，缺日/缺源从不填0。

**新版本／实际Root已接通**：
- Backtest新`cn_a_share_portfolio_daily_nav_analysis_v1.py`导出5个public值/操作：`CnASharePortfolioDailyNavMetricProfileV1`、`CnASharePortfolioDailyNavPointV1`、`CnASharePortfolioDailyNavAnalysisV1`、`CnASharePortfolioDailyNavAnalysisRefV1`、`CnASharePortfolioDailyNavAnalysisRuntimeV1`。Runtime的`publish_metric_profile()`及kw-only `derive(publication_ref, execution_input_ref, metric_profile_ref)`只接exact refs，不接调用方权益/布尔。
- 新两namespace：`cn_a_share_portfolio_daily_nav_metric_profile@1`／`cn_a_share_portfolio_daily_nav_analysis@1`，共同Profile hash=`c73c1e131753437b52be077a2bc2da211ff4de4563ebb9014204fa8162f86a54`。原Repository catalog仅增两decoder及public `load_cn_a_share_portfolio_daily_nav()`；冷读重新从原completion/input8/source投影、逐字节比较整分析。旧Analysis@1/@2、MetricProfile@1及旧Result/Engine/input8字节不扩写，旧load_analysis拒新ref。
- Source验证先public Repository完整核旧完成图，再canonical→result→evidence→原Engine及显式input8 ref。sole input8 decoder/target repository/definition reader核request/run/spec/build/target/whole source/native初态/bundle/account；两日历TRADING、原midnight-exclusive窗口与15:00 fullclock marks/日事实exact-cover。Journal头须为该clock**最大可见原前缀**，复用原生GenericLedger/PortfolioSnapshotProjector重投完整现金/持仓/费用/marks并比较，非新PnL模拟器。
- 核原native component/digest/input/result hash、inline fact、事件ID/fullclock、unique witness、初终Journal/最终Ledger/run-end hash和末日权益。期初后外部现金流拒绝；仅原native资金模型允许同source id、同UTC+phase、同账户、沪深相反等额两腿，不能跨clock抵消。公司行动旧guard继续失败关闭。每点绑定whole snapshot/Journal prefix/mark batch/native inline fact哈希。

**局限仍明确**：原CAS仅留MarketBundleRef、没有market stream，本轮**不造reader、不声称完整Engine cold验证或retention证明**。只从已核完成图/原生财务前缀/声明mark进行DEV净值投影；原retention/source/fee限制保持。收盘估值时点不是provider发布时间，9/29日线假设不再列开发阻塞。来源/真实费税/交易/部署/Validation资格均false。

**实际验证**：
- 先public ABI/Profile红灯，再新合成2股/空目标/合法15:00收盘/CNY100000 public prepare小样；0收益/0回撤独立literal通过，分析阶段Engine.run强制fail，derive/公开冷load幂等。fixture实际Aug25，effective_time字段按public dataclass修正；conftest仅禁网，不改Root包来源。
- 新owner **32个不同检查最终通过**：surface/完整小样、4 worked peak/舍入、8 value/clock/grade、7 source/ref缺失或合法重hash替换、旧接口隔离、7冷篡改/源丢失、caller权益/未核证完成值、2外部资本/跨clock转资优先级。新Root消费者 **5 passed / 0.54s**，namespace无fallback/缺原CAS不暗建/metadata仅定位input/输出隔离/public-only守卫。3旧metric ref/收益舍入/stored v1 golden **3 passed / 0.51s**；5个changed source/test/driver新鲜Pyright0。
- 具体修正：tuple/list policy按canonical bytes比较；Ledger.state_hash是派生属性，复用GenericLedger核整Ledger；Repository旧ports reader未export，改直取同一protocol。没有放宽来源/hash/日期/grade守卫。
- 小样与拒绝通过才固定A≤64MiB原图，A成功后B同路径；各10点、原return/fills/publication/execution hash不变、derive同ref。新独立Root进程只凭NAV ref再source重投两臂，3旧golden过；原Engine/旧Analysis值/旧Runtime/verified完成值/sole input8 decoder共5文件SHA与本轮前一致。14包metadata、Root配置/锁与安装后快照一致；Backtest**合法新源码增量**不再称整树未变，无安装。

**文件／证据**：新Root `experiments/analyze_a_share_pharma_daily_nav_development.py`及test，仅读原v1分析CAS、写两新namespace；`research/evidence/a-share-pharma-october-2024-acquisition-20260930/daily-nav-analysis-v1/{A,B}/summary.json`和各`analysis-cas/`。无source复制/回退、owner/sample append、经济run/OOS；两新CAS clock/owner registry空。旧两份summary SHA仍A=`d15fafe3fbd3fef437d6daca8103b5416b237405b76a6d2eea920060e2e7a5cb`、B=`5d18a118bf15a206179102f356553da1155e7a1e7fc6489654d84a621c5defab`，旧Analysis refs/失败根保留。

**NAV后依赖复核／下一安全动作**：实际安装OosRule@1仍拒maximum_drawdown/paired_net_return_difference；新NAV nominal类型尚无accepted成对Research/Validation admission，v0草案不自动转完成。已留Jan费用snapshot只覆盖XSHE/DOMESTIC/ORDINARY_A_SHARE/Jan开发投影，不是Oct真实双市账户费。有限local composition搜索只定位D202专用store和分析CAS，未取回医药ledger/producer/revision/future interval身份；不宣称全局不存在或无人读取，也未reserve。

下一内部写入链由Main冻结新NAV nominal ref成对admission与预留composition的exact owner/consumer/producer/source等价语义后推进，不空造ledger/将已读窗口补记OOS。正式来源、费用和未触碰样本依据分别补齐，不请用户“批准缺证据”。当前没有需重复批准的开发/NAV/假设门；若后续必须新增认证批次或真实账户/成本范围，先提交具体范围、attempts/时限/MiB/停止条件与实际资料选项再等人类决定。本轮0新认证请求。
