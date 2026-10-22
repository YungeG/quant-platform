from decimal import Decimal
import pytest
from experiments.l2_marketcap_scope_v11 import in_cap_range,select_marketcap


@pytest.mark.parametrize('value,expected',[
 ('5999999999.99',False),('6000000000',True),('6000000000.01',True),
 ('100000000000',True),('100000000000.01',False),
 ('600000',False),('10000000',False), # Never interpret raw CNY as units of 1e4 CNY.
 ('NaN',None),('Infinity',None),('',None),(None,None),('0',None),
])
def test_total_cap_bounds_and_unknown(value,expected):
    assert in_cap_range(value) is expected


def test_total_not_circulating_cap_and_missing_not_negative():
    scope={'asof':'20261019','symbols':['000001.SZ','600000.SH','300001.SZ'],
           'names':{'000001.SZ':'A','600000.SH':'B','300001.SZ':'C'}}
    rows=[{'ts_code':'000001.SZ','trade_date':'20261019','total_mv':'7000000000','circ_mv':'100000000'},
          {'ts_code':'600000.SH','trade_date':'20261019','total_mv':'200000000000','circ_mv':'7000000000'}]
    selected,out=select_marketcap(scope,rows)
    assert selected==['000001.SZ'] and out[2]['eligible'] is None


def test_future_date_not_admitted():
    with pytest.raises(ValueError):select_marketcap({'asof':'20261019','symbols':[],'names':{}},[{'ts_code':'000001.SZ','trade_date':'20261021'}])
