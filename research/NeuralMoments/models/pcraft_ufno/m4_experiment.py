"""M4 exact-analytic P0 training/validation ablation, deliberately NOT native W2.

Identical M3 geometry and query oracle (SHA reproducible), training/test family
split, and training examples for each arm. Within training families, hold out
whole geometry IDs for early stopping, never controls from the same geometry.
W5 snapshots are read-only and use a lossy 9D voxel summary; raw feature
parity with M4 is *not* established.

  python -m research.NeuralMoments.models.pcraft_ufno.m4_experiment \
      --seeds 19,23,29 --steps 100 --output m4_result.json
"""
from __future__ import annotations
import argparse, copy, hashlib, json, math, platform, resource, statistics, time
from typing import Any
import torch
from torch import Tensor
from .analytic_cut import sample_dataset,assert_disjoint_family_splits,GeometrySpec,vertical_cut_truth,voxel_geometry
from .m4_lite_model import LiteUFNOMoment,num_real_parameters,voxel_statistics9
from .w5_snapshot.deeponet.model import DeepONetMoment
from .w5_snapshot.geometry_mlp.model import GeometryMLPMoment

NAMES=('lite_dual','lite_bottleneck','lite_local_only','w5_deeponet','w5_geometry_mlp')
W0_B=(1.,)*7+(2.,)*3
OLD_M3_SEED19_TRAIN_SHA='7b65ebbb3e5d32e82ff7ee23a1f88978fa4100902b67f63e16b0fdc2df54e087'


def make_model(name:str,seed:int,grid_size:int=8):
    torch.manual_seed(seed)
    if name.startswith('lite_'):return LiteUFNOMoment(name[5:],grid_size=grid_size)
    if name=='w5_deeponet':return DeepONetMoment()
    if name=='w5_geometry_mlp':return GeometryMLPMoment()
    raise ValueError('unknown model')


def encoded(model,name:str,voxels:Tensor)->Tensor:
    return model.encode_geometry(voxels if name.startswith('lite_') else voxel_statistics9(voxels))


def dataset_digest(data)->str:
    d,c,r,J,meta=data
    digest=hashlib.sha256()
    for tensor in (d,c,r,J):
        a=tensor.detach().contiguous().cpu().numpy()
        digest.update(str((a.shape,str(a.dtype))).encode('ascii'))
        digest.update(a.tobytes())
    digest.update(json.dumps(meta,sort_keys=True,separators=(',',':')).encode('utf-8'))
    return digest.hexdigest()


def subset_dataset(data,indices:list[int]):
    return tuple(x[indices] for x in data[:4])+( [data[4][i] for i in indices], )


def split_by_geometry(train_all,seed:int,validation_geometries_per_family:int=4):
    """8 whole geometries in validation, 32 in fitting, no query mixing."""
    meta=train_all[4]
    generator=torch.Generator().manual_seed(seed+487)
    val_ids=set()
    for family in ('box','sphere'):
        ids=list(dict.fromkeys(row['geometry_id'] for row in meta if row['family']==family))
        if len(ids)<=validation_geometries_per_family:raise ValueError('not enough geometries for validation')
        order=torch.randperm(len(ids),generator=generator).tolist()
        val_ids.update(ids[i] for i in order[:validation_geometries_per_family])
    train_indices=[i for i,row in enumerate(meta) if row['geometry_id'] not in val_ids]
    val_indices=[i for i,row in enumerate(meta) if row['geometry_id'] in val_ids]
    train,valid=subset_dataset(train_all,train_indices),subset_dataset(train_all,val_indices)
    ids_tr={x['geometry_id'] for x in train[4]}
    ids_va={x['geometry_id'] for x in valid[4]}
    assert not ids_tr & ids_va
    return train,valid,{'train_geo':len(ids_tr),'val_geo':len(ids_va),
                        'train_queries':len(train_indices),'validation_queries':len(val_indices),
                        'validation_geometry_sha256':hashlib.sha256(('\n'.join(sorted(ids_va))).encode()).hexdigest()}


def sample_schedule(n:int,steps:int,batch:int,seed:int)->Tensor:
    if min(n,steps,batch)<1:raise ValueError('positive dimensions needed')
    return torch.randint(n,(steps,batch),generator=torch.Generator().manual_seed(seed+313))


