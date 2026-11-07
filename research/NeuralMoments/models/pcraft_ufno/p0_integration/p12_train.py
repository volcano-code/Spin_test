"""W6 P12: label-budget-matched upstream-adapter fine-tuning and UQNO calibration.

Primary trunk remains the pinned P-CRAFT SpinPINO. A shared pretrained
baseline is reused for all arms; GINO/QuadrANN are trained separately and
only through geometry-conditional, nonnegative quadrature corrections.
UQNO scale is trained using FIT-only residuals, then calibrated on disjoint
VALIDATION geometry IDs; ELLIPSOID test IDs are never used for selection.

Analytic P0 interior vertical planes ONLY, no native Cherchi admission.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import resource
import statistics
import time
from pathlib import Path

import torch

from ..spin_pino.dataset import generate_splits
from ..spin_pino.spin_pino import SpinPINO
from ..spin_pino.train import run_seed
from .selected_pino import SelectedPINOCandidates, GroupwiseConformalScreen

ARMS = ("pino_head", "gino", "quadrann")
SOURCE = "ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI"


def _new_pino():
    return SpinPINO(
        width=4, modes=2, n_layers=2, grid_size=8,
        points_per_axis=4, hidden_dim=48, smoothing=.02,
        moment_parameterization="logistic_atom", temperature=.12,
    )


def _make_arm(arm, state, seed):
    if arm not in ARMS:
        raise ValueError("unknown adapter arm")
    pino = _new_pino()
    pino.load_state_dict(state)
    torch.manual_seed(seed + 80021)
    model = SelectedPINOCandidates(
        pino,
        gino=(arm == "gino"), quadrann=(arm == "quadrann"),
        uqno=False, gino_hidden=8, max_gino_points=32,
        quadrann_condition_on_material=(arm == "quadrann"),
        quadrann_max_points=48,
    )
    for param in pino.parameters():
        param.requires_grad_(False)
    if arm == "pino_head":
        for param in pino.weight_head.parameters():
            param.requires_grad_(True)
    elif arm == "gino":
        with torch.no_grad():
            model.gino_gate.fill_(.1)
    else:
        with torch.no_grad():
            model.quadrann_gate.fill_(.1)
    return model


def _predict_by_geometry(model, data):
    D, coeff, truth, trueJ, meta = data
    model.eval()
    grouped = {}
    for i, row in enumerate(meta):
        grouped.setdefault(row["geometry_id"], []).append(i)
    rs = torch.zeros_like(truth)
    js = torch.zeros_like(trueJ)
    encode_time = 0.
    query_time = 0.
    with torch.no_grad():
        for _, indices in grouped.items():
            ref = indices[0]
            for ii in indices[1:]:
                if not torch.equal(D[ref], D[ii]):
                    raise AssertionError("same geometry ID used for different voxel fields")
            start = time.perf_counter()
            w = model.geometry_weights(D[ref:ref+1])
            encode_time += time.perf_counter()-start
            start = time.perf_counter()
            r = model.pino.moment_from_weights(w.expand(len(indices),-1), coeff[indices])
            J = model.pino.jacobian_from_weights(w.expand(len(indices),-1), coeff[indices])
            query_time += time.perf_counter()-start
            rs[indices] = r
            js[indices] = J
    return {
        "r":rs, "J":js,
        "r_mae":float((rs-truth).abs().mean()),
        "J_mae":float((js-trueJ).abs().mean()),
        "r_relative_l2":float(torch.linalg.vector_norm(rs-truth)
                              /torch.linalg.vector_norm(truth).clamp_min(1e-12)),
        "J_relative_l2":float(torch.linalg.vector_norm(js-trueJ)
                              /torch.linalg.vector_norm(trueJ).clamp_min(1e-12)),
        "cold_encoding_seconds":encode_time,
        "warm_query_seconds":query_time,
        "unique_geometry_count":len(grouped),
        "total_queries":len(coeff),
        "model_J_native_admitted":False,
    }


def _scalar_metrics(pred):
    return {k:v for k,v in pred.items() if not isinstance(v,torch.Tensor)}


def _fit_adapter(model, data, *, arm, seed, steps, indices):
    D, c, r, J, _ = data["fit"]
    model.train()
    model.pino.eval()    # freeze original trunk statistics/numerical behavior
    params = [p for p in model.parameters() if p.requires_grad]
    if not params:
        raise AssertionError("no trainable adapter parameters")
    optimizer = torch.optim.Adam(params, lr=.0015)
    best_state = copy.deepcopy(model.state_dict())
    model.eval()
    val0 = _predict_by_geometry(model, data["validation"])
    best = val0["r_mae"] + .25*val0["J_mae"]
    selected_step = 0
    history = [{"step":0, "validation_score":best}]
    start = time.perf_counter()
    for step, sample_idx in enumerate(indices,1):
        model.train()
        model.pino.eval()
        weights=model.geometry_weights(D[sample_idx:sample_idx+1])
        sample_c=c[sample_idx:sample_idx+1]
        pred=model.pino.moment_from_weights(weights,sample_c)
        predJ=model.pino.jacobian_from_weights(weights,sample_c)
        loss=(pred-r[sample_idx:sample_idx+1]).square().mean() + \
             .25*(predJ-J[sample_idx:sample_idx+1]).square().mean()
        if not bool(torch.isfinite(loss)):
            raise FloatingPointError("nonfinite adapter training loss")
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(params,1.0)
        optimizer.step()
        if step == steps or step == 1 or step%4==0:
            model.eval()
            val = _predict_by_geometry(model, data["validation"])
            score=val["r_mae"]+.25*val["J_mae"]
            history.append({"step":step,"validation_score":score,
                            "train_loss":float(loss.detach())})
            if score < best:
                best,selected_step,best_state=score,step,copy.deepcopy(model.state_dict())
    elapsed=time.perf_counter()-start
    model.load_state_dict(best_state)
    model.eval()
    validation=_scalar_metrics(_predict_by_geometry(model,data["validation"]))
    test=_scalar_metrics(_predict_by_geometry(model,data["test"]))
    return model,{
        "arm":arm, "seed":seed,"updates":steps,
        "selected_step":selected_step,
        "selected_by":"validation r_MAE + 0.25 J_MAE, never test",
        "train_seconds":elapsed,
        "frozen_pino_except_original_head_finetune":True,
        "trainable_parameters":sum(p.numel() for p in params),
        "total_parameters":sum(p.numel() for p in model.parameters()),
        "validation":validation,"test":test,
        "history":history,"newton_admission":False,
        "GINO_original_learned":arm=="gino",
        "QuadrANN_original_learned":arm=="quadrann",
    }


def _uq_calibration(frozen_head_model, data, *, seed, train_steps, alpha=.25, tolerance=.05):
    """Train original UQNO residual head using fit only, groupwise calibrate val."""
    import torch.nn.functional as F
    pino = copy.deepcopy(frozen_head_model.pino)
    for par in pino.parameters():
        par.requires_grad_(False)
    pino.eval()
    torch.manual_seed(seed+733101)
    uq = SelectedPINOCandidates(pino,uqno=True)
    for par in uq.pino.parameters():
        par.requires_grad_(False)
    params=[p for p in uq.uqno_adapter.parameters() if p.requires_grad]
    optim=torch.optim.Adam(params,lr=.003)
    fit=data["fit"]
    samples=torch.randint(len(fit[0]),(train_steps,),
                          generator=torch.Generator().manual_seed(seed+55357)).tolist()
    start=time.perf_counter()
    for i in samples:
        uq.train();uq.pino.eval()
        with torch.no_grad():
            w=uq.pino.encode_geometry(fit[0][i:i+1])
        mean,scale=uq.uqno_adapter(w,fit[1][i:i+1])
        residual=(mean.detach()-fit[2][i:i+1])
        objective=((residual/scale).square()+2*torch.log(scale)).mean()
        if not bool(torch.isfinite(objective)):
            raise FloatingPointError("nonfinite UQNO scale objective")
        optim.zero_grad(set_to_none=True)
        objective.backward()
        torch.nn.utils.clip_grad_norm_(params,1.)
        optim.step()
    train_time=time.perf_counter()-start
    uq.eval()
    def get(data_):
        mean,scale=[],[]
        with torch.no_grad():
            for i in range(len(data_[0])):
                proposal=uq(data_[0][i:i+1],data_[1][i:i+1])
                mean.append(proposal.result.moments)
                scale.append(proposal.result.uncertainty)
        return torch.cat(mean),torch.cat(scale)
    val_m,val_s=get(data["validation"])
    test_m,test_s=get(data["test"])
    train_ids={x["geometry_id"] for x in data["fit"][4]}
    cal_ids=[x["geometry_id"] for x in data["validation"][4]]
    test_ids=[x["geometry_id"] for x in data["test"][4]]
    if set(cal_ids)&train_ids or set(test_ids)&(train_ids|set(cal_ids)):
        raise AssertionError("UQ geometry leakage")
    conformal=GroupwiseConformalScreen(alpha=alpha).fit(
        val_m,val_s,data["validation"][2],cal_ids,
        training_geometry_ids=sorted(train_ids),
    )
    qhat=conformal.qhat
    groups=sorted(set(test_ids))
    covered=[]
    for gid in groups:
        idx=torch.tensor([x==gid for x in test_ids])
        radius=qhat*test_s[idx]
        covered.append(bool(((test_m[idx]-data["test"][2][idx]).abs()<=radius).all()))
    threshold_rejected=0
    native_derivative_blocked=0
    with torch.no_grad():
        for i in range(len(test_ids)):
            proposal=uq(data["test"][0][i:i+1],data["test"][1][i:i+1])
            st=conformal.screen(proposal,test_ids[i],
                                max_simultaneous_radius=tolerance)
            threshold_rejected += int(st.exact_required)
            native=conformal.screen(proposal,test_ids[i],
                                    max_simultaneous_radius=tolerance,
                                    for_native_newton=True)
            native_derivative_blocked+=int(native.exact_required)
    return {
        "seed":seed,"train_updates":train_steps,
        "residual_fit_only":True,"train_seconds":train_time,
        "calibration_geometry_count":len(set(cal_ids)),
        "test_geometry_count":len(groups),
        "alpha":alpha,"qhat":qhat,
        "geometry_group_coverage":sum(covered)/len(covered),
        "threshold_predeclared":tolerance,
        "exact_request_fraction":threshold_rejected/len(test_ids),
        "native_newton_exact_request_fraction":native_derivative_blocked/len(test_ids),
        "native_newton_admitted":False,
        "groupwise_exchangeability_not_proven":True,
    }


def run(*, seeds=(131,137,139), base_steps=40, adapter_steps=12,
        uq_steps=24, train_geometries_per_family=10, test_ellipsoids=6):
    if not seeds or min(base_steps,adapter_steps,uq_steps)<1:
        raise ValueError("positive budgets and nonempty seeds required")
    torch.set_num_threads(1)
    rows=[]
    for seed in seeds:
        baseline=run_seed(seed=seed,steps=base_steps,
                          train_geometries_per_family=train_geometries_per_family,
                          test_ellipsoid_geometries=test_ellipsoids,
                          queries_per_geometry=2,
                          grid_size=8,points_per_axis=4,smoothing=.02,
                          moment_parameterization="logistic_atom",temperature=.12,
                          device="cpu")
        data=generate_splits(seed=seed,
            train_geometries_per_family=train_geometries_per_family,
            test_ellipsoid_geometries=test_ellipsoids,
            queries_per_geometry=2,grid_size=8)
        # Identical pretrained state and same data/observation indices.
        trained_state=baseline["checkpoint_state"]
        obs=torch.randint(
            len(data["fit"][0]),(adapter_steps,),
            generator=torch.Generator().manual_seed(seed+31337),
        ).tolist()
        arms=[]
        reference=None
        for arm in ARMS:
            candidate=_make_arm(arm,trained_state,seed)
            candidate,receipt=_fit_adapter(candidate,data,arm=arm,seed=seed,
                                           steps=adapter_steps,indices=obs)
            arms.append(receipt)
            if arm=="pino_head":
                reference=candidate
        uq_metrics=_uq_calibration(reference,data,seed=seed,
                                   train_steps=uq_steps)
        if any(r["updates"]!=adapter_steps for r in arms):
            raise AssertionError("unmatched update budgets")
        rows.append({
            "seed":seed,
            "fit_digest":data["metadata"]["fit_sha256"],
            "validation_digest":data["metadata"]["validation_sha256"],
            "test_digest":data["metadata"]["test_sha256"],
            "fit_geometries":len(set(x["geometry_id"] for x in data["fit"][4])),
            "val_geometries":len(set(x["geometry_id"] for x in data["validation"][4])),
            "test_geometries":len(set(x["geometry_id"] for x in data["test"][4])),
            "pretrained_pino_selected_step":baseline["training"]["selected_step"],
            "arms":arms,"uqno":uq_metrics,
        })
    aggregate=[]
    for arm in ARMS:
        rr=[next(y for y in row["arms"] if y["arm"]==arm) for row in rows]
        aggregate.append({
            "arm":arm,"seeds":list(seeds),
            "mean_test_r_relative_l2":statistics.mean(r["test"]["r_relative_l2"] for r in rr),
            "mean_test_J_relative_l2":statistics.mean(r["test"]["J_relative_l2"] for r in rr),
            "mean_test_r_mae":statistics.mean(r["test"]["r_mae"] for r in rr),
            "mean_test_J_mae":statistics.mean(r["test"]["J_mae"] for r in rr),
            "mean_train_seconds":statistics.mean(r["train_seconds"] for r in rr),
            "mean_test_cold_encoding_seconds":statistics.mean(r["test"]["cold_encoding_seconds"] for r in rr),
            "mean_test_warm_query_seconds":statistics.mean(r["test"]["warm_query_seconds"] for r in rr),
            "trainable_parameters":rr[0]["trainable_parameters"],
            "selected_steps":[r["selected_step"] for r in rr],
        })
    uq_aggregate={
        "mean_group_coverage":statistics.mean(r["uqno"]["geometry_group_coverage"] for r in rows),
        "mean_exact_request_fraction":statistics.mean(r["uqno"]["exact_request_fraction"] for r in rows),
        "all_native_newton_admissions_withheld":all(not r["uqno"]["native_newton_admitted"] for r in rows),
    }
    return {
        "schema":"W6_P12_THREE_SEED_ADAPTER_TRAIN_AND_UQNO_V1",
        "source":"ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI",
        "same_frozen_pretrained_PINO_per_seed":True,
        "same_fit_validation_test_geometry_ids_within_seed":True,
        "matched_auxiliary_label_and_update_budget":True,
        "parameter_and_flop_budgets_not_matched":True,
        "pretrained_pino_updates":base_steps,
        "adapter_updates_per_arm":adapter_steps,
        "UQNO_fit_only_updates":uq_steps,
        "trunk_is_primary":"P-CRAFT UFNO3d",
        "seeds":list(seeds),"aggregate":aggregate,"uq_aggregate":uq_aggregate,
        "per_seed":rows,"maximum_process_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "claims":{"full_Cherchi_teacher":False,"native_Newton_J_certified":False,
                  "original_PINO_replaced":False,"full_512_cube_training":False,
                  "all_models_promoted":False,
                  "upstream_adapters_separately_trained":True},
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--seeds",default="131,137,139")
    p.add_argument("--base-steps",type=int,default=40)
    p.add_argument("--adapter-steps",type=int,default=12)
    p.add_argument("--uq-steps",type=int,default=24)
    p.add_argument("--train-geometries-per-family",type=int,default=10)
    p.add_argument("--test-ellipsoids",type=int,default=6)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=run(seeds=tuple(int(x) for x in a.seeds.split(",")),
               base_steps=a.base_steps,adapter_steps=a.adapter_steps,
               uq_steps=a.uq_steps,train_geometries_per_family=a.train_geometries_per_family,
               test_ellipsoids=a.test_ellipsoids)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({"aggregate":result["aggregate"],
                      "uq_aggregate":result["uq_aggregate"]},indent=2))
if __name__=="__main__":
    main()
