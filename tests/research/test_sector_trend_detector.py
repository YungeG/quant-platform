from __future__ import annotations
import pandas as pd
from experiments.build_sector_trend_states import run
from experiments.evaluate_false_breakout_rejection import metrics
from experiments.false_breakout import BreakoutStatus,classify_three_day_hold
from experiments.true_breakout import TrueBreakoutStatus,classify_ten_day_progress

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
