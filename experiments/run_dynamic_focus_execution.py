"""Evaluate weekly-rebalanced dynamic absorption focus baskets."""
from __future__ import annotations
import argparse,json,gc
from pathlib import Path
import numpy as np,pandas as pd
from experiments.quarterly_portfolio import Bar,BasketConfig,simulate_basket
from experiments.run_weekly_industry_events import summarize
from experiments.weekly_industry_cycle import path_metrics
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.research.combination import repair_point_in_time_size
COST=.00155
def run(waves_path,focus_panel,benchmark_path,max_year,end_date,events_path,out_json,out_md):
 waves=pd.read_csv(waves_path);waves=waves[waves.diffusion_date.notna()].copy();waves["signal_date"]=pd.to_datetime(waves.diffusion_date);waves=waves[waves.signal_date.dt.year<=max_year];focus=pd.read_csv(focus_panel);focus.trade_date=pd.to_datetime(focus.trade_date);focus=focus.set_index(["trade_date","sector"]);symbols={symbol for value in focus.focus_symbols.dropna() for symbol in json.loads(value)};cfg=Config();con=connect(cfg,read_only=True)
 try:built=load_or_build_panel(cfg,"2017-01-01",end_date,con=con)
 finally:con.close()
 p=repair_point_in_time_size(built.df);p.TradingDay=pd.to_datetime(p.TradingDay);sessions=sorted(p.TradingDay.drop_duplicates());index={d:i for i,d in enumerate(sessions)};market=p[p.Symbol.isin(symbols)][["TradingDay","Symbol","adj_open","adj_close","Open","High","Low","Close","Volume","PctChange"]].set_index(["TradingDay","Symbol"]).sort_index();benchmark=pd.read_csv(benchmark_path);benchmark=benchmark[benchmark.asset=="equity"].copy();benchmark.trade_date=pd.to_datetime(benchmark.trade_date,format="mixed");benchmark=benchmark.set_index("trade_date").sort_index();records=[]
 def lookup(date,symbol):
  try:r=market.loc[(pd.Timestamp(date),symbol)]
  except KeyError:return None
  if float(r.Open)<=0 or float(r.adj_open)<=0:return None
  return Bar(adj_open=float(r.adj_open),adj_close=float(r.adj_close),raw_open=float(r.Open),raw_high=float(r.High),raw_low=float(r.Low),raw_close=float(r.Close),volume=float(r.Volume),pct_change=float(r.PctChange))
 for row in waves.itertuples(index=False):
  signal=pd.Timestamp(row.signal_date);start=index.get(signal);base={"event_id":f"{signal.date()}|{row.sector}","signal_date":signal.date().isoformat(),"industry":row.sector,"score":100.0,"status":"VALID","rejection_reason":""}
  if start is None or start+35>=len(sessions):records.append({**base,"status":"INVALID","rejection_reason":"missing_horizon","observed_days":0});continue
  dates=sessions[start:min(len(sessions),start+41)];date_strings=[d.date().isoformat() for d in dates];targets={}
  for offset in range(0,len(dates)-1,5):
   day=dates[offset];key=(day,row.sector);targets[day.date().isoformat()]=json.loads(focus.at[key,"focus_symbols"])[:20] if key in focus.index else []
  initial=targets.get(signal.date().isoformat(),[])
  if len(initial)<10:records.append({**base,"status":"INVALID","rejection_reason":"initial_focus_below_10","observed_days":0});continue
  result=simulate_basket(date_strings,lookup,targets,BasketConfig(row.sector,20,buy_cost=COST,sell_cost=COST,buy_retry_days=1));bench=[]
  if dates[1] in benchmark.index:
   entry=float(benchmark.at[dates[1],"adj_open"])
   for day in dates[1:41]:
    if day not in benchmark.index:break
    bench.append(float(benchmark.at[day,"adj_close"])/entry-1)
  metrics=path_metrics(result.dates,result.nav,bench,400000);average_nav=float(np.mean(result.nav));one_way=.5*sum(float(t["notional"]) for t in result.trades)/average_nav if average_nav>0 else 0;payload={**base,**metrics.__dict__,"trade_count":len(result.trades),"one_way_turnover_event":one_way,"annualized_one_way_turnover":one_way*252/40,"average_cash_fraction":float(np.mean(result.cash_fraction[1:])) if len(result.cash_fraction)>1 else 1.0,"blocked_buys":result.blocked_buys,"expired_buys":result.expired_buys,"lot_failures":result.lot_failures};payload["success_d35"]=bool(payload["return_d35"] is not None and payload["return_d35"]>0 and payload["active_d35"]>=.02);records.append(payload)
 events=pd.DataFrame(records);events.to_csv(events_path,index=False);summary,checks=summarize(events);valid=events[(events.status=="VALID")&events.active_d35.notna()];summary["median_annualized_turnover"]=float(valid.annualized_one_way_turnover.median()) if len(valid) else 0.0;checks["turnover"]=summary["median_annualized_turnover"]<=12;checks["success"]=summary["success_rate"]>=.55;verdict="GO" if all(checks.values()) else ("MARGINAL" if summary["mean_active35"]>0 else "NO-GO");payload={"study":"a-share-dynamic-focus-execution-v1","data":{"panel_version":built.version_hash,"events":len(events),"valid":len(valid),"max_year":max_year},"summary":summary,"decision":{"verdict":verdict,"checks":checks},"events":events_path,"limitations":["weekly focus rebalance is exploratory","signal thresholds unchanged from V6","no formal Platform Backtest authority"]};Path(out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n");lines=["# A股动态关注名单执行结果","",f"- verdict: **{verdict}**",f"- valid/success/outperform/active35: {len(valid)}/{summary['success_rate']:.2%}/{summary['outperform_rate']:.2%}/{summary['median_active35']:.2%}",f"- median annualized one-way turnover: {summary['median_annualized_turnover']:.2f}"];Path(out_md).write_text("\n".join(lines)+"\n");del p,market;gc.collect();return payload
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--waves",default="overall/a-share-turnover-absorption-waves.csv");p.add_argument("--focus-panel",default="overall/a-share-turnover-absorption-panel.csv");p.add_argument("--benchmark",default="overall/a-share-equity-etf-daily-current.csv");p.add_argument("--max-year",type=int,default=2025);p.add_argument("--end-date",default="2026-08-27");p.add_argument("--events",default="overall/a-share-dynamic-focus-events.csv");p.add_argument("--out-json",default="overall/a-share-dynamic-focus-execution.json");p.add_argument("--out-md",default="overall/a-share-dynamic-focus-execution.md");a=p.parse_args(argv);payload=run(a.waves,a.focus_panel,a.benchmark,a.max_year,a.end_date,a.events,a.out_json,a.out_md);print(json.dumps(payload["summary"],ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
