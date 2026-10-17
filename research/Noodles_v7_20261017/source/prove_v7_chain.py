"""Independent rational planar signed surface chain checks for v7 CSG outputs.

Does not assert physical solid validity. No optimization is performed.
"""
from pathlib import Path
import json,time,hashlib,sys
from fractions import Fraction
sys.path.insert(0,'/mnt/data/Noodles_v6_C4_work/code')
from exact_planar_patches import oriented_planar_chain_signature

root=Path('/mnt/data/Noodles_v7_paper_geometry_candidate/exact_v7c')
identities=[('F_plus_D_equals_A',[('fixed',1),('design',1),('initial',-1)]),
            ('K_plus_D_equals_E',[('fixed-inside-envelope',1),('design',1),('envelope',-1)]),
            ('K_plus_R_equals_F',[('fixed-inside-envelope',1),('fixed-outside-envelope',1),('fixed',-1)])]
reports=[]
for label,pairs in identities:
    resultpath=root/(label+'-chain-check.json')
    if resultpath.exists():
        print('SKIP_EXISTING',label,flush=True);reports.append(json.loads(resultpath.read_text()));continue
    st=time.monotonic();verts=[];faces=[];input_hashes={}
    for name,sign in pairs:
        path=root/(name+'-rational.json');d=json.loads(path.read_text());off=len(verts);verts.extend(d['vertices'])
        faces.extend(([off+int(i) for i in f] if sign==1 else [off+int(i) for i in f[::-1]]) for f in d['faces'])
        input_hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    print('CHECK',label,len(verts),len(faces),flush=True)
    try:
        s=oriented_planar_chain_signature(verts,faces)
        result=dict(name=label,success=len(s['signature'])==0 and not s['exact_null_triangle_indices'],nonzero_support_planes=len(s['signature']),exact_zero_area_triangles=len(s['exact_null_triangle_indices']),inputs=input_hashes,seconds=time.monotonic()-st)
    except BaseException as e:
        result=dict(name=label,success=False,error=f'{type(e).__name__}:{e}',inputs=input_hashes,seconds=time.monotonic()-st)
    resultpath.write_text(json.dumps(result,indent=2))
    print('RESULT',label,result,flush=True);reports.append(result)
    if not result['success']:
        break
summary={'all_three_chains_verified':len(reports)==3 and all(r['success'] for r in reports),'results':reports,'does_not_prove_native_solid_validity':True}
(root/'exact-chain-summary.json').write_text(json.dumps(summary,indent=2))
print('COMPLETE',summary['all_three_chains_verified'],flush=True)
