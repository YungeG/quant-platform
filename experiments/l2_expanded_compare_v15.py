"""Date-separated local raw comparisons over an audited daily cash cube.

No trade simulator, no time-OOS claim, no source/price qualification upgrade.
"""
import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from fractions import Fraction
from pathlib import Path

from experiments import l2_ranking_compare_v12 as helpers
from experiments.l2_continuous_interval_v6 import interval_profile
from experiments.l2_historical_cap_screen_v11 import classify_profile, integer
from experiments.l2_window_horizon_v13 import evaluate_probe, summarize
from experiments.l2_cash_risk_wait_v10 import exact_price, read_small

HOME=Path('/srv/bcache-8t/ygguo/quant/l2-expanded-study-v15')
METHODS=('g3_a3','g4_a3','g5_a3','g3_a4','g3_a5','g5_a5','price_momentum','ordinary_turnover','hash_control')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_spec(path):
    s=helpers.load(path)
    if ([m['id'] for m in s['methods']]!=list(METHODS) or s['top_n']!=20 or s['future_horizons']!=[3,5]
            or s['calendar']!=sorted(set(s['calendar'])) or s['calendar'][0]!='20260831'
            or s['cutoffs_W5']!=['20260907','20260908','20260909','20260910','20260911','20260914']
            or s['matched_W5_W10_cutoff']!='20260914'
            or s['price_file_max_bytes']>512*1024 or s['price_total_max_bytes']>512*1024**2
            or s['price_max_symbols']>1024):
        raise ValueError('unapproved finite study axes/budget')
    if sha(s['cohorts_path'])!=s['cohorts_sha256']:
        raise ValueError('asof cohort snapshot changed')
    for source,pin in s['dependent_code_sha256'].items():
        if sha(source)!=pin:raise ValueError('pinned analysis dependency changed')
    if sha(HOME/'daily_execution_spec.json')!=s['daily_execution_spec_sha256']:
        raise ValueError('daily execution specification changed')
    for source,pin in s['prior_price_receipts'].items():
        if sha(source)!=pin:raise ValueError('prior price source changed')
    return s


def window_dates(calendar,cutoff,lookback):
    if type(lookback) is not int or lookback not in (5,10):
        raise ValueError('only declared5/10windows supported')
    end=calendar.index(cutoff)
    if end-lookback<0:
        raise ValueError('missing preceding close; never use negative/future index')
    return calendar[end-lookback+1:end+1],calendar[end-lookback]


def window_feature(symbol,name,cutoff,lookback,lookup,basic,spec):
    dates,previous=window_dates(spec['calendar'],cutoff,lookback)
    if any((symbol,d) not in lookup for d in dates):
        raise ValueError('audited daily cube missing requested fact')
    days=[lookup[(symbol,d)] for d in dates]
    p=interval_profile(days,lookback)
    cls=classify_profile(p)
    cap=helpers.decimal_fraction(basic[cutoff][symbol]['total_mv'])
    if not 6000000000<=cap<=100000000000:
        raise ValueError('asof capitalization roster mismatch')
    momentum=turnover=close=None;errors=[]
    try:
        close=helpers.decimal_fraction(basic[cutoff][symbol]['close'])
        if close<=0:close=None
    except (KeyError,ValueError):pass
    try:
        cs=[helpers.decimal_fraction(basic[d][symbol]['close']) for d in [previous]+dates]
        if any(v<=0 for v in cs):raise ValueError('invalid close')
        momentum=cs[-1]/cs[0]-1
    except (KeyError,ValueError):errors.append('missing_or_invalid_past_close')
    try:
        rates=[helpers.decimal_fraction(basic[d][symbol]['turnover_rate']) for d in dates]
        if any(v<0 for v in rates):raise ValueError('invalid ordinary turnover')
        turnover=sum(rates)/lookback
    except (KeyError,ValueError):errors.append('missing_or_invalid_past_ordinary_turnover')
    if cls=='D':errors.append('incomplete_cash_window')
    r={'symbol':symbol,'name':name,'asof':cutoff,'lookback':lookback,'window_start':dates[0],
       'momentum_base_day':previous,'source_class':cls,'own_feature_eligible':not errors,
       'common_eligible':not errors,'exclusion_reason':';'.join(errors),'total_mv_cny':helpers.number_text(cap),
       'group_positive_days':p.get('group_positive_days'),'active_positive_days':p.get('active_positive_days'),
       'group_positive_streak':p.get('group_positive_streak'),'active_positive_streak':p.get('active_positive_streak'),
       'raw_close_at_cutoff':helpers.number_text(close),'raw_momentum_window_pct':helpers.number_text(momentum,100),
       'ordinary_turnover_window_mean_pct':helpers.number_text(turnover),
       '_momentum':momentum,'_turnover':turnover,'_active_cap':None,'_concentration':None}
    for stem in ('group_difference','active_difference','passive_difference','unknown_difference','market_amount'):
        r[stem+'_1e4']=integer(p.get(stem+'_1e4'))
    if cls!='D':
        r['_active_cap']=Fraction(r['active_difference_1e4'],10000)/cap
        r['group_cap_pct']=helpers.number_text(Fraction(r['group_difference_1e4'],10000)/cap,100)
        positive=sorted((d['buy']-d['sell'] for d in days if d['buy']>d['sell']),reverse=True)
        r['_concentration']=Fraction(sum(positive[:2]),sum(positive)) if positive else None
    else:r['group_cap_pct']=None
    r['active_cap_pct']=helpers.number_text(r['_active_cap'],100)
    r['top2_group_positive_share_pct']=helpers.number_text(r['_concentration'],100)
    return r


