"""M6 reproducible P0 test of Gauss integration and voxel occupancy prior.

Same frozen W6 M3/M4/M5 analytical box/sphere train and ellipsoid holdout,
exact native W0 order, and equal teacher labels/parameter budgets. This is a
local CPU *analytic-only* comparison. Never compare speed with native Cherchi.

From repository root:
    python -m research.NeuralMoments.models.pcraft_ufno.m6_experiment \
        --seeds 19,23,29 --steps 400 --output PATH
"""
from __future__ import annotations
import argparse
import json
import platform
import statistics
import time

import torch

from .m6_gauss_potential import GaussPotentialMoment
from .m6_teacher_handoff import W0_PIN, W2_PIN
from .m4_experiment import (dataset_digest, encoded, latency, metrics,
                             split_by_geometry, train_early_stop)
from .analytic_cut import sample_dataset, assert_disjoint_family_splits
from .m4_lite_model import num_real_parameters
from .m5_experiment import structural_diagnostic
from .m6_moment_guard import physical_moment_diagnostic

MODES = ('lite_m6_midpoint', 'lite_m6_gauss', 'lite_m6_gauss_prior25')
CONFIRMATORY = ('lite_m6_confirm_baseline', 'lite_m6_confirm_gauss25')
MODEL_KW = {
    'lite_m6_midpoint': dict(rule='midpoint', prior_fraction=0.0),
    'lite_m6_gauss': dict(rule='gauss', prior_fraction=0.0),
    'lite_m6_gauss_prior25': dict(rule='gauss', prior_fraction=.25),
    'lite_m6_confirm_baseline': dict(rule='midpoint', prior_fraction=0., smoothing=.04),
    'lite_m6_confirm_gauss25': dict(rule='gauss', prior_fraction=0., smoothing=.25),
}
M3_SEED_DATA_SHA = {
    19:'7b65ebbb3e5d32e82ff7ee23a1f88978fa4100902b67f63e16b0fdc2df54e087',
    23:'d36d707cbf7ecdd0089f66fea3f8784a200830f09a2e0b5a60790ce6028562e7',
    29:'25eece482d68d864064bfcc7785226785afc41307f56978f2f027ba4ac838394',
}


def make_model(name,seed,grid_size=8,smoothing=.04):
    if name not in MODEL_KW:
        raise ValueError('unknown M6 model')
    torch.manual_seed(seed)
    options=dict(MODEL_KW[name])
    options.setdefault('smoothing',smoothing)
    return GaussPotentialMoment(grid_size=grid_size,points_per_axis=6,hidden=32,
                                **options)


def gradient_decision_diagnostic(model, name, data):
    """Analytic-only || d(0.5||r||²)/dc - true gradient ||, no fake Newton step.

    NOT the Spin balance objective and NOT a solver convergence certificate.
    """
    D,c,r,J,_=data
    z=encoded(model,name,D).detach()
    with torch.no_grad():
        rr=model.moment(z,c)
        jj=model.jacobian(z,c)
        g=torch.bmm(jj.transpose(-1,-2),rr.unsqueeze(-1)).squeeze(-1)
        truth=torch.bmm(J.transpose(-1,-2),r.unsqueeze(-1)).squeeze(-1)
        residual=g-truth
        return {'quadratic_gradient_mae':float(residual.abs().mean()),
                'quadratic_gradient_relative_l2':float(residual.norm()/truth.norm().clamp_min(1e-12)),
                'quadratic_gradient_cosine_mean':float(torch.nn.functional.cosine_similarity(g,truth,dim=-1).mean()),
                'interpretation':'analytic P0 zero-reference quadratic objective only, not true Spin solver'}


def moment_support_diagnostic(model,name,data):
    """Necessary cube-support conditions; passing cannot certify geometry."""
    D,c,_,_,_=data
    model.eval()
    with torch.no_grad():
        z=encoded(model,name,D)
        prediction=model.moment(z,c)
        original=physical_moment_diagnostic(prediction)
        always_negative_c=torch.zeros_like(c)
        always_negative_c[:,0]=-1.0
        raw_for_empty_cut=model.moment(z,always_negative_c)
        empty_probe=physical_moment_diagnostic(raw_for_empty_cut)
    return {'heldout_fraction_necessary_conditions_pass':float(original['necessary_conditions_pass'].float().mean()),
            'empty_true_mass':0.0,
            'empty_negative_constant_predicted_mass_mean':float(raw_for_empty_cut[:,0].mean()),
            'empty_negative_constant_fraction_rejected':float((~empty_probe['necessary_conditions_pass']).float().mean()),
            'interpretation':'negative empty mass is a mathematical counterexample to physical realizability despite Jq PSD'}


