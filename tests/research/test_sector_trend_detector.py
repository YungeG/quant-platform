from __future__ import annotations
import pandas as pd
from experiments.build_sector_trend_states import run

def test_breakout_uses_prior_ten_sessions_and_enters_once(tmp_path):
 dates=pd.bdate_range("2024-01-02",periods=45);index=[1.0]*11+[1.0+0.01*i for i in range(1,35)];panel=pd.DataFrame({"trade_date":dates,"sector":"钢铁","sector_index":index,"benchmark_index":1.0});source=tmp_path/"panel.csv";states=tmp_path/"states.csv";positions=tmp_path/"positions.csv";labels=tmp_path/"labels.csv";panel.to_csv(source,index=False);run(str(source),str(states),str(positions),str(labels));s=pd.read_csv(states);entries=s[s.enter_signal.astype(str).str.lower().eq("true")];assert len(entries)==1;assert entries.iloc[0].trade_date==dates[11].date().isoformat();assert entries.iloc[0].sector_index>s.iloc[1:11].sector_index.max()
