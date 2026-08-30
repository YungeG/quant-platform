"""Build PIT daily industry attention breadth states from THS Top-100 rankings."""
from __future__ import annotations
import argparse,json
from collections import deque
import duckdb,numpy as np,pandas as pd
from experiments.build_industry_revision_diffusion_states import members_at
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.research.combination import repair_point_in_time_size
def final_snapshots(raw_dir):
 con=duckdb.connect()
 try:
  frame=con.execute(f'''with x as (select cast(trade_date as varchar) trade_date,ts_code,ts_name,cast(rank as integer) rank,cast(hot as double) hot,cast(rank_time as timestamp) rank_time,time_bucket(interval '30 minutes',cast(rank_time as timestamp)) bucket from read_parquet('{raw_dir}/ths_stock_*.parquet')), d as (select trade_date,max(bucket) last_bucket,count(distinct bucket) bucket_count from x group by 1) select x.trade_date,x.ts_code,x.ts_name,x.rank,x.hot,x.rank_time from x join d using(trade_date) where x.bucket=d.last_bucket and hour(d.last_bucket)>=15 and d.bucket_count>=5 order by x.trade_date,x.rank''').fetchdf()
 finally:con.close()
 frame["decision_date"]=pd.to_datetime(frame.trade_date);frame["Symbol"]=frame.ts_code.str[:6];frame["rank_pct"]=1-(frame["rank"]-1)/99;dates=sorted(frame.decision_date.unique());date_index={d:i for i,d in enumerate(dates)};frame["date_index"]=frame.decision_date.map(date_index);frame["new_entry"]=False;frame["persistence_5d"]=0
 for _,index in frame.groupby("Symbol",sort=False).groups.items():
  positions=frame.loc[index,"date_index"].to_numpy();last=-10**9;window=deque()
  for row_index,position in zip(index,positions,strict=True):
   frame.at[row_index,"new_entry"]=position-last>5
   while window and window[0]<position-4:window.popleft()
   window.append(position);frame.at[row_index,"persistence_5d"]=len(window);last=position
 return frame,dates
def run(raw_dir,members_path,start,end,states_path,event_states_path,waves_path):
 top,source_dates=final_snapshots(raw_dir);source_dates=[d for d in source_dates if pd.Timestamp(start)<=d<=pd.Timestamp(end)];top=top[top.decision_date.isin(source_dates)];m=pd.read_csv(members_path,dtype=str);m["Symbol"]=m.ts_code.str[:6];m["in_date"]=pd.to_datetime(m.in_date,errors="coerce");m["out_date"]=pd.to_datetime(m.out_date,errors="coerce");cfg=Config();con=connect(cfg,read_only=True)
 try:built=load_or_build_panel(cfg,"2023-01-01",end,con=con)
 finally:con.close()
 p=repair_point_in_time_size(built.df);p.TradingDay=pd.to_datetime(p.TradingDay);adv=p.groupby("TradingDay").adv20.rank(pct=True,method="first");p["practical"]=(~p.is_st.fillna(True))&(~p.suspended.fillna(True))&(p.age>=252)&(p.Close>=5)&(p.Volume>0)&p.CircMV.notna()&(adv>.5);sessions=sorted(p.TradingDay.drop_duplicates());session_index={d:i for i,d in enumerate(sessions)};rows=[]
 for day in source_dates:
  mem=members_at(m,day);base=p[(p.TradingDay==day)&p.practical&p.Symbol.isin(mem.Symbol)].merge(mem[["Symbol","l1_name"]],on="Symbol",how="inner");ranked=top[top.decision_date.eq(day)].sort_values(["rank","Symbol"]).drop_duplicates("Symbol")
  for industry,b in base.groupby("l1_name"):
   hits=ranked[ranked.Symbol.isin(b.Symbol)];targets=hits.head(10).Symbol.tolist();tradable=b.Symbol.nunique();rows.append({"decision_date":day,"industry":industry,"tradable_count":tradable,"appeared_count":hits.Symbol.nunique(),"industry_breadth":hits.Symbol.nunique()/tradable if tradable else np.nan,"industry_new_entries":int(hits.new_entry.sum()),"median_rank_pct":float(hits.rank_pct.median()) if len(hits) else np.nan,"top_symbols":json.dumps(targets,ensure_ascii=False)})
 states=pd.DataFrame(rows).sort_values(["decision_date","industry"]);states["breadth_pct"]=states.groupby("decision_date").industry_breadth.rank(pct=True,method="average");states["breadth_baseline20"]=states.groupby("industry").industry_breadth.transform(lambda s:s.shift(1).rolling(20,min_periods=20).median());states["breadth_shock"]=states.industry_breadth-states.breadth_baseline20;states["seed_condition"]=(states.tradable_count>=10)&(states.breadth_pct>=.80)&(states.breadth_shock>0)&(states.industry_new_entries>=2);records=[];events=[];waves=[]
 for industry,g in states.groupby("industry"):
  active=False;previous_seed=False;hold_fail=0;last_event=-10**9
  for row in g.sort_values("decision_date").itertuples(index=False):
   event=False;resolved=row.tradable_count>=10 and pd.notna(row.breadth_baseline20)
   if active:
    hold=resolved and row.breadth_pct>=.60;hold_fail=0 if hold else hold_fail+1
    if hold_fail>=2:active=False;status="NO-ENTRY"
    else:status="ENTER"
   elif resolved and row.seed_condition and previous_seed:
    active=True;hold_fail=0;status="ENTER";position=session_index.get(pd.Timestamp(row.decision_date),-10**9);event=position-last_event>40
    if event:last_event=position
   elif resolved and row.seed_condition:status="ATTENTION_SEED"
   elif not resolved:status="UNRESOLVED"
   else:status="NO-ENTRY"
   data={**row._asdict(),"status":status,"entry_event":event,"score":float(row.breadth_pct*100) if pd.notna(row.breadth_pct) else np.nan};records.append(data)
   if event:events.append({"decision_date":row.decision_date,"industry":industry,"score":data["score"],"entry_event":True,"top_symbols":row.top_symbols});waves.append({"sector":industry,"seed_date":row.decision_date,"diffusion_date":row.decision_date,"status":"ATTENTION_DIFFUSION"})
   previous_seed=bool(resolved and row.seed_condition)
 out=pd.DataFrame(records);out.to_csv(states_path,index=False,date_format="%Y-%m-%d");pd.DataFrame(events).to_csv(event_states_path,index=False,date_format="%Y-%m-%d");pd.DataFrame(waves).to_csv(waves_path,index=False,date_format="%Y-%m-%d");return {"panel_version":built.version_hash,"valid_source_dates":len(source_dates),"rows":len(out),"events":len(events),"industries":out.industry.nunique(),"states":states_path,"event_states":event_states_path,"waves":waves_path}
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--raw-dir",default="overall/a-share-attention-raw");p.add_argument("--members",default="overall/a-share-sw2021-members.csv");p.add_argument("--start",default="2024-01-02");p.add_argument("--end",default="2026-08-27");p.add_argument("--states",default="overall/a-share-attention-states.csv");p.add_argument("--event-states",default="overall/a-share-attention-event-states.csv");p.add_argument("--waves",default="overall/a-share-attention-waves.csv");a=p.parse_args(argv);print(json.dumps(run(a.raw_dir,a.members,a.start,a.end,a.states,a.event_states,a.waves),ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
