#!/usr/bin/env python3
"""Real MuJoCo A/B dynamics for a HYPOTHETICAL 30g mass relocation.

Both cases use identical P2 CGAL proxy visual and collision geometry, the same
MuJoCo integrator, gravity, contact/friction, time, tilt, and angular speed.
Only the full physical body inertia/COM change by transferring a 30g point
mass at z=0.115m to z=0.015m. Not actual geometry/material, NOT a Cherchi
optimized design, NOT a reproduction of the paper's Figure 9.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,os,subprocess,sys,tempfile,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import cv2
from scipy.spatial.transform import Rotation
from p4_mujoco_verified_video import preflight,sha

MASS_TRANSFER_KG=0.030
FROM_Z_M=0.115
TO_Z_M=0.015
SPIN_RAD_S=30.
TILT_DEGREES=5.


def as_arr(s,n):
    a=np.fromstring(s,sep=' ',dtype=np.float64)
    if a.shape!=(n,) or not np.isfinite(a).all():raise ValueError('INVALID_INERTIAL_ARRAY')
    return a


def tensor_of_inertial(node):
    mass=float(node.get('mass'))
    com=as_arr(node.get('pos'),3)
    quat=as_arr(node.get('quat'),4)
    diag=as_arr(node.get('diaginertia'),3)
    if mass<=0 or np.any(diag<=0) or abs(np.linalg.norm(quat)-1)>1e-8:
        raise ValueError('INVALID_INERTIAL_PARAMETERS')
    R=Rotation.from_quat([quat[1],quat[2],quat[3],quat[0]]).as_matrix()
    return mass,com,R@np.diag(diag)@R.T


def parallel_tensor(x):
    return float(x@x)*np.eye(3)-np.outer(x,x)


def make_counterfactual(scene):
    scene=Path(scene)
    p=preflight(scene)
    if p['geometry_source']!='P2_CGAL_PROXY_NOT_CHERCHI':
        raise ValueError('MUST_BE_DECLARED_DIAGNOSTIC_CGAL_PROXY')
    tree=ET.parse(scene)
    inertial=tree.getroot().find('worldbody/body/inertial')
    if inertial is None:raise ValueError('NO_INERTIAL')
    mass,old_com,old_tensor=tensor_of_inertial(inertial)
    dm=MASS_TRANSFER_KG
    if not (0<dm<mass):raise ValueError('INVALID_MASS_TRANSFER')
    source=np.array([0.,0.,FROM_Z_M]);target=np.array([0.,0.,TO_Z_M])
    new_com=old_com + dm/mass*(target-source)
    inertia_at_origin=old_tensor + mass*parallel_tensor(old_com)
    new_inertia_at_origin=inertia_at_origin+dm*(parallel_tensor(target)-parallel_tensor(source))
    new_tensor=.5*((new_inertia_at_origin-mass*parallel_tensor(new_com))+
                   (new_inertia_at_origin-mass*parallel_tensor(new_com)).T)
    eig,basis=np.linalg.eigh(new_tensor)
    if np.any(eig<=0) or 2*max(eig)>sum(eig)+1e-12:
        raise ValueError('MASS_TRANSFER_INVALID_INERTIA')
    if np.linalg.det(basis)<0:basis[:,0]*=-1
    qxyzw=Rotation.from_matrix(basis).as_quat()
    quat=[qxyzw[3],*qxyzw[:3]]
    inertial.set('pos',' '.join(format(float(v),'.16g') for v in new_com))
    inertial.set('quat',' '.join(format(float(v),'.16g') for v in quat))
    inertial.set('diaginertia',' '.join(format(float(v),'.16g') for v in eig))
    variant=scene.parent/'teapot_counterfactual_mass_shift_30g.xml'
    ET.indent(tree,space='  ')
    tree.write(variant,encoding='unicode',xml_declaration=True)
    reloaded=ET.parse(variant).getroot().find('worldbody/body/inertial')
    verify_mass,verify_com,verify_tensor=tensor_of_inertial(reloaded)
    if (abs(verify_mass-mass)>1e-13 or
        not np.allclose(verify_com,new_com,atol=1e-12,rtol=0) or
        not np.allclose(verify_tensor,new_tensor,atol=1e-11,rtol=0)):
        raise ValueError('COUNTERFACTUAL_INERTIA_ROUNDTRIP_FAILED')
    # Only exactly three attributes of the inertial node may change.
    a=ET.parse(scene).getroot(); b=ET.parse(variant).getroot()
    for root in (a,b):
        item=root.find('worldbody/body/inertial')
        for fld in ('pos','quat','diaginertia'):item.set(fld,'CHECKED_INDEPENDENT_TENSOR')
    if ET.tostring(a,encoding='unicode')!=ET.tostring(b,encoding='unicode'):
        raise ValueError('SCENE_NON_INERTIAL_FIELDS_CHANGED')
    report=dict(schema='W4MuJoCoCounterfactualCaseV1',
        status='PHYSICAL_INERTIA_PREPARED_NOT_MUJOCO_RUN',
        scientific_claim='ANALYTIC_MASS_TRANSFER_NOT_CHERCHI_AND_NOT_ACTUAL_MATERIAL',
        frozen_baseline_xml_sha256=sha(scene),variant_xml_sha256=sha(variant),
        visual_mesh_sha256=p['visual_mesh_sha256'],
        mass_kg=mass,moved_mass_kg=dm,source_z_m=FROM_Z_M,destination_z_m=TO_Z_M,
        original_com_m=old_com.tolist(),counterfactual_com_m=new_com.tolist(),
        original_inertia_com_kgm2=old_tensor.tolist(),new_inertia_com_kgm2=new_tensor.tolist(),
        max_inertia_tensor_roundtrip_error=float(np.max(np.abs(verify_tensor-new_tensor))),
        identical_collision_geometry=True,real_mujoco_started=False)
    (scene.parent/'mass_shift_case.json').write_text(json.dumps(report,indent=2)+'\n')
    return variant,report


def csv_dump(path,rows):
    with Path(path).open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def simulate(xml,*,duration,fps,label):
    import mujoco
    model=mujoco.MjModel.from_xml_path(str(Path(xml).resolve()))
    if (model.nq,model.nv)!=(7,6):raise RuntimeError('MUJOCO_MODEL_NOT_SINGLE_FREEBODY')
    data=mujoco.MjData(model)
    bid=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_BODY,'teapot')
    tid=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_GEOM,'virtual_tip_contact')
    floor=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_GEOM,'floor')
    if min(bid,tid,floor)<0:raise RuntimeError('MISSING_SIMULATION_GEOMETRY')
    th=math.radians(TILT_DEGREES)
    data.qpos[:7]=[0,0,float(model.geom_size[tid,0]),math.cos(th/2),math.sin(th/2),0,0]
    data.qvel[:]=0.;data.qvel[5]=SPIN_RAD_S
    mujoco.mj_forward(model,data)
    camera=mujoco.MjvCamera();camera.type=mujoco.mjtCamera.mjCAMERA_FREE
    camera.lookat[:]=[0,0,.065];camera.distance=.54;camera.azimuth=138;camera.elevation=-20
    frames=[]; rows=[]; times=np.linspace(0,duration,int(math.ceil(duration*fps))+1)
    renderer=mujoco.Renderer(model,height=440,width=590)
    try:
        for target in times:
            while data.time<target-1e-10:
                mujoco.mj_step(model,data)
                if not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all():
                    raise RuntimeError('NONFINITE_REAL_MUJOCO_STATE')
            z=np.asarray(data.xmat[bid]).reshape(3,3)@[0,0,1]
            angle=float(np.degrees(np.arccos(np.clip(z[2],-1,1))))
            tip_contacts=sum(1 for k in range(data.ncon) if
                {int(data.contact[k].geom1),int(data.contact[k].geom2)}=={tid,floor})
            rows.append(dict(time_s=float(data.time),tilt_deg=angle,
                com_height_m=float(data.xipos[bid,2]),
                tip_contacts=int(tip_contacts),total_contacts=int(data.ncon),
                angular_speed_rad_s=float(np.linalg.norm(data.qvel[3:6]))))
            renderer.update_scene(data,camera=camera)
            rgb=renderer.render()
            if rgb.shape!=(440,590,3):raise RuntimeError('MUJOCO_RENDER_BAD_FRAME_SHAPE')
            frames.append(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
    finally:renderer.close()
    if len(rows)!=len(times) or len(frames)!=len(times):raise RuntimeError('MISSING_SAMPLES')
    if any(rows[i]['time_s']<=rows[i-1]['time_s'] for i in range(1,len(rows))):
        raise RuntimeError('MUJOCO_NON_MONOTONIC_TIME')
    return frames,rows,mujoco.__version__


def _plot_curve(canvas,rows,i,left,top,width=570):
    bottom=top+90;right=left+width
    cv2.rectangle(canvas,(left,top),(right,bottom),(36,40,48),-1)
    for label in (0,30,60,90,120,150,180):
        y=int(bottom-label/180*90)
        cv2.line(canvas,(left,y),(right,y),(56,58,64),1)
    xy=np.array([(int(left+(k/(len(rows)-1))*width),
                  int(bottom-min(180,max(0,row['tilt_deg']))/180*90))
                  for k,row in enumerate(rows)],dtype=np.int32).reshape(-1,1,2)
    cv2.polylines(canvas,[xy],False,(114,206,241) if i==0 else (130,222,140),2,cv2.LINE_AA)


def export_video(out,frame_list,rows_list,*,fps,duration):
    out=Path(out)
    width,height=1240,680
    def render():
        for k,(a,b) in enumerate(zip(*frame_list)):
            im=np.full((height,width,3),(29,30,40),dtype=np.uint8)
            im[72:512,20:610]=a
            im[72:512,630:1220]=b
            for i,title in enumerate(('ORIGINAL MASS DISTRIBUTION','HYPOTHETICAL 30 g SHIFT')):
                x=24+i*610
                cv2.putText(im,title,(x,32),cv2.FONT_HERSHEY_SIMPLEX,.66,
                            (215,217,240) if i==0 else (162,242,178),2,cv2.LINE_AA)
                cv2.putText(im,f'SAME 30 rad/s | tilt 5 deg | MuJoCo 3.3.7',(x,53),
                            cv2.FONT_HERSHEY_SIMPLEX,.4,(185,191,203),1,cv2.LINE_AA)
                row=rows_list[i][k]
                cv2.putText(im,f"Tilt {row['tilt_deg']:.1f} deg  tip contacts {row['tip_contacts']}",
                            (x,544),cv2.FONT_HERSHEY_SIMPLEX,.55,(219,228,239),1,cv2.LINE_AA)
                _plot_curve(im,rows_list[i],i,x,560,width=570)
                px=x+int(k/max(1,len(rows_list[i])-1)*570)
                cv2.line(im,(px,560),(px,650),(250,250,250),1,cv2.LINE_AA)
            cv2.putText(im,'CGAL diagnostic geometry; mass redistribution NOT Cherchi optimization',(22,671),
                        cv2.FONT_HERSHEY_SIMPLEX,.54,(193,200,227),1,cv2.LINE_AA)
            yield im
    video=out/'mujoco_baseline_vs_hypothetical_mass_shift.mp4'
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','bgr24',
         '-s',f'{width}x{height}','-r',str(fps),'-i','-',
         '-an','-c:v','libx264','-crf','22','-preset','medium',
         '-pix_fmt','yuv420p','-movflags','+faststart',str(video)]
    process=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for frame in render():process.stdin.write(frame.tobytes())
        process.stdin.close();stderr=process.stderr.read().decode();code=process.wait(timeout=120)
        process.stderr.close()
        if code!=0:raise RuntimeError('FFMPEG_FAILED: '+stderr[-500:])
    except Exception:
        process.kill();raise
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries',
        'stream=codec_name,width,height,nb_frames','-select_streams','v:0','-of','json',str(video)],text=True))
    stream=probe['streams'][0]
    if stream['codec_name']!='h264' or int(stream['width'])!=width or int(stream['height'])!=height:
        raise RuntimeError('OUTPUT_VIDEO_PROBE_INVALID')
    return dict(path=video.name,sha256=sha(video),size_bytes=video.stat().st_size,
                codec='h264',frames=int(stream['nb_frames']),fps=fps)


def main(scene,out,*,duration=2.8,fps=24):
    if duration<=0 or fps<5 or fps>60:raise ValueError('INVALID_VIDEO_SETTINGS')
    scene=Path(scene);out=Path(out)
    # No MuJoCo import until the true source and hypothetical inertia pass.
    variant,physics=make_counterfactual(scene)
    try:import mujoco
    except ImportError as ex:raise RuntimeError('REAL_MUJOCO_ENGINE_REQUIRED_NO_SURROGATE') from ex
    out.mkdir(parents=True,exist_ok=True)
    batches=[];version=[]
    for label,xml in [('baseline',scene),('hypothetical_mass_shift',variant)]:
        frames,rows,v=simulate(xml,duration=duration,fps=fps,label=label)
        batches.append((frames,rows));version.append(v)
    if len(set(version))!=1:raise RuntimeError('MUJOCO_ENGINE_VERSION_CHANGED')
    with tempfile.TemporaryDirectory(prefix='w4-mujoco-comparison-',dir=out) as d:
        temp=Path(d)
        for label,(_,rows) in zip(('baseline','hypothetical_mass_shift'),batches):
            csv_dump(temp/f'{label}.csv',rows)
        movie=export_video(temp,[x[0] for x in batches],[x[1] for x in batches],fps=fps,duration=duration)
        for name in ['baseline.csv','hypothetical_mass_shift.csv',movie['path']]:
            os.replace(temp/name,out/name)
    summaries=[]
    for label,(frames,rows) in zip(('baseline','hypothetical_mass_shift'),batches):
        tail=[row for row in rows if row['time_s']>=duration*.75]
        summaries.append(dict(case=label,peak_tilt_deg=max(r['tilt_deg'] for r in rows),
             final_tilt_deg=rows[-1]['tilt_deg'],
             last_quarter_mean_tilt_deg=float(np.mean([r['tilt_deg'] for r in tail])),
             last_quarter_tip_contact_fraction=float(np.mean([r['tip_contacts']>0 for r in tail])),
             csv_sha256=sha(out/f'{label}.csv'),samples=len(rows)))
    report=dict(schema='W4RealMuJoCoCounterfactualComparisonV1',
        status='REAL_MUJOCO_AB_DIAGNOSTIC_EXECUTED',
        engine='MuJoCo',version=version[0],duration_s=duration,fps=fps,
        source_geometry='P2_CGAL_PROXY_NOT_CHERCHI',
        optimization_source='NONE_ANALYTIC_HYPOTHETICAL_MASS_RELOCATION',
        mass_shift=physics,controlled_spin_rad_s=SPIN_RAD_S,
        controlled_tilt_deg=TILT_DEGREES,contact_model='VIRTUAL_SPHERE_PROXY_NOT_REAL_CAD',
        video=movie,results=summaries)
    (out/'mujoco_ab_results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--xml',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--duration',type=float,default=2.8)
    parser.add_argument('--fps',type=int,default=24)
    args=parser.parse_args()
    print(json.dumps(main(args.xml,args.out,duration=args.duration,fps=args.fps),indent=2))
