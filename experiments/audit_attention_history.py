"""Audit captured attention rankings without reading price outcomes."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import duckdb
def run(raw_dir,out_path):
 raw=Path(raw_dir);source=json.loads((raw/"manifest.json").read_text());con=duckdb.connect();channels={}
 try:
  for channel in source["channels"]:
   glob=str(raw/f"{channel}_*.parquet");daily=con.execute(f'''with x as (select cast(trade_date as varchar) trade_date,time_bucket(interval '30 minutes',cast(rank_time as timestamp)) bucket,rank from read_parquet('{glob}')), d as (select trade_date,max(bucket) last_bucket,count(distinct bucket) bucket_count,count(*) row_count,max(rank) max_rank from x group by 1) select trade_date,strftime(last_bucket,'%H:%M') last_time,bucket_count,row_count,max_rank,case when hour(last_bucket)>=15 and bucket_count>=5 then true else false end is_valid from d order by 1''').fetchdf();duplicates=con.execute(f'''select count(*) from (select source,channel,trade_date,rank_time,ts_code,rank,count(*) n from read_parquet('{glob}') group by all having n>1)''').fetchone()[0];channels[channel]={"captured_dates":len(daily),"valid_final_snapshot_dates":int(daily.is_valid.sum()),"invalid_final_snapshot_dates":daily.loc[~daily.is_valid,"trade_date"].tolist(),"first_date":daily.trade_date.min() if len(daily) else None,"last_date":daily.trade_date.max() if len(daily) else None,"median_buckets":float(daily.bucket_count.median()) if len(daily) else None,"median_rows":float(daily.row_count.median()) if len(daily) else None,"median_max_rank":float(daily.max_rank.median()) if len(daily) else None,"natural_key_duplicates":int(duplicates),"zero_row_dates":source["channels"][channel]["zero_row_dates"]}
 finally:con.close()
 result={"source_manifest":str(raw/"manifest.json"),"valid_day_rule":"last snapshot bucket >=15:00 and at least 5 distinct 30-minute buckets","channels":channels};Path(out_path).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n");return result
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--raw-dir",default="overall/a-share-attention-raw");p.add_argument("--out",default="overall/a-share-attention-history-audit.json");a=p.parse_args(argv);print(json.dumps(run(a.raw_dir,a.out),ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
