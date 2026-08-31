# 沪深300 / 中证500 / 中证1000调样来源审计V2

## 结论

**`SOURCE_FOUND / CAPTURE_PARTIAL / NO_BACKTEST_RUN`**

已定位中证指数公司官网的第一方公告接口：

- 列表：`https://www.csindex.com.cn/csindex-home/announcement/queryAnnouncementByVo`
- 详情：`https://www.csindex.com.cn/csindex-home/announcement/queryAnnouncementById?id=<notice_id>`
- 固定过滤：`index_rebalance`、`announcement`、`index`

公告详情提供正式发布日期、正文、附件URL和附件创建/更新时间；正文通常明确实际生效日。2024小样本成功捕获6条目标指数公告、6个官方附件，6条均解析出明确生效日。

## 2024烟雾验证

- 覆盖：2024-01-01—2024-12-31
- 公告：6条
- 附件：6个PDF/XLSX
- 明确生效日：6/6
- 发布时间范围：2024-05-08—2024-11-29
- `notices.jsonl` SHA256：`b556dea7868a19cb808d787a0055afe9242948514ff6306a09347d421f8b3bb5`

其中2024-05-31和2024-11-29公告同时包含沪深300、中证500和中证1000的定期调整，正文分别声明2024-06-14和2024-12-13收市后生效。

## 全量尝试

2016-01-01—2026-08-31全量捕获在读取公告`14223`时被官网WAF以HTTP 403阻断。未伪造缺失记录，也未启动回测。

`experiments/fetch_csi_rebalance_history.py`现已增加：

- 每条公告独立检查点；
- 附件SHA256与大小；
- 可调请求间隔；
- 失败收据和断点续跑；
- 公告发布日期及生效日提取。

## 未完成Gate

1. WAF解除后完成断点捕获；
2. 解析全部PDF/XLSX调入调出名单；
3. 覆盖临时调整、退市触发和更正公告；
4. 建立不可变原始文件哈希及终端完整性证明；
5. 预留独立holdout后才能预注册回测。

因此旧`SOURCE-BLOCKED`状态有所改善，但尚未达到可回测来源标准，`trade_authorized=false`。
