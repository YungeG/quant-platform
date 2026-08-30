"""Build and evaluate sector ETF primary-share inflow diffusion events."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
SEED=20260829;COST=.0031
def rolling_pct(values):
 out=[]
 for i,v in enumerate(values):
  h=pd.Series(values[max(0,i-119):i+1]).dropna();out.append(float((h<=v).mean()) if pd.notna(v) and len(h)>=120 else np.nan)
 return out
def bootstrap(values):
 x=np.asarray(values,float);rng=np.random.default_rng(SEED);means=[float(x[rng.integers(0,len(x),len(x))].mean()) for _ in range(2000)];return [float(np.quantile(means,.025)),float(np.quantile(means,.975))]
def run(candidates_path,share_path,daily_path,adj_path,benchmark_path,sector_panel_path,panel_out,events_out,out_json,out_md):
 candidates=pd.read_csv(candidates_path,dtype=str);share=pd.read_parquet(share_path);daily=pd.read_parquet(daily_path);adj=pd.read_parquet(adj_path)
 for d in [share,daily,adj]:d.trade_date=pd.to_datetime(d.trade_date.astype(str),format="mixed")
 price=daily.merge(adj,on=["ts_code","trade_date"],how="inner");price["adj_close"]=price.close*price.adj_factor;price["adj_open"]=price.open*price.adj_factor;share=share.merge(price[["ts_code","trade_date","adj_close","amount"]],on=["ts_code","trade_date"],how="inner").sort_values(["ts_code","trade_date"]);g=share.groupby("ts_code");share["share_lag5"]=g.fd_share.shift(5);share["obs"]=g.cumcount()+1;share["net_creation_value"]=(share.fd_share-share.share_lag5)*share.adj_close;share["aum_prev_proxy"]=share.share_lag5*share.adj_close;share["positive_creation"]=share.net_creation_value>0;share=share[share.obs>=20].merge(candidates[["industry","ts_code"]],on="ts_code",how="inner");rows=[]
 for (day,industry),x in share.groupby(["trade_date","industry"]):
  denom=x.aum_prev_proxy.sum();rows.append({"trade_date":day,"industry":industry,"etf_count":x.ts_code.nunique(),"creation_rate5":float(x.net_creation_value.sum()/denom) if denom>0 else np.nan,"positive_etf_breadth":float(x.positive_creation.mean()),"total_aum_proxy":float(denom)})
 panel=pd.DataFrame(rows).sort_values(["industry","trade_date"]);panel["creation_rate5_pct120"]=panel.groupby("industry")["creation_rate5"].transform(lambda s:pd.Series(rolling_pct(s.tolist()),index=s.index));waves=[]
 for industry,x in panel.groupby("industry"):
  x=x.reset_index();state="DORMANT";seed=None;diff=None;wave_id=None;negative=0
  for i,row in x.iterrows():
   seed_condition=row.creation_rate5>0 and row.creation_rate5_pct120>=.8 and (x.loc[i-1,"creation_rate5_pct120"]<.8 if i>0 and pd.notna(x.loc[i-1,"creation_rate5_pct120"]) else False) and row.positive_etf_breadth>.5
   if state=="DORMANT":
    if seed_condition:state="INFLOW_SEED";seed=i;wave_id=f"{row.trade_date.date()}|{industry}"
    continue
   if state=="INFLOW_SEED":
    last3=x.loc[max(seed,i-2):i];condition=len(last3)==3 and (last3.creation_rate5>0).all() and row.positive_etf_breadth>=.6
    if condition:state="INFLOW_DIFFUSION";diff=i;negative=0
    elif i-seed>=10:waves.append({"wave_id":wave_id,"industry":industry,"status":"FAILED_SEED","seed_date":x.loc[seed,"trade_date"].date().isoformat(),"diffusion_date":None,"end_date":row.trade_date.date().isoformat()});state="DORMANT";seed=None
    continue
   negative=negative+1 if row.creation_rate5<0 else 0
   if negative>=3:waves.append({"wave_id":wave_id,"industry":industry,"status":"COMPLETED_WAVE","seed_date":x.loc[seed,"trade_date"].date().isoformat(),"diffusion_date":x.loc[diff,"trade_date"].date().isoformat(),"end_date":row.trade_date.date().isoformat()});state="DORMANT";seed=None;diff=None
  if seed is not None:waves.append({"wave_id":wave_id,"industry":industry,"status":"ACTIVE_SEED" if diff is None else "ACTIVE_WAVE","seed_date":x.loc[seed,"trade_date"].date().isoformat(),"diffusion_date":x.loc[diff,"trade_date"].date().isoformat() if diff is not None else None,"end_date":x.iloc[-1].trade_date.date().isoformat()})
 wave=pd.DataFrame(waves);benchmark=pd.read_csv(benchmark_path);benchmark=benchmark[benchmark.asset=="equity"].copy();benchmark.trade_date=pd.to_datetime(benchmark.trade_date,format="mixed");benchmark=benchmark.set_index("trade_date").sort_index();sector=pd.read_csv(sector_panel_path);sector.trade_date=pd.to_datetime(sector.trade_date);records=[]
 for row in wave[wave.diffusion_date.notna()].itertuples(index=False):
  signal=pd.Timestamp(row.diffusion_date);pool=candidates[candidates.industry==row.industry].ts_code.unique();choice=None;best=-np.inf
  for code in pool:
   h=price[(price.ts_code==code)&(price.trade_date<signal)].sort_values("trade_date").tail(20)
   if len(h)>=10 and h.amount.mean()>=10000 and h.amount.mean()>best:choice=code;best=float(h.amount.mean())
  base={"event_id":f"{signal.date()}|{row.industry}","signal_date":signal.date().isoformat(),"industry":row.industry,"etf_code":choice,"status":"VALID","rejection_reason":""};dates=benchmark.index[benchmark.index>signal][:40]
  if choice is None or len(dates)<35:records.append({**base,"status":"INVALID","rejection_reason":"no_liquid_etf_or_horizon","observed_days":0});continue
  q=price[price.ts_code==choice].set_index("trade_date").sort_index();entry=dates[0]
  if entry not in q.index:records.append({**base,"status":"INVALID","rejection_reason":"missing_t1_open","observed_days":0});continue
  entry_price=float(q.at[entry,"adj_open"]);returns=[];bench=[];used=[]
  for day in dates:
   if day not in q.index:break
   used.append(day);returns.append(float(q.at[day,"adj_close"])/entry_price-1-COST);bench.append(float(benchmark.at[day,"adj_close"])/float(benchmark.at[entry,"adj_open"])-1)
  active=np.asarray(returns)-np.asarray(bench);observed=len(returns)
  def at(values,n):return float(values[n-1]) if len(values)>=n else None
  def ex(values,kind):
   if not len(values):return None,None,None
   i=int(np.argmax(values) if kind=="max" else np.argmin(values));return float(values[i]),i+1,used[i].date().isoformat()
  maxr,maxrd,maxrdate=ex(returns,"max");minr,minrd,minrdate=ex(returns,"min");maxa,maxad,maxadate=ex(active,"max");mina,minad,minadate=ex(active,"min");sector_row=sector[(sector.sector==row.industry)&(sector.trade_date==signal)];records.append({**base,"entry_date":entry.date().isoformat(),"observed_days":observed,"return_d30":at(returns,30),"return_d35":at(returns,35),"return_d40":at(returns,40),"active_d30":at(active,30),"active_d35":at(active,35),"active_d40":at(active,40),"max_return_40":maxr,"max_return_day":maxrd,"max_return_date":maxrdate,"min_return_40":minr,"min_return_day":minrd,"min_return_date":minrdate,"max_active_40":maxa,"max_active_day":maxad,"max_active_date":maxadate,"min_active_40":mina,"min_active_day":minad,"min_active_date":minadate,"days_outperform_hs300_40":int((active>0).sum()),"outperform_ratio_40":float((active>0).mean()) if observed else None,"success_d35":bool(observed>=35 and returns[34]>0 and active[34]>=.02),"sector_active35":float(sector_row.active_future35.iloc[0]) if len(sector_row) and pd.notna(sector_row.active_future35.iloc[0]) else None})
 events=pd.DataFrame(records);panel.to_csv(panel_out,index=False);events.to_csv(events_out,index=False);complete=events[(events.status=="VALID")&events.active_d35.notna()].copy();complete["year"]=pd.to_datetime(complete.signal_date).dt.year;trim=complete[complete.active_d35<=complete.active_d35.quantile(.95)] if len(complete) else complete;ci=bootstrap(complete.active_d35) if len(complete) else [np.nan,np.nan];folds={name:{"count":len(x),"mean_active35":float(x.active_d35.mean()) if len(x) else 0.0,"success_rate":float(x.success_d35.mean()) if len(x) else 0.0} for name,a,b in (("2018-2022",2018,2022),("2023-2024",2023,2024),("2025",2025,2025)) for x in [complete[complete.year.between(a,b)]]};summary={"waves":len(wave),"failed_seeds":int((wave.status=="FAILED_SEED").sum()),"diffused":int(wave.diffusion_date.notna().sum()),"complete35":len(complete),"absolute_positive_rate":float((complete.return_d35>0).mean()) if len(complete) else 0.0,"outperform_rate":float((complete.active_d35>0).mean()) if len(complete) else 0.0,"success_rate":float(complete.success_d35.mean()) if len(complete) else 0.0,"mean_active35":float(complete.active_d35.mean()) if len(complete) else 0.0,"median_active35":float(complete.active_d35.median()) if len(complete) else 0.0,"bootstrap95":ci,"trim_top5_mean":float(trim.active_d35.mean()) if len(trim) else 0.0,"folds":folds};checks={"count":len(complete)>=30,"absolute":summary["absolute_positive_rate"]>=.6,"outperform":summary["outperform_rate"]>=.6,"success":summary["success_rate"]>=.55,"median":summary["median_active35"]>=.02,"bootstrap":ci[0]>0,"trim":summary["trim_top5_mean"]>0,"folds":sum(x["mean_active35"]>0 for x in folds.values())>=2,"holdout":folds["2025"]["count"]>0 and folds["2025"]["success_rate"]>.5 and folds["2025"]["mean_active35"]>0};verdict="GO" if all(checks.values()) else ("MARGINAL" if summary["mean_active35"]>0 else "NO-GO");payload={"study":"a-share-sector-etf-share-flow-v1","summary":summary,"decision":{"verdict":verdict,"checks":checks},"events":events_out,"panel":panel_out,"limitations":["direct ETF mappings only","new ETFs excluded for first20 observations","fund share is provider source-bounded"]};Path(out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n");Path(out_md).write_text(f"# A股行业ETF份额流策略\n\n- verdict: **{verdict}**\n- waves/diffused/complete35: {len(wave)}/{summary['diffused']}/{len(complete)}\n- success/outperform/median active35: {summary['success_rate']:.2%}/{summary['outperform_rate']:.2%}/{summary['median_active35']:.2%}\n");return payload
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--candidates",default="overall/a-share-sector-etf-candidates.csv");p.add_argument("--share",default="overall/a-share-sector-etf-raw-v2/fund_share.parquet");p.add_argument("--daily",default="overall/a-share-sector-etf-raw-v2/fund_daily.parquet");p.add_argument("--adj",default="overall/a-share-sector-etf-raw-v2/fund_adj.parquet");p.add_argument("--benchmark",default="overall/a-share-equity-etf-daily-current.csv");p.add_argument("--sector-panel",default="overall/a-share-sector-daily-2017-2026.csv");p.add_argument("--panel-out",default="overall/a-share-sector-etf-share-flow-panel.csv");p.add_argument("--events-out",default="overall/a-share-sector-etf-share-flow-events.csv");p.add_argument("--out-json",default="overall/a-share-sector-etf-share-flow-result.json");p.add_argument("--out-md",default="overall/a-share-sector-etf-share-flow-result.md");a=p.parse_args(argv);payload=run(a.candidates,a.share,a.daily,a.adj,a.benchmark,a.sector_panel,a.panel_out,a.events_out,a.out_json,a.out_md);print(json.dumps(payload["summary"],ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
