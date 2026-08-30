"""Exploratory PIT validation of strong-H1/weak-price expectation gaps."""
from __future__ import annotations
import argparse,gc,json
from pathlib import Path
import numpy as np,pandas as pd
from experiments.run_analyst_revision import consensus_revisions,load_reports,json_clean
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.research.combination import repair_point_in_time_size
INDUSTRIES=("半导体","基础化工","医药生物");GROUPS=("expectation_gap","confirmed_leader","fundamental_strong");HORIZONS=(63,126,252);COST=.0031;SEED=20260829

def statement_latest(path,year,cutoff):
 d=pd.read_csv(path,dtype={"ts_code":str,"ann_date":str,"f_ann_date":str,"end_date":str});d=d[d.end_date.astype(str)==f"{year}0630"].copy();d["ann_date"]=pd.to_datetime(d.ann_date,errors="coerce");d["f_ann_date"]=pd.to_datetime(d.f_ann_date,errors="coerce") if "f_ann_date" in d else pd.NaT;d["visible"]=d.f_ann_date.fillna(d.ann_date);d=d[d.visible<=cutoff];d["update_flag"]=pd.to_numeric(d.update_flag,errors="coerce").fillna(0);d["Symbol"]=d.ts_code.str[:6];return d.sort_values(["Symbol","visible","update_flag"]).drop_duplicates("Symbol",keep="last")
def active_members(m,date):
 d=pd.Timestamp(date);x=m[(m.in_date<=d)&(m.out_date.isna()|(m.out_date>=d))&m.industry.ne("")&m.ts_code.str.endswith((".SH",".SZ"))&~m.name.astype(str).str.contains("ST",case=False)].copy();return x.sort_values(["Symbol","in_date"]).drop_duplicates("Symbol",keep="last")
def bootstrap_ci(values):
 x=np.asarray(values,float);rng=np.random.default_rng(SEED);means=[float(x[rng.integers(0,len(x),len(x))].mean()) for _ in range(2000)];return [float(np.quantile(means,.025)),float(np.quantile(means,.975))]
def summary(events,group,h):
 x=events[events[group]&events[f"active{h}"].notna()][["year","industry",f"active{h}"]].copy();v=x[f"active{h}"]
 if len(x)<5:return {"count":len(x),"insufficient":True}
 folds={name:{"count":len(f),"mean":float(f[f"active{h}"].mean()) if len(f) else 0.0} for name,a,b in (("2017-2019",2017,2019),("2020-2022",2020,2022),("2023-2025",2023,2025)) for f in [x[x.year.between(a,b)]]};trim=x[x[f"active{h}"]<=x[f"active{h}"].quantile(.95)][f"active{h}"]
 return {"count":len(x),"mean":float(v.mean()),"median":float(v.median()),"win_rate":float((v>0).mean()),"bootstrap95":bootstrap_ci(v),"trim_top5_mean":float(trim.mean()),"folds":folds,"years":{str(y):{"count":len(g),"mean":float(g[f"active{h}"].mean())} for y,g in x.groupby("year")},"industries":{i:{"count":len(g),"mean":float(g[f"active{h}"].mean())} for i,g in x.groupby("industry")}}
