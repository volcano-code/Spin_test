"""Independent rational CGAL vs Cherchi exact-chain comparison on the SAME binary64 inputs.
Do not conflate independent author-rational final export with this dyadic test.
"""
from pathlib import Path
import argparse,gzip,hashlib,json,time,traceback,sys
from fractions import Fraction as Q
sys.path.insert(0,'/mnt/data/Noodles_v6_C4_work/code')
from common import ExactBuilder,token,sha,write_json
from exact_planar_patches import oriented_planar_chain_signature
p=argparse.ArgumentParser();p.add_argument('--design',type=Path,required=True);p.add_argument('--material',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
t=time.monotonic();a.output.mkdir(parents=True,exist_ok=False)
record=dict(schema='v7-independent-Chi-CGAL-same-binary64-operand-exact-chain-v1',status='STARTED',passed=False)
try:
 d=json.loads(a.design.read_text());D={'vertices':[[token(Q(float(Q(x)))) for x in row] for row in d['vertices']],'faces':d['faces']}
 with gzip.open(a.material,'rt') as f:m=json.load(f)
 S={'vertices':[[token(Q(float(x))) for x in row] for row in m['quadric_source_vertices']],'faces':m['quadric_source_faces']}
 op='intersection' if m['boolean_operation']=='intersection' else 'difference'
 print('PROOF_BEGIN',len(D['faces']),len(S['faces']),op,flush=True)
 builder=ExactBuilder('/mnt/data/Noodles_v6_C4_work/native/noodles-exact-boolean',a.output/'csg',timeout=600)
 result=builder.boolean(D,S,op)
 print('CGAL_SAME_FLOAT_DONE',len(result['faces']),'time',time.monotonic()-t,flush=True)
 shift=Q(float(-0.16))
 # Cherchi material rational coordinates are target-frame; undo target-origin shift.
 cv=[[token(Q(x)+(shift if j==2 else Q(0))) for j,x in enumerate(row)] for row in m['variable_rational_vertices']]
 bv=result['vertices'];n=len(cv)
 faces=m['variable_faces']+[[n+f[2],n+f[1],n+f[0]] for f in result['faces']]
 sig=oriented_planar_chain_signature(cv+bv,faces)
 passed=not sig['signature'] and not sig['exact_null_triangle_indices']
 record.update(status='COMPLETED',passed=passed,exact_signed_surface_chain_equal=passed,
               nonzero_support_planes=len(sig['signature']),exact_null_faces=len(sig['exact_null_triangle_indices']),
               cherchi_faces=len(m['variable_faces']),cgal_faces=len(result['faces']),
               source_design_sha256=sha(a.design),source_material_sha256=sha(a.material),
               cgalsamefloat_sha256=sha(a.output/'csg/result-0001.json'))
 print('PROOF_END',passed,'nonzero',record['nonzero_support_planes'],'time',time.monotonic()-t,flush=True)
 if not passed:raise RuntimeError('CHERCHI_CGAL_SAME_FLOAT_MATERIAL_MISMATCH')
except Exception as e:
 record.update(status='FAILED',error=f'{type(e).__name__}: {e}',traceback=traceback.format_exc());raise
finally:
 record['seconds']=time.monotonic()-t
 (a.output/'status.json').write_text(json.dumps(record,indent=2))
