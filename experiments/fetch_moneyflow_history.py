"""Fetch full-market daily directional moneyflow into monthly Parquet partitions."""
from __future__ import annotations
import argparse,hashlib,json,os
from pathlib import Path
from threading import Event
import duckdb,pandas as pd,requests
PROXY_ENDPOINT="https://fast.xiaodefa.cn";DB_PATH="/srv/bcache-8t/ygguo/duckdb/quant-a50/quant_a50.duckdb";LIMIT=6000;FIELDS="ts_code,trade_date,buy_sm_vol,buy_sm_amount,sell_sm_vol,sell_sm_amount,buy_md_vol,buy_md_amount,sell_md_vol,sell_md_amount,buy_lg_vol,buy_lg_amount,sell_lg_vol,sell_lg_amount,buy_elg_vol,buy_elg_amount,sell_elg_vol,sell_elg_amount,net_mf_vol,net_mf_amount"
def trade_dates(start,end):
 con=duckdb.connect(DB_PATH,read_only=True)
 try:return [str(row[0]).replace("-","") for row in con.execute("select distinct TradingDay from MarketData where TradingDay between ? and ? order by 1",[start,end]).fetchall()]
 finally:con.close()
def fetch(token,date):
 rows=[];offset=0;schema=[]
 while True:
  last=""
  for attempt in range(15):
   try:
    r=requests.post(PROXY_ENDPOINT,headers={"x-api-key":token},json={"api_name":"moneyflow","params":{"trade_date":date,"offset":offset},"fields":FIELDS},timeout=120)
    if r.status_code==429:raise RuntimeError("HTTP 429")
    r.raise_for_status();p=r.json()
    if p.get("code")==0:break
    raise RuntimeError(str(p.get("msg","proxy error")))
   except Exception as e:last=f"{type(e).__name__}: {e}";Event().wait(30 if "超速" in last or "429" in last else min(8,.5*2**attempt))
  else:return [],last
  d=p.get("data") or {};schema=list(d.get("fields") or []);batch=list(d.get("items") or []);rows.extend(batch)
  if len(batch)<LIMIT:return [dict(zip(schema,item,strict=True)) for item in rows],""
  offset+=len(batch)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(start,end,token_file,out_dir,delay):
 token=Path(token_file).read_text().strip();out=Path(out_dir);out.mkdir(parents=True,exist_ok=True);qpath=out/"queries.csv";queries=pd.read_csv(qpath,dtype={"trade_date":str}) if qpath.exists() else pd.DataFrame(columns=["trade_date","month","status","row_count","error"]);done=set(queries.loc[queries.status.eq("success"),"trade_date"]);dates=trade_dates(start,end);months={}
 for date in dates:months.setdefault(date[:6],[]).append(date)
 for month,month_dates in months.items():
  pending=[date for date in month_dates if date not in done];path=out/f"moneyflow_{month}.parquet";existing=pd.read_parquet(path) if path.exists() else pd.DataFrame();records=[];updates=[]
  for date in pending:
   rows,error=fetch(token,date);updates.append({"trade_date":date,"month":month,"status":"staged" if not error else "failed","row_count":len(rows),"error":error});records.extend(rows);Event().wait(delay)
  if records:
   frame=pd.concat([existing,pd.DataFrame(records)],ignore_index=True).drop_duplicates(["trade_date","ts_code"],keep="last");tmp=path.with_suffix(".tmp.parquet");frame.to_parquet(tmp,index=False,compression="zstd");os.replace(tmp,path)
  elif not path.exists():pd.DataFrame(columns=FIELDS.split(",")).to_parquet(path,index=False,compression="zstd")
  if updates:
   update=pd.DataFrame(updates);update.loc[update.status.eq("staged"),"status"]="success";queries=pd.concat([queries,update],ignore_index=True).drop_duplicates("trade_date",keep="last").sort_values("trade_date");queries.to_csv(qpath,index=False);done=set(queries.loc[queries.status.eq("success"),"trade_date"])
 manifest={"endpoint":PROXY_ENDPOINT,"api":"moneyflow","start":start,"end":end,"requested_dates":len(dates),"successful_dates":len(done.intersection(dates)),"failed_dates":queries[queries.trade_date.isin(dates)&queries.status.ne("success")].trade_date.tolist(),"partitions":{}}
 for path in sorted(out.glob("moneyflow_*.parquet")):
  frame=pd.read_parquet(path,columns=["trade_date","ts_code"]);manifest["partitions"][path.stem[-6:]]={"path":str(path),"rows":len(frame),"dates":int(frame.trade_date.astype(str).nunique()),"sha256":sha(path)}
 (out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n");return manifest
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--start",default="2018-01-01");p.add_argument("--end",default="2026-08-27");p.add_argument("--token-file",default="/home/ygguo/.config/ai-crypt/xiaodefa-token");p.add_argument("--out-dir",default="overall/a-share-moneyflow-raw");p.add_argument("--delay",type=float,default=.15);a=p.parse_args(argv);result=run(a.start,a.end,a.token_file,a.out_dir,a.delay);print(json.dumps({k:result[k] for k in ["start","end","requested_dates","successful_dates","failed_dates"]},ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
