#!/usr/bin/env python3
"""W4 P14: Cherchi-only D/shaft junction perturbation study.

Source material is the immutable ACTUAL failed P13 native artifact, not an
invented mesh. All offsets are in unapproved reconstruction coordinates.
Native exit 0, visual watertightness, and a Boolean result alone do NOT
constitute physical F/D or Spin-It Faster optimization acceptance.
"""
from __future__ import annotations
import argparse,hashlib,json,math,os,subprocess,time
from pathlib import Path
import numpy as np
import trimesh

SCHEMA='W4P14CherchiShaftCavityJunctionStudyV1'
SOURCE_RUN=39446111126
PIN={
    'D':('p13-d-reference.obj','2fee98a34bf26cc536eb424f1013520c87abed05a9af2e439f934e7e5acba5cd'),
    'shaft':('p13-shaft-reference.obj','65d794715d580ebab231716669e25d79fea7f353da35c96d4a54f1779dc7e9f0'),
    'outer':('p13-outer-cherchi-union.obj','f3ac662e0d3c175b30a2cbcc6f1efd04785ad9d599d5ca666d7ea44b39718db5'),
    'failed':('p13-D-shaft-excluded.obj','855d7819f7ccbbb2cb05ccf9c18ab7ac6a1e6eca1456dd231967c3f9a48e30c0'),
    'failure_receipt':('p13-D-shaft-excluded.native-call.json','8050b87a1cc0a279f152f1f95554518126d7b3eb27119553ba529ff5d94c00ea')}
CASES=(
 ('baseline',0,0,0,1),
 ('rotate_1p5',0,0,1.5,1),
 ('rotate_7p0',0,0,7,1),
 ('translate_x_002',.002,0,0,1),
 ('translate_x_008',.008,0,0,1),
 ('translate_y_008',0,.008,0,1),
 ('translate_xy_012_m008',.012,-.008,0,1),
 ('translate_x_020',.02,0,0,1),
 ('translate_x_012_rotate_7',.012,0,7,1),
 ('radius_099',0,0,0,.99),
 ('radius_101',0,0,0,1.01))
CENTER=np.array([0.,0.,.67])
THIN_AREA=1e-14
TOL_TEN=5e-7

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_pinned(directory):
    folder=Path(directory)
    result={}
    for key,(name,expected) in PIN.items():
        path=folder/name
        if not path.is_file() or digest(path)!=expected:
            raise ValueError('PINNED_REAL_P13_ARCHIVE_SHA_MISMATCH_'+key)
        result[key]=path
    receipt=json.loads(result['failure_receipt'].read_text())
    if receipt.get('exit')!=0 or receipt.get('sha256')!=PIN['failed'][1]:
        raise ValueError('REAL_P13_NATIVE_EXIT_AND_OUTPUT_BINDING_FAILED')
    return result

