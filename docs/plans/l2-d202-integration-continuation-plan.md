# L2 / D202 行情对接接续计划

日期：2026-09-11。阶段：**PLAN**。计划可交付；**真实在线执行仍被外部门禁阻塞，正式验收未执行**。

## 1. 目标与范围

沿同一工作树接续已有 Platform `capture → archive → read/replay` 链路，补齐契约、许可与运行时证据后，才进入原已授权的 SH603790 有界在线验收。不是重新开发行情框架，也不是策略实验或交易部署。

本阶段只新增本计划，不改代码、不执行采集。后续操作以[入口文档](../intraday-market-data.md)、[领域约束](../../CONTEXT.md)及[时间语义 ADR 0009](../../backtest/docs/adr/0009-historical-provider-availability-is-distinct-from-local-acquisition.md)为准；计划、`READY` 或 board 完成均不构成新增授权。

## 2. 已有证据与当前状态

权威材料：

- 交接：`/tmp/d202-handoff-8bfm0hvd.md`，仅作导航，不替代规格和源码。
- 主报告：`$HOME/.local/share/intra-md-client/evidence/d202-platform-capture-validation-20260911T070533Z.json`；SHA256：`2a23fa4ff5487850a492a58923de4f8039bda37213e73fbba1c64ec13e512797`。
- 保护基线：同目录 `d202-offline-worktree-baseline.json`；后续报告另存，不覆盖历史证据。

本次只读复核：主报告哈希、5 个接入工作文件、27 个受保护未跟踪文件，以及 HEAD/分支、索引差异、根目录差异、backtest HEAD/完整状态/差异均匹配报告及基线。根 HEAD 为 `e802d8907770d42943a1d32dfe33ae802d480d27`，分支 `main`。相对历史集合另有既存 `docs/plans/koruust-strategy-development-plan.md`，保留不动；不能称整个工作树没有额外变化。

历史工程结果（**本阶段未重跑**）：

- 聚焦测试 122 通过；按 Platform `.venv/bin/python`、传输 `/usr/bin/python3` 分别配置的 Pyright 无诊断。
- 全工作区 584 通过、2 失败；失败位于 `tests/architecture/test_integration_v5_design.py:153`、`tests/architecture/test_integration_v6_design.py:364`，是受保护 backtest HEAD `93d8a391…` 与预期 `f73d068d…` 的既有差异。不是全绿，不改版本钉或 backtest 来消除失败。
- 六份历史采集已通过公开 CLI 离线复验、重开逐字节读回；结果仍为 `limited`，不证明当前新鲜度或供应商语义。
- 旧报告的 worker 清理结果不证明当前服务就绪；供应商契约、当前许可、当前运行时尚未获新证据。

目前没有已证实的新增代码缺陷，默认不改代码，不为消耗阶段制造工程工作。

## 3. 复用边界与条件化改动位置

| 现有文件 / 符号 | 职责与不得破坏的约束 |
| --- | --- |
| [intraday_market_data.py](../../intraday_market_data.py)：`main`、`_run_cli`、`capture_d202` | 唯一公开采集入口；私有原文先落盘，再归档；超时/SIGINT kill + wait。不得改用旧 probe 或私有测试入口。 |
| [intraday_d202_transport.py](../../intraday_d202_transport.py)：`capture_record`、`_run` | 预装 websocket-client 的隔离子进程；固定 loopback `/d202`、一次订阅、退订并关闭。无自动重连、D201 回退或客户端启动。 |
| `intraday_market_data.py`：`archive_capture`、`read_capture`、`replay_capture`、`_project_item`、`_project_row`、`_sequence_flags`、`_receipt_flags` | Foundation 普通运维日志 `intraday.d202.captures.v1`；完整原文字节校验与重开读取。保留全 item/行、接收顺序和原字段；不猜方向、不跨连接去重、不修补缺口、不把接收时间冒充事件或供应商可用时间。 |
| [test_intraday_capture.py](../../tests/integration/test_intraday_capture.py)、[test_intraday_market_data.py](../../tests/integration/test_intraday_market_data.py) | 复用公开 CLI/API 和现有合成 loopback fixture；覆盖语义不确定性、持久化、安全限额、故障与进程清理。 |
| [docs/intraday-market-data.md](../intraday-market-data.md) | 后续仅在取得权威材料或确有行为修复后更新对应契约/操作说明，不复制第二份运行规范。 |

