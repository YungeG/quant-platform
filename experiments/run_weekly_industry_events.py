"""Evaluate independent weekly industry-entry events over the frozen 40-day path."""
from __future__ import annotations
import argparse,json,gc
from pathlib import Path
import numpy as np,pandas as pd
from experiments.quarterly_portfolio import Bar,BasketConfig,simulate_basket
from experiments.run_analyst_revision import json_clean
from experiments.weekly_industry_cycle import path_metrics
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.research.combination import repair_point_in_time_size
SEED=20260829;COST=.00155;FOLDS=(("2018-2020",2018,2020),("2021-2022",2021,2022),("2023-2025",2023,2025))
def bootstrap(values):
 x=np.asarray(values,float);rng=np.random.default_rng(SEED);means=[float(x[rng.integers(0,len(x),len(x))].mean()) for _ in range(2000)];return [float(np.quantile(means,.025)),float(np.quantile(means,.975))]
def evaluate_event(row,sessions,session_index,market,etf,min_targets=10):
 signal=pd.Timestamp(row.decision_date);start=session_index.get(signal);symbols=json.loads(row.top_symbols) if isinstance(row.top_symbols,str) else []
 base={"event_id":f"{signal.date()}|{row.industry}","signal_date":signal.date().isoformat(),"industry":row.industry,"score":row.score,"target_count":len(symbols),"status":"VALID","rejection_reason":""}
 if start is None or len(symbols)<min_targets:return {**base,"status":"INVALID","rejection_reason":"insufficient_target_or_session","observed_days":0}
 dates=sessions[start:start+41];date_strings=[d.date().isoformat() for d in dates]
 def lookup(date,symbol):
  try:r=market.loc[(pd.Timestamp(date),symbol)]
  except KeyError:return None
  if float(r.Open)<=0 or float(r.adj_open)<=0:return None
  return Bar(adj_open=float(r.adj_open),adj_close=float(r.adj_close),raw_open=float(r.Open),raw_high=float(r.High),raw_low=float(r.Low),raw_close=float(r.Close),volume=float(r.Volume),pct_change=float(r.PctChange))
 result=simulate_basket(date_strings,lookup,{date_strings[0]:symbols},BasketConfig(row.industry,len(symbols),buy_cost=COST,sell_cost=COST,buy_retry_days=1));benchmark=[]
 if len(dates)>1 and dates[1] in etf.index:
  entry=float(etf.at[dates[1],"adj_open"])
  for day in dates[1:41]:
   if day not in etf.index:break
   benchmark.append(float(etf.at[day,"adj_close"])/entry-1)
 metrics=path_metrics(result.dates,result.nav,benchmark,400000);payload={**base,**metrics.__dict__,"blocked_buys":result.blocked_buys,"expired_buys":result.expired_buys,"lot_failures":result.lot_failures,"average_cash_fraction":float(np.mean(result.cash_fraction[1:])) if len(result.cash_fraction)>1 else 1.0};payload["success_d35"]=bool(payload["return_d35"] is not None and payload["return_d35"]>0 and payload["active_d35"]>=.02);return payload
def summarize(events):
 x=events[(events.status=="VALID")&events.active_d35.notna()].copy();active=x.active_d35;trim=x[x.active_d35<=x.active_d35.quantile(.95)].active_d35 if len(x) else pd.Series(dtype=float);folds={}
 for name,a,b in FOLDS:
  f=x[pd.to_datetime(x.signal_date).dt.year.between(a,b)];folds[name]={"count":len(f),"mean_active35":float(f.active_d35.mean()) if len(f) else 0.0,"success_rate":float(f.success_d35.mean()) if len(f) else 0.0}
 hold=x[pd.to_datetime(x.signal_date).dt.year==2025];ci=bootstrap(active) if len(active) else [np.nan,np.nan];result={"count":len(x),"absolute_positive_rate":float((x.return_d35>0).mean()) if len(x) else 0.0,"outperform_rate":float((active>0).mean()) if len(x) else 0.0,"success_rate":float(x.success_d35.mean()) if len(x) else 0.0,"mean_active35":float(active.mean()) if len(x) else 0.0,"median_active30":float(x.active_d30.median()) if len(x) else 0.0,"median_active35":float(active.median()) if len(x) else 0.0,"median_active40":float(x.active_d40.median()) if x.active_d40.notna().any() else 0.0,"bootstrap95":ci,"trim_top5_mean":float(trim.mean()) if len(trim) else 0.0,"median_max_return40":float(x.max_return_40.median()) if len(x) else 0.0,"median_min_return40":float(x.min_return_40.median()) if len(x) else 0.0,"median_outperform_days40":float(x.days_outperform_hs300_40.median()) if len(x) else 0.0,"folds":folds,"holdout2025":{"count":len(hold),"success_rate":float(hold.success_d35.mean()) if len(hold) else 0.0,"median_active35":float(hold.active_d35.median()) if len(hold) else 0.0},"industries":{i:{"count":len(g),"success_rate":float(g.success_d35.mean()),"median_active35":float(g.active_d35.median())} for i,g in x.groupby("industry")}};checks={"count":len(x)>=50,"absolute":result["absolute_positive_rate"]>=.60,"outperform":result["outperform_rate"]>=.60,"median":result["median_active35"]>=.02,"bootstrap":ci[0]>0,"horizons":min(result["median_active30"],result["median_active35"],result["median_active40"])>0,"folds":sum(v["mean_active35"]>0 for v in folds.values())>=2,"trim":result["trim_top5_mean"]>0,"holdout":result["holdout2025"]["count"]>0 and result["holdout2025"]["success_rate"]>.50 and result["holdout2025"]["median_active35"]>0};return result,checks
