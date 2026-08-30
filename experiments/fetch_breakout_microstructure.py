"""Fetch frozen breakout event-window 5-minute and opening-auction data."""
from __future__ import annotations
import argparse,hashlib,json
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from threading import Event
import pandas as pd,requests
PROXY_ENDPOINT="https://fast.xiaodefa.cn"
ROLES={"breakout":"breakout_date","retest":"retest_date","signal":"signal_date","entry":"entry_date"}

def code(symbol):
 s=str(symbol).zfill(6)
 return f"{s}.BJ" if s.startswith(("4","8","9")) else (f"{s}.SH" if s.startswith(("5","6")) else f"{s}.SZ")
def truth(v):return v is True or str(v).lower()=="true"
def call(token,kind,symbol,date):
 api="stk_mins" if kind=="mins" else "stk_auction_o";params={"ts_code":symbol,"start_date":f"{date[:4]}-{date[4:6]}-{date[6:]} 09:00:00","end_date":f"{date[:4]}-{date[4:6]}-{date[6:]} 15:30:00","freq":"5min"} if kind=="mins" else {"ts_code":symbol,"trade_date":date}
 last=""
 for attempt in range(15):
  try:
   r=requests.post(PROXY_ENDPOINT,headers={"x-api-key":token},json={"api_name":api,"params":params,"fields":""},timeout=120)
   if r.status_code==429:raise RuntimeError("HTTP 429")
   r.raise_for_status();p=r.json()
   if p.get("code")==0:
    d=p.get("data") or {};f=list(d.get("fields") or []);return {"kind":kind,"symbol":symbol,"date":date,"ok":True,"records":[dict(zip(f,x,strict=True)) for x in list(d.get("items") or [])],"error":""}
   raise RuntimeError(str(p.get("msg","proxy API error")))
  except Exception as e:
   last=f"{type(e).__name__}: {e}"
   if "超速" in last or "429" in last:Event().wait(30)
   else:Event().wait(min(8,2**attempt*.5))
 return {"kind":kind,"symbol":symbol,"date":date,"ok":False,"records":[],"error":last}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(events_path,token_file,out_dir,workers):
 out=Path(out_dir);out.mkdir(parents=True,exist_ok=True);events=pd.read_csv(events_path,dtype={"symbol":str});events=events[events.execution_reason=="executed"].copy();maps=[]
 for r in events.itertuples(index=False):
  for role,col in ROLES.items():
   value=getattr(r,col)
   if pd.isna(value):continue
   date=pd.Timestamp(value).strftime("%Y%m%d");maps.append({"event_id":r.event_id,"role":role,"symbol":str(r.symbol).zfill(6),"ts_code":code(r.symbol),"date":date,"request_key":f"mins|{code(r.symbol)}|{date}"})
 mapping=pd.DataFrame(maps);mapping.to_csv(out/"event_roles.csv",index=False);requests_set={("mins",r.ts_code,r.date) for r in mapping.itertuples(index=False)}|{("auction",r.ts_code,r.date) for r in mapping[mapping.role=="entry"].itertuples(index=False)}
 qpath=out/"queries.csv";prior=pd.read_csv(qpath,dtype=str) if qpath.exists() else pd.DataFrame();done={(r.kind,r.symbol,r.date) for r in prior.itertuples(index=False) if truth(r.ok)} if len(prior) else set();pending=sorted(requests_set-done);token=Path(token_file).read_text().strip();results=[]
 with ThreadPoolExecutor(max_workers=workers) as ex:
  futures=[ex.submit(call,token,*req) for req in pending]
  for f in as_completed(futures):results.append(f.result())
 qrecords=(prior.to_dict("records") if len(prior) else [])+[{"kind":r["kind"],"symbol":r["symbol"],"date":r["date"],"ok":r["ok"],"row_count":len(r["records"]),"error":r["error"]} for r in results];q=pd.DataFrame(qrecords).drop_duplicates(["kind","symbol","date"],keep="last").sort_values(["kind","date","symbol"]);q.to_csv(qpath,index=False)
 paths={"mins":out/"mins.csv","auction":out/"auction.csv"}
 for kind,path in paths.items():
  old=pd.read_csv(path).to_dict("records") if path.exists() and path.stat().st_size>1 else [];new=[{"request_symbol":r["symbol"],"request_date":r["date"],**x} for r in results if r["kind"]==kind for x in r["records"]];frame=pd.DataFrame(old+new)
  if len(frame):frame=frame.drop_duplicates(keep="last")
  frame.to_csv(path,index=False)
 success=q.ok.map(truth);manifest={"endpoint":PROXY_ENDPOINT,"events":len(events),"event_roles":len(mapping),"unique_minute_requests":sum(k[0]=="mins" for k in requests_set),"unique_auction_requests":sum(k[0]=="auction" for k in requests_set),"query_success_rate":float(success.mean()),"kind_success_rates":{k:float(success[q.kind==k].mean()) for k in ("mins","auction")},"row_counts":{k:(len(pd.read_csv(p)) if p.exists() and p.stat().st_size>1 else 0) for k,p in paths.items()},"role_counts":mapping.role.value_counts().to_dict(),"outputs":{"event_roles":{"path":str(out/"event_roles.csv"),"sha256":sha(out/"event_roles.csv")},"queries":{"path":str(qpath),"sha256":sha(qpath)},**{k:{"path":str(p),"sha256":sha(p)} for k,p in paths.items()}}};(out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n");return manifest
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--events",default="overall/a-share-breakout-retest-v2-events.csv");p.add_argument("--token-file",default="/home/ygguo/.config/ai-crypt/xiaodefa-token");p.add_argument("--out-dir",default="overall/a-share-breakout-microstructure-raw");p.add_argument("--workers",type=int,default=4);a=p.parse_args(argv);print(json.dumps(run(a.events,a.token_file,a.out_dir,a.workers),ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
