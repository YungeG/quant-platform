"""Run the frozen monthly sector-ETF absolute plus relative momentum strategy."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd
from experiments.quarterly_portfolio import Bar,BasketConfig,simulate_basket
from experiments.run_analyst_revision import benchmark_returns
from experiments.run_largecap_lowvol import summarize_basket
def encode(value):return value.item() if hasattr(value,"item") else str(value)
FOLDS=(("2020-2022","2020-01-01","2022-12-31"),("2023-2024","2023-01-01","2024-12-31"),("2025","2025-01-01","2025-12-31"))
def month_ends(dates):return [day for i,day in enumerate(dates) if i==len(dates)-1 or dates[i+1].month!=day.month]
def build_targets(candidates,prices,decisions):
 targets={};details=[]
 for day in decisions:
  pool=candidates[(candidates.list_date<=day)&(candidates.delist_date.isna()|(candidates.delist_date>=day))];representatives=[]
  for code in pool.ts_code.unique():
   price=prices.get(code)
   if price is None:continue
   history=price[price.index<=day]
   if len(history)<120 or day not in history.index:continue
   amount20=float(history.tail(20).amount.mean())
   if amount20<10000:continue
   close=float(history.at[day,"adj_close"]);sma120=float(history.tail(120).adj_close.mean());return60=close/float(history.iloc[-61].adj_close)-1;industry=str(pool.loc[pool.ts_code.eq(code),"industry"].iloc[0]);representatives.append({"ts_code":code,"industry":industry,"amount20":amount20,"close":close,"sma120":sma120,"return60":return60})
  frame=pd.DataFrame(representatives)
  if len(frame):frame=frame.sort_values(["industry","amount20","ts_code"],ascending=[True,False,True]).drop_duplicates("industry",keep="first");eligible=frame[frame.close.gt(frame.sma120)].sort_values(["return60","amount20","ts_code"],ascending=[False,False,True]).head(3)
  else:eligible=pd.DataFrame(columns=["ts_code"])
  key=day.date().isoformat();targets[key]=eligible.ts_code.astype(str).tolist()
  for rank,row in enumerate(eligible.itertuples(index=False),1):details.append({"decision_date":key,"rank":rank,"ts_code":row.ts_code,"industry":row.industry,"amount20":row.amount20,"return60":row.return60,"close":row.close,"sma120":row.sma120})
 return targets,pd.DataFrame(details)
def yearly_return(returns,year):
 x=returns[pd.to_datetime(returns.index).year==year];return float((1+x).prod()-1) if len(x) else 0.0
def run(candidates_path,daily_path,adj_path,benchmark_path,start,end,signals_path,nav_path,out_json,out_md,current_json,current_md):
 candidates=pd.read_csv(candidates_path,dtype=str);candidates["list_date"]=pd.to_datetime(candidates.list_date,errors="coerce");candidates["delist_date"]=pd.to_datetime(candidates.delist_date,errors="coerce");daily=pd.read_parquet(daily_path);adj=pd.read_parquet(adj_path);daily.trade_date=pd.to_datetime(daily.trade_date.astype(str),format="mixed");adj.trade_date=pd.to_datetime(adj.trade_date.astype(str),format="mixed");frame=daily.merge(adj,on=["ts_code","trade_date"],how="inner");frame["adj_open"]=frame.open*frame.adj_factor;frame["adj_close"]=frame.close*frame.adj_factor;prices={code:g.set_index("trade_date").sort_index() for code,g in frame.groupby("ts_code")};benchmark_data=pd.read_csv(benchmark_path);benchmark_data=benchmark_data[benchmark_data.asset.eq("equity")].copy();benchmark_data.trade_date=pd.to_datetime(benchmark_data.trade_date,format="mixed");dates=[day for day in benchmark_data.trade_date.sort_values().unique() if pd.Timestamp(start)<=day<=pd.Timestamp(end)];decisions=month_ends(dates);targets,signals=build_targets(candidates,prices,decisions);signals.to_csv(signals_path,index=False);selected={code for values in targets.values() for code in values};market=frame[frame.ts_code.isin(selected)&frame.trade_date.isin(dates)].set_index(["trade_date","ts_code"]).sort_index()
 def lookup(date,symbol):
  try:r=market.loc[(pd.Timestamp(date),symbol)]
  except KeyError:return None
  return Bar(adj_open=float(r.adj_open),adj_close=float(r.adj_close),raw_open=float(r.open),raw_high=float(r.high),raw_low=float(r.low),raw_close=float(r.close),volume=float(r.vol),pct_change=float(r.pct_chg))
 date_strings=[pd.Timestamp(day).date().isoformat() for day in dates];config=BasketConfig(name="sector_etf_dual_momentum",target_count=3,initial_nav=400000,buy_cost=.0015,sell_cost=.0015);gross_config=BasketConfig(name="sector_etf_dual_momentum_gross",target_count=3,initial_nav=400000,buy_cost=0,sell_cost=0);result=simulate_basket(date_strings,lookup,targets,config);gross=simulate_basket(date_strings,lookup,targets,gross_config);benchmark=benchmark_returns(benchmark_path,date_strings);portfolio=summarize_basket(result,gross,benchmark,config,folds=FOLDS);pd.DataFrame({"date":result.dates,"nav":result.nav,"gross_nav":gross.nav,"benchmark_return":benchmark.to_numpy()}).to_csv(nav_path,index=False);participation=float(sum(bool(v) for v in targets.values())/len(targets));strategy_2025=float(portfolio["yearly_returns"].get("2025",0));benchmark_2025=yearly_return(benchmark,2025);checks={"cagr":portfolio["metrics"]["cagr"]>=.10,"sharpe":portfolio["metrics"]["sharpe"]>=.80,"drawdown":portfolio["metrics"]["max_drawdown"]>=-.30,"excess":portfolio["excess_cagr"]>=.02,"validation":portfolio["folds"]["2023-2024"]["cagr"]>0,"holdout":strategy_2025>0 and strategy_2025>benchmark_2025,"cost_retention":portfolio["gross_to_net_cagr_retention"]>=.90,"participation":.20<=participation<=.80};payload={"study":"a-share-sector-etf-dual-momentum-v12","authority":"exploratory_only_no_platform_prepare_operation","data":{"start":start,"end":end,"decision_months":len(targets),"participation":participation,"selected_etfs":len(selected)},"portfolio":portfolio,"holdout_2025":{"strategy_return":strategy_2025,"benchmark_return":benchmark_2025,"excess":strategy_2025-benchmark_2025},"checks":checks,"verdict":"GO" if all(checks.values()) else "NO-GO","trade_authorized":False};Path(out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2,default=encode)+"\n");m=portfolio["metrics"];lines=["# A股行业ETF双重动量V12结果","",f"- verdict: **{payload['verdict']}**",f"- CAGR/Sharpe/MDD: {m['cagr']:.2%} / {m['sharpe']:.3f} / {m['max_drawdown']:.2%}",f"- excess CAGR/participation: {portfolio['excess_cagr']:.2%} / {participation:.2%}",f"- 2025 strategy/benchmark/excess: {strategy_2025:.2%} / {benchmark_2025:.2%} / {strategy_2025-benchmark_2025:.2%}"];Path(out_md).write_text("\n".join(lines)+"\n");last=decisions[-1].date().isoformat();current={"as_of":end,"last_decision":last,"targets":targets[last],"strategy_verdict":payload["verdict"],"trade_authorized":False};Path(current_json).write_text(json.dumps(current,ensure_ascii=False,indent=2)+"\n");Path(current_md).write_text("# A股行业ETF双重动量当前状态\n\n"+f"- as of: {end}\n- targets: {', '.join(targets[last]) or 'CASH'}\n- trade authorized: **NO**\n");print("\n".join(lines));return payload
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--candidates",default="overall/a-share-sector-etf-candidates.csv");p.add_argument("--daily",default="overall/a-share-sector-etf-raw-v2/fund_daily.parquet");p.add_argument("--adj",default="overall/a-share-sector-etf-raw-v2/fund_adj.parquet");p.add_argument("--benchmark",default="overall/a-share-equity-etf-daily-current.csv");p.add_argument("--start",default="2020-01-02");p.add_argument("--end",default="2026-08-25");p.add_argument("--signals",default="overall/a-share-sector-etf-dual-momentum-signals.csv");p.add_argument("--nav",default="overall/a-share-sector-etf-dual-momentum-nav.csv");p.add_argument("--out-json",default="overall/a-share-sector-etf-dual-momentum-v12-result.json");p.add_argument("--out-md",default="overall/a-share-sector-etf-dual-momentum-v12-result.md");p.add_argument("--current-json",default="overall/a-share-sector-etf-dual-momentum-current.json");p.add_argument("--current-md",default="overall/a-share-sector-etf-dual-momentum-current.md");a=p.parse_args(argv);run(a.candidates,a.daily,a.adj,a.benchmark,a.start,a.end,a.signals,a.nav,a.out_json,a.out_md,a.current_json,a.current_md);return 0
if __name__=="__main__":raise SystemExit(main())
