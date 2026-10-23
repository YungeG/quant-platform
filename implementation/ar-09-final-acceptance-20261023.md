# AR-09核心代码与干净组合验收

**核心整改、新版模型合同与干净组合已通过实际验收。** 本记录提交时，四个leaf整改分支已发布并核实；Platform集成分支尚待该文档commit产生后推送，不能把本记录当作已经完成Root发布的证明。实时发布状态只在roadmap及执行目录的实际remote-ref凭据中维护。

## 被验收版本

| Repo | 确切commit | 已核实的远端整改分支 |
|---|---|---|
| Backtest | `ea957d59527e93765681d85c7a2f3fd83e6356a0` | `impl/ar-backtest-release-20261022` |
| Foundation | `9d88ed67a84d06c558276f8bae2206b069bcec8f` | 本轮未修改 |
| Research | `5f8302acb121d1426c3aee8abd6f9655f1316933` | `impl/ar-research-integration-20261022` |
| Validation | `fcd158b7c728b0b309667e1d763cc123b572fe7a` | `impl/ar-validation-integration-20261022` |
| Promotion | `c22fe938682d72dcd79d7bf59a2c28a8d5a5f4df` | `impl/ar-promotion-integration-20261022` |

Root行为候选`34207443081f0d65ed71975f852131ae61ddfc2d`包含实现`d41b65f1`和确切leaf gitlinks。后续Root文档提交不改上述代码/pins，并单独执行文档及source-identity定测，不伪称对每个文档HEAD又跑过整套。

## 已执行的验收

| 检查 | 实际结果 |
|---|---|
| 完整Backtest，同一冻结源码组合 | **3299 passed、2项原有fixture skipped，1584.46秒，exit0**；无deselect |
| 真实默认安装Root，候选3420744 | **1303 passed，384.11秒，exit0**；无失败/跳过，含所有Foundation/Research/Validation/Promotion默认测试 |
| 干净Git检出＋新环境，同一候选 | **1303 passed，360.07秒，exit0**；无失败/跳过 |
| 默认环境标准validator | **self PASS（5项）；offline-pc PASS（原98项）** |
| 干净组合标准validator | **self PASS（5项）；offline-pc PASS（原98项）** |
| 父独立模型小样＋正确兼容证明 | **23 passed，32.56秒**；旧ordinary1/model1/target2完整payload、任务wires、refs与普通helper行为相等 |
| writer候选半径 | **104 affected、249 adjacent、16 post-commit**通过；这些批次有重叠，不能累计成独立总量 |
| 独立只读审查 | 新合同与前置预约/消费者变更无具体新增P1/P2；静态review没有被写成reviewer亲自执行测试 |
| 保护字节 | Backtest原9779条目/7292文件、117183604字节保持bytes/mode/symlink一致；旧Root合同与新scope fixture哈希保持不变 |

干净组合不是PYTHONPATH覆盖或搬用旧venv：Root由确切Git候选clone（Root发布前的本地候选对象），五个submodule从配置的GitHub远端取得已可达SHA；全新`.venv`使用独立remote UV cache，九个包origin均在干净检出下，五个Backtest包均为Git EA安装。先Foundation小样和公开模型/预约小样，再完整安装/全套；HTTPS fresh-cache Domain构建及代码对Git blob比较也通过。原默认环境仍保存在`/home/ygguo/.cache/platform-ar20261022/original-platform-venv`，Backtest开发venv未修改。

## 模型合同与关键语义

- 显式新增ExperimentSpec@3及`evaluation_slices`；旧@1/@2 canonical payload/ref和target语义保持。训练仍属于声明全集，新版Trial只从评估集合展开；无重复compiler或金融公式。
- 训练[0,1000)ns、可用1000ns保持不倒填；新评估[2000,3000)和OOS[4000,5000)的真实生成bundle refs、coverage、request/target/bar/mark时钟一致。模型Candidate仍@2，Validation Report仍@1。
- ALL model Trial预约在ALL prepare之前，后续同记录预约幂等；失败保留原异常和保守预约、阻止整个prepare/read，不造request/ref/outcome。OOS实际准备推迟到Case预约后的既有run端口；重放不再次准备、读样本、运行或预约。
- 合成链4 Trials/10 tasks（8完成、2阻断），账本8项=2build+4discovery+2selection；OOS实际-0.1/1trade得到原规则的rejected及适用负面Promotion。六身份、owner/cutoff、完整任务/分析与原refs重放保持。
- 原100ns目标使用1000ns模型的actual-public负例仍拒绝并无request/attempt发布。Promotion仅增加必要Experiment3消费者gate，不改变资格/状态/等级，targetCandidate3/Report2仍不支持。
- 新合同fixture SHA `4cd02832911dc83cb49c28f25a63a45a5533f4f07eda201bce0ff3a030cac192`；用户授权的是范围，未伪称用户签署该hash。

## 失败与恢复没有被抹去

原Backtest3245/11fail/2skip、Root1263/15fail完整日志保留，后续版本实际全套通过才关闭对应技术门。模型writer的发布/消费者gate遗漏、测试tuple解包错误、Source reader wrapper错误和服务连接中断都有原日志；中断后先冻结四repo diff、确认无运行测试，按同一agent/协议恢复，没有绕开执行模式。

最初legacy wire序列化把mapping values降为keys，那两份文件**不是canonical字节证明**。修正证明从确切旧Git module重建，使用实际canonical formatter比较完整值、refs、任务与普通helper；父再次独立执行通过。没有盲刷新旧golden/hash或删除负测。

## 交付与保留限制

- 用户已允许四个leaf整改分支及Platform集成分支推送；不改子仓库远端main，不force/delete。本记录只关闭已经实际执行的技术验收；Root推送必须另行核实后才关闭发布状态。
- 历史L2源码archive已按AR08核实1101文件，但未恢复旧绝对路径、未重读行情/执行历史市场回放。
- 合成协议、metadata和来源/时钟一致性不等于真实ML训练/PIT/未污染OOS/策略有效性，也不授予Shadow/Live。AR10继续未授权。

完整执行材料：`/srv/bcache-8t/ygguo/quant/platform-remediation-20261022/`，包括`root-default-full-suite-v2.log`、`clean-composition-full-suite.log`、`clean-environment-origin-proof.json`、`model-evaluation-official-qualification-records/`、`model-evaluation-independent-review.md`、正确canonical证明和`model-leaf-publication-receipt.json`。实际fixture/output路径保留未重写；接收方应从已发布Git提交构建新环境，不依赖代理内存、原工作树或旧安装包。
