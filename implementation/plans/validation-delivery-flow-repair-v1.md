# 验证与交付流程修复计划 v1

**当前结论：CURRENT_FORMAL_PROFILES_PASSED / FULL_ROADMAP_ACCEPTANCE_NOT_ESTABLISHED。** 用户批准独立新轮次后，正式self与offline-pc各一次实际host/CLI exit0，分别5项与98项通过，294个P/C阶段报告完整；本轮原件直接持久留存并经只读核对。当前两个profile的可复查证据缺口已补齐；旧五份临时终核原件仍未恢复、140控制整套本轮未重跑。R1参考去重成立，但原VF5历史收益门仍未满足，整体不标完成。VF4当前进程实际加载版本UNKNOWN，不把重载列为Platform离线交付前提；上次检查发现的个人settings整体变化仍未归因，本批未读写该配置。准确授权、范围及原件见[交付v2§9](../validation-flow-repair/acceptance-v2.md)。本轮2/2 pytest已封账，不追加测试/benchmark/安装/重载；D009停止与原4/12不变。

以下批次叙述中的“当前/拟/下一项”按该次实施语境理解，不是新的执行许可；行为契约、原验收要求及失败历史均不改写。

**历史批次状态：VF2固定离线范围已OFFLINE_SCOPE_PASSED_LOCAL，VF3已DESK_CHECKED_LOCAL，VF4内容哈希快照已配置供未来加载，SDK1.3隔离注册通过（该工作未reload）；VF5有限交付但改善门仍未满足，整体路线图未完成。** 本批次主控最终host exit0，当前入口P/C98项、独立self和三类plan CLI合同核对通过，详见末尾新收口记录；不宣称N已执行、完整原生资格或整体路线图结束。 原回合上限达到后确已停止；用户“允许”后仅做两文件补丁及对应回归，不自动再增回合。不是完整VF2执行闭包、原TaskSupervisor任务验收、发布或安装；D009仍停止。 初始授权来自用户“可以，就这么推进”；首次修复上限达到后已停止并披露阻塞，依据用户明确答复“允许”完成一个额外两文件修复/定点复审，未自动扩围。D009实源路线的停止决定1475967d继续有效；旧任务板即使显示active也不是恢复源执行许可。原4/12任务、全部审批、失败与封账不变，不清空或替换任务板。

## 1. 目标、判断与证据

目标：对一个声明范围的代码改动，通过固定入口得到**绑定当前版本、失败不被隐藏、覆盖范围明确、可复查的验证结果**；小改动不默认触发整条历史验收重做。

优先级依据是实际阻塞、反复发生和返工影响，不是最新提出的方法名称。“MVP”只用于缩小第一阶段范围，不降低正确性、安全与证据标准。

| 事实依据 | 暴露的问题 | 本计划处理 |
| --- | --- | --- |
| [C0关闭记录](../../research/evidence/d009-retro-v1-c0-engineering-close-v1/close.json)：当时628项测试wall 49.136秒 | 单轮测试不慢，测试之外的交付闭环成本高 | VF1固定入口，VF5一次组合收口 |
| [H0关闭记录](../../research/evidence/d009-retro-v1-credential-h0-close-v1/close.json)：验证子进程合计约2秒，打包宿主exit1，新组合身份未完成 | 解释器/包装错误让局部通过无法交付 | VF1统一进程与结果语义 |
| [capture_adapter_hash](../../experiments/a_share_ingestion/retro_capture_v1.py)绑定5个完整文件 | 组合身份变化与重测范围混在一起 | VF2显式影响矩阵，不删除身份校验 |
| [根pytest配置](../../pyproject.toml)默认testpaths不含tests/research | 默认通过不等于研究回归覆盖 | VF2声明安全离线测试集合 |
| [D1结果§5](../../research/d009-retro-v1-source-capability-research-v1.md)只读研究被套入写者命令验收 | 任务类型与验收证据不匹配 | VF3在任务开始前确定证据类型 |
| Supervisor会话超过旧256MiB，恢复失败只显示泛化错误/0任务；扩容后原任务恢复 | 诊断不明确；提高上限不是完整恢复性能证明 | VF4准确诊断，性能先测量 |
| [D009未执行终态](../../research/d009-retro-v1-not-executed-result-v1.md) | 数据路线未就绪；未执行结案不是成功完成 | VF3前置可行性与结案规则 |

历史1039次顶层调用仅514次带duration，88.6小时是t-2.1日历跨度，不是测试工时。它们不用于宣称完整耗时占比。本轮不重跑历史测试、实源查询或大日志扫描。

规划基线：Platform HEAD `718be80b2c8c9f06e139addaa68126a70154ea5a`，工作区已有未提交/未跟踪变更；Supervisor源码仓库HEAD `04bda585d1f8b9800e4ab298abfaddfec06611f1`。这些只是Git坐标，不是运行中插件或当前全部文件的身份。实施时记录实际字节、工具版本和已有改动，不reset/checkout清理、不把HEAD代替dirty文件hash。

## 2. 不可变约束

1. 不修改D009数学、Core、既有准入/授权规则，不读取行情/成员/原库/凭据，不联网、拟合、重启旧根或借用已关闭额度。
2. 不把bash/codemode全部标为只读，不关闭Supervisor新鲜回执、分支或审批校验，不伪造新的原生批准。
3. 不改写旧失败和旧验收。旧版本证明保持有效的历史含义，但不能冒充当前组合通过。
4. 验证工具不是权限系统或OS沙箱；固定命令列表不是物理网络/磁盘隔离。只运行审查过的离线夹具；未知副作用的测试不自动加入。
5. 不加新依赖、队列、服务或通用DAG/缓存框架。一个仓库同时只有一个写者；跨仓库源码修复与安装分别授权。
6. 本计划不授commit/push、包安装、Pi settings修改或原会话迁移。默认交付本地可核验候选，不称已发布或运行中生效。

## 3. 分阶段依赖与状态（本修复计划的唯一状态表）

```text
VF1 验证入口 ──→ VF2 局部验证 ──┐
      └────────→ VF3 可行性规则 ─┴──→ VF5 Platform离线验收/交付
VF4 控制器诊断（独立仓库）──────────→ 独立验收；不阻塞VF5
```

Platform交付范围固定为VF1、VF2、VF3、VF5；VF4有自己的源码授权、验收状态和回执。VF5完成不代表VF4完成；整份路线图只有五项全部通过才可结案。若VF4尚未授权或未完成，明确报告“Platform部分已交付，整体路线图未完成”，不为等VF4而延迟Platform交付，也不删掉VF4。

| 顺序 | 节点 | 状态 | 可独立交付的结果 | 依赖类型/冲突 | 估计有效工时 |
| --- | --- | --- | --- | --- | --- |
| 1 | VF1 | CURRENT_SELF_PROFILE_PASSED_DURABLE | 新正式self实际CLI/内层exit0、5个固定node通过，前后身份及结果读回一致、原件持久可检索 | 只签该self profile；旧单文件/静态原件未重建，不称原生任务验收 | 本轮self1次，CLI1496ms；不报告历史性能收益 |
| 2 | VF2 | CURRENT_OFFLINE_PC_PASSED_DURABLE | 新正式offline-pc实际CLI/内层exit0，98项/294阶段完整passed、guard0，13依赖/46模块身份闭合、持久原件可检索 | 规划合同仍有R1原件支持；本轮未重跑140控制整套或plan CLI，N仍BLOCKED | 本轮P/C1次、CLI12967ms；不授自动复用、实源/原生或普遍收益结论 |
| 3 | VF3 | DESK_CHECKED_LOCAL | §6五项清单、结案口径及H0/D1/D009三例桌面检查通过 | 独立审阅接受C8；没有新数据、状态机、旧任务验收或数学变更 | 只读材料核对，无旧实验重跑 |
| 4 | VF4 | CONFIGURED_FOR_FUTURE_LOAD / CURRENT_NOT_RELOADED | 原源码122通过/6跳过；按98da+d418授权快照a6c139…、SDK1.3两次隔离注册通过、个人单条来源切换及持久证据核对通过 | 当前进程未reload/版本UNKNOWN；原源码验证临时原件丢失未重造；不是旧任务验收或完整产品验证 | 源码测试3/4及cold2/2均封账；VF5改善仍不足，整体不结案 |
| 5 | VF5 | DELIVERED_LOCAL_LIMITED / HISTORICAL_BENEFIT_NOT_ESTABLISHED | 交付v2§9新增两个正式入口持久终核，结合R1及既有有限交付；旧记录不改写 | 当前两profile证据缺口已补；原B0调度/人工往返历史仍未知，原改善门未满足 | 本轮2/2封账，停止追加；不称历史收益、插件实时生效或原TaskBoard验收 |

