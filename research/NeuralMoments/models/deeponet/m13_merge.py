"""Lossless W5 M13 seed-merge with strict protocol and input-identity checks."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics

from .m13_m7_model_comparison import MODEL_NAMES


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def merge(paths):
    if len(paths)<2:
        raise ValueError('REQUIRE_MULTIPLE_INDEPENDENT_SEEDS')
    records=[];seen=set();hashes={}
    protocol=None;source=None
    for path in paths:
        p=Path(path);value=json.loads(p.read_text(encoding='utf-8'),parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
        if value.get('schema')!='W5_M13_CENTERED_4CH_MATCHED_NEURAL_COMPARISON_V1':
            raise ValueError('M13_PROTOCOL_UNKNOWN')
        if value.get('native_Cherchi_evaluations')!=0 or value.get('W2_admissible_J_labels')!=0:
            raise ValueError('NATIVE_LABEL_TRAINING_MUST_BE_SEPARATELY_AUTHENTICATED')
        seeds=value.get('seeds');rows=value.get('all_seed_results')
        if not isinstance(seeds,list) or len(seeds)!=1 or not isinstance(rows,list) or len(rows)!=1 or seeds[0]!=rows[0]['seed']:
            raise ValueError('EXPECTED_ONE_COMPLETE_ACTUAL_SEED_PER_INPUT')
        seed=seeds[0]
        if seed in seen:
            raise ValueError('DUPLICATED_RANDOM_SEED')
        seen.add(seed)
        p_info=(value['per_family'],value['steps_max'],tuple(value['models']),
                tuple(sorted(value['parameter_counts'].items())),
                value['all_same_4channel_center_cell_sampling'],
                value['optimizer'])
        if protocol is not None and p_info!=protocol:
            raise ValueError('UNMATCHED_TRAINING_PROTOCOL')
        protocol=p_info
        if source is not None and value['W6_m7_git_blob_pins']!=source:
            raise ValueError('W6_EXTERNAL_BLOB_DRIFT')
        source=value['W6_m7_git_blob_pins']
        if set(rows[0].get('results',{}))!=set(MODEL_NAMES):
            raise ValueError('INCOMPLETE_MODEL_COMPARISON')
        if not rows[0].get('train_SHA256') or not rows[0].get('heldout_SHA256'):
            raise ValueError('MISSING_DATASET_FINGERPRINT')
        for model,experiment in rows[0]['results'].items():
            step=experiment['training']
            if step.get('max_steps')!=value['steps_max'] or step.get('fit_analytic_queries',0)<=0:
                raise ValueError('FITTING_EVIDENCE_INCOMPLETE')
            if experiment['heldout']['r_mae'] < 0 or experiment['heldout']['J_mae'] < 0:
                raise ValueError('INVALID_ERROR')
        hashes[str(seed)]={'source_file_sha256':sha256_file(p),
                           'train_sha256':rows[0]['train_SHA256'],
                           'heldout_sha256':rows[0]['heldout_SHA256']}
        records.append(rows[0])
    for field in ('train_sha256','heldout_sha256'):
        if len({e[field] for e in hashes.values()})!=len(hashes):
            raise ValueError('DUPLICATE_SAMPLED_DATASETS_ACROSS_SEEDS')
    records.sort(key=lambda x:x['seed'])
    aggregated={}
    for model in MODEL_NAMES:
        result={}
        for section,name in (('heldout','r_mae'),('heldout','J_mae'),
                             ('heldout','directional_mae'),
                             ('analytic_1d_decision','one_step_candidate_accepted_fraction'),
                             ('model_cpu_timing','encoding_ms'),('model_cpu_timing','warm_J_ms')):
            values=[float(x['results'][model][section][name]) for x in records]
            result[section+'.'+name]={'mean':statistics.mean(values),
                                     'sample_sd':statistics.stdev(values),
                                     'per_seed':dict(zip((str(x['seed']) for x in records),values))}
        result['parameter_count']=protocol[3] and dict(protocol[3])[model]
        result['sum_train_cpu_seconds']=sum(x['results'][model]['training']['cpu_training_seconds'] for x in records)
        aggregated[model]=result
    return {'schema':'W5_M13_THREE_SEED_NEW_CENTERED_DATA_VERIFIED_V1',
            'training_model_count':len(MODEL_NAMES),'independent_seed_count':len(records),
            'seeds':[r['seed'] for r in records],'per_family':protocol[0],
            'steps_max':protocol[1],'capacity_minmax':max(dict(protocol[3]).values())/min(dict(protocol[3]).values()),
            'same_centered_four_channel_data':True,
            'W6_original_M7_git_blob_pins':source,
            'W2_native_teacher_samples':0,'native_Cherchi_evaluations':0,
            'origin':'ANALYTIC_P0_CONTINUUM_TRUTH_NOT_REAL_CAD',
            'per_seed_input_hashes':hashes,
            'full_seed_results':records,'aggregate':aggregated,
            'not_a_full_native_solver_result':True}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('inputs',nargs='+')
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args()
    merged=merge(args.inputs)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(merged,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'schema':merged['schema'],'seeds':merged['seeds'],
                      'aggregate':merged['aggregate']},indent=2))

if __name__=='__main__':main()
