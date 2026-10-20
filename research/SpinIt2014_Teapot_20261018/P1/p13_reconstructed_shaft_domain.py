#!/usr/bin/env python3
"""W4 P13: reference-aligned physical spindle *proposal* and Cherchi-only F/D smoke.

The unmodified archived real P9/P11 material is the ONLY Teapot input. Reuse
geometry and parameter values from existing, frozen reconstructed Teapot
experiment code (not original author's paper CAD). There is NO W0 signoff,
no proof of global manufacturability and no optimization or MuJoCo claim.

P13 addresses a substantive P11 incompatibility: the proposed P11 interior
sphere overlaps the fixed center shaft, so D must be replaced with D-minus-shaft
and F must be generated from the whole combined material, not just assumed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time
import numpy as np
import trimesh
from p12_physical_case import SHA, raw_ten, transform_ten_physical

SCHEMA = 'W4P13ReferenceSpindleDesignDomainV1'
UPSTREAM_TEAPOT_BLOB='a80974d062c7fef2fe1852df677477e82a5adb54'
UPSTREAM_PREPARE_BLOB='fde050a83b2e39b9a92dab5e46616e1f37a9f4ff'
REF_SCALE=.4
REF_TRANSLATION_Z=.15
METERS_PER_REF_MODEL_UNIT=.025
DENSITY_KG_M3=1200.
R_YUP_TO_ZUP=np.array([[1.,0.,0.],[0.,0.,-1.],[0.,1.,0.]])
# Frozen from experiments/teapot_spin2014/teapot.py::shaft_mesh (read-only).
SHAFT_RADIUS=.06
SHAFT_TOP_Z=1.71
SHIFT_PROOF=np.array([.03,0.,.67])  # interior to BOTH rod and P11 trial sphere
UNAPPROVED = ('W0_physical_case_admitted','W0_spindle_approved',
              'W0_fixed_F_design_D_admitted','printability_certified',
              'faster_optimization_performed','real_optimized_MuJoCo_validated')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_obj(path,mesh,comment):
    verts=np.asarray(mesh.vertices,dtype=np.float64)
    faces=np.asarray(mesh.faces,dtype=np.int64)
    with Path(path).open('w',encoding='utf-8',newline='\n') as stream:
        stream.write('# W4 P13 UNAPPROVED RECONSTRUCTION: '+comment+'\n')
        for x,y,z in verts:
            stream.write(f'v {x:.17g} {y:.17g} {z:.17g}\n')
        for a,b,c in faces:
            stream.write(f'f {a+1} {b+1} {c+1}\n')


def reference_transform(mesh):
    # This reproduces the existing explicit source x,y,z -> scaled x,-z,y+0.15.
    vertices=REF_SCALE*(np.asarray(mesh.vertices)@R_YUP_TO_ZUP.T)
    vertices+=np.array([0.,0.,REF_TRANSLATION_Z])
    result=trimesh.Trimesh(vertices=vertices,faces=np.asarray(mesh.faces),process=False)
    if not result.is_volume:raise ValueError('REFERENCE_FRAME_TRANSFORM_NOT_VOLUME')
    return result


def round_spindle():
    # EXACT profile/slices from frozen reconstructed 2014 Teapot shaft_mesh.
    theta=np.linspace(-np.pi/2.,0.,7)
    profile=[(0.,0.)]+[(float(.025*np.cos(t)),float(.025+.025*np.sin(t))) for t in theta[1:]]
    profile += [(.06,.13),(.06,1.71),(0.,1.71)]
    solid=trimesh.creation.revolve(np.asarray(profile),sections=32)
    if solid.volume<0:solid.invert()
    if not solid.is_volume or abs(solid.bounds[0,2])>1e-13:
        raise ValueError('RECONSTRUCTED_SHAFT_NOT_CLOSED_OR_TIP_NOT_ZERO')
    if len(solid.faces)!=512 or len(solid.vertices)!=258:
        raise ValueError('PINNED_REFERENCE_SHAFT_DISCRETIZATION_CHANGED')
    return solid


def closed_metadata(mesh):
    if not mesh.is_volume or not mesh.is_watertight or not mesh.is_winding_consistent:
        raise ValueError('SAVED_MESH_NOT_ORIENTED_VOLUME')
    return dict(vertices=len(mesh.vertices),faces=len(mesh.faces),
                signed_volume=float(mesh.volume),watertight=True,
                winding_consistent=True,
                bounding_box_model_units=np.asarray(mesh.bounds).tolist())


def solid_angle_winding(mesh,point):
    tri=np.asarray(mesh.triangles,dtype=np.float64)-np.asarray(point,dtype=np.float64)
    a,b,c=tri.transpose(1,0,2)
    norm=np.linalg.norm(tri,axis=2)
    ab=np.einsum('ij,ij->i',a,b)
    bc=np.einsum('ij,ij->i',b,c)
    ca=np.einsum('ij,ij->i',c,a)
    numerator=np.einsum('ij,ij->i',a,np.cross(b,c))
    denominator=(norm[:,0]*norm[:,1]*norm[:,2]+ab*norm[:,2]+
                 bc*norm[:,0]+ca*norm[:,1])
    return float(np.sum(2*np.arctan2(numerator,denominator))/(4*np.pi))


def native_raw_si(mesh):
    # p12_physical_case implements the frozen W0 undoubled cross moments.
    # Here mesh is already in the reference normalized 2014 reconstruction.
    r=raw_ten(mesh)
    return np.array([r[0]*DENSITY_KG_M3*METERS_PER_REF_MODEL_UNIT**3,
                     *r[1:4]*DENSITY_KG_M3*METERS_PER_REF_MODEL_UNIT**4,
                     *r[4:]*DENSITY_KG_M3*METERS_PER_REF_MODEL_UNIT**5])


def prepare(paths,report,out):
    paths={k:Path(x) for k,x in paths.items()}
    for k in ('M','F','D'):
        if digest(paths[k])!=SHA[k]:raise ValueError(f'FROZEN_CHERCHI_{k}_HASH_MISMATCH')
    if digest(report)!=SHA['P11']:raise ValueError('FROZEN_CHERCHI_P11_REPORT_HASH_MISMATCH')
    source_report=json.loads(Path(report).read_text())
    if (source_report.get('status')!='EXPERIMENTAL_CHERCHI_FD_NUMERIC_ADDENDUM_PASS' or
        source_report.get('material_partition_approved') is not False or
        source_report.get('W0_fixed_F_removable_D_authorized') is not False):
        raise ValueError('P11_UNAPPROVED_NATIVE_PROVENANCE_MISMATCH')
    originals={k:trimesh.load_mesh(p,process=False) for k,p in paths.items()}
    prepared={k:reference_transform(m) for k,m in originals.items()}
    rod=round_spindle()
    for k in originals:
        # Raw ten inputs and physical outputs are evaluated independently.
        before=raw_ten(originals[k])
        after=native_raw_si(prepared[k])
        # Independent direct source-to-SI affine moments, including offset.
        in_M,in_L,src_Q=before[0],before[1:4],np.array([
            [before[4],before[9],before[8]],
            [before[9],before[5],before[7]],
            [before[8],before[7],before[6]]])
        A=REF_SCALE*R_YUP_TO_ZUP; t=np.array([0,0,REF_TRANSLATION_Z])
        jac=abs(np.linalg.det(A))
        directM=in_M*jac
        directL=jac*(A@in_L+in_M*t)
        at=A@in_L
        directQ=jac*(A@src_Q@A.T+np.outer(at,t)+np.outer(t,at)+in_M*np.outer(t,t))
        expected=np.array([directM,*directL,directQ[0,0],directQ[1,1],directQ[2,2],directQ[1,2],directQ[0,2],directQ[0,1]])
        factors=np.array([DENSITY_KG_M3*METERS_PER_REF_MODEL_UNIT**i for i in [3,4,4,4,5,5,5,5,5,5]])
        if np.max(np.abs(after-expected*factors))>1e-11:
            raise ValueError(f'W0_AFFINE_PHYSICAL_MOMENT_DISAGREEMENT_{k}')
    raw_residual=raw_ten(prepared['M'])-raw_ten(prepared['F'])-raw_ten(prepared['D'])
    residual=max(abs(raw_residual))
    if residual>5e-9:raise ValueError('P13_AFFINE_MFD_PARTITION_MISMATCH')
    witness=SHIFT_PROOF
    rod_winding=solid_angle_winding(rod,witness)
    d_winding=solid_angle_winding(prepared['D'],witness)
    if not (abs(rod_winding)>1-1e-6 and abs(d_winding)>1-1e-6):
        raise ValueError('P11_D_SHAFT_OVERLAP_WITNESS_NOT_CONFIRMED')
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    inputs={}
    for k,m in {**prepared,'shaft':rod}.items():
        file=out/('p13-'+k.lower()+'-reference.obj')
        save_obj(file,m,f'{k} source-provenance, reference-frame proposal')
        reloaded=trimesh.load_mesh(file,process=False)
        if not reloaded.is_volume or len(reloaded.faces)!=len(m.faces):
            raise ValueError('P13_SAVED_OBJ_NOT_CLOSED')
        inputs[k]=dict(file=file.name,sha256=digest(file),**closed_metadata(reloaded),
                       proposed_mass_kg=float(native_raw_si(reloaded)[0]))
    massM=float(native_raw_si(prepared['M'])[0]);massRod=float(native_raw_si(rod)[0])
    receipt=dict(schema=SCHEMA,status='CONFLICT_IDENTIFIED_CANDIDATES_STAGED_NATIVE_UNION_NOT_RUN',
        source_real_Cherchi_M_F_D_sha256={k:digest(v) for k,v in paths.items()},
        previous_real_P11_report_sha256=digest(report),
        inherited_Cherchi_original_author_CAD_certified=False,
        frozen_reconstruction_code_git_blobs=dict(teapot=UPSTREAM_TEAPOT_BLOB,prepare=UPSTREAM_PREPARE_BLOB),
        frame=dict(R_original_YUP_to_reference_ZUP=R_YUP_TO_ZUP.tolist(),
                   scale_original_to_reconstructed=REF_SCALE,
                   z_translation_reconstructed=REF_TRANSLATION_Z,
                   meters_per_reconstructed_unit=METERS_PER_REF_MODEL_UNIT,
                   uniform_solid_density_assumed_kg_m3=DENSITY_KG_M3),
        staged=inputs,mass_M_kg=massM,mass_shaft_kg=massRod,
        approximate_nonunion_mass_upper_bound_kg=massM+massRod,
        incompatible_P12_15cm_PLA_solid_mass_kg=3.460898891676966,
        previous_15cm_P12_case_is_distinct=True,
        old_0_25kg_MuJoCo_demonstration_is_distinct=True,
        shaft_min_tip_height_m=float(rod.bounds[0,2]*METERS_PER_REF_MODEL_UNIT),
        shaft_max_height_m=float(rod.bounds[1,2]*METERS_PER_REF_MODEL_UNIT),
        teapot_bottom_height_m=float(prepared['M'].bounds[0,2]*METERS_PER_REF_MODEL_UNIT),
        shaft_trial_tip=[0.,0.,0.],
        proposed_spin_axis=[0.,0.,1.],
        P11_D_shaft_positive_overlap_witness_reference_units=witness.tolist(),
        winding_number_in_D_at_witness=d_winding,
        winding_number_in_shaft_at_witness=rod_winding,
        old_P11_D_not_compatible_with_new_fixed_shaft=True,
        M_F_D_ref_raw_ten_max_residual=float(residual),
        solver_objectives_registered=['INERTIA_ONLY','LOWER_COM_ONLY','MASS_REDUCTION_ONLY'],
        **{k:False for k in UNAPPROVED},
        calibrated_tip_contact=False,
        physical_observations_not_original_paper_parameters=True,
        native_Cherchi_reference_union_completed=False,
        require_D_minus_shaft_before_optimization=True)
    (out/'p13-preflight.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
    verify_preflight(out/'p13-preflight.json',out)
    return receipt


def verify_preflight(receipt_path,out):
    rec=json.loads(Path(receipt_path).read_text())
    if rec.get('schema')!=SCHEMA or rec.get('status')!='CONFLICT_IDENTIFIED_CANDIDATES_STAGED_NATIVE_UNION_NOT_RUN':
        raise ValueError('P13_PRELIMINARY_STATUS_OR_SCHEMA_ALTERED')
    if any(rec.get(flag) is not False for flag in UNAPPROVED):
        raise ValueError('P13_PREMATURE_APPROVAL_CLAIM')
    if not rec.get('require_D_minus_shaft_before_optimization',False):
        raise ValueError('P13_SHAFT_PROTECTION_GATE_REMOVED')
    for key,m in rec.get('staged',{}).items():
        f=Path(out)/m['file']
        if digest(f)!=m['sha256']:
            raise ValueError('P13_STAGED_MESH_TAMPER_'+key)
        mesh=trimesh.load_mesh(f,process=False)
        if not mesh.is_volume or len(mesh.faces)!=m['faces'] or len(mesh.vertices)!=m['vertices']:
            raise ValueError('P13_STAGED_MESH_GEOMETRY_CHANGED_'+key)
    if set(rec.get('staged',{}))!={'M','F','D','shaft'}:
        raise ValueError('P13_INCOMPLETE_STAGED_SET')
    return True


def _native(executable,op,operands,out,limit):
    cmd=[str(Path(executable).resolve()),op,*map(lambda x:str(Path(x).resolve()),operands),str(Path(out).resolve())]
    start=time.monotonic()
    trace=Path(out).with_suffix('.native-call.json')
    try:
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=limit,check=False,
                         env={**os.environ,'OMP_NUM_THREADS':'1'})
    except subprocess.TimeoutExpired as e:
        trace.write_text(json.dumps(dict(operation=op,status='NATIVE_TIMEOUT',
                                         timeout_s=limit,elapsed_s=time.monotonic()-start),indent=2)+'\n')
        raise RuntimeError('CHERCHI_NATIVE_TIMEOUT_'+op) from e
    audit=dict(op=op,argc_operands=len(operands),source_sha256=[digest(x) for x in operands],
               exit=p.returncode,seconds=time.monotonic()-start,
               stdout_tail=p.stdout[-4000:],stderr_tail=p.stderr[-4000:],
               native_output_exists=Path(out).is_file())
    # Persist raw native stdout/exit evidence BEFORE topology validation,
    # otherwise a rejected mesh would silently lose its actual process facts.
    trace.write_text(json.dumps(audit,indent=2)+'\n')
    if p.returncode!=0 or not Path(out).is_file():
        raise RuntimeError(f'CHERCHI_NATIVE_{op.upper()}_NOT_COMPLETED')
    mesh=trimesh.load_mesh(out,process=False)
    audit.update(sha256=digest(out),volume=float(mesh.volume),
                 faces=len(mesh.faces),vertices=len(mesh.vertices),
                 watertight=bool(mesh.is_watertight),
                 is_volume=bool(mesh.is_volume),
                 winding_consistent=bool(mesh.is_winding_consistent))
    trace.write_text(json.dumps(audit,indent=2)+'\n')
    if not mesh.is_volume or not mesh.is_winding_consistent:
        raise ValueError(f'CHERCHI_NATIVE_{op.upper()}_NONVOLUME')
    return mesh,audit


def run_native(source_paths,report,executable,upstream_checkout,out,*,timeout=120):
    """Three genuine Cherchi calls: O=M+shaft, D_eff=D-shaft, F_eff=O-D_eff.

    Structural acceptance requires saved reread and ten-moment additivity.
    No fallback to CGAL or physical authorization even on successful native CSG.
    """
    from p7_cherchi_native_union import native_identity
    identity=native_identity(executable,upstream_checkout)
    data=prepare(source_paths,report,out)
    out=Path(out)
    evidence=out/'p13-native-csg-audit.json'
    audit=dict(schema='W4P13CherchiReferenceUnionAndShaftExcludedDesignV1',
               status='STARTED_NO_NATIVE_SUCCESS',native=identity,
               preflight_sha256=digest(out/'p13-preflight.json'),
               source_does_not_claim_original_CAD=True,
               operations=[],geometry_accepted=False,
               material_F_D_W0_admitted=False,final_Faster_optimization=False)
    def write():evidence.write_text(json.dumps(audit,indent=2,allow_nan=False)+'\n')
    write()
    try:
        path=lambda key:out/data['staged'][key]['file']
        outer,entry=_native(executable,'union',[path('M'),path('shaft')],out/'p13-outer-cherchi-union.obj',timeout)
        audit['operations'].append(entry);write()
        design,entry=_native(executable,'subtraction',[path('D'),path('shaft')],out/'p13-D-shaft-excluded.obj',timeout)
        audit['operations'].append(entry);write()
        fixed,entry=_native(executable,'subtraction',
                            [out/'p13-outer-cherchi-union.obj',out/'p13-D-shaft-excluded.obj'],
                            out/'p13-F-shaft-preserved.obj',timeout)
        audit['operations'].append(entry);write()
        from p2_self_intersection import check_nonincident_triangle_contacts
        for name,mesh in [('outer',outer),('design',design),('fixed',fixed)]:
            # F is allowed to have 2 boundary components (outer+cavity).
            contact=check_nonincident_triangle_contacts(mesh.vertices,mesh.faces,max_witnesses=8)
            audit[name+'_contact_check']=contact
            if contact['witnesses'] or not contact['exhaustive']:
                raise ValueError(f'CHERCHI_{name.upper()}_SELF_CONTACT_PRECHECK_FAILED')
        volume_bounds=(max(data['staged']['M']['signed_volume'],data['staged']['shaft']['signed_volume'])-1e-6,
                       data['staged']['M']['signed_volume']+data['staged']['shaft']['signed_volume']+1e-6)
        if not volume_bounds[0]<=outer.volume<=volume_bounds[1]:
            raise ValueError('CHERCHI_UNION_VOLUME_OUTSIDE_BOUNDS')
        if not 0<design.volume<data['staged']['D']['signed_volume']:
            raise ValueError('DESIGN_ROD_SUBTRACTION_VOLUME_BAD')
        raw_res=raw_ten(outer)-raw_ten(fixed)-raw_ten(design)
        maxerr=float(np.max(np.abs(raw_res)))
        audit.update(max_abs_10_raw_moment_partition_error=maxerr,
                     outer_volume=float(outer.volume),fixed_volume=float(fixed.volume),
                     carveable_volume=float(design.volume),
                     shaft_tip_m=[0.,0.,0.],
                     volume_bounds=volume_bounds,
                     true_native_Cherchi_calls=3)
        if maxerr>5e-7:raise ValueError('REAL_CHERCHI_FD_TEN_MOMENT_ADDITIVITY_FAILED')
        # This is an engineering feasibility only: W0 and source CAD remain unapproved.
        audit['status']='NATIVE_CHERCHI_EXPLORATORY_SHAFT_DOMAIN_NUMERIC_PASS'
        audit['geometry_accepted']=True
        audit['material_F_D_W0_admitted']=False
    except Exception as exc:
        audit['status']='NATIVE_CHERCHI_EXPLORATORY_SHAFT_DOMAIN_FAILED'
        audit['failure']=f'{type(exc).__name__}: {exc}'
        write()
        raise
    write()
    return audit


def main():
    p=argparse.ArgumentParser()
    for name in ('m','f','d','p11-report','out'):
        p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--native-bin',type=Path)
    p.add_argument('--upstream-checkout',type=Path)
    p.add_argument('--timeout',type=int,default=120)
    args=p.parse_args()
    src={'M':args.m,'F':args.f,'D':args.d}
    if (args.native_bin is None)!=(args.upstream_checkout is None):
        raise ValueError('NATIVE_CLI_AND_UPSTREAM_MUST_BOTH_BE_SET')
    if args.native_bin:
        result=run_native(src,args.p11_report,args.native_bin,args.upstream_checkout,args.out,timeout=args.timeout)
    else:result=prepare(src,args.p11_report,args.out)
    print(json.dumps(dict(status=result['status'],native_csg=bool(args.native_bin),
                          tip=result.get('shaft_trial_tip',result.get('shaft_tip_m')),
                          overlap=result.get('old_P11_D_not_compatible_with_new_fixed_shaft',True)),indent=2))

if __name__=='__main__':main()
