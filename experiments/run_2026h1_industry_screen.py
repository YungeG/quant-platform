"""Screen 2026H1 A-share performance in semiconductor, chemical, and pharma."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import duckdb,numpy as np,pandas as pd,requests
PROXY_ENDPOINT="https://fast.xiaodefa.cn";DB_PATH="/srv/bcache-8t/ygguo/duckdb/quant-a50/quant_a50.duckdb";AS_OF="20260826";START="20260526"

def api(token,name,fields):
 r=requests.post(PROXY_ENDPOINT,headers={"x-api-key":token},json={"api_name":name,"params":{"period":"20260630"},"fields":fields},timeout=120);r.raise_for_status();p=r.json()
 if p.get("code")!=0:raise RuntimeError(str(p.get("msg","proxy error")))
 d=p.get("data") or {};f=d.get("fields") or [];return pd.DataFrame([dict(zip(f,x,strict=True)) for x in (d.get("items") or [])])
def latest(frame):
 frame=frame.copy();frame.ann_date=pd.to_datetime(frame.ann_date,errors="coerce");frame=frame[frame.ann_date<=pd.Timestamp("2026-08-26")];frame.update_flag=pd.to_numeric(frame.update_flag,errors="coerce").fillna(0);return frame.sort_values(["ts_code","ann_date","update_flag"]).drop_duplicates("ts_code",keep="last")
def run(token_file,members_path,out_json,out_md,out_csv):
 token=Path(token_file).read_text().strip();m=pd.read_csv(members_path,dtype=str);m["symbol"]=m.ts_code.str[:6];m["name"]=m["name"].fillna(m.symbol);m["industry"]=np.select([m.l2_name.eq("半导体"),m.l1_name.eq("基础化工"),m.l1_name.eq("医药生物")],["半导体","基础化工","医药生物"],default="");m=m[m.industry!=""].drop_duplicates("symbol")
 fina=latest(api(token,"fina_indicator_vip","ts_code,ann_date,end_date,eps,tr_yoy,netprofit_yoy,dt_netprofit_yoy,roe_waa,grossprofit_margin,ocf_yoy,update_flag"));inc=latest(api(token,"income_vip","ts_code,ann_date,end_date,total_revenue,n_income_attr_p,update_flag"));fina["symbol"]=fina.ts_code.str[:6];inc["symbol"]=inc.ts_code.str[:6]
 con=duckdb.connect(DB_PATH,read_only=True)
 try:
  con.register("u",m[["symbol"]]);market=con.execute("""with px as (select m.Symbol,m.TradingDay,m.Close,row_number() over(partition by m.Symbol order by m.TradingDay desc) rn_end,row_number() over(partition by m.Symbol order by case when m.TradingDay<=date '2026-05-26' then m.TradingDay end desc nulls last) rn_start from MarketData m join u on u.symbol=m.Symbol where m.TradingDay<=date '2026-08-26'), e as (select Symbol,Close end_close from px where rn_end=1), s as (select Symbol,Close start_close from px where rn_start=1 and TradingDay<=date '2026-05-26') select e.Symbol,e.end_close,s.start_close from e left join s using(Symbol)""").df();mv=con.execute("select f.Symbol,f.TotalMV from FundamentalData f join u on u.symbol=f.Symbol where f.TradingDay=date '2026-08-26'").df()
 finally:con.close()
 base=m.merge(market,left_on="symbol",right_on="Symbol",how="left").merge(mv,left_on="symbol",right_on="Symbol",how="left",suffixes=("","_mv"));base["return_3m"]=base.end_close/base.start_close-1;base["market_cap_yi"]=base.TotalMV/100000000
 perf=base.merge(fina.drop(columns=["ts_code"]),on="symbol",how="inner").merge(inc[["symbol","total_revenue","n_income_attr_p"]],on="symbol",how="left");perf["revenue_yi"]=pd.to_numeric(perf.total_revenue,errors="coerce")/100000000;perf["net_profit_yi"]=pd.to_numeric(perf.n_income_attr_p,errors="coerce")/100000000
 metrics=["tr_yoy","netprofit_yoy","dt_netprofit_yoy","roe_waa","ocf_yoy"]
 for c in metrics:perf[c]=pd.to_numeric(perf[c],errors="coerce");perf[c+"_pct"]=perf.groupby("industry")[c].rank(pct=True,method="average")
 perf["performance_score"]=perf[[c+"_pct" for c in metrics]].mean(axis=1,skipna=False);eligible=perf[(perf.tr_yoy>0)&(perf.netprofit_yoy>0)&(perf.dt_netprofit_yoy>0)&(pd.to_numeric(perf.n_income_attr_p,errors="coerce")>0)].copy()
 top={i:g.sort_values(["performance_score","netprofit_yoy"],ascending=False).head(10) for i,g in eligible.groupby("industry")};caps={};bottom={}
 for industry,g in base.groupby("industry"):
  valid=g.dropna(subset=["market_cap_yi"]);caps[industry]={"largest":valid.nlargest(1,"market_cap_yi").iloc[0],"smallest":valid.nsmallest(1,"market_cap_yi").iloc[0]};bottom[industry]=g.dropna(subset=["return_3m"]).nsmallest(20,"return_3m")
 def records(df,cols):
  return [{c:(None if pd.isna(v) else (v.date().isoformat() if isinstance(v,pd.Timestamp) else (v.item() if isinstance(v,np.generic) else v))) for c,v in row.items()} for row in df[cols].to_dict("records")]
 payload={"as_of":"2026-08-26","return_start":"2026-05-26","definitions":{"semiconductor":"SW2021 L2 半导体","chemical":"SW2021 L1 基础化工","pharma":"SW2021 L1 医药生物","bright":"revenue/net profit/deducted profit all positive; industry percentile mean of five metrics"},"counts":{"universe":base.groupby("industry").size().to_dict(),"reported":perf.groupby("industry").size().to_dict(),"bright_eligible":eligible.groupby("industry").size().to_dict()},"top_performance":{i:records(g,["symbol","name","ann_date","revenue_yi","net_profit_yi","tr_yoy","netprofit_yoy","dt_netprofit_yoy","roe_waa","ocf_yoy","performance_score","market_cap_yi","return_3m"]) for i,g in top.items()},"market_cap_extremes":{i:{k:{"symbol":r.symbol,"name":r["name"],"market_cap_yi":float(r.market_cap_yi)} for k,r in v.items()} for i,v in caps.items()},"bottom_3m":{i:records(g,["symbol","name","return_3m","market_cap_yi"]) for i,g in bottom.items()}}
 Path(out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");allrows=[]
 for i,g in top.items():x=g.copy();x["section"]="top_performance";allrows.append(x)
 for i,g in bottom.items():x=g.copy();x["section"]="bottom_3m";allrows.append(x)
 pd.concat(allrows,ignore_index=True).to_csv(out_csv,index=False)
 lines=["# 2026H1半导体、基础化工、医药生物业绩与市场表现筛选","",f"- as of: 2026-08-26","- 3个月口径: 2026-05-26至2026-08-26（最近可得收盘）",""]
 for i in ["半导体","基础化工","医药生物"]:
  lines += [f"## {i}","",f"样本/已披露/正增长合格: {payload['counts']['universe'].get(i,0)}/{payload['counts']['reported'].get(i,0)}/{payload['counts']['bright_eligible'].get(i,0)}","",f"市值最大: {caps[i]['largest']['name']} {caps[i]['largest'].market_cap_yi:.2f}亿元；最小: {caps[i]['smallest']['name']} {caps[i]['smallest'].market_cap_yi:.2f}亿元","","### 业绩综合Top10","","|代码|公司|营收(亿)|归母净利(亿)|营收YoY|净利YoY|扣非YoY|ROE|3个月|","|---|---|---:|---:|---:|---:|---:|---:|---:|"]
  for r in top.get(i,pd.DataFrame()).itertuples(index=False):lines.append(f"|{r.symbol}|{r.name}|{r.revenue_yi:.2f}|{r.net_profit_yi:.2f}|{r.tr_yoy:.1f}%|{r.netprofit_yoy:.1f}%|{r.dt_netprofit_yoy:.1f}%|{r.roe_waa:.1f}%|{r.return_3m:.1%}|")
  lines += ["","### 最近3个月涨幅最小20只","","|代码|公司|3个月涨幅|市值(亿元)|","|---|---|---:|---:|"]
  for r in bottom[i].itertuples(index=False):lines.append(f"|{r.symbol}|{r.name}|{r.return_3m:.1%}|{r.market_cap_yi:.2f}|")
  lines.append("")
 Path(out_md).write_text("\n".join(lines)+"\n",encoding="utf-8");return payload
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--token-file",default="/home/ygguo/.config/ai-crypt/xiaodefa-token");p.add_argument("--members",default="overall/a-share-sw2021-members.csv");p.add_argument("--out-json",default="overall/a-share-2026h1-three-industry-screen.json");p.add_argument("--out-md",default="overall/a-share-2026h1-three-industry-screen.md");p.add_argument("--out-csv",default="overall/a-share-2026h1-three-industry-screen.csv");a=p.parse_args(argv);payload=run(a.token_file,a.members,a.out_json,a.out_md,a.out_csv);print(json.dumps(payload["counts"],ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
