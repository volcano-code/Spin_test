"""Deterministic independent aggregation of W5 M10 one-seed CPU records."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import statistics

SCHEMA='W5_M10_POSITIVE_DISCRETE_MOMENT_CONE_ANALYTIC_V1'
METRICS=('r_mae','J_mae','Jq_asymmetry','native_radial_Jc_c',
         'necessary_moment_pass_fraction','negative_mass_empty_fraction',
         'empty_predicted_mass_mean','guarded_candidate_accept_fraction',
         'cold_encode_plus_r_ms','cached_J_ms','fit_cpu_seconds')


def merge_single_seed_files(paths)->dict:
    if not paths:
        raise ValueError('At least one real execution record required')
    raw=[Path(p).read_bytes() for p in paths]
    sources=[json.loads(b) for b in raw]
    anchor=sources[0]
    compared=('schema','models','steps_upper_bound','per_family','parameters_real',
              'training_loss','labels','four_channel_input_parity','CPU_threads',
              'reference_W6_readonly_commit','W0_real_81point_report_git_blob',
              'no_Cherchi_or_CAD_supervision_used')
    seeds=[];rows=[]
    for x in sources:
        if any(x.get(k)!=anchor.get(k) for k in compared) or x.get('schema')!=SCHEMA:
            raise ValueError('Incompatible schema or training protocol across seeds')
        if len(x.get('seeds',[]))!=1 or len(x.get('all_seed_records',[]))!=1:
            raise ValueError('One source must represent exactly one actually executed seed')
        seed=x['seeds'][0]
        if seed in seeds or x['all_seed_records'][0]['seed']!=seed:
            raise ValueError('Duplicate/relabelled seed')
        if not x.get('archived_real_evidence_admission_gate',{}).get('certified_smooth_J_admitted_total')==0:
            raise ValueError('Native derivative data admission not allowed')
        seeds.append(seed); rows.append(x['all_seed_records'][0])
    combined=dict(anchor)
    combined['seeds']=seeds
    combined['all_seed_records']=rows
    combined['source_seed_file_sha256']={str(seed):hashlib.sha256(b).hexdigest()
                                         for seed,b in zip(seeds,raw)}
    combined['aggregate']={}
    for name in anchor['models']:
        data=[row['models'][name] for row in rows]
        funcs={
            'r_mae':lambda r:r['heldout']['r_mae'],
            'J_mae':lambda r:r['heldout']['J_mae'],
            'Jq_asymmetry':lambda r:r['heldout']['Jq_max_asymmetry'],
            'native_radial_Jc_c':lambda r:r['heldout']['native_radial_max'],
            'necessary_moment_pass_fraction':lambda r:r['moment_necessity']['necessary_support_pass_fraction'],
            'negative_mass_empty_fraction':lambda r:r['moment_necessity']['empty_cut_predicted_negative_mass_fraction'],
            'empty_predicted_mass_mean':lambda r:r['moment_necessity']['empty_cut_predicted_mass_mean'],
            'guarded_candidate_accept_fraction':lambda r:r['guarded_decision']['accepted_over_all_samples'],
            'cold_encode_plus_r_ms':lambda r:r['cpu_latency']['cold_r_ms'],
            'cached_J_ms':lambda r:r['cpu_latency']['warm_J_ms'],
            'fit_cpu_seconds':lambda r:r['training']['cpu_training_seconds'],
        }
        combined['aggregate'][name]={key:{
            'mean':statistics.mean(func(r) for r in data),
            'sample_sd':statistics.stdev(func(r) for r in data) if len(data)>1 else None,
            'per_seed':{str(seed):func(r) for seed,r in zip(seeds,data)}
        } for key,func in funcs.items()}
        combined['aggregate'][name]['measured_8_queries_moment_J_ms']=statistics.mean(
            r['measured_query_costs']['8']['single_encode_q_moment_and_J_ms'] for r in data)
    if anchor.get('W2_real_native_J_training_labels_admitted')!=0:
        raise ValueError('Source claimed unauthorized J supervision')
    combined['merge_note']='Per-seed metrics recomputed from actual trained model records; never from historical W6 results'
    return combined


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('files',nargs='+')
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    a.output.write_text(json.dumps(merge_single_seed_files(a.files),sort_keys=True,
                                  ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(a.output)

if __name__=='__main__':main()
