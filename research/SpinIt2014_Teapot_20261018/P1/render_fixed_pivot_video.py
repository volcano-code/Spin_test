#!/usr/bin/env python3
"""Render REAL numerical fixed-pivot SciPy reference trajectories.
NOT a MuJoCo integration and NOT a Cherchi-optimized output.
The video adds no synthetic contacts or manufactured dynamics samples.
"""
from pathlib import Path
import argparse,csv,json,math,subprocess,hashlib,time
import numpy as np
import cv2
import trimesh
from PIL import Image,ImageDraw,ImageFont
from scipy.spatial.transform import Rotation,Slerp

FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
EPS=1e-12


def point(bgr):return tuple(map(int,bgr))

def text(img,value,xy,size=.62,color=(225,235,248),bold=False):
    cv2.putText(img,str(value),xy,cv2.FONT_HERSHEY_DUPLEX if bold else cv2.FONT_HERSHEY_SIMPLEX,
                size,color,1 if not bold else 2,cv2.LINE_AA)


def smooth_line(img,points,color,thickness=2):
    a=np.asarray(points,dtype=np.int32).reshape(-1,1,2)
    if len(a)>1:cv2.polylines(img,[a],False,color,thickness,cv2.LINE_AA)


def make_base(width,height,summary):
    canvas=np.zeros((height,width,3),dtype=np.uint8)
    # Matte indigo background with a restrained vertical light gradient.
    for y in range(height):
        x=y/height
        canvas[y,:]=(int(25-6*x),int(19-7*x),int(15-6*x))
    for i,accent in enumerate(((80,180,252),(153,220,120),(245,173,123))):
        x0=25+i*470;xr=x0+452
        cv2.rectangle(canvas,(x0,138),(xr,586),(38,38,49),-1)
        cv2.rectangle(canvas,(x0,138),(xr,586),(71,66,72),1,cv2.LINE_AA)
        cv2.rectangle(canvas,(x0,138),(xr,144),accent,-1)
        cv2.rectangle(canvas,(x0,606),(xr,777),(36,35,47),-1)
        cv2.rectangle(canvas,(x0,606),(xr,777),(71,66,72),1,cv2.LINE_AA)
        if i==0:subtitle='0 rad/s  |  NO INITIAL SPIN'
        elif i==1:subtitle='30 rad/s  |  MODERATE SPIN'
        else:subtitle='60 rad/s  |  HIGH SPIN'
        text(canvas,subtitle,(x0+17,183),.70,accent,True)
        text(canvas,f'Max tilt: {summary[i]["max_tilt_deg"]:.1f} deg',(x0+17,214),.55,(173,178,197))
        text(canvas,'Fixed pivot  /  no surface contact',(x0+17,570),.46,(157,162,181))
        cx,cy=x0+225,502
        # Light dashed vertical world axis for reference.
        for yr in range(288,502,18):
            cv2.line(canvas,(cx,yr),(cx,min(yr+8,502)),(96,100,119),1,cv2.LINE_AA)
        # Oblique reference plane through constrained pivot; not a collision surface.
        cv2.line(canvas,(x0+44,508),(xr-44,508),(71,80,95),1,cv2.LINE_AA)
        cv2.circle(canvas,(cx,cy),5,accent,-1,cv2.LINE_AA)
        text(canvas,'VIRTUAL PIVOT',(cx-62,528),.4,(131,141,167))
        tx0=x0+34;tx1=xr-26;ty0=647;ty1=745
        for degree in (0,60,120,180):
            yy=int(ty1-(ty1-ty0)*degree/180)
            cv2.line(canvas,(tx0,yy),(tx1,yy),(54,55,68),1,cv2.LINE_AA)
            text(canvas,str(degree),(x0+4,yy+4),.35,(125,133,159))
        text(canvas,'TILT ANGLE (deg)',(tx0,632),.5,(173,180,201))
        text(canvas,'0 s',(tx0,765),.38,(133,141,167))
        text(canvas,'2.8 s',(tx1-39,765),.38,(133,141,167))
    # Chinese + English upper title.
    im=Image.fromarray(cv2.cvtColor(canvas,cv2.COLOR_BGR2RGB))
    draw=ImageDraw.Draw(im)
    font=ImageFont.truetype(FONT,34,index=0)
    draw.text((28,15),'Utah Teapot 旋转动力学对照',fill=(248,249,255),font=font)
    font2=ImageFont.truetype(FONT,19,index=0)
    draw.text((29,68),'SciPy 固定枢轴参考模拟 · 使用实际网格惯性矩 · 非 MuJoCo / 非 Cherchi 优化',fill=(175,188,209),font=font2)
    draw.text((29,101),'2.8 s 物理时间 / 5.6 s 慢放视频  |  m=0.25 kg, 高度=0.15 m, 初始倾角=5°, 重力=9.81 m/s²',fill=(163,177,196),font=font2)
    base=cv2.cvtColor(np.asarray(im),cv2.COLOR_RGB2BGR)
    text(base,'NO COLLISION · NO FRICTION · NOT A SPIN-IT EXPERIMENT',(29,height-13),.46,(140,153,178))
    return base


