"""W6 M11: independent analytic P0 moment-anchor correction and decision budgets.

Uses the source-pinned M10 W5/W6 models; trains the SAME held-out family
protocol, then queries separate analytic anchors only on TEST geometries.
No W2 label is admitted and no native result is claimed. A K-anchor correction
is a decision-only 1D bias diagnostic, not a certified material r or J.

  python -m research.NeuralMoments.models.pcraft_ufno.m11_experiment \
    --seeds 67,71,73 --steps 100 --output /tmp/w6m11.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import time
import numpy as np
import torch

from .analytic_cut import GeometrySpec, TEACHER_KIND, vertical_cut_truth
from .m4_experiment import dataset_digest, split_by_geometry
from .m10_experiment import (MODEL_NAMES,centered_dataset,make_model,fit_model,
                              centered_voxel)
from .m10_decision import native_plane_c_and_tangent,gn_step,objective
from .m11_anchor_cache import AnalyticAnchorLedger
from .m4_lite_model import num_real_parameters

MODEL_POLICIES=("baseline", "one_anchor", "two_anchors", "current_truth_counterfactual")


def _summarize(rows):
    keys=("accepted","gradient_sign_wrong","step_abs_error","signed_regret",
          "true_decrease","corrected_mae","cone_pass","correction_used",
          "anchor_fallback","trust_clipped")
    return {"cases":len(rows),"acceptance":statistics.mean(x["accepted"] for x in rows),
            "gradient_sign_error":statistics.mean(x["gradient_sign_wrong"] for x in rows),
            "mean_abs_step_error":statistics.mean(x["step_abs_error"] for x in rows),
            "mean_signed_regret":statistics.mean(x["signed_regret"] for x in rows),
            "mean_true_objective_decrease":statistics.mean(x["true_decrease"] for x in rows),
            "decision_r_mae":statistics.mean(x["corrected_mae"] for x in rows),
            "candidate_cone_pass":statistics.mean(x["cone_pass"] for x in rows),
            "correction_applied":statistics.mean(x["correction_used"] for x in rows),
            "anchor_fallback":statistics.mean(x["anchor_fallback"] for x in rows),
            "trust_clipped":statistics.mean(x["trust_clipped"] for x in rows),
            "total_selection_oracle_calls":sum(x["selection_oracle_calls_charged"] for x in rows),
            "selection_oracle_calls_per_candidate":statistics.mean(x["selection_oracle_calls_charged"] for x in rows),
            "oracle_for_goal_and_validation_only":"NOT_CHARGED_AS_SELECTION; distinct separate evaluator in analytic P0 experiment"}


def eval_model(model, heldout, *, seed:int, targets_per_geometry:int=8,
               one_anchor_h:float=0., two_anchor_h=(-.3,.3), goal_offset:float=.12):
    """Score supported GN steps on disjoint targets; account per-geometry anchors."""
    if targets_per_geometry<1 or not 0<abs(goal_offset)<=.2:
        raise ValueError("invalid target count or goal")
    D,C,R,J,meta=heldout
    if not all(m["family"]=="ellipsoid" for m in meta):
        raise ValueError("heldout must consist only of excluded ellipsoid family")
    groups={}
    for idx,m in enumerate(meta):groups.setdefault(m["geometry_id"],[]).append(idx)
    all_records={p:[] for p in MODEL_POLICIES}
    id_bound={}
    all_receipts=[]
    for gid, indices in groups.items():
        initial=meta[indices[0]]
        shape=initial["shape"]
        spec=GeometrySpec(initial["family"],tuple(shape["center"]),
                          tuple(shape["axes"]),float(shape["density"]))
        if spec.geometry_id!=gid:
            raise ValueError("geometry SHA does not bind analytic spec")
        vox=centered_voxel(spec,8).unsqueeze(0)
        if not torch.equal(vox[0],D[indices[0]]) or any(not torch.equal(D[i],vox[0]) for i in indices):
            raise ValueError("frozen evaluation geometry differs from model input")
        probes={p:AnalyticAnchorLedger(model,vox,spec) for p in MODEL_POLICIES[:3]}
        probes["one_anchor"].obtain_r(one_anchor_h,source=TEACHER_KIND)
        for h in two_anchor_h:probes["two_anchors"].obtain_r(h,source=TEACHER_KIND)
        if any(x.geometry_encoder_calls!=1 for x in probes.values()):
            raise AssertionError("expected one encoder invocation per isolated cache")
        rng=np.random.default_rng(int(seed)+500000+len(groups)*1009+int(gid[:7],16))
        target_h=rng.uniform(-.55,.55,targets_per_geometry)
        for h_np in target_h:
            h=float(h_np)
            native,r_true,J_true=vertical_cut_truth(spec,h)
            goal=vertical_cut_truth(spec,h+goal_offset)[1]
            _, tangent=native_plane_c_and_tangent(spec,h)
            exact_step=gn_step(r_true,J_true,tangent,goal)
            oracle_obj=objective(vertical_cut_truth(spec,h+exact_step)[1],goal)
            before=objective(r_true,goal)
            truth_gradient=float((r_true-goal) @ (J_true@tangent))
            # Trust cost for counterfactual is a real separate current-r call.
            for policy in MODEL_POLICIES:
                if policy=="current_truth_counterfactual":
                    raw=probes["baseline"].decision_input(h,"baseline")
                    used_r=r_true
                    used_J=raw.Jc_surrogate
                    cone_pass=True; correction_used=True; fallback=False
                    charged=1.
                else:
                    entry=probes[policy].decision_input(h,policy)
                    used_r=entry.r_for_step
                    used_J=entry.Jc_surrogate
                    cone_pass=entry.candidate_cone_check_pass
                    correction_used=entry.correction_used
                    fallback=entry.fallback_reason is not None
                    charged=float({"baseline":0,"one_anchor":1,"two_anchors":2}[policy])/targets_per_geometry
                step=gn_step(used_r,used_J,tangent,goal)
                post=vertical_cut_truth(spec,h+step)[1]
                after=objective(post,goal)
                gradient=float((used_r-goal)@(used_J@tangent))
                result={"seed":seed,"geometry_sha256":gid,"h_local":h,
                        "policy":policy,"accepted":int(after<before-1e-12),
                        "gradient_sign_wrong":int(gradient*truth_gradient<0),
                        "step_abs_error":abs(step-exact_step),
                        "signed_regret":after-oracle_obj,"true_decrease":before-after,
                        "corrected_mae":float(np.mean(np.abs(used_r-r_true))),
                        "cone_pass":int(cone_pass),"correction_used":int(correction_used),
                        "anchor_fallback":int(fallback),"trust_clipped":int(abs(step)>=.12-1e-10),
                        "selection_oracle_calls_charged":charged,
                        "native_W2_calls":0,"decision_r_is_material_proof":False}
                all_records[policy].append(result)
        per_geo={p:probes[p].receipt() for p in probes}
        id_bound[gid]={"same_geometry_sha":gid,"receipts":per_geo,
                       "target_count":targets_per_geometry}
        all_receipts.extend(per_geo.values())
    for x in id_bound.values():
        if (x["receipts"]["baseline"]["analytic_oracle_calls"]!=0
           or x["receipts"]["one_anchor"]["analytic_oracle_calls"]!=1
           or x["receipts"]["two_anchors"]["analytic_oracle_calls"]!=2):
            raise AssertionError("anchor query budget mismatch")
    stats={p:_summarize(rows) for p,rows in all_records.items()}
    return {"policy_stats":stats,"per_case":all_records,"per_geometry_receipts":id_bound,
            "distinct_heldout_geometry_ids":len(groups),"targets_per_geometry":targets_per_geometry,
            "queried_analytic_support_count_total":{"baseline":0,"one_anchor":len(groups),
                  "two_anchors":2*len(groups),"current_truth_counterfactual":len(groups)*targets_per_geometry},
            "all_oracle_labels_are_analytic_not_W2":True}


def run(*,seeds=(67,71,73),steps:int=100,per_family:int=20,
        targets_per_geometry:int=8,models=("w6_m7_base","w6_m7_directional","w5_voxel_deeponet"),
        goal_offset:float=.12):
    if (not seeds or len(set(seeds))!=len(seeds) or per_family<6 or steps<1
       or not models or len(set(models))!=len(models) or any(m not in MODEL_NAMES for m in models)
       or not isinstance(goal_offset,(float,int)) or not 0<abs(goal_offset)<=.2):
        raise ValueError("invalid model/training budget")
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    out={"schema":"W6_M11_ANCHORED_DECISION_AUDIT_V1",
         "status":"ANALYTIC_P0_ONLY_NOT_NATIVE_CHERCHI",
         "seeds":list(seeds),"steps_max":steps,"goal_offset":goal_offset,
         "training_geometry_families":["box","sphere"],"heldout_family":"ellipsoid",
         "per_family":per_family,"target_controls_per_geometry":targets_per_geometry,
         "oracle_query_budget":"zero / one / two analytic r anchors per unique heldout geometry; current truth costs one per target",
         "model_source":"original W6 M7 and W5 M8 voxel DeepONet, inherited unchanged M10 training",
         "native_W2_admitted_training_labels":0,"native_W2_calls":0,
         "physical_moment":"corrected r allowed for GN direction ONLY; raw bounded atomic output unchanged",
         "torch":torch.__version__,"python":platform.python_version(),"device":"cpu",
         "cases":[],"aggregate":{}}
    for seed in seeds:
        train_all=centered_dataset(("box","sphere"),per_family=per_family,seed=seed)
        heldout=centered_dataset(("ellipsoid",),per_family=per_family,seed=seed+1)
        if set(x["geometry_id"] for x in train_all[4])&set(x["geometry_id"] for x in heldout[4]):
            raise ValueError("train/heldout geometry leak")
        fit,val,split=split_by_geometry(train_all,seed,max(1,per_family//5))
        if split["train_geo"]!=2*(per_family-max(1,per_family//5)):
            raise AssertionError("wrong fit/validation split")
        case={"seed":seed,"fit_geometry_ids":split["train_geo"],
              "val_geometry_ids":split["val_geo"],
              "heldout_geometry_ids":len({m["geometry_id"] for m in heldout[4]}),
              "training_tensor_sha256":dataset_digest(train_all),
              "heldout_tensor_sha256":dataset_digest(heldout),"models":{}}
        for name in models:
            model=make_model(name,seed)
            parameters=num_real_parameters(model)
            training=fit_model(model,name,fit,val,seed=seed,steps=steps)
            evals=eval_model(model,heldout,seed=seed,
                             targets_per_geometry=targets_per_geometry,goal_offset=goal_offset)
            case["models"][name]={"parameters_real":parameters,"training":training,
                                 "evaluation":evals}
        out["cases"].append(case)
    for name in models:
        out["aggregate"][name]={}
        for policy in MODEL_POLICIES:
            rows=[c["models"][name]["evaluation"]["policy_stats"][policy] for c in out["cases"]]
            agg={k:{"mean":statistics.mean(x[k] for x in rows),
                    "sample_sd":statistics.stdev(x[k] for x in rows) if len(rows)>1 else None}
                 for k in ("acceptance","gradient_sign_error","mean_abs_step_error",
                      "mean_signed_regret","mean_true_objective_decrease","decision_r_mae",
                      "candidate_cone_pass","correction_applied","anchor_fallback",
                      "selection_oracle_calls_per_candidate")}
            out["aggregate"][name][policy]=agg
    return out


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--seeds',default='67,71,73')
    p.add_argument('--steps',type=int,default=100)
    p.add_argument('--per-family',type=int,default=20)
    p.add_argument('--target-controls',type=int,default=8)
    p.add_argument('--goal-offset',type=float,default=.12)
    p.add_argument('--models',default=','.join(MODEL_NAMES))
    p.add_argument('--output',type=Path,required=True)
    x=p.parse_args()
    result=run(seeds=tuple(int(s) for s in x.seeds.split(',')),steps=x.steps,
               per_family=x.per_family,targets_per_geometry=x.target_controls,
               models=tuple(x.models.split(',')),goal_offset=x.goal_offset)
    x.output.parent.mkdir(parents=True,exist_ok=True)
    x.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({"schema":result["schema"],"seeds":result["seeds"],
           "aggregate":result["aggregate"]},indent=2))


if __name__=='__main__':main()
