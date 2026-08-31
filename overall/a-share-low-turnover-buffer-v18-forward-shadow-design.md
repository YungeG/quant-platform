# A股低换手缓冲V18前向Shadow设计

## 状态

- Candidate: `a-share-low-turnover-top20-buffer40-v1`
- Freeze cutoff: `2026-08-31`
- Historical candidate signal: `2026-08-25`
- `trade_authorized: false`

Shadow只记录冻结日之后新到达的数据，不回填历史事件，不修改Top-20/Top-40、20日窗口、5日频率或成本假设。

## 冻结规则

沿用`experiments/run_low_turnover_buffer.py`：

- 20日低换手排名Top-20进入；
- 已持仓排名不低于Top-40则保留；
- 每5个交易日检查，保持原2016-01-01起始会话锚点；
- 目标20只，PIT ST、上市时间、价格、成交和流动性过滤不变；
- 研究成本仍为单边12bp，仅用于与冻结研究结果连续比较。

截至2026-08-31，2026-08-25后只有4个新增交易日，尚未出现下一个冻结调仓点。因此首行仅为`BASELINE_ONLY`，不得计算或宣称前向收益。

## 记录规则

每个冻结调仓点追加一行，记录信号日、目标持仓和数据版本。`experiments/run_low_turnover_buffer_shadow.py --end YYYY-MM-DD`只追加新目标，不计算自定义PnL；重复运行同一截止日必须为no-op。

组合收益、基准收益和active收益在正式证据可用前保持空值，不填零。正式订单成交、最低佣金、涨跌停延迟退出仍受`a-share-low-turnover-buffer-v18-order-replay-capability-review.md`所述公共Backtest入口阻塞；Shadow账本不得冒充订单级回放。

## 晋级要求

至少累计12个月真正前向记录，并在公共A股多股票Backtest入口完成订单级复核后，才允许重新评估；期间不做参数扫描。Shadow本身不授权实盘。
