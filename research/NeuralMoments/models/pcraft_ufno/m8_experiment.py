"""W6 M8 reproducible ANALYTIC-P0 0/1/2 independent support-query comparison.

The frozen M3 training labels and split are reused; validation chooses M7
weights without looking at test ellipsoids. For each unseen ellipsoid, two
separately seeded analytic supports and eight DISJOINT analytic test cuts are
created. Only 0, 1 or 2 supports are given to the bounded adapter; the
8 test labels are accessed solely during evaluation. These are NOT W2 labels.

Examples, from repository root:
  python -m research.NeuralMoments.models.pcraft_ufno.m8_experiment \
    --seeds 19,23,29 --steps 400 --output /tmp/w6_m8_cpu.json
"""
from __future__ import annotations

import argparse
import json
import math
import platform
import statistics
import time

import numpy as np
import torch

from .analytic_cut import (GeometrySpec, sample_dataset,
                           assert_disjoint_family_splits, vertical_cut_truth)
from .m4_experiment import dataset_digest, split_by_geometry, train_early_stop
from .m7_experiment import make_model, M3_FROZEN_SHA
from .m7_realizable import RealizableUFNOMoment
from .m8_bounded_adapter import BoundedAtomAdapter
from .m6_moment_guard import physical_moment_diagnostic