def build_features(cash_dir,spec):
    cash_dir=Path(cash_dir);run=helpers.load(cash_dir/'run_spec.json');summary=helpers.load(cash_dir/'summary.json');audit=helpers.load(cash_dir/'independent_daily_check.json')
    if (audit['passed'] is not True or audit['summary_sha256']!=sha(cash_dir/'summary.json')
            or summary['expected_facts']!=summary['completed_facts']
            or run['bound_delta_manifest_sha256']!=sha(cash_dir/'bound_delta_manifest.json')
            or run['identity']['program_sha256']!=sha(Path(__file__).with_name('l2_cash_daily_delta_v15.py'))
            or run['identity']['spec_sha256']!=spec['daily_execution_spec_sha256']):
        raise ValueError('daily cube identity/audit mismatch')
    lookup={};hashes=[]
    for symbol in run['effective_scope']['symbols']:
        path=cash_dir/'stock_results'/(symbol+'.json');raw=read_small(path,limit=4*1024**2);x=json.loads(raw);hashes.append((symbol,hashlib.sha256(raw).hexdigest()))
        if x['identity']!=run['identity'] or x['bound_delta_manifest_sha256']!=run['bound_delta_manifest_sha256']:
            raise ValueError('daily checkpoint identity changed')
        for fact in x['days']:
            key=(symbol,fact['day'])
            if key in lookup:raise ValueError('duplicate daily fact')
            lookup[key]=fact['daily']
    digest=hashlib.sha256(json.dumps(hashes,separators=(',',':')).encode()).hexdigest()
    if digest!=audit['checkpoint_set_sha256'] or {d+'/'+s for s,d in lookup}!=set(run['effective_scope']['expected_fact_keys']):
        raise ValueError('daily fact set changed after audit')
    basic={}
    for path,pin in spec['formation_input_pins'].items():
        raw=read_small(Path(path),pin,2*1024**2)
        if Path(path).name.startswith('daily_basic_'):
            day=Path(path).stem.rsplit('_',1)[1];rs=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
            if any(r['trade_date']!=day for r in rs) or len({r['ts_code'] for r in rs})!=len(rs):raise ValueError('basic identity/duplicates')
            basic[day]={r['ts_code']:r for r in rs}
    cohorts=helpers.load(spec['cohorts_path']);cash_symbols=set(run['effective_scope']['symbols']);features=[];availability=[];cache={}
    def get(s,cut,w):
        key=(s,cut,w)
        if key not in cache:cache[key]=window_feature(s,cohorts['names'][s],cut,w,lookup,basic,spec)
        return cache[key]
    for sl in spec['slices']:
        cut,w=sl['cutoff'],sl['lookback'];roster=cohorts['cohorts'][cut]
        if run['identity']['mode']=='smoke':roster=[s for s in roster if s in cash_symbols]
        if not set(roster)<=cash_symbols:raise ValueError('cash cube omits actual asof cohort')
        for s in roster:
            r={**get(s,cut,w),'slice':sl['id'],'pool_kind':sl['pool']}
            if sl['id'].startswith('matched'):
                paired=get(s,cut,10 if w==5 else 5)
                r['common_eligible']=r['own_feature_eligible'] and paired['own_feature_eligible']
                if not paired['own_feature_eligible']:r['exclusion_reason']+=';paired_window_unavailable'
            features.append(r)
        subset=[r for r in features if r['slice']==sl['id']]
        availability.append({'slice':sl['id'],'cutoff':cut,'lookback':w,'asof_roster':len(roster),
                             'own_feature_ready':sum(r['own_feature_eligible'] for r in subset),
                             'common_ready':sum(r['common_eligible'] for r in subset)})
    provenance={'cash_dir':str(cash_dir.resolve()),'cash_mode':run['identity']['mode'],
                'cash_run_spec_sha256':sha(cash_dir/'run_spec.json'),'cash_summary_sha256':sha(cash_dir/'summary.json'),
                'cash_checkpoint_set_sha256':digest}
    return features,availability,provenance


