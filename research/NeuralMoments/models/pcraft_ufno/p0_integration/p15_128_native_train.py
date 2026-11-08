"""P15: first genuinely trained 128^3 native P-CRAFT PINO pilot.

All PINO weights are trainable. Uses activation checkpointing on every
spectral U-FNO block, batch=1, chunked evaluation, geometry-grouped
exact cube augmentation, and the full SpinPINOLoss. Labels are analytic
P0 only, never W2/Cherchi. One seed is a capacity pilot, not a final
statistical claim.
"""
from __future__ import annotations
import argparse, json, resource, time
from pathlib import Path
import torch

from ..spin_pino.dataset import generate_splits
from ..spin_pino.spin_pino import SpinPINO, SpinPINOLoss
from ..spin_pino.train import run_seed, _evaluate
from ..densicrafter_pino.p13b_highres import exact_discrete_cut_moments


def _metric(a,b):
    return float((a-b).norm()/b.norm().clamp_min(1e-12))


def run(*, seed=271, steps=12, batch_size=1, eval_batch_size=1,
        train_geometries_per_family=6, test_ellipsoid_geometries=4,
        queries_per_geometry=2, points_per_axis=8):
    grid=128
    torch.set_num_threads(1)
    started=time.perf_counter()
    result=run_seed(
        seed=seed,
        train_geometries_per_family=train_geometries_per_family,
        test_ellipsoid_geometries=test_ellipsoid_geometries,
        queries_per_geometry=queries_per_geometry,
        steps=steps,batch_size=batch_size,eval_batch_size=eval_batch_size,
        grid_size=grid,points_per_axis=points_per_axis,
        smoothing=.04,preconditioned_loss=True,pcgrad=False,
        moment_parameterization="logistic_atom",temperature=.12,
        geometry_adapter="none",lambda_equivariance=0.0,
        rotation_augmentation=True,rotation_augmentation_mode="cube_group",
        evaluation_rotation_mode="so3",use_gradient_checkpoint=True,
        device="cpu",
    )
    train_wall=time.perf_counter()-started
    state=result.pop("checkpoint_state")
    if not result["claims"]["trained_spin_model"]:
        raise AssertionError("PINO main backbone was not trained")
    if result["claims"]["cherchi_supervised"]:
        raise AssertionError("analytic P0 must not claim Cherchi supervision")
    if result["model_config"]["grid_size"]!=grid:
        raise AssertionError("native Fourier grid mismatch")
    if not result["model_config"]["use_gradient_checkpoint"]:
        raise AssertionError("gradient checkpointing was not enabled")

    splits=generate_splits(
        seed=seed,train_geometries_per_family=train_geometries_per_family,
        test_ellipsoid_geometries=test_ellipsoid_geometries,
        queries_per_geometry=queries_per_geometry,grid_size=grid,
    )
    if splits["metadata"]["test_sha256"]!=result["dataset"]["test_sha256"]:
        raise AssertionError("independent test dataset digest mismatch")
    model=SpinPINO(
        width=8,modes=4,n_layers=4,grid_size=grid,
        points_per_axis=points_per_axis,hidden_dim=48,smoothing=.04,
        moment_parameterization="logistic_atom",temperature=.12,
        geometry_adapter="none",use_gradient_checkpoint=True,
    ).eval()
    model.load_state_dict(state,strict=True)
    test=splits["test"]
    metrics=_evaluate(model,test,batch_size=eval_batch_size)
    D,c,target_r,target_J,meta=test
    pred_r_parts=[];pred_J_parts=[];discrete_parts=[]
    physics_values=[]
    criterion=SpinPINOLoss(lambda_data=1.,lambda_physics=.05,lambda_jacobian=.25)
    with torch.no_grad():
        for i in range(len(D)):
            w=model.encode_geometry(D[i:i+1])
            pred_r_parts.append(model.moment_from_weights(w,c[i:i+1]))
            pred_J_parts.append(model.jacobian_from_weights(w,c[i:i+1]))
            discrete_parts.append(exact_discrete_cut_moments(D[i:i+1,0:1],c[i:i+1]))
            losses=criterion(model,w,c[i:i+1],target_moments=target_r[i:i+1],
                             target_jacobian=target_J[i:i+1],derivative_admitted=True)
            physics_values.append(float(losses["physics"]))
    pred_r=torch.cat(pred_r_parts);pred_J=torch.cat(pred_J_parts)
    discrete=torch.cat(discrete_parts)
    checkpoint=Path(f"/tmp/w6_p15_grid128_seed{seed}.pt")
    torch.save({
        "state_dict":state,"seed":seed,"grid_size":128,
        "width":8,"modes":4,"n_layers":4,"points_per_axis":points_per_axis,
        "use_gradient_checkpoint":True,
        "source":"ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI",
    },checkpoint)
    return {
        "schema":"W6_P15_NATIVE_128_CUBE_TRAINED_PINO_PILOT_V1",
        "seed":seed,"input_grid":128,"PINO_internal_Fourier_grid":128,
        "width":8,"modes":4,"n_layers":4,
        "points_per_axis":points_per_axis,"quadrature_atoms":points_per_axis**3,
        "trainable_parameters":result["trainable_parameters"],
        "all_PINO_parameters_trainable":True,
        "PINO_main_backbone":"P-CRAFT factorized F-FNO/U-FNO",
        "external_GINO_QuadrANN_UQNO_disabled":True,
        "use_gradient_checkpoint":True,
        "train_batch_size":batch_size,"evaluation_batch_size":eval_batch_size,
        "train_geometry_count_per_family":train_geometries_per_family,
        "test_ellipsoid_geometry_count":test_ellipsoid_geometries,
        "queries_per_geometry":queries_per_geometry,
        "training":{"steps":steps,"selected_step":result["training"]["selected_step"],
            "seconds":result["training"]["seconds"],"end_to_end_wall_seconds":train_wall,
            "history":result["training"]["history"],
            "loss_conditioning":result["loss_conditioning"]},
        "dataset":result["dataset"],
        "fit_metrics":result["fit_metrics"],
        "validation_metrics":result["validation_metrics"],
        "heldout_ellipsoid_metrics":metrics,
        "heldout_SO3_rotated_ellipsoid_metrics":result["held_out_rotated_ellipsoid_metrics"],
        "rotation_diagnostics":result["rotation_evaluation_diagnostics"],
        "independent_discrete_validation":{
            "model_r_vs_analytic_continuum_relative_l2":_metric(pred_r,target_r),
            "model_J_vs_analytic_continuum_relative_l2":_metric(pred_J,target_J),
            "cell_centered_hard_cut_vs_analytic_continuum_relative_l2":_metric(discrete,target_r),
            "model_r_vs_independent_hard_cut_relative_l2":_metric(pred_r,discrete),
            "mean_SpinPINOLoss_physics_identity_residual":sum(physics_values)/len(physics_values),
        },
        "checkpoint":str(checkpoint),
        "peak_process_ru_maxrss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "claims":{"trained_native_128_PINO":True,"PINO_primary":True,
            "Cherchi_supervised":False,"arbitrary_quadric_certified":False,
            "native_Newton_admitted":False,"512_cube_trained":False,
            "real_Spin_end_to_end_validated":False},
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--seed",type=int,default=271)
    p.add_argument("--steps",type=int,default=12)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=run(seed=a.seed,steps=a.steps)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({
        "resolution":128,"steps":result["training"]["steps"],
        "train_seconds":result["training"]["seconds"],
        "test_r_relative_l2":result["heldout_ellipsoid_metrics"]["r_relative_l2"],
        "test_J_relative_l2":result["heldout_ellipsoid_metrics"]["J_relative_l2"],
        "peak_rss_kib":result["peak_process_ru_maxrss_kib"],
    },indent=2))


if __name__=="__main__":
    main()
