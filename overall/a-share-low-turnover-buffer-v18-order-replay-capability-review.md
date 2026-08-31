# A股低换手缓冲V18订单级回放能力审查

## Mode and market

- Mode: **Review / Plan-only**
- Market: 沪深A股普通股票，20只等权组合，现金账户
- Candidate: `a-share-low-turnover-top20-buffer40-v1`

## Capability decision

**当前不可执行正式订单级Backtest。**

`crypto_quant_backtest`公共根只暴露现金开发类准备入口：

- `prepare_cash_development_backtest`
- `prepare_cash_target_stream_backtest`
- `prepare_model_bound_cash_development_backtest`

现有A股能力仅覆盖固定单票/零交易或规则与费用绑定。`prepare_cn_a_share_current_selected_fee_execution_v2`位于内部模块，未从公共根导出，而且只绑定单个订单费用，不是多股票组合Backtest准备入口。

因此不得为V18另写撮合、账户、费用或延迟退出模拟器，也不得直接组合Backtest内部对象。

## Frozen replay requirements

正式入口必须原样消费V18冻结目标流，不得重新选择参数：

- 20日低换手排名Top-20买入、Top-40保留；
- 每5个交易日检查；
- T日收盘信号，最早T+1开盘执行；
- 100股整手，不得向上取整；
- 涨停买入失败保留现金；跌停卖出失败延迟至首个可卖日；
- A股T+1可卖数量；
- 历史佣金、最低佣金、过户费和卖出印花税；
- 停牌、退市、ST有效区间、公司行动和现金占用；
- 每日账户估值、订单拒绝/阻塞原因和未成交现金。

## Exact missing public seam

需要Backtest公共根新增并验收一个**多股票A股目标流准备操作**（名称待Backtest所有者确定），由Backtest负责：

1. 接收冻结的PIT股票目标权重流与不可变MarketBundle；
2. 解析A股日历、上市/ST/停牌、涨跌停、T+1和100股数量格；
3. 绑定历史费用、最低佣金、税费和现金账户；
4. 注册请求、生成语义run id、执行并发布完整/终止证据；
5. 通过公共`BacktestEvidenceRepository`提供可验证结果。

该入口必须支持多标的换仓、部分成交/买入失败、延迟卖出和现金残留；固定单票或单订单费用绑定不能冒充该能力。

## Validation result

**No report / capability-blocked.** V18仍为`GO_CANDIDATE_RESEARCH_GRADE`，`trade_authorized=false`。原研究指标不得升级为正式Backtest或实盘证据。

## Next safe action

先由Backtest模块实现并验收上述公共准备入口及最小多标的夹具；入口存在后，使用冻结V18目标流执行一次开发级回放，再预留独立Forward Shadow。不得在此之前追加同样本参数扫描。
