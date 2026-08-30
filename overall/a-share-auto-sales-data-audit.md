# A股汽车销量周期数据审计

## 结论

中汽协官网可复现发现链不足以形成2018—2025连续月度PIT面板，当前**不得验证或交易**汽车销量加速度策略。

- 抓取入口：`http://www.caam.org.cn/chn/4/cate_31/list_N.html`
- 发现2018—2025月度汽车工业文章：45个月/应有96个月。
- 成功提取：44/45；HTML 40，官方文章图片OCR 4。
- 2018完整；2019—2025均有缺月；2022只有单篇2月文章且原图已404，正文没有月度数值。
- 补扫内容ID `5235201—5235760`仅发现上述2022年2月文章，不能闭合2022月度序列。
- 每篇HTML、图片/OCR文本、URL、发布时间和SHA256已保存；缺失保持missing，不插值、不用搜索摘要补数。

## 产物

- `overall/a-share-auto-sales-monthly.csv`
- `overall/a-share-auto-sales-manifest.json`
- `overall/a-share-auto-sales-raw/`
- `experiments/fetch_caam_auto_sales.py`

## 裁决

`SOURCE-BLOCKED / NO BACKTEST`。若后续获得中汽协《中国汽车工业产销快讯》连续原件或另一个有正式发布时间的官方连续月度源，可恢复预注册模型；否则不允许用现有44个月选择窗口或阈值。
