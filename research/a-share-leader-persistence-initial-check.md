# A 股板块旧龙头持续性：初步检查

> 归档说明（2026-09-22）：本文保留原初筛时的数据路径、依赖枚举及文献访问记录，“当前/本次”均指当时，不代表本次重新核验。后续[依赖对齐](../implementation/dependency-alignment-20260921.md)已采用 Backtest `8cc5b874`，公开 CN preparation 已可导入；这不证明本多股票假设或样本已获接受。初筛草案后的候选口径见[分层路线图 v0.4](../overall/a-share-layered-opportunity-implementation-plan.md)，其中整轮主结果与 20 日辅助结果已区分；本归档不改写旧草案、不授予实验权限。

## 结论与研究状态

**保留为候选假设；证据不足，未证实，也未否定。** 本次只完成假设澄清、数据可用性与相关文献核查；没有运行历史排名统计、收益回测或样本外验证，没有新增策略代码，也未将该规则加入现有牛熊/板块筛选工具。

模式：A 股 / Plan 阶段的能力预检，不是完整、已冻结或可执行的 Experiment 计划。不生成 `StrategyCandidate` 或 `ValidationReport`，不授权交易。

用户原始思路：某板块上一轮表现最好的股票，在该板块下一轮活跃时，大概率仍是涨幅最高的股票。

## 1. 必须分别检验的命题

| 命题 | 要统计的量 | 不可偷换的边界 |
| --- | --- | --- |
| 强命题：旧冠军下一轮仍为冠军 | 前轮第1在下一独立轮次仍排名第1的比例 | 若“大概率”指超过一半，需单独检验是否超过50%；高于随机概率不等于大概率 |
| 弱命题：旧龙头仍有相对优势 | 下一轮排名分位、保持前10%的比例、相对板块平均的价格表现 | 即使成立，也不证明下轮仍第1 |
| 可交易命题：识别后还有优势 | 只观察下一轮信号已确认之后的表现，再另行处理成交和成本 | 启动当天已经涨完、买不到、开盘跳空均可能使交易价值消失 |

这里的“龙头”先严格按用户所说的**上轮区间涨幅冠军**定义，不替换为市值最大、成交额最高、最早涨停或主观认定的“核心股”。这些若要研究，应作为另外的假设，不能事后挑最有利定义。

可能的机制包括资金关注和交易习惯的持续性，但本次没有直接验证这些机制。旧龙头过度透支、题材换了核心受益者、新龙头出现、普通动量/高波动导致的重复排名，都可能使原命题失效或看似成立。

## 2. 本次实际核查

### 当前目录的数据缺口

只在 `/home/ygguo/agent-projs/ai-crypt/platform` 中检查既有研究入口及其依赖；未扫描或借用其他项目的数据。

以下路径的 `Path.is_file()` 均为 False：

- `overall/a-share-sw2021-members.csv`
- `overall/a-share-equity-etf-daily-current.csv`
- `overall/a-share-2026-sector-volume-panel.csv`
- `overall/a-share-volume-diffusion-panel.csv`
- `overall/a-share-2026-volume-diffusion-waves.csv`
- `overall/a-share-2026-volume-diffusion-wave-daily.csv`
- `quant_a50.duckdb`

这证明已检查的既有入口缺少可直接复验的依赖，不等于证明所有地方都没有相关数据。[已有数据清单](../overall/research-data-inventory.md)还提及其他项目的探索数据；本次没有核验或使用那些文件。

### 旧成果不能直接回答这个问题

- [板块启动研究定义](../overall/a-share-2026-sector-volume-launch-design.md)用随后35日的绝对/相对收益定义 `LAUNCH`，并明确标注为事后描述标签。它不能用来挑出“当时就能识别的成功启动”，否则漏掉失败信号。
- [成交量扩散波段程序](../experiments/reconstruct_2026_volume_diffusion_waves.py)的 `seed_leaders` 来自种子日 `focus_symbols`，是成交量关注集合，不是上轮涨幅第1名。[波段报告](../overall/a-share-2026-volume-diffusion-waves.md)因此不是旧冠军跨轮持续性的证据。
- [板块面板构建程序](../experiments/build_2026_sector_volume_panel.py)依赖历史行业成员、底层个股面板和基准行情。上述输入未齐，不能用现有报告摘要重建全体股票排名。
- 未运行这些旧脚本，未重新计算或采信其收益为本假设的验证结果。

### 正式 Platform 能力边界

实际导入当前 `.venv` 的公开 `crypto_quant_backtest` 根，枚举到的 `prepare_*_backtest` 只有：

