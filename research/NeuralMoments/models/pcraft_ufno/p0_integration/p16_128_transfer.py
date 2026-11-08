"""P16: strict warm-start transfer of trained 64^3 P-CRAFT PINO to 128^3.

Uses the actual P14 seed-271 64^3 trained checkpoint, regenerates the
same geometry identities at 128^3, evaluates zero-shot transfer, then
fine-tunes all PINO weights at native 128^3 with full SpinPINOLoss.
This is not a Cherchi-trained model.
"""
from __future__ import annotations
import argparse,json,resource,time
from pathlib import Path
import torch

from ..spin_pino.dataset import generate_splits
from ..spin_pino.spin_pino import SpinPINO
from ..spin_pino.train import run_seed,_evaluate
from ..densicrafter_pino.p13b_highres import exact_discrete_cut_moments


def _model(grid=128):
    return SpinPINO(width=8,modes=4,n_layers=4,grid_size=grid,
        points_per_axis=8,hidden_dim=48,smoothing=.04,
        moment_parameterization="logistic_atom",temperature=.12,
        geometry_adapter="none",use_gradient_checkpoint=True).eval()


def _rel(a,b):
    return float((a-b).norm()/b.norm().clamp_min(1e-12))


def run(*,checkpoint_dir,seed=271,steps=8):
    torch.set_num_threads(1)
    checkpoint_path=Path(checkpoint_dir)/f"w6_p14_grid64_seed{seed}.pt"
    if not checkpoint_path.is_file():
        raise FileNotFoundError(f"missing P14 64 checkpoint: {checkpoint_path}")
    package=torch.load(checkpoint_path,map_location="cpu",weights_only=False)
    if package.get("seed")!=seed or package.get("grid_size")!=64:
        raise ValueError("P14 checkpoint seed/grid provenance mismatch")
    state=package["state_dict"]

    common=dict(train_geometries_per_family=8,
        test_ellipsoid_geometries=6,queries_per_geometry=2)
    split64=generate_splits(seed=seed,grid_size=64,**common)
    split128=generate_splits(seed=seed,grid_size=128,**common)
    for name in ("fit_geometry_ids","validation_geometry_ids","test_geometry_ids"):
        if split64["metadata"][name]!=split128["metadata"][name]:
            raise AssertionError("geometry identity differs across resolution: "+name)

    model=_model(128)
    # Strictly load all P14 weights into native 128-grid PINO. No shape
    # interpolation or dropped parameters; only the nonpersistent coordinate
    # grid changes with resolution.
    model.load_state_dict(state,strict=True)
    zero_shot=_evaluate(model,split128["test"],batch_size=1)
    zero_shot_val=_evaluate(model,split128["validation"],batch_size=1)

    started=time.perf_counter()
    result=run_seed(
        seed=seed,**common,steps=steps,batch_size=1,eval_batch_size=1,
        grid_size=128,points_per_axis=8,smoothing=.04,
        preconditioned_loss=True,pcgrad=False,
        moment_parameterization="logistic_atom",temperature=.12,
        geometry_adapter="none",lambda_equivariance=0.,
        rotation_augmentation=True,rotation_augmentation_mode="cube_group",
        evaluation_rotation_mode="so3",use_gradient_checkpoint=True,
        initial_state_dict=state,
        initial_state_source=f"P14_native64_seed{seed}",
        device="cpu",
    )
    wall=time.perf_counter()-started
    trained_state=result.pop("checkpoint_state")
    model.load_state_dict(trained_state,strict=True)
    final_test=_evaluate(model,split128["test"],batch_size=1)
    final_val=_evaluate(model,split128["validation"],batch_size=1)
    D,c,r,J,_=split128["test"]
    pred_r=[];pred_J=[];voxel_r=[]
    with torch.no_grad():
        for i in range(len(D)):
            w=model.encode_geometry(D[i:i+1])
            pred_r.append(model.moment_from_weights(w,c[i:i+1]))
            pred_J.append(model.jacobian_from_weights(w,c[i:i+1]))
            voxel_r.append(exact_discrete_cut_moments(D[i:i+1,0:1],c[i:i+1]))
    pred_r=torch.cat(pred_r);pred_J=torch.cat(pred_J);voxel_r=torch.cat(voxel_r)
    out=Path(f"/tmp/w6_p16_128_transfer_seed{seed}.pt")
    torch.save({"state_dict":trained_state,"seed":seed,"grid_size":128,
        "initialized_from":"P14_native64","source":"ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI"},out)
    return {
        "schema":"W6_P16_NATIVE_128_WARMSTART_FROM_TRAINED_64_V1",
        "seed":seed,"source_checkpoint":str(checkpoint_path),
        "source_checkpoint_sha256":package.get("sha256"),
        "source_resolution":64,"target_input_and_Fourier_grid":128,
        "strict_full_state_transfer":True,"state_dict_key_count":len(state),
        "model":"P-CRAFT SpinPINO factorized F-FNO/U-FNO",
        "width":8,"modes":4,"layers":4,"parameters":model.real_parameter_count(),
        "quadrature_atoms":512,"all_PINO_weights_fine_tuned":True,
        "gradient_checkpointing":True,"train_batch_size":1,"eval_batch_size":1,
        "geometry_identity_same_64_to_128":True,
        "fit_geometry_ids":split128["metadata"]["fit_geometry_ids"],
        "validation_geometry_ids":split128["metadata"]["validation_geometry_ids"],
        "heldout_ellipsoid_geometry_ids":split128["metadata"]["test_geometry_ids"],
        "dataset_sha256":{"fit":split128["metadata"]["fit_sha256"],
            "validation":split128["metadata"]["validation_sha256"],
            "test":split128["metadata"]["test_sha256"]},
        "zero_shot_64_checkpoint_at_128":{
            "validation":zero_shot_val,"heldout":zero_shot},
        "fine_tuning":{"steps":steps,"selected_step":result["training"]["selected_step"],
            "seconds":result["training"]["seconds"],"wall_seconds":wall,
            "history":result["training"]["history"],
            "initial_state_source":result["model_config"]["initial_state_source"]},
        "after_fine_tuning":{"validation":final_val,"heldout":final_test,
            "rotated_heldout":result["held_out_rotated_ellipsoid_metrics"]},
        "independent_heldout":{
            "pred_r_vs_analytic_continuum_relative_l2":_rel(pred_r,r),
            "pred_J_vs_analytic_continuum_relative_l2":_rel(pred_J,J),
            "cell_centered_hard_cut_vs_analytic_continuum_relative_l2":_rel(voxel_r,r),
            "pred_r_vs_independent_voxel_cut_relative_l2":_rel(pred_r,voxel_r)},
        "checkpoint":str(out),
        "peak_process_ru_maxrss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "claims":{"native_128_PINO_finetuned":True,"PINO_primary":True,
            "Cherchi_supervised":False,"native_Newton_admitted":False,
            "512_cube_trained":False,"real_Spin_end_to_end":False},
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--checkpoint-dir",type=Path,required=True)
    p.add_argument("--seed",type=int,default=271)
    p.add_argument("--steps",type=int,default=8)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    r=run(checkpoint_dir=a.checkpoint_dir,seed=a.seed,steps=a.steps)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({"zero_shot":r["zero_shot_64_checkpoint_at_128"]["heldout"],
        "after":r["after_fine_tuning"]["heldout"],
        "rotated":r["after_fine_tuning"]["rotated_heldout"],
        "seconds":r["fine_tuning"]["seconds"],"rss_kib":r["peak_process_ru_maxrss_kib"]},indent=2))


if __name__=="__main__":
    main()
