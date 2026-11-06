"""Compare direct PINO inference with SO(3) orbit-averaged inference."""
from __future__ import annotations
import argparse, json, statistics, time
from pathlib import Path
import torch
from .dataset import generate_splits
from .equivariance import augment_with_random_so3
from .orbit_ensemble import orbit_average, make_so3_orbit
from .spin_pino import SpinPINO
from .train import run_seed

def metrics(pred_r, pred_J, truth_r, truth_J):
    dr=pred_r-truth_r; dJ=pred_J-truth_J
    return {
      "r_mae":float(dr.abs().mean()),
      "J_mae":float(dJ.abs().mean()),
      "r_relative_l2":float(dr.norm()/truth_r.norm().clamp_min(1e-12)),
      "J_relative_l2":float(dJ.norm()/truth_J.norm().clamp_min(1e-12)),
    }

def run(seeds=(131,137,139), views=(1,2,4), steps=120):
    torch.set_num_threads(1); rows=[]
    for seed in seeds:
      trained=run_seed(seed=seed,steps=steps,batch_size=8,grid_size=8,
        points_per_axis=6,smoothing=0.02,moment_parameterization="logistic_atom",
        temperature=0.12,device="cpu")
      model=SpinPINO(width=4,modes=2,n_layers=2,grid_size=8,
        points_per_axis=6,hidden_dim=48,smoothing=0.02,
        moment_parameterization="logistic_atom",temperature=0.12)
      model.load_state_dict(trained["checkpoint_state"]); model.eval()
      data=generate_splits(seed=seed,train_geometries_per_family=16,
        test_ellipsoid_geometries=8,queries_per_geometry=2,grid_size=8)["test"]
      rotated=augment_with_random_so3(data,seed=seed+900001)
      D,c,r,J,meta=rotated
      # Only appended rotated test cases are scored.
      n=len(data[0]); D,c,r,J=D[n:],c[n:],r[n:],J[n:]
      rho_occ=(D[:,0:1]*D[:,1:2]).sum(dim=(1,2,3,4))
      base_occ=(data[0][:,0:1]*data[0][:,1:2]).sum(dim=(1,2,3,4))
      interp_rel=((rho_occ-base_occ).abs()/base_occ.abs().clamp_min(1e-12)).mean()
      with torch.no_grad():
        z=model.encode_geometry(D); direct_r=model.moment_from_weights(z,c)
        direct_J=model.jacobian_from_weights(z,c)
      seed_row={"seed":seed,"interpolation_mass_relative_error":float(interp_rel),"conditions":[]}
      for k in views:
        rot=make_so3_orbit(k,seed=seed+700001,dtype=D.dtype,device=D.device)
        start=time.perf_counter()
        with torch.no_grad():
          if k==1:
            out={"moments":direct_r,"jacobian":direct_J}
          else:
            out=orbit_average(model,D,c,rot,with_jacobian=True)
        elapsed=time.perf_counter()-start
        m=metrics(out["moments"],out["jacobian"],r,J)
        seed_row["conditions"].append({"views":k,**m,"inference_seconds":elapsed})
      rows.append(seed_row)
    aggregate=[]
    for k in views:
      items=[x["conditions"][list(views).index(k)] for x in rows]
      aggregate.append({"views":k,**{
        key:statistics.mean(x[key] for x in items)
        for key in ("r_mae","J_mae","r_relative_l2","J_relative_l2","inference_seconds")
      }})
    return {"schema":"SPIN_PINO_M7E_ORBIT_ENSEMBLE_V1",
      "label_source":"ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI",
      "same_rotated_test_cases":True,"seeds":list(seeds),"views":list(views),
      "aggregate":aggregate,"per_seed":rows,
      "claims":{"cherchi_supervised":False,"newton_admitted":False,
        "arbitrary_quadric_certified":False,"real_spin_end_to_end_validated":False}}

def main():
 p=argparse.ArgumentParser();p.add_argument("--seeds",default="131,137,139")
 p.add_argument("--views",default="1,2,4");p.add_argument("--steps",type=int,default=120)
 p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 result=run(tuple(int(x) for x in a.seeds.split(",")),
   tuple(int(x) for x in a.views.split(",")),a.steps)
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
 print(json.dumps(result["aggregate"],indent=2))
if __name__=="__main__": main()