Main是计划、接口及最终验收负责人。当前VF2固定入口由只读readiness收敛后，Main直接担任唯一代码写者、整合者及计划文档写者，随后一次新只读审阅；没有第二个Repo写者，也不把独立修复运行绑定到旧D009任务。VF3为可独立推进的文档工作，不等待VF4。工期合计约5–9个有效工作日；含修正余量暂估7–12个工作日，不含外部审批等待。这不是审批/执行额度或完成承诺。VF1同路径小样完成后，依据实际实现/包装成本重估VF2–5，不把初始估时当实测。环境缺失、部署验证、外部等待另记，不混入测试耗时。

只更新本表状态，不为每个小步骤建立一份同义计划。每阶段完成仅记录：改变了什么、准确验证结果、残留风险、下一项。不得为推动状态而关闭未完成节点。

## 4. VF1：让验证失败与成功都能正确收口

**产物：** 一个小型标准库执行入口，不是新测试框架。拟写集：`tools/validate_change.py`、`tests/validation/test_validate_change.py`；`pyproject.toml`只增本工具测试目录，不动依赖/lock/原testpaths。当前这些新路径尚不存在。

### 行为契约

- 初版只提供`self`离线自检profile；使用固定argv调用，不接受任意shell命令，不用管道最后一个exit当整体结果。
- 固定项目`.venv/bin/python`并核实际存在/版本；缺失即明确BLOCKED，不切到系统Python、不安装依赖。只检查该profile真正需要的依赖；结果打包仅用标准库，不导入Domain或研究包。
- 同一入口完成预检、执行、输出完整性检查与汇总。每次输出根exclusive；含一份`result.json`及有界日志，不自动覆盖旧结果或重复执行失败命令。
- 每项记录argv、解释器/工具版本、相关输入/源码/测试/依赖身份、开始结束时间、耗时、真实退出码及状态；不记录完整环境或凭据。测试开始后输入发生变化则不能PASS。
- 检查状态为PASS/FAIL/BLOCKED/NOT_RUN/CANCELLED；整体只有全部必需项通过且结果持久化/核验成功才exit0。预期失败必须由测试断言捕获并让测试进程exit0，不把任意非零当“预期”。
- 子检查通过而打包失败：整体仍非零，原日志保留。超时/用户中止：不执行后续正常检查，必要清理和失败记录仍做，原停止原因优先；不能承诺所有异常都能写出完整结果。
- 每个检查有时间/日志帽；默认无重试。先运行小样再扩大；不为省步骤跳过环境、失败路径或停止测试。
- `result.json`是验证记录，不是Platform研究publication，也不能替代Supervisor实际host receipt。最终验收命令直接暴露结构化exit_code；当前Supervisor要求保持原样。

### 首版入口与固定检查集合

以下是未来实现后的入口示例，不是本轮执行；输出目录中的`EXCLUSIVE_RUN_ID`由执行者换成新值，目录必须不存在：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
.venv/bin/python -B tools/validate_change.py --profile self \
  --output /tmp/validation-self-EXCLUSIVE_RUN_ID
```

`self`只证明验证器自身的工程行为，不证明D009或任何研究模块通过。必需检查恰为以下两个，不能为空、重复、缺项或由调用者替换；输出根检查、身份检查和结果持久化是外层必需条件，不伪装成被测子进程：

1. `environment`：核对当前解释器是项目`.venv/bin/python`对应环境、Python满足根requires-python、pytest已安装且版本符合根声明；不安装、不自动降级。此项失败为BLOCKED，下一项NOT_RUN。
2. `validator_contract`：用同一解释器执行`-I -B -m pytest -c <root>/pyproject.toml --confcutdir=<root>/tests/validation -p no:cacheprovider -q`及以下**准确node列表**，固定cwd为项目根。子进程设置`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`，不继承`PYTEST_ADDOPTS`/`PYTEST_PLUGINS`，不打印环境值：
   - `tests/validation/test_validate_change.py::test_failure_is_not_masked`
   - `tests/validation/test_validate_change.py::test_packaging_failure_is_nonzero`
   - `tests/validation/test_validate_change.py::test_input_identity_change_prevents_pass`
   - `tests/validation/test_validate_change.py::test_stop_preserves_reason_and_cleans_child`
   - `tests/validation/test_validate_change.py::test_required_check_set_is_exact`

这些node通过内部函数与短小合成子进程验证行为，**不得再启动self入口**。另设`test_self_cli_end_to_end`从外部调用上述完整入口，检查结果与退出码；它不在self的五个node中，因此整文件测试调用self时不会递归重跑自己。该端到端测试也不计作第六个self子检查。

首版每项30秒、stdout/stderr合计1MiB；总运行120秒，其中保留10秒用于必要关闭；无自动重试。达到任一帽不得PASS，日志截断/超限须显式记录。这些是待实施的验证器限制，不是恢复任何旧预算，也不代替host对整条命令的期限约束。

整体exit0仅表示两个必需检查均PASS、身份前后相同、结果成功持久化并读回匹配。FAIL退出1，前置条件/参数阻断退出2；SIGINT/SIGTERM分别保留130/143及CANCELLED，后续项NOT_RUN。超时作为FAIL并记TIMEOUT；外层原始中止优先于清理失败。其他非零值不能被解释为通过。终态不能只靠JSON中的PASS判断，必须结合本次宿主退出码与实际结果文件。

### self身份的有限范围

首版身份域命名为`self-inputs-v1`，不是整个Platform或完整`.venv`的不可篡改证明：

- 文件集合固定为`tools/validate_change.py`、`tests/validation/test_validate_change.py`、`pyproject.toml`、`uv.lock`，以及`tests/validation/conftest.py`的存在标记与存在时字节hash。缺少前四项为BLOCKED；conftest从无到有也改变身份。
- `-c`及`--confcutdir`固定配置/夹具发现范围；首版node不得依赖其他项目模块或动态外部fixture。如确需增加，先更新该有限集合和契约，不能静默漏出身份域。`tests/research/conftest.py`不被self加载；VF2的research profile必须另纳入其身份。
- 记录实际解释器入口/解析后可执行文件及其hash、`.venv/pyvenv.cfg`、Python版本/构建信息、实际pytest及其已安装声明依赖的版本和安装位置；读取这些distribution的METADATA/RECORD字节hash，不扫描整个`.venv`。元数据不是完整包代码真实性证明，首版不据此跨运行自动复用检查结果；依赖无法识别时BLOCKED。
- 绑定两个check ID、准确argv、明确设置的非秘密运行选项、限制值和结果schema版本；不能只绑定源码或Git HEAD。
- 明确排除本次输出根、`result.json`、stdout/stderr、临时夹具、`.pytest_cache`和`__pycache__`；输出根不得与上述输入重叠，也不得写入被测输入。路径排序、存在标记和实际字节hash形成输入清单，前后重新计算；不一致即FAIL，禁止刷新旧记录使其看起来通过。

### 最小结果格式

下例只展示结构；尖括号值是文档占位符，不是实际证据。`checks`须准确覆盖上述两个ID且保持顺序，`argv`由固定profile生成；有子进程时须记录其实际返回码，未启动时为null。

```json
{
  "schema_version": 1,
  "profile": "self",
  "identity_scope": "self-inputs-v1",
  "input_manifest": "inputs.json",
  "input_before_sha256": "<64hex>",
  "input_after_sha256": "<64hex>",
  "overall_status": "PASS",
  "reason": null,
  "checks": [
    {"id": "environment", "status": "PASS", "argv": [], "exit_code": null, "duration_ms": 0, "reason": null},
    {"id": "validator_contract", "status": "PASS", "argv": ["<venv-python>", "<固定参数及五个node>"], "exit_code": 0, "duration_ms": 1, "reason": null}
  ],
  "started_at": "<UTC时间>",
  "finished_at": "<UTC时间>",
  "duration_ms": 1
}
```

`inputs.json`与结果同根exclusive保存，内容为上述有限清单；不包含任何凭据。总体及子项耗时用单调时钟计算，墙钟仅记录时间；未运行检查耗时为null而非0。缺项/重复/未知ID、任一必需项非PASS或子进程非零，都不得生成有效的整体PASS。保存结果后才做fsync/读回并决定退出码；打包失败可能留下部分文件或候选PASS字节，不能单凭该孤立文件验收。标准输出只在全部关闭成功后返回结果路径、hash和简短结论，不自造host receipt。

### 必须通过的反例

1. 第一项失败、最后一项成功，整体仍失败。
2. 错解释器/缺依赖在昂贵检查之前被阻断。
3. 子项成功但结果保存失败，整体失败且不丢原日志。
4. 超时/中止没有孤儿子进程，不隐式重试，后续项NOT_RUN。
5. 源码/命令/必要依赖变化，旧结果不能作为当前版本PASS。
6. 真实小样成功路径完成同一个入口的预检、执行、汇总、退出；不只测内部helper。

拟首个验证命令（文件实现后，非本轮执行）：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
.venv/bin/python -B -m pytest -p no:cacheprovider \
tests/validation/test_validate_change.py -q
```

