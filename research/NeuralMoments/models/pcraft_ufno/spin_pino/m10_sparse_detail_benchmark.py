"""M10 CPU contract benchmark: same pooled input, different fine source positions.

No training or accuracy gain claim. Shows whether fine indices actually
affect output under an opt-in nonzero adapter gate and measures overhead.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch

from .m10_sparse_detail import SparseDetailSpinPINO
from .sparse_bridge import sparse_to_pino_grid
from .spin_pino import SpinPINO


def _pair(n=32, shift=0):
    axis=torch.arange(8,dtype=torch.long)
    parents=torch.stack(torch.meshgrid(axis,axis,axis,indexing="ij"),-1).reshape(-1,3)
    coords=parents*(n//8)+shift
    idx=torch.cat((torch.zeros((len(coords),1),dtype=torch.long),coords),1)
    v=torch.tensor([[.8,1.,0.,0.]]).repeat(len(coords),1)
    return idx,v


def _sparse_512(records=4096):
    n=512
    flat=(torch.arange(records,dtype=torch.long)*10007+701)%n**3
    xyz=torch.stack((flat//(n*n),(flat//n)%n,flat%n),-1)
    return (torch.cat((torch.zeros((len(flat),1),dtype=torch.long),xyz),1),
            torch.tensor([[.8,1.,0.,0.]]).repeat(records,1))


def run():
    torch.set_num_threads(1)
    torch.manual_seed(307)
    base=SpinPINO(width=4,modes=2,n_layers=2,grid_size=8,
                  hidden_dim=32,points_per_axis=4,
                  moment_parameterization="logistic_atom").eval()
    model=SparseDetailSpinPINO(base,levels=(8,16),coarse_grid_size=8,width=32).eval()
    (a,va),(b,vb)=_pair(shift=0),_pair(shift=3)
    coarse_a,_=sparse_to_pino_grid(a,va,batch_size=1,source_resolution=32,pino_grid_size=8)
    coarse_b,_=sparse_to_pino_grid(b,vb,batch_size=1,source_resolution=32,pino_grid_size=8)
    c=torch.tensor([[.2,.1,-.2,.7,.1,0.,0.,0.,0.,0.]])
    with torch.no_grad():
        base_r,base_J=base(coarse_a,c,with_jacobian=True)
        baseline_equal=torch.equal(coarse_a,coarse_b)
        fresh_r,fresh_J=model(a,va,c,batch_size=1,source_resolution=32,with_jacobian=True)
        zero_err=float(torch.max(torch.cat(((fresh_r-base_r).abs().flatten(),
                                             (fresh_J-base_J).abs().flatten()))))
        model.detail_gate.fill_(1.5)
        start=time.perf_counter()
        ra,Ja=model(a,va,c,batch_size=1,source_resolution=32,with_jacobian=True)
        rb,Jb=model(b,vb,c,batch_size=1,source_resolution=32,with_jacobian=True)
        pair_seconds=time.perf_counter()-start
        fine_effect_r=float((ra-rb).abs().max())
        fine_effect_J=float((Ja-Jb).abs().max())
    large=SparseDetailSpinPINO(base,levels=(16,32,64),
                               coarse_grid_size=16,width=24).eval()
    si,sv=_sparse_512()
    with torch.no_grad():
        start=time.perf_counter()
        r512,J512,ledger=large(si,sv,c,batch_size=1,source_resolution=512,
                               with_jacobian=True,return_diagnostics=True)
        sparse512_seconds=time.perf_counter()-start
    if not baseline_equal or zero_err != 0.0 or fine_effect_r <= 0.0:
        raise AssertionError("M10 lost zero-gate parity or fine-detail sensitivity")
    if not bool(torch.isfinite(r512).all() and torch.isfinite(J512).all()):
        raise AssertionError("512 sparse detail output nonfinite")
    return {
        "schema":"W6_SPIN_PINO_M10_SPARSE_DETAIL_CPU_PROTOTYPE",
        "same_coarse_input_for_distinct_source_positions":baseline_equal,
        "zero_gate_r_J_max_abs_diff":zero_err,
        "active_detail_r_max_abs_diff":fine_effect_r,
        "active_detail_J_max_abs_diff":fine_effect_J,
        "32_cube_pair_seconds":pair_seconds,
        "source_512_records":ledger["sparse_records"],
        "source_512_detail_levels":list(ledger["detail_levels"]),
        "source_512_forward_seconds":sparse512_seconds,
        "source_512_mass_relative_error":ledger["relative_mass_error_max"],
        "source_512_ten_moment_coarse_drift":ledger["relative_ten_moment_drift_max"],
        "full_resolution_dense_512_fft":False,
        "fVDB_or_FIGConv_upstream_code_integrated":False,
        "trained_or_physics_certified":False,
        "pino_primary_trunk":True,
        "interpretation":"Representational sensitivity only; no held-out accuracy or native speed certification."
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=run()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
