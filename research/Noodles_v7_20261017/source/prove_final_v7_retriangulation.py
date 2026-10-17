"""Independent proof of entire signed oriented rational planar chain equality.

Only verifies boundary representational equivalence. It cannot certify the
binary64 mesh, manifold geometry or scientific numerical solver.
"""
from pathlib import Path
import json, hashlib, time, sys
sys.path.insert(0,'/mnt/data/Noodles_v6_C4_work/code')
from exact_planar_patches import oriented_planar_chain_signature
R=Path(__file__).resolve().parent
orig=R/'exact_v7c/design-rational.json'; repl=R/'two-stage-generic-retriangulation-candidate-rational.json'
start=time.monotonic();d=json.loads(orig.read_text());c=json.loads(repl.read_text());V=d['vertices']+c['vertices']; offset=len(d['vertices'])
F=d['faces']+[[offset+x for x in f[::-1]] for f in c['faces']]
print('CHECK_BOUNDARY_CHAIN',len(V),len(F),flush=True)
try:
 s=oriented_planar_chain_signature(V,F)
 r=dict(completed=True,exact_surface_chain_equal=not s['signature'] and not s['exact_null_triangle_indices'],nonzero_support_planes=len(s['signature']),exact_zero_area_triangles=len(s['exact_null_triangle_indices']),source_sha256=hashlib.sha256(orig.read_bytes()).hexdigest(),candidate_sha256=hashlib.sha256(repl.read_bytes()).hexdigest(),seconds=time.monotonic()-start,notes='Only exact rational oriented surface equivalence, not binary64 suitability')
except Exception as e:r=dict(completed=False,exception=type(e).__name__+': '+str(e),seconds=time.monotonic()-start)
(R/'final-design-global-exact-chain-proof.json').write_text(json.dumps(r,indent=2))
print('RESULT',r,flush=True)
