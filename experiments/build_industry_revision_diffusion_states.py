"""Build weekly PIT industry analyst-revision diffusion states and targets."""
from __future__ import annotations
import argparse,json
import numpy as np,pandas as pd
from experiments.run_analyst_revision import consensus_revisions,load_reports
from experiments.weekly_industry_cycle import weekly_last_sessions
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.research.combination import repair_point_in_time_size
def members_at(m,day):return m[(m.in_date<=day)&(m.out_date.isna()|(m.out_date>=day))&m.ts_code.str.endswith((".SH",".SZ"))&~m.name.astype(str).str.contains("ST",case=False)].sort_values(["Symbol","in_date"]).drop_duplicates("Symbol",keep="last")
def run(members_path,reports_dir,start,end,states_path,event_states_path,waves_path):
 m=pd.read_csv(members_path,dtype=str);m["Symbol"]=m.ts_code.str[:6];m["in_date"]=pd.to_datetime(m.in_date,errors="coerce");m["out_date"]=pd.to_datetime(m.out_date,errors="coerce");cfg=Config();con=connect(cfg,read_only=True)
 try:built=load_or_build_panel(cfg,"2016-01-01",end,con=con)
 finally:con.close()
 p=repair_point_in_time_size(built.df);p.TradingDay=pd.to_datetime(p.TradingDay);adv=p.groupby("TradingDay").adv20.rank(pct=True,method="first");p["practical"]=(~p.is_st.fillna(True))&(~p.suspended.fillna(True))&(p.age>=252)&(p.Close>=5)&(p.Volume>0)&p.CircMV.notna()&(adv>.5);sessions=sorted(p.TradingDay.drop_duplicates());weeks=[d for d in weekly_last_sessions(sessions) if pd.Timestamp(start)<=d<=pd.Timestamp(end)];reports=load_reports(reports_dir);rows=[]
 for day in weeks:
  mem=members_at(m,day);base=p[(p.TradingDay==day)&p.practical&p.Symbol.isin(mem.Symbol)].merge(mem[["Symbol","l1_name","l2_name","name"]],on="Symbol",how="inner");l1=base.assign(industry=base.l1_name);semi=base[base.l2_name.eq("半导体")].assign(industry="半导体");universe=pd.concat([l1,semi],ignore_index=True);revision=consensus_revisions(reports,day)
  for industry,b in universe.groupby("industry"):
   r=b[["Symbol"]].merge(revision,on="Symbol",how="inner");valid=r.dropna(subset=["revision"]);positive=valid[valid.revision>0].sort_values(["revision","paired_count","Symbol"],ascending=[False,False,True]);rows.append({"decision_date":day,"industry":industry,"tradable_count":b.Symbol.nunique(),"valid_count":len(valid),"coverage":len(valid)/b.Symbol.nunique() if b.Symbol.nunique() else 0,"positive_count":len(positive),"positive_breadth":float((valid.revision>0).mean()) if len(valid) else np.nan,"median_revision":float(valid.revision.median()) if len(valid) else np.nan,"top_symbols":json.dumps(positive.head(10).Symbol.tolist(),ensure_ascii=False)})
 states=pd.DataFrame(rows).sort_values(["industry","decision_date"]);states["breadth_lag4"]=states.groupby("industry").positive_breadth.shift(4);states["seed_condition"]=(states.valid_count>=10)&(states.coverage>=.30)&(states.positive_breadth>=.60)&(states.median_revision>0)&((states.positive_breadth-states.breadth_lag4)>=.10);session_index={d:i for i,d in enumerate(sessions)};records=[];events=[];waves=[]
 for industry,g in states.groupby("industry"):
  active=False;previous=False;hold_fail=0;last_event=-10**9
  for row in g.itertuples(index=False):
   event=False
   if active:
    hold=row.positive_breadth>=.50 and row.median_revision>=0;hold_fail=0 if hold else hold_fail+1
    if hold_fail>=2:active=False;status="NO-ENTRY"
    else:status="ENTER"
   elif row.seed_condition and previous:
    active=True;hold_fail=0;status="ENTER";position=session_index.get(pd.Timestamp(row.decision_date),-10**9);event=position-last_event>40
    if event:last_event=position
   elif row.seed_condition:status="REVISION_SEED"
   elif row.valid_count<10 or row.coverage<.30:status="UNRESOLVED"
   else:status="NO-ENTRY"
   data={**row._asdict(),"status":status,"entry_event":event,"score":float(row.positive_breadth*100) if pd.notna(row.positive_breadth) else np.nan};records.append(data)
   if event:events.append({"decision_date":row.decision_date,"industry":industry,"score":data["score"],"entry_event":True,"top_symbols":row.top_symbols});waves.append({"sector":industry,"seed_date":row.decision_date,"diffusion_date":row.decision_date,"status":"REVISION_DIFFUSION"})
   previous=bool(row.seed_condition)
 out=pd.DataFrame(records);out.to_csv(states_path,index=False,date_format="%Y-%m-%d");pd.DataFrame(events).to_csv(event_states_path,index=False,date_format="%Y-%m-%d");pd.DataFrame(waves).to_csv(waves_path,index=False,date_format="%Y-%m-%d");return {"panel_version":built.version_hash,"weeks":len(weeks),"rows":len(out),"events":len(events),"industries":out.industry.nunique(),"states":states_path,"event_states":event_states_path,"waves":waves_path}
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--members",default="overall/a-share-sw2021-members.csv");p.add_argument("--reports",default="overall/a-share-report-rc-raw");p.add_argument("--start",default="2017-01-06");p.add_argument("--end",default="2026-08-21");p.add_argument("--states",default="overall/a-share-industry-revision-diffusion-states.csv");p.add_argument("--event-states",default="overall/a-share-industry-revision-event-states.csv");p.add_argument("--waves",default="overall/a-share-industry-revision-waves.csv");a=p.parse_args(argv);print(json.dumps(run(a.members,a.reports,a.start,a.end,a.states,a.event_states,a.waves),ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
