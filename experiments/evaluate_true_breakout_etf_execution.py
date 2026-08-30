"""Evaluate D11 industry-ETF execution after V5 true-breakout confirmation."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
BUY_COST=.0015;SELL_COST=.0015;SEED=20260830
def encode(value):return value.item() if hasattr(value,"item") else str(value)
def net_horizon_return(close,entry):return close/entry*(1-BUY_COST)*(1-SELL_COST)-1
def bootstrap(values,reps=10000):
 x=np.asarray(values,float);rng=np.random.default_rng(SEED);means=[rng.choice(x,len(x),replace=True).mean() for _ in range(reps)];return np.quantile(means,[.025,.975]).tolist()
def select_etf(day,sector,candidates,prices):
 pool=candidates[(candidates.industry==sector)&(candidates.list_date<=day)&(candidates.delist_date.isna()|(candidates.delist_date>=day))];choice=None;best=-np.inf
 for code in pool.ts_code.unique():
  price=prices.get(code)
  if price is None:continue
  history=price[price.index<day].tail(20)
  if len(history)>=10 and float(history.amount.mean())>=10000 and float(history.amount.mean())>best:choice=code;best=float(history.amount.mean())
 return choice,best,None,None
def select_correlated_etf(day,sector,candidates,prices,sector_returns):
 pool=candidates[(candidates.industry==sector)&(candidates.list_date<=day)&(candidates.delist_date.isna()|(candidates.delist_date>=day))];sector_history=sector_returns.get(sector);choices=[]
 if sector_history is None:return None,None,None,None
 for code in pool.ts_code.unique():
  price=prices.get(code)
  if price is None:continue
  history=price[price.index<day];liquidity=history.tail(20)
  if len(liquidity)<10 or float(liquidity.amount.mean())<10000:continue
  returns=history.adj_close.pct_change().rename("etf_return").to_frame().join(sector_history.rename("sector_return"),how="inner").dropna().tail(120)
  if len(returns)<60:continue
  correlation=float(returns.etf_return.corr(returns.sector_return))
  if np.isfinite(correlation):choices.append((correlation,float(liquidity.amount.mean()),str(code),len(returns)))
 if not choices:return None,None,None,None
 correlation,amount,code,common=sorted(choices,key=lambda item:(-item[0],-item[1],item[2]))[0];return code,amount,correlation,common
def run(features_path,sector_panel,candidates_path,daily_path,adj_path,benchmark_path,events_path,out_json,out_md,current_json,current_md,mapping_mode="liquidity"):
 features=pd.read_csv(features_path);features["signal_date"]=pd.to_datetime(features.signal_date);confirmed=features.confirmation_complete_10.astype(str).str.lower().eq("true")&features.held_abs_10.astype(str).str.lower().eq("true")&features.held_rel_10.astype(str).str.lower().eq("true")&features.progress_return_10.ge(.07)&features.progress_active_10.ge(.03);signals=features[confirmed].copy();panel=pd.read_csv(sector_panel,usecols=["trade_date","sector","sector_return"]);panel["trade_date"]=pd.to_datetime(panel.trade_date);panel=panel[panel.sector.ne("半导体")].drop_duplicates(["sector","trade_date"]).sort_values(["sector","trade_date"]);sector_returns={sector:g.set_index("trade_date").sector_return.sort_index() for sector,g in panel.groupby("sector")};confirmation={}
 for sector,g in panel.groupby("sector"):
  dates=g.trade_date.tolist();index={d:i for i,d in enumerate(dates)}
  for day in signals.loc[signals.sector.eq(sector),"signal_date"]:
   i=index.get(day)
   if i is not None and i+10<len(dates):confirmation[(sector,day)]=dates[i+10]
 candidates=pd.read_csv(candidates_path,dtype=str);candidates["list_date"]=pd.to_datetime(candidates.list_date,errors="coerce");candidates["delist_date"]=pd.to_datetime(candidates.delist_date,errors="coerce");daily=pd.read_parquet(daily_path);adj=pd.read_parquet(adj_path);daily.trade_date=pd.to_datetime(daily.trade_date.astype(str),format="mixed");adj.trade_date=pd.to_datetime(adj.trade_date.astype(str),format="mixed");prices_frame=daily.merge(adj,on=["ts_code","trade_date"],how="inner");prices_frame["adj_open"]=prices_frame.open*prices_frame.adj_factor;prices_frame["adj_close"]=prices_frame.close*prices_frame.adj_factor;prices={code:g.set_index("trade_date").sort_index() for code,g in prices_frame.groupby("ts_code")};benchmark=pd.read_csv(benchmark_path);benchmark=benchmark[benchmark.asset.eq("equity")].copy();benchmark.trade_date=pd.to_datetime(benchmark.trade_date,format="mixed");benchmark=benchmark.set_index("trade_date").sort_index();records=[]
 for row in signals.itertuples(index=False):
  confirm=confirmation.get((row.sector,pd.Timestamp(row.signal_date)));base={"event_id":f"{pd.Timestamp(row.signal_date).date()}|{row.sector}","signal_date":pd.Timestamp(row.signal_date).date().isoformat(),"confirmation_date":confirm.date().isoformat() if confirm is not None else None,"sector":row.sector,"status":"VALID","rejection_reason":""}
  if confirm is None:records.append({**base,"status":"INVALID","rejection_reason":"missing_confirmation_date"});continue
  code,amount,map_correlation,map_common=(select_correlated_etf(confirm,row.sector,candidates,prices,sector_returns) if mapping_mode=="correlation" else select_etf(confirm,row.sector,candidates,prices));future=benchmark.index[benchmark.index>confirm][:20]
  if code is None or len(future)<10:records.append({**base,"etf_code":code,"status":"INVALID","rejection_reason":"no_liquid_etf_or_horizon"});continue
  price=prices[code];entry_date=future[0]
  if entry_date not in price.index or float(price.at[entry_date,"adj_open"])<=0:records.append({**base,"etf_code":code,"status":"INVALID","rejection_reason":"missing_d11_open"});continue
  entry=float(price.at[entry_date,"adj_open"]);bench_entry=float(benchmark.at[entry_date,"adj_open"]);returns=[];active=[]
  for day in future:
   if day not in price.index:break
   value=net_horizon_return(float(price.at[day,"adj_close"]),entry);bench=float(benchmark.at[day,"adj_close"])/bench_entry-1;returns.append(value);active.append(value-bench)
  def at(values,n):return float(values[n-1]) if len(values)>=n else None
  records.append({**base,"etf_code":code,"mapping_correlation":map_correlation,"mapping_common_days":map_common,"entry_date":entry_date.date().isoformat(),"avg_amount20":amount,"observed_days":len(returns),"return_d10":at(returns,10),"return_d20":at(returns,20),"active_d10":at(active,10),"active_d20":at(active,20),"max_return20":float(max(returns)) if returns else None,"min_return20":float(min(returns)) if returns else None,"success_d10":bool(len(returns)>=10 and returns[9]>0 and active[9]>0)})
 events=pd.DataFrame(records);events.to_csv(events_path,index=False);events["year"]=pd.to_datetime(events.signal_date).dt.year;historical=events[events.year.between(2018,2025)];complete=historical[(historical.status=="VALID")&historical.active_d10.notna()].copy();ci=bootstrap(complete.active_d10) if len(complete) else [np.nan,np.nan];cut=max(1,int(np.ceil(len(complete)*.05))) if len(complete) else 0;trim=complete.sort_values("active_d10").iloc[:-cut].active_d10.mean() if len(complete)>cut else np.nan;periods={name:{"count":len(g),"mean_active10":float(g.active_d10.mean()) if len(g) else 0.0,"median_active10":float(g.active_d10.median()) if len(g) else 0.0,"success_rate":float(g.success_d10.mean()) if len(g) else 0.0} for name,a,b in [("2018-2022",2018,2022),("2023-2024",2023,2024),("2025",2025,2025)] for g in [complete[complete.year.between(a,b)]]};summary={"source_signals":len(historical),"mapped":int(historical.etf_code.notna().sum()),"mapping_rate":float(historical.etf_code.notna().mean()) if len(historical) else 0.0,"complete10":len(complete),"absolute_positive10":float((complete.return_d10>0).mean()) if len(complete) else 0.0,"outperform10":float((complete.active_d10>0).mean()) if len(complete) else 0.0,"success10":float(complete.success_d10.mean()) if len(complete) else 0.0,"median_active10":float(complete.active_d10.median()) if len(complete) else 0.0,"median_active20":float(complete.active_d20.median()) if complete.active_d20.notna().any() else None,"bootstrap95_active10":ci,"trim_best5_mean_active10":float(trim) if pd.notna(trim) else None,"periods":periods};checks={"mapping":summary["mapping_rate"]>=.50,"count":len(complete)>=30,"absolute":summary["absolute_positive10"]>=.55,"outperform":summary["outperform10"]>=.55,"success":summary["success10"]>=.50,"active10":summary["median_active10"]>0,"active20":summary["median_active20"] is not None and summary["median_active20"]>0,"bootstrap":ci[0]>0,"trim":pd.notna(trim) and trim>0,"periods":all(v["mean_active10"]>0 for v in periods.values()),"holdout":periods["2025"]["count"]>=5 and periods["2025"]["success_rate"]>=.50 and periods["2025"]["median_active10"]>0};payload={"study":"a-share-true-breakout-correlated-etf-v7" if mapping_mode=="correlation" else "a-share-true-breakout-etf-execution-v6","mapping_mode":mapping_mode,"authority":"exploratory_only_no_platform_prepare_operation","summary":summary,"checks":checks,"verdict":"GO" if all(checks.values()) else "NO-GO","events":events_path,"trade_authorized":False};Path(out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2,default=encode)+"\n");title="# A股真突破相关性ETF映射V7结果" if mapping_mode=="correlation" else "# A股真突破ETF执行V6结果";lines=[title,"",f"- verdict: **{payload['verdict']}**",f"- source/mapped/complete10: {summary['source_signals']} / {summary['mapped']} / {summary['complete10']}",f"- positive/outperform/success10: {summary['absolute_positive10']:.2%} / {summary['outperform10']:.2%} / {summary['success10']:.2%}",f"- median active10/20: {summary['median_active10']:.2%} / {summary['median_active20']:.2%}"];Path(out_md).write_text("\n".join(lines)+"\n");current=events[events.year.eq(2026)].drop(columns="year").to_dict("records");current_payload={"as_of":"2026-08-27","strategy_verdict":payload["verdict"],"trade_authorized":False,"events":current};Path(current_json).write_text(json.dumps(current_payload,ensure_ascii=False,indent=2,default=encode)+"\n");Path(current_md).write_text("# A股真突破ETF当前事件\n\n"+f"- strategy: **{payload['verdict']}**\n- trade authorized: **NO**\n- events: {len(current)}\n");print("\n".join(lines));return payload
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--features",default="overall/a-share-sector-true-breakout-features.csv");p.add_argument("--sector-panel",default="overall/a-share-sector-daily-2017-2026.csv");p.add_argument("--candidates",default="overall/a-share-sector-etf-candidates.csv");p.add_argument("--daily",default="overall/a-share-sector-etf-raw-v2/fund_daily.parquet");p.add_argument("--adj",default="overall/a-share-sector-etf-raw-v2/fund_adj.parquet");p.add_argument("--benchmark",default="overall/a-share-equity-etf-daily-current.csv");p.add_argument("--events",default="overall/a-share-true-breakout-etf-events.csv");p.add_argument("--out-json",default="overall/a-share-true-breakout-etf-execution-v6-result.json");p.add_argument("--out-md",default="overall/a-share-true-breakout-etf-execution-v6-result.md");p.add_argument("--current-json",default="overall/a-share-true-breakout-etf-current.json");p.add_argument("--current-md",default="overall/a-share-true-breakout-etf-current.md");p.add_argument("--mapping-mode",choices=["liquidity","correlation"],default="liquidity");a=p.parse_args(argv);run(a.features,a.sector_panel,a.candidates,a.daily,a.adj,a.benchmark,a.events,a.out_json,a.out_md,a.current_json,a.current_md,a.mapping_mode);return 0
if __name__=="__main__":raise SystemExit(main())
