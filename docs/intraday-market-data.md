# D202 盘中行情：Platform 有界采集与离线回放

## 当前边界

`intraday_market_data.py` 是本工作区的接入入口：`capture` 执行一次显式请求的有界 loopback 订阅；`archive/replay` 离线归档、重开读取，并按原接收顺序生成带质量标记的诊断投影。

- 采集使用仓库自有 `intraday_d202_transport.py` 子进程和预装的 websocket-client，不调用私有 probe。**没有**自动重连、缺口修复、后台服务或交易能力；工程入口存在不等于在线验收通过。
- 原始字节通过 `LocalFoundation.append/entries` 存取。`intraday.d202.captures.v1` 是普通运维日志，**不是**指定的 artifact owner log；不改动冻结的 owner-log 表。
- 不创建 `ArtifactEnvelope`、`ArtifactRef`、`MarketBundle` 或 `MarketEvent`，不发布 Research、Validation、Promotion 证据。兼容保留的目录标记 `.d202-offline-store` 仅用于避免 CLI 误用其他存储，不是证据、离线性保证或供应商认证。
- 供应商序号、方向、历史边界、完整性、时间与授权契约仍未核实。CLI 永远输出 `supplier_contract_verified: false`、`qualified_market_data: false`（失败时只输出安全错误码）。**离线通过不等于父任务验收、策略准入或 Live 授权。**

领域边界见 [CONTEXT.md](../CONTEXT.md)；时间语义见 [ADR 0009](../backtest/docs/adr/0009-historical-provider-availability-is-distinct-from-local-acquisition.md)。

## 离线运行方式

在仓库根目录使用**已经安装好的** `.venv`。以下 Linux 离线命令用独立网络命名空间阻断网络，不执行下载或依赖同步。

```bash
# SOURCE 必须是已有的、已结束的 D202 采集，不是账号/配置文件。
SOURCE=/absolute/private/existing-capture.jsonl
# 父目录应为受信任的私有目录；首次运行时 STORE 本身尚不存在。
STORE=/absolute/private/d202-offline-store

unshare -Urn env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m intraday_market_data archive \
  --store "$STORE" --source "$SOURCE" --symbol SH603790

# 使用 archive 返回的文件键。评估时刻必须显式提供且带时区。
unshare -Urn env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m intraday_market_data replay \
  --store "$STORE" --capture-key 'SH603790:<64位原始文件SHA256>' \
  --assessed-at '2026-09-11T02:00:00Z' --max-age-seconds 30
```

时间只是示例，不能把示例评估时刻当作现在。历史回放可明确使用最后接收时刻之后的评估点；这只能评估当时的**接收年龄**，不能证明当前新鲜度、源端延迟或供应商可用时间。

## 有界采集入口

**以下是操作示例，不是本阶段已执行的真实采集。** 当前只有隔离网络内合成 peer 的验证；供应商方向、序号身份、重连/回补契约尚不足以通过正式验收。真实执行必须先补齐这些契约，重新核查许可与运行时状态，再在已授权的 SH603790 范围内先做 5 秒 smoke；通过后最多 30 秒。旧许可到期时间不能充当新授权证明。

```bash
# 仅在上述前置门禁满足后使用；父目录必须已存在、当前用户拥有且为 0700。
STORE=/absolute/private/d202-capture-store
RAW=/absolute/private/new-unique-capture.jsonl
.venv/bin/python -m intraday_market_data capture \
  --store "$STORE" --raw-path "$RAW" --symbol SH603790 \
  --seconds 5 --levels 10 --port 18087 --transport-python /usr/bin/python3
```

