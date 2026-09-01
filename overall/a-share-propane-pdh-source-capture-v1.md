# A股丙烷—PDH—聚丙烯源捕获 V1

## 裁决

- **状态：** `source_capture_completed`
- **范围：** `PG=PGL.DCE`、`PP=PPL.DCE`，半开区间 `[2020-03-30, 2026-08-29)`。
- **数据裁决：** 交易所代理数据闭合；物理利润仍 `SOURCE-BLOCKED`。
- **交易、Shadow、Backtest授权：** 均为 `false`。

## 捕获结果

| 项目 | 结果 |
| --- | ---: |
| 成功请求 | 321 |
| 失败请求 | 0 |
| 原始响应 | 321 |
| 连续日线 | 3,115行 |
| 连续映射 | 3,116行 |
| 映射月合约日线 | 3,116行 |
| 仓单 | 22,524行 |
| 完整运行 | 148秒 |

查询构成：连续日线8次、连续映射8次、月合约日线149次、仓单156次。

完整attestation：`overall/a-share-propane-pdh-source-capture-v1.json`。

## 完整性

- PG、PP映射与月合约日线：`3,116 / 3,116`逐日exact-cover。
- 原始响应树SHA-256：`92a5e7fcfdcde8f83fa17b7781571245f13226bce03d658bd3040adc995756e7`。
- 查询账本SHA-256：`5f2eb28083ae4961dc6809f25eafc9b1c34d52ea5172db68bc9ab30230d58484`。
- PG月合约71个；PP月合约78个。
- PP在`2022-02-21`有映射及月合约数据，但供应商连续序列缺失；没有补值或删除。

输出SHA-256：

| 输出 | SHA-256 |
| --- | --- |
| `fut_daily.parquet` | `ac9807483bbf96254d5d4ab8ebce758098aedc09d29c286b15a29eaaf6a9f675` |
| `fut_wsr.parquet` | `d1c6bdffb14d96644f2b09c339ffd2e5704cfec72327618167a834c33c4633c9` |
| `fut_mapping.parquet` | `2df29daf04a1efabb3563238993f75ffddc86f1fcf7e9e8996d2fdadc73ec209` |
| `fut_native_daily.parquet` | `ed47f9099c2713cf941321ba1c097e83ff0d91430544f3eb6e1967a07179fe77` |

## 仓单覆盖

| 产品 | 行数 | 日期数 | 首日 | 末日 | 单位 |
| --- | ---: | ---: | --- | --- | --- |
| PG | 9,713 | 1,381 | 2020-07-29 | 2026-08-28 | 手 |
| PP | 12,811 | 1,500 | 2020-03-30 | 2026-08-28 | 手 |

PG上市日至2020-07-28没有该接口仓单记录，保持missing，不填0。两个产品的仓单也不互相换算或相减。

## 同路径Smoke

完整捕获前使用同一程序、同一接口和`PG,PP`配置执行 `[2024-01-02, 2024-01-06)`：8次请求全部成功，连续、映射、月合约和仓单分别为8、8、8、40行，耗时2秒，映射exact-cover通过。

首次smoke失败是命令将日志预先重定向到捕获目录，使目录在manifest产生前非空；未触发网络抓取。重试把日志移到目录外后通过，生产代码无需修改。

## 因果结论

东华能源2021及2024年报披露LPG采购合同以`CP`价格为基础，公司通过进口采购、纸货、期货、船货和库存管理控制成本。大商所PG是境内燃料LPG合约，不能直接替代进口丙烷CP/CFR成本。

因此当前只能保留：

```text
PG = domestic_fuel_lpg_proxy
PP = domestic_polypropylene_price_observation
PP/PG physical margin = unauthorized
```

东华能源5条PDH/PP资产记录全部仍为`partial`。当前数据不能冻结东华能源买入规则，也不能扩展为PDH行业篮子。

## 下一安全动作

寻找并冻结带历史发布时间、许可与原始记录的进口丙烷CP/CFR序列。未取得前，不定义PG—PP价差策略，不运行收益研究。
