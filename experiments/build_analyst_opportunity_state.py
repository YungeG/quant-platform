"""Build a canonical monthly state table for analyst-revision opportunities."""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np,pandas as pd
FEATURES=("positive_revision_breadth","median_revision","top30_revision","coverage","paired_count")
def trailing_pct(values):
 out=[]
 for i,value in enumerate(values):
  history=pd.Series(values[max(0,i-59):i+1]).dropna()
  out.append(float((history<=value).mean()) if pd.notna(value) and len(history)>=12 else np.nan)
 return out
def run(signals_path,out_path):
 signals=pd.read_csv(signals_path);signals["signal_date"]=pd.to_datetime(signals.signal_date);rows=[]
 for day,g in signals.groupby("signal_date"):
  valid=g.dropna(subset=["revision"]);selected=valid[valid.revision>0].sort_values(["revision","paired_count","symbol"],ascending=[False,False,True]).head(30);active=selected.active20.dropna();rows.append({"decision_date":day,"positive_revision_breadth":float((valid.revision>0).mean()) if len(valid) else np.nan,"median_revision":float(valid.revision.median()) if len(valid) else np.nan,"top30_revision":float(selected.revision.median()) if len(selected) else np.nan,"coverage":len(valid),"paired_count":float(valid.paired_count.median()) if len(valid) else np.nan,"outcome":float(active.mean()-.0031) if len(active)==len(selected) and len(selected)>=10 else np.nan,"selected_count":len(selected)})
 state=pd.DataFrame(rows).sort_values("decision_date").reset_index(drop=True)
 for feature in FEATURES:state[feature+"_pct"]=trailing_pct(state[feature].tolist())
 state["current_complete"]=(state.coverage>=300)&(state.selected_count>=10)&state[[f+"_pct" for f in FEATURES]].notna().all(axis=1);state.to_csv(out_path,index=False,date_format="%Y-%m-%d");return state
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--signals",default="overall/a-share-analyst-revision-signals.csv");p.add_argument("--out",default="overall/a-share-analyst-opportunity-state.csv");a=p.parse_args(argv);state=run(a.signals,a.out);print(state.tail(3).to_string(index=False));return 0
if __name__=="__main__":raise SystemExit(main())
