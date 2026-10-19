"""W5 M8: genuinely same four-channel analytic P0 model training and comparison.

Requires an EXTERNAL W6 checkout/mirror with source Git blob hashes pinned by M7.
Writes only caller-named W5 output, never W6. No native Cherchi, CUDA, CAD
Boolean or optimization convergence evidence is claimed. Train/val/test split by
geometry ID and held-out family, not by different queries of the same geometry.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import platform
import statistics
import time
import numpy as np
import torch
from .m7_cross_framework import load_pinned_w6, W6_FILES, W6_PINNED_COMMIT
from .m8_voxel_models import VoxelMomentCandidate
from .m8_analytic_data import Shape, analytic_truth, dataset, sha_dataset, independent_family_check, TEACHER

FRAMEWORKS=('w5_deeponet_voxel','w5_geometry_mlp_voxel',
            'w6_pcraft_ufno','w6_local_no_fft','w6_convex_potential6')
W0_B=(1.,)*7+(2.,)*3
W2_PINNED_HEAD='bd87b26a926e260a4f3dd4df6b96ca561a49f6eb'
W2_M8_MANIFEST_SHA='fffb0d9286935bedaae3380e4171d7a4a9501442'


def model_for(name: str, seed: int, w6_modules):
    m4,m5=w6_modules
    torch.manual_seed(seed)
    if name=='w5_deeponet_voxel': return VoxelMomentCandidate('deeponet')
    if name=='w5_geometry_mlp_voxel': return VoxelMomentCandidate('geometry_mlp')
    if name=='w6_pcraft_ufno': return m4.LiteUFNOMoment('bottleneck',grid_size=8)
    if name=='w6_local_no_fft': return m4.LiteUFNOMoment('local_only',grid_size=8)
    if name=='w6_convex_potential6':
        return m5.ConvexPotentialMoment(variant='bottleneck',grid_size=8,
                                         points_per_axis=6,hidden=32,smoothing=.04)
    raise ValueError('unrecognized framework')


def real_parameters(model):
    return sum(p.numel()*(2 if p.is_complex() else 1) for p in model.parameters() if p.requires_grad)


def subset(data, indices):
    return tuple(x[indices] for x in data[:4])+([data[4][i] for i in indices],)


def split_fit_validation(train_all,seed:int,holdout_each:int):
    meta=train_all[4]
    rng=torch.Generator().manual_seed(seed+487)
    ids=set()
    for family in ('box','sphere'):
        ordered=list(dict.fromkeys(m['geometry_id'] for m in meta if m['family']==family))
        if not 0<holdout_each<len(ordered):raise ValueError('not enough training geometries')
        choices=torch.randperm(len(ordered),generator=rng).tolist()
        ids.update(ordered[i] for i in choices[:holdout_each])
    valid_indices=[i for i,m in enumerate(meta) if m['geometry_id'] in ids]
    train_indices=[i for i,m in enumerate(meta) if m['geometry_id'] not in ids]
    fit,valid=subset(train_all,train_indices),subset(train_all,valid_indices)
    return fit,valid


def check_training_readiness(w2_manifest:dict|None):
    """Historical 25 numeric r archives are NOT certified J labels/train samples.

    Never count pointwise archived moments as per-family train+test or as a
    smooth ambient derivative certificate. This runner is analytic-only.
    """
    if w2_manifest is not None:
        if not isinstance(w2_manifest,dict) or w2_manifest.get('schema')!='w2-cherchi-teacher-v2-pre-w0':
            raise ValueError('unknown W2 manifest; fail closed')
        if w2_manifest.get('training_samples')!=0 or w2_manifest.get('native_teacher_runs')!=0:
            raise ValueError('W2 manifest changed: review and independently verify before proceeding')
        evidence=w2_manifest.get('previously_recorded_native_evidence',{})
        if not isinstance(evidence,dict) or evidence.get('archived_samples_offline_independently_reverified')!=25:
            raise ValueError('historical archive status unrecognized')
    return {'teacher':TEACHER,'w2_head':W2_PINNED_HEAD,'w2_manifest_git_blob':W2_M8_MANIFEST_SHA,
            'historical_native_h8e_offline_r_reverified':25 if w2_manifest else None,
            'w2_native_new_runs':0,'w2_admissible_training_labels':0,
            'historical_r_observations_used_in_training':0,
            'native_J_neighborhood_certified':False,
            'real_cad_accuracy_claim_allowed':False}


def metrics(model, data):
    D,c,r,J,meta=data
    model.eval()
    with torch.no_grad():
        z=model.encode_geometry(D).detach()
        pred=model.moment(z,c).detach()
    pred_j=model.jacobian(z,c).detach()
    scales=torch.tensor([8.]+[16.]*3+[32.]*6,dtype=r.dtype)
    B=torch.tensor(W0_B,dtype=r.dtype)
    jq=pred_j/B
    dc=[]
    for info in meta:
        shape=info['shape'];z_world=shape['center'][2]+shape['axes'][2]*info['h_local']
        tangent=torch.zeros(10)
        tangent[0]=-shape['axes'][2]/(1+z_world*z_world)**1.5
        tangent[3]=-z_world*shape['axes'][2]/(1+z_world*z_world)**1.5
        dc.append(tangent)
    tangent=torch.stack(dc)
    proj_delta=torch.einsum('bij,bj->bi',pred_j-J,tangent)
    mass_unsafe=float((pred[:,0]<0).float().mean())
    return {'r_mae':float((pred-r).abs().mean()),
            'J_mae':float((pred_j-J).abs().mean()),
            'directional_mae':float(proj_delta.abs().mean()),
            'r_W0_normalized_mae':float(((pred-r).abs()/scales).mean()),
            'Jq_max_asymmetry':float((jq-jq.transpose(-1,-2)).abs().max()),
            'native_radial_max':float((pred_j@c.unsqueeze(-1)).abs().max()),
            'predicted_negative_mass_fraction':mass_unsafe}


def truth_decision_metrics(model, data, *, damping=.01, trust=.12):
    """Analytic independent 1D c(h) decision; NOT 10D real native Spin.

    Uses target at h+0.12 and the exact shape analytic oracle to measure
    candidate outcomes, not predictions from any network as true acceptance.
    """
    D,c,rs,Js,meta=data
    model.eval()
    with torch.no_grad():
        z=model.encode_geometry(D).detach()
        preds=model.moment(z,c).detach().numpy()
    jacs=model.jacobian(z,c).detach().numpy()
    gap=[];steps=[];accepted=0;before_total=0.;after_total=0.
    for i,info in enumerate(meta):
        spec=Shape(info['family'],tuple(info['shape']['center']),
                   tuple(info['shape']['axes']),info['shape']['density'])
        h=info['h_local'];goal=analytic_truth(spec,h+.12)[1]
        native_c,exact_r,exact_j=analytic_truth(spec,h)
        wh=spec.center[2]+spec.axes[2]*h
        dc=np.zeros(10);dc[0]=-spec.axes[2]/(1+wh*wh)**1.5
        dc[3]=-wh*spec.axes[2]/(1+wh*wh)**1.5
        def step(r,J):
            directional=J@dc
            return float(np.clip(-np.dot(directional,r-goal)/(np.dot(directional,directional)+damping),-trust,trust))
        oracle=step(exact_r,exact_j);candidate=step(preds[i],jacs[i])
        before=float(np.dot(exact_r-goal,exact_r-goal)/2.)
        post=analytic_truth(spec,h+candidate)[1]
        truthpost=analytic_truth(spec,h+oracle)[1]
        after=float(np.dot(post-goal,post-goal)/2.)
        oracle_after=float(np.dot(truthpost-goal,truthpost-goal)/2.)
        accepted+=int(after<before-1e-12)
        gap.append(after-oracle_after);steps.append(abs(candidate-oracle))
        before_total+=before;after_total+=after
    return {'one_step_candidate_accepted_fraction':accepted/len(meta),
            'one_step_height_abs_error':statistics.mean(steps),
            'signed_true_objective_gap':statistics.mean(gap),
            'mean_true_loss_before':before_total/len(meta),
            'mean_true_loss_candidate_after':after_total/len(meta),
            'validation_type':'INDEPENDENT_ANALYTIC_P0_1D_ONLY',
            'oracle_poststep_queries':2*len(meta)}


def train(model,fit,valid,*,seed,steps=100,lr=.003,batch=8,derivative_weight=.5,patience=5):
    schedule=torch.randint(len(fit[0]),(steps,batch),generator=torch.Generator().manual_seed(seed+313))
    opt=torch.optim.Adam(model.parameters(),lr=lr)
    best=float('inf');best_step=0;best_state=copy.deepcopy(model.state_dict());stale=0
    start=time.perf_counter();history=[]
    for step,indices in enumerate(schedule,1):
        model.train();data,c,ground_r,ground_j=(item[indices] for item in fit[:4])
        z=model.encode_geometry(data)
        pred=model.moment(z,c)
        loss_r=(pred-ground_r).square().mean()
        pred_j=model.jacobian(z,c)
        loss_j=(pred_j-ground_j).square().mean()
        loss=loss_r+derivative_weight*loss_j
        if not bool(torch.isfinite(loss)):raise FloatingPointError('nonfinite training loss')
        opt.zero_grad(set_to_none=True);loss.backward();opt.step()
        if step%10==0 or step==steps:
            val=metrics(model,valid)
            score=val['r_mae']+.25*val['J_mae']
            history.append({'step':step,'validation_score':score})
            if score<best-1e-7:
                best=score;best_step=step;best_state=copy.deepcopy(model.state_dict());stale=0
            else:stale+=1
            if stale>=patience:break
    duration=time.perf_counter()-start
    model.load_state_dict(best_state)
    return {'selected_step':best_step,'steps_executed':step,'max_steps':steps,
            'validation_score':best,'validation_only_early_stop':True,
            'history':history,'batch_schedule_sha256':hashlib.sha256(schedule.numpy().tobytes()).hexdigest(),
            'cpu_training_seconds':duration,'gpu_hours':0.,
            'fit_analytic_queries':len(fit[0]),'validation_analytic_queries':len(valid[0]),
            'loss':'MSE(r)+0.5*MSE(Jc)','lr':lr,'batch_size':batch}


def latency(model,data,*,repeats=7):
    D=data[0][:1];c=data[1][:1]
    model.eval()
    with torch.no_grad():
        z=model.encode_geometry(D).detach()
        model.moment(z,c)
        model.jacobian(z,c)
    def timed(fn):
        for _ in range(3):fn()
        vals=[]
        for _ in range(repeats):
            t=time.perf_counter_ns();fn();vals.append((time.perf_counter_ns()-t)*1e-6)
        return float(statistics.median(vals))
    with torch.no_grad():
        enc=timed(lambda:model.encode_geometry(D))
        warm=timed(lambda:model.moment(z,c))
        jac=timed(lambda:model.jacobian(z,c))
        cold=timed(lambda:model.moment(model.encode_geometry(D),c))
    budgets={str(q):{'one_encode_plus_q_r_and_J_ms':enc+q*(warm+jac),
                     'q_reencoding_r_and_J_ms':q*(enc+warm+jac),
                     'amortized_per_query_ms':(enc/q)+warm+jac}
             for q in (1,2,4,8,16,64)}
    return {'encoding_ms':enc,'warm_r_ms':warm,'warm_J_ms':jac,'cold_r_ms':cold,
            'query_budget_cost_model':budgets,'cost_is_additive_estimate_not_measured_solver':True,
            'cpu_threads':torch.get_num_threads(),'gpu_peak_vram_mb':None}


def execute(*,w6_root,seeds=(19,23,29),steps=100,per_family=20,
            repeats=7,names=FRAMEWORKS,w2_manifest=None):
    if not seeds or len(set(seeds))!=len(seeds) or per_family<5 or steps<1 or repeats<1:
        raise ValueError('invalid experiment budget')
    if not names or len(set(names))!=len(names) or any(n not in FRAMEWORKS for n in names):
        raise ValueError('unrecognized model selection')
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    modules=load_pinned_w6(w6_root)
    parameters={name:real_parameters(model_for(name,seeds[0],modules)) for name in names}
    ratio=max(parameters.values())/min(parameters.values())
    if ratio>1.05:raise ValueError('parameter ratio exceeds +5%')
    gate=check_training_readiness(w2_manifest)
    rows=[]
    for seed in seeds:
        all_train=dataset(('box','sphere'),per_family=per_family,seed=seed)
        holdout=dataset(('ellipsoid',),per_family=per_family,seed=seed+1)
        fit,valid=split_fit_validation(all_train,seed,max(1,per_family//5))
        split=independent_family_check(fit,valid,holdout)
        item={'seed':seed,'full_train_sha256':sha_dataset(all_train),
              'full_heldout_sha256':sha_dataset(holdout),'split':split,'models':{}}
        for name in names:
            model=model_for(name,seed,modules)
            record=train(model,fit,valid,seed=seed,steps=steps)
            item['models'][name]={'training':record,'heldout':metrics(model,holdout),
                                  'decision':truth_decision_metrics(model,holdout),
                                  'timing':latency(model,holdout,repeats=repeats)}
        rows.append(item)
    aggregate={}
    for name in names:
        samples=[s['models'][name] for s in rows]
        fields=(('heldout','r_mae'),('heldout','J_mae'),('heldout','directional_mae'),
                ('heldout','Jq_max_asymmetry'),('heldout','predicted_negative_mass_fraction'),
                ('decision','one_step_candidate_accepted_fraction'),
                ('decision','one_step_height_abs_error'),('decision','signed_true_objective_gap'))
        aggregate[name]={f'{a}.{b}':{'mean':statistics.mean(x[a][b] for x in samples),
                                   'sd':statistics.stdev(x[a][b] for x in samples) if len(samples)>1 else None}
                         for a,b in fields}
        aggregate[name]['median_cold_r_ms']=statistics.median(x['timing']['cold_r_ms'] for x in samples)
        aggregate[name]['median_warm_J_ms']=statistics.median(x['timing']['warm_J_ms'] for x in samples)
        aggregate[name]['median_encode_ms']=statistics.median(x['timing']['encoding_ms'] for x in samples)
        aggregate[name]['train_cpu_seconds']=sum(x['training']['cpu_training_seconds'] for x in samples)
    return {'schema':'W5_M8_RAW_4CHANNEL_PARITY_ANALYTIC_V1',
            'status':'LOCAL_ANALYTIC_CONTINUUM_NO_NATIVE_W2_LABELS',
            'train_label_kind':TEACHER,'seeds':list(seeds),'max_steps':steps,'per_family':per_family,
            'queries_per_geometry':2,'torch':torch.__version__,'python':platform.python_version(),
            'device':'cpu','threads':torch.get_num_threads(),'gpu_hours':0.,
            'input_information_parity':True,'identical_four_channel_tensor_passed_to_every_architecture':True,
            'channels':['rho_sampled','occupancy_sampled','signed_implicit_level_proxy_NOT_exact_SDF','boundary_proximity_proxy'],
            'label_truth_geometry':'EXACT_ANALYTIC_CONTINUUM_SOLIDS_NOT_8cubed_VOXEL_BOOLEAN',
            'encoder_architecture_parity':False,'parameter_counts_real':parameters,
            'parameter_max_min_ratio':ratio,'models':list(names),
            'read_only_w6_source_git_blobs':W6_FILES,'w6_read_only_commit_source':W6_PINNED_COMMIT,
            'w2_readiness':gate,'native_cherchi_calls':0,'newton_CAD_calls':0,
            'underlying_F_fixed_moments':'F=0 across analytic dataset; variable D only',
            'original_CAD_speedup_claim_allowed':False,'repeats_latency':repeats,
            'full_seed_experiments':rows,'aggregate':aggregate}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--w6-root',required=True)
    p.add_argument('--seeds',default='19,23,29')
    p.add_argument('--steps',type=int,default=100)
    p.add_argument('--per-family',type=int,default=20)
    p.add_argument('--repeats',type=int,default=7)
    p.add_argument('--models',default=','.join(FRAMEWORKS))
    p.add_argument('--w2-manifest')
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    report=execute(w6_root=a.w6_root,seeds=tuple(int(s) for s in a.seeds.split(',')),
                   steps=a.steps,per_family=a.per_family,repeats=a.repeats,
                   names=tuple(a.models.split(',')),
                   w2_manifest=json.loads(Path(a.w2_manifest).read_text()) if a.w2_manifest else None)
    txt=json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n'
    if a.output:a.output.write_text(txt,encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('full_seed_experiments',)},indent=2))

if __name__=='__main__': main()
