"""P14: train the actual P-CRAFT PINO backbone at native 16/32/64 Fourier grids.

This calls the repository real run_seed() training loop, not the P13
random-weight forward/backward probe. Every PINO parameter is trainable.
Labels are exact analytic continuum P0 box/sphere cuts and analytic
Jacobians; held-out geometry family is ellipsoid. SpinPINOLoss includes
data, convex-potential physics identities, and admitted analytic-J
supervision. The P0 label scope is NOT Cherchi/CAD admission.
"""
from __future__ import annotations
import argparse, json, resource, time
from pathlib import Path
import torch

from ..spin_pino.dataset import generate_splits
from ..spin_pino.spin_pino import SpinPINO, SpinPINOLoss
from ..spin_pino.train import run_seed
from ..densicrafter_pino.p13b_highres import exact_discrete_cut_moments


def _model(grid, points):
    return SpinPINO(
        width=8, modes=4, n_layers=4, grid_size=grid,
        points_per_axis=points, hidden_dim=48, smoothing=.04,
        moment_parameterization="logistic_atom", temperature=.12,
        geometry_adapter="none",
    )


def _metric(a,b):
    return float((a-b).norm()/b.norm().clamp_min(1e-12))


def run_resolution(*, grid_size, seeds=(271,277,281), steps=40,
                   batch_size=2, train_geometries_per_family=8,
                   test_ellipsoid_geometries=6, queries_per_geometry=2,
                   points_per_axis=8):
    if grid_size not in (16,32,64):
        raise ValueError("P14 first-stage native Fourier grids are 16,32,64")
    if not seeds or steps<1 or batch_size<1 or points_per_axis<4:
        raise ValueError("invalid P14 training configuration")
    torch.set_num_threads(1)
    rows=[]
    reference_ids={}
    for seed in seeds:
        low=generate_splits(seed=seed,
            train_geometries_per_family=train_geometries_per_family,
            test_ellipsoid_geometries=test_ellipsoid_geometries,
            queries_per_geometry=queries_per_geometry,grid_size=8)
        high=generate_splits(seed=seed,
            train_geometries_per_family=train_geometries_per_family,
            test_ellipsoid_geometries=test_ellipsoid_geometries,
            queries_per_geometry=queries_per_geometry,grid_size=grid_size)
        for split in ("fit","validation","test"):
            low_ids=low["metadata"][split+"_geometry_ids"]
            high_ids=high["metadata"][split+"_geometry_ids"]
            if low_ids!=high_ids:
                raise AssertionError("geometry identities changed with voxel resolution")
            reference_ids[split]=high_ids

        started=time.perf_counter()
        result=run_seed(
            seed=seed,
            train_geometries_per_family=train_geometries_per_family,
            test_ellipsoid_geometries=test_ellipsoid_geometries,
            queries_per_geometry=queries_per_geometry,
            steps=steps,
            batch_size=batch_size,
            grid_size=grid_size,
            points_per_axis=points_per_axis,
            smoothing=.04,
            preconditioned_loss=True,
            pcgrad=False,
            moment_parameterization="logistic_atom",
            temperature=.12,
            geometry_adapter="none",
            lambda_equivariance=0.0,
            rotation_augmentation=True,
            rotation_augmentation_mode="cube",
            evaluation_rotation_mode="so3",
            device="cpu",
        )
        wall=time.perf_counter()-started
        state=result.pop("checkpoint_state")
        if not result["claims"]["trained_spin_model"]:
            raise AssertionError("PINO backbone was not trained")
        if result["claims"]["cherchi_supervised"]:
            raise AssertionError("P0 training cannot claim Cherchi labels")
        if result["model_config"]["grid_size"]!=grid_size:
            raise AssertionError("wrong internal PINO Fourier grid")
        model=_model(grid_size,points_per_axis).eval()
        model.load_state_dict(state,strict=True)
        if model.encoder.grid_size!=grid_size:
            raise AssertionError("checkpoint did not load into native-grid PINO")
        test=high["test"]
        D,c,target_r,target_J,meta=test
        with torch.no_grad():
            prepared=model.encoder._prepare_geometry(D)
            if prepared.shape[-3:]!=(grid_size,)*3:
                raise AssertionError("input was silently downsampled")
            weights=model.encode_geometry(D)
            pred_r=model.moment_from_weights(weights,c)
            pred_J=model.jacobian_from_weights(weights,c)
            discrete=exact_discrete_cut_moments(D[:,0:1],c)
            criterion=SpinPINOLoss(lambda_data=1.,lambda_physics=.05,
                                   lambda_jacobian=.25)
            physics=criterion(model,weights,c,target_moments=target_r,
                              target_jacobian=target_J,
                              derivative_admitted=True)
        checkpoint_path=Path(f"/tmp/w6_p14_grid{grid_size}_seed{seed}.pt")
        torch.save({
            "state_dict":state,"seed":seed,"grid_size":grid_size,
            "points_per_axis":points_per_axis,"width":8,"modes":4,
            "n_layers":4,"source":"ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI",
        },checkpoint_path)
        rows.append({
            "seed":seed,
            "fit_geometry_ids":high["metadata"]["fit_geometry_ids"],
            "validation_geometry_ids":high["metadata"]["validation_geometry_ids"],
            "heldout_ellipsoid_geometry_ids":high["metadata"]["test_geometry_ids"],
            "dataset_sha256":{"fit":high["metadata"]["fit_sha256"],
                "validation":high["metadata"]["validation_sha256"],
                "test":high["metadata"]["test_sha256"]},
            "training":{"steps":result["training"]["steps"],
                "selected_step":result["training"]["selected_step"],
                "seconds":result["training"]["seconds"],
                "end_to_end_wall_seconds":wall,
                "trainable_parameters":result["trainable_parameters"],
                "loss_conditioning":result["loss_conditioning"],
                "history":result["training"]["history"]},
            "model_config":result["model_config"],
            "fit_metrics":result["fit_metrics"],
            "validation_metrics":result["validation_metrics"],
            "heldout_ellipsoid_metrics":result["held_out_ellipsoid_metrics"],
            "heldout_so3_rotated_metrics":result["held_out_rotated_ellipsoid_metrics"],
            "rotation_diagnostics":result["rotation_evaluation_diagnostics"],
            "independent_discrete_test":{
                "model_r_vs_analytic_continuum_relative_l2":_metric(pred_r,target_r),
                "model_J_vs_analytic_continuum_relative_l2":_metric(pred_J,target_J),
                "voxel_hard_cut_vs_analytic_continuum_relative_l2":_metric(discrete,target_r),
                "model_r_vs_independent_voxel_hard_cut_relative_l2":_metric(pred_r,discrete),
                "physics_identity_loss":float(physics["physics"]),
                "complement_residual":float(physics["complement"]),
                "radial_residual":float(physics["radial"]),
                "jacobian_symmetry_residual":float(physics["jacobian_symmetry"]),
                "jacobian_psd_residual":float(physics["jacobian_psd"]),
                "mass_bounds_residual":float(physics["mass_bounds"]),
                "analytic_J_supervision_loss":float(physics["jacobian_supervision"])},
            "checkpoint_file":str(checkpoint_path),"claims":result["claims"],
        })
    def mean(path):
        vals=[]
        for row in rows:
            x=row
            for k in path:
                x=x[k]
            vals.append(float(x))
        return sum(vals)/len(vals)
    aggregate={
        "mean_train_seconds":mean(("training","seconds")),
        "mean_parameters":mean(("training","trainable_parameters")),
        "mean_test_r_relative_l2":mean(("heldout_ellipsoid_metrics","r_relative_l2")),
        "mean_test_J_relative_l2":mean(("heldout_ellipsoid_metrics","J_relative_l2")),
        "mean_rotated_r_relative_l2":mean(("heldout_so3_rotated_metrics","r_relative_l2")),
        "mean_rotated_J_relative_l2":mean(("heldout_so3_rotated_metrics","J_relative_l2")),
        "mean_independent_discrete_cut_vs_continuum":mean(("independent_discrete_test","voxel_hard_cut_vs_analytic_continuum_relative_l2")),
        "mean_physics_identity_loss":mean(("independent_discrete_test","physics_identity_loss")),
    }
    return {
        "schema":"W6_P14_NATIVE_HIGHRES_TRAINED_PINO_V1",
        "resolution":grid_size,"PINO_internal_fourier_grid":grid_size,
        "input_grid":grid_size,"points_per_axis":points_per_axis,
        "quadrature_atoms":points_per_axis**3,
        "backbone":"P-CRAFT SpinPINO factorized F-FNO/U-FNO",
        "all_PINO_parameters_trainable":True,
        "external_GINO_QuadrANN_UQNO_disabled":True,
        "full_SpinPINOLoss_used":True,
        "preconditioned_loss_fit_split_only":True,
        "rotation_augmentation":"one exact cube rotation appended per fit sample",
        "test":"unseen ellipsoid geometry family + SO(3)-rotated ellipsoids",
        "label_source":"ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI",
        "analytic_J_supervision_scope":"strictly interior vertical-plane box/sphere cuts only",
        "seeds":list(seeds),"steps_per_seed":steps,"batch_size":batch_size,
        "geometry_ids_resolution_invariant":True,"reference_geometry_ids":reference_ids,
        "aggregate":aggregate,"per_seed":rows,
        "peak_process_ru_maxrss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "claims":{"trained_native_highres_PINO":True,"PINO_is_primary_backbone":True,
            "Cherchi_supervised":False,"arbitrary_quadric_certified":False,
            "native_Newton_admitted":False,"512_cube_training":False,
            "real_Spin_end_to_end_validated":False},
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--grid-size",type=int,required=True,choices=(16,32,64))
    p.add_argument("--seeds",default="271,277,281")
    p.add_argument("--steps",type=int,default=40)
    p.add_argument("--batch-size",type=int,default=2)
    p.add_argument("--points-per-axis",type=int,default=8)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=run_resolution(grid_size=a.grid_size,
        seeds=tuple(int(x) for x in a.seeds.split(",")),
        steps=a.steps,batch_size=a.batch_size,
        points_per_axis=a.points_per_axis)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps(result["aggregate"],indent=2,sort_keys=True))


if __name__=="__main__":
    main()
