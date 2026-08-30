"""Render the confirmed event-level path metrics and schema manifest."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import pandas as pd
FIELDS=["event_id","signal_date","industry","score","status","observed_days","return_d30","return_d35","return_d40","active_d30","active_d35","active_d40","max_return_40","max_return_day","max_return_date","min_return_40","min_return_day","min_return_date","max_active_40","max_active_day","max_active_date","min_active_40","min_active_day","min_active_date","days_outperform_hs300_40","outperform_ratio_40","success_d35","rejection_reason"]
def fmt(value,percent=False):
 if pd.isna(value):return ""
 return f"{float(value):.2%}" if percent else str(value)
def run(events_path,markdown_path,manifest_path):
 source=Path(events_path);d=pd.read_csv(source);missing=[field for field in FIELDS if field not in d.columns]
 if missing:raise ValueError(f"missing event path fields: {missing}")
 lines=["# A股周度行业周期逐事件路径结果","",f"- source: `{events_path}`",f"- rows: {len(d)}；valid: {(d.status=='VALID').sum()}；invalid: {(d.status!='VALID').sum()}","","|信号日|行业|状态|分数|观察日|30日|35日|40日|最高收益(日/日期)|最低收益(日/日期)|最高超额|最低超额|跑赢天数|成功|拒绝原因|","|---|---|---|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---|---|"]
 for r in d.itertuples(index=False):
  maximum=f"{fmt(r.max_return_40,True)} ({fmt(r.max_return_day)}/{fmt(r.max_return_date)})" if pd.notna(r.max_return_40) else "";minimum=f"{fmt(r.min_return_40,True)} ({fmt(r.min_return_day)}/{fmt(r.min_return_date)})" if pd.notna(r.min_return_40) else "";days=f"{fmt(r.days_outperform_hs300_40)}/{fmt(r.observed_days)}" if pd.notna(r.days_outperform_hs300_40) else ""
  lines.append(f"|{r.signal_date}|{r.industry}|{r.status}|{fmt(r.score)}|{fmt(r.observed_days)}|{fmt(r.return_d30,True)}|{fmt(r.return_d35,True)}|{fmt(r.return_d40,True)}|{maximum}|{minimum}|{fmt(r.max_active_40,True)}|{fmt(r.min_active_40,True)}|{days}|{fmt(r.success_d35)}|{fmt(r.rejection_reason)}|")
 Path(markdown_path).write_text("\n".join(lines)+"\n");digest=hashlib.sha256(source.read_bytes()).hexdigest();manifest={"source":{"path":events_path,"sha256":digest},"rows":len(d),"valid_rows":int((d.status=="VALID").sum()),"invalid_rows":int((d.status!="VALID").sum()),"required_fields":FIELDS,"invalid_fields_remain_null":True,"markdown":markdown_path};Path(manifest_path).write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n");return manifest
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--events",default="overall/a-share-weekly-industry-events.csv");p.add_argument("--markdown",default="overall/a-share-weekly-industry-event-path-results.md");p.add_argument("--manifest",default="overall/a-share-weekly-industry-event-path-results-manifest.json");a=p.parse_args(argv);print(json.dumps(run(a.events,a.markdown,a.manifest),ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
