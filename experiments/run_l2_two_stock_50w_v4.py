"""Local SH/SZ two-stock 50w research; no simulation/provider/forecast authority."""
from __future__ import annotations

import argparse,csv,hashlib,io,json,re,subprocess,time,zlib
from collections import Counter
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from pathlib import Path,PurePosixPath

import pandas as pd
from experiments.l2_postclose_source_v2 import exact_integer,_clock,_TRADE_HEADER,_QUOTE_REQUIRED
from experiments.run_l2_postclose_fund_flow_v2 import ROOT,PROFILE,MANIFEST,load_binding,digest,dump,_code,_reference,_column,_exact_table
from experiments.run_l2_postclose_ladder_v3 import ladder_facts,wide_rows,ROLE_COUNTS

SYMBOLS=('300855.SZ','688202.SH')
KINDS=('行情.csv','逐笔成交.csv')
SOURCE=Path('/srv/bcache-8t/ygguo/quant/L2')
HOME=Path('/srv/bcache-8t/ygguo/quant/l2-two-stock-50w-v4')
SPEC=ROOT/'research/l2-two-stock-50w-v4-spec.md'
CALENDAR_EVIDENCE=ROOT/'research/evidence/l2-two-stock-50w-v4/calendar-basis.md'
EDGES=(0,500000)


def inventory(source,dates=None):
    """Header-only inventory; count full involved solid-block bytes, not just selections."""
    archives=sorted(p for month in ('202609','202610') for p in (source/month).glob('*.7z') if re.fullmatch(r'\d{8}(?:\(\d+\))?\.7z',p.name))
    archives=[p for p in archives if '20260901'<=p.name[:8]<'20261020' and (dates is None or p.name[:8] in dates)]
    if not archives or len({p.name[:8] for p in archives})!=len(archives):raise ValueError('empty/ambiguous archive dates')
    if dates is not None and set(dates)!={p.name[:8] for p in archives}:raise ValueError('requested archive missing')
    if sum(p.stat().st_size for p in archives)>180*1024**3:raise ValueError('archive budget exceeded')
    result=[];members=[];missing=[];solid_bytes=0
    for path in archives:
        before=path.stat();r=subprocess.run(['7z','l','-slt',str(path)],input='',capture_output=True,text=True,timeout=45)
        if r.returncode or '----------' not in r.stdout or len(r.stdout)>64*1024**2:raise ValueError('archive listing failed/too large')
        header,body=r.stdout.split('----------',1);files=[]
        for block in body.strip().split('\n\n'):
            f=dict(line.split(' = ',1) for line in block.splitlines() if ' = ' in line)
            if 'Path' in f and not f.get('Attributes','').startswith('D'):files.append(f)
        day=path.name[:8];wanted={f'{day}/{s}/{k}' for s in SYMBOLS for k in KINDS}
        chosen=[f for f in files if f['Path'] in wanted]
        if len({f['Path'] for f in chosen})!=len(chosen):raise ValueError('duplicate member')
        touched={f['Block'] for f in chosen}
        block_bytes=sum(int(f['Size']) for f in files if f.get('Block') in touched)
        solid_bytes+=block_bytes
        for f in chosen:
            if f.get('Encrypted')!='-' or not 0<int(f['Size'])<=256*1024**2 or not re.fullmatch('[0-9A-Fa-f]{8}',f.get('CRC','')):raise ValueError('unsupported/encrypted/oversize member')
            members.append({'archive':str(path),'member':f['Path'],'bytes':int(f['Size']),'crc32':f['CRC'].lower(),'block':f['Block']})
        missing.extend(sorted(wanted-{f['Path'] for f in chosen}))
        after=path.stat()
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('archive changed during listing')
        result.append({'path':str(path),'day':day,'bytes':before.st_size,'mtime_ns':before.st_mtime_ns,'selected_members':len(chosen),'involved_solid_uncompressed_bytes':block_bytes})
    if solid_bytes>4*1024**3 or sum(m['bytes'] for m in members)>1024**3:raise ValueError('selected/solid-block budget exceeded')
    return {'schema':'local_two_stock_intake@4','archives':result,'members':members,'missing_members':missing,'involved_solid_bytes':solid_bytes,'selected_bytes':sum(m['bytes'] for m in members),'source_origin':'local_collection_not_provider_authentication'}


