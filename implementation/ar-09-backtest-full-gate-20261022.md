# AR-09：Backtest首轮全套失败与处置

**首轮完整验收失败，不能用定向通过抵消。** 冻结候选`6ce79d6dc148be000e7fcc4b5d62b875b243dbd4`，使用已有Backtest开发环境及显式同一源码组合，一次执行3258项，**3245 passed、11 failed、2 skipped**，1620.18秒。无重试/选择性排除。执行前后HEAD与工作树保持不变。

原始日志及只执行worker记录位于`/srv/bcache-8t/ygguo/quant/platform-remediation-20261022/backtest-full-suite.log`和`backtest-full-handoff.md`。测试集合含大量本地合成/已保留fixture，未启动新的供应商采集。

## 处置分类

| 分类 | 失败数 | 已有证据与处置 |
|---|---:|---|
| **本轮AR-05引入的兼容回归** | 2 | legacy native Binance文件受G12L精确源SHA/函数签名保护。不能改保护hash。候选`0eb0377f`恢复原v1字节与测试，把响应后采样转为明确`binance_usdm_v2`入口；父109项重跑和fresh review通过，最终集成全套仍待运行 |
| 旧schema/factory测试期待落后于已接受的bundle@7/@8 | 4 | 源码与测试均byte-match `3ab6bfd8`；更新的是精确版本清单，不新增schema，不允许任意未来版本，不改旧payload/golden |
| Runtime跨包访问Trading内部模块 | 3 | 七个运行模块14处imports也byte-match基线；是真实架构违反，不以放宽checker掩盖。父批准精确八符号公共profile facade及一条exact policy声明，生产逻辑不变，施工中 |
| 保留分钟authority测试在实际evidence目录调用publisher | 1 | bytes/ref/proof一致，但checkout文件为0644/目录02755，与不可变final发布约束不符。改为临时目录等字节复制并只硬化副本，不chmod真实evidence，不放松仓库校验，施工中 |
| 历史日历源hash误与当前加法扩展代码比较 | 1 | 找到所需历史blob及原`0382…9532`摘要；保留历史期望，归档精确源并测试当前普通phase语义兼容，不盲更新hash，施工中 |

对九个baseline失败的归因来自72个相关文件、七个offending runtime文件的本地Git字节比较及readonly stat/AST检查，不伪称又跑了一次旧基线全套。source/fixture hash、权威和最小施工包保留为`backtest-failure-readiness.md`；父合同选择在`backtest-failure-parent-freeze.json`。

## 本轮兼容决定

1. legacy `tools/acquisition/binance_usdm.py`必须继续保持原字节SHA256 `99f4cf3a4631cd4e69830674751b63e23f66537e96745439fba86a7d52b36617`；其旧CLI请求前取时行为明确标为legacy，不宣称已修。新响应取得时间要求使用v2入口，历史receipt不改。
2. 新`crypto_quant_trading.profiles.cn_a_share.portfolio_v1`是精确八符号同对象re-export公共包，generic Trading与已有CN root文件保持不变。其他内部/深层路径仍禁止，generic Kernel不得反向import concrete profile；不建设registry或新金融计算层。
3. 只在临时fixture副本修复读取所需的physical mode；Git不能保存readonly目录属性，不能因此放松生产仓库的不可变要求。
4. 历史日历来源与当前兼容实现是两项证明：旧source hash仍代表旧字节，当前实现通过语义parity桥接；不能把当前源hash写回旧权威。

## 后续验收门

- 分组先跑此前失败的精确节点与新增负测；分支提交及独立review后由主控合入。
- 全部修复fanin到同一冻结Backtest候选后再运行一次全套；新失败照实保留，不能为结束任务删test/deselect或只报通过数。
- 根默认环境、统一五包版本、采集SDK pin与root集成仍是独立门。叶子focused通过、引入new public facade或归档旧源均不自动代表金融/市场资格。
- 本记录是失败事实与处置责任，不是最终通过收据，当前状态只在roadmap维护。
