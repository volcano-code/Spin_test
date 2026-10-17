from pathlib import Path
import json,time,hashlib,sys
import numpy as np
import _make_it_stand as n
import _cherchi_core_boolean as b
R=Path('/mnt/data/Heart_Cherchi_H1')
p=json.loads((R/'evidence/cherchi_exact_output.json').read_text())
print('CANDIDATE',len(p['vertices']),len(p['faces']),'operands',len(p['exact_vertices']),flush=True)
f=np.asarray(p['faces'],dtype=np.int32)
t=time.monotonic()
try:
 a=dict(n.audit_exact_rational_triangle_boundary(p['exact_vertices'],f,'AnyNonzero'))
 print('EXACT_AUDIT',time.monotonic()-t,{k:(len(a[k]) if isinstance(a.get(k),list) else a.get(k)) for k in ['boundary_valid','closed','edge_manifold','vertex_manifold','component_orientations_valid','self_intersection_free','intersecting_pairs','degenerate_faces','intersection_error']},flush=True)
 (R/'evidence/rational-output-audit.json').write_text(json.dumps(a,indent=2,default=str))
 if a.get('boundary_valid'):
  import numpy as np
  from fractions import Fraction
  # no assertion of same material until independent set equality validation
  try:
   material=n.make_exact_material_region_from_rationals(p['exact_vertices'],f)
   print('RATIONAL_REGION constructed',type(material),time.monotonic()-t,flush=True)
  except Exception as e: print('REGION_EXCEPTION',type(e).__name__,str(e)[:400],flush=True)
except Exception as e:print('EXACT_AUDIT_EXCEPTION',type(e).__name__,str(e)[:500],flush=True);raise