def rank_key(row,method):
    ident=method['id']
    if ident.startswith('g'):
        return (-row['_active_cap'],-row['active_positive_days'],row['_concentration'],row['symbol'])
    if ident=='price_momentum':return (-row['_momentum'],row['symbol'])
    if ident=='ordinary_turnover':return (-row['_turnover'],row['symbol'])
    if ident=='hash_control':return (hashlib.sha256(('7:'+row['asof']+':'+row['symbol']).encode()).hexdigest(),row['symbol'])
    raise ValueError('unknown method')


def choose(features,spec):
    selected,counts=[],[]
    for sl in spec['slices']:
        pool=[r for r in features if r['slice']==sl['id'] and r['common_eligible']]
        for method in spec['methods']:
            eligible=pool
            if method['id'].startswith('g'):
                g,a=method['group_fraction'],method['active_fraction'];w=sl['lookback']
                eligible=[r for r in pool if r['source_class']=='A' and r['group_positive_days']*g[1]>=g[0]*w and r['active_positive_days']*a[1]>=a[0]*w]
            winners=sorted(eligible,key=lambda r:rank_key(r,method))[:20]
            counts.append({'panel':sl['id'],'arm':method['id'],'cutoff':sl['cutoff'],'lookback':sl['lookback'],
                           'common_pool':len(pool),'eligible_n':len(eligible),'planned_n':20,'selected_n':len(winners),
                           'underfilled':len(winners)<20})
            for i,r in enumerate(winners,1):selected.append({'panel':sl['id'],'arm':method['id'],'selection_rank':i,**helpers.exported(r)})
    return selected,counts


def freeze(cash_dir,output,spec_path):
    s=load_spec(spec_path);features,availability,provenance=build_features(cash_dir,s)
    selected,counts=choose(features,s)
    out=helpers.new_output(output,[cash_dir,HOME/'formation_inputs',*s['source_price_roots']]);out.mkdir(parents=True)
    helpers.write_csv(out/'feature_universe.csv',[helpers.exported(r) for r in features]);helpers.write_csv(out/'availability.csv',availability)
    helpers.write_csv(out/'selections.csv',selected);helpers.write_csv(out/'counts.csv',counts)
    date_symbols={cut:{r['symbol'] for r in selected if r['asof']==cut and r['panel'].startswith('standalone')} for cut in s['cutoffs_W5']}
    pairs=[]
    for i,first in enumerate(s['cutoffs_W5']):
        for second in s['cutoffs_W5'][i+1:]:
            a,b=date_symbols[first],date_symbols[second];pairs.append({'first_cutoff':first,'second_cutoff':second,'first_n':len(a),'second_n':len(b),'overlap_n':len(a&b),'union_n':len(a|b)})
    helpers.write_csv(out/'selection_overlap_by_date.csv',pairs)
    manifest={'role':'date_separated_selection_before_outcome_reads_not_governed_Research','spec_sha256':sha(spec_path),
              'code_sha256':sha(__file__),**provenance,'selected_rows':len(selected),'unique_symbols':len({r['symbol'] for r in selected}),
              'underfilled_groups':sum(c['underfilled'] for c in counts),'new_trigger_status':'not_assessed',
              'source_price_roots':s['source_price_roots'],
              'outputs':{n:sha(out/n) for n in ['feature_universe.csv','availability.csv','selections.csv','counts.csv','selection_overlap_by_date.csv']},
              'formal_provider_or_forecast':False}
    helpers.dump(out/'selection_manifest.json',manifest)
    return manifest