先单个失败传播sentinel，再跑此文件。测试只使用临时目录、假子进程/短小子进程及合成信息，无真实账户/数据/原会话写入。

### 固定offline-pc入口（当前快照已本地通过）

用户最新“按照计划推进”授权继续本地修复。冻结设计见`/tmp/platform-vf2-entry-xmc_v96b/readiness.md`及同根`execution.json`；Main作为唯一代码写者修改`tools/validate_change.py`、`tests/validation/test_validation_profiles.py`，新增`tools/validation_offline_pc.py`，同时负责本计划；旧VF1测试/依赖/lock/D009代码不变。

新增`--profile offline-pc --output EXCLUSIVE_DIR`，不接受scope或任意命令/node；只用固定项目cwd、项目-I/-B解释器和五键干净环境，运行两个已审阅fake文件。实际入口通过本轮审阅/收口后，规划器已知P/C检查改为NOT_RUN（而非旧未核闭包BLOCKED），并给出一个固定`offline_execution_entry`及其共同覆盖S/P/C，提示只需运行一次；不由调用者字段解除任何条件。计划仍不读/执行/签PASS，未知/夹具/依赖/规范文档策略不变，N仍BLOCKED。单独identity域`offline-pc-inputs-v1`，两检查为`environment`、`offline_pc_contract`；self的两ID/五node/schema和plan的纯声明/退出语义不变。S/P/C只有98个唯一收集项及所有setup/call/teardown均passed、S三组4/4/1实例全部覆盖时才记已覆盖；skip/xfail/缺报告/未收集/意外guard事件均不能PASS。N始终未覆盖、未授权。

资格仅固定已审夹具/配置及13项依赖版本；每次重新记录其实际元数据，46个已知项目模块、当前runner/companion/解释器及配置在运行前后绑定。被测生产代码可在获准编辑后取得新身份，不照抄旧hash放行；新增模块/夹具/依赖失配先阻断。临时输出根不进入语义输入身份，实际argv/cwd单独留证。受控child使用独占空pycache前缀并禁写字节码，避免将旧项目pyc当作当前源码执行。精确Popen env和安全child读回分开记录，BLAS变量为1不等于实测线程数。删除旧临时guard的S5三例外依赖，不读取其市场/审计原件；audit hook不是OS沙箱，元数据不是完整二进制认证。

本轮普通离线验证预留一次有界定点修补及受影响重核；至多3个**新入口完整P/C子进程**（候选、主控收口、必要修补后收口），每次60秒、日志2MiB、总120秒/关闭10秒；精确记录用途与真实退出，不借旧3次资格账、不自动重试。先用最小合成覆盖/环境/守卫sentinel，候选实际固定入口只运行本次小范围两个文件，不跑全部研究集。一名新reviewer后主控当前版本收口；未解决阻塞保持未完成。普通包装修补不要求重开源审批，但任何真实源/native/跨仓安装仍禁止。

## 5. VF2：缩小重验证范围，而不是弱化证据

**完整阶段产物：** 固定、可审查的profile/影响矩阵及当前版本验证清单。用户本轮“继续”后先实施**plan-only规划器子范围**，不据此宣称P/C/N实际执行闭包或完整VF2验收通过。当前精确写集仅`tools/validate_change.py`、新增`tests/validation/test_validation_profiles.py`；既有VF1测试、pyproject/lock、组合hash算法及D009生产代码保持不动。

当前冻结契约：`/tmp/platform-vf2-uk2zlf0r/execution.json`，SHA256 `ef7683337e0e263933d8ede0c83c8c62ccb6dd630f85fa8b16a1c1e2acd584f0`；`preflight.json`记录14份保护身份与现有改动，`b0.json`为三类合成变更的人工必需覆盖基线，历史时间UNKNOWN，不声称提速。

- CLI新增`--profile plan --scope JSON --output EXCLUSIVE_DIR`；纯函数`build_plan(scope)`和`compare_evidence(old,current)`只处理有界声明，不读目标源码、不执行命令、不签复用。输入JSON≤64KiB、changes≤64，闭合字段/严格类型/唯一规范化相对路径；未知、依赖、fixture或混合未知不得静默降级。
- 固定顺序D/S/P/C/N分别为document_review、proxy_smoke、proxy_regression、capture_integration、native_policy。已审阅说明→D，proxy→S/P/C，采集公共接口/权限变化→S/P/C/N。`.md`不自动低风险，规范文档/契约不可冒充普通说明；调用者列表与review_basis不证明全树完整。
- S仅列出已核的三个fake节点：proxy测试中的`test_unapproved_endpoint_rejected`、`test_failure_redacted_no_retry_no_failover_no_refund`、`test_capture_retains_exact_safe_bytes_without_pandas_or_second_request`，保留参数例。P完整proxy回归、C完整capture合成集仍有Pandas/SDK闭包未核，N未有原生授权，当前规划器必须明确BLOCKED；任何请求字段都不能自行解除。
- 使用独立`validation_plan`结果：GENERATED不等于验证，overall仅NOT_RUN/BLOCKED；所有未执行检查exit/duration=null，verification_passed=false、reuse_allowed=false、DECLARED_ONLY/UNVERIFIED。可用未执行计划exit3，含阻断义务exit2，输入/持久化错误exit1，停止130/143。**plan无exit0或验证PASS通道**，不能拿规划成功替代代码验收。
- 保留旧/当前声明清单，不刷新为实际hash；逐检查比较source/contract/test/fixture/argv/env/dependency。变化INVALIDATED，缺失UNKNOWN，相同只记UNCHANGED_DECLARED，绝不自动复用。VF1 self的两ID/五node、schema、隔离与停止语义不变，self不接受scope参数。

先证明选择和失效规则；候选验证为新规划器测试、既有VF1兼容与真实CLI/静态检查。规划器功能通过不等于实际业务检查已运行；P/C/N资格及整体效果仍列为阶段待处理项。不建设通用DAG、缓存或epoch改造。

**当前检查点：** 初始候选`6867e72c-9652-4f07-8ad7-8fd7d7191ea9`经审阅发现参数退出码P2；一次定点修复`2eb6cbaf-feb4-46d9-8c67-2e790065047a`修了原三形式，复审仍BLOCK。主控实测`--profile=plan --profile`返回2、`--help --profile=plan --profile`返回0，契约均要求无有效计划的错误退出1；证据`/tmp/platform-vf2-uk2zlf0r/parent-parser-repro.json`，最终host exit1。`repair-1`中的100 passed/self通过/Ruff通过仍保留，但不能替代这两个反例。原回合上限后已停止；用户明确回复“允许”追加仅参数状态保留和对应回归的窄修复。主控已做最小补丁：profile预解析缺值不覆盖上一完整声明，实际parser的错误处理与完整重复值last-wins保持；只改原两文件。新增4例经单元及真实CLI两组覆盖，RED6失败/38通过，GREEN44通过/58未选中；记录在`/tmp/platform-vf2-uk2zlf0r/repair-2/`。独立确认`4054e715-5c45-474d-876c-1856213617d4`结论原P2 RESOLVED、OK with notes，未执行重测。该规划器当前版本已完成主控收口（见末尾记录），保留P/C/N未就绪，不改契约掩盖失败。用户再答“继续”后仅核定P/C合成离线候选：执行包`/tmp/platform-vf2-pc-gf5n6x22/execution.json`冻结最多2个pytest进程，守卫及干净环境不触达真实源。初次元数据预检误拦固定审计JSON，修正为三个精确只读白名单后通过；首次pytest从临时目录启动，两个相对node未找到，exit4为用法错误（非标准未收集码5），未扩大运行。主控第二次通过已有执行器显式固定项目cwd，2节点通过/0.49秒、13依赖、45已加载项目模块、意外守卫事件0、29份源码/保护种子一致。原两进程上限耗尽时已停止，未私自扩大。用户随后明确“允许”追加一次full，累计3次；同一守卫/干净环境/固定项目cwd下组合98项通过1.67秒，意外守卫事件0。独立审阅ACCEPT_LIMITED及主控只读终核支持当前受控方式/快照的P/C离线候选；不代表实际入口已接入，不解除规划器P/C/N阻断。环境传参证据为原始调用+未变实现+执行者声明，非独立environ采样；BLAS1只是环境请求。原始失败、补零日志及纠正说明保留在`/tmp/platform-vf2-pc-gf5n6x22/parent-status.json`等原件。该旧快照核定没有Repo源码、真实源/凭据/原生权限变更，不授其他阶段；其后用户“按照计划推进”的本轮入口与规划器对齐范围，以§4和新execution.json为准，不把旧核定自动提升为新代码PASS。