- 固定连接 `ws://127.0.0.1:<port>/d202`，不接收外部主机 URL，不回退到 D201。代理必须已由获授权的流程就绪；本入口不启动客户端/服务，不登录、续费或读凭据。
- 一次发送 `thousand`（指定 levels）、`entrust`（count 50、filter 0）、`trade`（count 50）订阅。前 50 条不据此视为新事件。结束时尝试取消全部订阅并关闭连接，无自动重连。
- Platform 使用现有 `.venv`；Linux 传输子进程默认用已安装 websocket-client 1.8.0 的 `/usr/bin/python3`。可指定其他**受信任、绝对路径、已安装依赖**的解释器。不会安装/同步依赖；缺运行时或库会保留安全错误记录并降级。
- 子进程使用 `-I -B`，只继承私有原文文件描述符，环境仅有固定 PATH/LANG；stdin/stdout/stderr 不作为数据通道，不继承凭据或代理环境配置。
- `--seconds` 默认 5，范围 `(0, 30]`；`--levels` 为 1–1000；`--port` 为 1–65535。订阅后的接收窗口与进程上限不同：父进程等待最多 **seconds + 8 秒**，覆盖连接、接收和关闭；超时或 SIGINT 会 kill 并 wait 子进程，再尝试保留诊断、归档。归档扫描时间不包含在这个子进程时限中；不承诺 SIGKILL、掉电或重复强制中断后的清理。
- `--max-frames` 默认/上限 5000，计数包含控制帧和库交付的完整数据消息；`--max-bytes` 默认/上限 8 MiB，限制接受的数据消息 payload 总量。均可设更小正整数用于 smoke。触发上限时只保留已接受前缀和资源错误，**不会把截断结果判为成功**。
- 库负责 WebSocket 分片重组、ping/pong；原文是接受的完整消息 payload（base64）及接收/控制元数据，**不是 TCP 抓包或逐 WebSocket 分片镜像**。超限/未收全消息不进入市场投影。Linux 子进程地址空间上限 256 MiB、文件大小上限 16 MiB；记录器预留尾部空间，最多写 15 MiB。
- 原文先落独占新建的 `0600` 文件，子进程结束后才通过 Foundation 发布并逐字节读回确认。归档失败不删除原文、不覆盖旧归档；可在故障解决后用 `archive --source "$RAW"` 重试。若原文写入失败留下不完整 JSONL，则归档失败封闭，不能自动截断“修好”。
- `capture` 在结束时记录明确的 UTC assessment，以 30 秒阈值回放。因此 30 秒采集中最早的消息可能已陈旧，不能为通过而刷新接收时刻。还要求三类流各有至少一个代码匹配、字段有效的投影；`missing_types` 非空即降级。这仍不是流完整性或实时性证明。

## 文件安全

- 归档源必须是当前用户拥有的 `0600` 普通文件；拒绝符号链接、FIFO、设备以及含 `..` 的路径。读取有大小上限，并检查读取期间的大小/修改时间变化。
- 采集原文目标必须不存在，父目录必须为当前用户拥有的 `0700` 目录；拒绝链接和 `..`，绝不覆盖已有文件或自动修改其权限。
- CLI 新建 `0700` 专用存储；目录、文件分别要求 `0700`、`0600`。使用 `umask 077`，不自动放宽或修复已有权限。
- 不接管已有未标记目录；不把 Research/Validation/Promotion 的 Foundation 根目录传给 CLI。拒绝检测到的目录树符号链接和异常文件类型。
- 使用受信任的本地文件系统和父目录；不允许其他进程同时修改源或存储。这不是针对恶意同用户进程的文件系统沙箱。
- 原始数据可能包含许可行情或供应商消息。不要提交到 Git，不要打印原文或把未知 `info/error` 内容贴进日志。CLI 只输出键、计数、状态和静态质量码。

### 返回值

| 操作/状态 | 退出码 | 含义 |
| --- | ---: | --- |
| `archive` / `archived` | 0 | 原始采集已发布到运维日志；仍须回放，内层坏消息也可能被保留 |
| `replay/capture` / `limited` | 0 | 完成诊断，只有声明的局限；**不是健康/合格行情** |
| `replay/capture` / `degraded` | 1 | 畸形、陈旧、断连、权限、序号、资源/进程等质量问题；采集还检查缺失流 |
| `failed` | 2 | 参数、路径、格式、容量或 Foundation 失败；只返回安全错误码 |

`quality_flags` 的值是受影响的**投影数量**，不是丢失事件数量、源端错误次数或交易笔数。`valid_market_observations` 和按流统计的 `valid_market_kinds` 仅排除字段畸形和代码不匹配的行/快照，不表示时间、方向、历史或完整性已获认证。`offline` 在 `capture` 为 false，在 `archive/replay` 为 true；不是授权标志。

## 原始持久化与读取

一个采集文件作为一个 payload 原子追加，文件键为：

```text
<symbol>:<sha256(原始文件全部字节)>
```

同 symbol、同字节重试幂等；不同字节（包括空白变化）、重叠历史、不同连接文件均不合并。这个键不是市场事件 ID，也不是被证明的连接 ID。

