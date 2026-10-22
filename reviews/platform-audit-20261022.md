> 归档说明：本报告记录 2026-10-22 在 Platform `f578fe0` 及文中所列子模块版本上的只读审计事实，不是施工完成记录。
> 按用户要求保存；当前只新增文档，未开始修复。原复现脚本、日志和哈希清单已保留至 `/srv/bcache-8t/ygguo/quant/platform-audit-20261022/`，不再仅依赖临时目录。
> 后续施工见 [整改施工计划](../implementation/plans/platform-audit-remediation-20261022.md)。不要修改本报告来伪造历史验收；后续发现及验收另行记录。

# Platform 全项目只读审计：正确性、门禁与目标可达性

## 结论

**What this repo does：** Platform 把数据、回测、实验选择、样本外验证和研究晋级组织成可追溯的离线流程。Backtest 负责经济模拟，Foundation 保存不可变证据，Research/Validation/Promotion 分别管理实验、样本使用和晋级。

假设的负载是个人/小团队、本地文件系统、有限离线研究与合作进程；不是互联网多租户服务，也不以实盘盈利作为既有能力。

**总体判断：方向合理，已有实质性实现；目前不应称为已经达到“通用、可靠、随时可复现的策略验证平台”。** 正常路径测试很多，但存在影响样本记录、证据语义、模型时间和交易数量的缺口。门禁不应整体撤掉，也不应继续按数量增加：要把必要门禁做完整，把探索、正式验证和操作许可分开。

本次没有修改仓库、子模块、配置、依赖或金融规则，没有访问市场供应商，没有运行真实数据实验。所有复现使用合成输入和临时存储；scratch 与报告仅在本目录。用户当前无需操作；修复属于下一项需要另行授权的工作。

## 基线与验证

| 范围 | 本次 HEAD |
|---|---|
| Platform | `f578fe0dcba2449ebaac0839a453593f0971342d` |
| Backtest | `3ab6bfd8c86a3e5a65be645ea733b5c2e382494a` |
| Foundation | `9d88ed67a84d06c558276f8bae2206b069bcec8f` |
| Research | `de8b2c457358c23ceef3039c831b25ff920b0cf6` |
| Validation | `e87d98bc70fadd57eae7dae27e6ddff1055e2763` |
| Promotion | `8e6dddf5da0494b57cca6990d5024fe4198e6b44` |

所有工作树在开始和结束时均干净。审查了根项目与5个子项目；约36万行Python含测试，不是逐行全覆盖。六个分区的静态审查由独立上下文完成，父审计独立运行关键复现并检查源码。两个最初子任务因模型限制在执行前失败，随后在相同只读协议下重试；失败不是通过证据。

实际检查：

- 默认环境代表性 smoke：**13 passed**。
- 根配置默认测试集：**1092 passed、4 failed**，176.58秒。四个失败涉及依赖对齐和旧版集成状态断言。
- 显式导入当前checkout全部源包的 smoke：**13 passed**。
- 当前源码的 Foundation/Research/Validation/Promotion 测试：**737 passed**，120.03秒。
- Backtest代表性 smoke：**2 passed**；随后7个相关测试文件：**66 passed**，27.28秒。
- 官方验证工具 `self`：**PASS**。它只验证验证器自身，不能解释为整个项目通过。
- 官方验证工具 `offline-pc`：**FAIL**，其固定合成采集检查 **71 passed、27 failed**，均卡在治理代码pin不一致。
- 11个定向行为样例已运行：10个确认正确性/契约缺口，1个确认需澄清合同的过严账户覆盖行为；另确认一条不完整候选来源可进入正式报告路径。这些复现不属于修复后的通过测试。
- 上述测试集有重叠，不相加声称独立覆盖数量。Backtest全部测试和所有`tests/research`没有全跑。

## 必须修复：会造成错误接受或破坏证据链

### 1. P1：样本消费可以记到另一个存储，实验仍然执行

