"""Build weekly necessary-condition states for consumer-health and manufacturing-tech families."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from experiments.weekly_industry_cycle import weekly_last_sessions
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.research.combination import repair_point_in_time_size
CONSUMER={"医药生物","食品饮料","家用电器","美容护理","社会服务","商贸零售"};MANUFACTURING={"电子","计算机","通信","汽车","机械设备","电力设备","国防军工"}
def balance_source(path):
 d=pd.read_csv(path,dtype={"ts_code":str,"ann_date":str,"f_ann_date":str,"end_date":str});d["Symbol"]=d.ts_code.str[:6];d["ann_date"]=pd.to_datetime(d.ann_date,errors="coerce");d["f_ann_date"]=pd.to_datetime(d.f_ann_date,errors="coerce");d["visible"]=d.f_ann_date.fillna(d.ann_date);d["end_date"]=pd.to_datetime(d.end_date,errors="coerce");d["update_flag"]=pd.to_numeric(d.update_flag,errors="coerce").fillna(0);fields=["accounts_receiv","inventories","total_assets"]
 for field in fields:d[field]=pd.to_numeric(d[field],errors="coerce")
 return d[["Symbol","end_date","visible","update_flag",*fields]].dropna(subset=["end_date","visible"]).drop_duplicates()
def balance_snapshot(con,day):return con.execute("""with b as (select * exclude(rn) from (select *,row_number() over(partition by Symbol,end_date order by visible desc,update_flag desc) rn from balance_source where visible<=?) where rn=1) select * from b qualify row_number() over(partition by Symbol order by end_date desc)=1""",[day]).df()
def members_at(m,day):return m[(m.in_date<=day)&(m.out_date.isna()|(m.out_date>=day))&m.l1_name.isin(MANUFACTURING)&m.ts_code.str.endswith((".SH",".SZ"))&~m.name.astype(str).str.contains("ST",case=False)].sort_values(["Symbol","in_date"]).drop_duplicates("Symbol",keep="last")
def run(v1_states,balance_path,members_path,start,end,out_path):
 states=pd.read_csv(v1_states);states["decision_date"]=pd.to_datetime(states.decision_date);states=states[states.decision_date.between(start,end)].copy();m=pd.read_csv(members_path,dtype=str);m["Symbol"]=m.ts_code.str[:6];m["in_date"]=pd.to_datetime(m.in_date,errors="coerce");m["out_date"]=pd.to_datetime(m.out_date,errors="coerce");cfg=Config();con=connect(cfg,read_only=True)
 try:
  built=load_or_build_panel(cfg,"2016-01-01",end,con=con);p=repair_point_in_time_size(built.df);p.TradingDay=pd.to_datetime(p.TradingDay);p=p.sort_values(["Symbol","TradingDay"]);adv=p.groupby("TradingDay").adv20.rank(pct=True,method="first");p["practical"]=(~p.is_st.fillna(True))&(~p.suspended.fillna(True))&(p.age>=252)&(p.Close>=5)&(p.Volume>0)&p.CircMV.notna()&(adv>.5);con.register("balance_source",balance_source(balance_path));balance_rows=[]
  for day in sorted(states.decision_date.unique()):
   mem=members_at(m,pd.Timestamp(day)).rename(columns={"l1_name":"study_industry"});tradable=p[(p.TradingDay==day)&p.practical&p.Symbol.isin(mem.Symbol)].merge(mem[["Symbol","study_industry"]],on="Symbol",how="inner");tradable["industry"]=tradable.study_industry;b=tradable.merge(balance_snapshot(con,pd.Timestamp(day).date()),on="Symbol",how="left");b["inventory_assets"]=b.inventories/b.total_assets;b["receivables_assets"]=b.accounts_receiv/b.total_assets
   for industry,g in b.groupby("industry"):
    valid=g.dropna(subset=["inventory_assets","receivables_assets"]);balance_rows.append({"decision_date":day,"industry":industry,"balance_coverage":len(valid)/len(g) if len(g) else 0,"inventory_assets_median":float(valid.inventory_assets.median()) if len(valid) else np.nan,"receivables_assets_median":float(valid.receivables_assets.median()) if len(valid) else np.nan})
 finally:con.close()
 states=states.merge(pd.DataFrame(balance_rows),on=["decision_date","industry"],how="left");states["family"]=np.select([states.industry.isin(CONSUMER),states.industry.isin(MANUFACTURING)],["consumer_health","manufacturing_tech"],default="unsupported")
 for column,lag in [("triple_growth_breadth",13),("roe_median",13),("ocf_positive_breadth",13),("fcf_positive_breadth",13),("positive_revision_breadth",4),("inventory_assets_median",13),("receivables_assets_median",13),("relative20",1),("ma20_breadth",1)]:states[column+f"_lag{lag}"]=states.groupby("industry")[column].shift(lag)
 states["consumer_operating_gate"]=(states.triple_growth_breadth>states.triple_growth_breadth_lag13)&(states.roe_median>states.roe_median_lag13)&(states.ocf_positive_breadth>=states.ocf_positive_breadth_lag13);states["manufacturing_operating_gate"]=(states.triple_growth_breadth>states.triple_growth_breadth_lag13)&(states.fcf_positive_breadth>=states.fcf_positive_breadth_lag13)&(states.inventory_assets_median<states.inventory_assets_median_lag13)&(states.receivables_assets_median<=states.receivables_assets_median_lag13);states["operating_gate"]=np.where(states.family=="consumer_health",states.consumer_operating_gate,np.where(states.family=="manufacturing_tech",states.manufacturing_operating_gate,False));states["expectation_gate"]=(states.positive_revision_breadth>states.positive_revision_breadth_lag4)&(states.median_revision>0);states["price_gate"]=(states.relative20>0)&(states.ma20_breadth>.5)&(states.relative20_lag1>0)&(states.ma20_breadth_lag1>.5);complete=states.data_complete.astype(str).str.lower().eq("true");states["risk_gate"]=complete&(states.tradable_count>=10)&(states.pe_median_pct<=.8)&((states.family!="manufacturing_tech")|(states.balance_coverage>=.6));states["all_entry_gates"]=states.operating_gate&states.expectation_gate&states.price_gate&states.risk_gate;states["hold_condition"]=(states.median_revision>0)&((states.relative20>0)|(states.ma20_breadth>.5));sessions=sorted(p.TradingDay.drop_duplicates());session_index={d:i for i,d in enumerate(sessions)};records=[]
 for industry,g in states.sort_values("decision_date").groupby("industry"):
  active=False;hold_fail=0;last_event=-10**9
  for row in g.itertuples(index=False):
   event=False
   if row.family=="unsupported" or not row.risk_gate:status="UNRESOLVED";active=False;hold_fail=0
   elif active:
    hold_fail=0 if row.hold_condition else hold_fail+1
    if hold_fail>=2:active=False;status="NO-ENTRY"
    else:status="ENTER"
   elif row.all_entry_gates:
    active=True;hold_fail=0;status="ENTER";position=session_index.get(pd.Timestamp(row.decision_date),-10**9);event=position-last_event>40
    if event:last_event=position
   elif row.operating_gate and row.expectation_gate:status="EXPECTATION_CONFIRMED"
   elif row.operating_gate:status="IMPROVING"
   else:status="DORMANT"
   values=row._asdict();values.update({"status":status,"entry_event":event,"score":100.0 if row.all_entry_gates else 25.0*sum([bool(row.operating_gate),bool(row.expectation_gate),bool(row.price_gate),bool(row.risk_gate)])});records.append(values)
 out=pd.DataFrame(records);out.to_csv(out_path,index=False,date_format="%Y-%m-%d");return {"rows":len(out),"events":int(out.entry_event.sum()),"families":out.family.value_counts().to_dict(),"output":out_path}
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--v1-states",default="overall/a-share-weekly-industry-states.csv");p.add_argument("--balance",default="overall/a-share-quarterly-balance-raw/balancesheet_vip.csv");p.add_argument("--members",default="overall/a-share-sw2021-members.csv");p.add_argument("--start",default="2017-01-06");p.add_argument("--end",default="2025-12-31");p.add_argument("--out",default="overall/a-share-industry-cycle-family-v2-states.csv");a=p.parse_args(argv);print(json.dumps(run(a.v1_states,a.balance,a.members,a.start,a.end,a.out),ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
