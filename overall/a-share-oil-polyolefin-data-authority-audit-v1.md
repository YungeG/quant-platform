# A股原油—聚烯烃产业链数据权威审计 V1

## 裁决

- **研究对象：** 上海原油期货 `SC` → 聚丙烯 `PP` / 线型低密度聚乙烯 `L` → A股相关生产资产。
- **当前状态：** **DATA-AUDIT COMPLETE / BACKTEST BLOCKED**。
- **可用部分：** 已保留的 PP、L 结算价和交易所仓单可用于探索性、结算价口径的研究。
- **阻塞部分：** 本地没有 SC 原始序列、连续合约换月映射和月合约；没有可授权的原油到 PP/L 物理利润转换系数；没有连续、带发布时间的全国 PP/L 开工率和商业库存；尚未建立资产级公司暴露表。
- **Platform 能力：** 当前公共根没有 A股行业产业链策略的具体 Backtest 准备操作，因此正式执行仍为 **plan-only**。

本文件只确认数据与因果链权威，不产生收益结论或交易授权。

## 1. 本地保留数据

原始数据位于：

`/home/ygguo/agent-projs/ai-crypt/platform-a-share-research/overall/a-share-resource-cycle-raw/`

清单：`manifest.json`

| 数据 | 行数 | 请求区间 | SHA-256 |
| --- | ---: | --- | --- |
| `fut_daily.parquet` | 31,496 | 2018-01-01—2026-08-27 | `de6d991574c67028db862b00a749886f08c250c118934a567c2133497c22cf0f` |
| `fut_wsr.parquet` | 562,347 | 2018-01-01—2026-08-27 | `a4e68df1cfee22308d597d0ab945c037bccbb31c681d4edb2f28ce15cbceba5c` |

### PP / L 价格

- `PPL.DCE`、`LL.DCE`各有 2,099 个不同结算日，覆盖 2018-01-02—2026-08-27。
- `settle`完整；PP 的 OHLC 有 554 个缺失，L 有 664 个缺失。
- 这些代码是供应商连续合约标识，不是交易所定义的可交易合约。
- 本地没有保存 `fut_mapping`、换月记录或对应月合约，因此只能复现供应商给出的连续结算价，不能独立重建连续序列。

