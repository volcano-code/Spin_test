#!/usr/bin/env python3
"""P11 W4: exploratory, UNAPPROVED F=M-minus-D partition via native Cherchi.

D is an analytic enclosed test sphere, NOT a W0-authorized removable material.
No CAD identity, tip, density, printable shell or optimization is claimed.
Native exit zero is insufficient without independent geometry and ten moments.
"""
from __future__ import annotations
import argparse,json,os,subprocess,time
from pathlib import Path
import numpy as np
import trimesh
from p10_cherchi_material_baseline import P9_SHA,sha

SCHEMA='W4P11CherchiTrialFDPartitionV1'
CENTER_YUP=(0.,1.3,0.)
RADIUS_SOURCE_UNITS=.5
MIN_GEOMETRIC_CLEARANCE=.15
TEN_MOMENT_RECONCILIATION_TOL=5e-7

def signed_winding(mesh,point):
    tri=np.asarray(mesh.triangles,dtype=float)-np.asarray(point,dtype=float)
    a,b,c=tri.transpose(1,0,2)
    ab=np.einsum('ij,ij->i',a,b)
    bc=np.einsum('ij,ij->i',b,c)
    ca=np.einsum('ij,ij->i',c,a)
    la=np.linalg.norm(a,axis=1);lb=np.linalg.norm(b,axis=1);lc=np.linalg.norm(c,axis=1)
    num=np.einsum('ij,ij->i',a,np.cross(b,c))
    return float(np.sum(2*np.arctan2(num,la*lb*lc+ab*lc+bc*la+ca*lb))/(4*np.pi))

def sphere_clearance(mesh,center=CENTER_YUP,radius=RADIUS_SOURCE_UNITS):
    """Point inside with 4pi signed solid angle and boundary separation in
    saved binary64 mesh. This is *not* a native exact-solid proof."""
    center=np.asarray(center,dtype=float)
    if center.shape!=(3,) or not np.isfinite(center).all() or radius<=0:
        raise ValueError('INVALID_TRIAL_CAVITY')
    tri=np.asarray(mesh.triangles)
    closest=trimesh.triangles.closest_point(tri,np.tile(center,(len(tri),1)))
    distance=float(np.min(np.linalg.norm(closest-center,axis=1)))
    winding=signed_winding(mesh,center)
    clearance=distance-radius
    if (not np.isfinite(distance) or
        not np.isclose(abs(winding),1.,atol=1e-7) or
        clearance<MIN_GEOMETRIC_CLEARANCE):
        raise ValueError('TRIAL_D_NOT_PROVEN_DEEPLY_CONTAINED_IN_NUMERIC_MESH')
    return dict(center_source_yup=center.tolist(),radius_source_units=radius,
        numeric_surface_winding_number=winding,
        minimum_point_to_outer_triangle_distance=distance,
        minimum_spherical_cavity_surface_clearance=clearance,
        independent_float_containment_pass=True,physical_units_W0_approved=False)

def triangle_moments(mesh):
    v=np.asarray(mesh.vertices,dtype=float)
    a,b,c=v[np.asarray(mesh.faces)].transpose((1,0,2))
    w=np.einsum('ij,ij->i',a,np.cross(b,c))/6.
    s=a+b+c
    m=w.sum();first=(w[:,None]*s/4).sum(axis=0)
    Q=np.empty((3,3))
    for x in range(3):
        for y in range(3):
            Q[x,y]=np.sum(w*(s[:,x]*s[:,y]+a[:,x]*a[:,y]+b[:,x]*b[:,y]+c[:,x]*c[:,y])/20)
    return np.array([m,*first,Q[0,0],Q[1,1],Q[2,2],Q[1,2],Q[0,2],Q[0,1]],dtype=float)

def edge_certificate(mesh):
    face=np.asarray(mesh.faces,dtype=int)
    if len(face)<4 or len(mesh.vertices)<4:
        raise ValueError('EMPTY_PARTITION_SURFACE')
    keys=np.sort(np.stack([face[:,[0,1]],face[:,[1,2]],face[:,[2,0]]],axis=1).reshape(-1,2),axis=1)
    _,count=np.unique(keys,axis=0,return_counts=True)
    ok=(bool(mesh.is_watertight) and bool(mesh.is_winding_consistent) and
        bool(mesh.is_volume) and np.all(count==2) and mesh.volume>0 and
        np.all(np.asarray(mesh.area_faces)>1e-14))
    return dict(contains_only_two_incident_edges=bool(np.all(count==2)),
        non_two_edges=int(np.sum(count!=2)),watertight=bool(mesh.is_watertight),
        is_volume=bool(mesh.is_volume),
        winding_consistent=bool(mesh.is_winding_consistent),
        signed_volume=float(mesh.volume),vertices=len(mesh.vertices),
        triangles=len(mesh.faces),numeric_surface_gate=bool(ok))

