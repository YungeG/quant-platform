# AR-07/09：默认环境、完整回归与当前阻断

**Backtest完整验收已通过；Platform整体尚未通过。** 真实默认安装暴露14项模型合同冲突及1项历史坐标断言，不能用隔离源码通过或静态review替代它们。合同扩展与远端推送均等待用户明确授权，未启动AR-10。

## 已完成的真实验收

| 范围 | 实际候选/配置 | 结果 |
|---|---|---|
| Backtest集成 | `ea957d59527e93765681d85c7a2f3fd83e6356a0`；同一B源码组合、已有Backtest开发解释器 | **3299 passed、2 skipped，1584.46秒，exit0**；两项原有fixture skip，无deselect |
| Backtest修复半径 | 合并native v2兼容与九项基线修复 | 独立执行**314项focused、176项adjacent**通过；import checker扫描186文件通过 |
| 旧证据保留 | 全套后父独立检查9779个原条目/7292文件，117183604字节 | 原bytes/mode/symlink状态全相等；唯一新增protected fixture为精确历史日历源，SHA仍`0382ec…9532` |
| 默认安装cohort | root `42e4e1f`，五个Backtest包均不可变Git `ea957d5`；gitlink、lock、PEP610及site-packages导入一致 | **不使用PYTHONPATH**的安装/公开prepare入口、alignment/seam小样通过；不是源码覆盖诊断 |
| SDK绑定v2 | root `083fd668`及父测试加强；保留原V1映射，当前三项Validation源pin按已接受代码重新绑定 | 父**120项**（含原98项及新负测/历史坐标/alignment）通过 |
| 较宽catalog相邻诊断 | 原缺duckdb产生39失败，保留原日志；声明既有代码已强制的`duckdb==1.5.4`后，先1项合成DB小样再扩展 | 父**153 passed，24.00秒**；没有实际数据或供应商操作 |
| validator自身与profile | 显式`offline-pc-inputs-v2`，保留PINS_V1和三项原98测试源hash；父新负测先RED后GREEN | **142项validator测试通过；标准self PASS（5项），标准offline-pc PASS（98项）** |
| fresh审查 | AR07版本/SDK/history、AR09跨模块fix radius | 无新P1/P2；reviewer仅静态查阅，不声称执行过父测试，也不关闭尚失败的完整门 |

上述批次有重叠，不能合计成独立用例总量。所有完整失败日志、usage/collection/缺依赖失败和后续纠正均保留。

第一轮Backtest完整候选`6ce79d6d`的3245通过/11失败/2跳过不是“已知失败豁免”：两项本轮native受保护源回归和九项基线失败已实际修复，后续一次完整新候选3299/2通过。legacy Binance v1源与原签名恢复原字节；准确响应后取时是明确v2入口，旧CLI未被宣称修好。

## 环境与资格边界

- 五个Backtest包都由Git构建安装，workspace四库来自root已接受gitlinks。首个Domain真实构建/导入小样及不存在Git object失败小样均执行；再安装整个候选环境，检查所有origin与PEP610。
- 初始代码取得使用**进程级本地Git URL重写桥接**（不改global Git配置），之后默认环境从确切缓存对象`uv sync --locked --offline`。这证明本机对象/安装组合，**不证明远端可达或干净远端clone可交付**。
- 确认没有旧默认解释器进程后，原`.venv`被保留在`/home/ygguo/.cache/platform-ar20261022/original-platform-venv`，另建正常位置的新默认`.venv`；不是搬动带失效shebang的候选venv。Backtest开发`.venv`未修改。
- 标准offline-pc第一次输出放到`/srv`，被既有guard拒绝，exit1及只读诊断保留。根因是**操作路径不符合既有禁止/srv的合同**，未改guard；改用`/home/ygguo/.cache/platform-ar20261022/qualification/offline-pc-v3`后标准98项通过。原报告路径不重写，7份精确证据副本及copy-manifest归档到执行目录。
- SDK新绑定只改变三项已接受Validation代码身份，原七项V1事实仍保留。身份guard无I/O/clock；154579字节源码仍在256KiB上界内，捕获/目录程序本来就把ledger绑定到同一个Foundation。没有增加物理I/O、分布式隔离或真实source授权保证。
- offline profile的固定98项测试和guard合同不变；新版资格明确区分新pyproject/lock。额外DuckDB是现有合成catalog测试依赖，不授予PC原生数据库/行情/模型权限。

## Platform默认全套失败：合同冲突，不得伪修

冻结root `42e4e1f99b5dfda8b6983f240866c8edd29c11ff`、真实新默认环境、无PYTHONPATH，实际完成：**1263 passed、15 failed，217.75秒，exit1**。源码/环境/git状态未变。

- **14项：** 旧模型fixture训练区间[0,1000)ns，模型到1000ns/phase70才可用，却借用100ns目标。Backtest新增时间守卫正确拒绝`MODEL_ARTIFACT_UNAVAILABLE`。
- **1项：** V3旧断言把历史Promotion `8e6ddd…`强制当当前HEAD。父以`5590438`保留历史SHA并验证到当前严格gitlink的祖先关系；该模块**2项定测通过**。此后完整architecture目录加Research model-build-core **72 passed，1.68秒**。这些不是整个默认套件重跑通过。

只把模型目标改到2100ns也无法诚实修复完整模型链：

1. 冻结v2合同与Research `ExperimentSpec`强制训练slice必须属于Experiment.data_slices；所有slice都会展开Trial全集。
2. 训练metadata又必须精确等于训练slice端点。不能把模型available/training_end倒填到目标之前，也不能在旧slice标签下运行区间外的市场数据。
3. 加后续slice会形成8个Trials/18个tasks，其中4个训练区间Trials正确准备失败。但现有model seam一次prepare全部Trials，异常发生在真实request/ref产生前，没有公开的逐trial准备失败变体；不能伪造ref或私写target-only失败map。
4. 模型OOS现有声明的2026年区间与纳秒级合成执行时钟也不一致；将来设计必须显式对齐，不能只取得rejected报告就宣称OOS来源诚实。

主控与只读readiness均确认**NOT_READY**。建议经过单独授权追加新版模型合同，分开训练声明与评估集合，仍保留两类样本的事前预约、确切task全集与失败。没有擅自删除旧membership检查、增加schema、改旧合同/凭证或让production降级迁就fixture。

## 剩余责任与授权

- **用户决定：** 是否授权新版模型合同的范围扩展；以及是否授权四个leaf整改分支和Platform集成分支推送。子仓库远端main不在请求范围内。
- **主控后续：** 获得前者才设计/复核版本合同及实现对应合法新fixture；获得后者才推leaf、核实确切提交可达，再完成干净组合与root交付。当前本地draft引用不是已发布版本；未推送本轮任何提交。
- **不可提前关闭：** 模型全链、默认全套重跑、远端可达/干净组合及最终交付。旧模型链负例不能通过假请求、改日期或删test掩盖。
- **明确不包含：** AR10真实策略/供应商数据、未污染OOS、金融有效性、Shadow/Live。

执行材料根：`/srv/bcache-8t/ygguo/quant/platform-remediation-20261022/`。主要证据为`backtest-full-suite-v2.log`、`backtest-fanin-parent-byteproof-v2.json`、`ar07-default-origins.json`、`ar07-official-qualification-records/`、`root-default-full-suite.log`及`root-model-fixture-readiness.md`。当前可变状态只由roadmap维护，本记录是已发生操作与失败事实。
