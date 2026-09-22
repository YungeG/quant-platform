# BTCUSDT 日频时间序列动量验证计划

## 1. 目标

验证一个冻结的 BTCUSDT USD-M 永续合约日频时间序列动量候选：

> 完成的过去 7 根日线收益方向，是否对下一持有期的成本后收益具有稳定、可复现的预测价值。

本计划验证的是 **development-grade 研究候选**，不是收益承诺、`shadow_ready`、实盘资格或部署授权。

## 2. 前置结论

当前仓库已具备 development-grade 的永续合约多空持仓、资金费率、费用、保证金、保守清算审计、策略调用和样本保留语义，但现有 G12 数据切片不足以组成连续、因果可用的历史回测区间。

因此验证分为两道不可跳过的门：

1. **数据权威门：** 先建立连续、可追溯、因果可用的 BTCUSDT 历史数据 Bundle。
2. **策略证据门：** 数据门通过后，才运行冻结策略、预留最终 holdout 并形成 Validation 结论。

本地权威：

- [策略候选研究](strategy-ideas.md)
- [Backtest acceptance matrix](../backtest/docs/implementation/acceptance-matrix.md)
- [Research Platform design](../research-platform/design.md)
- [Strategy Validation design](../strategy-validation/design.md)
- [G11D named Bar window](../backtest/docs/research/g11d-named-bar-window.md)
- [G11I Portfolio Strategy invocation](../backtest/docs/research/g11i-portfolio-strategy-invocation.md)
- [Funding H3 authority decision](../backtest/docs/research/g12m-binance-funding-availability-authority-decision-v1.md)
- [历史项目行情数据盘点](prior-project-market-data-inventory.md)

### 2.1 已发现的启动数据

`crypt-gemini/artifacts/carry_audit_20260728/input/` 已保存 BTCUSDT 2021-01-01 至 2026-07-27 的连续 perpetual 1h Bar 和 funding 数据；manifest SHA-256 为 `13875c8c17d97742db1d3a8e47c5ef503c97fd939987a04e8f9b4d98714bdbde`。Funding `mark_price` 从 2023-10-31 起存在。

项目所有者确认这些文件下载后没有被人工修改，并授权直接使用。Legacy pilot 将只读原文件，在启动 receipt 中冻结 manifest 和输入 SHA-256；不重新下载、不复制后修改、不覆盖源目录。

该 Bundle 足以立即运行一个 legacy pilot，但全部历史已经被读取，且下载程序生成的是规范化 CSV，历史规则和费用仍是假设，正式 provider availability/revision authority 也未闭合。因此采用两轨制：

1. **Legacy pilot：** 直接使用现有文件，快速验证 7 日 TSM 的机械正确性和经济可行性；最高结论为 `INCONCLUSIVE / PROMISING` 或 `REJECTED`。
2. **Platform authority：** 继续执行下述 Phase A 数据权威门；只有该轨可以进入正式 `SUPPORTED` 判定。

Legacy pilot 不得占用或重新命名未来正式 holdout。

## 3. 冻结候选

| 项目 | 冻结值 |
| --- | --- |
| Instrument | `BTCUSDT`，仅接受 point-in-time 证据确认的 Binance USD-M linear perpetual 区间 |
| Bar | 完成的 UTC 日线；BarDefinition、数据集和 capability 必须版本化 |
| Signal | `sign(log(close_t / close_{t-7}))` |
| Decision | 日线 `t` 完成并可见后，在对应完整 `SimulationInstant` 决策 |
| Target | 正信号 `+1` gross、负信号 `-1` gross、缺失/不可用为 `BLOCKED`；不做波动率缩放 |
| Rebalance | 每日评估；目标方向未变化时不创建无意义换仓 |
| Execution | 首个严格晚于 Decision 的可执行事件；禁止同 Bar 成交 |
| Leverage | 不优化；使用一个冻结账户/Profile 配置 |
| Funding | 持仓期间每个适用 funding slot 必须有完整权威证据 |
| Fees | 优先使用 source/account-bound 费率；否则只能形成假设性 development 结果 |
| Slippage | Base `2 bps/side`；预承诺压力 `0/5/10 bps/side` |
| Model/ML | 无 |
| Tunable parameters | 无；最终候选只使用 7 日 lookback |

## 4. 非目标

