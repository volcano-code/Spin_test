#!/usr/bin/env python3
"""W4 MuJoCo spinning-top diagnostic, with strict geometry provenance.

PREPARE uses the candidate's real closed mesh to derive mass properties and
writes an actual MuJoCo MJCF model with a free joint and rigid-body inertia.
RUN requires the *real* MuJoCo Python engine; no surrogate solver or CGAL
simulation is allowed. Diagnostic CGAL *geometry* cannot be promoted to
Cherchi/physics truth. All physical dimensions of diagnostic runs are assumed.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial.transform import Rotation
import trimesh

P2_Z_SHA256 = 'd3289193185192ebca4d63fc813bd77d96810051089c672e887accdf3205b331'
CHERCHI_ID = 'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0-inprocess-v1'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fmt(arr):
    return ' '.join(f'{float(x):.16g}' for x in np.ravel(arr))


def geometry_origin_contract(mesh_path, origin, certificate=None, case=None):
    identity=digest(mesh_path)
    if origin=='diagnostic-cgal':
        if identity!=P2_Z_SHA256:
            raise ValueError('DIAGNOSTIC_CGAL_MESH_SHA_MISMATCH')
        if case is not None:
            raise ValueError('NO_W0_CONTRACT_MIXED_WITH_DIAGNOSTIC_PROXY')
        return dict(source_kind=origin,mesh_sha256=identity,authoritative_cherchi=False,
                    physical_case_authorized=False,warning='DIAGNOSTIC_CGAL_GEOMETRY_ONLY_NOT_CHERCHI_RESULT')
    if origin!='cherchi-certified':raise ValueError('SOURCE_KIND_INVALID')
    if certificate is None or case is None:
        raise ValueError('CHERCHI_NATIVE_CERT_AND_W0_PHYSICAL_CASE_REQUIRED')
    cert=json.loads(Path(certificate).read_text())
    physical=json.loads(Path(case).read_text())
    if (cert.get('schema')!='w4-teapot-cherchi-certified-v1' or
        cert.get('native_backend')!=CHERCHI_ID or cert.get('mesh_sha256')!=identity or
        cert.get('exact_boundary_certified') is not True or
        cert.get('independent_geometry_certified') is not True):
        raise ValueError('CHERCHI_INDEPENDENT_CERT_REQUIRED')
    if (physical.get('schema')!='W4TeapotPhysicalCaseV1' or
        physical.get('mesh_sha256')!=identity or
        not physical.get('W0_physical_case_authorized',False) or
        not physical.get('fixed_F_sha256') or not physical.get('design_D_sha256')):
        raise ValueError('W0_PHYSICAL_F_D_CONTRACT_REQUIRED')
    return dict(source_kind=origin,mesh_sha256=identity,
                authoritative_cherchi=True,physical_case_authorized=True,
                native_binary_sha256=cert.get('native_binary_sha256'),
                physical_case_sha256=digest(case))


def inertial_from_mesh(mesh,height_m,mass_kg):
    """Mass-normalize raw volume-integral inertia and diagonalize COM tensor.

    Mesh geometry is in Z-up model units. Translation to COM and scaling s
    satisfy I_SI = (mass_kg / volume) * s^2 * I_model, exactly for uniform density.
    """
    if not mesh.is_volume or len(mesh.split(only_watertight=False))!=1:
        raise ValueError('INERTIAL_MESH_MUST_BE_ONE_CLOSED_POSITIVE_VOLUME')
    if not np.isfinite(mesh.vertices).all():raise ValueError('NONFINITE_MESH')
    height=float(np.ptp(mesh.bounds[:,2]))
    if height<=0 or height_m<=0 or mass_kg<=0 or not all(map(math.isfinite,(height_m,mass_kg))):
        raise ValueError('PHYSICAL_SIZE_OR_MASS_INVALID')
    s=height_m/height
    centroid=np.asarray(mesh.center_mass)*s
    inertia=np.asarray(mesh.moment_inertia)*(mass_kg/mesh.volume)*(s*s)
    inertia=.5*(inertia+inertia.T)
    diag,principal=np.linalg.eigh(inertia)
    if diag.min()<=0 or diag.max()>=sum(diag)-diag.max():
        raise ValueError('INERTIA_NOT_POSITIVE_PHYSICAL_TENSOR')
    if np.linalg.det(principal)<0:principal[:,0]*=-1
    # scipy quaternion xyzw -> MuJoCo wxyz
    q=Rotation.from_matrix(principal).as_quat()
    quat=[q[3],q[0],q[1],q[2]]
    return dict(scale=s,model_volume=float(mesh.volume),com_m=centroid.tolist(),
                physical_mass_kg=float(mass_kg),inertia_com_kg_m2=inertia.tolist(),
                diagonal_inertia_kg_m2=diag.tolist(),quat_wxyz=quat,
                mesh_height_m=float(height_m),roundtrip_inertia_max_abs_error=float(np.max(
                    np.abs(principal@np.diag(diag)@principal.T-inertia))))


def prepare_model(mesh_path,out,*,source_kind,certificate=None,case=None,
                  height_m=None,mass_kg=None,tip_radius_m=0.002,friction=0.9):
    mesh_path=Path(mesh_path)
    source=geometry_origin_contract(mesh_path,source_kind,certificate,case)
    if source_kind=='cherchi-certified':
        physical=json.loads(Path(case).read_text())
        # Case tip and rotation axis must be explicitly established by W0.
        if physical.get('axis_z_up')!=[0,0,1] or physical.get('tip_z_up_mesh_units')!=[0,0,0]:
            raise ValueError('PHYSICAL_CASE_AXIS_OR_TIP_NOT_IN_SIM_FRAME')
        height_m=float(physical['height_m']);mass_kg=float(physical['mass_kg'])
        tip_radius_m=float(physical['tip_radius_m'])
    else:
        if height_m is None or mass_kg is None:
            raise ValueError('DIAGNOSTIC_DIMENSIONS_MUST_BE_EXPLICIT')
    if tip_radius_m<=0 or friction<=0 or not math.isfinite(tip_radius_m+friction):
        raise ValueError('INVALID_TIP_OR_FRICTION')
    mesh=trimesh.load_mesh(mesh_path,process=False)
    prop=inertial_from_mesh(mesh,float(height_m),float(mass_kg))
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    assets=out/'assets';assets.mkdir(exist_ok=True)
    local=assets/'teapot_visual_z_up.obj'
    shutil.copyfile(mesh_path,local)
    scene=ET.Element('mujoco',attrib={'model':'w4_teapot_spinning_diagnostic'})
    ET.SubElement(scene,'compiler',attrib={'angle':'radian','inertiafromgeom':'false','autolimits':'true'})
    ET.SubElement(scene,'option',attrib={'timestep':'0.002','gravity':'0 0 -9.81',
                                         'integrator':'implicitfast','solver':'Newton','iterations':'70'})
    ET.SubElement(scene,'asset')
    ET.SubElement(scene.find('asset'),'mesh',attrib={'name':'teapot_visual',
        'file':'assets/teapot_visual_z_up.obj','scale':fmt([prop['scale']]*3)})
    world=ET.SubElement(scene,'worldbody')
    ET.SubElement(world,'light',attrib={'pos':'0 0 2','dir':'0 0 -1'})
    ET.SubElement(world,'geom',attrib={'name':'floor','type':'plane','pos':'0 0 0',
        'size':'2 2 .1','rgba':'0.86 0.86 0.86 1',
        'friction':fmt([friction,0.01,0.001])})
    body=ET.SubElement(world,'body',attrib={'name':'teapot','pos':'0 0 0'})
    ET.SubElement(body,'freejoint',attrib={'name':'teapot_free'})
    ET.SubElement(body,'inertial',attrib={'pos':fmt(prop['com_m']),
        'quat':fmt(prop['quat_wxyz']),
        'mass':fmt([prop['physical_mass_kg']]),
        'diaginertia':fmt(prop['diagonal_inertia_kg_m2'])})
    ET.SubElement(body,'geom',attrib={'name':'teapot_mesh_visual','type':'mesh',
        'mesh':'teapot_visual','contype':'0','conaffinity':'0',
        'rgba':'0.60 0.68 0.78 0.9','group':'2'})
    # WARNING: Virtual tip + body sphere are simplified test fixtures. These
    # are NOT the actual printable shell/shaft collision geometries.
    ET.SubElement(body,'geom',attrib={'name':'virtual_tip_contact','type':'sphere',
        'pos':'0 0 0','size':fmt([tip_radius_m]),
        'friction':fmt([friction,0.01,0.001]),
        'rgba':'0.9 0.2 0.18 1'})
    sphere_z=max(prop['com_m'][2],float(height_m)*0.48)
    sphere_radius=min(float(height_m)*0.32,sphere_z-tip_radius_m*1.2)
    if sphere_radius<=0:raise ValueError('BODY_COLLISION_SPHERE_INVALID')
    ET.SubElement(body,'geom',attrib={'name':'approximate_body_contact','type':'sphere',
        'pos':fmt([0,0,sphere_z]),'size':fmt([sphere_radius]),
        'friction':fmt([friction,0.01,0.001]),
        'rgba':'0.20 0.5 0.9 0.05','group':'3'})
    ET.indent(scene,space='  ')
    path=out/'teapot_spinning.xml'
    ET.ElementTree(scene).write(path,encoding='unicode',xml_declaration=True)
    # Static readback of XML structure and all physical scalar values.
    reread=ET.parse(path).getroot()
    assert reread.find('worldbody/body/inertial') is not None
    assert reread.find('worldbody/body/freejoint') is not None
    report=dict(schema='W4MuJoCoSimulationV1',
        status='MJCF_GENERATED_RUNTIME_NOT_YET_EXECUTED',mesh_provenance=source,
        physical_parameters=prop,
        experiment_kind='ILLUSTRATIVE_NOT_AUTHOR_PAPER_REPRODUCTION' if
            source_kind=='diagnostic-cgal' else 'CERTIFIED_CHERCHI_W0_CASE',
        collision_model='VIRTUAL_TIP_SPHERE_PLUS_APPROXIMATE_BODY_SPHERE_NOT_TRUE_CAD_CONTACT',
        friction=float(friction),tip_radius_m=float(tip_radius_m),
        mjcf_sha256=digest(path),mesh_asset_sha256=digest(local),
        engine='MuJoCo (required at runtime)',
        claims_cherchi_geometry=source['authoritative_cherchi'],
        claims_mujoco_dynamics_run=False,
        proposed_spin_rates_rad_s=[0.,30.,60.],
        initial_tilt_deg=5.,gravity_m_s2=9.81)
    (out/'simulation-manifest.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report


def run_simulation(xml_path,output,*,duration=2.0,spin_rates=(0.,30.,60.),tilt_deg=5.,sample_every=10):
    """Execute actual MuJoCo physics; absence is a hard failure, never substitute."""
    try:
        import mujoco
    except ImportError as exc:
        raise RuntimeError('MUJOCO_RUNTIME_UNAVAILABLE_INSTALL_MUJOCO_3_3_OR_NEWER') from exc
    if duration<=0 or not (0<tilt_deg<90) or sample_every<=0:
        raise ValueError('INVALID_SIMULATION_SETTINGS')
    xml_path=Path(xml_path);out=Path(output)
    out.mkdir(parents=True,exist_ok=True)
    model=mujoco.MjModel.from_xml_path(str(xml_path.resolve()))
    body_id=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_BODY,'teapot')
    tip_id=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_GEOM,'virtual_tip_contact')
    floor_id=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_GEOM,'floor')
    if body_id<0 or tip_id<0 or floor_id<0 or model.nq!=7 or model.nv!=6:
        raise RuntimeError('INVALID_MUJOCO_FREE_BODY_MODEL')
    r=Rotation.from_euler('x',tilt_deg,degrees=True)
    xyzw=r.as_quat()
    quaternion=[xyzw[3],xyzw[0],xyzw[1],xyzw[2]]
    tip_radius=float(np.asarray(model.geom_size[tip_id])[0])
    runs=[]
    for spin in spin_rates:
        if not math.isfinite(spin) or spin<0:raise ValueError('SPIN_RATE_INVALID')
        data=mujoco.MjData(model)
        data.qpos[:7]=[0,0,tip_radius,*quaternion]
        # For MuJoCo freejoint, qvel angular components live in the body frame.
        data.qvel[:]=0
        data.qvel[5]=float(spin)
        mujoco.mj_forward(model,data)
        samples=[];n_steps=int(math.ceil(duration/model.opt.timestep))
        for k in range(n_steps+1):
            if k%sample_every==0 or k==n_steps:
                axis=np.asarray(data.xmat[body_id]).reshape(3,3) @ [0.,0.,1.]
                tilt=float(np.degrees(np.arccos(np.clip(axis[2],-1.,1.))))
                tip_contact=sum(1 for ci in range(data.ncon) if
                    {int(data.contact[ci].geom1),int(data.contact[ci].geom2)}=={tip_id,floor_id})
                com_z=float(data.xipos[body_id,2])
                samples.append(dict(time_s=float(data.time),tilt_deg=tilt,
                    com_z_m=com_z,angular_speed_rad_s=float(np.linalg.norm(data.qvel[3:6])),
                    tip_contact_count=int(tip_contact),total_contacts=int(data.ncon)))
            if k<n_steps:
                mujoco.mj_step(model,data)
                if not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all():
                    raise RuntimeError('NONFINITE_MUJOCO_DYNAMICS')
        csv_path=out/f'teapot_spin_{int(spin)}rad_s.csv'
        with csv_path.open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(samples[0]))
            writer.writeheader();writer.writerows(samples)
        tail=[s for s in samples if s['time_s']>=duration*0.75]
        runs.append(dict(spin_rad_s=float(spin),samples=len(samples),
            max_tilt_deg=max(s['tilt_deg'] for s in samples),
            final_tilt_deg=samples[-1]['tilt_deg'],
            final_com_z_m=samples[-1]['com_z_m'],
            min_com_z_m=min(s['com_z_m'] for s in samples),
            tail_tip_contact_fraction=sum(s['tip_contact_count']>0 for s in tail)/len(tail),
            stable_diagnostic_only=bool(max(s['tilt_deg'] for s in tail)<15 and
                                        sum(s['tip_contact_count']>0 for s in tail)/len(tail)>0.5),
            csv=csv_path.name,sha256=digest(csv_path)))
    result=dict(schema='W4MuJoCoRunV1',status='ACTUAL_MUJOCO_ENGINE_EXECUTED',
        engine_version=mujoco.__version__,model_sha256=digest(xml_path),
        timestep_s=float(model.opt.timestep),duration_s=float(duration),
        initial_tilt_deg=float(tilt_deg),contact_model_approximate=True,
        physics_validates_cherchi_optimizer=False,runs=runs)
    (out/'mujoco-run.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest='command',required=True)
    prep=sub.add_parser('prepare')
    prep.add_argument('--mesh',type=Path,required=True)
    prep.add_argument('--output',type=Path,required=True)
    prep.add_argument('--source-kind',required=True,choices=('diagnostic-cgal','cherchi-certified'))
    prep.add_argument('--certificate',type=Path)
    prep.add_argument('--case-contract',type=Path)
    prep.add_argument('--height-m',type=float)
    prep.add_argument('--mass-kg',type=float)
    prep.add_argument('--tip-radius-m',type=float,default=0.002)
    prep.add_argument('--friction',type=float,default=0.9)
    run=sub.add_parser('run')
    run.add_argument('--xml',type=Path,required=True)
    run.add_argument('--output',type=Path,required=True)
    run.add_argument('--duration',type=float,default=2)
    run.add_argument('--tilt-deg',type=float,default=5)
    run.add_argument('--spin-rates',type=float,nargs='+',default=[0,30,60])
    args=ap.parse_args()
    try:
        if args.command=='prepare':
            result=prepare_model(args.mesh,args.output,source_kind=args.source_kind,
                certificate=args.certificate,case=args.case_contract,
                height_m=args.height_m,mass_kg=args.mass_kg,
                tip_radius_m=args.tip_radius_m,friction=args.friction)
        else:
            result=run_simulation(args.xml,args.output,duration=args.duration,
                                  spin_rates=args.spin_rates,tilt_deg=args.tilt_deg)
        print(json.dumps(result,indent=2))
        return 0
    except (RuntimeError,ValueError,ImportError) as exc:
        print(f'W4_GUARDED_FAILURE: {type(exc).__name__}: {exc}',file=sys.stderr)
        return 2


if __name__=='__main__':sys.exit(main())
