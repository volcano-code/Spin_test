"""W6 M10: source-matched W5/W6 training and analytic 1D decision ablations.

Never uses W2 excluded H8f archives; the analytic teacher is independently
closed-form on boxes/spheres/ellipsoids and is NOT a native Cherchi certificate.
Run (from repo root):
  python -m research.NeuralMoments.models.pcraft_ufno.m10_experiment \
    --seeds 67,71,73 --steps 100 --output /path/within/W6/m10_seed67_71_73.json
"""
from __future__ import annotations
import argparse, copy, hashlib, json, math, platform, statistics, time
from pathlib import Path
import numpy as np
import torch
from .analytic_cut import (GeometrySpec, sample_dataset, vertical_cut_truth,
                           assert_disjoint_family_splits)
from .m4_experiment import dataset_digest, split_by_geometry
from .m7_realizable import RealizableUFNOMoment
from .m10_w5_readonly import W5VoxelDeepONet
from .m10_decision import (choose_and_evaluate, predicted_backtrack_decision,
                           native_plane_c_and_tangent, gn_step, objective, STRATEGIES)
from .m4_lite_model import num_real_parameters

MODEL_NAMES=('w6_m7_base','w6_m7_directional','w5_voxel_deeponet')
SOURCE_PIN='0bcc187b3005478baa586a6d6f450e73811ca342'
W6_PARENT='42d9a3b10df7d12d97a7db6e076d2306b8f0c6ae'
W5_HEAD_OBSERVED='33363d833d0623627afb2a7d5eff5dde5c46dffc'
W5_ENCODER_BLOB='317bcf1c3965326ee56b5948b80b01bbd052b592'
W5_DEEPONET_BLOB='7aa363769c0baf9f843d50e268164e761b566977'
W2_ELIGIBLE_COUNT=0


def centered_voxel(spec:GeometrySpec,n:int=8):
    """The same center-cell four-channel construction as W5 M13 (read-only)."""
    if n<8:raise ValueError('n >= 8')
    t=np.linspace(-1+1/n,1-1/n,n,dtype=np.float64)
    xyz=np.stack(np.meshgrid(t,t,t,indexing='ij'),axis=-1)
    u=(xyz-np.asarray(spec.center))/np.asarray(spec.axes)
    level=np.max(np.abs(u),axis=-1)-1 if spec.family=='box' else np.sqrt((u*u).sum(-1))-1
    occ=(level<=0).astype(np.float32)
    return torch.from_numpy(np.stack((occ*spec.density,occ,level.astype(np.float32),
                                       np.exp(-8*np.abs(level)).astype(np.float32)),axis=0))


def centered_dataset(families,*,per_family:int,seed:int,grid_size:int=8,queries=2):
    """Recreate frozen primitive identities/controls; replace only voxel sampling.

    No label/teacher r or J enters preprocessing, only primitive used to create
    the analytic P0 geometry. Under both models this is exactly the same D.
    """
    old=sample_dataset(tuple(families),per_family=per_family,seed=seed,
                       grid_size=grid_size,queries_per_geometry=queries)
    rng=np.random.default_rng(seed)
    d=[];meta=[];idx=0
    for family in families:
        for _ in range(per_family):
            center=tuple(float(x) for x in rng.uniform(-.1,.1,3))
            if family=='sphere':
                a=float(rng.uniform(.46,.73));axes=(a,a,a)
            else:
                a=tuple(float(x) for x in rng.uniform(.46,.73,3))
                axes=(a[0],a[1]*.8,a[2]*1.1) if family=='ellipsoid' else a
            spec=GeometrySpec(family,center,axes)
            vox=centered_voxel(spec,grid_size)
            for j in range(queries):
                h=float(rng.uniform(-.65,.65))
                native,r,J=vertical_cut_truth(spec,h)
                if old[4][idx]['geometry_id']!=spec.geometry_id:
                    raise AssertionError('same exact frozen geometry identities required')
                if not np.allclose(native,old[1][idx].double().numpy(),atol=2e-8):
                    raise AssertionError('native control changed')
                if not np.allclose(r,old[2][idx].double().numpy(),atol=2e-7):
                    raise AssertionError('teacher moment changed')
                d.append(vox)
                meta.append({'family':family,'geometry_id':spec.geometry_id,
                    'shape':{'center':center,'axes':axes,'density':spec.density},
                    'h_local':h,'query_index':j,'source':'ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI'})
                idx+=1
    if idx!=len(old[4]):raise AssertionError('dataset length mismatch')
    return torch.stack(d),old[1],old[2],old[3],meta


