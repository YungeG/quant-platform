# A股分红生命周期来源审计V2

## 结论

**`SOURCE_FOUND / BOUNDED_CAPTURE / NO_BACKTEST_RUN`**

已确认巨潮资讯网第一方公告接口可按日期和关键字分页获取全市场`权益分派实施公告`，并从`static.cninfo.com.cn`下载官方PDF。公告提供证券代码、公告日期、公告ID和原始PDF；仅有日期没有可靠的日内时间，因此统一按公告日收盘后可用处理。

## 2025年1月验证

- 捕获实施公告：129份；
- 当前沪深普通A股范围：122份；
- 沪深普通A股完整解析：122/122；
- 提取字段：公告日、股权登记日、除权除息日、现金红利发放日、税前每股现金红利；
- 北交所范围7份仍有格式差异，但不属于当前`.SH/.SZ`策略范围；
- 原始清单SHA256：`44e814469872e5c82116297d5605b7ba4caccebeefbf411a40179107766d9932`；
- 规范化CSV SHA256：`938cfb2e433180c762b39d7ad11284b4ed30a41a908da1c4243f4192e939a7a7`。

采集与解析入口：

- `experiments/fetch_cninfo_dividend_lifecycle.py`
- `experiments/parse_cninfo_dividend_lifecycle.py`
- `overall/a-share-cninfo-dividend-2025-01-normalized.csv`

## 尚未解除的阻塞

2025全年精确标题匹配为4552份，需按月检查点采集，不应一次性无界下载。更重要的是，实施公告只证明最终登记、除权和支付安排，尚不构成完整的声明、股东大会批准、取消、更正和替换链。

分红增长＋现金覆盖策略仍缺：

1. 多年完整实施公告及修订终端集；
2. PIT年度经营现金流和基准股本单位权威；
3. 全市场状态、费用、税费及公司行动执行权威；
4. 正式多股票A股Backtest准备入口；
5. 预先冻结的独立holdout。

因此来源状态由完全未知改善为有界可采集，但仍禁止回测和交易，`trade_authorized=false`。