def render_frame(frame,mesh,body_normals,body_centers,quat_by_rate,tilts,complete_tilts,
                 elapsed,summary,params,width,height):
    cam=np.array([.52,-1.,.55]);cam/=np.linalg.norm(cam)
    right=np.cross([0,0,1.],cam);right/=np.linalg.norm(right)
    up=np.cross(cam,right);up/=np.linalg.norm(up)
    light=np.array([.26,-.45,.86]);light/=np.linalg.norm(light)
    basis=np.vstack([right,up])
    verts=np.asarray(mesh.vertices,dtype=float)*params['scale']
    faces=np.asarray(mesh.faces,dtype=np.int32)
    for i in range(3):
        x0=25+i*470; cx=x0+225;cy=502
        R=quat_by_rate[i].as_matrix()
        # All 3D locations are the real saved state at this simulated instant.
        pos=verts@R.T
        screen=pos@basis.T
        pp=np.column_stack([cx+screen[:,0]*1040,cy-screen[:,1]*1040]).astype(np.int32)
        ns=body_normals@R.T
        fc=body_centers@R.T
        front=np.flatnonzero((ns@cam)>0.001)
        draworder=front[np.argsort(fc[front]@cam)]
        diff=np.maximum(0.,ns@light)
        accent=((80,180,252),(153,220,120),(245,173,123))[i]
        base_bgr=np.array(accent,dtype=float)
        # Draw the teapot with a painter pass; no fake rotation interpolation.
        for face_index in draworder:
            poly=pp[faces[face_index]]
            if np.any(poly[:,0]<x0+3) or np.any(poly[:,0]>x0+449) or np.any(poly[:,1]<234) or np.any(poly[:,1]>555):
                continue
            shade=.43+.46*diff[face_index]+.08*max(0,ns[face_index]@cam)
            color=np.minimum(255,base_bgr*shade+np.array([14.,13.,15.])).astype(int)
            cv2.fillConvexPoly(frame,poly,color.tolist(),cv2.LINE_AA)
        # Draw reference body local z-axis and tip location.
        end=R@np.array([0.,0.,.16])
        px=int(cx+np.dot(end,right)*1040);py=int(cy-np.dot(end,up)*1040)
        cv2.arrowedLine(frame,(cx,cy),(px,py),(58,200,255),3,cv2.LINE_AA,tipLength=.10)
        cv2.circle(frame,(cx,cy),6,(73,79,245),-1,cv2.LINE_AA)
        angle=tilts[i]
        text(frame,f'{angle:5.1f}',(x0+20,267),1.26,(255,255,255),True)
        text(frame,'deg tilt',(x0+153,264),.55,(189,195,215))
        # Real-time chart through this simulation time.
        tx0=x0+34;tx1=x0+426;ty0=647;ty1=745
        vals=complete_tilts[i]
        pts=np.column_stack([tx0+np.linspace(0,1,len(vals))*(tx1-tx0),ty1-np.clip(vals,0,180)/180*(ty1-ty0)])
        smooth_line(frame,pts,(72,74,86),2)
        endi=max(1,int(round(elapsed/params['dt'])))
        smooth_line(frame,pts[:endi+1],accent,3)
        nowi=min(len(pts)-1,endi)
        cv2.circle(frame,tuple(pts[nowi].astype(int)),5,accent,-1,cv2.LINE_AA)
        text(frame,f'Current: {angle:.1f} deg',(x0+194,633),.49,(209,214,229))
    text(frame,f'SIM TIME {elapsed:0.2f} s',(1131,height-13),.57,(232,236,247),True)
    return frame


