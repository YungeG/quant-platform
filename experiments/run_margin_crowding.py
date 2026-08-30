"""Test financing crowding as an analyst-revision risk filter."""

from __future__ import annotations

import argparse,gc,json
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from experiments.quarterly_portfolio import Bar,BasketConfig,simulate_basket
from experiments.run_analyst_revision import FOLDS,benchmark_returns,consensus_revisions,json_clean,load_reports,month_ends
from experiments.run_largecap_lowvol import summarize_basket
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.research.combination import repair_point_in_time_size


def build_inputs(start,end,reports):
 cfg=Config();con=connect(cfg,read_only=True)
 try:
  built=load_or_build_panel(cfg,"2014-11-27",end,con=con);m=con.execute("select TradeDate,Symbol,RZYE,CircMV,FinIntensity from MarginDetailData where TradeDate between ? and ? order by Symbol,TradeDate",[start,end]).df()
 finally:con.close()
 m.TradeDate=pd.to_datetime(m.TradeDate);m=m.sort_values(["Symbol","TradeDate"]);m["fin_change20"]=(m.RZYE-m.groupby("Symbol").RZYE.shift(20))/m.CircMV
 p=repair_point_in_time_size(built.df);p.TradingDay=pd.to_datetime(p.TradingDay);p=p.sort_values(["Symbol","TradingDay"]).reset_index(drop=True);g=p.groupby("Symbol",sort=False);p["_fwd20"]=g.adj_open.shift(-21)/g.adj_open.shift(-1)-1
 adv=p.groupby("TradingDay").adv20.rank(pct=True,method="first");p["practical"]=(~p.suspended.fillna(True))&(p.age>=252)&(p.Close>=5)&(p.Volume>0)&p.CircMV.notna()&(adv>.5)
 sessions=sorted(p.loc[p.TradingDay>=pd.Timestamp(start),"TradingDay"].drop_duplicates());margin_dates=set(m.TradeDate.unique());decisions=[d for d in month_ends(sessions) if d in margin_dates]
 targets={"base":{},"overlay":{}};signals=[];all_symbols=set()
 for day in decisions:
  u=p[(p.TradingDay==day)&p.practical].nlargest(500,"CircMV").merge(m[m.TradeDate==day][["Symbol","FinIntensity","fin_change20"]],on="Symbol",how="inner")
  if len(u)<250:continue
  u["level_pct"]=u.FinIntensity.rank(pct=True,method="average");u["change_pct"]=u.fin_change20.rank(pct=True,method="average");u["crowding_score"]=u[["level_pct","change_pct"]].mean(axis=1,skipna=False);bench=float(u._fwd20.mean());u["active20"]=u._fwd20-bench
  signals.extend({"signal_date":day,"symbol":r.Symbol,"fin_intensity":r.FinIntensity,"fin_change20":r.fin_change20,"crowding_score":r.crowding_score,"active20":r.active20} for r in u.itertuples(index=False))
  rev=consensus_revisions(reports,day);c=u.merge(rev,on="Symbol",how="inner");base=c[c.revision>0].sort_values(["revision","current_count","Symbol"],ascending=[False,False,True]).head(30);cut=float(u.crowding_score.quantile(.8));overlay=c[(c.revision>0)&(c.crowding_score<=cut)].sort_values(["revision","current_count","Symbol"],ascending=[False,False,True]).head(30);key=day.date().isoformat();targets["base"][key]=base.Symbol.tolist();targets["overlay"][key]=overlay.Symbol.tolist();all_symbols.update(targets["base"][key]+targets["overlay"][key])
 cols=["TradingDay","Symbol","adj_open","adj_close","Open","High","Low","Close","Volume","PctChange"];market=p[p.Symbol.isin(all_symbols)&p.TradingDay.isin(sessions)][cols].set_index(["TradingDay","Symbol"]).sort_index();dates=[d.date().isoformat() for d in sessions]
 def lookup(date,symbol):
  try:r=market.loc[(pd.Timestamp(date),symbol)]
  except KeyError:return None
  return Bar(adj_open=float(r.adj_open),adj_close=float(r.adj_close),raw_open=float(r.Open),raw_high=float(r.High),raw_low=float(r.Low),raw_close=float(r.Close),volume=float(r.Volume),pct_change=float(r.PctChange))
 meta={"panel_version":built.version_hash,"margin_rows":len(m),"decisions":len(targets["base"])};del p,m;gc.collect();return dates,lookup,targets,pd.DataFrame(signals),meta

def corr_stats(s,feature):
 x=s[[feature,"active20","signal_date"]].dropna();t=spearmanr(x[feature],x.active20);folds={}
 for name,start,end in FOLDS:
  f=x[x.signal_date.between(start,end)];folds[name]={"count":len(f),"rho":float(spearmanr(f[feature],f.active20).statistic) if len(f)>3 else 0.0}
 return {"count":len(x),"rho":float(t.statistic),"p_value":float(t.pvalue),"folds":folds}

def run(reports_dir,start,end,benchmark_path):
 reports=load_reports(reports_dir);dates,lookup,targets,signals,meta=build_inputs(start,end,reports);bench=benchmark_returns(benchmark_path,dates);port={}
 for name in targets:
  cfg=BasketConfig(name=name,target_count=30,initial_nav=400_000,buy_cost=.00155,sell_cost=.00155);gcfg=BasketConfig(name=name+"_gross",target_count=30,initial_nav=400_000,buy_cost=0,sell_cost=0);net=simulate_basket(dates,lookup,targets[name],cfg);gross=simulate_basket(dates,lookup,targets[name],gcfg);port[name]=summarize_basket(net,gross,bench,cfg,folds=FOLDS)
 b=port["base"];o=port["overlay"];checks={"drawdown":o["metrics"]["max_drawdown"]>=b["metrics"]["max_drawdown"]+.03,"sharpe":o["metrics"]["sharpe"]>=b["metrics"]["sharpe"]+.05,"cagr":o["metrics"]["cagr"]>=b["metrics"]["cagr"]-.01,"folds":o["positive_excess_folds"]==3};verdict="GO" if all(checks.values()) else "NO-GO"
 return json_clean({"study":"a-share-margin-crowding-v1","data":meta,"signals":{"level":corr_stats(signals,"fin_intensity"),"change20":corr_stats(signals,"fin_change20")},"portfolios":port,"decision":{"verdict":verdict,"checks":checks}})

def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--reports",default="overall/a-share-report-rc-raw");p.add_argument("--start",default="2017-01-03");p.add_argument("--end",default="2026-06-08");p.add_argument("--benchmark",default="overall/a-share-multi-asset-etf-daily.csv");p.add_argument("--out-json",default="overall/a-share-margin-crowding.json");p.add_argument("--out-md",default="overall/a-share-margin-crowding.md");a=p.parse_args(argv);payload=run(a.reports,a.start,a.end,a.benchmark);Path(a.out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");b=payload["portfolios"]["base"]["metrics"];o=payload["portfolios"]["overlay"]["metrics"];text=f"# A股融资拥挤结果\n\n- verdict: **{payload['decision']['verdict']}**\n- level/change rho: {payload['signals']['level']['rho']:.3f}/{payload['signals']['change20']['rho']:.3f}\n- overlay vs base CAGR/Sharpe/MDD: {o['cagr']:.2%}/{o['sharpe']:.3f}/{o['max_drawdown']:.2%} vs {b['cagr']:.2%}/{b['sharpe']:.3f}/{b['max_drawdown']:.2%}\n";Path(a.out_md).write_text(text,encoding="utf-8");print(text);return 0
if __name__=="__main__":raise SystemExit(main())
