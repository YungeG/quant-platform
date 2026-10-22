"""Read-only real-source audit and fail-closed postclose report.

This adapter does NOT admit a supplier. Unknown source semantics cannot be
opened by a CLI flag or by editing booleans. Qualified-source arithmetic is
available in the pure core; source admission needs a separately reviewed adapter.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import numpy as np
import pandas as pd

from experiments.l2_postclose_core_v1 import PostcloseSpec, rolling_profiles, future_labels
from experiments.l2_postclose_inference_v1 import infer_primary
from experiments.l2_three_stock_microstructure_v1 import load_member

BASIS=Path('/srv/bcache-8t/ygguo/quant/l2-three-stock-20260901-20261016-v1/full_v2/source_manifest.json')
RAW=Path('/srv/bcache-8t/ygguo/quant/l2-three-stock-20260901-20261016-v1/raw')
NOTES=Path('research/evidence/l2-postclose-qualification-v1/qualification-notes.json')
KINDS=('行情.csv','逐笔委托.csv','逐笔成交.csv')
QUAL_KEYS=('research_provider_qualified','field_dictionary_qualified','order_scope_qualified','trade_codes_qualified','auction_semantics_qualified','close_authority_qualified','corporate_action_segments_qualified','provider_availability_qualified','prospective_sample_qualified')


def write_json(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def integer_column(frame,name):
    strings=frame[name].astype(str)
    if not strings.str.fullmatch(r'\d+').all():
        raise ValueError(f'invalid nonnegative integer field: {name}')
    values=strings.map(int)
    if values.map(lambda x:x>np.iinfo(np.int64).max).any():
        raise ValueError(f'integer overflow: {name}')
    return values.astype('int64')


def read_selected(raw_root,member,meta,day,symbol,kind):
    parts=PurePosixPath(member).parts
    if parts!=(day,symbol,kind) or kind not in KINDS:
        raise ValueError('unexpected selected member path')
    path=raw_root.joinpath(*parts)
    if path.is_symlink() or not path.resolve().is_relative_to(raw_root.resolve()) or not path.is_file():
        raise ValueError('selected source is missing or escapes raw root')
    # Existing reader validates size, CRC, schema and instrument/date identity.
    frame,detail=load_member(path,{'bytes':meta['bytes'],'crc32':meta['crc32']},day,symbol,kind)
    if detail['sha256']!=meta['sha256']:
        raise ValueError('selected source SHA256 mismatch')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=detail['sha256']:
        raise ValueError('selected source changed during verification')
    reader=csv.reader(io.StringIO(raw.decode('gb18030').replace('\x00','')))
    width=len(next(reader));count=0
    for row in reader:
        if len(row)!=width: raise ValueError('CSV row width mismatch')
        count+=1
    if count!=len(frame): raise ValueError('CSV record count mismatch')
    detail['member']=member
    return frame,detail


def reference_audit(orders,trades,day,symbol):
    orders=orders.copy();trades=trades.copy()
    for c in ('委托编号','交易所委托号','委托价格','委托数量','时间'):
        orders[c]=pd.array(integer_column(orders,c),dtype='Int64')
    for c in ('成交价格','成交数量','叫买序号','叫卖序号','成交编号','时间'):
        trades[c]=integer_column(trades,c)
    positive=trades.loc[(trades['成交价格']>0)&(trades['成交数量']>0)]
    adds=orders.loc[orders['委托类型'].eq('A')&orders['委托代码'].isin(['B','S'])]
    out=[]
    for key in ('委托编号','交易所委托号'):
        for side,field in (('B','叫买序号'),('S','叫卖序号')):
            a=adds.loc[(adds['委托代码']==side)&(adds[key]>0)]
            duplicates=int(a[key].duplicated().sum())
            row={'day':day,'symbol':symbol,'candidate_key':key,'side':side,'positive_price_records':len(positive),'duplicate_add_keys':duplicates,'semantics_status':'unqualified_candidate_mapping_only'}
            if duplicates:
                row.update(matched_records=None,matched_quantity_share=None,before_add_records=None,limit_price_violations=None,fill_gt_A_quantity_groups=None)
            else:
                joined=positive.merge(a[[key,'委托价格','委托数量','时间']],how='left',left_on=field,right_on=key,suffixes=('_record','_add'),validate='many_to_one')
                matched=joined[key].notna()
                total=int(positive['成交数量'].sum())
                filled=joined.loc[matched].groupby(key)['成交数量'].sum()
                declared=a.set_index(key)['委托数量'].reindex(filled.index)
                violation=joined['成交价格']>joined['委托价格'] if side=='B' else joined['成交价格']<joined['委托价格']
                row.update(matched_records=int(matched.sum()),matched_quantity_share=float(joined.loc[matched,'成交数量'].sum()/total) if total else None,before_add_records=int((matched&(joined['时间_record']<joined['时间_add'])).sum()),limit_price_violations=int((matched&(joined['委托价格']>0)&violation).sum()),fill_gt_A_quantity_groups=int((filled>declared).sum()))
            out.append(row)
    return out


def audit_day(frames,day,symbol):
    q,o,t=(frames[k] for k in KINDS)
    q=q.copy()
    for name in ('时间','成交价','当日累计成交量','成交笔数'):
        q[name]=integer_column(q,name)
    price=integer_column(t,'成交价格');qty=integer_column(t,'成交数量')
    positive=(price>0)&(qty>0)
    scaled=[int(p)*int(v) for p,v in zip(price[positive],qty[positive])]
    amount=sum(scaled);volume=sum(int(v) for v in qty[positive])
    if amount>np.iinfo(np.int64).max or volume>np.iinfo(np.int64).max:
        raise ValueError('raw daily total overflow')
    last=q.iloc[-1]
    expected_volume=int(last['当日累计成交量']);expected_count=int(last['成交笔数'])
    close=int(last['成交价'])
    times=t.ms.to_numpy()[positive]
    continuous=((times>=34200000)&(times<41400000))|((times>=46800000)&(times<53820000))
    row={'day':day,'symbol':symbol,'audit_status':'technical_read_ok_semantics_unqualified','quote_records':len(q),'order_records':len(o),'trade_file_records':len(t),'positive_price_records':int(positive.sum()),'zero_price_records':int((price==0).sum()),'positive_quantity_sum':volume,'candidate_amount_1e4':amount,'candidate_turnover_cny':amount/10000,'candidate_vwap_cny':amount/volume/10000 if volume else None,'candidate_price_scale':10000,'closing_quote_price_raw':close,'candidate_closing_price_cny':close/10000,'closing_quote_time':int(last['时间']),'closing_quote_quantity':expected_volume,'closing_quote_record_count':expected_count,'quantity_gap':expected_volume-volume,'record_count_gap':expected_count-int(positive.sum()),'raw_reconciliation_ok':volume==expected_volume and int(positive.sum())==expected_count,'clock_pre0930_records':int((times<34200000).sum()),'clock_continuous_records':int(continuous.sum()),'clock_from1457_records':int((times>=53820000).sum()),'clock_other_records':int((~continuous&(times>=34200000)&(times<53820000)).sum()),'raw_trade_ref_duplicates':int(t.loc[positive,'成交编号'].duplicated().sum()),'supplier_semantics_status':'unqualified','economic_conclusion':'not_generated'}
    return row,reference_audit(o,t,day,symbol)


def load_notes(path):
    data=json.loads(path.read_text())
    if data.get('schema')!='l2_postclose_source_qualification_notes@1':
        raise ValueError('unsupported source-gap ledger schema')
    # A file containing true is not a source-acceptance proof.
    if any(data.get(k) is not False for k in QUAL_KEYS):
        raise ValueError('this adapter cannot admit supplier semantics; do not edit qualification flags')
    calendar=path.parent/data['calendar']['path']
    excerpt=path.parent/data['calendar']['source_excerpt']
    for p in (calendar,excerpt):
        if not p.resolve().is_relative_to(path.parent.resolve()) or not p.is_file():
            raise ValueError('source-gap ledger reference escapes evidence directory')
    c=pd.read_csv(calendar,dtype=str,keep_default_na=False)
    if list(c.columns)!=['cal_date','is_open'] or c.cal_date.duplicated().any() or not c.is_open.isin(['0','1']).all():
        raise ValueError('invalid full-date schedule')
    dates=pd.to_datetime(c.cal_date,format='%Y%m%d',errors='raise')
    if list(dates)!=list(pd.date_range(dates.min(),dates.max())):
        raise ValueError('calendar has missing/unsorted natural dates')
    return data,tuple(c.loc[c.is_open=='1','cal_date']),{'notes_sha256':digest(path),'calendar_sha256':digest(calendar),'calendar_source_excerpt_sha256':digest(excerpt),'scope_start':data['calendar']['scope_start'],'scope_end_inclusive':data['calendar']['scope_end_inclusive']}


def window_quality(raw,cal,spec):
    mapping={(r.day,r.symbol):r for r in raw.itertuples(index=False)}
    rows=[]
    for symbol in spec.symbols:
        for W in spec.lookbacks:
            for i,day in enumerate(cal):
                days=cal[max(0,i-W+1):i+1]
                # pandas/numpy bool scalars are normalized explicitly, not by identity.
                bad=[d for d in days if (d,symbol) not in mapping or not bool(mapping[(d,symbol)].raw_reconciliation_ok)]
                rows.append({'day':day,'symbol':symbol,'lookback':W,'warmup_complete':len(days)==W,'raw_reconciliation_contiguous':len(days)==W and not bad,'bad_or_missing_days':';'.join(bad),'fund_flow_qualified':False})
    return pd.DataFrame(rows)


def render_report(summary,raw,quality,profiles,out):
    text=['# 盘后资金行为实现与现有样本结果','', '**研究结论：仍受资格阻塞；不能把本报告作为上涨预测或主力资金流向结论。**','',f"工程审计状态：`{summary['engineering_status']}`。原始已观察样本 {summary['stock_days']} 个股票日，技术读取成功 {summary['technical_ok_stock_days']}，对账不一致 {summary['reconciliation_failed_stock_days']}。",'', '## 已完成与未完成','', '- 已完成：可配置纯计算核心、独立价格标签、缺失传播、完整比较矩阵、本地探索性统计协议实现及真实文件审计。','- 未完成：本地供应商／编号／成交与竞价语义验收、独立收盘价与公司行为资格、前瞻可用时间与新日期验证。','- 所有真实资金结构值与 F/P 均保持缺失，未用候选编号分组冒充大额订单。矩阵的零样本数不是上涨概率0%。','', '## 最新原始记录描述（未认证语义，不是资金判断）','', '| 股票 | 日期 | 正价记录数 | 候选均价（按1万比例） | 收盘字段候选值 | 对账 |','|---|---|---:|---:|---:|---|']
    def number(v):
        return '缺失' if pd.isna(v) else f'{float(v):.4f}'
    for symbol in sorted(raw.symbol.unique()):
        r=raw.loc[raw.symbol==symbol].sort_values('day').iloc[-1]
        text.append(f"| {symbol} | {r.day} | {r.get('positive_price_records','缺失')} | {number(r.get('candidate_vwap_cny'))} | {number(r.get('candidate_closing_price_cny'))} | {'一致' if r.raw_reconciliation_ok else '不一致／读取失败'} |")
    text.extend(['','候选均价及价格字段仅描述源文件，不证明它们是已验收官方收盘／真实成交，更不是大资金持仓成本。','', '## 最新多尺度资格','', '| 股票 | W | 连续原始对账 | 资金画像 |','|---|---:|---|---|'])
    for symbol in sorted(raw.symbol.unique()):
        last=raw.loc[raw.symbol==symbol].day.max()
        for r in quality.loc[(quality.symbol==symbol)&(quality.day==last)].itertuples(index=False):
            text.append(f"| {symbol} | {r.lookback} | {'完整' if r.raw_reconciliation_contiguous else '不足：'+r.bad_or_missing_days} | 数据不足：源端资格未通过 |")
    text.extend(['','W=5等尺度包含10月12日时，其异常必须传播，不能跳过拼接。较短尺度对账恢复也不能代替来源和编号语义验收。','', '## 阻塞与下一动作',''])
    for reason in summary['research_blockers']: text.append('- '+reason)
    text.extend(['','执行者下一步应取得与本地包一致的字段字典、编号／通道规则及来源说明，核验后另实现受审阅的来源适配器；不能修改资格布尔值、使用相似数据集卡或复用旧样本来解锁。','', '本轮无新日期、无真实委托、无资金账户识别、无费用／PnL／收益认证，未生成正式Platform ValidationReport。','', '## 输出','', '`raw_daily_audit.csv`、`order_reference_audit.csv`、`daily_inputs.csv`、`window_quality.csv`、`profiles.csv`、`labels.csv`、`matrix.csv`、`source_verification.json`、`qualification_report.json`、`run_spec.json`。'])
    (out/'report.md').write_text('\n'.join(text)+'\n',encoding='utf-8')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-manifest',type=Path,default=BASIS)
    p.add_argument('--raw-root',type=Path,default=RAW)
    p.add_argument('--qualification-notes',type=Path,default=NOTES)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--symbols',nargs='+',default=['688122.SH','688137.SH','688655.SH'])
    p.add_argument('--lookbacks',nargs='+',type=int,default=[3,5,10,20])
    p.add_argument('--horizons',nargs='+',type=int,default=[1,3,5,10,20])
    p.add_argument('--thresholds-cny',nargs='+',type=int,default=[500000,1000000])
    p.add_argument('--primary-threshold-cny',type=int,default=1000000)
    p.add_argument('--dates',nargs='+')
    args=p.parse_args(argv)
    spec=PostcloseSpec(symbols=tuple(args.symbols),lookbacks=tuple(args.lookbacks),horizons=tuple(args.horizons),thresholds_cny=tuple(args.thresholds_cny),primary_threshold_cny=args.primary_threshold_cny)
    if args.output.exists() or args.output.resolve().is_relative_to(args.raw_root.resolve()):
        raise ValueError('output must be new and outside source cache')
    notes,calendar,evidence=load_notes(args.qualification_notes)
    manifest=json.loads(args.source_manifest.read_text())
    metas={}
    for m in manifest['members']:
        member=m['member'];parts=PurePosixPath(member).parts
        if len(parts)!=3 or not re.fullmatch(r'\d{8}',parts[0]) or parts[1] not in PostcloseSpec().symbols or parts[2] not in KINDS:
            raise ValueError('unexpected member catalog')
        if member in metas: raise ValueError('duplicate catalog member')
        if type(m.get('bytes')) is not int or m['bytes']<=0 or not re.fullmatch(r'[0-9A-Fa-f]{8}',str(m.get('crc32',''))) or not re.fullmatch(r'[0-9a-f]{64}',str(m.get('sha256',''))):
            raise ValueError('invalid catalog byte count or content fingerprints')
        metas[member]=m
    dates=sorted({member.split('/')[0] for member in metas})
    if args.dates:
        if args.dates!=sorted(set(args.dates)) or not set(args.dates).issubset(dates):
            raise ValueError('requested dates must be sorted unique and catalogued')
        dates=args.dates
    if not dates or len(dates)>150: raise ValueError('source date budget exceeded/empty')
    if dates[0]<evidence['scope_start'] or dates[-1]>evidence['scope_end_inclusive'] or not set(dates).issubset(calendar):
        raise ValueError('source dates outside evidenced schedule; do not invent future calendar')
    cal=tuple(d for d in calendar if dates[0]<=d<=dates[-1])
    members=[f'{d}/{s}/{k}' for d in dates for s in spec.symbols for k in KINDS]
    if sum(metas[m]['bytes'] for m in members if m in metas)>5*1024**3: raise ValueError('selected raw byte budget exceeded')
    args.output.mkdir(parents=True)
    run={'schema':'l2_postclose_audit_run@1','mode':'observed_unqualified_source_audit','generated_at':datetime.now(timezone.utc).isoformat(),'configuration':asdict(spec),'requested_dates':dates,'calendar_open_dates':cal,'source_manifest_sha256':digest(args.source_manifest),'basis_selected_data_sha256':manifest.get('selected_data_sha256'),'evidence':evidence,'code_sha256':{name:digest(Path(__file__).with_name(name)) for name in ('l2_postclose_core_v1.py','l2_postclose_inference_v1.py','run_l2_postclose_fund_flow_v1.py','l2_three_stock_microstructure_v1.py')},'environment':{'python':sys.version.split()[0],'pandas':pd.__version__,'numpy':np.__version__},'design_sha256':digest(Path('research/l2-postclose-fund-flow-design-v1.md')),'execution_spec_sha256':digest(Path('research/l2-postclose-execution-spec-v1.md')),'prospective_eligible':False}
    write_json(args.output/'run_spec.json',run)
    audits=[];references=[];verified=[];failures=[];daily_rows=[]
    for day in dates:
        for symbol in spec.symbols:
            frames={}
            try:
                for kind in KINDS:
                    member=f'{day}/{symbol}/{kind}'
                    if member not in metas: raise ValueError(f'missing catalog member: {member}')
                    frames[kind],detail=read_selected(args.raw_root,member,metas[member],day,symbol,kind)
                    verified.append(detail)
                audit,ref= audit_day(frames,day,symbol)
                references.extend(ref)
            except (OSError,ValueError,KeyError,UnicodeError,pd.errors.ParserError) as error:
                audit={'day':day,'symbol':symbol,'audit_status':'file_or_schema_failed','raw_reconciliation_ok':False,'error':str(error)[:500]}
                failures.append({'day':day,'symbol':symbol,'error':str(error)[:500]})
            audits.append(audit)
            for threshold in spec.thresholds_cny:
                daily_rows.append({'day':day,'symbol':symbol,'threshold_cny':threshold,'amount_1e4':audit.get('candidate_amount_1e4'),'quantity':audit.get('positive_quantity_sum'),'large_buy_1e4':None,'large_sell_1e4':None,'trade_ok':False,'order_ok':False,'close_raw':audit.get('closing_quote_price_raw'),'close_ok':False,'price_segment':None})
            print(json.dumps({'day':day,'symbol':symbol,'technical_status':audit['audit_status'],'raw_reconciliation_ok':bool(audit['raw_reconciliation_ok']),'fund_flow_qualified':False},ensure_ascii=False),flush=True)
    raw=pd.DataFrame(audits);daily=pd.DataFrame(daily_rows)
    for name in ('amount_1e4','quantity','large_buy_1e4','large_sell_1e4','close_raw'): daily[name]=pd.array(daily[name],dtype='Int64')
    profiles=rolling_profiles(daily,cal,spec)
    price=daily[['day','symbol','close_raw','close_ok','price_segment']].drop_duplicates(['day','symbol'])
    labels=future_labels(price,cal,spec,max(dates))
    matrix=infer_primary(profiles,labels,cal,spec,prospective_eligible=False)
    quality=window_quality(raw,cal,spec)
    for name,frame in (('raw_daily_audit.csv',raw),('order_reference_audit.csv',pd.DataFrame(references)),('daily_inputs.csv',daily),('window_quality.csv',quality),('profiles.csv',profiles),('labels.csv',labels),('matrix.csv',matrix)):
        frame.to_csv(args.output/name,index=False)
    write_json(args.output/'source_verification.json',{'files':verified,'failures':failures,'selected_verified_files':len(verified),'selected_expected_files':len(members),'physical_complete':not failures and len(verified)==len(members)})
    summary={'engineering_status':'completed_audit_with_blocked_research' if not failures else 'audit_has_physical_failures','research_status':'blocked','stock_days':len(raw),'technical_ok_stock_days':int(raw.audit_status.eq('technical_read_ok_semantics_unqualified').sum()),'reconciliation_failed_stock_days':int((raw.audit_status.eq('technical_read_ok_semantics_unqualified')&~raw.raw_reconciliation_ok).sum()),'physical_failed_stock_days':len(failures),'new_dates':0 if manifest.get('selected_data_sha256')=='22d7e32d0676e75b7334c29d77daee7b4482d1248d2368faecc3196c214a2891' else None,'prospective_dates_used':0,'qualified_fund_flow_rows':int(profiles.structure_status.eq('ok').sum()),'comparison_cells':len(matrix),'inference_cells_computed':int(matrix.inference_status.eq('computed_exploratory_only').sum()),'research_blockers':notes['blockers'],'source_qualification':notes,'semantic_gate_opened':False}
    write_json(args.output/'qualification_report.json',summary)
    render_report(summary,raw,quality,profiles,args.output)
    print(json.dumps({k:summary[k] for k in ('engineering_status','research_status','stock_days','technical_ok_stock_days','reconciliation_failed_stock_days','qualified_fund_flow_rows','comparison_cells','inference_cells_computed')},ensure_ascii=False),flush=True)
    return 2 if failures else 0


if __name__=='__main__':
    raise SystemExit(main())
