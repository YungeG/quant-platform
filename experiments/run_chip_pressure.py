"""Backtest monthly chip-cost pressure and an analyst-revision chip overlay."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from experiments.quarterly_portfolio import Bar, BasketConfig, simulate_basket
from experiments.run_analyst_revision import FOLDS, benchmark_returns, consensus_revisions, json_clean, load_reports
from experiments.run_largecap_lowvol import summarize_basket
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.research.combination import repair_point_in_time_size


def ic_summary(rows: pd.DataFrame) -> dict:
    monthly=[]
    for day,g in rows.dropna(subset=["chip_balance","active20"]).groupby("signal_date"):
        if len(g)>=20 and g.chip_balance.nunique()>1: monthly.append({"signal_date":day,"ic":float(spearmanr(g.chip_balance,g.active20).statistic),"count":len(g)})
    f=pd.DataFrame(monthly);mean=float(f.ic.mean()) if len(f) else 0.0;std=float(f.ic.std(ddof=1)) if len(f)>1 else 0.0
    folds={}
    for name,start,end in FOLDS:
        x=f[f.signal_date.between(start,end)] if len(f) else f;folds[name]={"count":len(x),"mean_ic":float(x.ic.mean()) if len(x) else 0.0}
    return {"count":len(f),"mean":mean,"median":float(f.ic.median()) if len(f) else 0.0,"win_rate":float((f.ic>0).mean()) if len(f) else 0.0,"t_stat":mean/(std/np.sqrt(len(f))) if std>0 else 0.0,"average_coverage":float(f["count"].mean()) if len(f) else 0.0,"folds":folds}


def build_inputs(start:str,end:str,cyq:pd.DataFrame,reports:pd.DataFrame)->tuple:
    cfg=Config();con=connect(cfg,read_only=True)
    try: built=load_or_build_panel(cfg,"2014-11-27",end,con=con)
    finally: con.close()
    p=repair_point_in_time_size(built.df);p["TradingDay"]=pd.to_datetime(p.TradingDay);p=p.sort_values(["Symbol","TradingDay"]).reset_index(drop=True)
    grp=p.groupby("Symbol",sort=False);p["_fwd20"]=grp.adj_open.shift(-21)/grp.adj_open.shift(-1)-1
    adv=p.groupby("TradingDay").adv20.rank(pct=True,method="first");p["practical"]=(~p.suspended.fillna(True))&(p.age>=252)&(p.Close>=5)&(p.Volume>0)&p.CircMV.notna()&(adv>.5)
    cyq=cyq.copy();cyq["TradingDay"]=pd.to_datetime(cyq.trade_date.astype(str));cyq["Symbol"]=cyq.ts_code.astype(str).str[:6]
    for c in ["winner_rate","cost_15pct","cost_85pct","weight_avg"]: cyq[c]=pd.to_numeric(cyq[c],errors="coerce")
    dates_available=sorted(cyq.TradingDay.unique());sessions=sorted(p.loc[p.TradingDay>=pd.Timestamp(start),"TradingDay"].drop_duplicates());decision_days=[pd.Timestamp(x) for x in dates_available if pd.Timestamp(x)>=pd.Timestamp(start) and pd.Timestamp(x)<=pd.Timestamp(end)]
    targets={"chip":{},"analyst_base":{},"analyst_overlay":{}};signals=[];all_symbols=set()
    for day in decision_days:
        u=p[(p.TradingDay==day)&p.practical].nlargest(500,"CircMV");snapshot=cyq[cyq.TradingDay==day]
        u=u.merge(snapshot[["Symbol","winner_rate","cost_15pct","cost_85pct","weight_avg"]],on="Symbol",how="inner")
        if len(u)<300: continue
        u["chip_balance"]=-np.abs(u.winner_rate-50.0);u["chip_width"]=(u.cost_85pct-u.cost_15pct)/u.weight_avg
        bench=float(u._fwd20.mean());u["active20"]=u._fwd20-bench
        signals.extend({"signal_date":day,"symbol":r.Symbol,"chip_balance":r.chip_balance,"winner_rate":r.winner_rate,"chip_width":r.chip_width,"active20":r.active20} for r in u.itertuples(index=False))
        chip=u.dropna(subset=["chip_balance"]).sort_values(["chip_balance","Symbol"],ascending=[False,True]).head(30)
        rev=consensus_revisions(reports,day);c=u.merge(rev,on="Symbol",how="inner");base=c[c.revision>0].sort_values(["revision","current_count","Symbol"],ascending=[False,False,True]).head(30)
        cutoff=float(u.winner_rate.quantile(.80));overlay=c[(c.revision>0)&(c.winner_rate<=cutoff)].sort_values(["revision","current_count","Symbol"],ascending=[False,False,True]).head(30)
        key=day.date().isoformat();targets["chip"][key]=chip.Symbol.astype(str).tolist();targets["analyst_base"][key]=base.Symbol.astype(str).tolist();targets["analyst_overlay"][key]=overlay.Symbol.astype(str).tolist()
        all_symbols.update(targets["chip"][key]+targets["analyst_base"][key]+targets["analyst_overlay"][key])
    cols=["TradingDay","Symbol","adj_open","adj_close","Open","High","Low","Close","Volume","PctChange"]
    market=p[p.Symbol.isin(all_symbols)&p.TradingDay.isin(sessions)][cols].set_index(["TradingDay","Symbol"]).sort_index();dates=[d.date().isoformat() for d in sessions]
    def lookup(date,symbol):
        try:r=market.loc[(pd.Timestamp(date),symbol)]
        except KeyError:return None
        return Bar(adj_open=float(r.adj_open),adj_close=float(r.adj_close),raw_open=float(r.Open),raw_high=float(r.High),raw_low=float(r.Low),raw_close=float(r.Close),volume=float(r.Volume),pct_change=float(r.PctChange))
    meta={"panel_version":built.version_hash,"decisions":len(targets["chip"]),"symbols":len(all_symbols)};del p;gc.collect();return dates,lookup,targets,pd.DataFrame(signals),meta


def run(cyq_path,reports_dir,start,end,benchmark_path):
    cyq=pd.read_csv(cyq_path,dtype={"trade_date":str,"ts_code":str});reports=load_reports(reports_dir);dates,lookup,targets,signals,meta=build_inputs(start,end,cyq,reports);bench=benchmark_returns(benchmark_path,dates)
    results={}
    for name in targets:
        cfg=BasketConfig(name=name,target_count=30,initial_nav=400_000,buy_cost=.00155,sell_cost=.00155);gcfg=BasketConfig(name=name+"_gross",target_count=30,initial_nav=400_000,buy_cost=0,sell_cost=0)
        net=simulate_basket(dates,lookup,targets[name],cfg);gross=simulate_basket(dates,lookup,targets[name],gcfg);results[name]=summarize_basket(net,gross,bench,cfg,folds=FOLDS)
    ic=ic_summary(signals);base=results["analyst_base"];over=results["analyst_overlay"]
    overlay_checks={"drawdown":over["metrics"]["max_drawdown"]>=base["metrics"]["max_drawdown"]+.03,"sharpe":over["metrics"]["sharpe"]>=base["metrics"]["sharpe"]+.05,"cagr":over["metrics"]["cagr"]>=base["metrics"]["cagr"]-.01,"folds":over["positive_excess_folds"]==3}
    chip=results["chip"];chip_checks={"ic":ic["mean"]>=.02,"t":ic["t_stat"]>=2,"cagr":chip["metrics"]["cagr"]>=.10,"sharpe":chip["metrics"]["sharpe"]>=.8,"drawdown":chip["metrics"]["max_drawdown"]>=-.30,"folds":chip["positive_excess_folds"]==3}
    verdict="GO" if all(overlay_checks.values()) or all(chip_checks.values()) else "NO-GO"
    return json_clean({"study":"a-share-chip-pressure-v1","data":{**meta,"cyq_rows":len(cyq)},"ic":ic,"portfolios":results,"decision":{"verdict":verdict,"overlay_checks":overlay_checks,"chip_checks":chip_checks}})

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument("--cyq",default="overall/a-share-cyq-month-ends.csv");p.add_argument("--reports",default="overall/a-share-report-rc-raw");p.add_argument("--start",default="2018-01-31");p.add_argument("--end",default="2026-08-25");p.add_argument("--benchmark",default="overall/a-share-multi-asset-etf-daily.csv");p.add_argument("--out-json",default="overall/a-share-chip-pressure.json");p.add_argument("--out-md",default="overall/a-share-chip-pressure.md");a=p.parse_args(argv);payload=run(a.cyq,a.reports,a.start,a.end,a.benchmark);Path(a.out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");c=payload["portfolios"]["chip"]["metrics"];o=payload["portfolios"]["analyst_overlay"]["metrics"];b=payload["portfolios"]["analyst_base"]["metrics"];text=f"# A股筹码成本压力结果\n\n- verdict: **{payload['decision']['verdict']}**\n- chip IC: {payload['ic']['mean']:.4f}; t: {payload['ic']['t_stat']:.2f}\n- chip CAGR/Sharpe/MDD: {c['cagr']:.2%}/{c['sharpe']:.3f}/{c['max_drawdown']:.2%}\n- analyst overlay vs base: {o['cagr']:.2%}/{o['sharpe']:.3f}/{o['max_drawdown']:.2%} vs {b['cagr']:.2%}/{b['sharpe']:.3f}/{b['max_drawdown']:.2%}\n";Path(a.out_md).write_text(text,encoding="utf-8");print(text);return 0
if __name__=="__main__":raise SystemExit(main())
