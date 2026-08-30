"""Append the latest attention state to the frozen zero-capital forward ledger."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import pandas as pd
FREEZE_DATE=pd.Timestamp("2026-08-27");KEYS=["as_of","record_type","industry","signal_date"]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def run(states_path,event_states_path,raw_manifest_path,result_path,ledger_path,manifest_path,out_md,as_of=None):
 states=pd.read_csv(states_path);states["decision_date"]=pd.to_datetime(states.decision_date);events=pd.read_csv(event_states_path);events["decision_date"]=pd.to_datetime(events.decision_date);latest=states.decision_date.max();day=pd.Timestamp(as_of) if as_of else latest;raw_hash=sha(raw_manifest_path);states_hash=sha(states_path);verdict=json.loads(Path(result_path).read_text())["stock"]["verdict"];columns=["as_of","record_type","industry","signal_date","state","evidence_eligible","trade_authorized","appeared_count","industry_new_entries","industry_breadth","breadth_pct","breadth_shock","top_symbols","return_d30","return_d35","return_d40","active_d30","active_d35","active_d40","observed_days","raw_manifest_sha256","states_sha256","historical_verdict","rejection_reason"]
 ledger=pd.read_csv(ledger_path,dtype=str).fillna("") if Path(ledger_path).exists() else pd.DataFrame(columns=columns);records=[];snapshot=states[states.decision_date.eq(day)]
 def record(record_type,industry="",signal_date="",state="",eligible=False,row=None,reason=""):
  return {"as_of":day.date().isoformat(),"record_type":record_type,"industry":industry,"signal_date":signal_date,"state":state,"evidence_eligible":str(bool(eligible)).lower(),"trade_authorized":"false","appeared_count":getattr(row,"appeared_count","") if row is not None else "","industry_new_entries":getattr(row,"industry_new_entries","") if row is not None else "","industry_breadth":getattr(row,"industry_breadth","") if row is not None else "","breadth_pct":getattr(row,"breadth_pct","") if row is not None else "","breadth_shock":getattr(row,"breadth_shock","") if row is not None else "","top_symbols":getattr(row,"top_symbols","") if row is not None else "","return_d30":"","return_d35":"","return_d40":"","active_d30":"","active_d35":"","active_d40":"","observed_days":"","raw_manifest_sha256":raw_hash,"states_sha256":states_hash,"historical_verdict":verdict,"rejection_reason":reason}
 if snapshot.empty:records.append(record("SOURCE_MISSING",reason="no valid final snapshot for as_of"))
 else:
  active=snapshot[snapshot.status.isin(["ENTER","ATTENTION_SEED"])]
  if day<=FREEZE_DATE:
   for row in active.itertuples(index=False):records.append(record("BASELINE_ONLY",row.industry,"",row.status,False,row,"signal on or before freeze date"))
  else:
   for row in active.itertuples(index=False):records.append(record("DAILY_STATE",row.industry,"",row.status,False,row,"state observation only"))
   new=events[events.decision_date.gt(FREEZE_DATE)&events.decision_date.le(day)]
   for row in new.itertuples(index=False):records.append(record("FORWARD_EVENT",row.industry,row.decision_date.date().isoformat(),"ENTER",True,row,""))
  if not records:records.append(record("NO-NEW-EVENT",reason="no active state or forward event"))
 update=pd.DataFrame(records,columns=columns).fillna("");combined=pd.concat([ledger,update],ignore_index=True).fillna("").drop_duplicates(KEYS,keep="last").sort_values(KEYS);combined.to_csv(ledger_path,index=False);manifest={"freeze_date":FREEZE_DATE.date().isoformat(),"as_of":day.date().isoformat(),"rows":len(combined),"evidence_eligible_events":int(combined.record_type.eq("FORWARD_EVENT").sum()),"trade_authorized":False,"raw_manifest_sha256":raw_hash,"states_sha256":states_hash,"ledger_sha256":sha(ledger_path)};Path(manifest_path).write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n");counts=combined[combined.as_of.eq(day.date().isoformat())].record_type.value_counts().to_dict();Path(out_md).write_text("# A股关注热度前向Shadow\n\n"+f"- as of: {day.date().isoformat()}\n- freeze date: {FREEZE_DATE.date().isoformat()}\n- records: {json.dumps(counts,ensure_ascii=False)}\n- evidence eligible events: {manifest['evidence_eligible_events']}\n- trade authorized: **NO**\n");return manifest
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--states",default="overall/a-share-attention-states.csv");p.add_argument("--event-states",default="overall/a-share-attention-event-states.csv");p.add_argument("--raw-manifest",default="overall/a-share-attention-raw/manifest.json");p.add_argument("--result",default="overall/a-share-attention-result.json");p.add_argument("--ledger",default="overall/a-share-attention-forward-shadow-ledger.csv");p.add_argument("--manifest",default="overall/a-share-attention-forward-shadow-manifest.json");p.add_argument("--out-md",default="overall/a-share-attention-forward-shadow-ledger.md");p.add_argument("--as-of");a=p.parse_args(argv);print(json.dumps(run(a.states,a.event_states,a.raw_manifest,a.result,a.ledger,a.manifest,a.out_md,a.as_of),ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
