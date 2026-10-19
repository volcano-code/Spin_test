"""M4 independently labeled *W0-native physical P0* CPU surrogate comparison.

Unlike M1/M2's synthetic polynomial-density smoke, this experiment uses a
physical retained volume D cap under native beta=c0+c3*z. W0 ten-moment and
ambient derivative conventions are respected. Train on boxes/spheres; test on
held-out ellipsoids, without shared primitive identities. No CAD mesh features,
real Cherchi calls, independent native W2 seals or speedups are claimed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import statistics
import time
from typing import Any

import numpy as np
import torch

from .adapt import SUPPORTED_QUERY_COUNTS, fit_residual_adapter
from .contract_gate import W0_SOURCE_SHA, normalized_component_error, strict_json
from .m2_audit import check_w2_readiness
from .model import DeepONetMoment
from .native_p0 import B, dh_native_c
from .native_p0_families import NativeP0Primitive, oracle, decision, validate_exact_reference
from research.NeuralMoments.models.geometry_mlp.model import GeometryMLPMoment


def _generate_primitives(family: str, *, seed: int, count: int) -> list[NativeP0Primitive]:
    if count < 1:
        raise ValueError('count must be positive')
    rng = random.Random(seed)
    items=[]
    for _ in range(count):
        center = tuple(rng.uniform(-.2,.2) for _ in range(3))
        if family=='sphere':
            r=rng.uniform(.5,1.05)
            axes=(r,r,r)
        elif family in ('box','ellipsoid'):
            axes=tuple(rng.uniform(.48,1.02) for _ in range(3))
            if family=='ellipsoid' and max(axes)-min(axes) < .08:
                axes=(axes[0],axes[1],axes[2]*1.4)
        else:
            raise ValueError('unknown family')
        items.append(NativeP0Primitive(family,center,axes,rng.uniform(.9,1.1)))
    if len({p.source_sha256 for p in items}) != len(items):
        raise RuntimeError('duplicate analytic primitive specification')
    return items


def make_dataset(*, seed: int, per_family: int, queries_per_geometry: int = 3) -> dict[str, Any]:
    """Generate physical P0 labels using analytic integrals, not predictions."""
    if per_family < 1 or queries_per_geometry < 1 or queries_per_geometry > 8:
        raise ValueError('invalid geometry/query count')
    train_shapes = (_generate_primitives('box',seed=seed*37+1,count=per_family)
                    + _generate_primitives('sphere',seed=seed*37+2,count=per_family))
    test_shapes = _generate_primitives('ellipsoid',seed=seed*37+3,count=per_family)
    if {p.family for p in train_shapes} & {p.family for p in test_shapes}:
        raise RuntimeError('geometry-family leakage')
    if {p.source_sha256 for p in train_shapes} & {p.source_sha256 for p in test_shapes}:
        raise RuntimeError('primitive identity leakage')

    def build(shapes, query_seed):
        g=random.Random(query_seed)
        descriptors=[];cs=[];moments=[];jacobians=[];primitives=[];heights=[]
        for shape in shapes:
            for _ in range(queries_per_geometry):
                h=shape.center[2] + shape.axes[2]*g.uniform(-.62,.62)
                r,j,c=oracle(shape,h)
                descriptors.append(shape.descriptor());cs.append(c)
                moments.append(r);jacobians.append(j)
                primitives.append(shape);heights.append(h)
        d,c,r,j=(np.asarray(x,dtype=np.float64) for x in (descriptors,cs,moments,jacobians))
        return {'d':torch.from_numpy(d).float(),'c':torch.from_numpy(c).float(),
                'r':torch.from_numpy(r).float(),'j':torch.from_numpy(j).float(),
                'shapes':primitives,'heights':heights, 'geometry_sha256':[p.source_sha256 for p in shapes]}

    train=build(train_shapes,seed*37+4)
    test=build(test_shapes,seed*37+5)
    material=hashlib.sha256()
    for subset in (train,test):
        for name in ('d','c','r','j'):
            material.update(subset[name].numpy().tobytes())
    return {'train':train,'test':test,'sha256':material.hexdigest(),
            'train_geometry_families':['box','sphere'],
            'test_geometry_families':['ellipsoid'],
            'geometry_holdout_verified':True}


def train(model: torch.nn.Module, ds: dict[str, Any], *, steps: int, seed: int,
          derivative_enhanced: bool, batch_size: int = 16, lr: float = .003) -> dict[str, Any]:
    if steps < 0 or batch_size < 1 or lr <= 0:
        raise ValueError('invalid training budget')
    tr=ds['train'];gen=torch.Generator(device='cpu').manual_seed(seed)
    opt=torch.optim.Adam(model.parameters(),lr=lr)
    last_r=None;last_j=None
    t0=time.perf_counter()
    model.train()
    for _ in range(steps):
        idx=torch.randint(len(tr['d']),(batch_size,),generator=gen)
        z=model.encode_geometry(tr['d'][idx])
        pred=model.moment(z,tr['c'][idx])
        mse_r=(pred-tr['r'][idx]).square().mean()
        loss=mse_r
        if derivative_enhanced:
            jac=model.jacobian(z,tr['c'][idx])
            mse_j=(jac-tr['j'][idx]).square().mean()
            loss=loss + .5*mse_j
            last_j=float(mse_j.item())
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        last_r=float(mse_r.item())
    return {'steps':steps,'batch_size':batch_size,'learning_rate':lr,
            'derivative_weight':.5 if derivative_enhanced else 0.,
            'last_train_r_mse':last_r,'last_train_j_mse':last_j,
            'cpu_train_seconds':time.perf_counter()-t0,'gpu_seconds':0.}


def evaluate(model: torch.nn.Module, ds: dict[str, Any]) -> dict[str, float]:
    te=ds['test'];model.eval()
    with torch.no_grad():
        z=model.encode_geometry(te['d']).detach()
        pred=model.moment(z,te['c']).detach().cpu().numpy().astype(np.float64)
    jac=model.jacobian(z,te['c']).detach().cpu().numpy().astype(np.float64)
    truth=te['r'].numpy().astype(np.float64)
    true_j=te['j'].numpy().astype(np.float64)
    if pred.shape != truth.shape or jac.shape != true_j.shape or not (np.isfinite(pred).all() and np.isfinite(jac).all()):
        raise ValueError('invalid heldout model outputs')
    direction_error=[];step_errors=[];step_gaps=[];failed_improvements=[];scaled_errors=[]
    for i, (shape,h) in enumerate(zip(te['shapes'],te['heights'])):
        d=dh_native_c(h)
        direction_error.append(float(np.mean(abs((jac[i]-true_j[i])@d))))
        length_ref=2*max(shape.axes)
        scaled_errors.extend(normalized_component_error(pred[i],truth[i],length_ref=length_ref,density_ref=shape.density))
        normalized_height=(h-shape.center[2])/shape.axes[2]
        target=shape.center[2]+shape.axes[2]*np.clip(normalized_height+.16,-.83,.83)
        record=decision(shape,h,target,predicted_r=pred[i],predicted_jc=jac[i])
        step_errors.append(record['step_absolute_error'])
        step_gaps.append(record['signed_oracle_loss_gap'])
        failed_improvements.append(record['loss_candidate_after']>record['loss_before'])
    return {
        'r_mae':float(np.mean(abs(pred-truth))),
        'r_relative_l2':float(np.linalg.norm(pred-truth)/max(np.linalg.norm(truth),1e-12)),
        'w0_normalized_component_mae':float(np.mean(scaled_errors)),
        'Jc_mae':float(np.mean(abs(jac-true_j))),
        'Jc_relative_l2':float(np.linalg.norm(jac-true_j)/max(np.linalg.norm(true_j),1e-12)),
        'height_directional_mae':float(np.mean(direction_error)),
        'step_absolute_error':float(np.mean(step_errors)),
        'signed_true_objective_gap':float(np.mean(step_gaps)),
        'candidate_step_worsened_start_fraction':float(np.mean(failed_improvements)),
        'evaluated_queries':len(truth), 'unique_heldout_geometries':len(te['geometry_sha256']),
    }


def benchmark_cached(model: torch.nn.Module, d: torch.Tensor, c: torch.Tensor,
                     *, repeats: int = 25) -> dict[str, Any]:
    """Uncompiled, single-thread CPU timings; report median and spread.

    The warm path EXCLUDES geometry encoding; jacrev is over one native c.
    These Python overhead measurements are not a Cherchi-vs-net speedup.
    """
    if repeats < 1:
        raise ValueError('positive repeat count required')
    model.eval()
    with torch.no_grad():
        z=model.encode_geometry(d).detach()
    def measure(action):
        for _ in range(5):
            action()
        values=[]
        for _ in range(repeats):
            started=time.perf_counter_ns()
            action()
            values.append((time.perf_counter_ns()-started)/1e6)
        return {'median_ms':float(statistics.median(values)),
                'minimum_ms':float(min(values)),
                'maximum_ms':float(max(values))}
    with torch.no_grad():
        cold=measure(lambda:model.moment(model.encode_geometry(d),c))
        warm=measure(lambda:model.moment(z,c))
    jac=measure(lambda:model.jacobian(z,c))
    return {'estimated_complexity':model.complexity(),
            'cold_encode_plus_query':cold,
            'warm_cached_query':warm,
            'cached_jacrev_10x10':jac,
            'repeats':repeats,'cpu_threads':torch.get_num_threads(),
            'no_gpu_or_native_teacher_timing':True}


def adaptation(model: torch.nn.Module, primitive: NativeP0Primitive) -> dict[str, Any]:
    """True *independent P0* 0/1/2/4/8-shot corrections on unseen geometry."""
    model.eval()
    z=model.encode_geometry(torch.tensor(primitive.descriptor(),dtype=torch.float32)).detach()
    cz,az=primitive.center[2],primitive.axes[2]
    support_h=np.array([-.75,-.57,-.39,-.21,-.03,.15,.40,.73])*az+cz
    heldout_h=np.array([-.66,-.49,-.30,-.12,.06,.27,.56])*az+cz
    def labels(heights):
        rjc=[oracle(primitive,float(h)) for h in heights]
        c=torch.tensor(np.stack([x[2] for x in rjc]),dtype=torch.float32)
        r=torch.tensor(np.stack([x[0] for x in rjc]),dtype=torch.float32)
        return c,r,np.stack([x[1] for x in rjc])
    sc,sr,_=labels(support_h)
    tc,tr,tj=labels(heldout_h)
    result={}
    for k in SUPPORTED_QUERY_COUNTS:
        adaptor=fit_residual_adapter(model,z,sc[:k],sr[:k])
        with torch.no_grad():
            pred=adaptor.predict(tc).detach().numpy()
        derived=adaptor.jacobian(tc).detach().numpy()
        dd=np.stack([dh_native_c(float(h)) for h in heldout_h])
        pdir=np.einsum('bij,bj->bi',derived,dd)
        true_dir=np.einsum('bij,bj->bi',tj,dd)
        result[str(k)]={'oracle_query_count':k,'heldout_query_count':len(heldout_h),
                        'r_mae':float(np.mean(abs(pred-tr.numpy()))),
                        'height_directional_mae':float(np.mean(abs(pdir-true_dir)))}
    return result


def run(*, seeds: tuple[int,...] = (7,19,31), steps: int = 90,
        per_family: int = 12, repeats: int = 25, w2_manifest: str|None = None) -> dict[str,Any]:
    if not seeds or any(s<0 for s in seeds) or len(set(seeds))!=len(seeds):
        raise ValueError('unique nonnegative seeds required')
    if steps<0 or repeats<1:
        raise ValueError('invalid steps/repeats')
    torch.set_num_threads(1)
    readiness=check_w2_readiness(w2_manifest)
    if readiness['ready']:
        raise RuntimeError('W2 real teacher admission requires separate independent evaluation')
    result={'schema':'W5-M4-native-P0-physical-moment-derivative-v1',
            'status':'INDEPENDENT_ANALYTIC_P0_ONLY_REAL_W2_TRAINING_BLOCKED',
            'frozen_source_sha':W0_SOURCE_SHA,
            'w0_contract_head_checked':'bfedacd3a1f4e10d30f1258331260380739d243c',
            'w2_teacher_head_checked':'56212f46b007fa255cc5796224192010aa67513c',
            'w0_c_order':'CONST,X,Y,Z,XX,YY,ZZ,YZ,XZ,XY',
            'w0_r_order':'M,LX,LY,LZ,QXX,QYY,QZZ,QYZ,QXZ,QXY',
            'w0_native_to_monomial_diag':B.tolist(),
            'cut_model':'beta=c0+c3*z; c=normalize(-h,0,0,1,0,...); c3>0',
            'material_partition':'analytic D cut only; fixed F identically zero',
            'analytic_source':'closed boxes, exact spheres, axis-aligned ellipsoids; symbolic polynomial integrals',
            'geometry_input':'10D exact primitive parameters; NOT the M3 24D mesh descriptor',
            'train_families':['box','sphere'],'test_families':['ellipsoid'],
            'teacher_source':'independently derived analytic P0 oracle, no W2 or neural-generated labels',
            'native_teacher_runs':0,'native_training_samples':0,
            'teacher_gate':readiness,
            'seeds':list(seeds),'steps':steps,'per_family':per_family,'queries_per_geometry':3,
            'repeats':repeats,'device':'cpu','cpu_threads':torch.get_num_threads(),
            'torch_version':torch.__version__,'python_version':platform.python_version(),
            'gpu_seconds':0., 'real_native_speedup_claim':False,
            'runs':{}, 'oracle_audits':{}}
    for seed in seeds:
        data=make_dataset(seed=seed,per_family=per_family)
        p=data['test']['shapes'][0]
        h=p.center[2]+.22*p.axes[2]
        result['oracle_audits'][str(seed)]=validate_exact_reference(p,h)
        per_run={'dataset_sha256':data['sha256'],
                 'train_queries':len(data['train']['d']),
                 'test_queries':len(data['test']['d']),
                 'train_unique_geometries':len(data['train']['geometry_sha256']),
                 'test_unique_geometries':len(data['test']['geometry_sha256']),
                 'family_and_identity_holdout_verified':data['geometry_holdout_verified'],
                 'models':{}}
        for name,cls in [('deeponet',DeepONetMoment),('geometry_mlp',GeometryMLPMoment)]:
            arms={}
            for enhanced in (False,True):
                torch.manual_seed(seed)
                model=cls(geometry_dim=10).float()
                record=train(model,data,steps=steps,seed=seed,
                             derivative_enhanced=enhanced)
                heldout=evaluate(model,data)
                timings=benchmark_cached(model,data['test']['d'][0],data['test']['c'][0],repeats=repeats)
                fewshot=adaptation(model,data['test']['shapes'][0])
                arms['derivative_enhanced' if enhanced else 'residual_only']={
                    'training':record,'heldout':heldout,
                    'complexity_and_cpu_timing':timings,'oracle_adaptation':fewshot}
            per_run['models'][name]=arms
        result['runs'][str(seed)]=per_run
    # Deliberately no universal percent/speedup threshold.
    return result


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seeds',default='7,19,31')
    p.add_argument('--steps',type=int,default=90)
    p.add_argument('--per-family',type=int,default=12)
    p.add_argument('--repeats',type=int,default=25)
    p.add_argument('--w2-manifest',default=None)
    args=p.parse_args()
    seeds=tuple(int(x.strip()) for x in args.seeds.split(',') if x.strip())
    print(json.dumps(run(seeds=seeds,steps=args.steps,per_family=args.per_family,
                         repeats=args.repeats,w2_manifest=args.w2_manifest),
                     indent=2,sort_keys=True,allow_nan=False))

if __name__=='__main__':
    main()
