"""Repo-native SVG case paths; nullable cash stays blank, no PnL drawing."""
import argparse
import csv
import hashlib
import html
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path


def table(path):
    with path.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))


def render(source, output, symbols=None):
    if output.exists():raise ValueError('new plots directory required')
    data=table(source/'daily_price_cash.csv');anchors=table(source/'price_anchors.csv');timing=table(source/'first_observed_cash_timing.csv');output.mkdir(parents=True)
    renderer=Path('/home/ygguo/.agent/diagrams/rasterize-l2-svg.py');artifacts=[]
    for a in anchors:
        symbol=a['symbol']
        if symbols is not None and symbol not in symbols:continue
        ds=sorted((r for r in data if r['symbol']==symbol),key=lambda r:r['day']);days=[r['day'] for r in ds];t=next(r for r in timing if r['symbol']==symbol)
        width,height=1600,1000;left,right=105,1530;dx=(right-left)/(len(ds)-1)
        X=lambda i:left+i*dx
        svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">','<rect width="1600" height="1000" fill="#f8fafc"/>','<defs><pattern id="missing" width="8" height="8" patternUnits="userSpaceOnUse"><path d="M-2,2 L2,-2 M0,8 L8,0 M6,10 L10,6" stroke="#cbd5e1" stroke-width="1"/></pattern></defs>','<g font-family="Noto Sans CJK SC,Noto Sans CJK JP,sans-serif">']
        def text(x,y,value,size=18,color='#334155',anchor='start'):
            svg.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{html.escape(str(value))}</text>')
        def line(x1,y1,x2,y2,color='#cbd5e1',dash=None,stroke=1):
            svg.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{color}" stroke-width="{stroke}"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>')
        def poly(values,Y,color):
            segment=[]
            def emit():
                if len(segment)>1:svg.append('<polyline fill="none" stroke="'+color+'" stroke-width="2.5" points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in segment)+'"/>')
                for x,y in segment:svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.4" fill="{color}"/>')
            for i,value in enumerate(values):
                if value is None:emit();segment=[]
                else:segment.append((X(i),Y(value)))
            emit()
        text(70,43,f"{symbol}  {a['name']}｜价格阶段 × 成交组现金",29,'#0f172a')
        text(70,77,'价格至2026-10-21；资金至10-19。低点/峰值为事后原值锚点，不是实时买点。',18)
        prices=[float(Decimal(r['raw_source_close_yuan'])) if r['raw_source_close_yuan'] else None for r in ds]
        low=min(v for v in prices if v is not None);high=max(v for v in prices if v is not None);pad=max((high-low)*0.10,0.1);lo,hi=low-pad,high+pad;Y=lambda v:340-(v-lo)/(hi-lo)*225
        for k in range(5):
            value=lo+(hi-lo)*k/4;y=Y(value);line(left,y,right,y,'#e2e8f0');text(left-12,y+6,f'{value:.2f}',15,anchor='end')
        text(28,130,'原价',17);text(28,155,'元',16)
        for i,r in enumerate(ds):
            if not r['raw_source_close_yuan']:svg.append(f'<rect x="{X(i)-dx/2:.2f}" y="110" width="{dx:.2f}" height="235" fill="url(#missing)"/>')
        poly(prices,Y,'#2563eb')
        fields=['group_difference_1e4','active_difference_1e4','passive_difference_1e4','unknown_difference_1e4']
        vals={k:[float(Decimal(r[k])/100000000) if r['cash_ready']=='True' and r.get(k,'')!='' else None for r in ds] for k in fields}
        bands=[(390,570,['group_difference_1e4']), (640,835,fields[1:])]
        colors={'active_difference_1e4':'#d97706','passive_difference_1e4':'#7c3aed','unknown_difference_1e4':'#64748b'}
        for top,bottom,ks in bands:
            maximum=max([abs(v) for k in ks for v in vals[k] if v is not None]+[1]);maximum*=1.08;mid=(top+bottom)/2;Ycash=lambda v,mid=mid,top=top,maximum=maximum:mid-v/maximum*(mid-top)
            for v in (-maximum,0,maximum):line(left,Ycash(v),right,Ycash(v),'#cbd5e1' if v==0 else '#e2e8f0');text(left-12,Ycash(v)+5,f'{v:,.0f}',14,anchor='end')
            for i,r in enumerate(ds):
                if r['cash_ready']!='True':svg.append(f'<rect x="{X(i)-dx/2:.2f}" y="{top}" width="{dx:.2f}" height="{bottom-top}" fill="url(#missing)"/>')
            if ks==['group_difference_1e4']:
                for i,v in enumerate(vals[ks[0]]):
                    if v is None:continue
                    y=Ycash(v);svg.append(f'<rect x="{X(i)-8:.2f}" y="{min(mid,y):.2f}" width="16" height="{max(abs(mid-y),0.6):.2f}" fill="'+('#b45309' if v>=0 else '#059669')+'"/>')
            else:
                for k in ks:poly(vals[k],Ycash,colors[k])
        text(28,411,'组差',17);text(15,438,'万元',15);text(28,661,'角色差',17);text(15,689,'万元',15)
        for day,label,color,yy in ((a['trough_day'],'原值低点','#0891b2',365),(a['peak_day'],'段内峰值','#dc2626',365)):
            i=days.index(day);x=X(i);line(x,105,x,844,color,'5 5',1.5);text(x+5 if x<1350 else x-5,yy,label+' '+day[4:6]+'/'+day[6:],16,color,'start' if x<1350 else 'end')
        joint=t.get('first_observed_joint_hit','')
        if joint:
            x=X(days.index(joint));line(x,385,x,844,'#9333ea','2 5',1.3);text(x+5 if x<1300 else x-5,605,'首个可见5日双条件 '+joint[4:6]+'/'+joint[6:],15,'#9333ea','start' if x<1300 else 'end')
        for i in (0,5,10,16,20,23,27,30):
            if i<len(days):text(X(i),875,days[i][4:6]+'/'+days[i][6:],16,anchor='middle')
        text(120,918,'角色差：',17);text(220,918,'● 主动',17,'#d97706');text(365,918,'● 被动',17,'#7c3aed');text(510,918,'● 未判',17,'#64748b')
        text(70,956,'斜线/断线：没有完整记录，不是0；股价原值未授复权收益资格。各图现金纵轴独立缩放。',17)
        text(70,982,'现金按每日全日≥50万元交付引用组定档；差额不等于机构净流入或持仓。双条件标记不代表预测成立。',16)
        svg.append('</g></svg>');path=output/(symbol[:6]+'.svg');png=path.with_suffix('.png');path.write_text('\n'.join(svg)+'\n')
        subprocess.run([sys.executable,str(renderer),str(path),str(png)],check=True,capture_output=True,text=True,timeout=30)
        artifacts.append({'symbol':symbol,'svg':str(path),'png':str(png),'png_sha256':hashlib.sha256(png.read_bytes()).hexdigest(),'bytes':png.stat().st_size})
    page=['<!doctype html><meta charset="utf-8"><title>九股价格阶段与资金轨迹</title><style>body{font-family:system-ui;margin:24px;background:#f1f5f9;color:#0f172a}img{width:100%;max-width:1600px}section{margin:36px 0}p{max-width:1100px}</style><h1>九股价格阶段 × 资金轨迹</h1><p>原始价格观察、源标记成交组现金；数据缺口不填零。低点/峰值事后确定。不是收益或领先性检验。</p>']
    for a in artifacts:page.append(f'<section><h2>{a["symbol"]}</h2><img src="{Path(a["png"]).name}" alt="{a["symbol"]}价格与现金原始记录"></section>')
    (output/'index.html').write_text('\n'.join(page)+'\n');receipt={'role':'raw_price_cash_case_graphs_not_qualified_trends','source_dir':str(source),'artifacts':artifacts,'renderer':str(renderer),'renderer_sha256':hashlib.sha256(renderer.read_bytes()).hexdigest(),'HTML_browser_layout_verified':False};(output/'plot_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--symbols',nargs='+');a=p.parse_args();r=render(a.source,a.output,a.symbols);print(json.dumps({'plots':len(r['artifacts']),'output':str(a.output)},ensure_ascii=False))
