"""Metadata-only historical SH/SZ breadth/resource preflight. Never extracts data."""
import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

HOME=Path('/srv/bcache-8t/ygguo/quant/l2-historical-candidates-v11')


def inventory(scope,dates,scope_path=None):
    if not scope.get('metadata_only') or not set(dates)<=set(scope['dates']):
        raise ValueError('metadata-only declared dates required')
    archives=[];missing=[];members=[];listing_bytes=0
    for day in dates:
        path=Path(scope['source'])/day[:6]/(day+'.7z');before=path.stat();start=time.monotonic()
        cp=subprocess.run(['7z','l','-slt',str(path)],capture_output=True,text=True,timeout=scope['per_listing_timeout_seconds'])
        n=len(cp.stdout.encode());listing_bytes+=n
        if cp.returncode or n>scope['single_listing_max_bytes'] or listing_bytes>scope['metadata_stdout_budget_bytes'] or '----------' not in cp.stdout:
            raise ValueError('listing failed or metadata budget exceeded')
        files=[]
        for block in cp.stdout.split('----------',1)[1].strip().split('\n\n'):
            r=dict(line.split(' = ',1) for line in block.splitlines() if ' = ' in line)
            if 'Path' in r and not r.get('Attributes','').startswith('D'):files.append(r)
        wanted={f'{day}/{s}/{kind}' for s in scope['symbols'] for kind in scope['kinds']}
        chosen=[r for r in files if r['Path'] in wanted]
        if len({r['Path'] for r in chosen})!=len(chosen):raise ValueError('duplicate selected member')
        touched={r['Block'] for r in chosen}
        solid=sum(int(r['Size']) for r in files if r.get('Block') in touched)
        for r in chosen:members.append({'archive':str(path),'member':r['Path'],'bytes':int(r['Size']),'crc32':r['CRC'].lower(),'block':r['Block']})
        missing.extend(sorted(wanted-{r['Path'] for r in chosen}));after=path.stat()
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('archive changed during listing')
        archives.append({'day':day,'path':str(path),'bytes':before.st_size,'mtime_ns':before.st_mtime_ns,'selected_member_count':len(chosen),'selected_bytes':sum(int(r['Size']) for r in chosen),'involved_solid_uncompressed_bytes':solid,'listing_seconds':round(time.monotonic()-start,3)})
    return {'role':'metadata_only_resource_estimate_no_payload_read','asof':scope['asof'],'symbols':len(scope['symbols']),'dates':dates,'listing_output_bytes':listing_bytes,'selected_bytes':sum(m['bytes'] for m in members),'involved_solid_bytes':sum(a['involved_solid_uncompressed_bytes'] for a in archives),'missing_members':missing,'archives':archives,'members':members,'scope_sha256':hashlib.sha256((scope_path or HOME/'inventory_scope.json').read_bytes()).hexdigest(),'payload_extracted':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--smoke',action='store_true');p.add_argument('--scope',type=Path,default=HOME/'inventory_scope.json');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('new receipt path required')
    scope=json.loads(a.scope.read_text());dates=scope['dates'][-1:] if a.smoke else scope['dates'];r=inventory(scope,dates,a.scope)
    a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ('members','archives','missing_members')},ensure_ascii=False));print('members',len(r['members']),'missing',len(r['missing_members']))
