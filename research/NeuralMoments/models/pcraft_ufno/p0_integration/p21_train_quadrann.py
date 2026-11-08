"""P21: train the pinned MIT QuadrANN proposal as an optional residual adapter to trained P-CRAFT PINO.

PINO remains the only moment/Jacobian backbone. QuadrANN only proposes
geometry-conditioned positive weights on the fixed PINO quadrature nodes.
The c-independent proposal keeps the PINO analytic coefficient Jacobian
consistent. All derivatives remain diagnostic-only pending W0/W2 admission.
"""
from __future__ import annotations
import argparse,copy,hashlib,json,resource,time
from pathlib import Path
import torch
from torch.nn.utils import clip_grad_norm_

from ..spin_pino.dataset import generate_splits
from ..spin_pino.spin_pino import SpinPINO
from .selected_pino import SelectedPINOCandidates


def _model(grid=64):
    return SpinPINO(width=8,modes=4,n_layers=4,grid_size=grid,
        points_per_axis=8,hidden_dim=48,smoothing=.04,
        moment_parameterization="logistic_atom",temperature=.12,
        geometry_adapter="none")


def _batch(data,indices):
    D,c,r,J,meta=data
    idx=torch.as_tensor(indices,dtype=torch.long)
    return (D.index_select(0,idx),c.index_select(0,idx),
            r.index_select(0,idx),J.index_select(0,idx),
            [meta[int(i)] for i in indices])


def _metrics(model,data,batch_size=2):
    model.eval()
    D,c,target_r,target_J,meta=data
    pred_r=[];pred_J=[]
    with torch.no_grad():
        for start in range(0,len(D),batch_size):
            end=min(start+batch_size,len(D))
            out=model(D[start:end],c[start:end])
            pred_r.append(out.result.moments)
            pred_J.append(out.diagnostic_model_jacobian)
    pred_r=torch.cat(pred_r);pred_J=torch.cat(pred_J)
    return {
        "r_mae":float((pred_r-target_r).abs().mean()),
        "J_mae":float((pred_J-target_J).abs().mean()),
        "r_relative_l2":float((pred_r-target_r).norm()/target_r.norm().clamp_min(1e-12)),
        "J_relative_l2":float((pred_J-target_J).norm()/target_J.norm().clamp_min(1e-12)),
        "negative_mass_fraction":float((pred_r[:,0]<-1e-7).float().mean()),
    }


def _pino_metrics(pino,data,batch_size=2):
    pino.eval()
    D,c,target_r,target_J,_=data
    pr=[];pj=[]
    with torch.no_grad():
        for start in range(0,len(D),batch_size):
            end=min(start+batch_size,len(D))
            r,J=pino(D[start:end],c[start:end],with_jacobian=True)
            pr.append(r);pj.append(J)
    pr=torch.cat(pr);pj=torch.cat(pj)
    return {
        "r_mae":float((pr-target_r).abs().mean()),
        "J_mae":float((pj-target_J).abs().mean()),
        "r_relative_l2":float((pr-target_r).norm()/target_r.norm().clamp_min(1e-12)),
        "J_relative_l2":float((pj-target_J).norm()/target_J.norm().clamp_min(1e-12)),
        "negative_mass_fraction":float((pr[:,0]<-1e-7).float().mean()),
    }


