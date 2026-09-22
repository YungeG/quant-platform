# A 股牛熊阶段识别 v1

> 归档说明（2026-09-22）：下文的 2026-09-21 行情、访问记录、测试数字及当时安装能力均为历史记录，不是本次重跑或最新市场判断。后续[依赖对齐](../implementation/dependency-alignment-20260921.md)已将根环境切换至 Backtest `8cc5b874`，公开 `prepare_cn_a_share_development_backtest` 已可导入；原先只有三个 cash preparation 的枚举不再代表当前环境，但这不等于本多股票研究已经获准或验收。
>
> 下文 `research/evidence/a-share-market-regime-20260921/` 中的原文、CSV、回执和结果为**本地保留、未随 Git 发布**的历史文件。新检出不含这些输入；相关回放命令只适用于另行取得原冻结文件的环境，不能通过重新下载来冒充原版本。本次归档不启动采集、回测或交易，也不重新认证旧结果。

## 用途与边界

入口：`experiments/run_a_share_market_regime.py`；纯算法：`experiments/a_share_market_regime.py`。

这是一个**可解释的收盘市场状态诊断策略**，判断指定时点最近一个已收盘交易日的阶段，不预测拐点、不生成交易订单。可选的[板块高波动筛选](#指定板块的高波动股票观察名单)在此基础上输出股票观察名单，不是买入指令。判断入口只读本地冻结数据，不联网，不隐式读取系统当前时间；仅显式传入 `--now` 时读取一次系统时钟。下方独立获取入口负责准备冻结输入，不在策略评估中联网。

它不修改原有 `run_bull_bear_selector.py` 的单 ETF 月末实验，也不沿用那份实验的历史牛熊结论。输出为 `diagnostic_only`，不是正式 Research / Backtest / Validation 证据，更不授予交易或部署权限。

## 当前快照诊断与既有工作复用（2026-09-21）

**本轮结果：截至 `2026-09-21T10:54:01.977824+08:00`，按当前已知快照重算，最近收盘日 `2026-09-18` 为 `bear` / 偏熊形态。** 这是固定价格规则对三指数代理的描述，不是盘中状态、全市场广度、转折预测或交易建议。默认历史点时模式仍是 `unknown`；没有把这个未通过的历史确认结果改成 bear。

### 借鉴了哪些已有工作

- [旧牛熊选择设计](../overall/a-share-bull-bear-selector-design.md) 与 `experiments/run_bull_bear_selector.py` 已使用 MA200 和 60 日动量。本工具沿用这些价格指标定义，并复用 `a_share_market_regime.py` 的同一指标/投票/窗口实现，不另建计算或收益模拟器。
- [旧结论](../overall/a-share-bull-bear-selector-conclusion.md) 为 **NO-GO**；其 `current_state=bear` 对应 **2026-08-25 的单 ETF 旧样本末条状态**，不能当作今天或三指数的结论。旧组合映射、收益数字和已使用样本不作为本任务的交易/OOS验证。
- [数据清单](../overall/research-data-inventory.md) 中的多ETF/基本面原始数据位于其他工作树，当前项目中核查的对应路径及旧实验实际引用的 `overall/a-share-multi-asset-etf-daily.csv` 均不存在。本轮不跨项目找密钥，不重采已取得的数据；直接复用本项目 `public-full-v2/` 的 651 条冻结价格、325 日历记录和来源回执。
- 已实际核查安装的 `crypto_quant_backtest` 公共根：准备操作仅有 `prepare_cash_development_backtest`、`prepare_cash_target_stream_backtest`、`prepare_model_bound_cash_development_backtest`。参照 [TSR-FI-01 接入验收](../implementation/tsr-fi-01-receipt.md) 与 [路线图](../implementation/roadmap.md)，这是通用 cash development 路径，不是本三指数/A股组合策略的已接受准备接口。**没有用私有 Backtest 类、现金示例或旧自写收益模拟来冒充正式 A 股回测。**

### 两种明确区分的口径

| CLI | 允许的历史窗口可见时点 | 输出含义 |
| --- | --- | --- |
| `--basis historical`（默认） | 各历史窗口截止日结束，且不晚于 as-of | 原 `a_share_market_regime_v1`；证明输入满足当时可见性约束后才能确认，默认 JSON 字节格式保持不变 |
| `--basis snapshot`（显式） | 所有回看窗口均以**当前评估 as-of** 为可见性截止 | 新 `a_share_market_snapshot_v1`；描述当前已知版本下的最近三日形态，不声称过去当时已发出这些信号 |

两种口径仍共享 MA200、动量60、三指数多数和三日连续形态，至少需要 202 个交易日；没有调参、重命名日期、回填时间或删除缺失记录。`snapshot` 中任何版本若在 as-of 之后才可用，仍返回 unknown。历史窗口的重算结果**不能用于冒充历史交易信号或历史收益回测**。

Python API 为 `evaluate_market_regime(..., basis=EvaluationBasis.SNAPSHOT)`；默认是 `EvaluationBasis.HISTORICAL`。返回值 `MarketRegime.basis` 明确记录语义。快照 CLI 输出 `result.basis=snapshot`、`historical_confirmation_claimed=false`，中文标签带“当前快照重算，非历史点时确认”；原因使用 `snapshot_pattern_*`，不沿用 `confirmed_*`。`--basis snapshot` **禁止与 `--stocks/--sectors` 合用**，现有股票门控继续使用默认历史模式。

### 本次真实计算与复核

使用 10:26 获取并冻结的版本，在 10:54 评估；所有价格均已在 as-of 前取得。独立重算各指数指标、三日投票及最终阶段，与程序一致：

| 指数 | 9月18日收盘 | MA200 | 60交易日动量（百分比四舍五入） | 当前快照形态 |
| --- | ---: | ---: | ---: | --- |
| 沪深300 | 4507.39 | 4694.56885 | -7.41% | bear |
| 中证500 | 7799.61 | 8030.81035 | -10.39% | bear |
| 中证1000 | 7687.59 | 7982.8481 | -10.62% | bear |

9月16、17、18三个回看窗口按当前快照重算的多数标签均为 bear，因此本口径输出 bear。此结论不补足三个日期**当时**的观测证据，历史模式仍因 `close_not_available` 返回 unknown，退出 `1`；输出已与修改前保存的 `regime-as-of.json` **逐字节比较一致**。

结果保存在本地未入库的 `research/evidence/a-share-market-regime-20260921/current-snapshot-run-2b939da7/`：`snapshot-now.json`、`snapshot-replay.json`、`verification.json`。原文与 CSV SHA-256 已重验；固定 as-of 的两次快照回放字节相同；`--now` 与对应 `--as-of` 回放仅时刻来源字段不同。源快照、旧回执、旧历史结果和旧代码哈希记录均未覆盖；新验证文件绑定本轮代码身份。

原时点复核命令（预期退出 `0`；不要将该旧 as-of 永远称作“当前”）：

```bash
.venv/bin/python -m experiments.run_a_share_market_regime \
  --prices research/evidence/a-share-market-regime-20260921/public-full-v2/prices.csv \
  --calendar research/evidence/a-share-market-regime-20260921/public-full-v2/calendar.csv \
  --basis snapshot --as-of '2026-09-21T10:54:01.977824+08:00'
```

判断之后的当前状态时，先准备覆盖实际评估时点的新快照，再使用 `--basis snapshot --now`。旧日历/收盘后缺当天价格会失败关闭；它不会自动更新行情，也不提供盘中判断。

## 固定规则

使用以下三个指数作为大、中、小盘市场代理；**这不是全 A 股个股广度，也不保证覆盖每个板块**：

| 指数 | CSV `ts_code` | 权重 |
| --- | --- | --- |
| 沪深300 | `000300.SH` | 一票 |
| 中证500 | `000905.SH` | 一票 |
| 中证1000 | `000852.SH` | 一票 |

在每个交易日 t，对每个指数计算：

- `moving_average = mean(close[t-199:t+1])`：包含当日收盘的 MA200。
- `momentum = close[t] / close[t-60] - 1`：60 个**交易日**动量，非自然日。
- `close > moving_average` 且 `momentum > 0`：该指数为 `bull`。
- `close < moving_average` 且 `momentum < 0`：该指数为 `bear`。
- 其他情况（包括等号、均线与动量方向冲突）：该指数为 `transition`。

至少两个指数为 bull / bear，才形成当日对应的候选阶段；无方向多数为 transition。任一必需数据缺失时，不能仅用其余两个指数投票。

| 最终阶段 | 含义 |
| --- | --- |
| `bull` / 牛市 | 最近连续 3 个交易日的候选阶段全部为 bull |
| `bear` / 熊市 | 最近连续 3 个交易日的候选阶段全部为 bear |
| `transition` / 震荡、转换期 | 无方向多数，或新方向尚未连续确认 3 日 |
| `unknown` / 无法判断 | 日历、历史长度、价格或可用时点证据不足 |

转换等待期不继续沿用旧的牛/熊标签。3 日确认降低单日翻转，但引入滞后，不是预测准确率保证。`consecutive_sessions` 只统计本次最后 3 个候选阶段中的连续支持天数，上限为 3，不代表完整牛熊持续时间或概率。

参数在观察真实行情前固定为 MA200、动量60、确认3；**最少需要 202 个完整交易日、每个指数 202 条收盘记录**。没有参数扫描、训练或按收益挑选阈值。Python API 可传 `RegimeConfig`（用于明确指定规则或短窗口测试），CLI 固定使用上述 v1 参数。

## 时点与数据要求

1. `--as-of` 与 `--now` 必须且只能选一个。`--as-of` 使用有时区的 ISO 时间；`--now` 在读取输入文件**之前**一次性获取系统当前时刻。两者统一为 `Asia/Shanghai`，作为固定评估截止时点；文件读取耗时不移动截止时点。纯算法仍只接受显式 `as_of`，不读取时钟。
2. 日历必须来自可靠的交易日历快照，从输入起日到 as-of 的中国日期**逐自然日完整覆盖**，包括周末、节假日的 `is_open=0`。不得简单用工作日推测中国交易日。
3. 交易日 15:00 起视为已收盘，但收盘记录还必须实际可用。盘中、休市日使用最近已收盘交易日，并显式输出 `decision_date`；当天收盘后缺少当天记录则 unknown，不能悄悄退回旧日。
4. `available_at` 是该版本收盘数据的真实可用时点，必须带时区且不早于该日 15:00。不得把盘中值当收盘，不得用文件修改时间或今日下载时间反推历史可用时间。
5. 默认 `--basis historical` 中，每个历史确认日只使用在该日结束前已可用的数据；截止时间为 `min(as_of, 确认日23:59:59.999999+08:00)`。显式 `--basis snapshot` 则对所有回看窗口统一使用评估 `as_of`，只能称为当前快照重算，不能追认历史信号。两种口径均不修改 `available_at`，也不能使用评估时点之后才取得的数据。
6. 窗口严格按日历交易日取值，不前向填充、不删掉共同缺失日、不缩小指数集合。暖机不足、日历过期/缺日、任何必需指数价格缺失或尚不可用均为 unknown，并给出原因。
7. 每个指数每个交易日只能有一个冻结版本。重复记录、非正/非有限价格、休市日收盘、非法代码、无时区时间或 malformed CSV 会直接报输入错误。需要多版本历史时，调用方必须提供具有真实可用时间的冻结版本；v1 不提供历史修订重建功能。

**程序只能检查结构与时间约束，不能验证外部数据供应方的真实性。** 日历和收盘数据的来源、版本及原始可用时间需要由数据准备方核验；本地 SHA-256 仅标识输入字节，不等于 Platform 数据授权或权威 MarketBundle 身份。

## 真实数据准备与本轮结果（2026-09-21）

09:14 的初次预检未发现当前进程的 Tushare 凭据或项目内候选快照；随后已通过**无需凭据的中证指数/上交所公开入口**取得完整窗口。凭据缺失不再是这条诊断数据路线的阻碍，但历史可用性仍未证实。没有读取其他项目的凭据，也没有访问账户或交易接口。

### 来源与获取边界

独立入口：`experiments/capture_a_share_market_regime.py`，仅依赖 Python 标准库。公开解析函数为 `parse_calendar()`、`parse_index()`，获取函数为 `capture_snapshot()`。

| 来源 | 使用方式 | 限制 |
| --- | --- | --- |
| [中证指数官网](https://www.csindex.com.cn/en/indices/index-detail/000300) 的 `/csindex-home/perf/index-perf` | 固定三指数，日期范围显式；原始 JSON 留存 | 收盘价格与交易日不证明该版本历史发布时间；官网响应未来仍可修订 |
| [上交所 2025 年休市安排](https://www.sse.com.cn/disclosure/dealinstruc/closed/c/c_20241223_10767110.shtml) | 留存 HTML，严格解析完整年度休市表 | 仅年度安排，不证明没有临时停市；三指数实际日期必须与计算出的交易日精确覆盖 |
| [上交所 2026 年休市安排](https://www.sse.com.cn/disclosure/dealinstruc/closed/c/c_20251222_10802510.shtml) | 同上；周末与法定节假日均保留为关闭日 | 不采用“所有工作日都是交易日”，也不把调休周日当交易日 |

该路线仅用于本地诊断，**不是 G12M 接受的 Tushare/Binance Provider 扩展或正式 MarketBundle/Backtest 证据**，不改变现有 ADR、结果等级或交易授权。

获取器限制与失败行为：

- 仅允许明确列出的 HTTPS 日历地址及固定格式的中证三指数 URL；无认证头、不读取 token、不跟随重定向、不自动换源。每次响应最多 2 MB、超时 20 秒，请求间隔 0.5 秒，无无限重试。
- 查询自然日范围最多 400 天，只支持已固定来源的 2025/2026 年。截止自然日是获取开始的中国日期，指数只请求当时最近已收盘日及以前；日历仍覆盖当天。新年度必须先核验并明确加入来源，不能自动猜日历。
- `--output` 必须是不存在的新目录，已有目录一律拒绝。原文与逐次回执保留；失败写 `status=failed`，不输出成功获取 JSON。不得删除失败数据再把同一目录当成功运行。
- 源字段、代码、日期、正有限价格、唯一 JSON 键及每指数完整交易日集合均校验；缺失/额外日期、格式变更、业务失败或网络失败均停止。不删除坏行、不前向填充。
- `receipt.json` 中保留 URL、原文件名、实际 `acquired_at`、SHA-256 和 `provider_available_at=null`。CSV `available_at` 仅使用实际获取时刻作为**保守可见性边界**，另列 `available_at_basis=local_acquisition_only`；绝不回填历史交易日 15:00/17:00。这与 [ADR 0009](../backtest/docs/adr/0009-historical-provider-availability-is-distinct-from-local-acquisition.md) 的时间区分一致。
- 获取退出 `0` / `status=captured` 只表示输入结构/范围检查通过；`history_sufficient=true` 只说明交易日数量足够，**不表示历史可用性合格或牛熊判断成功**。非法输入或获取失败退出 `2`。

先跑小样本，确认后才扩大；以下输出目录需选用新的名称：

```bash
.venv/bin/python -m experiments.capture_a_share_market_regime \
  --start 2026-09-13 --output research/evidence/regime-new-smoke

.venv/bin/python -m experiments.capture_a_share_market_regime \
  --start 2025-11-01 --output research/evidence/regime-new-full
```

以上起日对应本轮有限窗口，后续运行应按实际评估日期调整；它不是定时采集或多日观测合并器。

### 已执行的真实来源检查

本地保留目录（未入 Git）：`research/evidence/a-share-market-regime-20260921/`。

- `public-smoke-v1/`：三指数各 2 个交易日；哈希验证通过，原策略正确返回历史不足 `unknown`，两次回放字节一致。
- `public-full-v1/`：**失败证据，未当作成功数据使用**。当 `startDate=20251101`（周六）时，官网多返回一条周六记录，内容与 11 月 3 日相同。严格覆盖检查拒绝它，未生成 CSV。修复为请求日历中的首个/最后一个实际交易日，仍拒绝任何额外日期，而不是删除该行。
- `public-smoke-v2/`：从周日 9 月 13 日开始，实际指数请求 9 月 14–18 日；三指数各 5 日，日历含周末。修复后小样本通过才重新扩大。
- `public-full-v2/`：获取时间 **2026-09-21 10:26:48–10:26:51 +08:00**。日历覆盖 **2025-11-01 至 2026-09-21，共 325 个自然日**；指数覆盖 **2025-11-03 至 2026-09-18，各 217 个交易日，共 651 条收盘记录**。所有原文及 CSV 哈希核验通过；从原文重新解析得到的日期/数值/实际获取时刻与 CSV 一致，两次小样本共 21 条重叠价格与完整窗口一致。

完整快照的 `public-full-v2/receipt.json`、`public-full-v2/regime-as-of.json` 与 `public-full-v2/verification.json` 均保存在上述本地目录，未随 Git 发布。原策略真实执行结果：

- `as_of=2026-09-21T10:26:51.126256+08:00`，`decision_date=2026-09-18`。
- **phase=unknown / 无法判断，退出码 1**；原因是 `close_not_available`，不是价格历史长度不足。
- 三个确认日为 9 月 16、17、18 日，均早于本次首次获取。不能把今天取得的历史数据说成当时已经观测到；两次原时点回放的输出字节完全一致。

可不联网复核该次诊断（退出 `1` 是已知的证据不足结果）：

```bash
.venv/bin/python -m experiments.run_a_share_market_regime \
  --prices research/evidence/a-share-market-regime-20260921/public-full-v2/prices.csv \
  --calendar research/evidence/a-share-market-regime-20260921/public-full-v2/calendar.csv \
  --as-of '2026-09-21T10:26:51.126256+08:00'
```

### 尚未解决的时点证据

[Tushare `index_daily`](https://tushare.pro/document/2?doc_id=95) 官方列出的输出同样没有历史版本 `available_at`；[交易日历文档](https://tushare.pro/document/2?doc_id=26) 也不替代价格版本证据。此次官网响应未补足历史可用时间，因此**历史点时口径仍为 unknown**，不能把该结果换成 bull/bear。上方新增的显式 snapshot 口径回答的是另一个问题：按当前已知版本重算，最近收盘形态是什么；其 bear 结果不是历史确认缺口已修复的证明。

后续需取得对应历史可用性依据，或在未来确认日实际获取并保留点时版本。后者还需要核验跨快照相同/修订记录并保留真实早期观测时间；当前入口每次独立获取，**不会自动合并历史观测**，也不能靠重复下载与复制今天的时间戳补齐过去。本轮没有启动定时任务、跨日等待、交易或部署。

## CSV 与运行

`prices.csv` 必需列（可有其他不重名列）：

```csv
ts_code,trade_date,close,available_at
000300.SH,20250106,1000.0,2025-01-06T15:01:00+08:00
000905.SH,20250106,2000.0,2025-01-06T15:01:00+08:00
000852.SH,20250106,3000.0,2025-01-06T15:01:00+08:00
```

以上只是**虚构的字段格式示例**，不是该日真实行情；必须提供足够完整的历史。`trade_date` / `cal_date` 支持 `YYYYMMDD` 或 `YYYY-MM-DD`。价格指数不应替换为 ETF 价格或混用不一致的复权序列。

`calendar.csv` 必需列：

```csv
cal_date,is_open
20250104,0
20250105,0
20250106,1
```

输入顺序不影响判断；日历日期不得重复，`is_open` 只接受 `0` 或 `1`。编码为 UTF-8，可带 BOM。

在仓库根目录运行（时点只是示例，不代表今天）：

```bash
.venv/bin/python -m experiments.run_a_share_market_regime \
  --prices /path/to/prices.csv \
  --calendar /path/to/calendar.csv \
  --as-of '2025-06-30T16:00:00+08:00'
```

要判断目前阶段，应先准备覆盖**真实评估时点**的完整快照，再显式传入该时点，或使用当前时间入口：

```bash
.venv/bin/python -m experiments.run_a_share_market_regime \
  --prices /path/to/prices.csv \
  --calendar /path/to/calendar.csv \
  --now
```

`--now` **只读取时钟，不下载、刷新或修补数据**，也不证明输入是真实、最新的行情。它依赖机器时钟正确；过期日历、收盘后缺失当天价格或数据尚未发布仍输出 unknown、退出 `1`，不会退回旧日并称作当前结论。盘中和休市日仍判断最近已收盘交易日，并通过 `decision_date` 明示。也可与已有 `--stocks`、`--sectors` 配对参数组合使用。

不要用旧 CSV 和旧 as-of 的结果称作当前市场判断，也不要将今日下载时间批量填成历史 `available_at`；这不能补足前两个确认日的可用性证据。保存 `result.as_of`，之后对同一快照使用 `--as-of '<该时刻>'`，可回放相同诊断（只有 `as_of_source` 不同）。默认输出到 stdout，不写入或覆盖既有研究报告。

输出 JSON 包括：策略版本、参数、两份输入文件的路径及 SHA-256、`as_of_source`（`explicit` 或 `system_clock`，只标识时刻来源，不是数据新鲜度认证）、中文阶段标签，以及 `result` 下的 as-of、目标交易日、最终/候选阶段、最新各指数的收盘/均线/动量/可用时间、3 日确认序列和原因。Decimal 指标使用字符串输出，动量 `"0.05"` 代表 5%，不是 0.05%。unknown 时 `decision_date` 若存在是应检查的交易日，不证明该日数据已齐全；最新可计算的部分指数指标不构成有效市场结论。

退出码：

- `0`：成功识别 bull / bear / transition，输出 JSON。
- `1`：证据不足，输出 unknown JSON 和具体原因，不应当作成功判断。
- `2`：输入、文件或参数错误，stderr 报错，不输出成功 JSON。

## 指定板块的高波动股票观察名单

纯算法：`experiments/a_share_sector_opportunities.py`，API 为 `evaluate_sector_opportunities()`。它内部调用相同的牛熊判断，股票与市场使用**同一个 as-of 和交易日历**，不接受手工填写的 bull/bear 开关。没有接入依赖事后收益样本的旧 `opportunity_engine.py`，也没有运行旧板块实验或复用其事后标签。

### 固定筛选规则 v1

1. `--sectors` 必须明确指定一个或多个板块名称，精确匹配输入的 `sector`；不自动选“热门板块”。使用统一分类口径，每股每个交易日一个主板块；不自动映射重叠概念。
2. 对每只范围内的股票，要求最近 **60 个交易日**的连续有效记录。最新交易日缺失、窗口内缺日/未发布、停牌或零成交额，不前向填充、不把 20 个有效观测当成 20 个交易日。历史不足的新股也不能入选。
3. 剔除当前 ST、停牌股票。以下指标只由截止时点已可用的收盘记录计算：

| 条件 | 默认定义 |
| --- | --- |
| 高波动且不过度极端 | 最近 20 个日简单涨跌幅的**样本标准差**（分母 19）× √252，落在 `[0.30, 0.80]`，即年化 30%–80%，两端包含 |
| 流动性 | 最近 20 日平均成交额 ≥ 100,000,000 **人民币元** |
| 上行趋势 | 当日复权收盘 > MA60，且 `close[t] / close[t-20] - 1 > 0` |
| 震荡期额外条件 | 当日复权收盘**严格大于此前 20 个交易日**的最高收盘；高点窗口不含当日 |

252 是固定年化约定，不是预测。高波动不是越高越好，80% 上限是这一版的保守风险筛选，而不是已证明最优的参数。这些阈值在读取真实个股行情前固定，未做收益调参。Python API 可显式传 `StockScreenConfig`，CLI 使用上述固定默认值。

| 市场阶段 | 个股满足条件后的处理 |
| --- | --- |
| bull | `watch`：上行趋势观察名单 |
| transition | 还须满足突破条件，才为 `watch`；否则 rejected |
| bear | `blocked`，不输出机会名单，不做空 |
| unknown | `unresolved`，不输出机会名单 |

其余不合格股票为 `rejected`，数据不足为 `unresolved`，均保留具体原因。有指标时输出复权收盘、均线、动量、年化波动率、日均成交额、此前高点及整个窗口最迟可用时间。观察名单按 20 日动量降序、同值按代码升序排列，**仅是查看顺序，不是预期收益、仓位或买入优先级**。

### 股票输入与命令

新增 `stocks.csv` 必需列如下；以下单行同样只是**虚构格式示例**，运行需至少 60 日完整记录：

```csv
ts_code,sector,trade_date,adj_close,amount_cny,is_st,is_suspended,available_at
000001.SZ,板块甲,20250106,100.0,200000000,0,0,2025-01-06T15:02:00+08:00
```

- `ts_code` 使用 A 股代码格式，排除指数、ETF、B 股格式；格式校验不是证券身份/上市状态权威核验。
- `adj_close` 必须是同一冻结版本、口径一致、在截止时点可知的复权信号价格，不得用今日后复权结果冒充历史可知信息，也不要用未处理除权的跳变制造“高波动”。它不是成交价格，不用于计算策略收益。
- `amount_cny` 必须先统一为**元**，程序不猜单位。例如若数据源明确使用千元，应由准备方乘 1000 后输入。
- `is_st`、`is_suspended` 必填且只接受 `0/1`；不得把未知状态填成 `0`。缺少真实收盘的停牌日可以缺行，程序会将受影响窗口判为 unresolved，而非填平价格。
- `sector`、状态、复权因子均须符合该记录交易日及评估时点的可知信息；`available_at` 是**整行所有字段均已可用**的时间，不能只用原始价格的发布时间遮蔽较晚的分类/状态修订。
- 采用最新可见行的板块；最新行迟到时不借用其板块、价格或 ST 状态。若某只股票在目标日期以前有记录、但整段都尚不可见，输出 `sector=null` 和 unresolved，不能推测其所属板块。仅有未来交易日记录的股票不会进入过去的筛选。
- 每股每日只接受一个冻结版本。**不得用今天的成分股名单回填历史股票池**。本工具不重建修订历史，也不能识别完全没有出现在输入中的成员；数据准备方需保留股票池及分类来源。

```bash
.venv/bin/python -m experiments.run_a_share_market_regime \
  --prices /path/to/prices.csv \
  --calendar /path/to/calendar.csv \
  --stocks /path/to/stocks.csv \
  --sectors '板块甲' '板块乙' \
  --as-of '2025-06-30T16:00:00+08:00'
```

板块名称需替换为你明确要关注、且在 CSV 中采用的名称。`--stocks` 与 `--sectors` 必须成对提供；不提供时，原市场阶段输出及默认行为保持不变。

输出新增 `sources.stocks` 字节指纹和 `screening`（版本 `a_share_sector_opportunities_v1`）：参数、选定板块、逐股理由、`watchlist`、`unresolved_sectors`、风险限制及 `complete`。`complete` **只说明已提供输入的可用性检查，不证明板块成员完整或投资有效**。指定板块没有任何可见成员时会明确 unresolved，不会把拼写错误当成“没有机会”。

- 股票证据不足或指定板块无法判断：`complete=false`、退出 `1`，可能仍有其他股票的**部分**观察名单；不可当作完整筛选。市场 unknown 时名单始终为空。
- 输入齐备但熊市门控、全部不合格等：正常退出 `0`，名单可以为空；空名单不等于程序故障。
- 股票文件/字段/参数非法：退出 `2`，不输出成功 JSON。

**高波动不等于可获利机会。** 未核验涨跌停可成交性、公告风险、T+1、交易成本或组合集中度；未生成订单、仓位、止损或正式 StrategyCandidate。本名单不授权交易，实际可执行性及样本外收益仍需独立验证。

## 验证与限制

最小 CLI 入口冒烟（使用 202 日 × 3 指数的合成输入；同时覆盖成功、缺失与非法输入，不使用真实行情）：

```bash
.venv/bin/python -m pytest -q tests/research/test_a_share_market_regime.py \
  -k 'cli_default_smoke_and_replay or cli_unknown_is_json_with_exit_one or cli_bad_input_is_exit_two_without_success_json'
```

显式当前时间入口冒烟（固定测试时钟及合成行情；真实时钟子进程只验证空日历失败，不代表当前行情）：

```bash
.venv/bin/python -m pytest -q tests/research/test_a_share_market_regime.py \
  -k 'now_smoke_and_explicit_replay or now_stale_calendar_is_unknown or now_bad_input_is_exit_two or now_real_clock_empty_calendar_fails_closed'
```

额外覆盖盘中/周末、15:00 缺失当日价格、尚未发布及迟到历史数据、时刻参数互斥、读取前只捕获一次时钟及原时点精确回放。

新增股票筛选的代表性冒烟（合成行情，经同一默认 CLI，验证成功/回放、数据不足、错误输入）：

```bash
.venv/bin/python -m pytest -q tests/research/test_a_share_sector_opportunities.py \
  -k 'cli_sector_smoke_and_replay or cli_sector_incomplete_is_exit_one or cli_bad_stock_input_is_exit_two'
```

完整针对性测试及已复用类型的回归：

```bash
.venv/bin/python -m pytest -q \
  tests/research/test_capture_a_share_market_regime.py \
  tests/research/test_a_share_market_regime.py \
  tests/research/test_a_share_sector_opportunities.py \
  tests/research/test_a_share_risk_state.py
```

`tests/research` 不在根 pytest 默认发现目录内，因此需要显式给出路径。测试覆盖方向/分歧/等号、默认暖机、确认中断、无未来数据、迟到数据、日历缺口、盘中/周末、失败退出码、JSON 指纹与确定性回放。新增筛选测试覆盖板块范围、波动率定义及上下限、流动性、趋势/突破、ST/停牌、迟到的板块/状态、未来上市记录、缺失与排序。它们证明实现遵循规则，**不证明金融预测能力**。

上轮获取器阶段相关回归为 192 项。本轮增加 19 个快照口径测试实例，同一相关测试集合为 **211 passed in 1.34s**。新增测试覆盖牛/熊/分歧、周一盘中重算上周五、未取得版本、未来价格、顺序/时区/Decimal上下文、缺失/日历缺口/暖机、三日形态等待、非法口径、CLI 回放和隔离股票门控。原获取器的 42 项边界测试仍在集合内。

代表性新入口冒烟为 `-k 'cli_snapshot_smoke or cli_snapshot_failure_paths or cli_snapshot_cannot_feed_stock_gate'`：**5 passed, 85 deselected**。核心算法和 CLI 主动 LSP 均确认 clean；测试文件 LSP 无诊断但 inconclusive，不计为通过。独立 `ruff` 仍不可用，全仓库测试未运行。

已复用真实三指数快照，取得明确限定口径的 **当前快照重算 bear**，并保留原历史点时 **unknown** 的字节兼容回放。两者不混用：前者不是历史当时已确认的信号，也不说明未来收益或交易获利能力。没有生成真实个股机会名单；收益回测、样本外和实盘验证未运行。正式投资价值验证仍需要现有公开 Research / Backtest / Validation 流程及适用 A 股准备能力，不能用此诊断 JSON 或旧探索性收益替代。
