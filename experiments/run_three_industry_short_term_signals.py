"""Generate the frozen three-industry analyst-revision Shadow candidates."""
from __future__ import annotations
import argparse,json,urllib.request
from pathlib import Path
import duckdb,numpy as np,pandas as pd
from experiments.run_analyst_revision import consensus_revisions,load_reports
PROXY_ENDPOINT="https://fast.xiaodefa.cn";DB_PATH="/srv/bcache-8t/ygguo/duckdb/quant-a50/quant_a50.duckdb"
def api(token,name,fields):
 body=json.dumps({"api_name":name,"params":{"period":"20260630"},"fields":fields}).encode();req=urllib.request.Request(PROXY_ENDPOINT,data=body,headers={"x-api-key":token,"Content-Type":"application/json"},method="POST")
 with urllib.request.urlopen(req,timeout=120) as response:p=json.load(response)
 if p.get("code")!=0:raise RuntimeError(str(p.get("msg","proxy error")))
 d=p.get("data") or {};return pd.DataFrame([dict(zip(d.get("fields") or [],x,strict=True)) for x in (d.get("items") or [])])
def latest(d,asof):
 d=d.copy();d["ann_date"]=pd.to_datetime(d.ann_date,errors="coerce");d=d[d.ann_date<=asof];d["update_flag"]=pd.to_numeric(d.update_flag,errors="coerce").fillna(0);d["Symbol"]=d.ts_code.str[:6];return d.sort_values(["Symbol","ann_date","update_flag"]).drop_duplicates("Symbol",keep="last")
