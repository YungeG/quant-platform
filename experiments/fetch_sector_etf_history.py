"""Fetch chunked, resumable daily histories for frozen sector ETF candidates."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from threading import Event
import pandas as pd,requests
PROXY_ENDPOINT="https://fast.xiaodefa.cn";FIELDS={"fund_daily":"ts_code,trade_date,pre_close,open,high,low,close,pct_chg,vol,amount","fund_adj":"ts_code,trade_date,adj_factor","fund_share":"ts_code,trade_date,fd_share,fund_type,market"}
def fetch(token,api,code,start,end):
 last=""
 for attempt in range(15):
  try:
   r=requests.post(PROXY_ENDPOINT,headers={"x-api-key":token},json={"api_name":api,"params":{"ts_code":code,"start_date":start,"end_date":end},"fields":FIELDS[api]},timeout=120);r.raise_for_status();p=r.json()
   if p.get("code")==0:
    d=p.get("data") or {};return [dict(zip(d.get("fields") or [],row,strict=True)) for row in (d.get("items") or [])],""
   raise RuntimeError(str(p.get("msg","proxy error")))
  except Exception as e:last=f"{type(e).__name__}: {e}";Event().wait(30 if "超速" in last or "429" in last else min(8,.5*2**attempt))
 return [],last
def chunks(start,end):
 first=pd.Timestamp(start);last=pd.Timestamp(end);result=[]
 for year in range(first.year,last.year+1,2):result.append((max(first,pd.Timestamp(f"{year}-01-01")).strftime("%Y%m%d"),min(last,pd.Timestamp(f"{min(year+1,last.year)}-12-31")).strftime("%Y%m%d")))
 return result
def append_parquet(path,rows):
 old=pd.read_parquet(path) if path.exists() else pd.DataFrame();frame=pd.concat([old,pd.DataFrame(rows)],ignore_index=True)
 if len(frame):frame=frame.drop_duplicates(["ts_code","trade_date"],keep="last")
 frame.to_parquet(path,index=False,compression="zstd")
def run(candidates,start,end,token_file,out_dir):
 token=Path(token_file).read_text().strip();out=Path(out_dir);out.mkdir(parents=True,exist_ok=True);codes=sorted(pd.read_csv(candidates,dtype=str).ts_code.unique());qpath=out/"queries.csv";q=pd.read_csv(qpath,dtype=str) if qpath.exists() else pd.DataFrame(columns=["api","ts_code","chunk_start","chunk_end","status","rows","error"])
 for code in codes:
  done={(r.api,r.ts_code,r.chunk_start,r.chunk_end) for r in q.itertuples(index=False) if r.status=="success"};records={api:[] for api in FIELDS};updates=[]
  for chunk_start,chunk_end in chunks(start,end):
   for api in FIELDS:
    if (api,code,chunk_start,chunk_end) in done:continue
    rows,error=fetch(token,api,code,chunk_start,chunk_end);records[api].extend(rows);updates.append({"api":api,"ts_code":code,"chunk_start":chunk_start,"chunk_end":chunk_end,"status":"success" if not error else "failed","rows":len(rows),"error":error});Event().wait(.1)
  if not updates:continue
  for api,rows in records.items():append_parquet(out/f"{api}.parquet",rows)
  q=pd.concat([q,pd.DataFrame(updates)],ignore_index=True).drop_duplicates(["api","ts_code","chunk_start","chunk_end"],keep="last").sort_values(["api","ts_code","chunk_start"]);q.to_csv(qpath,index=False)
 manifest={"endpoint":PROXY_ENDPOINT,"start":start,"end":end,"codes":len(codes),"successful_queries":int(q.status.eq("success").sum()),"failed_queries":q[q.status.ne("success")][["api","ts_code","chunk_start","chunk_end","error"]].to_dict("records"),"outputs":{}}
 for api in FIELDS:
  path=out/f"{api}.parquet";d=pd.read_parquet(path) if path.exists() else pd.DataFrame();manifest["outputs"][api]={"path":str(path),"rows":len(d),"codes":d.ts_code.nunique() if len(d) else 0,"min_date":str(d.trade_date.min()) if len(d) else None,"max_date":str(d.trade_date.max()) if len(d) else None,"sha256":hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None}
 (out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n");return manifest
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--candidates",default="overall/a-share-sector-etf-candidates.csv");p.add_argument("--start",default="2018-01-01");p.add_argument("--end",default="2026-08-27");p.add_argument("--token-file",default="/home/ygguo/.config/ai-crypt/xiaodefa-token");p.add_argument("--out-dir",default="overall/a-share-sector-etf-raw-v2");a=p.parse_args(argv);result=run(a.candidates,a.start,a.end,a.token_file,a.out_dir);print(json.dumps({k:result[k] for k in ["codes","successful_queries","failed_queries"]},ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
