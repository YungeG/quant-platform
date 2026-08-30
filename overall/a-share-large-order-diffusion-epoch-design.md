# A股大单方向扩散分时期设计

- **数据：** `moneyflow`大单与超大单买卖分项
- **方向：** `large_net_rate=((buy_lg+buy_elg)-(sell_lg+sell_elg))/directional_amount`
- **方法断点：** 2021→2022大小单占比显著变化；滚动120日历史按`2018-2021`和`2022-2026`两个epoch独立计算，2022年新epoch前120个交易日仅作暖机，不产生事件
- **禁止：** 跨epoch比较large_net_rate绝对水平；使用供应商net_mf_amount；使用全买减全卖

个股buy/sell leader、持续龙头、新进入、板块买卖广度、正净买入集中度、熵及ACCUMULATION_SEED/BUY_DIFFUSION/BROAD_ACCUMULATION/DISTRIBUTION/END状态沿用`signed-volume-diffusion-design.md`。

历史检验：2018—2021为早期独立时期；2022仅暖机；2023—2024验证；2025冻结保留；2026前向。各时期结果分别报告，模型总Gate不允许由断点前单独贡献。
