# KORUUST 策略开发：最小续接实施计划

> 归档说明（2026-09-22）：本文保留原派发/续接时的提案、失败与未决项，不是新的实施或实验批准。旧基线、工作树状态、权限和测试数字只描述各自记录的阶段；依赖切换后的基线见[对齐记录](../../implementation/dependency-alignment-20260921.md)，早期 pin 不一致不再是当前阻塞。同级工作树引用仅为历史本地路径，不随本仓库发布，本次未进入这些工作树复验。标的/接口的后续评审以[Native 接入提案](koruusdt-native-analysis-admission-plan.md)为线索；不能把后续记录倒写成旧阶段已获授权，也不能因归档跳过原独立批准门。

- 日期：2026-09-11；卡片：#4；阶段：PLAN。
- 状态：**plan-only；实施方案，不是已批准、可执行的研究预注册**。
- 本阶段只新增本文；不改代码、不更新依赖、不读取市场原始数据、不运行实验或接触留出集。

## 1. 目标、市场与范围

卡片只给出“KORUUST 策略开发”。仓库的[数据清单](../../overall/research-data-inventory.md)指向已有 `platform-koru-research/research/koruusdt/` 工作区，但尚无用户确认二者是同一标的。

**待确认假设：KORUUST 指 Binance USD-M 的 KORUUSDT（TRADIFI_PERPETUAL、USDT 结算）**，不是普通币本位/USDT 永续，也不是直接买卖美国 KORU ETF。不得静默改名或把 `TRADIFI_PERPETUAL` 降为 `PERPETUAL`。若该假设不成立，停止本方案的依赖步骤，重新明确标的与市场。

建议目标：续接现有 Premium 均值回归研究，打通“已发布数据权威 → 四组封存策略 → Backtest → Research 选优”的最小公开路径；条件满足后再单独审批 OOS。

非目标：重做回测器、扩展通用策略框架、迁移整个平台、重新优化已拒绝的 range-fade、一次执行四个策略族、接入新行情源、Shadow/Live/交易账户或自动下单。

## 2. 已核实的基线与能力判断

路径约定：`P` 为当前 `platform/`，`K` 为同级 `platform-koru-research/`。下文未来代码改动均相对 **经批准的 K 隔离工作树**，不是在 P 中直接新增一套副本。

续接复核范围：当前派发仍限定 P。本轮只核对 P 内保留的 Git 对象、当前公开入口和 GitHub Issue；没有访问 K 工作树或重新打开正式 authority。下表 K 的检出及未提交状态是原计划记录，不是本轮重新核验。P 内缺少 KORU runner、Preflight V2 模块/测试和 V4 preparation，不能直接执行本文的 K 测试命令。

