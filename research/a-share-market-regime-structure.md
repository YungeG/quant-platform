# A 股牛熊判断：当前程序结构

![当前程序结构（校核版）](diagrams/a-share-market-regime-structure.png)

[打开 PNG](diagrams/a-share-market-regime-structure.png) · [可编辑 SVG](diagrams/a-share-market-regime-structure.svg) · [终端文本图](diagrams/a-share-market-regime-structure.tui.txt)

> 范围说明（2026-09-22）：图示只覆盖现有市场诊断 CLI 链路。另有[独立板块轮次纯函数](a-share-sector-rounds.md)，未接入该 CLI，不能把图中没有该模块理解为它不存在。文中的“本轮”指原制图阶段；本次仅核对并归档说明与既有图示，不重跑行情或收益研究。

这是一张现有程序的数据流图，不是未来架构或投资收益证明。连线表示数据处理关系，可选路径用虚线；归档是终点，评估 CLI 只读取 CSV。策略计算不联网；联网只发生在独立快照获取步骤。下方 Mermaid 为可编辑的逻辑图源。

```mermaid
flowchart TB
  subgraph SOURCES["1 数据来源"]
    CSI["中证指数官网 JSON<br/>沪深300 · 中证500 · 中证1000<br/>000300.SH / 000905.SH / 000852.SH"]
    SSE["上交所年度休市安排 HTML<br/>固定 2025 / 2026 来源<br/>包含周末与节假日"]
  end

  subgraph CAPTURE["2 联网获取与冻结"]
    GET["capture_a_share_market_regime.py<br/>固定 HTTPS / 禁止重定向 / 有限范围"]
    CHECK["解析与源校验<br/>字段、代码、价格、唯一性<br/>三指数与已收盘交易日精确覆盖"]
    RAW["原始 JSON / HTML + receipt.json<br/>URL · SHA-256 · 实际 acquired_at<br/>历史 provider availability 未证实"]
    CSV["冻结输入<br/>prices.csv + calendar.csv<br/>采集器 available_at = 实际获取时刻<br/>不回填历史发布时间"]
    BAD_CAPTURE["采集或源校验失败<br/>停止；目录已创建时保留失败回执<br/>不输出成功获取结果"]
    GET --> CHECK
    GET -. "原文与回执" .-> RAW
    CHECK -->|通过| CSV
    CHECK -->|不合格| BAD_CAPTURE
  end
  CSI --> GET
  SSE --> GET

  subgraph OFFLINE["3 离线读取与判断"]
    CLI["run_a_share_market_regime.py<br/>--prices / --calendar<br/>--as-of 或 --now（只取一次时钟）"]
    VALID["输入和时点检查<br/>完整日历 · 最近已收盘日<br/>每指数至少202个交易日 · 不填缺失"]
    HIST["historical（默认）<br/>每个回看窗口只用该日结束前已知数据<br/>同时不晚于评估 as-of"]
    SNAP["snapshot（显式）<br/>统一使用评估 as-of 前已知版本重算<br/>不证明历史当时已确认"]
    SIGNAL["a_share_market_regime.py 共用纯算法<br/>MA200；动量 = close[t] / close[t-60] - 1<br/>收盘高于MA且动量正：bull<br/>收盘低于MA且动量负：bear<br/>其余：transition"]
    VOTE["方向投票<br/>至少2个指数同为 bull 或 bear<br/>否则 transition；不能缩小指数集合"]
    PATTERN["最近3个交易日形态<br/>连续同向 → bull / bear<br/>分歧或等待 → transition"]
    UNKNOWN["日历 / 历史 / 价格 / 可见性不足<br/>unknown，退出1"]
    INVALID["输入、文件或参数非法<br/>stderr 报错，退出2"]
    CLI --> VALID
    CLI -->|输入非法| INVALID
    VALID --> HIST
    VALID --> SNAP
    HIST -->|满足窗口可见性| SIGNAL
    SNAP -->|满足评估时点可见性| SIGNAL
    VALID -->|数据不足| UNKNOWN
    HIST -->|数据未可用| UNKNOWN
    SNAP -->|数据未可用| UNKNOWN
    SIGNAL --> VOTE --> PATTERN
  end
  CSV --> CLI

  subgraph OUTPUTS["4 输出与边界"]
    OUT["解释性 JSON<br/>bull / bear / transition 正常退出0<br/>as_of · decision_date · 指标 · 三日序列 · 原因<br/>输入路径与 SHA-256"]
    FLAGS["diagnostic_only / trade_authorized=false<br/>snapshot 另标 historical_confirmation_claimed=false<br/>不是盘中预测；不生成仓位或订单"]
    STOCKS["可选：外部准备 stocks.csv + --sectors<br/>a_share_sector_opportunities.py<br/>内部仅用 historical 市场门控<br/>输出观察名单/逐股原因；snapshot 禁止接入"]
    NOT_CONNECTED["当前未接入：正式 A 股收益回测 / OOS / 实盘<br/>已有回测框架不是本诊断主链的已调用模块"]
    OUT --> FLAGS
    UNKNOWN -->|带原因的 JSON| FLAGS
  end
  PATTERN --> OUT
  CLI -. "仅历史口径、成对提供股票参数" .-> STOCKS
  STOCKS -. "市场判断复用同一纯算法；结果附于 JSON" .-> FLAGS
```

## 代码对应关系

| 层 | 当前文件 / 关键入口 | 职责 |
| --- | --- | --- |
| 来源与冻结 | `experiments/capture_a_share_market_regime.py`：`capture_snapshot`、`parse_calendar`、`parse_index` | 官网请求、严格解析、原文/回执留存、CSV 输出；不授予历史可用时间权威 |
| 命令入口 | `experiments/run_a_share_market_regime.py`：`main` | CSV/参数读取、固定评估时点、选择口径、JSON 与退出码；不下载数据 |
| 纯判断 | `experiments/a_share_market_regime.py`：`evaluate_market_regime` | 日历/可用性检查、MA200、60日动量、三指数多数和三日形态；不读时钟/文件/网络 |
| 可选股票观察 | `experiments/a_share_sector_opportunities.py`：`evaluate_sector_opportunities` | 复用默认 historical 判断，按板块、波动率、流动性、趋势等条件筛选输入股票池；不是订单 |

## 两个容易混淆的边界

1. **完整价格不等于历史点时证据**：采集器用实际获取时刻作保守可见性边界。historical 不能把今天取得的数据倒推成过去已知；snapshot 只描述当前已知版本下的历史价格形态。
2. **诊断不等于回测/交易**：本链路不调用正式 A 股收益回测、OOS 或实盘执行，也不以旧探索性结果冒充验证。`--stocks/--sectors` 仅是可选观察名单路径，不能与 snapshot 合用。

`--now` 不刷新行情。盘中/休市日使用最近已收盘交易日；收盘后缺当天价格或日历过期时失败关闭。图中的截止时间判断均使用中国时区。

详细规则、真实快照结果与使用命令见 [A 股牛熊阶段识别](a-share-market-regime.md)。本轮仅制作结构图，未修改策略代码，未重跑策略测试、行情获取或收益回测。
