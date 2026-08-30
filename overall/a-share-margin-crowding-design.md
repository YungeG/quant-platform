# A股融资拥挤预注册设计

- **状态：** frozen before execution
- **数据：** MarginDetailData，2015—2026-06，无自然键重复

每月T日使用：

- `fin_intensity=RZYE/CircMV`；
- `fin_change20=(RZYE_T-RZYE_T-20)/CircMV_T`。

两者均预期与未来20日active return负相关。综合拥挤分为两项在Top-500中的高分位均值。

冻结分析师叠加：排除综合融资拥挤最高20%的股票，再按原EPS修正选择Top-30。只比较同一2015—2026-06样本内的分析师基准。

Overlay Gate：最大回撤改善>=3个百分点、Sharpe提高>=0.05、CAGR下降不超过1个百分点、三个固定时期仍为正超额。不得修改20日窗口、20%排除比例或权重。
