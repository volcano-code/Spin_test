"""M10b: same-source, three-seed analytic P0 training ablation.

Arms: P-CRAFT SpinPINO; SpinPINO + fine ten-moment summary only;
SpinPINO + fine ten-moment summary + sparse local multiscale features.
The two augmentations have IDENTICAL parameter counts/topology.
PINO always owns the main factorized U-FNO trunk and physics-aware head.

All labels are analytic continuum vertical cuts; no W2/Cherchi provenance.
Validation geometry identities (not test labels) select checkpoints.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import resource
import statistics
import time
from pathlib import Path

import numpy as np
import torch

from ..analytic_cut import GeometrySpec, TEACHER_KIND, vertical_cut_truth
from .m10_sparse_detail import SparseDetailSpinPINO
from .sparse_bridge import sparse_to_pino_grid
from .spin_pino import SpinPINO, SpinPINOLoss

ARMS = ("pino", "moments_only", "sparse_multiscale")


def _material_from_spec(spec: GeometrySpec, n: int):
    """Sample fixed density on cell centres; do not treat samples as teacher."""
    ax = (torch.arange(n, dtype=torch.float32) + 0.5) * (2.0 / n) - 1.0
    xyz = torch.stack(torch.meshgrid(ax, ax, ax, indexing="ij"), dim=-1)
    center = torch.tensor(spec.center, dtype=torch.float32)
    axes = torch.tensor(spec.axes, dtype=torch.float32)
    u = (xyz - center) / axes
    inside = u.abs().amax(dim=-1) <= 1.0 if spec.family == "box" else (u*u).sum(dim=-1) <= 1.0
    coords = inside.nonzero(as_tuple=False).to(torch.long)
    if coords.numel() == 0:
        raise ValueError("empty analytic solid at this sample resolution")
    indices = torch.cat((torch.zeros((len(coords), 1), dtype=torch.long), coords), dim=-1)
    values = torch.zeros((len(coords), 4), dtype=torch.float32)
    values[:, 0] = float(spec.density)
    values[:, 1] = 1.
    return indices, values


def _geometry_spec(rng: np.random.Generator, family: str):
    center = tuple(float(x) for x in rng.uniform(-.08, .08, 3))
    if family == "sphere":
        r = float(rng.uniform(.48, .68))
        axes = (r, r, r)
    else:
        raw = rng.uniform(.48, .68, 3)
        if family == "ellipsoid":
            raw *= np.array((1.0, .82, 1.12))
        axes = tuple(float(x) for x in raw)
    return GeometrySpec(family, center, axes)


def _case(spec: GeometrySpec, rng, source_resolution: int,
          coarse_grid: int, queries_per_geometry: int):
    idx, values = _material_from_spec(spec, source_resolution)
    coarse, ledger = sparse_to_pino_grid(
        idx, values, batch_size=1,
        source_resolution=source_resolution, pino_grid_size=coarse_grid,
    )
    ctrls, moments, jac = [], [], []
    for _ in range(queries_per_geometry):
        h = float(rng.uniform(-.6, .6))
        c, r, J = vertical_cut_truth(spec, h)
        ctrls.append(torch.tensor(c, dtype=torch.float32))
        moments.append(torch.tensor(r, dtype=torch.float32))
        jac.append(torch.tensor(J, dtype=torch.float32))
    return {
        "geometry_id": spec.geometry_id,
        "family": spec.family,
        "indices": idx,
        "values": values,
        "coarse": coarse,
        "coefficients": torch.stack(ctrls),
        "moments": torch.stack(moments),
        "jacobian": torch.stack(jac),
        "fine_moments": ledger["fine_ten_moments"],
    }


def _split_digest(groups):
    sha = hashlib.sha256()
    for key in ("fit", "validation", "test"):
        sha.update(key.encode("utf-8"))
        for case in groups[key]:
            sha.update(case["geometry_id"].encode("ascii"))
            for name in ("indices", "values", "coarse", "coefficients", "moments", "jacobian"):
                tensor = case[name].contiguous()
                sha.update(str((name,tuple(tensor.shape),str(tensor.dtype))).encode("utf-8"))
                sha.update(tensor.numpy().tobytes())
    return sha.hexdigest()


def make_splits(*, seed: int, source_resolution: int = 16,
                coarse_grid: int = 8, geometries_per_family: int = 8,
                test_ellipsoids: int = 5, queries_per_geometry: int = 2):
    if (source_resolution < 8 or coarse_grid < 8 or
            source_resolution % coarse_grid or geometries_per_family < 4 or
            test_ellipsoids < 2 or queries_per_geometry < 1):
        raise ValueError("invalid M10b dataset sizes")
    rng = np.random.default_rng(seed + 8879)
    groups = {"fit": [], "validation": [], "test": []}
    for family in ("box", "sphere", "ellipsoid"):
        number = test_ellipsoids if family == "ellipsoid" else geometries_per_family
        for k in range(number):
            spec = _geometry_spec(rng, family)
            split = ("test" if family == "ellipsoid"
                     else ("validation" if k < max(1,number//4) else "fit"))
            groups[split].append(_case(spec, rng, source_resolution,
                                       coarse_grid, queries_per_geometry))
    ids = {k:{row["geometry_id"] for row in v} for k,v in groups.items()}
    if (ids["fit"] & ids["validation"] or
            ids["fit"] & ids["test"] or ids["validation"] & ids["test"]):
        raise AssertionError("geometry identity leakage")
    if {row["family"] for row in groups["test"]} != {"ellipsoid"}:
        raise AssertionError("test family must be held out")
    return groups, {
        "source_resolution":source_resolution,
        "coarse_grid":coarse_grid,
        "queries_per_geometry":queries_per_geometry,
        "geometry_counts":{k:len(v) for k,v in groups.items()},
        "query_counts":{k:len(v)*queries_per_geometry for k,v in groups.items()},
        "split_ids":{k:sorted(ids[k]) for k in groups},
        "source_sha256":_split_digest(groups),
        "label_source":TEACHER_KIND,
        "W2_or_Cherchi_labels_used":False,
        "geometry_disjoint":True,
    }


def _make_model(arm: str, seed: int, coarse_grid: int, source_resolution: int):
    if arm not in ARMS:
        raise ValueError("unknown ablation")
    torch.manual_seed(seed + 12001)
    pino = SpinPINO(width=4, modes=2, n_layers=2, grid_size=coarse_grid,
                    hidden_dim=32, points_per_axis=4,
                    moment_parameterization="logistic_atom", temperature=.12)
    if arm == "pino":
        return pino
    levels = (coarse_grid, source_resolution) if source_resolution != coarse_grid else (coarse_grid,)
    model = SparseDetailSpinPINO(
        pino, levels=levels, width=16, coarse_grid_size=coarse_grid,
        feature_ablation=("moments_only" if arm == "moments_only" else "full"),
    )
    # Both auxiliary arms start from the same nonzero training gate.
    # M10's public default remains zero, preserving exact legacy parity.
    with torch.no_grad():
        model.detail_gate.fill_(.2)
    return model


def _pino(model):
    return model if isinstance(model, SpinPINO) else model.pino


def _encode(model, case, *, source_resolution: int):
    if isinstance(model, SpinPINO):
        return model.encode_geometry(case["coarse"])
    weights, _ = model.encode_sparse(case["indices"], case["values"],
                                     batch_size=1, source_resolution=source_resolution)
    return weights


def _eval(model, cases, *, source_resolution: int):
    model.eval()
    pred_r, pred_J, truth_r, truth_J = [], [], [], []
    timings={"encode_seconds":0.0,"queries_seconds":0.0}
    with torch.no_grad():
        for case in cases:
            start=time.perf_counter()
            w=_encode(model,case,source_resolution=source_resolution)
            timings["encode_seconds"]+=time.perf_counter()-start
            controls=case["coefficients"]
            weights=w.expand(len(controls),-1)
            start=time.perf_counter()
            r=_pino(model).moment_from_weights(weights,controls)
            J=_pino(model).jacobian_from_weights(weights,controls)
            timings["queries_seconds"]+=time.perf_counter()-start
            pred_r.append(r)
            pred_J.append(J)
            truth_r.append(case["moments"])
            truth_J.append(case["jacobian"])
    r=torch.cat(pred_r);J=torch.cat(pred_J)
    rt=torch.cat(truth_r);Jt=torch.cat(truth_J)
    err_r=(r-rt).abs();err_J=(J-Jt).abs()
    return {
        "r_mae":float(err_r.mean()),
        "J_mae":float(err_J.mean()),
        "r_relative_l2":float(torch.linalg.vector_norm(r-rt)/torch.linalg.vector_norm(rt).clamp_min(1e-12)),
        "J_relative_l2":float(torch.linalg.vector_norm(J-Jt)/torch.linalg.vector_norm(Jt).clamp_min(1e-12)),
        "r_worst_component_mae":float(err_r.mean(0).max()),
        "J_worst_component_mae":float(err_J.mean((0,1)).max()),
        "max_abs_r":float(err_r.max()),
        "max_abs_J":float(err_J.max()),
        "encoding_seconds":timings["encode_seconds"],
        "query_seconds":timings["queries_seconds"],
        "n_geometry":len(cases),
        "n_queries":len(rt),
    }


def train_arm(*, arm: str, seed: int, groups, steps: int,
              source_resolution: int, coarse_grid: int, lr: float=0.0015):
    torch.manual_seed(seed+51)
    model=_make_model(arm,seed,coarse_grid,source_resolution)
    model.train()
    criterion=SpinPINOLoss(lambda_data=1.0,lambda_jacobian=.25,lambda_physics=.05)
    optimizer=torch.optim.Adam(model.parameters(),lr=lr)
    observations=[(i,q) for i,case in enumerate(groups["fit"])
                  for q in range(len(case["coefficients"]))]
    if steps<1 or not observations:
        raise ValueError("invalid training budget")
    indices=torch.randint(len(observations),(steps,),
                          generator=torch.Generator().manual_seed(seed+31337)).tolist()
    history=[]
    best_score=math.inf;best_step=0;best_state=None
    begin=time.perf_counter()
    for step,obs in enumerate(indices,1):
        model.train()
        i,q=observations[obs]
        sample=groups["fit"][i]
        w=_encode(model,sample,source_resolution=source_resolution)
        coeff=sample["coefficients"][q:q+1]
        result=criterion(
            _pino(model),w,coeff,
            target_moments=sample["moments"][q:q+1],
            target_jacobian=sample["jacobian"][q:q+1],
            derivative_admitted=True, # restricted synthetic analytic P0 only
        )
        loss=result["total"]
        if not bool(torch.isfinite(loss)):
            raise FloatingPointError("nonfinite M10b training loss")
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
        optimizer.step()
        if step==1 or step%10==0 or step==steps:
            val=_eval(model,groups["validation"],source_resolution=source_resolution)
            score=val["r_mae"]+.25*val["J_mae"]
            history.append({"step":step,"validation_score":score,
                            "train_total":float(loss.detach())})
            if score<best_score:
                best_score=score;best_step=step;best_state=copy.deepcopy(model.state_dict())
    training_seconds=time.perf_counter()-begin
    model.load_state_dict(best_state)
    fit=_eval(model,groups["fit"],source_resolution=source_resolution)
    validation=_eval(model,groups["validation"],source_resolution=source_resolution)
    test=_eval(model,groups["test"],source_resolution=source_resolution)
    n_params=sum(int(p.numel()) for p in model.parameters() if p.requires_grad)
    return {"arm":arm,"seed":seed,"parameters":n_params,
            "selected_step":best_step,"validation_selection_score":best_score,
            "optimizer_updates":steps,"source_queries_used_for_fit":len(observations),
            "train_seconds":training_seconds,"fit":fit,"validation":validation,
            "test":test,"history":history,
            "detail_gate":float(torch.tanh(model.detail_gate).detach()) if arm!="pino" else None,
            "pino_trunk_preserved":True,
            "native_derivative_admitted":False}


def run(*, seeds=(131,137,139), steps=60, source_resolution=16,
        coarse_grid=8, geometries_per_family=8, test_ellipsoids=5):
    torch.set_num_threads(1)
    if not seeds or steps<1:
        raise ValueError("nonempty seeds and positive steps required")
    experiments=[]
    for seed in seeds:
        data,receipt=make_splits(
            seed=seed,source_resolution=source_resolution,coarse_grid=coarse_grid,
            geometries_per_family=geometries_per_family,
            test_ellipsoids=test_ellipsoids,
        )
        rows=[train_arm(arm=arm,seed=seed,groups=data,steps=steps,
                        source_resolution=source_resolution,coarse_grid=coarse_grid)
              for arm in ARMS]
        if rows[1]["parameters"]!=rows[2]["parameters"]:
            raise AssertionError("auxiliary arm parameter count mismatch")
        experiments.append({"seed":seed,"receipt":receipt,"arms":rows})
    aggregated=[]
    for arm in ARMS:
        rows=[next(x for x in e["arms"] if x["arm"]==arm) for e in experiments]
        aggregated.append({
            "arm":arm,
            "parameters":rows[0]["parameters"],
            "test_r_relative_l2_mean":statistics.mean(r["test"]["r_relative_l2"] for r in rows),
            "test_J_relative_l2_mean":statistics.mean(r["test"]["J_relative_l2"] for r in rows),
            "test_r_mae_mean":statistics.mean(r["test"]["r_mae"] for r in rows),
            "test_J_mae_mean":statistics.mean(r["test"]["J_mae"] for r in rows),
            "train_seconds_mean":statistics.mean(r["train_seconds"] for r in rows),
            "test_encode_seconds_mean":statistics.mean(r["test"]["encoding_seconds"] for r in rows),
            "test_query_seconds_mean":statistics.mean(r["test"]["query_seconds"] for r in rows),
            "selected_step_mean":statistics.mean(r["selected_step"] for r in rows),
            "gates":[r["detail_gate"] for r in rows],
        })
    for metric in ("test_r_relative_l2_mean","test_J_relative_l2_mean"):
        if any(not math.isfinite(row[metric]) for row in aggregated):
            raise FloatingPointError("nonfinite held-out metric")
    return {
        "schema":"W6_M10B_THREE_ARM_ANALYTIC_P0_ABLATION_V1",
        "labels":TEACHER_KIND,
        "source_resolution":source_resolution,"coarse_grid":coarse_grid,
        "seeds":list(seeds),"steps_per_arm_per_seed":steps,
        "same_split_and_oracle_budget":True,
        "same_initial_pino_weights_across_arms":True,
        "same_training_observation_indices_across_arms":True,
        "same_auxiliary_parameter_count":True,
        "active_parameter_count_not_equivalent":True,
        "model_selection":"validation r_mae + 0.25 * J_mae; held-out entire ellipsoid family",
        "aggregate":aggregated,"per_seed":experiments,
        "max_process_ru_maxrss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "claims":{"trained_on_Cherchi":False,
                  "512_full_grid_supported":False,
                  "full_CAD_quadric_derivative_certified":False,
                  "native_newton_speedup":False,
                  "trained_512_sparse_model":False}
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--seeds",default="131,137,139")
    parser.add_argument("--steps",type=int,default=60)
    parser.add_argument("--source-resolution",type=int,default=16)
    parser.add_argument("--coarse-grid",type=int,default=8)
    parser.add_argument("--geometries-per-family",type=int,default=8)
    parser.add_argument("--test-ellipsoids",type=int,default=5)
    parser.add_argument("--output",type=Path,required=True)
    a=parser.parse_args()
    result=run(seeds=tuple(int(x) for x in a.seeds.split(",")),
               steps=a.steps,source_resolution=a.source_resolution,
               coarse_grid=a.coarse_grid,geometries_per_family=a.geometries_per_family,
               test_ellipsoids=a.test_ellipsoids)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps(result["aggregate"],indent=2))


if __name__=="__main__":
    main()
