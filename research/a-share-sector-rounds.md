# A 股独立板块轮次：首批合成工程

纯函数：[`replay_sector_rounds`](../experiments/a_share_sector_rounds.py)。依据[路线图 v0.4 §4](../overall/a-share-layered-opportunity-implementation-plan.md)，仅实现独立 B 轮次的状态回放，不依赖 A 提示、牛熊标签或已筛选的股票名单。它不是当前市场判断、收益研究或正式 Platform 证据。

既有 `evaluate_market_regime`、`evaluate_sector_opportunities` 和 CLI 参数/输出不变。新模块没有文件读取、联网、系统当前时间、持久化、订单或收益计算。

## 输入与初始化

调用方提供：

- `sector`：稳定、非空的板块身份；当前不自动识别或映射申万代码。
- `signals: tuple[SectorRoundSignal, ...]`：逐交易日预计算的 `rs5`、`close`、`ma20`（有限 Decimal），以及 `trading_date`、有时区的 `available_at`。收盘价和均线须为正。
- `calendar`：从起日至 as-of 中国日期逐自然日完整的开闭市声明；不凭周一到周五推断真实交易日。
- `initial_inactive_on`：**显式声明的已知空闲起日**。该日开盘前无活动轮次、待确认序列或剩余冷却。函数没有默认起点，不能把文件第一天当成“之前没有轮次”的证据。
- `as_of`：显式、有时区的评估截止时点；统一为 `Asia/Shanghai`。

`rs5` 必须由同口径行业与沪深300的5交易日简单收益之差准备；`ma20` 必须为包含当日的20交易日均值。`available_at` 是**全部指标及其历史依赖的该版本**已可用时间，不是今天的下载时间，也不能只用当天原始价格的发布时间。本模块只验证输入值和时点结构，**不计算这些指标、不核验其来源或完整性**。

真实使用前还需要数据准备、历史可知版本/覆盖对账、样本用途隔离，以及初始状态的可审计依据。当前接口接受的是调用方声明，不构成对该声明的验证。无依据时不能随意选一个中途日期重置状态，跳过困难历史。

## 固定状态规则

候选版本固定为 `layered_candidate_v1`，没有调参入口：

1. 空闲状态连续2个交易日 `rs5 >= 0.02` 且 `close > ma20`，第二个确认日启动；不回填第一天。
2. 活动状态连续3个交易日 `rs5 <= 0`，第三个确认日结束；正值打断结束确认。活动中的持续强势不会另开一轮。
3. 结束后的10个完整交易日均不能参与新轮启动确认。第10日结束后回到空闲；最快第11日累计一次，第12日确认新轮。
4. 非交易日不累计确认或冷却。未收盘日不参与；每个历史交易日仅使用 `min(as_of, 当日结束)` 之前已可用的信号。
5. `start_known_at` / `end_known_at` 使用确认信号的实际可用时间，不默认为15:00可成交。逻辑键是 `(sector, start_known_at, rule_version)`，只是研究去重坐标，不是 ArtifactRef。

## 缺数与恢复：保守工程限制

- 格式错误、重复日期/冲突版本、休市日信号直接抛出 `TypeError` 或 `ValueError`，不转换成合法空结果。
- 日历不完整时返回 `unknown`，不推断交易日或返回可信前缀。
- 从声明起日回放到第一个缺失或迟到信号时停止，返回 `unknown`、缺口日期和原因；后面价格即使齐备也不猜测跨缺口的状态。
- 已确认且结束的轮次保留。当前已启动但未结束的轮次保留其启动记录，标记 `unresolved_on`，不伪造结束时间。返回的确认/冷却计数清零，仅表示不可续用，不表示真实冷却已经结束。
- 首批实现对冷却期间缺数也统一停止，属于保守的工程可用性限制，不是额外择时规则。它可能拒绝本可继续推断的片段；不允许只使用剩下的完整片段开展金融统计。
- 没有持久状态或中途恢复入口。修复具有真实历史可用时间证据的输入后，只能从同一声明起日重新回放。**真实迟到的版本仍不能追认历史启动**，不得修改 `available_at` 来让程序通过。

完整回放中尚未结束的活动轮次保持 `end_date=None`、`unresolved_on=None`；这不是成功或失败标签。自然轮次尚未完成与数据未决分开，不用固定短窗口补出整轮结果。

## 输出边界

`SectorRoundReplay` 包含板块、声明起日、as-of、目标交易日、阶段、轮次、确认计数、剩余冷却、缺口与原因。`decision_date` 是应评价的最新收盘日；`unknown` 时不表示该日已成功处理。

`replay_complete` **只表示在调用方的初始状态假设下，已提供指标的回放没有遇到缺口**。它不是 `input_pool_complete` 或 `declared_scope_complete` 的数据资格证明，也不验证指标计算正确、历史成员齐备、真实样本可用或策略有效。规则版本不代替数据版本；正式输入清单和发布流程仍须另外满足。

同一输入重复运行/改变行顺序产生同一结果和逻辑键。调用方不能将每次返回的整个轮次集合追加后再按行数统计。没有 A 提示也生成 B 轮次；A→B 关系、多 A 关联、历史冠军、两类名单、月末地量适配及统计分母并不在这个首批模块中。

## 合成验证

测试全部使用虚构指标与显式虚构日历，不读取行情或保留样本。先跑同一纯函数路径的代表性成功、重复回放、缺数、迟到和非法输入：

```bash
.venv/bin/python -B -m pytest -q tests/research/test_a_share_sector_rounds.py -k smoke
```

再检查完整状态机与原牛熊/筛选兼容性（研究测试不在根默认发现目录内）：

```bash
.venv/bin/python -B -m pytest -q \
  tests/research/test_a_share_sector_rounds.py \
  tests/research/test_a_share_market_regime.py \
  tests/research/test_a_share_sector_opportunities.py \
  tests/research/test_a_share_risk_state.py

pyright --pythonpath .venv/bin/python \
  experiments/a_share_sector_rounds.py tests/research/test_a_share_sector_rounds.py
```

这些检查验证实现规则，不验证真实 RS5/MA20 序列、牛熊判断准确率、投资收益或样本外有效性。首批合成工程完成不代表 P0 或 P2 全部完成，不授权读取真实行情、回测或交易。
