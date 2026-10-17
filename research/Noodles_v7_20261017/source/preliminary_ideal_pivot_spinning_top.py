"""Exploratory gravity-driven rigid body with a frictionless FIXED pivot.

This is an explicit, limited mechanical benchmark for before/after *computed*
Noodles v7 mass properties. It does NOT model ground contacts, collisions,
friction, manufacturing, user spin-up, or the paper's full simulation protocol.
"""
import argparse,json,time
from pathlib import Path
import numpy as np,trimesh
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

p=argparse.ArgumentParser();p.add_argument('--initial',type=Path,required=True);p.add_argument('--optimized',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)

def qmul(q,r):
 w,x,y,z=q;a,b,c,d=r
 return np.array([w*a-x*b-y*c-z*d,w*b+x*a+y*d-z*c,w*c-x*d+y*a+z*b,w*d+x*c-y*b+z*a])
def Rof(q):
 q=q/np.linalg.norm(q);w,x,y,z=q
 return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                  [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                  [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
def properties(path):
 mesh=trimesh.load(path,force='mesh',process=False)
 if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume<=0:raise ValueError('UNSAFE_MESH')
 m=mesh.volume*1e-9*1200.; cm=np.asarray(mesh.center_mass)*1e-3
 tip=np.array([0.,0.,-0.004]) # frozen model bottom-most point -4mm
 if abs(mesh.bounds[0,2]*1e-3-tip[2])>1e-10:raise ValueError('TIP_HEIGHT_MISMATCH')
 r=cm-tip
 Ic=np.asarray(mesh.moment_inertia)*1e-15*1200.
 I=Ic+m*(np.dot(r,r)*np.eye(3)-np.outer(r,r))
 if np.min(np.linalg.eigvalsh(I))<=0:raise ValueError('NON_POSITIVE_INERTIA')
 return dict(m=m,r=r,I=I,cm=cm,Tip=tip,obj=str(path),faces=len(mesh.faces))
def benchmark(P,omega,initial_tilt_deg=10.,duration=2.0,max_step=.003):
 m,r,I=P['m'],P['r'],P['I'];inverse=np.linalg.inv(I)
 tilt=np.deg2rad(initial_tilt_deg);y0=np.r_[np.array([np.cos(tilt/2),np.sin(tilt/2),0.,0.]),[0.,0.,float(omega)]]
 t_eval=np.linspace(0,duration,401)
 def f(t,y):
  q=y[:4];w=y[4:]
  rot=Rof(q);gbody=rot.T @ np.array([0.,0.,-9.81*m]);torque=np.cross(r,gbody)
  dwdt=inverse@(torque-np.cross(w,I@w));dq=.5*qmul(q,np.r_[0.,w])
  return np.r_[dq,dwdt]
 result=solve_ivp(f,(0,duration),y0,method='DOP853',rtol=2e-10,atol=2e-12,max_step=max_step,t_eval=t_eval)
 if not result.success:raise RuntimeError('IVP_FAILED:'+result.message)
 angles=[];energy=[];Lz=[];omegaZ=[]
 for yi in result.y.T:
  q=yi[:4];w=yi[4:];rot=Rof(q)
  axis=rot[:,2]
  angles.append(np.rad2deg(np.arccos(np.clip(axis[2],-1,1))))
  energy.append(.5*w@(I@w)+m*9.81*(rot@r)[2]);Lz.append((rot@(I@w))[2]);omegaZ.append(w[2])
 angles=np.asarray(angles);energy=np.asarray(energy);Lz=np.asarray(Lz)
 record=dict(model=P['obj'],spin_rad_s=omega,initial_tilt_deg=initial_tilt_deg,max_step=max_step,
    max_tilt_deg=float(angles.max()),min_tilt_deg=float(angles.min()),
    max_deviation_from_initial_deg=float(np.max(abs(angles-initial_tilt_deg))),
    rms_tilt_change_deg=float(np.sqrt(np.mean((angles-initial_tilt_deg)**2))),
    relative_energy_drift=float(np.max(abs(energy-energy[0]))/max(1e-12,abs(energy[0]))),
    relative_world_z_angular_momentum_drift=float(np.max(abs(Lz-Lz[0]))/max(1e-12,abs(Lz[0]))))
 return record,np.column_stack((t_eval,angles,omegaZ,energy,Lz))

start=time.monotonic();record={'schema':'spin-v7-ideal-frictionless-fixed-tip-pivot-only-v1','full_contact_simulation':False,
 'status':'EXPLORATORY_NOT_PAPER_PHYSICS','model_source':'independent_trimesh_mass_inertia_from_exact_union_OBJ',
 'tip_m':[0,0,-.004], 'gravity_m_s2':9.81, 'torque':'r_body cross (R_body_to_world.T * gravity_world)',
 'motor_torque':0, 'damping':0, 'contact_friction':'not_modeled_ideal_pinned_pivot',
 'material_density_kg_m3':1200.,'tested':[]}
meshes={'initial':properties(a.initial),'optimized':properties(a.optimized)}
for key,v in meshes.items():record[key+'_physical']={k:(val.tolist() if isinstance(val,np.ndarray) else val) for k,val in v.items()}
for spin in (100.,160.):
 runs={}
 for key,prop in meshes.items():
  coarse,data_coarse=benchmark(prop,spin,max_step=.003)
  fine,data_fine=benchmark(prop,spin,max_step=.0015)
  diff=float(np.max(abs(data_fine[:,1]-data_coarse[:,1])))
  runs[key]=dict(record=coarse,independent_step=fine,time_step_max_angle_difference_deg=diff,
                 verified_integration_consistency=bool(diff<.005 and fine['relative_energy_drift']<2e-5
                                                  and fine['relative_world_z_angular_momentum_drift']<2e-5))
  np.savetxt(a.out/f'{key}-{int(spin)}rads-fixed-pivot.csv',data_fine,
       delimiter=',',header='time_s,tilt_deg,body_spin_omega_z_rad_s,total_energy_J,world_vertical_L_kgm2s',comments='')
 fig,ax=plt.subplots(figsize=(9,4.5))
 for k in ('initial','optimized'):
  data=np.loadtxt(a.out/f'{k}-{int(spin)}rads-fixed-pivot.csv',delimiter=',',skiprows=1)
  ax.plot(data[:,0],data[:,1],label=k)
 ax.set(xlabel='Time (s)',ylabel='Body axis tilt (deg)',title=f'Ideal pinned tip only; initial spin {spin:.0f} rad/s (NOT contact dynamics)')
 ax.legend();ax.grid(True,alpha=.25);fig.tight_layout();fig.savefig(a.out/f'fixed-pivot-tilt-{int(spin)}.png',dpi=160);plt.close(fig)
 record['tested'].append(dict(spin_rad_s=spin,**runs))
print(json.dumps({'comparisons':[{k:r[k]['record']['max_deviation_from_initial_deg'] for k in ('initial','optimized')} for r in record['tested']], 'step_checks':[r['initial']['verified_integration_consistency'] and r['optimized']['verified_integration_consistency'] for r in record['tested']]},indent=2))
record['elapsed_seconds']=time.monotonic()-start
(a.out/'report.json').write_text(json.dumps(record,indent=2,allow_nan=False))