def geometry(path):
    mesh=trimesh.load_mesh(path,process=False)
    v=np.asarray(mesh.vertices,dtype=float);f=np.asarray(mesh.faces,dtype=int)
    if not len(f) or f.shape[1:]!=(3,) or not np.isfinite(v).all():
        raise ValueError('MALFORMED_CHERCHI_NATIVE_OBJ')
    edges=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1)
    unique,n=np.unique(edges,axis=0,return_counts=True)
    bad=np.where(n!=2)[0];areas=np.asarray(mesh.area_faces)
    out=dict(vertices=len(v),triangles=len(f),sha256=digest(path),
             non_two_incident_edges=int(len(bad)),
             edge_incidence_histogram={str(int(k)):int(c) for k,c in
                 zip(*np.unique(n,return_counts=True))},
             low_area_triangles=int(np.sum(areas<=THIN_AREA)),
             min_triangle_area=float(areas.min()),
             is_volume=bool(mesh.is_volume),watertight=bool(mesh.is_watertight),
             winding_consistent=bool(mesh.is_winding_consistent),
             indexed_components=len(mesh.split(only_watertight=False)),
             signed_tetrahedral_integral=float(mesh.volume))
    if len(bad):
        midpoint=(v[unique[bad,0]]+v[unique[bad,1]])/2
        rad=np.linalg.norm(midpoint[:,:2],axis=1)
        out['nonmanifold_locus']=dict(
            radial_min=float(rad.min()),radial_max=float(rad.max()),
            max_distance_to_shaft_radius=float(np.max(np.abs(rad-.06))),
            height_min=float(midpoint[:,2].min()),
            height_max=float(midpoint[:,2].max()),
            first_edges=[dict(vertex_coordinates=v[unique[i]].tolist(),
                              incidence=int(n[i])) for i in bad[:10]])
    out['strict_numeric_preflight']=bool(
        len(bad)==0 and out['is_volume'] and out['watertight'] and
        out['winding_consistent'] and out['low_area_triangles']==0 and
        out['indexed_components']>=1)
    if out['strict_numeric_preflight']:
        from p2_self_intersection import check_nonincident_triangle_contacts
        sat=check_nonincident_triangle_contacts(v,f,max_witnesses=12)
        out['conservative_nonincident_SAT']=sat
        out['strict_numeric_preflight']=bool(sat['exhaustive'] and not sat['witnesses'])
    return out

def variant(mesh,config):
    name,dx,dy,angle,radius=config
    dx,dy,angle,radius=map(float,(dx,dy,angle,radius))
    if not all(math.isfinite(x) for x in (dx,dy,angle,radius)) or \
       math.hypot(dx,dy)>.030 or abs(angle)>15 or not .98<=radius<=1.02:
        raise ValueError('PROPOSED_D_CHANGE_OUT_OF_BOUNDS')
    rad=math.radians(angle)
    rot=np.array([[math.cos(rad),-math.sin(rad),0],
                  [math.sin(rad),math.cos(rad),0],[0,0,1]],dtype=float)
    v=np.asarray(mesh.vertices,dtype=float)
    vv=(v-CENTER)@rot.T*radius+CENTER+[dx,dy,0]
    out=trimesh.Trimesh(vertices=vv,faces=np.asarray(mesh.faces),process=False)
    if not out.is_volume or abs(out.volume/mesh.volume-radius**3)>2e-11:
        raise ValueError('D_VARIANT_VOLUME_OR_TOPOLOGY_CHANGED')
    info=dict(name=name,dx=dx,dy=dy,angle_degrees=angle,radius_multiplier=radius,
              max_vertex_displacement=float(np.linalg.norm(vv-v,axis=1).max()),
              physical_scale_NOT_W0_authorized=True)
    return out,info

def write_obj(path,mesh):
    with Path(path).open('w',encoding='ascii',newline='\n') as f:
        f.write('# P14 D hypothesis; not W0-authorized or optimized\n')
        for xyz in mesh.vertices:
            f.write('v '+' '.join(format(float(x),'.17g') for x in xyz)+'\n')
        for a,b,c in mesh.faces:f.write(f'f {a+1} {b+1} {c+1}\n')

def raw_ten(mesh):
    v=np.asarray(mesh.vertices);a,b,c=v[np.asarray(mesh.faces)].transpose((1,0,2))
    w=np.einsum('ij,ij->i',a,np.cross(b,c))/6.
    s=a+b+c;L=(w[:,None]*s/4).sum(axis=0)
    Q=np.empty((3,3))
    for i in range(3):
        for j in range(3):
            Q[i,j]=(w*(s[:,i]*s[:,j]+a[:,i]*a[:,j]+b[:,i]*b[:,j]+c[:,i]*c[:,j])/20).sum()
    return np.array([w.sum(),*L,Q[0,0],Q[1,1],Q[2,2],Q[1,2],Q[0,2],Q[0,1]],dtype=float)

