#!/usr/bin/env python3
"""W4 P12 exploratory Teapot physical preflight; NEVER a W0 admission.

Uses saved REAL Cherchi P9 M and P11 F/D surfaces, with SHA256 source pins.
W0 MomentContractV1 ordinary raw ten-moment convention, no doubled Q cross
terms. Physical scale and density are declared *hypotheses*, not inferred.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh

SCHEMA = 'W4P12PhysicalCaseProposalV1'
SHA = {
    'M': '154cdfc9ec94b6885a95e596c36ac1382dd2d36ed99e19d0b36c2b9de80b6df4',
    'F': '22593c5ab3b5f6ee786f2d17ce15f3beae16fcb09589dce2314d1615b3f115ba',
    'D': '4cc61b54939fe9c9acdfe9e956af24f2a411d6016acd83fd32d46722749a99b9',
    'P11': '798ee3092487a4797a427e9a36dad11791f21835b897235c25f4b6518aee404f',
}
MOMENT_ORDER = ['M','LX','LY','LZ','QXX','QYY','QZZ','QYZ','QXZ','QXY']
YUP_TO_ZUP = np.array([[1.,0.,0.],[0.,0.,-1.],[0.,1.,0.]])
DENY_FIELDS = ('W0_teapot_case_authorized', 'W0_design_F_D_authorized',
               'real_tip_or_shaft_merged', 'manufacturing_pass',
               'actual_Cherchi_Faster_optimization_complete',
               'official_before_after_MuJoCo_complete')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def raw_ten(mesh):
    tri=np.asarray(mesh.vertices)[np.asarray(mesh.faces,dtype=np.int64)]
    a,b,c=tri.transpose((1,0,2))
    w=np.einsum('ij,ij->i',a,np.cross(b,c))/6.
    s=a+b+c
    m=float(w.sum());L=(w[:,None]*s/4.).sum(axis=0)
    Q=np.zeros((3,3),dtype=np.float64)
    for i in range(3):
        for j in range(3):
            Q[i,j]=np.sum(w*(s[:,i]*s[:,j]+a[:,i]*a[:,j]+b[:,i]*b[:,j]+c[:,i]*c[:,j])/20.)
    return np.array([m,*L,Q[0,0],Q[1,1],Q[2,2],Q[1,2],Q[0,2],Q[0,1]])


def ten_to_matrices(r):
    v=np.asarray(r,dtype=np.float64)
    if v.shape!=(10,) or not np.isfinite(v).all() or v[0]<=0:
        raise ValueError('MOMENT_VECTOR_INVALID')
    Q=np.array([[v[4],v[9],v[8]],[v[9],v[5],v[7]],[v[8],v[7],v[6]]])
    return float(v[0]),v[1:4],Q


def transform_ten_physical(raw,height_scale,density):
    if not (np.isfinite(height_scale) and height_scale>0 and np.isfinite(density) and density>0):
        raise ValueError('PHYSICAL_SCALE_DENSITY_INVALID')
    M,L,Q=ten_to_matrices(raw)
    m=density*height_scale**3*M
    first=density*height_scale**4*(YUP_TO_ZUP@L)
    q=density*height_scale**5*(YUP_TO_ZUP@Q@YUP_TO_ZUP.T)
    return m,first,q


def si_properties(raw,scale,density):
    m,L,Q=transform_ten_physical(raw,scale,density)
    com=L/m
    I0=np.trace(Q)*np.eye(3)-Q
    Icom=I0-m*((com@com)*np.eye(3)-np.outer(com,com))
    Icom=(Icom+Icom.T)/2.
    eig,evec=np.linalg.eigh(Icom)
    if eig.min()<=0 or 2*max(eig)>=sum(eig):
        raise ValueError('PHYSICAL_INERTIA_TENSOR_INVALID')
    z=np.array([0.,0.,1.])
    angle=float(np.degrees(np.arccos(np.clip(np.max(np.abs(evec.T@z)),-1,1))))
    return dict(mass_kg=float(m),center_of_mass_zup_m=com.tolist(),
        raw_first_moment_SI=L.tolist(),raw_second_moment_SI=Q.tolist(),
        inertia_origin_kg_m2=I0.tolist(),inertia_com_kg_m2=Icom.tolist(),
        principal_inertia_kg_m2=eig.tolist(),
        nearest_principal_axis_angle_to_trial_z_deg=angle,
        inertia_about_trial_z_at_com_kg_m2=float(z@Icom@z))


def _pins(paths,report):
    for k,file in {**paths,'P11':report}.items():
        if digest(file)!=SHA[k]:
            raise ValueError(f'FROZEN_REAL_CHERCHI_{k}_SHA256_MISMATCH')


def _check_report(report):
    evidence=json.loads(Path(report).read_text())
    if (evidence.get('status')!='EXPERIMENTAL_CHERCHI_FD_NUMERIC_ADDENDUM_PASS' or
        evidence.get('source_P9_sha256')!=SHA['M'] or
        evidence.get('F_sha256')!=SHA['F'] or
        evidence.get('D_trial_sha256')!=SHA['D'] or
        evidence.get('operation')!='CHERCHI_NATIVE_SUBTRACTION_ONLY_NO_CGAL_FALLBACK' or
        evidence.get('native_exit_code')!=0 or
        evidence.get('max_abs_ten_moment_partition_error',float('inf'))>5e-7 or
        evidence.get('material_partition_approved') is not False or
        evidence.get('W0_fixed_F_removable_D_authorized') is not False):
        raise ValueError('P11_ORIGINAL_NATIVE_EVIDENCE_INVALID_OR_PROMOTED')
    return evidence


def _test_case(case):
    if case.get('schema')!=SCHEMA or case.get('admission')!='EXPLORATORY_NOT_W0_APPROVED':
        raise ValueError('EXPLORATORY_CASE_SCHEMA_OR_ADMISSION_INVALID')
    if any(case.get(field) is not False for field in DENY_FIELDS):
        raise ValueError('FORBIDDEN_PREMATURE_PHYSICAL_AUTHORIZATION')
    if case.get('coordinate_transform')!=YUP_TO_ZUP.astype(int).tolist():
        raise ValueError('WRONG_YUP_ZUP_FRAME')
    physical=case.get('diagnostic_assumptions',{})
    if physical.get('tip_contact')!='VIRTUAL_NOT_MATERIALIZED' or physical.get('spin_axis')!=[0,0,1]:
        raise ValueError('TIP_OR_AXIS_NOT_EXPLICIT_PROVISIONAL')
    h=float(physical['height_m']);density=float(physical['uniform_density_kg_m3'])
    mass=float(physical['previous_demo_mass_kg'])
    if not np.isfinite(h) or h<=0 or not np.isfinite(density) or density<=0 or mass<=0:
        raise ValueError('PHYSICAL_ASSUMPTIONS_INVALID')
    return h,density,mass


def evaluate(files,report,case_path,output):
    paths={k:Path(v) for k,v in files.items()}
    _pins(paths,report)
    upstream=_check_report(report)
    case=json.loads(Path(case_path).read_text())
    h,density,previous_mass=_test_case(case)
    meshes={k:trimesh.load_mesh(path,process=False) for k,path in paths.items()}
    for k,m in meshes.items():
        if not (m.is_volume and m.is_watertight and m.is_winding_consistent):
            raise ValueError(f'MATERIAL_{k}_RELOAD_INVALID')
    r={k:raw_ten(m) for k,m in meshes.items()}
    for k,field in [('M','raw_M'),('F','raw_F'),('D','raw_D')]:
        if max(abs(r[k]-np.asarray(upstream[field])))>1e-9:
            raise ValueError(f'MATERIAL_{k}_TEN_MOMENT_MISMATCH')
    residual=r['M']-r['F']-r['D']
    raw_err=float(np.max(np.abs(residual)))
    if raw_err>1e-9:raise ValueError('REAL_F_D_RAW_TEN_MOMENT_ADDITIVITY_FAILED')
    model_height=float(np.ptp(meshes['M'].bounds[:,1]))
    if model_height<=0:raise ValueError('MODEL_VERTICAL_SPAN_INVALID')
    scale=h/model_height
    props={k:si_properties(r[k],scale,density) for k in r}
    transformed={k:transform_ten_physical(r[k],scale,density) for k in r}
    si_residual=[transformed['M'][i]-transformed['F'][i]-transformed['D'][i] for i in range(3)]
    si_error=max(abs(si_residual[0]),float(np.max(np.abs(si_residual[1]))),
                 float(np.max(np.abs(si_residual[2]))))
    if si_error>1e-9:raise ValueError('SI_PHYSICAL_MOMENT_ADDITIVITY_FAILED')
    ideal_density_for_previous_mass=previous_mass/(meshes['M'].volume*scale**3)
    metric_clearance=float(upstream['sphere_containment_preflight']['minimum_spherical_cavity_surface_clearance'])*scale
    baseline=props['M'];removed=props['F']
    effects=dict(actual_cavity_volume_fraction=float(meshes['D'].volume/meshes['M'].volume),
        mass_reduction_kg=baseline['mass_kg']-removed['mass_kg'],
        mass_reduction_fraction=1-removed['mass_kg']/baseline['mass_kg'],
        COM_height_reduction_m=baseline['center_of_mass_zup_m'][2]-removed['center_of_mass_zup_m'][2],
        trial_z_spin_inertia_difference_kg_m2=removed['inertia_about_trial_z_at_com_kg_m2']-
            baseline['inertia_about_trial_z_at_com_kg_m2'],
        real_optimization_delta=False,design_optimization_performed=False)
    out=dict(schema='W4P12RealCherchiPhysicalPreflightV1',status='DIAGNOSTIC_PHYSICAL_CASE_ONLY',
        material_provenance='P9_ORIGINAL_ARCHIVED_REAL_CHERCHI_PLUS_P11_NEW_REAL_SUBTRACTION',
        experiment_Cherchi_original_author_CAD=False,
        W0_contract_approval=False,W2_teacher_admitted=False,
        actual_optimized_geometry_available=False,
        previous_MuJoCo_demo_physically_comparable=False,
        source_file_sha256={**{k:digest(v) for k,v in paths.items()},'P11':digest(report),'case':digest(case_path)},
        source_raw_moment_order=MOMENT_ORDER,
        body_height_source_units=model_height,physical_height_assumed_m=h,
        scale_m_per_source_unit=scale,assumed_material_density_kg_m3=density,
        material=props,raw_additivity_max_abs=raw_err,SI_additivity_max_abs=si_error,
        minimum_inner_cavity_to_original_outer_surface_lower_bound_m=metric_clearance,
        material_relative_effects=effects,
        previous_demo_mass_kg=previous_mass,
        required_effective_density_for_previous_demo_mass_kg_m3=ideal_density_for_previous_mass,
        assumed_solid_mass_divided_by_old_demo_mass=baseline['mass_kg']/previous_mass,
        spin_tip_contact_status='VIRTUAL_NOT_REAL_TIP',
        spin_axis_status='PROVISIONAL_UNAPPROVED',
        printability_wall_thickness_status='NOT_CERTIFIED_CONSERVATIVE_CAVITY_CLEARANCE_ONLY',
        shaft_outer_shell_F_status='UNAPPROVED_SPHERICAL_TRIAL_ONLY',
        W0_MomentContractV1_handoff_state='PROPOSED_CASE_NEEDS_W0_SIGNOFF',
        P12_final_SpinIt_Faster_optimization_performed=False)
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
    return out


def main():
    ap=argparse.ArgumentParser()
    for k in ('m','f','d','p11-report','case','output'):
        ap.add_argument('--'+k,required=True,type=Path)
    a=ap.parse_args()
    result=evaluate({'M':a.m,'F':a.f,'D':a.d},a.p11_report,a.case,a.output)
    print(json.dumps({'status':result['status'],
        'material_mass_kg':{k:v['mass_kg'] for k,v in result['material'].items()},
        'raw_ten_error':result['raw_additivity_max_abs'],
        'SI_error':result['SI_additivity_max_abs'],
        'W0_approved':result['W0_contract_approval']},indent=2))

if __name__=='__main__':main()
