# A股筹码成本压力预注册设计

- **状态：** frozen before full acquisition
- **数据：** cyq_perf月末全市场快照，2018—2026

## 信号

主信号为`chip_balance=-abs(winner_rate-50)`：获利盘过低代表上方套牢压力，过高代表止盈供给，中间状态得分最高。辅助诊断为筹码宽度`(cost_85pct-cost_15pct)/weight_avg`，不参与主排序。

检验主信号未来20日active IC及Top-30月度组合，股票池、执行和成本沿用基本面动量设计。

另做冻结分析师叠加：在分析师V1候选中排除Top-500股票winner_rate最高20%的获利盘拥挤股票，再按原EPS修正选择Top-30。

Overlay Gate：相对分析师V1最大回撤改善>=3个百分点、Sharpe提高>=0.05、CAGR下降不超过1个百分点、三折仍为正超额。不得调整50%中心或20%排除比例。
