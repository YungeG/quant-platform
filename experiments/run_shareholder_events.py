"""Evaluate first buyback implementation and important-holder net purchase events."""
from __future__ import annotations
import argparse,gc,json
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from experiments.run_lowturn_livermore import _clean
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.research.combination import repair_point_in_time_size
COST=.0031;FOLDS=(("2017-2019","2017-01-01","2019-12-31"),("2020-2022","2020-01-01","2022-12-31"),("2023-2026","2023-01-01","2026-12-31"))

def repurchase_events(path):
 d=pd.read_csv(path,dtype={"ts_code":str,"ann_date":str});d["ann_date"]=pd.to_datetime(d.ann_date,errors="coerce");d["amount"]=pd.to_numeric(d.amount,errors="coerce");d["Symbol"]=d.ts_code.str[:6];out=[]
 for s,g in d.dropna(subset=["ann_date"]).sort_values(["Symbol","ann_date"]).groupby("Symbol"):
  plan=None;used=False
  for r in g.itertuples(index=False):
   if r.proc=="预案":plan=r.ann_date;used=False
   elif r.proc=="实施" and plan is not None and not used and r.ann_date>=plan:
    out.append({"Symbol":s,"ann_date":r.ann_date,"amount":r.amount,"plan_date":plan});used=True
 return pd.DataFrame(out)

def holder_events(path):
 d=pd.read_csv(path,dtype={"ts_code":str,"ann_date":str});d["ann_date"]=pd.to_datetime(d.ann_date,errors="coerce");d["change_ratio"]=pd.to_numeric(d.change_ratio,errors="coerce");d=d[d.holder_type.isin(["G","P"])].dropna(subset=["ann_date","change_ratio"]);d["signed_ratio"]=np.where(d.in_de=="IN",d.change_ratio,-d.change_ratio);d["Symbol"]=d.ts_code.str[:6]
 return d.groupby(["Symbol","ann_date"],as_index=False).agg(signal=("signed_ratio","sum"),record_count=("signed_ratio","count"))

def attach(events,end,signal_col):
 cfg=Config();con=connect(cfg,read_only=True)
 try:built=load_or_build_panel(cfg,"2014-11-27",end,con=con)
 finally:con.close()
 p=repair_point_in_time_size(built.df);p.TradingDay=pd.to_datetime(p.TradingDay);p=p.sort_values(["Symbol","TradingDay"]).reset_index(drop=True);g=p.groupby("Symbol",sort=False)
 for h in (5,20,60):p[f"_fwd{h}"]=g.adj_open.shift(-(h+1))/g.adj_open.shift(-1)-1
 adv=p.groupby("TradingDay").adv20.rank(pct=True,method="first");p["practical"]=(~p.suspended.fillna(True))&(p.age>=252)&(p.Close>=5)&(p.Volume>0)&p.CircMV.notna()&(adv>.5);p["size_rank"]=p.groupby("TradingDay").CircMV.rank(method="first",ascending=False)
 sessions=sorted(p.TradingDay.drop_duplicates());pos=np.searchsorted(np.array(sessions,dtype="datetime64[ns]"),events.ann_date.to_numpy(dtype="datetime64[ns]"),side="right")-1;events=events.copy();events["signal_date"]=[sessions[i] if i>=0 else pd.NaT for i in pos]
 ctx=p[["TradingDay","Symbol","Close","CircMV","practical","size_rank","_fwd5","_fwd20","_fwd60"]];events=events.merge(ctx,left_on=["signal_date","Symbol"],right_on=["TradingDay","Symbol"],how="left");events=events[events.practical.fillna(False)&(events.size_rank<=500)].copy()
 top=p[p.practical&(p.size_rank<=500)];bench={h:top.groupby("TradingDay")[f"_fwd{h}"].mean() for h in (5,20,60)}
 if signal_col=="amount":events["signal"]=events.amount/(events.CircMV*10000)
 for h in (5,20,60):events[f"active{h}"]=events[f"_fwd{h}"]-events.signal_date.map(bench[h])-COST
 meta={"panel_version":built.version_hash};del p,top;gc.collect();return events,meta

def bootstrap(top):
 clusters=[g.active20.dropna().to_numpy(float) for _,g in top.groupby(top.ann_date.dt.to_period("M")) if g.active20.notna().any()];rng=np.random.default_rng(20260827);vals=[]
 for _ in range(2000):vals.append(float(np.concatenate([clusters[i] for i in rng.integers(0,len(clusters),len(clusters))]).mean()))
 return [float(np.quantile(vals,.025)),float(np.quantile(vals,.975))]

def evaluate(e):
 x=e.dropna(subset=["signal","active20"]);t=spearmanr(x.signal,x.active20);q=float(x.signal.quantile(.8));top=x[x.signal>=q];folds={}
 for name,start,end in FOLDS:
  f=top[top.ann_date.between(start,end)];folds[name]={"count":len(f),"mean":float(f.active20.mean()) if len(f) else 0.0,"median":float(f.active20.median()) if len(f) else 0.0,"win":float((f.active20>0).mean()) if len(f) else 0.0}
 stats={"count":len(top),"mean5":float(top.active5.mean()),"mean20":float(top.active20.mean()),"mean60":float(top.active60.mean()),"median20":float(top.active20.median()),"win20":float((top.active20>0).mean()),"bootstrap95":bootstrap(top),"folds":folds};checks={"count":len(x)>=500,"rho":float(t.statistic)>=.02,"p":float(t.pvalue)<.05,"mean":stats["mean20"]>=.01,"median":stats["median20"]>0,"win":stats["win20"]>.52,"folds":sum(f["mean"]>0 for f in folds.values())>=2,"bootstrap":stats["bootstrap95"][0]>0};verdict="GO" if all(checks.values()) else ("MARGINAL" if float(t.statistic)>0 and stats["mean20"]>0 else "NO-GO");return {"verdict":verdict,"checks":checks,"all":{"count":len(x),"rho":float(t.statistic),"p":float(t.pvalue)},"top":stats,"q80":q}

def run(raw,end):
 rep=repurchase_events(str(Path(raw)/"repurchase.csv"));hold=holder_events(str(Path(raw)/"stk_holdertrade.csv"));rep,meta=attach(rep,end,"amount");hold,_=attach(hold,end,"signal");return _clean({"study":"a-share-shareholder-events-v1","data":{**meta,"repurchase_events":len(rep),"holder_events":len(hold)},"repurchase":evaluate(rep),"holdertrade":evaluate(hold)})

def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--raw",default="overall/a-share-shareholder-events-raw");p.add_argument("--end",default="2026-08-26");p.add_argument("--out-json",default="overall/a-share-shareholder-events.json");p.add_argument("--out-md",default="overall/a-share-shareholder-events.md");a=p.parse_args(argv);payload=run(a.raw,a.end);Path(a.out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");r=payload["repurchase"];h=payload["holdertrade"];text=f"# A股回购与股东增持事件结果\n\n- repurchase: **{r['verdict']}**, rho {r['all']['rho']:.3f}, top20 {r['top']['mean20']:.2%}\n- holdertrade: **{h['verdict']}**, rho {h['all']['rho']:.3f}, top20 {h['top']['mean20']:.2%}\n";Path(a.out_md).write_text(text,encoding="utf-8");print(text);return 0
if __name__=="__main__":raise SystemExit(main())
