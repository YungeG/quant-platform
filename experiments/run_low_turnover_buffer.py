"""Run the frozen low-turnover Top-20 entry / Top-40 retention buffer."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from factormine.config import Config
from factormine.data.calendar import TradingCalendar
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.eval.returns import forward_return_columns
from experiments.run_low_turnover_replication import ANCHOR,COST_PER_SIDE,PLACEBO_SEEDS,TOP_N,_latest_lot_feasibility,_prepare,_summarize
def encode(value):return value.item() if hasattr(value,"item") else str(value)
def scheduled_selections(data,seed=None):
 sessions=sorted(pd.to_datetime(data.TradingDay.unique()));rebalance=set(sessions[::ANCHOR]);rng=np.random.default_rng(seed) if seed is not None else None;previous=[]
 for day,group in data[data.TradingDay.isin(rebalance)].groupby("TradingDay"):
  eligible=group[group.practical&group._score.notna()].copy()
  if len(eligible)<40:continue
  if rng is None:eligible=eligible.sort_values(["_score","Symbol"],ascending=[False,True])
  else:eligible["_random"]=rng.random(len(eligible));eligible=eligible.sort_values(["_random","Symbol"],ascending=[False,True])
  rank={symbol:i+1 for i,symbol in enumerate(eligible.Symbol.astype(str))};target=[symbol for symbol in previous if rank.get(symbol,10**9)<=40]
  for symbol in eligible.Symbol.astype(str):
   if symbol not in target:target.append(symbol)
   if len(target)>=TOP_N:break
  selected=eligible[eligible.Symbol.astype(str).isin(target)].set_index(eligible[eligible.Symbol.astype(str).isin(target)].Symbol.astype(str)).loc[target].reset_index(drop=True)
  yield pd.Timestamp(day),eligible,selected,tuple(previous),tuple(target)
  previous=target

def records(data,seed=None):
 rows=[];latest=[]
 for day,eligible,selected,previous,target in scheduled_selections(data,seed):
  valid=selected.fwd5.notna();executed=set(selected.loc[valid,"Symbol"].astype(str));gross=float(selected.fwd5.fillna(0).sum()/TOP_N);benchmark=float(eligible.fwd5.dropna().mean());turnover=1.0 if not previous else 1-len(executed&set(previous))/TOP_N;cost=turnover*COST_PER_SIDE*2;rows.append({"date":day,"gross_absolute":gross,"net_absolute":gross-cost,"benchmark":benchmark,"gross_active":gross-benchmark,"net_active":gross-benchmark-cost,"turnover":turnover,"missing_rate":1-float(valid.mean()),"executed_names":len(executed)});latest=list(target)
 return pd.DataFrame(rows).set_index("date").sort_index(),latest
def run(start,end,out_json,out_md):
 cfg=Config();con=connect(cfg,read_only=True)
 try:cal=TradingCalendar.from_duckdb(con);built=load_or_build_panel(cfg,start,end,con=con)
 finally:con.close()
 data=_prepare(forward_return_columns(built.df,cal,[ANCHOR]));real_records,latest_holdings=records(data);real=_summarize(real_records);placebos=[_summarize(records(data,seed)[0])["active"]["sharpe"] for seed in PLACEBO_SEEDS];median=float(np.median(placebos));checks={"cagr":real["absolute"]["cagr"]>=.10 and real["absolute"]["cagr"]>.09171292101959483,"active_sharpe":real["active"]["sharpe"]>=.50,"turnover":real["annual_turnover"]<16,"folds":real["positive_folds"]==3,"missing":real["selected_missing_rate"]<=.02,"placebo":real["active"]["sharpe"]>=median+.15};payload={"study":"a-share-low-turnover-buffer-v18","data_version":built.version_hash,"parameters":{"enter_rank":20,"retain_rank":40,"anchor":ANCHOR,"cost_per_side":COST_PER_SIDE},"real":real,"placebo_sharpes":placebos,"placebo_median":median,"checks":checks,"verdict":"GO-CANDIDATE" if all(checks.values()) else "NO-GO","latest_lot_feasibility":_latest_lot_feasibility(data),"current":{"as_of":str(pd.Timestamp(data.TradingDay.max()).date()),"holdings":latest_holdings},"limitations":["research forward-return portfolio, not order-level delayed-exit simulation","missing scheduled forward return is treated as cash","rolling historical evidence, not virgin OOS"],"trade_authorized":False};Path(out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2,default=encode)+"\n");lines=["# A股低换手持仓缓冲V18结果","",f"- verdict: **{payload['verdict']}**",f"- absolute CAGR/Sharpe/MDD: {real['absolute']['cagr']:.2%} / {real['absolute']['sharpe']:.3f} / {real['absolute']['max_drawdown']:.2%}",f"- active edge/Sharpe: {real['active']['mean']:.3%} / {real['active']['sharpe']:.3f}",f"- annual turnover: {real['annual_turnover']:.2f}"];Path(out_md).write_text("\n".join(lines)+"\n");print("\n".join(lines));return payload
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--start",default="2016-01-01");p.add_argument("--end",default="2026-08-25");p.add_argument("--out-json",default="overall/a-share-low-turnover-buffer-v18-result.json");p.add_argument("--out-md",default="overall/a-share-low-turnover-buffer-v18-result.md");a=p.parse_args(argv);run(a.start,a.end,a.out_json,a.out_md);return 0
if __name__=="__main__":raise SystemExit(main())
