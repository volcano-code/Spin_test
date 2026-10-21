"""W6 M12 strict offline replay/audit of mixed-goal analytic VOI decisions.

Uses only recorded per-case outcomes after experiments, never informs a heldout
online policy. No W2 native training admission can be inferred from the result.
"""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
from .m12_value_policy import FrozenVOIPolicy, ObservableRisk,calibration_identity
from .m12_experiment import _family_scores

class AuditError(ValueError):pass

def require(ok,why):
    if not ok:raise AuditError(why)

def close(x,y):
    return (isinstance(x,(int,float)) and isinstance(y,(int,float)) and
            math.isfinite(x) and math.isfinite(y) and abs(x-y)<1e-9)

def audit(report:dict)->dict:
    require(type(report) is dict and report.get('schema')=='W6_M12_VALIDATION_ONLY_VOI_ANALYTIC_P0_V1','schema mismatch')
    require(report.get('native_W2_admitted_labels')==0 and report.get('native_W2_calls')==0,'W2 leak')
    require(report.get('selection_teacher_provenance')=='R_ONLY_ANALYTIC_CONTINUUM_P0_NOT_W2','teacher provenance changed')
    seeds=report.get('seeds')
    require(isinstance(seeds,list) and len(seeds)==len(set(seeds)) and seeds,'seed identities missing')
    records=report.get('seed_records')
    require(isinstance(records,list) and [r['seed'] for r in records]==seeds,'seed records absent/reordered')
    observations={};total_geo=0;total_cases=0
    for row in records:
        require(row['heldout_geometries']>=1 and row['policy_development_geometries']>=1,'empty split')
        required=['source_frozen_train_sha256','heldout_tensor_sha256','policy_calibration_source_sha256']
        require(all(isinstance(row.get(k),str) and len(row[k])==64 for k in required),'dataset SHA missing')
        for model_name,model in row['model_runs'].items():
            pin=model['frozen_policy']; policy=FrozenVOIPolicy(**pin)
            calibration=model['policy_calibration_receipts']; ids=[v['geometry_id'] for v in calibration]
            require(policy.calibration_geometry_sha256==calibration_identity(ids),'calibration identity changed')
            holdouts=model['heldout_per_geometry']; test_ids=[v['geometry_id'] for v in holdouts]
            require(not(set(test_ids)&set(ids)) and len(set(test_ids))==len(test_ids),'heldout leakage')
            require(len(test_ids)==row['heldout_geometries'],'heldout geometry count drift')
            for geom in holdouts:
                n=geom['task_count']; require(n==report['target_count_per_geometry'],'target count mismatch')
                obs=ObservableRisk(**geom['observable'])
                require(obs.target_count==n and obs.score>=0,'risk score invalid')
                require(geom['risk_extra_surrogate_r_and_J_evaluations']==n,'unaccounted surrogate risk feature')
                require(geom['risk_proxy_cell_mass_evaluations']==n+1,'proxy call undercount')
                for k in (0,1,2):
                    p=geom['decision_only'][str(k)]
                    require(p['calls']['selection_analytic_r_calls']==k,'anchor oracle budget violated')
                    require(p['calls']['encoder_calls']==1,'encoder not cached')
                    require(len(p['cases'])==n,'candidate count mismatch')
                    directions=[x['goal_direction'] for x in p['cases']]
                    require(directions.count(1)==directions.count(-1)==n//2,'mixed directions biased')
                    for x in p['cases']:
                        require(x['accepted'] in (0,1) and math.isfinite(x['true_decrease']),'invalid poststep truth')
                atom=geom['bounded_atoms']
                if atom is not None:
                    for k in (0,1,2):
                        require(atom[str(k)]['calls']['selection_analytic_r_calls']==k,'atomic query undercount')
            for policy_name in ('0','1','2','voi_frozen'):
                replay=_family_scores(holdouts,choice=int(policy_name) if policy_name!='voi_frozen' else None,
                                    policy=policy if policy_name=='voi_frozen' else None)
                logged=model['heldout'][policy_name]
                for field in ('acceptance','positive_goal_acceptance','negative_goal_acceptance',
                              'mean_true_decrease','selection_calls_per_target','guard_fallback_fraction'):
                    require(close(replay[field],logged[field]),'policy replay mismatch '+field)
                require(replay['selection_r_only_queries']==logged['selection_r_only_queries'],'oracle calls tampered')
            total_geo+=len(holdouts);total_cases+=sum(x['task_count'] for x in holdouts)
            observations.setdefault(model_name,0);observations[model_name]+=1
        require(max(x['parameters_real'] for x in row['model_runs'].values())/min(x['parameters_real'] for x in row['model_runs'].values())<=1.05,'parameter parity violated')
    for model_name,by_policy in report['aggregate'].items():
        for key,rec in by_policy.items():
            individual=[r['model_runs'][model_name]['heldout'][key] for r in records]
            require(close(sum(x['acceptance'] for x in individual)/len(individual),rec['mean_acceptance']),
                    'aggregate acceptance was altered')
            require(close(sum(x['selection_calls_per_target'] for x in individual)/len(individual),
                    rec['mean_online_r_oracle_per_target']),'aggregate cost was altered')
    return {'schema':'W6_M12_AUDITED_P0_OFFLINE_REPLAY_V1','status':'PASS_NOT_NATIVE',
            'seeds':seeds,'per_model_seed_runs':observations,
            'independent_heldout_geometry_model_evaluations':total_geo,
            'offline_target_model_evaluations':total_cases,
            'native_W2_admitted_training_labels':0,'native_W2_calls':0,
            'online_teacher_cost_simulated_from_separate_policy_paths':True,
            'same_full_report_per_case_recomputed':True}

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();data=json.loads(Path(a.input).read_text());check=audit(data)
    Path(a.output).write_text(json.dumps(check,indent=2,sort_keys=True)+'\n')
    print(json.dumps(check,indent=2))
if __name__=='__main__':main()