def subset_inventory(plan,dates):
    selected=set(dates)
    archives=[a for a in plan['archives'] if a['day'] in selected]
    members=[m for m in plan['members'] if PurePosixPath(m['member']).parts[0] in selected]
    return {**plan,'archives':archives,'members':members,'missing_members':[m for m in plan['missing_members'] if PurePosixPath(m).parts[0] in selected],'selected_bytes':sum(m['bytes'] for m in members),'involved_solid_bytes':sum(a['involved_solid_uncompressed_bytes'] for a in archives),'all_local_inventory_totals':{'archives':len(plan['archives']),'selected_bytes':plan['selected_bytes'],'involved_solid_bytes':plan['involved_solid_bytes']}}


def extract_selected(plan,cache):
    start=time.monotonic();bound=[]
    def remaining():
        seconds=1800-(time.monotonic()-start)
        if seconds<=0:raise ValueError('extraction elapsed budget exceeded')
        return seconds
    for a in plan['archives']:
        remaining()
        archive=Path(a['path']);stat=archive.stat()
        if (stat.st_size,stat.st_mtime_ns)!=(a['bytes'],a['mtime_ns']):raise ValueError('archive identity changed')
        selected=[m for m in plan['members'] if m['archive']==str(archive)];needed=[]
        for m in selected:
            parts=PurePosixPath(m['member']).parts
            if len(parts)!=3 or parts[0]!=a['day'] or parts[1] not in SYMBOLS or parts[2] not in KINDS:raise ValueError('unsafe selected path')
            target=cache.joinpath(*parts)
            if not target.resolve().is_relative_to(cache.resolve()) or target.is_symlink():raise ValueError('cache escapes/symlink')
            if not target.exists():needed.append(m['member'])
        if needed:
            cache.mkdir(parents=True,exist_ok=True)
            r=subprocess.run(['7z','x','-y','-bd','-bb0',f'-o{cache}',str(archive),*needed],input='',capture_output=True,text=True,timeout=min(90,remaining()))
            if r.returncode:raise ValueError('selected extraction failed: '+r.stderr[:200])
        for m in selected:
            remaining()
            path=cache.joinpath(*PurePosixPath(m['member']).parts)
            if path.is_symlink() or not path.is_file() or path.stat().st_size!=m['bytes']:raise ValueError('selected member missing/size mismatch')
            raw=path.read_bytes();crc=f'{zlib.crc32(raw)&0xffffffff:08x}'
            if crc!=m['crc32']:raise ValueError('selected member CRC mismatch')
            bound.append({**m,'sha256':hashlib.sha256(raw).hexdigest()})
            remaining()
        stat=archive.stat()
        if (stat.st_size,stat.st_mtime_ns)!=(a['bytes'],a['mtime_ns']):raise ValueError('archive changed during extraction')
    elapsed=time.monotonic()-start
    if elapsed>1800:raise ValueError('extraction elapsed budget exceeded')
    return {**plan,'members':bound,'extraction_seconds':round(elapsed,3),'selected_data_sha256':hashlib.sha256(json.dumps(sorted((m['member'],m['sha256']) for m in bound),separators=(',',':')).encode()).hexdigest()}


