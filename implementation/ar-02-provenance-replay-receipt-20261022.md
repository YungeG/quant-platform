# AR-02：完整候选来源与验证报告回放验收

本记录关闭AR-02叶子/公共seam整改，不代替AR-07默认安装环境或AR-09最终Platform/Backtest全套验收。没有真实市场实验或新OOS有效性结论。

## 已接受候选

- Research：`ba2af01b7e070a677b7f365ef37f7d8a6a071ff6`。新增只读`verify_candidate_provenance`，复用既有任务全集、尝试闭包、manifest、全部分析和选择算法；不复制第二套checker。
- Validation：`fa16b688cc1468007c2f92e2c53079bc4ab5464d`。消费显式注入的Research verifier；缺少callback在I/O前失败，D1存储检查优先。Graph检查其可见身份，runtime独立核对真实manifest owner-entry截止引用。
- Promotion composition test：`65052d737a43b5d7bbbe7790bccc8bb90e60006a`（production继承已接受`4de95ace`，这里只接线）。
- 根composition：原`a796faed`，集成分支cherry-pick为`a123e43`；六文件仅公开接线与反向依赖/懒加载守卫。历史fixture/hash/BT-PORT JSON不改。

普通报告回放重建原Plan、两类必需CaseResults/Case、assessment、Backtest证据与原OOS预约，比较全部派生报告字段；无CaseResults的假supported不再通过。有效重放返回原refs，不运行经济回测/derive、不新增预约/clock/checkpoint/publish。target @2强路径保持单独版本，没有泛化为@1解码。

## 实际证据与复核

1. A02a fresh复核发现参数轴scalar可逃逸为AttributeError；窄修复先RED/GREEN，再父独立**132 passed**。修复只加解码形状检查，不泛捕基础设施异常。
2. A02b writer保留原missing-verifier/假supported RED，迁移正例为真实Research生产者；本地fixture的Research与OOS采用一致但不同的引用，避免靠加载计数掩盖冲突。旧不完整生产者仅用于负测与历史wire序列化。
3. 父独立新runtime/seam smoke **48 passed，8.96秒**。
4. 父独立Foundation/Research/Validation/Promotion全模块，显式同一隔离源码组合：**891 passed，231.75秒**。
5. Fresh审查没有新回归，但指出原target回放的基础设施错误分类缺口：Report读取WRITE_LOCK_UNAVAILABLE被误映射为case错误，ValidationCase缺失反而传播。该项按本轮错误合同纳入修复，没有以“旧问题”忽略。
6. 窄修复`fa16b688`只保留Foundation异常并在关闭回放边界把ARTIFACT_NOT_FOUND映射到原semantic NoReport；父独立target及public-adapter/seam重跑 **63 passed，20.68秒**，定向复核无剩余阻断。

统计批次有重叠，不能合计为独立测试总量。reviewer仅读查，没有把父执行的测试当成自己的执行。原review意见保存在`*-review-v1.md`，没有用最终意见覆盖失败历史。

## 剩余范围

默认环境仍需对齐新的不可变包组合，capture SDK pin需重新验收。全Backtest第一轮3258项有11失败，涉及独立旧schema/边界/证据测试及native工具受保护源冲突；该失败不由891项治理通过抵消，AR-09仍未关闭。合入分支尚不是main发布；远端可达性/发布授权单独核实。

执行材料：`/srv/bcache-8t/ygguo/quant/platform-remediation-20261022/`中的A2a/A2b handoff、准确patches、`ar-a2b-parent-full-governance.log`、`ar-a2b-target-parent-rerun.log`和独立复核。旧artifact/ref不回写，未知外部调用者必须显式注入verifier，不能静默回退到旧弱通路。
