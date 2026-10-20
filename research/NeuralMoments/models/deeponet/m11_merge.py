"""Fail-closed aggregation of actually executed independent M11 seed artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics

SCHEMA='W5_M11_POSITIVE_CONE_CONVEX_POTENTIAL_ANALYTIC_V1'
FIELDS={
    'r_mae':('heldout','r_mae'),
    'J_mae':('heldout','J_mae'),
    'Jq_asymmetry_max':('structural','Jq_max_asymmetry'),
    'Jq_min_eigenvalue':('structural','Jq_min_symmetric_eigenvalue'),
    'necessary_support_pass':('necessary_support','necessary_support_pass_fraction'),
    'empty_cut_mass':('necessary_support','empty_cut_predicted_mass_mean'),
    'guarded_1D_accept_fraction':('guarded_1D_decision','accepted_over_all_samples'),
    'cold_r_ms':('latency','cold_r_ms'),
    'warm_J_ms':('latency','warm_J_ms'),
    'cpu_fit_seconds':('training','cpu_training_seconds'),
}


def merge_seed_files(paths):
    if len(paths)<2:
        raise ValueError('Independent aggregate requires >=2 seed runs')
    bodies=[Path(p).read_bytes() for p in paths]
    sources=[json.loads(b) for b in bodies]
    anchor=sources[0]
    keys=('schema','status','models','max_steps','per_family',
          'input_4channel_resolution','real_parameter_counts',
          'upstream_W6_source_commit','dataset_teacher_kind','training_loss',
          'optimizer','W2_admissible_training_labels','W5_new_native_cherchi_queries',
          'native_c_B_diagonal')
    seeds=[];train_hashes=set();test_hashes=set()
    for x in sources:
        if x.get('schema')!=SCHEMA or any(x.get(k)!=anchor.get(k) for k in keys):
            raise ValueError('M11 experiment protocol/sources incompatible')
        if (x.get('W2_admissible_training_labels')!=0 or
                x.get('W5_new_native_cherchi_queries')!=0 or
                x.get('global_native_Hessian_or_CAD_material_certified') is not False):
            raise ValueError('Untrusted native/CAD proof promotion')
        if x.get('seeds') != [x.get('seed')] or x['seed'] in seeds:
            raise ValueError('Duplicate/relabelled seed')
        seed=x['seed'];seeds.append(seed)
        if x['dataset_train_sha256'] in train_hashes or x['dataset_heldout_sha256'] in test_hashes:
            raise ValueError('Repeated dataset/hash across supposedly independent seeds')
        train_hashes.add(x['dataset_train_sha256']);test_hashes.add(x['dataset_heldout_sha256'])
        split=x['geometry_split']
        if (not isinstance(split,dict) or split.get('heldout_families')!=['ellipsoid']
                or type(split.get('fit_ids')) is not int or split['fit_ids']<1
                or type(split.get('validation_ids')) is not int or split['validation_ids']<1
                or type(split.get('heldout_ids')) is not int or split['heldout_ids']<1):
            # Non-overlap of individual IDs was checked in the executed dataset generator.
            raise ValueError('Missing or incompatible split provenance')
        if set(x['results'])!=set(anchor['models']):
            raise ValueError('Missing model results')
    stats={}
    for name in anchor['models']:
        sub=[x['results'][name] for x in sources]
        agg={}
        for label,(group,metric) in FIELDS.items():
            values=[float(row[group][metric]) for row in sub]
            if any(v!=v or abs(v)==float('inf') for v in values):
                raise ValueError('Nonfinite result')
            agg[label]={'mean':statistics.mean(values),
                        'sample_sd':statistics.stdev(values),
                        'per_seed':dict(zip(map(str,seeds),values))}
        for q in ('1','8'):
            values=[float(row['measured_queries'][q]['single_encode_q_moment_and_J_ms']) for row in sub]
            agg['measured_'+q+'_queries_ms']={'mean':statistics.mean(values),
                                                 'sample_sd':statistics.stdev(values)}
        agg['selected_steps']=[row['training']['selected_step'] for row in sub]
        stats[name]=agg
    return {'schema':'W5_M11_REPRODUCED_MULTI_SEED_AGGREGATE_V1',
            'source_experiment_schema':SCHEMA,'seeds':seeds,
            'source_file_sha256':dict(zip(map(str,seeds),map(lambda b:hashlib.sha256(b).hexdigest(),bodies))),
            'models':anchor['models'],'real_parameter_counts':anchor['real_parameter_counts'],
            'parameter_ratio':anchor['real_parameter_ratio'],
            'common_protocol':{k:anchor.get(k) for k in keys},
            'data_split_sha_per_seed':{str(x['seed']):{'train':x['dataset_train_sha256'],
                                  'heldout':x['dataset_heldout_sha256']}
                                  for x in sources},
            'analytic_only':True,'real_native_calls':0,'native_J_training_labels':0,
            'historical_Cherchi_material_training_used':False,
            'aggregate':stats}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('files',nargs='+')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    result=merge_seed_files(a.files)
    a.output.write_text(json.dumps(result,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'seeds':result['seeds'],'means':{k:{n:round(v[n]['mean'],7)
           for n in ('r_mae','J_mae','necessary_support_pass','guarded_1D_accept_fraction')}
           for k,v in result['aggregate'].items()}},indent=2))


if __name__=='__main__':main()
