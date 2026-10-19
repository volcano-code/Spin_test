#!/usr/bin/env python3
"""Numerical fixed-pivot heavy-top model (NOT MuJoCo / NOT Cherchi).

Uses the original model's exact signed-mesh integral inertia from a previously
frozen CGAL diagnostic *proxy* teapot (NOT Spin-It / Cherchi optimized shape).
The pivot is constrained, contact/friction are disabled, torque is gravity.
Scientific role: illustrate dynamics and visually debug the future MuJoCo scene.
"""
import argparse, hashlib, json, time
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
from scipy.spatial.transform import Rotation

ASSET_SHA = 'd3289193185192ebca4d63fc813bd77d96810051089c672e887accdf3205b331'
G=9.81

def h(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def qmul(q,r):
    a,b,c,d=q; e,f,g,h=r
    return np.array([a*e-b*f-c*g-d*h, a*f+b*e+c*h-d*g, a*g-b*h+c*e+d*f, a*h+b*g-c*f+d*e])

def R_of_q(q):
    q=np.asarray(q,dtype=float)
    q=q/np.linalg.norm(q)
    return Rotation.from_quat(np.array([q[1],q[2],q[3],q[0]])).as_matrix()

def simulate(case, mesh_path, total=2.8, step=0.02, rates=(0.,30.,60.), tilt=5.):
    assert h(mesh_path)==ASSET_SHA, 'PROVENANCE_SHA_MISMATCH'
    p=json.loads(Path(case).read_text())
    d=p['physical_parameters'];m=float(d['physical_mass_kg'])
    com=np.asarray(d['com_m'],dtype=float)
    I_com=np.asarray(d['inertia_com_kg_m2'],dtype=float)
    I=I_com+m*(np.dot(com,com)*np.eye(3)-np.outer(com,com))
    Iinv=np.linalg.inv(I)
    theta=np.radians(tilt)
    q0=np.array([np.cos(theta/2),np.sin(theta/2),0,0])
    t_eval=np.linspace(0,total,int(round(total/step))+1)
    rows=[];summary=[]
    for spin in rates:
        def f(t,y):
            q=y[:4]; omega=y[4:]
            R=R_of_q(q)
            gravity_body=R.T@np.array([0.,0.,-m*G])
            torque=np.cross(com,gravity_body)
            d_omega=Iinv@(torque-np.cross(omega,I@omega))
            d_q=0.5*qmul(q,[0.,*omega])
            return np.hstack([d_q,d_omega])
        y0=np.r_[q0,[0.,0.,float(spin)]]
        t0=time.monotonic()
        sol=solve_ivp(f,(0.,total),y0,method='DOP853',t_eval=t_eval,rtol=2e-10,atol=1e-12,max_step=.012)
        if not sol.success:raise RuntimeError(sol.message)
        E=[];Lz=[];theta_seq=[]
        for k,t in enumerate(t_eval):
            q=sol.y[:4,k];omega=sol.y[4:,k]
            R=R_of_q(q)
            vertical=R@[0.,0.,1.]
            angle=np.degrees(np.arccos(np.clip(vertical[2],-1,1)))
            com_world=R@com
            kinetic=float(.5*omega@(I@omega))
            energy=kinetic+m*G*com_world[2]
            vertical_L=float((R@I@omega)[2])
            row=dict(rate_rad_s=float(spin),time_s=float(t),tilt_deg=float(angle),com_z_m=float(com_world[2]),
                     omega_body_x=float(omega[0]),omega_body_y=float(omega[1]),omega_body_z=float(omega[2]),
                     quat_w=float(q[0]),quat_x=float(q[1]),quat_y=float(q[2]),quat_z=float(q[3]),
                     energy_J=energy,vertical_angular_momentum=vertical_L)
            rows.append(row);E.append(energy);Lz.append(vertical_L);theta_seq.append(angle)
        summary.append(dict(spin_rad_s=spin,final_tilt_deg=theta_seq[-1],
             max_tilt_deg=max(theta_seq),first_60deg_time_s=next((r['time_s'] for r in rows if r['rate_rad_s']==spin and r['tilt_deg']>=60),None),
             mean_last_quarter_tilt_deg=float(np.mean(theta_seq[int(.75*len(theta_seq)):])) ,
             peak_relative_energy_error=max(abs(e-E[0]) for e in E)/max(1e-12,abs(E[0])),
             peak_absolute_vertical_angular_momentum_error=max(abs(l-Lz[0]) for l in Lz),
             integration_wall_s=time.monotonic()-t0))
    return rows,summary,dict(schema='W4FixedPivotSurrogateV1',engine='SciPy solve_ivp DOP853',not_mujoco=True,
        not_cherchi=True,geometry='CGAL_DIAGNOSTIC_PROXY',asset_sha256=h(mesh_path),
        physics='fixed_pivot_heavy_top_gravity_only_no_contact_no_friction',
        virtual_tip='body_origin_pivot',mass_kg=m,com_body_m=com.tolist(),I_pivot_kgm2=I.tolist(),
        initial_tilt_deg=tilt,dt_output_s=step,duration_s=total,initial_angular_velocity_body_z_rad_s=list(rates),
        energy_conservation_label='numeric_invariant_only_not_physical_validation')

if __name__=='__main__':
    import csv
    pa=argparse.ArgumentParser();pa.add_argument('--asset',required=True);pa.add_argument('--manifest',required=True)
    pa.add_argument('--out',required=True);pa.add_argument('--duration',type=float,default=2.8)
    args=pa.parse_args(); rows,s,meta=simulate(args.manifest,args.asset,total=args.duration)
    o=Path(args.out);o.mkdir(parents=True,exist_ok=True)
    with (o/'reference_trajectories.csv').open('w',newline='') as fp:
        w=csv.DictWriter(fp,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    meta.update(results=s,trajectory_sha256=h(o/'reference_trajectories.csv'))
    (o/'reference_summary.json').write_text(json.dumps(meta,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'results':s,'trajectory_sha256':meta['trajectory_sha256']},indent=2))
