# A股原油—聚烯烃资产路线映射 V1 预注册设计

## 目标

建立2018-03-26—2026-08-28期间可由公告证明的A股聚烯烃资产时点表。该表只描述资产、路线和名义产能，不推断开工率、产量、吨利润或股票仓位。

## 冻结发行人

以下发行人来自当前申万一级石油石化/基础化工成员，并覆盖主要生产路线：

| 代码 | 名称 | 预期需要核验的路线 |
| --- | --- | --- |
| 601857.SH | 中国石油 | 油气—炼化一体化、混合资产 |
| 600028.SH | 中国石化 | 炼油石化、煤化工、混合资产 |
| 600688.SH | 上海石化 | 油制炼化一体化 |
| 600346.SH | 恒力石化 | 原油—炼化—烯烃一体化 |
| 002493.SZ | 荣盛石化 | 浙石化炼化一体化 |
| 000301.SZ | 东方盛虹 | 盛虹炼化及其他化工路线 |
| 002648.SZ | 卫星化学 | 乙烷/轻烃路线 |
| 600989.SH | 宝丰能源 | 煤/焦炉气—甲醇—烯烃 |
| 002221.SZ | 东华能源 | 丙烷脱氢及聚丙烯 |

冻结后不因检索方便或结果表现增加、删除发行人。

## 行结构

```text
issuer_code
issuer_name
asset_or_project
product
route
asset_state
capacity_tpa
ownership_share
effective_from
effective_to
filing_publish_datetime
source_ids_json
filing_urls_json
source_sha256s_json
page_or_table
evidence_status
notes
closure_visibility_date
closure_source_ids_json
closure_filing_urls_json
closure_source_sha256s_json
```

## 允许值

- `product`：`PP | LLDPE | HDPE | other_PE | mixed_PE | unresolved`
- `route`：`oil_integrated | coal_MTO | ethane_gas | propane_PDH | mixed | unknown`
- `asset_state`：`planned | test_production | operating | disposed_precommission`
- `evidence_status`：
  - `qualified`：公告同时绑定命名资产、产品、路线、产能和生效依据；
  - `partial`：至少绑定命名资产和路线，但产品、产能或生效日期不完整；
  - `unresolved`：仅有集团或行业描述，不能绑定资产。

## 时点规则

1. 只使用CNINFO、上交所、深交所或发行人正式年报、半年报、项目公告。
2. `filing_publish_datetime`决定区间开启信息的可见时间；不得使用公告发布日期之前的信息。
3. `effective_to`必须同时保存后续关闭证据及`closure_visibility_date`；在关闭证据公开前，PIT读取仍视为原区间未关闭。
4. 投产、收购、出售、停产或扩建开启/关闭资产区间；计划产能不得提前视为有效产能。
5. 年报只能确认报告期末状态；若无法定位实际投产日期，`effective_from`保持空值或使用明确的保守可见日期并标记`partial`。
6. 集团同时包含多种路线时必须拆分资产；不能给整个公司贴单一路线标签。
7. `capacity_tpa`保持公告原单位换算后的吨/年；不把权益产能与名义产能混淆。
8. 缺失不填零；冲突公告并列保留并进入人工复核。

## 固定产物

- `overall/a-share-oil-polyolefin-issuer-assets-v1.csv`
- `overall/a-share-oil-polyolefin-issuer-sources-v1.json`
- `overall/a-share-oil-polyolefin-issuer-map-v1-conclusion.md`
- 原始PDF保存在`overall/a-share-oil-polyolefin-issuer-raw/`，由Git忽略。

## 验收与停止条件

- 9家发行人均至少有一份带SHA-256的第一方来源；
- 每个`qualified`行均有可复核页码或表名；
- 时间区间无重叠冲突，除非明确标记待复核；
- 无来源的路线、产能和生效日期保持缺失；
- 若油制PP/L核心资产中超过一半只能得到集团级`partial/unresolved`证据，则停止策略设计，维持plan-only。

本设计不授权回测或交易。
