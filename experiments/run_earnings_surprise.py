"""Evaluate annual actual EPS versus pre-announcement analyst consensus."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from experiments.run_analyst_revision import load_reports
from experiments.run_lowturn_livermore import _clean
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.research.combination import repair_point_in_time_size


COST=0.0031
FOLDS=(("2017-2019","2017-01-01","2019-12-31"),("2020-2022","2020-01-01","2022-12-31"),("2023-2025","2023-01-01","2025-12-31"))


def load_actuals(path:str)->pd.DataFrame:
    a=pd.read_csv(path,dtype={"ts_code":str,"ann_date":str,"end_date":str});a["Symbol"]=a.ts_code.str[:6];a["ann_date"]=pd.to_datetime(a.ann_date,errors="coerce");a["end_date"]=pd.to_datetime(a.end_date,errors="coerce");a["eps"]=pd.to_numeric(a.eps,errors="coerce");a["update_flag"]=pd.to_numeric(a.update_flag,errors="coerce")
    a=a.dropna(subset=["ann_date","end_date","eps"]);a["year"]=a.end_date.dt.year
    first_dates=a.groupby(["Symbol","year"]).ann_date.transform("min");a=a[a.ann_date==first_dates].sort_values(["Symbol","year","update_flag"]).drop_duplicates(["Symbol","year"],keep="last")
    return a[(a.year>=2016)&(a.year<=2025)]


def match_consensus(actuals:pd.DataFrame,reports:pd.DataFrame)->pd.DataFrame:
    groups={(s,q):g for (s,q),g in reports.groupby(["Symbol","quarter"])};rows=[]
    for r in actuals.itertuples(index=False):
        quarter=f"{int(r.year)}Q4";g=groups.get((r.Symbol,quarter))
        if g is None:continue
        cutoff=pd.Timestamp(r.ann_date)-pd.Timedelta(days=1);window=g[g.report_date.between(cutoff-pd.Timedelta(days=180),cutoff)].sort_values(["org_name","report_date","create_time"]);latest=window.drop_duplicates("org_name",keep="last")
        if len(latest)<3:continue
        consensus=float(latest.eps.median());dispersion=float(latest.eps.std(ddof=1)) if len(latest)>1 else 0.0
        rows.append({"Symbol":r.Symbol,"ann_date":r.ann_date,"end_date":r.end_date,"actual_eps":float(r.eps),"consensus_eps":consensus,"consensus_count":len(latest),"consensus_dispersion":dispersion})
    return pd.DataFrame(rows)


def attach_returns(events:pd.DataFrame,end:str)->tuple[pd.DataFrame,dict]:
    cfg=Config();con=connect(cfg,read_only=True)
    try:built=load_or_build_panel(cfg,"2014-11-27",end,con=con)
    finally:con.close()
    p=repair_point_in_time_size(built.df);p["TradingDay"]=pd.to_datetime(p.TradingDay);p=p.sort_values(["Symbol","TradingDay"]).reset_index(drop=True);grp=p.groupby("Symbol",sort=False)
    for h in (5,20,60):p[f"_fwd{h}"]=grp.adj_open.shift(-(h+1))/grp.adj_open.shift(-1)-1
    adv=p.groupby("TradingDay").adv20.rank(pct=True,method="first");p["practical"]=(~p.suspended.fillna(True))&(p.age>=252)&(p.Close>=5)&(p.Volume>0)&p.CircMV.notna()&(adv>.5)
    sessions=sorted(p.TradingDay.drop_duplicates());positions=np.searchsorted(np.array(sessions,dtype="datetime64[ns]"),events.ann_date.to_numpy(dtype="datetime64[ns]"),side="right")-1;events=events.copy();events["signal_date"]=[sessions[i] if i>=0 else pd.NaT for i in positions]
    cols=["TradingDay","Symbol","Close","CircMV","practical","_fwd5","_fwd20","_fwd60"];ctx=p[cols];events=events.merge(ctx,left_on=["signal_date","Symbol"],right_on=["TradingDay","Symbol"],how="left")
    practical=p[p.practical].copy();practical["size_rank"]=practical.groupby("TradingDay").CircMV.rank(method="first",ascending=False);top=practical[practical.size_rank<=500]
    benchmarks={h:top.groupby("TradingDay")[f"_fwd{h}"].mean() for h in (5,20,60)}
    events=events[events.practical.fillna(False)&(events.CircMV.rank(pct=True).notna())].copy()
    # Exact top-500 membership at each signal date.
    ranks=p.groupby("TradingDay").CircMV.rank(method="first",ascending=False);p["_size_rank"]=ranks;rank_map=p.set_index(["TradingDay","Symbol"])["_size_rank"]
    events["size_rank"]=[rank_map.get((d,s),np.nan) for d,s in zip(events.signal_date,events.Symbol,strict=True)];events=events[events.size_rank<=500].copy()
    events["surprise_to_price"]=(events.actual_eps-events.consensus_eps)/events.Close
    for h in (5,20,60):events[f"benchmark{h}"]=events.signal_date.map(benchmarks[h]);events[f"active{h}"]=events[f"_fwd{h}"]-events[f"benchmark{h}"]-COST
    meta={"panel_version":built.version_hash,"panel_rows":len(p)};del p,practical,top;gc.collect();return events,meta


def cluster_bootstrap(values:pd.DataFrame)->list[float]:
    clusters=[g.active20.dropna().to_numpy(float) for _,g in values.groupby(values.ann_date.dt.to_period("M")) if g.active20.notna().any()];rng=np.random.default_rng(20260827);means=[]
    for _ in range(2000):
        sample=np.concatenate([clusters[i] for i in rng.integers(0,len(clusters),len(clusters))]);means.append(float(sample.mean()))
    return [float(np.quantile(means,.025)),float(np.quantile(means,.975))]


def evaluate(e:pd.DataFrame)->dict:
    clean=e.dropna(subset=["surprise_to_price","active20"]);test=spearmanr(clean.surprise_to_price,clean.active20);q80=float(clean.surprise_to_price.quantile(.8));q20=float(clean.surprise_to_price.quantile(.2));top=clean[clean.surprise_to_price>=q80];bottom=clean[clean.surprise_to_price<=q20]
    folds={}
    for name,start,end in FOLDS:
        x=top[top.ann_date.between(start,end)];folds[name]={"count":len(x),"mean_active20":float(x.active20.mean()) if len(x) else 0.0,"median_active20":float(x.active20.median()) if len(x) else 0.0,"win_rate":float((x.active20>0).mean()) if len(x) else 0.0}
    top_stats={"count":len(top),"mean_active5":float(top.active5.mean()),"mean_active20":float(top.active20.mean()),"mean_active60":float(top.active60.mean()),"median_active20":float(top.active20.median()),"win_rate20":float((top.active20>0).mean()),"cluster_bootstrap_95":cluster_bootstrap(top),"folds":folds}
    checks={"count":len(clean)>=500,"rho":float(test.statistic)>=.02,"p_value":float(test.pvalue)<.05,"top_mean":top_stats["mean_active20"]>=.01,"top_median":top_stats["median_active20"]>0,"top_win":top_stats["win_rate20"]>.52,"folds":sum(f["mean_active20"]>0 for f in folds.values())>=2,"bootstrap":top_stats["cluster_bootstrap_95"][0]>0}
    verdict="GO" if all(checks.values()) else ("MARGINAL" if float(test.statistic)>0 and top_stats["mean_active20"]>0 else "NO-GO")
    return {"verdict":verdict,"checks":checks,"all":{"count":len(clean),"rho":float(test.statistic),"p_value":float(test.pvalue)},"top_quintile":top_stats,"bottom_quintile":{"count":len(bottom),"mean_active20":float(bottom.active20.mean()),"median_active20":float(bottom.active20.median()),"win_rate20":float((bottom.active20>0).mean())},"quintile_bounds":{"q20":q20,"q80":q80}}


def run(actual_path,reports_dir,end,ledger):
    actual=load_actuals(actual_path);reports=load_reports(reports_dir);events=match_consensus(actual,reports);events,meta=attach_returns(events,end);events.to_csv(ledger,index=False,date_format="%Y-%m-%d");decision=evaluate(events);return _clean({"study":"a-share-analyst-earnings-surprise-v1","data":{**meta,"actual_rows":len(actual),"consensus_matched":len(events)},"decision":decision,"ledger":ledger,"limitations":["annual EPS only","report_date and ann_date have day-level timing","source-bounded non-virgin history"]})

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument("--actual",default="overall/a-share-annual-eps.csv");p.add_argument("--reports",default="overall/a-share-report-rc-raw");p.add_argument("--end",default="2026-08-26");p.add_argument("--ledger",default="overall/a-share-earnings-surprise-events.csv");p.add_argument("--out-json",default="overall/a-share-earnings-surprise.json");p.add_argument("--out-md",default="overall/a-share-earnings-surprise.md");a=p.parse_args(argv);payload=run(a.actual,a.reports,a.end,a.ledger);Path(a.out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");d=payload["decision"];t=d["top_quintile"];text=f"# A股分析师一致预期盈利惊喜结果\n\n- verdict: **{d['verdict']}**\n- events/rho/p: {d['all']['count']} / {d['all']['rho']:.4f} / {d['all']['p_value']:.4g}\n- top quintile active 5/20/60: {t['mean_active5']:.2%} / {t['mean_active20']:.2%} / {t['mean_active60']:.2%}\n";Path(a.out_md).write_text(text,encoding="utf-8");print(text);return 0
if __name__=="__main__":raise SystemExit(main())
