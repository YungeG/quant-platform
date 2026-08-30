"""Fetch annual actual EPS announcements for earnings-surprise research."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from threading import Event

import pandas as pd
import requests


PROXY_ENDPOINT = "https://fast.xiaodefa.cn"
FIELDS = "ts_code,ann_date,end_date,eps,dt_eps,update_flag"


def run(start_year: int, end_year: int, token_file: str, output: str, manifest: str) -> dict:
    token = Path(token_file).read_text(encoding="utf-8").strip();records=[];counts=[]
    for year in range(start_year,end_year+1):
        period=f"{year}1231";offset=0;period_rows=[]
        while True:
            for _ in range(15):
                response=requests.post(PROXY_ENDPOINT,headers={"x-api-key":token},json={"api_name":"fina_indicator_vip","params":{"period":period,"offset":offset},"fields":FIELDS},timeout=120);response.raise_for_status();payload=response.json()
                if payload.get("code")==0:break
                if "超速" not in str(payload.get("msg","")):raise RuntimeError(str(payload.get("msg","proxy API error")))
                Event().wait(30)
            else:raise RuntimeError("proxy rate-limit cooldown did not clear")
            data=payload.get("data") or {};fields=list(data.get("fields") or []);rows=list(data.get("items") or []);period_rows.extend(rows)
            if len(rows)<12000:break
            offset+=len(rows)
        records.extend(dict(zip(fields,row,strict=True)) for row in period_rows);counts.append({"period":period,"row_count":len(period_rows)});Event().wait(.2)
    path=Path(output);frame=pd.DataFrame(records).drop_duplicates(keep="last");frame.to_csv(path,index=False)
    result={"endpoint":PROXY_ENDPOINT,"api":"fina_indicator_vip","periods":counts,"row_count":len(frame),"output":{"path":str(path),"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}}
    Path(manifest).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return result

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument("--start-year",type=int,default=2016);p.add_argument("--end-year",type=int,default=2025);p.add_argument("--token-file",default="/home/ygguo/.config/ai-crypt/xiaodefa-token");p.add_argument("--output",default="overall/a-share-annual-eps.csv");p.add_argument("--manifest",default="overall/a-share-annual-eps-manifest.json");a=p.parse_args(argv);print(json.dumps(run(a.start_year,a.end_year,a.token_file,a.output,a.manifest),ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
