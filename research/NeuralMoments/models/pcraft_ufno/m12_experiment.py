"""W6 M12: validation-only value-of-information versus fixed 0/1/2 queries.

Physically bounded atom-weight adaptation vs M11 decision-only correction.
Analytic P0 only; runs W6 M7 and the source-matched W5 voxel DeepONet on
identical center-cell inputs and W0 native c/r/J. No W2 native label is used.
A goal r* is a pre-existing task input. Objective evaluation uses analytic
truth only *after* selection, never as a risk feature or candidate decision.

Run from repo root:
  python -m research.NeuralMoments.models.pcraft_ufno.m12_experiment \
    --seeds 107,109,113 --steps 100 --output /tmp/w6m12.json
"""
from __future__ import annotations
import argparse, collections, dataclasses, hashlib, json, math, platform, statistics, time
from pathlib import Path
import numpy as np
import torch
from .analytic_cut import GeometrySpec, TEACHER_KIND, vertical_cut_truth
from .m4_experiment import split_by_geometry, dataset_digest
from .m10_experiment import centered_dataset, centered_voxel, make_model, fit_model
from .m10_decision import gn_step, native_plane_c_and_tangent, objective
from .m11_anchor_cache import AnalyticAnchorLedger
from .m12_value_policy import ObservableRisk, observe_risk, select_thresholds
from .m4_lite_model import num_real_parameters
from .m8_bounded_adapter import BoundedAtomAdapter

MODEL_NAMES=('w6_m7_base','w5_voxel_deeponet')
ANCHOR_HEIGHTS={0:(),1:(0.,),2:(-.3,.3)}
ARCHIVE_TRAINING_DENIED=True


def specs_from_dataset(data):
    groups={}
    for row in data[4]:
        gid=row['geometry_id']
        if gid not in groups:
            shape=row['shape']
            spec=GeometrySpec(row['family'],tuple(shape['center']),tuple(shape['axes']),shape['density'])
            if spec.geometry_id!=gid:raise ValueError('geometry identity collision')
            groups[gid]=spec
    return groups