def metrics(model,name:str,data)->dict[str,float]:
    D,c,r,J,_=data
    model.eval()
    with torch.no_grad():
        z=encoded(model,name,D)
        pred=model.moment(z,c)
    j=model.jacobian(z.detach(),c).detach()
    diag=torch.as_tensor(W0_B,dtype=r.dtype)[None,None,:]
    jq=j/diag
    direction=torch.arange(1,11,dtype=r.dtype)
    direction=direction/direction.norm()
    scales=torch.as_tensor([8.]+[16.]*3+[32.]*6,dtype=r.dtype)
    return {'r_mae':float((pred-r).abs().mean()),
            'r_relative_l2':float((pred-r).norm()/r.norm().clamp_min(1e-12)),
            'r_W0_normalized_mae':float(((pred-r).abs()/scales).mean()),
            'J_mae':float((j-J).abs().mean()),
            'J_relative_l2':float((j-J).norm()/J.norm().clamp_min(1e-12)),
            'directional_mae':float(((j-J)@direction).abs().mean()),
            'predicted_Jq_asymmetry_max':float((jq-jq.transpose(-1,-2)).abs().max()),
            'projective_radial_Jc_c_max':float((j@c.unsqueeze(-1)).abs().max())}


def train_early_stop(model,name:str,train,valid,*,seed:int,steps:int=100,
                     batch:int=8,lr:float=.003,eval_every:int=10,patience:int=5,
                     derivative_enhanced:bool=True):
    if steps<1 or eval_every<1 or patience<1:raise ValueError('invalid early stopping control')
    schedule=sample_schedule(len(train[0]),steps,batch,seed)
    optimizer=torch.optim.Adam(model.parameters(),lr=lr)
    best_val=float('inf');best_step=0;best_state=copy.deepcopy(model.state_dict())
    history=[];stale=0
    t0=time.perf_counter()
    for step,ids in enumerate(schedule,1):
        model.train()
        z=encoded(model,name,train[0][ids]);c=train[1][ids]
        pred=model.moment(z,c)
        loss_r=(pred-train[2][ids]).square().mean()
        loss=loss_r
        loss_j=None
        if derivative_enhanced:
            j=model.jacobian(z,c)
            loss_j=(j-train[3][ids]).square().mean()
            loss=loss+0.5*loss_j
        if not bool(torch.isfinite(loss)):
            raise FloatingPointError('nonfinite training loss')
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        if step%eval_every==0 or step==steps:
            val=metrics(model,name,valid)
            # Precommitted selection score on VALIDATION ONLY; test never read.
            score=val['r_mae']+0.25*val['J_mae']
            history.append({'step':step,'validation_score':score,
                            'validation_r_mae':val['r_mae'],
                            'validation_J_mae':val['J_mae'],
                            'train_last_r_mse':float(loss_r.detach()),
                            'train_last_J_mse':float(loss_j.detach()) if loss_j is not None else None})
            if score<best_val-1e-7:
                best_val=score;best_step=step
                best_state=copy.deepcopy(model.state_dict());stale=0
            else:stale+=1
            if stale>=patience:break
    elapsed=time.perf_counter()-t0
    model.load_state_dict(best_state)
    return {'steps_executed':step,'steps_selected':best_step,'max_steps':steps,
            'best_validation_score':best_val,'stop_reason':'patience' if stale>=patience else 'budget',
            'derivative_enhanced':derivative_enhanced,'analytic_unique_train_labels':len(train[0]),
            'analytical_validation_labels':len(valid[0]),'batch_size':batch,'lr':lr,
            'cpu_training_seconds':elapsed,'gpu_hours':0.0,
            'batch_schedule_sha256':hashlib.sha256(schedule.numpy().tobytes()).hexdigest(),
            'history':history}