def run(*,checkpoint_dir,seed=883,pino_seed=271,steps=60,batch_size=4,lr=1e-3,
        train_geometries_per_family=16,test_ellipsoid_geometries=8,
        queries_per_geometry=4,grid_size=64):
    torch.set_num_threads(1)
    torch.manual_seed(seed)
    source=Path(checkpoint_dir)/f"w6_p14_grid64_seed{pino_seed}.pt"
    if not source.is_file(): raise FileNotFoundError(source)
    pkg=torch.load(source,map_location="cpu",weights_only=False)
    if pkg.get("seed")!=pino_seed or pkg.get("grid_size")!=64:
        raise ValueError("P14 source checkpoint identity mismatch")
    source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
    pino=_model(grid_size)
    pino.load_state_dict(pkg["state_dict"],strict=True)
    pino.eval()
    for p in pino.parameters(): p.requires_grad_(False)

    splits=generate_splits(seed=seed,
        train_geometries_per_family=train_geometries_per_family,
        test_ellipsoid_geometries=test_ellipsoid_geometries,
        queries_per_geometry=queries_per_geometry,grid_size=grid_size)
    fit=splits["fit"];validation=splits["validation"];test=splits["test"]
    fit_r_scale=fit[2].std(dim=0).clamp_min(1e-3)
    fit_J_scale=fit[3].std(dim=0).clamp_min(1e-4)

    selected=SelectedPINOCandidates(
        pino,quadrann=True,quadrann_condition_on_material=True,
        quadrann_max_points=128,quadrann_kernel_width=.45,
    )
    selected.eval()
    # Zero gate must be exactly the original P-CRAFT PINO function.
    D0,c0=fit[0][:2],fit[1][:2]
    with torch.no_grad():
        base_r,base_J=pino(D0,c0,with_jacobian=True)
        zero=selected(D0,c0)
    if not torch.equal(base_r,zero.result.moments):
        raise AssertionError("zero-gated QuadrANN changed PINO moments")
    if not torch.equal(base_J,zero.diagnostic_model_jacobian):
        raise AssertionError("zero-gated QuadrANN changed PINO Jacobian")

    trainable=list(selected.quadrann_adapter.model.parameters())+[selected.quadrann_gate]
    for p in selected.pino.parameters(): p.requires_grad_(False)
    optimizer=torch.optim.Adam(trainable,lr=lr)
    baseline_val=_pino_metrics(pino,validation)
    baseline_test=_pino_metrics(pino,test)
    best_score=baseline_val["r_relative_l2"]+.25*baseline_val["J_relative_l2"]
    best_q=copy.deepcopy(selected.quadrann_adapter.model.state_dict())
    best_gate=selected.quadrann_gate.detach().clone()
    best_step=0
    history=[]
    generator=torch.Generator(device="cpu");generator.manual_seed(seed+9001)
    start=time.perf_counter()
    for step in range(1,steps+1):
        selected.train()
        selected.pino.eval()
        # Keep upstream dropout disabled for reproducible geometry-conditioned
        # proposals across coefficient queries; gradients still flow normally.
        selected.quadrann_adapter.model.eval()
        indices=torch.randint(len(fit[0]),(batch_size,),generator=generator)
        D,c,target_r,target_J,_=_batch(fit,indices.tolist())
        proposal=selected(D,c)
        loss_r=((proposal.result.moments-target_r)/fit_r_scale).square().mean()
        loss_J=((proposal.diagnostic_model_jacobian-target_J)/fit_J_scale).square().mean()
        loss=loss_r+.25*loss_J
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        grad_norm=clip_grad_norm_(trainable,1.0)
        if not bool(torch.isfinite(torch.as_tensor(grad_norm))):
            raise FloatingPointError("nonfinite QuadrANN training gradient")
        optimizer.step()
        history.append({"step":step,"loss":float(loss.detach()),
            "r_loss":float(loss_r.detach()),"J_loss":float(loss_J.detach()),
            "gate":float(selected.quadrann_gate.detach()),
            "gradient_norm":float(torch.as_tensor(grad_norm))})
        if step%5==0 or step==steps:
            val=_metrics(selected,validation,batch_size=2)
            score=val["r_relative_l2"]+.25*val["J_relative_l2"]
            if score<best_score:
                best_score=score;best_step=step
                best_q=copy.deepcopy(selected.quadrann_adapter.model.state_dict())
                best_gate=selected.quadrann_gate.detach().clone()
    train_wall=time.perf_counter()-start
    final_q=copy.deepcopy(selected.quadrann_adapter.model.state_dict())
    final_gate=float(selected.quadrann_gate.detach())
    selected.quadrann_adapter.model.load_state_dict(best_q,strict=True)
    selected.quadrann_gate.data.copy_(best_gate)
    best_val=_metrics(selected,validation,batch_size=2)
    best_test=_metrics(selected,test,batch_size=2)
    final_val=_pino_metrics(pino,validation)
    final_test=_pino_metrics(pino,test)
    checkpoint=Path(f"/tmp/w6_p21_quadrann_pino{pino_seed}_seed{seed}.pt")
    torch.save({
        "quadrann_state_dict":best_q,"quadrann_final_state_dict":final_q,
        "quadrann_gate":float(best_gate),"quadrann_final_gate":final_gate,
        "pino_source_checkpoint_sha256":source_sha,"pino_seed":pino_seed,
        "quadrann_upstream":"kesmarag/QuadrANN@111dd611aaeac1fb98c76385706b003ea8ef94be",
        "quadrann_license":"MIT","quadrann_condition_on_material":True,
        "quadrann_max_points":128,"quadrann_kernel_width":.45,
        "training_seed":seed,"grid_size":grid_size,
    },checkpoint)
    return {
        "schema":"W6_P21_TRAINED_QUADRANN_OPTIONAL_PINO_RESIDUAL_V1",
        "training_seed":seed,"pino_source_seed":pino_seed,
        "pino_source_checkpoint_sha256":source_sha,
        "quadrann_upstream_commit":"111dd611aaeac1fb98c76385706b003ea8ef94be",
        "quadrann_license":"MIT","original_core_unchanged":True,
        "primary_backbone":"P-CRAFT SpinPINO factorized F-FNO/U-FNO",
        "pino_grid":grid_size,"pino_parameters_frozen":True,
        "quadrann_condition_on_material":True,"quadrann_max_points":128,
        "quadrann_trainable_parameters":sum(p.numel() for p in trainable),
        "zero_gate_exact_pino_parity":True,"quadrann_gate_initial":0.0,
        "quadrann_gate_final":final_gate,"quadrann_gate_selected":float(best_gate),
        "steps":steps,"batch_size":batch_size,"learning_rate":lr,
        "best_validation_step":best_step,"training_seconds":train_wall,
        "fit_geometry_ids":splits["metadata"]["fit_geometry_ids"],
        "validation_geometry_ids":splits["metadata"]["validation_geometry_ids"],
        "heldout_ellipsoid_geometry_ids":splits["metadata"]["test_geometry_ids"],
        "dataset_sha256":{"fit":splits["metadata"]["fit_sha256"],
            "validation":splits["metadata"]["validation_sha256"],
            "test":splits["metadata"]["test_sha256"]},
        "baseline_pino":{"validation":baseline_val,"heldout":baseline_test},
        "quadrann_enhanced":{"validation":best_val,"heldout":best_test},
        "improvement":{
            "heldout_r_relative_l2_fraction":
                (baseline_test["r_relative_l2"]-best_test["r_relative_l2"])/max(baseline_test["r_relative_l2"],1e-12),
            "heldout_J_relative_l2_fraction":
                (baseline_test["J_relative_l2"]-best_test["J_relative_l2"])/max(baseline_test["J_relative_l2"],1e-12)},
        "history":history,"checkpoint":str(checkpoint),
        "peak_process_ru_maxrss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "claims":{"PINO_is_primary":True,"QuadrANN_is_optional_geometry_proposal":True,
            "quadrann_original_MIT_core_used":True,"PINO_Jacobian_remains_geometry_conditioned":True,
            "native_Cherchi_admitted":False,"Newton_admitted":False,
            "QuadrANN_trained":best_step>0 and abs(float(best_gate))>1e-8,
            "production_default":False},
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--checkpoint-dir",type=Path,required=True)
    p.add_argument("--seed",type=int,default=883)
    p.add_argument("--pino-seed",type=int,default=271,choices=(271,277,281))
    p.add_argument("--steps",type=int,default=60)
    p.add_argument("--batch-size",type=int,default=4)
    p.add_argument("--lr",type=float,default=1e-3)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    r=run(checkpoint_dir=a.checkpoint_dir,seed=a.seed,pino_seed=a.pino_seed,steps=a.steps,
          batch_size=a.batch_size,lr=a.lr)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({"baseline_test":r["baseline_pino"]["heldout"],
        "quadrann_test":r["quadrann_enhanced"]["heldout"],
        "improvement":r["improvement"],"gate":r["quadrann_gate_selected"],
        "best_step":r["best_validation_step"]},indent=2))


if __name__=="__main__":
    main()
