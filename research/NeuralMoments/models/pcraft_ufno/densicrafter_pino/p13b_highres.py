"""P13b high-resolution CPU feasibility tournament: DensiCrafter x Spin-PINO.

Design density rho is optimized at N^3. The PINO spectral trunk STILL runs
at its configured small grid (default 8^3), so this is NOT an N^3 native FNO.
Two independent checks are used:
  (1) cell-centered, density-weighted full-material raw ten moments, and
  (2) cell-centered HARD sign(beta_c) cut moments computed without PINO.

Only analytic/synthetic geometry and RANDOM untrained PINO are used.
Do not call this a CAD, printed-object or Cherchi-certified optimizer.
"""
from __future__ import annotations

import argparse
import json
import math
import resource
import time
from pathlib import Path

import torch

from .bridge import DensiCrafterSpinPINOBridge, material_moments, physical_grid
from ..spin_pino.spin_pino import SpinPINO

ARMS=("densicrafter_only","pino_only","weighted_coupled","feasible_joint")


def masks(n: int, *, wall_cells: int = 2, device="cpu"):
    if not isinstance(n,int) or n < 8:
        raise ValueError("at least 8 cells per axis required")
    if not isinstance(wall_cells,int) or not (1 <= wall_cells < n//2):
        raise ValueError("invalid wall thickness")
    solid=torch.zeros((1,1,n,n,n),dtype=torch.bool,device=device)
    for axis in range(2,5):
        for at in (slice(0,wall_cells),slice(n-wall_cells,n)):
            slices=[slice(None)]*5
            slices[axis]=at
            solid[tuple(slices)]=True
    return solid,~solid


def _pino():
    # Tiny but actual P-CRAFT factorized-U-FNO: the frozen 8^3 trunk
    # is not being mistaken for a 64/128^3 high-res Fourier operator.
    return SpinPINO(
        width=4,modes=2,n_layers=2,grid_size=8,points_per_axis=4,
        hidden_dim=32,moment_parameterization="logistic_atom",temperature=.12,
    ).eval()


def exact_discrete_cut_moments(density:torch.Tensor,coeff:torch.Tensor):
    """PINO-INDEPENDENT voxel-center quadrature of rho * 1[beta_c>=0].

    Real cut at a grid cell is sub-voxel and discontinuous in c. This
    deliberately checks a separate discrete physical quantity, NOT
    a native smooth Cherchi/CAD derivative and NOT exact continuum volume.
    """
    if density.ndim!=5 or density.shape[1]!=1:
        raise ValueError("density must be [B,1,X,Y,Z]")
    if coeff.shape!=(density.shape[0],10) or not bool(torch.isfinite(coeff).all()):
        raise ValueError("c must be finite [B,10]")
    xyz=physical_grid(density.shape[-3:],device=density.device,dtype=density.dtype)
    x,y,z=xyz.unbind(-1)
    monomials=torch.stack([torch.ones_like(x),x,y,z,x*x,y*y,z*z,y*z,x*z,x*y],-1)
    doubled=monomials.new_tensor([1.,1.,1.,1.,1.,1.,1.,2.,2.,2.])
    beta=torch.einsum("bq,xyzq->bxyz",coeff,monomials*doubled)
    region=(beta>=0).to(density.dtype)
    vol=8.0/math.prod(density.shape[-3:])
    return torch.einsum("bxyz,xyzq->bq",density[:,0]*region,monomials)*vol


def _relative_norm(new:torch.Tensor,reference:torch.Tensor):
    return float((new-reference).norm().detach()/reference.norm().clamp_min(1e-8).detach())


def _normalized_ledger(density):
    ten=material_moments(density)
    return ten/ten[:,:1].clamp_min(1e-8)


def _feasibility(model,coeff,model_ref,cut_ref,normalized_ref,*,tolerances):
    with torch.no_grad():
        out=model(coeff)
        cut=exact_discrete_cut_moments(out["density"],coeff)
        normalized=_normalized_ledger(out["density"])
        errors={
            "model_cut_r_relative_l2":_relative_norm(out["moments"],model_ref),
            "independent_discrete_cut_r_relative_l2":_relative_norm(cut,cut_ref),
            "normalized_full_9_moment_l2":float(
                (normalized[:,1:]-normalized_ref[:,1:]).norm()
            ),
        }
        feasible=all(errors[k] <= tolerances[k]+1e-8 for k in tolerances)
        if not bool(torch.isfinite(out["moments"]).all()):
            feasible=False
        return feasible,errors


def _objective_weights(arm):
    if arm=="densicrafter_only":
        return dict(mass=1.0,com_contact=.2,negative_contact_area=.02,
                    com_height=.05,cut_moment_error=0.)
    if arm=="pino_only":
        return dict(mass=0.,com_contact=0.,negative_contact_area=0.,
                    com_height=0.,cut_moment_error=25.)
    if arm in ("weighted_coupled","feasible_joint"):
        return dict(mass=1.0,com_contact=.2,negative_contact_area=.02,
                    com_height=.05,cut_moment_error=25.)
    raise ValueError("unknown arm")


def _run_arm(n,pino,wall_cells,coeff,initial_model_r,
             initial_cut_r,initial_ledger,arm,steps,lr,tolerances):
    shell,design=masks(n,wall_cells=wall_cells)
    model=DensiCrafterSpinPINOBridge(
        pino,shell,design,gravity_axis=2,smoothing=False
    )
    weights=_objective_weights(arm)
    optim=torch.optim.Adam([model.density_logits],lr=lr)
    start=time.perf_counter()
    with torch.no_grad():
        init=model(coeff,reference_cut_moments=initial_model_r,weights=weights)
        start_loss=float(init["loss"])
        start_mass=float(init["full_material_moments"][0,0])
    accepted=0; rejected=0
    for _ in range(steps):
        model.train()
        result=model(coeff,reference_cut_moments=initial_model_r,weights=weights)
        optim.zero_grad(set_to_none=True)
        result["loss"].backward()
        if not bool(torch.isfinite(model.density_logits.grad).all()):
            raise FloatingPointError("nonfinite density-design gradient")
        if arm=="feasible_joint":
            previous=model.density_logits.detach().clone()
        optim.step()
        if arm=="feasible_joint":
            proposed=model.density_logits.detach().clone()
            success=False
            for division in range(9):
                alpha=2.0**(-division)
                with torch.no_grad():
                    model.density_logits.copy_(
                        previous+(proposed-previous)*alpha
                    )
                ok,_=_feasibility(
                    model,coeff,initial_model_r,initial_cut_r,
                    initial_ledger,tolerances=tolerances,
                )
                if ok:
                    success=True
                    accepted+=1
                    break
            if not success:
                with torch.no_grad():
                    model.density_logits.copy_(previous)
                rejected+=1
    elapsed=time.perf_counter()-start
    with torch.no_grad():
        output=model(coeff,reference_cut_moments=initial_model_r,weights=weights)
        end_cut=exact_discrete_cut_moments(output["density"],coeff)
        end_ledger=_normalized_ledger(output["density"])
        end_loss=float(output["loss"])
        end_mass=float(output["full_material_moments"][0,0])
        final_ok,errors=_feasibility(model,coeff,initial_model_r,initial_cut_r,
                                     initial_ledger,tolerances=tolerances)
        frozen_shell=bool((output["density"][shell]==1.).all())
        if not frozen_shell:
            raise AssertionError("protected shell changed")
        if arm=="feasible_joint" and not final_ok:
            raise AssertionError("feasibility filter admitted an infeasible state")
        return {
            "arm":arm,"grid":n,"wall_cells":wall_cells,
            "steps":steps,"objective_initial":start_loss,
            "objective_final":end_loss,
            "mass_initial":start_mass,"mass_final":end_mass,
            "material_reduction_fraction":1.0-end_mass/max(start_mass,1e-8),
            "model_r_relative_l2_error":errors["model_cut_r_relative_l2"],
            "independent_cut_r_relative_l2_error":errors["independent_discrete_cut_r_relative_l2"],
            "normalized_full_9_moment_l2_error":errors["normalized_full_9_moment_l2"],
            "feasible_under_predeclared_tolerances":final_ok,
            "accepted_steps":accepted if arm=="feasible_joint" else None,
            "rejected_steps":rejected if arm=="feasible_joint" else None,
            "outer_shell_preserved":frozen_shell,
            "coupled_gradients_computed":True,
            "cpu_seconds":elapsed,
            "PINO_grid_size":pino.encoder.grid_size,
            "native_Cherchi_J_admitted":False,
        }


def run(resolutions=(32,64),steps=12,wall_cells=2,lr=.12):
    if not resolutions or steps<1 or not 0<lr<1:
        raise ValueError("positive resolution/updates and lr in (0,1)")
    torch.manual_seed(20261108)
    torch.set_num_threads(1)
    tolerances={
        "model_cut_r_relative_l2":.045,
        "independent_discrete_cut_r_relative_l2":.045,
        "normalized_full_9_moment_l2":.04,
    }
    cases=[]
    for n in resolutions:
        if n<8:
            raise ValueError("grid must be >=8")
        pino=_pino()
        for par in pino.parameters():
            par.requires_grad_(False)
        coeff=torch.tensor([[.08,0.,0.,.75,.03,0.,.0,0.,0.,0.]],
                           dtype=torch.float32)
        shell,design=masks(n,wall_cells=wall_cells)
        initial=DensiCrafterSpinPINOBridge(pino,shell,design)
        with torch.no_grad():
            pred=initial(coeff)
            model_ref=pred["moments"].detach().clone()
            cut_ref=exact_discrete_cut_moments(pred["density"],coeff).detach().clone()
            norm_ref=_normalized_ledger(pred["density"]).detach().clone()
            material_mass_ref=float(pred["full_material_moments"][0,0])
        cases.append({
            "source_resolution":n,
            "active_density_cells":int(design.sum().item()),
            "protected_shell_cells":int(shell.sum().item()),
            "initial_independent_cut_moments":cut_ref[0].tolist(),
            "initial_full_material_mass":material_mass_ref,
            "PINO_operator_grid_size":pino.encoder.grid_size,
            "results":[_run_arm(
                n,pino,wall_cells,coeff,model_ref,cut_ref,norm_ref,
                arm,steps,lr,tolerances
            ) for arm in ARMS],
        })
    return {
        "schema":"W6_P13B_DENSICRAFTER_PINO_CPU_ABLATION_V1",
        "random_model_seed":20261108,"resolutions":list(resolutions),
        "steps_per_arm":steps,"wall_thickness_cells":wall_cells,
        "constraint_tolerances":tolerances,
        "PINO_trunk":"original P-CRAFT factorized-FNO U-FNO",
        "PINO_neural_weights_trained":False,
        "source_512_GPU_training":False,
        "independent_cut_check":"hard cell-centered voxel reference; NOT exact CAD",
        "real_continuum_Cherchi_reference":False,
        "native_Newton_J_admitted":False,
        "case_results":cases,
        "peak_process_ru_maxrss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }


def stress_128(n=128):
    """One full 128^3 density/PINO forward-backward, no optimization claims."""
    torch.manual_seed(20261108)
    torch.set_num_threads(1)
    pino=_pino().eval()
    for par in pino.parameters():
        par.requires_grad_(False)
    shell,design=masks(n,wall_cells=2)
    model=DensiCrafterSpinPINOBridge(pino,shell,design)
    coeff=torch.tensor([[.08,0.,0.,.75,.03,0.,0.,0.,0.,0.]],
                       dtype=torch.float32)
    tic=time.perf_counter()
    result=model(coeff)
    result["moments"].sum().backward()
    seconds=time.perf_counter()-tic
    grad=model.density_logits.grad
    return {
        "stress_resolution":n,
        "input_voxels":n**3,
        "internal_PINO_operator_grid":pino.encoder.grid_size,
        "full_resolution_operator":False,
        "full_resolution_density_design_gradient":bool(
            torch.isfinite(grad).all() and grad[design].abs().sum()>0
        ),
        "protected_shell_exact":bool((result["density"][shell]==1.).all()),
        "cpu_forward_backward_seconds":seconds,
        "peak_process_ru_maxrss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "native_Cherchi_validated":False,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--resolutions",default="32,64")
    p.add_argument("--steps",type=int,default=12)
    p.add_argument("--wall-cells",type=int,default=2)
    p.add_argument("--stress-128",action="store_true")
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.stress_128:
        result=stress_128()
    else:
        resolution=tuple(int(x) for x in a.resolutions.split(","))
        result=run(resolutions=resolution,steps=a.steps,wall_cells=a.wall_cells)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,allow_nan=False,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2,allow_nan=False,sort_keys=True))

if __name__=="__main__":
    main()