- 不同时测试 ETH、其他 lookback 或动态参数并从 holdout 选赢家。
- 不使用当前 `/exchangeInfo` 回填历史规则。
- 不用 late-acquired REST Funding History 假装 settlement instant 已可见。
- 不从 mark/index/premium 数据构造可执行成交价。
- 不实现第二套简化回测器绕过现有 Backtest public seam。
- 不根据一次成功结果推导实盘、部署或 Promotion 资格。

## 5. Phase A — 数据权威门

### A1. 冻结数据区间

在查看策略收益前选择一个明确的半开区间 `[start, end)`：

- 建议至少包含 **1,500 个有效 Decision 日**；
- 最终 holdout 至少 **365 个 Decision 日**；
- 数据不足时允许在读取收益前调整一次区间，调整理由只能是覆盖率，不能是表现。

以上数量是研究充分性假设，不是交易所事实。

### A2. 必需数据

1. **Execution-reference/last-price 日线**：完整 OHLC，支持下一 Bar open 执行。
2. **Mark-price 数据**：覆盖 valuation、margin、liquidation 和 funding 所需时点。
3. **Funding publications/settlements**：rate、funding mark、slot、revision、availability 和 settlement evidence。
4. **Instrument metadata**：contract identity、listing/status、multiplier。
5. **Historical order rules**：tick、quantity step/minimum、notional/order admission。
6. **Historical margin tiers/account profile**：覆盖完整运行区间。
7. **Fee authority**：明确 maker/taker/account tier 的生效区间；无法取得时保留为显式假设。

### A3. 每类数据的通过条件

- 原始字节、请求边界、来源版本和内容哈希可复现。
- `event_time` 与 `available_time` 分离，且不存在回填式因果倒置。
- revision/supersession 关系闭合；无法证明闭合时明确限定 source-bounded scope。
- 连续区间内每个缺口都有 `NO_SESSION | NO_TRADES | SOURCE_OUTAGE | MISSING` 等权威分类。
- Bar、Funding、Metadata、Rules、Fees 的 Instrument 和时间覆盖完全一致。
- G12 manifest、bundle publication、reader replay 和 exact source trace 通过。

### A4. 数据门失败规则

出现以下任一情况，状态保持 `BLOCKED`，不得进入绩效验证：

- 任一非零持仓期间缺少适用 funding slot 或 funding mark；
- 用当前元数据推断历史规则；
- 用 acquisition time 晚于经济事件的记录声称当时已可用；
- 日线、mark、funding、rules 的覆盖区间无法 exact 对齐；
- 无法判断结果相关缺口是无交易还是数据缺失。

## 6. Phase B — 策略逻辑与因果检查

在真实数据运行前留下一个最小确定性检查：

1. 8 根已完成日线能产生正确的 7 日收益符号。
2. 未完成日线不可进入窗口。
3. Decision 之前不可读取下一 Bar open/high/low/close。
4. Signal 在 Bar `t` 完成后才可见，最早 Fill 位于后续事件。
5. 缺 Bar、短窗口、foreign Instrument、错误 BarDefinition 必须 fail closed。
6. 相同输入重复运行产生相同 Strategy/Decision/Backtest evidence hashes。
7. 将未来 Bar 故意注入 Signal 的负控件必须被因果/窗口校验拒绝。

逻辑检查只证明实现没有明显泄漏，不证明策略有效。

## 7. Phase C — 样本划分与预注册

### C1. 时间切分

按可用 Decision 日顺序切分，不随机打散：

- Development：前 50%
- Pre-holdout validation：接下来的 20%
- Untouched final holdout：最后 30%

在各区间之间增加 **7 个 Decision 日 embargo**，避免 lookback 跨边界污染。

### C2. Holdout 保护

在读取 final holdout 前必须：

1. 发布 StrategyDefinition、数据 revision、BarDefinition、Fee/Slippage Profile 和 BacktestRequest。
2. 冻结唯一候选：7 日 lookback，不允许根据 holdout 改参数。
3. 通过 Validation 的 sample-consumption ledger 预留 final holdout。
4. 冻结 ValidationPlan、指标、压力场景和判定规则。

Holdout 只运行一次。任何结果驱动的修改都形成新候选，并需要新的 untouched period。

## 8. Phase D — Development 与 pre-holdout

### D1. Development 可做

- 检查实现正确性、数据异常和成本归因。
- 运行预承诺的 3/14/28 日 sibling diagnostics，但不得替代 7 日主候选。
- 检查 long/short sleeve、牛熊阶段、波动率分组和年度稳定性。
- 校准报告格式和失败分类，不以收益最大化选择参数。

