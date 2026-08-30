# 科创50提前预警历史回测

> Research-only；不构成投资建议或 decision-grade 证据。

- 数据截止：2026-05-07
- 信号区间：2021-02-10 至 2026-05-07
- 周度信号：264 个
- 状态计数：`{"off": 171, "watch": 25, "on": 68}`
- 基准切换成本：20 bps/满额切换

## 策略结果

| 策略 | CAGR | 波动率 | Sharpe | 最大回撤 | Calmar | 切换 | 科创暴露 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| benchmark_buy_hold | -3.19% | 17.83% | -0.10 | -45.60% | -0.07 | 0 | 0.0% |
| target_buy_hold | 2.94% | 29.67% | 0.25 | -60.08% | 0.05 | 1 | 99.9% |
| confirmation_only | 1.82% | 22.77% | 0.20 | -44.65% | 0.04 | 28 | 26.6% |
| warning_full | 1.33% | 24.39% | 0.18 | -50.74% | 0.03 | 51 | 35.3% |
| warning_staged | 1.63% | 23.33% | 0.19 | -47.73% | 0.03 | 57 | 31.0% |

## 预警质量

- 标签：`future20_excess>=5% and future60_excess>0`
- 标签基础发生率：40/250（16.0%）
- WATCH 周精确率：19.2%
- WATCH 周召回率：25.0%
- 确认周精确率：22.7%
- 确认周召回率：37.5%
- WATCH 新预警命中：6/27
- 新预警精确率：22.2%
- 每年假预警：4.2
- 命中后达到 5% 相对超额的中位交易日：9.5

## 条件数量敏感性

| 最少满足条件 | CAGR | Sharpe | 最大回撤 | 切换 | 科创暴露 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 4.25% | 0.30 | -53.09% | 55 | 50.8% |
| 3 | 1.33% | 0.18 | -50.74% | 51 | 35.3% |
| 4 | 1.93% | 0.20 | -44.65% | 30 | 27.3% |
| 5 | 1.82% | 0.20 | -44.65% | 28 | 26.6% |

## 年度收益

- `benchmark_buy_hold`：2021 -14.93%, 2022 -21.63%, 2023 -11.38%, 2024 14.68%, 2025 17.66%, 2026 5.84%
- `target_buy_hold`：2021 -3.06%, 2022 -31.35%, 2023 -11.24%, 2024 16.07%, 2025 35.92%, 2026 24.90%
- `confirmation_only`：2021 -6.85%, 2022 -30.14%, 2023 -5.52%, 2024 18.89%, 2025 45.66%, 2026 3.20%
- `warning_full`：2021 -7.99%, 2022 -26.21%, 2023 -15.38%, 2024 23.28%, 2025 37.30%, 2026 10.20%
- `warning_staged`：2021 -7.40%, 2022 -28.17%, 2023 -10.53%, 2024 21.24%, 2025 41.44%, 2026 6.66%

## 限制

- Sohu index history is a third-party research source, not immutable provider authority.
- Breadth uses all observed STAR-board 688*/689* stocks, not historical 000690 constituents.
- Sector diffusion uses three Shenwan industry proxies.
- 000688 history begins at 2019-12-31; the 271-observation warmup shortens the evaluation sample.
- Returns use index closes and assumed switch costs, not ETF tracking, fees, slippage, or executable fills.
- Rules were evaluated retrospectively and are not genuine prospective out-of-sample evidence.

完整数值和逐周信号见同名 JSON。
