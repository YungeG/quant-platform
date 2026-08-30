"""Backtest canonical 12-1 momentum and 52-week-high proximity."""
from __future__ import annotations
import argparse,gc,json
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from experiments.context_features import holm_adjust
from experiments.quarterly_portfolio import Bar,BasketConfig,simulate_basket
from experiments.run_analyst_revision import FOLDS,benchmark_returns,json_clean,month_ends
from experiments.run_largecap_lowvol import summarize_basket
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.research.combination import repair_point_in_time_size
SIGNALS=("momentum_12_1","high_52w")

def build(start,end):
 cfg=Config();con=connect(cfg,read_only=True)
 try:built=load_or_build_panel(cfg,"2014-11-27",end,con=con)
 finally:con.close()
 p=repair_point_in_time_size(built.df);p.TradingDay=pd.to_datetime(p.TradingDay);p=p.sort_values(["Symbol","TradingDay"]).reset_index(drop=True);g=p.groupby("Symbol",sort=False)
 p["momentum_12_1"]=g.adj_close.shift(21)/g.adj_close.shift(252)-1;p["high_52w"]=p.adj_close/g.adj_close.transform(lambda s:s.rolling(252,min_periods=252).max());p["_fwd20"]=g.adj_open.shift(-21)/g.adj_open.shift(-1)-1
 adv=p.groupby("TradingDay").adv20.rank(pct=True,method="first");p["practical"]=(~p.suspended.fillna(True))&(p.age>=252)&(p.Close>=5)&(p.Volume>0)&p.CircMV.notna()&(adv>.5)
 sessions=sorted(p.loc[p.TradingDay>=pd.Timestamp(start),"TradingDay"].drop_duplicates());targets={s:{} for s in SIGNALS};signal_rows=[];all_symbols=set()
 for day in month_ends(sessions):
  u=p[(p.TradingDay==day)&p.practical].nlargest(500,"CircMV");bench=float(u._fwd20.mean())
  for signal in SIGNALS:
   valid=u.dropna(subset=[signal]).copy();valid["active20"]=valid._fwd20-bench;signal_rows.extend({"signal_date":day,"symbol":r.Symbol,"signal":signal,"value":getattr(r,signal),"active20":r.active20} for r in valid.itertuples(index=False));sel=valid.sort_values([signal,"Symbol"],ascending=[False,True]).head(30);key=day.date().isoformat();targets[signal][key]=sel.Symbol.tolist();all_symbols.update(targets[signal][key])
 cols=["TradingDay","Symbol","adj_open","adj_close","Open","High","Low","Close","Volume","PctChange"];market=p[p.Symbol.isin(all_symbols)&p.TradingDay.isin(sessions)][cols].set_index(["TradingDay","Symbol"]).sort_index();dates=[d.date().isoformat() for d in sessions]
 def lookup(date,symbol):
  try:r=market.loc[(pd.Timestamp(date),symbol)]
  except KeyError:return None
  return Bar(adj_open=float(r.adj_open),adj_close=float(r.adj_close),raw_open=float(r.Open),raw_high=float(r.High),raw_low=float(r.Low),raw_close=float(r.Close),volume=float(r.Volume),pct_change=float(r.PctChange))
 meta={"panel_version":built.version_hash,"decisions":len(targets[SIGNALS[0]]),"symbols":len(all_symbols)};del p;gc.collect();return dates,lookup,targets,pd.DataFrame(signal_rows),meta

def ic(rows,signal):
 monthly=[]
 for day,g in rows[(rows.signal==signal)].dropna(subset=["value","active20"]).groupby("signal_date"):
  if len(g)>=20 and g.value.nunique()>1:monthly.append({"signal_date":day,"ic":float(spearmanr(g.value,g.active20).statistic),"count":len(g)})
 f=pd.DataFrame(monthly);mean=float(f.ic.mean());std=float(f.ic.std(ddof=1));all_test=spearmanr(rows.loc[rows.signal==signal,"value"],rows.loc[rows.signal==signal,"active20"],nan_policy="omit");folds={}
 for name,start,end in FOLDS:
  x=f[f.signal_date.between(start,end)];folds[name]={"count":len(x),"mean_ic":float(x.ic.mean()) if len(x) else 0.0}
 return {"count":len(f),"mean":mean,"median":float(f.ic.median()),"win_rate":float((f.ic>0).mean()),"t_stat":mean/(std/np.sqrt(len(f))) if std>0 else 0.0,"p_value":float(all_test.pvalue),"folds":folds}

def run(start,end,benchmark_path):
 dates,lookup,targets,rows,meta=build(start,end);bench=benchmark_returns(benchmark_path,dates);ics={s:ic(rows,s) for s in SIGNALS};adj=holm_adjust({s:ics[s]["p_value"] for s in SIGNALS});ports={};decisions={}
 for s in SIGNALS:
  cfg=BasketConfig(name=s,target_count=30,initial_nav=400_000,buy_cost=.00155,sell_cost=.00155);gcfg=BasketConfig(name=s+"_gross",target_count=30,initial_nav=400_000,buy_cost=0,sell_cost=0);net=simulate_basket(dates,lookup,targets[s],cfg);gross=simulate_basket(dates,lookup,targets[s],gcfg);ports[s]=summarize_basket(net,gross,bench,cfg,folds=FOLDS);q=ports[s];checks={"ic":ics[s]["mean"]>=.02,"p":adj[s]<.05,"ic_folds":sum(f["mean_ic"]>0 for f in ics[s]["folds"].values())>=2,"cagr":q["metrics"]["cagr"]>=.10,"excess":q["excess_cagr"]>=.02,"sharpe":q["metrics"]["sharpe"]>=.8,"drawdown":q["metrics"]["max_drawdown"]>=-.30,"folds":q["positive_excess_folds"]==3,"turnover":q["annual_turnover"]<=6};decisions[s]={"verdict":"GO" if all(checks.values()) else ("MARGINAL" if ics[s]["mean"]>0 and q["excess_cagr"]>0 else "NO-GO"),"holm_p":adj[s],"checks":checks}
 overall="GO" if any(d["verdict"]=="GO" for d in decisions.values()) else ("MARGINAL" if any(d["verdict"]=="MARGINAL" for d in decisions.values()) else "NO-GO")
 return json_clean({"study":"a-share-technical-momentum-v1","data":meta,"ic":ics,"portfolios":ports,"decision":{"verdict":overall,"signals":decisions}})

def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--start",default="2017-01-03");p.add_argument("--end",default="2026-08-26");p.add_argument("--benchmark",default="overall/a-share-multi-asset-etf-daily.csv");p.add_argument("--out-json",default="overall/a-share-technical-momentum.json");p.add_argument("--out-md",default="overall/a-share-technical-momentum.md");a=p.parse_args(argv);payload=run(a.start,a.end,a.benchmark);Path(a.out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");lines=["# A股中期技术动量结果","",f"- verdict: **{payload['decision']['verdict']}**",""]
 for s in SIGNALS:
  i=payload["ic"][s];m=payload["portfolios"][s]["metrics"];lines.append(f"- {s}: IC {i['mean']:.4f}, CAGR {m['cagr']:.2%}, Sharpe {m['sharpe']:.3f}, MDD {m['max_drawdown']:.2%}, {payload['decision']['signals'][s]['verdict']}")
 text="\n".join(lines)+"\n";Path(a.out_md).write_text(text,encoding="utf-8");print(text);return 0
if __name__=="__main__":raise SystemExit(main())
