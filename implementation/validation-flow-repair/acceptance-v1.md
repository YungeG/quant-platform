# 验证流程修复：Platform本地交付记录 v1

**状态：工程组合已通过；本交付说明获独立审阅ACCEPT_LOCAL_LIMITED。VF5改善门仍NOT_ESTABLISHED，完整VF5与整体路线图未完成。**

交付范围为VF1验证器、VF2固定离线范围及VF3文档规则。当前工作区是已有大量改动的本地候选，不是clean clone、发布、安装或原TaskSupervisor验收。VF4在独立仓库，未实施，不阻塞本地说明交付；整体路线图未完成。D009停止决定`1475967d`、原4/12及失败账不变。

## 1. 当前结果与准确范围

| 项目 | 已观察证据 | 不证明什么 |
| --- | --- | --- |
| 控制/兼容回归 | 140项通过，4.24秒；Ruff F通过 | 不代替P/C或全树回归 |
| 独立self CLI | host检查成功，内部固定两检查/五node通过 | 不是研究通过或源资格 |
| 当前固定offline-pc | 98项通过，3.24秒；98唯一收集项、294阶段报告；意外guard事件0 | 不授N、实源、模型或发布权限 |
| 身份 | 当前三文件、46项目模块及配置前后绑定；13依赖元数据稳定；27外层保护文件一致 | 非完整安装代码/native真实性，不识别中途改后还原 |
| 三类plan CLI | 普通说明/局部proxy/公共接口返回3/3/2，必需义务选择缺失均0 | plan没有执行任何目标检查；非零预期码不是业务PASS |
| VF3 | 五项开工清单、H0/D1/D009三例桌面核对及独立审阅通过 | 不追认旧失败、不把用户停止变成任务完成 |

当前完整工程gate：`/tmp/platform-vf2-entry-xmc_v96b/parent-final/result.json`，SHA256
`dcdf47167f6b42d357700d669d6f35d5df8a7a94199e8283e2baf58681110eaf`。
直接最终host命令退出0；状态`LOCAL_FINAL_GATE_PASSED`。原生任务验收、发布和运行生效均未发生。

## 2. 版本绑定

| 当前文件 | SHA256 |
| --- | --- |
| [tools/validate_change.py](../../tools/validate_change.py) | `326da060e95bb12d45f29952716e200f2a2b5c5a1833f8f45ed99f456b3cadf8` |
| [tools/validation_offline_pc.py](../../tools/validation_offline_pc.py) | `e26e50e05efc92b2bded24c8d4d0f195036da7fac51683e54d5bd6206d4708b5` |
| [tests/validation/test_validation_profiles.py](../../tests/validation/test_validation_profiles.py) | `961a1a4420815d876d8ddd965f95e2316631deb969415363e623109c3563768b` |
| [既有VF1测试](../../tests/validation/test_validate_change.py) | `2a00b5545c183b1e162e5ba107da8dbfb6fd3086673353101b8cfddfcf310958` |
| [pyproject.toml](../../pyproject.toml) | `c33c31e91a80ca5c56b1b5ccf1356c18dd8deff28ca07a0605a15448182e0aab` |
| [uv.lock](../../uv.lock) | `77e015a4b69f4bce62f61170dc80201a0abee51fd2b4e507819cfd0f4d8a3e5f` |

被测fixture/配置五份pin、13项依赖版本和46模块路径是固定资格范围。获准修改的既有生产源码使用每次实际前后字节；新增模块、fixture/配置或依赖资格失配会阻断，不能复制旧hash放行。没有跨版本自动复用。

本轮VF5只写本文件与[计划](../plans/validation-delivery-flow-repair-v1.md)，不改上述源码、依赖或既有研究结果；本说明是交付输出，不反向成为上述工程gate的输入。

## 3. B0对照：选择与参考编排，不是历史提速

