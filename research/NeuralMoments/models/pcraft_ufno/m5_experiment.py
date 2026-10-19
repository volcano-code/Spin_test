"""W6 M5 convex-potential comparison: same W0 physical-cut analytic P0 dataset.

python -m research.NeuralMoments.models.pcraft_ufno.m5_experiment \
    --seeds 19,23,29 --steps 100 --output /path/to/m5_three_seed_cpu.json

Genuine W2 Cherchi training is forbidden until its independently sealed
native labels and frozen W0 semantic validator are available. All numerical
metrics below are for analytic P0, not real CAD or Faster acceleration.
"""
from __future__ import annotations

import argparse
import json
import math
import platform
import statistics
import time

import torch

from .m5_potential import ConvexPotentialMoment
from .m4_lite_model import num_real_parameters
from .m4_experiment import (
    dataset_digest, encoded, latency, make_model as make_m4_model, metrics,
    split_by_geometry, train_early_stop)
from .analytic_cut import sample_dataset, assert_disjoint_family_splits

NAMES = ('lite_potential_4', 'lite_potential_6', 'lite_potential_8',
         'lite_bottleneck', 'w5_deeponet', 'w5_geometry_mlp')
CONFIG = {
    'lite_potential_4': dict(points_per_axis=4, hidden=60, smoothing=.04),
    'lite_potential_6': dict(points_per_axis=6, hidden=32, smoothing=.04),
    'lite_potential_8': dict(points_per_axis=8, hidden=16, smoothing=.04),
}
ORACLE_KIND = 'ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI'


def create_model(name: str, seed: int, grid_size: int = 8) -> torch.nn.Module:
    if name in CONFIG:
        torch.manual_seed(seed)
        return ConvexPotentialMoment(variant='bottleneck',grid_size=grid_size,
                                     **CONFIG[name])
    return make_m4_model(name,seed,grid_size)


def structural_diagnostic(model, name, D, c):
    """Descriptive; exact PSD is certified only by the M5 model construction."""
    z=encoded(model,name,D)
    J=model.jacobian(z.detach(),c)
    B=torch.as_tensor([1.]*7+[2.]*3,dtype=J.dtype,device=J.device)
    H=J/B[None,None,:]
    symmetry=(H-H.transpose(-1,-2)).abs().amax()
    min_eig=torch.linalg.eigvalsh((H+H.transpose(-1,-2))/2).amin()
    # Gradient of synthetic quadratic objective F(c)=||r_D(c)||²/2, *not*
    # a real Spin Newton objective. Avoid M3's saturated/trust-radius steps.
    with torch.no_grad():
        r=model.moment(z,c)
    return {'Jq_max_asymmetry':float(symmetry.detach()),
            'Jq_min_symmetric_eigenvalue':float(min_eig.detach()),
            'Jc_radial_max':float(torch.bmm(J,c.unsqueeze(-1)).abs().amax().detach()),
            'predicted_quadratic_objective_gradient_norm_mean':float(torch.bmm(J.transpose(1,2),r.unsqueeze(-1)).squeeze(-1).norm(dim=-1).mean().detach())}


