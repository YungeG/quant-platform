# KORUUSDT：Native Analysis / Research 最小接入提案

> 归档说明（2026-09-22）：本文保留原派发/续接时的提案、失败与未决项，不是新的实施或实验批准。旧基线、工作树状态、权限和测试数字只描述各自记录的阶段；依赖切换后的基线见[对齐记录](../../implementation/dependency-alignment-20260921.md)，早期 pin 不一致不再是当前阻塞。同级工作树引用仅为历史本地路径，不随本仓库发布，本次未进入这些工作树复验。标的/接口的后续评审以[Native 接入提案](koruusdt-native-analysis-admission-plan.md)为线索；不能把后续记录倒写成旧阶段已获授权，也不能因归档跳过原独立批准门。

- 状态：**PROPOSED / 设计评审稿，非已接受接口，非实验启动批准**。
- 原提案轮次：`0f073cde-daf3-4c29-ad65-6f9f4730e52a`；第 2–7 节的源码与测试记录属于该轮次，续接核查见第 8 节。
- 标的已明确为 Binance USD-M `KORUUSDT / TRADIFI_PERPETUAL`。原提案记录的目录切换授权不扩展到本次派发；续接 RUN `4090ce87-6fb4-4572-b601-7149d9eacf42` 仅限 `/home/ygguo/agent-projs/ai-crypt/platform`。
- 评审交付范围：追踪接入链、运行无行情契约检查、提出有限实现范围。不改产品代码、不发布真实 authority、不运行正式 Experiment/OOS。

## 1. 结论与建议

**不能只删除 `UNSUPPORTED_NATIVE_ANALYSIS`。** 现有 native 分支可以描述完成/失败证据，但上游 Preflight、分析、Research 端口、终态和候选消费尚未形成同一可接受协议。

建议下一实施阶段先做 **B1：Backtest-owned native analysis**；通过独立的合成证据验收后，再做 **R1：明确版本的 Research admission**。两阶段不改变 CompilerV2/V3、撮合、资金费、账户、风险或 native 的 no-action 判定，也不把 native 路线视为已获准的真实缺口补救。

这是一份待接受的具体接入方案，不是为了在缺证据处强行得到收益。若 native 经济语义及其基础实现尚未被接受，应先明确其依据；代码存在、旧测试通过和本方案均不能代替批准。

## 2. 基线与已核实的缺口

原提案的路径约定与历史基线（均位于 `/home/ygguo/agent-projs/ai-crypt/`；当前 P 基线以第 8 节为准）：

| 代号 | 工作区 | 作用/状态 |
| --- | --- | --- |
| P | `platform` | 本文所在；HEAD `e802d890`，现有 v6 能力不能被旧依赖覆盖。 |
| C | `platform-koru-card4-execute` | HEAD `95a8441`，已有未提交的 ReaderSetV2/V4 Premium runner；不是 native runner。 |
| N | `backtest-koru-native-implementation-01` | HEAD `92925ea`，分支 `impl/koru-native-implementation-01`；native 实现在大量未提交文件中，HEAD 不足以标识完整候选。 |

所有已有改动必须保留。实施冻结还需记录实际源码来源、相关文件/差异摘要与匹配依赖；不能仅记录 commit 后忽略未提交代码。

| 层 | 当前源码证据 | 接入要求 |
| --- | --- | --- |
| 公开 operations 名称 | C 的 `BinanceUsdmKoruPremiumBacktestOperationsV2` 接受 ReaderSetV2/V4；N 的同名类接受 ReaderSetV3/V5。 | 同名不能视为兼容；合并时不得静默覆盖导出。 |
| Native 完成证据 | `BacktestCanonicalPublicationRefV3` → `load_completed_v4()` → `VerifiedCompletedPublicationV4`。 | 不降格为旧 publication ref，不手工构造 verified wrapper。 |
| Native 非完成证据 | `NativeAttemptTerminalRefV1` → `load_native_terminal_v1()`，保持 FAILED/BLOCKED/CANCELLED。 | 不解包成旧裸 ArtifactRef 来欺骗终态分派。 |
| 分析 | `BacktestAnalysisRuntime.derive()` 精确接受旧 verified 类型，不接受 V4；native operations 的 `derive()` 显式拒绝。 | 新增版本化分析路径，保留旧 derive 的接受集合/语义。 |
| Research 端口 | `_require_backtest()` 要求 `load_analysis`；native operations 当前没有它。 | 仅解除 derive 的拒绝，仍无法通过 Research 的入口检查。 |
| Research ref / observation | 当前 ref 表只接受 completed/analysis 1、2；终态识别只接受裸 ArtifactRef；完成 observation 也有精确字段集合。 | 必须同时处理版本分派、字段、witness、重放和失败映射，不能只加一项 ref 字符串。 |
| 上游 authority | Research PreflightV2 精确要求 ReaderSetV2，不能直接装入 native ReaderSetV3/OverlayV5。 | Native 研究需要独立、可公开重开的上游发布契约。 |
| 候选与下游 | C 只发布 Candidate@1/@2；P 已将 Candidate@3 用于 target materialization。Validation 当前也只接收旧 completed/analysis refs。 | 不占用已有 @3 身份；native 候选版本需跨模块分配。Validation/Promotion 暂时保持拒绝。 |

