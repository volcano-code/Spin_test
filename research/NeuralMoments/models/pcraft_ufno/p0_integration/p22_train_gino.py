"""P22: train the pinned MIT NeuralOperator GINO geometry proposal around P-CRAFT PINO."""
from __future__ import annotations
import argparse,copy,hashlib,json,resource,time
from pathlib import Path
import torch
from torch.nn.utils import clip_grad_norm_

from ..spin_pino.dataset import generate_splits
from ..spin_pino.spin_pino import SpinPINO
from .selected_pino import SelectedPINOCandidates


def _pino(grid=64):
    return SpinPINO(width=8,modes=4,n_layers=4,grid_size=grid,
        points_per_axis=8,hidden_dim=48,smoothing=.04,
        moment_parameterization="logistic_atom",temperature=.12,
        geometry_adapter="none")


def _metrics(model,data,batch_size=2):
    model.eval();D,c,r,J,_=data;pr=[];pj=[]
    with torch.no_grad():
        for s in range(0,len(D),batch_size):
            e=min(s+batch_size,len(D));out=model(D[s:e],c[s:e])
            pr.append(out.result.moments);pj.append(out.diagnostic_model_jacobian)
    pr=torch.cat(pr);pj=torch.cat(pj)
    return {"r_mae":float((pr-r).abs().mean()),"J_mae":float((pj-J).abs().mean()),
        "r_relative_l2":float((pr-r).norm()/r.norm().clamp_min(1e-12)),
        "J_relative_l2":float((pj-J).norm()/J.norm().clamp_min(1e-12)),
        "negative_mass_fraction":float((pr[:,0]<-1e-7).float().mean())}


def _pino_metrics(pino,data,batch_size=2):
    pino.eval();D,c,r,J,_=data;pr=[];pj=[]
    with torch.no_grad():
        for s in range(0,len(D),batch_size):
            e=min(s+batch_size,len(D));a,b=pino(D[s:e],c[s:e],with_jacobian=True)
            pr.append(a);pj.append(b)
    pr=torch.cat(pr);pj=torch.cat(pj)
    return {"r_mae":float((pr-r).abs().mean()),"J_mae":float((pj-J).abs().mean()),
        "r_relative_l2":float((pr-r).norm()/r.norm().clamp_min(1e-12)),
        "J_relative_l2":float((pj-J).norm()/J.norm().clamp_min(1e-12)),
        "negative_mass_fraction":float((pr[:,0]<-1e-7).float().mean())}


def _batch(data,indices):
    D,c,r,J,meta=data;idx=torch.as_tensor(indices,dtype=torch.long)
    return D.index_select(0,idx),c.index_select(0,idx),r.index_select(0,idx),J.index_select(0,idx)