def latency(model,name:str,vox:Tensor,c:Tensor,repetitions:int=9):
    if repetitions<1:raise ValueError('repetitions')
    D=vox.unsqueeze(0);c=c.unsqueeze(0)
    model.eval()
    with torch.no_grad():
        z=encoded(model,name,D).detach()
        model.moment(z,c)
        model.jacobian(z,c)
    def measure(fn):
        for _ in range(3):fn()
        values=[]
        for _ in range(repetitions):
            s=time.perf_counter();fn();values.append(1000*(time.perf_counter()-s))
        return {'median_ms':statistics.median(values),'min_ms':min(values),'max_ms':max(values),'repeats':repetitions}
    with torch.no_grad():
        out={'cold_voxel_to_head':measure(lambda:model.moment(encoded(model,name,D),c)),
             'encode_only':measure(lambda:encoded(model,name,D)),
             'cached_head':measure(lambda:model.moment(z,c)),
             'cached_J10x10':measure(lambda:model.jacobian(z,c))}
    out['cpu_process_peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    out['gpu_peak_memory_mb']=None
    return out


def run(*,seeds=(19,23,29),steps=100,per_family=20,grid_size=8,
        repetitions=7,names=NAMES,derivative_enhanced=True)->dict:
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    unique_seeds=tuple(int(x) for x in seeds)
    if not unique_seeds or len(unique_seeds)!=len(set(unique_seeds)):
        raise ValueError('seed list must be nonempty and unique')
    reference_params={n:num_real_parameters(make_model(n,19,grid_size)) for n in names}
    if max(reference_params.values())/min(reference_params.values())>1.05:
        raise ValueError('parameter capacity >5% across requested architectures')
    report={'status':'ANALYTIC_CONTINUUM_P0_M4_NO_W2_REAL_TEACHER',
            'seeds':list(unique_seeds),'models':list(names),'parameters_real':reference_params,
            'W2_real_teacher_samples':0,'source':'same M3 full analytic vertical-cut dataset, native c, W0 raw r/J',
            'representation_parity':False,'W5_representation':'9D lossy voxel statistics',
            'W6_representation':'4 channel voxel + label-blind 9D statistics',
            'train_families':['box','sphere'],'validation_families':['box','sphere'],
            'heldout_families':['ellipsoid'],'training_samples_are_continuum_not_voxel_integrals':True,
            'torch_version':torch.__version__,'python_version':platform.python_version(),
            'device':'cpu','cpu_threads':torch.get_num_threads(),'max_steps':steps,
            'validation_rule':'minimize r_mae+0.25*J_mae, evaluated every 10 steps; patience 5',
            'derivative_loss':'MSE(r)+0.5*MSE(J)' if derivative_enhanced else 'MSE(r)',
            'all_experiments':[]}
    for seed in unique_seeds:
        all_train=sample_dataset(('box','sphere'),per_family=per_family,seed=seed,grid_size=grid_size)
        heldout=sample_dataset(('ellipsoid',),per_family=per_family,seed=seed+1,grid_size=grid_size)
        assert_disjoint_family_splits(all_train,heldout)
        train,valid,manifest=split_by_geometry(all_train,seed,validation_geometries_per_family=max(1,per_family//5))
        assert not ({x['geometry_id'] for x in heldout[4]} & {x['geometry_id'] for x in train[4]+valid[4]})
        per_seed={'seed':seed,'full_M3_train_sha256':dataset_digest(all_train),
                  'full_M3_heldout_sha256':dataset_digest(heldout),
                  'geometry_split':manifest,'results':{}}
        for name in names:
            model=make_model(name,seed,grid_size)
            train_record=train_early_stop(model,name,train,valid,seed=seed,steps=steps,
                                          derivative_enhanced=derivative_enhanced)
            per_seed['results'][name]={
                'training':train_record,
                'heldout':metrics(model,name,heldout),
                'cpu_timing':latency(model,name,heldout[0][0],heldout[1][0],repetitions=repetitions)}
        report['all_experiments'].append(per_seed)
    report['aggregate']={}
    for name in names:
        vals=[x['results'][name]['heldout'] for x in report['all_experiments']]
        timers=[x['results'][name]['cpu_timing'] for x in report['all_experiments']]
        report['aggregate'][name]={}
        for metric in ('r_mae','J_mae','directional_mae','predicted_Jq_asymmetry_max'):
            values=[float(x[metric]) for x in vals]
            report['aggregate'][name][metric]={'mean':statistics.mean(values),
                                               'sample_sd':statistics.stdev(values) if len(values)>1 else None,
                                               'per_seed':dict(zip(map(str,unique_seeds),values))}
        report['aggregate'][name]['cold_ms_median_across_seeds']=statistics.median(x['cold_voxel_to_head']['median_ms'] for x in timers)
        report['aggregate'][name]['cached_J_ms_median_across_seeds']=statistics.median(x['cached_J10x10']['median_ms'] for x in timers)
        report['aggregate'][name]['selected_steps']=[x['results'][name]['training']['steps_selected'] for x in report['all_experiments']]
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--seeds',default='19,23,29')
    parser.add_argument('--steps',type=int,default=100)
    parser.add_argument('--per-family',type=int,default=20)
    parser.add_argument('--grid-size',type=int,default=8)
    parser.add_argument('--repetitions',type=int,default=7)
    parser.add_argument('--models',default=','.join(NAMES))
    parser.add_argument('--moment-only',action='store_true')
    parser.add_argument('--output')
    args=parser.parse_args()
    result=run(seeds=tuple(map(int,args.seeds.split(','))),steps=args.steps,
               per_family=args.per_family,grid_size=args.grid_size,
               repetitions=args.repetitions,names=tuple(args.models.split(',')),
               derivative_enhanced=not args.moment_only)
    encoded=json.dumps(result,sort_keys=True,indent=2,allow_nan=False)
    if args.output:
        with open(args.output,'w',encoding='utf8') as f:f.write(encoded+'\n')
    print(encoded)

if __name__=='__main__':main()
