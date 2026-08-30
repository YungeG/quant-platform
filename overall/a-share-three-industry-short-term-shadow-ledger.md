# 三行业中短期信息策略Shadow账本

该账本对应`a-share-three-industry-short-term-information-design.md`，资金为0，不产生真实订单。

- Arm A：月末行业内分析师正修正Top-10；
- Arm B：Arm A中20日收益为正且站上MA20；
- Arm C：行业内实际盈利惊喜最高五分位。

每次决策必须追加信号和空信号；停牌、涨停、整手不足、缺失价格和数据错误均写入`execution_status/rejection_reason`，不能删除。结果成熟后填入20/60日股票、行业及active return。`data_snapshot_hash`绑定当次原始报告、财报、行情和行业成员快照；`replay_status`记录计划与独立回放是否一致。

最低观察12个月。任何字段、阈值和行业变化都必须另建版本，禁止覆盖本账本。