def run(*,seeds=(19,23,29),steps=400,per_family=20,grid_size=8,
        repeats=7,names=MODES,derivative_enhanced=True,smoothing=.04):
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    seeds=tuple(int(s) for s in seeds)
    names=tuple(names)
    if not seeds or len(set(seeds))!=len(seeds) or not names or len(set(names))!=len(names):
        raise ValueError('nonempty unique seeds and models required')
    if steps<1 or per_family<3 or repeats<1:
        raise ValueError('positive step/repeat budget and per_family>=3 required')
    params={n:num_real_parameters(make_model(n,seeds[0],grid_size,smoothing)) for n in names}
    if max(params.values())/min(params.values())>1.05:
        raise ValueError('parameter counts differ by >5%')
    result={'schema':'W6_M6_GAUSS_POTENTIAL_ANALYTIC_P0_V1',
        'status':'ANALYTIC_ONLY_NON_NATIVE_W2_NOT_ADMITTED',
        'W0_branch_pin':W0_PIN,'W2_branch_pin':W2_PIN,
        'W2_native_teacher_samples':0,'native_evaluator_runs_by_W6':0,
        'teacher':'independent continuum analytic vertical-plane cut, NOT W2',
        'c_order':'const,x,y,z,xx,yy,zz,yz,xz,xy',
        'r_order':'M,LX,LY,LZ,QXX,QYY,QZZ,QYZ,QXZ,QXY',
        'q_equals_Bc':True,'B_diag':[1]*7+[2]*3,
        'positive_projective_only':True,'retained_side':'beta(x)>=0',
        'names':names,'seeds':seeds,'parameters_real':params,
        'data':'train 20 boxes + 20 spheres; heldout 20 ellipsoids, 2 cuts per geometry',
        'feature_parity_with_W5':False,
        'grid_size':grid_size,'smoothing_default':smoothing,
        'smoothing_by_model':{name:MODEL_KW[name].get('smoothing',smoothing) for name in names},
        'training_steps_max':steps,'validation':'group by geometry_id within box/sphere; choose best r_mae+0.25 J_mae; patience 5',
        'batch_size':8,'optimizer':'Adam lr=0.003',
        'derivative_enhanced':derivative_enhanced,'cpu_threads':torch.get_num_threads(),
        'platform':platform.python_version(),'torch':torch.__version__,
        'GPU_hours':0.0,'experiments':[],'aggregate':{}}
    for seed in seeds:
        train_all=sample_dataset(('box','sphere'),per_family=per_family,seed=seed,grid_size=grid_size)
        heldout=sample_dataset(('ellipsoid',),per_family=per_family,seed=seed+1,grid_size=grid_size)
        assert_disjoint_family_splits(train_all,heldout)
        train,valid,split=split_by_geometry(train_all,seed,validation_geometries_per_family=max(1,per_family//5))
        if per_family==20 and grid_size==8 and seed in M3_SEED_DATA_SHA and dataset_digest(train_all)!=M3_SEED_DATA_SHA[seed]:
            raise RuntimeError('frozen M3 dataset hash differs; no silent dataset swap')
        record={'seed':seed,'train_dataset_sha256':dataset_digest(train_all),
                'heldout_dataset_sha256':dataset_digest(heldout),'split':split,'models':{}}
        for name in names:
            model=make_model(name,seed,grid_size,smoothing)
            start=time.perf_counter()
            training=train_early_stop(model,name,train,valid,seed=seed,steps=steps,
                                       derivative_enhanced=derivative_enhanced,batch=8,
                                       eval_every=10,patience=5)
            elapsed=time.perf_counter()-start
            record['models'][name]={
                'training':training,
                'heldout':metrics(model,name,heldout),
                'structure':structural_diagnostic(model,name,heldout[0],heldout[1]),
                'gradient_diagnostic':gradient_decision_diagnostic(model,name,heldout),
                'moment_support_diagnostic':moment_support_diagnostic(model,name,heldout),
                'timings':latency(model,name,heldout[0][0],heldout[1][0],repetitions=repeats),
                'total_fit_seconds':elapsed}
        result['experiments'].append(record)
    for name in names:
        samples=[ex['models'][name] for ex in result['experiments']]
        stats={}
        for key,extract in (
            ('r_mae',lambda x:x['heldout']['r_mae']),
            ('J_mae',lambda x:x['heldout']['J_mae']),
            ('directional_mae',lambda x:x['heldout']['directional_mae']),
            ('Jq_asymmetry',lambda x:x['structure']['Jq_max_asymmetry']),
            ('Jq_min_eig',lambda x:x['structure']['Jq_min_symmetric_eigenvalue']),
            ('quadratic_gradient_mae',lambda x:x['gradient_diagnostic']['quadratic_gradient_mae']),
            ('heldout_necessary_conditions_fraction',lambda x:x['moment_support_diagnostic']['heldout_fraction_necessary_conditions_pass']),
            ('empty_mass_predicted',lambda x:x['moment_support_diagnostic']['empty_negative_constant_predicted_mass_mean']),
            ('cold_ms',lambda x:x['timings']['cold_voxel_to_head']['median_ms']),
            ('cached_J_ms',lambda x:x['timings']['cached_J10x10']['median_ms']),
            ('train_seconds',lambda x:x['total_fit_seconds'])
        ):
            vals=[float(extract(x)) for x in samples]
            stats[key]={'mean':statistics.mean(vals),'sample_sd':statistics.stdev(vals) if len(vals)>1 else None,
                        'per_seed':dict(zip(map(str,seeds),vals))}
        stats['selected_steps']=[x['training']['steps_selected'] for x in samples]
        result['aggregate'][name]=stats
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--seeds',default='19,23,29')
    parser.add_argument('--steps',type=int,default=400)
    parser.add_argument('--per-family',type=int,default=20)
    parser.add_argument('--grid-size',type=int,default=8)
    parser.add_argument('--repeats',type=int,default=7)
    parser.add_argument('--names',default=','.join(MODES))
    parser.add_argument('--moment-only',action='store_true')
    parser.add_argument('--smoothing',type=float,default=.04)
    parser.add_argument('--output',default=None)
    args=parser.parse_args()
    report=run(seeds=tuple(map(int,args.seeds.split(','))),steps=args.steps,
               per_family=args.per_family,grid_size=args.grid_size,
               repeats=args.repeats,names=tuple(args.names.split(',')),
               derivative_enhanced=not args.moment_only,smoothing=args.smoothing)
    s=json.dumps(report,sort_keys=True,indent=2,allow_nan=False)
    if args.output:
        with open(args.output,'w',encoding='utf-8') as f:f.write(s+'\n')
    print(s)


if __name__=='__main__':
    main()
