"""Select one interpretable false-breakout rule using discovery years only."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd
CAPS=(.50,.55,.60,.65,.70);KINDS=("held3","followthrough3")
def run(features_path,out_json,out_md):
 x=pd.read_csv(features_path);x=x[x.year.between(2018,2022)].copy();truth=x.true_trend.astype(str).str.lower().eq("true");held=x.held_abs_3.astype(str).str.lower().eq("true")&x.held_rel_3.astype(str).str.lower().eq("true");follow=x.followthrough_confirm3.astype(str).str.lower().eq("true");rows=[]
 for kind in KINDS:
  base=held if kind=="held3" else follow
  for cap in CAPS:
   selected=base&x.price_breadth.le(cap);count=int(selected.sum());true=int((selected&truth).sum());rows.append({"kind":kind,"breadth_cap":cap,"signals":count,"true":true,"precision":true/count if count else 0.0,"recall":true/int(truth.sum())})
 eligible=[r for r in rows if r["signals"]>=80 and r["precision"]>=.60];selected=max(eligible,key=lambda r:(r["recall"],r["precision"],r["signals"],-r["breadth_cap"],r["kind"]));payload={"discovery_period":"2018-2022","candidate_rules":rows,"eligibility":{"min_signals":80,"min_precision":.60},"selection_policy":"maximize recall, then precision, signals, lower breadth cap, lexical kind","selected_rule":selected};Path(out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n");lines=["# 假突破过滤Discovery选择","",f"- selected: `{selected['kind']}` and `price_breadth<={selected['breadth_cap']:.0%}`",f"- signals/precision/recall: {selected['signals']} / {selected['precision']:.2%} / {selected['recall']:.2%}","","|确认|广度上限|信号|精确率|召回率|","|---|---:|---:|---:|---:|"]+[f"|{r['kind']}|{r['breadth_cap']:.0%}|{r['signals']}|{r['precision']:.2%}|{r['recall']:.2%}|" for r in rows];Path(out_md).write_text("\n".join(lines)+"\n");print("\n".join(lines[:4]));return payload
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--features",default="overall/a-share-sector-false-breakout-features.csv");p.add_argument("--out-json",default="overall/a-share-sector-false-breakout-discovery.json");p.add_argument("--out-md",default="overall/a-share-sector-false-breakout-discovery.md");a=p.parse_args(argv);run(a.features,a.out_json,a.out_md);return 0
if __name__=="__main__":raise SystemExit(main())