def read_bound_v4(path,meta,day,symbol,kind):
    """Dedicated two-symbol reader; old whitelist/profile is never patched."""
    if not isinstance(day,str) or not re.fullmatch('[0-9]{8}',day):raise ValueError('malformed source date')
    datetime.strptime(day,'%Y%m%d')
    if symbol not in SYMBOLS or kind not in KINDS:raise ValueError('outside v4 source scope')
    if type(meta.get('bytes')) is not int or not 0<meta['bytes']<=256*1024**2:raise ValueError('source size budget')
    if path.is_symlink() or not path.is_file():raise ValueError('not a regular source file')
    with path.open('rb') as f:raw=f.read(256*1024**2+1)
    crc=f'{zlib.crc32(raw)&0xffffffff:08x}';sha=hashlib.sha256(raw).hexdigest()
    if len(raw)!=meta['bytes'] or crc!=meta['crc32'] or sha!=meta['sha256']:raise ValueError('source content mismatch')
    reader=csv.reader(io.StringIO(raw.decode('gb18030')));header=next(reader,None)
    expected=67 if kind=='行情.csv' else 13
    if header is None or len(header)!=expected or header[-1].strip() or len(set(header[:-1]))!=len(header)-1:raise ValueError('source header shape')
    if kind=='逐笔成交.csv' and tuple(header)!=_TRADE_HEADER:raise ValueError('source trade fields')
    if kind=='行情.csv' and not _QUOTE_REQUIRED.issubset(header):raise ValueError('source quote fields')
    data=[]
    for r in reader:
        if len(r)!=expected or r[-1].strip():raise ValueError('source row width/trailing field')
        data.append(r[:-1])
    if not data:raise ValueError('no source records')
    frame=pd.DataFrame(data,columns=header[:-1])
    for k,v in (('万得代码',symbol),('交易所代码',symbol[:6]),('自然日',day)):
        if not frame[k].eq(v).all():raise ValueError('source date/instrument mismatch')
    frame['_source_record']=range(1,len(frame)+1);frame['ms']=frame['时间'].map(_clock)
    return frame,{'member':meta['member'],'path':str(path),'bytes':len(raw),'sha256':sha,'crc32':crc,'records':len(frame),'nul_bytes':raw.count(b'\0'),'header':header,'row_coordinate':'1-based CSV data-record ordinal, not exchange-unique ID'}


def select_executions(trades,day,symbol):
    px=_column(trades,'成交价格');qty=_column(trades,'成交数量');codes=trades['成交代码'].map(_code)
    execution=codes.isin(('', '0')) if symbol.endswith('.SH') else codes.eq('0')
    cancel=pd.Series(False,index=trades.index) if symbol.endswith('.SH') else codes.eq('C')
    bad=execution&((px<=0)|(qty<=0));unknown=~(execution|cancel)
    valid=execution&~bad;t=trades.loc[valid]
    records=pd.DataFrame({'day':day,'symbol':symbol,'record_key':t['_source_record'].map(lambda n:f'record:{n}'),'price_raw':px.loc[valid],'quantity':qty.loc[valid],'buy_ref':t['叫买序号'],'sell_ref':t['叫卖序号'],'source_bs':t['BS标志'],'ms':t['ms']})
    original=[c for c in trades if c not in ('ms','_source_record')]
    duplicates=int(t.duplicated(original).sum())
    diag={'source_trade_records':len(trades),'selected_executions':len(records),'cancel_records_excluded':int(cancel.sum()),'cancel_quantity_excluded':sum(int(v) for v in qty.loc[cancel]),'unknown_role_records':int(unknown.sum()),'invalid_execution_records':int(bad.sum()),'exact_duplicate_candidates':duplicates,'source_codes':json.dumps(codes.value_counts().to_dict())}
    return records,diag,bool(not unknown.any() and not bad.any() and duplicates==0 and len(records)>0)


def grouped_records(records):
    data=records.copy();data['cash']=pd.Series([exact_integer(int(p)*int(q),'execution cash',minimum=1) for p,q in zip(data.price_raw,data.quantity)],index=data.index,dtype=object)
    groups=[]
    for side,field in (('B','buy_ref'),('S','sell_ref')):
        ref=data[field].map(_reference);known=data.loc[ref.notna(),['quantity','cash']].copy();known['reference']=ref.loc[ref.notna()]
        g=known.groupby('reference',sort=False).agg(amount_1e4=('cash','sum'),quantity=('quantity','sum'),record_count=('cash','size')).reset_index()
        for c in ('amount_1e4','quantity','record_count'):g[c]=pd.array([exact_integer(v,c,minimum=1) for v in g[c]],dtype='Int64')
        g['day']=records.day.iloc[0];g['symbol']=records.symbol.iloc[0];g['side']=side;groups.append(g)
    return pd.concat(groups,ignore_index=True)


