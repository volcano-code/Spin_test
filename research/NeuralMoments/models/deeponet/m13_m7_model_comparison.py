"""W5 M13 new-seed matched W6-M7-vs-W5 training with centered-cell input.

Actual W6 M7 source is SHA-checked and loaded from an external readonly mirror.
Every trainable model sees exactly identical [rho,occ,level,proximity]
center-cell tensors and exact analytic P0 r/J, same geometry-family split,
seeded minibatches, validation-only selection, Adam and CPU budget. The
nontrainable cell-volume integral is listed separately, not passed off as a
capacity-matched neural model or exact continuum native teacher.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import statistics

import numpy as np
import torch

from .m8_analytic_data import Shape, dataset,sha_dataset, independent_family_check
from .m8_fair_benchmark import (model_for,real_parameters,split_fit_validation,
    train,metrics,latency,truth_decision_metrics)
from .m9_readonly_w6 import load_m9_w6
from .m10_positive_quadrature import PositiveQuadratureMoment
from .m13_w6_m7_probe import load_w6_m7,W6_M7_COMMIT,W6_M7_FILES
from .m13_resolution_benchmark import center_cell_voxel

MODEL_NAMES=('w5_deeponet_centered','w5_positive_measure_centered','w6_realizable_m7_centered')


def centered_dataset(families, *, per_family:int,seed:int,queries:int=2):
    old=dataset(families,per_family=per_family,seed=seed,grid_size=8,queries=queries)
    voxel=[]
    for x in old[4]:
        shape_dict=x['shape']; shape=Shape(x['family'],tuple(shape_dict['center']),
                                           tuple(shape_dict['axes']),shape_dict['density'])
        if shape.identity!=x['geometry_id']:
            raise ValueError('unverified geometry ID')
        voxel.append(torch.from_numpy(center_cell_voxel(shape,8)))
    return (torch.stack(voxel),old[1],old[2],old[3],old[4])


def build_model(name,seed,libs):
    (m4,m5,m6,guard,m7)=libs
    torch.manual_seed(seed)
    if name=='w5_deeponet_centered':
        return model_for('w5_deeponet_voxel',seed,(m4,m5))
    if name=='w5_positive_measure_centered':
        enc=m6.GaussPotentialMoment(rule='gauss',grid_size=8,
                                    points_per_axis=6,hidden=32,smoothing=.04)
        return PositiveQuadratureMoment(enc,smoothing=.12,certify_cube_sign=True)
    if name=='w6_realizable_m7_centered':
        return m7.RealizableUFNOMoment(temperature=.12,points_per_axis=6,
                                       hidden=32,grid_size=8)
    raise ValueError('unknown matched framework')


def run(*,w6_root,seeds=(67,71,73),per_family=20,steps=100,repeats=5,
        models=MODEL_NAMES)->dict:
    if (not seeds or len(set(seeds))!=len(seeds) or not models or
        len(set(models))!=len(models) or any(m not in MODEL_NAMES for m in models)
        or per_family<6 or steps<1 or repeats<1):
        raise ValueError('invalid matched analytic training protocol')
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    m4,m5,m6,guard=load_m9_w6(w6_root)
    m7=load_w6_m7(w6_root)
    libs=m4,m5,m6,guard,m7
    counts={n:real_parameters(build_model(n,seeds[0],libs)) for n in models}
    if max(counts.values())/min(counts.values())>1.05:
        raise ValueError('parameter capacity mismatch >5%')
    full=[]
    for seed in seeds:
        train_all=centered_dataset(('box','sphere'),per_family=per_family,seed=seed)
        heldout=centered_dataset(('ellipsoid',),per_family=per_family,seed=seed+1)
        fit,valid=split_fit_validation(train_all,seed,max(1,per_family//5))
        checks=independent_family_check(fit,valid,heldout)
        row={'seed':seed,'train_SHA256':sha_dataset(train_all),
             'heldout_SHA256':sha_dataset(heldout),'split':checks,'results':{}}
        for name in models:
            model=build_model(name,seed,libs)
            training=train(model,fit,valid,seed=seed,steps=steps)
            result=metrics(model,heldout)
            decision=truth_decision_metrics(model,heldout)
            timing=latency(model,heldout,repeats=repeats)
            row['results'][name]={'training':training,'heldout':result,
                                  'analytic_1d_decision':decision,'model_cpu_timing':timing}
        full.append(row)
    agg={}
    for name in models:
        rows=[x['results'][name] for x in full]
        keys=(('heldout','r_mae'),('heldout','J_mae'),('heldout','directional_mae'),
              ('analytic_1d_decision','one_step_candidate_accepted_fraction'),
              ('model_cpu_timing','encoding_ms'),('model_cpu_timing','warm_J_ms'))
        agg[name]={f'{group}.{key}':{'mean':statistics.mean(r[group][key] for r in rows),
                                    'sample_sd':statistics.stdev(r[group][key] for r in rows) if len(rows)>1 else None}
                   for group,key in keys}
        agg[name]['training_seconds_total']=sum(x['training']['cpu_training_seconds'] for x in rows)
        agg[name]['parameter_count']=counts[name]
    return {'schema':'W5_M13_CENTERED_4CH_MATCHED_NEURAL_COMPARISON_V1',
            'data_origin':'W0_ANALYTIC_CONTINUUM_P0_NOT_W2_CAD',
            'W2_admissible_J_labels':0,'native_Cherchi_evaluations':0,
            'W6_m7_exact_readonly_commit':W6_M7_COMMIT,
            'W6_m7_git_blob_pins':W6_M7_FILES,
            'models':list(models),'parameter_counts':counts,
            'capacity_max_min_ratio':max(counts.values())/min(counts.values()),
            'seeds':list(seeds),'per_family':per_family,'steps_max':steps,
            'all_same_4channel_center_cell_sampling':True,
            'train_families':['box','sphere'],'heldout_family':['ellipsoid'],
            'optimizer':'Adam lr0.003 batch8 MSE(r)+0.5*MSE(Jc) validation-only early stopping',
            'loss_label':'ANALYTIC_P0_NOT_NATIVE_MATERIAL',
            'device':'cpu','threads':torch.get_num_threads(),'gpu_hours':0.0,
            'no_full_10d_native_optimizer_test':True,
            'python':platform.python_version(),'torch':torch.__version__,
            'all_seed_results':full,'aggregate':agg,
            'scientific_limitations':[
              'Actual W6 M7 model source tested and fitted, original external pretrained weights were not used',
              'All labels derive from analytic ideal solids rather than rasterized voxels or Cherchi',
              'P0 heldout ellipsoid alone is not a complex CAD generalization benchmark',
              'Surrogate differentiable J is not W0-certified native material J',
              'CPU timings are not Faster/Cherchi end-to-end speedup',
            ]}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--w6-root',required=True)
    p.add_argument('--seeds',default='67,71,73')
    p.add_argument('--per-family',type=int,default=20)
    p.add_argument('--steps',type=int,default=100)
    p.add_argument('--repeats',type=int,default=5)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    result=run(w6_root=a.w6_root,seeds=tuple(int(x) for x in a.seeds.split(',')),
               per_family=a.per_family,steps=a.steps,repeats=a.repeats)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k in ('schema','seeds','aggregate','parameter_counts','capacity_max_min_ratio')},indent=2))

if __name__=='__main__':main()
