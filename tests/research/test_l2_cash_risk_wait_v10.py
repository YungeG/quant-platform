"""Synthetic raw-path checks, not claims about executable investment returns."""
from datetime import date, timedelta
import pytest
from experiments.l2_cash_risk_wait_v10 import evaluate_path, signal_events, FAMILIES

CAL=[(date(2026,1,1)+timedelta(days=i)).strftime('%Y%m%d') for i in range(31)]


def bars(n=30,close='105',low='95',high='110'):
    return {CAL[i]:{'open':'100','close':close,'low':low,'high':high} for i in range(1,n+1)}


def test_exact_10pct_touch_is_not_exceeded():
    data=bars(low='90')
    r=evaluate_path(CAL,data,CAL[0],10)
    assert r['path_complete'] and r['raw_risk_state']=='within_limit_complete'
    assert r['risk_line_first_touch_day']==CAL[1]
    assert r['risk_line_first_breach_day'] is None
    assert r['raw_adverse_move_pct_observed']=='10'


def test_early_breach_not_erased_by_later_gain():
    data=bars(close='120',low='95',high='125');data[CAL[2]]['low']='89'
    r=evaluate_path(CAL,data,CAL[0],10)
    assert r['raw_risk_state']=='breached_observed'
    assert r['raw_close_change_pct_full_horizon']=='20'
    assert r['raw_lowrisk_late_up_candidate'] is False


def test_partial_observed_breach_is_known_limit_failure():
    data=bars(3,low='89')
    r=evaluate_path(CAL[:4],data,CAL[0],10)
    assert not r['path_complete'] and r['right_censored']
    assert r['raw_risk_state']=='breached_observed'
    assert r['raw_lowrisk_late_up_candidate'] is False
    assert 'raw_close_change_pct_full_horizon' not in r


def test_partial_no_breach_is_pending_not_success_or_failure():
    r=evaluate_path(CAL[:4],bars(3),CAL[0],10)
    assert r['raw_risk_state']=='unknown_incomplete'
    assert r['raw_lowrisk_late_up_candidate'] is None


def test_internal_missing_bar_not_skipped_or_zero_filled():
    data=bars();del data[CAL[5]]
    r=evaluate_path(CAL,data,CAL[0],10)
    assert not r['path_complete'] and not r['right_censored']
    assert r['price_missing_dates']==CAL[5]
    assert r['raw_risk_state']=='unknown_incomplete'


def test_missing_entry_not_shifted_to_next_available_open():
    data=bars();del data[CAL[1]]
    r=evaluate_path(CAL,data,CAL[0],10)
    assert r['reference_day']==CAL[1] and r['raw_risk_state']=='unknown_reference'
    assert 'reference_raw_open' not in r


def test_signal_close_not_used_as_reference():
    data=bars();data[CAL[0]]={'open':'1','close':'1','low':'1','high':'1'}
    r=evaluate_path(CAL,data,CAL[0],10)
    assert r['reference_raw_open']=='100' and r['raw_adverse_move_pct_observed']=='5'


def test_highest_intraday_price_does_not_define_late_strength():
    data=bars(close='99',low='95',high='200')
    r=evaluate_path(CAL,data,CAL[0],10)
    assert r['raw_favorable_move_pct_observed']=='100'
    assert r['raw_late_up_full_horizon'] is False
    assert r['raw_lowrisk_late_up_candidate'] is False


def test_low_adverse_wait_then_late_rise_can_pass20_not10():
    data=bars(close='100',low='95',high='150')
    for i in range(11,21):data[CAL[i]]['close']=str(100+(i-10)*3)
    a=evaluate_path(CAL,data,CAL[0],10);b=evaluate_path(CAL,data,CAL[0],20)
    assert a['raw_risk_state']==b['raw_risk_state']=='within_limit_complete'
    assert a['raw_lowrisk_late_up_candidate'] is False
    assert b['raw_lowrisk_late_up_candidate'] is True
    assert b['first3_rising_closes_wait_sessions']==12


def test_rising_wait_does_not_compress_missing_market_days():
    data=bars(close='99')
    data[CAL[1]]['close']='101';data[CAL[2]]['close']='102';del data[CAL[3]];data[CAL[4]]['close']='103'
    r=evaluate_path(CAL,data,CAL[0],10)
    assert r['first3_rising_closes_wait_sessions'] is None


@pytest.mark.parametrize('bad',[5,15,0,10.0,'10'])
def test_only_approved_future_horizons(bad):
    with pytest.raises(ValueError):evaluate_path(CAL,bars(),CAL[0],bad)


def signals(states):
    return [{'day':CAL[i],'cash_window_ready':'False' if s is None else 'True',
             'group_buy_bias':'' if s is None else str(s),'active_support':str(s is True)} for i,s in enumerate(states)]


def test_consecutive_true_dates_one_event_with_run_length():
    e=signal_events(signals([False,True,True,False,True]),FAMILIES[0])
    assert len(e)==2 and e[0]['visible_run_days']==2
    assert e[0]['boundary']=='confirmed_false_to_true' and e[0]['first_visible_event']
    assert not e[1]['first_visible_event']


def test_unknown_to_true_is_not_a_confirmed_new_episode():
    e=signal_events(signals([True,None,True]),FAMILIES[0])
    assert len(e)==2 and all(r['boundary']=='unknown_prior_boundary' for r in e)
    assert e[0]['run_end_reason']=='unknown_cash'


def test_passive_buyer_state_not_deleted_by_joint_family():
    r=signals([False,True]);r[1]['active_support']='False'
    assert len(signal_events(r,FAMILIES[0]))==1
    assert signal_events(r,FAMILIES[1])==[]
