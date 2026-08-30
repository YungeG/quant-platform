"""Build volume-only dynamic leader/follower states inside every sector."""
from __future__ import annotations
import argparse,json,math
import numpy as np,pandas as pd
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.research.combination import repair_point_in_time_size
def entropy(excess):
 values=np.asarray([v for v in excess if pd.notna(v) and v>0],float)
 if len(values)<=1:return 0.0
 weights=values/values.sum();return float(-(weights*np.log(weights)).sum()/math.log(len(weights)))
def run(members_path,start,end,panel_path,focus_path):
 m=pd.read_csv(members_path,dtype=str);m["Symbol"]=m.ts_code.str[:6];m["in_date"]=pd.to_datetime(m.in_date,errors="coerce");m["out_date"]=pd.to_datetime(m.out_date,errors="coerce");cfg=Config();con=connect(cfg,read_only=True)
 try:built=load_or_build_panel(cfg,"2023-12-01",end,con=con)
 finally:con.close()
 p=repair_point_in_time_size(built.df);p.TradingDay=pd.to_datetime(p.TradingDay);p=p[p.TradingDay.between(start,end)&(~p.is_st.fillna(True))&(~p.suspended.fillna(True))&(p.age>=252)&(p.Close>=5)&(p.Volume>0)&p.CircMV.notna()].sort_values(["Symbol","TradingDay"]).copy();p["turnover_proxy"]=p.Amount/p.CircMV.replace(0,np.nan);g=p.groupby("Symbol",sort=False);p["turnover_median20"]=g.turnover_proxy.transform(lambda s:s.rolling(20,min_periods=20).median());p["activity_ratio"]=p.turnover_proxy/p.turnover_median20;joined=p.merge(m[["Symbol","name","l1_name","l2_name","in_date","out_date"]],on="Symbol",how="inner");joined=joined[(joined.TradingDay>=joined.in_date)&(joined.out_date.isna()|(joined.TradingDay<=joined.out_date))&~joined.name.astype(str).str.contains("ST",case=False)];x=pd.concat([joined.assign(sector=joined.l1_name),joined[joined.l2_name.eq("半导体")].assign(sector="半导体")],ignore_index=True).sort_values(["sector","Symbol","TradingDay"]);x["activity_pct120"]=x.groupby(["sector","Symbol"])["activity_ratio"].transform(lambda s:s.rolling(120,min_periods=120).rank(pct=True));x["abnormal"]=(x.activity_ratio>=1.5)&(x.activity_pct120>=.9);groups=x.groupby(["sector","Symbol"],sort=False);x["abnormal_3count"]=groups.abnormal.transform(lambda s:s.rolling(3,min_periods=1).sum());x["prior5_count"]=groups.abnormal.transform(lambda s:s.shift(1).rolling(5,min_periods=1).sum());x["persistent_leader"]=x.abnormal_3count>=2;x["new_entrant"]=x.abnormal&(x.prior5_count.fillna(0)==0);x["excess_activity"]=np.where(x.abnormal,x.activity_ratio-1,0.0);rows=[]
 for sector,s in x.groupby("sector"):
  previous=set()
  for day,d in s.groupby("TradingDay"):
   valid=d[d.activity_pct120.notna()];abnormal=d[d.abnormal];current=set(abnormal.Symbol);union=current|previous;jaccard=len(current&previous)/len(union) if union else 0.0;excess=abnormal.excess_activity;total=float(excess.sum());focus=d[d.persistent_leader|d.new_entrant].sort_values(["activity_ratio","Symbol"],ascending=[False,True]).head(20);rows.append({"trade_date":day,"sector":sector,"eligible_count":len(valid),"abnormal_count":len(abnormal),"abnormal_breadth":len(abnormal)/len(valid) if len(valid) else np.nan,"new_entrant_count":int(d.new_entrant.sum()),"new_entrant_rate":float(d.new_entrant.sum()/len(valid)) if len(valid) else np.nan,"top5_excess_concentration":float(excess.nlargest(5).sum()/total) if total>0 else 0.0,"focus_persistence":jaccard,"activity_entropy":entropy(excess),"abnormal_symbols":json.dumps(sorted(current),ensure_ascii=False),"focus_symbols":json.dumps(focus.Symbol.tolist(),ensure_ascii=False)});previous=current
 panel=pd.DataFrame(rows).sort_values(["sector","trade_date"])
 for column in ["abnormal_breadth","new_entrant_rate","top5_excess_concentration","focus_persistence","activity_entropy"]:panel[column+"_pct120"]=panel.groupby("sector")[column].transform(lambda s:s.rolling(120,min_periods=120).rank(pct=True))
 panel.to_csv(panel_path,index=False,date_format="%Y-%m-%d");focus=x[(x.TradingDay.dt.year==2026)&(x.abnormal|x.persistent_leader|x.new_entrant)][["TradingDay","sector","Symbol","name","activity_ratio","activity_pct120","abnormal","persistent_leader","new_entrant"]].rename(columns={"TradingDay":"trade_date"});focus.to_csv(focus_path,index=False,date_format="%Y-%m-%d");return {"panel_version":built.version_hash,"rows":len(panel),"focus_rows":len(focus),"sectors":panel.sector.nunique(),"start":str(panel.trade_date.min().date()),"end":str(panel.trade_date.max().date()),"panel":panel_path,"focus":focus_path}
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--members",default="overall/a-share-sw2021-members.csv");p.add_argument("--start",default="2024-01-01");p.add_argument("--end",default="2026-08-27");p.add_argument("--panel",default="overall/a-share-volume-diffusion-panel.csv");p.add_argument("--focus",default="overall/a-share-2026-volume-dynamic-focus.csv");a=p.parse_args(argv);print(json.dumps(run(a.members,a.start,a.end,a.panel,a.focus),ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