def old_price_registry(spec):
    registry={}
    for p,pin in spec['prior_price_receipts'].items():
        if sha(p)!=pin:raise ValueError('prior price receipt changed')
        for meta in helpers.load(p)['files']:
            registry.setdefault(meta['symbol'],meta)
    return registry


def parse_prices(raw,symbol,allowed):
    records,invalid={},[]
    try:
        seen=set()
        for row in csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))):
            if not isinstance(row.get('date'),str):raise ValueError('missing price identity date')
            day=row['date'].replace('-','')
            if day not in allowed:continue
            if day in seen:raise ValueError('duplicate scoped price date')
            seen.add(day)
            if not isinstance(row.get('symbol'),str) or row['symbol'].strip().zfill(6)!=symbol[:6]:raise ValueError('price identity mismatch')
            try:
                p={k:exact_price(row[k]) for k in ('open','high','low','close')}
                if p['low']>min(p['open'],p['close']) or p['high']<max(p['open'],p['close']) or p['low']>p['high']:raise ValueError('invalid OHLC')
            except ValueError:invalid.append(day);continue
            records[day]={k:row[k] for k in p}
    except (UnicodeError,KeyError,csv.Error,ValueError) as exc:return {},invalid,str(exc)
    return records,invalid,None


def snapshot_prices(symbols,out,spec):
    if len(symbols)>spec['price_max_symbols']:raise ValueError('price symbol bound exceeded')
    known=old_price_registry(spec);snap=out/'price_snapshot';snap.mkdir();bars={};metas=[];used=0;newbytes=0
    allowed=set()
    for cut in spec['cutoffs_W5']:
        start=spec['calendar'].index(cut)+1;allowed.update([cut]+spec['calendar'][start:start+max(spec['future_horizons'])])
    roots=[Path(p).resolve() for p in spec['source_price_roots']]
    for symbol in sorted(symbols):
        meta={'symbol':symbol,'economic_prices_qualified':False}
        if symbol in known:
            original=known[symbol];meta['reused_prior_record']=True
            if 'snapshot_path' not in original:
                bars[symbol]={};metas.append({**meta,'error':original.get('error','old_price_missing'),'original_record':original});continue
            path=Path(original['snapshot_path']);raw=read_small(path,original['sha256'],spec['price_file_max_bytes'])
            meta.update(reuse_source_snapshot_path=str(path),reuse_source_sha256=original['sha256'])
        else:
            logical=Path(spec['source_price_roots'][0])/(symbol[:6]+'.csv');meta.update(logical_path=str(logical),reused_prior_record=False)
            if not logical.is_file():bars[symbol]={};metas.append({**meta,'error':'missing_price_file'});continue
            path=logical.resolve(strict=True)
            if path.name!=symbol[:6]+'.csv' or not any(path.is_relative_to(root) for root in roots):bars[symbol]={};metas.append({**meta,'error':'unapproved_price_target'});continue
            before=path.stat();raw=read_small(path,limit=spec['price_file_max_bytes']);after=path.stat()
            if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns) or logical.resolve(strict=True)!=path:raise ValueError('price identity changed while binding')
            newbytes+=len(raw);meta['resolved_path']=str(path)
        used+=len(raw)
        if used>spec['price_total_max_bytes']:raise ValueError('price byte bound exceeded')
        target=snap/(symbol+'.csv');target.write_bytes(raw)
        records,invalid,error=parse_prices(raw,symbol,allowed)
        meta.update(snapshot_path=str(target),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),invalid_bar_dates=invalid,usable_scoped_dates=sorted(records))
        if error:meta['error']=error
        bars[symbol]=records;metas.append(meta)
    return bars,{'role':'frozen_prior_price_bytes_reparsed_plus_new_selected_local_prices','symbols':len(symbols),'bytes':used,
                 'new_local_price_bytes':newbytes,'allowed_price_dates':sorted(allowed),'files':metas,'economic_prices_qualified':False}


