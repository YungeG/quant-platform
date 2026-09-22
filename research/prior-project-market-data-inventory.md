# 历史项目行情数据盘点

## 结论

之前的项目里确实存在大量可复用行情数据。对当前 BTCUSDT 日频时间序列动量候选，最有价值的是：

1. `crypt-gemini/artifacts/carry_audit_20260728/input/`：BTC/ETH 永续与现货 1 小时 Bar、资金费率、部分 funding mark、来源 URL、retrieval time 和文件 SHA-256。
2. `crypt-gemini/artifacts/historical_bundle_8symbols/prepared/`：8 个币种连续的 1d/1h/funding 研究 Bundle 和稳定文件哈希。
3. `crypt-gemini/data/n5lite/`：约 537 个 USD-M 合约的日线，以及约 536 个合约的 1h/funding 数据。
4. `/srv/bcache-8t/ygguo/crypt/mm_l1_engineering_20260720`：约 200 GiB 的 ETHUSDT 官方 checksummed `bookTicker`/`aggTrades` 原始档案和 funding 原始响应。

项目所有者已确认这些本地数据文件下载后没有被人工修改，并授权本研究直接使用。后续以当前文件字节及其 SHA-256 作为 canonical local dataset identity，不重新下载、不覆盖原文件，也不在原目录做清洗或补写。

这些数据足以立即启动 **development/exploratory** 验证。该确认关闭了“下载后发生人工修改”的顾虑，但不改变以下独立事实：部分下载程序在写 CSV 时做过 JSON→表格和数值规范化；历史数据已被其他研究读取；provider availability/revision authority、历史规则和账户费率仍不完整；Funding H3 决策仍然成立。因此本地数据可以直接使用，但不能仅凭“未人工修改”自动成为当前 Platform 的正式 `SUPPORTED` 证据。

## 1. 可复用性矩阵

| 数据集 | Coverage | 完整性证据 | 当前用途 | 正式 Validation |
| --- | --- | --- | --- | --- |
| Carry audit BTC/ETH | 2021-01-01 至 2026-07-27，1h + funding；另有 spot | retrieval time、URL、row count、每文件 SHA-256；1h 连续 | **首选 BTC pilot 输入** | 不可直接 `SUPPORTED` |
| Historical bundle 8 symbols | 2021-01-01 至 2026-05-26，1d/1h/funding | prepared manifest、连续性校验、每文件 SHA-256 | 回归、parity、策略机械验证 | 不可直接 `SUPPORTED` |
| n5lite full universe | 537 个 1d、536 个 1h、536 个 funding 文件 | 部分结果 artifact 保存文件 hash | 截面研究、候选发现 | 使用前必须重新冻结快照 |
| Full-universe daily prepared | 378 个合约，日线至 2026-06-14 | CSV 本身；根目录无完整 source manifest | 截面信号探索 | 不可直接使用 |
| BTC/ETH 1m caches | 一年 1m；另有 2026-05 至 2026-07 holdout 段 | 文件 hash；内部分钟连续 | 执行延迟/滑点诊断 | 非 provider authority |
| ETH MM L1 raw archive | 2024-03-01 至 2024-03-30 | 官方 ZIP checksum、原始 funding bytes、request receipt | G12 adapter、执行与微观结构验证 | 最强原始来源，但只有 ETH/30 天 |
| crypto-quant-platform fixture | 9 根 ETHUSDT 合成 1m Bar | Git fixture | 单元测试 | 不是真实行情 |

## 2. 首选：Carry audit BTC/ETH Bundle

路径：

```text
/home/ygguo/agent-projs/crypt-gemini/artifacts/carry_audit_20260728/input
```

Manifest：

```text
manifest SHA-256:
13875c8c17d97742db1d3a8e47c5ef503c97fd939987a04e8f9b4d98714bdbde

retrieved_at:
2026-07-28T09:19:03.125215+00:00
```

### BTCUSDT

| Kind | Rows | Coverage | SHA-256 |
| --- | ---: | --- | --- |
| Perpetual 1h | 48,816 | 2021-01-01 00:00 至 2026-07-27 23:00 UTC | `9d36819c364b0d07ced06198ed92480e0ec63cde3a89b5616b6068b85a6f3e8f` |
| Funding | 6,102 | 2021-01-01 00:00 至 2026-07-27 16:00 UTC | `67618d554a2bf66b6242077c2fa0cc8a3e439393c1c17706d4f2d7a5ee396f4e` |
| Spot 1h | 48,802 | 2021-01-01 至 2026-07-27 | `7457b33f0a9be22387eeded95f30ee15a7efc4a31ee066732b771120a958b31c` |

