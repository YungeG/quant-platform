# A股资源行业周期领先数据审计

- **期货主力/连续映射：** `fut_mapping` 2018和2026均可访问；
- **连续期货日线：** `fut_daily`可直接查询`CUL.SHF`、`RBL.SHF`、`IL.DCE`、`SCL.INE`等连续代码；
- **仓单日报：** `fut_wsr` 2018和2026均可访问，字段含昨日仓单、今日仓单和变化；
- **权限裁决：** RESEARCH-USABLE。

建议映射：有色金属=CU/AL/ZN/PB/NI/SN；钢铁=RB/HC/I/J/JM；基础化工=TA/MA/PP/L/V/EG/EB/RU/SA/FG/UR；石油石化=SC/FU/BU/LU。煤炭的ZC/JM仓单跨期覆盖不足，第一版UNRESOLVED。

仓单覆盖并不统一：CU/AL/ZN/NI、RB/HC/J、FU/BU、MA/PP/L/V/RU/FG在2018与2026均有记录；I/SC/EG/EB主要是后期数据，TA/ZC等当前覆盖缺失。模型必须按产品自身历史有效期计算，不把缺失库存视为0。

连续合约解决主力换月，但仍需保存映射和结算价；仓单单位随产品不同，只能使用产品自身20日变化率和行业内方向广度，不能直接汇总吨数/手数。
