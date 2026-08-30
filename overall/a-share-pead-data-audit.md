# A股盈利预告/PEAD数据审计

## 结论

`~/.config/ai-crypt/xiaodefa-token`是`https://fast.xiaodefa.cn`代理的`x-api-key`，不是Tushare原生Token。通过代理调用，以下VIP接口已验证可用：

- `forecast_vip`
- `express_vip`
- `income_vip`
- `fina_indicator_vip`

因此盈利公告研究已从`DATA-BLOCKED`变为`RESEARCHABLE`。

## 覆盖抽样

| 报告期 | forecast_vip | express_vip | income_vip | fina_indicator_vip |
| --- | ---: | ---: | ---: | ---: |
| 2016-12-31 | 2,898 | 1,629 | 5,430 | 10,425 |
| 2020-06-30 | 1,854 | 147 | 9,000+ | 10,706 |
| 2026-06-30 | 1,911 | 50 | 3,588 | 3,635 |

`forecast_vip`返回完整字段：证券代码、公告日、报告期、预告类型、净利润变化区间、净利润区间、上年利润、首次公告日和修订标记。

## PIT处理

同一公司同一报告期可能有1—4条记录。研究主事件冻结为：

- `ann_date == first_ann_date`的首次业绩预告；
- 保留原始公告日，不用后续修订覆盖首发信号；
- 缺少`p_change_min/max`的事件不参与数值信号；
- T日公告，最早T+1开盘进入；不假定知道公告时分秒；
- 后续修订只用于审计，不作为回填首发数据。

2016年年报样本中约21%证券存在重复/修订记录，说明简单按公司报告期保留最新行会产生未来函数。

## 当前研究边界

第一阶段只验证管理层业绩预告后的漂移：`预增`和`扭亏`事件。它是PEAD家族的公告信息策略，但不等同于分析师一致预期SUE。若第一阶段无edge，不继续建设更重的income/analyst surprise管线。