| 改动类 | 最小必需检查 | 升级条件 |
| --- | --- | --- |
| 文档说明 | 相关链接/声明一致性，代码身份不变 | 规范性契约变更不能按普通文档处理 |
| proxy局部修复 | 对应离线安全回归＋受影响的采集契约集成 | 涉及权限、凭据、异常关闭时增加直接安全反例 |
| 公共接口/准入/资源控制 | 局部回归＋调用方集成；按原政策做必要native验证 | 未获得native授权则BLOCKED，不假称离线能替代 |
| 依赖、测试夹具或未知路径 | 保守升级到相应离线整套/人工确认影响 | 不能因为未匹配到规则而跳过验证 |

候选既有测试：`tests/research/test_a_share_ingestion_proxy.py`、`test_a_share_retro_capture_v1.py`、`test_a_share_price_volume_retro_real_v1.py`、`test_a_share_price_volume_retro_resources_v1.py`。实施时逐项核定其当前副作用和环境要求，固定准确node集合；不将全部`tests/research`盲目纳入默认运行。

全局manifest仍绑定完整当前版本；每个检查另外绑定它消费的源码、公开契约、测试/夹具、命令参数、解释器及依赖。首版只做**显式选择与复用资格说明**：无法证明依赖未变就重测或BLOCKED，不能把旧版本hash换成新hash后沿用成功结果。实际工程验收仍执行所需的当前集成检查。

旧回执可作历史支持材料；只有通过现有Supervisor规则的新鲜最终验证命令，才可用于任务验收。其职责是核当前清单、相关检查和必需集成，不是输出一句PASS。

若未来启用本修复的监督任务，收口顺序固定为：**完成代码/文档写入及任务定义 → 将该任务从implementing转为reviewing → 确认没有未知或重叠执行 → 直接通过host执行一次最终验证命令 → 检查其结构化整数exit_code为0、回执匹配当前reviewing任务digest/epoch且可用于验收 → 提交完成证据。** 在implementing阶段产生的成功命令、旧版本回执或无结构化退出码的工具响应都不能充当该次passed证据。不得把最终命令藏在并行/嵌套工具调用中。

最终命令后不再跑无关bash/codemode或修改文件；若确需修正，则保留原结果，完成修改后重做受影响检查及必要的新鲜收口，不改写旧回执。Supervisor未启用时只报告离线验证结果，不声称任务已被原生验收；本段不恢复原D009监督器。

**验收：** 用合成文件变更验证普通文档不选择数学测试；proxy变更选择安全/采集检查而非所有研究实验；权限/依赖/未知路径不会低估范围；变更后旧证据可复用项与失效项可解释。只读/并行回执等Supervisor协议改造不在本节点。

## 6. VF3：可行性前置与正确结案

**产物：** 在本计划附录形成短清单，不新增审批框架或任务状态机；本文件是本节点唯一文档写集。

任务开始前只明确五件事：可观察交付物、必要输入合同、实际权限/范围、成功/失败验收方法、有限停止条件。数据路线尚不可行时，不进入大量真实执行工程；模拟夹具只能证明工程，不签真实数据资格。

验证资源按风险分层：普通离线命令预留有界诊断/修复/关闭额度；原生资源、市场网络、凭据等仍独立计量和审批。明确哪些失败允许在同一已批准范围内修正重试，哪些必须停止；不以“普通检查”为名规避真实风险。历史额度不追补。

只读研究、代码交付、未执行结案采用不同证据要求；不能为了满足工具的统一模板而执行无关命令。若现有任务工具不支持该验收类型，应在开始前说明限制，不能事后伪造成功。

**验收：** 对已有H0、D1、D009停止三个案例做桌面检查，能在开工前分别发现环境/关闭预留、只读验收错配、未执行终态需求。科学阴性、输入不足、用户停止明确分开；仍不把D009剩余任务标done或修改其原结案。

### 开工前短清单（文档规则，不新增审批或状态机）

1. **交付物：** 明确本轮产物及可观察结论；只读报告、代码候选、实际研究结果或未执行记录不能互相替代。
2. **输入合同：** 列出必须已知的单位、状态、范围及前置证据；关键UNKNOWN先做有限补证或停止，不为尚不可行路线先扩真实执行工程，模拟通过不授实源资格。
3. **权限与边界：** 区分实际批准与提案/工具状态，冻结读写集、累计帽及关闭动作；旧根、未用余额、active投影不带来新许可。
4. **验收方法：** 代码交付核当前身份、相关反例、实际宿主退出及持久化；只读核来源/引文/未知/范围与报告完整性，不补跑无关命令。任务工具若强制不匹配的证据，开工前明确限制；工具REJECTED不能改口为accepted。
5. **停止与关闭：** 普通离线检查预留有界诊断、一次范围内修补和关闭，明确不可自动重试的风险；真实源/native/凭据仍独立批准计量。原中止优先于清理错误；失败及耗用保留，不换根退款。

| 既有案例/已核材料 | 开工前应发现的缺口 | 桌面检查结论（不追认历史验收） |
| --- | --- | --- |
| [H0关闭记录](../../research/evidence/d009-retro-v1-credential-h0-close-v1/close.json) | 最终元数据包装必须使用已核项目解释器或纯标准库；打包/关闭也要纳入同配置小样与有限余量 | 57项及静态通过仍只是局部代码证据；系统Python打包缺包、whole host exit1和6/6耗用保留，不补造第七次命令 |
| [D1结果§5](../../research/d009-retro-v1-source-capability-research-v1.md) | 只读文献核查不适用写者commands-run验收；开工前指定正文/引文/范围核对 | 有文档发现但输入资格未闭合；子运行exit0与native REJECTED同时保留，不运行无关代码改写该结论 |
| [D009未执行终态](../../research/d009-retro-v1-not-executed-result-v1.md) | 输入合同有限补证后仍不足，应支持明确未执行结案，而非强迫进入fit或伪标任务完成 | 决定1475967d停止路线；正式fit=0、科学问题未答、原4/12不变；停止报告不是策略无效证明或任务验收 |

报告时区分：**科学阴性**须有原定协议实际执行及支持该判定的结果；**输入不足**说明哪些必要依据缺失、哪些阶段未执行；**用户停止**记实际决定及已做/未做，不等于成功。工程命令失败另记真实失败，不隐藏在上述研究分类里；未执行不能推成“无增量”。这只是报告口径，不新增任务done/cancelled转换或修改原数学判据。

## 7. VF4：控制器可诊断，容量不再靠猜

独立仓库：`/home/ygguo/agent-projs/agent-ext/pi-task-supervisor`。拟范围为`src/human-journal.ts`、`src/events.ts`及现有`human-journal.test.ts`、`events.test.ts`、`status-ui.test.ts`；状态展示需要的`ui-capture.ts`/`status-ui.ts`仅在复现证明必要后纳入精确写集。实施前读该仓库当前指导和实际源码基线。

第一版只修可诊断性：保留JOURNAL_LIMIT/JOURNAL_INVALID/JOURNAL_BRANCH_INVALID等安全错误码；超帽说明实际值/阈值，未知保持未知；恢复失败显示“任务视图未恢复”，不把默认空表暗示为任务删除。不得在提示中泄露会话正文或凭据。

**验收：** 小型合成日志注入容量、坏JSON、断链、迁移待处理，显示不同准确原因；fault仍拒绝续行；结构/分支/审批校验与旧记录不变。使用既有Vitest/隔离fake-Pi，不改真实settings、不写原会话或制造批准。