源码入口：

- N operations（历史本地路径：`../../../backtest-koru-native-implementation-01/packages/backtest-runtime/src/crypto_quant_backtest/binance_usdm_koru_premium_operations_v2.py`）：类型、单次消费、完成/终态记录、显式拒绝。
- N verified views（历史本地路径：`../../../backtest-koru-native-implementation-01/packages/backtest-runtime/src/crypto_quant_backtest/verified_publications.py`）：V4 提供 starting/final snapshot、initial/final journal、fills、financial coverage、terminal inventory、verified graph hash。
- N analysis runtime（历史本地路径：`../../../backtest-koru-native-implementation-01/packages/backtest-runtime/src/crypto_quant_backtest/analysis_derivation.py`） 与 evidence repository（历史本地路径：`../../../backtest-koru-native-implementation-01/packages/backtest-runtime/src/crypto_quant_backtest/evidence_repository.py`）。
- C Research runtime（历史本地路径：`../../../platform-koru-card4-execute/research-platform/src/crypto_quant_research/runtime.py`） 与 integration（历史本地路径：`../../../platform-koru-card4-execute/research-platform/src/crypto_quant_research/integration.py`）。
- C PreflightV2（历史本地路径：`../../../platform-koru-card4-execute/research-platform/src/crypto_quant_research/koru_premium_preflight_authority_v2.py`）。
- [P candidate 版本分派](../../research-platform/src/crypto_quant_research/runtime.py)：`target_recipe_ref` 对应 Candidate@3。

## 3. B0：先消除契约基线歧义

本轮在 N 的源码环境实跑：

1. `test_derivation_has_one_exact_public_runtime_and_no_storage_framework`：**1 passed / 0.94s**。
2. `test_verified_publication_module_owns_one_minimal_completed_view`、`test_runtime_publishes_the_accepted_opaque_metric_profile_ref`、`test_return_formula_rounding_null_and_decimal_wire_match_frozen_examples`：**1 failed, 2 passed / 1.03s**。

合计 **3 通过、1 失败**，不是全绿。本文自身的 9 个本地链接、4 个测试节点及 whitespace 检查通过；仅本文的主动 LSP 检查为 1 file clean、0 diagnostics，不代表产品代码或全仓 clean。失败位于 analysis boundary test（历史本地路径：`../../../backtest-koru-native-implementation-01/tests/runtime/analysis/test_analysis_derivation_boundary.py`） 的公开类精确白名单断言。

只读 AST 对比 `git show HEAD:.../verified_publications.py` 证明：旧断言遗漏的四个 Research/canonical-journal 视图已经存在于 HEAD；native 增量再新增 `VerifiedCompletedPublicationV4` 和 `VerifiedNativeTerminalPublicationV1`。因此不能把全部失败归因于本轮或仅归因于 native。

B0 的修复需明确：哪些新增视图已获接受、旧类的构造/身份/字节如何继续冻结、新视图必须如何 repository-open。不得删除测试、改成无约束子集断言或把“实际返回类列表”直接当期望值。本轮保留失败，不替接口 owner 作出接受决定。

## 4. B1：Backtest-only 分析扩展（拟议，名称待 owner 接受）

### 4.1 公共接口与身份

建议保留一个 `BacktestAnalysisRuntime`，新增显式 `derive_native_v1(completed, metric_profile_ref)`，而不是扩大旧 `derive()` 的类型接受范围。

