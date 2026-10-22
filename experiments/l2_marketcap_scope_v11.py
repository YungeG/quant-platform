"""As-of raw daily-basic total market-cap filter. Does not use later returns."""
from decimal import Decimal, InvalidOperation

MIN_CNY=Decimal('6000000000')
MAX_CNY=Decimal('100000000000')


def in_cap_range(value):
    try:n=Decimal(value)
    except (InvalidOperation,TypeError,ValueError):return None
    if not n.is_finite() or n<=0:return None
    return MIN_CNY<=n<=MAX_CNY


def select_marketcap(scope,basic_rows):
    by={}
    for r in basic_rows:
        if r['ts_code'] in by or r['trade_date']!=scope['asof']:
            raise ValueError('duplicate symbol or foreign daily-basic date')
        by[r['ts_code']]=r
    rows=[];selected=[]
    for symbol in scope['symbols']:
        r=by.get(symbol)
        state=None if r is None else in_cap_range(r.get('total_mv'))
        item={'symbol':symbol,'name':scope['names'][symbol],'asof':scope['asof'],'total_mv_cny':r.get('total_mv') if r else None,'eligible':state,'reason':'missing_or_invalid_total_mv' if state is None else ('in_60_1000_yi_total_cap' if state else 'outside_total_cap_range')}
        if state is True:selected.append(symbol)
        rows.append(item)
    return selected,rows
