"""Lossless merge of separately executed M9 single-seed reports.

No predictions are re-evaluated; reference hashes and all full per-seed
training histories are preserved. Every displayed multi-seed aggregate is
recomputed, not copied from any earlier M8/W6 results.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics

FIELDS = (
    ('heldout','r_mae'), ('heldout','J_mae'),('heldout','directional_mae'),
    ('heldout','Jq_max_asymmetry'),
    ('necessary_support','necessary_support_pass_fraction'),
    ('necessary_support','empty_cut_predicted_mass_mean'),
    ('guarded_1D_decision','accepted_over_all_samples'),
    ('ungated_1D_decision','one_step_candidate_accepted_fraction'),
)


def merge_seeds(paths: list[str | Path]) -> dict:
    if len(paths)<2:
        raise ValueError('at least two distinct single-seed runs required')
    blobs=[Path(p).read_bytes() for p in paths]
    records=[json.loads(b) for b in blobs]
    baseline=records[0]
    if baseline.get('schema')!='W5_M9_4CH_INPUT_PARITY_GAUSS_PHYSICAL_GATES_V1':
        raise ValueError('unknown M9 report schema')
    exclude={'aggregate','full_seed_experiments','seeds','rss_process_high_water_kib'}
    required_fields={key:value for key,value in baseline.items() if key not in exclude}
    unique=set()
    for record in records:
        if {key:value for key,value in record.items() if key not in exclude}!=required_fields:
            raise ValueError('incompatible protocol, source, labels or capacity')
        if len(record['seeds'])!=1 or len(record['full_seed_experiments'])!=1:
            raise ValueError('requires exactly one genuine per-seed experiment')
        seed=record['seeds'][0]
        if seed in unique or seed!=record['full_seed_experiments'][0]['seed']:
            raise ValueError('duplicate or inconsistent seed')
        unique.add(seed)
        if set(record['full_seed_experiments'][0]['models'])!=set(record['models']):
            raise ValueError('missing model in one seed')
    experiments=[record['full_seed_experiments'][0] for record in records]
    seeds=list(record['seeds'][0] for record in records)
    aggregate={}
    for name in baseline['models']:
        series=[row['models'][name] for row in experiments]
        stats={}
        for group,key in FIELDS:
            values=[float(x[group][key]) for x in series]
            stats[f'{group}.{key}']={'mean':statistics.mean(values),
                                    'sample_sd':statistics.stdev(values),
                                    'per_seed':dict(zip(map(str,seeds),values))}
        stats['train_cpu_seconds_sum']=sum(x['training']['cpu_training_seconds'] for x in series)
        stats['median_encode_ms_across_seeds']=statistics.median(x['timing']['encoding_ms'] for x in series)
        stats['median_warm_J_ms_across_seeds']=statistics.median(x['timing']['warm_J_ms'] for x in series)
        stats['query_budget_mean_ms_across_seeds']={q:{scope:statistics.mean(x['measured_query_budgets'][q][scope] for x in series)
                                                for scope in ('single_encode_q_moment_and_J_ms','q_reencoding_moment_and_J_ms')}
                                                for q in ('1','2','4','8','16')}
        aggregate[name]=stats
    combined=dict(baseline)
    combined['seeds']=seeds
    combined['full_seed_experiments']=experiments
    combined['aggregate']=aggregate
    combined['rss_process_high_water_kib']=max(rec['rss_process_high_water_kib'] for rec in records)
    combined['merge_provenance']={
        'run_method':'THREE_GENUINE_SEPARATE_SEED_EXECUTIONS_NOT_SAME_PROCESS;NO_RETRAIN_DURING_MERGE',
        'individual_source_json_sha256':dict(zip(map(str,seeds),[hashlib.sha256(b).hexdigest() for b in blobs])),
        'all_expected_frameworks_per_seed':True,
        'test_families':['ellipsoid'],
        'training_families':['box','sphere'],
    }
    return combined


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('inputs',nargs='+',type=Path)
    ap.add_argument('--output',required=True,type=Path)
    a=ap.parse_args()
    record=merge_seeds(a.inputs)
    a.output.write_text(json.dumps(record,sort_keys=True,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:{kk:round(vv['mean'],8) for kk,vv in rec.items() if isinstance(vv,dict) and 'mean' in vv}
                      for k,rec in record['aggregate'].items()},indent=2))

if __name__=='__main__':main()
