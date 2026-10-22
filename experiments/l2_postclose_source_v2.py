"""Bounded delivery-format reader and exact reference-group arithmetic.

No source acceptance, trading, account identity or inference. Money is always
integer CNY*10000. Group scope is the observed stock/day/side reference proxy,
NOT an invented exchange channel or proof of original-order uniqueness.
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
import zlib
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.l2_postclose_core_v1 import MAX_INT, SUPPORTED_SYMBOLS, PostcloseSpec

_MAX_FILE=256*1024**2
_TEXT_INT_RE=re.compile(r'^[+-]?\d+(?:\.\d+)?$')
_TRADE_HEADER=('万得代码','交易所代码','自然日','时间','成交编号','成交代码','委托代码','BS标志','成交价格','成交数量','叫卖序号','叫买序号','')
_ORDER_HEADER=('万得代码','交易所代码','自然日','时间','委托编号','交易所委托号','委托类型','委托代码','委托价格','委托数量','')
_QUOTE_REQUIRED={'万得代码','交易所代码','自然日','时间','成交价','当日累计成交量','成交笔数','当日成交额'}


def exact_integer(value,name='value',minimum=0,maximum=MAX_INT):
    if isinstance(value,(bool,np.bool_)):
        raise ValueError(f'{name}: bool not accepted')
    if isinstance(value,(int,np.integer)):
        number=int(value)
    elif isinstance(value,str):
        text=value.strip()
        if not _TEXT_INT_RE.fullmatch(text):
            raise ValueError(f'{name}: invalid integer text')
        decimal=Decimal(text)
        if decimal!=decimal.to_integral_value():
            raise ValueError(f'{name}: nonintegral value')
        number=int(decimal)
    elif isinstance(value,(float,np.floating)):
        raise ValueError(f'{name}: float not accepted; use exact text')
    else:
        raise ValueError(f'{name}: unsupported type')
    if number<minimum: raise ValueError(f'{name}: below minimum')
    if number>maximum: raise ValueError(f'{name}: overflow')
    return number


def _day(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{8}',value): raise ValueError('malformed day')
    try: datetime.strptime(value,'%Y%m%d')
    except ValueError as exc: raise ValueError('malformed day') from exc


def _clock(value):
    t=exact_integer(value,'time',maximum=239999999)
    h,m,s=t//10000000,t//100000%100,t//1000%100
    if h>=24 or m>=60 or s>=60: raise ValueError('invalid time components')
    return ((h*60+m)*60+s)*1000+t%1000


def read_bound_csv(path,meta,kind,day,symbol):
    _day(day)
    if symbol not in SUPPORTED_SYMBOLS: raise ValueError('unsupported symbol')
    if kind not in ('行情.csv','逐笔委托.csv','逐笔成交.csv'): raise ValueError('unknown kind')
    if not isinstance(meta,dict) or type(meta.get('bytes')) is not int or meta['bytes']<=0:
        raise ValueError('meta bytes must be positive int')
    if meta['bytes']>_MAX_FILE: raise ValueError('file exceeds 256MiB')
    if not re.fullmatch(r'[0-9a-f]{64}',str(meta.get('sha256',''))): raise ValueError('invalid sha256')
    if not re.fullmatch(r'[0-9a-fA-F]{8}',str(meta.get('crc32',''))): raise ValueError('invalid crc32')
    path=Path(path)
    if path.is_symlink(): raise ValueError('symlink not accepted')
    if not path.is_file(): raise ValueError('not a regular file')
    with path.open('rb') as stream: raw=stream.read(_MAX_FILE+1)
    if len(raw)>_MAX_FILE: raise ValueError('file exceeds 256MiB')
    if len(raw)!=meta['bytes']: raise ValueError('size mismatch')
    sha=hashlib.sha256(raw).hexdigest();crc=f'{zlib.crc32(raw)&0xffffffff:08x}'
    if sha!=meta['sha256']: raise ValueError('sha256 mismatch')
    if crc!=meta['crc32'].lower(): raise ValueError('crc32 mismatch')
    reader=csv.reader(io.StringIO(raw.decode('gb18030')))
    header=next(reader,None)
    expected=67 if kind=='行情.csv' else (13 if kind=='逐笔成交.csv' else 11)
    if header is None or len(header)!=expected: raise ValueError('header width mismatch')
    if header[-1].strip() or len(set(header[:-1]))!=len(header)-1: raise ValueError('invalid or duplicate header')
    if kind=='行情.csv':
        if not _QUOTE_REQUIRED.issubset(header): raise ValueError('missing required quote columns')
    elif tuple(header)!=(_TRADE_HEADER if kind=='逐笔成交.csv' else _ORDER_HEADER):
        raise ValueError('source header fields mismatch')
    rows=[]
    for row in reader:
        if len(row)!=expected: raise ValueError('row width mismatch')
        if row[-1].strip(): raise ValueError('trailing field not empty')
        rows.append(row[:-1])
    if not rows: raise ValueError('no data records')
    frame=pd.DataFrame(rows,columns=header[:-1])
    for name,value in (('万得代码',symbol),('交易所代码',symbol[:6]),('自然日',day)):
        if not frame[name].eq(value).all(): raise ValueError(f'{name} mismatch')
    frame['_source_record']=np.arange(1,len(frame)+1)
    frame['ms']=frame['时间'].map(_clock)
    detail={'path':str(path),'bytes':len(raw),'sha256':sha,'crc32':crc,'rows':len(frame),'record_count':len(frame),'nul_bytes':raw.count(b'\0'),'time_reversals':int((frame.ms.diff()<0).sum()),'row_coordinate':'CSV data-record ordinal; header excluded','header':header}
    return frame,detail


def _known_ref(value):
    if not isinstance(value,str): return None
    text=value.strip()
    if not text or not text.isdigit(): return None
    try: positive=int(text)>0
    except ValueError: return None
    return text if positive else None


def _true_integer(value,name):
    if isinstance(value,(bool,np.bool_)) or not isinstance(value,(int,np.integer)):
        raise ValueError(f'{name}: requires normalized true integer')
    return exact_integer(value,name,minimum=1)


def reference_group_facts(records,spec,confirmed_collision_keys=frozenset()):
    if not isinstance(spec,PostcloseSpec): raise ValueError('spec must be PostcloseSpec')
    required={'day','symbol','record_key','price_raw','quantity','buy_ref','sell_ref'}
    if not isinstance(records,pd.DataFrame) or not required.issubset(records): raise ValueError('missing columns')
    if records.empty: raise ValueError('empty records')
    if set(records.symbol)-set(spec.symbols): raise ValueError('symbols outside spec')
    for d in records.day.unique(): _day(d)
    if any(not isinstance(k,str) or not k.strip() for k in records.record_key): raise ValueError('empty record_key')
    if records.duplicated(['day','symbol','record_key']).any(): raise ValueError('duplicate record_key')
    if 'channel' in records and records.channel.dropna().astype(str).str.strip().replace('',pd.NA).dropna().nunique()>1:
        raise ValueError('needs namespace-aware profile: multiple channels')
    if not isinstance(confirmed_collision_keys,frozenset): raise ValueError('collision keys must be frozen')
    for key in confirmed_collision_keys:
        if not isinstance(key,tuple) or len(key)!=4 or key[2] not in ('B','S') or _known_ref(key[3]) is None:
            raise ValueError('malformed confirmed collision key')
        _day(key[0])
        if key[1] not in spec.symbols: raise ValueError('collision outside symbol scope')
    # Use the same lexical normalization as grouping; evidence must not be
    # silently ignored because its reference carries surrounding whitespace.
    confirmed_collision_keys=frozenset((k[0],k[1],k[2],_known_ref(k[3])) for k in confirmed_collision_keys)
    data=records.copy()
    prices=[_true_integer(v,'price_raw') for v in data.price_raw]
    quantities=[_true_integer(v,'quantity') for v in data.quantity]
    amounts=[exact_integer(p*q,'record cash',minimum=1) for p,q in zip(prices,quantities)]
    data['quantity']=pd.Series(quantities,index=data.index,dtype=object)
    data['_cash']=pd.Series(amounts,index=data.index,dtype=object)
    all_groups=[];daily_rows=[]
    for (day,symbol),part in data.groupby(['day','symbol'],sort=False):
        total=exact_integer(sum(part._cash),'whole-day cash',minimum=1)
        qty=exact_integer(sum(part.quantity),'whole-day quantity',minimum=1)
        side_info={}
        for side,column in (('B','buy_ref'),('S','sell_ref')):
            refs=part[column].map(_known_ref)
            valid=refs.notna()
            known=part.loc[valid,['quantity','_cash']].copy();known['reference']=refs.loc[valid]
            grouped=known.groupby('reference',sort=False).agg(quantity=('quantity','sum'),amount_1e4=('_cash','sum'),record_count=('_cash','size')).reset_index()
            for c in ('quantity','amount_1e4'):
                grouped[c]=pd.array([exact_integer(v,c,minimum=1) for v in grouped[c]],dtype='Int64')
            grouped['day']=day;grouped['symbol']=symbol;grouped['side']=side
            grouped['vwap']=grouped.amount_1e4.astype(float)/grouped.quantity.astype(float)/10000
            grouped['identity_kind']='delivered_reference_group_proxy';grouped['original_order_identity_proven']=False
            all_groups.append(grouped)
            known_cash=exact_integer(sum(known._cash),'known side cash')
            if sum(grouped.amount_1e4)!=known_cash or sum(grouped.quantity)!=sum(known.quantity):
                raise ValueError('known-side conservation failure')
            present=set(grouped.reference)
            collisions=sum(key[0]==day and key[1]==symbol and key[2]==side and key[3] in present for key in confirmed_collision_keys)
            complete=bool(valid.all())
            info={'known':known_cash,'missing':int((~valid).sum()),'complete':complete,'collisions':collisions,'large':{}}
            for threshold in spec.thresholds_cny:
                large=grouped.loc[grouped.amount_1e4>=threshold*10000]
                cash=exact_integer(sum(large.amount_1e4),'large cash')
                q=exact_integer(sum(large.quantity),'large qty')
                info['large'][threshold]=(cash if complete and not collisions else None,cash/q/10000 if q and complete and not collisions else None)
            side_info[side]=info
        buy,sell=side_info['B'],side_info['S']
        for threshold in spec.thresholds_cny:
            bm,bv=buy['large'][threshold];sm,sv=sell['large'][threshold]
            daily_rows.append({'day':day,'symbol':symbol,'threshold_cny':threshold,'amount_1e4':total,'quantity':qty,'known_buy_amount_1e4':buy['known'],'known_sell_amount_1e4':sell['known'],'missing_buy_records':buy['missing'],'missing_sell_records':sell['missing'],'buy_reference_complete':buy['complete'],'sell_reference_complete':sell['complete'],'large_buy_1e4':bm,'large_sell_1e4':sm,'large_buy_vwap':bv,'large_sell_vwap':sv,'structure_imbalance':(bm-sm)/total if bm is not None and sm is not None else None,'large_participation':(bm+sm)/(2*total) if bm is not None and sm is not None else None,'confirmed_collision_count':buy['collisions']+sell['collisions']})
    group_columns=['day','symbol','side','reference','quantity','amount_1e4','record_count','vwap','identity_kind','original_order_identity_proven']
    groups=pd.concat(all_groups,ignore_index=True)[group_columns]
    daily=pd.DataFrame(daily_rows)
    for c in ('amount_1e4','quantity','known_buy_amount_1e4','known_sell_amount_1e4','large_buy_1e4','large_sell_1e4'):
        daily[c]=pd.array([r[c] for r in daily_rows],dtype='Int64')
    return groups,daily
