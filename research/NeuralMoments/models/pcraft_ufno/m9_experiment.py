"""W6 M9 P0 geometry capacity and bounded-atom few-shot resolution study.

Usage: python -m research.NeuralMoments.models.pcraft_ufno.m9_experiment
 --seeds 19,23,29 --per-family 20 --resolutions 8,16,24 --depth 2
 --output /tmp/m9_p0_capacity.json

This is a *geometry-privileged*, TRAINING-FREE quadrature diagnostic: the
analytic shape specification is available to m9_antialias. It does NOT mean
one can recover off-grid occupancy from the legacy M8 binary D8 alone. Only
independent analytic_cut.vertical_cut_truth supplies cut r/J labels; it is
never read by geometry reconstruction. No W2 samples are admitted.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import platform
import resource
import statistics
import time
import numpy as np
import torch
from .analytic_cut import GeometrySpec, vertical_cut_truth, sample_dataset
from .m4_experiment import dataset_digest
from .m7_experiment import M3_FROZEN_SHA
from .m6_moment_guard import physical_moment_diagnostic
from .m9_antialias import PrimitiveP0,sample_capacity,baseline_point_sample_mass
from .m9_bounded_atoms import BoundedCellMoment

W0_ORDER='M,LX,LY,LZ,QXX,QYY,QZZ,QYZ,QXZ,QXY'
SOURCE='ANALYTIC_P0_CUT_NOT_W2_NATIVE'


def heldout_case_list(seed:int, count:int, eval_queries:int=8):
    """Reconstruct EXACT M8 geometry/spec and disjoint support/eval RNG streams."""
    geometry_rng=np.random.default_rng(seed+1)
    support_rng=np.random.default_rng(seed+811)
    target_rng=np.random.default_rng(seed+2701)
    for i in range(count):
        center=tuple(float(x) for x in geometry_rng.uniform(-.1,.1,3))
        axes0=tuple(float(x) for x in geometry_rng.uniform(.46,.73,3))
        axes=(axes0[0],axes0[1]*.8,axes0[2]*1.1)
        _=geometry_rng.uniform(-.65,.65,2)  # frozen original heldout controls
        spec=GeometrySpec('ellipsoid',center,axes)
        source=PrimitiveP0('ellipsoid',center,axes)
        hs=tuple(float(x) for x in support_rng.uniform(-.55,.55,2))
        ht=tuple(float(x) for x in target_rng.uniform(-.55,.55,eval_queries))
        if set(hs)&set(ht):raise AssertionError('support/target controls collided')
        support=[vertical_cut_truth(spec,h) for h in hs]
        target=[vertical_cut_truth(spec,h) for h in ht]
        yield {'geometry_id':spec.geometry_id,'source':source,'support_h':hs,'eval_h':ht,
               'support_c':torch.from_numpy(np.stack([x[0] for x in support])).double(),
               'support_r':torch.from_numpy(np.stack([x[1] for x in support])).double(),
               'eval_c':torch.from_numpy(np.stack([x[0] for x in target])).double(),
               'eval_r':torch.from_numpy(np.stack([x[1] for x in target])).double(),
               'eval_J':torch.from_numpy(np.stack([x[2] for x in target])).double()}


def _aggregate(numbers:list[float])->dict:
    return {'mean':float(statistics.mean(numbers)),
            'sample_sd':float(statistics.stdev(numbers)) if len(numbers)>1 else None,
            'min':float(min(numbers)),'max':float(max(numbers))}


def run(*,seeds=(19,23,29),per_family=20,resolutions=(8,16,24),depth=2,
        eval_queries=8,ridge=1e-4,temperature=.12)->dict:
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    seeds=tuple(int(s) for s in seeds)
    resolutions=tuple(int(r) for r in resolutions)
    if not seeds or len(set(seeds))!=len(seeds) or not resolutions or any(r<4 for r in resolutions):
        raise ValueError('seed/resolutions required and unique')
    if per_family<1 or eval_queries<1:
        raise ValueError('positive geometry and evaluation budget required')
    report={'schema':'W6_M9_GEOMETRY_CAPACITY_P0_V1','status':'ANALYTIC_GEOMETRY_PRIVILEGED_NOT_NATIVE_TEACHER',
        'claim':'cell-fraction estimates with interval bounds; nonnegative atom moment, NOT CAD cert',
        'source':'frozen W6 M3/M8 analytic ellipsoid geometry + independent vertical_cut_truth',
        'seed_list':seeds,'heldout_geometry_per_seed':per_family,'eval_queries_per_geometry':eval_queries,
        'supports':[0,1,2],'resolutions':resolutions,'refinement_depth':depth,
        'source_geometry_extra_information':'analytic primitive center/axes, unavailable from legacy D8-only inputs',
        'neural_training':'NONE, neutral frozen gate 0.5 across all resolutions (NOT trained W6/W5)',
        'teacher_kind':SOURCE,'W2_admitted_labels':0,'W2_excluded_historical_81':'NEVER_USED',
        'W0_raw_r_order':W0_ORDER,'W0_native_B_diag':[1]*7+[2]*3,
        'surrogate_J':'normalized sigmoid discrete Jacobian, not Cherchi derivative',
        'cuda_hours':0.,'device':'cpu','torch':torch.__version__,'python':platform.python_version(),
        'samples':[],'aggregate':{}}
    for seed in seeds:
        # Check that the M9 generator shares exactly the M8 held-out geometry
        # families / frozen M3 train tensor stream.
        train=sample_dataset(('box','sphere'),per_family=20,seed=seed,grid_size=8)
        frozen_sha=dataset_digest(train)
        if seed in M3_FROZEN_SHA and frozen_sha!=M3_FROZEN_SHA[seed]:
            raise AssertionError('frozen M3 original training samples changed')
        cases=list(heldout_case_list(seed,per_family,eval_queries))
        if per_family==20:
            holdout=sample_dataset(('ellipsoid',),per_family=20,seed=seed+1,grid_size=8)
            expected=[holdout[4][2*i]['geometry_id'] for i in range(20)]
            assert [case['geometry_id'] for case in cases]==expected, 'M8 family/identity mismatch'
        for case in cases:
            shape=case['source']
            old_cap=baseline_point_sample_mass(shape,resolution=8)
            old_flag=[bool(float(case['support_r'][:k,0].max())>old_cap+1e-6) if k else False
                      for k in (0,1,2)]
            for n in resolutions:
                start=time.perf_counter()
                grid=sample_capacity(shape,resolution=n,refinement_depth=depth)
                sample_time=time.perf_counter()-start
                lo,hi=grid.mass_bracket
                truth=shape.true_full_mass
                if not lo-1e-8 <= truth <= hi+1e-8:
                    raise AssertionError('analytic ellipsoid mass escaped numerical interval bracket')
                model=BoundedCellMoment(grid,temperature=temperature)
                results={}
                for k in (0,1,2):
                    # Each K gets IDENTICAL independent neutral initial weights.
                    model.weights=(grid.estimated_capacity*.5).clone()
                    started=time.perf_counter()
                    audit=model.fit(case['support_c'][:k],case['support_r'][:k],source='ANALYTIC_P0',ridge=ridge)
                    fit_seconds=time.perf_counter()-started
                    predicted=model.moment(case['eval_c'])
                    derivative=model.jacobian(case['eval_c'])
                    gate=physical_moment_diagnostic(predicted,tol=1e-7)
                    if not bool(gate['necessary_conditions_pass'].all()):
                        raise AssertionError('nonnegative atomic moment failed moment feasibility')
                    if bool((model.weights<0).any() or (model.weights>grid.estimated_capacity+1e-12).any()):
                        raise AssertionError('adapter violated nonnegative capacity constraint')
                    results[str(k)]={'r_mae':float((predicted-case['eval_r']).abs().mean()),
                        'J_mae':float((derivative-case['eval_J']).abs().mean()),
                        'directional_mae':float(((derivative-case['eval_J']) @
                           (torch.arange(1,11,dtype=torch.float64)/torch.arange(1,11,dtype=torch.float64).norm())).abs().mean()),
                        'support_loss_before':audit.loss_before,'support_loss_after':audit.loss_after,
                        'support_mass_exceeds_capacity':audit.support_mass_exceeds_estimated_capacity,
                        'necessary_condition_pass_fraction':float(gate['necessary_conditions_pass'].float().mean()),
                        'fit_seconds':fit_seconds,'supports':k}
                report['samples'].append({'seed':seed,'geometry_id':case['geometry_id'],
                    'resolution':n,'interval_depth':depth,'true_full_mass':truth,
                    'legacy_binary_point_Gauss6_mass':old_cap,'legacy_over_capacity_supports':old_flag,
                    'sampled_capacity_mass':grid.estimated_mass,'lower_interval_mass':lo,
                    'upper_interval_mass':hi,'unresolved_subcells':grid.uncertain_subcells,
                    'relative_full_mass_error':abs(grid.estimated_mass-truth)/truth,
                    'relative_interval_width':(hi-lo)/truth,'geometry_sampling_seconds':sample_time,
                    'query_counts':results})
    for n in resolutions:
        subset=[x for x in report['samples'] if x['resolution']==n]
        metrics={'relative_full_mass_error':[s['relative_full_mass_error'] for s in subset],
                 'relative_interval_width':[s['relative_interval_width'] for s in subset],
                 'sampling_seconds':[s['geometry_sampling_seconds'] for s in subset],
                 'legacy_mass_relative_error':[abs(s['legacy_binary_point_Gauss6_mass']-s['true_full_mass'])/s['true_full_mass'] for s in subset]}
        report['aggregate'][str(n)]={key:_aggregate(vals) for key,vals in metrics.items()}
        report['aggregate'][str(n)]['query_counts']={}
        for k in (0,1,2):
            rows=[s['query_counts'][str(k)] for s in subset]
            report['aggregate'][str(n)]['query_counts'][str(k)]={key:_aggregate([float(row[key]) for row in rows])
                    for key in ('r_mae','J_mae','directional_mae','necessary_condition_pass_fraction','fit_seconds')}
            report['aggregate'][str(n)]['query_counts'][str(k)]['support_over_capacity_count']=sum(row['support_mass_exceeds_capacity'] for row in rows)
            report['aggregate'][str(n)]['query_counts'][str(k)]['legacy_support_over_capacity_count']=sum(s['legacy_over_capacity_supports'][k] for s in subset)
    report['cpu_process_peak_rss_kb']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    report['limitations']=[
         'Analytic primitive shape identity not inferable from M8 8^3 binary input',
         'Interval floating-point bounds are numerical, not exact rational CAD proof',
         'Continuum labels vs discrete atomic approximations; no trained neural checkpoints',
         '0/1/2 support fit cannot be guaranteed to improve unseen r/J',
         'Smooth normalized-sigmoid surrogate J does not certify W0 native smooth-stratum',
         'No real W2 admitted labels or Cherchi/GPU/Newton timing']
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seeds',default='19,23,29')
    p.add_argument('--per-family',type=int,default=20)
    p.add_argument('--resolutions',default='8,16,24')
    p.add_argument('--depth',type=int,default=2)
    p.add_argument('--eval-queries',type=int,default=8)
    p.add_argument('--output',required=True)
    a=p.parse_args()
    r=run(seeds=tuple(map(int,a.seeds.split(','))),per_family=a.per_family,
          resolutions=tuple(map(int,a.resolutions.split(','))),depth=a.depth,
          eval_queries=a.eval_queries)
    with open(a.output,'w',encoding='utf-8') as out:json.dump(r,out,indent=2,allow_nan=False)
    print(json.dumps({'output':a.output,'summary':{
        n:{'capacity_relative_err':v['relative_full_mass_error']['mean'],
          'r_mae_k0':v['query_counts']['0']['r_mae']['mean'],
          'r_mae_k1':v['query_counts']['1']['r_mae']['mean'],
          'r_mae_k2':v['query_counts']['2']['r_mae']['mean'],
          'support_overcapacity_k2':v['query_counts']['2']['support_over_capacity_count']}
          for n,v in r['aggregate'].items()}},ensure_ascii=False))
if __name__=='__main__':main()
