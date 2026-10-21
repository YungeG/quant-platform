# VF5-P1：前瞻性参考编排收益核验提案 v1

**PROPOSED / PLAN_ONLY / NOT_EXECUTED。**

原生选择`decision-57e92cac-6bd9-4a6a-952f-4a9f7f88bdda`、control`3c816c5c`仅要求Main准备新有限提案；不授执行权。本轮未运行测试、模型、网络或真实源，也不修改旧任务完成数。

## 1. 问题与结论边界

问题只问：**在当前冻结版本及同一受控参考执行器下，分开执行S/P/C与合并执行P/C，能否在不缺覆盖的前提下减少进程启动和重复测试实例；单次耗时分别是多少？**

这不是恢复旧B0。旧B0只有人工必需覆盖清单，缺原操作者实际调度、耗时、等待与介入记录；部分旧临时证据现已丢失，不能补造。原VF5历史改善门继续`NOT_ESTABLISHED`，即使本提案以后成功也不自动改写它。

若只需确认集合关系，已有静态证据足以说明S包含于P，不必执行本提案。只有需要一份**新的前瞻性实测参考样本**时才值得批准。结果不能证明整体研发交付变快、人工往返减少、所有改动均获益或策略/研究有效。

## 2. 最小范围与前提

- 只用现有已审fake夹具，不为产生差异修改生产代码或测试；不新增依赖、API、缓存、队列、通用执行框架。
- 唯一执行者Main。未来写集仅新独占运行目录的固定benchmark harness、日志/报告与本提案/原计划状态；不改`tools/validate_change.py`、`tools/validation_offline_pc.py`、Core/SDK或任何既有测试。
- 项目根固定`/home/ygguo/agent-projs/ai-crypt/platform`，项目Python `-I -B`；同一五键干净环境、同一guard、46个已知项目模块与配置前后实际字节、同一13项依赖元数据资格。元数据不是完整安装代码认证，audit不是OS沙箱，前后hash不识别中途改后还原。
- 每个child独占空pycache前缀、禁写字节码，tempfile/basetemp只在该child夹具目录；不清OS page cache，不假定热/冷机器状态相同。三个BLAS环境变量为1只是请求，不是实测线程数。
- 本次只读准备核过下表字节与13项发行包版本，未导入第三方业务模块。真正执行前还必须重核；任一资格/源码/依赖变化先阻断，不自动刷新hash。

| 固定输入 | SHA256 |
| --- | --- |
| [执行入口](../../tools/validate_change.py) | `326da060e95bb12d45f29952716e200f2a2b5c5a1833f8f45ed99f456b3cadf8` |
| [受控P/C helper](../../tools/validation_offline_pc.py) | `e26e50e05efc92b2bded24c8d4d0f195036da7fac51683e54d5bd6206d4708b5` |
| [proxy fake集](../../tests/research/test_a_share_ingestion_proxy.py) | `e74298c88d9e0ec2088a86ba6a374664c266c173ef3ce574e7842d838966c2ba` |
| [capture fake集](../../tests/research/test_a_share_retro_capture_v1.py) | `8b8f6f812abc574c48eb1bc610b13e0ef62c4bb6ddf3f3c369679e51564b66fc` |
| [research conftest](../../tests/research/conftest.py) | `385b36bb23043a5d5439287f52f130ebd7289a6eda5add3be8c182d54d2a3456` |
| [pyproject](../../pyproject.toml) / [lock](../../uv.lock) | `c33c31e91a80ca5c56b1b5ccf1356c18dd8deff28ca07a0605a15448182e0aab` / `77e015a4b69f4bce62f61170dc80201a0abee51fd2b4e507819cfd0f4d8a3e5f` |

## 3. 前瞻性执行方式

A和B使用**同一个新冻结的临时参考harness**，只改变以下选择与分组；不把A假称历史操作者流程。B也不是对生产公开CLI总耗时的直接测量，不能把临时harness计时改标签成公开入口计时。

| 顺序 | 方式/child | 精确目标 | 预计实例数（执行时须核实） |
| --- | --- | --- | --- |
| 1 | A-S，兼作同路径最小smoke | proxy文件的`test_unapproved_endpoint_rejected`、`test_failure_redacted_no_retry_no_failover_no_refund`、`test_capture_retains_exact_safe_bytes_without_pandas_or_second_request`全部参数例 | 4＋4＋1＝9 |
| 2 | A-P | 完整`tests/research/test_a_share_ingestion_proxy.py` | 57 |
| 3 | A-C | 完整`tests/research/test_a_share_retro_capture_v1.py` | 41 |
| 4 | B-PC | 上述两个完整文件，同一child执行 | 98 |

A-S必须先完成并核实环境/guard/报告/身份，再允许后续child；它本身就是预先冻结的A组成部分，不事后挑选，也不为smoke再加一次。任何失败立即停止剩余项，不重试、不换根；不补跑直到“更快”。单组A→B顺序有暖缓存/顺序偏差，故耗时只描述这一对，不做统计或因果推广。若以后要平衡顺序/多重复，需另一个明确提案，不使用本预算。

所有child共用固定pytest参数：项目配置、research confcutdir、禁插件自动加载与cacheprovider、`-q`、独占basetemp；只有表中固定node集合不同。不得接受任意node、shell或caller“合格”布尔值。

### 共用接缝与独立报告

