"""Same-five-day positive-count sensitivity, not account inflows or validation.

Only day-count eligibility changes. Exact active/cap ranking stays fixed, and
all selections are frozen before any newly needed local price payload reads.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

from experiments import l2_ranking_compare_v12 as base
from experiments.l2_cash_risk_wait_v10 import read_small
from experiments.l2_window_horizon_v13 import evaluate_probe, summarize

HOME=Path('/srv/bcache-8t/ygguo/quant/l2-positive-days-v14')
PAIRS=((3,3),(4,3),(5,3),(3,4),(3,5),(5,5))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_spec(path):
    s=base.load(path)
    if (s['asof']!='20260911' or s['cash_lookback']!=5 or s['top_n']!=20
            or s['horizons']!=[3,5,10,20]
            or tuple((v['group_min'],v['active_min']) for v in s['variants'])!=PAIRS
            or len({v['id'] for v in s['variants']})!=6):
        raise ValueError('unapproved finite day-count axes')
    for p,pin in s['dependent_code_sha256'].items():
        if sha(p)!=pin:
            raise ValueError('pinned dependency changed')
    for path_key,pin_key in [('base_spec_path','base_spec_sha256'),('old_price_receipt_path','old_price_receipt_sha256'),('source_feature_path','source_feature_sha256')]:
        if sha(s[path_key])!=s[pin_key]:
            raise ValueError('source input changed')
    return s


def select_counts(features,spec,base_spec):
    pool=[r for r in features if r['common_eligible'] and r['source_class']=='A']
    selected,counts=[],[]
    for v in spec['variants']:
        eligible=[r for r in pool if r['group_positive_days']>=v['group_min'] and r['active_positive_days']>=v['active_min']]
        chosen=sorted(eligible,key=lambda r:base.arm_key(r,'cash_active_cap',base_spec))[:20]
        counts.append({'panel':'whole_asof_pool','arm':v['id'],'group_min':v['group_min'],'active_min':v['active_min'],
                       'common_A_pool':len(pool),'eligible_n':len(eligible),'planned_n':20,
                       'selected_n':len(chosen),'underfilled':len(chosen)<20})
        for rank,r in enumerate(chosen,1):
            selected.append({'panel':'whole_asof_pool','arm':v['id'],'selection_rank':rank,
                             'group_min':v['group_min'],'active_min':v['active_min'],**base.exported(r)})
    return selected,counts


def freeze(cash_dir,output,spec_path,smoke=False):
    s=load_spec(spec_path);original=base.read_spec(s['base_spec_path'])
    features,provenance=base.build_features(cash_dir,original)
    if smoke:
        pool=sorted((r for r in features if r['common_eligible'] and r['source_class']=='A'),
                    key=lambda r:hashlib.sha256(('0:'+r['symbol']).encode()).hexdigest())[:8]
        features=pool
    selected,counts=select_counts(features,s,original)
    out=base.new_output(output,[cash_dir,original['price_source_dir'],*original.get('price_allowed_resolved_roots',[])])
    out.mkdir(parents=True)
    base.write_csv(out/'selections.csv',selected)
    base.write_csv(out/'counts.csv',counts)
    manifest={'role':'frozen_positive_day_count_selections_before_outcome_reads',
              'mode':'smoke' if smoke else 'full','asof':s['asof'],'spec_sha256':sha(spec_path),'code_sha256':sha(__file__),
              'selections_sha256':sha(out/'selections.csv'),'counts_sha256':sha(out/'counts.csv'),
              'selected_rows':len(selected),'unique_symbols':len({r['symbol'] for r in selected}),
              'formal_provider_or_forecast':False,**provenance}
    base.dump(out/'selection_manifest.json',manifest)
    return manifest


def retained_prices(symbols,receipt):
    bars,files,total={},{},0
    for meta in receipt['files']:
        symbol=meta['symbol']
        if symbol not in symbols:
            continue
        bars[symbol]={};files[symbol]={**meta,'reused_v12_snapshot_or_missing_record':True}
        if 'snapshot_path' not in meta:
            continue
        raw=read_small(Path(meta['snapshot_path']),meta['sha256'],512*1024);total+=len(raw)
        allowed=set(meta['usable_scoped_dates'])
        for row in csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))):
            day=row['date'].replace('-','')
            if day in allowed:
                bars[symbol][day]={k:row[k] for k in ('open','high','low','close')}
    return bars,files,total


def observe(selection_dir,output,spec_path):
    s=load_spec(spec_path);original=base.read_spec(s['base_spec_path']);selection_dir=Path(selection_dir)
    manifest=base.load(selection_dir/'selection_manifest.json')
    if (manifest['spec_sha256']!=sha(spec_path) or manifest['code_sha256']!=sha(__file__)
            or manifest['selections_sha256']!=sha(selection_dir/'selections.csv')
            or manifest['counts_sha256']!=sha(selection_dir/'counts.csv')):
        raise ValueError('frozen selections changed before prices')
    selected=base.table(selection_dir/'selections.csv');counts=base.table(selection_dir/'counts.csv')
    symbols={r['symbol'] for r in selected}
    if len(selected)!=manifest['selected_rows'] or len(symbols)!=manifest['unique_symbols'] or len(symbols)>120:
        raise ValueError('selection coverage/price symbol bound')
    out=base.new_output(output,[selection_dir,original['price_source_dir'],*original.get('price_allowed_resolved_roots',[])])
    out.mkdir(parents=True)
    base.dump(out/'selection_read_receipt.json',{'manifest_sha256':sha(selection_dir/'selection_manifest.json'),'spec_sha256':sha(spec_path),'code_sha256':sha(__file__)})
    bars,files,reused=retained_prices(symbols,base.load(s['old_price_receipt_path']))
    new=symbols-set(bars)
    fresh={'bytes':0,'files':[]}
    if new:
        folder=out/'fresh_prices';folder.mkdir()
        price_scope={**original,**{k:s[k] for k in ('price_file_max_bytes','price_total_max_bytes','price_max_symbols')}}
        extra,fresh=base.snapshot_prices(new,folder,price_scope)
        bars.update(extra);files.update({r['symbol']:{**r,'reused_v12_snapshot_or_missing_record':False} for r in fresh['files']})
    if reused+fresh['bytes']>s['price_total_max_bytes'] or set(bars)!=symbols:
        raise ValueError('combined price coverage/byte bound')
    price_receipt={'role':'old_frozen_prices_plus_new_selected_local_snapshots_not_price_qualification',
                   'reused_bytes':reused,'new_local_price_bytes':fresh['bytes'],'symbols':len(symbols),
                   'files':[files[symbol] for symbol in sorted(symbols)],'new_L2_payload_read':False}
    base.dump(out/'price_snapshot_receipt.json',price_receipt)
    paths=[{**r,**evaluate_probe(original['calendar'],bars[r['symbol']],s['asof'],h)} for r in selected for h in s['horizons']]
    summaries=summarize(paths,counts,s['horizons'])
    base.write_csv(out/'raw_paths.csv',paths);base.write_csv(out/'comparison_summary.csv',summaries)
    result={'role':'adaptive_same_period_positive_day_count_raw_comparison_not_validation','asof':s['asof'],
            'mode':manifest['mode'],'lookback':5,'variants':6,'horizons':s['horizons'],
            'selected_rows':len(selected),'unique_symbols':len(symbols),'raw_paths':len(paths),
            'complete_paths':sum(r['path_complete'] for r in paths),'summary_rows':len(summaries),
            'reused_price_bytes':reused,'new_local_price_bytes':fresh['bytes'],'new_price_symbols':len(new),
            'new_L2_payload_read':False,'long_window_budget_expanded':False,
            'unseen_OOS_or_economic_returns_or_strategy_effectiveness_validated':False,
            'spec_sha256':sha(spec_path),'code_sha256':sha(__file__),
            'selection_manifest_sha256':sha(selection_dir/'selection_manifest.json'),
            'outputs':{p.name:sha(p) for p in (out/'raw_paths.csv',out/'comparison_summary.csv')}}
    base.dump(out/'summary.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=('select','observe'))
    p.add_argument('--spec',default=str(HOME/'positive_days_spec.json'));p.add_argument('--input',required=True);p.add_argument('--output',required=True);p.add_argument('--smoke',action='store_true')
    a=p.parse_args();print(json.dumps(freeze(a.input,a.output,a.spec,a.smoke) if a.phase=='select' else observe(a.input,a.output,a.spec),ensure_ascii=False))
