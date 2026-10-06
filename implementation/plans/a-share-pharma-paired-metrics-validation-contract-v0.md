# 医药成对指标草案：本会话NAV更新

DRAFT / NOT_ACCEPTED；只保留本会话2026-10-04增量，不包含旧合约或后续成对比较实现。

## 2026-10-04实现更新（本v0成对验收仍DRAFT）

Backtest现有独立`CnASharePortfolioDailyNavAnalysisRuntimeV1`及新NAV profile/analysis@1、public Repository源重投影：原Oct A/B10日图在native Journal/mark/calendar绑定下已得**开发级收盘MaxDD**，旧simple return与旧Analysis字节不变。37个不同新增检查、3旧golden及实际两臂见[最新台账](a-share-pharma-weekly-ab-execution-v1.md)。这不是此草案拟定的decision-grade/成对Validation或holdout报告；新namespace不能让旧OosRule自动支持成对回撤。“只有最终snapshot”的旧概括只适用于旧分析视图，不再否认当前Native完成图已有十个日快照；旧Analysis本身仍无回撤字段。下文9/29内容保留历史背景。
