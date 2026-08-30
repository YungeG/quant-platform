from __future__ import annotations
import pytest
pytest.importorskip("numpy")
pd=pytest.importorskip("pandas")
from experiments.weekly_industry_cycle import FEATURE_WEIGHTS,mark_entry_events,path_metrics,rolling_percentile,score_weekly_states,weekly_last_sessions

def test_weekly_last_sessions_uses_each_week_last_observation():
 sessions=pd.to_datetime(["2025-01-02","2025-01-03","2025-01-06","2025-01-10"])
 assert weekly_last_sessions(sessions)==list(pd.to_datetime(["2025-01-03","2025-01-10"]))

def test_rolling_percentile_uses_only_trailing_history():
 values=list(range(60));result=rolling_percentile(values,window=52,minimum=52)
 assert pd.isna(result[50]);assert result[51]==1.0;assert result[-1]==1.0

def test_score_is_unresolved_until_history_and_coverage_exist():
 rows=[]
 for i,date in enumerate(pd.date_range("2020-01-03",periods=53,freq="W-FRI")):
  row={"decision_date":date,"industry":"测试","market_coverage":1.0,"financial_coverage":1.0,"analyst_coverage":1.0}
  row.update({feature:float(i+1) for feature in FEATURE_WEIGHTS});rows.append(row)
 scored=score_weekly_states(pd.DataFrame(rows));assert scored.score.iloc[:51].isna().all();assert pd.notna(scored.score.iloc[51]);rows[-1]["financial_coverage"]=.59;assert pd.isna(score_weekly_states(pd.DataFrame(rows)).score.iloc[-1])

def test_entry_hysteresis_and_cooldown_are_deterministic():
 sessions=list(pd.date_range("2025-01-03",periods=50,freq="B"));dates=[sessions[i] for i in [0,5,10,15,20,25]];scores=[50,65,71,65,59,72];frame=pd.DataFrame({"decision_date":dates,"industry":"测试","score":scores});marked=mark_entry_events(frame,sessions,cooldown_sessions=40)
 assert marked.status.tolist()==["NO-ENTRY","WATCH","ENTER","ENTER","NO-ENTRY","ENTER"]
 assert marked.entry_event.tolist()==[False,False,True,False,False,False]

def test_path_metrics_records_fixed_horizons_extremes_and_outperformance_days():
 dates=[d.date().isoformat() for d in pd.date_range("2025-01-03",periods=41,freq="B")];daily_returns=pd.Series(range(1,41),dtype=float)/1000-0.02;nav=[100.0]+list(100*(1+daily_returns));benchmark=[0.0]*40;result=path_metrics(dates,nav,benchmark,100.0)
 assert result.observed_days==40;assert result.return_d30==pytest.approx(.01);assert result.return_d35==pytest.approx(.015);assert result.return_d40==pytest.approx(.02);assert result.max_return_day==40;assert result.min_return_day==1;assert result.days_outperform_hs300_40==20;assert result.outperform_ratio_40==pytest.approx(.5)
