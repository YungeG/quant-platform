"""Fetch point-in-time A-share name-change intervals and derive ST spans."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from threading import Event
import pandas as pd,requests
PROXY_ENDPOINT="https://fast.xiaodefa.cn";FIELDS="ts_code,name,start_date,end_date,ann_date,change_reason"
def fetch(token,start,end):
 last=""
 for attempt in range(10):
  try:
   response=requests.post(PROXY_ENDPOINT,headers={"x-api-key":token},json={"api_name":"namechange","params":{"start_date":start,"end_date":end},"fields":FIELDS},timeout=120);response.raise_for_status();payload=response.json()
   if payload.get("code")!=0:raise RuntimeError(str(payload.get("msg","proxy error")))
   data=payload.get("data") or {};return [dict(zip(data.get("fields") or [],row,strict=True)) for row in data.get("items") or []]
  except Exception as exc:last=f"{type(exc).__name__}: {exc}";Event().wait(min(8,.5*2**attempt))
 raise RuntimeError(last)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def run(start_year,end_date,token_file,out_dir,manifest_path):
 token=Path(token_file).read_text().strip();out=Path(out_dir);out.mkdir(parents=True,exist_ok=True);records=[];counts=[]
 for year in range(start_year,int(end_date[:4])+1):
  start=f"{year}0101";end=min(end_date,f"{year}1231");rows=fetch(token,start,end);records.extend(rows);counts.append({"start":start,"end":end,"rows":len(rows)});Event().wait(.1)
 frame=pd.DataFrame(records).drop_duplicates(["ts_code","name","start_date","end_date","ann_date","change_reason"],keep="last").sort_values(["ts_code","start_date","name"]);raw=out/"namechange.csv";frame.to_csv(raw,index=False);names=frame.name.fillna("").astype(str).str.upper();spans=frame[names.str.contains("ST",regex=False)].copy();spans["Symbol"]=spans.ts_code.str[:6];spans["StartDate"]=pd.to_datetime(spans.start_date,errors="coerce");spans["EndDate"]=pd.to_datetime(spans.end_date,errors="coerce");spans=spans.dropna(subset=["Symbol","StartDate"])[["Symbol","StartDate","EndDate","name","ann_date","change_reason"]].drop_duplicates();span_path=out/"st_spans.csv";spans.to_csv(span_path,index=False,date_format="%Y-%m-%d");manifest={"endpoint":PROXY_ENDPOINT,"api":"namechange","start_year":start_year,"end_date":end_date,"row_count":len(frame),"st_span_count":len(spans),"symbol_count":int(frame.ts_code.nunique()),"st_symbol_count":int(spans.Symbol.nunique()),"chunks":counts,"raw":{"path":str(raw),"sha256":sha(raw)},"st_spans":{"path":str(span_path),"sha256":sha(span_path)}};Path(manifest_path).write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n");return manifest
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--start-year",type=int,default=1990);p.add_argument("--end-date",default="20260827");p.add_argument("--token-file",default="/home/ygguo/.config/ai-crypt/xiaodefa-token");p.add_argument("--out-dir",default="overall/a-share-namechange-raw");p.add_argument("--manifest",default="overall/a-share-namechange-manifest.json");a=p.parse_args(argv);print(json.dumps(run(a.start_year,a.end_date,a.token_file,a.out_dir,a.manifest),ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