1. `prepare_cash_development_backtest`
2. `prepare_cash_target_stream_backtest`
3. `prepare_model_bound_cash_development_backtest`

本地 `backtest` 子模块源码另有新增 A 股 preparation 导出，但工作区依赖仍固定到根 `pyproject.toml` 的版本，不能把源码目录的新符号当成已安装、已接受能力。参见 [roadmap 的 TSR-ASH-Q-01](../implementation/roadmap.md)。本次未确认可用于板块内多股票研究的已接受公开 preparation。

**缺正式 Backtest 接口与缺统计样本是两件事。** 本次不能算冠军持续率，直接原因是缺合适的历史成员、完整个股价格/状态和独立轮次样本；不能把平台交易接口限制误说成普通描述性统计在方法上不可能。

## 3. 相关外部证据，不是直接验证

已读取 NBER 原始摘要：[Gao、Jiang、Xiong、Xiong，Daily Momentum and New Investors in an Emerging Stock Market，Working Paper 31839（2023）](https://www.nber.org/papers/w31839)。摘要原文：

> “there’s a conspicuous absence of price momentum in weekly and monthly returns”
>
> “This study uncovers the presence of price momentum in daily returns”

该研究把其样本中的日频动量与新投资者注意力/交易活动联系起来。这提示强弱延续依赖持有周期，但**没有检验“同一板块冷却后再活跃时，原涨幅冠军仍第一”**。它既不能证实，也不能直接否定用户这个有条件的跨轮命题；本次只核验摘要，未复现论文数据。

另搜索到行业动量相关研究，但不把搜索摘要当直接支持：

- [Industry momentum and trading volume: evidence from China](https://doi.org/10.1108/MF-08-2022-0397)：DOI读取只返回书目信息，未核验正文。
- [Industry herding and momentum strategies](https://www.sciencedirect.com/science/article/abs/pii/S0927538X15000335)：出版商页面 HTTP 403，未读取正文。

行业持续强势、个股短期动量、跨轮龙头持续性是三个不同问题，不互相替代。

## 4. 最小检验草案：先测排名，不拼完整交易策略

在读取新行情前需要冻结以下口径：

1. **板块与轮次**：使用一个统一的历史板块分类；以当时已知的板块相对强度与成交活跃条件识别新一轮，先约定冷却间隔和非重叠规则。不按随后是否大涨决定该轮是否入样；不能把同一轮连续上涨切成两个独立事件。
2. **上轮冠军**：在上轮已结束且结果可知时确定，冻结证券身份；随后不能因旧冠军退市、停牌、退出板块或表现不佳而删样。并列第1单独记录，不靠证券代码顺序制造经济上的唯一冠军。
3. **下轮观察**：建议先固定20个交易日窗口，不挑事后最高价，也不选择最有利持有天数。启动当天的表现与信号确认后至窗口结束的表现分列，后者才接近后续可交易性问题。
4. **主要统计**：旧冠军再次第1的事件数/完整可评估事件数，同时给分母、样本不完整数、区间和板块/时期分布。未走完观察窗口的轮次标未决，不当失败，也不当成功。
5. **对照**：每轮同板块随机选股的第1概率（唯一冠军时为 `1/N`）只是最低基线，还需和普通近期动量、相近波动/流动性股票比较；否则测到的可能只是一般强势或高波动，而不是“龙头记忆”。
6. **反证**：若跨不同板块/时期没有稳定增量，或优势仅来自少数旧妖股、同一市场大波段、未来成员信息、当日不可参与的涨停，应暂不支持可用性；若只保持前列，则仅支持弱命题，不能宣布强命题通过。

小样本只检查定义、数据链与方向，不能由几轮行情宣布“大概率”。正式检验应处理同一板块和同一市场时期的相关性，并在开发样本之外留独立样本。

## 5. 未冻结项和下一安全步骤

尚缺：不可变数据版本、逐日历史板块成员及真实可用时间、个股复权信号口径/原始行情/成交额、上市退市与停牌状态、日历，以及未被旧研究消耗的留出样本。先按覆盖情况选样本，不按表现选样本；本次没有读取新的行情样本，也没有宣称保留了尚未核验的 holdout。

激活阈值、冷却长度、样本日期/板块范围、正式参数轴/seed/scenario/grade/预算/SelectionPolicy/ValidationPolicy 均未作权威冻结；因此这份记录**不是完整可执行计划**。不为补字段编造 dataset revision、公开准备接口或 Validation 指标支持。

下一步是取得一个历史板块的完整成员、个股日线和状态快照，先确认能无未来信息地切出两轮，再扩展到多个事先固定的板块和年份。先单独验证旧龙头的增量价值，之后才考虑与牛熊、高波动筛选组合。
