# 验证流程修复：当前有限交付记录 v2

**CURRENT_FORMAL_PROFILES_PASSED / NOT_FULL_ROADMAP_ACCEPTANCE。**

最新§9：self与offline-pc两个正式入口新增实际exit0及持久原件，当前两profile证据缺口已补齐；旧缺档未重建，原VF5历史门仍未满足。

本版汇总当前可检索证据；[v1](acceptance-v1.md)保留为当时快照，不改写其历史事实。源码实现、实际工程检查、参考benchmark、配置切换、运行中生效及任务验收是不同结论。

**已实测：** 新参考编排合并后，保持98个唯一测试覆盖，减少2次子进程启动及9次重复实例。**未建立：** 旧B0的实际调度、历史总体提速、人工往返减少，原VF5历史门仍`NOT_ESTABLISHED`。不因新参考样本通过而替换旧验收含义。

v2初次收尾及§8审查只读核对和写文档；随后用户独立批准§9新轮次，仅self/offline-pc各一次，没有模型、网络、真实源、安装或重载。各批历史语句按当时范围理解。旧Supervisor已由人类停止；D009停止决定`1475967d`、原4/12及`t-2.1`未完成状态保留，不重启旧监督器或重建任务板。

## 1. 目前能交付什么

| 范围 | 当前结论 | 关键限制 |
| --- | --- | --- |
| VF1执行/结果闭环 | 新正式self实际5项通过、CLI/内层exit0，结果与输入原件已持久留证 | 只证明固定self profile；旧完整gate原件未重建 |
| VF2选择与离线入口 | 新正式offline-pc实际98项/294阶段通过、guard0；规划合同引用R1的3/3/2原件 | 140控制整套及plan CLI本轮未重跑；N仍BLOCKED，无自动复用 |
| VF3开工/结案规则 | [计划§6](../plans/validation-delivery-flow-repair-v1.md)及H0/D1/D009桌面口径保留 | 不追认历史失败，不把停止或未执行伪标任务成功 |
| VF4源码/配置 | 内容哈希快照已配置供未来加载；宿主1.3.0隔离冷注册2/2成功 | 没有完整产品/真实终端验收；本工作未reload当前进程，内存实际版本未独立核定 |
| VF5-P1-R1 | 新前瞻参考样本`VALID_REFERENCE_SAMPLE`，四臂及同输入完整性通过 | 单对A→B、未平衡缓存/顺序；不证明历史或普遍收益 |
| 整份路线图 | 尚未完整验收 | 当前两profile已通过；原VF5历史门仍未满足，旧原件及范围外资格未扩 |

## 2. 新参考样本：已观察的结果

持久根：
`/home/ygguo/.local/state/ai-crypt/validation-flow/vf5p1/run-r1-20261021T054336Z-b2f22665/`

| 项目 | 分开参考A | 合并参考B |
| --- | ---: | ---: |
| child数 | 3：S/P/C | 1：PC |
| 实际测试实例 | 9＋57＋41＝107 | 98 |
| 唯一node | 98 | 98 |
| 缺失/额外唯一node | 0 / 0 | 0 / 0 |
| 本对父级墙钟 | 6926.896ms | 4614.629ms |
| 子进程时长合计 | 6280ms | 4328ms |

四臂均actual exit0，合计615个setup/call/teardown阶段报告完整passed；意外guard事件0，共同源码/配置/依赖和安全环境前后一致。S是P的9实例子集，故这份参考中实际减少9次重复实例及2次启动；不是减少必要覆盖。

父级墙钟已经包含子进程时长，不重复相加。仅一次A→B，OS/pagecache与顺序偏差未平衡；只能描述本对B较短，不报统计显著性、普遍提速或年化收益。临时参考harness不是生产公开CLI，不能把其耗时改标签为公开入口总耗时。人工介入及外部等待收益仍`UNKNOWN`。

同轮三份纯plan为D / S-P-C / S-P-C-N，实际退出3/3/2；目标检查执行0，N仍BLOCKED。它们核选择合同，不是三类业务检查都已通过。

| 可检索文件 | SHA256 |
| --- | --- |
| `result.json` | `69455875800395005450d17b77b61fa044d4d917ab4d60dd9b9bc0e29c014d2e` |
| `comparison.json` | `b9b61e1323b749d6abbad9efba6ad9892dee20aee846a98189dc52f03f65b560` |
| `close.json` | `36d5850f03b67f203508e5b9d20a31d181aa707f69ce69b844598b5ecf5d1aa5` |