性能仅做有界测量：先小样，再不超过32MiB/有界条目的合成日志，记录完整控制操作中的读量/扫描次数/墙钟；不是2GiB满载证明。若重复全量解析确实超过约定响应目标，再另立必要的增量检查点设计与完整性测试，**本版不直接改存储/分支/回执协议**。

原2GiB/16MiB/50万帽保持；旧1195回执迁移、500上限修复不重复重做。新源码验证通过不等于已安装；安装/重载及真实会话恢复检查须另有明确许可。

### 只读准备与已批准源码范围（当前源码候选本地通过，不安装）

- **新基线：** Supervisor源码HEAD `974b5ddca57f8c2bf62534a3b14b1a5f23c275ac`，只读前后git状态干净、已读文件hash匹配；不是原规划HEAD `04bda585…`，不得直接套旧补丁。两个旧AGENTS.md路径当前不存在（ENOENT已观察），源码目录及README存在，未恢复/生成指令文件。
- **静态定位：** `human-journal.ts`保留六种typed code，但LIMIT抛出点没有观察量/阈值字段；`events.ts`恢复catch将其替换为通用字符串。`status-ui.ts`及`board-view.ts`仍有原始0/0计数/进度输出路径。已有fault优先headline保留，不等于所有输出已消除歧义；尚未运行终端复现。早期恢复失败会留下空视图，较晚失败可能已有局部恢复的board，不把全部catch误说成任务丢失。
- **精确写集（后获原生授权3566474f）：** 源码5份`src/human-journal.ts`、`src/events.ts`、`src/ui-view.ts`、`src/board-view.ts`、`src/status-ui.ts`；测试4份`src/__tests__/human-journal.test.ts`、`events.test.ts`、`status-ui.test.ts`、`board-ui.test.ts`。只读准备时没有修改这些文件；后续候选按此9文件实施，不纳入`ui-capture.ts`、runtime/state/存储/回执/审批模块。
- **冻结最小接口：** JournalReadError只增加可选、只读的白名单metric＋安全数字detail，`.code/.message`旧语义不变；既有文件/行/条目LIMIT点附实际观察与阈值，配置异常未知就UNKNOWN，不输出正文、路径、ID或原始异常。纯`formatJournalReadError(error)`只识别该typed错误，给安全code/detail提示；未知异常保留现有保守阻断，不解析成权限。events仍disable续行、held恢复，不重放/修复原记录。
- **显示接缝：** 在ui-view增加纯`taskViewCountsUnknown(summary)`：仅当计数为0且有journal error blocker时保守判展示数量未知；statusbar和board counts/progress/空记录文案共用它，显示“任务视图未恢复（数量未知/记录未删除）”，不把0/0或空进度当已知总数。正常无fault空板仍按既有0/0显示，已知非空记录不改；只是只读显示，不增加TaskBoard字段、恢复操作或批准通道。
- **批准后验证限界：** 先新合成RED sentinel，再四份定点测试；一次新只读审阅，至多一次定点修补，Main当前版本终核。项目测试进程最多4次、每次60秒/日志1MiB；静态仅typecheck及精确写集ESLint/Prettier check。只用既有依赖，当前四个.bin路径存在不代表版本已验；缺失/不符即停，不npm ci、不npx下载、不跑全量check/real-Pi smokes。合成日志先≤64KiB计量完整inspect/restore路径的读取/扫描/墙钟；本轮不自动扩32MiB，更不制造2GiB真实日志，不声称性能收益。
- **现有取证：** `/tmp/platform-vf4-prep-11b_yzpz/preflight.json`与`proposal.json`（后者SHA256 `1c417e8f4ba483797b2611838f466fa345e7bee90cb1db10ee458dacc386c4b8`）。机械盘点由Main核对并更正了短HEAD笔误、遗漏的JOURNAL_BRANCH_INVALID、catch可能局部恢复及board-view输出；测试是必需验证，不是可省略项。已做只读查询，无项目代码/测试、源码修改、安装、settings或真实会话操作。
- **实际授权及执行：** 目标澄清信息门`decision-e43d3c64-a556-41f7-972d-5e2c340f6ac9`收到“授权”（control859e7cbf），因kind=information未升格为写许可。随后独立VF4精确授权门`decision-b04b0a7b-fd61-4a40-8485-e636e94ecae8`实际原生批准“批准上述范围”，control`3566474f`；它仅授上述9文件与有界离线验证，不恢复D009、不接受旧t-2.1或变更原4/12完成数。门记录附于原会话，但不把其批准当旧包A许可。Main唯一写者；新根`/tmp/platform-vf4-code-c5_jkof3/`保留基线9文件、授权与命令。新sentinel先RED，定点4文件122通过/6跳过，类型/格式/ESLint通过；后者101行超帽失败及最小整理复核保留，formatter原始AST括号误报及规范化复核保留。现有expanded capacity组含8/16MiB与2GiB稀疏样例，按64KiB授权未运行、不修改，不冒充容量复验。小样inspect10127B/2read/1EOF、完整restore30B/1read/1open，仅当前小样，不证明大日志性能。候选时测试2/4已用，随后独立只读审阅7389de50结论OK_FOR_FINAL_GATE，无已证实BLOCKER；它不是验收替身。Main直接当前版本终核host exit0，`/tmp/platform-vf4-code-c5_jkof3/parent-final/result.json` SHA256 `7c65f996aaf8e5b9a9342e286965bdd5e576816b25d72f6c98f15c49168d16d3`，122通过/6跳过、typecheck/精确ESLint/Prettier check均通过，Source9身份/依赖元数据/原caps前后匹配，无源码写集外diff/未跟踪/暂存。最终smallinspect10127B/2read/1EOF约0.582ms，restore30B/1read/1open约0.816ms，只证明此次小样；不称性能改善。原晚期非空局部恢复、非TUI status实参缺新增直接断言的NOTE保留；未跑全套、real-Pi/native/SDK1.2/真实终端或大容量边界。实际测试3/4，剩余1关闭不结转。审阅请求read-only diff后由Main提供精确artifact，等待工具曾在完成通知前返回no active，未启动替代review。安装/重载及真实会话验证仍需以后单独批准。

### VF4未来加载配置已完成（首预检失败及恢复授权保留，当前会话未重载）