def winding(mesh,point):
    t=np.asarray(mesh.triangles)-np.asarray(point,dtype=float)
    a,b,c=t.transpose((1,0,2))
    la=np.linalg.norm(a,axis=1);lb=np.linalg.norm(b,axis=1);lc=np.linalg.norm(c,axis=1)
    numerator=np.einsum('ij,ij->i',a,np.cross(b,c))
    denominator=(la*lb*lc+np.einsum('ij,ij->i',a,b)*lc+
                 np.einsum('ij,ij->i',b,c)*la+
                 np.einsum('ij,ij->i',c,a)*lb)
    return float(np.sum(2*np.arctan2(numerator,denominator))/(4*np.pi))

def native_call(executable,op,operands,out,timeout):
    args=[str(Path(executable).resolve()),op,*[str(Path(x).resolve()) for x in operands],
          str(Path(out).resolve())]
    tic=time.perf_counter()
    try:
        p=subprocess.run(args,capture_output=True,text=True,timeout=timeout,check=False,
                         env={**os.environ,'OMP_NUM_THREADS':'1'})
        info=dict(op=op,returncode=p.returncode,wall_seconds=time.perf_counter()-tic,
                  stdout=p.stdout[-5000:],stderr=p.stderr[-5000:],
                  source_sha256=[digest(x) for x in operands],output_exists=Path(out).is_file())
    except subprocess.TimeoutExpired:
        info=dict(op=op,returncode=None,output_exists=False,timeout_s=timeout,
                  wall_seconds=time.perf_counter()-tic)
    if info['output_exists']:info['output_sha256']=digest(out)
    Path(str(out)+'.native.json').write_text(json.dumps(info,indent=2)+'\n')
    return info