拟议类型为 `BacktestAnalysisV3` / `AnalysisArtifactRefV3` / `VerifiedBacktestAnalysisV3`，产物 `backtest_analysis@3`；新增 `BacktestEvidenceRepository.load_analysis_v3()`。**这些是拟议符号，不是已有 API 或已分配的全局版本。** 实施前核对所有受影响分支的 registry、根导出和命名分配。

- 输入只能是经公开 repository 验证、通过 Backtest-owned admission guard 的精确 `VerifiedCompletedPublicationV4`，以及精确接受的 metric profile ref。
- 精确类型检查不等于证据验证：拒绝未接纳/伪造的 wrapper、失配 graph/hash 和 terminal。需要的 admission guard 必须由 Backtest 补齐，不能由 Research 私自拼装或依赖进程信任缓存。
- 分析绑定 native publication ref、execution-result hash、verified-graph hash、metric-profile ref；这些身份与数值共同进入新产物 canonical body。
- grade 从已验证 completion 按现有 `ResultGrade` vocabulary 精确转换/核对，只允许当前 native 的 development；`deployment_authorized` 保持 false。
- loader 必须核验分析 envelope/ref，重新核验源 completion 和各链接，按同一 Backtest-owned 纯投影核对指标。不能因 CAS 可读就信任一个重新 hash 的伪造收益。
- 保留旧 Analysis@1/@2、refs、hashes、失败码及旧 loader 的闭合接受范围；不新增通用 metric registry、第二套 simulator 或跨包私有调用。

### 4.2 指标语义

优先复用 `simple_period_return.fill_count.v1` 的精确口径，但仅在以下等价性通过后保留其旧 ref；若口径发生变化，先另行接受新 metric profile，不能沿用旧 hash。

- 起始/结束权益分别来自 verified `starting_snapshot.equity` / `final_snapshot.equity`，不以现金余额代替净权益。
- 先证明 `initial_journal` 是 `final_journal` 的精确初始前缀，再取新增流水；不得因 prefix 长度相同就认为身份相同。
- 外部现金流仅使用旧 profile 的 CAPITAL_DEPOSITED/WITHDRAWN/TRANSFERRED；Funding/fee/交易现金流属于经济结果，不能再当外部注资扣除。
- 收益保持 `(期末权益 - 期初权益 - 净外部现金流) / 期初权益`，复用当前 Decimal precision、18 位量化、ROUND_HALF_EVEN 和 canonical string 规则。
- 币种不兼容、无法表达的外部流或非正分母按既有 profile 返回 null；身份/证据错误仍是失败，不能伪装为 null 或零。
- `trade_count = len(verified.fills)`，不是订单数、往返次数或获利笔数；部分成交的既定计数语义不变。
- terminal inventory 非空不自动等于失败或“已平仓”；收益使用已核验的最终估值，并保留 native financial coverage/terminal inventory 的实际限制。

B1 完成只意味着 native completion 可以形成可验证的 Backtest analysis；**不表示 Research admission、真实策略候选或 OOS 已完成**。

## 5. R1：Research admission 必须端到端闭合

### 5.1 输入与公开 operations

- 保留 C 的旧 runner 和 V2/V4 operations。建议为 native 后继使用无歧义的 `BinanceUsdmKoruPremiumNativeBacktestOperationsV1` 名称；既有 native 同名 OpsV2 的兼容/退役策略必须由 owner 冻结，不能自动改名或覆盖。
- 后继端口仍只接收固定 `intent_key`，支持 prepare/run、明确的 `load_completed_v4`、`load_native_terminal_v1`、derive、`load_analysis_v3`；不得借旧端口名静默返回另一版本。
- 补齐严格的 native Preflight/OverlayV5/ReaderSetV3 发布与公开 opener。具体 public 名称、artifact schemas 和指定 owner-log 需先冻结；旧 PreflightV2 不扩大接受类型。
- Raw/Boundary/Source/Economics 的原始发布 fact 可在明确兼容规则下复用；不能以路径、裸 dict 或拷贝 CAS 绕过原 owner log。现有 roots 无法被公开核验时，记录阻塞，不自动搬迁/补发。
- 继续使用已接受的 Foundation/sample ledger。native preparation 以及输入的语义打开必须在 discovery reservation 之后；不得新建空 ledger 擦除历史消费。

### 5.2 Research 状态与身份