def trial_partition(material_obj,native_bin,out,*,timeout=120):
    material_obj,native_bin,out=map(Path,(material_obj,native_bin,out))
    if sha(material_obj)!=P9_SHA:
        raise ValueError('MATERIAL_MUST_BE_PINNED_REAL_CHERCHI_P9')
    if native_bin.name!='w4_cherchi_reference_native' or not native_bin.is_file():
        raise ValueError('CHERCHI_NATIVE_BINARY_REQUIRED_NO_CGAL')
    if timeout<=0 or timeout>240:raise ValueError('INVALID_TIMEOUT')
    parent=trimesh.load_mesh(material_obj,process=False)
    if not parent.is_volume or len(parent.faces)!=6662:
        raise ValueError('P10_PARENT_NOT_ADMITTED')
    guard=sphere_clearance(parent)
    D=trimesh.creation.icosphere(subdivisions=2,radius=RADIUS_SOURCE_UNITS)
    D.apply_translation(CENTER_YUP)
    if not D.is_volume:raise ValueError('ANALYTIC_TEST_D_NOT_SOLID')
    out.mkdir(parents=True,exist_ok=True)
    D_file=out/'p11-D-trial-sphere-unapproved.obj'
    D.export(D_file)
    d_reloaded=trimesh.load_mesh(D_file,process=False)
    if not d_reloaded.is_volume:raise ValueError('TEST_D_SAVED_ROUNDTRIP_INVALID')
    F_file=out/'p11-F-trial-cherchi-subtraction-unapproved.obj'
    receipt=out/'p11-experimental-FD-partition.json'
    record=dict(schema=SCHEMA,status='NATIVE_NOT_YET_CALLED',
        source_P9_sha256=sha(material_obj),
        operation='CHERCHI_NATIVE_SUBTRACTION_ONLY_NO_CGAL_FALLBACK',
        source_deviated_original_handle_x=.005,
        source_exact_original_CAD=False,original_M_obj=material_obj.name,
        D_trial_obj=D_file.name,D_trial_sha256=sha(D_file),
        F_trial_obj=F_file.name,
        F_D_is_provisional_experiment_only=True,
        W0_physical_case_tip_axis_density_scale_authorized=False,
        W0_fixed_F_removable_D_authorized=False,
        printability_wall_thickness_verified=False,
        SpinIt_optimization_performed=False,
        material_partition_approved=False,sphere_containment_preflight=guard)
    def save():
        receipt.write_text(json.dumps(record,indent=2,allow_nan=False)+'\n')
    save()
    cmd=[str(native_bin.resolve()),'subtraction',
         str(material_obj.resolve()),str(D_file.resolve()),str(F_file.resolve())]
    start=time.perf_counter()
    try:
        p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            text=True,timeout=timeout,check=False,
            env={**os.environ,'OMP_NUM_THREADS':'1'})
        record['native_exit_code']=p.returncode
        record['native_wall_seconds']=time.perf_counter()-start
        record['native_stdout_tail']=p.stdout[-4000:]
        record['native_stderr_tail']=p.stderr[-4000:]
        if p.returncode!=0 or not F_file.is_file():
            raise RuntimeError('CHERCHI_SUBTRACTION_FAILED')
        Fmesh=trimesh.load_mesh(F_file,process=False)
        fo=edge_certificate(Fmesh);de=edge_certificate(d_reloaded)
        record['F_surface']=fo;record['D_surface']=de
        if not fo['numeric_surface_gate'] or not de['numeric_surface_gate']:
            raise ValueError('CHERCHI_F_OR_D_NOT_CLOSED_NUMERIC_MATERIAL')
        from p2_self_intersection import check_nonincident_triangle_contacts
        # A hollow F may contain two disconnected *boundary surfaces* even
        # when its 3D filled material region is one connected solid.
        contacts=check_nonincident_triangle_contacts(Fmesh.vertices,Fmesh.faces,
                                                      max_witnesses=12)
        record['F_float_contact_gate']=contacts
        if contacts['witnesses'] or not contacts['exhaustive']:
            raise ValueError('CHERCHI_F_FLOAT_CONTACTS_OR_INCOMPLETE_AUDIT')
        r_M=triangle_moments(parent);r_F=triangle_moments(Fmesh)
        r_D=triangle_moments(d_reloaded)
        residual=r_M-r_F-r_D
        error=float(np.max(np.abs(residual)))
        record.update(raw_ten_order=['M','LX','LY','LZ','QXX','QYY','QZZ',
                                     'QYZ','QXZ','QXY'],
            raw_M=r_M.tolist(),raw_F=r_F.tolist(),raw_D=r_D.tolist(),
            raw_additivity_residual=residual.tolist(),
            max_abs_ten_moment_partition_error=error,
            F_sha256=sha(F_file))
        if error>TEN_MOMENT_RECONCILIATION_TOL:
            raise ValueError('REAL_CHERCHI_PARTITION_TEN_MOMENTS_FAIL')
        record['status']='EXPERIMENTAL_CHERCHI_FD_NUMERIC_ADDENDUM_PASS'
        record['material_partition_approved']=False
    except Exception as e:
        record['status']='FAILED_REAL_CHERCHI_FD_NUMERIC_PARTITION'
        record['failure']=f'{type(e).__name__}: {e}'
        save()
        raise
    save()
    return record

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--material',required=True,type=Path)
    p.add_argument('--native-bin',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--timeout',type=int,default=120)
    a=p.parse_args()
    r=trial_partition(a.material,a.native_bin,a.output,timeout=a.timeout)
    print(json.dumps({'status':r['status'],'F_surface':r['F_surface'],
                      'D_surface':r['D_surface'],
                      'max_abs_10_moment_error':r['max_abs_ten_moment_partition_error']},indent=2))
if __name__=='__main__':main()