def run(token_file,members_path,reports_dir,asof,out_csv,out_json,out_md):
 day=pd.Timestamp(asof);token=Path(token_file).read_text().strip();m=pd.read_csv(members_path,dtype=str);m["Symbol"]=m.ts_code.str[:6];m["in_date"]=pd.to_datetime(m.in_date,errors="coerce");m["out_date"]=pd.to_datetime(m.out_date,errors="coerce");m["industry"]=np.select([m.l2_name.eq("半导体"),m.l1_name.eq("基础化工"),m.l1_name.eq("医药生物")],["半导体","基础化工","医药生物"],default="");m=m[(m.in_date<=day)&(m.out_date.isna()|(m.out_date>=day))&m.industry.ne("")].sort_values(["Symbol","in_date"]).drop_duplicates("Symbol",keep="last")
 rev=consensus_revisions(load_reports(reports_dir),day);rev=rev[(rev.revision>0)&(rev.current_count>=3)].merge(m[["Symbol","name","industry"]],on="Symbol",how="inner")
 con=duckdb.connect(DB_PATH,read_only=True)
 try:
  con.register("u",rev[["Symbol"]]);px=con.execute("select d.Symbol,d.TradingDay,d.Close from MarketData d join u on u.Symbol=d.Symbol where d.TradingDay<=? qualify row_number() over(partition by d.Symbol order by d.TradingDay desc)<=21 order by d.Symbol,d.TradingDay",[day.date()]).df();fund=con.execute("select f.Symbol,f.PETTM,f.PB,f.TotalMV from FundamentalData f join u on u.Symbol=f.Symbol where f.TradingDay=?",[day.date()]).df()
 finally:con.close()
 market=[]
 for s,g in px.groupby("Symbol"):
  g=g.sort_values("TradingDay");market.append({"Symbol":s,"return20":float(g.iloc[-1].Close/g.iloc[0].Close-1) if len(g)>=21 else np.nan,"ma20_ratio":float(g.iloc[-1].Close/g.tail(20).Close.mean()-1) if len(g)>=20 else np.nan})
 fina=latest(api(token,"fina_indicator_vip","ts_code,ann_date,end_date,tr_yoy,netprofit_yoy,dt_netprofit_yoy,roe_waa,grossprofit_margin,update_flag"),day);income=latest(api(token,"income_vip","ts_code,ann_date,end_date,n_income_attr_p,update_flag"),day);cash=latest(api(token,"cashflow_vip","ts_code,ann_date,end_date,n_cashflow_act,c_pay_acq_const_fiolta,update_flag"),day)
 x=rev.merge(pd.DataFrame(market),on="Symbol",how="left").merge(fund,on="Symbol",how="left").merge(fina.drop(columns=["ts_code"]),on="Symbol",how="left").merge(income[["Symbol","n_income_attr_p"]],on="Symbol",how="left").merge(cash[["Symbol","n_cashflow_act","c_pay_acq_const_fiolta"]],on="Symbol",how="left")
 for c in ["tr_yoy","netprofit_yoy","dt_netprofit_yoy","roe_waa","grossprofit_margin","n_income_attr_p","n_cashflow_act","c_pay_acq_const_fiolta"]:x[c]=pd.to_numeric(x[c],errors="coerce")
 x["ocf_np_ratio"]=x.n_cashflow_act/x.n_income_attr_p;x["fcf_proxy_yi"]=(x.n_cashflow_act-x.c_pay_acq_const_fiolta)/1e8;x["market_cap_yi"]=x.TotalMV/1e8;x["risk_flags"]=x.apply(lambda r:";".join((["修正低基数"] if r.revision>1 else [])+(["H1亏损"] if pd.notna(r.n_income_attr_p) and r.n_income_attr_p<=0 else [])+(["扣非下降"] if pd.notna(r.dt_netprofit_yoy) and r.dt_netprofit_yoy<0 else [])+(["OCF为负"] if pd.notna(r.n_cashflow_act) and r.n_cashflow_act<0 else [])+(["FCF为负"] if pd.notna(r.fcf_proxy_yi) and r.fcf_proxy_yi<0 else [])),axis=1);x=x.sort_values(["industry","revision","current_count","Symbol"],ascending=[True,False,False,True]);x["industry_rank"]=x.groupby("industry").cumcount()+1;x["arm_a"]=x.industry_rank<=10;x["arm_b"]=x.arm_a&(x.return20>0)&(x.ma20_ratio>0);x.to_csv(out_csv,index=False)
 cols=["Symbol","name","revision","current_count","return20","ma20_ratio","market_cap_yi","PETTM","PB","netprofit_yoy","dt_netprofit_yoy","ocf_np_ratio","fcf_proxy_yi","risk_flags","industry_rank","arm_a","arm_b"];payload={i:g[cols].to_dict("records") for i,g in x.groupby("industry")};Path(out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2,default=lambda z:z.item() if isinstance(z,np.generic) else None)+"\n");lines=["# 三行业中短期信息策略当前信号","",f"- as of: {asof}","- Arm A: 行业内分析师EPS正修正Top-10","- Arm B: Arm A且20日收益>0、站上MA20","- 仅Shadow，不授权交易",""]
 for i in ["半导体","基础化工","医药生物"]:
  g=x[(x.industry==i)&x.arm_a];lines += [f"## {i}","","|排名|代码|公司|EPS修正|机构|20日|MA20|Arm B|风险|","|---:|---|---|---:|---:|---:|---:|---|---|"]
  for r in g.itertuples(index=False):lines.append(f"|{r.industry_rank}|{r.Symbol}|{r.name}|{r.revision:.1%}|{r.current_count}|{r.return20:.1%}|{r.ma20_ratio:.1%}|{'是' if r.arm_b else '否'}|{r.risk_flags or '-'}|")
  lines.append("")
 Path(out_md).write_text("\n".join(lines)+"\n");return x
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--token-file",default="/home/ygguo/.config/ai-crypt/xiaodefa-token");p.add_argument("--members",default="overall/a-share-sw2021-members.csv");p.add_argument("--reports",default="overall/a-share-report-rc-raw");p.add_argument("--asof",default="2026-08-26");p.add_argument("--out-csv",default="overall/a-share-three-industry-short-term-signals.csv");p.add_argument("--out-json",default="overall/a-share-three-industry-short-term-signals.json");p.add_argument("--out-md",default="overall/a-share-three-industry-short-term-signals.md");a=p.parse_args(argv);x=run(a.token_file,a.members,a.reports,a.asof,a.out_csv,a.out_json,a.out_md);print(x.groupby("industry")[["arm_a","arm_b"]].sum());return 0
if __name__=="__main__":raise SystemExit(main())
