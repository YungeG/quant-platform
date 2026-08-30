from __future__ import annotations
from datetime import timedelta
import pandas as pd,pytest
from experiments.build_sector_trend_states import run
from experiments.evaluate_false_breakout_rejection import metrics
from experiments.false_breakout import BreakoutStatus,classify_three_day_hold
from experiments.true_breakout import TrueBreakoutStatus,classify_ten_day_progress,liquidated_basket_return
from experiments.evaluate_true_breakout_etf_execution import net_horizon_return,select_correlated_etf

def test_breakout_uses_prior_ten_sessions_and_enters_once(tmp_path):
 dates=pd.bdate_range("2024-01-02",periods=45);index=[1.0]*11+[1.0+0.01*i for i in range(1,35)];panel=pd.DataFrame({"trade_date":dates,"sector":"钢铁","sector_index":index,"benchmark_index":1.0,"relative20":0.1,"price_breadth":0.8});source=tmp_path/"panel.csv";states=tmp_path/"states.csv";positions=tmp_path/"positions.csv";labels=tmp_path/"labels.csv";panel.to_csv(source,index=False);run(str(source),str(states),str(positions),str(labels));s=pd.read_csv(states);entries=s[s.enter_signal.astype(str).str.lower().eq("true")];assert len(entries)==1;assert entries.iloc[0].trade_date==dates[11].date().isoformat();assert entries.iloc[0].sector_index>s.iloc[1:11].sector_index.max()

def test_leader_breadth_filter_rejects_narrow_breakout(tmp_path):
 dates=pd.bdate_range("2024-01-02",periods=25);index=[1.0]*11+[1.0+0.01*i for i in range(1,15)];panel=pd.DataFrame({"trade_date":dates,"sector":"钢铁","sector_index":index,"benchmark_index":1.0,"relative20":0.1,"price_breadth":0.5});source=tmp_path/"panel.csv";states=tmp_path/"states.csv";positions=tmp_path/"positions.csv";labels=tmp_path/"labels.csv";panel.to_csv(source,index=False);run(str(source),str(states),str(positions),str(labels),"leader_breadth");assert not pd.read_csv(states).enter_signal.astype(str).str.lower().eq("true").any()

def test_false_breakout_rejection_metrics():
 frame=pd.DataFrame({"confirmation_complete":[True]*4,"future20":[0.0]*4,"direct_true":[False,False,True,True],"held_abs_3":[False,True,False,True],"held_rel_3":[False,True,False,True]});result=metrics(frame);assert result["false_detection_precision"]==0.5;assert result["false_detection_recall"]==0.5;assert result["true_breakout_retention"]==0.5

def test_three_day_false_breakout_classifier():
 assert classify_three_day_hold([101,99,102],[101,102,103],100,100)==BreakoutStatus.FALSE_BREAKOUT_ABSOLUTE
 assert classify_three_day_hold([101,102,103],[101,99,103],100,100)==BreakoutStatus.FALSE_BREAKOUT_RELATIVE
 assert classify_three_day_hold([101,102],[101,102],100,100)==BreakoutStatus.PENDING_D3
 assert classify_three_day_hold([101,102,103],[101,102,103],100,100)==BreakoutStatus.BREAKOUT_HELD

def test_ten_day_true_breakout_classifier():
 held=[101+i for i in range(10)];assert classify_ten_day_progress(held,held,100,100,.08,.04)==TrueBreakoutStatus.TRUE_BREAKOUT_CONFIRMED
 assert classify_ten_day_progress(held,held,100,100,.05,.04)==TrueBreakoutStatus.UNCONFIRMED_BREAKOUT
 failed=held.copy();failed[4]=99;assert classify_ten_day_progress(failed,held,100,100,.08,.04)==TrueBreakoutStatus.FALSE_BREAKOUT_REJECTED
 assert classify_ten_day_progress(held[:5],held[:5],100,100,.08,.04)==TrueBreakoutStatus.PENDING_D10

def test_true_breakout_etf_return_charges_both_sides():
 assert net_horizon_return(110,100)==pytest.approx(1.1*(1-.0015)**2-1)

def test_correlated_etf_mapping_prefers_tracking_match():
 dates=pd.bdate_range("2024-01-02",periods=80);sector=pd.Series([.01 if i%2 else -.005 for i in range(80)],index=dates);prices={"MATCH.SH":pd.DataFrame({"adj_close":(1+sector).cumprod(),"amount":20000},index=dates),"OTHER.SH":pd.DataFrame({"adj_close":(1-sector).cumprod(),"amount":30000},index=dates)};candidates=pd.DataFrame({"ts_code":["MATCH.SH","OTHER.SH"],"industry":["钢铁","钢铁"],"list_date":[dates[0],dates[0]],"delist_date":[pd.NaT,pd.NaT]});code,_,correlation,common=select_correlated_etf(dates[-1]+timedelta(days=3),"钢铁",candidates,prices,{"钢铁":sector});assert code=="MATCH.SH";assert correlation>0.99;assert common==79

def test_stock_basket_liquidation_charges_sell_cost():
 assert liquidated_basket_return([400000,440000],[1.0,0.0],1)==pytest.approx(1.1*(1-.00155)-1)