- **这是什么：** 读取研究样本前要先记账，之后才能判断留出的数据是否真正没被用过。
- **问题：** `execute_experiment(inputs, Foundation_A, Ledger_B, port_A)`会成功发布候选。实测A的4次执行都看见0条预约，最终A为0条、B为5条。这是公共参数接错对象即可触发，不需修改内部对象。位置：`research-platform/src/crypto_quant_research/runtime.py:943–960,1992–2016,2416–2522`。
- **最小修复：** 入口检查ledger和foundation的权威存储一致；或在执行前从传入foundation精确验证预约收据。参考已有`retrospective_reservation.py:619–621`的同存储保护。
- **不修后果：** 后续可能把已经消费过的样本误当未使用，污染OOS判断。不能用事后补写冒充事前预约。

### 2. P2：Validation回放能接受没有验证证据的“supported”

- **这是什么：** 完成过的验证应复用原证据，不重新跑，但必须确认原证据有效。
- **问题：** 首次provider failure产生`NoReport`后，在正确owner log写入一个字段齐全、`case_result_refs=[]`、assessment指向不存在ref的`result=supported`报告，公共回放返回`PublishedValidationReport`，且没有新增Backtest调用。位置：`strategy-validation/src/crypto_quant_validation/runtime.py:770–799,1058–1062`。
- **最小修复：** 按Plan重验精确CaseResult集合、assessment和Backtest引用，并从既有证据重算result/thresholds；可以复用v6已有恢复校验思路，不重新消费样本。
- **不修后果：** 本地写入程序的错误可以绕过结果语义门禁。这里不是远程入侵或缺少RBAC的指控。

### 3. P2：T+1组合卖出检查混用了不同数量尺度

- **这是什么：** 同一100股可以由100个整数股或10000个百分之一股表示；计算必须对齐单位。
- **问题：** 未结算100股`Scale(0)`从Ledger的10000单位`Scale(2)`直接相减，得到99股“可卖”；下游又只比较裸整数，接受当日100股卖出计划。实测投影与计划均接受，未声称已经执行了非法成交。位置：`backtest/packages/trading-kernel/src/crypto_quant_trading/profiles/cn_a_share/portfolio_sellability_v1.py:104–119`；`portfolio_order_plan_v1.py:117–119`。
- **最小修复：** 在该A股组合入口要求/验证一致的整数股尺度，同时核对Quantity的标的；沿用普通settlement已有的尺度检查。
- **不修后果：** T+1保护可被合法构造的不同数量表示绕过，卖出计划不可信。

### 4. P2：未来才可用的模型可以绑定到过去决策

- **这是什么：** 模型身份进入回测结果时，模型必须在该决策时刻已经可用。
- **问题：** target决策为100，模型可用时间150，调用者timeline截止200；公开prepare、run和load_completed都成功并保留该未来模型。该路径不执行模型推理，所以没有据此声称成交/收益已被改变。位置：`backtest/packages/backtest-runtime/src/crypto_quant_backtest/cash_development_provider.py:914–936`。
- **最小修复：** 在发布request/bundle前，将selected model的完整SimulationInstant与实际target决策时点比较；同时测试同UTC、更晚phase/sequence。
- **不修后果：** 稳定重放会稳定保留错误的时点来源，而不是纠正未来信息。

### 5. P2／契约缺口：Verified Analysis验证链接，却不验证指标

- **这是什么：** 派生指标加载器会向下游返回“已验证”的分析对象。
- **问题：** 保留真实运行、结果hash、grade和metric-profile，只把1笔交易改为999999笔、收益`0.02392`改为`999`，重算规范内容地址后，`load_analysis`仍返回Verified对象。位置：`backtest/packages/backtest-runtime/src/crypto_quant_backtest/evidence_repository.py:2828–2873,2897–2952`。
- **最小修复：** 复用现有`analysis_derivation.py`纯派生函数和fills数量验证指标。不要另写收益算法。
- **不修后果：** 结果链接真实，但用于选策略的数字可能错误。现行文档确实只承诺link校验，所以这是需要提升的契约，不是伪称代码违反现有link-only条文。

