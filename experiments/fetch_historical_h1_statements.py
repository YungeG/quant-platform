"""Fetch 2016-2025 H1 financial statements for the frozen historical study."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from threading import Event
import pandas as pd,requests
PROXY_ENDPOINT="https://fast.xiaodefa.cn"
LIMITS={"fina_indicator_vip":12000,"income_vip":9000,"cashflow_vip":6400}
FIELDS={
 "fina_indicator_vip":"ts_code,ann_date,end_date,eps,tr_yoy,netprofit_yoy,dt_netprofit_yoy,roe_waa,grossprofit_margin,ocf_yoy,update_flag",
 "income_vip":"ts_code,ann_date,f_ann_date,end_date,total_revenue,n_income_attr_p,update_flag",
 "cashflow_vip":"ts_code,ann_date,f_ann_date,end_date,n_cashflow_act,c_pay_acq_const_fiolta,free_cashflow,update_flag",
}
def fetch(token,api,period):
 rows_all=[];offset=0;schema=[]
 while True:
  last=""
  for attempt in range(15):
   try:
    r=requests.post(PROXY_ENDPOINT,headers={"x-api-key":token},json={"api_name":api,"params":{"period":period,"offset":offset},"fields":FIELDS[api]},timeout=120)
    if r.status_code==429:raise RuntimeError("HTTP 429")
    r.raise_for_status();p=r.json()
    if p.get("code")==0:break
    raise RuntimeError(str(p.get("msg","proxy API error")))
   except Exception as e:
    last=f"{type(e).__name__}: {e}";Event().wait(30 if ("超速" in last or "429" in last) else min(8,.5*2**attempt))
  else:raise RuntimeError(last)
  d=p.get("data") or {};schema=list(d.get("fields") or []);rows=list(d.get("items") or []);rows_all.extend(rows)
  if len(rows)<LIMITS[api]:return [dict(zip(schema,x,strict=True)) for x in rows_all]
  offset+=len(rows)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(start_year,end_year,token_file,out_dir):
 token=Path(token_file).read_text().strip();out=Path(out_dir);out.mkdir(parents=True,exist_ok=True);manifest={"endpoint":PROXY_ENDPOINT,"start_year":start_year,"end_year":end_year,"apis":{}}
 for api in FIELDS:
  records=[];counts=[]
  for year in range(start_year,end_year+1):
   period=f"{year}0630";rows=fetch(token,api,period);records.extend(rows);counts.append({"period":period,"row_count":len(rows)});Event().wait(.2)
  path=out/f"{api}.csv";frame=pd.DataFrame(records).drop_duplicates(keep="last");frame.to_csv(path,index=False);manifest["apis"][api]={"row_count":len(frame),"periods":counts,"path":str(path),"sha256":sha(path)}
 mp=out/"manifest.json";mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n");return manifest
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--start-year",type=int,default=2016);p.add_argument("--end-year",type=int,default=2025);p.add_argument("--token-file",default="/home/ygguo/.config/ai-crypt/xiaodefa-token");p.add_argument("--out-dir",default="overall/a-share-historical-h1-raw");a=p.parse_args(argv);print(json.dumps(run(a.start_year,a.end_year,a.token_file,a.out_dir),ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