- 复用既有`run_process()`的真实exit、拥有的进程组清理、first-stop与限时/限日志；显式记录同一Popen env和安全child前后读回。
- 复用helper的`Guard`、`module_paths`、`Reader`、`observed_env/valid_env`及有界元数据读取逻辑。完整共同输入清单在每个child之前/之后取实际身份；之后新增项目模块不能用post-only hash补before。
- 每个child使用位于自身独占子树内的固定bootstrap/harness同hash副本；这些代码虽位于工作目录，仍显式纳入before/after输入，不能因“output”规则排除。这样无需放宽现有guard去读取未知外部harness路径。
- 不改helper的`FILES`、`COVERS`或98项production gate，不monkeypatch其child_main/coverage阈值。新harness仅有S/P/C/PC四个固定私有mode，用单独`benchmark-arm-v1`报告验证各臂的准确集合/数量。
- 共同输入bundle从当前输入文件、runtime/依赖/环境事实显式组成，单独绑定benchmark harness/selector/argv；不把helper中98项profile contract原样冒充9/57/41项契约。
- 每个收集node唯一，setup/call/teardown均恰一组passed；任何skip/xfail/xpass、deselect、空集、缺/重复报告、guard意外事件、日志截断、身份或环境变化均令样本无效。
- artifact_kind为`validation_benchmark_sample`，可记`sample_valid`，但不产生生产validation PASS、正式研究报告、publication或TaskSupervisor验收回执；`reuse_allowed=false`。

## 4. 三类选择只核安全性，不扩大收益主张

额外最多3次纯plan CLI，沿用原同样例：

1. `docs/notes/example.md` / informational → D，预期exit3。
2. `experiments/a_share_ingestion/proxy.py` / local → S/P/C，预期exit3。
3. `experiments/a_share_ingestion/retro_capture_v1.py` / public → S/P/C/N，N保持BLOCKED，预期exit2。

它们不执行数学、资源或业务检查；只核义务缺失0、未知/依赖/fixture/规范文档不降级。D和public/N没有成对执行收益测量，不得据此声称三类总体收益已验证。

## 5. 未来申请的有限资源（本轮均未执行）

| 项目 | 上限 |
| --- | --- |
| 实际pytest child | **4次**，即A-S/A-P/A-C/B-PC；无额外smoke、重复、修补重跑或旧额度结转 |
| 每pytest child | 45秒；stdout/stderr合计1MiB；child报告512KiB |
| 纯plan CLI | 3次，各10秒/日志256KiB；不计为目标测试执行，但纳入总进程与时限账 |
| 总执行窗 | 240秒，含必要关闭预留20秒；达到任何帽不能记样本有效 |
| 每child身份快照 | 单文件2MiB、累计32MiB；不读真实原件/凭据/旧journal |
| 临时＋持久新产物观测量 | 合计32MiB，持久证据最多12MiB；这是受控观测上限，不是OS强配额 |
| 网络、凭据、真实源/DB、模型/拟合/native、安装/重载 | **0** |
| 生产/测试/SDK源码、依赖/lock、settings、git stage/commit/push | **0变更** |

全部旧Source/资格/cold额度继续封账，不从本提案获得退款或第三次cold；本提案也不改已配置的Supervisor包、当前内存版本或原任务板。

## 6. 指标、验收与停止

- **覆盖完整性：** A三臂并集必须等于B集合，预期98唯一node，缺失/额外唯一node均0。S三组实际4/4/1且为P子集；若实际集合不符，直接无效，不修改基线迎合结果。
- **主要收益：** 实际A调用3个child、合计107实例；B1个child、98唯一实例。只有实际报告支持才记“这份前瞻参考编排减少2次启动/9次重复实例”。不是历史改善。
- **次要耗时：** 各child单调时钟时长、A串行总墙钟、B墙钟及各自包装开销分别记录；嵌套时长不重复求和。只给本对原始数值/差值，两个顺序未平衡，不给总体提速结论、统计显著性或年化节省。
- **人工与外部等待：** 若没有直接记录则UNKNOWN，不填0；自动化样本不证明人工干预减少。开发harness、诊断、审批和本次规划成本另列，不混入稳态child时长。
- **失败优先级：** 原SIGINT/SIGTERM/timeout/loglimit优先；原进程exit/原因保留，报告/身份/打包错误不能覆盖。失败、未执行与关闭都留证；未满足条件不算有效，无法关闭也明确失败。
- **终态：** `VALID_REFERENCE_SAMPLE`仅表示本方法/版本下样本有效；`INCOMPLETE`/`INVALID`/`NO_TIMING_GAIN_OBSERVED`都允许如实交付，不为PASS改门槛。旧VF5历史改善仍未建立，D009科学问题仍未回答。

## 7. 留证与后续权限

新运行若获批，使用全新/tmp工作根；同步持久保存白名单harness源码、授权/执行卡、身份、四臂process/report/log、三份plan结果、attempts及最终对照，拟目录：

`/home/ygguo/.local/state/ai-crypt/validation-flow/vf5p1/<EXCLUSIVE_RUN_ID>/`

目录0700、文件0600，逐文件hash/fsync/readback；不归档fixture/raw假token或缓存，不读取其他配置/原会话。缺证据不靠文档hash补PASS，不重建丢失的历史日志。实际持久新目录/文件创建及上述测试都必须在下一次明确执行授权范围内。

本轮只读准备位置`/tmp/platform-vf5p1-prep-o9yehmqc/`：9份代码/fixture/config身份及13发行包元数据版本匹配；它不是测试或完整安装代码认证。

**下一负责人Main：** 提交此新方法与预算供决定；只有另行批准执行后才实现固定临时harness、先最小臂核定再完成其余臂和文档终核。当前不派writer、不运行harness、不更新原D009 done数。原[修复计划](validation-delivery-flow-repair-v1.md)的历史B0与状态保持原义。
