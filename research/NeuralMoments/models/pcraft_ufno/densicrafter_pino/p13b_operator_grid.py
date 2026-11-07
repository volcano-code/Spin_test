"""P13b second scale-gate: actual P-CRAFT Fourier grids, not just input grids.

One CPU forward+backward per independent Python process with full source
DensiCrafter design density. This probes 8/16/32/64^3 P-CRAFT U-FNO
operator-grid computation and associated CPU RSS. It is NOT 512^3 native
neural training and is not an accuracy benchmark of a trained teacher.
"""
from __future__ import annotations

import argparse
import json
import math
import resource
import time
from pathlib import Path

import torch

from ..spin_pino.spin_pino import SpinPINO
from .bridge import DensiCrafterSpinPINOBridge
from .p13b_highres import masks,exact_discrete_cut_moments


def source_alias_pair(n: int):
    """Differ in fine material within each 8^3 parent bin, same parent means."""
    if n<16 or n%16:
        raise ValueError("source grid must be divisible by 16 and >=16")
    shell,design=masks(n,wall_cells=2)
    a=torch.full((1,4,n,n,n),0.,dtype=torch.float32)
    a[:,0]=torch.where(shell[:,0],1.,torch.where(design[:,0],.5,0.))
    a[:,1]=(shell|design).float()[:,0]
    b=a.clone()
    period=n//8
    z=torch.arange(n)
    wave=torch.where((z%period)<period//2,-.30,.30).float()
    pattern=wave.view(1,1,1,1,n)
    # Modify only complete 8-grid parent bins that avoid the fixed shell.
    edit=torch.zeros((1,1,n,n,n),dtype=torch.bool)
    edit[:,:,period:n-period,period:n-period,period:n-period]=True
    b[:,0]=(b[:,0]+torch.where(edit[:,0],pattern,0.)).clamp(0.,1.)
    return a,b,shell,design


def run(source_resolution=64,operator_grid=32):
    if not isinstance(operator_grid,int) or operator_grid<8 or operator_grid%4:
        raise ValueError("operator grid must be >=8 and divisible by four")
    if source_resolution < operator_grid or source_resolution%16:
        raise ValueError("source must be >=operator and multiple of 16")
    torch.set_num_threads(1)
    torch.manual_seed(20261108)
    pino=SpinPINO(
        width=4,modes=2,n_layers=2,grid_size=operator_grid,
        points_per_axis=4,hidden_dim=32,
        moment_parameterization="logistic_atom",temperature=.12
    ).eval()
    for param in pino.parameters():
        param.requires_grad_(False)
    shell,design=masks(source_resolution,wall_cells=2)
    model=DensiCrafterSpinPINOBridge(
        pino,shell,design,gravity_axis=2,smoothing=False
    )
    c=torch.tensor([[-.11,0.,0.,.78,.03,0.,0.,0.,0.,0.]],dtype=torch.float32)
    start=time.perf_counter()
    out=model(c)
    out["moments"].sum().backward()
    elapsed=time.perf_counter()-start
    gradients=model.density_logits.grad
    if gradients is None or not bool(torch.isfinite(gradients).all()):
        raise FloatingPointError("missing/nonfinite density gradient")
    grad_norm=float(gradients[design].norm())
    if not grad_norm>0:
        raise AssertionError("no gradient from native-grid PINO to density")
    a,b,_,_=source_alias_pair(source_resolution)
    with torch.no_grad():
        reduced_a=pino.encoder._prepare_geometry(a)
        reduced_b=pino.encoder._prepare_geometry(b)
        preprocess_delta=float((reduced_a-reduced_b).abs().max())
        difference=float((exact_discrete_cut_moments(
            a[:,0:1],c
        )-exact_discrete_cut_moments(b[:,0:1],c)).abs().max())
    if difference<=1e-4:
        raise AssertionError("source alias pair has no independent cut difference")
    if operator_grid==8 and preprocess_delta>1e-6:
        raise AssertionError("8 cube PINO parent-pool alias contract failed")
    if operator_grid>=16 and preprocess_delta<=.05:
        raise AssertionError("higher native PINO grid still discards source detail")
    return {
        "schema":"W6_P13B_REAL_OPERATOR_GRID_CPU_GRADIENT_V1",
        "source_grid_size":source_resolution,
        "PINO_Fourier_operator_grid_size":operator_grid,
        "input_voxels":source_resolution**3,
        "Fourier_spatial_sites":operator_grid**3,
        "is_native_Fourier_grid_at_source_resolution":operator_grid==source_resolution,
        "source_pair_same_8_cube_parent_means":True,
        "independent_discrete_cut_max_difference":difference,
        "internal_encoder_preprocess_max_difference":preprocess_delta,
        "full_input_density_gradient_norm":grad_norm,
        "backward_finite":True,
        "protected_two_cell_shell":bool((out["density"][shell]==1.).all()),
        "forward_backward_cpu_seconds":elapsed,
        "peak_process_ru_maxrss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "PINO_core":"P-CRAFT U-FNO factorized-Fourier, not GINO replacement",
        "training_accuracy_certified":False,
        "512_cube_Fourier_training":False,
        "Cherchi_or_Newton_admitted":False,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=int,default=64)
    p.add_argument("--operator",type=int,default=32)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=run(source_resolution=a.source,operator_grid=a.operator)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
