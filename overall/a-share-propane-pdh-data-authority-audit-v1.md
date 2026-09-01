# A股丙烷—PDH—聚丙烯数据权威审计 V1

## 裁决

- **对象：** 大连商品交易所液化石油气 `PG` → 聚丙烯 `PP` → 东华能源 `002221.SZ` 的已披露 PDH/PP 资产。
- **模式：** A股产业链 Plan / 数据权威捕获；不是策略 Backtest。
- **当前能力：** **PG/PP EXCHANGE DATA CAPTURABLE / PHYSICAL MARGIN SOURCE-BLOCKED / PLATFORM PLAN-ONLY**。
- **交易、Shadow、Backtest授权：** 均为 `false`。

本审计冻结下一步数据捕获，但不把国内燃料 LPG 期货价格解释为东华能源进口丙烷采购成本，也不产生任何收益结论。

## 1. 冻结数据切片

- 半开区间：`[2020-03-30, 2026-08-29)`；供应商请求末日为 `2026-08-28`。
- 产品及连续代码：`PG=PGL.DCE`、`PP=PPL.DCE`。
- 固定接口：`fut_daily`、`fut_mapping`、映射月合约 `fut_daily`、`fut_wsr`。
- 必须保留：每次请求参数、原始响应、UTC获取时间、响应SHA-256、查询账本、连续映射、月合约日线、Parquet摘要和整树摘要。
- PG于2020年3月30日上市；更早日期不进入切片。大商所合约页给出交易单位20吨/手、报价单位元/吨。

数据字段权威：

- Tushare `fut_mapping`：连续合约到月合约的逐交易日映射：<https://tushare.pro/document/2?doc_id=189>
- Tushare `fut_wsr`：仓库/厂库仓单日报：<https://tushare.pro/document/2?doc_id=140>
- 大商所PG合约：<http://www.dce.com.cn/dce/channel/list/2090.html>
- 大商所PG规则入口：<http://www.dce.com.cn/dalianshangpin/sspz/yhsyq/hyygz7622/6210766/index.html>

## 2. 因果边界

大商所PG是境内可交割液化石油气合约，标准品是燃料用LPG，交割体系允许不同组分等级。它可以观察境内LPG价格、交割和库存压力，但不能直接代表某家PDH工厂的进口高纯丙烷到岸采购成本。

东华能源披露：

- PDH以丙烷生产丙烯，PP装置再生产聚丙烯；
- 原料从北美、中东等全球市场采购；
- LPG采购合同以签约时 `CP` 价格为基础；
- 公司使用丙烷期货/纸货、船货和库存管理平抑采购成本。

来源：`002221-2021-annual`、`002221-2023-annual`、`002221-2024-annual`，冻结在 `overall/a-share-oil-polyolefin-issuer-sources-v1.json`。其中2024年报PDF SHA-256为 `c3adc77d8dfaed551fe4c059e8423232742977b7e457674e4c421fe849a88a21`。

因此：

- `PP/PG`、`PP-PG`或任意固定换算都不是物理吨利润；
- 不得发明丙烷收率、丙烯转化率、氢气副产收益、能耗、运费、关税、汇率或套保系数；
- PG与PP交易所仓单都不是全国商业库存；
- 后续最多把PG作为 `domestic_fuel_lpg_proxy=true` 的二级观察量。

## 3. A股暴露边界

复用 `overall/a-share-oil-polyolefin-issuer-assets-v1.csv` 中东华能源5条 `propane_PDH` PP资产状态：宁波一期、张家港、宁波三期及茂名试生产/运行状态。5条均为 `partial`，主要缺口是历史投产起点或权益时点。

第一版不得扩展为“PDH行业篮子”，也不得把卫星化学、宝丰能源、油制一体化公司混入同一成本曲线。单一发行人暴露不足以形成横截面策略。

## 4. 捕获接受条件

仅当以下条件全部满足，PG/PP源捕获才可标记完成：

1. 所有供应商请求成功且原始响应逐笔保留；
2. `fut_mapping`与月合约日线对PG、PP均实现逐日exact-cover；
3. 连续、映射、月合约和仓单输出都有行数与SHA-256；
4. PG与PP仓单单位分别报告，不跨产品或单位相加；
5. 现有目录重放必须依赖仓库内跟踪的attestation，篡改、孤儿文件、范围变化和协调修改均失败关闭。

任一条件失败即停止；不缩短区间、不改代码、不用连续价替代缺失月合约。

## 5. Platform能力

`crypto_quant_backtest`公共根没有A股产业链/行业/单发行人PG—PP策略的具体 `prepare_*_backtest` 操作。本工作只能冻结数据权威，不能通过私有composer、engine或runner执行正式Backtest。

## 下一安全动作

先用同一代码路径完成短区间PG/PP smoke；通过后才执行完整冻结捕获。即使完整捕获通过，下一步仍是寻找带历史发布时间的进口丙烷 `CP`/CFR价格权威，而不是直接回测PG—PP价差。