Tushare 的 `fut_mapping`接口明确用于连续合约与月合约映射；未来获取时必须一并保留 `trade_date`、`mapping_ts_code`和映射版本：[Tushare fut_mapping](https://tushare.pro/document/2?doc_id=189)。

### PP / L 仓单

- PP：14,696 行、1,937 个日期。
- L：17,198 行、1,943 个日期。
- `warehouse`是仓库名称，`vol`是当日仓单量，单位为`手`；日期＋仓库没有重复行。
- 缺少仓单记录只能表示不可用，不能填为零。
- 仓单是交易所可交割标准仓单，不等于生产企业、贸易商、港口或全国商业库存。
- 当前规则包含仓单注销等交割机制，季节性下降不能自动解释为需求改善。

字段语义：[Tushare fut_wsr](https://tushare.pro/document/2?doc_id=140)。交易所规则：[DCE PP 业务细则](http://www.dce.com.cn/dalianshangpin/fgfz/6142914/6142926/6146588/%E5%A4%A7%E8%BF%9E%E5%95%86%E5%93%81%E4%BA%A4%E6%98%93%E6%89%80%E8%81%9A%E4%B8%99%E7%83%AF%E6%9C%9F%E8%B4%A7%E4%B8%9A%E5%8A%A1%E7%BB%86%E5%88%99%EF%BC%88%E6%A0%B9%E6%8D%AE2024%E5%B9%B411%E6%9C%881%E6%97%A5%E3%80%942024%E3%80%95102%E5%8F%B7%E6%96%87%E4%BB%B6%E4%BF%AE%E6%94%B9%EF%BC%89.pdf)、[DCE LLDPE 业务细则](http://www.dce.com.cn/dalianshangpin/fgfz/6142914/6142926/6146536/%E5%A4%A7%E8%BF%9E%E5%95%86%E5%93%81%E4%BA%A4%E6%98%93%E6%89%80%E7%BA%BF%E5%9E%8B%E4%BD%8E%E5%AF%86%E5%BA%A6%E8%81%9A%E4%B9%99%E7%83%AF%E6%9C%9F%E8%B4%A7%E4%B8%9A%E5%8A%A1%E7%BB%86%E5%88%99%EF%BC%88%E6%A0%B9%E6%8D%AE2024%E5%B9%B411%E6%9C%881%E6%97%A5%E3%80%942024%E3%80%95102%E5%8F%B7%E6%96%87%E4%BB%B6%E4%BF%AE%E6%94%B9%EF%BC%89.pdf.pdf)。

## 2. 权威矩阵

| 输入 | 当前证据 | 裁决 | 使用边界 |
| --- | --- | --- | --- |
| PP、L 结算价 | 本地供应商连续序列完整 | **PARTIAL** | 仅可做结算价探索研究；必须标记`vendor_continuous=true` |
| PP、L 交易所仓单 | 本地已保留仓库级记录 | **RESEARCH-USABLE** | 按产品、日期汇总`vol`；单位保持`手`；不能称为全国库存 |
| SC 原油价格 | 上海国际能源交易中心有官方合约和历史数据入口，本地未保留 | **SOURCE-BLOCKED** | 获取月合约、结算价、映射和原始响应后才能进入研究 |
| SC 仓单 | 上海国际能源交易中心有盘后仓单报表，本地未保留 | **SOURCE-BLOCKED** | 保存原始文件、发布时间和可用时间；最早 T+1 使用 |
| 连续换月权威 | 本地未保留映射或月合约 | **SOURCE-BLOCKED** | 不得把供应商连续代码当成交易所连续合约 |
| 原油→PP/L物理利润 | 合约只规定单位与交割品，没有物料平衡 | **SOURCE-BLOCKED** | 不得发明收率、联产品分摊、能耗、税费或物流系数 |
| PP/L全国开工率与商业库存 | 未找到连续、可回溯、带发布时间的第一方序列 | **SOURCE-BLOCKED** | 交易所仓单不能替代 |
| 国家统计局产量 | 有乙烯、原油加工和初级形态塑料等宽口径数据 | **PARTIAL** | 仅作宏观背景；保留发布日期与修订版本 |
| A股产能与工艺路线 | 年报、半年报和项目公告可作为权威 | **PARTIAL** | 必须建立资产级时点表，不能静态给整个公司贴“油制”标签 |

SC 官方合约：[上海国际能源交易中心 SC](https://www.ine.cn/eng/market/futures/energy/sc/contract/)。国家统计局发布与修订说明：[月度数据发布时间](https://www.stats.gov.cn/zs/tjws/jbtjzswd/tjzb/202503/t20250321_1959112.html)、[累计数据修订说明](https://www.stats.gov.cn/zt_18555/zthd/lhfw/2021/rdwt/202302/t20230214_1903910.html)。

## 3. 物理利润为什么不能直接计算

SC 报价单位是人民币/桶，PP、L 是人民币/吨。交易所合约没有提供：

- 炼厂原油品种和实际进料结构；
- 石脑油、乙烯、丙烯到聚合物的物料平衡；
- 多种联产品的收益分配；
- 能耗、加工费、税费和物流；
- 不同企业的油制、煤制、MTO、乙烷路线差异。

因此，`PP/SC`或`L/SC`最多只能作为**无量纲相对价格关系**，并明确记录`not_a_physical_margin=true`；在取得工厂级物料平衡权威前，不得称为“吨利润”或“裂解价差”。

## 4. A股资产暴露

必须建立如下时点表：

```text
issuer_code
asset_or_project
product
route
capacity_tpa
ownership_share
effective_from / effective_to
filing_publish_datetime
filing_url
page_or_table
source_hash
```

初步权威样例：

- 中国石油 2024 年报支持综合炼化及合成树脂暴露，但不能仅凭集团口径分配具体 PP/L 资产：[年报](http://static.cninfo.com.cn/finalpage/2025-03-31/1222962163.PDF)。
- 中国石化同时包含炼油、石化和煤化工，集团整体不能静态标记为油制：[年报](http://static.cninfo.com.cn/finalpage/2025-03-24/1222873281.PDF)。
- 宝丰能源披露煤/焦炉气→甲醇→烯烃路线，应与油制资产分开建模：[年报摘要](http://static.cninfo.com.cn/finalpage/2025-03-12/1222769507.PDF)。

产能表示潜在暴露，不等于当期产量、开工率或边际盈利。

## 5. Platform 能力边界

公共导出位于：

`backtest/packages/backtest-runtime/src/crypto_quant_backtest/__init__.py`

当前准备操作只有：

- `prepare_cash_development_backtest`
- `prepare_cash_target_stream_backtest`
- `prepare_model_bound_cash_development_backtest`

没有 A股多资产、行业或产业链策略的具体公共准备操作。不得通过私有 composer、engine 或 runner 绕过该限制。

## 6. 保留与许可

现有抓取通过供应商代理完成，必须保留：原始响应、源 URL、请求参数、获取时间、发布时间、SHA-256、解析器版本、连续映射和使用许可。

DCE 对历史行情及信息产品有单独的数据与许可规则，内部留存与对外再分发不是同一权限：[DCE 信息服务收费与许可材料](http://www.dce.com.cn/DCE/resource/cms/2020/08/2020082109044970414.pdf)。

## 7. 下一安全动作

1. 获取并冻结 SC 月合约、结算价、仓单、`fut_mapping`和换月规则。
2. 为 PP、L 补齐月合约和既有连续序列的映射证据。
3. 从公告建立油制、煤制、MTO、乙烷路线的资产级时点表。
4. 继续阻塞物理利润、全国商业库存和全国开工率特征。
5. 数据闭合后再预注册唯一的无参数扫描研究规则；在公共 Backtest 准备操作出现前，不运行正式 Platform Backtest。

## 结论

当前能源化工方向值得继续，但第一阶段不是回测，而是补齐 **SC 与连续换月权威、资产级生产路线**。直接用“PP/L涨价＋仓单下降”或虚构的原油裂解利润开始回测，会重复已有资源周期模型的因果缺口。