def make_model(name:str,seed:int):
    if name not in MODEL_NAMES:raise ValueError('unknown model')
    torch.manual_seed(seed)
    if name.startswith('w6_'):
        return RealizableUFNOMoment(temperature=.12,points_per_axis=6,hidden=32,grid_size=8)
    return W5VoxelDeepONet()


def _tangents(meta):
    rows=[]
    for entry in meta:
        shape=entry['shape'];spec=GeometrySpec(entry['family'],tuple(shape['center']),tuple(shape['axes']),shape['density'])
        rows.append(native_plane_c_and_tangent(spec,entry['h_local'])[1])
    return torch.tensor(np.stack(rows),dtype=torch.float32)


def evaluate_error(model, data):
    D,c,r,J,meta=data
    model.eval()
    with torch.no_grad():
        z=model.encode_geometry(D).detach()
        pred=model.moment(z,c).detach()
        predicted_J=model.jacobian(z,c).detach()
    delta=_tangents(meta)
    drdh=torch.einsum('bij,bj->bi',predicted_J,delta)
    truth_drdh=torch.einsum('bij,bj->bi',J,delta)
    return {'r_mae':float((pred-r).abs().mean()),
            'J_mae':float((predicted_J-J).abs().mean()),
            'drdh_mae':float((drdh-truth_drdh).abs().mean()),
            'r_relative_l2':float((pred-r).norm()/r.norm().clamp_min(1e-12)),
            'J_relative_l2':float((predicted_J-J).norm()/J.norm().clamp_min(1e-12))}


def fit_model(model,name,train,valid,*,seed,steps=100,extra_directional_weight=2.,
              batch_size=8,patience=5):
    if steps<1 or patience<1 or batch_size<1 or extra_directional_weight<0:
        raise ValueError('invalid training budget')
    # Deliberately identical W5 M13 sampler + lr/checkpoint criterion.
    g=torch.Generator().manual_seed(seed+313)
    schedule=torch.randint(len(train[0]),(steps,batch_size),generator=g)
    tangents=_tangents(train[4])
    opt=torch.optim.Adam(model.parameters(),lr=.003)
    best=float('inf');best_step=0;best_state=copy.deepcopy(model.state_dict())
    history=[];stale=0
    start=time.perf_counter()
    for step,idx in enumerate(schedule,1):
        model.train()
        d,c,r,J=(x[idx] for x in train[:4])
        z=model.encode_geometry(d)
        predicted=model.moment(z,c)
        predicted_J=model.jacobian(z,c)
        loss_r=(predicted-r).square().mean()
        loss_j=(predicted_J-J).square().mean()
        loss=loss_r+.5*loss_j
        if name=='w6_m7_directional':
            t=tangents[idx]
            predicted_drdh=torch.einsum('bij,bj->bi',predicted_J,t)
            oracle_drdh=torch.einsum('bij,bj->bi',J,t)
            loss=loss+extra_directional_weight*(predicted_drdh-oracle_drdh).square().mean()
        if not bool(torch.isfinite(loss)):raise FloatingPointError('nonfinite loss')
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        if step%10==0 or step==steps:
            val=evaluate_error(model,valid)
            score=val['r_mae']+.25*val['J_mae']
            history.append({'step':step,'validation_score':score})
            if score<best-1e-7:
                best=score;best_step=step;best_state=copy.deepcopy(model.state_dict());stale=0
            else:stale+=1
            if stale>=patience:break
    duration=time.perf_counter()-start
    model.load_state_dict(best_state)
    return {'selected_step':best_step,'steps_executed':step,'max_steps':steps,
        'training_cpu_seconds':duration,'val_score':best,'history':history,
        'minibatch_schedule_sha256':hashlib.sha256(schedule.numpy().tobytes()).hexdigest(),
        'directional_loss_weight':extra_directional_weight if name=='w6_m7_directional' else 0.,
        'train_label_counts':{'r':len(train[0]),'J':len(train[0]),'extra_oracle':0},
        'hardware':'CPU_1_THREAD','optimization':'Adam_lr0.003_batch8_validation_only_early_stop'}