def analyze_day(frames,day,symbol):
    obs={'day':day,'symbol':symbol,'cash_fact_ready':False,'cash_reason':'missing_execution_or_quote','original_order_identity_proven':False,'formal_provider_admitted':False}
    records=pd.DataFrame();cells=[];diag=[];market={};t=frames.get('逐笔成交.csv');q=frames.get('行情.csv')
    if t is None:return obs,cells,diag,market
    records,info,roles_ok=select_executions(t,day,symbol);obs.update(info)
    if records.empty:obs['cash_reason']='no_explained_positive_execution';return obs,cells,diag,market
    obs['observed_amount_1e4']=exact_integer(sum(int(p)*int(v) for p,v in zip(records.price_raw,records.quantity)),'day cash',minimum=1)
    obs['observed_quantity']=exact_integer(sum(int(v) for v in records.quantity),'day quantity',minimum=1)
    if not roles_ok:obs['cash_reason']='unexplained_or_duplicate_execution_roles';return obs,cells,diag,market
    if q is not None:
        last=q.loc[q.ms==q.ms.max()].iloc[-1]
        try:
            source_qty=exact_integer(last['当日累计成交量'],'source cumulative qty');source_n=exact_integer(last['成交笔数'],'source cumulative count')
            obs['quantity_gap']=source_qty-obs['observed_quantity'];obs['record_count_gap']=source_n-len(records)
            if obs['quantity_gap']==0 and obs['record_count_gap']==0:obs.update(cash_fact_ready=True,cash_reason='source_volume_count_exact')
            else:obs['cash_reason']='source_volume_or_count_mismatch'
        except ValueError:obs['cash_reason']='invalid_required_quote_cumulative_fields'
        try:obs['source_last_price_raw']=exact_integer(last['成交价'],'source last price')
        except ValueError:obs['source_last_price_observation_status']='unavailable_not_a_cash_gate'
        try:
            quoted=Decimal(last['当日成交额'])
            if quoted.is_finite() and quoted>=0:obs['quote_amount_difference_cny']=str(Decimal(obs['observed_amount_1e4'])/10000-quoted)
        except (ValueError,InvalidOperation):pass
    groups=grouped_records(records);cells,diag,market=ladder_facts(records,groups,EDGES)
    side_ready={side:bool(records[field].map(_reference).notna().all()) for side,field in (('B','buy_ref'),('S','sell_ref'))}
    for c in cells:
        ready=bool(obs['cash_fact_ready'] and (c['band_id']==-1 or side_ready[c['side']]))
        c.update(cash_fact_ready=obs['cash_fact_ready'],side_band_distribution_ready=bool(obs['cash_fact_ready'] and side_ready[c['side']]),complete_cell_ready=ready,cash_reason=obs['cash_reason'])
        for suffix in ('amount_1e4','active_1e4','passive_1e4','unclassified_1e4'):c[suffix]=c['observed_'+suffix] if ready else None
    market.update(cash_fact_ready=obs['cash_fact_ready'],cash_reason=obs['cash_reason'])
    return obs,cells,diag,market


def retrospective_calendar():
    # Finite 2026 schedule: weekends plus captured SH/SZ holiday notices.
    closed={'20260925',*(f'202610{d:02d}' for d in range(1,8))}
    return tuple(d.strftime('%Y%m%d') for d in pd.date_range('2026-09-01','2026-10-19') if d.weekday()<5 and d.strftime('%Y%m%d') not in closed)