def run(states_path,benchmark_path,max_event_year,end_date,events_path,min_targets=10):
 states=pd.read_csv(states_path);states["decision_date"]=pd.to_datetime(states.decision_date);candidates=states[states.entry_event.astype(str).str.lower().eq("true")&states.decision_date.dt.year.le(max_event_year)].copy();cfg=Config();con=connect(cfg,read_only=True)
 try:built=load_or_build_panel(cfg,"2016-01-01",end_date,con=con)
 finally:con.close()
 p=repair_point_in_time_size(built.df);p.TradingDay=pd.to_datetime(p.TradingDay);sessions=sorted(p.TradingDay.drop_duplicates());index={d:i for i,d in enumerate(sessions)};symbols={s for value in candidates.top_symbols.dropna() for s in json.loads(value)};start=candidates.decision_date.min();finish=min(pd.Timestamp(end_date),candidates.decision_date.max()+pd.offsets.BDay(70));cols=["TradingDay","Symbol","adj_open","adj_close","Open","High","Low","Close","Volume","PctChange"];market=p[p.Symbol.isin(symbols)&p.TradingDay.between(start,finish)][cols].set_index(["TradingDay","Symbol"]).sort_index();etf=pd.read_csv(benchmark_path);etf=etf[etf.asset=="equity"].copy();etf.trade_date=pd.to_datetime(etf.trade_date,format="mixed");etf=etf.set_index("trade_date").sort_index();records=[evaluate_event(row,sessions,index,market,etf,min_targets) for row in candidates.itertuples(index=False)];events=pd.DataFrame(records);events.to_csv(events_path,index=False);summary,checks=summarize(events);verdict="GO" if all(checks.values()) else ("MARGINAL" if summary["mean_active35"]>0 else "NO-GO");del p,market;gc.collect();return json_clean({"study":"a-share-weekly-industry-cycle-v1","authority":"exploratory_only_no_platform_prepare_operation","data":{"panel_version":built.version_hash,"candidate_events":len(candidates),"valid_events":summary["count"],"max_event_year":max_event_year,"min_targets":min_targets},"summary":summary,"decision":{"verdict":verdict,"checks":checks},"events":events_path,"limitations":["source-bounded industry and financial histories","industry thesis is non-virgin","custom event simulator is not formal Platform Backtest evidence"]})
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--states",default="overall/a-share-weekly-industry-states.csv");p.add_argument("--benchmark",default="overall/a-share-equity-etf-daily-current.csv");p.add_argument("--max-event-year",type=int,default=2024);p.add_argument("--end-date",default="2026-08-27");p.add_argument("--events",default="overall/a-share-weekly-industry-events-preholdout.csv");p.add_argument("--out-json",default="overall/a-share-weekly-industry-cycle-preholdout.json");p.add_argument("--out-md",default="overall/a-share-weekly-industry-cycle-preholdout.md");p.add_argument("--min-targets",type=int,default=10);a=p.parse_args(argv);payload=run(a.states,a.benchmark,a.max_event_year,a.end_date,a.events,a.min_targets);Path(a.out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n");s=payload["summary"];text=f"# A股周度行业周期模型\n\n- through event year: {a.max_event_year}\n- verdict: **{payload['decision']['verdict']}**\n- events/success/outperform/median active35: {s['count']} / {s['success_rate']:.2%} / {s['outperform_rate']:.2%} / {s['median_active35']:.2%}\n- median max/min return40: {s['median_max_return40']:.2%} / {s['median_min_return40']:.2%}\n";Path(a.out_md).write_text(text);print(text);return 0
if __name__=="__main__":raise SystemExit(main())
