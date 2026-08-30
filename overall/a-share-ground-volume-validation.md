# A股地量效应验证结果

- verdict: **MARGINAL**
- signal GO carriers: 4/4
- portfolio GO carriers: 0/4
- data through: 2026-08-25

| 载体 | 120日spread | 正时间折 | 正偏移 | 偏移中位 | Signal | Timing CAGR | Calmar Δ | Portfolio |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |
| csi300_total_return | 4.87% | 2/3 | 5/6 | 7.49% | GO | 5.99% | +0.014 | NO |
| csi500_total_return | 2.87% | 3/3 | 5/6 | 7.26% | GO | 4.78% | -0.014 | NO |
| csi1000_total_return | 3.18% | 3/3 | 5/6 | 4.94% | GO | 3.36% | -0.022 | NO |
| csi_dividend_total_return | 6.45% | 3/3 | 6/6 | 9.54% | GO | 8.14% | +0.028 | NO |

## Gate

- GO：至少2个载体Signal GO，且至少1个载体Portfolio GO。
- MARGINAL：至少2个载体Signal GO，但没有Portfolio GO。
- NO-GO：少于2个载体Signal GO。
