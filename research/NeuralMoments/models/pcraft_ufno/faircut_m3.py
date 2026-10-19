"""W6 M3: same physical-cut analytic labels and matched training budget.

Three *real network implementations* are run locally: current W6 UFNO-Moment
and pinned W5 DeepONet/GeometryMLP source snapshots. Their only change is a
required 9D, parameter-free *voxel-derived* adapter for W5; W6 sees complete
4-channel voxel geometry. Both obtain information solely from the same input
voxels, but that 9D summary is lossy and does NOT establish representation
parity. The W5 source's original privileged 9D primitive descriptors are
intentionally forbidden. This is a conditional architectural smoke comparison,
not a fair production ranking or a W2 native/Cherchi teacher evaluation.

Run from repo root:
python -m research.NeuralMoments.models.pcraft_ufno.faircut_m3 --output ...
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import resource
import statistics
import time
from typing import Callable

import torch
from torch import Tensor

from .adaptation import ResidualAdapter
from .analytic_cut import (GeometrySpec, TEACHER_KIND, assert_disjoint_family_splits,
                           sample_dataset, vertical_cut_truth, voxel_geometry)
from .model import UFNOMoment, count_real_parameters
from .w5_snapshot.deeponet.model import DeepONetMoment
from .w5_snapshot.geometry_mlp.model import GeometryMLPMoment

W0_COMMIT = "bfedacd3a1f4e10d30f1258331260380739d243c"
W2_COMMIT = "ab93ccd6b894978311773b0f8a8b6b9c40d696ab"
W5_COMMIT = "7054cf6624eeb85f8ba06093090127bdb8016dc4"
W5_SNAPSHOT_BLOBS = {
    "deeponet_model": "7aa363769c0baf9f843d50e268164e761b566977",
    "geometry_mlp_model": "85db98ec60926a653270020f05294a7347221dcb",
    "interface": "9d776e5c324140899f03296ee96dbfad602f8836",
}
MODELS = ("ufno", "deeponet", "geometry_mlp")
ARMS = ("moment_only", "moment_and_jacobian")
B_DIAG = [1.0] * 7 + [2.0] * 3


def voxel_summary9(voxels: Tensor) -> Tensor:
    """Nine deterministic raw occupancy moments, no family / analytic parameters.

    (mass fraction, centroid xyz, variance xyz, covariance xy, covariance xz)
    computed exclusively from the same 4-channel voxel samples given to W6.
    Preprocessing is timed in cold W5 evaluation and uses zero learnable weights.
    """
    if voxels.ndim != 5 or voxels.shape[1] != 4 or not voxels.is_floating_point():
        raise ValueError("expected [B,4,Nx,Ny,Nz] floating voxel data")
    if not bool(torch.isfinite(voxels).all()):
        raise ValueError("voxels must be finite")
    if any(n < 4 for n in voxels.shape[2:]):
        raise ValueError("invalid voxel size")
    # C=0 is density and C=1 is sampled occupancy. Do not insert analytic
    # primitive type, exact semiaxes, cut labels, or heldout family metadata.
    rho = voxels[:, 0]
    coords = [torch.linspace(-1, 1, int(n),device=voxels.device,dtype=voxels.dtype)
              for n in voxels.shape[2:]]
    xyz = torch.stack(torch.meshgrid(*coords,indexing="ij"),dim=0)
    mass = rho.sum(dim=(1,2,3)).clamp_min(1e-8)
    mean = torch.einsum("bxyz,ixyz->bi",rho,xyz) / mass.unsqueeze(-1)
    centered = xyz.unsqueeze(0) - mean[:,:,None,None,None]
    variance = (rho.unsqueeze(1)*centered.square()).sum((-3,-2,-1)) / mass.unsqueeze(-1)
    cov_xy = (rho*centered[:,0]*centered[:,1]).sum((-3,-2,-1)) / mass
    cov_xz = (rho*centered[:,0]*centered[:,2]).sum((-3,-2,-1)) / mass
    return torch.cat((rho.mean((1,2,3)).unsqueeze(1),mean,variance,
                      cov_xy.unsqueeze(1),cov_xz.unsqueeze(1)),dim=-1)


def dataset_sha256(dataset) -> str:
    """Content digest of all voxel inputs, oracle c/r/J and geometry metadata."""
    d,c,r,J,meta=dataset
    digest=hashlib.sha256()
    for tensor in (d,c,r,J):
        arr=tensor.detach().contiguous().cpu().numpy()
        digest.update(str((arr.shape,str(arr.dtype))).encode('ascii'))
        digest.update(arr.tobytes())
    digest.update(json.dumps(meta,sort_keys=True,separators=(',',':')).encode('utf-8'))
    return digest.hexdigest()


def _make_model(name: str, seed: int, grid_size: int) -> torch.nn.Module:
    torch.manual_seed(seed)
    if name == "ufno":
        return UFNOMoment(width=4,modes=3,latent_dim=24,head_width=40,
                          grid_size=grid_size).float()
    if name == "deeponet":
        return DeepONetMoment().float()
    if name == "geometry_mlp":
        return GeometryMLPMoment().float()
    raise ValueError(f"unknown model {name}")


def prepare_geometry(name: str, voxels: Tensor) -> Tensor:
    if name not in MODELS:
        raise ValueError("invalid architecture")
    return voxels if name == "ufno" else voxel_summary9(voxels)


def get_cached(model, name: str, voxels: Tensor) -> Tensor:
    return model.encode_geometry(prepare_geometry(name,voxels))


def _same_minibatches(length: int, steps: int, batch_size: int, seed: int) -> Tensor:
    if length<=0 or steps<0 or batch_size<=0:
        raise ValueError("invalid minibatch schedule")
    rng=torch.Generator().manual_seed(seed)
    return torch.randint(length,(steps,batch_size),generator=rng)


def train(model, name: str, dataset, *, schedule: Tensor,
          derivative_enhanced: bool, lr: float=.003) -> dict:
    d,c,r,J,_=dataset
    if name not in MODELS or schedule.ndim!=2 or not (torch.isfinite(schedule.float()).all()):
        raise ValueError("invalid training arguments")
    optimizer=torch.optim.Adam(model.parameters(),lr=lr)
    model.train()
    t0=time.perf_counter()
    last={"r_loss":None,"J_loss":None}
    for idx in schedule:
        z=get_cached(model,name,d[idx])
        prediction=model.moment(z,c[idx])
        loss_r=(prediction-r[idx]).square().mean()
        total=loss_r
        loss_j=None
        if derivative_enhanced:
            predicted_J=model.jacobian(z,c[idx])
            loss_j=(predicted_J-J[idx]).square().mean()
            total=total+0.5*loss_j
        optimizer.zero_grad(set_to_none=True)
        total.backward()
        optimizer.step()
        last={"r_loss":float(loss_r.detach()),
              "J_loss":float(loss_j.detach()) if loss_j is not None else None}
    return {"steps":int(schedule.shape[0]),"batch_size":int(schedule.shape[1]),
            "lr":lr,"derivative_enhanced":derivative_enhanced,
            "analytic_training_queries":int(len(d)),
            "oracle_J_used":derivative_enhanced,
            "cpu_train_seconds":time.perf_counter()-t0,"gpu_hours":0.0,
            **last}


def evaluate(model,name: str,dataset) -> dict:
    d,c,r,J,_=dataset
    model.eval()
    with torch.no_grad():
        z=get_cached(model,name,d)
        r_hat=model.moment(z,c)
    j_hat=model.jacobian(z.detach(),c)
    unit_direction=torch.arange(1,11,device=c.device,dtype=c.dtype)
    unit_direction=unit_direction/unit_direction.norm()
    dr_true=torch.matmul(J,unit_direction)
    dr_pred=torch.matmul(j_hat,unit_direction)
    scales=torch.tensor([8.]+[16.]*3+[32.]*6,device=r.device,dtype=r.dtype)
    jq=j_hat/torch.as_tensor(B_DIAG,device=r.device,dtype=r.dtype)[None,None,:]
    with torch.no_grad():
        result={"r_mae":float((r_hat-r).abs().mean()),
                "r_relative_l2":float((r_hat-r).norm()/r.norm().clamp_min(1e-9)),
                "r_w0_normalized_component_mae":float(((r_hat-r).abs()/scales).mean()),
                "J_mae":float((j_hat-J).abs().mean()),
                "J_relative_l2":float((j_hat-J).norm()/J.norm().clamp_min(1e-9)),
                "directional_mae":float((dr_true-dr_pred).abs().mean()),
                "projective_radial_Jc_c_max":float(torch.bmm(j_hat,c.unsqueeze(-1)).abs().max()),
                "predicted_Jq_asymmetry_max":float((jq-jq.transpose(-1,-2)).abs().max())}
    return result


def _query_c_and_derivative(spec: GeometrySpec, h: float) -> tuple[Tensor,Tensor]:
    c_np,_,_=vertical_cut_truth(spec,h)
    c=torch.tensor(c_np,dtype=torch.float32).unsqueeze(0)
    u=torch.tensor([-spec.center[2]-spec.axes[2]*h,0,0,1,0,0,0,0,0,0],dtype=c.dtype)
    du=torch.zeros_like(u)
    du[0]=-spec.axes[2]
    dc=(du-c[0]*torch.dot(c[0],du))/torch.linalg.vector_norm(u)
    return c,dc


def synthetic_decision(model,name: str, *, grid_size: int) -> dict:
    """One true-oracle-measured 1D cut step, not a Spin Newton optimization.

    Compare model-derived damped Gauss-Newton move in cut height to oracle
    Jacobian-derived move; report true analytic objective after each move.
    """
    model.eval()
    spec=GeometrySpec("ellipsoid",(.03,-.04,.05),(.61,.48,.69))
    h0=-.12; target_h=.27; radius=.12; regularizer=1e-3
    voxel=voxel_geometry(spec,grid_size).unsqueeze(0)
    with torch.no_grad():z=get_cached(model,name,voxel)
    c,dc=_query_c_and_derivative(spec,h0)
    target=torch.tensor(vertical_cut_truth(spec,target_h)[1],dtype=torch.float32)
    r_true=torch.tensor(vertical_cut_truth(spec,h0)[1],dtype=torch.float32)
    J_true=torch.tensor(vertical_cut_truth(spec,h0)[2],dtype=torch.float32)
    with torch.no_grad():r_pred=model.moment(z,c)[0]
    J_pred=model.jacobian(z,c)[0].detach()
    dr_model=J_pred@dc
    dr_oracle=J_true@dc
    residual_model=r_pred-target
    residual_oracle=r_true-target
    grad_model=torch.dot(dr_model,residual_model)
    grad_oracle=torch.dot(dr_oracle,residual_oracle)
    def propose(gradient,dr):
        return -gradient/(dr.square().sum()+regularizer)
    unbounded_model=propose(grad_model,dr_model)
    unbounded_oracle=propose(grad_oracle,dr_oracle)
    step_pred=float(unbounded_model.clamp(-radius,radius))
    step_oracle=float(unbounded_oracle.clamp(-radius,radius))
    def objective(h):
        rr=torch.tensor(vertical_cut_truth(spec,h)[1],dtype=torch.float32)
        return float(0.5*(rr-target).square().sum())
    return {"true_initial_objective":objective(h0),
            "true_after_predicted_step":objective(h0+step_pred),
            "true_after_oracle_step":objective(h0+step_oracle),
            "signed_true_objective_gap":objective(h0+step_pred)-objective(h0+step_oracle),
            "absolute_step_error":abs(step_pred-step_oracle),
            "predicted_step":step_pred,"oracle_step":step_oracle,
            "predicted_step_clipped":bool(unbounded_model.abs()>radius),
            "oracle_step_clipped":bool(unbounded_oracle.abs()>radius),
            "predicted_objective_gradient":float(grad_model),
            "oracle_objective_gradient":float(grad_oracle),
            "absolute_objective_gradient_error":float((grad_model-grad_oracle).abs()),
            "dr_dh_relative_l2_error":float((dr_model-dr_oracle).norm()/dr_oracle.norm().clamp_min(1e-10)),
            "dr_dh_cosine":float(torch.dot(dr_model,dr_oracle)/(dr_model.norm()*dr_oracle.norm()).clamp_min(1e-10)),
            "scope":"one-dimensional analytic cut GN diagnostic, not Spin production optimizer; clipped steps can hide large gradient errors"}


def _sync(device: str):
    if device=="cuda":torch.cuda.synchronize()


def timing(model,name: str,voxel: Tensor,c: Tensor, *, repeats: int) -> dict:
    model.eval()
    if repeats<1:raise ValueError("repeats must be positive")
    voxel,c=voxel.unsqueeze(0),c.unsqueeze(0)
    with torch.no_grad():
        prepared=prepare_geometry(name,voxel)
        z=model.encode_geometry(prepared).detach()
        model.moment(z,c)
        model.jacobian(z,c)
    def measure(fn: Callable):
        for _ in range(3):fn()
        ms=[]
        for _ in range(repeats):
            _sync("cpu")
            t=time.perf_counter()
            fn()
            _sync("cpu")
            ms.append((time.perf_counter()-t)*1000)
        return {"median_ms":statistics.median(ms),"min_ms":min(ms),
                "max_ms":max(ms),"repeats":repeats}
    with torch.no_grad():
        pre=measure(lambda:prepare_geometry(name,voxel))
        encoder=measure(lambda:model.encode_geometry(prepared))
        cold=measure(lambda:model.moment(model.encode_geometry(prepare_geometry(name,voxel)),c))
        warm=measure(lambda:model.moment(z,c))
        jac=measure(lambda:model.jacobian(z,c))
    return {"voxel_preprocess":pre,"encode_only":encoder,
            "cold_voxel_to_head":cold,"cached_head":warm,"cached_J10x10":jac,
            "cpu_process_peak_rss_kb":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "gpu_peak_allocated_mb":None}


def adapt_common(model,name: str,*,seed: int,grid_size: int) -> dict:
    """Identical 0/1/2-support query policy on independent heldout ellipsoid."""
    spec=GeometrySpec("ellipsoid",(.08,-.06,.03),(.63,.47,.72))
    rng=torch.Generator().manual_seed(seed)
    support=(torch.rand(2,generator=rng)*1.1-.55).tolist()
    holdout=(torch.rand(16,generator=rng)*1.1-.55).tolist()
    support_truth=[vertical_cut_truth(spec,h) for h in support]
    holdout_truth=[vertical_cut_truth(spec,h) for h in holdout]
    import numpy as np
    cs=torch.tensor(np.stack([item[0] for item in support_truth]),dtype=torch.float32).unsqueeze(0)
    rs=torch.tensor(np.stack([item[1] for item in support_truth]),dtype=torch.float32).unsqueeze(0)
    tests=torch.tensor(np.stack([item[0] for item in holdout_truth]),dtype=torch.float32)
    truth=torch.tensor(np.stack([item[1] for item in holdout_truth]),dtype=torch.float32)
    with torch.no_grad():z=get_cached(model,name,voxel_geometry(spec,grid_size).unsqueeze(0)).detach()
    results={}
    for k in (0,1,2):
        adapter=ResidualAdapter(model,z,cs[:,:k],rs[:,:k])
        with torch.no_grad():prediction=torch.cat([adapter.predict(test.unsqueeze(0)) for test in tests])
        results[str(k)]={"r_mae":float((prediction-truth).abs().mean()),
                         "teacher_query_count":k}
    return results


def run(*,seed: int=19,steps: int=12,per_family: int=20,
        grid_size: int=8,repeats: int=7) -> dict:
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    train_set=sample_dataset(("box","sphere"),per_family=per_family,seed=seed,
                             grid_size=grid_size,queries_per_geometry=2)
    test_set=sample_dataset(("ellipsoid",),per_family=per_family,seed=seed+1,
                            grid_size=grid_size,queries_per_geometry=2)
    assert_disjoint_family_splits(train_set,test_set)
    train_ids={m['geometry_id'] for m in train_set[4]}
    test_ids={m['geometry_id'] for m in test_set[4]}
    adaptation_id=GeometrySpec("ellipsoid",(.08,-.06,.03),(.63,.47,.72)).geometry_id
    decision_id=GeometrySpec("ellipsoid",(.03,-.04,.05),(.61,.48,.69)).geometry_id
    if ({adaptation_id,decision_id} & (train_ids|test_ids)) or adaptation_id==decision_id:
        raise RuntimeError('adaptation/decision oracle geometry overlaps train/test')
    schedule=_same_minibatches(len(train_set[0]),steps,8,seed)
    parameters={name:count_real_parameters(_make_model(name,seed,grid_size)) for name in MODELS}
    if max(parameters.values())/min(parameters.values())>1.05:
        raise RuntimeError("model real DOF differs by >5%: "+str(parameters))
    report={"status":"SAME_NATIVE_C_ANALYTIC_CONTINUUM_P0_M3_ONLY",
            "scope":"analytic vertical cuts; no native Cherchi, CGAL, CAD or W2 training",
            "seed":seed,"source_teacher":TEACHER_KIND,"device":"cpu",
            "torch_version":torch.__version__,"python_version":platform.python_version(),
            "contract_W0_head":W0_COMMIT,"teacher_W2_head":W2_COMMIT,
            "baseline_W5_head":W5_COMMIT,"W5_source_blobs":W5_SNAPSHOT_BLOBS,
            "analytic_training_queries":len(train_set[0]),
            "train_dataset_sha256":dataset_sha256(train_set),
            "heldout_dataset_sha256":dataset_sha256(test_set),
            "shared_batch_schedule_sha256":hashlib.sha256(schedule.numpy().tobytes()).hexdigest(),
            "adaptation_geometry_sha256":adaptation_id,
            "decision_geometry_sha256":decision_id,
            "heldout_queries":len(test_set[0]),
            "train_geometry_count":len({m['geometry_id'] for m in train_set[4]}),
            "test_geometry_count":len({m['geometry_id'] for m in test_set[4]}),
            "train_families":["box","sphere"],"test_families":["ellipsoid"],
            "shared_geometry_source":"same 4-channel sampled voxel tensors, no primitive one-hot or exact axes to W5",
            "W5_feature_policy":"deterministic lossy voxel-derived summary9; no learnable parameters",
            "feature_equivalence":False,"raw_geometry_source_identical":True,
            "model_parameter_real_dof":parameters,
            "trained_pino_or_Cherchi_weights":False,
            "W2_real_teacher_samples_in_manifest":0,
            "config":{"steps":steps,"batch_size":8,"lr":.003,"grid_size":grid_size,
                      "repeats":repeats,"seed":seed,
                      "gradient_loss_weight":0.5},
            "model_results":{}}
    for name in MODELS:
        report["model_results"][name]={}
        for enhanced in (False,True):
            model=_make_model(name,seed,grid_size)
            training=train(model,name,train_set,schedule=schedule,
                           derivative_enhanced=enhanced)
            key="moment_and_jacobian" if enhanced else "moment_only"
            report["model_results"][name][key]={
                "training":training,
                "heldout":evaluate(model,name,test_set),
                "decision":synthetic_decision(model,name,grid_size=grid_size),
                "adaptation":adapt_common(model,name,seed=seed+100,grid_size=grid_size),
                "performance":timing(model,name,test_set[0][0],test_set[1][0],repeats=repeats)}
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--seed',type=int,default=19)
    p.add_argument('--steps',type=int,default=12)
    p.add_argument('--per-family',type=int,default=20)
    p.add_argument('--grid-size',type=int,default=8)
    p.add_argument('--repeats',type=int,default=7)
    p.add_argument('--output',default=None)
    args=p.parse_args()
    result=run(seed=args.seed,steps=args.steps,per_family=args.per_family,
               grid_size=args.grid_size,repeats=args.repeats)
    output=json.dumps(result,indent=2,ensure_ascii=False,sort_keys=True,allow_nan=False)
    if args.output:
        with open(args.output,'w',encoding='utf-8') as f:f.write(output+'\n')
    print(output)


if __name__=='__main__':
    main()
