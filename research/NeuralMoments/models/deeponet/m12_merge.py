"""W5 M12 reproducible fresh-seed analytic experiment aggregation (no retraining)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics

from .m12_experiment import TRAINED_NAMES


def digest(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def combine(paths)->dict:
    if len(paths)<2:
        raise ValueError('MULTIPLE_INDEPENDENT_SEEDS_REQUIRED')
    items=[];source=[];unique=set();heldout=set();training=set()
    for user_path in paths:
        p=Path(user_path)
        if not p.is_file() or p.is_symlink():
            raise ValueError('UNREADABLE_OR_LINKED_INPUT_RECORD')
        r=json.loads(p.read_text(encoding='utf-8'),parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
        if (r.get('schema')!='W5_M12_ANALYTIC_STRICT_SATURATION_V1'
                or r.get('models')!=list(TRAINED_NAMES)
                or r.get('max_optimizer_steps')!=100 or r.get('fit_samples')!=64
                or r.get('validation_samples')!=16 or r.get('heldout_samples')!=40
                or r.get('teacher_kind')!='ANALYTIC_P0_GROUND_TRUTH_ONLY_NOT_W2_REAL_MATERIAL'
                or r.get('real_w2_training_labels')!=0 or r.get('native_cherchi_calls')!=0
                or r.get('M12_distinction')!='SAME_TRAINED_M11_WEIGHTS_WITH_POSTHOC_ANALYTIC_SATURATION_NOT_FIFTH_INDEPENDENT_MODEL'
                or r.get('source_W6_commit')!='27d51678cf741233c7a2e6c54c78d9a4667bec00'):
            raise ValueError('M12_EXPERIMENT_PROTOCOL_OR_PROVENANCE_MISMATCH')
        seed=r['seed']
        if type(seed) is not int or seed in unique:
            raise ValueError('DUPLICATED_OR_MALFORMED_SEED')
        unique.add(seed)
        for key,seen in (('train_sha256',training),('heldout_sha256',heldout)):
            val=r.get(key)
            if not isinstance(val,str) or len(val)!=64 or val in seen:
                raise ValueError('DUPLICATE_OR_MALFORMED_DATASET_HASH')
            seen.add(val)
        m=r['results']['w5_cone_integrable_025']
        g=m['M12_strict_saturation_with_independent_analytic_full_moment']
        if (g.get('independent_analytic_geometry_count')!=20 or
                g.get('out_of_cut_queries')!=80 or
                g.get('full_queries')!=40 or g.get('empty_queries')!=40 or
                g.get('full_raw_r_mae')!=0 or g.get('empty_raw_r_mae')!=0 or
                g.get('max_full_abs_Jc')!=0 or g.get('max_empty_abs_Jc')!=0 or
                g.get('new_native_cherchi_calls')!=0 or
                g.get('analytic_full_reference_evaluations')!=20):
            raise ValueError('SATURATION_CLAIMS_NOT_MATCHING_RAW_SOURCE')
        inside=m['interior_preservation']
        if inside.get('max_r_difference')!=0 or inside.get('max_J_difference_where_defined')!=0:
            raise ValueError('UNEXPECTED_INTERIOR_NETWORK_DRIFT')
        items.append(r)
        source.append({'file':p.name,'seed':seed,'sha256':digest(p)})
    items.sort(key=lambda v:v['seed']);source.sort(key=lambda v:v['seed'])
    aggregated={}
    for model in TRAINED_NAMES:
        rows=[x['results'][model] for x in items]
        funcs={
          'interior_r_mae':lambda x:x['interior']['r_mae'],
          'interior_J_mae':lambda x:x['interior']['J_mae'],
          'interior_true_one_step_accepted':lambda x:x['guarded_one_dimensional_decision']['accepted_over_all_samples'],
          'unprotected_full_r_mae':lambda x:x['strict_saturation_without_independent_full_moment']['full_raw_r_mae'],
          'unprotected_empty_r_mae':lambda x:x['strict_saturation_without_independent_full_moment']['empty_raw_r_mae'],
          'unprotected_max_full_J_abs':lambda x:x['strict_saturation_without_independent_full_moment']['max_full_abs_Jc'],
          'training_cpu_seconds':lambda x:x['fit']['cpu_training_seconds'],
        }
        aggregated[model]={}
        for metric,fn in funcs.items():
            vals=[float(fn(row)) for row in rows]
            aggregated[model][metric]={
                'mean':float(statistics.mean(vals)),
                'sample_sd':float(statistics.stdev(vals)),
                'per_seed':{str(it['seed']):v for it,v in zip(items,vals)}}
    fresh=items[0]['results']['w5_cone_integrable_025']['M12_strict_saturation_with_independent_analytic_full_moment']
    return {
        'schema':'W5_M12_MERGED_FRESH_SEEDS_ANALYTIC_ONLY_V1',
        'seed_list':[x['seed'] for x in items],
        'model_names':list(TRAINED_NAMES),
        'per_seed_source_sha256':source,
        'aggregate':aggregated,
        'strict_saturation_total_queries':sum(x['results']['w5_cone_integrable_025']['M12_strict_saturation_with_independent_analytic_full_moment']['out_of_cut_queries'] for x in items),
        'strict_saturation_total_independent_geometries':sum(x['results']['w5_cone_integrable_025']['M12_strict_saturation_with_independent_analytic_full_moment']['independent_analytic_geometry_count'] for x in items),
        'strict_saturation_total_full_oracle_analytic_calls':sum(x['results']['w5_cone_integrable_025']['M12_strict_saturation_with_independent_analytic_full_moment']['analytic_full_reference_evaluations'] for x in items),
        'protected_full_r_mae':fresh['full_raw_r_mae'],
        'protected_empty_r_mae':fresh['empty_raw_r_mae'],
        'protected_max_J_abs':max(fresh['max_full_abs_Jc'],fresh['max_empty_abs_Jc']),
        'real_Cherchi_native_calls':0,
        'W2_certified_smooth_J_training_labels':0,
        'proof_scope':'TRUSTED_SELF_GENERATED_ANALYTIC_SHAPE_ONLY_NOT_REAL_CAD',
        'full_source_r_is_INDEPENDENT_ORACLE_not_network_prediction':True,
        'no_new_approximation_speedup_claim':True,
        'full_seed_records':items,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('inputs',nargs='+')
    ap.add_argument('--output',required=True,type=Path)
    args=ap.parse_args()
    data=combine(args.inputs)
    args.output.write_text(json.dumps(data,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'seeds':data['seed_list'],'strict_queries':data['strict_saturation_total_queries'],'aggregate':{n:{k:v['mean'] for k,v in m.items() if k in ('interior_r_mae','interior_J_mae','unprotected_full_r_mae')} for n,m in data['aggregate'].items()}},indent=2))

if __name__=='__main__':main()
