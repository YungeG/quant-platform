"""Build the frozen direct sector-to-ETF candidate map."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd
KEYWORDS={"交通运输":["交通运输"],"传媒":["传媒"],"公用事业":["公用事业"],"农林牧渔":["农业"],"医药生物":["医药"],"国防军工":["军工"],"基础化工":["化工"],"家用电器":["家电"],"建筑材料":["建材"],"房地产":["房地产"],"有色金属":["有色"],"机械设备":["机械"],"汽车":["汽车"],"煤炭":["煤炭"],"环保":["环保"],"电子":["电子"],"石油石化":["油气","石化"],"计算机":["计算机"],"通信":["通信","5G"],"钢铁":["钢铁"],"银行":["银行"],"非银金融":["证券"],"食品饮料":["食品饮料"]}
def run(fund_basic,out_csv,out_json):
 f=pd.read_csv(fund_basic,dtype=str);text=f.name.fillna("")+" "+f.benchmark.fillna("");eligible=f.name.fillna("").str.contains("ETF",case=False)&~text.str.contains("REIT|港股|香港|恒生|海外|纳斯达克",case=False,regex=True);rows=[]
 for industry,keywords in KEYWORDS.items():
  mask=False
  for keyword in keywords:mask=mask|text.str.contains(keyword,case=False,regex=False)
  x=f[eligible&mask].copy();x["industry"]=industry;rows.append(x)
 result=pd.concat(rows,ignore_index=True).drop_duplicates(["industry","ts_code"]);result.to_csv(out_csv,index=False);coverage={industry:int((result.industry==industry).sum()) for industry in KEYWORDS};payload={"study":"a-share-sector-etf-universe-v1","candidates":len(result),"industry_coverage":coverage,"unmapped":[industry for industry,count in coverage.items() if count==0],"output":out_csv};Path(out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n");return payload
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--fund-basic",default="overall/a-share-fund-basic.csv");p.add_argument("--out-csv",default="overall/a-share-sector-etf-candidates.csv");p.add_argument("--out-json",default="overall/a-share-sector-etf-universe-audit.json");a=p.parse_args(argv);print(json.dumps(run(a.fund_basic,a.out_csv,a.out_json),ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