```python
from datetime import datetime, timezone
from crypto_quant_foundation import LocalFoundation
from intraday_market_data import archive_capture, read_capture, replay_capture

# 嵌入式调用者负责私有目录、权限、输入来源和独立存储边界。
foundation = LocalFoundation("/absolute/private/library-owned-store")
key = archive_capture(foundation, existing_capture_bytes, symbol="SH603790")
raw = read_capture(foundation, key)  # Foundation 完整性校验 + 原始 SHA256 校验
observations = replay_capture(
    foundation, key,
    assessed_at=datetime(2026, 9, 11, 2, tzinfo=timezone.utc),
    max_age_seconds=30,
)
```

`Observation` 是诊断投影，定位为原文件的 `record`（从 1 起）、`item`/`row`（从 0 起）。外层对象不可重赋值，`data` 字典仍可变，**不是不可变领域证据**；改动投影不会改动归档。精确重建、原始元数据或核查应读取 `raw`。

边界：每份采集最多 **16 MiB、10,000 条外层记录**；每个表最多 **10,000 行**；每次回放最多 **100,000 个投影**。不会截断后冒充完整成功；超限失败，已归档原文仍可读取。格式预检失败不会发布任何记录；`archive` 先预检源再创建存储。`capture` 可能先创建空的专用存储/标记，但无效采集参数不会创建原文或连接网络。

这是有界运维实现：Foundation 整表替换、读取扫描日志，不适合无界持续采集。需控制专用存储规模；不提供自动轮转/清理。原子发布和进程重开读取经过测试，**不声明掉电/fsync 级持久性保证**。

## 解析及质量规则

- 遍历每帧 `list` 中所有 item。支持 `thousand`、`entrust`、`trade`、`info`、`error`。
- 表格支持平铺数组和恰好一层 singleton 包装；拒绝更深或混合包装。坏 item 不遮蔽其他 item；可定位的坏行不遮蔽同表其他行。
- 保留原始整数，不把字符串、布尔值、负价格/数量/序号静默转成有效行情。供应资料中的价格“分”、数量“手”仅作为原始字段约定记录；这里不做金融单位换算。
- `totalBuyVol/totalSellVol` 等保留供应商原值，不用返回档位之和覆盖。限档盘口不因此被判为合计损坏；完整盘口范围仍未知。
- `rowCount` 不一致单独标记，不截掉多出的行；不从 `startSeq` 推导未提供的事件。
- `seq` 仅在本次回放的局部区段内，按代码和流类型记录 seen/high-water。重复数字、前跳、倒退分别产生 `REPEATED_SEQ`、`SEQUENCE_GAP`、`SEQUENCE_REGRESSION`。不丢行、不排序、不以指纹替代事件 ID。
- 订阅记录、断连、传输错误、握手拒绝及接收时钟倒退会切分诊断区段。重连后保持 `GAP_UNKNOWN`；**不证明补齐，也不跨文件去重**。第一次看到的序号不是缺口起点证据。
- 所有市场投影有 `PROVIDER_TIME_UNKNOWN`、`COMPLETENESS_UNKNOWN`；盘口还有 `DEPTH_SCOPE_UNKNOWN`，逐笔还有 `SEQUENCE_SCOPE_UNKNOWN`、`HISTORY_BOUNDARY_UNKNOWN`、`DIRECTION_UNKNOWN`。
- `d` 原值保留（例如 B/S、0/128），不推断买卖；`t` 只检查 HHmmss 形状，不补交易日期。`l2Time` 保持不透明，代理 `ts` 不充当供应商可用时间。

### 时间和失败

| 标记 | 解释 |
| --- | --- |
| `STALE_CAPTURE` | 原接收 wall ns 比显式 assessment 早超过阈值；默认 30 秒 |
| `RECEIVED_AFTER_ASSESSMENT` | 接收时刻晚于所给评估点，不伪造为已知数据 |
| `RECEIVE_CLOCK_MISMATCH` | ISO 接收时间与 wall ns 相差超过 1 秒；这是本地诊断容差 |
| `RECEIVE_CLOCK_REGRESSION` | wall 或 monotonic 时钟倒退；保留原顺序并标记区段不确定 |
| `MALFORMED_PAYLOAD` / `MALFORMED_DATA` | JSON/包装异常或字段异常；原文保留，非合格行情 |
| `SYMBOL_MISMATCH` / `ROW_COUNT_MISMATCH` | 返回代码或声明行数不符；不静默纠正 |
| `DISCONNECT` / `TRANSPORT_ERROR` / `GAP_UNKNOWN` | 显式断连或无法证明连续性 |
| `HANDSHAKE_REJECTED` / `PERMISSION_DENIED` | 握手失败；401/403 额外标记权限失败 |
| `PROVIDER_ERROR` | 供应商 error item；不猜测未文档化错误码/权限语义 |
| `UNSUPPORTED_TYPE` / `UNSUPPORTED_CONTROL` | 未支持的 item 或非 ping/pong 控制帧 |
| `EMPTY_FRAME` / `EMPTY_BATCH` | 没有可用行；其他有效 item 仍保留 |
| `NO_MARKET_DATA` | 整份采集没有匹配且字段可解析的市场行/快照 |

