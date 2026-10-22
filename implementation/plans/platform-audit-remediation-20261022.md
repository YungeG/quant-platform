# Platform 全项目审计整改施工计划（2026-10-22）

> 本文件是施工方案，不是完成验收记录。用户已追加授权：**“按照设计文档推进至完成”**。本轮据此执行核心整改、AR-08及必要合成验证，采用最多3条隔离写入线；不自动启动需另行授权的AR-10真实市场实验、采集或部署。
>
> 状态权威仍为 [roadmap registry](../roadmap.md#2-status-registry)。由集成负责人统一登记节点状态，本文不建立第二份可变状态表；计划、READY、子任务交付均不代表已通过验收。

## 1. 目标、范围和工期判断

**目标：修复错误接受和恢复问题，统一一个默认可运行版本组合，让一条真实研究闭环正确、可恢复、可重跑。不是推倒重写，也不是增加更多审批层。**

| 交付层级 | 建议并行工期 | 单主线串行估计 | 完成意味着什么 |
|---|---:|---:|---|
| 第一批高风险修复 | 1–2工作日 | 2–4工作日 | 样本存储、模型时点、T+1等优先反例转为负测并关闭，不代表所有整改完成 |
| 核心整改＋跨模块验收（AR-00～AR-07、AR-09） | **4–6工作日** | **8–12工作日** | 约50–80人时预算，含复核、集成及约20%不确定性余量；不是仅有代码提交 |
| 加可移植复现和门禁操作简化（AR-08） | 上述之外约0.5–1日，可部分重叠 | 约1日 | 探索使用流程更顺畅，旧证据仍可精确恢复 |
| 一条真实策略工程闭环（AR-10） | 核心验收后再1–3工作日，**前提是已有合格数据与公开prepare能力** | 同左 | 验证研究工具可用，不承诺策略有正收益 |
| 新的前瞻样本外效果验证 | 另行估计 | 另行估计 | 要等待足够未看交易日、明确样本量及资格，不会因多开代理而加速市场时间 |

这里的工作日按约8小时工程投入计，估算不是自动代理运行时长或交付保证。并行建议为最多3条隔离写入线＋主控集成/独立复核。若候选来源验证需要较大公共接口迁移、旧版兼容重构，或需要新增供应商证据，核心工期需重新估计；不能把缺证据算成“等用户批准一下即可通过”。

**总体预期：一周左右取得核心工程整改版本；在数据前提满足时，约6–9工作日连同真实工程闭环。稳定盈利不在该工期承诺内。**

## 2. 单一事实来源

| 材料 | 职责 |
|---|---|
| [只读审计报告](../../reviews/platform-audit-20261022.md) | 审计发现1～14的原始事实、源码位置、行为复现及目标限制；不随施工结果改写历史 |
| 本文 | 未来行为约束、依赖、写入归属、验收和并行安排 |
| [roadmap](../roadmap.md#2-status-registry) | 开工后唯一可变状态权威；本方案中的依赖不是已通过状态 |
| `/srv/bcache-8t/ygguo/quant/platform-audit-20261022/` | 已存在的脚本、日志、inventory、audit receipt及`evidence_manifest.json`；不依赖原`/tmp`存活 |
| 未来节点验收记录 | 施工后才创建，写明真实子模块commit、执行命令、失败/通过、产物hash、剩余限制；不得预填通过数 |

原审计基线：Platform `f578fe0`；Backtest `3ab6bfd8`；Foundation `9d88ed6`；Research `de8b2c4`；Validation `e87d98bc`；Promotion `8e6dddf`。施工前重新核对工作树与所有HEAD；变化由主控分类，不覆盖其他会话改动。

原基线实测：默认根测试1092通过/4失败；显式当前源码四个治理子项目737通过；Backtest窄测试66通过；`self`通过；`offline-pc`71通过/27失败。测试范围有重叠，不能相加当覆盖率。已保留11个定向行为样例及候选来源例子；其中账户全book覆盖是合同问题，不直接当作代码bug修改。

## 3. 不可改变的约束

1. Backtest仍唯一拥有成交、费用、核算、指标派生、结果等级和证据验证；Platform不能另写金融模拟或收益算法。
2. 跨子项目只经已接受的公共根接口。候选来源校验若需要新公共Interface，必须先明确归属、输入/输出和失败语义，不能由Validation私自导入Research内部函数。
3. 旧artifact、原始字节、schema、hash、receipt和历史结果保持原样。修复使不合法对象不能继续进入新的结论链，不是回写历史报告“变正确”。
4. 不补写伪造的事前样本预约；缺证据保持失败/未知；已查看样本不会因换日期、改seed或删除工作树变成盲OOS。
5. 保留必要门禁：PIT/单位/行动完整性、完整实验、事前样本预约、原子发布、等级隔离和执行预算。
6. 普通探索不强制走完整Promotion；`SUPPORTED`不等于盈利，`shadow_ready`不等于交易授权。
7. 不删除供应商资格要求来“解阻”，不盲改SDK pin，不修改旧golden使失败看似通过。
8. 本方案不包含真实供应商采集、大规模数据读取、付费采购、Shadow/Live或实盘订单。此类工作需要单独明确范围与授权。

## 4. 先解决的三项设计决定（AR-00产物）

| 决定 | 必须固定的内容 | 建议方向；谁负责 |
|---|---|---|
| D1：同一存储的定义 | ledger与Foundation的权威身份；两个对象指向同一存储是否可接受；检查失败时不得已有发布/读取 | Validation拥有ledger约束。优先复用现有存储绑定约定，禁止Research读取Validation私有字段；主控提出最小公共检查，经接口复核冻结 |
| D2：完整候选来源的验证seam | 谁重建Experiment任务全集、截止点、attempt/closure和selection；精确输入、返回对象与失败映射 | Research持有实验语义；Validation消费权威校验结果。复用`validate_execution_prefix`等既有算法，不能各写半套；公共出口签名需在开工包固定，当前不冒称已有该出口 |
| D3：Analysis的Verified承诺 | 从link-only提升到来源指标一致性，适用于v1/v2的范围；有效旧artifact及调用者兼容 | Backtest-owned verifier复用已有纯派生实现，原则上不新增schema；涉及现行冻结契约文字的差异先列明并获接受，不以普通重构偷偷改变承诺 |

不需要用户提供代码、依赖或联系“模块负责人”。主控代理取得已有资料并提出具体选择。只有不可兼容的合同/范围选择才交用户决定；未决D1/D2阻塞AR-01/02相应共享seam，D3仅阻塞AR-04中的指标部分，不阻塞独立的T+1、模型时间和输入校验。

Binance未来band覆盖及H3 funding因果合同另列为评估项：先明确目标，不预设“删门禁就是修复”，也不让该外部语义问题阻塞本轮独立代码修复。

## 5. 依赖图：可以并行，但不是所有步骤同时写

```text
AR-00：基线＋最小合同/版本方案冻结
  ├─ A线：AR-01 样本存储绑定 → AR-02 报告与完整候选来源
  ├─ B线：AR-03 T+1数量      → AR-04 模型时点与Analysis校验
  └─ C线：AR-05 数据输入     → AR-06 Promotion恢复（前项交付后换任务）

AR-01…AR-06 已验收的leaf提交 ─→ AR-07 版本/SDK pin重新接受
AR-00 + 历史源码归档        ─→ AR-08 复现与操作简化（可选，利用空闲槽）
AR-01…AR-07                ─→ AR-09 单写者集成与跨模块验收
AR-09 + 真实数据/prepare证据 ─→ AR-10 一条真实策略工程闭环（另行授权）
```

AR-07的盘点和临时测试环境设计可在AR-00期间准备，但最终lock/pin必须等待leaf的真实commit，不能事先假填。AR-08不是核心正确性修复的前置条件；纳入本次交付时再加入AR-09验收范围。

### 关键边的类型

| 上游 → 下游 | 类型 | 跨边材料/真实原因 |
|---|---|---|
| AR-00 → AR-01/02/04 | Contract | D1存储身份、D2来源验证、D3指标验证的行为及失败契约；只阻塞相关子项 |
| AR-01 → AR-02 | Contract＋Write conflict | ledger可用的存储绑定保证；共享Validation runtime/integration文件须同一A线顺序编辑 |
| AR-03 → AR-04 | Write conflict/排班 | 同一个Backtest写入槽保守串行；金融上可独立。如确认write set和公共导出完全不相交，可用隔离worktree重排，不伪称合同依赖 |
| AR-05 → AR-06 | 排班，不是语义依赖 | C线先完成数据校验，再将写入槽交给Promotion；可与B线交换任务，但全局最多3个writer |
| AR-01…06 → AR-07 | Evidence | 已接受leaf提交、最终公共接口及真实代码hash；pin必须消费真实结果 |
| AR-01…07 → AR-09 | Evidence | leaf测试、反例回归、版本组合；单写者更新root引用、集成夹具和最终验收 |
| AR-00/归档 → AR-08 | Evidence | 已有完整源码归档、旧hash及恢复约束；不改旧证据 |
| AR-09/数据能力 → AR-10 | Contract＋Evidence | 修复后的公共prepare、符合目标的MarketBundle和真实未看样本；不是仅等待审批 |

## 6. 节点施工包

下列是有明确结果的施工切片，不是按文件行数拆任务。**编码启动前，主控仍需为共享seam补齐符号级Full packet及首个RED测试；本文件本身不把未选定的Interface标成READY。**

### AR-00｜基线、版本方案和共享合同冻结（4–6小时）

- **结果：** 一个明确的测试包来源组合、D1～D3的可审阅差异，以及每条写入线的固定输入。消费上述audit inventory和真实失败日志。
- **Owner/write set：** 主控负责Platform根配置设计与合同/验收草案；此步不擅自修改已接受子模块代码，不运行`uv sync`覆盖现环境。
- **施工：** 区分默认已安装8cc5包与当前3ab6源码；确定目标来源/版本，不一边用新源码一边宣布旧环境通过。为每个writer创建隔离分支/worktree及独立临时环境，校验实际import origins。
- **验收：** 首个smoke的解释器、源码、依赖和测试目标可复核；D1/D2/D3分别有签名/结果/错误/兼容约束；共享文件与集成归属明确。设计未决项不阻塞独立节点。
- **排除：** 不把四个旧架构红灯简单改成通过；不刷新既有证据时间。

### AR-01｜样本预约与读取属于同一权威存储（3–5小时；发现1）

- **调用链：** `execute_experiment/execute_model_experiment/execute_target_experiment → _reserve_slice → Backtest/materializer`；同时检查Validation相关公共入口，未复现的同类入口先写反例确认。
- **Owner/write set：** A线；`research-platform/.../runtime.py`、其公共root仅在D1必要时更新；`strategy-validation/.../ledger.py`及相应入口/测试。Foundation storage保持不变，除非明确证明现有Interface无法表达存储身份。
- **结果：** 外来ledger在任何受保护发布/样本读取前被拒绝；合法同存储调用继续工作，不允许事后补预约。
- **首个RED：** 将审计中A=0、B=5的公共错配用例改为“拒绝且执行次数0”；覆盖普通/模型/target及验证入口的适用检查。
- **验收：** 正常预约/重复预约/回放字节不变；错误存储不产生候选或读取；原样本记录不迁移伪造。

### AR-02｜报告回放及完整CandidateFamily来源（8–12小时；发现2、7）

- **Owner/write set：** 同一A线，顺序接续AR-01；Research既有`validate_execution_prefix/build_candidate_family/select_candidate`的公共验证出口（D2先固定），Validation `runtime.py`的`_candidate_graph/_existing_report`与`integration.py:_candidate_graph_status`，相关shell/integration测试。
- **结果：** 缺失CaseResult/assessment、错误plan链接、遗漏Trial、无attempt/closure、截止后追加任务或事后选择，均不能得到可用正式报告。
- **施工：** 回放精确读取原计划、必需case、sample assessment、Backtest证据，并复算报告派生字段；来源验证只维护一个权威算法，经公共seam消费，不导入Research私有实现。
- **首个RED：** `provider_failure → NoReport → 手工发布空case的supported → replay`必须拒绝；`experiment={fixture:one}`无尝试链也必须拒绝进入正式验证。
- **验收：** 真正完成的合法候选仍可验证；重复加载不新增经济运行、不重新消费样本、不刷新治理时间；v1/v2/v5适用路径与v6不回退。
- **兼容：** 简陋fixture不能靠放宽生产验证保留；改为合法来源夹具或明确纯核测试。

### AR-03｜A股T+1数量单位与标的一致（3–5小时；发现3）

- **Owner/write set：** B线；Backtest trading-kernel的`portfolio_sellability_v1.py:project_cn_a_share_portfolio_sellability_v1`、`portfolio_order_plan_v1.py:CnASharePortfolioOrderPlanV1`及对应测试。
- **结果：** 裸`units`不再跨scale/Instrument比较；非法表示不能生成同日卖出计划。
- **首个RED：** Ledger的10000/Scale(2)与未结算100/Scale(0)必须拒绝，不能产生99股可卖；另测相同scale但不同Instrument及预留量。
- **验收：** 沿用该A股组合接口的整数股前提，明确异常在计划前出现；节假日T+1、零股/整手、已有正确卖出和现金约束不回退。
- **排除：** 不改费用、账户核算或通用Quantity经济语义；不新增第二套数量换算体系。

### AR-04｜模型时点与来源指标真实一致（5–8小时；发现4、5）

- **Owner/write set：** 同一B线；Backtest runtime的`cash_development_provider.py:prepare_model_bound_cash_development_backtest`、`evidence_repository.py:load_analysis/load_analysis_v2`及既有`analysis_derivation.py`必要纯函数复用；模型provider和仓库测试。D3及必要合同文本由Backtest owner串行维护。
- **结果：** 模型available_at不得晚于实际target决策；指标必须可由所引用completed结果派生。
- **首个RED：** 决策100/模型150/timeline200在写入前拒绝；相同UTC更晚phase/sequence也拒绝。真实来源链接＋999999笔/收益999的analysis不能成为可用Verified分析。
- **验收：** 准确边界允许；未来revision不改变早期模型选择；v1/v2有效旧分析字节/身份不变；返回类型兼容；重验复用Backtest纯派生函数，不运行第二次回测、不写新artifact替换旧记录。
- **前置分离：** 模型时点子项只依赖AR-00的时间约定；D3未决不得拖住它。

### AR-05｜输入终态、checksum及采集时间（4–7小时；发现6、10、11）

- **Owner/write set：** C线；Backtest Builder的`tushare_000703_dividend_action_set_v2.py`、`source_snapshots.py:verify_source_snapshot`、`tools/acquisition/binance_usdm.py:main/acquire_*`和窄测试。不碰B线runtime/trading文件，不同时改公共导出或包配置。
- **结果：** 未终态分红页不能成为权威空集；声明checksum矛盾失败；acquired_at不早于对应字节取得。
- **首个RED：** 分红`items=[]/has_more=true`并重算receipt仍拒绝；declared hash与provenance同步变更仍拒绝；fake transport使时钟100→200后，receipt不得记100。
- **验收：** freeze/verify条件一致；code/count/分页/行数错误均覆盖；archive与checksum分别记录取得时间；已有caller显式时间语义如需扩展须先固定兼容接口。
- **排除：** 不联网、不重新采集历史数据、不改历史receipt；修正本地acquisition不宣称已证明provider历史availability。

### AR-06｜Promotion共享状态及中断恢复（4–6小时；发现8、9）

- **Owner/write set：** C线前项交付后换到Promotion repo；`runtime.py:_evaluate_case/_existing_decision`、`ledger.py`必要转换校验及shell测试。Foundation CAS/log实现不变。
- **结果：** 不同Case复用同一证据时只使用一个有效PUBLISH；Evaluation已提交而Decision失败可恢复为同一闭包。
- **首个RED：** 第二发布者场景不污染后续最新状态；注入Decision append失败，恢复后第三次调用仍可重放、同Case只有一份原Evaluation。
- **验收：** v1 negative和v2 positive适用路径覆盖；重试不产生新治理事实年龄、不重复评估或执行Backtest；非法状态先拒绝再写入，真实未知/冲突不能吞掉。

### AR-07｜默认环境与采集pin升级重新接受（4–6小时；发现12、13）

- **前置：** AR-01～06目标leaf提交已可引用。包来源矩阵的设计可在AR-00提前进行，最终pin不能提前锁死。
- **Owner/write set：** 主控/集成单写者；root `pyproject.toml/uv.lock`、submodule gitlinks、依赖一致性测试、`run_a_share_price_volume_retro_real_v1.py:CATALOG_GOVERNANCE_CODE_PINS`及相关采集合同测试/文档。
- **结果：** 默认导入与被接受版本组合一致，标准offline-pc不再因合法ledger升级一进入便失败。
- **验收：** 每包import origin和revision有证据；先小smoke，再原98项合成P/C覆盖（测试数量若变需说明）；`self`与`offline-pc`分别报告；root四个架构旧失败得到真实一致性解决，不删断言掩盖问题。
- **兼容：** 历史manifest/pin不改；新增接受清单/版本并明确切换。此处不是通过盲替换SHA来绕过资格。

### AR-08｜可移植复现与门禁操作减负（可选3–5小时；发现14及结构建议）

- **Owner/write set：** 主控或空闲隔离writer；受控复现入口/文档/测试、必要的未来manifest路径解析。旧L2脚本、旧spec和receipt先保持字节不变。
- **结果：** 能按commit/hash找到源码归档，或明确恢复旧路径；新研究不再把机器绝对路径误当代码身份。
- **验收：** 仅用小型保留样本或fake fixture验证不同目录解析、内容变化拒绝、失踪材料明确失败；不重新提取L2、不重新读取巨大行情。
- **门禁简化：** 探索只需范围/来源/已看样本/预算/结果限制；正式验证继续强制样本与经济门；Promotion只在晋级时运行。复用证据是否有效由代码及输入身份决定，不能把重复确认当新保护。
- **排除：** 不建设通用registry、工作流平台、自动凭证系统或泛化策略DSL，不用symlink冒充恢复证据。

### AR-09｜跨模块集成、独立审查与交付（6–10小时）

- **Owner/write set：** 一个主控集成writer；root gitlinks/lock、公开seam集成测试、roadmap状态和真实验收记录。不得同时让多个lane更新根文件。
- **结果：** 一套可从干净checkout构建的候选版本，不依赖前代理的内存、临时目录或旧安装包。
- **验收：** 全部本次反例转为期望拒绝/可恢复的回归；受影响leaf全套及root默认套件通过；研究采集专用路径单独覆盖；保留必要的legacy byte/hash sentinel。
- **跨模块golden：** 一项完整实验进入验证，再进入适用Promotion路径；检查真正任务全集、同存储预约、有效指标、版本分派和失败恢复，不再用缺闭包fixture宣布集成通过。
- **独立复核：** 一名fresh只读reviewer审高风险语义和fix radius，主控独立重跑。不可用/失败的检查仍是阻塞或显式缺口，不写PASS。
- **发布顺序：** leaf测试及commit → 维护者授权范围内推送leaf使gitlink可达 → root更新确切引用/lock → 干净组合验收 → root提交/推送。push/发布权限如未包含在执行授权内，先停该发布动作，不能指向仅本机可见的子模块提交。

### AR-10｜一条真实策略工程闭环（另行授权；1–3日或缺证据阻塞）

- **Owner：** 主控保留财务规则、因果判断和最终Go/No-Go；机械整理可交受限worker，不能让其决定资格。
- **前置材料：** 当前真正存在的公开`prepare_*`能力、保留的已准入MarketBundle、固定策略及成本假设、有限参数/seed/预算、真正未污染的holdout。任一缺失先查证并列明准确缺口，不要求用户替代理找依赖或修文件。
- **结果：** 一条从冻结假设→Research→Backtest→Analysis→OOS→适用Promotion的有界工程证明，或明确、真实的失败/不确定结论。
- **验收：** 先代表性小样本再固定范围；所有试验和失败完整覆盖；经济上有意义的预声明标准；缺少数据不得填零；同输入可重放；本次golden成功不等于策略有效。
- **排除：** 不能用−100%阈值的协议golden当alpha证明；不能拿已看过的9月行情当新盲OOS；Binance H3路线未另行得到可满足合同前不扩采集；不启动Shadow/Live。

## 7. 并行资源与写入纪律

**可以并行，推荐最多3个实现writer，而不是14个发现各开一个代理。**

| 角色/线 | 任务 | 文件/仓库归属 |
|---|---|---|
| 主控 | AR-00、共享决定、证据保管、AR-07/09；最终财务判断 | 根配置/lock/gitlink/registry只有主控写 |
| A线：研究与验证 | AR-01→AR-02 | Research/Validation各自隔离分支；同一文件不能交两位writer |
| B线：回测经济与指标 | AR-03→AR-04 | Backtest隔离分支/worktree；trading与runtime同一owner保守串行 |
| C线：数据→晋级 | AR-05→AR-06 | 先Backtest另一个隔离worktree，仅Builder/acquisition；交付后换Promotion |
| 独立review | 可随已交付节点并行读查 | fresh上下文、只读、不能自改代码或自行批准发布 |

两个Backtest分支只在write set不相交、公共Interface已固定时同时进行。`__init__.py`、共同fixture、pyproject、lock、合同或状态表有交集，先交主控协调，不同时修改。普通单writer路径仍有效；没有并行执行授权或资源不足时自动退回顺序，不能绕过批准门。

施工worktree使用新的独立路径和分支，不自动恢复已退休的L2研究工作树；只有明确的历史复现任务才按归档说明恢复旧路径。

Spark类快速worker适合冻结后的机械测试、夹具和重复修改；时间因果、资金/数量、证据权限、接口和最终接受留给主控或相应强审阅者。首次delegate先核对可执行agent/model，禁止重复使用已被配置拒绝的模型。

## 8. 验收预算与命令边界

- 编辑循环：每个发现一个最小RED/GREEN，先跑同代码/配置的小样本；不以全量作业发现普通导入或schema错误。
- 节点交付：相关直接边界和fix-radius测试；leaf冻结后全模块检查一次，不在每个中间编辑重复完整平台/市场套件。
- 根集成：默认环境检查与显式当前源码测试分开报告。最终接受必须是普通使用者能得到的环境，不能只靠私设PYTHONPATH绿灯。
- 首次读取真实payload、改变数据量/成本或启用网络属于新范围；本轮合成修复不需要市场下载。

基线命令示例（从Platform根，用现有解释器；施工后路径、node IDs与实际包来源需复核）：

```bash
# 默认根工作区：原基线是1092 passed /4 failed，不是预期永远保留红灯
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  .venv/bin/python -B -m pytest -q -p no:cacheprovider

# 两个profile各自创建独占输出；不要误以为self通过就完成项目验收
CHECK_OUT="$(mktemp -d "${TMPDIR:-/tmp}/platform-remediation-checks.XXXXXX")"
.venv/bin/python -I -B tools/validate_change.py --profile self --output "$CHECK_OUT/self"
.venv/bin/python -I -B tools/validate_change.py --profile offline-pc --output "$CHECK_OUT/offline-pc"
```

审计目录中的`run_checks.py/repro_governance.py/repro_backtest.py`已存在，仅作复现入口参考；它们的断言描述**旧缺陷存在**，转为修复负测后应更改预期，不把原复现断言继续通过当成修好了。

## 9. 开工、暂停与最终完成条件

- **已授权执行：** 按本文件完成核心整改和AR-08，采用最多3条隔离写入线。共享合同先由主控固定，writer在对应packet就绪后启动。
- **仍保留的授权门：** AR-10真实市场实验、付费/生产/范围扩张及未包含的远端发布动作。批准范围内的安全可逆步骤持续推进至必要验收，不要求逐文件/逐phase重复确认。
- **只暂停受阻分支：** 未决公共合同、无法满足的来源资格、破坏性清理、付费/生产操作或范围扩张。其他独立已授权节点继续。
- **完成核心整改：** 必修发现均有明确处置与回归，版本/pin一致，相关leaf/root/采集检查通过，独立审查完成，可恢复回放证明齐全；不是“已派任务”“代码已提交”或“所有分支都有一份收据”。
- **真实策略闭环另算：** AR-10必须消费已存在的能力和合格材料，不能用工程验收替代统计/经济有效性，也不能承诺最终盈利。