### D2. Pre-holdout 通过条件

- Base 成本后累计收益为正。
- `5 bps/side` 压力后累计收益仍为正。
- 下一完整日延迟执行后收益符号不翻转。
- 无清算事件；保证金/资金费率/费用全部可重建。
- 最大回撤低于同期 BTC buy-and-hold。
- 最佳 10 个损益日贡献不超过总正损益的 50%。

任一硬条件失败则冻结为 `rejected`，不消耗 final holdout。

## 9. Phase E — Final holdout 一次性验证

### E1. 主要报告指标

- Net cumulative return、CAGR
- Annualized volatility、Sharpe（零利率仅作明确标注的诊断）
- Maximum drawdown、Calmar ratio
- Turnover、订单数、持仓方向切换数
- Gross/Net 损益、fees、slippage、funding 分项
- Long/short sleeve attribution
- Margin usage、minimum available margin、liquidation count
- 与 cash、BTC buy-and-hold 的同期比较

### E2. 统计检查

- 对日净收益使用保留时间依赖的 block bootstrap。
- 报告 annualized net return 的 90% confidence interval。
- 不以单一 p-value 代替经济阈值、成本压力和回撤检查。

### E3. 预承诺压力矩阵

| Case | 变化 |
| --- | --- |
| Base | source-bound fee + `2 bps/side` |
| Low cost | source-bound fee + `0 bps/side` |
| Cost stress | source-bound fee + `5 bps/side` |
| Severe cost | source-bound fee + `10 bps/side` |
| Fee stress | 非税费/手续费加倍 |
| Delay stress | 所有入场与方向切换延后一个完整日 |
| Long-only diagnostic | 负信号时 target `0`，仅诊断，不替代主候选 |
| Inverted-signal placebo | Signal 符号反转，仅作负控件 |

## 10. 最终判定

### `BLOCKED`

- 数据权威、资金费率、执行、规则或账户覆盖不完整；或
- Backtest 没有产生完整 canonical publication/evidence。

`BLOCKED` 不等于策略失败。

### `REJECTED`

满足任一：

- Holdout Base 净收益 `<= 0`；
- `5 bps/side` 后净收益 `<= 0`；
- 延迟一日后净收益 `<= 0`；
- 出现清算；
- 最大回撤不低于 BTC buy-and-hold；
- 因果、样本污染或经济重建检查失败。

### `INCONCLUSIVE`

- Base/压力结果为正，但 90% bootstrap 区间下界 `<= 0`；或
- 收益过度集中：最佳 10 个损益日超过总正损益的 50%；或
- 有效 holdout 少于 365 个 Decision 日；或
- 费用只能使用未校准假设，无法形成 source-bound 成本结论。

### `SUPPORTED`

必须同时满足：

1. 所有 evidence-integrity 与 OOS case 完成；
2. Base、`5 bps/side` 和一日延迟三者净收益均为正；
3. 90% bootstrap annualized net return 区间下界 `> 0`；
4. 最大回撤严格低于 BTC buy-and-hold；
5. 零清算，且完整损益/fee/funding/margin 可重建；
6. 收益集中度未触发 `INCONCLUSIVE`。

`SUPPORTED` 只表示该冻结候选值得进入 ETH 复制与更广泛 robustness 阶段。

## 11. 必须保留的证据

- SourceSnapshot、raw member hashes、revision/availability receipts
- MarketBundle manifest、capability 与 coverage reports
- StrategyDefinition、BarDefinition、Decision schedule 和 build identity
- Experiment、Trial、TaskOutcome、ExecutionManifest、Candidate refs
- BacktestRequest、CompletedPublication、canonical evidence repository refs
- SampleConsumption ledger snapshot、ValidationPlan、ValidationCase、ValidationReport
- Base/stress/placebo 的逐项费用、资金费率、成交、持仓、保证金和结果归因
- 所有失败的 structured code；禁止只保留异常文本或汇总收益

## 12. 停止规则

- 数据门失败：停止，不写策略实现来绕过缺口。
- Pre-holdout 硬条件失败：停止，不读取 final holdout。
- Final holdout 完成：停止，不调参、不追加例外规则。
- `SUPPORTED`：下一步仅是 ETHUSDT 独立复制；不得直接进入实盘。
- `REJECTED`：保留证据，除非提出新的、事前可解释的 StrategyDefinition，否则不重跑同一 holdout。