本轮4/4 pytest、3/3 plan已封账，无余量结转。样本的`verification_passed=false`、`reuse_allowed=false`：不是生产validation、研究publication或原TaskSupervisor验收。

## 3. 保留失败，不追认旧样本

首轮证据仍位于：
`/home/ygguo/.local/state/ai-crypt/validation-flow/vf5p1/run-20261021T041334Z-185a092e/`

其A-S实际9项通过，但harness把pytest调用后被项目addopts展开的可变argv，与原始列表错误地比较，parent整体exit1、样本`INCOMPLETE`；A-P/A-C/B-PC未运行。该轮1/4测试、3/3 plan后关闭剩余3测试名额，不退款。

R1经用户明确批准为独立新轮次，只在新私有harness拆分`pytest_argv_requested`和`pytest_argv_effective`，根据已pin项目addopts分别核对。旧controller、child、报告、失败和关闭账保持原字节，没有重分类成成功。纯契约自检的正确例与7类坏报告检查不算实际benchmark；其准备检查脚本缺少v绑定的NameError也已留在R1执行卡中，不隐藏。

首轮`result.json` SHA：`dafa02b00394bf3a6915f7ae00d5fb2b52b9bc1519a2fe645469f1960e73a633`。
诊断`comparison.json` SHA：`b7799087a6df77b92505b1e6799e5b43353dcea36b2e1e92ca6934c9f2f52239`。

## 4. VF4配置与恢复留证

配置中的Supervisor来源仍匹配下列不可变本地快照，磁盘manifest与当前配置在本次收尾只读核对时相符：

`/home/ygguo/.pi/agent/local-packages/pi-task-supervisor/vf4-sha256-a6c1391f6215faa9eba5df056bdf6ae7e2e4f8690c774a0d44d89d4ec871a7ce`

54个包文件、760948B；payload文件0444、目录0555。不含tests/.git/node_modules，不指向可变工作树，不是新git commit。旧974快照保留，仅一条个人settings的source字符串改变；其他包/过滤未变，`npm:@tintinweb/pi-tasks`的extensions仍禁用。

| 配置/安装事实 | 身份 |
| --- | --- |
| settings切换前及原字节备份 | `26698c6a05f2a6844d02768ab8aaf53fedbef2573ad9e7fef6311a80a1e361fe` |
| settings切换后，v2初次收尾时匹配（最新身份见§8） | `cd185fc8acb05403a2e77054ae9c7401e3d3d2c6a778aa7f6a328940b7a5f234` |
| 安装`install-result.json` | `98bd4ec64991aeb57411450954badb697c48a2cedc50eac01bbac8720f4420c4` |

备份与持久证据分别在快照父目录的`vf4-install-backups/ijgwk29v/settings.before.json`及`evidence/`，前者0600；证据9文件23844B、文件0600/目录0700。

首次安装预检发现临时执行卡/manifest/源码通过记录原件缺失，实际0cold/0配置写入并停止。后按独立恢复授权`d418b53b`恢复出与原完整hash等价的执行卡9e718…和manifest a6c139…，保留缺档失败；没有重造旧PASS JSON或日志。原安装许可`98da48ae`与恢复许可分开，cold总计仍2/2，未重置。

随后实际宿主SDK1.3.0小扩展smoke/精确候选注册分别exit0、617ms/1409ms，errors/warnings/guard观察0；只注册，不创建AgentSession、prompt、执行命令或触发session hooks。它不是源码SDK1.1单测的替代，也不是完整1.3行为/人类批准/业务兼容认证。

**本工作没有调用当前`/reload`或恢复原会话。** 配置来源和磁盘hash不证明当前内存加载版本；若要在当前或新会话激活/核验，应另按实际操作范围处理，不能自动恢复D009。

## 5. 输入身份与边界

本次收尾重新只读核对R1运行卡中的7个runtime/fixture/config pin，当前字节匹配：

| 输入 | SHA256 |
| --- | --- |
| [执行器](../../tools/validate_change.py) | `326da060e95bb12d45f29952716e200f2a2b5c5a1833f8f45ed99f456b3cadf8` |
| [P/C helper](../../tools/validation_offline_pc.py) | `e26e50e05efc92b2bded24c8d4d0f195036da7fac51683e54d5bd6206d4708b5` |
| [proxy fixture](../../tests/research/test_a_share_ingestion_proxy.py) | `e74298c88d9e0ec2088a86ba6a374664c266c173ef3ce574e7842d838966c2ba` |
| [capture fixture](../../tests/research/test_a_share_retro_capture_v1.py) | `8b8f6f812abc574c48eb1bc610b13e0ef62c4bb6ddf3f3c369679e51564b66fc` |
| [research conftest](../../tests/research/conftest.py) | `385b36bb23043a5d5439287f52f130ebd7289a6eda5add3be8c182d54d2a3456` |
| [pyproject](../../pyproject.toml) | `c33c31e91a80ca5c56b1b5ccf1356c18dd8deff28ca07a0605a15448182e0aab` |
| [lock](../../uv.lock) | `77e015a4b69f4bce62f61170dc80201a0abee51fd2b4e507819cfd0f4d8a3e5f` |

