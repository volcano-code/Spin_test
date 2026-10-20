"""W5 M13 read-only, exact-blob W6 M7 realizable operator probe.

No W6 files are modified or copied into W5's Git commit. The W6 M7
operator has an exact analytic surrogate J and a bounded nonnegative atom
measure, NOT a certified W0 native J. Source code identity is checked before
importing. Trained weights are not available here unless fitted explicitly.
"""
from __future__ import annotations

import importlib
from pathlib import Path
import time

import torch

from .m7_cross_framework import UntrustedW6Source,git_blob_sha
from .m9_readonly_w6 import load_m9_w6,W6_M6_FILES

W6_M7_COMMIT='9d1758ea1ef527577b835f2b6bcfc5f0439d933d'
W6_M7_FILES={
  'm6_safe_inference.py':'6e43940adfd81c748dbd1c6a127cbe1c3f53141b',
  'm7_realizable.py':'a0e45b278de050329bed60cf5cb2b27e2fdd3c64',
}


def load_w6_m7(w6_root):
    base=Path(w6_root).resolve()/'research/NeuralMoments/models/pcraft_ufno'
    for name,blob in W6_M7_FILES.items():
        path=base/name
        if not path.is_file() or path.is_symlink() or git_blob_sha(path.read_bytes())!=blob:
            raise UntrustedW6Source('UNVERIFIED_W6_M7_BLOB:'+name)
    m4,m5,m6,guard=load_m9_w6(w6_root)
    ns='_w5_readonly_pcraft_ufno'
    m7=importlib.import_module(ns+'.m7_realizable')
    return m7


def untrained_m7_api_probe(w6_root, D:torch.Tensor,c:torch.Tensor, *, seed=67):
    if D.ndim!=5 or D.shape[1]!=4 or c.shape!=(D.shape[0],10):
        raise ValueError('single matched 4-channel input/native c expected')
    torch.manual_seed(seed)
    m7=load_w6_m7(w6_root)
    model=m7.RealizableUFNOMoment(temperature=.12).eval()
    with torch.no_grad():
        t=time.perf_counter_ns();z=model.encode_geometry(D);encode_ms=(time.perf_counter_ns()-t)*1e-6
        t=time.perf_counter_ns();r=model.moment(z,c);J=model.jacobian(z,c);query_ms=(time.perf_counter_ns()-t)*1e-6
        tangent,V=model.tangent_jacobian(z,c)
    if not bool(torch.isfinite(r).all() and torch.isfinite(J).all()):
        raise ValueError('untrained W6 M7 returned nonfinite outputs')
    if r.shape!=(len(D),10) or J.shape!=(len(D),10,10) or tangent.shape!=(len(D),10,9):
        raise ValueError('invalid W6 M7 output contract')
    params=model.real_parameter_count() if hasattr(model,'real_parameter_count') else sum(p.numel()*(2 if p.is_complex() else 1) for p in model.parameters() if p.requires_grad)
    return {'model':'W6_M7_REALIZABLE_UFNO_UNTRAINED_SOURCE_PINNED',
            'params':int(params),'r':r.detach().cpu().numpy()[0].tolist(),
            'Jc':J.detach().cpu().numpy()[0].tolist(),
            'encoding_ms':encode_ms,'cached_rJ_ms':query_ms,
            'source_blob_pins':dict(W6_M7_FILES),
            'W6_git_source_commit':W6_M7_COMMIT,
            'not_trained':True,'no_native_teacher_J':True}
