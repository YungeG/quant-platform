"""Pure helpers for the weekly all-industry cycle study."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
import numpy as np,pandas as pd
FEATURE_WEIGHTS={"triple_growth_breadth":15,"roe_median":10,"ocf_positive_breadth":5,"fcf_positive_breadth":5,"pe_median":10,"pb_median":5,"liquid_coverage":5,"diversification":5,"positive_revision_breadth":15,"median_revision":5,"ma20_breadth":5,"relative20":5};LOWER_BETTER={"pe_median","pb_median"}
@dataclass(frozen=True)
class EventPath:
 observed_days:int
 return_d30:float|None;return_d35:float|None;return_d40:float|None
 hs300_return_d30:float|None;hs300_return_d35:float|None;hs300_return_d40:float|None
 active_d30:float|None;active_d35:float|None;active_d40:float|None
 max_return_40:float|None;max_return_day:int|None;max_return_date:str|None
 min_return_40:float|None;min_return_day:int|None;min_return_date:str|None
 max_active_40:float|None;max_active_day:int|None;max_active_date:str|None
 min_active_40:float|None;min_active_day:int|None;min_active_date:str|None
 days_outperform_hs300_40:int;outperform_ratio_40:float|None
def weekly_last_sessions(sessions:Sequence[pd.Timestamp])->list[pd.Timestamp]:
 s=pd.Series(sorted(pd.to_datetime(list(sessions))));return s.groupby(s.dt.to_period("W-FRI")).max().tolist()
def rolling_percentile(values:Sequence[float],window:int=260,minimum:int=52,lower:bool=False)->list[float]:
 result=[]
 for index,value in enumerate(values):
  history=pd.Series(values[max(0,index-window+1):index+1]).dropna()
  if pd.isna(value) or len(history)<minimum:result.append(np.nan);continue
  transformed=-history if lower else history;current=-value if lower else value;result.append(float((transformed<=current).mean()))
 return result
def score_weekly_states(raw:pd.DataFrame)->pd.DataFrame:
 scored=raw.sort_values(["industry","decision_date"]).copy()
 for feature in FEATURE_WEIGHTS:
  scored[feature+"_pct"]=scored.groupby("industry",group_keys=False)[feature].transform(lambda s:pd.Series(rolling_percentile(s.tolist(),lower=feature in LOWER_BETTER),index=s.index))
 scored["data_complete"]=(scored.market_coverage>=.90)&(scored.financial_coverage>=.60)&(scored.analyst_coverage>=.30);scored["score"]=10.0
 for feature,weight in FEATURE_WEIGHTS.items():scored["score"]+=weight*scored[feature+"_pct"]
 scored.loc[~scored.data_complete|scored[[f+"_pct" for f in FEATURE_WEIGHTS]].isna().any(axis=1),"score"]=np.nan;return scored
def mark_entry_events(scored:pd.DataFrame,sessions:Sequence[pd.Timestamp],enter:float=70,hold:float=60,cooldown_sessions:int=40)->pd.DataFrame:
 index={pd.Timestamp(day):i for i,day in enumerate(sessions)};out=[]
 for industry,g in scored.sort_values("decision_date").groupby("industry"):
  active=False;last_event=-10**9
  for row in g.itertuples(index=False):
   score=float(row.score) if pd.notna(row.score) else np.nan;event=False
   if pd.isna(score):status="UNRESOLVED";active=False
   elif active and score>=hold:status="ENTER"
   elif active:status="NO-ENTRY";active=False
   elif score>=enter:
    status="ENTER";active=True;position=index.get(pd.Timestamp(row.decision_date),-10**9);event=position-last_event>cooldown_sessions
    if event:last_event=position
   elif score>=hold:status="WATCH"
   else:status="NO-ENTRY"
   values=row._asdict();values.update({"status":status,"entry_event":event});out.append(values)
 return pd.DataFrame(out)
def path_metrics(dates:Sequence[str],nav:Sequence[float],benchmark_returns:Sequence[float],initial_nav:float)->EventPath:
 observed=min(40,max(0,len(nav)-1),len(benchmark_returns));event_dates=list(dates)[1:1+observed];returns=np.asarray(nav[1:1+observed],float)/initial_nav-1;benchmark=np.asarray(benchmark_returns[:observed],float);active=returns-benchmark
 def at(values,day):return float(values[day-1]) if observed>=day else None
 def extreme(values,kind):
  if not len(values):return None,None,None
  i=int(np.argmax(values) if kind=="max" else np.argmin(values));return float(values[i]),i+1,str(event_dates[i])
 max_r,max_rd,max_rdate=extreme(returns,"max");min_r,min_rd,min_rdate=extreme(returns,"min");max_a,max_ad,max_adate=extreme(active,"max");min_a,min_ad,min_adate=extreme(active,"min");days=int((active>0).sum())
 return EventPath(observed,at(returns,30),at(returns,35),at(returns,40),at(benchmark,30),at(benchmark,35),at(benchmark,40),at(active,30),at(active,35),at(active,40),max_r,max_rd,max_rdate,min_r,min_rd,min_rdate,max_a,max_ad,max_adate,min_a,min_ad,min_adate,days,days/observed if observed else None)