def period_windows(wide,observations,calendar):
    lookup={(r['symbol'],r['day']):r for r in wide if r['band_id']==1};obs={(r['symbol'],r['day']):r for r in observations};result=[]
    for symbol in SYMBOLS:
        for i,day in enumerate(calendar):
            for W in (3,5,10,20):
                if i+1<W:
                    result.append({'symbol':symbol,'day':day,'start':calendar[0],'lookback':W,'window_ready':False,'window_reason':'warmup'});continue
                ds=calendar[i+1-W:i+1];parts=[lookup.get((symbol,d)) for d in ds]
                valid=all(obs.get((symbol,d),{}).get('cash_fact_ready',False) for d in ds) and all(p is not None and p['buy_amount_1e4'] is not None and p['sell_amount_1e4'] is not None for p in parts)
                row={'symbol':symbol,'day':day,'start':ds[0],'lookback':W,'window_ready':bool(valid),'window_reason':'ok' if valid else 'missing_or_unqualified_source_day'}
                if valid:
                    gd=[int(p['buy_amount_1e4'])-int(p['sell_amount_1e4']) for p in parts];ad=[int(p['buy_active_1e4'])-int(p['sell_active_1e4']) for p in parts]
                    row.update(group_difference_1e4=sum(gd),active_difference_1e4=sum(ad),passive_difference_1e4=sum(int(p['buy_passive_1e4'])-int(p['sell_passive_1e4']) for p in parts),unclassified_difference_1e4=sum(int(p['buy_unclassified_1e4'])-int(p['sell_unclassified_1e4']) for p in parts),positive_group_days=sum(x>0 for x in gd),positive_active_days=sum(x>0 for x in ad),group_buy_bias=sum(gd)>0 and sum(x>0 for x in gd)>W/2,active_support=sum(ad)>0 and sum(x>0 for x in ad)>W/2)
                result.append(row)
    return result