def observe(selection_dir,output,spec_path):
    s=load_spec(spec_path);selection_dir=Path(selection_dir);manifest=helpers.load(selection_dir/'selection_manifest.json')
    if manifest['spec_sha256']!=sha(spec_path) or manifest['code_sha256']!=sha(__file__) or any(sha(selection_dir/n)!=pin for n,pin in manifest['outputs'].items()):raise ValueError('frozen selection identity changed')
    selected=helpers.table(selection_dir/'selections.csv');counts=helpers.table(selection_dir/'counts.csv')
    if len(selected)!=manifest['selected_rows']:raise ValueError('selected matrix coverage changed')
    out=helpers.new_output(output,[selection_dir,*s['source_price_roots']]);out.mkdir(parents=True)
    helpers.dump(out/'selection_read_receipt.json',{'manifest_sha256':sha(selection_dir/'selection_manifest.json'),'code_sha256':sha(__file__),'spec_sha256':sha(spec_path)})
    bars,prices=snapshot_prices({r['symbol'] for r in selected},out,s);helpers.dump(out/'price_snapshot_receipt.json',prices)
    paths=[{**r,**evaluate_probe(s['calendar'],bars[r['symbol']],r['asof'],h)} for r in selected for h in s['future_horizons']]
    comparisons=summarize(paths,counts,s['future_horizons'])
    # The shared summarizer belongs to fixed W5; retain actual slice lookback.
    for r in comparisons:r['lookback']=next(c['lookback'] for c in counts if c['panel']==r['panel'] and c['arm']==r['arm'])
    helpers.write_csv(out/'raw_paths.csv',paths);helpers.write_csv(out/'comparison_summary.csv',comparisons)
    date_frequency=Counter(r['symbol'] for r in selected if r['panel'].startswith('standalone'))
    symbol_dates={symbol:{r['asof'] for r in selected if r['symbol']==symbol and r['panel'].startswith('standalone')} for symbol in date_frequency}
    details={'role':'overlap_counts_not_independent_signal_sample_sizes','unique_securities':len({r['symbol'] for r in selected}),
             'selected_rows':len(selected),'cash_state_is_not_first_new_trigger':True,'adjacent_windows_overlap':True,
             'source_and_price_qualification':False,'per_symbol_selected_row_counts_not_unique_events':dict(date_frequency),
             'per_symbol_unique_selected_cutoffs':{k:len(v) for k,v in symbol_dates.items()},
             'unique_symbol_cutoff_pairs_not_independent_events':sum(len(v) for v in symbol_dates.values()),
             'both_all_positive_unique_symbols':len({r['symbol'] for r in selected if r['arm']=='g5_a5'})}
    helpers.dump(out/'per_cutoff_scarcity_and_unique_symbols.json',details)
    result={'role':'expanded_multicutoff_raw_endpoint_comparison_not_time_OOS_or_Validation',
            'cash_mode':manifest['cash_mode'],'cutoffs':s['cutoffs_W5'],'lookbacks':[5,10],'horizons':s['future_horizons'],
            'selected_rows':len(selected),'unique_symbols':prices['symbols'],'path_rows':len(paths),'summary_rows':len(comparisons),
            'complete_paths':sum(p['path_complete'] for p in paths),'price_snapshot_bytes':prices['bytes'],
            'new_price_bytes':prices['new_local_price_bytes'],'validated_algorithm_winner':False,'unseen_temporal_OOS':False,
            'long20day_raw_budget_expanded':False,'formal_provider_or_forecast':False,'code_sha256':sha(__file__),
            'spec_sha256':sha(spec_path),'selection_manifest_sha256':sha(selection_dir/'selection_manifest.json')}
    helpers.dump(out/'summary.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=('select','observe'));p.add_argument('--spec',default=str(HOME/'expanded_study_spec_v3.json'));p.add_argument('--input',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();print(json.dumps(freeze(a.input,a.output,a.spec) if a.phase=='select' else observe(a.input,a.output,a.spec),ensure_ascii=False))
