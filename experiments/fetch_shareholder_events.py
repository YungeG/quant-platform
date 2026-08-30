"""Fetch paginated monthly repurchase and holder-trade histories."""

from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from threading import Event
import pandas as pd,requests
PROXY_ENDPOINT="https://fast.xiaodefa.cn"
LIMITS={"repurchase":2000,"stk_holdertrade":3000}

def fetch(token,api,start,end):
 rows_all=[];offset=0;fields=[]
 while True:
  for _ in range(15):
   r=requests.post(PROXY_ENDPOINT,headers={"x-api-key":token},json={"api_name":api,"params":{"start_date":start,"end_date":end,"offset":offset},"fields":""},timeout=120);r.raise_for_status();p=r.json()
   if p.get("code")==0:break
   if "超速" not in str(p.get("msg","")):raise RuntimeError(str(p.get("msg","proxy API error")))
   Event().wait(30)
  else:raise RuntimeError("rate-limit cooldown did not clear")
  d=p.get("data") or {};fields=list(d.get("fields") or []);rows=list(d.get("items") or []);rows_all.extend(rows)
  if len(rows)<LIMITS[api]:return fields,rows_all
  offset+=len(rows)

def run(start,end,token_file,out_dir):
 token=Path(token_file).read_text().strip();out=Path(out_dir);out.mkdir(parents=True,exist_ok=True);months=pd.period_range(start,end,freq="M");manifest={"endpoint":PROXY_ENDPOINT,"start":start,"end":end,"apis":{}}
 for api in LIMITS:
  records=[];counts=[]
  for m in months:
   s=max(pd.Timestamp(start),m.start_time).strftime("%Y%m%d");e=min(pd.Timestamp(end),m.end_time).strftime("%Y%m%d");fields,rows=fetch(token,api,s,e);records.extend(dict(zip(fields,row,strict=True)) for row in rows);counts.append({"month":str(m),"row_count":len(rows)});Event().wait(.2)
  path=out/f"{api}.csv";frame=pd.DataFrame(records).drop_duplicates(keep="last");frame.to_csv(path,index=False);manifest["apis"][api]={"row_count":len(frame),"months":counts,"path":str(path),"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
 (out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n");return manifest

def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--start",default="2016-01-01");p.add_argument("--end",default="2026-08-26");p.add_argument("--token-file",default="/home/ygguo/.config/ai-crypt/xiaodefa-token");p.add_argument("--out-dir",default="overall/a-share-shareholder-events-raw");a=p.parse_args(argv);print(json.dumps(run(a.start,a.end,a.token_file,a.out_dir),ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