def tasks_for_geometry(spec:GeometrySpec, *,seed:int,target_count:int=8,goal_shift:float=.12):
    if target_count<2 or target_count%2 or not 0<goal_shift<=.2:
        raise ValueError('even positive target budget required')
    # Geometry SHA gives deterministic, order-independent target split.
    generator=np.random.default_rng(seed+900001+int(spec.geometry_id[:12],16))
    heights=generator.uniform(-.55,.55,target_count)
    directions=np.array([1.,-1.]*(target_count//2),dtype=np.float64)
    generator.shuffle(directions)
    tasks=[]
    for h,direction in zip(heights,directions):
        native,tangent=native_plane_c_and_tangent(spec,float(h))
        goal=vertical_cut_truth(spec,float(h+goal_shift*direction))[1]
        tasks.append({'h':float(h),'c':native,'tangent':tangent,'goal':goal,
                      'direction':int(direction),'world_h':spec.center[2]+spec.axes[2]*float(h)})
    return tasks


def _simulated_policy_rows(model,D,spec,tasks,*,k:int,mode:str='decision_only'):
    """Independent policy path; at most K analytic r support calls per geometry.

    Final r/J truth calls are scoring-only, excluded from online query budget.
    The baseline and other policies are evaluated in *separate* counterfactual
    sessions: actual experiment total calls exceed each single deployed path.
    """
    if k not in ANCHOR_HEIGHTS or mode not in ('decision_only','bounded_atoms'):
        raise ValueError('unsupported K or mode')
    if mode=='bounded_atoms' and spec is None:raise ValueError('missing geometry')
    ledger=AnalyticAnchorLedger(model,D,spec)
    observations=[ledger.obtain_r(h,source=TEACHER_KIND) for h in ANCHOR_HEIGHTS[k]]
    adapter=None
    if mode=='bounded_atoms':
        if not hasattr(model,'monomials'):
            raise ValueError('bounded atomic fit requires M7 model')
        controls=torch.tensor([o.c_native for o in observations],dtype=D.dtype).reshape(1,k,10)
        moments=torch.tensor([o.r_design for o in observations],dtype=D.dtype).reshape(1,k,10)
        adapter=BoundedAtomAdapter(model,D,ledger.z,controls,moments,source='ANALYTIC_P0')
    cases=[]
    for task in tasks:
        h=task['h'];goal=task['goal']
        if mode=='decision_only':
            entry=ledger.decision_input(h,{0:'baseline',1:'one_anchor',2:'two_anchors'}[k])
            use_r,use_J=entry.r_for_step,entry.Jc_surrogate
            fallback=entry.fallback_reason is not None
            correction=entry.correction_used
        else:
            c=torch.tensor(task['c'],dtype=D.dtype).reshape(1,10)
            with torch.no_grad():
                use_r=adapter.predict(c)[0].double().numpy()
                use_J=adapter.jacobian(c)[0].double().numpy()
            fallback=False;correction=k>0
        step=gn_step(use_r,use_J,task['tangent'],goal)
        r_true=vertical_cut_truth(spec,h)[1]
        r_after=vertical_cut_truth(spec,h+step)[1]
        before=objective(r_true,goal);after=objective(r_after,goal)
        cases.append({'h':h,'goal_direction':task['direction'],
                      'accepted':int(after<before-1e-12),
                      'true_decrease':float(before-after),
                      'predicted_step':float(step),
                      'used_r_mae':float(np.mean(np.abs(use_r-r_true))),
                      'correction_used':int(correction),'fallback':int(fallback)})
    if ledger.analytic_oracle_calls!=k or ledger.geometry_encoder_calls!=1:
        raise AssertionError('oracle/encoder cost violated')
    cost={'selection_analytic_r_calls':ledger.analytic_oracle_calls,
          'encoder_calls':ledger.geometry_encoder_calls,
          'prediction_moment_calls':ledger.surrogate_moment_calls,
          'prediction_jacobian_calls':ledger.surrogate_jacobian_calls}
    return {'acceptance':sum(q['accepted'] for q in cases)/len(cases),
            'mean_decrease':statistics.mean(q['true_decrease'] for q in cases),
            'mean_r_mae':statistics.mean(q['used_r_mae'] for q in cases),
            'fallback_rate':statistics.mean(q['fallback'] for q in cases),
            'calls':cost,'cases':cases,
            'necessary_material_gate':'M11 decision-only residual guard' if mode=='decision_only'
              else 'M8 nonnegative bounded-atom-weight representation'}


def _geometry_experiment(model,spec,*,seed:int,target_count:int=8,
                         compare_atoms:bool=True):
    D=centered_voxel(spec,8).unsqueeze(0).float()
    tasks=tasks_for_geometry(spec,seed=seed,target_count=target_count)
    # Only model and external-goal information reaches observe_risk.
    with torch.no_grad():z=model.encode_geometry(D).detach()
    risk_started=time.perf_counter()
    observable=observe_risk(model,z,D,np.stack([x['c'] for x in tasks]),
                            np.stack([x['tangent'] for x in tasks]),
                            np.stack([x['goal'] for x in tasks]),
                            np.asarray([x['world_h'] for x in tasks]))
    risk_ms=(time.perf_counter()-risk_started)*1000.
    policies={str(k):_simulated_policy_rows(model,D,spec,tasks,k=k) for k in range(3)}
    atom_policies=({str(k):_simulated_policy_rows(model,D,spec,tasks,k=k,mode='bounded_atoms')
                    for k in range(3)} if compare_atoms else None)
    return {'geometry_id':spec.geometry_id,'family':spec.family,
            'observable':dataclasses.asdict(observable),
            'risk_cpu_ms':risk_ms,
            'risk_extra_surrogate_r_and_J_evaluations':len(tasks),
            'risk_proxy_cell_mass_evaluations':len(tasks)+1,
            'decision_only':policies,'bounded_atoms':atom_policies,
            'task_count':len(tasks),
            'offline_scoring_truth_used_only_after_selection':True,
            'offline_benchmark_executed_all_K_separately':True}


def _family_scores(results, *,choice=None,policy=None,mode='decision_only'):
    if mode not in ('decision_only','bounded_atoms'):raise ValueError('mode')
    runs=[]; total_calls=0; correction=0; fallback=0; n=0; gain=[];by_direction={1:[], -1:[]}
    kcounts=collections.Counter()
    for row in results:
        k=choice if choice is not None else policy.select(ObservableRisk(**row['observable']))
        if k not in (0,1,2):raise ValueError('bad K')
        item=row[mode][str(k)]
        if item is None:raise ValueError('no atomic control')
        kcounts[k]+=1
        total_calls+=item['calls']['selection_analytic_r_calls']
        cases=item['cases']
        for case in cases:
            n+=1;correction+=case['correction_used'];fallback+=case['fallback'];gain.append(case['true_decrease'])
            runs.append(case['accepted'])
            by_direction[case['goal_direction']].append(case['accepted'])
    return {'acceptance':sum(runs)/n,
            'positive_goal_acceptance':statistics.mean(by_direction[1]),
            'negative_goal_acceptance':statistics.mean(by_direction[-1]),
            'mean_true_decrease':statistics.mean(gain),
            'selection_r_only_queries':total_calls,'selection_calls_per_target':total_calls/n,
            'geometries_by_K':{str(k):kcounts[k] for k in (0,1,2)},
            'correction_used_fraction':correction/n,'guard_fallback_fraction':fallback/n,
            'n_cases':n,'n_geometries':len(results)}


def run(*,seeds=(107,109,113),steps=100,per_family=20,target_count=8,
        unit_query_cost=.2,models=MODEL_NAMES):
    if (not seeds or len(set(seeds))!=len(seeds) or steps<1 or
        per_family<6 or target_count<2 or target_count%2 or unit_query_cost<0 or
        len(set(models))!=len(models) or any(x not in MODEL_NAMES for x in models)):
        raise ValueError('invalid experiment setup')
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    records=[]; clock=time.perf_counter()
    for seed in seeds:
        train_all=centered_dataset(('box','sphere'),per_family=per_family,seed=seed)
        heldout=centered_dataset(('ellipsoid',),per_family=per_family,seed=seed+1)
        # Independent policy tuning on fresh development geometries of already
        # seen families, not on the checkpoint-validation or heldout identities.
        development=centered_dataset(('box','sphere'),per_family=max(2,per_family//5),seed=seed+2000)
        fit,val,split=split_by_geometry(train_all,seed,max(1,per_family//5))
        fit_ids={m['geometry_id'] for m in fit[4]}
        val_ids={m['geometry_id'] for m in val[4]}
        dev_ids=set(specs_from_dataset(development))
        test_ids=set(specs_from_dataset(heldout))
        if any(a&b for a,b in ((fit_ids,val_ids),(fit_ids,dev_ids),(val_ids,dev_ids),
                                (fit_ids,test_ids),(val_ids,test_ids),(dev_ids,test_ids))):
            raise ValueError('geometry identity leaked between train/selection/test')
        case={'seed':seed,'source_frozen_train_sha256':dataset_digest(train_all),
              'policy_calibration_source_sha256':dataset_digest(development),
              'heldout_tensor_sha256':dataset_digest(heldout),
              'fitting_geometries':len(fit_ids),'checkpoint_validation_geometries':len(val_ids),
              'policy_development_geometries':len(dev_ids),'heldout_geometries':len(test_ids),
              'model_runs':{}}
        for name in models:
            model=make_model(name,seed)
            training=fit_model(model,name,fit,val,seed=seed,steps=steps)
            model.eval();do_atoms=name=='w6_m7_base'
            dev=[_geometry_experiment(model,shape,seed=seed+2000,target_count=target_count,
                                      compare_atoms=do_atoms) for shape in specs_from_dataset(development).values()]
            calibration_rows=[{'geometry_id':x['geometry_id'],'risk_score':x['observable']['score'],
                     'cases':x['task_count'],'acceptances':tuple(x['decision_only'][str(k)]['acceptance'] for k in (0,1,2))}
                              for x in dev]
            policy,calibration=select_thresholds(calibration_rows,price=unit_query_cost,seed=seed)
            held=[_geometry_experiment(model,shape,seed=seed+3000,target_count=target_count,
                                     compare_atoms=do_atoms) for shape in specs_from_dataset(heldout).values()]
            results={str(k):_family_scores(held,choice=k) for k in (0,1,2)}
            results['voi_frozen']=_family_scores(held,policy=policy)
            atom_results=({str(k):_family_scores(held,choice=k,mode='bounded_atoms') for k in (0,1,2)}
                          if do_atoms else None)
            if atom_results is not None:
                atom_results['voi_frozen']=_family_scores(held,policy=policy,mode='bounded_atoms')
            case['model_runs'][name]={'parameters_real':num_real_parameters(model),
                'training':training,'frozen_policy':dataclasses.asdict(policy),
                'calibration':calibration,'policy_calibration_receipts':calibration_rows,
                'heldout':results,'physical_bounded_atom_comparison':atom_results,
                'heldout_per_geometry':held,
                'validation_policy_and_heldout_no_overlap':True}
        records.append(case)
    models_summary={}
    for name in models:
        models_summary[name]={}
        for key in ('0','1','2','voi_frozen'):
            rows=[r['model_runs'][name]['heldout'][key] for r in records]
            models_summary[name][key]={
                'mean_acceptance':statistics.mean(x['acceptance'] for x in rows),
                'mean_online_r_oracle_per_target':statistics.mean(x['selection_calls_per_target'] for x in rows),
                'mean_true_decrease':statistics.mean(x['mean_true_decrease'] for x in rows),
                'mean_positive_goal_acceptance':statistics.mean(x['positive_goal_acceptance'] for x in rows),
                'mean_negative_goal_acceptance':statistics.mean(x['negative_goal_acceptance'] for x in rows),
                'mean_calibration_utility_accept_minus_price':statistics.mean(
                    x['acceptance']-unit_query_cost*x['selection_calls_per_target'] for x in rows),
                'individual_seed_acceptance':[x['acceptance'] for x in rows],
                'individual_seed_K_mix':[x['geometries_by_K'] for x in rows]}
    return {'schema':'W6_M12_VALIDATION_ONLY_VOI_ANALYTIC_P0_V1',
            'status':'ANALYTIC_P0_ONLY_W2_RELEASE_BLOCKED',
            'seeds':list(seeds),'steps_max':steps,'per_family':per_family,
            'target_count_per_geometry':target_count,'goal_directions':'+0.12/-0.12 mixed per geometry',
            'calibration_price_abstract_per_oracle_per_target':unit_query_cost,
            'calibration_dev_data_uses_real_analytic_oracles':True,
            'selection_features':'raw D, model r/J, declared goal_r, cellwise vertical mass proxy only',
            'selection_teacher_provenance':'R_ONLY_ANALYTIC_CONTINUUM_P0_NOT_W2',
            'risk_feature_calculation_is_additional_surrogate_cost':True,
            'risk_requires_goals_for_all_predeclared_target_controls':True,
            'native_W2_admitted_labels':0,'native_W2_calls':0,
            'model_params_rule':'W5/W6 matched original 13939 vs 13448 real DOFs',
            'training':'Adam lr .003 batch8, r+0.5J, whole geometry checkpoint validation',
            'physical_adapter':'M8 bounded nonnegative sampled atoms; not CAD proof',
            'offline_benchmark_actual_queries_more_than_single_policy':True,
            'online_queries_accounted_by_each_policy_independently':True,
            'goal_and_poststep_analytic_evaluations_separate_from_selection_budget':True,
            'not_a_real_native_computation_time_or_10D_optimizer_test':True,
            'python':platform.python_version(),'torch':torch.__version__,'device':'cpu','cpu_threads':1,
            'elapsed_total_seconds':time.perf_counter()-clock,
            'seed_records':records,'aggregate':models_summary}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--seeds',default='107,109,113')
    ap.add_argument('--steps',type=int,default=100)
    ap.add_argument('--per-family',type=int,default=20)
    ap.add_argument('--target-count',type=int,default=8)
    ap.add_argument('--oracle-price',type=float,default=.2)
    ap.add_argument('--models',default=','.join(MODEL_NAMES))
    ap.add_argument('--output',required=True)
    args=ap.parse_args()
    result=run(seeds=tuple(int(x) for x in args.seeds.split(',')),
               steps=args.steps,per_family=args.per_family,
               target_count=args.target_count,unit_query_cost=args.oracle_price,
               models=tuple(args.models.split(',')))
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'schema':result['schema'],'seeds':result['seeds'],
          'elapsed_total_seconds':result['elapsed_total_seconds'],'aggregate':result['aggregate']},
          indent=2,allow_nan=False))

if __name__=='__main__':main()
