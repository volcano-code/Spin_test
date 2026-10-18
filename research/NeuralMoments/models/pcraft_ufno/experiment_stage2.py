"""W6 M2: W0-native-cut analytic P0 supervised smoke and derivative ablation.

This is NOT training on real W2 Cherchi labels or evidence of production
Faster/Cherchi speedup. Compare to W5 only after re-running W5 on these exact
same physical-cut labels; the pre-existing W5 smoke uses unrelated density c.

From repository root:
  python -m research.NeuralMoments.models.pcraft_ufno.experiment_stage2 \
    --steps 12 --per-family 20 --output /path/to/analytic_stage2_cpu.json
"""
from __future__ import annotations

import argparse
import json
import platform
import resource
import statistics
import time

import torch
from torch import Tensor

from .adaptation import ResidualAdapter
from .analytic_cut import (B_NATIVE_TO_MONOMIAL, GeometrySpec, TEACHER_KIND,
                           assert_disjoint_family_splits, sample_dataset,
                           vertical_cut_truth, voxel_geometry)
from .model import UFNOMoment, count_real_parameters

W0_SHA = "fbf3f3a3916d504baef0557ed9979525ec63b7b6"
W2_SHA = "14b1d2d5da4e258d125e664b5665ef84f7ebbb4e"
W5_SHA = "8efd22864dc61b4782e1e2f8c0b177db3a15fff5"
W5_BASELINE_PARAMETERS = {"deeponet":13674, "geometry_mlp":13482}


def _new_model(seed: int, grid_size: int) -> UFNOMoment:
    torch.manual_seed(seed)
    return UFNOMoment(width=4, modes=3, latent_dim=24, head_width=40,
                      grid_size=grid_size).float()


def train_tiny(model: UFNOMoment, dataset, *, steps: int, seed: int,
               derivative_enhanced: bool, batch_size: int = 8) -> dict:
    if steps < 0 or batch_size < 1:
        raise ValueError("invalid training budget")
    D, c, r, J, _ = dataset
    optimizer = torch.optim.Adam(model.parameters(), lr=.003)
    rng = torch.Generator().manual_seed(seed)
    stats = {"last_train_r_mse": None, "last_train_J_mse": None,
             "last_train_smooth_Jq_asymmetry_mse": None}
    start = time.perf_counter()
    model.train()
    for _ in range(steps):
        selected = torch.randint(len(D),(batch_size,),generator=rng)
        encoded = model.encode_geometry(D[selected])
        pred = model.moment(encoded,c[selected])
        r_loss = (pred-r[selected]).square().mean()
        loss = r_loss
        j_loss = None
        asymmetry = None
        if derivative_enhanced:
            prediction_J = model.jacobian(encoded,c[selected])
            j_loss = (prediction_J-J[selected]).square().mean()
            # W0: only permitted on *smooth continuum full-ambient* cuts.
            # All synthetic cuts are strict interior planes; never blindly
            # turn on this term for discrete, tangent or invalid W2 records.
            H = prediction_J / torch.as_tensor(B_NATIVE_TO_MONOMIAL.diagonal().copy(),
                                                 dtype=prediction_J.dtype)[None,None,:]
            asymmetry = (H-H.transpose(-1,-2)).square().mean()
            loss = loss + .5*j_loss + .05*asymmetry
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        stats.update(last_train_r_mse=float(r_loss.detach()),
                     last_train_J_mse=float(j_loss.detach()) if j_loss is not None else None,
                     last_train_smooth_Jq_asymmetry_mse=(float(asymmetry.detach())
                                                        if asymmetry is not None else None))
    stats.update(steps=steps,batch_size=batch_size,lr=.003,
                 derivative_enhanced=derivative_enhanced,
                 cpu_train_seconds=time.perf_counter()-start,gpu_seconds=0.0)
    return stats


