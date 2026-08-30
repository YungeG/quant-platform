"""Derive and evaluate frozen breakout microstructure features."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from experiments.context_features import holm_adjust
from experiments.run_lowturn_livermore import _clean
FEATURES=("retest_recovery","signal_close_vs_vwap","auction_turnover","entry_first30_return","entry_close_vs_vwap");FOLDS=(("2016-2019","2016-01-01","2019-12-31"),("2020-2022","2020-01-01","2022-12-31"),("2023-2026","2023-01-01","2026-12-31"))

def aggregate_days(mins,mapping):
 mins["trade_time"]=pd.to_datetime(mins.trade_time);mins["date"]=mins.request_date.astype(str);rows=[]
 for (symbol,date),g in mins.sort_values("trade_time").groupby(["request_symbol","date"]):
  amount=float(g.amount.sum());vol=float(g.vol.sum());vwap=amount/vol if vol>0 else np.nan;first=g.iloc[0];last=g.iloc[-1];early=g[g.trade_time.dt.time<=pd.Timestamp("10:00").time()];early_ret=float(early.iloc[-1].close/first.open-1) if len(early) else np.nan
  rows.append({"ts_code":symbol,"date":date,"day_open":float(first.open),"day_high":float(g.high.max()),"day_low":float(g.low.min()),"day_close":float(last.close),"day_vwap":vwap,"day_amount":amount,"first30_return":early_ret,"first30_amount_share":float(early.amount.sum()/amount) if amount>0 else np.nan,"max_intraday_drawdown":float(g.low.min()/first.open-1),"last_hour_return":float(last.close/g[g.trade_time.dt.time>=pd.Timestamp("14:00").time()].iloc[0].open-1)})
 return mapping.merge(pd.DataFrame(rows),on=["ts_code","date"],how="left")
def build(events_path,raw_dir,ledger):
 events=pd.read_csv(events_path,dtype={"symbol":str},parse_dates=["signal_date"]);events=events[events.execution_reason=="executed"].copy();mapping=pd.read_csv(Path(raw_dir)/"event_roles.csv",dtype={"date":str,"ts_code":str});mins=pd.read_csv(Path(raw_dir)/"mins.csv",dtype={"request_date":str,"request_symbol":str});days=aggregate_days(mins,mapping)
 wide={role:g.set_index("event_id") for role,g in days.groupby("role")};features=events.set_index("event_id")
 ret=wide["retest"];sig=wide["signal"];ent=wide["entry"]
 features["retest_recovery"]=(ret.day_close-ret.day_low)/(ret.day_high-ret.day_low).replace(0,np.nan);features["signal_close_vs_vwap"]=sig.day_close/sig.day_vwap-1;features["entry_first30_return"]=ent.first30_return;features["entry_close_vs_vwap"]=ent.day_close/ent.day_vwap-1;features["entry_first30_amount_share"]=ent.first30_amount_share;features["entry_max_intraday_drawdown"]=ent.max_intraday_drawdown;features["entry_last_hour_return"]=ent.last_hour_return
 auction=pd.read_csv(Path(raw_dir)/"auction.csv",dtype={"request_date":str,"request_symbol":str});entry_map=mapping[mapping.role=="entry"][["event_id","ts_code","date"]];auction=entry_map.merge(auction,left_on=["ts_code","date"],right_on=["request_symbol","request_date"],how="left").set_index("event_id")
 ctx=pd.read_csv("overall/a-share-breakout-context-events.csv",usecols=["event_id","signal_circ_mv"]).set_index("event_id")
 features["auction_turnover"]=auction.amount/(ctx.signal_circ_mv*10000);features.reset_index().to_csv(ledger,index=False,date_format="%Y-%m-%d");return features.reset_index()
def bootstrap(x,y):
 rng=np.random.default_rng(20260827);vals=[]
 for _ in range(2000):
  i=rng.integers(0,len(x),len(x));sx=x[i];sy=y[i];vals.append(0.0 if np.unique(sx).size<2 else float(spearmanr(sx,sy).statistic))
 return [float(np.quantile(vals,.025)),float(np.quantile(vals,.975))]
def stats(frame,feature):
 x=frame[[feature,"active20","signal_date"]].dropna();t=spearmanr(x[feature],x.active20);ci=bootstrap(x[feature].to_numpy(float),x.active20.to_numpy(float));folds={}
 for name,start,end in FOLDS:
  f=x[x.signal_date.between(start,end)];folds[name]={"count":len(f),"rho":float(spearmanr(f[feature],f.active20).statistic) if len(f)>=3 and f[feature].nunique()>1 else 0.0}
 return {"count":len(x),"rho":float(t.statistic),"p":float(t.pvalue),"bootstrap95":ci,"folds":folds,"success_median":float(x[x.active20>0][feature].median()),"failure_median":float(x[x.active20<=0][feature].median())}
def evaluate(frame):
 result={f:stats(frame,f) for f in FEATURES};adj=holm_adjust({f:result[f]["p"] for f in FEATURES});decisions={}
 for f,r in result.items():
  checks={"count":r["count"]>=100,"fold_counts":sum(v["count"]>=20 for v in r["folds"].values())>=2,"direction":r["rho"]>0,"bootstrap":r["bootstrap95"][0]>0,"fold_direction":sum(v["rho"]>0 for v in r["folds"].values())>=2,"holm":adj[f]<.05};decisions[f]={"status":"SHADOW-CANDIDATE" if all(checks.values()) else ("MARGINAL" if r["rho"]>0 else "NO-GO"),"holm_p":adj[f],"checks":checks}
 verdict="SHADOW-CANDIDATE" if any(v["status"]=="SHADOW-CANDIDATE" for v in decisions.values()) else ("MARGINAL" if any(v["status"]=="MARGINAL" for v in decisions.values()) else "NO-GO");return {"verdict":verdict,"features":result,"decisions":decisions}
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--events",default="overall/a-share-breakout-retest-v2-events.csv");p.add_argument("--raw",default="overall/a-share-breakout-microstructure-raw");p.add_argument("--ledger",default="overall/a-share-breakout-microstructure-events.csv");p.add_argument("--out-json",default="overall/a-share-breakout-microstructure.json");p.add_argument("--out-md",default="overall/a-share-breakout-microstructure.md");a=p.parse_args(argv);frame=build(a.events,a.raw,a.ledger);decision=evaluate(frame);payload=_clean({"study":"a-share-breakout-microstructure-v1","data":{"events":len(frame)},"decision":decision,"ledger":a.ledger});Path(a.out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");lines=["# A股突破回踩微观结构结果","",f"- verdict: **{decision['verdict']}**",""]+[f"- {f}: rho {decision['features'][f]['rho']:.3f}, {decision['decisions'][f]['status']}" for f in FEATURES];text="\n".join(lines)+"\n";Path(a.out_md).write_text(text,encoding="utf-8");print(text);return 0
if __name__=="__main__":raise SystemExit(main())
