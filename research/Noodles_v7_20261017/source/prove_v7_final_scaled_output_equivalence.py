"""Independently prove exact oriented finite surface-chain equivalence of v7 final output.
Separate implementation from local patch builder. Not a complete material-domain
proof or floating topology guarantee.
"""
from pathlib import Path
import argparse,hashlib,json,time,sys,traceback
sys.path.insert(0,'/mnt/data/Noodles_v6_C4_work/code')
from exact_planar_patches import oriented_planar_chain_signature
p=argparse.ArgumentParser();p.add_argument('--original',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();t=time.monotonic()
r=dict(schema='v7-terminal-full-independent-oriented-rational-chain-proof-v1',completed=False,exact_surface_chain_equal=False)
try:
 d=json.loads(a.original.read_text());c=json.loads(a.candidate.read_text());offset=len(d['vertices'])
 verts=d['vertices']+c['vertices'];faces=d['faces']+[[offset+v for v in f[::-1]] for f in c['faces']]
 print('GLOBAL CHAIN',len(verts),'vertices',len(faces),'faces',flush=True)
 s=oriented_planar_chain_signature(verts,faces)
 r.update(completed=True,exact_surface_chain_equal=(not s['signature'] and not s['exact_null_triangle_indices']),
     nonzero_support_planes=len(s['signature']),exact_null_faces=len(s['exact_null_triangle_indices']),
     original_sha256=hashlib.sha256(a.original.read_bytes()).hexdigest(),
     candidate_sha256=hashlib.sha256(a.candidate.read_bytes()).hexdigest(),
     original_faces=len(d['faces']),candidate_faces=len(c['faces']))
 print('GLOBAL RESULT',r['exact_surface_chain_equal'],'differences',r['nonzero_support_planes'],flush=True)
except BaseException as e:
 r.update(error=f'{type(e).__name__}: {e}',traceback=traceback.format_exc());raise
finally:
 r['elapsed_seconds']=time.monotonic()-t
 a.report.write_text(json.dumps(r,indent=2,allow_nan=False))
