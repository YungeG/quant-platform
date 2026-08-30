"""Build V3 three-session-held, low-breadth confirmed positions against fixed trend labels."""
from __future__ import annotations
import argparse,json
import numpy as np,pandas as pd
def run(panel_path,features_path,base_labels_path,positions_path,labels_path):
 panel=pd.read_csv(panel_path);panel["trade_date"]=pd.to_datetime(panel.trade_date);panel=panel[panel.sector.ne("半导体")].sort_values(["sector","trade_date"]);features=pd.read_csv(features_path);features["signal_date"]=pd.to_datetime(features.signal_date);held=features.held_abs_3.astype(str).str.lower().eq("true")&features.held_rel_3.astype(str).str.lower().eq("true");selected=features[held&features.price_breadth.le(.65)].copy();positions=[]
 for sector,g in panel.groupby("sector"):
  g=g.reset_index(drop=True).copy();g["relative_index"]=g.sector_index/g.benchmark_index;g["rel_low10_prev"]=g.relative_index.shift(1).rolling(10,min_periods=10).min();lookup={d:i for i,d in enumerate(g.trade_date)};last_exit=-1
  for row in selected[selected.sector.eq(sector)].sort_values("signal_date").itertuples(index=False):
   start=lookup.get(pd.Timestamp(row.signal_date));confirm=start+3 if start is not None else None
   if confirm is None or confirm>=len(g) or confirm<=last_exit:continue
   exit_index=len(g)-1;reason="OPEN"
   for j in range(confirm+1,min(len(g),confirm+36)):
    if g.at[j,"relative_index"]<g.at[j,"rel_low10_prev"]:exit_index=j;reason="relative_10d_low";break
    if j-confirm>=35:exit_index=j;reason="max_35_sessions";break
   position_id=f"{sector}|{g.at[confirm,'trade_date'].date()}";positions.append({"position_id":position_id,"sector":sector,"provisional_signal_date":row.signal_date,"entry_signal_date":g.at[confirm,"trade_date"],"entry_index":confirm,"exit_signal_date":g.at[exit_index,"trade_date"] if reason!="OPEN" else pd.NaT,"exit_index":exit_index,"exit_reason":reason,"initial_price_breadth":row.price_breadth,"holding_signal_sessions":exit_index-confirm});last_exit=exit_index
 fixed=pd.read_csv(base_labels_path);fixed["trend_start"]=pd.to_datetime(fixed.trend_start);fixed["trend_end"]=pd.to_datetime(fixed.trend_end);out_labels=[]
 for sector,g in panel.groupby("sector"):
  g=g.reset_index(drop=True);sector_positions=[p for p in positions if p["sector"]==sector]
  for row in fixed[fixed.sector.eq(sector)].itertuples(index=False):
   i=int(row.start_index);matched=[p for p in sector_positions if p["entry_index"]<=i<=p["exit_index"] or i<=p["entry_index"]<=i+10];match=min(matched,key=lambda p:(0 if p["entry_index"]<=i else p["entry_index"]-i,p["entry_index"])) if matched else None;delay=0 if match and match["entry_index"]<=i else match["entry_index"]-i if match else None;capture_start=max(i,match["entry_index"]) if match else None;remaining=g.at[i+20,"sector_index"]/g.at[capture_start,"sector_index"]-1 if match else None;record=row._asdict();record.update({"detected":bool(match),"position_id":match["position_id"] if match else "","detection_delay":delay,"remaining_return":remaining,"capture_ratio":remaining/row.forward20 if match and row.forward20 else None});out_labels.append(record)
 pd.DataFrame(positions).to_csv(positions_path,index=False,date_format="%Y-%m-%d");pd.DataFrame(out_labels).to_csv(labels_path,index=False,date_format="%Y-%m-%d");return {"selected_provisional":len(selected),"positions":len(positions),"detected_labels":sum(bool(x["detected"]) for x in out_labels),"positions_path":positions_path,"labels_path":labels_path}
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--panel",default="overall/a-share-sector-daily-2017-2026.csv");p.add_argument("--features",default="overall/a-share-sector-false-breakout-features.csv");p.add_argument("--base-labels",default="overall/a-share-sector-month-trend-labels.csv");p.add_argument("--positions",default="overall/a-share-sector-confirmed-breakout-positions.csv");p.add_argument("--labels",default="overall/a-share-sector-confirmed-breakout-labels.csv");a=p.parse_args(argv);print(json.dumps(run(a.panel,a.features,a.base_labels,a.positions,a.labels),ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