Perpetual 1h 文件严格单调、无重复、无小时缺口。Funding 文件无超过预期 8 小时加 1 秒的缺口；`mark_price` 共 3,002 行，从 2023-10-31 08:00 UTC 开始存在。

### 优点

- 对 BTC 日频动量所需样本长度足够；可从完整 1h 数据确定性聚合 UTC 日线。
- Manifest 保存来源 endpoint、retrieval time、row count 和内容哈希。
- Funding rate 和部分 funding mark 已在同一 Bundle。
- 现有 carry audit 已验证输入哈希、覆盖和可重复运行。

### 限制

- 项目所有者确认生成后的 CSV 未被人工修改；但下载程序写入时已将 API JSON 规范化为 pandas CSV，部分 decimal lexeme 与 provider 原始字符串不同。
- 2023-10-31 之前没有 funding mark。
- `historical_rules_evidence=false`，账户费用也是假设。
- 当前 rules JSON 是 retrieval 时的状态，不是历史规则时间线。
- Manifest 证明本地输入身份，不证明历史 participant availability 或完整 correction lineage。
- 全部区间已被历史项目读取，不能重新命名为 untouched holdout。

### 判定

这是当前 **最适合立即运行 BTCUSDT TSM pilot** 的输入。Pilot 必须标记：

```text
POST_HOC_ONLY
NORMALIZED_API_DATA
NON_HISTORICAL_RULES
ACCOUNT_FEE_ASSUMPTIONS
NO_PROVIDER_AVAILABILITY_AUTHORITY
NO_FUNDING_REVISION_CLOSURE
```

使用该 Bundle 的结果最高只能是 exploratory/development `INCONCLUSIVE`，不能是 Platform `SUPPORTED`。

## 3. Historical bundle 8 symbols

路径：

```text
/home/ygguo/agent-projs/crypt-gemini/artifacts/historical_bundle_8symbols/prepared
```

Market manifest SHA-256：

```text
feae9f18944b799ff68ea51e7c3093d1c98c13bfe6c4ceb2391bf779f58535ca
```

BTC/ETH 均包含：

- 1,972 根连续 UTC 日线；
- 47,328 根连续 UTC 小时线；
- 5,916 个 8 小时 funding slot；
- 覆盖 2021-01-01 至 2026-05-26；
- symbol manifest 和 prepared file SHA-256。

BTC 文件：

```text
btc_usdt_1d_prepared.csv
sha256: 690d32f00b15e5925c838d742278978925923a0584b9599a22147281fc88090f

btc_usdt_1h_prepared.csv
sha256: 6b2db0661e7776f8cc651c1e0c8f60454958661e9452a2d1270dbbeffb1ceb6d

btc_usdt_funding_prepared.csv
sha256: d7cd7eaace810ba6c6d51558b9e258417cb67e7db3a683781c1907a43d12d0b2
```

准备程序 `research/datafeed/prepare_binance_bundle.py` 会拒绝重复/非单调时间、小时缺口、非完整 UTC 日、非法 OHLC geometry，并生成确定性文件哈希。

限制：symbol/market manifest 只证明 prepared 文件身份，没有请求 URL、retrieval time、原始响应或 provider receipt；funding 仅保留 rate；`current_pinned_rules.json` 将 2026-07-19 捕获的当前规则投射到 2021-2026，明确是 `NON_HISTORICAL_RULES`。

该 Bundle 比可变的 `data/n5lite` 更适合作为机械回归输入，但 provenance 弱于 Carry audit Bundle。

## 4. n5lite 全市场数据

路径：

```text
/home/ygguo/agent-projs/crypt-gemini/data/n5lite
```

当前文件数：

```text
1d: 537
1h: 536
funding: 536
```

抓取程序：

```text
crypt-gemini/scripts/fetch_n5lite_universe.py
crypt-gemini/research/datafeed/fetch_binance_crypto_data.py
```