### 6. P2：未完成的分红页面可以变成“没有公司行动”

- **这是什么：** 空分红集合只有在请求完整结束后才意味着范围内无行动。
- **问题：** 合成响应`items=[]、has_more=true`，同步重算receipt/snapshot后，公共mapper返回`actions=()`且`zero_row_authoritative=True`。native采集入口会拒绝，但mapper没有同等检查。位置：`backtest/packages/market-bundle-builder/src/crypto_quant_bundle_builder/tushare_000703_dividend_action_set_v2.py:362–385,430–448`。
- **最小修复：** Builder入口独立检查响应成功、分页终态和行数一致，或消费真正已验证的名义类型；不能依赖调用者布尔承诺。
- **不修后果：** 未取得完整行动数据会被当成没有分红，可能遗漏现金流。未证明Runtime grade或部署权限也能被提升。

### 7. P2：Validation只检查被选中的任务，没有验证整个实验闭包

- **这是什么：** 候选应该来自完整实验，不能只展示赢的那两项结果。
- **问题：** 实测现有公共夹具用`experiment_spec={fixture:one}`、只有两个outcome和manifest、没有attempt/closure链，仍产生正式ValidationReport。该例结果是rejected，不是假称已获策略支持；缺的是候选来源准入。位置：`strategy-validation/src/crypto_quant_validation/runtime.py:330–365`、`integration.py:1259–1425`。
- **最小修复：** 对CandidateFamily使用一个按owner-log截止点检查任务全集、尝试闭包及选择声明的权威验证器；不要在各下游复制不同半套规则。
- **不修后果：** 漏掉失败试验、不完整来源仍可能进入后续验证，破坏预先声明实验的意义。

### 8. P2：换一个合法状态发布者就会污染Promotion状态日志

- **这是什么：** 不同晋级Case可以共享同一组证据。
- **问题：** 第一个Case完成后，用不同`status_issuer_ref`开启另一个Case，状态条目从21增至42，然后报`STATUS_CHAIN_MALFORMED`；之后读取最新状态也继续失败。位置：`promotion-gate/src/crypto_quant_promotion/runtime.py:559–564`、`ledger.py:158–164,227–233`、`integration.py:739–741`。
- **最小修复：** 复用同一证据的既有PUBLISH事实，新增状态前验证转换；不要把每个Case的调用者身份变成第二次证据发布。
- **不修后果：** 一次正常的调用者切换就损坏共享状态链，不是简单重试可恢复。

### 9. P2：Decision发布失败后的恢复会制造重复Evaluation

- **这是什么：** 评估已保存、最终决定尚未保存，是正常可出现的中断点。
- **问题：** 注入一次Decision append失败；恢复后重试成功，但同Case留下两个Evaluation，第三次重放报`PROMOTION_CASE_INVALID`。位置：`promotion-gate/src/crypto_quant_promotion/runtime.py:258–261,299–300,519–521,580–609`。
- **最小修复：** 恢复已提交的Evaluation及原checkpoint，只完成缺失Decision，不能重新冻结时间并生成另一个Evaluation。
- **不修后果：** 看似恢复成功，后续审计/重放却永久失败；门禁没有完整恢复语义。

### 10. P2：snapshot验证器允许声明checksum与实际内容矛盾

- **这是什么：** 输入自己声明的checksum是系统能直接检查的事实，不是无法取得的供应商永久最终性。
- **问题：** 改member的`declared_sha256`并同步重算provenance，`verify_source_snapshot`接受它；freeze入口对同样矛盾却会拒绝。位置：`backtest/packages/market-bundle-builder/src/crypto_quant_bundle_builder/source_snapshots.py:410–463`。
- **最小修复：** 非空declared checksum与实际内容摘要作相等检查，使用既有失败码。
- **不修后果：** freeze与verify的输入准入条件不一致，明确矛盾的来源声明可以通过公共校验。

