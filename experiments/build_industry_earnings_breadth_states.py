"""Build PIT weekly industry revenue/profit acceleration breadth states."""
from __future__ import annotations
import argparse,json
import numpy as np,pandas as pd
from experiments.build_industry_revision_diffusion_states import members_at
from experiments.weekly_industry_cycle import weekly_last_sessions
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.research.combination import repair_point_in_time_size
def load_financials(path):
 x=pd.read_csv(path,dtype={"ts_code":str,"ann_date":str,"end_date":str});x["Symbol"]=x.ts_code.str[:6];x.ann_date=pd.to_datetime(x.ann_date,errors="coerce");x.end_date=pd.to_datetime(x.end_date,errors="coerce");x["period_index"]=x.end_date.dt.year*4+x.end_date.dt.quarter
 for c in ["tr_yoy","netprofit_yoy","update_flag"]:x[c]=pd.to_numeric(x[c],errors="coerce")
 return x.dropna(subset=["ann_date","end_date","period_index"]).sort_values(["ann_date","Symbol","period_index","update_flag"])
def snapshot(data,day):
 v=data[data.ann_date<=day].drop_duplicates(["Symbol","period_index"],keep="last");cur=v.sort_values(["Symbol","period_index"]).drop_duplicates("Symbol",keep="last")[["Symbol","period_index","end_date","tr_yoy","netprofit_yoy"]];prev=v[["Symbol","period_index","tr_yoy","netprofit_yoy"]].rename(columns={"period_index":"prev_index","tr_yoy":"prev_tr","netprofit_yoy":"prev_np"});older=v[["Symbol","period_index","tr_yoy","netprofit_yoy"]].rename(columns={"period_index":"older_index","tr_yoy":"older_tr","netprofit_yoy":"older_np"});cur=cur.copy();cur["prev_index"]=cur.period_index-1;cur["older_index"]=cur.period_index-2;return cur.merge(prev,on=["Symbol","prev_index"],how="left").merge(older,on=["Symbol","older_index"],how="left")
