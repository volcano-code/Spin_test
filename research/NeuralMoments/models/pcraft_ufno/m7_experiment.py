"""M7 paired analytic-P0 comparison: discrete realizability vs M6/M5/W5.

The W2 excluded H8f historical records are NOT labels for this experiment.
Native optimizer speed, Boolean material validity, held-out CAD or Newton
convergence are not measured. No input/architecture parity claim with W5.

Run from repository root:
 python -m research.NeuralMoments.models.pcraft_ufno.m7_experiment \
  --seeds 19,23,29 --steps 400 --output report.json
"""
from __future__ import annotations
import argparse
import json
import platform
import statistics
import time

import torch

from .m7_realizable import RealizableUFNOMoment
from .m6_gauss_potential import GaussPotentialMoment
from .m4_lite_model import num_real_parameters
from .m4_experiment import (dataset_digest,split_by_geometry,train_early_stop,
                             metrics,latency,encoded,make_model as make_m4_model)
from .analytic_cut import sample_dataset,assert_disjoint_family_splits
from .m6_moment_guard import physical_moment_diagnostic

M3_FROZEN_SHA={
 19:'7b65ebbb3e5d32e82ff7ee23a1f88978fa4100902b67f63e16b0fdc2df54e087',
 23:'d36d707cbf7ecdd0089f66fea3f8784a200830f09a2e0b5a60790ce6028562e7',
 29:'25eece482d68d864064bfcc7785226785afc41307f56978f2f027ba4ac838394'}
W0_OBSERVED_SHA='64fa50ca171bc8e964edc5ded5e0b967cbbdb0a8'
W2_OBSERVED_SHA='36eb96a0abac1e1b6620264ac79b83f3345bbcb4'
OPTIONS={
 'lite_m7_tau012':('m7',.12),
 'lite_m7_tau025':('m7',.25),
 'lite_m6_gauss025':('m6',.25),
 'w5_deeponet':('w5',None),
}


def make_model(name,seed,grid_size=8,points_per_axis=6):
    if name not in OPTIONS:raise ValueError('unsupported model name')
    kind,param=OPTIONS[name]
    torch.manual_seed(seed)
    if kind=='m7':return RealizableUFNOMoment(rule='gauss',grid_size=grid_size,
                   points_per_axis=points_per_axis,hidden=32,temperature=param)
    if kind=='m6':return GaussPotentialMoment(rule='gauss',grid_size=grid_size,
                   points_per_axis=points_per_axis,hidden=32,smoothing=param)
    return make_m4_model(name,seed,grid_size)


def fraction_feasible(model,name,data):
    D,c,_,_,_=data
    with torch.no_grad():
        z=encoded(model,name,D)
        r=model.moment(z,c)
        return float(physical_moment_diagnostic(r,tol=1e-6)['necessary_conditions_pass'].float().mean())


def tangent_diagnostics(model,name,data):
    D,c,_,_,_=data
    if not isinstance(model,RealizableUFNOMoment):return None
    with torch.no_grad():
        z=encoded(model,name,D)
        J=model.jacobian(z,c)
        Jq=J / model.native_B.to(dtype=J.dtype)
        projected=model.projected_q_gram(z,c)
        tangent,basis=model.tangent_jacobian(z,c)
        return {'ambient_Jq_max_asymmetry':float((Jq-Jq.transpose(-1,-2)).abs().max()),
                'tangent_projected_Jq_max_asymmetry':float((projected-projected.transpose(-1,-2)).abs().max()),
                'tangent_projected_min_eigenvalue':float(torch.linalg.eigvalsh((projected+projected.transpose(-1,-2))/2).min()),
                'tangent_basis_max_orthogonality_error':float(torch.bmm(basis.transpose(1,2),c.unsqueeze(-1)).abs().max()),
                'tangent_J_shape':list(tangent.shape),
                'real_native_smooth_ambient_Hessian_verified':False}


