"""Independent OBJ vs newly converged Cherchi material / SI mass property audit.
Does not certify exact F+D=A in the separately rounded input representation.
"""
import argparse,gzip,hashlib,json,time,traceback
from pathlib import Path
import numpy as np
import trimesh

p=argparse.ArgumentParser()
p.add_argument('--complete',type=Path,required=True)
p.add_argument('--initial',type=Path,required=True)
p.add_argument('--material',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
t=time.monotonic();rec={'schema':'noodles-v7-independent-OBJ-physical-moments-audit-v1','passed':False,'status':'STARTED'}

def props(path):
    m=trimesh.load(path,force='mesh',process=False)
    mass_obj=float(m.volume)
    cm_mm=np.asarray(m.center_mass,dtype=float)
    inertia=np.asarray(m.moment_inertia,dtype=float)
    return m,{'vertices':int(len(m.vertices)),'faces':int(len(m.faces)),'obj_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
             'watertight':bool(m.is_watertight),'winding_consistent':bool(m.is_winding_consistent),
             'euler_number':int(m.euler_number),'signed_volume_mm3':mass_obj,
             'mass_g_at_1200kg_m3':float(mass_obj*.0012),
             'center_of_mass_mm':cm_mm.tolist(),'distance_COM_to_Z_axis_mm':float(np.hypot(*cm_mm[:2])),
             'inertia_center_kg_m2':(inertia/1e15*1200).tolist(),
             'inertia_axis_ratio_zz_xx':float(inertia[2,2]/inertia[0,0]),
             'inertia_axis_ratio_zz_yy':float(inertia[2,2]/inertia[1,1])}

try:
    initial,ip=props(a.initial);complete,cp=props(a.complete)
    rec.update(initial=ip,complete=cp)
    with gzip.open(a.material,'rt') as f:material=json.load(f)
    if not np.isfinite(complete.vertices).all() or not np.isfinite(complete.faces).all():raise ValueError('NAN_OBJ')
    if not cp['watertight'] or not cp['winding_consistent'] or cp['signed_volume_mm3']<=0:raise RuntimeError('INVALID_COMPLETE_SURFACE')
    if np.linalg.norm(cp['center_of_mass_mm']) > 1e5:raise RuntimeError('UNBOUNDED_CENTER')
    V=complete.volume/(25.**3)
    center=np.asarray(complete.center_mass,dtype=float)/25+np.array([0.,0.,.16])
    I=complete.moment_inertia/(25.**5)
    second=(np.trace(I)/2.)*np.eye(3)-I+V*np.outer(center,center)
    objraw=np.asarray([V,*(V*center),second[0,0],second[1,1],second[2,2],second[1,2],second[0,2],second[0,1]])
    expected=np.asarray(material['raw_moments'],dtype=float)
    err=np.abs(objraw-expected)/np.maximum(1.,np.abs(expected))
    rec.update(obj_raw_moments=objraw.tolist(),cherchi_raw_moments=expected.tolist(),
          signed_relative_raw_moment_errors=err.tolist(),max_scaled_moment_difference=float(err.max()),
          moment_check_tolerance=1e-10,material_geometry_hash=material['geometry_hash'],
          mass_decrease_pct=float(100*(ip['mass_g_at_1200kg_m3']-cp['mass_g_at_1200kg_m3'])/ip['mass_g_at_1200kg_m3']))
    rec['passed']=bool(np.isfinite(err).all() and err.max()<1e-10)
    rec['status']='NUMERICAL_MOMENT_CHECK_PASSED' if rec['passed'] else 'NUMERICAL_MOMENT_MISMATCH'
except BaseException as ex:
    rec.update(status='FAILED',error=f'{type(ex).__name__}: {ex}',traceback=traceback.format_exc())
    raise
finally:
    rec['elapsed_s']=time.monotonic()-t
    a.out.write_text(json.dumps(rec,indent=2,allow_nan=False))
print(rec['status'],rec.get('max_scaled_moment_difference'),rec.get('mass_decrease_pct'))
