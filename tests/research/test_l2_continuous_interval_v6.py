from decimal import Decimal
import pytest
from experiments.l2_continuous_interval_v6 import interval_profile,profiles,concentration,cumulative_fall,streak,merge_cash_input,bounded_price_read,CASH_ALIASES


def days(deltas=(100,100,100,100,100),rates=(12,12,12,12,12)):
    out=[]
    for i,(g,rate) in enumerate(zip(deltas,rates)):
        b=1000+max(g,0);s=1000+max(-g,0)
        out.append({'symbol':'688137.SH','day':f'202609{14+i:02d}','turnover_rate':Decimal(rate),'cash_ready':True,'buy':b,'sell':s,'active_buy':b,'active_sell':s,'passive_buy':0,'passive_sell':0,'unknown_buy':0,'unknown_sell':0,'market_amount':10000,'raw_price':{'last_raw':100+i,'previous_raw':99+i}})
    return out


def test_low_turnover_day_not_removed_from_window_or_cash():
    ds=days((100,100,-150,100,100),(12,12,1,12,14));r=interval_profile(ds,5)
    assert r['cash_window_ready'] and r['observed_days']==5
    assert r['group_difference_1e4']==250 and r['high_turnover_days']==4
    assert Decimal(r['mean_turnover_pct'])==Decimal('10.2') and r['activity_candidate']


def test_invalid_day_keeps_activity_but_blocks_cash_and_not_zero_fill():
    ds=days();ds[2]['cash_ready']=False;r=interval_profile(ds,5)
    assert r['activity_window_ready'] and not r['cash_window_ready']
    assert '20260916' in r['invalid_cash_dates'] and 'group_difference_1e4' not in r


def test_missing_rate_does_not_erase_cash():
    ds=days();ds[2]['turnover_rate']=None;r=interval_profile(ds,5)
    assert r['cash_window_ready'] and not r['activity_window_ready']


def test_average_ten_exact_not_gt_ten():
    r=interval_profile(days(rates=(10,10,10,10,10)),5)
    assert not r['activity_candidate'] and r['high_turnover_days']==0


def test_single_pulse_is_not_persistent_and_concentration_denominator_positive_only():
    r=interval_profile(days((1000,-100,-100,-100,-100)),5)
    assert r['group_difference_1e4']==600 and not r['group_buy_bias']
    assert r['group_positive_days']==1 and Decimal(r['top1_share_of_positive_deltas'])==1
    assert r['max_cumulative_group_delta_fall_1e4']==400
    assert Decimal(concentration((100,-99,50),1))==Decimal(100)/150


def test_zero_or_no_positive_concentration_missing():
    assert concentration((0,-1,-2),1) is None
    assert streak([True,True,False,True])==2
    assert cumulative_fall((100,-30,-10,20))==40


def test_price_reference_continuity_never_mints_price_comparability():
    r=interval_profile(days(),5)
    assert r['raw_previous_close_links_checked']==4 and r['raw_previous_close_link_disagreements']==0
    assert r['raw_source_price_sequence_available'] and not r['price_comparability_qualified']
    assert r['qualified_price_change_pct'] is None and r['qualified_price_drawdown_pct'] is None


def test_raw_price_gap_does_not_remove_valid_cash():
    ds=days();ds[2]['raw_price']=None;r=interval_profile(ds,5)
    assert r['cash_window_ready'] and not r['raw_source_price_sequence_available']


def test_profile_missing_calendar_day_does_not_compress_sequence():
    ds=days();cal=tuple(d['day'] for d in ds);source=ds[:2]+ds[3:]
    r=next(r for r in profiles(source,cal) if r['symbol']=='688137.SH' and r['day']==cal[-1] and r['lookback']==5)
    assert not r['cash_window_ready'] and cal[2] in r['invalid_cash_dates']


def test_warmup_not_reported_as_complete_shorter_window():
    r=interval_profile(days()[:3],5)
    assert r['cash_reason']=='warmup' and not r['cash_window_ready'] and r['observed_days']==3


@pytest.mark.parametrize('W',[3,0,6,21])
def test_only_predeclared_windows(W):
    with pytest.raises(ValueError):interval_profile(days(),W)


def test_foreign_or_duplicate_days_rejected():
    ds=days();ds[1]['symbol']='688655.SH'
    with pytest.raises(ValueError,match='foreign'):interval_profile(ds,5)
    ds=days();ds[1]['day']=ds[0]['day']
    with pytest.raises(ValueError,match='duplicate'):interval_profile(ds,5)


@pytest.mark.parametrize('ids',[(3,5),(3,4,4,5),(3,4,5,5),()])
def test_loader_missing_duplicate_bands_cannot_qualify_cash(ids):
    parts=[{'band_id':i,**{field:'10' for field in CASH_ALIASES.values()}} for i in ids]
    merged=merge_cash_input({'observed_amount_1e4':'100','cash_fact_ready':'True'},parts,(3,4,5))
    assert not merged['cash_ready'] and merged['buy'] is None and merged['market_amount']==100
    ds=days();ds[2].update(merged);result=interval_profile(ds,5)
    assert result['activity_window_ready'] and not result['cash_window_ready']


def test_loader_complete_band_set_preserves_amounts():
    parts=[{'band_id':i,**{field:'10' for field in CASH_ALIASES.values()}} for i in (3,4,5)]
    result=merge_cash_input({'observed_amount_1e4':'100','cash_fact_ready':'True'},parts,(3,4,5))
    assert result['cash_ready'] and result['buy']==30


def test_price_budget_rejected_before_any_open(tmp_path,monkeypatch):
    from pathlib import Path
    path=tmp_path/'q.csv';path.write_bytes(b'a'*1024)
    def forbidden(*args,**kwargs):raise AssertionError('opened before budget rejection')
    monkeypatch.setattr(Path,'open',forbidden)
    with pytest.raises(ValueError,match='preflight'):bounded_price_read(path,1024,512)


def test_price_bounded_read_and_post_read_size_change_rejected(tmp_path,monkeypatch):
    from pathlib import Path
    path=tmp_path/'q.csv';path.write_bytes(b'abc');original=Path.open;limits=[]
    class Stream:
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def read(self,n):
            limits.append(n)
            with original(path,'wb') as f:f.write(b'abcdef')
            return b'abc'
    monkeypatch.setattr(Path,'open',lambda *args,**kwargs:Stream())
    with pytest.raises(ValueError,match='changed'):bounded_price_read(path,3,3)
    assert limits==[3]


def test_profiles_keep_all_stocks_scales_and_failures():
    ds=days();out=profiles(ds,tuple(d['day'] for d in ds))
    assert len(out)==5*5*3
    assert sum(r['cash_window_ready'] for r in out)==1