def evaluate(model: UFNOMoment, dataset) -> dict:
    D,c,r,J,_=dataset
    model.eval()
    with torch.no_grad():
        z=model.encode_geometry(D)
        prediction_r=model.moment(z,c)
    prediction_J=model.jacobian(z.detach(),c)
    ray=torch.arange(1,11,dtype=c.dtype)
    ray=ray/ray.norm()
    d_true=torch.einsum("bij,j->bi",J,ray)
    d_pred=torch.einsum("bij,j->bi",prediction_J,ray)
    # Unit world domain [-1,1]^3; W0 component scales rho_ref*L^p.
    scales=torch.tensor([8.]+[16.]*3+[32.]*6,dtype=r.dtype)
    H=prediction_J/torch.tensor([1.]*7+[2.]*3,dtype=r.dtype)[None,None,:]
    return {"r_mae":(prediction_r-r).abs().mean().item(),
            "r_relative_l2":((prediction_r-r).norm()/r.norm().clamp_min(1e-12)).item(),
            "r_W0_normalized_component_mae":((prediction_r-r).abs()/scales).mean().item(),
            "J_mae":(prediction_J-J).abs().mean().item(),
            "J_relative_l2":((prediction_J-J).norm()/J.norm().clamp_min(1e-12)).item(),
            "directional_derivative_mae":(d_true-d_pred).abs().mean().item(),
            "predicted_Jq_max_asymmetry":(H-H.transpose(-1,-2)).abs().max().item(),
            "projective_radial_Jc_c_max":torch.bmm(prediction_J,c.unsqueeze(-1)).abs().max().item(),
            "oracle_Jq_max_asymmetry":(J/torch.tensor([1.]*7+[2.]*3)[None,None,:]
                                             -(J/torch.tensor([1.]*7+[2.]*3)[None,None,:]).transpose(-1,-2)).abs().max().item()}


def benchmark(model: UFNOMoment, d: Tensor, c: Tensor, *, repetitions: int = 7) -> dict:
    model.eval()
    d=d.unsqueeze(0);c=c.unsqueeze(0)
    with torch.no_grad():
        z=model.cache_geometry(d)
        model.moment(z,c)
        model.jacobian(z,c)
    def measure(fn):
        values=[]
        for _ in range(3):fn()
        for _ in range(repetitions):
            start=time.perf_counter()
            fn()
            values.append((time.perf_counter()-start)*1000)
        return {"median_ms":statistics.median(values),"min_ms":min(values),
                "max_ms":max(values),"repetitions":repetitions}
    with torch.no_grad():
        cold=measure(lambda:model.moment(model.encode_geometry(d),c))
        encode=measure(lambda:model.encode_geometry(d))
        warm=measure(lambda:model.moment(z,c))
        jac=measure(lambda:model.jacobian(z,c))
    return {"cold_encode_plus_head":cold,"encode_only":encode,
            "cached_head_only":warm,"cached_J_10x10":jac,
            "cpu_process_peak_rss_kb":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "cuda_peak_allocated_mb":None,
            "note":"CPU process peak RSS is not phase memory; measured on uncompiled warm CPU"}


def adaptation_metrics(model: UFNOMoment, *, seed: int, grid_size: int) -> dict:
    # Independent unseen ellipsoid and support controls; never train on this.
    spec=GeometrySpec("ellipsoid",(.07,-.05,.02),(.62,.45,.74))
    rng=torch.Generator().manual_seed(seed)
    support_h=(torch.rand(2,generator=rng)*1.1-.55).tolist()
    target_h=(torch.rand(16,generator=rng)*1.1-.55).tolist()
    support_truth=[vertical_cut_truth(spec,h) for h in support_h]
    test_truth=[vertical_cut_truth(spec,h) for h in target_h]
    support_c=torch.from_numpy(__import__('numpy').stack([x[0] for x in support_truth])).float()[None]
    support_r=torch.from_numpy(__import__('numpy').stack([x[1] for x in support_truth])).float()[None]
    target_c=torch.from_numpy(__import__('numpy').stack([x[0] for x in test_truth])).float()
    target_r=torch.from_numpy(__import__('numpy').stack([x[1] for x in test_truth])).float()
    z=model.cache_geometry(voxel_geometry(spec,grid_size).unsqueeze(0))
    results={}
    for k in (0,1,2):
        adapter=ResidualAdapter(model,z,support_c[:,:k],support_r[:,:k])
        with torch.no_grad():
            predicted=torch.cat([adapter.predict(cc.unsqueeze(0)) for cc in target_c])
        results[str(k)]={"r_mae":(predicted-target_r).abs().mean().item(),
                         "teacher_queries":k}
    return results