def study(input_dir,native_binary,source_dir,output,timeout=90):
    if not 0<timeout<=120:raise ValueError('EXCESSIVE_NATIVE_TIMEOUT')
    inp=load_pinned(input_dir)
    from p7_cherchi_native_union import native_identity
    ident=native_identity(native_binary,source_dir)
    root=Path(output);root.mkdir(parents=True,exist_ok=True)
    base=geometry(inp['failed'])
    if base['non_two_incident_edges']!=162 or base['low_area_triangles']!=8:
        raise ValueError('HISTORICAL_FAILURE_SIGNATURE_CHANGED')
    initial=trimesh.load_mesh(inp['D'],process=False)
    outer=trimesh.load_mesh(inp['outer'],process=False)
    report=dict(schema=SCHEMA,old_native_run=SOURCE_RUN,source_sha256={k:digest(v) for k,v in inp.items()},
        current_native=ident,baseline=base,original_input_modified=False,
        W0_approved=False,original_author_CAD_proven=False,
        printable_material_certified=False,
        real_SpinIt_Faster_optimization_complete=False,
        status='NATIVE_TRIALS_RUNNING',cases=[],admissible_candidate=None)
    receipt=root/'p14-junction-native-study.json'
    def save():receipt.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    save()
    for spec in CASES:
        proposed,entry=variant(initial,spec)
        case=root/entry['name'];case.mkdir(exist_ok=True)
        dinput=case/'hypothesis_D.obj';write_obj(dinput,proposed)
        entry['D_input_sha256']=digest(dinput)
        center=CENTER+np.array([entry['dx'],entry['dy'],0])
        triangles=np.asarray(outer.triangles)
        closest=trimesh.triangles.closest_point(triangles,np.tile(center,(len(triangles),1)))
        margin=float(np.linalg.norm(closest-center,axis=1).min()-.2*entry['radius_multiplier'])
        entry['numerical_outer_surface_clearance_lower_bound']=margin
        if margin<.08:
            entry['status']='REJECTED_CAVITY_OUTER_CLEARANCE'
            report['cases'].append(entry);save();continue
        dmesh=case/'D_minus_shaft_cherchi.obj'
        dcall=native_call(native_binary,'subtraction',[dinput,inp['shaft']],dmesh,timeout)
        entry['D_native']=dcall
        if dcall['returncode']!=0 or not dcall['output_exists']:
            entry['status']='NATIVE_D_NOT_PRODUCED'
            report['cases'].append(entry);save();continue
        Dgeom=geometry(dmesh);entry['D_geometry']=Dgeom
        if not Dgeom['strict_numeric_preflight']:
            entry['status']='REJECTED_D_NONMANIFOLD_OR_CONTACT'
            report['cases'].append(entry);save();continue
        dbody=trimesh.load_mesh(dmesh,process=False)
        entry['rod_core_D_winding']=winding(dbody,(.03,0,.67))
        entry['off_axis_D_winding']=winding(dbody,(.12,0,.67))
        if not (abs(entry['rod_core_D_winding'])<.1 and
                abs(entry['off_axis_D_winding']-1)<.1 and
                0<dbody.volume<proposed.volume):
            entry['status']='REJECTED_ROD_PROTECTION_OR_VOLUMES'
            report['cases'].append(entry);save();continue
        fmesh=case/'F_retained_cherchi.obj'
        fcall=native_call(native_binary,'subtraction',[inp['outer'],dmesh],fmesh,timeout)
        entry['F_native']=fcall
        if fcall['returncode']!=0 or not fcall['output_exists']:
            entry['status']='NATIVE_F_NOT_PRODUCED'
            report['cases'].append(entry);save();continue
        Fgeom=geometry(fmesh);entry['F_geometry']=Fgeom
        if not Fgeom['strict_numeric_preflight']:
            entry['status']='REJECTED_F_NONMANIFOLD_OR_CONTACT'
            report['cases'].append(entry);save();continue
        retained=trimesh.load_mesh(fmesh,process=False)
        entry['rod_core_F_winding']=winding(retained,(.03,0,.67))
        err=raw_ten(outer)-raw_ten(retained)-raw_ten(dbody)
        entry['ten_max_abs_additivity_error']=float(np.max(abs(err)))
        if abs(entry['rod_core_F_winding']-1)>.1 or entry['ten_max_abs_additivity_error']>TOL_TEN:
            entry['status']='REJECTED_MATERIAL_IDENTITY'
        else:
            entry['status']='CHERCHI_TWO_BOOLEANS_NUMERIC_PRECHECK_NOT_W0_APPROVED'
            candidate=dict(case=entry['name'],F_sha256=digest(fmesh),D_sha256=digest(dmesh),
              displaced_geometry=True,ten_max_abs_error=entry['ten_max_abs_additivity_error'],
              physical_authorization=False)
            if report['admissible_candidate'] is None:
                report['admissible_candidate']=candidate
        report['cases'].append(entry);save()
    report['status']='NUMERICAL_RESEARCH_CANDIDATE_FOUND_NOT_APPROVED' if \
         report['admissible_candidate'] is not None else 'COMPLETED_NEGATIVE_NATIVE_JUNCTION_STUDY'
    report['real_D_native_trials']=sum('D_native' in x for x in report['cases'])
    save()
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for f in ('input-dir','native-bin','native-source','output'):p.add_argument('--'+f,required=True,type=Path)
    p.add_argument('--timeout',type=int,default=90)
    a=p.parse_args()
    j=study(a.input_dir,a.native_bin,a.native_source,a.output,a.timeout)
    print(json.dumps(dict(status=j['status'],real_D_native_trials=j['real_D_native_trials'],
       old_bad_edges=j['baseline']['non_two_incident_edges'],
       accepted=j['admissible_candidate'],
       cases=[dict(name=x['name'],status=x['status'],
          new_bad_edges=x.get('D_geometry',{}).get('non_two_incident_edges'))
        for x in j['cases']]),indent=2))
    if j['admissible_candidate'] is None:raise SystemExit(2)
