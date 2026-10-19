"""W6 M3 multi-seed wrapper: paired analytic physical-cut experiments.

Run from repository root:
 python -m research.NeuralMoments.models.pcraft_ufno.m3_multiseed \
   --seeds 19,23,29 --steps 12 --per-family 20 --repeats 5 --output PATH

The per-seed dataset and paired minibatch schedule are identical across three
architectures. Aggregates are descriptive single-run CPU smoke statistics,
NOT matched native W2 teacher or converged scientific accuracy.
"""
from __future__ import annotations
import argparse
import json
import math
import statistics

from .faircut_m3 import ARMS, MODELS, run


def aggregate(results: list[dict]) -> dict:
    if not results:
        raise ValueError("one or more seed runs required")
    seeds=[int(r['seed']) for r in results]
    if len(set(seeds))!=len(seeds):
        raise ValueError("repeated seeds would invalidate an independent-seed aggregate")
    for r in results:
        if (r['status']!='SAME_NATIVE_C_ANALYTIC_CONTINUUM_P0_M3_ONLY'
                or r['model_parameter_real_dof']!=results[0]['model_parameter_real_dof']
                or {k:v for k,v in r['config'].items() if k!='seed'} !=
                {k:v for k,v in results[0]['config'].items() if k!='seed'}):
            raise ValueError("incompatible model settings for cross-seed aggregate")
    metrics=('r_mae','J_mae','directional_mae','r_w0_normalized_component_mae',
             'predicted_Jq_asymmetry_max','projective_radial_Jc_c_max')
    stats={}
    for name in MODELS:
        stats[name]={}
        for arm in ARMS:
            stats[name][arm]={}
            for metric in metrics:
                values=[float(x['model_results'][name][arm]['heldout'][metric]) for x in results]
                if not all(math.isfinite(v) for v in values):
                    raise ValueError("nonfinite heldout metric")
                stats[name][arm][metric]={"mean":statistics.mean(values),
                                         "sample_sd":statistics.stdev(values) if len(values)>1 else None,
                                         "per_seed":dict(zip(map(str,seeds),values))}
    return {"status":"ANALYTIC_P0_CUT_M3_MULTI_SEED_SMOKE_ONLY",
            "seeds":seeds,"independent_native_teacher_runs":0,
            "W5_input_feature_equivalence":False,
            "experimental_scope":"analytic physical-cut labels from the same voxel source; W5 uses lossy 9D fixed summary",
            "shared_configuration":{k:v for k,v in results[0]['config'].items() if k!='seed'},
            "parameter_counts":results[0]['model_parameter_real_dof'],
            "aggregates":stats,"runs":results}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--seeds',default='19,23,29')
    p.add_argument('--steps',type=int,default=12)
    p.add_argument('--per-family',type=int,default=20)
    p.add_argument('--grid-size',type=int,default=8)
    p.add_argument('--repeats',type=int,default=5)
    p.add_argument('--output',default=None)
    args=p.parse_args()
    seeds=[int(x) for x in args.seeds.split(',')]
    if len(seeds)<2:
        raise ValueError("provide at least two independent seeds for the aggregate")
    result=aggregate([run(seed=s,steps=args.steps,per_family=args.per_family,
                          grid_size=args.grid_size,repeats=args.repeats) for s in seeds])
    content=json.dumps(result,indent=2,ensure_ascii=False,sort_keys=True,allow_nan=False)
    if args.output:
        with open(args.output,'w',encoding='utf-8') as f:f.write(content+'\n')
    print(content)


if __name__=='__main__':
    main()
