"""W5 M9: same 4-channel analytic-P0 comparison of M8 and W6 M6 Gauss models.

This is NOT W2 supervised learning. W2's 25 independent historical r10
snapshots are merely audited through a pinned *metadata* manifest; no J
there is a certified smooth neighborhood derivative. Candidate decisions
are vetted against analytic truth, NOT an installed native Cherchi evaluator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import resource
import statistics
import time

import numpy as np
import torch

from .m8_fair_benchmark import (
    FRAMEWORKS as M8_MODELS, model_for as m8_model_for, real_parameters,
    train as m8_train, metrics as m8_metrics, truth_decision_metrics,
    split_fit_validation, latency as m8_latency)
from .m8_analytic_data import (
    Shape, TEACHER, analytic_truth, dataset, sha_dataset, independent_family_check)
from .m9_readonly_w6 import load_m9_w6, W6_M6_SOURCE_COMMIT, W6_M6_FILES
from .m7_cross_framework import W6_FILES
from .m9_archive_gate import inspect_historical_manifest, W2_SOURCE_COMMIT, W2_MANIFEST_EXPECTED_SHA

NAMES = M8_MODELS + ('w6_gauss_004', 'w6_gauss_025')
B_NATIVE = (1.,)*7+(2.,)*3
SCALES = torch.tensor((8.,)+(16.,)*3+(32.,)*6)


def create_model(name: str, seed: int, external):
    m4,m5,m6,_=external
    if name in M8_MODELS:
        return m8_model_for(name,seed,(m4,m5))
    torch.manual_seed(seed)
    if name=='w6_gauss_004':
        return m6.GaussPotentialMoment(rule='gauss',points_per_axis=6,hidden=32,smoothing=.04)
    if name=='w6_gauss_025':
        return m6.GaussPotentialMoment(rule='gauss',points_per_axis=6,hidden=32,smoothing=.25)
    raise ValueError('Unknown model, do not silently add candidates')


def _vec10(t):
    a=np.asarray(t,dtype=np.float64)
    if a.shape!=(10,) or not np.isfinite(a).all():
        raise ValueError('invalid finite ten-moment vector')
    return a


def physically_guarded_decisions(model, heldout, guard, *, damping=0.01, trust=0.12):
    """Reject nonphysical surrogate moments BEFORE trusting a 1D candidate.

    Numerically exact analytic truth is queried *offline* at target/candidate;
    the heldout original truth is precomputed by the analytic dataset. These
    oracle calls are not native Cherchi calls, no geometry commits occur.
    """
    if not math.isfinite(damping) or damping<=0 or not math.isfinite(trust) or not 0<trust<.2:
        raise ValueError('invalid 1D policy')
    D,c,real_r,real_J,meta=heldout
    model.eval()
    with torch.no_grad():
        z=model.encode_geometry(D).detach()
        pred=model.moment(z,c).detach()
    J=model.jacobian(z,c).detach()
    current_gate=guard.physical_moment_diagnostic(pred,low=(-1.,)*3,high=(1.,)*3)
    truth_gate=guard.physical_moment_diagnostic(real_r,low=(-1.,)*3,high=(1.,)*3)
    if not bool(truth_gate['necessary_conditions_pass'].all()):
        raise AssertionError('Independent analytic true moments violate known support box')
    n=len(meta);accepted=0; rejected_current=0;rejected_next=0;rejected_true=0
    candidate_calls=0;target_calls=0;step_errors=[];loss_gaps=[];after_losses=[]
    for i,info in enumerate(meta):
        shape_data=info['shape']
        shape=Shape(info['family'],tuple(shape_data['center']),tuple(shape_data['axes']),shape_data['density'])
        h=float(info['h_local'])
        goal=analytic_truth(shape,h+.12)[1]
        target_calls+=1
        initial=_vec10(real_r[i].numpy())
        before=float(0.5*np.dot(initial-goal,initial-goal))
        if not bool(current_gate['necessary_conditions_pass'][i]):
            rejected_current+=1
            after_losses.append(before)
            continue
        z_world=shape.center[2]+shape.axes[2]*h
        tangent=np.zeros(10)
        tangent[0]=-shape.axes[2]/(1+z_world*z_world)**1.5
        tangent[3]=-z_world*shape.axes[2]/(1+z_world*z_world)**1.5
        j_pred=np.asarray(J[i].numpy(),dtype=np.float64)
        directional=j_pred@tangent
        vec=_vec10(pred[i].numpy())-goal
        step=float(np.clip(-float(directional@vec)/(float(directional@directional)+damping),-trust,trust))
        next_h=h+step
        if not -1<next_h<1:
            rejected_next+=1
            after_losses.append(before)
            continue
        next_c=analytic_truth(shape,next_h)[0]
        # The encoder was computed only once; the next candidate is an extra
        # cheap query with the SAME frozen geometry code.
        with torch.no_grad():
            candidate_pred=model.moment(z[i:i+1],torch.as_tensor(next_c,dtype=c.dtype)[None]).detach()
        next_safe=guard.physical_moment_diagnostic(candidate_pred)['necessary_conditions_pass']
        if not bool(next_safe[0]):
            rejected_next+=1
            after_losses.append(before)
            continue
        exact_candidate=analytic_truth(shape,next_h)[1]
        candidate_calls+=1
        after=float(.5*np.dot(exact_candidate-goal,exact_candidate-goal))
        if after<before-1e-12:
            accepted+=1
            after_losses.append(after)
        else:
            rejected_true+=1
            after_losses.append(before)
        oracle_J=np.asarray(real_J[i].numpy(),dtype=np.float64)
        oracle_directional=oracle_J@tangent
        oracle_step=float(np.clip(-float(oracle_directional@(initial-goal)) /
                                  (float(oracle_directional@oracle_directional)+damping),-trust,trust))
        step_errors.append(abs(step-oracle_step))
        ideal=analytic_truth(shape,h+oracle_step)[1]
        oracle_loss=float(.5*np.sum((ideal-goal)**2))
        loss_gaps.append(after-oracle_loss)
    return {
        'eligible_samples':n,
        'true_moments_necessary_support_pass_fraction':float(truth_gate['necessary_conditions_pass'].float().mean()),
        'predicted_current_necessary_support_pass_fraction':float(current_gate['necessary_conditions_pass'].float().mean()),
        'rejected_at_current_surrogate_physicality':rejected_current,
        'rejected_at_candidate_surrogate_physicality_or_domain':rejected_next,
        'rejected_by_independent_analytic_true_objective':rejected_true,
        'accepted_candidates':accepted,
        'accepted_over_all_samples':accepted/n,
        'mean_true_loss_after_fallback':float(statistics.mean(after_losses)),
        'step_mae_for_physicality_screened_candidates':statistics.mean(step_errors) if step_errors else None,
        'true_signed_objective_gap_for_screened_candidates':statistics.mean(loss_gaps) if loss_gaps else None,
        'additional_analytic_target_oracle_queries':target_calls,
        'additional_analytic_candidate_oracle_queries':candidate_calls,
        'new_native_cherchi_queries':0,
        'not_a_10D_native_solver_optimization':True,
        'no_geometric_state_committed':True,
    }


def additional_physical_metrics(model, heldout, guard):
    """Independent necessary moment-cone checks and always-empty sign probe."""
    D,c,raw,_,_=heldout
    model.eval()
    with torch.no_grad():
        z=model.encode_geometry(D).detach()
        pred=model.moment(z,c).detach()
        empty_c=torch.zeros_like(c); empty_c[:,0]=-1.
        empty_pred=model.moment(z,empty_c).detach()
    cone=guard.physical_moment_diagnostic(pred)
    cone_empty=guard.physical_moment_diagnostic(empty_pred)
    true_cone=guard.physical_moment_diagnostic(raw)
    return {
        'necessary_support_pass_fraction':float(cone['necessary_conditions_pass'].float().mean()),
        'necessary_support_violation_count':int((~cone['necessary_conditions_pass']).sum()),
        'true_analytic_support_pass_fraction':float(true_cone['necessary_conditions_pass'].float().mean()),
        'empty_cut_predicted_mass_mean':float(empty_pred[:,0].mean()),
        'empty_cut_predicted_negative_mass_fraction':float((empty_pred[:,0]<0).float().mean()),
        'empty_cut_necessary_support_pass_fraction':float(cone_empty['necessary_conditions_pass'].float().mean()),
        'empty_cut_ground_truth_mass':0.0,
        'signed_empty_region_claim':'UNKNOWN_FOR_NETWORK_UNLESS_INDEPENDENT_SIGN_GATE;NOT_NATIVE_MATERIAL_CERTIFIED',
        'necessary_conditions_only_not_sufficient_geometry_proof':True,
    }


def query_budget_replay(model, sample, *, repeats=5, budgets=(1,2,4,8,16)):
    """Time ACTUAL repeated encode/queries (not additive estimates)."""
    if not 1<=repeats<=100 or any(q<1 for q in budgets):
        raise ValueError('invalid latency protocol')
    D=sample[0][:1];c=sample[1][:1]
    model.eval()
    with torch.no_grad():
        z=model.encode_geometry(D).detach()
        model.moment(z,c)
        model.jacobian(z,c)
    out={}
    def timed(fn):
        for _ in range(2):fn()
        samples=[]
        for _ in range(repeats):
            start=time.perf_counter_ns();fn();samples.append((time.perf_counter_ns()-start)*1e-6)
        return float(statistics.median(samples))
    with torch.no_grad():
        for q in budgets:
            controls=[c.clone() for _ in range(q)]
            for i,cc in enumerate(controls):
                cc[:,0]+= (i%5)*0.015
                cc /= cc.norm(dim=-1,keepdim=True)
            def reused():
                zz=model.encode_geometry(D)
                for ci in controls:
                    model.moment(zz,ci)
                    model.jacobian(zz,ci)
            def each():
                for ci in controls:
                    zz=model.encode_geometry(D)
                    model.moment(zz,ci)
                    model.jacobian(zz,ci)
            warm_ms=timed(reused)
            repeated_ms=timed(each)
            out[str(q)]={'single_encode_q_moment_and_J_ms':warm_ms,
                         'q_reencoding_moment_and_J_ms':repeated_ms,
                         'actual_measured_not_additive_estimate':True}
    return out


def execute(*,w6_root,w2_manifest,seeds=(19,23,29),steps=100,per_family=20,
            names=NAMES,repeats=5):
    if type(steps) is not int or steps<1 or type(per_family) is not int or per_family<5 or not names or len(set(names))!=len(names) or any(n not in NAMES for n in names):
        raise ValueError('invalid training scope')
    if not seeds or len(set(seeds))!=len(seeds) or any(type(s) is not int for s in seeds):
        raise ValueError('invalid random seeds')
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    m4,m5,m6,guard=load_m9_w6(w6_root)
    remote=inspect_historical_manifest(w2_manifest)
    extern=(m4,m5,m6,guard)
    counts={name:real_parameters(create_model(name,seeds[0],extern)) for name in names}
    capacity=max(counts.values())/min(counts.values())
    if capacity>1.05:raise ValueError('candidate parameter capacities differ by >5%')
    experiments=[]
    for seed in seeds:
        raw_train=dataset(('box','sphere'),per_family=per_family,seed=seed)
        heldout=dataset(('ellipsoid',),per_family=per_family,seed=seed+1)
        fit,valid=split_fit_validation(raw_train,seed,max(1,per_family//5))
        split=independent_family_check(fit,valid,heldout)
        row={'seed':seed,'dataset_train_sha256':sha_dataset(raw_train),
             'dataset_heldout_sha256':sha_dataset(heldout),
             'geometry_split':split,'models':{}}
        for name in names:
            model=create_model(name,seed,extern)
            training=m8_train(model,fit,valid,seed=seed,steps=steps)
            standard=m8_metrics(model,heldout)
            prior_decision=truth_decision_metrics(model,heldout)
            safety=additional_physical_metrics(model,heldout,guard)
            guarded=physically_guarded_decisions(model,heldout,guard)
            cost=m8_latency(model,heldout,repeats=repeats)
            repeated=query_budget_replay(model,heldout,repeats=repeats)
            row['models'][name]={'training':training,'heldout':standard,'ungated_1D_decision':prior_decision,
                                 'necessary_support':safety,'guarded_1D_decision':guarded,
                                 'timing':cost,'measured_query_budgets':repeated}
        experiments.append(row)
    aggregate={}
    fields=(('heldout','r_mae'),('heldout','J_mae'),('heldout','directional_mae'),
            ('heldout','Jq_max_asymmetry'),
            ('necessary_support','necessary_support_pass_fraction'),
            ('necessary_support','empty_cut_predicted_mass_mean'),
            ('guarded_1D_decision','accepted_over_all_samples'),
            ('ungated_1D_decision','one_step_candidate_accepted_fraction'))
    for name in names:
        series=[row['models'][name] for row in experiments]
        agg={}
        for group,key in fields:
            xs=[float(m[group][key]) for m in series]
            agg[f'{group}.{key}']={'mean':statistics.mean(xs),
                                  'sample_sd':statistics.stdev(xs) if len(xs)>1 else None,
                                  'per_seed':dict(zip(map(str,seeds),xs))}
        agg['train_cpu_seconds_sum']=sum(x['training']['cpu_training_seconds'] for x in series)
        agg['median_encode_ms_across_seeds']=statistics.median(x['timing']['encoding_ms'] for x in series)
        agg['median_warm_J_ms_across_seeds']=statistics.median(x['timing']['warm_J_ms'] for x in series)
        agg['query_budget_mean_ms_across_seeds']={q:{scope:statistics.mean(row['measured_query_budgets'][q][scope] for row in series)
                                          for scope in ('single_encode_q_moment_and_J_ms','q_reencoding_moment_and_J_ms')}
                                         for q in ('1','2','4','8','16')}
        aggregate[name]=agg
    return {
        'schema':'W5_M9_4CH_INPUT_PARITY_GAUSS_PHYSICAL_GATES_V1',
        'evidence':'NEW_CPU_ANALYTIC_P0_TRAINING;HISTORICAL_W2_MANIFEST_METADATA_ONLY',
        'training_data_truth_kind':TEACHER,
        'W0_native_B':list(B_NATIVE),'native_c_preserved':True,
        'supported_hessian_hypothesis':'ANALYTIC_SMOOTH_AMBIENT_P0_ONLY',
        'source_W6_M5_git_blobs':W6_FILES,'source_W6_M6_git_blobs':W6_M6_FILES,
        'source_W6_M6_readonly_head':W6_M6_SOURCE_COMMIT,
        'W2_readonly_head':W2_SOURCE_COMMIT,'W2_readonly_manifest_git_blob':W2_MANIFEST_EXPECTED_SHA,
        'W2_archive_metadata_gate':remote,
        'real_Cherchi_W5_calls':0,'W2_J_training_labels':0,
        'models':list(names),'seeds':list(seeds),'steps_upper_bound':steps,
        'fit_validation_test_from_exact_same_4channel_tensor':True,
        'encoder_architecture_equal':False,
        'parameter_counts_real':counts,'parameter_max_min_ratio':capacity,
        'training_loss':'MSE(r)+0.5*MSE(Jc)','optimizer':'Adam lr=.003, batch=8, validation_only checkpoint',
        'gauss_025_selection_scope':'EXPLORATORY; epsilon=.25 inherited from W6 M6 heldout exploratory tuning (not a fresh hyperparameter selection)',
        'physical_support_region':'ALL analytic D support is contained in independently known [-1,1]^3',
        'physical_constraints_are_only_necessary':True,
        'full_native_optimizer_evidence':False,
        'device':'cpu','torch':torch.__version__,'python':platform.python_version(),
        'torch_threads':torch.get_num_threads(),'gpu_hours':0.,
        'rss_process_high_water_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'per_family':per_family,'repeats':repeats,
        'full_seed_experiments':experiments,'aggregate':aggregate}


def main():
    parser=argparse.ArgumentParser(description='M9 fair analytic P0 Gauss/physicality audit')
    parser.add_argument('--w6-root',required=True)
    parser.add_argument('--w2-manifest',required=True)
    parser.add_argument('--seeds',default='19,23,29')
    parser.add_argument('--steps',type=int,default=100)
    parser.add_argument('--per-family',type=int,default=20)
    parser.add_argument('--models',default=','.join(NAMES))
    parser.add_argument('--repeats',type=int,default=5)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    report=execute(w6_root=args.w6_root,w2_manifest=args.w2_manifest,
                   seeds=tuple(map(int,args.seeds.split(','))),steps=args.steps,
                   per_family=args.per_family,names=tuple(args.models.split(',')),
                   repeats=args.repeats)
    txt=json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
    if args.output:args.output.write_text(txt,encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='full_seed_experiments'},sort_keys=True,indent=2))

if __name__=='__main__':main()
