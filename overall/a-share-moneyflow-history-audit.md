# A股历史有方向成交量数据审计

- rows/distinct/duplicates: 9,368,505/9,368,505/0
- coverage: 20180102—20260827；symbols: 5793
- MarketData join coverage: 92.9699%
- null max: 0；nonpositive denominator: 0
- decision: **RESEARCH-USABLE**

|年|行数|交易日|日截面中位数|小单占比|中单|大单|超大单|大单净流率中位数|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|2018|816,683|243|3355|26.01%|33.62%|27.49%|12.88%|-1.622%|
|2019|884,816|244|3610|26.39%|33.47%|27.26%|12.88%|-1.723%|
|2020|945,853|243|3857|25.38%|33.08%|27.68%|13.86%|-1.915%|
|2021|1,058,569|243|4378|28.29%|33.08%|25.62%|13.01%|-1.470%|
|2022|1,146,022|242|4715|34.18%|33.96%|22.41%|9.44%|-1.147%|
|2023|1,209,410|242|5002|34.27%|34.32%|22.55%|8.86%|-1.158%|
|2024|1,233,188|242|5095|34.03%|33.75%|22.88%|9.34%|-0.884%|
|2025|1,248,108|243|5139|32.47%|33.19%|23.70%|10.63%|-0.779%|
|2026|825,856|158|5187|30.67%|32.53%|23.98%|12.82%|-0.555%|

>=5pp bucket-share breaks: 1
All-order directional amount / MarketData Amount median scale: 0.000200000

> Large/small order buckets have a 2021→2022 structural break. All-order buy minus sell is mechanically near zero and cannot express direction. Directional research must use large/extra-large imbalance with rolling history reset at the 2022 methodology epoch.
> 658,613 rows lack local MarketData joins; directional breadth may use them, but price validation is limited to matched rows.
