# A股分红生命周期来源审计V2

## 结论

**`SOURCE_CAPTURED_2025 / IMPLEMENTATION_LIFECYCLE_COMPLETE / NO_BACKTEST_RUN`**

已确认巨潮资讯网第一方公告接口可按日期和关键字分页获取全市场`权益分派实施公告`，并从`static.cninfo.com.cn`下载官方PDF。公告提供证券代码、公告日期、公告ID和原始PDF；仅有日期没有可靠的日内时间，因此统一按公告日收盘后可用处理。

## 2025全年验证

- 已完整覆盖12个月；
- 唯一实施公告：4507份；
- 现金分红公告：4488份，纯送转或更正公告19份；
- 当前沪深普通A股现金分红范围：4222份；
- 沪深普通A股完整解析：4222/4222；
- 提取字段：公告日、股权登记日、除权除息日、现金红利发放日、税前每股现金红利；
- 北交所范围7份仍有格式差异，但不属于当前`.SH/.SZ`策略范围；
- 各批次原始与规范化SHA256见`a-share-cninfo-dividend-2025-capture-summary.csv`。

采集与解析入口：

- `experiments/fetch_cninfo_dividend_lifecycle.py`
- `experiments/parse_cninfo_dividend_lifecycle.py`
- `overall/a-share-cninfo-dividend-2025-01-normalized.csv`

## 尚未解除的阻塞

官网一次性全年查询返回4552行但仅2550个唯一公告ID，并遗漏月度查询可见的1957个ID，因此不能作为完整性权威。按月查询得到4507个互不重复公告ID，月度分页捕获数与落盘记录逐月一致。

更重要的是，实施公告只证明最终登记、除权和支付安排，尚不构成完整的声明、股东大会批准、取消、更正和替换链；单年数据也不足以验证连续三年分红增长。

分红增长＋现金覆盖策略仍缺：

1. 多年完整实施公告及修订终端集；
2. PIT年度经营现金流和基准股本单位权威；
3. 全市场状态、费用、税费及公司行动执行权威；
4. 正式多股票A股Backtest准备入口；
5. 预先冻结的独立holdout。

因此来源状态由完全未知改善为有界可采集，但仍禁止回测和交易，`trade_authorized=false`。
