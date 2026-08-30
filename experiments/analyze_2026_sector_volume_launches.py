"""Describe complete 2026 sector-launch volume paths and failed crossings."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import mannwhitneyu
from experiments.context_features import holm_adjust
PHASES={"quiet":(-20,-11),"preparation":(-10,-1),"start":(0,0),"ignition":(1,5),"expansion":(6,20),"follow_through":(21,40)};FEATURES=("amount_share","turnover_proxy","volume_breadth","up_amount_share","price_breadth","top5_amount_concentration")
def classify(row):
 if pd.isna(row.active_future35):return "INCOMPLETE_CROSS"
 if row.future35>0 and row.active_future35>=.08:return "LAUNCH"
 if row.active_future35<=0:return "FAILED"
 return "WEAK"
def run(panel_path,events_path,paths_path,summary_json,summary_md):
 panel=pd.read_csv(panel_path);panel.trade_date=pd.to_datetime(panel.trade_date);events=[];paths=[]
 for sector,g in panel.sort_values("trade_date").groupby("sector"):
  g=g.reset_index(drop=True);cross=(g.relative20>0)&(g.relative20.shift(1)<=0);last=-10**9
  for i in np.flatnonzero(cross.to_numpy()):
   if g.loc[i,"trade_date"].year!=2026 or i-last<60:continue
   last=i;row=g.loc[i];event_id=f"{row.trade_date.date()}|{sector}";kind=classify(row);events.append({"event_id":event_id,"signal_date":row.trade_date.date().isoformat(),"sector":sector,"event_type":kind,"future35":row.future35,"benchmark_future35":row.benchmark_future35,"active_future35":row.active_future35,"observed_forward_days":min(40,len(g)-i-1)})
   baseline=g.iloc[max(0,i-20):max(0,i-5)];base_amount=baseline.amount_share.median();base_turnover=baseline.turnover_proxy.median();
   for j in range(max(0,i-20),min(len(g),i+41)):
    item=g.loc[j];offset=j-i;paths.append({"event_id":event_id,"signal_date":row.trade_date.date().isoformat(),"sector":sector,"event_type":kind,"trade_date":item.trade_date.date().isoformat(),"day_offset":offset,"amount_share":item.amount_share,"amount_share_rel":item.amount_share/base_amount-1 if base_amount>0 else np.nan,"turnover_proxy":item.turnover_proxy,"turnover_rel":item.turnover_proxy/base_turnover-1 if base_turnover>0 else np.nan,"volume_breadth":item.volume_breadth,"up_amount_share":item.up_amount_share,"price_breadth":item.price_breadth,"top5_amount_concentration":item.top5_amount_concentration})
 event=pd.DataFrame(events);path=pd.DataFrame(paths);phase_rows=[]
 for event_id,g in path.groupby("event_id"):
  info=event[event.event_id==event_id].iloc[0];values={"event_id":event_id,"sector":info.sector,"event_type":info.event_type}
  for phase,(a,b) in PHASES.items():
   x=g[g.day_offset.between(a,b)]
   for feature in ["amount_share_rel","turnover_rel","volume_breadth","up_amount_share","price_breadth","top5_amount_concentration"]:values[f"{phase}_{feature}"]=float(x[feature].median()) if len(x) else np.nan
  ignition=values["ignition_amount_share_rel"];expansion=values["expansion_amount_share_rel"];start=values["start_amount_share_rel"];values["volume_pattern"]="SUSTAINED" if ignition>.10 and expansion>.10 else ("PULSE" if start>.20 and expansion<=0 else "MIXED");phase_rows.append(values)
 phases=pd.DataFrame(phase_rows);event=event.merge(phases,on=["event_id","sector","event_type"],how="left");event.to_csv(events_path,index=False);path.to_csv(paths_path,index=False);launch=event[event.event_type=="LAUNCH"];failed=event[event.event_type=="FAILED"];phase_summary={}
 for kind,g in event.groupby("event_type"):
  phase_summary[kind]={"count":len(g),"median_active35":float(g.active_future35.median()) if g.active_future35.notna().any() else None,"patterns":g.volume_pattern.value_counts().to_dict(),"median_phases":{column:float(g[column].median()) for column in g.columns if any(column.startswith(prefix+"_") for prefix in PHASES) and pd.api.types.is_numeric_dtype(g[column])}}
 compare_features=["preparation_amount_share_rel","preparation_turnover_rel","preparation_volume_breadth","start_amount_share_rel","start_turnover_rel","start_volume_breadth","start_up_amount_share","start_price_breadth","start_top5_amount_concentration"];comparisons=[];raw_p={}
 for feature in compare_features:
  a=launch[feature].dropna();b=failed[feature].dropna();p=float(mannwhitneyu(a,b,alternative="two-sided").pvalue);raw_p[feature]=p;comparisons.append({"feature":feature,"launch_median":float(a.median()),"failed_median":float(b.median()),"p":p})
 adjusted=holm_adjust(raw_p)
 for row in comparisons:row["holm_p"]=adjusted[row["feature"]]
 payload={"study":"a-share-2026-sector-volume-launches-v1","data":{"panel":panel_path,"events":len(event),"launches":len(launch),"failed":len(failed),"incomplete":int((event.event_type=="INCOMPLETE_CROSS").sum())},"phase_summary":phase_summary,"prestart_comparison":comparisons,"top_launches":launch.sort_values("active_future35",ascending=False)[["signal_date","sector","future35","active_future35","observed_forward_days","volume_pattern"]].to_dict("records"),"incomplete_crosses":event[event.event_type=="INCOMPLETE_CROSS"][["signal_date","sector","observed_forward_days","volume_pattern"]].to_dict("records"),"limitations":["2026-only descriptive sample","launch label uses future returns","volume patterns are not predictive validation"]};Path(summary_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n");lines=["# 2026年以来板块启动成交量全过程","",f"- crossings: {len(event)}；launches: {len(launch)}；failed: {len(failed)}；incomplete: {payload['data']['incomplete']}","","## 启动前可见差异","","|特征|启动中位数|失败中位数|Holm p|","|---|---:|---:|---:|"]
 for row in comparisons:lines.append(f"|{row['feature']}|{row['launch_median']:.2%}|{row['failed_median']:.2%}|{row['holm_p']:.4g}|")
 lines += ["","## 已完成启动事件","","|日期|板块|35日收益|35日超额|量能形态|静默成交占比变化|准备期|点火期|扩散期|","|---|---|---:|---:|---|---:|---:|---:|---:|"]
 for r in launch.sort_values("active_future35",ascending=False).itertuples(index=False):lines.append(f"|{r.signal_date}|{r.sector}|{r.future35:.2%}|{r.active_future35:.2%}|{r.volume_pattern}|{r.quiet_amount_share_rel:.2%}|{r.preparation_amount_share_rel:.2%}|{r.ignition_amount_share_rel:.2%}|{r.expansion_amount_share_rel:.2%}|")
 lines += ["","## 未走完35日的近期拐点","","|日期|板块|已观察日|量能形态|","|---|---|---:|---|"]
 for r in event[event.event_type=="INCOMPLETE_CROSS"].itertuples(index=False):lines.append(f"|{r.signal_date}|{r.sector}|{r.observed_forward_days}|{r.volume_pattern}|")
 Path(summary_md).write_text("\n".join(lines)+"\n");return payload
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--panel",default="overall/a-share-2026-sector-volume-panel.csv");p.add_argument("--events",default="overall/a-share-2026-sector-volume-events.csv");p.add_argument("--paths",default="overall/a-share-2026-sector-volume-paths.csv");p.add_argument("--out-json",default="overall/a-share-2026-sector-volume-launches.json");p.add_argument("--out-md",default="overall/a-share-2026-sector-volume-launches.md");a=p.parse_args(argv);payload=run(a.panel,a.events,a.paths,a.out_json,a.out_md);print(json.dumps(payload["data"],ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