这些不是全树身份或clean-clone认证。本地工作区仍含既有未提交/未跟踪工作；没有替用户stage/commit/push。固定guard、46模块及13项发行包元数据是有限边界，不是OS沙箱、恶意native防护或完整安装代码真实性证明；前后hash也不识别中途改后还原。

## 6. 当前不可检索的历史原件

本次只读检查确认，v1引用的VF1、VF2 planner、固定入口组合、VF4源码及VF5说明终核共五个`/tmp/.../result.json`已不存在。曾观察的host通过与原hash仍是历史记录，但没有把本文/hash当成原始回执，不称可完整复查，也没有在本次收尾补跑或伪造。

本版以当前仍可检索的R1、首轮失败、安装/恢复持久证据为主要依据；不将其转成另一版本的历史源码PASS。后续任何必须依赖缺失原件的动作，需先明确真实证据/有限新资格路径，不能请人类把缺证据批准为通过。

## 7. 收口建议

到此停止追加参考benchmark：已经回答本次有限参考去重问题，再多一次样本不能恢复旧B0历史。当前可交付的是工程实现、有限实际参考收益及未来加载配置，不是整份路线图或旧研究任务验收。

原VF5历史收益、真实人工往返改善、整体研发成本下降及当前进程实加载版本继续保留未证。若以后有新的业务/工程目标，先定义新范围与需要的证据，不重开旧额度，不重建原D009板。[当前计划状态](../plans/validation-delivery-flow-repair-v1.md)与[D009未执行终态](../../research/d009-retro-v1-not-executed-result-v1.md)保持各自含义。

## 8. 对照原目标的总体验收差距核对（新终核前的只读审查）

**结论：有限本地候选可交付；当前正式工程验收与原整体验收均未闭合。** 这不是新增路线图、任务板或验收标准。本轮仅核计划要求、固定入口收口/选择代码和现存证据；没有重跑、完整代码审计或新的独立审阅，不能据此宣称零缺陷。

| 原目标/验收要求 | 核对结果 | 处置与负责人 |
| --- | --- | --- |
| 固定入口、失败/停止不被包装成成功 | 源码有固定self/plan/offline-pc、原进程结果保留、exclusive写入/fsync/readback和非零退出；9个当前源码/测试/配置pin匹配 | 实现已交付；这是静态核对，不是新的行为PASS。本轮没有发现扩写架构的依据 |
| 当前版本正式离线路径及证据可复查 | 既往组合终核含正式入口和反例，但五份临时原件确已缺失；R1经私有参考harness，不是正式入口新终核 | **工程验收必须补的证据缺口。** 若继续正式验收，由Main新建一次有界、持久留证的组合终核，核既有验证器/选择反例及正式离线入口、真实host退出和身份。不得重建旧PASS；历史额度全封账，本轮不启动新进程 |
| 必要覆盖不遗漏、去掉重复检查 | R1当前可检索：98唯一node不缺、3→1child、107→98实例；三类plan退出3/3/2，N仍BLOCKED | 参考范围内成立，不再追加benchmark；不能扩大成生产CLI全耗时或全部研发成本收益 |
| VF5相对旧B0减少重复/人工往返 | 原B0缺真实调度/人工往返历史，现有资料无法建立原判据 | **原整体验收仍未满足。** 不是多做样本可修复的代码故障；不自动改标准、不要求批准缺证据为通过。以后若改目标/接受口径，须用户明确决定；一次新正式工程终核也不会让本项通过 |
| VF4诊断及部署层次分开 | 历史源码通过原件缺失；已配置内容哈希快照及两次1.3冷注册原件可检索，内存加载版本未知 | 不为Platform离线交付去重载/恢复原会话；独立运行态或源码重新资格若有实际需要，再按该范围处理，不转成当前主线 |
| 正确结案、不过度执行 | VF3清单/三例口径保留，D009停止报告hash不变；没有旧任务完成转换 | 本轮只读核对和文档纠偏完成；原4/12、失败/耗用/停令保持，不重启旧Supervisor |