def report_run(*, seeds=(19,23,29), steps=100, per_family=20, grid_size=8,
               repeats=7, names=NAMES, derivative_enhanced=True):
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    seeds=tuple(int(s) for s in seeds)
    names=tuple(names)
    if not seeds or len(set(seeds))!=len(seeds) or not names or len(set(names))!=len(names):
        raise ValueError('nonempty unique seeds and model list required')
    if steps<1 or per_family<2 or repeats<1:
        raise ValueError('positive budget and per-family>=2 required')
    num_params={name:num_real_parameters(create_model(name,seeds[0],grid_size)) for name in names}
    if max(num_params.values())/min(num_params.values())>1.05:
        raise ValueError('parameter capacity differs by >5%')
    report={
        'schema':'W6_M5_CONVEX_POTENTIAL_ANALYTIC_V1',
        'status':'ANALYTIC_P0_ONLY_NOT_NATIVE_CHERCHI',
        'W2_real_teacher_samples':0,
        'W0_native_coefficient_order':['const','x','y','z','xx','yy','zz','yz','xz','xy'],
        'W0_raw_moment_order':['M','Lx','Ly','Lz','Qxx','Qyy','Qzz','Qyz','Qxz','Qxy'],
        'B_diagonal':[1]*7+[2]*3,
        'retained_side':'beta_c(x)>=0',
        'Jq_symmetry_applicability':'smooth full-ambient continuum cuts ONLY',
        'oracle_kind':ORACLE_KIND,
        'seeds':seeds,'models':names,'parameter_counts_real':num_params,
        'train_families':['box','sphere'],'test_families':['ellipsoid'],
        'unique_train_geometry_and_validation_split':True,
        'feature_parity':False,
        'W5_features':'9D lossy voxel descriptors',
        'W6_features':'4 channel voxels with same label-independent summary',
        'teacher_calls_per_seed':{'analytic_total_train':per_family*2*2,
                                  'analytic_heldout':per_family*2,
                                  'real_Cherchi':0},
        'optimizer':'Adam 0.003','batch_size':8,'max_steps':steps,
        'validation_early_stop':'r_mae+0.25*J_mae every 10 steps, patience 5',
        'derivative_enhanced':derivative_enhanced,
        'training_objective':'MSE(r)+0.5*MSE(J)' if derivative_enhanced else 'MSE(r)',
        'runtime':{'device':'cpu','threads':1,'torch':torch.__version__,
                   'python':platform.python_version(),'gpu_time_hours':0.0},
        'experiments':[], 'aggregate':{}
    }
    for seed in seeds:
        train_all=sample_dataset(('box','sphere'),per_family=per_family,seed=seed,
                                 grid_size=grid_size)
        test=sample_dataset(('ellipsoid',),per_family=per_family,seed=seed+1,
                            grid_size=grid_size)
        assert_disjoint_family_splits(train_all,test)
        train,valid,manifest=split_by_geometry(train_all,seed,
                             validation_geometries_per_family=max(1,per_family//5))
        if {m['geometry_id'] for m in valid[4]} & {m['geometry_id'] for m in train[4]}:
            raise RuntimeError('training/validation CAD identity leakage')
        case={'seed':seed,'train_dataset_sha256':dataset_digest(train_all),
              'heldout_dataset_sha256':dataset_digest(test),
              'split':manifest,'models':{}}
        for name in names:
            model=create_model(name,seed,grid_size)
            t=time.perf_counter()
            trained=train_early_stop(model,name,train,valid,seed=seed,steps=steps,
                                     batch=8,eval_every=10,patience=5,
                                     derivative_enhanced=derivative_enhanced)
            elapsed=time.perf_counter()-t
            heldout=metrics(model,name,test)
            diagnostic=structural_diagnostic(model,name,test[0],test[1])
            timing=latency(model,name,test[0][0],test[1][0],repetitions=repeats)
            case['models'][name]={
                'training':trained,'heldout':heldout,'structure':diagnostic,
                'timing':timing,'elapsed_train_validation_seconds':elapsed,
                'real_parameters':num_params[name]
            }
        report['experiments'].append(case)
    for name in names:
        experiments=[x['models'][name] for x in report['experiments']]
        keys={'r_mae':lambda item:item['heldout']['r_mae'],
              'J_mae':lambda item:item['heldout']['J_mae'],
              'directional_mae':lambda item:item['heldout']['directional_mae'],
              'Jq_max_asymmetry':lambda item:item['structure']['Jq_max_asymmetry'],
              'Jq_min_eig':lambda item:item['structure']['Jq_min_symmetric_eigenvalue']}
        row={}
        for label,func in keys.items():
            values=[func(x) for x in experiments]
            row[label]={'mean':statistics.mean(values),
                        'sample_sd':statistics.stdev(values) if len(values)>1 else None,
                        'per_seed':dict(zip(map(str,seeds),values))}
        row['selected_steps']=[x['training']['steps_selected'] for x in experiments]
        row['median_cold_ms']=statistics.median(x['timing']['cold_voxel_to_head']['median_ms'] for x in experiments)
        row['median_cached_J_ms']=statistics.median(x['timing']['cached_J10x10']['median_ms'] for x in experiments)
        report['aggregate'][name]=row
    return report


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--seeds',default='19,23,29')
    ap.add_argument('--steps',type=int,default=100)
    ap.add_argument('--per-family',type=int,default=20)
    ap.add_argument('--grid-size',type=int,default=8)
    ap.add_argument('--repeats',type=int,default=7)
    ap.add_argument('--names',default=','.join(NAMES))
    ap.add_argument('--moment-only',action='store_true')
    ap.add_argument('--output',default=None)
    a=ap.parse_args()
    result=report_run(seeds=tuple(map(int,a.seeds.split(','))),steps=a.steps,
                      per_family=a.per_family,grid_size=a.grid_size,
                      repeats=a.repeats,names=tuple(a.names.split(',')),
                      derivative_enhanced=not a.moment_only)
    text=json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)
    if a.output:
        with open(a.output,'w',encoding='utf-8') as stream:stream.write(text+'\n')
    print(text)


if __name__=='__main__':main()
