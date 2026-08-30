# A股有方向成交量扩散模型预注册设计

- **唯一信号数据：** Tushare `moneyflow`原始买入/卖出分项；不使用财报、分析师、估值或价格生成信号
- **价格用途：** 仅用于事后30/35/40日收益和执行验证
- **历史：** 2018—2022发现，2023—2024验证，2025冻结保留，2026前向观察

## 原始计算

```text
large_buy = buy_lg_amount + buy_elg_amount
large_sell = sell_lg_amount + sell_elg_amount
large_net = large_buy - large_sell
all_buy = buy_sm + buy_md + buy_lg + buy_elg
all_sell = sell_sm + sell_md + sell_lg + sell_elg
directional_amount = all_buy + all_sell
large_net_rate = large_net / directional_amount
all_net_rate = (all_buy - all_sell) / directional_amount
```

不使用供应商`net_mf_amount`作为权威净额，只用于对账。无效分母保持missing。

## 个股动态集合

- `buy_leader`：large_net_rate>0且处于该股过去120日自身90%分位以上；
- `sell_leader`：large_net_rate<0且低于自身过去120日10%分位；
- `persistent_buy_leader`：最近3日至少2日为buy_leader；
- `new_buy_entrant`：当日buy_leader且前5日均不是；
- 动态关注名单为persistent_buy_leader与new_buy_entrant并集，按large_net_rate排序，最多20只。

## 板块状态

- 买入/卖出广度；
- 新买入股票比例；
- 板块large_net_rate和all_net_rate；
- 前五只正净买入集中度；
- 正净买入熵；
- 买入领导集合持续性；
- 所有板块阈值使用自身过去120日历史分位。

## 阶段

- `DORMANT`；
- `ACCUMULATION_SEED`：买入广度上穿80%分位、persistent买入龙头>=3、板块large_net_rate>0；
- `BUY_DIFFUSION`：种子后10日内买入广度连续3日>=80%分位、新买入比例>=70%分位、板块large_net_rate>0且买入广度>卖出广度；
- `BROAD_ACCUMULATION`：买入广度>=90%分位、正净买入熵>=70%分位；
- `DISTRIBUTION`：卖出广度>=80%分位且板块large_net_rate连续2日<0；
- `END`：扩散后买入广度连续3日<70%分位，或卖出广度>买入广度且large_net_rate连续3日<0；
- 种子后10日未扩散为`FAILED_SEED`。

同一板块结束前不生成新波段。每日保存动态关注、进入、退出和持续天数。

## 存储与审计

按自然月保存Parquet；请求账本区分成功空集与失败；保存SHA-256和字段。审计`(trade_date,ts_code)`重复、空值、原始分项与net_mf对账、年度覆盖、大小单占比和单位/分类结构断点。

## Gate

独立BUY_DIFFUSION完整事件>=30；35日绝对正收益率和跑赢沪深300比例均>=60%；active中位数>=2%；bootstrap均值下界>0；30/35/40日active中位数均>0；至少两个历史时期为正；去最高5%后仍为正；2025成功率>50%且active中位数>0。

不得根据结果修改120日、90/10%、3日、5日、10日、80/70/90%阶段阈值或30/35/40日结果期限。