- 当前个人settings只向Supervisor本地快照`/home/ygguo/.pi/agent/local-packages/pi-task-supervisor/974b5ddca57f8c2bf62534a3b14b1a5f23c275ac`注册，五个运行文件均是旧字节，不是新源码候选。`npm:@tintinweb/pi-tasks`对象的`extensions: []`保持，不把声明存在误说成扩展冲突；项目设置未发现同名覆盖。配置和磁盘来源不证明当前内存实际加载版本，该值仍UNKNOWN。
- 宿主SDK当前实际`1.3.0`，本次源码单测SDK为`1.1.0`；没有把旧1.2历史证明冒充1.3资格。拟授权后的先决条件为同隔离配置的小型扩展smoke及完整候选在实际宿主1.3的DefaultResourceLoader冷加载，最多2进程、每次60秒/日志1MiB，不创建AgentSession、不prompt、不激活命令/审批/旧session。SettingsManager仅inMemory空配置，空白/tmp cwd/agentDir/HOME、PI_OFFLINE、禁默认extensions/skills/prompts/themes/context，只额外加载精确候选。errors/warnings不为0或路径/注册不符即停，原settings不动，不自动追加。
- 已只读冻结54个常规包文件、760948B（只含manifest明确的runtime/src、docs与包说明，不含tests/.git/node_modules），内容清单hash `a6c1391f6215faa9eba5df056bdf6ae7e2e4f8690c774a0d44d89d4ec871a7ce`。与旧安装copy的runtime差异恰为已通过的五份源码。拟新目录`/home/ygguo/.pi/agent/local-packages/pi-task-supervisor/vf4-sha256-a6c1391f6215faa9eba5df056bdf6ae7e2e4f8690c774a0d44d89d4ec871a7ce`，目前不存在；不会指向可变工作树，不把旧HEAD坐标当新commit。
- 若以后明确批准，只创建该独占新快照，逐文件hash/readback/fsync，不覆盖旧974目录；冷加载通过后备份个人settings到`local-packages/pi-task-supervisor/vf4-install-backups/ijgwk29v/settings.before.json`（0600，不打印正文），再仅替换packages中唯一旧source字符串，其他字节/过滤/包/模型设置不动。预检settings SHA `26698c6a05f2a6844d02768ab8aaf53fedbef2573ad9e7fef6311a80a1e361fe`，拟替换后SHA `cd185fc8acb05403a2e77054ae9c7401e3d3d2c6a778aa7f6a328940b7a5f234`；并发变化、不单链/符号链接、来源不唯一均阻断。若写后核对失败，仅在当前仍等于本次预期输出时可精确回滚；未知并发状态不覆盖、不重试。
- 此方案只配置未来加载，不调用当前`/reload`，不打开/恢复原研究会话；运行中生效仍未证明。只读提案`/tmp/platform-vf4-install-prep-ijgwk29v/proposal.json`，SHA `9e718695c333385ccc98f817b82f3af2c704d20c632367abd3e10caa3eeec029`。原门曾deferred，聊天“批准”未被升格；后实际原生批准`decision-8045e96a-46bd-45d6-af91-2ae5bce20078`、control`98da48ae`已确认，同一重复通知不重复执行、不借旧源码测试额度。
- **首次阻塞（后经独立补充授权解除，失败保留）：** 首次安装预检在任何持久写入/cold之前发现整个临时提案目录及清单已不存在，原源码通过记录7c65…的临时原件也不存在；未推断删除者/原因。settings仍SHA26698…、新快照/备份均未创建，cold0/2、配置变更0。按路径/不可自动重试条件暂停，不以原生批准掩盖前置失败。只读从当前源码和已记录算法恢复出的清单与提案分别严格匹配原a6c139…和9e718…完整hash，是字节等价元数据，不是新PASS；没有重建丢失通过JSON/日志或读取禁止的原journal。历史host通过事实与现在不可检索原件严格区分。
- **恢复限定提案：** `/tmp/platform-vf4-install-held-vgnqbhd9/recovery-proposal.json`，SHA `b119e3019813ae76620ea20706ceca2f06f084c1efe2e8d94f18aeb81540c04b`。仅请求恢复两份同hash元数据、保留缺档失败/来源，并在明确解除本次预检hold后按原98da范围继续一次预检；原cold额度仍0/2、60秒各/总180秒，不退款、不增第三次、不另跑源码测试。另请求把新执行证据有限留存到既定备份父目录的`evidence/`（owner-only、最多4MiB），解决原“仅/tmp记录”的脆弱性；不把缺失原验证记录交给人类批准成通过。随后实际原生补充批准`decision-3cd50ad6-61df-4bb0-af90-b18055d8b5d4`、control`d418b53b`明确允许等价元数据恢复、一次预检续行和有界持久留证；原2冷额度未重置、原源码PASS文件/日志未重造。
- **安装实际结果：** 单次受控执行2.431秒、host exit0，smoke/candidate冷加载实际exit0、617ms/1409ms，host SDK1.3.0，errors/warnings/guard观察均0；候选来源路径匹配、两命令别名及8工具/必需handlers注册匹配。未创建AgentSession、未调用prompt/命令/审批/session hooks，没有运行真实研究/原journal。两次cold额度2/2关闭，不再自动重试；冷注册不是完整宿主行为/真实终端/人类或业务验收。
- **当前配置：** 已创建上述54文件内容哈希快照与清单，payload文件0444、目录0555；个人settings仅唯一source字符串替换，after SHA严格为`cd185fc8acb05403a2e77054ae9c7401e3d3d2c6a778aa7f6a328940b7a5f234`，其他字节/包/过滤不变，旧974目录保留。before原字节备份SHA26698…、mode0600。没有reload当前进程、没有打开/恢复原会话，当前内存revision仍UNKNOWN，不把配置更新冒充实时生效。
- **持久证据：** `/home/ygguo/.pi/agent/local-packages/pi-task-supervisor/vf4-install-backups/ijgwk29v/evidence/install-result.json`，SHA256 `98bd4ec64991aeb57411450954badb697c48a2cedc50eac01bbac8720f4420c4`，状态INSTALLED_FOR_FUTURE_LOAD_NOT_RELOADED。9份当前证据合计23844B、文件0600/目录0700，包含等价恢复来源、首次缺档失败和实际cold/安装结果；不包含捏造的旧验证日志。只读独立后核`/tmp/platform-vf4-install-exec-k804u10o/postcheck.json` SHA `dc6270663b2d5bfebde9ad378fa428ea4566004e53c83b36dd156e90a9ade627`，实际快照/配置/备份/过滤/证据均匹配，未增加第三冷加载。原D009停止与原4/12完成数不变，VF5改善门仍NOT_ESTABLISHED。

## 8. VF5：Platform离线组合验收与交付

**当前产物：** `implementation/validation-flow-repair/acceptance-v2.md`汇总仍可检索的R1/首轮失败/VF4安装证据；§8保留新终核前的总验收差距，§9记录本轮获准的self/offline-pc正式入口持久终核及真实exit0。当前两profile通过不等于140控制整套重跑、完整VF5或整体路线图验收。

**历史交付快照：** `implementation/validation-flow-repair/acceptance-v1.md`为VF4源码实施前已获独立审阅接受的有限Platform说明；其当时Main文档终核`/tmp/platform-vf5-32qkqmnw/result.json`与直接host exit0是历史观察，原件现已缺失，不称当前可取。该v1不能充当新VF4源码或运行版本证明；VF4状态以§3/§7及v2最新核对为准。VF4仍独立验收，不是Platform离线交付开工或通过的前提；安装、运行态生效分别处理，不能据部分交付宣布整份路线图完成。

正式验收前完成全部被测文档与代码写入；采用§5的reviewing→最终host命令→完成证据顺序。交付记录不得反过来成为本次被测输入的一部分。

本轮用户“继续”后唯一写者Main仅写上述交付说明与本计划；独立审阅e9f8fa23接受有限文档交付，同时明确§8“相较B0确实减少重复检查或人工往返”仍未证，不能因允许人工B0就假设其三进程历史。review原turn-budget提示保留，交付结论不扩大。执行卡`/tmp/platform-vf5-32qkqmnw/execution.json`（SHA256 `88dbbf15a241391fb2323b0e4212d2cb1d8307228e5eac497c71b0b224baa37f`）。先用同B0文档样例小样确认plan路径，再运行另两个同path/role样例，3次退出3/3/2符合合同，目标测试执行0、新P/C为0；没有借用已封账的3次P/C。对照`comparison.json`（SHA256 `6ba1fb3dcd522c67f2b0193d39e1ac96facc9946960a1589272c0189c3f1266f`）明确：仅在S/P/C分开执行的参考编排下为3进程/107实例，相对当前1进程/98唯一node去重9；原人工B0没有实际调度/时长记录，不能称历史提速或人工往返减少。当前源码与既有最终gate哈希一致，只引用同版本证据，不为说明另跑P/C。

### 改动前基线与改善判据

- **时点：** VF1获批后、首次实现改动前，先用一个短小合成小样确认测量路径，再记录现有手动验证方式的B0；VF2实现前冻结普通文档、局部代码、公共接口三类合成变更及其必需覆盖清单。数据和来源操作均为0，不重跑旧实验或故障会话。
- **范围：** 每类先做一份基线与一份新入口对照，固定环境、样例、命令语义及覆盖期望。现有流程没有自动选择器时，B0用明确的人工检查清单并标明其性质；不存在的历史计时记UNKNOWN，不补造，也不为让数字变好人为扩大B0。未覆盖某类时只能报告该类改善尚未验证。
- **指标：** 分开记录必要/实际检查数、缺失覆盖数、子进程时长、包装时长、外部等待及人工介入次数；保存准确版本和配置。安全反例必须保留，不能通过减少必要检查换取加速。
- **改善成立条件：** 三类必需覆盖缺失均为0；普通文档不运行数学/资源集成；局部变更的实际选择严格小于已声明的全套集合并包含全部直接相关检查；公共接口变化不漏跨模块检查。相较B0确实减少重复检查或人工往返才能称该方面改善，耗时上限通过本身不构成改善证明。
- **结果处理：** 单次小样用于工程定位，不报告统计显著性或推广为所有改动收益；未改善或明显回退时如实报告并最小修正，不改基线、不降低覆盖、不自动扩大方案。VF1小样后更新工期估计。

最终必须验证：