def main():
    pa=argparse.ArgumentParser()
    pa.add_argument('--asset',required=True)
    pa.add_argument('--manifest',required=True)
    pa.add_argument('--csv',required=True)
    pa.add_argument('--summary',required=True)
    pa.add_argument('--out',required=True)
    pa.add_argument('--poster',required=True)
    pa.add_argument('--fps',type=int,default=30)
    args=pa.parse_args()
    data=json.loads(Path(args.summary).read_text())
    assert data['not_mujoco'] is True and data['not_cherchi'] is True
    assert hashlib.sha256(Path(args.asset).read_bytes()).hexdigest()==data['asset_sha256']
    mesh=trimesh.load_mesh(args.asset,process=False)
    # Display-only clustering of CGAL proxy mesh; all dynamics are full-res.
    v0=np.asarray(mesh.vertices)
    keys=np.round(v0/0.25).astype(np.int32)
    _,inverse=np.unique(keys,axis=0,return_inverse=True)
    count=np.bincount(inverse)
    vv0=np.zeros((len(count),3))
    np.add.at(vv0,inverse,v0)
    vv0/=count[:,None]
    faces_render=inverse[np.asarray(mesh.faces)]
    good=(faces_render[:,0]!=faces_render[:,1])&(faces_render[:,1]!=faces_render[:,2])&(faces_render[:,0]!=faces_render[:,2])
    mesh=trimesh.Trimesh(vertices=vv0,faces=faces_render[good],process=False)
    print('render_faces',len(mesh.faces),'full_faces',len(faces_render),flush=True)
    faces=np.asarray(mesh.faces)
    vv=np.asarray(mesh.vertices)
    body_centers=vv[faces].mean(axis=1)*json.loads(Path(args.manifest).read_text())['physical_parameters']['scale']
    n=np.cross(vv[faces[:,1]]-vv[faces[:,0]],vv[faces[:,2]]-vv[faces[:,0]])
    n/=np.maximum(1e-30,np.linalg.norm(n,axis=1,keepdims=True))
    groups={k:[] for k in (0,30,60)}
    with open(args.csv,newline='') as f:
        for row in csv.DictReader(f):groups[int(float(row['rate_rad_s']))].append({k:float(v) for k,v in row.items()})
    times=np.array([row['time_s'] for row in groups[0]])
    T=float(times[-1]);nframes=round(2*T*args.fps)+1
    assert all(len(g)==len(times) for g in groups.values())
    interpolators=[];all_tilts=[]
    for k in (0,30,60):
        q=np.array([[r['quat_x'],r['quat_y'],r['quat_z'],r['quat_w']] for r in groups[k]])
        interpolators.append(Slerp(times,Rotation.from_quat(q)))
        all_tilts.append(np.array([r['tilt_deg'] for r in groups[k]]))
    W,H=1440,810
    bg=make_base(W,H,data['results'])
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-vcodec','rawvideo',
         '-pix_fmt','bgr24','-s',f'{W}x{H}','-r',str(args.fps),'-i','-',
         '-an','-c:v','libx264','-crf','21','-preset','veryfast','-pix_fmt','yuv420p',
         '-movflags','+faststart',args.out]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    tic=time.monotonic()
    poster_saved=False
    try:
        for k in range(nframes):
            simt=min(T,k/args.fps*.5)
            frame=bg.copy()
            qs=[obj([simt])[0] for obj in interpolators]
            tilts=[float(np.interp(simt,times,t)) for t in all_tilts]
            render_frame(frame,mesh,n,body_centers,qs,tilts,all_tilts,simt,data['results'],
                         dict(scale=json.loads(Path(args.manifest).read_text())['physical_parameters']['scale'],dt=times[1]-times[0]),W,H)
            proc.stdin.write(frame.tobytes())
            if not poster_saved and simt>=.66:
                cv2.imwrite(args.poster,frame);poster_saved=True
            if k%30==0:print(f'frame {k}/{nframes} sim={simt:.2f}s elapsed={time.monotonic()-tic:.1f}s',flush=True)
    finally:
        proc.stdin.close()
    err=proc.stderr.read().decode('utf8','replace')
    ret=proc.wait()
    if ret!=0:raise RuntimeError('ffmpeg failed: '+err)
    print('VIDEO',args.out,'BYTES',Path(args.out).stat().st_size,'SECONDS',time.monotonic()-tic)

if __name__=='__main__':main()
