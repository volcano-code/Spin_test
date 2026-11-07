"""P13a measured DensiCrafter physical-design + PINO-density gradient smoke.

Restricted CPU proof of differentiable integration; no true CAD/strength,
native Cherchi gradient certification or 512^3 training.
"""
from __future__ import annotations

import argparse
import json
import resource
import time
from pathlib import Path

import torch

from .bridge import DensiCrafterSpinPINOBridge
from ..spin_pino.spin_pino import SpinPINO


def make_masks(n, device):
    shell=torch.zeros((1,1,n,n,n),device=device,dtype=torch.bool)
    for dim in range(2,5):
        starts=[slice(None)]*5
        starts[dim]=0
        shell[tuple(starts)]=True
        ends=[slice(None)]*5
        ends[dim]=-1
        shell[tuple(ends)]=True
    return shell,~shell


def run(resolutions=(8,16),updates=12):
    torch.manual_seed(20261107)
    torch.set_num_threads(1)
    entries=[]
    for n in resolutions:
        if n<8 or updates<1:
            raise ValueError("at least 8 voxels and one optimization update required")
        net=SpinPINO(
            width=4,modes=2,n_layers=2,grid_size=8,
            points_per_axis=4,hidden_dim=32,
            moment_parameterization="logistic_atom",temperature=.12
        ).eval()
        for param in net.parameters():
            param.requires_grad_(False)
        shell,design=make_masks(n,device=torch.device("cpu"))
        model=DensiCrafterSpinPINOBridge(
            net,shell,design,gravity_axis=2,smoothing=False,
        )
        coeff=torch.tensor([[.15,.08,.0,.7,.0,.02,.0,.0,.0,.0]],dtype=torch.float32)
        with torch.no_grad():
            baseline=model(coeff)
            target=baseline["moments"].detach().clone()
        model.zero_grad(set_to_none=True)
        model(coeff)["moments"].sum().backward()
        gradient_norm=float(model.density_logits.grad[design].norm())
        model.zero_grad(set_to_none=True)
        if not gradient_norm>0:
            raise RuntimeError("no gradient from PINO output to material density")
        weights={
            "mass":1.0,"com_contact":.2,
            "negative_contact_area":.02,"com_height":.05,
            "cut_moment_error":2.0,
        }
        initial=model(coeff,reference_cut_moments=target,weights=weights)
        initial_loss=float(initial["loss"].detach())
        initial_mass=float(initial["full_material_moments"][0,0].detach())
        timer=time.perf_counter()
        opt=torch.optim.Adam([model.density_logits],lr=.1)
        for _ in range(updates):
            out=model(coeff,reference_cut_moments=target,weights=weights)
            opt.zero_grad(set_to_none=True)
            out["loss"].backward()
            opt.step()
        elapsed=time.perf_counter()-timer
        result=model(coeff,reference_cut_moments=target,weights=weights)
        final_loss=float(result["loss"].detach())
        final_mass=float(result["full_material_moments"][0,0].detach())
        if not final_loss<initial_loss:
            raise AssertionError("coupled objective failed to decrease")
        if not bool((result["density"][shell]==1).all()):
            raise AssertionError("protected shell changed")
        if not bool(torch.isfinite(result["moments"]).all()
                    and torch.isfinite(result["model_jacobian_diagnostic"]).all()):
            raise FloatingPointError("nonfinite model response")
        entries.append({
            "resolution":n,
            "optimizer_updates":updates,
            "PINO_drho_gradient_norm":gradient_norm,
            "initial_joint_loss":initial_loss,
            "final_joint_loss":final_loss,
            "initial_full_material_mass":initial_mass,
            "final_full_material_mass":final_mass,
            "relative_material_mass_reduction":1-final_mass/initial_mass,
            "cut_moment_deviation_L2":float(
                torch.linalg.vector_norm((result["moments"]-target).detach())
            ),
            "wall_clock_optimization_seconds":elapsed,
            "shell_cells_protected":int(shell.sum()),
            "geometry_design_cells":int(design.sum()),
            "native_J_admitted":result["native_jacobian_admitted"],
            "Cherchi_teacher_used":result["w0_w2_cherchi_training_admitted"],
        })
    return {
        "schema":"W6_P13A_DENSICRAFTER_TO_PINO_CPU_SMOKE_V1",
        "seed":20261107,"source":"DensiCrafter MIT physical loss core + P-CRAFT PINO",
        "PINO_main_backbone":True,
        "only_density_logits_optimized":True,
        "full_512_training":False,
        "native_CAD_or_FEM_certification":False,
        "original_TRELLIS_pipeline_reproduced":False,
        "experiments":entries,
        "peak_process_ru_maxrss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--updates",type=int,default=12)
    args=p.parse_args()
    result=run(updates=args.updates)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
