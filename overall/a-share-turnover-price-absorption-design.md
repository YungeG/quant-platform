# A股换手—价格响应吸收扩散模型预注册设计

- **主变量：** 总成交活跃度；不使用大小单或供应商净流入
- **方向判别：** 成交后价格相对VWAP和日内区间位置
- **历史：** 2018—2022发现、2023—2024验证、2025冻结保留、2026当前观察

## 个股定义

```text
turnover_proxy = Amount / CircMV
activity_ratio = turnover_proxy / 过去20日turnover_proxy中位数
vwap = Amount / Volume
close_vs_vwap = Close / vwap - 1
close_location = (Close-Low)/(High-Low)
```

`abnormal_activity`：activity_ratio>=1.5且处于个股过去120日90%分位以上。

- `absorption_stock`：abnormal_activity、close_vs_vwap>0、close_location>=0.60；
- `distribution_stock`：abnormal_activity、close_vs_vwap<0、close_location<=0.40；
- `persistent_absorption`：最近3日至少2日为absorption_stock；
- `new_absorption`：当日首次进入且过去5日均未进入。

每日动态关注名单为persistent_absorption与new_absorption并集，按activity_ratio排序最多20只。

## 板块状态

保存吸收/派发广度、新吸收比例、持续吸收龙头数、吸收异常换手集中度、吸收熵、关注集合持续性及`absorption_breadth-distribution_breadth`。阈值按板块自身过去120日分位。

- `ABSORPTION_SEED`：吸收广度上穿80%分位、持续吸收龙头>=3、吸收广度>派发广度；
- `BUYING_DIFFUSION`：种子后10日内吸收广度连续3日>=80%分位、新吸收比例>=70%分位、吸收广度>派发广度、集中度低于种子日；
- `BROAD_ADVANCE`：吸收广度>=90%分位且吸收熵>=70%分位；
- `DISTRIBUTION`：派发广度>=80%分位且连续2日高于吸收广度；
- `END`：扩散后吸收广度连续3日<70%分位，或派发广度连续3日高于吸收广度；
- 种子10日未扩散为FAILED_SEED。

同一板块结束前不生成新波段。

## 执行和Gate

以BUYING_DIFFUSION日为T，T+1开盘；保存30/35/40日板块收益、active、最高/最低绝对和相对收益、跑赢沪深300天数及每日动态关注名单。完整事件>=30；35日绝对正收益率和跑赢比例>=60%；主成功率>=55%；active中位数>=2%；bootstrap下界>0；30/35/40日中位active均>0；至少两个时期为正；去最高5%后为正；2025成功率>50%且active中位数>0。

不得调整1.5、90%、0.60/0.40、3/5/10日、80/70/90%或结果期限复活失败版本。