- 新增封闭的 native ref/record/witness 分支，精确区分 completed-v3、analysis-v3、native-terminal-v1。不能只修改 `_BACKTEST_REF_VARIANTS` 而保留旧的 `else` 分派。
- Native terminal 保持 nominal wrapper、原状态、cause/context 和证据链接；新增版本化 witness/解析能力，不压扁为旧裸 ArtifactRef。
- 拒绝新旧 completion/analysis 交叉配对；检查 source publication、execution hash、graph hash、metric profile、grade 与 trial request 的完整绑定。
- Local/provider/retention/tamper 错误仍是明确 FAILED 或无报告原因；合法 BLOCKED/FAILED/CANCELLED 不进入分析，不以零指标替代。
- 新实验身份明确绑定 native admission 版本和 native Preflight locator；不复用旧 range-fade 或 Premium V2/V4 trial identity。
- 四组参数、seed=0、至多一个候选及确定性 tie-break 不因接入而改变；正式 selection policy 仍需在观察新结果前接受。
- TaskOutcome、Manifest、Candidate 的新增 payload 接受集合和 schema 分配应作为同一协议评审。**P 的 Candidate@3 已占用，不能在 C 的旧基线上复用 @3。** 采用新增候选版本或独立有限 family，由全局 owner 确认，不在本文伪造已分配版本。
- 重放必须重验既有证据并返回同一发布 refs，不重复经济运行、不刷新治理时间；不能靠只记成功的 task manifest 挑赢家。

### 5.3 下游边界

此阶段只到 Research candidate/NoSelection。Validation/Promotion 对 native 新版本继续 fail closed；不把 native candidate 转成旧候选送 OOS，也不声称已有 discovery preparation 能处理 holdout。下游扩展另行接受。

## 6. 最小验收矩阵与顺序

| 阶段 | 必须观察到的行为 | 不足以通过的替代证据 |
| --- | --- | --- |
| B0 | 精确旧类型/身份哨兵保留，新视图有独立闭合契约，当前失败修复 | 删除失败断言或全局扩大接受类型 |
| B1-small | 一个公开构建的 native 完成 fixture → verified V4 →分析→公开 load；同 ref 重放 | 假造 verified 对象、手填收益或只跑导入 |
| B1-values | 非零持仓/Fill、fee、非零 funding、外部现金流/无流、null/舍入；终端库存按真实估值 | 只有全程 flat/零资金费的漂亮结果 |
| B1-reject | 旧 ref、terminal、错 profile、伪造 wrapper、改 metric/hash、丢源证据均明确拒绝 | 把异常吞成零收益 |
| R1-input | native spine 可公开 publish/open，精确四行；跨版本/缺前驱/错 owner log 拒绝 | 把 ReaderSetV3 强行装进 PreflightV2 |
| R1-flow | 预留先于读取；四组结果 exact-cover；合法完成才分析；失败/取消/阻塞保真 | 把任务 closure 当 Backtest completion |
| R1-replay | 相同 refs/日志，不新增 prepare/run/治理时间，篡改后失败 | 仅比较最终收益相等 |
| Compatibility | C 的既有 65 项相关回归及新增版本哨兵；P 的 v6 身份不被占用 | 仅在旧 C 分支通过后宣布全局兼容 |

先做单个代表性 fixture，再扩展上述有限用例；第一次 native 端到端应按有界预算单独测量，不从全量真实数据发现导入/Schema 错误。任何实际 publication/Experiment/OOS 都不包含在本方案验证中。

本轮已运行的检查可复现为（N 工作目录；已有源码 `.venv`，无需 uv sync）：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -B -m pytest -q -p no:cacheprovider \
  tests/runtime/analysis/test_analysis_derivation_boundary.py::test_derivation_has_one_exact_public_runtime_and_no_storage_framework

PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -B -m pytest -q -p no:cacheprovider \
  tests/runtime/analysis/test_analysis_derivation_boundary.py::test_verified_publication_module_owns_one_minimal_completed_view \
  tests/runtime/analysis/test_analysis_derivation_contract.py::test_runtime_publishes_the_accepted_opaque_metric_profile_ref \
  tests/runtime/analysis/test_analysis_derivation_contract.py::test_return_formula_rounding_null_and_decimal_wire_match_frozen_examples