def run(raw_dir,members_path,reports_dir,start_year,end_year,end_date,ledger_path):
 m=pd.read_csv(members_path,dtype=str);m["Symbol"]=m.ts_code.str[:6];m["in_date"]=pd.to_datetime(m.in_date,errors="coerce");m["out_date"]=pd.to_datetime(m.out_date,errors="coerce");m["industry"]=np.select([m.l2_name.eq("半导体"),m.l1_name.eq("基础化工"),m.l1_name.eq("医药生物")],INDUSTRIES,default="")
 cfg=Config();con=connect(cfg,read_only=True)
 try:built=load_or_build_panel(cfg,"2015-01-01",end_date,con=con)
 finally:con.close()
 p=repair_point_in_time_size(built.df);p.TradingDay=pd.to_datetime(p.TradingDay);p=p.sort_values(["Symbol","TradingDay"]).reset_index(drop=True);g=p.groupby("Symbol",sort=False)
 p["ret63"]=p.adj_close/g.adj_close.shift(63)-1;p["ret20"]=p.adj_close/g.adj_close.shift(20)-1;p["ma20_ratio"]=p.adj_close/g.adj_close.transform(lambda s:s.rolling(20,min_periods=20).mean())-1
 for h in HORIZONS:p[f"fwd{h}"]=g.adj_open.shift(-(h+1))/g.adj_open.shift(-1)-1
 adv=p.groupby("TradingDay").adv20.rank(pct=True,method="first");p["practical"]=(~p.suspended.fillna(True))&(p.age>=252)&(p.Close>=5)&(p.Volume>0)&p.CircMV.notna()&(adv>.5)
 sessions=sorted(p.TradingDay.drop_duplicates());reports=load_reports(reports_dir);events=[];cohorts=[]
 for year in range(start_year,end_year+1):
  cutoff=pd.Timestamp(f"{year}-08-31");decision=next((d for d in sessions if d>cutoff),None)
  if decision is None:continue
  members=active_members(m,decision).rename(columns={"name":"member_name","industry":"study_industry"});day=p[(p.TradingDay==decision)&p.Symbol.isin(members.Symbol)].merge(members[["Symbol","member_name","study_industry"]],on="Symbol",how="inner");day["name"]=day.member_name;day["industry"]=day.study_industry;day=day[day.practical].copy();bench={h:day.groupby("industry")[f"fwd{h}"].mean() for h in HORIZONS}
  fina=statement_latest(str(Path(raw_dir)/"fina_indicator_vip.csv"),year,cutoff);income=statement_latest(str(Path(raw_dir)/"income_vip.csv"),year,cutoff);cash=statement_latest(str(Path(raw_dir)/"cashflow_vip.csv"),year,cutoff)
  fields=["Symbol","tr_yoy","netprofit_yoy","dt_netprofit_yoy","roe_waa","grossprofit_margin","ocf_yoy"];x=day.merge(fina[fields],on="Symbol",how="inner").merge(income[["Symbol","total_revenue","n_income_attr_p"]],on="Symbol",how="left").merge(cash[["Symbol","n_cashflow_act","c_pay_acq_const_fiolta"]],on="Symbol",how="left")
  for c in ["tr_yoy","netprofit_yoy","dt_netprofit_yoy","roe_waa","grossprofit_margin","ocf_yoy","total_revenue","n_income_attr_p","n_cashflow_act","c_pay_acq_const_fiolta"]:x[c]=pd.to_numeric(x[c],errors="coerce")
  metrics=["tr_yoy","netprofit_yoy","dt_netprofit_yoy","roe_waa","ocf_yoy"]
  complete=x.dropna(subset=metrics).copy()
  for c in metrics:complete[c+"_pct"]=complete.groupby("industry")[c].rank(pct=True,method="average")
  complete["performance_score"]=complete[[c+"_pct" for c in metrics]].mean(axis=1);eligible=complete[(complete.tr_yoy>0)&(complete.netprofit_yoy>0)&(complete.dt_netprofit_yoy>0)&(complete.n_income_attr_p>0)].copy();eligible["fundamental_pct"]=eligible.groupby("industry").performance_score.rank(pct=True,method="average");day["price_pct"]=day.groupby("industry").ret63.rank(pct=True,method="average");day["size_pct"]=day.groupby("industry").CircMV.rank(pct=True,method="average");eligible=eligible.merge(day[["Symbol","price_pct","size_pct"]],on="Symbol",how="left")
  rev=consensus_revisions(reports,decision)[["Symbol","revision","current_count"]];eligible=eligible.merge(rev,on="Symbol",how="left");eligible["revision_pct"]=eligible.groupby("industry").revision.rank(pct=True,method="average");eligible["score100"]=10+40*eligible.performance_score+20*(1-eligible.price_pct)+5*eligible.size_pct+15*eligible.revision_pct+5*(eligible.ret20>0)+5*(eligible.ma20_ratio>0);eligible.loc[eligible.revision.isna(),"score100"]=np.nan
  eligible["expectation_gap"]=(eligible.fundamental_pct>=.7)&(eligible.price_pct<=.3);eligible["confirmed_leader"]=(eligible.fundamental_pct>=.7)&(eligible.price_pct>=.7);eligible["fundamental_strong"]=eligible.fundamental_pct>=.7
  for group in GROUPS:eligible[group]&=eligible.groupby("industry")[group].transform("sum")>=5
  eligible["year"]=year;eligible["decision_date"]=decision;eligible["ocf_np_ratio"]=eligible.n_cashflow_act/eligible.n_income_attr_p;eligible["fcf_proxy"]=eligible.n_cashflow_act-eligible.c_pay_acq_const_fiolta
  for h in HORIZONS:eligible[f"active{h}"]=eligible[f"fwd{h}"]-eligible.industry.map(bench[h])-COST
  for industry,ig in eligible.groupby("industry"):
   cohorts.append({"year":year,"industry":industry,"eligible":len(ig),**{group:int(ig[group].sum()) for group in GROUPS}})
  events.append(eligible)
 out=pd.concat(events,ignore_index=True) if events else pd.DataFrame();out.to_csv(ledger_path,index=False,date_format="%Y-%m-%d");summaries={group:{str(h):summary(out,group,h) for h in HORIZONS} for group in GROUPS};eg=summaries["expectation_gap"]["126"];fs=summaries["fundamental_strong"]["126"];cl=summaries["confirmed_leader"]["126"]
 checks={"count":eg.get("count",0)>=30,"mean":eg.get("mean",-1)>=.03,"median":eg.get("median",-1)>0,"win":eg.get("win_rate",0)>.52,"folds":sum(v["mean"]>0 for v in eg.get("folds",{}).values())>=2,"bootstrap":eg.get("bootstrap95",[-1])[0]>0,"trim":eg.get("trim_top5_mean",-1)>0,"beats_fundamental":eg.get("mean",-1)>=fs.get("mean",999),"beats_leader":eg.get("mean",-1)>=cl.get("mean",999)};verdict="GO" if all(checks.values()) else ("MARGINAL" if eg.get("mean",-1)>0 else "NO-GO")
 return json_clean({"study":"a-share-three-industry-historical-validation-v1","authority":"exploratory_only_no_platform_prepare_operation","data":{"panel_version":built.version_hash,"years":[start_year,end_year],"events":len(out),"cohorts":cohorts},"summaries":summaries,"decision":{"verdict":verdict,"checks":checks},"limitations":["current sector thesis makes history non-virgin","source-bounded SW2021 membership","event-level T+1 open approximation, not formal Platform Backtest","no governance/official S2 authority"]})
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--raw",default="overall/a-share-historical-h1-raw");p.add_argument("--members",default="overall/a-share-sw2021-members.csv");p.add_argument("--reports",default="overall/a-share-report-rc-raw");p.add_argument("--start-year",type=int,default=2017);p.add_argument("--end-year",type=int,default=2024);p.add_argument("--end-date",default="2026-08-27");p.add_argument("--ledger",default="overall/a-share-three-industry-historical-events-preholdout.csv");p.add_argument("--out-json",default="overall/a-share-three-industry-historical-validation-preholdout.json");p.add_argument("--out-md",default="overall/a-share-three-industry-historical-validation-preholdout.md");a=p.parse_args(argv);payload=run(a.raw,a.members,a.reports,a.start_year,a.end_year,a.end_date,a.ledger);Path(a.out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n");d=payload["decision"];e=payload["summaries"]["expectation_gap"]["126"];text=f"# 三行业历史预期差验证\n\n- years: {a.start_year}-{a.end_year}\n- verdict: **{d['verdict']}**\n- 6m count/mean/median/win: {e.get('count',0)} / {e.get('mean',0):.2%} / {e.get('median',0):.2%} / {e.get('win_rate',0):.2%}\n";Path(a.out_md).write_text(text);print(text);return 0
if __name__=="__main__":raise SystemExit(main())
