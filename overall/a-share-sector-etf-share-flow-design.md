# A股行业ETF份额申购扩散模型预注册设计

- **信号：** 行业ETF一级市场份额变化；不使用V6吸收扩散阈值
- **候选：** 冻结直接行业ETF映射，排除REIT/港股/海外；ETF上市满20个交易日后才纳入

个ETF五日申购率=`fd_share_t/fd_share_t-5-1`；五日净申购价值代理=`(fd_share_t-fd_share_t-5)*adj_close_t`。行业五日申购率=`sum(net_creation_value)/sum(fd_share_t-5*adj_close_t)`；同时记录正申购ETF占比和有效ETF数。

- `INFLOW_SEED`：行业五日申购率>0且上穿自身120日80%分位，正申购ETF占比>50%；
- `INFLOW_DIFFUSION`：种子后10日内申购率连续3日>0、正申购ETF占比>=60%；
- `END`：申购率连续3日<0；
- 未扩散为FAILED_SEED，同一行业结束前不重复。

事件以扩散日T为信号，测量行业指数及最液态直接ETF T+1后30/35/40日结果。Gate沿用行业模型；ETF历史覆盖不足保持unresolved，不使用未来上市基金补历史。
