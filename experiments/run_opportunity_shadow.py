"""Evaluate frozen opportunity specs and append a zero-capital Shadow ledger."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from typing import Any, Mapping
import pandas as pd
from experiments.opportunity_engine import OpportunityReport,OpportunitySpec,evaluate_opportunities
SUPPORTED_KINDS={"relative_industry_v1","monthly_signal_state_v1"}
LEDGER_COLUMNS=("observation_id","as_of","opportunity_id","status","selection","reason","analog_count","mean","median","direction_share","bootstrap_low","bootstrap_high","snapshot_sha256","catalog_sha256","trade_authorized")
def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def canonical_hash(value:Mapping[str,Any])->str:return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def build_relative_state(source:Path,value:Mapping[str,Any])->tuple[pd.DataFrame,dict[str,Any]]:
 d=pd.read_csv(source);d["decision_date"]=pd.to_datetime(d.decision_date,format="mixed",errors="coerce")
 if d.decision_date.isna().any():raise ValueError("relative-industry source contains invalid dates")
 left=str(value["left"]);right=str(value["right"]);features=[str(item) for item in value["features"]];outcome=str(value.get("source_outcome_column","future63"));rows=[]
 for day,g in d.groupby("decision_date"):
  x=g.set_index("industry")
  if left not in x.index or right not in x.index:continue
  if x.index.duplicated().any():raise ValueError(f"duplicate industry state on {day.date()}")
  row={"decision_date":day,"outcome":_difference(x,left,right,outcome)}
  for feature in features:row[feature]=_difference(x,left,right,feature)
  row["current_complete"]=all(float(x.at[side,rule["column"]])>=float(rule["minimum"]) for rule in value.get("coverage_rules",[]) for side in (left,right))
  rows.append(row)
 table=pd.DataFrame(rows).sort_values("decision_date").reset_index(drop=True);current=d[d.decision_date==pd.Timestamp(value["as_of"])].set_index("industry") if "as_of" in value else pd.DataFrame();metadata={"source":str(source),"source_sha256":sha(source),"left":left,"right":right}
 if len(current) and "score" in current.columns:metadata["current_scores"]={left:_optional_float(current.at[left,"score"]),right:_optional_float(current.at[right,"score"])}
 return table,metadata
def build_monthly_signal_state(source:Path,value:Mapping[str,Any])->tuple[pd.DataFrame,dict[str,Any]]:
 d=pd.read_csv(source);date_column=str(value.get("date_column","decision_date"));d[date_column]=pd.to_datetime(d[date_column],format="mixed",errors="coerce")
 if d[date_column].isna().any() or d[date_column].duplicated().any():raise ValueError("monthly-signal source requires unique valid dates")
 required={date_column,str(value.get("source_outcome_column","outcome")),str(value.get("current_complete_column","current_complete")),*value["features"]};missing=sorted(required.difference(d.columns))
 if missing:raise ValueError(f"monthly-signal source missing columns: {missing}")
 outcome=str(value.get("source_outcome_column","outcome"));complete=str(value.get("current_complete_column","current_complete"));table=d[[date_column,*value["features"],outcome,complete]].rename(columns={outcome:"outcome",complete:"current_complete"});return table,{"source":str(source),"source_sha256":sha(source)}

def run(catalog_path:str,report_path:str,ledger_path:str,as_of_override:str|None=None)->dict[str,Any]:
 catalog_file=Path(catalog_path);catalog=json.loads(catalog_file.read_text());
 if catalog.get("version")!=1:raise ValueError("unsupported opportunity catalog version")
 as_of=str(as_of_override or catalog["as_of"]);decisions=[];sources=[]
 for raw in catalog.get("opportunities",[]):
  kind=raw.get("kind")
  if kind not in SUPPORTED_KINDS:raise ValueError(f"unsupported opportunity kind: {kind}")
  opportunity_as_of=str(as_of_override or raw.get("as_of") or as_of);value={**raw,"as_of":opportunity_as_of};source=Path(value["source"])
  table,metadata=(build_relative_state(source,value) if kind=="relative_industry_v1" else build_monthly_signal_state(source,value));spec=OpportunitySpec.from_mapping({**value,"outcome_column":"outcome","date_column":"decision_date","current_complete_column":"current_complete"});report=evaluate_opportunities(table,opportunity_as_of,[spec]);decisions.extend(report.decisions);sources.append(metadata)
 report=OpportunityReport(as_of=as_of,decisions=tuple(decisions));catalog_sha=sha(catalog_file);payload={"catalog":{"path":str(catalog_file),"sha256":catalog_sha},"sources":sources,"capital":int(catalog.get("capital",0)),"trade_authorized":bool(catalog.get("trade_authorized",False)),**report.to_dict()};Path(report_path).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n");append_ledger(Path(ledger_path),payload);return payload
def append_ledger(path:Path,payload:Mapping[str,Any])->None:
 existing=pd.read_csv(path,dtype=str) if path.exists() and path.stat().st_size else pd.DataFrame(columns=LEDGER_COLUMNS);rows=[];source_hashes={item["source"]:item["source_sha256"] for item in payload["sources"]};snapshot_hash=canonical_hash(source_hashes)
 for decision in payload["decisions"]:
  evidence=decision.get("evidence") or {};interval=evidence.get("bootstrap95") or [None,None];positive=evidence.get("positive_share");selection=decision.get("selection");direction_share=(1-positive if selection in {"CHEMICAL","RIGHT"} and positive is not None else positive);identity=canonical_hash({"as_of":decision["as_of"],"opportunity_id":decision["opportunity_id"],"snapshot_sha256":snapshot_hash,"catalog_sha256":payload["catalog"]["sha256"]});rows.append({"observation_id":identity,"as_of":decision["as_of"],"opportunity_id":decision["opportunity_id"],"status":decision["status"],"selection":selection,"reason":decision["reason"],"analog_count":evidence.get("count",0),"mean":evidence.get("mean"),"median":evidence.get("median"),"direction_share":direction_share,"bootstrap_low":interval[0],"bootstrap_high":interval[1],"snapshot_sha256":snapshot_hash,"catalog_sha256":payload["catalog"]["sha256"],"trade_authorized":False})
 added=pd.DataFrame(rows);combined=(added if existing.empty else pd.concat([existing,added],ignore_index=True)).drop_duplicates("observation_id",keep="last").reindex(columns=LEDGER_COLUMNS);combined.to_csv(path,index=False)
def _difference(frame:pd.DataFrame,left:str,right:str,column:str)->float:
 if column not in frame.columns:return float("nan")
 a=pd.to_numeric(pd.Series([frame.at[left,column]]),errors="coerce").iloc[0];b=pd.to_numeric(pd.Series([frame.at[right,column]]),errors="coerce").iloc[0];return float(a-b) if pd.notna(a) and pd.notna(b) else float("nan")
def _optional_float(value:Any)->float|None:return None if pd.isna(value) else float(value)
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--catalog",default="overall/a-share-opportunity-catalog-v1.json");p.add_argument("--report",default="overall/a-share-opportunity-report.json");p.add_argument("--ledger",default="overall/a-share-opportunity-shadow-ledger.csv");p.add_argument("--as-of");a=p.parse_args(argv);payload=run(a.catalog,a.report,a.ledger,a.as_of);print(json.dumps({"as_of":payload["as_of"],"decisions":[{"id":d["opportunity_id"],"status":d["status"],"selection":d["selection"],"reason":d["reason"]} for d in payload["decisions"]]},ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