def run(members_path,financials_path,start,end,states_path,event_states_path,waves_path):
 m=pd.read_csv(members_path,dtype=str);m["Symbol"]=m.ts_code.str[:6];m["in_date"]=pd.to_datetime(m.in_date,errors="coerce");m["out_date"]=pd.to_datetime(m.out_date,errors="coerce");f=load_financials(financials_path);cfg=Config();con=connect(cfg,read_only=True)
 try:built=load_or_build_panel(cfg,"2016-01-01",end,con=con)
 finally:con.close()
 p=repair_point_in_time_size(built.df);p.TradingDay=pd.to_datetime(p.TradingDay);adv=p.groupby("TradingDay").adv20.rank(pct=True,method="first");p["practical"]=(~p.is_st.fillna(True))&(~p.suspended.fillna(True))&(p.age>=252)&(p.Close>=5)&(p.Volume>0)&p.CircMV.notna()&(adv>.5);sessions=sorted(p.TradingDay.drop_duplicates());weeks=[d for d in weekly_last_sessions(sessions) if pd.Timestamp(start)<=d<=pd.Timestamp(end)];rows=[]
 for day in weeks:
  mem=members_at(m,day);base=p[(p.TradingDay==day)&p.practical&p.Symbol.isin(mem.Symbol)].merge(mem[["Symbol","l1_name","l2_name"]],on="Symbol",how="inner");universe=pd.concat([base.assign(industry=base.l1_name),base[base.l2_name.eq("半导体")].assign(industry="半导体")],ignore_index=True);snap=snapshot(f,day)
  for industry,b in universe.groupby("industry"):
   joined=b[["Symbol"]].merge(snap,on="Symbol",how="inner").dropna(subset=["tr_yoy","netprofit_yoy","prev_tr","prev_np"])
   if len(joined):
    counts=joined.groupby(["period_index","end_date"]).size().sort_values();period,end_date=counts.index[-1];valid=joined[joined.period_index.eq(period)].copy()
   else:period=np.nan;end_date=pd.NaT;valid=joined.copy()
   valid["tr_acc"]=valid.tr_yoy-valid.prev_tr;valid["np_acc"]=valid.netprofit_yoy-valid.prev_np;valid["dual"]=valid.tr_acc.gt(0)&valid.np_acc.gt(0);previous=valid.dropna(subset=["older_tr","older_np"]);previous_dual=(previous.prev_tr.gt(previous.older_tr)&previous.prev_np.gt(previous.older_np)).mean() if len(previous) else np.nan;valid["score"]=valid.tr_acc.rank(pct=True)+valid.np_acc.rank(pct=True);top=valid[valid.dual].sort_values(["score","Symbol"],ascending=[False,True]).head(10).Symbol.tolist();breadth=float(valid.dual.mean()) if len(valid) else np.nan;tradable=b.Symbol.nunique();rows.append({"decision_date":day,"industry":industry,"report_period":end_date,"tradable_count":tradable,"valid_count":len(valid),"coverage":len(valid)/tradable if tradable else 0,"dual_positive_count":int(valid.dual.sum()) if len(valid) else 0,"dual_breadth":breadth,"previous_period_breadth":float(previous_dual) if pd.notna(previous_dual) else np.nan,"top_symbols":json.dumps(top,ensure_ascii=False)})
 states=pd.DataFrame(rows).sort_values(["industry","decision_date"]);states["seed_condition"]=(states.valid_count>=10)&(states.coverage>=.30)&(states.dual_breadth>=.55)&((states.dual_breadth-states.previous_period_breadth)>=.10);session_index={d:i for i,d in enumerate(sessions)};records=[];events=[];waves=[]
 for industry,g in states.groupby("industry"):
  active=False;previous_seed=False;hold_fail=0;last_event=-10**9
  for row in g.itertuples(index=False):
   event=False
   if active:
    hold=row.dual_breadth>=.45;hold_fail=0 if hold else hold_fail+1
    if hold_fail>=2:active=False;status="NO-ENTRY"
    else:status="ENTER"
   elif row.seed_condition and previous_seed:
    active=True;hold_fail=0;status="ENTER";position=session_index.get(pd.Timestamp(row.decision_date),-10**9);event=position-last_event>40
    if event:last_event=position
   elif row.seed_condition:status="EARNINGS_SEED"
   elif row.valid_count<10 or row.coverage<.30:status="UNRESOLVED"
   else:status="NO-ENTRY"
   data={**row._asdict(),"status":status,"entry_event":event,"score":float(row.dual_breadth*100) if pd.notna(row.dual_breadth) else np.nan};records.append(data)
   if event:events.append({"decision_date":row.decision_date,"industry":industry,"score":data["score"],"entry_event":True,"top_symbols":row.top_symbols});waves.append({"sector":industry,"seed_date":row.decision_date,"diffusion_date":row.decision_date,"status":"EARNINGS_BREADTH"})
   previous_seed=bool(row.seed_condition)
 out=pd.DataFrame(records);out.to_csv(states_path,index=False,date_format="%Y-%m-%d");pd.DataFrame(events).to_csv(event_states_path,index=False,date_format="%Y-%m-%d");pd.DataFrame(waves).to_csv(waves_path,index=False,date_format="%Y-%m-%d");return {"panel_version":built.version_hash,"weeks":len(weeks),"rows":len(out),"events":len(events),"industries":out.industry.nunique(),"states":states_path,"event_states":event_states_path,"waves":waves_path}
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--members",default="overall/a-share-sw2021-members.csv");p.add_argument("--financials",default="overall/a-share-quarterly-statements-raw/fina_indicator_vip.csv");p.add_argument("--start",default="2018-01-05");p.add_argument("--end",default="2026-08-21");p.add_argument("--states",default="overall/a-share-industry-earnings-breadth-states.csv");p.add_argument("--event-states",default="overall/a-share-industry-earnings-breadth-event-states.csv");p.add_argument("--waves",default="overall/a-share-industry-earnings-breadth-waves.csv");a=p.parse_args(argv);print(json.dumps(run(a.members,a.financials,a.start,a.end,a.states,a.event_states,a.waves),ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