- VF1失败传播、VF2选择/失效、VF3停止语义各有对应证据；VF4结果单列为已验收或待处理，不冒充本交付已覆盖。
- 一条真实的**离线工程**路径完成预检→局部检查→必要集成→结果文件→当前身份核验；不是只让JSON字段自称PASS。
- 使用同一组样例记录：普通文档、局部代码、公共接口三类的检查数、子进程时长、包装时长、等待时间、人工介入次数。前后同配置比较，缺失值不当0，嵌套时长不重复求和。
- 建议性能目标：self小样≤30秒、普通局部离线检查≤2分钟、组合离线检查≤10分钟。它们是待测服务目标而非已有成绩或跳过检查理由；超出先定位并报告，不自动放宽或用更小测试冒充。
- 默认回归、明确research离线集合与高成本检查的分工清楚；必要的当前全套/跨模块检查在此一次运行，不在每个文档写回后重复。
- 真实网络、凭据、市场数据、模型调用为0；临时进程/文件按声明关闭；D009原任务、审计根、失败账未修改。
- 交付说明绑定实际dirty源码/新增文件与依赖；不把未跟踪文件漏掉，不把当前worktree称clean clone。未获commit/push/安装授权时，只交付可核验本地候选并标明未发布/未部署。

Supervisor原生任务验收与离线验证报告分别处理：报告PASS不能自行解除任何人类门禁。若未来为本修复启用新任务板，只能在明确新目标范围后建立，不能覆盖原D009板或继承其done作为本修复证明。

### VF5-P1前瞻样本已授权尝试，结果INCOMPLETE（封账，未修补重跑）

原生choice `decision-57e92cac-6bd9-4a6a-952f-4a9f7f88bdda`、control`3c816c5c`选择保持D009停止，由Main只准备新有限收益核验提案；这不是运行许可。已形成[VF5-P1提案](validation-flow-prospective-benchmark-v1.md)：在同一新冻结参考harness下，A-S/P/C三child与B-PC一child比较覆盖、重复实例及单对耗时；第一A-S兼作最小smoke，拟最多4次pytest/3次纯plan、总240秒，无重试，不改生产或测试代码，不接触数据/模型/网络/安装。只有集合完整且各阶段实际通过才能记新的参考样本有效，不签生产validation PASS；单序A→B缓存偏差不支持普遍提速或人工减少。若仅需确认静态S子集关系，本实验未必值得执行。

它是新的前瞻性参考，不恢复/补造历史B0，不自动解除原VF5的NOT_ESTABLISHED。准备阶段仅核9份源码/fixture/config及13项版本元数据，原choice不授运行。后实际执行授权`decision-982ad4b7-7252-426a-9db8-acab4b09a892`、control`a5562792`获批准；其持久目录误写/home/ygguoo，是Main笔误，未执行即停。再获仅目录更正授权`decision-c93625db-32ce-4548-8ea8-e388b4b0b6d9`、control`a923eb90`后在正确/home/ygguo路径执行，方法/预算未变，错误目录没有写入。冻结提案文件SHA `5b989cc126661ea8721fe28737e0986b7662d02b71bdd50c24515728a9b2ab19`保持不改，以下结果是另行留证，不覆盖原提案或回填历史。

**实际结果：INCOMPLETE，不是有效收益样本。** 运行证据持久目录`/home/ygguo/.local/state/ai-crypt/validation-flow/vf5p1/run-20261021T041334Z-185a092e/`。3份纯plan退出3/3/2、选择义务匹配且目标执行0。首A-S child真实exit0、9通过/0.10秒、27阶段报告、意外guard0、Source/环境前后与parent一致；随后parent参数合同断言失败，整体host exit1，A-S未被接纳为有效benchmark arm，A-P/A-C/B-PC均NOT_RUN，不能凭child9通过说整组成功。没有收益对照或历史改善结论。

**只读定位：** 项目pyproject已有addopts `--import-mode=importlib`；child把同一可变argv列表交给pytest.main，调用后报告包含该配置展开前缀，而parent只期待原始列表。归档实际报告严格等于“已固定项目addopts＋原始argv”。这是Main临时harness没有区分原始/有效参数的合同缺陷，不是P/C回归或额外权限。没有修改harness/生产代码、没有追认有效、没有修补重跑。测试1/4、plan3/3，剩余3测试名额已关闭、不退款/结转。

**可核结果：** 持久`result.json` SHA `dafa02b00394bf3a6915f7ae00d5fb2b52b9bc1519a2fe645469f1960e73a633`；`comparison.json`仅失败诊断，SHA `b7799087a6df77b92505b1e6799e5b43353dcea36b2e1e92ca6934c9f2f52239`；`close.json` SHA `5630a2c9e3036d42e8cee1c3e9978eb7228e09e1b8ba5b2df2663fd09c9a14e8`。23个证据文件141927B、owner-only，7个运行pin与两份冻结harness hash当前未变；最终只读核对通过不等于样本通过。原VF5历史收益仍NOT_ESTABLISHED，D009与旧t-2.1/原4/12不变。若以后决定修harness再试，须新有限提案及明确授权，不借本轮余量。

### VF5-P1-R1：最小参数契约修补后的独立新轮次（VALID_REFERENCE_SAMPLE）

旧Supervisor已由人类停止后，用户要求“继续”，Main明确提出“仅修私有harness，新的4次pytest/3次plan/240秒同方法复核”，用户实际回复“批准”。本轮不是原a556余量、没有重启旧监督器或改原任务板；旧失败结果dafa02…和关闭账5630a…保持原字节。

只改新私有harness：在pytest.main前将requested argv保存为不可变tuple，报告schema2分开记录requested/effective；parent分别核固定selector原始argv与“已pin项目addopts＋原始argv”，不宽泛忽略未知参数。纯契约自检1正确例/7错误例均符合预期，未运行pytest；准备检查脚本一次缺v绑定的NameError保留，修正只涉及自检命名空间、不消费实验额度。生产/fixture/config及依赖未改。

**实际结果：** host exit0，4臂9/57/41/98均exit0、615个阶段报告完整passed，意外guard0、共同输入/安全环境前后一致，A三臂并集与B都是98唯一node，缺失/额外唯一node0。新参考中A用3子进程/107实例，B用1子进程/98实例，实际避免2次启动和9次重复。A单对墙钟6926.896ms、B4614.629ms；A子进程时长合计6280ms、B4328ms，这些嵌套量不相加。顺序仅A→B、OS/cache偏差未平衡，只能说本对B较短，不作历史/普遍/统计提速、人工减少或生产公开CLI总耗时结论；原VF5历史门继续NOT_ESTABLISHED。3份纯plan退出3/3/2、义务选择缺失0、目标执行0且N仍BLOCKED。

**持久取证：** `/home/ygguo/.local/state/ai-crypt/validation-flow/vf5p1/run-r1-20261021T054336Z-b2f22665/`，`result.json` SHA256 `69455875800395005450d17b77b61fa044d4d917ab4d60dd9b9bc0e29c014d2e`；`comparison.json` SHA `b9b61e1323b749d6abbad9efba6ad9892dee20aee846a98189dc52f03f65b560`；`close.json` SHA `36d5850f03b67f203508e5b9d20a31d181aa707f69ce69b844598b5ecf5d1aa5`。33个owner-only文件550445B；只读终核确认schema2两类argv、集合、615阶段、Source7pin/冻结2代码hash和旧失败不变。4/4pytest、3/3plan均封账，无附加测试。不是production validation PASS、原任务验收或研究结果；D009停止及原4/12不变。

## 9. 有意不做，以及何时重新评估

| 暂缓项 | 为什么不现在做 | 再进入条件 |
| --- | --- | --- |
| 任意跨版本自动缓存/全局epoch改造 | 权限与完整性风险高，先验证显式局部选择的收益 | VF2仍存在可测的主要重复成本且新协议获批 |
| 大日志增量存储重构 | 已扩容解除了眼前拒绝条件，性能根因尚未量化 | VF4实测表明重复扫描主导控制耗时 |
| 通用“取消即验收”状态机 | 取消不是成功，不能冲淡原任务语义 | 有独立契约与审批，明确关闭未执行但不计成功 |
| D009源合同、N2、实源A/B | 路线已被人类停止，流程修复不恢复它 | 新范围与有限提案明确批准 |
| Promotion/Shadow/Live或新供应商 | 不解决当前验证闭环问题 | 独立产品目标与批准 |

## 10. 推进与停止规则