def _aggregate_dict(rows, keys):
    return {k:{'mean':statistics.mean(x[k] for x in rows),
               'sample_sd':statistics.stdev(x[k] for x in rows) if len(rows)>1 else None}
            for k in keys}


def evaluate_decisions(model, heldout, *, goal_offset=.12, trust=.12,damping=.01):
    """No model updates or policy selection using heldout oracle poststep truth."""
    D,c,r,J,meta=heldout
    model.eval()
    with torch.no_grad():
        z=model.encode_geometry(D).detach()
        prediction=model.moment(z,c).detach().cpu().double().numpy()
        jac=model.jacobian(z,c).detach().cpu().double().numpy()
    per_policy={p:[] for p in STRATEGIES}
    counterfactual=[]
    for i,entry in enumerate(meta):
        data=entry['shape']
        spec=GeometrySpec(entry['family'],tuple(data['center']),tuple(data['axes']),data['density'])
        h=entry['h_local']
        goal=vertical_cut_truth(spec,h+goal_offset)[1]
        _,dc=native_plane_c_and_tangent(spec,h)
        # Counterfactual oracle substitutions are DIAGNOSTICS only. They never
        # feed a real no-oracle policy's decision; they consume W0 analytic
        # reference r/J, and would require real teacher calls in production.
        r_truth=r[i].detach().double().cpu().numpy()
        J_truth=J[i].detach().double().cpu().numpy()
        g_truth=float((r_truth-goal)@(J_truth@dc))
        g_both=float((prediction[i]-goal)@(jac[i]@dc))
        g_pred_r_true_J=float((prediction[i]-goal)@(J_truth@dc))
        g_true_r_pred_J=float((r_truth-goal)@(jac[i]@dc))
        def sign_mismatch(g):
            return bool(g*g_truth<0)
        true_r_step=gn_step(r_truth,jac[i],dc,goal,trust=trust,damping=damping)
        true_J_step=gn_step(prediction[i],J_truth,dc,goal,trust=trust,damping=damping)
        before=objective(r_truth,goal)
        counterfactual.append({
           'g_truth':g_truth,'g_both_predicted':g_both,
           'g_predicted_r_true_J':g_pred_r_true_J,
           'g_true_r_predicted_J':g_true_r_pred_J,
           'sign_mismatch_both':sign_mismatch(g_both),
           'sign_mismatch_predicted_r_true_J':sign_mismatch(g_pred_r_true_J),
           'sign_mismatch_true_r_predicted_J':sign_mismatch(g_true_r_pred_J),
           'true_r_predicted_J_candidate_accepted':bool(objective(vertical_cut_truth(spec,h+true_r_step)[1],goal)<before-1e-12),
           'predicted_r_true_J_candidate_accepted':bool(objective(vertical_cut_truth(spec,h+true_J_step)[1],goal)<before-1e-12),
        })
        # Audit r/J are available but no no-oracle selection function takes them.
        for policy in STRATEGIES:
            if policy=='predicted_backtrack':
                record=predicted_backtrack_decision(spec,h,z[i:i+1],model,goal,
                                                   trust=trust,damping=damping)
            else:
                record=choose_and_evaluate(spec,h,prediction[i],jac[i],goal,
                         strategy=policy,oracle_r=r[i].double().numpy(),
                         oracle_j=J[i].double().numpy(),trust=trust,damping=damping)
            per_policy[policy].append(record)
    metrics={}
    for name,records in per_policy.items():
        metrics[name]={
            'accepted_fraction':sum(x.actual_accept for x in records)/len(records),
            'mean_true_objective_drop':statistics.mean(x.actual_improvement for x in records),
            'mean_true_loss_after':statistics.mean(x.actual_loss_after for x in records),
            'mean_abs_oracle_step_error':statistics.mean(x.oracle_step_abs_error for x in records),
            'mean_oracle_objective_gap':statistics.mean(x.oracle_step_objective_gap for x in records),
            'gradient_sign_error_fraction':sum(x.gradient_sign_wrong for x in records)/len(records),
            'direction_sign_error_fraction':sum(x.direction_sign_wrong for x in records)/len(records),
            'false_surrogate_descent_fraction':sum(x.predicted_false_descent for x in records)/len(records),
            'trust_saturated_fraction':sum(x.trust_clipped for x in records)/len(records),
            'selection_additional_oracle_calls':sum(x.additional_selection_oracle_calls for x in records),
            'selection_additional_surrogate_calls':sum(x.additional_surrogate_moment_calls for x in records),
            'mean_policy_rejections':statistics.mean(x.predicted_rejections for x in records),
            'total_cases':len(records),
            'failed_cases':sum(not x.actual_accept for x in records),
            'failed_with_wrong_gradient_count':sum((not x.actual_accept) and x.gradient_sign_wrong for x in records),
            'failed_with_right_gradient_count':sum((not x.actual_accept) and (not x.gradient_sign_wrong) for x in records),
            'failed_with_saturated_trust_count':sum((not x.actual_accept) and x.trust_clipped for x in records),
            'successful_despite_wrong_gradient_count':sum(x.actual_accept and x.gradient_sign_wrong for x in records),
            'oracle_calls_per_candidate':sum(x.additional_selection_oracle_calls for x in records)/len(records),
            'surrogate_extra_calls_per_candidate':sum(x.additional_surrogate_moment_calls for x in records)/len(records),
        }
    attribution={
       'sign_error_fraction_full_proxy':sum(x['sign_mismatch_both'] for x in counterfactual)/len(counterfactual),
       'sign_error_fraction_predicted_r_true_J':sum(x['sign_mismatch_predicted_r_true_J'] for x in counterfactual)/len(counterfactual),
       'sign_error_fraction_true_r_predicted_J':sum(x['sign_mismatch_true_r_predicted_J'] for x in counterfactual)/len(counterfactual),
       'counterfactual_true_r_predicted_J_acceptance':sum(x['true_r_predicted_J_candidate_accepted'] for x in counterfactual)/len(counterfactual),
       'counterfactual_predicted_r_true_J_acceptance':sum(x['predicted_r_true_J_candidate_accepted'] for x in counterfactual)/len(counterfactual),
       'mean_abs_gradient_error_full':statistics.mean(abs(x['g_both_predicted']-x['g_truth']) for x in counterfactual),
       'mean_abs_gradient_error_predicted_r_only':statistics.mean(abs(x['g_predicted_r_true_J']-x['g_truth']) for x in counterfactual),
       'mean_abs_gradient_error_predicted_J_only':statistics.mean(abs(x['g_true_r_predicted_J']-x['g_truth']) for x in counterfactual),
       'note':'oracle substitutions are offline attribution only; cannot be used for model-only selection without trusted current r/J',
    }
    return {'metrics':metrics,'oracle_substitution_attribution':attribution,
        'failure_cases':[
          {'geometry_id':meta[i]['geometry_id'],'h_local':meta[i]['h_local'],
           'base_step':record.step,'gradient_sign_wrong':record.gradient_sign_wrong,
           'direction_sign_wrong':record.direction_sign_wrong,
           'oracle_gap':record.oracle_step_objective_gap}
          for i,record in enumerate(per_policy['gn']) if not record.actual_accept],
        'policy_notes':{'gn':'W5 M13 exact regularized 1D baseline',
            'predicted_backtrack':'surrogate-only line search with charged warm model calls',
            'mass_sign_guard':'additional signed monotone mass prior specific to positive vertical cuts; no oracle calls',
            'checked_backtrack':'uses charged independent oracle r at candidates; not an acceleration claim'},
        'evaluation_only_oracle_reference_calls_excluded_from_selection_budget':True,
        'goal_analytic_reference_labels_per_model':len(meta),
        'current_analytic_reference_labels_per_model':len(meta),
        'query_accounting_note':'checked_backtrack counts only additional selection oracle calls; independent audit truth/goal references are separate; no native calls',
        'not_general_10d_solver':True}


