"""Build frozen online sector trend states and ex-post monthly trend labels."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
EXCLUDED={"半导体"}
def run(panel_path,states_path,positions_path,labels_path):
 x=pd.read_csv(panel_path,usecols=["trade_date","sector","sector_index","benchmark_index"]);x["trade_date"]=pd.to_datetime(x.trade_date);x=x[~x.sector.isin(EXCLUDED)].sort_values(["sector","trade_date"]);states=[];positions=[];labels=[]
 for sector,g in x.groupby("sector"):
  g=g.reset_index(drop=True).copy();g["relative_index"]=g.sector_index/g.benchmark_index;g["abs_high10_prev"]=g.sector_index.shift(1).rolling(10,min_periods=10).max();g["rel_high10_prev"]=g.relative_index.shift(1).rolling(10,min_periods=10).max();g["rel_low10_prev"]=g.relative_index.shift(1).rolling(10,min_periods=10).min();g["breakout"]=g.sector_index.gt(g.abs_high10_prev)&g.relative_index.gt(g.rel_high10_prev);active=False;entry_index=None;position_id=None;hold=0
  for i,row in g.iterrows():
   enter=False;exit_=False;reason=""
   if active:
    hold+=1
    if row.relative_index<row.rel_low10_prev:exit_=True;reason="relative_10d_low"
    elif hold>=35:exit_=True;reason="max_35_sessions"
   elif bool(row.breakout):
    active=True;enter=True;entry_index=i;hold=0;position_id=f"{sector}|{row.trade_date.date()}"
   states.append({"trade_date":row.trade_date,"sector":sector,"sector_index":row.sector_index,"benchmark_index":row.benchmark_index,"relative_index":row.relative_index,"abs_high10_prev":row.abs_high10_prev,"rel_high10_prev":row.rel_high10_prev,"rel_low10_prev":row.rel_low10_prev,"breakout":bool(row.breakout),"enter_signal":enter,"exit_signal":exit_,"active_at_close":active and not exit_,"position_id":position_id if active else "","hold_sessions":hold if active else 0,"exit_reason":reason})
   if exit_:
    positions.append({"position_id":position_id,"sector":sector,"entry_signal_date":g.at[entry_index,"trade_date"],"entry_index":entry_index,"exit_signal_date":row.trade_date,"exit_index":i,"exit_reason":reason,"holding_signal_sessions":i-entry_index});active=False;entry_index=None;position_id=None;hold=0
  if active:positions.append({"position_id":position_id,"sector":sector,"entry_signal_date":g.at[entry_index,"trade_date"],"entry_index":entry_index,"exit_signal_date":pd.NaT,"exit_index":len(g)-1,"exit_reason":"OPEN","holding_signal_sessions":len(g)-1-entry_index})
  raw=[]
  for i in range(len(g)-20):
   r10=g.at[i+10,"sector_index"]/g.at[i,"sector_index"]-1;r20=g.at[i+20,"sector_index"]/g.at[i,"sector_index"]-1;a20=g.at[i+20,"relative_index"]/g.at[i,"relative_index"]-1
   if r10>=.04 and r20>=.08 and a20>=.04:raw.append((i,r10,r20,a20))
  kept=[];last=-10**9
  for item in raw:
   if item[0]-last>=20:kept.append(item);last=item[0]
  sector_positions=[p for p in positions if p["sector"]==sector]
  for i,r10,r20,a20 in kept:
   matched=[]
   for p in sector_positions:
    entry=p["entry_index"];exit_index=p["exit_index"]
    if entry<=i<=exit_index or i<=entry<=i+10:matched.append(p)
   match=min(matched,key=lambda p:(0 if p["entry_index"]<=i else p["entry_index"]-i,p["entry_index"])) if matched else None;delay=0 if match and match["entry_index"]<=i else match["entry_index"]-i if match else None;capture_start=max(i,match["entry_index"]) if match else None;remaining=g.at[i+20,"sector_index"]/g.at[capture_start,"sector_index"]-1 if match else None;labels.append({"trend_id":f"{sector}|{g.at[i,'trade_date'].date()}","sector":sector,"trend_start":g.at[i,"trade_date"],"trend_end":g.at[i+20,"trade_date"],"start_index":i,"forward10":r10,"forward20":r20,"active20":a20,"detected":bool(match),"position_id":match["position_id"] if match else "","detection_delay":delay,"remaining_return":remaining,"capture_ratio":remaining/r20 if match and r20!=0 else None})
 pd.DataFrame(states).to_csv(states_path,index=False,date_format="%Y-%m-%d");pd.DataFrame(positions).to_csv(positions_path,index=False,date_format="%Y-%m-%d");pd.DataFrame(labels).to_csv(labels_path,index=False,date_format="%Y-%m-%d");return {"sectors":x.sector.nunique(),"states":len(states),"positions":len(positions),"trend_labels":len(labels),"states_path":states_path,"positions_path":positions_path,"labels_path":labels_path}
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--panel",default="overall/a-share-sector-daily-2017-2026.csv");p.add_argument("--states",default="overall/a-share-sector-trend-states.csv");p.add_argument("--positions",default="overall/a-share-sector-trend-positions.csv");p.add_argument("--labels",default="overall/a-share-sector-month-trend-labels.csv");a=p.parse_args(argv);print(json.dumps(run(a.panel,a.states,a.positions,a.labels),ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