def empty_cells(day,symbol,reason):
    return [{'day':day,'symbol':symbol,'side':side,'band_id':i,'band':('＜50万元','≥50万元','大小未知')[i if i>=0 else 2],'cash_fact_ready':False,'complete_cell_ready':False,'cash_reason':reason,**{k:None for k in ('amount_1e4','active_1e4','passive_1e4','unclassified_1e4','observed_amount_1e4')}} for side in ('B','S') for i in (0,1,-1)]


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--dates',nargs='+');parser.add_argument('--source',type=Path,default=SOURCE);parser.add_argument('--cache',type=Path,default=HOME/'raw')
    args=parser.parse_args(argv)
    if args.output.exists() or args.output.resolve().is_relative_to(args.cache.resolve()) or args.output.resolve().is_relative_to(args.source.resolve()):raise ValueError('output must be new outside source/cache')
    calendar=retrospective_calendar()
    if args.dates and (args.dates!=sorted(set(args.dates)) or not set(args.dates).issubset(calendar)):raise ValueError('invalid/unsorted dates')
    dates=tuple(args.dates or calendar);load_binding(PROFILE,MANIFEST)
    calendar_sha=digest(CALENDAR_EVIDENCE)
    # These pins attest retained DOCUMENTS, not reuse of the old 3-stock scope.
    plan=subset_inventory(inventory(args.source),dates)
    args.output.mkdir(parents=True);dump(args.output/'planned_intake.json',plan)
    bound=extract_selected(plan,args.cache);dump(args.output/'source_manifest.json',bound);metas={m['member']:m for m in bound['members']}
    run={'schema':'local_sh_sz_cash_structure@4','generated_at':datetime.now(timezone.utc).isoformat(),'symbols':SYMBOLS,'dates':dates,'calendar':calendar,'cutoff_cny':500000,'input_selected_sha256':bound['selected_data_sha256'],'document_base_profile_sha256':digest(PROFILE),'document_base_scope_reused':False,'mapping':{'688202.SH':{'execution':['','0'],'cancel':[]},'300855.SZ':{'execution':['0'],'cancel':['C'],'D':'unknown_unadmitted'}},'spec_sha256':digest(SPEC),'calendar_evidence_sha256':calendar_sha,'calendar_role':'retrospective weekdays minus captured exchange holidays; not stock tradability','code_sha256':{n:digest(ROOT/'experiments'/n) for n in ('run_l2_two_stock_50w_v4.py','run_l2_postclose_ladder_v3.py','run_l2_postclose_fund_flow_v2.py','l2_postclose_source_v2.py')},'formal_provider_admitted':False,'original_order_identity_proven':False,'prospective_eligible':False,'price_comparability_verified':False}
    dump(args.output/'run_spec.json',run)
    observations=[];allcells=[];diagnostics=[];markets=[];verified=[];errors=[]
    for day in dates:
        for symbol in SYMBOLS:
            frames={}
            for kind in KINDS:
                member=f'{day}/{symbol}/{kind}'
                try:
                    meta=metas[member];frame,detail=read_bound_v4(args.cache/member,meta,day,symbol,kind);frames[kind]=frame;verified.append(detail)
                except (OSError,ValueError,KeyError,UnicodeError,csv.Error) as e:errors.append({'day':day,'symbol':symbol,'kind':kind,'error':str(e)[:240]})
            try:obs,cells,diag,market=analyze_day(frames,day,symbol)
            except (ValueError,KeyError,OverflowError) as e:
                errors.append({'day':day,'symbol':symbol,'kind':'analysis','error':str(e)[:240]});obs={'day':day,'symbol':symbol,'cash_fact_ready':False,'cash_reason':'source_numeric_or_allocation_invalid'};cells=[];diag=[];market={}
            if not cells:cells=empty_cells(day,symbol,obs['cash_reason'])
            observations.append(obs);allcells.extend(cells);diagnostics.extend(diag);markets.append(market or {'day':day,'symbol':symbol,'cash_fact_ready':False,'cash_reason':obs['cash_reason']})
            print(json.dumps({'day':day,'symbol':symbol,'cash_ready':obs['cash_fact_ready'],'reason':obs['cash_reason']},ensure_ascii=False),flush=True)
    wide=wide_rows(allcells);windows=period_windows(wide,observations,tuple(d for d in calendar if min(dates)<=d<=max(dates)))
    tables={'bands.csv':_exact_table(allcells,('observed_quantity','execution_legs','known_reference_groups',*ROLE_COUNTS)),'daily_wide.csv':_exact_table(wide,()),'day_observations.csv':_exact_table(observations,('observed_quantity','source_last_price_raw','quantity_gap','record_count_gap','source_trade_records','selected_executions','cancel_records_excluded','cancel_quantity_excluded','unknown_role_records','invalid_execution_records','exact_duplicate_candidates')),'market_activity.csv':_exact_table(markets,('observed_quantity','execution_records')),'activity_diagnostics.csv':_exact_table(diagnostics,('quantity','records')),'windows.csv':_exact_table(windows,('positive_group_days','positive_active_days'))}
    for name,frame in tables.items():frame.to_csv(args.output/name,index=False)
    summary={'role':'local_descriptive_only_not_platform_validation','stock_days':len(observations),'cash_ready_days':sum(o['cash_fact_ready'] for o in observations),'selected_files':len(verified),'selected_bytes':sum(v['bytes'] for v in verified),'cancel_records_excluded':sum(o.get('cancel_records_excluded',0) for o in observations),'complete_windows':sum(w['window_ready'] for w in windows),'source_errors':len(errors),'latest_sample_day':max(dates),'original_order_identity_proven':False,'formal_provider_admitted':False,'price_or_OOS_accepted':False}
    dump(args.output/'summary.json',summary);dump(args.output/'source_verification.json',{'verified_files':verified,'errors':errors,'missing_members':bound['missing_members']})
    print(json.dumps(summary,ensure_ascii=False));return 2 if errors else 0


if __name__=='__main__':raise SystemExit(main())

