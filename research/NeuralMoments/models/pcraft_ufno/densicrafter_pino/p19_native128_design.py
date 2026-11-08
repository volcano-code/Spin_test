"""P19: native 128^3 DensiCrafter design with a trained 64^3 PINO transferred to 128.

The complete P-CRAFT SpinPINO state_dict is strictly loaded from the P14
64^3 trained checkpoint into the same network at a true 128^3 Fourier grid.
All PINO weights are frozen; only material density logits are optimized.
The U-FNO blocks use activation checkpointing for gradients w.r.t. density.
"""
from __future__ import annotations
import argparse,json,resource,statistics
from pathlib import Path
import torch

from ..analytic_cut import sample_dataset
from ..spin_pino.spin_pino import SpinPINO
from .bridge import DensiCrafterSpinPINOBridge,material_moments
from .p13b_highres import exact_discrete_cut_moments
from .p17_trained_pino import (
    _surface_masks,_normalised_material_moments,_run_arm,
)


def _relative(a,b):
    return float((a-b).norm()/b.norm().clamp_min(1e-8))


def run(*,checkpoint_dir,seed=271,steps=3,lr=.03,wall_cells=4):
    torch.set_num_threads(1)
    source=Path(checkpoint_dir)/f"w6_p14_grid64_seed{seed}.pt"
    if not source.is_file():
        raise FileNotFoundError(f"missing trained P14 checkpoint: {source}")
    package=torch.load(source,map_location="cpu",weights_only=False)
    if package.get("seed")!=seed or package.get("grid_size")!=64:
        raise ValueError("source checkpoint provenance mismatch")
    pino=SpinPINO(width=8,modes=4,n_layers=4,grid_size=128,
        points_per_axis=8,hidden_dim=48,smoothing=.04,
        moment_parameterization="logistic_atom",temperature=.12,
        geometry_adapter="none",use_gradient_checkpoint=True).eval()
    incompatible=pino.load_state_dict(package["state_dict"],strict=True)
    if incompatible.missing_keys or incompatible.unexpected_keys:
        raise AssertionError("strict P14-to-128 state transfer failed")
    for parameter in pino.parameters():
        parameter.requires_grad_(False)
    # InstanceNorm3d has no running statistics in this architecture. Train
    # mode activates non-reentrant checkpointing for density-input gradients.
    pino.train()
    if any(parameter.requires_grad for parameter in pino.parameters()):
        raise AssertionError("PINO weights must stay frozen during design")

    data=sample_dataset(("sphere",),per_family=1,seed=seed+707,
                        grid_size=128,queries_per_geometry=1)
    D,c,_,_,metadata=data
    if D.shape[-3:]!=(128,128,128):
        raise AssertionError("128^3 source was silently downsampled")
    occupancy=D[:,1:2]>0
    shell,design=_surface_masks(occupancy,wall_cells=wall_cells)
    if not bool(shell.any() and design.any()):
        raise AssertionError("invalid 128^3 shell/design partition")

    baseline=DensiCrafterSpinPINOBridge(
        pino,shell,design,gravity_axis=2,smoothing=False
    )
    with torch.no_grad():
        baseline.density_logits.fill_(4.)
        initial=baseline(c)
        model_ref=initial["moments"].detach().clone()
        cut_ref=exact_discrete_cut_moments(initial["density"],c).detach().clone()
        norm_ref=_normalised_material_moments(initial["density"]).detach().clone()
    tolerances={"model_r_rel":.02,"independent_cut_r_rel":.02,
                "normalized_material_9moment_l2":.02}
    rows=[]
    for arm in ("densicrafter_only","pino_only","soft_joint","feasible_joint"):
        rows.append(_run_arm(pino,shell,design,c,model_ref,cut_ref,norm_ref,
                             arm,steps,lr,tolerances))
    saved={}
    for row in rows:
        density=row.pop("final_density")
        cut=row.pop("final_independent_cut")
        moments=row.pop("final_material_moments")
        saved[row["arm"]]={"density":density,"independent_cut":cut,
                           "material_moments":moments}
    checkpoint=Path(f"/tmp/w6_p19_native128_seed{seed}.pt")
    torch.save({
        "pino_state_dict":package["state_dict"],
        "pino_source":"P14 trained 64^3 seed checkpoint, strict loaded at 128^3",
        "seed":seed,"grid_size":128,"PINO_internal_Fourier_grid":128,
        "pino_width":8,"pino_modes":4,"pino_layers":4,
        "quadrature_atoms":512,"density_design":saved,
        "geometry_id":metadata[0]["geometry_id"],
        "wall_cells":wall_cells,
        "source":"ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI",
    },checkpoint)
    feasible=next(x for x in rows if x["arm"]=="feasible_joint")
    return {
        "schema":"W6_P19_NATIVE128_TRAINED_PINO_DENSICRAFTER_V1",
        "seed":seed,"resolution":128,"source_checkpoint":str(source),
        "source_resolution":64,"strict_full_state_transfer":True,
        "target_input_and_Fourier_grid":128,
        "pino":"P-CRAFT SpinPINO factorized F-FNO/U-FNO",
        "pino_width":8,"pino_modes":4,"pino_layers":4,
        "pino_parameters_frozen":True,"density_logits_trainable":True,
        "activation_checkpointing_for_density_gradient":True,
        "quadrature_atoms":512,
        "geometry_family":"sphere","geometry_id":metadata[0]["geometry_id"],
        "source_density_shape":list(D.shape),
        "wall_cells":wall_cells,
        "wall_thickness_scale_relative_to_P18_64":wall_cells/2*(64/128),
        "protected_shell_cells":int(shell.sum()),
        "design_cells":int(design.sum()),
        "reference_model_moments":model_ref[0].tolist(),
        "reference_independent_cut_moments":cut_ref[0].tolist(),
        "predeclared_tolerances":tolerances,
        "steps_per_arm":steps,"learning_rate":lr,
        "results":rows,
        "feasible_joint":{
            "mass_reduction_fraction":feasible["mass_reduction_fraction"],
            "model_cut_moment_relative_error":feasible["model_cut_moment_relative_error"],
            "independent_hard_cut_relative_error":feasible["independent_hard_cut_relative_error"],
            "normalized_material_9moment_l2":feasible["normalized_material_9moment_l2"],
            "accepted_steps":feasible["accepted_steps"],
            "rejected_steps":feasible["rejected_steps"],
            "feasible":feasible["feasible_under_predeclared_tolerances"],
            "outer_shell_preserved":feasible["outer_shell_preserved"],
        },
        "checkpoint":str(checkpoint),
        "peak_process_ru_maxrss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "claims":{"native_128_input_and_Fourier_grid":True,
            "trained_PINO_transferred_from_64":True,
            "DensiCrafter_density_design_executed":True,
            "independent_voxel_hard_cut_checked":True,
            "continuous_Cherchi":False,"FEM_strength":False,
            "millimeter_wall_certified":False,"native_Newton_admitted":False,
            "512_cube":False},
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--checkpoint-dir",type=Path,required=True)
    parser.add_argument("--seed",type=int,default=271)
    parser.add_argument("--steps",type=int,default=3)
    parser.add_argument("--lr",type=float,default=.03)
    parser.add_argument("--wall-cells",type=int,default=4)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result=run(checkpoint_dir=args.checkpoint_dir,seed=args.seed,
               steps=args.steps,lr=args.lr,wall_cells=args.wall_cells)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps(result["feasible_joint"],indent=2,sort_keys=True))


if __name__=="__main__":
    main()
