# A股EPS比例修正分母归因设计（冻结）

## 对象

使用PIT ST修正后的`revision_breadth_top10`历史入选记录，不修改信号、状态、持股数或执行。

## 互斥分类

每个决策月先在有效候选中，对`prior_eps>0`股票的旧EPS共识计算20%分位数。入选Top-10按以下优先级分类：

1. `NEGATIVE_BASE_DETERIORATION`：`prior_eps<0`且`current_eps<prior_eps`，比例修正为正但亏损实际恶化；
2. `SMALL_POSITIVE_BASE_UPGRADE`：`prior_eps>0`、`current_eps>prior_eps`且旧EPS不高于当月正EPS候选20%分位；
3. `NORMAL_POSITIVE_UPGRADE`：`prior_eps>0`且`current_eps>prior_eps`，不属于小基数；
4. `OTHER_RATIO_POSITIVE`：其余比例修正>0情况。

不得根据收益修改20%或合并类别。

## 价格提前反映分层

在决策日计算股票过去20日收益，并减同日PIT Top-500可交易股票池过去20日等权收益。按当月有效候选的`prior_active20`百分位：

- `HIGH_PRIOR_RUNUP`：最高20%；
- `NORMAL_PRIOR_RUNUP`：其余80%。

先报告两组及其与EPS分母类别的交叉结果，不直接排除。不得测试10%/30%分位或其他回看窗口。

## 指标

报告记录数、月份覆盖、修正值中位数、过去20日active、未来20日active均值/中位数/胜率、2017—2019/2020—2022/2023—2026固定时期、active总和占比、类别内最佳5%收益剔除后的均值，以及Top-10类别构成。

该审计只解释17.81%候选来源，不生成新交易策略。
