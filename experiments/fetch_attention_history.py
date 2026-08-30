"""Fetch THS/DC A-share attention rankings into immutable monthly partitions."""
from __future__ import annotations
import argparse,hashlib,json,os
from pathlib import Path
from threading import Event
import duckdb,pandas as pd,requests
PROXY_ENDPOINT="https://fast.xiaodefa.cn";DB_PATH="/srv/bcache-8t/ygguo/duckdb/quant-a50/quant_a50.duckdb";LIMIT=2000
FIELDS="trade_date,data_type,ts_code,ts_name,rank,pct_change,current_price,concept,rank_reason,hot,rank_time"
CHANNELS={
 "ths_stock":("ths_hot",{"market":"热股","is_new":"N"},"20240102"),
 "ths_industry":("ths_hot",{"market":"行业板块","is_new":"N"},"20240102"),
 "dc_popularity":("dc_hot",{"market":"A股市场","hot_type":"人气榜","is_new":"N"},"20240401"),
 "dc_rising":("dc_hot",{"market":"A股市场","hot_type":"飙升榜","is_new":"N"},"20240401"),
}
def trade_dates(start,end):
 con=duckdb.connect(DB_PATH,read_only=True)
 try:return [str(row[0]).replace("-","") for row in con.execute("select distinct TradingDay from MarketData where TradingDay between ? and ? order by 1",[start,end]).fetchall()]
 finally:con.close()
def fetch(token,api,params):
 rows=[];offset=0;schema=[]
 while True:
  last=""
  for attempt in range(15):
   try:
    request={**params,"offset":offset};r=requests.post(PROXY_ENDPOINT,headers={"x-api-key":token},json={"api_name":api,"params":request,"fields":FIELDS},timeout=120)
    if r.status_code==429:raise RuntimeError("HTTP 429")
    r.raise_for_status();payload=r.json()
    if payload.get("code")==0:break
    raise RuntimeError(str(payload.get("msg","proxy error")))
   except Exception as exc:last=f"{type(exc).__name__}: {exc}";Event().wait(30 if "超速" in last or "429" in last else min(8,.5*2**attempt))
  else:return [],last
  data=payload.get("data") or {};schema=list(data.get("fields") or []);batch=list(data.get("items") or []);rows.extend(batch)
  if len(batch)<LIMIT:return [dict(zip(schema,item,strict=True)) for item in rows],""
  offset+=len(batch)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(start,end,token_file,out_dir,delay):
 token=Path(token_file).read_text().strip();out=Path(out_dir);out.mkdir(parents=True,exist_ok=True);qpath=out/"queries.csv";queries=pd.read_csv(qpath,dtype={"trade_date":str}) if qpath.exists() else pd.DataFrame(columns=["trade_date","month","channel","status","row_count","error"]);dates=trade_dates(start,end)
 for channel,(api,base,effective_start) in CHANNELS.items():
  channel_dates=[d for d in dates if d>=effective_start];done=set(queries.loc[queries.channel.eq(channel)&queries.status.eq("success"),"trade_date"])
  for month in sorted({d[:6] for d in channel_dates}):
   month_dates=[d for d in channel_dates if d.startswith(month)];pending=[d for d in month_dates if d not in done];path=out/f"{channel}_{month}.parquet";existing=pd.read_parquet(path) if path.exists() else pd.DataFrame();records=[];updates=[]
   for date in pending:
    rows,error=fetch(token,api,{**base,"trade_date":date});records.extend({**row,"source":api,"channel":channel} for row in rows);updates.append({"trade_date":date,"month":month,"channel":channel,"status":"staged" if not error else "failed","row_count":len(rows),"error":error});Event().wait(delay)
   if records:
    frame=pd.concat([existing,pd.DataFrame(records)],ignore_index=True);keys=[c for c in ["source","channel","trade_date","rank_time","ts_code","rank"] if c in frame];frame=frame.drop_duplicates(keys,keep="last");tmp=path.with_suffix(".tmp.parquet");frame.to_parquet(tmp,index=False,compression="zstd");os.replace(tmp,path)
   elif not path.exists():pd.DataFrame(columns=FIELDS.split(",")+["source","channel"]).to_parquet(path,index=False,compression="zstd")
   if updates:
    update=pd.DataFrame(updates);update.loc[update.status.eq("staged"),"status"]="success";queries=pd.concat([queries,update],ignore_index=True).drop_duplicates(["trade_date","channel"],keep="last").sort_values(["trade_date","channel"]);queries.to_csv(qpath,index=False);done=set(queries.loc[queries.channel.eq(channel)&queries.status.eq("success"),"trade_date"])
 manifest={"endpoint":PROXY_ENDPOINT,"start":start,"end":end,"requested_trading_dates":len(dates),"channels":{},"partitions":{}}
 for channel,(_,_,effective_start) in CHANNELS.items():
  expected={d for d in dates if d>=effective_start};q=queries[queries.channel.eq(channel)&queries.trade_date.isin(expected)];manifest["channels"][channel]={"effective_start":effective_start,"requested_dates":len(expected),"successful_dates":int(q.status.eq("success").sum()),"failed_dates":q.loc[q.status.ne("success"),"trade_date"].tolist(),"zero_row_dates":q.loc[q.status.eq("success")&q.row_count.eq(0),"trade_date"].tolist(),"rows":int(q.loc[q.status.eq("success"),"row_count"].sum())}
 for path in sorted(out.glob("*.parquet")):
  frame=pd.read_parquet(path,columns=["trade_date","rank_time"]);manifest["partitions"][path.stem]={"path":str(path),"rows":len(frame),"dates":int(frame.trade_date.astype(str).nunique()) if len(frame) else 0,"sha256":sha(path)}
 (out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n");return manifest
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--start",default="2024-01-02");p.add_argument("--end",default="2026-08-27");p.add_argument("--token-file",default="/home/ygguo/.config/ai-crypt/xiaodefa-token");p.add_argument("--out-dir",default="overall/a-share-attention-raw");p.add_argument("--delay",type=float,default=.12);a=p.parse_args(argv);result=run(a.start,a.end,a.token_file,a.out_dir,a.delay);print(json.dumps({"start":result["start"],"end":result["end"],"channels":result["channels"]},ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
