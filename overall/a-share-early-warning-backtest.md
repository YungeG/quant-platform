# 科创成长提前预警历史回测

> Research-only；不构成投资建议或 decision-grade 证据。

- 数据截止：2026-05-07
- 信号区间：2024-08-09 至 2026-05-07
- 周度信号：91 个
- 状态计数：`{"off": 50, "watch": 7, "on": 34}`
- 基准切换成本：20 bps/满额切换

## 策略结果

| 策略 | CAGR | 波动率 | Sharpe | 最大回撤 | Calmar | 切换 | 科创暴露 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| benchmark_buy_hold | 24.81% | 19.41% | 1.30 | -15.66% | 1.58 | 0 | 0.0% |
| target_buy_hold | 96.87% | 39.61% | 2.00 | -16.95% | 5.72 | 1 | 99.8% |
| confirmation_only | 36.92% | 29.44% | 1.27 | -18.32% | 2.02 | 14 | 39.3% |
| warning_full | 36.47% | 29.88% | 1.24 | -22.62% | 1.61 | 22 | 45.6% |
| warning_staged | 36.74% | 29.55% | 1.26 | -20.40% | 1.80 | 25 | 42.4% |

## 预警质量

- 标签：`future20_excess>=5% and future60_excess>0`
- 标签基础发生率：30/77（39.0%）
- WATCH 周精确率：64.7%
- WATCH 周召回率：36.7%
- 确认周精确率：31.2%
- 确认周召回率：33.3%
- WATCH 新预警命中：8/11
- 新预警精确率：72.7%
- 每年假预警：2.1
- 命中后达到 5% 相对超额的中位交易日：10.0

## 条件数量敏感性

| 最少满足条件 | CAGR | Sharpe | 最大回撤 | 切换 | 科创暴露 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 71.58% | 1.74 | -20.73% | 21 | 64.0% |
| 3 | 36.47% | 1.24 | -22.62% | 22 | 45.6% |
| 4 | 36.92% | 1.27 | -18.32% | 14 | 39.3% |
| 5 | 36.92% | 1.27 | -18.32% | 14 | 39.3% |

## 年度收益

- `benchmark_buy_hold`：2024 18.11%, 2025 17.66%, 2026 5.84%
- `target_buy_hold`：2024 36.76%, 2025 82.27%, 2026 30.48%
- `confirmation_only`：2024 12.05%, 2025 53.71%, 2026 0.34%
- `warning_full`：2024 6.31%, 2025 47.16%, 2026 9.84%
- `warning_staged`：2024 9.16%, 2025 50.42%, 2026 5.01%

## 限制

- Sohu index history is a third-party research source, not immutable provider authority.
- Breadth uses all observed STAR-board 688*/689* stocks, not historical 000690 constituents.
- Sector diffusion uses three Shenwan industry proxies.
- 000690 history begins at 2023-06-21; the 271-observation warmup shortens the evaluation sample.
- Returns use index closes and assumed switch costs, not ETF tracking, fees, slippage, or executable fills.
- Rules were evaluated retrospectively and are not genuine prospective out-of-sample evidence.

完整数值和逐周信号见同名 JSON。