来源是 Binance public REST `/fapi/v1/klines` 与 `/fapi/v1/fundingRate`。程序会分页、重试并输出 CSV，但不保留原始响应、headers、每页 receipt 或 acquisition manifest；funding 输出丢弃 provider `markPrice`。

目录是 untracked/ignored 的下载缓存；项目所有者确认没有人工编辑。部分文件曾由采集程序继续更新，因此使用前必须冻结当前内容哈希。示例：

```text
btc_usdt_1d_20210101_20260608.csv
filename end: 2026-06-08
actual final row: 2026-07-02
mtime: 2026-07-02
```

文件名与内容范围已经漂移，说明不能直接把目录当 immutable authority。它仍非常适合：

- broad-universe 候选发现；
- 截面动量/流动性排序的 exploratory research；
- 生成一个重新冻结、有限范围、带哈希的 legacy source snapshot。

## 5. BTC/ETH 分钟级数据

主要文件：

```text
crypt-gemini/data/btc_usdt_1m_1y.csv
525,603 rows
2025-05-24 14:01 至 2026-05-24 14:03
sha256: a5d971c2d396573514e0ce0149565f55f08f5cbf3faafc6127a03b09dca2f65d

crypt-gemini/data/new_holdout/btc_usdt_1m_20260526_20260710.csv
64,801 rows
2026-05-26 00:00 至 2026-07-10 00:00
sha256: 6ba0981ea792f46a910c0ec4847b4c5cb127dcecde272228057f30d360a6d61a
```

两个文件内部分钟连续、无重复。它们可用于 entry-delay、next-open 和短期滑点敏感性诊断，但没有 source receipt、历史规则、mark/funding 对齐和 untouched status，不能替代主 Bundle。

## 6. 最强原始证据：ETH MM L1 archive

路径：

```text
/srv/bcache-8t/ygguo/crypt/mm_l1_engineering_20260720
size: 200G
```

Raw bundle receipt：

```text
sha256:
e731f0007a380601306ad0299aa542e015a6971b3e7094f75d45da9420553676
```

内容：

- ETHUSDT 2024-03-01 至 2024-03-30；
- 官方 `bookTicker` 与 `aggTrades` daily ZIP；
- 每日相邻 `.CHECKSUM`，下载值与官方值一致；
- Funding REST 原始 JSON page、request parameter hash 和 response hash；
- 已有 normalized bundle、manifest 和确定性 replay artifacts。

这是可直接转成新 G12A/G12L bounded fixture 的最强历史数据，但只有 ETH、30 天，不满足 BTC 日频 TSM 样本长度。适合验证 acquisition adapter、execution/liquidity 和 ETH replication，而不是 BTC 主绩效样本。

## 7. 对 BTCUSDT TSM 计划的影响

### 可以立即做

1. 冻结 Carry audit Bundle 的 BTC perp/funding 文件及 manifest hash。
2. 从 1h 数据确定性聚合日线，运行 7 日 TSM 的机械、因果和成本敏感性 pilot。
3. 严格版本可从 2023-10-31 之后开始，避免对缺失 funding mark 使用代理。
4. 把 Historical bundle 作为独立 parity 输入，检查聚合与策略结果是否一致。
5. 用 BTC 1m 数据做 next-event/一日延迟诊断。

### 仍不能做

- 不能把 2021-2026 的任一区间重新宣布为 untouched holdout。
- 不能使用当前 exchangeInfo 规则声称历史成交资格。
- 不能把本地 retrieval time 或经济时间替代 provider availability authority。
- 不能绕过 Funding H3 决策产生正式 `SUPPORTED` 结论。

### 建议的两轨验证

**Track 1 — Legacy pilot：**

- 输入：直接读取 Carry audit BTC perp/funding Bundle，不复制、不重新下载、不修改源文件；
- 启动前把 manifest 与三类输入文件 SHA-256 写入本次 Pilot receipt；
- 用途：快速判断 7 日 TSM 是否值得继续；
- 最高结论：`INCONCLUSIVE / PROMISING` 或 `REJECTED`；
- 不消耗未来正式 holdout。

**Track 2 — Platform authority：**

- 复用现有 Backtest G12 acquisition 工具和 ETH raw archive 模式；
- 为 BTC 建立新的 source-bounded raw archive/receipt；
- 另行解决 historical rules、fees 和 Funding H3 authority；
- 只在这些门关闭后运行正式 Validation。