def external_ellipsoid_queries(heldout, *, seed: int,
                                supports: int = 2, targets: int = 8):
    """Match M3 ellipsoid geometry IDs while drawing fresh independent controls.

    Geometry RNG consumes 2 training-free controls per geometry in
    sample_dataset; we reproduce that stream only to recover the primitive
    parameters, then draw all supports and holdout controls using two
    separate RNG streams. Each geometry appears ONCE in this outer split.
    """
    if supports != 2 or targets < 1:
        raise ValueError('two potential support cuts and positive test cuts required')
    D, _, _, _, meta = heldout
    if len(meta)%2 or any(m['family']!='ellipsoid' for m in meta):
        raise ValueError('expected M7 ellipsoid-only two-controls-per-geometry split')
    geom_rng=np.random.default_rng(seed+1)
    support_rng=np.random.default_rng(seed+811)
    target_rng=np.random.default_rng(seed+2701)
    ds=[];support_c=[];support_r=[];eval_c=[];eval_r=[];eval_j=[];identities=[];all_h=[]
    for idx in range(len(meta)//2):
        center=tuple(float(x) for x in geom_rng.uniform(-.1,.1,3))
        axes=tuple(float(x) for x in geom_rng.uniform(.46,.73,3))
        spec=GeometrySpec('ellipsoid',center,(axes[0],axes[1]*.8,axes[2]*1.1))
        # Two h draws present in the original frozen heldout dataset.
        _=geom_rng.uniform(-.65,.65,2)
        if meta[2*idx]['geometry_id']!=spec.geometry_id or meta[2*idx+1]['geometry_id']!=spec.geometry_id:
            raise AssertionError('M3 heldout geometry identity mismatch')
        hs=list(map(float,support_rng.uniform(-.55,.55,supports)))
        ht=list(map(float,target_rng.uniform(-.55,.55,targets)))
        if any(abs(a-b)<1e-12 for a in hs for b in ht):
            raise AssertionError('support and target controls must be disjoint')
        sp=[vertical_cut_truth(spec,h) for h in hs]
        ev=[vertical_cut_truth(spec,h) for h in ht]
        ds.append(D[2*idx])
        support_c.append(torch.from_numpy(np.stack([row[0] for row in sp])).float())
        support_r.append(torch.from_numpy(np.stack([row[1] for row in sp])).float())
        eval_c.append(torch.from_numpy(np.stack([row[0] for row in ev])).float())
        eval_r.append(torch.from_numpy(np.stack([row[1] for row in ev])).float())
        eval_j.append(torch.from_numpy(np.stack([row[2] for row in ev])).float())
        identities.append(spec.geometry_id)
        all_h.append({'support_h':hs,'eval_h':ht})
    return {'D':torch.stack(ds), 'support_c':torch.stack(support_c),
            'support_r':torch.stack(support_r),'eval_c':torch.stack(eval_c),
            'eval_r':torch.stack(eval_r),'eval_J':torch.stack(eval_j),
            'geometry_ids':identities,'support_eval_cut_ledger':all_h}


def evaluate_adaptation(model: RealizableUFNOMoment, cases: dict, *,
                        ridge=1e-4, max_iterations=5, count_queries=(0,1,2)) -> dict:
    model.eval()
    D=cases['D']; n=len(D);q=cases['eval_c'].shape[1]
    with torch.no_grad():
        start=time.perf_counter()
        z=model.encode_geometry(D).detach()     # exactly once for all query counts
        encode_seconds=time.perf_counter()-start
    measurements={}
    for k in count_queries:
        if k not in (0,1,2):raise ValueError('only 0/1/2 queries supported')
        start=time.perf_counter()
        adapter=BoundedAtomAdapter(model,D,z,cases['support_c'][:,:k],
                    cases['support_r'][:,:k],source='ANALYTIC_P0',
                    ridge=ridge,max_iterations=max_iterations)
        fitting_seconds=time.perf_counter()-start
        preds=[];jac=[]
        with torch.no_grad():
            for j in range(q):
                preds.append(adapter.predict(cases['eval_c'][:,j]))
                jac.append(adapter.jacobian(cases['eval_c'][:,j]))
        pred=torch.stack(preds,dim=1)
        J=torch.stack(jac,dim=1)
        real=cases['eval_r'];truth_j=cases['eval_J']
        feasible=physical_moment_diagnostic(pred.reshape(-1,10),tol=1e-6)
        direction=torch.arange(1,11,dtype=J.dtype,device=J.device)
        direction=direction/direction.norm()
        full_cap=adapter.capacity.sum(dim=1)
        measurements[str(k)]={
            'r_mae':float((pred-real).abs().mean()),
            'J_mae':float((J-truth_j).abs().mean()),
            'directional_derivative_mae':float(((J-truth_j)@direction).abs().mean()),
            'r_relative_l2':float((pred-real).norm()/real.norm().clamp_min(1e-12)),
            'necessary_condition_pass_fraction':float(feasible['necessary_conditions_pass'].float().mean()),
            'adapted_mass_weight_min':float(adapter.weights.min()),
            'adapted_weight_minus_capacity_max':float((adapter.weights-adapter.capacity).max()),
            'support_mse_before_mean':statistics.mean(adapter.audit.support_loss_before),
            'support_mse_after_mean':statistics.mean(adapter.audit.support_loss_after),
            'support_mass_exceeds_sampled_capacity_count':sum(adapter.audit.support_mass_exceeds_sampled_capacity),
            'support_iterations':list(adapter.audit.iterations),
            'teacher_query_count_per_heldout_geometry':k,
            'total_support_queries':k*n,
            'evaluation_oracle_only_queries':n*q,
            'fit_wall_seconds_total':fitting_seconds,
            'geometry_encoding_seconds_once_shared':encode_seconds,
            'no_W2_native_training':True,
            'no_proven_CAD_realisability':True,
        }
    return measurements


def run(*, seeds=(19,23,29), max_steps=400, per_family=20,
        grid_size=8, ridge=1e-4, iterations=5) -> dict:
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    seeds=tuple(int(s) for s in seeds)
    if not seeds or len(set(seeds))!=len(seeds) or max_steps<1 or per_family<5:
        raise ValueError('invalid seed, training budget or geometry count')
    report={
      'schema':'W6_M8_BOUND_NONNEGATIVE_ATOMIC_FEWSHOT_P0_V1',
      'status':'ANALYTIC_P0_ONLY_NOT_W2_CAD_CERTIFICATE',
      'source':'volcano-code/Spin_test frozen M3 independent continuum plane-cut P0',
      'seed_list':list(seeds),'training':'M7 tau=0.12, Adam 0.003, MSE(r)+0.5*MSE(J), family split and validation early stopping',
      'max_train_steps':max_steps,'train_geometries_per_family':per_family,
      'test_families':['ellipsoid'],'test_queries_per_geometry':8,
      'allowed_support_queries_per_geometry':[0,1,2],
      'support_provenance':'ANALYTIC_P0 only; all W2 archived H8f candidates excluded',
      'policy':'0/1/2 supports independently generated, not seen in neural training; target labels not seen by adapter',
      'geometry_input':'M7 four-channel 8^3 sampled voxel source; fixed sampled atom capacity',
      'model_claim':'NONNEGATIVE_BOUNDED_ATOMIC_MEASURE_NOT_NATIVE_CHERCHI',
      'native_J_claim':False,'optimizer_admission':False,'W2_admitted_training_labels':0,
      'W0_B_diag':[1.]*7+[2.]*3,
      'ridge':ridge,'iterations':iterations,
      'device':'cpu','torch_version':torch.__version__,
      'python_version':platform.python_version(), 'cuda_hours':0.,
      'cases':[],'aggregate':{}
    }
    for seed in seeds:
        all_train=sample_dataset(('box','sphere'),per_family=per_family,seed=seed,grid_size=grid_size)
        holdout=sample_dataset(('ellipsoid',),per_family=per_family,seed=seed+1,grid_size=grid_size)
        assert_disjoint_family_splits(all_train,holdout)
        sha=dataset_digest(all_train)
        if per_family==20 and grid_size==8 and seed in M3_FROZEN_SHA and sha!=M3_FROZEN_SHA[seed]:
            raise AssertionError('frozen M3 training dataset SHA mismatch')
        train,val,split=split_by_geometry(all_train,seed,
                                           validation_geometries_per_family=max(1,per_family//5))
        model=make_model('lite_m7_tau012',seed,grid_size=grid_size)
        trained=train_early_stop(model,'lite_m7_tau012',train,val,seed=seed,
                                 steps=max_steps,derivative_enhanced=True)
        probes=external_ellipsoid_queries(holdout,seed=seed)
        assert not ({m['geometry_id'] for m in all_train[4]} & set(probes['geometry_ids']))
        res=evaluate_adaptation(model,probes,ridge=ridge,max_iterations=iterations)
        report['cases'].append({'seed':seed,'train_dataset_sha256':sha,
                 'train_validation_split':split,'trained':trained,
                 'heldout_geometry_sha256':dataset_digest(holdout),
                 'heldout_geometry_ids':probes['geometry_ids'],
                 'support_and_target_h':probes['support_eval_cut_ledger'],
                 'query_counts':res})
    for k in (0,1,2):
        data=[case['query_counts'][str(k)] for case in report['cases']]
        report['aggregate'][str(k)]={}
        for metric in ('r_mae','J_mae','directional_derivative_mae',
                       'necessary_condition_pass_fraction','fit_wall_seconds_total',
                       'support_mse_after_mean','support_mass_exceeds_sampled_capacity_count'):
            vals=[float(v[metric]) for v in data]
            report['aggregate'][str(k)][metric]={
                'mean':statistics.mean(vals),'sd':statistics.stdev(vals) if len(vals)>1 else None,
                'per_seed':dict(zip(map(str,seeds),vals))}
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--seeds',default='19,23,29')
    p.add_argument('--steps',type=int,default=400)
    p.add_argument('--per-family',type=int,default=20)
    p.add_argument('--grid-size',type=int,default=8)
    p.add_argument('--ridge',type=float,default=1e-4)
    p.add_argument('--iterations',type=int,default=5)
    p.add_argument('--output',required=True)
    a=p.parse_args()
    report=run(seeds=tuple(map(int,a.seeds.split(','))),max_steps=a.steps,
         per_family=a.per_family,grid_size=a.grid_size,ridge=a.ridge,iterations=a.iterations)
    with open(a.output,'w',encoding='utf8') as f:json.dump(report,f,indent=2,allow_nan=False)
    print(json.dumps({'output':a.output,'aggregate':{
        k:{m:round(v['mean'],8) for m,v in values.items()}
        for k,values in report['aggregate'].items()}},ensure_ascii=False))

if __name__=='__main__':main()