这些是后续定位点，不是本阶段修改清单。文件键 `symbol:sha256(全部原文字节)` 只提供文件级幂等，不是市场事件或连接身份。CLI 的 `supplier_contract_verified`、`qualified_market_data` 仍为 false；不通过删除 UNKNOWN 标记或翻转布尔值“完成接入”。

## 4. 真实执行前必须取得的材料

供应商材料须能定位发布方、适用 D202 版本、条款/章节及生效日期；记录出处与文件哈希。许可原文留在获授权私有位置，仓库仅保留安全引用。已有样本、猜测和合成 peer 均不能补齐契约。

| 门禁 | 需要供应商或获授权操作人给出的具体回答 / 证据 |
| --- | --- |
| G1 方向与事件类别 | `entrust`、`trade` 分别确认 `d` 的枚举语义（含 B/S、0/128）；明确买卖侧、主动方向是否不同，以及适用的撤单/中性/其他事件类别。 |
| G2 序号与历史/重连边界 | `seq` 身份及代码/流/交易日/连接作用域；是否单调、是否保证连续、何时重置、重复/更正的含义；`startSeq`、`rowCount` 语义。明确 count 50 / filter 0 的历史窗口、顺序和转入增量的边界；重连重发、回补能力及其 ID、范围、保留期、结束标记。若不支持须明确记为限制，不能宣称已补齐或擅自实现回补。 |
| G3 时间、盘口与完整性 | `t`、`l2Time`、代理 `ts` 的生产方、格式、单位、交易日期、时区及时间权威；区分 Event / Provider Availability / Acquisition / Assessment Time。明确价格/数量单位、全量或增量盘口、levels 与合计字段的范围、交付完整性及丢失/迟到/更正行为。 |
| G4 新鲜许可 | 当前验收窗口内 D202、SH603790、三类订阅与请求深度的有效权限、到期时间、频率限制、本地留存权，以及拒绝/到期的行为；旧到期记录不够。由获授权操作人提供，不读凭据、不续费或改账户。 |
| G5 当前运行条件 | 受信任已安装的 `.venv/bin/python`、`/usr/bin/python3` 与 websocket-client；已由获授权流程就绪的 `127.0.0.1:18087/d202`；合适交易时段、时区/时钟状态；当前用户独占的 0700 父目录、未存在的原文路径、私有小规模存储及可用空间。只读核查，缺客户端/服务就绪则由操作人处理，不自行启动或安装。 |

G1–G5 必须在实际执行前闭合；缺任一项，停止其依赖的真实采集，列明缺失条款/材料。明确的“不支持”只消除信息未知，不自动满足完整行情验收要求。若契约揭示需新增接口、归一化语义或放宽标准，先提交范围与接口决策，不由实现者猜定。

## 5. 接续顺序与退出条件

1. **保持基线。** 继续同一目录、单写入者；修改前复核主报告哈希和保护集合。额外变更保留并说明，不 reset、清理或覆盖。此步骤本阶段已做，后续执行前再核对可变状态。
2. **闭合证据门禁。** 只检查已获授权读取的可靠材料，向供应商/操作人索取第 4 节缺项。当前停在这里；若没有独立且必要的本地修复，直接交付阻塞清单，不开新工程主线。
3. **条件化本地修复。** 仅当出现可复现、原范围内的实际缺陷时，在现有公开 seam 先加最小失败回归，再修共同根因，按第 6 节验证。纯本地缺陷不必等待无关外部门禁，但本 PLAN 阶段不实施；涉及新语义/范围的部分等待明确决策。
4. **有界真实 smoke。** 仅 G1–G5 均有有效证据且既有授权范围不变时，使用入口文档的公共 `capture` 命令采 SH603790 **5 秒**：levels 10、port 18087、既有两个解释器、max-frames 5000、max-bytes 8 MiB。不得以“技术测试”绕过前置条件。使用新的私有存储/唯一原文文件，不复用治理存储。
5. **核对后才扩大。** 检查三类流都有代码匹配且字段有效的投影、无 `missing_types` / 降级 / 截断；保留原文与哈希，经 Foundation 重开逐字节核对，按契约逐项核查实际语义与历史边界，并检查退订、连接关闭及 worker 回收。smoke 未通过即止。通过且门禁仍有效后，才进行一次同范围、同路径/配置的 **不超过 30 秒**窗口；每次使用独占新原文文件。不得自动重试、重连、扩大标的/深度、注入真实故障或退回旧 probe。
6. **报告而非自动准入。** 分别报告工程检查、契约核对、有界在线观测结果与剩余限制；新增私有报告保留源码哈希、门禁来源、实际参数、带时区评估时刻、原文哈希/读回结果、安全质量码、退出码和清理证据，不贴原文。只有逐项证据满足原验收标准才可提交正式验收结论；`limited` / exit 0 本身不是通过，不自动宣布父任务获验收。