- 先前VF2两文件规划器及无Repo写集的P/C旧快照核定已完成；用户最新“按照计划推进”后继续§4所列三文件固定offline-pc入口及§6的VF3文档规则。Main统一写代码/文档、一次focused只读审阅及有界修补，不重建原任务板。VF4跨仓源码与安装仍需单独明确范围/许可，VF5须满足VF1–3证据门；不由旧板active推断新源或原生权限。
- 节点一旦获批，在其不变范围内自动完成实施与必需验证，不为普通阶段反复索要确认；仅权限/共享接口/预算/外部访问出现实质变化时暂停受影响工作。
- 每个失败保留原始退出/回执，先定位再做最小修正；不盲目重复整套验证，不为耗尽旧额度换根重开。
- 只做必要的阶段审查。高风险权限/身份规则不得因追求速度省掉反例；低风险文档不要求无关native证明。
- 若VF1/2即可显著改善交付，应先交付其独立结果，不为等待低优先级重构而延迟所有价值。
- 最终结论必须区分：本地验证通过、任务被接受、版本已发布、运行中已生效；任一项未发生就明确写未发生。

## 11. 本次VF1执行卡

- **范围：** 一个写者仅修改`tools/validate_change.py`、`tests/validation/test_validate_change.py`、`pyproject.toml`；后者仅加验证器测试目录。主控只在写者结束后更新本计划状态，不与子代理并行写工作区。无依赖/lock、D009源码、Supervisor源码或settings改动。
- **编排：** 允许的`cliproxyapi/gpt-6.1-sol`模型；fresh-context写者→一次独立只读reviewer→必要时最多一次定点修复与一次定点复审→主控验收。启动/权限失败先报告，不换执行模式或重复派发活跃写者；有效阻塞未解则保持未完成。
- **证据：** `/tmp/platform-vf1-z1as0psx/preflight.json`记录现有改动和12份保护文件身份；`b0.json`记录短小合成进程的实际退出码/时长。旧self入口不存在，比较基线明确为NOT_AVAILABLE，不据此宣称提速。子代理输出走原生执行产物，不创建同义仓库报告。
- **检查：** 先失败传播sentinel，再验证器单文件；self的五node与外部端到端测试保持非递归。写者只做候选验证，主控在审阅/必要修复后执行一次当前版本收口，并检查写集/保护身份及pyproject仅增目录。
- **限界：** 这是离线工程验证，不是OS沙箱。所有故意损坏、身份变化、超时及进程清理测试只用临时合成夹具，不触碰实际源、凭据、原会话或旧账。禁止网络、安装、commit/push、启动实源和借用历史额度。
- **完成口径：** VF1实际命令/结果/失败与限制可复查才记本阶段通过；不自动开始VF2–5，不宣称新原生任务板验收或D009完成。原生workflow状态记录运行事实，本表只登记节点授权/验收状态。
- **当前检查点：** 初始写者`a8b30b91-aa25-4ea1-94b0-1135ffb3ee0b`完成候选，首次审阅发现3项P1；一次定点修复`2740eb09-740e-47a4-b492-4a306f6746d3`修复这3项，复审`728767e6-9674-47b8-97e5-67fdbd681920`确认原项解决，但发现透明exec侵入非隔离pytest中的合成main调用。主控执行计划所述非-I路径的`test_packaging_failure_is_nonzero`，真实exit1、1 failed/0.06秒（产物根`/tmp/platform-vf1-z1as0psx/parent-nonisolate-probe`）；不能用仅-I模式6 passed替代。原始失败、候选与修复日志均保留。复审见`/tmp/platform-vf1-z1as0psx/targeted-rereview.md`。
- **追加授权与下一处置：** 原一轮上限达到后确已停止；用户明确回复“允许”后，写者`05cc53ad-4d17-45d0-b672-734d0d764074`只修两个候选文件，pyproject未再改。透明exec已限于真实CLI引导；真实environment仍要求-I/-B，合成断言在隔离子进程中执行。默认非-I失败节点先RED后GREEN，非-I单文件6 passed、独立真实CLI与隔离五node通过。复审`e1942258-2646-47d0-aac9-32957c07652e`结论OK with notes，见`/tmp/platform-vf1-z1as0psx/extra-rereview.md`。主控仅做一次当前版本最终验证及范围核对；不授VF2或再下一回合。
- **主控收口位置：** `/tmp/platform-vf1-z1as0psx/parent-final/`必须新建；将保存实际命令、退出码、日志、self结果、身份与保护检查。只有最终host命令exit0并对应产物核对成功，才登记VF1本地验证通过；不是原TaskSupervisor任务验收。旧失败和未归因目录状态变化继续保留，不宣称全工作区完整性、发布、安装或D009完成。



- **主控最终结果：** 当前两文件hash分别为`1e4b0c7a7207d96e17ff52fa8110dfd4a9709efa092084e97452c69181d1e4f5`、`2a00b5545c183b1e162e5ba107da8dbfb6fd3086673353101b8cfddfcf310958`；非-I单文件6项通过、独立非-I self CLI成功（内部隔离五node）、Ruff F通过，12份保护文件及pyproject原有字节复核一致，无暂存。详见`/tmp/platform-vf1-z1as0psx/parent-final/result.json`，SHA256 `6e6beeebcae2c314c35bfca42487ad557baa06ad0fc8e9713e37d4c2592ac81c`；须结合最终host exit0。先前失败全部保留，未归因状态差异仍披露，不称全树完整性。VF2–5未实施，D009未恢复，无发布或安装。

- **VF2主控收口：** 当前规划器子范围本地通过；非-I组合108项、独立self、三类实际plan CLI（3/2/2）及原两项错误参数CLI（1/1）、Ruff F和14份保护核对均符合预期。证据`/tmp/platform-vf2-uk2zlf0r/parent-final/result.json`，SHA256 `f1673e56a2ffd44f36225fa1bf179a930cf4ba618d146efa6f558791a5d9e940`，须结合最终host exit0。三类计划均未运行业务检查、不授复用；P/C/N执行资格和完整VF2未完成，无性能提升结论。VF1旧证明只对当时字节有效，本次新runner兼容性由当前组合与self重新确认；D009未恢复，其他阶段未启动。

- **P/C有限核定收口：** `/tmp/platform-vf2-pc-gf5n6x22/accepted-limited.json`，SHA256 `e633cb9d424315be38b7953e53d0a02181b4db1389889f0452eaed312a0bfac9`，须结合主控最终host exit0。29份seed/保护文件前后稳定且当前匹配、13项distribution元数据稳定；46项目模块hash仅为结束/当前观察。未重跑测试，原预检/cwd/补零日志错误保留。规划器实际P/C执行接入、N权限及完整VF2仍未完成，不签跨版本复用、不声称全树/二进制真实性或实盘/实源资格。

- **本批次VF2入口＋VF3主控收口：** `/tmp/platform-vf2-entry-xmc_v96b/parent-final/result.json`，SHA256 `dcdf47167f6b42d357700d669d6f35d5df8a7a94199e8283e2baf58681110eaf`；直接最终host exit0，状态LOCAL_FINAL_GATE_PASSED。最新三文件分别为runner `326da060e95bb12d45f29952716e200f2a2b5c5a1833f8f45ed99f456b3cadf8`、profiles测试 `961a1a4420815d876d8ddd965f95e2316631deb969415363e623109c3563768b`、companion `e26e50e05efc92b2bded24c8d4d0f195036da7fac51683e54d5bd6206d4708b5`。140控制/兼容项4.24秒及Ruff F通过；当前实际P/C98项3.24秒、294阶段报告、意外guard事件0、13依赖元数据和46项目源码前后身份闭合，27保护文件一致；独立self成功，三类plan退出3/3/2符合未执行/阻断语义，绝不把它们称业务PASS。初次捕获/dev/null误拒、第二次目录句柄误拒的62通过/36失败，以及审阅C7原因覆盖P2、六项RED均保留；修补后定点复审26feed28结论OK_FOR_FINAL_GATE，非验收替身。本轮新入口完整子进程累计3/3已关闭，旧资格3次另账不变。
- **范围与下一项：** VF2只交付固定离线范围；N、真实源/凭据/DB/模型/安装权限均未获得，D009停止决定1475967d与原4/12不变。VF3§6及三例来源身份已桌面核对并获独立审阅接受，不追认H0/D1/旧任务验收。性能收益仍NOT_ESTABLISHED，B0仅人工覆盖声明，不是历史耗时；VF5下一批处理对照与交付说明，VF4仍为独立未完成项。本段仅登记交付状态，不改变已测三文件或§6行为规则；不是原TaskSupervisor验收、发布或运行生效。