```

## 7. 决策请求与未验证项

**建议先批准 B0/B1 的接口评审及后续小 fixture 实现范围，不批准真实经济运行。** 需确认 native 基础语义的接受依据、无歧义 operations 名称、Analysis/public-ref 版本和 metric profile 等价性标准；B1 通过后再冻结 R1 的上游 authority 与 Research witness/candidate 版本。

- 本轮产品实现、native 完整 public fixture、正式 authority 重开、全仓测试、产品代码 Ruff/LSP、正式预检、真实 Experiment/OOS：**未运行/未完成**。
- 上轮 C 的 65 项定向测试是历史验证，本轮没有重复计为新通过。
- 现有 Source/Economics 接受记录不等于完整 native spine；本轮未重新打开真实链，未生成收益/候选结论。
- 本轮仅新增本文。当前 1 项契约测试失败继续列为失败；新接口尚未实现、尚未验收。

## 8. 当前目录续接：B0/B1 接口与兼容性评审

续接 RUN：`4090ce87-6fb4-4572-b601-7149d9eacf42`。结论仍为 **PROPOSED / NOT IMPLEMENTATION-READY**；用户要求继续不等于接受 native 基础语义、分配新版本或批准跨目录实施。本节只补充本目录可核验的事实，不替代第 3 节 N 的未解除失败。

### 8.1 已更新的 P 基线

核查期间仓库由外部更新至 P `e92d7cf`，Backtest 锁定、gitlink、检出及五个已安装 Git 包均为 `8cc5b874c31c38a6ec7526d1dbf345b93998a39f`；Research 保持 `c06662449a8a13aed5824398b96bd21e889a9fee`。本轮没有实施该升级，详见[依赖切换记录](../../implementation/dependency-alignment-20260921.md)。**前一阶段的 pin/检出不一致阻塞已消除，不能继续列为当前阻塞。**

`git -C backtest diff --name-only 93d8a391..8cc5b874 -- packages tests/runtime/analysis` 无输出。此前在 P 的 `93d8a391` 源码环境运行的四项契约检查为 4 passed；这不是本阶段新运行，更不覆盖 N 的历史失败。

当前根 `.venv` 的 `direct_url.json` 确认 Backtest 为 `8cc5b874`，但公开探针仍找不到 `VerifiedCompletedPublicationV4`、`NativeAttemptTerminalRefV1`、`BacktestAnalysisV3`、`AnalysisArtifactRefV3`、`derive_native_v1`、`load_completed_v4`、`load_analysis_v3`。依赖对齐没有引入 native 能力。

### 8.2 B1 最小拟议改动面

下表是评审定位，不是已分配的公开接口或允许写入的实施清单。跨模块消费者仍只使用公开根导入。

| 当前文件 / 符号 | B1 必须满足的变化与复用限制 |
| --- | --- |
| [analysis_derivation.py](../../backtest/packages/backtest-runtime/src/crypto_quant_backtest/analysis_derivation.py)：`_calculate_simple_period_return`、`BacktestAnalysisRuntime.derive` | 只在 Backtest 内部复用现有 Decimal 纯计算；新增 native 投影不改变旧 `derive` 的精确类型集合。native 流水必须先验证完整初始前缀，再提取资本流；不能直接套用旧的计数切片。 |
| [verified_publications.py](../../backtest/packages/backtest-runtime/src/crypto_quant_backtest/verified_publications.py)：`_VerifiedCompletedEvidenceV3` | 当前闭合图自验可作为内部模式参考，不是 native guard。需依据获接受的 native 图定义绑定与自验；不转成旧 V3、不靠类名、进程缓存或一次性信任标记通过 admission。 |
| [analysis.py](../../backtest/packages/backtest-runtime/src/crypto_quant_backtest/analysis.py)：`BacktestAnalysisV2` 等旧值类型 | 拟新增独立的 V3 分析、ref、verified 值，绑定 native publication、execution hash、verified-graph hash、profile、grade 和指标。旧 canonical body、构造与身份不变；新版本仍待全局分配。 |
| [evidence_repository.py](../../backtest/packages/backtest-runtime/src/crypto_quant_backtest/evidence_repository.py)：`load_analysis_v2`、`_load_analysis_v2`、schema 注册 | 拟新增精确版本 decoder / `load_analysis_v3`；重开源 completion 并核对完整链接，再使用同一 Backtest-owned 纯投影重算、逐项比较指标。不能照搬仅验证链接的旧 loader。 |
| [公开根](../../backtest/packages/backtest-runtime/src/crypto_quant_backtest/__init__.py)与原有 analysis 测试目录 | 新导出必须有独立闭合契约；保留旧精确白名单与身份哨兵。首个 native fixture 必须来自获接受的公开 native 构建路径，不手工拼装 verified wrapper 或借旧 fixture 冒充。 |

`BacktestAnalysisRuntime` 现有 constructor 只有 publisher；B1 如何在不扩大旧契约的前提下验证 native 入参，仍需结合实际 native 图冻结。若候选不能提供可独立核验的闭合证据，须重新评审 Interface，而不是以 `type(...) is VerifiedCompletedPublicationV4` 代替证据验证。

### 8.3 新运行的检查与 loader 行为探针

均使用 P 新根环境的 Python，禁用字节码；pytest 禁用自动插件及缓存。不访问真实行情或 owner log。

| 检查 | 本阶段实测结果 |
| --- | --- |
| [依赖一致性测试](../../tests/architecture/test_dependency_alignment.py)：`test_submodule_checkout_and_lock_match_declared_backtest_revision`、`test_installed_cohort_matches_pin_and_has_public_cn_preparation` | **2 passed / 0.42s**；source、gitlink、五包 pin/lock/安装来源一致。 |
| [既有 AnalysisV2 公共闭环](../../backtest/tests/runtime/analysis/test_analysis_v2.py)：`test_analysis_v2_exact_dispatch_and_repository_load` | **1 passed / 3.73s**；run → completion loader → derive → analysis loader，并拒绝错误对象及旧 loader 跨版本调用。是旧版本合成 fixture，不是 native 验收。 |
| 同一旧版本合成完成图上的三种重哈希变更 | 改 `simple_period_return`：**被接受**；改 `trade_count`：**被接受**；改 `source_execution_result_hash`：以 `PORT_ANALYSIS_LINK_MISMATCH` 拒绝。这是行为观察，**不是三项拒绝测试通过**。 |

探针复用现有 `test_durable_rebuild_facade.py` 的内存 `_Store` 与小型图 fixture，先经公开 `BacktestRuntime`、`BacktestEvidenceRepository`、`BacktestAnalysisRuntime` 得到合法分析；对其 `analysis` 执行 `dataclasses.replace`，重新创建 `backtest_analysis@2` envelope/ref，再调用公开 `load_analysis_v2`。独立临时目录限于 P 的 `.venv`，网络被测试 guard 禁用，没有发布真实 authority。

该结果具体证明：合法 CAS/ref 与正确来源链接不足以满足 B1 的数值真实性要求。**B1 必须拒绝重哈希后的错误收益或成交数，并将此加入公开 loader 的负例。** 本轮不顺带改写已冻结的 V2 行为；旧版本是否扩展修复需另行接受。

可复现的最小 pytest 命令（从 P 开始，`TMPDIR` 使临时 fixture 留在项目内）：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  uv run --locked --offline --no-sync python -B -m pytest -q -p no:cacheprovider \
  tests/architecture/test_dependency_alignment.py

(cd backtest && TMPDIR="$PWD/../.venv" PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  ../.venv/bin/python -B -m pytest -q -p no:cacheprovider \
  tests/runtime/analysis/test_analysis_v2.py::test_analysis_v2_exact_dispatch_and_repository_load)
```

### 8.4 下一道实施门

1. 明确 native 基础语义及完整源码基线的接受依据，包括必需的未提交文件；选择本目录内经评审的兼容迁入，或另行派发到原 native 工作区。本轮不跨目录，也不以旧 gitlinks 覆盖当前 P。
2. 接受 B0/B1 的精确范围、native admission Interface 与无冲突的类型/schema 分配，再修复 N 的 B0 哨兵并实现单个公开 native fixture；第 8.3 节旧 fixture 不替代这一步。
3. B1 通过第 6 节矩阵后再冻结 R1。`StrategyCandidate@3` 已用于 target materialization，不能复用；Validation/Promotion 对 native 继续 fail closed。

**仍未验证/未完成**：N 的历史失败复验、C 的 65 项回归、native 公开 fixture 及完整 B1/R1、全仓测试、真实 authority 重开、Experiment/OOS。没有新收益或候选结论，真实数据发布与实验各自保留独立批准门。