B0是预先记录的**人工必需覆盖声明**：`/tmp/platform-vf2-uk2zlf0r/b0.json`，不是历史执行日志。历史耗时原本为UNKNOWN。VF5使用同样的三个path/role重新调用plan，输出见`/tmp/platform-vf5-32qkqmnw/comparison.json`，SHA256
`6ba1fb3dcd522c67f2b0193d39e1ac96facc9946960a1589272c0189c3f1266f`。

| 相同B0样例 | 必需/实际选择 | 选择缺失 | 当前plan结果 | 实际执行边界 |
| --- | --- | --- | --- | --- |
| `docs/notes/example.md`，informational | D / D | 0 | NOT_RUN，exit3 | plan执行数学/资源检查0；D人工审阅尚未由本样例执行 |
| `experiments/a_share_ingestion/proxy.py`，local | S/P/C / S/P/C | 0 | NOT_RUN，exit3 | 提供一次固定offline-pc入口；本次plan本身不运行它 |
| `experiments/a_share_ingestion/retro_capture_v1.py`，public | S/P/C/N / S/P/C/N | 0 | BLOCKED，exit2 | C跨模块义务保留，N无授权，不得当作全部检查完成 |

D/S/P/C/N是声明的五类义务，不是全仓测试全集。局部选择3类小于五类全集，并包含全部已声明必需项；未知/依赖/fixture/规范文档不会因此静默降级。Scope仍是`DECLARED_ONLY`，不是自动发现全树影响。

### 可证明的条件性结构对照

若把S/P/C三条测试义务**分别启动**，当前固定夹具会产生：S9个参数实例、P57、C41，共107次测试实例，三个测试进程。其中S的9个实例完全包含于P。当前固定入口实际用一个P/C测试进程运行98个唯一node，三个义务全部覆盖；并集缺失0、额外node0。

因此，**相对于“三条义务分开执行”的明确参考编排**，入口可合并2次启动及9次重复实例。它不证明旧操作者确实曾按三个进程执行；B0本身没有记录实际调度。不能称历史测试数下降、真实提速、总开发成本下降或人工往返减少。也不能因3类选择小于五类就声称全仓覆盖充分。

### 当前测量与缺失值

| 数值 | 结果 | 解释 |
| --- | --- | --- |
| P/C pytest摘要 | 3.24秒 | 当前单次、摘要有舍入 |
| 内部守卫child | 4283ms | 含启动、guard/身份和pytest，不与3.24秒相加 |
| offline-pc profile整体 | 4495ms | 含child；child外部分212ms |
| 外部CLI进程 | 4559ms | 包含profile；差64ms，不是另一份总耗时 |
| 历史B0运行/等待/人工介入 | UNKNOWN | 不填0，不用VF1的9ms假子进程作为P/C基线 |
| 历史速度/人工往返改善 | NOT_ESTABLISHED | 未做相同条件的前后运行对照 |

VF5本轮只做3次有界plan CLI，目标检查执行0、新P/C测试进程0。没有为了制造“改善”重复跑已关闭的P/C。此前临时资格的1.67秒与当前3.24秒使用不同守卫/身份范围，不能互作同比。

## 4. 固定使用接口与失败语义

以下为以后有有效工作范围时的使用示例，不是恢复任何已关闭额度；输出路径必须全新，项目环境缺失不安装、不回退。当前阶段没有新增执行这些示例。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
.venv/bin/python -B tools/validate_change.py --profile self \
  --output /tmp/validation-self-EXCLUSIVE_RUN_ID

PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
.venv/bin/python -B tools/validate_change.py --profile plan \
  --scope /absolute/path/to/bounded-scope.json \
  --output /tmp/validation-plan-EXCLUSIVE_RUN_ID

PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
.venv/bin/python -B tools/validate_change.py --profile offline-pc \
  --output /tmp/validation-offline-pc-EXCLUSIVE_RUN_ID
