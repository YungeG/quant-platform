# A股突破位回踩V2预注册设计

- **状态：** frozen before execution
- **目标：** 区分真正“突破位由阻力转为支撑”的回踩，与假突破、派发和普通下跌
- **窗口：** 2016-01-01—2026-08-25

## 1. PIT股票池

- 上市至少252个交易日；
- 当日未停牌、价格至少5元；
- 过去20日平均成交额前50%；
- PIT流通市值前500；
- 非ST权威缺失单列限制。

## 2. 平台和突破

突破日前冻结：

- `breakout_level`：此前20日最高价；
- 该最高价距离突破日至少5个交易日；
- 此前40日振幅不超过30%；
- `ATR20`和过去20日成交额中位数。

有效突破日必须：

- 收盘 > `breakout_level + 0.5 ATR20`；
- 成交额 >= 过去20日中位数1.5倍；
- 收盘位置`(close-low)/(high-low) >= 0.70`；
- 非零振幅、非一字涨停；
- 同一股票一个事件结束前不重复创建突破事件。

## 3. 回踩状态机

突破后第3—12个交易日寻找回踩。

终止优先级：

1. 任一收盘 < `breakout_level - 1 ATR`：`support_break`；
2. 下跌日成交额 > 突破日成交额：`distribution_selloff`；
3. 第12日仍未触及回踩区：`no_retest_timeout`。

回踩区：最低价 <= `breakout_level + 1 ATR`，同时收盘 >= `breakout_level - 0.5 ATR`。

触及后还必须：

- 突破后至回踩日成交额中位数 <= 突破日成交额80%；
- 回踩日ATR5 <= 突破日ATR20的1.1倍；

否则分别记为`retest_volume_not_contracted`或`retest_volatility_expanded`。

## 4. 再启动触发

回踩确认后、最迟突破后第12日：

- 收盘重新站上breakout level；
- 收盘 > 前3日最高价；
- 收盘位置 >= 0.60；
- 当日成交额 > 前5日中位数；
- 非一字涨停。

未触发记为`no_recovery_timeout`。

## 5. 执行失败原因

触发后T+1开盘进入。逐事件记录：

- `missing_or_suspended_open`；
- `entry_limit_up`；
- `entry_gap_above_half_atr`；
- `entry_below_pullback_low`；
- `executed`。

## 6. Outcome

执行事件测量T+1开盘至第5/10/20个交易日开盘收益，扣31bp往返成本，并减同日PIT股票池等权收益。

结果原因：

- `successful_20d`：20日active>0；
- `early_failure`：5日active<=0且20日active<=0；
- `failed_after_initial_strength`：5日active>0但20日active<=0。

所有突破事件写入CSV，一条事件只能有一个结构终止原因和一个结果原因。

## 7. Event GO Gate

执行事件全部满足：

1. 数量>=300；
2. 10日成本后平均active>=1%；
3. 20日成本后平均active>=1%；
4. 20日active中位数>0；
5. 20日胜率>52%；
6. 三个固定时期至少两个20日平均active>0；
7. bootstrap 95%均值下界>0；
8. 执行拒绝率<=15%。

不满足全部为NO-GO；均值为正但稳健性不足为MARGINAL。