### 11. P2：Binance采集把请求开始时间当作取得响应时间

- **这是什么：** Acquisition time表示本地真正取得字节的时刻，不等于请求发出时刻，更不等于历史可用时间。
- **问题：** 合成时钟在请求前100、返回后200，成功receipt仍记录100。代码在fetch/retry前一次性取时。位置：`backtest/tools/acquisition/binance_usdm.py:410–428`。
- **最小修复：** 每个响应返回后记录时钟；archive和checksum分别取时，整体收齐时间取最大值。历史收据保持原样。
- **不修后果：** 使用者可能把尚未取得的字节判断为已取得；修复此项也不能自动证明历史provider availability。

## 应修复：可用性、集成与维护

### 12. P2：同一个工作环境实际混用不同Backtest版本

- **这是什么：** 根工作区、子模块、锁文件和运行时导入应有清晰一致的版本契约。
- **问题：** runtime/trading导入当前`3ab6…`工作树，builder/domain/market-data实际导入安装的`8cc5…`；root default suite的四个架构检查失败。`pyproject.toml:24–26,48–58`、`uv.lock`、`tests/architecture/test_dependency_alignment.py:20–28`。
- **最小修复：** 决定并验证一个一致的包组合，统一锁/安装/源码来源；旧版集成断言按当前接受合同调整，不能删掉版本对齐检查来消除红灯。
- **不修后果：** 看的是新代码、执行的可能是旧包；源代码审查通过不能证明用户默认环境相同行为。此次用显式src路径的737项测试另作标记，没有冒称等价于默认环境。

### 13. P2：采集代码pin随SDK升级失配，标准离线检查已经不可通过

- **这是什么：** pin应阻止未评估的新代码进入已验收流程，但升级还需要一个重新验收路径。
- **问题：** `offline-pc`实跑27失败、71通过，失败全部为`CAPTURE_GOV_CODE_PIN`；预期ledger SHA为`94c4…`，当前为`46c0…`。来源：`experiments/run_a_share_price_volume_retro_real_v1.py:966–975`及`experiments/a_share_ingestion/retro_capture_v1.py:707–734`。
- **最小修复：** 对新ledger做兼容性审阅、重新跑固定合成采集合同，发布新的代码绑定清单。不能盲改hash或删除pin。默认pytest没有包含该`tests/research`路径，集成升级测试矩阵应覆盖它。
- **不修后果：** 新的合成流程尚且进不了，真实流程同样会卡；增加更多审批文档不能解决接口/版本失配。

### 14. 可用性缺口：研究脚本的精确复现依赖已退休工作树绝对路径

- **这是什么：** 保留旧证据hash正确，但可复现入口还需找到那些字节。
- **问题：** 从当前main加载v16配置，立即因旧`platform-l2-risers-phase-v9/.../l2_ranking_compare_v12.py`不存在失败，尚未读取行情或运行研究。`experiments/l2_cash_flat_v16.py:13,21–36`及`l2_expanded_compare_v15.py:39–40`。这是此前用户授权清理后的已知限制，不归咎为未经授权删除。
- **最小修复：** 提供按commit/hash定位的受控恢复/复现入口，保留旧source bundle或按已记录命令恢复旧路径。未来新研究清单把代码身份与机器路径分开，不重写旧收据。
- **不修后果：** “代码已经合并”仍不是“换机器/换目录就能重跑”。现有完整源码归档和恢复说明仍在，没有丢数据。

## 门禁到底该保留、简化还是删除？

