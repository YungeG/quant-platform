"""Build a three-industry strong-fundamental/weak-price expectation-gap matrix."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import duckdb,numpy as np,pandas as pd,requests
PROXY_ENDPOINT="https://fast.xiaodefa.cn";DB_PATH="/srv/bcache-8t/ygguo/duckdb/quant-a50/quant_a50.duckdb";ASOF=pd.Timestamp("2026-08-26")

def api(token,name,params,fields="",limit=None):
 allrows=[];offset=0;schema=[]
 while True:
  q={**params,"offset":offset} if offset else params;r=requests.post(PROXY_ENDPOINT,headers={"x-api-key":token},json={"api_name":name,"params":q,"fields":fields},timeout=120);r.raise_for_status();p=r.json()
  if p.get("code")!=0:raise RuntimeError(str(p.get("msg","proxy error")))
  d=p.get("data") or {};schema=list(d.get("fields") or []);rows=list(d.get("items") or []);allrows.extend(rows)
  if not limit or len(rows)<limit:break
  offset+=len(rows)
 return pd.DataFrame([dict(zip(schema,x,strict=True)) for x in allrows])
def latest(f):
 f=f.copy();f.ann_date=pd.to_datetime(f.ann_date,errors="coerce");f=f[f.ann_date<=ASOF];f.update_flag=pd.to_numeric(f.update_flag,errors="coerce").fillna(0);return f.sort_values(["ts_code","ann_date","update_flag"]).drop_duplicates("ts_code",keep="last")
def load_q4_reports(raw_dir):
 con=duckdb.connect()
 try:r=con.execute("select ts_code,report_date,org_name,quarter,eps,create_time from read_csv_auto(?,union_by_name=true,header=true) where regexp_matches(quarter,'^[0-9]{4}Q4$') and eps is not null",[str(Path(raw_dir)/"report_rc_*.csv")]).df()
 finally:con.close()
 r["Symbol"]=r.ts_code.astype(str).str[:6];r["report_date"]=pd.to_datetime(r.report_date.astype(str));r["quarter_year"]=r.quarter.astype(str).str[:4].astype(int);return r

def current_revisions(reports,day):
 current_start=day-pd.Timedelta(days=180);prior_cutoff=day-pd.Timedelta(days=60);prior_start=prior_cutoff-pd.Timedelta(days=180);w=reports[reports.report_date.between(prior_start,day)&(reports.quarter_year>=day.year)].copy()
 def snap(start,cut,prefix):
  x=w[w.report_date.between(start,cut)].sort_values(["Symbol","quarter","org_name","report_date","create_time"]).drop_duplicates(["Symbol","quarter","org_name"],keep="last");return x.groupby(["Symbol","quarter"]).eps.agg([("count","count"),("median","median")]).rename(columns={"count":prefix+"_count","median":prefix+"_eps"}).reset_index()
 c=snap(current_start,day,"current");p=snap(prior_start,prior_cutoff,"prior");x=c.merge(p,on=["Symbol","quarter"]);x=x[(x.current_count>=3)&(x.prior_count>=3)&(x.prior_eps!=0)].copy();x["revision"]=x.current_eps/x.prior_eps-1;x["year"]=x.quarter.str[:4].astype(int);return x.sort_values(["Symbol","year"]).drop_duplicates("Symbol")

def load_q2_reports(raw_dir):
 con=duckdb.connect()
 try:r=con.execute("select ts_code,report_date,org_name,quarter,eps,create_time from read_csv_auto(?,union_by_name=true,header=true) where quarter='2026Q2' and eps is not null",[str(Path(raw_dir)/"report_rc_*.csv")]).df()
 finally:con.close()
 r["Symbol"]=r.ts_code.astype(str).str[:6];r["report_date"]=pd.to_datetime(r.report_date.astype(str));return r

def h1_surprises(fina,reports):
 groups={(s,q):g for (s,q),g in reports.groupby(["Symbol","quarter"])};out=[]
 for r in fina.itertuples(index=False):
  g=groups.get((r.symbol,"2026Q2"));
  if g is None:continue
  cutoff=pd.Timestamp(r.ann_date)-pd.Timedelta(days=1);w=g[g.report_date.between(cutoff-pd.Timedelta(days=180),cutoff)].sort_values(["org_name","report_date","create_time"]).drop_duplicates("org_name",keep="last")
  if len(w)>=3:out.append({"symbol":r.symbol,"h1_consensus_eps":float(w.eps.median()),"h1_surprise_eps":float(r.eps)-float(w.eps.median()),"h1_consensus_count":len(w)})
 return pd.DataFrame(out,columns=["symbol","h1_consensus_eps","h1_surprise_eps","h1_consensus_count"])
def run(token_file,members_path,reports_dir,out_csv,out_json,out_md):
 token=Path(token_file).read_text().strip();m=pd.read_csv(members_path,dtype=str);m["symbol"]=m.ts_code.str[:6];m["industry"]=np.select([m.l2_name.eq("半导体"),m.l1_name.eq("基础化工"),m.l1_name.eq("医药生物")],["半导体","基础化工","医药生物"],default="");m=m[m.industry!=""].drop_duplicates("symbol")
 fina=latest(api(token,"fina_indicator_vip",{"period":"20260630"},"ts_code,ann_date,end_date,eps,tr_yoy,netprofit_yoy,dt_netprofit_yoy,roe_waa,ocf_yoy,update_flag"));income=latest(api(token,"income_vip",{"period":"20260630"},"ts_code,ann_date,end_date,total_revenue,n_income_attr_p,update_flag"));fina["symbol"]=fina.ts_code.str[:6];income["symbol"]=income.ts_code.str[:6]
 money=api(token,"moneyflow_dc",{"trade_date":"20260826"},limit=6000);money["symbol"]=money.ts_code.str[:6];cyq=pd.read_csv("overall/a-share-cyq-month-ends.csv",dtype={"trade_date":str,"ts_code":str});cyq=cyq[cyq.trade_date=="20260825"].copy();cyq["symbol"]=cyq.ts_code.str[:6]
 con=duckdb.connect(DB_PATH,read_only=True)
 try:con.register("u",m[["symbol"]]);px=con.execute("select d.Symbol,d.TradingDay,d.Close from MarketData d join u on u.symbol=d.Symbol where d.TradingDay between date '2026-05-01' and date '2026-08-26' order by d.Symbol,d.TradingDay").df();mv=con.execute("select f.Symbol,f.TotalMV from FundamentalData f join u on u.symbol=f.Symbol where f.TradingDay=date '2026-08-26'").df()
 finally:con.close()
 px.TradingDay=pd.to_datetime(px.TradingDay);market=[]
 for s,g in px.groupby("Symbol"):
  g=g.sort_values("TradingDay");end=g.iloc[-1];before=g[g.TradingDay<=pd.Timestamp("2026-05-26")];start=before.iloc[-1] if len(before) else None;market.append({"symbol":s,"close":end.Close,"return_3m":end.Close/start.Close-1 if start is not None else np.nan,"return_20d":end.Close/g.iloc[-21].Close-1 if len(g)>=21 else np.nan,"ma20_ratio":end.Close/g.tail(20).Close.mean()-1})
 base=m.merge(pd.DataFrame(market),on="symbol",how="left").merge(mv,left_on="symbol",right_on="Symbol",how="left");base["market_cap_yi"]=base.TotalMV/1e8
 f=base.merge(fina.drop(columns=["ts_code"]),on="symbol",how="inner").merge(income[["symbol","total_revenue","n_income_attr_p"]],on="symbol",how="left")
 for c in ["tr_yoy","netprofit_yoy","dt_netprofit_yoy","roe_waa","ocf_yoy"]:f[c]=pd.to_numeric(f[c],errors="coerce");f[c+"_pct"]=f.groupby("industry")[c].rank(pct=True,method="average")
 f["performance_score"]=f[[c+"_pct" for c in ["tr_yoy","netprofit_yoy","dt_netprofit_yoy","roe_waa","ocf_yoy"]]].mean(axis=1,skipna=False);f=f[(f.tr_yoy>0)&(f.netprofit_yoy>0)&(f.dt_netprofit_yoy>0)&(pd.to_numeric(f.n_income_attr_p,errors="coerce")>0)].copy();f["fundamental_pct"]=f.groupby("industry").performance_score.rank(pct=True,method="average");base["price_pct"]=base.groupby("industry").return_3m.rank(pct=True,method="average");f=f.merge(base[["symbol","price_pct"]],on="symbol",how="left");f["category"]=np.select([(f.fundamental_pct>=.7)&(f.price_pct<=.3),(f.fundamental_pct>=.7)&(f.price_pct>=.7),f.fundamental_pct>=.7],["预期差候选","已确认龙头","基本面强观察"],default="其他")
 reports=load_q4_reports(reports_dir);rev=current_revisions(reports,ASOF)[["Symbol","revision","current_count"]].rename(columns={"Symbol":"symbol","revision":"analyst_revision60","current_count":"analyst_count"});sur=h1_surprises(fina,load_q2_reports(reports_dir));f=f.merge(rev,on="symbol",how="left").merge(sur,on="symbol",how="left").merge(money[["symbol","net_amount_rate"]],on="symbol",how="left").merge(cyq[["symbol","winner_rate"]],on="symbol",how="left")
 f["confirmation_count"]=(f.analyst_revision60>0).astype(int)+(f.h1_surprise_eps>0).astype(int)+(pd.to_numeric(f.net_amount_rate,errors="coerce")>0).astype(int)+(f.return_20d>0).astype(int)+(f.ma20_ratio>0).astype(int);f=f.sort_values(["industry","category","confirmation_count","performance_score"],ascending=[True,True,False,False]);f.to_csv(out_csv,index=False)
 payload={i:{c:g[g.category==c][["symbol","name","performance_score","return_3m","market_cap_yi","analyst_revision60","h1_surprise_eps","net_amount_rate","winner_rate","return_20d","ma20_ratio","confirmation_count"]].to_dict("records") for c in ["预期差候选","已确认龙头","基本面强观察"]} for i,g in f.groupby("industry")};Path(out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2,default=lambda x:x.item() if isinstance(x,np.generic) else None)+"\n")
 lines=["# 三行业2026H1基本面—价格预期差候选","", "确认项：分析师60日上修、H1盈利惊喜为正、当日资金净流入、20日收益为正、站上MA20。",""]
 for i in ["半导体","基础化工","医药生物"]:
  lines += [f"## {i}",""]
  for cat in ["预期差候选","已确认龙头","基本面强观察"]:
   x=f[(f.industry==i)&(f.category==cat)].sort_values(["confirmation_count","performance_score"],ascending=False);lines += [f"### {cat}（{len(x)}）","","|代码|公司|业绩分位|3个月|分析师修正|H1惊喜EPS|资金流率|获利盘|20日|确认数|","|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
   for r in x.itertuples(index=False):lines.append(f"|{r.symbol}|{r.name}|{r.fundamental_pct:.0%}|{r.return_3m:.1%}|{r.analyst_revision60:.1%}|{r.h1_surprise_eps:.3f}|{r.net_amount_rate:.1f}%|{r.winner_rate:.1f}%|{r.return_20d:.1%}|{r.confirmation_count}|")
   lines.append("")
 Path(out_md).write_text("\n".join(lines)+"\n");return f
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--token-file",default="/home/ygguo/.config/ai-crypt/xiaodefa-token");p.add_argument("--members",default="overall/a-share-sw2021-members.csv");p.add_argument("--reports",default="overall/a-share-report-rc-raw");p.add_argument("--out-csv",default="overall/a-share-three-industry-expectation-gap.csv");p.add_argument("--out-json",default="overall/a-share-three-industry-expectation-gap.json");p.add_argument("--out-md",default="overall/a-share-three-industry-expectation-gap.md");a=p.parse_args(argv);f=run(a.token_file,a.members,a.reports,a.out_csv,a.out_json,a.out_md);print(f.groupby(["industry","category"]).size());return 0
if __name__=="__main__":raise SystemExit(main())
