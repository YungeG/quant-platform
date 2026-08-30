"""Project absorption diffusion dates into executable frozen focus baskets."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd
def run(waves_path,panel_path,out_path):
 waves=pd.read_csv(waves_path);waves=waves[waves.diffusion_date.notna()].copy();panel=pd.read_csv(panel_path);states=waves.merge(panel[["trade_date","sector","focus_symbols"]],left_on=["diffusion_date","sector"],right_on=["trade_date","sector"],how="left");states=states.rename(columns={"diffusion_date":"decision_date","sector":"industry","focus_symbols":"top_symbols"});states["entry_event"]=True;states["score"]=100.0;states[["decision_date","industry","score","entry_event","top_symbols"]].to_csv(out_path,index=False);return {"events":len(states),"targets_ge10":int(states.top_symbols.apply(lambda value:len(json.loads(value)) if isinstance(value,str) else 0).ge(10).sum()),"output":out_path}
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--waves",default="overall/a-share-turnover-absorption-waves.csv");p.add_argument("--panel",default="overall/a-share-turnover-absorption-panel.csv");p.add_argument("--out",default="overall/a-share-turnover-absorption-event-states.csv");a=p.parse_args(argv);print(json.dumps(run(a.waves,a.panel,a.out),ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
