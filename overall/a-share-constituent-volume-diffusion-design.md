# A股板块内部成交量扩散模型预注册设计

- **唯一预测变量：** 成交活跃度及其板块内扩散；财报、分析师、估值和价格均不进入信号
- **价格用途：** 仅用于事后30/35/40日收益验证和执行计价
- **首阶段：** 2026描述性重建，不宣称预测有效

## 个股成交活跃度

```text
turnover_proxy = Amount / CircMV
activity_ratio = turnover_proxy / 个股过去20日turnover_proxy中位数
```

个股当日属于`abnormal_set`需同时满足：`activity_ratio>=1.5`，且处于该股过去120日自身历史90%分位以上。缺少20/120日历史不进入集合。

## 动态关注集合

- `persistent_leader`：最近3日中至少2日属于`abnormal_set`；
- `new_entrant`：当日进入`abnormal_set`，此前5日均未进入；
- 每日关注名单=`persistent_leader ∪ new_entrant`，按activity_ratio排序，最多20只；
- 保存每日进入、退出、持续天数和原始activity_ratio，不固定持有整个行业。

## 板块成交量状态

- `abnormal_breadth`：异常活跃股票/有效成员；
- `new_entrant_rate`：新进入股票/有效成员；
- `top5_excess_concentration`：前五只股票异常活跃增量占全部异常增量；
- `focus_persistence`：当日与前日abnormal_set的Jaccard；
- `activity_entropy`：异常活跃增量分布的标准化熵，越高表示越广泛；
- 所有板块阈值使用该板块自身过去120日历史分位。

## 成交量阶段

- `DORMANT`：无有效种子；
- `SEED`：abnormal_breadth首次上穿自身80%分位、异常股票>=3只、top5 concentration高于自身历史中位数；种子日Top-5异常股票记录为初始量能龙头；
- `DIFFUSION`：种子后10日内，breadth连续3日不低于80%分位、new_entrant_rate高于70%分位、top5 concentration低于种子日；
- `BROAD`：breadth>=90%分位且activity_entropy>=70%分位；
- `EXHAUSTION`：进入DIFFUSION/BROAD后，breadth连续3日低于70%分位，或new_entrant_rate与focus_persistence连续3日同时低于各自历史中位数；
- 种子后10日未进入DIFFUSION则为`FAILED_SEED`。

同一板块一轮波段结束前不产生新种子。事件保存seed/diffusion/broad/exhaustion日期和每日动态关注名单。

## 验证

2026阶段只比较进入DIFFUSION的波段和FAILED_SEED，观察T+1至30/35/40日板块和动态关注名单收益、最高/最低收益及跑赢沪深300天数。不得用价格反向修改成交量阶段。

历史验证另建版本：2018—2022发现、2023—2024验证、2025保留；需要>=30个独立扩散波段，35日正收益和跑赢沪深300比例均>=60%，active中位数>=2%，bootstrap下界>0，去最高5%后仍为正。
