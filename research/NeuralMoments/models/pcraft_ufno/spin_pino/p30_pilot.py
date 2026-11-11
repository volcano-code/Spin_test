"""Fixed-budget P30 CPU pilot; discrete SOFT-cut reference, not Cherchi.

Run from repo root:
 python -m research.NeuralMoments.models.pcraft_ufno.spin_pino.p30_pilot --output DIR
No test-selected checkpoints/hyperparameters. Geometry IDs disjoint across
train/test/OOD. Uniform/material arms have identical parameter counts and
initial tensors. Baseline uses fewer parameters; this is explicitly reported.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import platform
import time
from pathlib import Path
import numpy as np
import torch
from .spin_pino import SpinPINO
from .material_core import MaterialAwareSpinPINO

BASE_COMMIT = '49655d19bc0471b38b1c3764b822ecdd38894ffd'
MODEL_CONFIG = dict(width=4,modes=2,n_layers=2,grid_size=8,
                    points_per_axis=8,hidden_dim=24,temperature=.12,
                    moment_parameterization='logistic_atom')
PROTOCOL = dict(model=MODEL_CONFIG, seeds=[301,307,311], steps=60,
                batch_geometries=6, queries_per_geometry=4, input_grid=16,
                train_geometries=24,test_geometries=12,ood_geometries=4,
                optimizer='AdamW',lr=.002,weight_decay=.0001,
                loss='train-RMS scaled r MSE + 0.1*train-RMS scaled J MSE',
                checkpoint_selection='last fixed step; no test selection',
                reference='independent dense cell-centered logistic soft-cut integral',
                reference_temperature=.12, native_teacher=False)


def make_geometry(index, family, n=16):
    rng = np.random.default_rng(90711+index)
    axis=(torch.arange(n,dtype=torch.float64)+.5)*2/n-1
    xyz=torch.stack(torch.meshgrid(axis,axis,axis,indexing='ij'),-1)
    center=torch.tensor(rng.uniform(-.12,.12,3))
    p=xyz-center
    size=torch.tensor(rng.uniform(.55,.85,3))
    x,y,z=p.unbind(-1)
    inner=torch.zeros_like(x)
    if family=='ellipsoid':
        field=((p/size).square().sum(-1).sqrt()-1)*size.min()
    elif family=='perforated':
        outer=(p.abs()-size).amax(-1)
        hole=(x.square()+y.square()).sqrt()-float(rng.uniform(.18,.33))
        field=torch.maximum(outer,-hole)
        inner=(hole.abs()<2/n).double()
    elif family=='shell':
        outer=((p/size).square().sum(-1).sqrt()-1)*size.min()
        cavity=((p/(size*.55)).square().sum(-1).sqrt()-1)*(size.min()*.55)
        field=torch.maximum(outer,-cavity)
        inner=(cavity.abs()<2/n).double()
    elif family=='ribbed_ood':
        # Union of a thin slab and two offset ribs; unseen training family.
        slab=torch.stack((x.abs()-.7,y.abs()-.6,(z+.4).abs()-.13),-1).amax(-1)
        rib1=torch.stack(((x-.32).abs()-.12,y.abs()-.6,z.abs()-.6),-1).amax(-1)
        rib2=torch.stack(((x+.32).abs()-.12,y.abs()-.6,z.abs()-.6),-1).amax(-1)
        field=torch.minimum(slab,torch.minimum(rib1,rib2))
    else:
        raise ValueError(family)
    occ=(field<0).double()
    rho=occ*(.45+.45*torch.sigmoid(2*x+.7*y-.3*z+float(rng.normal())))
    # This channel is an implicit-field proxy, not a certified metric SDF.
    d=torch.stack((rho,occ,torch.tanh(field/.2),inner)).float()
    c=torch.tensor(rng.normal(size=(4,10)),dtype=torch.float64)
    c[:,0]*=.3;c[:,4:]*=.3
    return d,c,xyz


def reference(d,c,xyz):
    # Never calls model.moment_from_weights or model.jacobian_from_weights.
    x,y,z=xyz.reshape(-1,3).unbind(-1)
    phi=torch.stack((torch.ones_like(x),x,y,z,x*x,y*y,z*z,y*z,x*z,x*y),-1)
    B=torch.tensor([1.]*7+[2.]*3,dtype=torch.float64)
    material=d[0].double().flatten()*d[1].double().flatten()*8/xyz[...,0].numel()
    norm=c.norm(dim=-1,keepdim=True)
    polynomial=(c*B)@phi.T
    a=torch.sigmoid(polynomial/(.12*norm))
    r=(a*material)@phi
    ds=(B*phi)[None]-polynomial[:,:,None]*c[:,None]/norm.square()[:,:,None]
    J=torch.einsum('qn,ni,qnj->qij',material*a*(1-a)/(.12*norm),phi,ds)
    return r.float(),J.float()


def dataset():
    rows={key:[] for key in ('train','test','ood')}
    for split,start,count in [('train',0,24),('test',100,12),('ood',200,4)]:
        for j in range(count):
            family='ribbed_ood' if split=='ood' else ('ellipsoid','perforated','shell')[j%3]
            d,c,xyz=make_geometry(start+j,family)
            r,J=reference(d,c,xyz)
            rows[split].append(dict(id=f'{family}:{start+j}',family=family,D=d,c=c.float(),r=r,J=J))
    return rows


def pack(rows):
    return {k:torch.stack([r[k] for r in rows]) for k in ('D','c','r','J')}


def predict(model,batch):
    count,queries=batch['c'].shape[:2]
    w=model.encode_geometry(batch['D'])
    w=w[:,None].expand(-1,queries,-1).reshape(count*queries,-1)
    c=batch['c'].reshape(-1,10)
    return (model.moment_from_weights(w,c).reshape(count,queries,10),
            model.jacobian_from_weights(w,c).reshape(count,queries,10,10))


@torch.no_grad()
def evaluate(model,rows):
    model.eval()
    r,J=predict(model,pack(rows))
    truth=pack(rows)
    re=(r-truth['r']).norm(dim=-1)/truth['r'].norm(dim=-1).clamp_min(1e-8)
    je=(J-truth['J']).flatten(2).norm(dim=-1)/truth['J'].flatten(2).norm(dim=-1).clamp_min(1e-8)
    return dict(r_relative_l2_mean=float(re.mean()),J_relative_l2_mean=float(je.mean()),
                by_family={f:dict(r_relative_l2_mean=float(re[[row['family']==f for row in rows]].mean()),
                                 J_relative_l2_mean=float(je[[row['family']==f for row in rows]].mean()))
                           for f in sorted({row['family'] for row in rows})})


def state_hash(model):
    h=hashlib.sha256()
    for k,v in sorted(model.state_dict().items()):
        h.update(k.encode());h.update(v.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def run(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    data=dataset();train=pack(data['train'])
    ids={key:{row['id'] for row in rows} for key,rows in data.items()}
    assert not ids['train'] & ids['test'] and not ids['train'] & ids['ood']
    sr=train['r'].square().mean((0,1)).sqrt().clamp_min(.01)
    sj=train['J'].square().mean((0,1)).sqrt().clamp_min(.01)
    all_runs=[]
    protocol_json=json.dumps(PROTOCOL,sort_keys=True)
    (output/'protocol.json').write_text(protocol_json+'\n')
    for seed in PROTOCOL['seeds']:
        torch.manual_seed(seed)
        baseline=SpinPINO(**MODEL_CONFIG)
        material=MaterialAwareSpinPINO(**MODEL_CONFIG,slices=4,measure='material')
        material.load_baseline(baseline)
        uniform=MaterialAwareSpinPINO(**MODEL_CONFIG,slices=4,measure='uniform')
        uniform.load_state_dict(material.state_dict(),strict=True)
        order_rng=torch.Generator().manual_seed(seed+1000)
        batches=[torch.randperm(len(data['train']),generator=order_rng)[:PROTOCOL['batch_geometries']]
                 for _ in range(PROTOCOL['steps'])]
        for name,model in [('baseline',baseline),('uniform_internal',uniform),('material_internal',material)]:
            optimizer=torch.optim.AdamW(model.parameters(),lr=.002,weight_decay=.0001)
            history=[];started=time.perf_counter();model.train()
            for step,index in enumerate(batches):
                batch={k:v[index] for k,v in train.items()}
                r,J=predict(model,batch)
                loss=((r-batch['r'])/sr).square().mean()+.1*((J-batch['J'])/sj).square().mean()
                if not torch.isfinite(loss): raise FloatingPointError('nonfinite loss')
                optimizer.zero_grad(set_to_none=True);loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(),2.)
                optimizer.step()
                if step in (0,19,39,59):history.append(dict(step=step+1,loss=float(loss.detach())))
            elapsed=time.perf_counter()-started
            report=dict(seed=seed,arm=name,real_parameters=model.real_parameter_count(),
                        training_seconds=elapsed,history=history,
                        test=evaluate(model,data['test']),ood=evaluate(model,data['ood']),
                        state_sha256=state_hash(model))
            if name!='baseline':report['learned_gates']={n:float(m.gate.detach().tanh()) for n,m in model.encoder.mixers.items()}
            torch.save(dict(state_dict=model.state_dict(),config=MODEL_CONFIG,arm=name,seed=seed),
                       output/f'{name}-{seed}.pt')
            all_runs.append(report)
            print(json.dumps(report),flush=True)
    means={arm:{metric:float(np.mean([r['test'][metric] for r in all_runs if r['arm']==arm]))
                 for metric in ('r_relative_l2_mean','J_relative_l2_mean')}
           for arm in ('baseline','uniform_internal','material_internal')}
    result=dict(schema='W6_P30_MATERIAL_CORE_PILOT_V1',base_commit=BASE_COMMIT,
                environment=dict(python=platform.python_version(),torch=torch.__version__,numpy=np.__version__,device='cpu',threads=1),
                protocol=PROTOCOL,protocol_sha256=hashlib.sha256(protocol_json.encode()).hexdigest(),
                geometry_ids={k:sorted(v) for k,v in ids.items()},runs=all_runs,test_means=means,
                decision='RESEARCH_CANDIDATE_NOT_PRODUCTION_PROMOTED',
                claims=dict(native_Cherchi=False,native_Jacobian_admission=False,
                            TRELLIS_assets_used=False,grid512=False,statistical_superiority=False))
    (output/'result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('MEANS',json.dumps(means),flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();run(args.output)
