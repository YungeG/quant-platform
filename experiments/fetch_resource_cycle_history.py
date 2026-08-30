"""Fetch resumable continuous futures and warehouse-receipt histories for resource-cycle products."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from threading import Event
import pandas as pd,requests
PROXY_ENDPOINT="https://fast.xiaodefa.cn";PRODUCTS={"CU":"CUL.SHF","AL":"ALL.SHF","ZN":"ZNL.SHF","PB":"PBL.SHF","NI":"NIL.SHF","SN":"SNL.SHF","RB":"RBL.SHF","HC":"HCL.SHF","J":"JL.DCE","MA":"MAL.ZCE","PP":"PPL.DCE","L":"LL.DCE","V":"VL.DCE","RU":"RUL.SHF","FG":"FGL.ZCE"};FIELDS={"fut_daily":"ts_code,trade_date,open,high,low,close,settle,vol,amount,oi,oi_chg","fut_wsr":"trade_date,symbol,fut_name,warehouse,pre_vol,vol,vol_chg,unit"}
def call(token,api,params):
 last=""
 for attempt in range(15):
  try:
   r=requests.post(PROXY_ENDPOINT,headers={"x-api-key":token},json={"api_name":api,"params":params,"fields":FIELDS[api]},timeout=120);r.raise_for_status();p=r.json()
   if p.get("code")==0:
    d=p.get("data") or {};return [dict(zip(d.get("fields") or [],row,strict=True)) for row in (d.get("items") or [])],""
   raise RuntimeError(str(p.get("msg","proxy error")))
  except Exception as e:last=f"{type(e).__name__}: {e}";Event().wait(30 if "超速" in last or "429" in last else min(8,.5*2**attempt))
 return [],last
def year_chunks(start,end):
 a=pd.Timestamp(start);b=pd.Timestamp(end);return [(max(a,pd.Timestamp(f"{y}-01-01")).strftime("%Y%m%d"),min(b,pd.Timestamp(f"{min(y+1,b.year)}-12-31")).strftime("%Y%m%d")) for y in range(a.year,b.year+1,2)]
def month_chunks(start,end):return [(p.start_time.strftime("%Y%m%d"),p.end_time.strftime("%Y%m%d")) for p in pd.period_range(start,end,freq="M")]
def append(path,rows,keys):
 old=pd.read_parquet(path) if path.exists() else pd.DataFrame();d=pd.concat([old,pd.DataFrame(rows)],ignore_index=True)
 if len(d):d=d.drop_duplicates(keys,keep="last")
 d.to_parquet(path,index=False,compression="zstd")
def run(start,end,token_file,out_dir):
 token=Path(token_file).read_text().strip();out=Path(out_dir);out.mkdir(parents=True,exist_ok=True);qpath=out/"queries.csv";q=pd.read_csv(qpath,dtype=str) if qpath.exists() else pd.DataFrame(columns=["api","product","start","end","status","rows","error"])
 for product,continuous in PRODUCTS.items():
  done={(r.api,r.product,r.start,r.end) for r in q.itertuples(index=False) if r.status=="success"};updates=[];daily_rows=[];warehouse_rows=[]
  for a,b in year_chunks(start,end):
   if ("fut_daily",product,a,b) in done:continue
   rows,error=call(token,"fut_daily",{"ts_code":continuous,"start_date":a,"end_date":b});daily_rows.extend(rows);updates.append({"api":"fut_daily","product":product,"start":a,"end":b,"status":"success" if not error else "failed","rows":len(rows),"error":error});Event().wait(.1)
  for a,b in month_chunks(start,end):
   if ("fut_wsr",product,a,b) in done:continue
   rows,error=call(token,"fut_wsr",{"symbol":product,"start_date":a,"end_date":b});warehouse_rows.extend(rows);updates.append({"api":"fut_wsr","product":product,"start":a,"end":b,"status":"success" if not error else "failed","rows":len(rows),"error":error});Event().wait(.1)
  if daily_rows:append(out/"fut_daily.parquet",daily_rows,["ts_code","trade_date"])
  if warehouse_rows:append(out/"fut_wsr.parquet",warehouse_rows,["trade_date","symbol","warehouse","unit"])
  if updates:q=pd.concat([q,pd.DataFrame(updates)],ignore_index=True).drop_duplicates(["api","product","start","end"],keep="last").sort_values(["api","product","start"]);q.to_csv(qpath,index=False)
 manifest={"endpoint":PROXY_ENDPOINT,"start":start,"end":end,"products":PRODUCTS,"successful_queries":int(q.status.eq("success").sum()),"failed_queries":q[q.status.ne("success")].to_dict("records"),"outputs":{}}
 for name in ["fut_daily","fut_wsr"]:
  path=out/f"{name}.parquet";d=pd.read_parquet(path) if path.exists() else pd.DataFrame();manifest["outputs"][name]={"path":str(path),"rows":len(d),"sha256":hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None}
 (out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n");return manifest
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--start",default="2018-01-01");p.add_argument("--end",default="2026-08-27");p.add_argument("--token-file",default="/home/ygguo/.config/ai-crypt/xiaodefa-token");p.add_argument("--out-dir",default="overall/a-share-resource-cycle-raw");a=p.parse_args(argv);result=run(a.start,a.end,a.token_file,a.out_dir);print(json.dumps({k:result[k] for k in ["successful_queries","failed_queries","outputs"]},ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
