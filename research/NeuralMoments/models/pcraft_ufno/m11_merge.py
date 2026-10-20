"""W6 M11: fail-closed merger of paired +/− analytic decision experiments.

Reads exactly the independently executed JSON reports; recomputes aggregate
results from per-case observations, checks split/source/training identity,
counts actual paid anchor calls and performs exploratory geometry-grouped
bootstrap intervals. No held-out labels are used for training or tuning.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import numpy as np

from .m11_experiment import MODEL_POLICIES,MODEL_NAMES


class AuditMismatch(ValueError):
    pass


def _digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _validate_source(report):
    if (report.get('schema')!='W6_M11_ANCHORED_DECISION_AUDIT_V1'
        or report.get('status')!='ANALYTIC_P0_ONLY_NOT_NATIVE_CHERCHI'
        or report.get('native_W2_admitted_training_labels')!=0
        or report.get('native_W2_calls')!=0):
        raise AuditMismatch('incompatible analytic/P0 source or W2 counts')
    if not report.get('cases') or (report.get('goal_offset') is not None and not isinstance(report.get('goal_offset'),(float,int))):
        raise AuditMismatch('missing cases or target offset')
    if len(report['seeds'])!=len(set(report['seeds'])):
        raise AuditMismatch('duplicate seed within report')
    if {c['seed'] for c in report['cases']}!=set(report['seeds']):
        raise AuditMismatch('reported seed/case mismatch')
    return report


def _model_cases(cases,name,policy):
    rows=[]
    for c in cases:
        e=c['models'][name]['evaluation']
        rows.extend(e['per_case'][policy])
    return rows


def _grouped_delta_ci(cases,name,policy,*,n_boot=2000,bootstrap_seed=20261021):
    # Group 8 controls by geometry. Respect seed/geometry within a group;
    # independent random seeds represent an outer cluster level.
    groups={}
    for case in cases:
        a=case['models'][name]['evaluation']['per_case']['baseline']
        b=case['models'][name]['evaluation']['per_case'][policy]
        for x,y in zip(a,b):
            if any(x[k]!=y[k] for k in ('seed','geometry_sha256','h_local')):
                raise AuditMismatch('not paired controls')
            groups.setdefault(x['seed'],{}).setdefault(x['geometry_sha256'],[]).append(y['accepted']-x['accepted'])
    seeds=list(sorted(groups))
    if not seeds or any(len(groups[s])!=cases[0]['models'][name]['evaluation']['distinct_heldout_geometry_ids'] for s in seeds):
        raise AuditMismatch('geometry split changed across seeds')
    means_by_seed={s:np.array([np.mean(v) for v in groups[s].values()],dtype=float) for s in seeds}
    rng=np.random.default_rng(bootstrap_seed)
    samples=[]
    for _ in range(n_boot):
        chosen=rng.choice(seeds,len(seeds),replace=True)
        sample=[]
        for s in chosen:
            arr=means_by_seed[s]
            sample.append(float(np.mean(rng.choice(arr,len(arr),replace=True))))
        samples.append(float(np.mean(sample)))
    return {"method":"EXPLORATORY_HIERARCHICAL_SEED_GEOMETRY_BOOTSTRAP_NOT_CONFIRMATORY",
            "bootstrap_draws":n_boot,
            "paired_difference_acceptance":statistics.mean(float(np.mean(arr)) for arr in means_by_seed.values()),
            "percentile95":list(map(float,np.quantile(samples,[.025,.975]))),
            "seed_count":len(seeds),"geometry_groups":sum(len(v) for v in groups.values())}


def merge(positive_first:dict,positive_rest:dict,negative:dict):
    p1,p2,neg=(_validate_source(obj) for obj in (positive_first,positive_rest,negative))
    if not (math.isclose(p1.get('goal_offset',.12),.12) and math.isclose(p2.get('goal_offset',.12),.12)
            and math.isclose(neg['goal_offset'],-.12)):
        # M11 positive first call was executed with v1 CLI without persisted
        # goal_offset; that version has an implicit documented +0.12 default.
        if not (p1.get('goal_offset',.12)==.12 and p2.get('goal_offset',.12)==.12
                and neg.get('goal_offset')==-.12):
            raise AuditMismatch('target direction mismatch')
    plus=p1['cases']+p2['cases']
    minus=neg['cases']
    splus={c['seed']:c for c in plus}
    sminus={c['seed']:c for c in minus}
    if (len(splus)!=len(plus) or set(splus)!=set(sminus)
        or len(splus)<3 or any(len(c['models'])!=len(MODEL_NAMES) for c in plus+minus)):
        raise AuditMismatch('missing/duplicate model or independent seed')
    for seed in splus:
        a,b=splus[seed],sminus[seed]
        if (a['training_tensor_sha256']!=b['training_tensor_sha256']
            or a['heldout_tensor_sha256']!=b['heldout_tensor_sha256']):
            raise AuditMismatch('positive and negative do not share exact frozen datasets')
        for name in MODEL_NAMES:
            ma,mb=a['models'][name],b['models'][name]
            if (ma['parameters_real']!=mb['parameters_real'] or
                ma['training']['selected_step']!=mb['training']['selected_step'] or
                ma['training']['minibatch_schedule_sha256']!=mb['training']['minibatch_schedule_sha256']):
                raise AuditMismatch('training or parameter budget was changed by target direction')
            ea,eb=ma['evaluation'],mb['evaluation']
            if ea['distinct_heldout_geometry_ids']!=eb['distinct_heldout_geometry_ids']:
                raise AuditMismatch('different heldout shape count')
            for policy in MODEL_POLICIES:
                ra,rb=ea['per_case'][policy],eb['per_case'][policy]
                if len(ra)!=len(rb):raise AuditMismatch('unequal direction target cases')
                for x,y in zip(ra,rb):
                    if any(x[k]!=y[k] for k in ('seed','geometry_sha256','h_local')):
                        raise AuditMismatch('positive and negative target controls not paired')
                expected=int({'baseline':0,'one_anchor':1,'two_anchors':2,
                               'current_truth_counterfactual':ea['targets_per_geometry']}[policy])
                if ea['queried_analytic_support_count_total'][policy] !=expected*ea['distinct_heldout_geometry_ids']:
                    raise AuditMismatch('anchor oracle budget understated')
                if eb['queried_analytic_support_count_total'][policy] !=expected*eb['distinct_heldout_geometry_ids']:
                    raise AuditMismatch('reverse oracle budget understated')
    result={"schema":"W6_M11_PAIRED_POS_NEG_DECISION_SUMMARY_V1",
            "status":"ANALYTIC_P0_ONLY_NOT_W2_NATIVE",
            "seeds":sorted(splus),"target_directions":["+0.12","-0.12"],
            "same_source_and_frozen_training_across_directions":True,
            "positive_legacy_CLI_goal_offset_inferred_from_documented_default":True,
            "eligible_W2_labels":0,"new_native_Cherchi_calls":0,
            "trained_parameters_real":{n:plus[0]['models'][n]['parameters_real'] for n in MODEL_NAMES},
            "models":{},"limitations":[
              'Only analytic box/sphere/ellipsoid family heldout, one-dimensional vertical cuts',
              'Truth goal construction and poststep validation are not model-selection calls but are real analytic oracle evaluations',
              'The cached r correction is for GN step choice only, not valid certified material moments',
              'Cone check is necessary, not sufficient, and fallback occurs',
              'An extra support query per geometry is not free in native Cherchi',
              'No real W2 admissible teacher, native 10D optimization or GPU speedup measured',
              'Bootstrap intervals exploratory; both directions evaluated after selecting policy specification']}
    for name in MODEL_NAMES:
        result['models'][name]={}
        for direction,cases in (('positive',plus),('negative',minus)):
            result['models'][name][direction]={}
            for policy in MODEL_POLICIES:
                rows=_model_cases(cases,name,policy)
                metric={"n_cases":len(rows),"acceptance":statistics.mean(x['accepted'] for x in rows),
                        "gradient_sign_error":statistics.mean(x['gradient_sign_wrong'] for x in rows),
                        "mean_signed_regret":statistics.mean(x['signed_regret'] for x in rows),
                        "mean_true_objective_decrease":statistics.mean(x['true_decrease'] for x in rows),
                        "mean_decision_r_mae":statistics.mean(x['corrected_mae'] for x in rows),
                        "correction_use_fraction":statistics.mean(x['correction_used'] for x in rows),
                        "cone_necessary_pass_fraction":statistics.mean(x['cone_pass'] for x in rows),
                        "fallback_fraction":statistics.mean(x['anchor_fallback'] for x in rows),
                        "paid_selection_oracle_calls":sum(x['selection_oracle_calls_charged'] for x in rows),
                        "oracle_calls_per_candidate":statistics.mean(x['selection_oracle_calls_charged'] for x in rows),
                        "positive_material_proof":False}
                if policy not in ('baseline','current_truth_counterfactual'):
                    metric['paired_bootstrap_vs_zero']=_grouped_delta_ci(cases,name,policy)
                result['models'][name][direction][policy]=metric
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--positive-first',type=Path,required=True)
    p.add_argument('--positive-rest',type=Path,required=True)
    p.add_argument('--negative',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    texts=[x.read_bytes() for x in (args.positive_first,args.positive_rest,args.negative)]
    result=merge(*[json.loads(t) for t in texts])
    result['evidence_source_sha256']={key:hashlib.sha256(raw).hexdigest() for key,raw in
        zip(('positive_first','positive_rest','negative'),texts)}
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps({n:{d:{p:round(v['acceptance'],4) for p,v in pol.items()}
                          for d,pol in dirs.items()} for n,dirs in result['models'].items()},indent=2))


if __name__=='__main__':main()
