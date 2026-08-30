"""Find frozen historical analogs for the current pharma-versus-chemical state."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
FEATURES=("triple_growth_breadth_pct","ocf_positive_breadth_pct","pe_median_pct","positive_revision_breadth_pct","median_revision_pct","ma20_breadth_pct","relative20_pct");SEED=20260829
def bootstrap(values):
 x=np.asarray(values,float);rng=np.random.default_rng(SEED);means=[float(x[rng.integers(0,len(x),len(x))].mean()) for _ in range(2000)];return [float(np.quantile(means,.025)),float(np.quantile(means,.975))]
def run(ledger,current_date):
 d=pd.read_csv(ledger);d["decision_date"]=pd.to_datetime(d.decision_date);current=pd.Timestamp(current_date);rows=[]
 for day,g in d.groupby("decision_date"):
  if set(g.industry)!={"医药生物","基础化工"}:continue
  x=g.set_index("industry");row={"decision_date":day,"pharma_future63":x.at["医药生物","future63"],"chemical_future63":x.at["基础化工","future63"],"current_market_ok":bool((x.market_coverage>=.9).all()),"current_financial_ok":bool((x.financial_coverage>=.6).all()),"current_analyst_ok":bool((x.analyst_coverage>=.3).all()),"pharma_score":x.at["医药生物","score"],"chemical_score":x.at["基础化工","score"]}
  for f in FEATURES:row[f]=x.at["医药生物",f]-x.at["基础化工",f]
  rows.append(row)
 states=pd.DataFrame(rows).sort_values("decision_date");cur=states[states.decision_date==current]
 if len(cur)!=1:raise RuntimeError(f"missing current state {current_date}")
 cur=cur.iloc[0];history=states[(states.decision_date<current)&(states.decision_date<=pd.Timestamp("2025-12-31"))].dropna(subset=list(FEATURES)+["pharma_future63","chemical_future63"]).copy();history["distance"]=np.sqrt(sum((history[f]-cur[f])**2 for f in FEATURES));selected=[]
 for r in history.sort_values(["distance","decision_date"]).itertuples(index=False):
  if all(abs((r.decision_date.to_period("M")-s.decision_date.to_period("M")).n)>=3 for s in selected):selected.append(r)
  if len(selected)>=10:break
 analog=pd.DataFrame(selected);analog["pharma_minus_chemical_3m"]=analog.pharma_future63-analog.chemical_future63;v=analog.pharma_minus_chemical_3m;ci=bootstrap(v) if len(v) else [np.nan,np.nan];pharma_win=float((v>0).mean()) if len(v) else 0.0;current_ok=bool(cur.current_market_ok and cur.current_financial_ok and cur.current_analyst_ok);direction="NO-SELECTION"
 if current_ok and len(v)>=8 and float(v.median())>=.03 and pharma_win>=.60 and ci[0]>0:direction="PHARMA"
 if current_ok and len(v)>=8 and float(v.median())<=-.03 and pharma_win<=.40 and ci[1]<0:direction="CHEMICAL"
 checks={"market":bool(cur.current_market_ok),"financial":bool(cur.current_financial_ok),"analyst":bool(cur.current_analyst_ok),"analogs":len(v)>=8,"median_abs":abs(float(v.median()))>=.03 if len(v) else False,"direction_share":max(pharma_win,1-pharma_win)>=.60,"bootstrap":bool(ci[0]>0 or ci[1]<0)}
 current_vector={f:float(cur[f]) for f in FEATURES};return {"study":"a-share-pharma-chemical-current-analogs-v1","current":{"date":current_date,"vector_pharma_minus_chemical":current_vector,"pharma_score":float(cur.pharma_score),"chemical_score":float(cur.chemical_score),"data_complete":current_ok},"analogs":analog[["decision_date","distance","pharma_future63","chemical_future63","pharma_minus_chemical_3m"]].assign(decision_date=lambda x:x.decision_date.dt.strftime("%Y-%m-%d")).to_dict("records"),"statistics":{"count":len(v),"mean":float(v.mean()),"median":float(v.median()),"pharma_win_rate":pharma_win,"bootstrap95":ci},"decision":{"verdict":direction,"checks":checks},"limitations":["current 2026H1 snapshot remains provider-source-bounded","nearest-neighbor history is non-virgin and small","relative direction is not positive absolute-return authority"]}
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--ledger",default="overall/a-share-pharma-chemical-rotation-monthly-current.csv");p.add_argument("--current-date",default="2026-08-27");p.add_argument("--out-json",default="overall/a-share-pharma-chemical-current-analogs.json");p.add_argument("--out-md",default="overall/a-share-pharma-chemical-current-analogs.md");a=p.parse_args(argv);payload=run(a.ledger,a.current_date);Path(a.out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n");s=payload["statistics"];c=payload["current"];text=f"# 医药—基础化工当前历史相似期\n\n- current: {a.current_date}\n- provisional verdict: **{payload['decision']['verdict']}**\n- current pharma/chemical score: {c['pharma_score']:.2f}/{c['chemical_score']:.2f}\n- analog count/mean/median/pharma win: {s['count']} / {s['mean']:.2%} / {s['median']:.2%} / {s['pharma_win_rate']:.2%}\n- bootstrap 95%: [{s['bootstrap95'][0]:.2%}, {s['bootstrap95'][1]:.2%}]\n";Path(a.out_md).write_text(text);print(text);return 0
if __name__=="__main__":raise SystemExit(main())