```

- 真CLI引导到项目解释器`-I -B`，import的`main()`不替换调用者。固定cwd为项目根，无任意shell/node输入。普通默认pytest不代表完整research覆盖；self只证明验证器，offline-pc只证明两个固定fake文件，高成本/native验证单独授权。
- `self`：两项通过、身份前后相同、结果持久化/读回且实际host exit0才通过；FAIL1、BLOCKED2，中止130/143。
- `plan`：纯声明处理，可用未执行计划3、阻断2、无效/持久化错误1，中止130/143；没有exit0/PASS/复用。
- `offline-pc`：预检30秒、child60秒、整体120秒/关闭预留10秒，日志2MiB、无自动重试。前置阻断2，检查/覆盖/身份/打包失败1，中止保留130/143；只有两个必需项及全部覆盖/持久化通过才0。原process原因保留，after快照错误列secondary。
- 输出包含`inputs.json/result.json`及有界日志、child报告；除实际Popen参数，还记录安全child环境前后读回。三个线程环境变量为1只表示请求，不等于实测线程数或CPU配额。
- Python audit hooks与已审fake夹具不是OS沙箱；固定祖先目录句柄用于安全遍历，具体文件仍限已核路径，`/dev/null`仅固定capture sink。元数据不是完整已安装代码/native认证。

## 5. 失败、审阅与封账

| 保留事项 | 当前处理 |
| --- | --- |
| VF1首次signal/隔离问题与非-I回归 | 原失败及追加许可仍在旧VF1证据根，未改写 |
| VF2 planner缺值profile错误 | RED、两次反例及受准补丁保留，当前控制回归覆盖 |
| P/C旧临时资格：metadata误拒、cwd错误、补零日志 | `/tmp/platform-vf2-pc-gf5n6x22/`保留；旧3次资格账关闭，不计为新入口通过 |
| 新入口第一次：捕获sink误拒，0 collected | `/tmp/platform-vf2-entry-xmc_v96b/candidate-pc/`，outer/child1；空log不等于无失败，child报告保留 |
| 新入口第二次：目录句柄误拒 | `candidate-pc-2/`，62通过/36失败；未以控制134通过覆盖实际失败 |
| 独立审阅C7原原因被覆盖P2 | `review.md`；六项合成RED后修补，140 GREEN；`repair-review.md`为不可resume后的同角色fallback，结论OK_FOR_FINAL_GATE，非验收替身 |
| 最终新入口第三次 | `parent-final/`，当前98通过；新入口3/3账关闭，不自动追加 |

真实数据、凭据、DB、模型、网络、native启动及公开发行均未因本修复增加。没有stage/commit/push、依赖安装、Pi settings或其他仓库代码修改。仅交付本地候选；旧D009任务及审计账不变。

## 6. 剩余事项与取证限制

- **VF5改善门：** 选择覆盖和条件性参考去重已提供；真实前后时间/等待/人工介入收益未建立。本说明不自行降低原计划改善判据或把未知记通过。
- **VF4：** 控制器诊断在另一仓库，源码范围/安装各需独立许可；未实施，整份路线图不能结案。
- 证据目前在本机`/tmp`，未制作完整可迁移的持久取证包；文档保留了关键hash/命令/失败结论，但不是原始日志替身。原临时证据若丢失，不能仅凭本文伪造回执或声称可完整复查。
- [当前计划状态与未完成项](../plans/validation-delivery-flow-repair-v1.md)为状态入口；[D009未执行终态](../../research/d009-retro-v1-not-executed-result-v1.md)继续有效。

独立只读审阅`e9f8fa23-84e2-4be4-90fc-ba53c57f853c`结论ACCEPT_LOCAL_LIMITED，明确原计划§8改善门NOT_ESTABLISHED；未重跑或独立重算源码hash。原输出的turn-budget wrap-up提示与完整结论一并保留在`/tmp/platform-vf5-32qkqmnw/review.md`。Main终核位置为同根`result.json`，必须结合直接host exit0及文件读回；只核当前源码、文档链接/数值与现有证据，不重复执行P/C、不授旧任务验收。若该终核结果不存在或失败，本文不能自行证明完成终核。
