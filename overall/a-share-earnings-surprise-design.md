# A股分析师一致预期盈利惊喜预注册设计

- **状态：** frozen before actual-EPS acquisition
- **窗口：** 2017—2025年度报告公告，收益观察至2026-08-26

每个股票/年度只使用最早`ann_date`的年度`fina_indicator_vip`实际EPS。公告日前一自然日，取过去180日内针对同一`yearQ4`、每家机构最新的`report_rc` EPS预测；至少3家机构，共识为中位数。

```text
surprise_to_price = (actual_eps - consensus_eps) / 公告前最后交易日收盘价
```

公告日仅有日期精度，统一在公告后下一交易日开盘进入。测量5/20/60日收益，扣31bp往返成本，并减同日PIT Top-500可交易股票等权收益。

## Gate

- 有效事件>=500；
- 全样本surprise与20日active Spearman>=0.02且p<0.05；
- 最高惊喜五分位20日平均active>=1%、中位数>0、胜率>52%；
- 最高五分位三个固定时期至少两个平均active>0；
- 按公告月份cluster bootstrap的95%均值下界>0。

本轮只做事件信号验证；Gate通过后才设计重叠持仓组合。不得修改180日、3家机构、价格归一化或五分位定义。
