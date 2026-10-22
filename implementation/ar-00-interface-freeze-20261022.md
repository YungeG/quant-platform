# AR-00：施工基线与共享Interface冻结

本记录消费用户“按照设计文档推进至完成”的授权与[施工计划](plans/platform-audit-remediation-20261022.md)。它冻结本轮代码方案，不声明任何修复已通过；实际状态只在[roadmap](roadmap.md#2-status-registry)。AR-10真实市场实验、生产/付费/范围扩张与未包括的远端发布动作仍保留授权门。

## 1. 起点、隔离与证据

- 根基线`f578fe0`；施工文档及授权登记提交`3722ac1`，集成分支`impl/platform-audit-remediation-20261022`。main和旧研究证据不重写。
- Leaf基线：Backtest`3ab6bfd8`、Foundation`9d88ed6`、Research`de8b2c4`、Validation`e87d98bc`、Promotion`8e6dddf`。
- 原审计及实际复现保留于`/srv/bcache-8t/ygguo/quant/platform-audit-20261022/`；新执行材料位于`/srv/bcache-8t/ygguo/quant/platform-remediation-20261022/`。
- 三个新隔离根：`/srv/bcache-8t/ygguo/worktrees/platform-ar-20261022/{a,b,c}/platform`。每个根包含独立git worktree形式的完整source cohort及根测试夹具，不把符号链接/旧安装包冒充当前源码。
- A仅写其Research/Validation及明确的根composition迁移文件；B仅写其Backtest trading/runtime；C仅写其Backtest Builder/acquisition，交付后转Promotion。根配置、gitlinks、lock、registry只有主控写。没有恢复已退休的L2工作树路径。
- 原解释器`/home/ygguo/agent-projs/ai-crypt/platform/.venv/bin/python`暂只读复用，leaf tests显式指向各自全部source packages。该诊断配置不是默认安装环境已修复的证据。
- 实际隔离smoke：B两项通过（1.83秒）、A两项通过（0.58秒）、C一项通过（0.11秒）。其中B验证5个Backtest包均来自其本地source root。原审计全套结果只作为原基线，不伪称重新跑过。

## 2. D1：样本存储绑定

Validation已经使用同一`LocalFoundation`对象的约定，Foundation没有公开path/storage identity接口。本轮沿用该约定：

```python
SampleConsumptionLedger.require_foundation(foundation: LocalFoundation) -> None
```

- 错参数类型为既有TypeError；ledger不是绑定到传入的同一对象时，抛`ValidationCoreFailure("SAMPLE_LEDGER_CONFLICT")`；成功只返回None，无I/O/clock/checkpoint。
- 同一Foundation对象上的不同ledger可以使用；同一路径的两个Foundation实例仍拒绝。重开存储时同时重建caller Foundation和ledger即可。
- Research ordinary/model/target和Validation ordinary/target在纯参数检查之后、任何发布/读取/port调用之前使用此公开guard。
- statistical/retrospective reservation同样提前guard，保留各自原有wrapper失败码；Research不访问Validation私有字段。
- 不新增Foundation API，不迁移预约，不把事后补写当作事前消费证明。原正常输入的canonical bytes与事件ID保持。

## 3. D2：完整候选来源验证与报告回放

依赖方向已经核实为Research→Validation。**Validation不能反向import Research，连公共根也不能用动态import绕开。** 本轮选定显式composition注入：

- Validation-owned frozen in-memory `VerifiedCandidateProvenance`：绑定candidate、family、experiment、execution manifest、selection declaration和真实manifest截止entry；不是持久证书、布尔自证或对恶意插件的安全认证。
- Research-owned `verify_candidate_provenance(candidate_ref, foundation, backtest)`：只读重建完整已发布Experiment，复用既有任务/attempt/manifest/selection算法，不执行、预约、derive、创建新checkpoint或发布。
- `validate_candidate`及`validate_target_candidate`新增keyword-only `candidate_provenance_verifier`，由composition root从Research公共根注入。缺失时明确NoReport，不保留弱默认通路；非callable为TypeError；身份不匹配/来源语义失败按既有provenance失败映射。
- 这是有意的调用方迁移，不宣称所有旧调用透明兼容；原有效artifact/schema/refs不变。所有库内调用者需要显式接线。纯core夹具可提供绑定的假值，但不能据此当作生产来源验收；生产通路必须使用真实Research verifier。
- Research复用`validate_execution_prefix`、`build_execution_manifest`、`build_candidate_family`及`select_candidate`；不在Validation复制第二套Experiment checker，不把Foundation存储权限当作语义正确性。
- v1已有报告回放需解析原Plan、完整必需CaseResults、真实assessment、原预约和Backtest证据，复算报告派生字段后返回原引用；不能先shape-check报告便早退。v6保留较强既有target恢复路径。
- 非法历史字节保留但不能继续获得新的Verified/报告结论；合法重放不得重复run/derive、预约、clock/checkpoint或重发记录。

完整符号级提案及已读调用路径：执行证据目录`ar-a-readiness.md`。主控已冻结上述依赖与失败决策；A先交付AR-01，再以独立切片完成只读verifier与Validation迁移，不将整个治理链交给一次无边界写入。

## 4. D3：指标验证及独立金融修复

- Backtest v1/v2 analysis loader仍保持其公开签名、结果类型与schema。Verified接受条件从link-only加强为：合法profile/真实来源链接/等级一致，且trade_count和simple_period_return与该completed来源的既有纯派生值一致。
- 复用`analysis_derivation.py`原有纯计算，不引入新收益公式、容差、模拟、run、CAS写入或替换旧analysis。错误指标走既有`PORT_ANALYSIS_LINK_MISMATCH`；保留版本、类型和retention错误原有优先级。
- 新增当前验证承诺的addendum，不回写历史G07收据/产物；valid legacy bytes/ref不变，错误内容不再获Verified接受。
- 模型available_at比较真实target完整SimulationInstant，并在写入前拒绝未来UTC/phase/sequence；使用现有`MODEL_ARTIFACT_UNAVAILABLE`，不新增推理能力。
- A股组合接口坚持整数股并显式核对scale/Instrument，不能以裸units跨单位比较；不改变通用Quantity或费用规则。

## 5. 版本组合与发布边界

1. Leaf开发与定向反例使用同一隔离根的全部当前源码。这可以证明修改行为，不能作为默认安装环境通过章。
2. AR-07最终目标是5个Backtest分包使用同一已接受、不可变Backtest revision，与root gitlink/lock/实际安装来源一致；其他workspace模块按实际接受leaf提交组合。
3. 最终revision必须等待B/C集成与leaf验收，不提前假填。临时环境与现有`.venv`分离；所有writer/验证结束前不覆盖共用解释器环境。
4. 旧代码pin及原接受产物保持历史含义；对新Validation ledger发布新的兼容性接受清单与capture pin，不盲替换SHA让检查绿灯。
5. 子仓库提交是否能远端访问，必须真实验证。没有包括在当前权限内的push/发布只暂停该动作，继续本地编码和独立检查，不隐瞒为完成。

## 6. 本记录的限度

本记录选择了最小可执行合同与隔离方案，并不代表这些合同已经被代码实现或各节点已验收。每个writer仍须RED/GREEN、提交真实diff/commit和检查输出；主控独立重跑并安排fresh review。失败保留失败，不以packet、代理完成或计划估时替代交付。