| 门禁类别 | 结论 | 适用层级与原因 |
|---|---|---|
| 数据范围、字节身份、重复/缺失、单位、公司行动、历史可用时间 | **保留并补齐** | 直接影响因果性和经济正确性；上面6/10/11说明有些检查还不完整 |
| 固定实验轴、参数/seed、选择规则、完整失败清单 | **保留，简化录入** | 防止结果出来后挑赢家；由一次声明自动产生后续任务，不应让人反复抄写同一事实 |
| 读取前样本预约、真实未看OOS、独立形成holdout目标 | **保留并绑定同一存储** | 是有效验证底线；台账只能覆盖受控读取，不能证明人工和外部程序从没看过 |
| CAS、owner-log、完整发布与checkpoint | **保留** | 分别回答字节是谁、是否正式提交、历史截止在哪；它们并不重复，但不能替代语义验证 |
| 重放、double attempt、durable reopen | **按等级使用** | development探索不必复制decision-grade的所有成本；正式持久证据仍须证明可以从原材料重建 |
| 独立review与Promotion | **正式晋级保留；普通探索推迟** | 不应用来阻止一张明确标为描述性的统计表；本地actor/attestation不是现实身份认证，更不是交易许可 |
| 小样本smoke、明确CPU/字节/时间预算 | **保留；合并重复收据** | 大量数据作业前非常有用；预算未变、接口未变的重复确认不增加保护。审批范围变化才重新征求授权 |
| 每改代码都与旧硬编码SHA比较 | **保留历史pin，改进升级机制** | 旧运行复现必须严，新工作应产生新接受清单；不能使一切合法升级永久失效 |
| self验证、变更planner、offline-pc | **作为窄工具，不作全平台通过章** | self只证明验证器自身；planner只认识部分proxy/capture路径；本轮offline-pc实际失败 |
| 全局来源永久不修订、最早可用时间必须精确等于某事件瞬间 | **不要泛化为普通研究门槛；特定正式合同需重新评估** | ADR0008已允许部分外部最终性未知；对不可取得证据的合同，应更换可满足的目标或降级明确假设，不是伪造证据通过 |

### 一个已复现、但暂不当作代码缺陷的“过严门”例子

Binance账户查询当前点：仅放当前已知band时通过；再加入未来才可见的band，相同当前点变成`MISSING_PROFILE_INTERVAL`。原因是`account_profile.py:504–524`要求“当前已可见bands”覆盖整本book。

这个限制是否错误取决于该Interface承诺验证当前点还是整段已可见覆盖。本审计确认了行为，**不把更改全段合同偷偷包装成修bug**。应澄清并区分“整本book结构覆盖”与“当前点可见性”；若需要逐时因果解析，应避免未来区段阻断当前事实。

### 没有依据建议整体删除的门

- Foundation本地合作写者的原子性、锁、单调时钟和checkpoint，没有发现足够证据要求推翻。
- `development`不得冒充经济决策级、`shadow_ready`不得冒充Live授权，应继续保留。
- 不支持hedge、多资产、复杂税务等时fail-closed是合理的能力限制，不是默认应该放行。
- 不能声称本轮已识别可安全删除多少行或依赖；没有经完整引用核验的死代码数量。优先合并验证逻辑与输入声明，而不是改写冻结历史版本。

## 能否达到预期目的？

以下按文档和近期使用理解目标：有用的A股/Binance策略研究 → 可信Backtest/OOS → 得到值得实际验证的策略。若目标不同，应重新对齐，不能据此承诺盈利。

