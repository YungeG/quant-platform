"""Frozen bounded cash-plus-flat-price descriptive comparison (no simulator)."""
import argparse
import csv
import hashlib
import json
from fractions import Fraction
from pathlib import Path

from experiments import l2_expanded_compare_v15 as base
from experiments import l2_ranking_compare_v12 as helpers
from experiments.l2_window_horizon_v13 import evaluate_probe, summarize

SPEC_DEFAULT = Path('/srv/bcache-8t/ygguo/quant/l2-cash-flat-v16/cash_flat_spec.json')
GATE_KEYS = {'role', 'execution_spec_sha256', 'program_sha256', 'smoke_receipt_path', 'smoke_receipt_sha256'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_spec(path):
    raw = json.loads(Path(path).read_text())
    if sha(path) != '00264eaa2290247ed827a3310eb88f2caed4fc6d4d207091239ab48e49046bd5':
        raise ValueError('cash-flat specification pin changed')
    if raw['cutoffs'] != ['20260907','20260908','20260909','20260910','20260911','20260914'] or raw['lookback'] != 5 or raw['future_horizons'] != [3,5]:
        raise ValueError('unapproved axes')
    base.load_spec(raw['base_spec_path'])
    for p,pin in raw['source_pins'].items():
        if sha(p) != pin: raise ValueError('pinned source changed')
    for p,pin in raw['formation_input_pins'].items():
        if sha(p) != pin: raise ValueError('pinned formation input changed')
    for p,pin in raw['dependent_code_sha256'].items():
        if sha(p) != pin: raise ValueError('pinned dependency changed')
    for p,pin in raw['prior_price_receipts'].items():
        if sha(p) != pin: raise ValueError('prior price receipt changed')
    return raw


def price_state(symbol, cutoff, basic, calendar):
    dates, c0 = base.window_dates(calendar, cutoff, 5)
    try:
        closes = [helpers.decimal_fraction(basic[d][symbol]['close']) for d in [c0] + dates]
        if any(not x > 0 for x in closes): return {'flat_state':'unknown','_flat':None}
    except (KeyError, ValueError, TypeError):
        return {'flat_state':'unknown','_flat':None}
    r=closes[-1]/closes[0]-1
    ups=sum(b>a for a,b in zip(closes,closes[1:]))
    downs=sum(b<a for a,b in zip(closes,closes[1:]))
    flat=(-Fraction(1,20)<=r<=Fraction(1,20) and max(closes)/min(closes)<=Fraction(11,10) and ups>=1 and downs>=1)
    return {'flat_state':'flat' if flat else 'not_flat','_flat':flat,
            'flat_return_pct':helpers.number_text(r,100),'flat_max_min_close_ratio':helpers.number_text(max(closes)/min(closes)),
            'flat_strict_up_days':ups,'flat_strict_down_days':downs,'flat_close_dates':';'.join([c0]+dates)}


def build_features(cfg, mode):
    s=load_spec(cfg)
    # v15 is the audited source of cash features. Restrict to its standalone W5 panel;
    # no W10 intersection or alternate cash evaluator is introduced.
    bs=base.load_spec(s['base_spec_path'])
    bs['slices']=[x for x in bs['slices'] if x['id'] in {f'standalone5_{d}' for d in s['cutoffs']}]
    features, availability, provenance=base.build_features(s['cash_dir'], bs)
    cutoff_ids={f'standalone5_{d}' for d in s['cutoffs']}
    features=[r for r in features if r['slice'] in cutoff_ids]
    basic={}
    for p,pin in s['formation_input_pins'].items():
        if Path(p).name.startswith('daily_basic_'):
            from experiments.l2_cash_risk_wait_v10 import read_small
            raw=read_small(Path(p),pin,2*1024**2)
            day=Path(p).stem.rsplit('_',1)[1]
            basic[day]={r['ts_code']:r for r in csv.DictReader(raw.decode('utf-8-sig').splitlines())}
    for r in features: r.update(price_state(r['symbol'],r['asof'],basic,s['calendar']))
    if mode=='smoke':
        symbols=sorted({r['symbol'] for r in features},key=lambda symbol:hashlib.sha256((s['smoke_hash_seed']+symbol).encode()).hexdigest())[:s['smoke_symbol_count']]
        features=[r for r in features if r['symbol'] in set(symbols)]
    return features,availability,provenance


def choose(features,cfg):
    selected=[]; counts=[]; matched=[]
    for cutoff in cfg['cutoffs']:
        pool=[r for r in features if r['asof']==cutoff and r.get('common_eligible')]
        cash=[r for r in pool if r['source_class']=='A' and r['group_positive_days']>=3 and r['active_positive_days']>=3]
        eligible={'cash_base':cash,'cash_flat':[r for r in cash if r['_flat'] is True],
                  'flat_not_cash':[r for r in pool if r['_flat'] is True and r['source_class'] in ('B','C')]}
        lists={}
        for arm,rows in eligible.items():
            key=(lambda r:(hashlib.sha256(f"7:{cutoff}:{r['symbol']}".encode()).hexdigest(),r['symbol'])) if arm=='flat_not_cash' else (lambda r:base.rank_key(r,{'id':'g3_a3'}))
            lists[arm]=sorted(rows,key=key)[:20]
        n=min(20,len(lists['cash_flat']),len(lists['flat_not_cash']))
        for arm,rows in lists.items():
            c={'panel':'standalone5_'+cutoff,'arm':arm,'cutoff':cutoff,'lookback':5,'common_pool':len(pool),'eligible_n':len(eligible[arm]),'planned_n':20,'selected_n':len(rows),'underfilled':len(rows)<20}
            counts.append(c)
            matched.append({**c,'comparison_view':'sameN_prefix','planned_n':n,'selected_n':n,'underfilled':False,'primary_selected_n':len(rows),'no_comparable_signal':n==0})
            for i,r in enumerate(rows,1):selected.append({'panel':c['panel'],'arm':arm,'cutoff':cutoff,'selection_rank':i,**helpers.exported(r)})
    return selected,counts,matched


def freeze(spec_path, output, mode='full', full_gate=None):
    s=load_spec(spec_path)
    if mode not in ('smoke','full'): raise ValueError('invalid mode')
    gate_inputs=[]
    if mode=='full':
        if not full_gate: raise ValueError('full mode requires parent gate')
        gate=json.loads(Path(full_gate).read_text())
        if (set(gate)!=GATE_KEYS or gate.get('role')!='parent_smoke_accepted'
                or gate.get('execution_spec_sha256')!=sha(spec_path) or gate.get('program_sha256')!=sha(__file__)):
            raise ValueError('invalid parent gate')
        receipt=Path(gate['smoke_receipt_path'])
        if not receipt.is_absolute() or any(p.is_symlink() for p in (receipt,*receipt.parents)) or not receipt.is_file():
            raise ValueError('absolute regular parent smoke receipt required')
        if sha(receipt)!=gate['smoke_receipt_sha256']: raise ValueError('invalid parent smoke receipt')
        gate_inputs=[full_gate,receipt]
    features,availability,provenance=build_features(spec_path,mode)
    selected,counts,matched=choose(features,s)
    bs=base.load_spec(s['base_spec_path'])
    protected=[s['cash_dir'],spec_path,__file__,base.HOME,*s['formation_input_pins'],*s['source_pins'],*bs['source_price_roots'],*s['prior_price_receipts'],*gate_inputs]
    out=helpers.new_output(output,protected);out.mkdir(parents=True)
    helpers.write_csv(out/'feature_universe.csv',[helpers.exported(r) for r in features]);helpers.write_csv(out/'selections.csv',selected)
    helpers.write_csv(out/'counts.csv',counts);helpers.write_csv(out/'matched_counts.csv',matched)
    outputs={n:sha(out/n) for n in ('feature_universe.csv','selections.csv','counts.csv','matched_counts.csv')}
    manifest={'role':'frozen_local_descriptive_selection','mode':mode,'spec_sha256':sha(spec_path),'code_sha256':sha(__file__),**provenance,
      'selected_rows':len(selected),'outputs':outputs,'matched_counts':matched,'new_trigger_status':'not_assessed','economic_prices_qualified':False}
    helpers.dump(out/'selection_manifest.json',manifest);return manifest


def observe(spec_path, selection_dir, output):
    s=load_spec(spec_path);sel=Path(selection_dir);m=helpers.load(sel/'selection_manifest.json')
    names=('feature_universe.csv','selections.csv','counts.csv','matched_counts.csv')
    if m['spec_sha256']!=sha(spec_path) or m['code_sha256']!=sha(__file__) or any(sha(sel/n)!=m['outputs'][n] for n in names): raise ValueError('frozen selection identity changed')
    selections=helpers.table(sel/'selections.csv')
    if len(selections)!=m['selected_rows']: raise ValueError('frozen selection coverage changed')
    bs=base.load_spec(s['base_spec_path'])
    bs['prior_price_receipts']=s['prior_price_receipts']
    for key in ('price_file_max_bytes','price_total_max_bytes','price_max_symbols'):bs[key]=s[key]
    protected=[sel,spec_path,__file__,base.HOME,*s['formation_input_pins'],*s['source_pins'],*bs['source_price_roots'],*s['prior_price_receipts']]
    out=helpers.new_output(output,protected);out.mkdir(parents=True)
    helpers.dump(out/'selection_read_receipt.json',{'manifest_sha256':sha(sel/'selection_manifest.json'),'code_sha256':sha(__file__),'spec_sha256':sha(spec_path)})
    bars,receipt=base.snapshot_prices({r['symbol'] for r in selections},out,bs)
    helpers.dump(out/'price_snapshot_receipt.json',receipt)
    paths=[{**r,**evaluate_probe(s['calendar'],bars[r['symbol']],r['asof'],h)} for r in selections for h in s['future_horizons']]
    counts=helpers.table(sel/'counts.csv');matched=helpers.table(sel/'matched_counts.csv')
    targets={(c['panel'],c['arm']):int(c['selected_n']) for c in matched}
    matched_paths=[r for r in paths if int(r['selection_rank'])<=targets[(r['panel'],r['arm'])]]
    primary=summarize(paths,counts,s['future_horizons']);sameN=summarize(matched_paths,matched,s['future_horizons'])
    helpers.write_csv(out/'raw_paths.csv',paths);helpers.write_csv(out/'comparison_summary.csv',primary);helpers.write_csv(out/'matched_summary.csv',sameN)
    result={'role':'cash_positive_plus_sideways_price_raw_paths_not_temporal_OOS_or_Validation','mode':m['mode'],
            'selected_rows':len(selections),'unique_symbols':len(bars),'path_rows':len(paths),'summary_rows':len(primary),'matched_summary_rows':len(sameN),
            'complete_paths':sum(r['path_complete'] for r in paths),'price_snapshot_bytes':receipt['bytes'],'new_price_bytes':receipt['new_local_price_bytes'],
            'spec_sha256':sha(spec_path),'code_sha256':sha(__file__),'selection_manifest_sha256':sha(sel/'selection_manifest.json'),
            'economic_prices_qualified':False,'unseen_temporal_OOS':False,'validated_algorithm_winner':False,'new_L2_payload_bytes':0}
    helpers.dump(out/'summary.json',result);return result


def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('select','observe'));p.add_argument('--spec',default=str(SPEC_DEFAULT));p.add_argument('--mode',choices=('smoke','full'),default='full');p.add_argument('--input');p.add_argument('--output',required=True);p.add_argument('--full-gate')
    a=p.parse_args()
    print(json.dumps(freeze(a.spec,a.output,a.mode,a.full_gate) if a.phase=='select' else observe(a.spec,a.input,a.output),ensure_ascii=False))

if __name__=='__main__': main()
