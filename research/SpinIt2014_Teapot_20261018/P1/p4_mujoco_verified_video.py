#!/usr/bin/env python3
"""W4 P4: strict MuJoCo contact/rotation comparison and MP4 exporter.

Only official MuJoCo may run dynamics. The default input is explicitly the
P2 CGAL *diagnostic proxy*, NOT a Cherchi result or Spin-It optimization.
Preflight is executable without MuJoCo; video/trajectory generation is NOT.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
import numpy as np
import cv2
import trimesh

P2_Z_SHA256 = 'd3289193185192ebca4d63fc813bd77d96810051089c672e887accdf3205b331'
RATES = (0., 30., 60.)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _need(node, msg):
    if node is None:
        raise ValueError(msg)
    return node


def _numbers(text, count, label):
    values = np.fromstring(str(text), sep=' ', dtype=np.float64)
    if len(values) != count or not np.isfinite(values).all():
        raise ValueError(f'INVALID_{label}')
    return values


def preflight(xml_path):
    """Independently bind MJCF, visual mesh, actual inertial data and provenance.

    This checks XML syntax/structure and source physics; it does not claim the
    unavailable MuJoCo engine parsed the MJCF or ran any contact solver.
    """
    xml_path = Path(xml_path).resolve(strict=True)
    manifest_path = xml_path.parent / 'simulation-manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('schema') != 'W4MuJoCoSimulationV1':
        raise ValueError('UNRECOGNIZED_SIMULATION_MANIFEST')
    if manifest.get('mjcf_sha256') != sha(xml_path):
        raise ValueError('MJCF_SHA256_MISMATCH')
    provenance = manifest.get('mesh_provenance') or {}
    if (provenance.get('source_kind') != 'diagnostic-cgal' or
        provenance.get('authoritative_cherchi') is not False or
        provenance.get('physical_case_authorized') is not False or
        manifest.get('claims_cherchi_geometry') is not False or
        manifest.get('claims_mujoco_dynamics_run') is not False):
        raise ValueError('DIAGNOSTIC_MESH_FALSELY_PROMOTED')
    if manifest.get('mesh_asset_sha256') != P2_Z_SHA256:
        raise ValueError('MANIFEST_VISUAL_ASSET_MISMATCH')
    root = ET.parse(xml_path).getroot()
    if root.tag != 'mujoco':
        raise ValueError('NOT_MJCF')
    asset = _need(root.find('asset/mesh[@name="teapot_visual"]'), 'MISSING_VISUAL_MESH')
    relpath = Path(asset.attrib.get('file',''))
    if relpath.is_absolute() or '..' in relpath.parts:
        raise ValueError('UNSAFE_ASSET_PATH')
    mesh_path = (xml_path.parent / relpath).resolve(strict=True)
    if not mesh_path.is_relative_to(xml_path.parent):
        raise ValueError('MESH_OUTSIDE_SCENE_DIRECTORY')
    if sha(mesh_path) != P2_Z_SHA256:
        raise ValueError('VISUAL_MESH_SHA256_MISMATCH')
    mesh = trimesh.load_mesh(mesh_path, process=False)
    if not mesh.is_volume or len(mesh.split(only_watertight=False)) != 1:
        raise ValueError('VISUAL_PROXY_NOT_CLOSED_SOLID')
    body = _need(root.find('worldbody/body[@name="teapot"]'), 'MISSING_BODY')
    _need(body.find('freejoint[@name="teapot_free"]'), 'MISSING_FREEJOINT')
    inertial = _need(body.find('inertial'), 'MISSING_EXPLICIT_INERTIA')
    mass = _numbers(inertial.attrib.get('mass'), 1, 'MASS')[0]
    com = _numbers(inertial.attrib.get('pos'), 3, 'COM')
    diag = _numbers(inertial.attrib.get('diaginertia'), 3, 'DIAGONAL_INERTIA')
    quat = _numbers(inertial.attrib.get('quat'), 4, 'INERTIA_QUAT')
    if mass <= 0 or np.min(diag) <= 0 or 2*max(diag) >= sum(diag)+1e-10 or abs(np.linalg.norm(quat)-1)>1e-7:
        raise ValueError('INVALID_PHYSICAL_INERTIA')
    params = manifest.get('physical_parameters') or {}
    if abs(float(params.get('physical_mass_kg', float('nan'))) - mass) > 1e-12:
        raise ValueError('MANIFEST_MASS_MISMATCH')
    if not np.allclose(com, params.get('com_m'), atol=1e-12, rtol=0):
        raise ValueError('MANIFEST_COM_MISMATCH')
    if not np.allclose(diag, params.get('diagonal_inertia_kg_m2'), atol=1e-12, rtol=0):
        raise ValueError('MANIFEST_INERTIA_MISMATCH')
    scales = _numbers(asset.attrib.get('scale'), 3, 'SCALE')
    if not np.allclose(scales, params.get('scale'), atol=1e-12, rtol=0):
        raise ValueError('VISUAL_SCALE_MISMATCH')
    # Mesh inertia must be from the material mesh, not the visual/collision proxy geoms.
    calc_com = np.asarray(mesh.center_mass) * scales[0]
    if not np.allclose(calc_com, com, atol=1e-10, rtol=0):
        raise ValueError('RELOADED_MESH_COM_MISMATCH')
    # Explicit inertial data prevents MuJoCo from deducing inertial mass from visuals.
    floor = _need(root.find('worldbody/geom[@name="floor"]'), 'MISSING_FLOOR')
    tip = _need(body.find('geom[@name="virtual_tip_contact"]'), 'MISSING_DIAGNOSTIC_TIP')
    approx = _need(body.find('geom[@name="approximate_body_contact"]'), 'MISSING_APPROX_COLLISION')
    visual = _need(body.find('geom[@name="teapot_mesh_visual"]'), 'MISSING_VISUAL_GEOM')
    opts = _need(root.find('option'), 'MISSING_OPTION')
    if floor.get('type') != 'plane' or tip.get('type') != 'sphere' or approx.get('type') != 'sphere':
        raise ValueError('UNEXPECTED_CONTACT_GEOMETRY')
    if visual.get('contype') != '0' or visual.get('conaffinity') != '0':
        raise ValueError('VISUAL_MESH_SHOULD_NOT_COLLIDE')
    if not np.allclose(_numbers(opts.get('gravity'),3,'GRAVITY'),[0,0,-9.81]):
        raise ValueError('GRAVITY_NOT_DECLARED')
    timestep = float(opts.attrib.get('timestep','nan'))
    if not np.isfinite(timestep) or timestep<=0:
        raise ValueError('BAD_MUJOCO_TIMESTEP')
    if float(_numbers(tip.get('size'),1,'TIP_RADIUS')[0])<=0:
        raise ValueError('TIP_RADIUS_NOT_POSITIVE')
    return dict(schema='W4MuJoCoVideoPreflightV1',
                preflight='STATIC_SOURCE_AND_SCENE_PASS_MUJOCO_NOT_EXECUTED',
                xml_sha256=sha(xml_path), visual_mesh_sha256=sha(mesh_path),
                mesh_vertices=int(len(mesh.vertices)), mesh_faces=int(len(mesh.faces)),
                mass_kg=float(mass), com_body_m=com.tolist(),
                inertia_principal_kgm2=diag.tolist(), timestep_s=timestep,
                contact='VIRTUAL_TIP_AND_APPROX_BODY_SPHERES_NOT_TRUE_CAD',
                geometry_source='P2_CGAL_PROXY_NOT_CHERCHI',
                does_not_prove='MJCf_NATIVE_ACCEPTANCE_OR_DYNAMICS_OR_OPTIMIZATION')


def _require_runtime():
    try:
        import mujoco
    except ImportError as exc:
        raise RuntimeError('MUJOCO_RUNTIME_UNAVAILABLE_NO_ACTUAL_SIMULATION_OR_VIDEO') from exc
    return mujoco


def _encode_mp4(frames, target, *,fps, width,height):
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo',
         '-pix_fmt','bgr24','-s',f'{width}x{height}','-r',str(fps),'-i','-',
         '-an','-c:v','libx264','-crf','22','-preset','medium',
         '-pix_fmt','yuv420p','-movflags','+faststart',str(target)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for frame in frames:
            if frame.shape!=(height,width,3) or frame.dtype!=np.uint8:
                raise ValueError('VIDEO_FRAME_SHAPE_INVALID')
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        message=proc.stderr.read().decode('utf-8','replace')
        ret=proc.wait(timeout=120)
        proc.stderr.close()
        if ret:
            raise RuntimeError(f'FFMPEG_ENCODING_FAILED exit={ret}: {message[-600:]}')
    except Exception:
        try: proc.kill()
        except Exception: pass
        raise
    if not Path(target).is_file() or Path(target).stat().st_size<512:
        raise RuntimeError('ENCODED_MP4_NOT_PRESENT')
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0',
          '-show_entries','stream=codec_name,width,height,nb_frames','-of','json',str(target)],text=True))
    streams=probe.get('streams',[])
    if (len(streams)!=1 or streams[0].get('codec_name')!='h264' or
        streams[0].get('width')!=width or streams[0].get('height')!=height):
        raise RuntimeError('VIDEO_INDEPENDENT_PROBE_FAILED')
    return streams[0]


def run(xml,out,*,duration=2.8,fps=24,tilt_deg=5.,spins=RATES):
    if duration<=0 or fps<5 or fps>60 or not (0<=tilt_deg<90) or len(spins)!=3:
        raise ValueError('INVALID_EXPERIMENT_SETTINGS')
    if tuple(map(float,spins)) != RATES:
        raise ValueError('THREE_CANONICAL_SPIN_RATES_REQUIRED')
    source=preflight(xml)
    mujoco=_require_runtime()  # Only this engine may create results/video.
    xml=Path(xml).resolve(strict=True)
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    model=mujoco.MjModel.from_xml_path(str(xml))
    bid=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_BODY,'teapot')
    tid=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_GEOM,'virtual_tip_contact')
    gid=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_GEOM,'floor')
    if min(bid,tid,gid)<0 or (model.nq,model.nv)!=(7,6):
        raise RuntimeError('MUJOCO_EXPECTED_FREEBODY_NOT_FOUND')
    frames_by_rate=[];rows_by_rate=[];summaries=[]
    started=time.monotonic()
    try:
        renderer=mujoco.Renderer(model,height=480,width=440)
    except Exception as exc:
        raise RuntimeError(f'MUJOCO_OFFSCREEN_RENDER_INIT_FAILED: {exc}') from exc
    camera=mujoco.MjvCamera();camera.type=mujoco.mjtCamera.mjCAMERA_FREE
    camera.lookat[:]=[0,0,.065];camera.distance=.55;camera.azimuth=138;camera.elevation=-20
    th=math.radians(tilt_deg)
    q=[math.cos(th/2),math.sin(th/2),0.,0.]
    sample_times=np.linspace(0.,float(duration),int(math.ceil(duration*fps))+1)
    try:
        for spin in spins:
            data=mujoco.MjData(model)
            data.qpos[:7]=[0.,0.,float(model.geom_size[tid,0]),*q]
            data.qvel[:]=0.;data.qvel[5]=float(spin)
            mujoco.mj_forward(model,data)
            frames=[];rows=[]
            for desired in sample_times:
                while data.time < desired-1e-10:
                    mujoco.mj_step(model,data)
                    if not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all():
                        raise RuntimeError('MUJOCO_INTEGRATOR_NONFINITE')
                world_z=np.asarray(data.xmat[bid]).reshape(3,3) @ np.array([0.,0.,1.])
                tilt=float(np.degrees(np.arccos(np.clip(world_z[2],-1,1))))
                tip_contacts=sum(1 for ci in range(data.ncon) if
                   {int(data.contact[ci].geom1),int(data.contact[ci].geom2)}=={tid,gid})
                renderer.update_scene(data,camera=camera)
                rgb=renderer.render()
                if rgb.shape!=(480,440,3): raise RuntimeError('MUJOCO_FRAME_SHAPE_INVALID')
                frame=cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR)
                cv2.rectangle(frame,(0,0),(440,70),(22,27,38),-1)
                cv2.putText(frame,f'MuJoCo | {int(spin)} rad/s',(11,23),
                            cv2.FONT_HERSHEY_SIMPLEX,.67,(240,242,255),2)
                cv2.putText(frame,f'tilt={tilt:.1f} deg  tip={tip_contacts}',(11,46),
                            cv2.FONT_HERSHEY_SIMPLEX,.52,(190,220,255),1)
                cv2.putText(frame,'CGAL proxy, NOT Cherchi',(11,63),
                            cv2.FONT_HERSHEY_SIMPLEX,.39,(145,180,250),1)
                frames.append(frame)
                rows.append(dict(time_s=float(data.time),tilt_deg=tilt,
                    com_height_m=float(data.xipos[bid,2]),
                    tip_floor_contact_count=int(tip_contacts),
                    total_contact_count=int(data.ncon),
                    angular_speed_rad_s=float(np.linalg.norm(data.qvel[3:6]))))
            frames_by_rate.append(frames);rows_by_rate.append(rows)
            if any(rows[i]['time_s']<=rows[i-1]['time_s'] for i in range(1,len(rows))):
                raise RuntimeError('MUJOCO_TIMESTAMPS_NOT_INCREASING')
            tail=[row for row in rows if row['time_s']>=.75*duration]
            fraction=sum(row['tip_floor_contact_count']>0 for row in tail)/len(tail)
            summaries.append(dict(initial_spin_rad_s=float(spin),samples=len(rows),
                final_tilt_deg=rows[-1]['tilt_deg'],
                peak_tilt_deg=max(row['tilt_deg'] for row in rows),
                tail_tip_contact_fraction=float(fraction),
                diagnostic_stable_threshold_pass=bool(
                    max(x['tilt_deg'] for x in tail)<15 and fraction>.5)))
    finally:
        renderer.close()
    # Only after every real physical run/renderer sample succeeds may a video be emitted.
    with tempfile.TemporaryDirectory(prefix='w4-video-temp-',dir=out) as td:
        td=Path(td)
        csv_files=[]
        for spin, rows in zip(spins,rows_by_rate):
            path=td/f'mujoco_{int(spin)}_rad_s.csv'
            with path.open('w',newline='',encoding='utf-8') as file:
                writer=csv.DictWriter(file,fieldnames=list(rows[0]))
                writer.writeheader();writer.writerows(rows)
            csv_files.append(path)
        path=td/'mujoco_teapot_comparison.mp4'
        video_frames=(np.concatenate(items,axis=1) for items in zip(*frames_by_rate))
        stream=_encode_mp4(video_frames,path,fps=fps,width=1320,height=480)
        video_info=dict(codec=stream['codec_name'],width=1320,height=480,
                        frame_count=int(stream.get('nb_frames',len(sample_times))),
                        sha256=sha(path))
        for file in csv_files:
            os.replace(file,out/file.name)
        os.replace(path,out/path.name)
    result=dict(schema='W4RealMuJoCoVideoV2',status='REAL_MUJOCO_ENGINE_AND_VIDEO_EXECUTED',
        engine='MuJoCo',engine_version=mujoco.__version__,
        source_preflight=source,source_geometry='P2_CGAL_DIAGNOSTIC_PROXY_NOT_CHERCHI',
        contact_model='VIRTUAL_TIP_PLUS_APPROXIMATE_SPHERE_NOT_PRINTABLE_MATERIAL',
        physics_conclusion='ILLUSTRATIVE_SIMULATION_NOT_VALIDATED_SPIN_IT',
        duration_requested_s=float(duration),fps=int(fps),
        initial_tilt_deg=float(tilt_deg),
        wall_seconds=float(time.monotonic()-started),
        videos={'comparison_mp4':video_info},
        trajectory_sha256_by_rate={str(int(rate)):sha(out/f'mujoco_{int(rate)}_rad_s.csv')
                                   for rate in spins}, results=summaries)
    (out/'mujoco_video_results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description='W4 MuJoCo runtime and truthful video export')
    parser.add_argument('--xml',type=Path,required=True)
    parser.add_argument('--out',type=Path)
    parser.add_argument('--duration',type=float,default=2.8)
    parser.add_argument('--fps',type=int,default=24)
    parser.add_argument('--preflight-only',action='store_true')
    args=parser.parse_args()
    try:
        if args.preflight_only:
            print(json.dumps(preflight(args.xml),indent=2))
            return 0
        if args.out is None:
            raise ValueError('OUTPUT_PATH_REQUIRED')
        print(json.dumps(run(args.xml,args.out,duration=args.duration,fps=args.fps),indent=2))
        return 0
    except (RuntimeError,ValueError,ImportError,FileNotFoundError) as exc:
        print(f'W4_MUJOCO_VIDEO_GATE_BLOCKED: {type(exc).__name__}: {exc}',file=sys.stderr)
        return 2

if __name__=='__main__':
    sys.exit(main())