| 目标 | 当前判断 | 主要缺口 |
|---|---|---|
| 查看数据、提出并反驳假设 | **已经可用** | v15/v16实际完成多日期比较；应明确描述性/已看样本，不必为此要求实盘资格 |
| 同样输入重复得到同样结果 | **有较好基础，但不是无条件可复现产品** | 环境混用、外置配置/代码、绝对路径与部分失败恢复仍需解决 |
| 经济上可信的回测结果 | **已有公共实现，但不能笼统给全项目合格结论** | T+1单位、模型时点、行动完整性和指标语义缺口需修；每个市场/profile的数据资格也须满足 |
| 公平筛选并在真正未看数据上验证 | **工程链已有，证据不足** | 样本权威存储绑定、完整实验来源、报告回放漏洞；真实未污染OOS和经济上有意义的门槛不能由收据数量替代 |
| 通用、顺畅验证任意A股/Binance策略 | **尚未达到** | 有公共A股组合入口，但若干来源/route仍只覆盖固定标的、日期和有限假设，不能外推；需要一条真实日常研究闭环而不是更多孤立golden |
| 直接实盘、稳定赚钱 | **未达到，也不是目前合同承诺** | Shadow/Live实现和运营风控明确在外；即使代码零缺陷，也不能保证alpha |

**特别提醒：** v6集成golden的单笔收益为−10%，阈值设为−100%，所以`SUPPORTED`在该测试中完全合法。它证明协议会按阈值判断，不证明策略值得交易。证据：`tests/integration/test_integration_v6.py:171–184,249–259`。

**Binance特定实质阻塞：** `backtest/docs/research/g12m-binance-funding-availability-authority-decision-v1.md:13–46`已将该funding历史资格分支定为`H3/NO_CAUSAL_AUTHORITY`。当前严格契约要求无法从现有数据证明的精确最早可用时点/完整修订链，甚至没有授权前瞻REST方案。不能靠“多下载一点”解开，也不表示所有Binance研究都不可能；应另行确定可满足的有限因果合同，或明确停留在post-hoc开发研究。

## 建议的下一步，不自动执行

由父编码代理在获得修复授权后负责，不把寻找已有资料或修复依赖的工作转交用户：

1. **统一一个可运行版本组合**，对采集pin升级做新验收；保留已有失败证据，恢复默认检查与实际离线采集检查。
2. **先修影响结论的缺口**：样本存储绑定、报告/实验来源验证、模型时点、T+1数量、指标和行动输入；随后补Promotion中断恢复。
3. **补反例测试，不只加happy-path golden**：将本次小复现改成负测，要求进入payload/交易/发布前失败。恢复测试要求同一Case最终只有一套原始证据。
4. **跑一条有边界的真实策略闭环**：先核实已有公开prepare与已准入数据组合，冻结有经济意义的对照、成本和样本外条件；没有该组合就准确列缺口。不能绕过公开seam自建第二模拟器。
5. **之后再做简化**：统一scope/版本清单、入口级验证器和恢复流程；探索报告免走正式Promotion，正式晋级仍保留经济与样本门。

不建议现在继续扩充审批层、通用抽象或更多孤立receipt。先让同一条真实闭环正确、能恢复、能重跑，才能判断还需要哪些门。

## 未检查与证据文件

未逐行覆盖全部约36万行Python；未全跑Backtest、所有研究脚本、真实供应商采集、大型原始数据、长时间并发/崩溃压力、实盘执行、现实人员独立性或外部安全攻防。没有新的预测有效性结论。

- `inventory.json`：版本、初始状态、默认导入来源。
- `default_root_suite.log`、`checkout_core_modules.log`、`backtest_targeted_tests.log`：实际测试输出。
- `governance_repros.jsonl`：4个治理问题的合成复现。
- `candidate_provenance_repro.json`：不完整候选来源准入。
- `backtest_repros.jsonl`：模型、指标、数量、账户覆盖、分页、checksum、时间的7个合成复现。
- `validator_self/`、`validator_offline_pc/`、`capture_pin_mismatches.json`：工具门禁实测。
- `l2_relocation_check.json`：旧路径加载失败，未启动数据作业。
- 各分区报告的“未运行”指子审没有执行工具；本总报告只把父审计实测成功的事项列为已复现。

**Verdict：有价值的离线研究基础，不是应推倒重写的废项目；先修错误接受和版本/恢复问题，减少重复操作门，不要把工程流程通过当作经济有效。**