def run(*, seed: int=19, steps: int=12, per_family: int=20,
        grid_size: int=8, repetitions: int=7) -> dict:
    torch.set_num_threads(1)
    train=sample_dataset(("box","sphere"),per_family=per_family,
                         seed=seed,grid_size=grid_size)
    test=sample_dataset(("ellipsoid",),per_family=per_family,
                        seed=seed+1,grid_size=grid_size)
    assert_disjoint_family_splits(train,test)
    model_for_count=_new_model(seed,grid_size)
    parameters=count_real_parameters(model_for_count)
    if not all(abs(parameters-n)/n<.05 for n in W5_BASELINE_PARAMETERS.values()):
        raise RuntimeError("stage2 model no longer near W5 parameter budget")
    report={"status":"ANALYTIC_P0_CUT_SMOKE_NOT_W2_TEACHER",
            "seed":seed,"train_families":["box","sphere"],
            "test_families":["ellipsoid"],
            "train_examples":len(train[0]),"test_examples":len(test[0]),
            "geometry_ids_train":len({x['geometry_id'] for x in train[4]}),
            "geometry_ids_test":len({x['geometry_id'] for x in test[4]}),
            "teacher":TEACHER_KIND,
            "native_c_order":"const,x,y,z,xx,yy,zz,yz,xz,xy",
            "r_order":"mass,x,y,z,xx,yy,zz,yz,xz,xy",
            "retained_side":"beta_c(x)>=0",
            "derivative_type":"smooth_full_ambient_continuum_only",
            "positive_projective_c_unit":True,
            "contract_W0_branch_sha":W0_SHA,
            "W2_branch_sha":W2_SHA,
            "W2_actual_teacher_records":0,
            "W5_branch_sha":W5_SHA,
            "W5_existing_report_comparable":False,
            "W5_comparison_reason":"Existing W5 smoke uses polynomial density c, not native physical cut c. Retrain both on identical labels before claiming a win.",
            "parameters_real":parameters,"W5_reference_parameters":W5_BASELINE_PARAMETERS,
            "training_teacher_query_count":len(train[0]),
            "cpu_threads":torch.get_num_threads(),"device":"cpu",
            "torch_version":torch.__version__,"python_version":platform.python_version(),
            "analytical_labels_are_continuum_not_voxel_integrals":True,
            "config":{"steps":steps,"lr":.003,"batch_size":8,
                      "grid_size":grid_size,"repetitions":repetitions},
            "arms":{}}
    for enhanced in (False,True):
        torch.manual_seed(seed)
        model=_new_model(seed,grid_size)
        training=train_tiny(model,train,steps=steps,seed=seed,
                            derivative_enhanced=enhanced)
        key="derivative_plus_W0_smooth_Jq" if enhanced else "moment_only"
        report['arms'][key]={"training":training,"heldout":evaluate(model,test),
                            "latency":benchmark(model,test[0][0],test[1][0],
                                                 repetitions=repetitions),
                            "adaptation":adaptation_metrics(model,seed=seed+100,
                                                            grid_size=grid_size)}
    return report


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--seed",type=int,default=19)
    parser.add_argument("--steps",type=int,default=12)
    parser.add_argument("--per-family",type=int,default=20)
    parser.add_argument("--grid-size",type=int,default=8)
    parser.add_argument("--repetitions",type=int,default=7)
    parser.add_argument("--output",default=None)
    args=parser.parse_args()
    result=run(seed=args.seed,steps=args.steps,per_family=args.per_family,
               grid_size=args.grid_size,repetitions=args.repetitions)
    serialized=json.dumps(result,sort_keys=True,indent=2,allow_nan=False)
    if args.output:
        with open(args.output,'w',encoding='utf-8') as stream:stream.write(serialized+'\n')
    print(serialized)


if __name__=='__main__':
    main()