阈值必须有限、非负；评估时间必须带时区。较新的 info/心跳不会刷新旧市场投影。历史行可能刚刚被接收，因此接收年龄小仍**不证明事件是新的**。未记录的静默丢包、缺失尾段或未覆盖流，不能仅凭本文件判断；没有 `SEQUENCE_GAP` 不等于完整。

## 故障处理与重试

1. `CAPTURE_FORMAT`：检查采集元数据、编码、事件字段。不要把凭据文件当采集导入；不要修改已保留原文来“修好”回放。
2. `PRIVATE_SOURCE_REQUIRED` / `PRIVATE_STORE_REQUIRED` / `UNSAFE_PATH`：核实路径和所有权；不自动 chmod、不复用治理存储、不跟随链接。
3. `LOG_PUBLICATION_FAILED` / `FILE_IO_ERROR` 等：检查私有目录空间和权限。不要手工重写 registry 或删锁“恢复健康”。初始化失败可另选新的私有目录。
4. 明确解决故障后，使用**相同字节和 symbol**重试。即使发布已完成但调用者未收到输出，文件级幂等也不会增加重复记录。
5. 完整性校验失败时停止使用该存储并保留现场，不返回部分数据冒充成功。

## 验证与尚未通过的门禁

两份测试均使用明确标注的**合成**数据；仓库不包含新增许可采集或凭据：

- `tests/integration/test_intraday_market_data.py`：重开读回、幂等、扁平/包装表、全 item、空/坏数据、时钟/陈旧、方向未知、重复/跳号/区段切分、符号隔离、控制帧、容量、哈希/日志篡改、CLI 私有目录与无原文输出。
- `tests/integration/test_intraday_capture.py`：隔离 loopback peer 经真正的 Platform CLI/库入口、传输子进程和 websocket-client；覆盖 text/binary、分片/ping、401/403、缺失流、info/error/坏报文、早关闭、帧/字节上限、未完成巨长声明消息、无效参数/不安全路径、运行时失败、超时/SIGINT 清理。通过内核查询确认子进程资源上限，在 CLI 退出前检查子进程已回收，避免 init 回收孤儿进程掩盖缺陷。采集后 `os.replace` 注入 ENOSPC/EACCES，验证旧归档不变、原文仍在且可重试。

测试只启用**独立网络命名空间自身的 loopback**，不会连到宿主机 D202 或外网；未启动真实供应商客户端/服务。先跑聚焦测试，再跑工作区回归，不安装依赖：

```bash
unshare -Urn pyright --pythonpath .venv/bin/python \
  intraday_market_data.py tests/integration/test_intraday_market_data.py \
  tests/integration/test_intraday_capture.py
unshare -Urn pyright --pythonpath /usr/bin/python3 intraday_d202_transport.py
unshare -Urn sh -c 'ip link set lo up && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q tests/integration/test_intraday_market_data.py tests/integration/test_intraday_capture.py'
unshare -Urn sh -c 'ip link set lo up && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q'
```

已有 2026-09-11 六份采集可用于本入口的离线复验：先单份 5 秒历史采集 smoke，再用同样的 CLI、显式“最后接收 + 1 秒”、60 秒阈值扩大验证。原文仅存于私有目录；报告只含哈希、计数和质量状态。临时 Foundation 重开后逐字节读回，再清理本次临时存储。它不构成新的实时样本。

**正式验收仍未执行**：用户已授权有界在线验收，但授权不豁免供应商序号身份/作用域、方向、重连/回补等契约前置条件，也不能替代新鲜的许可核查。完整性、时区/源端时间、深度合计及授权生命周期仍需明确。不得用合成测试、离线 `limited`、旧 probe 或本文件替代门禁；不启动常驻服务，不推进交易或父任务验收。工程执行与私有验证报告不依赖 htask。
