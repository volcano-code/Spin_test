"""Reproducible CPU-only budget/rejection audit; NO native Cherchi invoked."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import platform
from pathlib import Path
import statistics

import numpy as np
import torch

from research.NeuralMoments.models.deeponet.m6_analytic_rollout import (
    ReplayPolicy, check_w2_manifest, guarded_analytic_step)
from research.NeuralMoments.models.deeponet.m6_model_adapter import cached_prediction
from research.NeuralMoments.models.deeponet.native_p0 import (
    cap_jacobian_native, cap_moments, native_vertical_c)
from research.NeuralMoments.models.deeponet.model import DeepONetMoment
from research.NeuralMoments.models.geometry_mlp.model import GeometryMLPMoment

W5_PARENT_SHA = "c4dcde3d21edc51f5b0f9f96cffe65919859de9c"
W0_READ_ONLY_SHA = "8466202ee23eb0ffc1eb655988b97a1ce098783c"
W2_READ_ONLY_SHA = "df3641280c0f7dde16e53a3f64a1529ccef2b5b4"
FROZEN_SOURCE = "0bcc187b3005478baa586a6d6f450e73811ca342"


def run_audit(*, seeds=(7, 19, 31), heights=(-0.3, 0.25, 0.5),
              w2_manifest=None):
    torch.set_num_threads(1)
    radius, density = 1.2, 1.3
    scales = density * np.array([radius**3] + [radius**4]*3 + [radius**5]*6)
    cases = []
    for seed in seeds:
        torch.manual_seed(seed)
        rng = np.random.default_rng(seed)
        models = {
            "random_untrained_deeponet": DeepONetMoment(geometry_dim=9).double().eval(),
            "random_untrained_geometry_mlp": GeometryMLPMoment(geometry_dim=9).double().eval(),
        }
        for h in heights:
            target_h = -0.05 if h < 0 else 0.05
            truth = cap_moments(radius, h, density=density)
            jac = cap_jacobian_native(radius, h, density=density)
            target = cap_moments(radius, target_h, density=density)
            perturb_r = truth + rng.normal(0., 0.02, 10) * scales
            perturb_J = jac * (1 + rng.normal(0., 0.12, (10, 10)))
            predictions = {
                "exact_analytic_prediction": (truth, jac, None),
                "controlled_noise": (perturb_r, perturb_J, None),
                "reversed_derivative": (truth, -jac, None),
                "zero_derivative": (truth, np.zeros_like(jac), None),
            }
            # Model-path smoke uses untrained random weights; these are NOT
            # the trained M4 weights (none were transferred in this checkout).
            geometry_features = np.array([radius, density, h, 0., 0., 0., 0., 0., 0.])
            for name, model in models.items():
                pred = cached_prediction(model, geometry_features, native_vertical_c(h))
                predictions[name] = (pred["predicted_r"], pred["predicted_Jc"], {
                    "encode_seconds": pred["encode_seconds"],
                    "warm_moment_seconds": pred["warm_moment_seconds"],
                    "warm_jacobian_seconds": pred["warm_jacobian_seconds"],
                    "parameter_count": pred["parameter_count"]})
            for kind, (r, J, adapter) in predictions.items():
                outcome = guarded_analytic_step(radius=radius, density=density,
                    current_h=h, target_r=target, predicted_r=r,
                    predicted_Jc=J, policy=ReplayPolicy())
                cases.append({"seed":seed, "height":h,"target_height":target_h,
                              "case":kind, "result":outcome,
                              "r_normalized_mae":float(np.mean(np.abs(r-truth)/scales)),
                              "Jc_normalized_mae":float(np.mean(np.abs(J-jac)/scales[:,None])),
                              "inference":adapter})
    grouped=defaultdict(list)
    for row in cases:
        grouped[row["case"]].append(row)
    summary={}
    for kind, rows in sorted(grouped.items()):
        summary[kind]={
            "cases":len(rows),
            "accepted":sum(int(r["result"]["accepted"]) for r in rows),
            "accept_fraction":sum(int(r["result"]["accepted"]) for r in rows)/len(rows),
            "mean_analytic_oracle_queries":statistics.mean(r["result"]["truth_calls"] for r in rows),
            "median_wall_milliseconds":statistics.median(r["result"]["wall_seconds"]*1000 for r in rows),
            "mean_normalized_r_mae":statistics.mean(r["r_normalized_mae"] for r in rows),
            "mean_normalized_Jc_mae":statistics.mean(r["Jc_normalized_mae"] for r in rows),
            "mean_actual_objective_drop":statistics.mean(r["result"]["actual_drop"] for r in rows),
        }
    if w2_manifest is None:
        readiness={"teacher_training_admissible":False,
                   "reason":"W2 read-only manifest not supplied; no native labels used"}
    else:
        readiness=check_w2_manifest(w2_manifest)
    return {"schema":"W5_M6_ANALYTIC_P0_BUDGET_AUDIT_V1",
            "source": {"w5_parent":W5_PARENT_SHA,"w0_read_only":W0_READ_ONLY_SHA,
                       "w2_read_only":W2_READ_ONLY_SHA,"frozen_core":FROZEN_SOURCE},
            "environment":{"python":platform.python_version(),
                           "torch":torch.__version__,"numpy":np.__version__,
                           "device":"cpu","num_threads":torch.get_num_threads(),
                           "gpu_seconds":0,"native_cherchi_executions":0},
            "design":{"seeds":list(seeds),"heights":list(heights),
                      "truth":"closed-form smooth horizontal sphere-cap only",
                      "radius":radius,"density":density,
                      "maximum_truth_queries_per_iteration":4,
                      "model_weights":"RANDOM_UNTRAINED_ONLY",
                      "labels_generated_by_network":False,
                      "actual_cad_material_certification":False,
                      "candidate_commit_performed":False},
            "w2_gate":readiness,"summary":summary,"cases":cases}


def main():
    parser=argparse.ArgumentParser(description="W5 M6 analytic-only safe decision replay")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--w2-manifest",type=Path)
    args=parser.parse_args()
    manifest=(json.loads(args.w2_manifest.read_text(encoding="utf-8"))
              if args.w2_manifest else None)
    report=run_audit(w2_manifest=manifest)
    rendered=json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n"
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(rendered,encoding="utf-8")
        print(f"W5 M6 analytic audit: {len(report['cases'])} cases -> {args.out}")
    else:
        print(rendered,end="")


if __name__=="__main__":
    main()
