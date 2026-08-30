"""Evaluate resource-industry futures price momentum plus warehouse contraction."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
PRODUCTS={"有色金属":["CU","AL","ZN","PB","NI","SN"],"钢铁":["RB","HC","J"],"基础化工":["MA","PP","L","V","RU","FG"]};CODES={"CUL.SHF":"CU","ALL.SHF":"AL","ZNL.SHF":"ZN","PBL.SHF":"PB","NIL.SHF":"NI","SNL.SHF":"SN","RBL.SHF":"RB","HCL.SHF":"HC","JL.DCE":"J","MAL.ZCE":"MA","PPL.DCE":"PP","LL.DCE":"L","VL.DCE":"V","RUL.SHF":"RU","FGL.ZCE":"FG"};SEED=20260829
def bootstrap(values):
 x=np.asarray(values,float);rng=np.random.default_rng(SEED);means=[float(x[rng.integers(0,len(x),len(x))].mean()) for _ in range(2000)];return [float(np.quantile(means,.025)),float(np.quantile(means,.975))]
def run(daily_path,warehouse_path,sector_path,panel_out,events_out,out_json,out_md):
 d=pd.read_parquet(daily_path);w=pd.read_parquet(warehouse_path);d.trade_date=pd.to_datetime(d.trade_date.astype(str),format="mixed");w.trade_date=pd.to_datetime(w.trade_date.astype(str),format="mixed");d["product"]=d.ts_code.map(CODES);d=d[d["product"].notna()].sort_values(["product","trade_date"]);warehouse=w.groupby(["symbol","trade_date"],as_index=False).vol.sum().rename(columns={"symbol":"product","vol":"warehouse_vol"}).sort_values(["product","trade_date"]);parts=[]
 for product,g in d.groupby("product"):
  x=pd.merge_asof(g.sort_values("trade_date"),warehouse[warehouse["product"]==product].sort_values("trade_date"),on="trade_date",by="product",direction="backward",tolerance=pd.Timedelta(days=5));x["price_return20"]=x.settle/x.settle.shift(20)-1;x["inventory_change20"]=x.warehouse_vol/x.warehouse_vol.shift(20)-1;parts.append(x)
 product_panel=pd.concat(parts,ignore_index=True);rows=[]
 for industry,products in PRODUCTS.items():
  x=product_panel[product_panel["product"].isin(products)].copy();x["week"]=x.trade_date.dt.to_period("W-FRI")
  for _,g in x.groupby("week"):
   latest=g.sort_values("trade_date").groupby("product").tail(1);day=latest.trade_date.max();valid=latest.dropna(subset=["price_return20","inventory_change20"]);rows.append({"decision_date":day,"industry":industry,"eligible_products":len(valid),"price_positive_breadth":float((valid.price_return20>0).mean()) if len(valid) else np.nan,"inventory_down_breadth":float((valid.inventory_change20<0).mean()) if len(valid) else np.nan,"products":json.dumps(valid["product"].tolist(),ensure_ascii=False)})
 panel=pd.DataFrame(rows).sort_values(["industry","decision_date"]);records=[]
 for industry,g in panel.groupby("industry"):
  active=False;last_event=pd.Timestamp("1900-01-01");prev_condition=False;exit_fail=0
  for row in g.itertuples(index=False):
   enter_condition=row.eligible_products>=3 and row.price_positive_breadth>=.6 and row.inventory_down_breadth>=.6;event=False
   if active:
    hold=row.price_positive_breadth>=.4 and row.inventory_down_breadth>=.4;exit_fail=0 if hold else exit_fail+1
    if exit_fail>=2:active=False;status="NO-ENTRY"
    else:status="ENTER"
   elif enter_condition and prev_condition:
    active=True;exit_fail=0;status="ENTER";event=(pd.Timestamp(row.decision_date)-last_event).days>=60
    if event:last_event=pd.Timestamp(row.decision_date)
   elif enter_condition:status="WATCH"
   else:status="NO-ENTRY"
   records.append({**row._asdict(),"status":status,"entry_event":event});prev_condition=enter_condition
 states=pd.DataFrame(records);sector=pd.read_csv(sector_path);sector.trade_date=pd.to_datetime(sector.trade_date);events=[]
 for row in states[states.entry_event].itertuples(index=False):
  s=sector[sector.sector==row.industry].sort_values("trade_date").reset_index(drop=True);idx=s.index[s.trade_date==pd.Timestamp(row.decision_date)]
  base={"event_id":f"{pd.Timestamp(row.decision_date).date()}|{row.industry}","signal_date":pd.Timestamp(row.decision_date).date().isoformat(),"industry":row.industry,"eligible_products":row.eligible_products,"status":"VALID","rejection_reason":""}
  if not len(idx):events.append({**base,"status":"INVALID","rejection_reason":"missing_sector_date","observed_days":0});continue
  i=int(idx[0]);after=s.loc[i+1:min(len(s)-1,i+40)];returns=after.sector_index/s.loc[i,"sector_index"]-1;active=returns-(after.benchmark_index/s.loc[i,"benchmark_index"]-1);observed=len(after)
  def at(values,n):return float(values.iloc[n-1]) if len(values)>=n else None
  def ex(values,kind):
   if not len(values):return None,None,None
   j=values.idxmax() if kind=="max" else values.idxmin();return float(values.loc[j]),int(j-i),s.loc[j,"trade_date"].date().isoformat()
  maxr,maxrd,maxrdate=ex(returns,"max");minr,minrd,minrdate=ex(returns,"min");maxa,maxad,maxadate=ex(active,"max");mina,minad,minadate=ex(active,"min");events.append({**base,"observed_days":observed,"return_d30":at(returns,30),"return_d35":at(returns,35),"return_d40":at(returns,40),"active_d30":at(active,30),"active_d35":at(active,35),"active_d40":at(active,40),"max_return_40":maxr,"max_return_day":maxrd,"max_return_date":maxrdate,"min_return_40":minr,"min_return_day":minrd,"min_return_date":minrdate,"max_active_40":maxa,"max_active_day":maxad,"max_active_date":maxadate,"min_active_40":mina,"min_active_day":minad,"min_active_date":minadate,"days_outperform_hs300_40":int((active>0).sum()),"outperform_ratio_40":float((active>0).mean()) if observed else None,"success_d35":bool(observed>=35 and returns.iloc[34]>0 and active.iloc[34]>=.02)})
 event=pd.DataFrame(events);states.to_csv(panel_out,index=False);event.to_csv(events_out,index=False);complete=event[(event.status=="VALID")&event.active_d35.notna()].copy();complete["year"]=pd.to_datetime(complete.signal_date).dt.year;trim=complete[complete.active_d35<=complete.active_d35.quantile(.95)] if len(complete) else complete;ci=bootstrap(complete.active_d35) if len(complete) else [np.nan,np.nan];folds={name:{"count":len(x),"mean_active35":float(x.active_d35.mean()) if len(x) else 0.0,"success_rate":float(x.success_d35.mean()) if len(x) else 0.0} for name,a,b in (("2018-2022",2018,2022),("2023-2024",2023,2024),("2025",2025,2025)) for x in [complete[complete.year.between(a,b)]]};summary={"events":len(event),"complete35":len(complete),"absolute_positive_rate":float((complete.return_d35>0).mean()) if len(complete) else 0.0,"outperform_rate":float((complete.active_d35>0).mean()) if len(complete) else 0.0,"success_rate":float(complete.success_d35.mean()) if len(complete) else 0.0,"mean_active35":float(complete.active_d35.mean()) if len(complete) else 0.0,"median_active35":float(complete.active_d35.median()) if len(complete) else 0.0,"bootstrap95":ci,"trim_top5_mean":float(trim.active_d35.mean()) if len(trim) else 0.0,"folds":folds,"industries":{i:{"count":len(x),"success_rate":float(x.success_d35.mean()),"median_active35":float(x.active_d35.median())} for i,x in complete.groupby("industry")}};checks={"count":len(complete)>=30,"absolute":summary["absolute_positive_rate"]>=.6,"outperform":summary["outperform_rate"]>=.6,"success":summary["success_rate"]>=.55,"median":summary["median_active35"]>=.02,"bootstrap":ci[0]>0,"trim":summary["trim_top5_mean"]>0,"folds":sum(x["mean_active35"]>0 for x in folds.values())>=2,"holdout":folds["2025"]["count"]>0 and folds["2025"]["success_rate"]>.5 and folds["2025"]["mean_active35"]>0};verdict="GO" if all(checks.values()) else ("MARGINAL" if summary["mean_active35"]>0 else "NO-GO");payload={"study":"a-share-resource-price-inventory-cycle-v1","summary":summary,"decision":{"verdict":verdict,"checks":checks},"events":events_out,"panel":panel_out,"limitations":["continuous futures and warehouse receipts are source-bounded","product coverage differs by history","sector index outcomes are exploratory"]};Path(out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n");Path(out_md).write_text(f"# A股资源品价格—库存周期结果\n\n- verdict: **{verdict}**\n- events/complete35: {len(event)}/{len(complete)}\n- success/outperform/median active35: {summary['success_rate']:.2%}/{summary['outperform_rate']:.2%}/{summary['median_active35']:.2%}\n");return payload
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--daily",default="overall/a-share-resource-cycle-raw/fut_daily.parquet");p.add_argument("--warehouse",default="overall/a-share-resource-cycle-raw/fut_wsr.parquet");p.add_argument("--sector",default="overall/a-share-sector-daily-2017-2026.csv");p.add_argument("--panel-out",default="overall/a-share-resource-price-inventory-panel.csv");p.add_argument("--events-out",default="overall/a-share-resource-price-inventory-events.csv");p.add_argument("--out-json",default="overall/a-share-resource-price-inventory-result.json");p.add_argument("--out-md",default="overall/a-share-resource-price-inventory-result.md");a=p.parse_args(argv);payload=run(a.daily,a.warehouse,a.sector,a.panel_out,a.events_out,a.out_json,a.out_md);print(json.dumps(payload["summary"],ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
