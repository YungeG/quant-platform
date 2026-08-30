"""Select a ten-session true-breakout confirmation using discovery years only."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd
RETURN_LEVELS=(.04,.05,.06,.07,.08);ACTIVE_LEVELS=(.02,.03,.04,.05)
def run(features_path,out_json,out_md):
 x=pd.read_csv(features_path);x=x[x.year.between(2018,2022)].copy();truth=x.direct_true.astype(str).str.lower().eq("true");held=x.held_abs_10.astype(str).str.lower().eq("true")&x.held_rel_10.astype(str).str.lower().eq("true");rows=[]
 for return_min in RETURN_LEVELS:
  for active_min in ACTIVE_LEVELS:
   selected=held&x.progress_return_10.ge(return_min)&x.progress_active_10.ge(active_min);count=int(selected.sum());true=int((selected&truth).sum());rows.append({"confirmation_day":10,"return_min":return_min,"active_min":active_min,"signals":count,"true":true,"precision":true/count if count else 0.0,"recall":true/int(truth.sum())})
 eligible=[r for r in rows if r["signals"]>=30 and r["precision"]>=.60];selected=max(eligible,key=lambda r:(r["recall"],r["precision"],r["signals"],-r["return_min"],-r["active_min"]));payload={"discovery_period":"2018-2022","candidate_rules":rows,"eligibility":{"min_signals":30,"min_precision":.60},"selection_policy":"maximize recall, then precision, signals, lower return and active thresholds","selected_rule":selected};Path(out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n");lines=["# 真突破确认Discovery选择","",f"- selected: D10 held, return>={selected['return_min']:.0%}, active>={selected['active_min']:.0%}",f"- signals/precision/recall: {selected['signals']} / {selected['precision']:.2%} / {selected['recall']:.2%}","","|D10收益|D10 active|信号|精确率|召回率|","|---:|---:|---:|---:|---:|"]+[f"|{r['return_min']:.0%}|{r['active_min']:.0%}|{r['signals']}|{r['precision']:.2%}|{r['recall']:.2%}|" for r in rows];Path(out_md).write_text("\n".join(lines)+"\n");print("\n".join(lines[:4]));return payload
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--features",default="overall/a-share-sector-true-breakout-features.csv");p.add_argument("--out-json",default="overall/a-share-true-breakout-discovery.json");p.add_argument("--out-md",default="overall/a-share-true-breakout-discovery.md");a=p.parse_args(argv);run(a.features,a.out_json,a.out_md);return 0
if __name__=="__main__":raise SystemExit(main())
