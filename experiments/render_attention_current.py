"""Render the latest non-authorizing attention risk dashboard."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd
def run(states_path,result_path,out_json,out_md):
 states=pd.read_csv(states_path);latest=states.decision_date.max();current=states[states.decision_date.eq(latest)&states.status.isin(["ENTER","ATTENTION_SEED"])][["industry","status","appeared_count","industry_new_entries","industry_breadth","breadth_pct","breadth_shock","top_symbols"]];result=json.loads(Path(result_path).read_text());payload={"as_of":latest,"authority":"research_risk_dashboard_only","trade_authorized":False,"historical_verdict":result["stock"]["verdict"],"industries":current.to_dict("records")};Path(out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n");lines=["# A股关注热度当前看板","",f"- as of: {latest}","- authority: **RESEARCH RISK DASHBOARD ONLY**","- trade authorized: **NO**",""]+[f"- {r.industry}: {r.status}, breadth {r.industry_breadth:.2%}, percentile {r.breadth_pct:.2%}, new entries {r.industry_new_entries}" for r in current.itertuples(index=False)];Path(out_md).write_text("\n".join(lines)+"\n");return payload
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--states",default="overall/a-share-attention-states.csv");p.add_argument("--result",default="overall/a-share-attention-result.json");p.add_argument("--out-json",default="overall/a-share-attention-current.json");p.add_argument("--out-md",default="overall/a-share-attention-current.md");a=p.parse_args(argv);print(json.dumps(run(a.states,a.result,a.out_json,a.out_md),ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
