import json
from fractions import Fraction
from types import SimpleNamespace

import pytest
from experiments import l2_window_horizon_v13 as m
from experiments.l2_cash_risk_wait_v10 import evaluate_path


def fixture():
    calendar=[str(20260901+i) for i in range(21)]
    bars={d:{'open':'100','high':'125','low':str(100-i),'close':str(100+i)} for i,d in enumerate(calendar[1:],1)}
    return calendar,bars,calendar[0]


@pytest.mark.parametrize('h',[3,5,10,20])
def test_requested_horizon_complete_not_false_censored_by_legacy_helper(h):
    calendar,bars,signal=fixture();r=m.evaluate_probe(calendar,bars,signal,h)
    assert r['path_complete'] and not r['right_censored'] and r['expected_days']==h
    assert r['horizon_market_days']==h and r['horizon_end_day']==calendar[h]
    assert Fraction(r['raw_adverse_move_pct_observed'])==h
    assert r['raw_endpoint_up'] is True
    assert r['raw_within_limit_and_endpoint_up'] is (h<=10)
    if h<10:assert r['legacy_late_up'] is r['legacy_within_limit_and_late_up'] is None


def test_nested_horizons_mechanically_reduce_risk_not_evidence_of_alpha():
    calendar,bars,signal=fixture()
    values=[Fraction(m.evaluate_probe(calendar,bars,signal,h)['raw_adverse_move_pct_observed']) for h in m.HORIZONS]
    assert values==sorted(values)


def test_five_day_endpoint_up_does_not_use_identical_first_last_five_means():
    calendar,bars,signal=fixture();r=m.evaluate_probe(calendar,bars,signal,5)
    assert r['raw_within_limit_and_endpoint_up'] is True and r['legacy_late_up'] is None


@pytest.mark.parametrize('h',[10,20])
def test_supported_legacy_risk_and_late_labels_unchanged(h):
    calendar,bars,signal=fixture();r=m.evaluate_probe(calendar,bars,signal,h);old=evaluate_path(calendar,bars,signal,h)
    for k in ['reference_day','reference_raw_open','path_complete','raw_risk_state','raw_adverse_move_pct_observed','risk_line_first_breach_day','first3_rising_closes_wait_sessions']:
        assert r[k]==old[k]
    assert r['legacy_late_up']==old['raw_late_up_full_horizon']
    assert r['legacy_within_limit_and_late_up']==old['raw_lowrisk_late_up_candidate']


def test_missing_entry_no_shift_and_partial_observed_breach_stays_failure():
    calendar,bars,signal=fixture();bars.pop(calendar[1])
    assert m.evaluate_probe(calendar,bars,signal,3)['raw_risk_state']=='unknown_reference'
    calendar,bars,signal=fixture();bars[calendar[2]]['low']='89.999';bars.pop(calendar[3])
    r=m.evaluate_probe(calendar,bars,signal,3)
    assert not r['path_complete'] and r['raw_risk_state']=='breached_observed'
    assert r['raw_within_limit_and_endpoint_up'] is False and r['raw_endpoint_up'] is None


def test_exact_ten_touch_not_breach():
    calendar,bars,signal=fixture()
    for d in calendar[1:4]:bars[d]['low']='90'
    r=m.evaluate_probe(calendar,bars,signal,3)
    assert r['risk_line_first_touch_day']==calendar[1] and r['risk_line_first_breach_day'] is None
    assert r['raw_within_limit_and_endpoint_up'] is True


@pytest.mark.parametrize('h',[True,0,4,30])
def test_no_implicit_unbounded_parameter_sweep(h):
    calendar,bars,signal=fixture()
    with pytest.raises(ValueError):m.evaluate_probe(calendar,bars,signal,h)


def test_selected_denominator_unknown_and_empty_not_zero():
    calendar,bars,signal=fixture();known=m.evaluate_probe(calendar,bars,signal,3)
    unknown=m.evaluate_probe(calendar,{},signal,3)
    rs=[{'panel':'p','arm':'a',**r} for r in [known,unknown]]
    counts=[{'panel':'p','arm':'a','selected_n':2,'planned_n':20}]
    summary=m.summarize(rs,counts,[3])[0]
    assert summary['joint_endpoint_positive']==1 and summary['joint_unknown']==1
    assert summary['joint_lower_pct']=='50' and summary['joint_upper_pct']=='100'
    empty=m.summarize([], [{**counts[0],'selected_n':0}],[3])[0]
    assert empty['joint_lower_pct'] is None


def test_metadata_handles_parenthesized_archive_and_never_extracts(tmp_path,monkeypatch):
    root=tmp_path/'source';(root/'202609').mkdir(parents=True)
    archive=root/'202609'/'20260917(1).7z';archive.write_bytes(b'not a real archive')
    scope={'metadata_only':True,'dates':['20260917'],'asof':'20260917','source':str(root),
           'symbols':['000001.SZ'],'kinds':['行情.csv','逐笔成交.csv'],'file_bytes_max':100,
           'per_listing_timeout_seconds':1,'single_listing_max_bytes':10000,'metadata_stdout_budget_bytes':10000,
           'selected_bytes_max':0,'involved_solid_bytes_max':0}
    sp=tmp_path/'scope.json';sp.write_text(json.dumps(scope))
    text='archive header\n----------\nPath = 20260917/000001.SZ/行情.csv\nSize = 1\nCRC = 12345678\nEncrypted = -\nBlock = 0\nAttributes = A\n'
    def listing(args,**kwargs):
        assert args[:3]==['7z','l','-slt'] and args[-1]==str(archive)
        return SimpleNamespace(returncode=0,stdout=text)
    monkeypatch.setattr(m.subprocess,'run',listing)
    output=tmp_path/'inventory.json';result=m.inventory(sp,output)
    assert result['payload_extracted'] is False and result['exceeds_previous_selected_budget'] is True
    saved=json.loads(output.read_text())
    assert saved['archives'][0]['path']==str(archive) and len(saved['missing_members'])==1
    assert len(saved['members'])==1