停止规则：许可不足、服务未就绪、代码/字段不符、坏报文、缺流、断连、时钟/序号异常、容量/发布/进程故障均不扩大运行。保留原文及安全故障证据，不删样本、不篡改修复、不绕过权限。完整性失败停止使用该存储；发布故障解决后才按入口文档以同字节/symbol 重试归档。

`capture` 结束时使用显式 UTC assessment 和 30 秒接收年龄阈值；最长窗口的早期消息可能陈旧，应缩短窗口而非刷新时间或放宽阈值求通过。接收年龄小、心跳新或没有跳号都不能证明事件实时、连续或完整。

## 6. 最小验证路径

**本 PLAN 阶段：** 仅检查计划中的链接、文件/符号/测试名、门禁与命令边界，复核源码/报告/保护状态和本次写入集合；运行会话级 `lens_diagnostics(mode=all)`，不启动全仓扫描。无源码变化，不重跑长回归；历史报告的扫描缓存/解释器及安全告警局限继续保留，不称历史已清理。

**后续确有代码修复时：** 先用对应解释器做定向 LSP 检查，再执行已安装工具；全部测试限定在独立网络命名空间，不连接宿主机真实 D202，不安装依赖。

```bash
unshare -Urn pyright --pythonpath .venv/bin/python \
  intraday_market_data.py tests/integration/test_intraday_market_data.py \
  tests/integration/test_intraday_capture.py
unshare -Urn pyright --pythonpath /usr/bin/python3 intraday_d202_transport.py

# 先小样本：公开归档/回放、文本/二进制采集、权限失败、发布失败留存与重试。
unshare -Urn sh -c 'ip link set lo up && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q tests/integration/test_intraday_market_data.py::test_cli_archive_reopen_replay_is_private_and_never_qualified tests/integration/test_intraday_capture.py::test_capture_cli_retains_raw_then_reopens_and_replays_through_platform tests/integration/test_intraday_capture.py::test_capture_archives_permission_failure_without_echoing_server_text tests/integration/test_intraday_capture.py::test_capture_keeps_raw_and_previous_archive_on_publication_failure'

# 小样本通过后，仍使用同路径、解释器与隔离配置跑两份聚焦测试。
unshare -Urn sh -c 'ip link set lo up && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q tests/integration/test_intraday_market_data.py tests/integration/test_intraday_capture.py'
```

实际修复还须先通过其新增失败回归。仅变更影响要求更广回归时，按入口文档执行全工作区测试；将上述 2 个既有失败与新增失败分列，不把既有失败改写为通过。历史兼容行为确有变化才复用既有六份私有样本：先单份 5 秒历史样本、再其余五份，保持“最后接收 + 1 秒”、60 秒阈值及重开逐字节校验，不当作当前新鲜样本。

## 7. 完成判据与非目标

- **本阶段完成：** 本计划保存并通过静态核验；唯一新增仓库文件为本计划；受保护状态未被本阶段修改；board 只关闭 PLAN 阶段。
- **接续工程完成：** 若有必要修复，其定向回归通过，无新增阻塞诊断/失败，原文安全、幂等、时间未知和清理边界不退化；既有失败、扫描局限仍单独报告。
- **在线验收：** 当前未执行且阻塞。须有 G1–G5 证据、同公共路径的 smoke 和后续有界观测及逐项契约核对；不能以工程通过、旧历史回放或合成 peer 代替。获得契约不自动使当前诊断投影成为合格领域行情。
- **不做：** htask/任务库恢复、代理或 workflow、新 worktree、依赖安装/同步、凭据读取/账户变更、客户端/服务启动、交易/Shadow/Live、暂存/提交/推送、受保护 backtest/版本钉/测试变更。主报告 `not_performed` 不是授权清单。
- **不扩展：** 自动重连/回补、跨连接去重、持续采集/轮转、D201 回退；不创建 `ArtifactEnvelope`、`ArtifactRef`、`MarketBundle`、`MarketEvent` 或 Research/Validation/Promotion 证据。若要合格行情或下游消费接口，需另行明确范围和治理契约。

后续工程报告兼容末行（仅文本，不创建任务）：

```text
HERDR_TASK_OFFLINE_REPORT_01M2781ZYA6BV3RZVDPM3C5ZG1
```
