"""Restartable exact CGAL input construction for Noodles v7.

No optimization, no fabricated final mesh; save each Boolean node for review.
Cherchi remains production Newton backend; this CGAL code is offline input setup.
"""
from pathlib import Path
import argparse,hashlib,json,time,sys
from common import ExactBuilder, obj_packet,packet_arrays,sha,write_json,load_json,export_obj


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',default='/mnt/data/Noodles_v7_paper_geometry_candidate/source_parts_v7c')
 ap.add_argument('--out',default='/mnt/data/Noodles_v7_paper_geometry_candidate/exact_v7c')
 ap.add_argument('--boolean',default='/mnt/data/Noodles_v6_C4_work/native/noodles-exact-boolean')
 args=ap.parse_args();source=Path(args.source);out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
 manifest=load_json(source/'manifest.json');parts=manifest['parts'];recipe=manifest['construction']
 if manifest['spec']['schema']!='noodles-paper-photo-hypothesis-v7' or len(recipe['fixed_parts'])!=93:
  raise ValueError('incorrect input v7 identity')
 for n,item in parts.items():
  if sha(source/item['model_obj'])!=item['sha256_model']:raise ValueError('source digest mismatch '+n)
 # Fail if missing exact source boundary PASS. Expect written after source audit.
 a=load_json(out.parent/'source-v7c-native-audit.json')
 if not a['full_source_parts_passed'] or a['parts_completed']!=94:raise ValueError('source not audited')
 aud={x['part']:x for x in a['results']}
 for n,item in parts.items():
  if n+'-model.obj' not in aud or aud[n+'-model.obj']['sha256']!=item['sha256_model']:
   raise ValueError('source audit mismatch '+n)
 b=ExactBuilder(args.boolean,out/('csg-run-'+str(int(time.time()))),timeout=330)
 start=time.monotonic();names=recipe['fixed_parts'];nodes=[]
 for name in names:
  packet=obj_packet(source/parts[name]['model_obj']);nodes.append((name,packet))
 print('SOURCE',len(nodes),'fixed items; starting balanced exact union',flush=True)
 roundidx=0
 while len(nodes)>1:
  new=[]
  for j in range(0,len(nodes),2):
   if j+1>=len(nodes):new.append(nodes[j]);continue
   ka,a=nodes[j];kb,bobj=nodes[j+1]
   fname=f'fixed-union-level{roundidx:02d}-pair{j//2:03d}.json'
   p=out/fname
   if p.exists():
    rec=load_json(out/(fname+'.receipt'))
    if rec['sources']!=[ka,kb] or rec['result_sha']!=sha(p):raise ValueError('cached union identity mismatch '+fname)
    val=load_json(p);print('CACHE',fname,len(val['faces']),flush=True)
   else:
    val=b.boolean(a,bobj,'union')
    write_json(p,val);write_json(out/(fname+'.receipt'),dict(sources=[ka,kb],result_sha=sha(p),out_faces=len(val['faces']),backend_sha=b.exe_sha))
    print('UNION',fname,len(val['faces']),'faces; native boolean #',b.index,flush=True)
   new.append((f'({ka}+{kb})',val))
  nodes=new
  print('LEVEL',roundidx,'remaining nodes',len(nodes),'seconds',round(time.monotonic()-start,2),flush=True)
  roundidx+=1
 fixed=nodes[0][1];p=out/'fixed-rational.json'
 if not p.exists():write_json(p,fixed)
 E=obj_packet(source/parts['outer-ellipsoid']['model_obj'])
 for name,a,bobj,op in [
    ('envelope',None,None,None),('design',E,fixed,'difference'),('initial',E,fixed,'union'),
    ('fixed-inside-envelope',E,fixed,'intersection'),('fixed-outside-envelope',fixed,E,'difference')]:
  path=out/(name+'-rational.json')
  if path.exists():continue
  if op is None:r=E
  else:r=b.boolean(a,bobj,op)
  write_json(path,r)
  print('CONSTRUCTED',name,'faces',len(r['faces']),'seconds',round(time.monotonic()-start,2),flush=True)
 summary=dict(schema='noodles-v7-exact-cgal-input-construction',status='EXACT_INPUT_CONSTRUCTED_NOT_OPTIMIZED',manifest_sha=sha(source/'manifest.json'),
              backend_sha=b.exe_sha,csg_executed_current_process=b.index,
              outputs={n:dict(path=str(out/(n+'-rational.json')),sha=sha(out/(n+'-rational.json')),
                               faces=len(load_json(out/(n+'-rational.json'))['faces'])) for n in ('fixed','envelope','design','initial','fixed-inside-envelope','fixed-outside-envelope')},
              elapsed_sec=time.monotonic()-start,independent_partition_verified=False,
              newton_solved=False,physics_simulated=False)
 write_json(out/'construction.json',summary)
 for n in ['fixed','envelope','design','initial']:
  r=load_json(out/(n+'-rational.json'))
  export_obj(out/(n+'-input-mm.obj'),r,manifest['spec']['model_unit_m']*1000,label='v7 PHOTO HYPOTHESIS INPUT NOT OPTIMIZED')
 print('INPUT_CONSTRUCTION_COMPLETE',round(time.monotonic()-start,2),flush=True)

if __name__=='__main__':main()
