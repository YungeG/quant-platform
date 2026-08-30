"""Reconstruct 2026 seed-to-diffusion-to-exhaustion volume waves."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
def future(index,n):return index.shift(-n)/index-1
def run(volume_panel,price_panel,waves_path,daily_path,out_json,out_md):
 v=pd.read_csv(volume_panel);v.trade_date=pd.to_datetime(v.trade_date);p=pd.read_csv(price_panel);p.trade_date=pd.to_datetime(p.trade_date);p=p.sort_values(["sector","trade_date"])
 for n in [30,35,40]:p[f"future{n}"]=p.groupby("sector").sector_index.transform(lambda s:future(s,n));p[f"benchmark_future{n}"]=p.groupby("sector").benchmark_index.transform(lambda s:future(s,n));p[f"active{n}"]=p[f"future{n}"]-p[f"benchmark_future{n}"]
 v=v.merge(p[["trade_date","sector",*[f"future{n}" for n in [30,35,40]],*[f"active{n}" for n in [30,35,40]]]],on=["trade_date","sector"],how="left");waves=[];daily=[]
 for sector,g in v.sort_values("trade_date").groupby("sector"):
  g=g.reset_index(drop=True);state="DORMANT";seed=None;diffusion=None;broad=None;seed_concentration=np.nan;low_breadth=0;low_flow=0;wave_id=None
  def close_wave(end_index,status):
   nonlocal seed,diffusion,broad,wave_id
   s=g.loc[seed];d=g.loc[diffusion] if diffusion is not None else None;path=g.loc[seed:end_index]
   if g.loc[end_index,"trade_date"]<pd.Timestamp("2026-01-01"):return
   seed_symbols=set(json.loads(s.focus_symbols));all_focus=set(symbol for value in path.focus_symbols for symbol in json.loads(value));waves.append({"wave_id":wave_id,"sector":sector,"status":status,"seed_date":s.trade_date.date().isoformat(),"diffusion_date":d.trade_date.date().isoformat() if d is not None else None,"broad_date":g.loc[broad].trade_date.date().isoformat() if broad is not None else None,"end_date":g.loc[end_index].trade_date.date().isoformat(),"duration_days":end_index-seed+1,"seed_leaders":json.dumps(sorted(seed_symbols),ensure_ascii=False),"new_focus_symbols":json.dumps(sorted(all_focus-seed_symbols),ensure_ascii=False),"max_abnormal_breadth":float(path.abnormal_breadth.max()),"max_focus_count":int(max(len(json.loads(value)) for value in path.focus_symbols)),"future30":float(d.future30) if d is not None and pd.notna(d.future30) else None,"future35":float(d.future35) if d is not None and pd.notna(d.future35) else None,"future40":float(d.future40) if d is not None and pd.notna(d.future40) else None,"active30":float(d.active30) if d is not None and pd.notna(d.active30) else None,"active35":float(d.active35) if d is not None and pd.notna(d.active35) else None,"active40":float(d.active40) if d is not None and pd.notna(d.active40) else None})
   for _,r in path.iterrows():daily.append({"wave_id":wave_id,"sector":sector,"trade_date":r.trade_date.date().isoformat(),"phase":"SEED" if diffusion is None or r.name<diffusion else ("BROAD" if broad is not None and r.name>=broad else "DIFFUSION"),"focus_symbols":r.focus_symbols,"abnormal_symbols":r.abnormal_symbols,"abnormal_breadth":r.abnormal_breadth,"new_entrant_rate":r.new_entrant_rate,"top5_excess_concentration":r.top5_excess_concentration,"focus_persistence":r.focus_persistence,"activity_entropy":r.activity_entropy})
  for i,row in g.iterrows():
   seed_condition=row.abnormal_breadth_pct120>=.8 and (g.loc[i-1,"abnormal_breadth_pct120"]<.8 if i>0 and pd.notna(g.loc[i-1,"abnormal_breadth_pct120"]) else False) and row.abnormal_count>=3 and row.top5_excess_concentration_pct120>=.5
   if state=="DORMANT":
    if seed_condition:state="SEED";seed=i;diffusion=None;broad=None;seed_concentration=row.top5_excess_concentration;wave_id=f"{row.trade_date.date()}|{sector}"
    continue
   if state=="SEED":
    last3=g.loc[max(seed,i-2):i,"abnormal_breadth_pct120"];diffusion_condition=len(last3)==3 and (last3>=.8).all() and row.new_entrant_rate_pct120>=.7 and row.top5_excess_concentration<seed_concentration
    if diffusion_condition:state="DIFFUSION";diffusion=i;low_breadth=0;low_flow=0
    elif i-seed>=10:close_wave(i,"FAILED_SEED");state="DORMANT";seed=None
    continue
   if state in {"DIFFUSION","BROAD"}:
    if state=="DIFFUSION" and row.abnormal_breadth_pct120>=.9 and row.activity_entropy_pct120>=.7:state="BROAD";broad=i
    low_breadth=low_breadth+1 if row.abnormal_breadth_pct120<.7 else 0;low_flow=low_flow+1 if row.new_entrant_rate_pct120<.5 and row.focus_persistence_pct120<.5 else 0
    if low_breadth>=3 or low_flow>=3:close_wave(i,"COMPLETED_WAVE");state="DORMANT";seed=None
  if seed is not None:close_wave(len(g)-1,"ACTIVE_SEED" if diffusion is None else "ACTIVE_WAVE")
 wave=pd.DataFrame(waves);day=pd.DataFrame(daily);wave.to_csv(waves_path,index=False);day.to_csv(daily_path,index=False);completed=wave[wave.status.eq("COMPLETED_WAVE")];diffused=wave[wave.diffusion_date.notna()];payload={"study":"a-share-2026-volume-diffusion-waves-v1","data":{"waves":len(wave),"failed_seeds":int((wave.status=="FAILED_SEED").sum()),"diffused_waves":len(diffused),"completed_waves":len(completed),"active_waves":int(wave.status.str.startswith("ACTIVE").sum())},"waves":wave.to_dict("records"),"summary":{"diffused_future35_count":int(diffused.future35.notna().sum()),"diffused_future35_mean":float(diffused.future35.mean()) if diffused.future35.notna().any() else None,"diffused_active35_mean":float(diffused.active35.mean()) if diffused.active35.notna().any() else None,"diffused_active35_median":float(diffused.active35.median()) if diffused.active35.notna().any() else None},"limitations":["2026-only descriptive reconstruction","price is outcome only","phase thresholds have not passed historical validation"]};Path(out_json).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n");lines=["# 2026板块内部成交量扩散波段","",f"- waves: {len(wave)}；failed seeds: {payload['data']['failed_seeds']}；diffused: {len(diffused)}；completed: {len(completed)}；active: {payload['data']['active_waves']}","","|板块|种子|扩散|普涨|结束|状态|35日收益|35日超额|初始龙头数|新增关注数|","|---|---|---|---|---|---|---:|---:|---:|---:|"]
 for r in wave.itertuples(index=False):lines.append(f"|{r.sector}|{r.seed_date}|{r.diffusion_date or ''}|{r.broad_date or ''}|{r.end_date}|{r.status}|{'' if pd.isna(r.future35) else f'{r.future35:.2%}'}|{'' if pd.isna(r.active35) else f'{r.active35:.2%}'}|{len(json.loads(r.seed_leaders))}|{len(json.loads(r.new_focus_symbols))}|")
 Path(out_md).write_text("\n".join(lines)+"\n");return payload
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--volume-panel",default="overall/a-share-volume-diffusion-panel.csv");p.add_argument("--price-panel",default="overall/a-share-2026-sector-volume-panel.csv");p.add_argument("--waves",default="overall/a-share-2026-volume-diffusion-waves.csv");p.add_argument("--daily",default="overall/a-share-2026-volume-diffusion-wave-daily.csv");p.add_argument("--out-json",default="overall/a-share-2026-volume-diffusion-waves.json");p.add_argument("--out-md",default="overall/a-share-2026-volume-diffusion-waves.md");a=p.parse_args(argv);payload=run(a.volume_panel,a.price_panel,a.waves,a.daily,a.out_json,a.out_md);print(json.dumps(payload["data"],ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