def run(*,checkpoint_dir,seed=887,steps=40,batch_size=2,lr=5e-4,
        train_geometries_per_family=12,test_ellipsoid_geometries=8,
        queries_per_geometry=3,grid_size=64):
    torch.set_num_threads(1)
    source=Path(checkpoint_dir)/"w6_p14_grid64_seed271.pt"
    if not source.is_file(): raise FileNotFoundError(source)
    pkg=torch.load(source,map_location="cpu",weights_only=False)
    if pkg.get("seed")!=271 or pkg.get("grid_size")!=64: raise ValueError("P14 checkpoint mismatch")
    source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
    pino=_pino(grid_size);pino.load_state_dict(pkg["state_dict"],strict=True);pino.eval()
    for p in pino.parameters(): p.requires_grad_(False)
    splits=generate_splits(seed=seed,train_geometries_per_family=train_geometries_per_family,
        test_ellipsoid_geometries=test_ellipsoid_geometries,
        queries_per_geometry=queries_per_geometry,grid_size=grid_size)
    fit=splits["fit"];validation=splits["validation"];test=splits["test"]
    r_scale=fit[2].std(dim=0).clamp_min(1e-3);J_scale=fit[3].std(dim=0).clamp_min(1e-4)

    selected=SelectedPINOCandidates(pino,gino=True,gino_hidden=8,max_gino_points=64)
    selected.eval()
    D0,c0=fit[0][:2],fit[1][:2]
    with torch.no_grad():
        br,bj=pino(D0,c0,with_jacobian=True);zero=selected(D0,c0)
    if not torch.equal(br,zero.result.moments) or not torch.equal(bj,zero.diagnostic_model_jacobian):
        raise AssertionError("zero GINO gate must preserve exact PINO")
    # The selected wrapper uses GINO.encode + a residual map; its standalone
    # coefficient head is not used and is excluded from the optimizer.
    for p in selected.gino_adapter.head.parameters(): p.requires_grad_(False)
    trainable=list(selected.gino_adapter.encoder.parameters())+list(selected.gino_correction.parameters())+[selected.gino_gate]
    optimizer=torch.optim.Adam(trainable,lr=lr)
    baseline_val=_pino_metrics(pino,validation);baseline_test=_pino_metrics(pino,test)
    best_score=baseline_val["r_relative_l2"]+.25*baseline_val["J_relative_l2"]
    best_encoder=copy.deepcopy(selected.gino_adapter.encoder.state_dict())
    best_correction=copy.deepcopy(selected.gino_correction.state_dict())
    best_gate=selected.gino_gate.detach().clone();best_step=0
    history=[];gen=torch.Generator(device="cpu");gen.manual_seed(seed+19001)
    started=time.perf_counter()
    for step in range(1,steps+1):
        selected.train();selected.pino.eval()
        idx=torch.randint(len(fit[0]),(batch_size,),generator=gen)
        D,c,tr,tJ=_batch(fit,idx.tolist())
        out=selected(D,c)
        lr_loss=((out.result.moments-tr)/r_scale).square().mean()
        lj_loss=((out.diagnostic_model_jacobian-tJ)/J_scale).square().mean()
        loss=lr_loss+.25*lj_loss
        optimizer.zero_grad(set_to_none=True);loss.backward()
        gn=clip_grad_norm_(trainable,1.0)
        if not bool(torch.isfinite(torch.as_tensor(gn))): raise FloatingPointError("nonfinite GINO gradient")
        optimizer.step()
        history.append({"step":step,"loss":float(loss.detach()),"r_loss":float(lr_loss.detach()),
            "J_loss":float(lj_loss.detach()),"gate":float(selected.gino_gate.detach()),
            "gradient_norm":float(torch.as_tensor(gn))})
        if step%5==0 or step==steps:
            val=_metrics(selected,validation,batch_size=2)
            score=val["r_relative_l2"]+.25*val["J_relative_l2"]
            if score<best_score:
                best_score=score;best_step=step
                best_encoder=copy.deepcopy(selected.gino_adapter.encoder.state_dict())
                best_correction=copy.deepcopy(selected.gino_correction.state_dict())
                best_gate=selected.gino_gate.detach().clone()
    elapsed=time.perf_counter()-started
    final_gate=float(selected.gino_gate.detach())
    selected.gino_adapter.encoder.load_state_dict(best_encoder,strict=True)
    selected.gino_correction.load_state_dict(best_correction,strict=True)
    selected.gino_gate.data.copy_(best_gate)
    val_best=_metrics(selected,validation);test_best=_metrics(selected,test)
    checkpoint=Path("/tmp/w6_p22_gino_seed887.pt")
    torch.save({"gino_encoder":best_encoder,"gino_correction":best_correction,
        "gino_gate":float(best_gate),"gino_final_gate":final_gate,
        "pino_source_checkpoint_sha256":source_sha,"pino_source_seed":271,
        "neuraloperator_commit":"a6648eeeb60fe0837f2d7d021517a945a159a0c8",
        "neuraloperator_license":"MIT","training_seed":seed,"grid_size":grid_size,
        "max_gino_points":64},checkpoint)
    return {"schema":"W6_P22_TRAINED_GINO_OPTIONAL_PINO_RESIDUAL_V1",
        "training_seed":seed,"pino_source_seed":271,"pino_source_checkpoint_sha256":source_sha,
        "neuraloperator_commit":"a6648eeeb60fe0837f2d7d021517a945a159a0c8",
        "neuraloperator_license":"MIT","primary_backbone":"P-CRAFT SpinPINO factorized F-FNO/U-FNO",
        "pino_grid":grid_size,"pino_parameters_frozen":True,"gino_max_points":64,
        "gino_trainable_parameters":sum(p.numel() for p in trainable),
        "gino_gate_initial":0.0,"gino_gate_final":final_gate,"gino_gate_selected":float(best_gate),
        "steps":steps,"batch_size":batch_size,"learning_rate":lr,"best_validation_step":best_step,
        "training_seconds":elapsed,"fit_geometry_ids":splits["metadata"]["fit_geometry_ids"],
        "validation_geometry_ids":splits["metadata"]["validation_geometry_ids"],
        "heldout_ellipsoid_geometry_ids":splits["metadata"]["test_geometry_ids"],
        "dataset_sha256":{"fit":splits["metadata"]["fit_sha256"],
            "validation":splits["metadata"]["validation_sha256"],"test":splits["metadata"]["test_sha256"]},
        "baseline_pino":{"validation":baseline_val,"heldout":baseline_test},
        "gino_enhanced":{"validation":val_best,"heldout":test_best},
        "improvement":{
            "heldout_r_relative_l2_fraction":(baseline_test["r_relative_l2"]-test_best["r_relative_l2"])/max(baseline_test["r_relative_l2"],1e-12),
            "heldout_J_relative_l2_fraction":(baseline_test["J_relative_l2"]-test_best["J_relative_l2"])/max(baseline_test["J_relative_l2"],1e-12)},
        "history":history,"checkpoint":str(checkpoint),
        "peak_process_ru_maxrss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "claims":{"PINO_primary":True,"GINO_optional_geometry_residual":True,
            "original_NeuralOperator_GINO_used":True,"PINO_Jacobian_geometry_conditioned":True,
            "native_Cherchi":False,"Newton":False,"production_default":False}}


def main():
    p=argparse.ArgumentParser();p.add_argument("--checkpoint-dir",type=Path,required=True)
    p.add_argument("--seed",type=int,default=887);p.add_argument("--steps",type=int,default=40)
    p.add_argument("--batch-size",type=int,default=2);p.add_argument("--lr",type=float,default=5e-4)
    p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    r=run(checkpoint_dir=a.checkpoint_dir,seed=a.seed,steps=a.steps,batch_size=a.batch_size,lr=a.lr)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({"baseline_test":r["baseline_pino"]["heldout"],"gino_test":r["gino_enhanced"]["heldout"],
        "improvement":r["improvement"],"gate":r["gino_gate_selected"],"best_step":r["best_validation_step"]},indent=2))
if __name__=="__main__": main()
