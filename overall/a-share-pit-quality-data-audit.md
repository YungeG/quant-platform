# PIT质量因子数据审计

- **接口：** fina_indicator_vip
- **裁决：** RESEARCHABLE

年度接口从2012起可返回`ann_date`、`end_date`、`update_flag`和完整质量指标。单个年度实测可超过10,000行且正常返回；2012、2016、2020、2025年分别返回7,876、10,425、11,914、6,817行。

本轮只获取年度报告的`roe_waa`、`grossprofit_margin`、`debt_to_assets`，按公告日PIT选择最新可见版本。它解决了本地FinancialIndicatorData AnnDate全空的问题。
