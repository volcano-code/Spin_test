"""Independent CGAL set-equality certificate AFTER Cherchi Boolean, never a solver fallback.
This may be slow; incomplete results are not success.
"""
import json,time,hashlib
from pathlib import Path
import numpy as np
import _make_it_stand as n
p=Path('/mnt/data/Heart_Cherchi_H1')
pkt=json.loads((p/'evidence/cherchi_exact_output.json').read_text())
old=json.loads(Path('/mnt/data/heart_lab/fixtures/heart-older-frozen-requests-v4.json').read_text())
req=old['requests'][1]['request']; q=np.array(json.loads(Path('/mnt/data/heart_lab/fixtures/heart-seed1-source-failure-registration-01.json').read_text())['event']['quadric_coefficients'])
axes=np.array(req['target_axes']);origin=np.array(req['target_origin']); design=(np.array(req['design_vertices'])-origin)@axes.T
settings=n.SpinTriangulationSettings()
for key in ('icosphere_subdivisions','maximum_radius_doublings','retain_fixed_normal_provenance','truncation_radius','algebraic_finite_map'):
 setattr(settings,key,old['evaluator_settings'][key])
settings.maximum_icosphere_subdivisions=settings.icosphere_subdivisions
settings.paper_projective_hyperboloid=True
settings.retain_fixed_normal_provenance=True
source=n.evaluate_spin_it_faster_source_motion(q,design,settings)
if not source['defined'] or source['interior_is_positive'] is not True:raise ValueError('SOURCE_WRONG_BRANCH')
base=time.monotonic();print('INDEPENDENT only—not solver backend',flush=True)
d=n.make_exact_material_region(design,np.array(req['design_faces'],dtype=np.int32))
print('DESIGN_REGION',round(time.monotonic()-base,3),flush=True)
s=n.make_exact_material_region(np.asarray(source['vertices']),np.asarray(source['faces'],dtype=np.int32))
print('SOURCE_REGION',round(time.monotonic()-base,3),flush=True)
m=n.make_exact_material_region_from_rationals(pkt['exact_vertices'],np.array(pkt['faces'],dtype=np.int32))
print('MATERIAL_REGION',round(time.monotonic()-base,3),flush=True)
proof=dict(n.relate_exact_boolean_operation_to_material(d,s,m,pkt['operation']))
print('PROOF_DONE',round(time.monotonic()-base,3),json.dumps(proof,default=str)[:1400],flush=True)
(p/'evidence/independent-exact-set-comparison.json').write_text(json.dumps({'role':'INDEPENDENT_AUDIT_ONLY_NOT_BACKEND','elapsed_seconds':time.monotonic()-base,'proof':proof},indent=2,default=str))
