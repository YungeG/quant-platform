# A股价格归一化EPS修正＋未提前上涨V15设计（预注册）

## 信号

沿用V14：

```text
revision_to_price = (current_consensus_eps - prior_consensus_eps) / T日股价
```

使用PIT ST、Top-500市值/流动性股票池和24个月正修正广度状态。

## 唯一新增规则

在每个决策月全部有效候选中，计算过去20日股票收益减PIT Top-500等权过去20日收益的`prior_active20`百分位。排除当月最高20%（`prior_runup_pct>=0.80`），再从`revision_to_price>0`股票中按修正、配对机构数、代码选择Top-10。

不测试10%/30%、5/60日回看、固定涨幅阈值或与比例修正组合。

## Gate

完全沿用V14：CAGR严格高于14.32%，2023—2024和2025正超额，Sharpe>=0.60、最大回撤>=-50%、成本保留>=80%、换手<=12。信号必须有限且无旧EPS分母。