**本轮发现的配置变化：** 总验收核对时个人settings整体SHA已为`f7fbbf968ce398eb0e983153b81451815bb46c78a44c9753786780e0501980d1`，不同于安装后的cd185…；首次元数据核对因此实际exit1（AssertionError），没有把它改称通过。随后只读确认Supervisor唯一source仍是a6c139…快照、54个payload字节仍匹配，变化归因及其他设置语义未核定；没有恢复、覆盖或修改settings。§4的cd185…是安装及v2初次收尾时的历史身份，不能继续标为当前整文件身份。

**明确收口：** Main已完成这轮获准的只读差距检查及两份文档纠偏，没有新测试/benchmark/cold/reload、源数据、网络或模型操作。下一项若要消除工程验收缺口，只应是上述一次新授权的正式入口持久终核，不是更多参考实验或新框架；未获该实际执行范围前不运行。即使该工程终核通过，原历史VF5门仍保留未满足，整份原路线图不能自动标完成。

## 9. 当前两个正式入口：新增持久终核已通过

用户批准“按照这个方案推进”后，Main仅执行self→offline-pc各一次：最多2个pytest进程、总300秒、留证≤12MiB、无重试/修补重跑。旧Supervisor已停止，此批准是独立聊天许可，不制造原生批准回执、不重启旧板或借用旧额度。先self作为固定入口最小实际小样，通过后才运行已核定的两文件offline-pc。

**直接host exit0，状态`CURRENT_FORMAL_PROFILES_PASSED`。** 两次实际CLI均使用项目-I/-B解释器、固定项目cwd、显式干净环境；各自完成预检、执行、输入前后一致、结果持久写入及读回。

| 正式profile | 实际CLI / 内层exit | 验证结果 | CLI墙钟（含内层，不与总墙钟相加） |
| --- | --- | --- | --- |
| self | 0 / 0 | 固定5个契约node通过，两个必需check完整 | 1496ms |
| offline-pc | 0 / 0 | 98唯一node、294阶段报告完整passed，意外guard事件0，S/P/C已覆盖 | 12967ms |

控制器在写总结果前记录耗时14532ms，含上述两次CLI、不含其后清单/关闭记录写入；不是完整host墙钟或历史/普遍性能比较。13项发行包元数据、46个已知项目模块及各profile前后身份闭合；额外9个源码/测试/配置pin及2个保护文档前后一致。没有改生产/测试/依赖/个人settings，没有计划CLI、benchmark、网络、真实源、模型、安装或重载。仅在受控进程结束后清理本轮独占输出下的合成P/C临时夹具；不归档夹具/凭据/缓存，bytecode前缀保持空。

**持久根：**
`/home/ygguo/.local/state/ai-crypt/validation-flow/formal-entry-20261021T064118Z-79ab3b43/`

| 关键原件 | SHA256 |
| --- | --- |
| `execution.json` | `fecb2883e9054dbff244101965c62dc60f5d3bafa895c070c47d742a69d85a46` |
| `result.json` | `67aac0f0bcf2397c307d7ccd7dd0fc0984b3bd05a676a8e70eae134062637126` |
| `manifest.json` | `351498e735803c0b09517c2acc13d1c46d03a42a1b31d19a890327b660976c77` |
| `self/result.json` | `29b8f3e0804c9900af589b8572749c56b290f758afbfa80cce1de5f30dfd14a1` |
| `offline-pc/result.json` | `4f25f215f0393c7acb76eb924a96fdf0a75a25b93d737bfe7cd95e4730308a5f` |

23个文件合计261628B（含manifest），文件0600、目录0700；含实际argv/cwd/明确Popen环境、真实整数exit/时长、原样有界日志、输入前后原件、child阶段报告及关闭账。只读后查核实清单所有hash、实际文件集合/字节/权限、前后身份与两入口结果一致；这不是另一次测试或另一个独立reviewer。

**收口边界：** 当前两个正式profile的可复查证据缺口已补齐，本轮2/2 pytest额度关闭、无余量结转，不再追加执行。没有重建旧五份临时原件，没有重跑140控制整套；N、实源、完整产品/安装代码真实性、自动复用与原TaskSupervisor验收不在范围。原VF5历史收益继续`NOT_ESTABLISHED`、当前进程Supervisor版本仍未核定；D009停止、原4/12及所有旧失败不变，不能据此自动宣告整份原路线图完成。
