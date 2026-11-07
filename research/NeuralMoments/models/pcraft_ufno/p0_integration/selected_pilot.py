"""W6 P11 one-seed controlled source-pinned PINO/GINO/QuadrANN/UQNO CPU pilot.

Real P-CRAFT PINO weights are fitted to analytic continuum P0 labels.
External GINO/QuadrANN/UQNO auxiliary weights are NOT trained in this pilot,
so their activated-gate rows are diagnostic ablations, not validated gains.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from pathlib import Path

import torch

from ..spin_pino.dataset import generate_splits
from ..spin_pino.spin_pino import SpinPINO
from ..spin_pino.train import run_seed
from .selected_pino import GroupwiseConformalScreen, SelectedPINOCandidates


def _evaluate(data, bridge):
    D, c, truth_r, truth_J, metadata = data
    rs, js, scales = [], [], []
    begin = time.perf_counter()
    with torch.no_grad():
        for i in range(len(D)):
            out = bridge(D[i:i+1],c[i:i+1])
            rs.append(out.result.moments)
            js.append(out.diagnostic_model_jacobian)
            scales.append(out.result.uncertainty)
    seconds = time.perf_counter() - begin
    pred_r = torch.cat(rs, 0)
    pred_J = torch.cat(js, 0)
    scale = torch.cat(scales, 0)
    return {
        "moments":pred_r,
        "J_diagnostic":pred_J,
        "scale":scale,
        "seconds":seconds,
        "r_relative_l2":float(torch.linalg.vector_norm(pred_r-truth_r)/
            torch.linalg.vector_norm(truth_r).clamp_min(1e-12)),
        "J_relative_l2":float(torch.linalg.vector_norm(pred_J-truth_J)/
            torch.linalg.vector_norm(truth_J).clamp_min(1e-12)),
        "r_mae":float((pred_r-truth_r).abs().mean()),
        "J_mae":float((pred_J-truth_J).abs().mean()),
        "model_J_is_native_certified":False,
    }


def _compact(metrics):
    return {k:v for k,v in metrics.items() if not isinstance(v,torch.Tensor)}


def run(*, seed=131, steps=20, train_geometries_per_family=8, test_ellipsoids=4):
    torch.set_num_threads(1)
    if steps < 1 or train_geometries_per_family < 4 or test_ellipsoids < 2:
        raise ValueError("insufficient matched pilot size")
    # All conditions share one trained PINO model, split, and analytic labels.
    checkpoint = run_seed(
        seed=seed, steps=steps,
        train_geometries_per_family=train_geometries_per_family,
        test_ellipsoid_geometries=test_ellipsoids,
        queries_per_geometry=2,
        grid_size=8, points_per_axis=4, smoothing=.02,
        moment_parameterization="logistic_atom", temperature=.12,
        device="cpu",
    )
    data = generate_splits(
        seed=seed, train_geometries_per_family=train_geometries_per_family,
        test_ellipsoid_geometries=test_ellipsoids,
        queries_per_geometry=2, grid_size=8,
    )
    base = SpinPINO(
        width=4, modes=2, n_layers=2, grid_size=8,
        points_per_axis=4, hidden_dim=48, smoothing=.02,
        moment_parameterization="logistic_atom", temperature=.12,
    ).eval()
    base.load_state_dict(checkpoint["checkpoint_state"])
    torch.manual_seed(seed+900001)
    bridge = SelectedPINOCandidates(
        base, gino=True, quadrann=True, uqno=True,
        gino_hidden=8, max_gino_points=48,
    ).eval()
    test = data["test"]
    val = data["validation"]
    conditions=[]
    raw_results={}
    for name,gg,qg in (
        ("pino_zero_gates",0.0,0.0),
        ("gino_random_gate",0.2,0.0),
        ("quadrann_random_gate",0.0,0.2),
        ("both_random_gates",0.2,0.2),
    ):
        with torch.no_grad():
            bridge.gino_gate.fill_(gg)
            bridge.quadrann_gate.fill_(qg)
        v = _evaluate(val, bridge)
        t = _evaluate(test, bridge)
        conditions.append({
            "condition":name,
            "gino_gate":gg,"quadrann_gate":qg,
            "validation":_compact(v),
            "test":_compact(t),
            "external_adapters_trained":False,
        })
        raw_results[name] = (v,t)
    zero = raw_results["pino_zero_gates"][1]
    with torch.no_grad():
        direct_r,direct_J = base(test[0],test[1],with_jacobian=True)
    max_diff = max(
        float((direct_r-zero["moments"]).abs().max()),
        float((direct_J-zero["J_diagnostic"]).abs().max()),
    )
    if max_diff>2e-6:
        raise AssertionError("zero-gate selected adapter did not reproduce PINO")
    # Fit UQNO conformal radius only on disjoint calibration geometries.
    val_zero = raw_results["pino_zero_gates"][0]
    train_ids = {x["geometry_id"] for x in data["fit"][4]}
    val_ids = [x["geometry_id"] for x in val[4]]
    test_ids = [x["geometry_id"] for x in test[4]]
    if set(val_ids) & train_ids or set(test_ids) & (train_ids | set(val_ids)):
        raise AssertionError("split geometry identity overlap")
    group_gate = GroupwiseConformalScreen(alpha=.25).fit(
        val_zero["moments"], val_zero["scale"], val[2], val_ids,
        training_geometry_ids=tuple(train_ids),
    )
    qhat=group_gate.qhat
    group_coverage={}
    screened=0
    requiring_exact=0
    for gid in sorted(set(test_ids)):
        mask=torch.tensor([id==gid for id in test_ids], dtype=torch.bool)
        lower=zero["moments"][mask]-zero["scale"][mask]*qhat
        upper=zero["moments"][mask]+zero["scale"][mask]*qhat
        group_coverage[gid]=bool((test[2][mask]>=lower).all()
                                 and (test[2][mask]<=upper).all())
    # A single trial decision: NEVER release predicted J to native Newton.
    with torch.no_grad():
        proposal=bridge(test[0][:1],test[1][:1])
    one_id=test_ids[0]
    trial=group_gate.screen(proposal,one_id,max_simultaneous_radius=.05)
    newton=group_gate.screen(proposal,one_id,max_simultaneous_radius=.05,
                            for_native_newton=True)
    if not newton.exact_required or newton.native_newton_admitted:
        raise AssertionError("unadmitted Newton derivative escaped gate")
    return {
        "schema":"W6_P11_SELECTED_PINO_UPSTREAM_CPU_PILOT_V1",
        "source_label":"ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI",
        "seed":seed,"pino_training_steps":steps,
        "data_sha256":data["metadata"]["fit_sha256"],
        "val_sha256":data["metadata"]["validation_sha256"],
        "test_sha256":data["metadata"]["test_sha256"],
        "fit_geometry_count":len(train_ids),
        "calibration_geometry_count":len(set(val_ids)),
        "heldout_geometry_count":len(set(test_ids)),
        "zero_gate_r_J_max_absolute_difference":max_diff,
        "precommitted_random_gate_values":[0.2],
        "conditions":conditions,
        "groupwise_conformal":{
            "alpha":group_gate.alpha,
            "qhat":qhat,
            "geometry_group_coverage_fraction":sum(group_coverage.values())/len(group_coverage),
            "n_groups":len(group_coverage),
            "trial_exact_required":trial.exact_required,
            "trial_reason":trial.reason,
            "native_newton_exact_required":newton.exact_required,
            "native_newton_admitted":newton.native_newton_admitted,
            "uncertainty_model_trained":False,
            "conditional_exchangeability_assumed_not_established":True,
        },
        "source_pins":"p0_integration/UPSTREAM_PINS.json",
        "claims":{
            "GINO_QuadrANN_UQNO_original_code_instantiated":True,
            "PCRAFT_PINO_primary":True,
            "trained_upstream_auxiliary_adapters":False,
            "Cherchi_supervised":False,
            "native_J_admitted":False,
            "512_cube_GPU_verified":False,
            "full_Spin_Neutron_speedup":False,
        },
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--seed",type=int,default=131)
    p.add_argument("--steps",type=int,default=20)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=run(seed=a.seed,steps=a.steps)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({
      "zero_gate_error":result["zero_gate_r_J_max_absolute_difference"],
      "conditions":[{"name":x["condition"],"r":x["test"]["r_relative_l2"],
                    "J":x["test"]["J_relative_l2"],
                    "time":x["test"]["seconds"]} for x in result["conditions"]],
      "calibration":result["groupwise_conformal"]
    },indent=2))
if __name__=="__main__":
    main()
