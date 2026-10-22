"""Same-share source-bound reference-group PROXY research, not account flow.

Evidence and per-day checks enable descriptions, never true-order identity,
provider admission, cross-action prices or forward predictions. No network or
execution of supplied scripts; old code/results remain unchanged.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from dataclasses import asdict
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from pathlib import Path,PurePosixPath

import numpy as np
import pandas as pd

from experiments.l2_postclose_core_v1 import PostcloseSpec,rolling_profiles,future_labels,MAX_INT
from experiments.l2_postclose_inference_v1 import infer_primary
from experiments.l2_postclose_source_v2 import exact_integer,read_bound_csv,reference_group_facts

ROOT=Path(__file__).resolve().parents[1]
PROFILE=ROOT/'research/evidence/l2-postclose-source-v2/source-profile.json'
PROFILE_SHA256='f917ad99412542d813e85a85dc714b4b9abd0e12f3ad8ee016298e485acdb4ca'
MANIFEST=Path('/srv/bcache-8t/ygguo/quant/l2-three-stock-20260901-20261016-v1/full_v2/source_manifest.json')
RAW=Path('/srv/bcache-8t/ygguo/quant/l2-three-stock-20260901-20261016-v1/raw')
KINDS=('行情.csv','逐笔委托.csv','逐笔成交.csv')
MONEY_COLUMNS=('amount_1e4','quantity','large_buy_1e4','large_sell_1e4','close_raw')


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def load_binding(profile_path,source_manifest):
    if digest(profile_path)!=PROFILE_SHA256: raise ValueError('source profile identity changed; needs review, not edited booleans')
    p=json.loads(Path(profile_path).read_text())
    if p.get('schema')!='same_share_sh_reference_group_profile@2': raise ValueError('unsupported source profile')
    base=Path(p['documents_root']).resolve()
    for f in p['documents']:
        relative=PurePosixPath(f['relative_path'])
        target=base.joinpath(*relative.parts)
        if relative.is_absolute() or '..' in relative.parts or target.is_symlink() or not target.resolve().is_relative_to(base):
            raise ValueError('documentation path escapes bound source')
        if not target.is_file() or target.stat().st_size!=f['bytes'] or digest(target)!=f['sha256']:
            raise ValueError('documentation content changed')
    for name,key in (('receipt.json','receipt_sha256'),('inspection-receipt.json','inspection_receipt_sha256')):
        if digest(base/name)!=p[key]: raise ValueError('documentation receipt changed')
    check=json.loads((base/'inspection-receipt.json').read_text())
    if check.get('original_share_identity_checked') is not True or check.get('share_without_query_sha256')!=p['share_without_query_sha256']:
        raise ValueError('same-share binding unavailable')
    if digest(source_manifest)!=p['source_scope']['source_manifest_sha256']:
        raise ValueError('data snapshot not covered by this finite source profile')
    manifest=json.loads(Path(source_manifest).read_text())
    if manifest.get('selected_data_sha256')!=p['source_scope']['selected_data_sha256']:
        raise ValueError('selected data fingerprint differs')
    c=p['calendar'];calendar_path=ROOT/c['path'];excerpt_path=ROOT/c['source_excerpt']
    if digest(calendar_path)!=c['sha256'] or digest(excerpt_path)!=c['source_excerpt_sha256']:
        raise ValueError('calendar evidence changed')
    frame=pd.read_csv(calendar_path,dtype=str,keep_default_na=False)
    if list(frame.columns)!=['cal_date','is_open'] or not frame.is_open.isin(['0','1']).all(): raise ValueError('invalid calendar schema')
    dates=pd.to_datetime(frame.cal_date,format='%Y%m%d',errors='raise')
    if list(dates)!=list(pd.date_range(dates.min(),dates.max())): raise ValueError('calendar is not a full contiguous natural-date schedule')
    return p,manifest,tuple(frame.loc[frame.is_open=='1','cal_date'])


def _code(v): return v.strip(' \t\r\n\x00')


def _reference(v):
    text=v.strip()
    if not re.fullmatch(r'[0-9]+',text): return None
    return text if int(text)>0 else None


def _column(frame,name,minimum=0):
    return pd.Series([exact_integer(v,name,minimum=minimum) for v in frame[name]],index=frame.index,dtype=object)


def _observed_sum(values,name): return exact_integer(sum(int(v) for v in values),name)


def _base_row(day,symbol,threshold,observation):
    return {'day':day,'symbol':symbol,'threshold_cny':threshold,'amount_1e4':observation.get('observed_amount_1e4'),'quantity':observation.get('observed_quantity'),'large_buy_1e4':None,'large_sell_1e4':None,'trade_ok':False,'order_ok':False,'close_raw':observation.get('source_last_quote_price_raw'),'close_ok':False,'price_segment':None,'cash_fact_ready':False,'proxy_ready':False,'cash_reason':observation.get('cash_reason','missing_execution_input'),'proxy_reason':'cash_facts_unavailable','source_close_observed':observation.get('source_last_quote_price_raw') is not None,'original_order_identity_proven':False,'identity_kind':'delivered_reference_group_proxy'}


def evaluate_day(frames,errors,day,symbol,spec,execution_codes,confirmed_collision_keys=frozenset()):
    """Check source-bound facts. Auxiliary order data never filters executions."""
    observation={'day':day,'symbol':symbol,'cash_fact_ready':False,'cash_reason':'missing_trade_or_quote','source_close_observed':False,'phase_split_ready':False,'cross_day_price_ready':False,'prospective_eligible':False,'formal_provider_admitted':False,'original_order_identity_proven':False,'identity_kind':'delivered_reference_group_proxy'}
    diagnostics={'day':day,'symbol':symbol,'auxiliary_order_status':'missing_or_invalid','phase_codes':'','unknown_zero_phase_codes':'','matched_buy_quantity_share':None,'matched_sell_quantity_share':None,'quantity_semantics':'not_used_as_execution_denominator'}
    groups=pd.DataFrame()
    q=frames.get('行情.csv');t=frames.get('逐笔成交.csv');o=frames.get('逐笔委托.csv')
    selected=pd.DataFrame()
    quote_turnover=None
    if q is not None:
        cq=q.loc[q.ms==q.ms.max()].iloc[-1]
        observation['source_last_quote_ms']=int(cq.ms)
        try:
            observation['source_cumulative_quantity']=exact_integer(cq['当日累计成交量'],'当日累计成交量')
            observation['source_cumulative_count']=exact_integer(cq['成交笔数'],'成交笔数')
        except ValueError as e:
            errors.append({'day':day,'symbol':symbol,'kind':'行情.csv','role':'required_for_complete_day','error':str(e)})
            q=None;observation['cash_reason']='quote_cumulative_fields_invalid'
        try:
            observation['source_last_quote_price_raw']=exact_integer(cq['成交价'],'成交价')
            observation['source_close_observed']=True
        except ValueError as e:
            # Last-price observation is not the volume/count reconciliation.
            errors.append({'day':day,'symbol':symbol,'kind':'行情.csv','role':'price_observation_only','error':str(e)})
        try:
            quote_turnover=Decimal(cq['当日成交额'].strip())
            if not quote_turnover.is_finite() or quote_turnover<0: raise InvalidOperation
            observation['source_cumulative_turnover_cny']=str(quote_turnover)
        except (ValueError,InvalidOperation):
            quote_turnover=None
            observation['quote_turnover_diagnostic_status']='unavailable_not_a_cash_gate'
    if t is not None:
        try:
            prices=_column(t,'成交价格');quantities=_column(t,'成交数量')
            codes=t['成交代码'].map(_code)
            positive=(prices>0)&(quantities>0)
            unsupported=~codes.isin(execution_codes)
            malformed=(~positive)&((prices>0)|(quantities>0))
            selected=t.loc[positive].copy()
            selected_prices=prices.loc[positive];selected_quantities=quantities.loc[positive]
            cash=[exact_integer(int(p)*int(v),'record cash') for p,v in zip(selected_prices,selected_quantities)]
            amount=_observed_sum(cash,'observed cash');volume=_observed_sum(selected_quantities,'observed quantity')
            # Normalize numeric values only; original field text remains in t.
            records=pd.DataFrame({'day':day,'symbol':symbol,'record_key':selected['_source_record'].map(lambda n:f'record:{n}'),'price_raw':selected_prices,'quantity':selected_quantities,'buy_ref':selected['叫买序号'].map(_reference),'sell_ref':selected['叫卖序号'].map(_reference)})
            duplicate_count=int(t.loc[positive,[c for c in t if c not in ('ms','_source_record')]].duplicated().sum())
            observation.update(trade_file_records=len(t),selected_execution_records=len(selected),zero_value_records=int((~positive&~malformed).sum()),unsupported_code_records=int(unsupported.sum()),nonzero_malformed_records=int(malformed.sum()),exact_duplicate_execution_candidates=duplicate_count,execution_codes=json.dumps(codes.value_counts().to_dict(),ensure_ascii=False),observed_amount_1e4=amount,observed_quantity=volume,observed_vwap=amount/volume/10000 if volume else None)
            # A zero/zero TRADE-table row has no documented non-execution
            # role in this finite profile. This is not an order-table S/E row.
            complete_roles=not unsupported.any() and bool(positive.all()) and duplicate_count==0
            if q is not None:
                observation['quantity_gap']=int(observation['source_cumulative_quantity'])-volume
                observation['record_count_gap']=int(observation['source_cumulative_count'])-len(selected)
                observation['volume_count_reconciled']=observation['quantity_gap']==0 and observation['record_count_gap']==0
                if quote_turnover is not None:
                    observation['quote_amount_difference_cny']=str(Decimal(amount)/Decimal(10000)-quote_turnover)
            else: observation['volume_count_reconciled']=False
            if not len(selected): observation['cash_reason']='zero_executions_observed_not_a_direction_signal'
            elif not complete_roles: observation['cash_reason']='unsupported_or_ambiguous_execution_records'
            elif q is None: observation['cash_reason']='missing_or_invalid_quote_for_complete_day'
            elif not observation['volume_count_reconciled']: observation['cash_reason']='source_volume_or_count_mismatch'
            else: observation.update(cash_fact_ready=True,cash_reason='source_bound_full_day_checks_passed')
            # Supported observed groups can be retained on an incomplete day,
            # but that day's COMPLETE large-side amounts/labels remain missing.
            grouped=pd.DataFrame()
            if len(records) and complete_roles:
                groups,grouped=reference_group_facts(records,spec,confirmed_collision_keys)
                groups['complete_day_cash_ready']=bool(observation['cash_fact_ready'])
            rows=[]
            for threshold in spec.thresholds_cny:
                row=_base_row(day,symbol,threshold,observation)
                row.update(trade_ok=bool(observation['cash_fact_ready']),cash_fact_ready=bool(observation['cash_fact_ready']))
                side=grouped.loc[grouped.threshold_cny==threshold] if len(grouped) else grouped
                if len(side):
                    values=side.iloc[0]
                    for name in ('known_buy_amount_1e4','known_sell_amount_1e4','missing_buy_records','missing_sell_records','buy_reference_complete','sell_reference_complete','confirmed_collision_count'):
                        row[name]=values[name]
                    ready=bool(values.buy_reference_complete and values.sell_reference_complete and values.confirmed_collision_count==0)
                    row['proxy_reason']='ready_source_reference_proxy' if ready else 'unknown_references_or_confirmed_collision'
                    row.update(order_ok=bool(observation['cash_fact_ready'] and ready),proxy_ready=bool(observation['cash_fact_ready'] and ready))
                    for name in ('large_buy_1e4','large_sell_1e4','large_buy_vwap','large_sell_vwap','structure_imbalance','large_participation'):
                        row[name]=values[name] if observation['cash_fact_ready'] else None
                    if not observation['cash_fact_ready']: row['proxy_reason']=observation['cash_reason']
                rows.append(row)
            observation['proxy_reference_coverage_checked']=bool(len(grouped))
        except (ValueError,KeyError,OverflowError) as e:
            errors.append({'day':day,'symbol':symbol,'kind':'逐笔成交.csv','role':'required','error':str(e)})
            observation.update(cash_fact_ready=False,cash_reason='execution_numeric_or_mapping_invalid')
            rows=[_base_row(day,symbol,T,observation) for T in spec.thresholds_cny]
    else:
        rows=[_base_row(day,symbol,T,observation) for T in spec.thresholds_cny]
        selected=pd.DataFrame()
    if o is not None:
        try:
            types=o['委托类型'].map(_code);sides=o['委托代码'].map(_code)
            px=_column(o,'委托价格');qty=_column(o,'委托数量')
            phase=(types=='S')&(px==0)&(qty==0)
            phase_codes=sorted(set(sides.loc[phase]))
            diagnostics.update(auxiliary_order_status='source_order_diagnostics_only',phase_codes=json.dumps(phase_codes),unknown_zero_phase_codes=json.dumps([v for v in phase_codes if v not in ('I','O','J','C')]))
            adds=o.loc[(types=='A')&sides.isin(['B','S'])].copy()
            adds['_ref']=adds['交易所委托号'].map(_reference);adds['_side']=sides.loc[adds.index]
            diagnostics['duplicate_A_reference_candidates']=int(adds.duplicated(['_side','_ref']).sum())
            if t is not None and len(selected):
                all_qty=_column(selected,'成交数量')
                for side,field,name in (('B','叫买序号','buy'),('S','叫卖序号','sell')):
                    ids=set(adds.loc[adds._side==side,'_ref'].dropna())
                    matched=selected[field].map(_reference).isin(ids)
                    diagnostics[f'matched_{name}_quantity_share']=sum(all_qty.loc[matched])/sum(all_qty) if sum(all_qty) else None
            # A quantity is deliberately NOT used to infer original size,
            # discard executions, or accept full-day reference identities.
        except (ValueError,KeyError) as e:
            diagnostics['auxiliary_order_status']='auxiliary_mapping_invalid'
            diagnostics['error']=str(e)
            errors.append({'day':day,'symbol':symbol,'kind':'逐笔委托.csv','role':'auxiliary_fields','error':str(e)})
    return observation,rows,groups,diagnostics


def dual_axis_profiles(daily,calendar,spec):
    result=rolling_profiles(daily,calendar,spec)
    states=[]
    for r in result.itertuples(index=False):
        if r.structure_status!='ok': state='不可用'
        elif r.imbalance>0 and r.positive_fraction>.5: state='偏买'
        elif r.imbalance<0 and r.negative_fraction>.5: state='偏卖'
        else: state='中性'
        states.append(state)
    result['cash_structure_state']=states
    result['price_confirmation_state']='待核：跨日价格及公司行为'
    result['identity_kind']='delivered_reference_group_proxy'
    result['original_order_identity_proven']=False
    result['legacy_description']=result['description']
    result['description']=[f'编号组结构{state}；价格确认待核' if state!='不可用' else '编号组结构不可用；保留具体缺口' for state in states]
    return result


def _exact_table(rows,names):
    result=pd.DataFrame(rows)
    for name in set(names)|{c for c in result.columns if c.endswith('_1e4')}:
        if name in result:
            result[name]=pd.array([r.get(name) for r in rows],dtype='Int64')
    return result


def _typed_daily(rows):
    result=_exact_table(rows,MONEY_COLUMNS)
    for name in ('trade_ok','order_ok','close_ok','cash_fact_ready','proxy_ready'):
        result[name]=pd.Series([bool(r.get(name,False)) for r in rows],dtype=bool)
    return result


def _read_file(raw_root,member,meta,kind,day,symbol):
    parts=PurePosixPath(member).parts
    if parts!=(day,symbol,kind): raise ValueError('unexpected member path')
    target=raw_root.joinpath(*parts)
    if not target.resolve().is_relative_to(raw_root.resolve()): raise ValueError('source path escapes raw root')
    return read_bound_csv(target,meta,kind,day,symbol)


def render_report(out,observations,daily,profiles,summary):
    primary=summary['primary_threshold_cny']
    lines=['# 成交编号组代理：盘后复盘报告 v2','',f"**样本截止：{summary['last_observed_market_day']}；不是生成当天的实时资金。**",'', '**以下为同分享交付格式下的编号组统计，不是机构账户净流入、持仓留存或上涨预测。**','',f"{summary['cash_fact_ready_days']}／{summary['stock_days']}个股票日通过源内整日检查；{summary['ready_proxy_daily_rows']}行大额结构可描述；{summary['ready_proxy_window_rows']}行多尺度结构可描述。价格确认与真实推断仍未通过。",'', f'## 最新完整日：主阈值{primary/10000:g}万元','', '| 股票 | 日期 | 大额买组成交额（万元） | 大额卖组成交额（万元） | 组差／全日额 | 买组均价 | 卖组均价 | 源末价* |','|---|---|---:|---:|---:|---:|---:|---:|']
    def value(v,digits=2): return '缺失' if pd.isna(v) else f'{float(v):.{digits}f}'
    for symbol in sorted(observations.symbol.unique()):
        ready=daily.loc[(daily.symbol==symbol)&daily.proxy_ready&(daily.threshold_cny==primary)].sort_values('day')
        if ready.empty:
            lines.append(f'| {symbol} | 无完整日 | 缺失 | 缺失 | 缺失 | 缺失 | 缺失 | 缺失 |');continue
        r=ready.iloc[-1]
        lines.append(f"| {symbol} | {r.day} | {value(int(r.large_buy_1e4)/100000000)} | {value(int(r.large_sell_1e4)/100000000)} | {value(r.structure_imbalance*100)}% | {value(r.large_buy_vwap,4)} | {value(r.large_sell_vwap,4)} | {value(r.close_raw/10000,4)} |")
    lines.extend(['',f'金额是≥{primary/10000:g}万元编号组的累计已成交额，组差不是账户中留下的钱；均价不含费用，也不是仍持有仓位成本。*源末价是同日同源末快照的成交价，未独立核验官方收盘，仅供同源观察，不授予跨日价格确认。辅助阈值按运行规格单列CSV，不与主阈值相加。','', '## 最新观察日的多尺度结构','', '| 股票 | W | 组差占比 | 正差日比例 | 资金轴（编号组代理） | 价格轴 |','|---|---:|---:|---:|---|---|'])
    for symbol in sorted(observations.symbol.unique()):
        last=observations.loc[observations.symbol==symbol].day.max()
        for r in profiles.loc[(profiles.symbol==symbol)&(profiles.day==last)&(profiles.threshold_cny==primary)].sort_values('lookback').itertuples(index=False):
            lines.append(f"| {symbol} | {r.lookback} | {value(r.imbalance*100)}% | {value(r.positive_fraction*100)}% | {r.cash_structure_state} | 待核 |")
    lines.extend(['','偏买／偏卖仅表示这个交付数据中大额买卖编号组的金额差和日际持续性，不能解释为同一资金连续持仓，也不构成买卖建议。价格轴未知不让已合格资金轴消失，但不会被当成价格未确认或未来不涨。','', '## 异常与剩余限制',''])
    bad=observations.loc[~observations.cash_fact_ready]
    for r in bad.itertuples(index=False):
        lines.append(f'- {r.day} {r.symbol}：{r.cash_reason}；完整大额方向及包含该日的窗口不生成，已观察量价留在诊断。')
    lines.extend(['- A事件匹配覆盖只作辅助诊断；无A的成交没有删除。未知零价S/E状态不参与现金，不关闭另一张完整成交表。','- 当前无通道唯一性证明；所有编号组仍为proxy，不升级为完整原始订单或账户。金额门槛不识别机构，机构也可拆成多个小号。','- 源内量／笔数相符是必要检查，不证明源端绝无共同遗漏或已经官方认证。','- 未获得足够独立价格与公司行为可比段；P及未来标签不生成，不用平滑价格猜测没有除权。','- 全部28日早已观察，source-bound描述不是OOS。前瞻队列、正式平台来源接纳和真实上涨验证均未完成。','', '## 复核材料','', '`source_profile_binding.json`、`source_verification.json`、`day_observations.csv`、`order_diagnostics.csv`、`daily_proxy.csv`、`daily_inputs.csv`、`profiles.csv`、`labels.csv`、`matrix.csv`、`groups/`、`run_spec.json`。'])
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile',type=Path,default=PROFILE)
    p.add_argument('--source-manifest',type=Path,default=MANIFEST)
    p.add_argument('--raw-root',type=Path,default=RAW)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--symbols',nargs='+',default=['688122.SH','688137.SH','688655.SH'])
    p.add_argument('--lookbacks',nargs='+',type=int,default=[3,5,10,20])
    p.add_argument('--horizons',nargs='+',type=int,default=[1,3,5,10,20])
    p.add_argument('--thresholds-cny',nargs='+',type=int,default=[500000,1000000])
    p.add_argument('--primary-threshold-cny',type=int,default=1000000)
    p.add_argument('--dates',nargs='+')
    args=p.parse_args(argv)
    spec=PostcloseSpec(tuple(args.symbols),tuple(args.lookbacks),tuple(args.horizons),tuple(args.thresholds_cny),args.primary_threshold_cny)
    if args.output.exists() or args.output.resolve().is_relative_to(args.raw_root.resolve()): raise ValueError('output must be new and outside raw cache')
    profile,manifest,calendar=load_binding(args.profile,args.source_manifest)
    if args.output.resolve().is_relative_to(Path(profile['documents_root']).resolve()): raise ValueError('output must be outside original documentation')
    metas={}
    for m in manifest['members']:
        parts=PurePosixPath(m['member']).parts
        if len(parts)!=3 or not re.fullmatch(r'\d{8}',parts[0]) or parts[1] not in profile['symbols'] or parts[2] not in KINDS or m['member'] in metas: raise ValueError('invalid source catalog member')
        if type(m['bytes']) is not int or m['bytes']<=0: raise ValueError('invalid catalog size')
        metas[m['member']]=m
    dates=sorted({m.split('/')[0] for m in metas})
    if args.dates:
        if args.dates!=sorted(set(args.dates)) or not set(args.dates).issubset(dates): raise ValueError('dates must be sorted unique and catalogued')
        dates=args.dates
    if not dates or len(dates)>150 or not set(dates).issubset(calendar): raise ValueError('source dates outside evidenced calendar/budget')
    if dates[0]<profile['source_scope']['start'] or dates[-1]>=profile['source_scope']['end_exclusive']: raise ValueError('source outside finite profile')
    cal=tuple(d for d in calendar if dates[0]<=d<=dates[-1])
    wanted=[f'{d}/{s}/{k}' for d in dates for s in spec.symbols for k in KINDS]
    if sum(metas[m]['bytes'] for m in wanted if m in metas)>5*1024**3: raise ValueError('raw byte budget exceeded')
    args.output.mkdir(parents=True)
    run={'schema':'source_bound_reference_proxy_run@2','profile_id':profile['profile_id'],'profile_sha256':digest(args.profile),'source_manifest_sha256':digest(args.source_manifest),'selected_data_sha256':manifest['selected_data_sha256'],'configuration':asdict(spec),'source_dates':dates,'calendar_dates':cal,'generated_at':datetime.now(timezone.utc).isoformat(),'last_observed_market_day':max(dates),'prospective_eligible':False,'formal_provider_admitted':False,'original_order_identity_proven':False,'legacy_order_ok_role':'proxy aggregation readiness only, not true original-order identity','environment':{'python':sys.version.split()[0],'numpy':np.__version__,'pandas':pd.__version__},'code_sha256':{name:digest(Path(__file__).with_name(name)) for name in ('l2_postclose_core_v1.py','l2_postclose_inference_v1.py','l2_postclose_source_v2.py','run_l2_postclose_fund_flow_v2.py')},'design_sha256':digest(ROOT/'research/l2-postclose-fund-flow-design-v2.md'),'execution_spec_sha256':digest(ROOT/'research/l2-postclose-execution-spec-v2.md')}
    dump(args.output/'run_spec.json',run)
    dump(args.output/'source_profile_binding.json',{'profile':profile,'documents_and_receipts_verified':True,'data_snapshot_bound':True,'provider_authenticated':False,'original_order_identity_proven':False,'scope_role':'source_bound_reference_proxy_only'})
    observations=[];daily_rows=[];diagnostics=[];verified=[];errors=[];group_files=[]
    for day in dates:
        for symbol in spec.symbols:
            frames={}
            for kind in KINDS:
                member=f'{day}/{symbol}/{kind}'
                try:
                    if member not in metas: raise ValueError('missing catalogued source')
                    frame,detail=_read_file(args.raw_root,member,metas[member],kind,day,symbol)
                    frames[kind]=frame;detail.update(member=member,kind=kind)
                    verified.append(detail)
                except (OSError,ValueError,KeyError,UnicodeError,csv.Error) as e:
                    errors.append({'day':day,'symbol':symbol,'kind':kind,'role':'auxiliary' if kind=='逐笔委托.csv' else 'required_for_complete_day','error':str(e)[:300]})
            try:
                observation,rows,groups,diag=evaluate_day(frames,errors,day,symbol,spec,set(profile['definition']['execution_codes']))
            except (ValueError,KeyError,OverflowError) as e:
                errors.append({'day':day,'symbol':symbol,'kind':'day_evaluation','role':'required_for_complete_day','error':str(e)[:300]})
                observation={'day':day,'symbol':symbol,'cash_fact_ready':False,'cash_reason':'source_mapping_failed'}
                rows=[_base_row(day,symbol,T,observation) for T in spec.thresholds_cny];groups=pd.DataFrame();diag={'day':day,'symbol':symbol,'auxiliary_order_status':'not_evaluated'}
            observations.append(observation);daily_rows.extend(rows);diagnostics.append(diag)
            if not groups.empty:
                path=args.output/'groups'/day/f'{symbol}.csv.gz';path.parent.mkdir(parents=True,exist_ok=True);groups.to_csv(path,index=False,compression={'method':'gzip','mtime':0})
                group_files.append({'relative_path':str(path.relative_to(args.output)),'groups':len(groups),'sha256':digest(path),'identity_kind':'delivered_reference_group_proxy'})
            print(json.dumps({'day':day,'symbol':symbol,'cash_fact_ready':bool(observation['cash_fact_ready']),'proxy_ready_rows':sum(bool(r['proxy_ready']) for r in rows),'cash_reason':observation['cash_reason']},ensure_ascii=False),flush=True)
    observed=_exact_table(observations,('observed_quantity','source_last_quote_price_raw','source_cumulative_quantity','source_cumulative_count','source_last_quote_ms','trade_file_records','selected_execution_records','zero_value_records','unsupported_code_records','nonzero_malformed_records','exact_duplicate_execution_candidates','quantity_gap','record_count_gap'));daily=_typed_daily(daily_rows)
    profiles=dual_axis_profiles(daily,cal,spec)
    prices=daily[['day','symbol','close_raw','close_ok','price_segment']].drop_duplicates(['day','symbol'])
    labels=future_labels(prices,cal,spec,max(dates))
    matrix=infer_primary(profiles,labels,cal,spec,prospective_eligible=False)
    for name,frame in (('day_observations.csv',observed),('order_diagnostics.csv',pd.DataFrame(diagnostics)),('daily_proxy.csv',daily),('daily_inputs.csv',daily),('profiles.csv',profiles),('labels.csv',labels),('matrix.csv',matrix)):
        frame.to_csv(args.output/name,index=False)
    summary={'engineering_status':'completed_source_bound_proxy_research' if not errors else 'completed_with_explicit_source_errors','research_status':'descriptive_reference_proxy_only','stock_days':len(observed),'primary_threshold_cny':spec.primary_threshold_cny,'last_observed_market_day':max(dates),'cash_fact_ready_days':int(observed.cash_fact_ready.sum()),'ready_proxy_daily_rows':int(daily.proxy_ready.sum()),'ready_proxy_window_rows':int(profiles.structure_status.eq('ok').sum()),'price_confirmation_rows':int(profiles.P.notna().sum()),'inference_cells_computed':int(matrix.inference_status.eq('computed_exploratory_only').sum()),'comparison_cells':len(matrix),'source_errors':len(errors),'reference_group_files':len(group_files),'original_order_identity_proven':False,'formal_provider_admitted':False,'new_prospective_dates':0}
    dump(args.output/'source_verification.json',{'verified_files':verified,'source_errors':errors,'expected_files':len(wanted),'verified_files_count':len(verified),'observed_reference_group_files':group_files})
    dump(args.output/'capabilities.json',summary)
    render_report(args.output,observed,daily,profiles,summary)
    print(json.dumps(summary,ensure_ascii=False),flush=True)
    return 2 if errors else 0


if __name__=='__main__':
    raise SystemExit(main())
