"""Fetch quarterly PIT statement inputs for the weekly industry-cycle study."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from threading import Event
import pandas as pd,requests
PROXY_ENDPOINT="https://fast.xiaodefa.cn";LIMITS={"fina_indicator_vip":12000,"income_vip":9000,"cashflow_vip":6400};FIELDS={"fina_indicator_vip":"ts_code,ann_date,end_date,tr_yoy,netprofit_yoy,dt_netprofit_yoy,roe_waa,update_flag","income_vip":"ts_code,ann_date,f_ann_date,end_date,n_income_attr_p,update_flag","cashflow_vip":"ts_code,ann_date,f_ann_date,end_date,n_cashflow_act,c_pay_acq_const_fiolta,update_flag"}
def periods(start,end):return [d.strftime("%Y%m%d") for d in pd.date_range(pd.Timestamp(start),pd.Timestamp(end),freq="QE")]
def fetch(token,api,period):
 rows=[];offset=0;schema=[]
 while True:
  last=""
  for attempt in range(15):
   try:
    r=requests.post(PROXY_ENDPOINT,headers={"x-api-key":token},json={"api_name":api,"params":{"period":period,"offset":offset},"fields":FIELDS[api]},timeout=120)
    if r.status_code==429:raise RuntimeError("HTTP 429")
    r.raise_for_status();p=r.json()
    if p.get("code")==0:break
    raise RuntimeError(str(p.get("msg","proxy error")))
   except Exception as e:last=f"{type(e).__name__}: {e}";Event().wait(30 if "超速" in last or "429" in last else min(8,.5*2**attempt))
  else:raise RuntimeError(last)
  d=p.get("data") or {};schema=list(d.get("fields") or []);batch=list(d.get("items") or []);rows.extend(batch)
  if len(batch)<LIMITS[api]:return [dict(zip(schema,item,strict=True)) for item in rows]
  offset+=len(batch)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(start,end,token_file,out_dir):
 token=Path(token_file).read_text().strip();out=Path(out_dir);out.mkdir(parents=True,exist_ok=True);ps=periods(start,end);manifest={"endpoint":PROXY_ENDPOINT,"start":start,"end":end,"apis":{}}
 for api in FIELDS:
  records=[];counts=[]
  for period in ps:
   batch=fetch(token,api,period);records.extend(batch);counts.append({"period":period,"row_count":len(batch)});Event().wait(.2)
  path=out/f"{api}.csv";frame=pd.DataFrame(records).drop_duplicates(keep="last");frame.to_csv(path,index=False);manifest["apis"][api]={"row_count":len(frame),"periods":counts,"path":str(path),"sha256":sha(path)}
 mp=out/"manifest.json";mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n");return manifest
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--start",default="2015-03-31");p.add_argument("--end",default="2026-06-30");p.add_argument("--token-file",default="/home/ygguo/.config/ai-crypt/xiaodefa-token");p.add_argument("--out-dir",default="overall/a-share-quarterly-statements-raw");a=p.parse_args(argv);print(json.dumps(run(a.start,a.end,a.token_file,a.out_dir),ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
