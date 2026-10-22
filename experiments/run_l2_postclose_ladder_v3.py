"""Daily disjoint money bands and source-B/S liquidity-role proxies.

Local post-hoc descriptions only. No exchange-order, account, inventory,
forecast, Backtest, fee, fill or source-admission authority is created.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import json
from collections import defaultdict
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path,PurePosixPath

import pandas as pd

from experiments.l2_postclose_core_v1 import MAX_INT,PostcloseSpec
from experiments.l2_postclose_source_v2 import exact_integer
from experiments.run_l2_postclose_fund_flow_v2 import (
    ROOT,PROFILE,MANIFEST,RAW,digest,dump,load_binding,evaluate_day,
    _read_file,_column,_code,_reference,_exact_table,
)

EDGES=(0,50000,200000,500000,1000000,5000000)
SPEC=ROOT/'research/l2-postclose-ladder-active-v3-spec.md'
ROLES=('active','passive','unclassified')
ROLE_COUNTS=tuple(f'{prefix}_{role}_{suffix}' for role in ROLES for prefix,suffix in (('observed','quantity'),('observed','execution_legs'),('known','reference_groups')))


def validate_edges(edges):
    if not isinstance(edges,tuple) or not 1<=len(edges)<=12:
        raise ValueError('bands need 1..12 frozen lower bounds')
    if any(type(x) is not int or not 0<=x<=MAX_INT//10000 for x in edges):
        raise ValueError('band lower bounds must be exact supported CNY integers')
    if edges[0]!=0 or tuple(sorted(set(edges)))!=edges:
        raise ValueError('bands must start at zero and be sorted unique')
    return tuple(x*10000 for x in edges)


def band_label(i,edges):
    if i==-1: return '无法归组（大小未知）'
    low=edges[i]/10000
    if i==len(edges)-1: return f'≥{low:g}万'
    high=edges[i+1]/10000
    return f'{low:g}–{high:g}万'


def source_aggressor(bs,ms,buy_ref,sell_ref):
    """Only a source-marked, clock-scoped and internally checked proxy."""
    ms=exact_integer(ms,'ms',maximum=86399999)
    if not (34200000<=ms<41400000 or 46800000<=ms<53820000):
        return 'U','outside_continuous_clock_scope'
    code=_code(bs) if isinstance(bs,str) else ''
    if code not in ('B','S'): return 'U','unsupported_or_missing_BS'
    b=_reference(buy_ref) if isinstance(buy_ref,str) else None
    s=_reference(sell_ref) if isinstance(sell_ref,str) else None
    if b is None or s is None: return 'U','reference_rule_unverifiable'
    if int(b)==int(s): return 'U','equal_references'
    expected='B' if int(b)>int(s) else 'S'
    if code!=expected: return 'U','BS_reference_rule_conflict'
    return code,'source_marked_and_rule_consistent'


def normalized_records(trades,day,symbol):
    p=_column(trades,'成交价格');q=_column(trades,'成交数量')
    select=(p>0)&(q>0)
    t=trades.loc[select]
    return pd.DataFrame({'day':day,'symbol':symbol,'record_key':t['_source_record'].map(lambda x:f'record:{x}'),'price_raw':p.loc[select],'quantity':q.loc[select],'buy_ref':t['叫买序号'],'sell_ref':t['叫卖序号'],'source_bs':t['BS标志'],'ms':t['ms']})


def ladder_facts(records,groups,edges=EDGES):
    """Allocate executions using full-day group size BEFORE liquidity-role split.

    groups comes from the reused v2 group arithmetic; every membership/cash/
    quantity/count is checked again here. This pure function accepts no source.
    """
    scaled=validate_edges(edges)
    required={'day','symbol','record_key','price_raw','quantity','buy_ref','sell_ref','source_bs','ms'}
    if records.empty or not required.issubset(records): raise ValueError('missing/empty normalized executions')
    if records.duplicated(['day','symbol','record_key']).any(): raise ValueError('duplicate source record key')
    scopes=set(zip(records.day,records.symbol))
    if len(scopes)!=1: raise ValueError('one stock/day per allocation; never merge days')
    day,symbol=next(iter(scopes));gmap={};group_seen=defaultdict(lambda:[0,0,0])
    cells={};role_groups=defaultdict(set)
    for side in ('B','S'):
        for i in (*range(len(edges)),-1):
            cells[(side,i)]={'day':day,'symbol':symbol,'side':side,'band_id':i,'band':band_label(i,edges),'lower_cny':edges[i] if i>=0 else None,'upper_cny':edges[i+1] if 0<=i<len(edges)-1 else None,'observed_amount_1e4':0,'observed_quantity':0,'execution_legs':0,'known_reference_groups':0 if i>=0 else None,'observed_active_1e4':0,'observed_passive_1e4':0,'observed_unclassified_1e4':0,'identity_kind':'delivered_reference_group_proxy','original_order_identity_proven':False}
            for role in ROLES:
                cells[(side,i)].update({f'observed_{role}_quantity':0,f'observed_{role}_execution_legs':0,f'known_{role}_reference_groups':0 if i>=0 else None})
    for r in groups.to_dict('records'):
        if (r['day'],r['symbol'])!=(day,symbol) or r['side'] not in ('B','S'):
            raise ValueError('foreign group scope')
        ref=_reference(r['reference']);key=(r['side'],ref)
        if ref is None or key in gmap: raise ValueError('unknown/duplicate group identity')
        cash=exact_integer(r['amount_1e4'],'group cash',minimum=1)
        q=exact_integer(r['quantity'],'group quantity',minimum=1)
        n=exact_integer(r['record_count'],'group records',minimum=1)
        i=bisect.bisect_right(scaled,cash)-1
        gmap[key]=(i,cash,q,n);cells[(r['side'],i)]['known_reference_groups']+=1
    diagnostics=defaultdict(lambda:[0,0,0]);market={'day':day,'symbol':symbol,'observed_amount_1e4':0,'observed_quantity':0,'execution_records':0,'observed_active_buy_1e4':0,'observed_active_sell_1e4':0,'observed_unclassified_1e4':0}
    for r in records.to_dict('records'):
        p=exact_integer(r['price_raw'],'price_raw',minimum=1)
        q=exact_integer(r['quantity'],'quantity',minimum=1)
        cash=exact_integer(p*q,'execution cash',minimum=1)
        aggressor,reason=source_aggressor(r['source_bs'],r['ms'],r['buy_ref'],r['sell_ref'])
        d=diagnostics[(aggressor,reason,repr(r['source_bs']))];d[0]+=cash;d[1]+=q;d[2]+=1
        market['observed_amount_1e4']+=cash;market['observed_quantity']+=q;market['execution_records']+=1
        name={'B':'observed_active_buy_1e4','S':'observed_active_sell_1e4','U':'observed_unclassified_1e4'}[aggressor]
        market[name]+=cash
        for side,field in (('B','buy_ref'),('S','sell_ref')):
            ref=_reference(r[field]) if isinstance(r[field],str) else None
            if ref is None: i=-1
            else:
                if (side,ref) not in gmap: raise ValueError('execution has no full-day reference group')
                i=gmap[(side,ref)][0]
                actual=group_seen[(side,ref)];actual[0]+=cash;actual[1]+=q;actual[2]+=1
            cell=cells[(side,i)];cell['observed_amount_1e4']+=cash;cell['observed_quantity']+=q;cell['execution_legs']+=1
            kind='unclassified' if aggressor=='U' else ('active' if aggressor==side else 'passive')
            cell[f'observed_{kind}_1e4']+=cash
            cell[f'observed_{kind}_quantity']+=q
            cell[f'observed_{kind}_execution_legs']+=1
            if ref is not None: role_groups[(side,i,kind)].add(ref)
    for (side,i),cell in cells.items():
        for role in ROLES:
            if i>=0: cell[f'known_{role}_reference_groups']=len(role_groups[(side,i,role)])
    for key,(_,cash,q,n) in gmap.items():
        if group_seen[key]!=[cash,q,n]: raise ValueError('group membership/cash/quantity/count mismatch')
    for name in ('observed_amount_1e4','observed_quantity'):
        exact_integer(market[name],name,minimum=1)
        for side in ('B','S'):
            if sum(c[name] for (s,_),c in cells.items() if s==side)!=market[name]:
                raise ValueError('side conservation failure')
    for c in cells.values():
        if sum(c[f'observed_{k}_1e4'] for k in ROLES)!=c['observed_amount_1e4']:
            raise ValueError('liquidity-role conservation failure')
        if sum(c[f'observed_{k}_quantity'] for k in ROLES)!=c['observed_quantity'] or sum(c[f'observed_{k}_execution_legs'] for k in ROLES)!=c['execution_legs']:
            raise ValueError('role quantity/legs conservation failure')
    if market['observed_active_buy_1e4']+market['observed_active_sell_1e4']+market['observed_unclassified_1e4']!=market['observed_amount_1e4']:
        raise ValueError('market conservation failure')
    market['source_classified_cash_share']=(market['observed_active_buy_1e4']+market['observed_active_sell_1e4'])/market['observed_amount_1e4']
    market['aggression_kind']='source_BS_rule_checked_clock_subset_proxy_not_exchange_reconstruction'
    diag=[{'day':day,'symbol':symbol,'classification':a,'reason':reason,'raw_BS_repr':raw,'amount_1e4':v[0],'quantity':v[1],'records':v[2]} for (a,reason,raw),v in diagnostics.items()]
    return list(cells.values()),diag,market


def qualify(rows,observation,daily):
    # Side readiness comes from RECOMPUTED v2 facts, not an operator checkbox.
    primary=next(r for r in daily if r['threshold_cny']==1000000)
    ready={s:bool(observation['cash_fact_ready'] and not pd.isna(primary[f'large_{n}_1e4'])) for s,n in (('B','buy'),('S','sell'))}
    for r in rows:
        is_ready=bool(observation['cash_fact_ready'] and (r['band_id']==-1 or ready[r['side']]))
        r.update(cash_fact_ready=bool(observation['cash_fact_ready']),side_band_distribution_ready=ready[r['side']],complete_cell_ready=is_ready,cash_reason=observation['cash_reason'])
        for suffix in ('amount_1e4','active_1e4','passive_1e4','unclassified_1e4'):
            r[suffix]=r[f'observed_{suffix}'] if is_ready else None
    return rows


def wide_rows(cells):
    by={}
    for r in cells:
        key=(r['day'],r['symbol'],r['band_id'])
        w=by.setdefault(key,{'day':r['day'],'symbol':r['symbol'],'band_id':r['band_id'],'band':r['band']})
        side='buy' if r['side']=='B' else 'sell'
        for col in ('amount_1e4','active_1e4','passive_1e4','unclassified_1e4','observed_amount_1e4'):
            w[f'{side}_{col}']=r[col]
    for r in by.values():
        b,s=r.get('buy_amount_1e4'),r.get('sell_amount_1e4')
        r['difference_1e4']=int(b)-int(s) if b is not None and s is not None else None
    return list(by.values())


def money(v):
    return '待核' if v is None or pd.isna(v) else f'{Decimal(int(v))/Decimal(100000000):,.2f}'


def write_report(out,cells,markets,edges):
    wide=wide_rows(cells)
    last=max(m['day'] for m in markets)
    lines=['# 逐日互斥金额阶梯与源标记主动／被动','', f'**样本截止{last}，非报告当天实时资金。金额单位：万元。**','', '先按全日买／卖侧引用组成交额定档，再拆主动／被动；不是单笔大小，不跨日合组，不是机构身份或持仓留存。档位左闭右开，末档包含下界。买、卖各侧六档＋未知分别合计全日M，不能再将两侧相加当市场总额。','', 'B＝源标记主动买，对手卖方被动；S相反。仅采用09:30–11:30、13:00–14:57的半开时钟子集且标记／序号规则一致；其余金额保留未判。这是同源标记内校验，不是完整撮合、阶段或交易所时钟认证。','']
    lookup={(m['day'],m['symbol']):m for m in markets}
    keys=sorted({(r['day'],r['symbol']) for r in cells},reverse=True)
    for day,symbol in keys:
        m=lookup[(day,symbol)]
        lines.extend([f'## {day} {symbol}',''])
        if not m['cash_fact_ready']:
            lines.extend([f"**完整日不通过：{m['cash_reason']}。本节金额待核；已观察部分留CSV，不当成0。**",''])
        elif not m.get('allocation_available',False):
            lines.extend(['**分档不可用，详见来源错误。**',''])
        else:
            lines.extend([f"全日成交额 **{money(m['observed_amount_1e4'])}**；源规则可判时钟子集覆盖 **{m['source_classified_cash_share']:.2%}**。未判市场额 **{money(m['observed_unclassified_1e4'])}**。",''])
        lines.extend(['| 全日组金额档 | 买组额 | 卖组额 | 组差 | 主动买 | 被动买 | 买侧未判 | 主动卖 | 被动卖 | 卖侧未判 |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|'])
        for r in sorted((x for x in wide if (x['day'],x['symbol'])==(day,symbol)),key=lambda r:(r['band_id']==-1,r['band_id'])):
            fields=('buy_amount_1e4','sell_amount_1e4','difference_1e4','buy_active_1e4','buy_passive_1e4','buy_unclassified_1e4','sell_active_1e4','sell_passive_1e4','sell_unclassified_1e4')
            lines.append('| '+r['band']+' | '+' | '.join(money(r.get(k)) for k in fields)+' |')
        lines.append('')
    lines.extend(['## 边界','', '- 未知引用不是最小档；若某侧引用不全，该侧已知区间仅留观察额，完整区间金额待核。未知桶金额可观察，但不能判断其大小。','- 每笔可同时属于某买组和另一卖组，各自定档；主动买与被动卖是同一笔的两腿，不可相加作为两次成交。一个组可既有主动部分又有被动部分，故各角色去重组数不相加作总组数。','- 组差不等于主动买卖差；所有档组差合计为0，是不同大小编号组之间的结构差，不是全市场资金净流入。','- 被动买只是提供买方流动性的源标记角色，不代表承接成功、库存增加或后续会上涨。','- 10月12日仍未闭合，价格／公司行动、未来收益和OOS仍未接纳。本报告没有新收益或概率结论。'])
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--profile',type=Path,default=PROFILE);p.add_argument('--source-manifest',type=Path,default=MANIFEST);p.add_argument('--raw-root',type=Path,default=RAW)
    p.add_argument('--dates',nargs='+');p.add_argument('--symbols',nargs='+',default=['688122.SH','688137.SH','688655.SH'])
    p.add_argument('--band-edges-cny',type=int,nargs='+',default=list(EDGES))
    args=p.parse_args(argv);edges=tuple(args.band_edges_cny);validate_edges(edges)
    spec=PostcloseSpec(symbols=tuple(args.symbols))
    if args.output.exists() or args.output.resolve().is_relative_to(args.raw_root.resolve()): raise ValueError('output must be new and outside raw cache')
    profile,manifest,calendar=load_binding(args.profile,args.source_manifest)
    if not set(spec.symbols).issubset(profile['symbols']): raise ValueError('symbols outside source profile')
    if args.output.resolve().is_relative_to(Path(profile['documents_root']).resolve()): raise ValueError('output must be outside documentation')
    metas={m['member']:m for m in manifest['members']}
    for member in metas:
        parts=PurePosixPath(member).parts
        if len(parts)!=3 or parts[1] not in profile['symbols'] or parts[2] not in ('行情.csv','逐笔成交.csv','逐笔委托.csv'):
            raise ValueError('malformed bound catalog')
    if len(metas)!=len(manifest['members']): raise ValueError('duplicate source member')
    dates=sorted({PurePosixPath(m).parts[0] for m in metas})
    if args.dates:
        if args.dates!=sorted(set(args.dates)) or not set(args.dates).issubset(dates): raise ValueError('dates must be sorted unique and catalogued')
        dates=args.dates
    if not dates or not set(dates).issubset(calendar) or len(dates)>150: raise ValueError('dates exceed calendar/budget')
    if dates[0]<profile['source_scope']['start'] or dates[-1]>=profile['source_scope']['end_exclusive']: raise ValueError('outside source profile scope')
    wanted=[f'{d}/{s}/{k}' for d in dates for s in spec.symbols for k in ('行情.csv','逐笔成交.csv')]
    planned=sum(metas[m]['bytes'] for m in wanted if m in metas)
    if planned>1024**3: raise ValueError('1GiB selected-read budget exceeded')
    args.output.mkdir(parents=True)
    run={'schema':'local_source_reference_ladder_activity@3','generated_at':datetime.now(timezone.utc).isoformat(),'dates':dates,'symbols':list(spec.symbols),'band_lower_bounds_cny':edges,'intervals':'lower inclusive; upper exclusive; final unbounded; unknown reference separate','source_profile_sha256':digest(args.profile),'source_manifest_sha256':digest(args.source_manifest),'selected_data_sha256':manifest['selected_data_sha256'],'planned_raw_bytes':planned,'spec_sha256':digest(SPEC),'code_sha256':{n:digest(ROOT/'experiments'/n) for n in ('run_l2_postclose_ladder_v3.py','run_l2_postclose_fund_flow_v2.py','l2_postclose_source_v2.py','l2_postclose_core_v1.py')},'aggression_kind':'source_BS_rule_checked_clock_subset_proxy_not_exchange_reconstruction','formal_provider_admitted':False,'original_order_identity_proven':False,'prospective_eligible':False,'price_capability_enabled':False}
    dump(args.output/'run_spec.json',run)
    all_cells=[];all_diag=[];markets=[];observations=[];verified=[];errors=[]
    for day in dates:
        for symbol in spec.symbols:
            frames={}
            for kind in ('行情.csv','逐笔成交.csv'):
                member=f'{day}/{symbol}/{kind}'
                try:
                    if member not in metas: raise ValueError('missing catalogued source')
                    frame,detail=_read_file(args.raw_root,member,metas[member],kind,day,symbol)
                    frames[kind]=frame;detail['member']=member;verified.append(detail)
                except (OSError,ValueError,KeyError,UnicodeError,csv.Error) as e:
                    errors.append({'day':day,'symbol':symbol,'kind':kind,'error':str(e)[:300]})
            obs,daily,groups,_=evaluate_day(frames,errors,day,symbol,spec,set(profile['definition']['execution_codes']))
            observations.append(obs)
            cells=[];diag=[];market={'day':day,'symbol':symbol}
            try:
                if not obs.get('proxy_reference_coverage_checked',False) or '逐笔成交.csv' not in frames: raise ValueError('source roles or execution input unavailable for bands')
                records=normalized_records(frames['逐笔成交.csv'],day,symbol)
                cells,diag,market=ladder_facts(records,groups,edges)
                cells=qualify(cells,obs,daily)
                # Existing >=500k and >=1m amounts must equal corresponding disjoint sums.
                if 500000 in edges and 1000000 in edges:
                    for old in daily:
                        for side,name in (('B','buy'),('S','sell')):
                            old_amount=old['large_'+name+'_1e4']
                            if not pd.isna(old_amount):
                                result=sum(c['amount_1e4'] for c in cells if c['side']==side and c['band_id']>=0 and c['lower_cny']>=old['threshold_cny'])
                                if result!=int(old_amount): raise ValueError('v2 threshold cash mismatch')
                market['allocation_available']=True
            except (ValueError,KeyError,OverflowError) as e:
                errors.append({'day':day,'symbol':symbol,'kind':'band_allocation','error':str(e)[:300]})
                cells=[{'day':day,'symbol':symbol,'side':s,'band_id':i,'band':band_label(i,edges),'cash_fact_ready':bool(obs['cash_fact_ready']),'side_band_distribution_ready':False,'complete_cell_ready':False,'cash_reason':obs['cash_reason'],**{k:None for k in ('amount_1e4','active_1e4','passive_1e4','unclassified_1e4','observed_amount_1e4')}} for s in ('B','S') for i in (*range(len(edges)),-1)]
                market={'day':day,'symbol':symbol,'allocation_available':False}
            market.update(cash_fact_ready=bool(obs['cash_fact_ready']),cash_reason=obs['cash_reason'])
            all_cells.extend(cells);all_diag.extend(diag);markets.append(market)
            print(json.dumps({'day':day,'symbol':symbol,'cash_ready':bool(obs['cash_fact_ready']),'allocation_available':market['allocation_available']},ensure_ascii=False),flush=True)
    tables={'bands.csv':_exact_table(all_cells,('lower_cny','upper_cny','observed_quantity','execution_legs','known_reference_groups',*ROLE_COUNTS)),'bands_wide.csv':_exact_table(wide_rows(all_cells),()),'activity_diagnostics.csv':_exact_table(all_diag,('quantity','records')),'market_activity.csv':_exact_table(markets,('observed_quantity','execution_records')),'day_observations.csv':_exact_table(observations,('observed_quantity','source_last_quote_price_raw','source_cumulative_quantity','source_cumulative_count','quantity_gap','record_count_gap'))}
    for name,frame in tables.items(): frame.to_csv(args.output/name,index=False)
    summary={'schema':'descriptive_ladder_activity_only@3','stock_days':len(markets),'cash_ready_days':sum(m['cash_fact_ready'] for m in markets),'allocated_days':sum(bool(m['allocation_available']) for m in markets),'complete_band_cells':sum(c['complete_cell_ready'] for c in all_cells),'band_rows':len(all_cells),'wide_rows':len(wide_rows(all_cells)),'source_errors':len(errors),'verified_files':len(verified),'verified_bytes':sum(x['bytes'] for x in verified),'formal_provider_admitted':False,'price_capability_enabled':False,'prospective_eligible':False}
    dump(args.output/'source_verification.json',{'verified_files':verified,'errors':errors,'expected_files':len(wanted)})
    dump(args.output/'summary.json',summary)
    write_report(args.output,all_cells,markets,edges)
    print(json.dumps(summary,ensure_ascii=False))
    return 2 if errors else 0


if __name__=='__main__': raise SystemExit(main())
