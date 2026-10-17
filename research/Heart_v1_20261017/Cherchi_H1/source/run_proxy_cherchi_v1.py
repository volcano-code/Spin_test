"""Native source-to-Cherchi single-call probe with frozen historical *proxy* design.
Not the authoritative eval60 request; not a formal Newton step.
"""
import hashlib,json,time,sys,os
from pathlib import Path
import numpy as np
import _make_it_stand as n
import _cherchi_core_boolean as b
HERE=Path(__file__).resolve().parents[1]
fix=Path('/mnt/data/heart_lab/fixtures')
payload_path=fix/'heart-older-frozen-requests-v4.json'
reg_path=fix/'heart-seed1-source-failure-registration-01.json'
p=json.loads(payload_path.read_text());reg=json.loads(reg_path.read_text())
q=np.asarray(reg['event']['quadric_coefficients'],dtype=np.float64)
req=p['requests'][1]['request']; e=p['evaluator_settings']
axes=np.asarray(req['target_axes']);origin=np.asarray(req['target_origin']);design=(np.asarray(req['design_vertices'])-origin)@axes.T
cfg=n.SpinTriangulationSettings()
for key in ('icosphere_subdivisions','maximum_radius_doublings','retain_fixed_normal_provenance','truncation_radius','algebraic_finite_map'):
    setattr(cfg,key,e[key])
cfg.maximum_icosphere_subdivisions=cfg.icosphere_subdivisions
cfg.paper_projective_hyperboloid=True
cfg.retain_fixed_normal_provenance=True
print('HEAD',json.dumps({'n':hashlib.sha256(Path(n.__file__).read_bytes()).hexdigest(),'cherchi':hashlib.sha256(Path(b.__file__).read_bytes()).hexdigest(),'proxy_design_sha':hashlib.sha256(payload_path.read_bytes()).hexdigest(),'not_authoritative_eval60':True,'q_sha':reg['event']['quadric_hash']}),flush=True)
t=time.monotonic();src=n.evaluate_spin_it_faster_source_motion(q,design,cfg);print('SOURCE',src['defined'],src['side_selection_defined'],len(src['vertices']),len(src['faces']),time.monotonic()-t, flush=True)
if not src['defined'] or not src['side_selection_defined']:raise RuntimeError('SOURCE_NOT_DEFINED')
sv=np.asarray(src['vertices']);sf=np.asarray(src['faces']); print('SRC SIGN',src['interior_is_positive'],flush=True)
op='intersection' if src['interior_is_positive'] else 'difference'
t=time.monotonic();pkt=b.boolean(design.tolist(),req['design_faces'],sv.tolist(),sf.tolist(),op)
print('CHERCHI DONE',len(pkt['vertices']),len(pkt['faces']),len(pkt['construction_records']),time.monotonic()-t, flush=True)
verts=np.asarray(pkt['vertices']);faces=np.asarray(pkt['faces']);
t=time.monotonic();audit=dict(n.audit_exact_triangle_boundary(verts,faces,'AnyNonzero'));
print('AUDIT',audit.get('boundary_valid'),len(audit.get('intersecting_pairs',[])),time.monotonic()-t,flush=True)
rec={'source_type':'ARCHIVED_V4_PROXY_NOT_REAL_EVAL60','historical_eval60_reproduced':False,'complete_heart_newton':False,'chernhi_no_fallback':True,'cherchi_backend':pkt['backend'],'boolean_operation':op,'input_design_faces':len(req['design_faces']),'source_faces':len(sf),'material_faces':len(faces),'material_vertices':len(verts),'construction_records':len(pkt['construction_records']),'audit_boundary_valid':bool(audit.get('boundary_valid')),'native_hash':hashlib.sha256(Path(n.__file__).read_bytes()).hexdigest(),'cherchi_sha256':hashlib.sha256(Path(b.__file__).read_bytes()).hexdigest()}
(HERE/'evidence/proxy-single-boolean-result.json').write_text(json.dumps(rec,indent=2))
print('FINAL',json.dumps(rec),flush=True)
if not rec['audit_boundary_valid']:raise RuntimeError('CHERCHI_OUTPUT_FAILED_INDEPENDENT_AUDIT')