| 事项 | 本次核查结果与影响 |
| --- | --- |
| 卡片目录 | `space_cwd` 已是 P；旧的多 cwd 报错不再是当前阻塞。 |
| P 基线 | HEAD `e802d8907770d42943a1d32dfe33ae802d480d27`；依赖锁定 Backtest `f73d068d24ffb7ecc0b7d78194fcbc96908d3c04`，实际子模块为 `93d8a391c9e206588c3312b44dfae2b258f09539`，不可把脏检出当锁定能力。 |
| K 基线 | HEAD `95a8441af753fbb98b9d88f21e858e0fd663da4a`；Backtest 锁定/检出为 `92925ea50e88dc48f4e818a1c50a3b1404eb20e1`。K 与 P 的 Research/Foundation/Validation 版本也不同。 |
| 工作树 | 两处都有既有修改/未跟踪文件。先记录状态和实际包来源，保留所有修改；禁止 reset、stash、覆盖或整体替换 gitlinks。P 的 v6 能力不能被 K 的旧依赖覆盖。 |
| 旧研究 | `K/research/koruusdt/formal-discovery-result.md` 记载 8 组负收益、`NO_ELIGIBLE_TRIAL`、`holdout_touched:false`。这是保留报告，不是本次重新核验的经济证据或全局未污染证明。 |
| 已有公开能力 | RawBlobSnapshot、BoundaryIndex V3、SourceProjection V3、Economics/Overlay V4、ReaderSet/Preflight V2 已有公开 publish/open 操作；V4 Backtest preparation 也已存在。 |
| 尚缺接入点 | `BinanceUsdmKoruPremiumBacktestOperationsV1` 只接收精确 `KoruPremiumReaderSetV1` 并调用旧 preparation；通用 Directional Operations V3 也走旧路径。不能直接把 ReaderSet V2 交给它们。 |
| 发布状态 | [#52 的 real-02 记录](https://github.com/YungeG/quant-platform/issues/52#issuecomment-5549075684)报告 Boundary V3 已发布，authority 为 `sha256:14c7357cf1ec51b348183b66b7e4d05e70c37ebc190769c260d64388d05cca48`。[#57 后续记录](https://github.com/YungeG/quant-platform/issues/57#issuecomment-5549075839)仍待 SourceProjection V3、Economics/Overlay V4、ReaderSet V2 和顶层 V2 authority 发布；下一阶段需独立授权。本轮未重开上述产物，不把 Issue 记录当作完整链验证，也不直接重跑已报告完成的 Boundary 审计。 |

**能力结论：当前不可直接执行。** P 没有已接受的 KORU 接入口；K 有大部分必要构件，但仍需核验完整权威链、接受 V2/V4 operations 接口，以及确认工作区、实验身份和选择策略。

旧 README/context 中“缺少公开 source constructor”“每次 FICLONE”等描述已落后于代码。以当前公开导出、实现和发布证据为准，不照旧文档重做 RawBlobSnapshot。遵守现有 ADR 的信号/决策/执行/估值分离及来源限定 grade，不以策略脚本覆盖这些边界。

## 3. 有限研究设计草案（需在观察新结果前冻结）

### 假设与参数

假设：KORUUSDT 的 Mark 相对 Index 出现极端溢价/折价后，会在 12 小时内充分收敛，使固定低敞口的反向持仓在既定费用、资金费与执行规则下具有正收益。

复用已封存 Premium 编译器，不在 runner 中另写信号。`premium_bps = 10000 × (mark − index) / index`；正极值做空，负极值做多；收敛、跨零、超时及反向条件的优先级以现有编译器契约为准。

| 固定意图 ID | entry_bps | exit_bps | max_hold_hours | target_exposure | seed |
| --- | ---: | ---: | ---: | ---: | ---: |
| KORU-PRM-01 | 20 | 5 | 12 | 0.25 | 0 |
| KORU-PRM-02 | 30 | 5 | 12 | 0.25 | 0 |
| KORU-PRM-03 | 40 | 5 | 12 | 0.25 | 0 |
| KORU-PRM-04 | 60 | 5 | 12 | 0.25 | 0 |

共同固定项：1h 已完成、同一 revision 的 Mark/Index 精确配对，`flat_when_inside_band=true`；只使用可因果获得的信息。成交使用决策之后下一个合格边界的首个保留 aggTrade，不在观察 bar 上成交，不前向填充，不合成缺失成交。成交价、Mark 风险估值、Index、funding 各归原有 authority。

账户沿用 V4 封存条款：`account-1`、初始 10000 USDT、金额 scale 8、`allocation_fraction=1`；后者不是策略敞口 0.25。费用、滑点、保证金、杠杆及 calendar/unit 条款须逐项绑定已接受 profile，本次未核实其全部数值，禁止假设为零费用或任意杠杆。只请求 `development` grade，不升级为决策级证据。

### 数据范围、身份与预算

| 轴/身份 | 冻结值或执行阻塞 |
| --- | --- |
| InstrumentId | venue `binance_usdm`；stable_key `koru-usdt-tradifi-perpetual`。 |
| Discovery | UTC 半开区间 `[2026-07-15T10:00:00Z, 2026-08-24T11:00:00Z)`，保持拆分/恢复后的既定范围。 |
| Holdout | UTC 半开区间 `[2026-08-24T11:00:00Z, 2026-10-05T00:00:00Z)`，沿用已冻结边界；截至本文日期尚未结束。 |
| 数据 revision | 以重新公开打开且验证通过的 Raw/Boundary/Source/Economics/Overlay/ReaderSet 发布链为准；完整链 ref 尚待封存，是执行阻塞，不可用探索 CSV revision 替代。 |
| 原始快照候选 | 旧 receipt 记录 `sha256:066823d65662a319b60ac2e783f22c034c2b454a44e802a5037f7d39fe7b9e2a`；仅用于定位和重新验证，不代表当前链已获准。 |
| 策略与模板 | 四个 sealed strategy/parameter envelope 与 Backtest 模板身份必须从已验证绑定取得，并建立 Research trial 的可审计映射；不得复用旧 range-fade 身份。 |
| scenario / seed / slice | 恰好 1 个固定 scenario（确切 ref 待批准和封存）× seed `[0]` × 上述 1 个 discovery slice。 |
| metric profile | 沿用 `simple_period_return.fill_count.v1`，`backtest_metric_profile@1`，`sha256:bced4dbef8bbf6e1ec9821ae3b68e8c6ce2bbed953f95fe1214c8e21676dbd6a`；经公开发布/读取确认一致。 |
| 试验预算 | 最多 4 个 discovery 声明、候选最多 1 个；后续 OOS 最多 1 个且单独审批。原全局 12-trial 上限不扩大、不把失败槽位转配给新参数。 |
| 资源预算 | 小 fixture smoke 后再申请固定时限、存储和执行预算；未批准不得运行数百万行处理或全量经济试验。 |

所有组合显式列举，按公开构造器要求规范排序；没有随机补样、连续范围、自适应搜索或结果驱动增参。缺失 scenario/template/封存发布 ref 时，不构造伪造的权威 `ExperimentSpec`。

保留已知 aggTrade 缺口 `[2026-08-24T00:00:00Z, 2026-08-24T06:34:20.640Z)`。**618/611 的边界口径待核，不是已完成的验证。** 618 是原计划记载的完整预期数量；本轮未复验其生成或测试。在 P 保留的 `95a8441` 中，`research/koruusdt/run_public_koru_retained_preflight.py:571–581` 的旧 `_boundaries()` 从 gap audit 的 `events` 取值并要求 611 条；`build_discovery_source_targets_v2.py:640–669` 同时要求 `eligible_boundary_count` 和事件数均为 611，其测试第 59 行也断言 611。因此不能仅凭数字把 611 解释为同一 618 请求的成功子集。#52 的 real-02 记录也报告 611；须在获准的 K 工作区核对实际 request/result、完整预期边界与缺失证据。本轮 P 的子模块对象库不含 K 所锁定的 Backtest `92925ea`、Research `289a9cd`，没有通过替代版本或联网拉取补足验证。

不得删除缺口对应边界来凑数，也不得直接把已发布 611 改成 618。不得下载完整 8 月 24 日归档以“补数据”，它会跨入 11:00 后 holdout。任何已发布 boundary authority 的修复都需要独立批准，并保留原发布的 append-only 历史。

### 选择、拒绝与验证规则

建议为 **Premium 子研究** 明确批准以下窄规则：只接纳公开核验为 `COMPLETED`、grade 为 development、metric profile 匹配的分析；过滤 `trade_count >= 8` 且 `simple_period_return > 0`，按收益降序、交易数降序、`trial_declaration_ref` 升序确定性选至多 1 个候选。

这是待批准的修订，不是既定事实：旧 directional 全局策略按净 PnL、较低 maxDrawdown、slate 次序选优，而现有 metric profile 不提供 maxDrawdown。必须在观察新结果前接受替代规则，或先由指标 owner 补齐能力；不得悄悄改 policy，也不得把四组 Premium 胜者称为全部 12 组的全局胜者。

- 四组都无合格正收益分析：发布 `NO_ELIGIBLE_TRIAL`，拒绝本批候选进入 OOS，不加参数挽救。
- 数据/权威/能力问题：保留 `BLOCKED`、`FAILED`、`CANCELLED`，不折算成零收益或科学否定。
- 候选成立才考虑 OOS：建议 `OosRule(simple_period_return, fraction, gte, threshold="0", min_trade_count=8)`，须另行批准。
- OOS 有效完成且交易充分时，依 Validation 返回 `supported` 或 `rejected`；缺指标/交易不足等按契约为 `inconclusive`，执行或证据完整性错误记录失败/无报告原因，不伪造报告。
- 执行任何数据读取或试验前，先由 Validation 接受对应 sample reservation；检查跨历史实验 ledger，不能用报告中的 `holdout_touched:false` 代替污染核查。

## 4. 顺序实施步骤与最小改动面

### S0 — 确认标的、工作区与授权（后续步骤的前置门）

1. 确认 KORUUST → KORUUSDT、只续接 Premium 四组，不是重新启动旧失败策略。
2. 接受本方案的接口补充范围、研究 policy 修订和预算；分别保留“实现/测试”“预检发布”“Experiment 启动”“OOS”的授权门。
3. 选择经批准的 K 基线及需保留的未提交变更，再建立隔离工作树和匹配依赖；记录各模块 commit、锁文件、实际 import 来源。不得因建了干净工作树而漏掉必需的未提交修复。
4. 先不向 P 合并；若以后需要迁移，另列兼容性/依赖升级计划，不用旧 K gitlinks 覆盖 P 的 v6。

验收：标的、工作区、兼容边界、候选规则和预算均有明确记录；缺一项，只暂停其依赖步骤。

### S1 — 复用公开权威链，先小样本后全量

1. 在原有测试框架内，用最小 fixture 贯通同一 Raw → Boundary V3 → Source V3 → Economics/Overlay V4 → ReaderSet/Preflight V2 路径，包含 official/retained capture 边界及缺口。若生产 scope 不允许缩小，使用原有契约允许的 fixture，不截断真实数据冒充正式发布。
2. 验证成功、超时、缺失发布、篡改、holdout 拒绝和重放；通过后才按预算公开打开候选快照及前驱发布。旧诊断曾处理 6,602,236 行并在 aggregate boundary 阶段超时，不先重跑旧 `--full` 或单纯调大超时。
3. 复用 `publish_koru_premium_preflight_authority_v2` / `open_published_koru_premium_preflight_authority_v2`。缺链时仅在授权范围内经现有 publisher 补齐，不从 dict、任意 reader 或私有对象拼装 authority。
4. 复用 `run_public_koru_retained_preflight.py` 的 `--consume-published-preflight-authority-v2` 与 canonical locator/foundation/repository/receipt roots，确认四个有序绑定及完整 owner-log/artifact spine。
5. 区分“复用已有 receipt”与“本次重新公开打开并验证”；相同 locator 的 receipt replay 不能冒充新核验。`GO_FOR_SEPARATE_EXPERIMENT_LAUNCH_REVIEW` 只允许另行启动评审，不授权运行 Experiment。

最小改动面：原则上复用 `research/koruusdt/run_public_koru_retained_preflight.py`、其 tests 与现有 Research publishers；仅修改确实暴露的缺陷并补回归。不能重写已存在的 durable snapshot 或回退到旧 V1/V2 source 路径。

验收：代表性 smoke 有成功及失败证据；正式预检仅在完整公开链核验通过时给出 launch-review 状态，否则明确阻断且没有假成功 authority。

### S2 — 补齐 Backtest-owned V2/V4 Operations（本次 discovery 的最小接口补充）

拟新增名称 `BinanceUsdmKoruPremiumBacktestOperationsV2`，名称/签名先由 Backtest 接口 owner 接受，不视作现有 API。

- 只接受精确、封存且经 repository 公开打开的 `KoruPremiumReaderSetV2`；固定允许 `KORU-PRM-01..04`，请求仍只包含 `intent_key`。
- 在公开 `prepare` 边界核对意图与策略/参数/reader 绑定，再调用现有 `prepare_binance_usdm_tradifi_directional_bar_backtest_v4`。
- 复用现有 prepared-trial、run_prepared、terminal/evidence/analysis 协议；由 Backtest 生成 request/input/run 身份及全部经济结果，Research 不重算 hash、PnL、费用或 grade。
- 新增而不改写 V1/V3 的接受类型、语义或身份；拒绝 V1/V2 交叉混用、错配 overlay、任意替代 reader 及未接受 seed。不得 monkeypatch 私有实现或新增通用回调注册框架。

预计文件：`backtest/packages/backtest-runtime/src/crypto_quant_backtest/binance_usdm_tradifi_operations.py`、同目录 `__init__.py`、`backtest/tests/runtime/providers/` 下相应新/既有测试。跨包消费者仅从 `crypto_quant_backtest` 等公开根导入，不导入私有 facade/runner/composition。

验收：四种意图均能经 V4 生成合规 prepared execution；拒绝错配和篡改；旧 V1/V3 测试仍通过，原语义 identity 不变。

### S3 — 增加薄 Premium 研究入口，不复制旧 runner

1. 新建 `research/koruusdt/run_premium_discovery_v1.py` 及相邻测试，使用公开 `IntegratedExperimentSpec`、`FrozenExperimentInputs`、`DeferredTrialExecution` 和 `execute_experiment()`；不改旧八组 range-fade 的脚本/状态。
2. 封存第 3 节全部轴及 ref、策略身份映射、selection policy 和样本 ledger，再单独取得 Experiment 启动批准。
3. 使用独立 `research/koruusdt/data/premium_discovery_v1/` 产物命名空间；闭合确切四个 trial 的 manifest，保留失败项；只从已核验完成的 Backtest publication 派生分析。
4. 输出 Experiment/Manifest/Family/Candidate 或 NoSelection 的公开 refs、成本/风险限制和失败原因。重放使用既有证据，不再次经济运行、不刷新治理时间；不手工挑赢家。

验收：声明精确四组，结果状态完整且选择可复现；新 runner 不包含第二套信号、撮合、账户、指标或证据校验实现。

### S4 — 单独评审 OOS 能力与时间门，不自动开始

当前 KORU 公开 authority/目标编译契约绑定 discovery scope；不能因 V4 存在就假设它接受 holdout 日期。须先接受 OOS scope/preparation/target materialization 的公开能力，缺失时另立小方案，不在此扩大通用接口。

至少等到 `2026-10-05T00:00:00Z` 区间结束、数据可冻结、污染核查和 sample reservation 通过，且存在合法候选并取得 OOS 批准后，才运行一个验证 case。保持原 holdout，不提前看曲线、不移动日期，不把已看过的历史重新标成“未见”。由 `validate_candidate()` 给出报告或明确无报告原因；任何 backtest/validation 结果均不授权部署。

## 5. 验证顺序与完成标准

**本 PLAN 的验证**：只检查本文、源路径、链接、改动范围和文档诊断；没有执行下面的代码测试、正式预检、研究或 OOS，不报告收益结论。

未来实现时，先对改动文件运行 LSP diagnostics，再使用匹配锁定包的 Python/uv 环境。先单文件/小 fixture，成功后逐级扩展，不能用全量真实数据发现普通导入或 schema 错误。

在批准的 K 工作树中，首个代表性测试命令：

```bash
uv run --frozen --offline pytest -q research-platform/tests/test_koru_premium_preflight_authority_v2.py
```

若离线依赖不齐，报告环境阻塞；不要取消锁定、静默联网或运行替代版本。随后按改动范围运行现有测试：

| 范围 | K 相对测试路径与检查 |
| --- | --- |
| 权威链/预检 | `research/koruusdt/tests/test_run_public_koru_retained_preflight.py`；`research-platform/tests/test_koru_source_projection_publication_v3.py`；`research-platform/tests/test_koru_boundary_index_publication.py`。核验 owner-log、缺前驱、篡改、超时无假成功、完整边界覆盖（618/611 口径差异须先解决）和 holdout 门。 |
| 数据与编译 | `backtest/tests/bundle_builder/providers/binance_usdm/test_koru_aggtrade_boundary_index_v3.py`、`test_koru_tradifi_source_projection_v3.py`、`test_koru_tradifi_builder_v4.py`、`test_koru_directional_target_compiler_v1.py`。覆盖溢价正负/阈值/平仓优先级、因果时点与缺口，不改变经济契约。 |
| V4 接入 | `backtest/tests/runtime/providers/test_binance_usdm_tradifi_directional_preparation_v4.py`；新增 Operations V2 测试覆盖四意图、错类型/错绑定、tamper、seed 和旧接口兼容。 |
| 跨层与架构 | `backtest/tests/architecture/test_koru_tradifi_builder_v4_boundary.py`；`tests/integration/test_koru_research_public_execution.py` 保持通过，并给新 runner 添加真实公开 preparation→execution→analysis→selection/replay 小 fixture。 |
| 未来 P 合并 | 仅在另行批准迁移后，加入 P 的 `tests/integration/test_integration_v6.py` 等受影响集成/架构测试；不是直接降低版本后宣称通过。 |

开发阶段完成标准：公开接口接受、相同生产代码路径的小样本成功与失败覆盖、相关测试通过、四组不可变实验封存、发布链可重开、未触碰 holdout。若仅完成实现/预检而未批准研究运行，交付状态必须是“实现完成/待启动评审”，不能写“策略已验证有效”。

## 6. 证据入口与下一步

- 研究设计：`K/research/koruusdt/directional-discovery-plan-v1.md`、`K/docs/experiments/koru_directional_discovery_capability_contract_v1.md`。这些是同级工作区的本地证据路径，不是 P 内文档；其中旧能力缺口须与当前代码交叉核对。
- 公开链：Research exports（历史本地路径：`../../../platform-koru-research/research-platform/src/crypto_quant_research/__init__.py`）、Preflight V2 publisher/open（历史本地路径：`../../../platform-koru-research/research-platform/src/crypto_quant_research/koru_premium_preflight_authority_v2.py`）、retained preflight CLI（历史本地路径：`../../../platform-koru-research/research/koruusdt/run_public_koru_retained_preflight.py`）。
- 关键接入差距：现有 Operations V1/V3（历史本地路径：`../../../platform-koru-research/backtest/packages/backtest-runtime/src/crypto_quant_backtest/binance_usdm_tradifi_operations.py`）、已有 preparation V4（历史本地路径：`../../../platform-koru-research/backtest/packages/backtest-runtime/src/crypto_quant_backtest/binance_usdm_tradifi_directional_preparation_v4.py`）。

**下一步需要确认**：① KORUUST 是否就是 KORUUSDT；② 是否在保留既有变更的 K 隔离工作树续接；③ 是否接受四组 Premium 子研究及上述选择规则修订。确认前可评审本文，不能启动代码改动、数据发布或实验。确认及实施批准也不替代后续 Experiment/OOS 的独立授权。
