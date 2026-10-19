#!/usr/bin/env python3
"""Actual MuJoCo offscreen H264 spin-triptych (requires installed mujoco).

Fail closed if the physics engine or renderer is unavailable. This code has NOT
been executed with MuJoCo in the current isolated container. The input model
remains the CGAL *diagnostic proxy* until Cherchi is independently certified.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, os, subprocess, sys
from pathlib import Path
import numpy as np
import cv2

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def run(xml,out,duration=2.,fps=24,tilt_deg=5.,spins=(0.,30.,60.)):
    try:
        import mujoco
    except ImportError as e:
        raise RuntimeError('MUJOCO_RUNTIME_UNAVAILABLE: no real MuJoCo simulation/video possible') from e
    xml=Path(xml).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    if duration<=0 or fps<5 or len(spins)!=3 or not 0<=tilt_deg<90:
        raise ValueError('BAD_EXPERIMENT_PARAMETERS')
    model=mujoco.MjModel.from_xml_path(str(xml))
    bid=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_BODY,'teapot')
    gid=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_GEOM,'virtual_tip_contact')
    floor=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_GEOM,'floor')
    if min(bid,gid,floor)<0 or model.nq!=7 or model.nv!=6:
        raise ValueError('MUJOCO_MODEL_NOT_EXPECTED_FREE_TEAPOT')
    rates=[];image_sequences=[];summaries=[]
    # Require real OpenGL context: inability to render is an explicit failure.
    try:
        renderer=mujoco.Renderer(model,height=480,width=440)
    except Exception as e:
        raise RuntimeError('MUJOCO_RENDERER_INIT_FAILED: '+str(e)) from e
    camera=mujoco.MjvCamera();camera.type=mujoco.mjtCamera.mjCAMERA_FREE
    camera.lookat[:]=[0,0,0.065]
    camera.distance=0.55;camera.azimuth=138;camera.elevation=-20
    th=math.radians(tilt_deg)
    quat=[math.cos(th/2),math.sin(th/2),0,0]
    times=np.linspace(0,duration,math.ceil(duration*fps)+1)
    for spin in spins:
        if not math.isfinite(spin): raise ValueError('BAD_SPIN_RATE')
        data=mujoco.MjData(model)
        data.qpos[:7]=[0,0,float(model.geom_size[gid,0]),*quat]
        data.qvel[:]=0;data.qvel[5]=float(spin)
        mujoco.mj_forward(model,data)
        frames=[];rows=[]
        for sample_t in times:
            while data.time<sample_t-1e-10:
                mujoco.mj_step(model,data)
                if not (np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all()):
                    raise RuntimeError('MUJOCO_DYNAMICS_NAN')
            body_z=data.xmat[bid].reshape(3,3)@[0.,0.,1.]
            tilt=float(np.degrees(np.arccos(np.clip(body_z[2],-1,1))))
            contact=sum(1 for idx in range(data.ncon) if
                        {int(data.contact[idx].geom1),int(data.contact[idx].geom2)}=={gid,floor})
            renderer.update_scene(data,camera=camera)
            pixels=renderer.render().copy()
            if pixels.ndim!=3 or pixels.shape[2]!=3:raise RuntimeError('RENDERED_FRAME_INVALID')
            frame=cv2.cvtColor(pixels,cv2.COLOR_RGB2BGR)
            cv2.rectangle(frame,(0,0),(440,55),(19,23,35),-1)
            cv2.putText(frame,f'MuJoCo | {spin:.0f} rad/s',(12,23),cv2.FONT_HERSHEY_SIMPLEX,.68,(230,236,255),2)
            cv2.putText(frame,f'tilt={tilt:.1f} deg  contacts={contact}',(12,45),cv2.FONT_HERSHEY_SIMPLEX,.5,(185,216,255),1)
            frames.append(frame)
            rows.append(dict(time_s=float(data.time),tilt_deg=tilt,com_height_m=float(data.xipos[bid,2]),
                             tip_floor_contact=int(contact),angular_speed_rad_s=float(np.linalg.norm(data.qvel[3:]))))
        rates.append(rows);image_sequences.append(frames)
        summaries.append(dict(spin_rad_s=spin,final_tilt_deg=rows[-1]['tilt_deg'],
                              max_tilt_deg=max(r['tilt_deg'] for r in rows),
                              tip_contact_frames=sum(r['tip_floor_contact']>0 for r in rows)))
        with (out/f'mujoco_{int(spin)}_rad_s.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    renderer.close()
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','bgr24',
         '-s','1320x480','-r',str(fps),'-i','-', '-c:v','libx264','-crf','22','-preset','medium',
         '-pix_fmt','yuv420p','-movflags','+faststart',str(out/'mujoco_teapot_comparison.mp4')]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for img in zip(*image_sequences):proc.stdin.write(np.concatenate(img,axis=1).tobytes())
    finally:proc.stdin.close()
    errors=proc.stderr.read().decode('utf8','replace')
    if proc.wait():raise RuntimeError('VIDEO_ENCODING_FAILED: '+errors)
    record=dict(schema='W4RealMuJoCoVideoV1',status='REAL_MUJOCO_EXECUTED',
        engine_version=mujoco.__version__,provenance='DIAGNOSTIC_CGAL_GEOMETRY_NOT_CHERCHI',
        collision_geometry='SIMPLIFIED_SPHERES_NOT_FULL_TEAPOT_SURFACE',
        xml_sha256=sha(xml),video_sha256=sha(out/'mujoco_teapot_comparison.mp4'),
        fps=fps,duration_s=duration,results=summaries)
    (out/'mujoco_video_results.json').write_text(json.dumps(record,indent=2)+'\n')
    return record

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--xml',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--duration',type=float,default=2);p.add_argument('--fps',type=int,default=24)
    a=p.parse_args()
    try:print(json.dumps(run(a.xml,a.out,duration=a.duration,fps=a.fps),indent=2))
    except Exception as e:
        print(f'MUJOCO_VIDEO_BLOCKED: {type(e).__name__}: {e}',file=sys.stderr)
        sys.exit(2)
