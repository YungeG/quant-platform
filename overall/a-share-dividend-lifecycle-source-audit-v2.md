# A股分红生命周期来源审计V2

## 结论

**`SOURCE_CAPTURED_2022_2025 / LIFECYCLE_COMPLETE_RESEARCH_GRADE / NO_BACKTEST_RUN`**

已确认巨潮资讯网第一方公告接口可按日期和关键字分页获取全市场`权益分派实施公告`，并从`static.cninfo.com.cn`下载官方PDF。公告提供证券代码、公告日期、公告ID和原始PDF；仅有日期没有可靠的日内时间，因此统一按公告日收盘后可用处理。

## 2022—2025验证

- 已完整按月捕获4个自然年；
- 唯一实施公告：15652份；
- 现金分红公告：15505份，纯送转、更正或补充公告147份；
- 当前沪深普通A股现金分红范围：14691份；
- 完整生命周期：14691/14691；
- 公告`1212668618`的官方PDF未声明普通股支付日，使用已哈希保存的东方财富F10实施数据补充为2022-04-01；该条仅具补充vendor研究权威；
- 提取字段：公告日、股权登记日、除权除息日、现金红利发放日、税前每股现金红利；
- 两处PDF文字提取缺字及一处补充vendor日期记录在`a-share-cninfo-dividend-extraction-overrides-v1.json`；
- 统一数据：`a-share-cninfo-dividend-2022-2025-normalized.csv`，SHA256 `0e381e5755ec18e1bba00e136aae8e4a64cd95d2d4c7d1e55a90d4dfbe6c0a55`；
- 年度现金分红记录12485份，公告日当时可用的年度经营现金流覆盖12485/12485。

采集与解析入口：

- `experiments/fetch_cninfo_dividend_lifecycle.py`
- `experiments/parse_cninfo_dividend_lifecycle.py`
- `overall/a-share-cninfo-dividend-2022-2025-normalized.csv`

## 尚未解除的阻塞

官网一次性全年查询返回4552行但仅2550个唯一公告ID，并遗漏月度查询可见的1957个ID，因此不能作为完整性权威。按月查询得到4507个互不重复公告ID，月度分页捕获数与落盘记录逐月一致。

实施公告只证明最终登记、除权和支付安排，尚不构成完整的声明、股东大会批准、取消、更正和替换链。四年窗口已覆盖三年分红增长所需实施记录，但其中一条支付日依赖补充vendor来源，正式权威仍未闭合。

分红增长＋现金覆盖策略仍缺：

1. 决定是否接受公告`1212668618`的补充vendor支付日期，并闭合声明/取消/更正链；
2. 将已捕获的PIT经营现金流CSV升级为不可变、终端完整的数据权威，并绑定分红支付分母；
3. 全市场状态、费用、税费及公司行动执行权威；
4. 正式多股票A股Backtest准备入口；
5. 预先冻结的独立holdout。

因此研究级实施生命周期已完整，但尚未达到正式Backtest与数据权威Gate，仍禁止回测和交易，`trade_authorized=false`。