def run(*,seeds=(19,23,29),steps=400,per_family=20,grid_size=8,repeats=5,
        names=('lite_m7_tau012','lite_m7_tau025','lite_m6_gauss025','w5_deeponet'),
        derivative_enhanced=True):
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    seeds=tuple(int(s) for s in seeds)
    names=tuple(names)
    if not seeds or len(set(seeds))!=len(seeds) or not names or len(set(names))!=len(names):
        raise ValueError('unique nonempty seeds/models required')
    if steps<1 or per_family<3 or repeats<1:raise ValueError('invalid training/test protocol')
    params={n:num_real_parameters(make_model(n,seeds[0],grid_size)) for n in names}
    if max(params.values())/min(params.values())>1.05:raise ValueError('model parameter budget >5%')
    report={
       'schema':'W6_M7_DISCRETE_ATOMIC_MOMENT_P0_V1',
       'status':'ANALYTIC_P0_ONLY_NATIVE_W2_ADMISSION_ZERO',
       'W0_observed_sha':W0_OBSERVED_SHA,'W2_observed_sha':W2_OBSERVED_SHA,
       'W2_native_training_samples':0,'W2_excluded_historical_candidates':81,
       'c':'native [const,x,y,z,xx,yy,zz,yz,xz,xy]','r':'undoubled raw r10',
       'B_diag':[1]*7+[2]*3,'positive_projective_only':True,
       'teacher':'Independent continuum plane-cut formulas, not real Cherchi/native mesh',
       'data_policy':'same frozen M3 geometry identities and oracle labels',
       'train_families':['box','sphere'],'heldout':['ellipsoid'],
       'geometry_split':'per-geometry train-val; no heldout family seen during model selection',
       'representation_parity_W5':False,'architecture_parity_W5':False,
       'physics':'M7 atomic moment realization on sampled grid, tangent-only structural PSD; NOT original CAD proof',
       'max_steps':steps,'optimizer':'Adam lr0.003 batch8',
       'derivative_loss':('MSE(r)+0.5*MSE(J_native_smooth_surrogate)' if derivative_enhanced else 'MSE(r)'),
       'validation':'r_mae + 0.25 J_mae, patience 5, every 10 steps',
       'seeds':list(seeds),'models':list(names),'parameters_real':params,
       'cpu_threads':torch.get_num_threads(),'torch':torch.__version__,
       'python':platform.python_version(),'GPU_hours':0,'native_evaluations':0,
       'cases':[],'aggregate':{}}
    for seed in seeds:
        source=sample_dataset(('box','sphere'),per_family=per_family,seed=seed,grid_size=grid_size)
        held=sample_dataset(('ellipsoid',),per_family=per_family,seed=seed+1,grid_size=grid_size)
        assert_disjoint_family_splits(source,held)
        full_sha=dataset_digest(source)
        if per_family==20 and grid_size==8 and seed in M3_FROZEN_SHA and full_sha!=M3_FROZEN_SHA[seed]:
            raise RuntimeError('M3 analytic dataset checksum mismatch')
        train,validation,split=split_by_geometry(source,seed,validation_geometries_per_family=max(1,per_family//5))
        case={'seed':seed,'frozen_training_dataset_sha256':full_sha,
              'heldout_dataset_sha256':dataset_digest(held),'split':split,'models':{}}
        for name in names:
            model=make_model(name,seed,grid_size)
            before=time.perf_counter()
            trained=train_early_stop(model,name,train,validation,seed=seed,steps=steps,
                                     derivative_enhanced=derivative_enhanced)
            elapsed=time.perf_counter()-before
            entry={'train':trained,'heldout':metrics(model,name,held),
                   'feasible_fraction':fraction_feasible(model,name,held),
                   'tangent_structure':tangent_diagnostics(model,name,held),
                   'time':latency(model,name,held[0][0],held[1][0],repetitions=repeats),
                   'fit_wall_seconds':elapsed}
            case['models'][name]=entry
        report['cases'].append(case)
    for name in names:
        values=[c['models'][name] for c in report['cases']]
        agg={}
        for key,extract in (
            ('r_mae',lambda x:x['heldout']['r_mae']),
            ('J_mae',lambda x:x['heldout']['J_mae']),
            ('directional_mae',lambda x:x['heldout']['directional_mae']),
            ('feasible_fraction',lambda x:x['feasible_fraction']),
            ('cold_ms',lambda x:x['time']['cold_voxel_to_head']['median_ms']),
            ('warm_ms',lambda x:x['time']['cached_head']['median_ms']),
            ('cached_J_ms',lambda x:x['time']['cached_J10x10']['median_ms']),
            ('fit_wall_seconds',lambda x:x['fit_wall_seconds'])
        ):
            vals=[float(extract(x)) for x in values]
            agg[key]={'mean':statistics.mean(vals),'sample_sd':statistics.stdev(vals) if len(vals)>1 else None,
                      'per_seed':dict(zip(map(str,seeds),vals))}
        agg['selected_steps']=[x['train']['steps_selected'] for x in values]
        report['aggregate'][name]=agg
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--seeds',default='19,23,29')
    p.add_argument('--steps',type=int,default=400)
    p.add_argument('--per-family',type=int,default=20)
    p.add_argument('--grid-size',type=int,default=8)
    p.add_argument('--repeats',type=int,default=5)
    p.add_argument('--models',default=','.join(OPTIONS))
    p.add_argument('--moment-only',action='store_true')
    p.add_argument('--output',required=True)
    args=p.parse_args()
    report=run(seeds=tuple(map(int,args.seeds.split(','))),steps=args.steps,
               per_family=args.per_family,grid_size=args.grid_size,
               repeats=args.repeats,names=tuple(args.models.split(',')),
               derivative_enhanced=not args.moment_only)
    with open(args.output,'w',encoding='utf-8') as f:
        json.dump(report,f,indent=2,allow_nan=False)
    print(json.dumps({'path':args.output,'aggregate':{k:{metric:round(val['mean'],7)
        for metric,val in v.items() if isinstance(val,dict) and 'mean' in val}
        for k,v in report['aggregate'].items()}},ensure_ascii=False))

if __name__=='__main__':main()