def cpu_timing(model,data,*,repetitions=7):
    """Uncompiled CPU median timings, not native Faster/Cherchi solver cost."""
    import time
    D=data[0][:1]; c=data[1][:1]
    model.eval()
    with torch.no_grad():
        z=model.encode_geometry(D).detach()
        model.moment(z,c)
        model.jacobian(z,c)
        def measure(fn):
            for _ in range(3):fn()
            times=[]
            for _ in range(repetitions):
                t=time.perf_counter_ns();fn();times.append((time.perf_counter_ns()-t)*1e-6)
            return float(statistics.median(times))
        return {'encode_ms':measure(lambda:model.encode_geometry(D)),
                'cached_r_ms':measure(lambda:model.moment(z,c)),
                'cached_J_ms':measure(lambda:model.jacobian(z,c)),
                'repetitions':repetitions,'device':'cpu','thread_count':torch.get_num_threads(),
                'native_speedup_claim':False}


def run(*,seeds=(67,71,73),steps=100,per_family=20,trust=.12,damping=.01,
        extra_directional_weight=2.,models=MODEL_NAMES):
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    seeds=tuple(int(s) for s in seeds)
    models=tuple(models)
    if not seeds or len(seeds)!=len(set(seeds)) or not models or len(models)!=len(set(models)) or any(n not in MODEL_NAMES for n in models) or steps<1 or per_family<6:
        raise ValueError('invalid seeded protocol')
    param={name:num_real_parameters(make_model(name,seeds[0])) for name in models}
    if max(param.values())/min(param.values())>1.05:
        raise ValueError('trainable real parameter budget >5%')
    report={
        'schema':'W6_M10_ANALYTIC_P0_OPTIMIZATION_DECISION_V1',
        'source_pin':SOURCE_PIN,'W6_parent':W6_PARENT,'W5_observed':W5_HEAD_OBSERVED,
        'W5_source_blobs':{'voxel_spatial':W5_ENCODER_BLOB,'deeponet':W5_DEEPONET_BLOB},
        'truth':'INDEPENDENT_ANALYTIC_CONTINUUM_VERTICAL_PLANE_P0_NOT_NATIVE_CHERCHI',
        'W2_native_training_admitted':0,'W2_H8f_81_archived_used':False,
        'seeds':list(seeds),'models':list(models),'trainable_real_parameters':param,
        'config':{'steps_max':steps,'per_family':per_family,'grid_size':8,
                  'train_geometries':per_family*2,'validation_geometries':2*(per_family//5),
                  'heldout_ellipsoid_geometries':per_family,
                  'heldout_controls_per_geometry':2,'goal_h_offset':.12,
                  'trust_radius':trust,'GN_damping':damping,
                  'directional_supervision_weight':extra_directional_weight,
                  'backtrack_factors':[1.,.5,.25,.125]},
        'same_input_for_both':'four-channel centered-cell analytic voxel D; geometry identity from independent shape oracle',
        'same_training_labels_and_schedule':True,
        'train_data_families':['box','sphere'],'heldout_family':['ellipsoid'],
        'training_extra_native_oracle_calls':0,'device':'cpu','cpu_threads':torch.get_num_threads(),
        'torch_version':torch.__version__,'python_version':platform.python_version(),
        'no_real_native_J_training':True,'native_solver_verified':False,
        'policies':list(STRATEGIES),'cases':[],'aggregate':{},
    }
    for seed in seeds:
        source=centered_dataset(('box','sphere'),per_family=per_family,seed=seed)
        heldout=centered_dataset(('ellipsoid',),per_family=per_family,seed=seed+1)
        assert_disjoint_family_splits(source,heldout)
        train,val,split=split_by_geometry(source,seed,validation_geometries_per_family=max(1,per_family//5))
        sha_train=dataset_digest(source);sha_test=dataset_digest(heldout)
        report_case={'seed':seed,'train_sha256':sha_train,'heldout_sha256':sha_test,
                     'split':split,'models':{}}
        for name in models:
            model=make_model(name,seed)
            tr=fit_model(model,name,train,val,seed=seed,steps=steps,
                         extra_directional_weight=extra_directional_weight)
            err=evaluate_error(model,heldout)
            decisions=evaluate_decisions(model,heldout,trust=trust,damping=damping)
            report_case['models'][name]={'training':tr,'heldout':err,'decision':decisions,'cpu_timing':cpu_timing(model,heldout)}
        report['cases'].append(report_case)
    for name in models:
        rows=[c['models'][name] for c in report['cases']]
        report['aggregate'][name]={'heldout':_aggregate_dict([r['heldout'] for r in rows],('r_mae','J_mae','drdh_mae')),
            'cpu_timing':_aggregate_dict([r['cpu_timing'] for r in rows],('encode_ms','cached_r_ms','cached_J_ms')),
            'oracle_substitution_attribution':_aggregate_dict([r['decision']['oracle_substitution_attribution'] for r in rows],
                 ('sign_error_fraction_full_proxy','sign_error_fraction_predicted_r_true_J',
                  'sign_error_fraction_true_r_predicted_J',
                  'counterfactual_true_r_predicted_J_acceptance',
                  'counterfactual_predicted_r_true_J_acceptance',
                  'mean_abs_gradient_error_full',
                  'mean_abs_gradient_error_predicted_r_only',
                  'mean_abs_gradient_error_predicted_J_only')),
            'decisions':{policy:_aggregate_dict([r['decision']['metrics'][policy] for r in rows],
                 ('accepted_fraction','mean_true_objective_drop','mean_oracle_objective_gap',
                  'gradient_sign_error_fraction','direction_sign_error_fraction',
                  'false_surrogate_descent_fraction','trust_saturated_fraction',
                  'selection_additional_oracle_calls','selection_additional_surrogate_calls',
                  'failed_with_wrong_gradient_count','failed_with_right_gradient_count'))
                    for policy in STRATEGIES}}
    report['limitations']=[
        'New experiment from fresh randomly initialized models; no pretrained original external P-CRAFT weight reproduction',
        'Oracle goal shape h+.12 is a controlled 1D analytic problem, not general CAD or a 10D Spin native optimization problem',
        'True poststep moment oracle is evaluation-only for non-checked strategies, but checked backtracking calls are charged',
        'Trust/damping/policy settings predeclared; no heldout tuning permitted',
        'Equal supervised teacher r,J labels; directional arm reuses same J, no extra labels',
        'No W2 teacher admissible r/J, no real optimizer speedup, GPU benchmarking or smooth native branch certificate',
        'Mass sign guard uses monotonic property only of positive vertical continuum cut; not deployable for arbitrary quadrics',
    ]
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--seeds',default='67,71,73')
    p.add_argument('--steps',type=int,default=100)
    p.add_argument('--per-family',type=int,default=20)
    p.add_argument('--trust',type=float,default=.12)
    p.add_argument('--damping',type=float,default=.01)
    p.add_argument('--directional-weight',type=float,default=2.0)
    p.add_argument('--models',default=','.join(MODEL_NAMES))
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    result=run(seeds=tuple(map(int,a.seeds.split(','))),steps=a.steps,
               per_family=a.per_family,trust=a.trust,damping=a.damping,
               extra_directional_weight=a.directional_weight,
               models=tuple(a.models.split(',')))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'path':str(a.output),'aggregate':result['aggregate'],'seeds':result['seeds']},indent=2))
if __name__=='__main__':main()
