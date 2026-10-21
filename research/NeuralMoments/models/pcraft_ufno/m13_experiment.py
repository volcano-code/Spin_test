"""W6 M13: same-indexed-mesh -> same four-channel D -> fair W5/W6 P0.

Train with labels integrated from the INDEXED TRIANGLE MESH itself (not the
analytic shape that was used to generate test meshes); no privileged shape
axes, reference label, or cut-specific result appears in model input D.
All oracle labels are independent convex mesh vertical cuts; NO W2 material
teacher or arbitrary-quadric/10D Newton/Cherchi execution is claimed.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import time
import numpy as np
import torch
import trimesh
from .m13_mesh_source import FrozenTriMesh,mesh_to_cells,_sha
from .m13_cell_integrals import FrozenCellVolume,unit_vertical_native_c
from .m13_mesh_cut import convex_mesh_vertical_cut
from .m7_realizable import RealizableUFNOMoment
from .m10_w5_readonly import W5VoxelDeepONet
from .m4_lite_model import num_real_parameters

SOURCE_POLICY='EXPLICIT_INDEXED_CONVEX_TRIANGLE_MESH_NUMERIC_P0_NOT_W2'


def _create_convex_mesh(family:str,center:np.ndarray,axes:np.ndarray)->FrozenTriMesh:
    """Shape params ONLY generate an explicit indexed mesh, never enter sampler."""
    if family=='box':
        raw=trimesh.creation.box(extents=2*axes)
    else:
        if family=='sphere' and np.max(axes)-np.min(axes)>1e-12:
            raise ValueError('sphere axes mismatch')
        raw=trimesh.creation.icosphere(subdivisions=2, radius=1.)
        raw.vertices[:]=raw.vertices*axes[None]
    return FrozenTriMesh(np.asarray(raw.vertices)+center[None],raw.faces)


def _shape_stream(families:tuple[str,...],seed:int,per_family:int):
    rng=np.random.default_rng(seed)
    for family in families:
        for _ in range(per_family):
            center=rng.uniform(-.10,.10,3)
            if family=='sphere':
                a=float(rng.uniform(.46,.73));axes=np.array([a,a,a])
            else:
                axes=rng.uniform(.46,.73,3)
                if family=='ellipsoid':axes*=np.array([1.,.8,1.1])
            mesh=_create_convex_mesh(family,center,axes)
            hlocals=rng.uniform(-.55,.55,2)
            yield family,mesh,center,axes,hlocals


def _target_for_mesh(mesh:FrozenTriMesh,h_world:float):
    ref=convex_mesh_vertical_cut(mesh,h_world)
    if ref.Jc is None:raise ValueError('FAIL_CLOSED_UNAVAILABLE_MESH_J')
    return ref


def _load_split(families,seed:int,per_family:int,*,resolution=8,samples_per_axis=3):
    D=[];c=[];r=[];J=[];meta=[];mesh_count=0
    for family,mesh,center,axes,hlocals in _shape_stream(tuple(families),seed,per_family):
        sample=mesh_to_cells(mesh,resolution=resolution,samples_per_axis=samples_per_axis)
        proxy=FrozenCellVolume(sample.D)
        for hloc in hlocals:
            h=float(center[2]+axes[2]*hloc)
            truth=_target_for_mesh(mesh,h)
            control=unit_vertical_native_c(h)
            D.append(torch.from_numpy(sample.D.copy()))
            c.append(torch.tensor(control,dtype=torch.float32))
            r.append(torch.tensor(truth.r,dtype=torch.float32))
            J.append(torch.tensor(truth.Jc,dtype=torch.float32))
            meta.append({'family':family,'mesh_sha256':mesh.identity,
                        'voxel_sha256':sample.voxel_sha256,
                        'height_world':h,'cut_kind':'POSITIVE_VERTICAL_P0',
                        'source':SOURCE_POLICY})
        mesh_count+=1
    result=(torch.stack(D),torch.stack(c),torch.stack(r),torch.stack(J),meta)
    return result,mesh_count


def _digest(data)->str:
    h=hashlib.sha256()
    for x in data[:4]:
        raw=x.contiguous().numpy()
        h.update(str((raw.shape,str(raw.dtype))).encode());h.update(raw.tobytes())
    h.update(json.dumps(data[4],sort_keys=True,separators=(',',':')).encode())
    return h.hexdigest()


def _slice(data,indices):
    return tuple(x[indices] for x in data[:4])+([data[4][i] for i in indices],)


def _train_valid(data,seed):
    meta=data[4]
    rng=np.random.default_rng(seed+777)
    valid_ids=set()
    for family in ('box','sphere'):
        ids=list(dict.fromkeys(x['mesh_sha256'] for x in meta if x['family']==family))
        if len(ids)<5:raise ValueError('at least 5 shapes per training family')
        valid_ids.update(ids[i] for i in rng.choice(len(ids),size=max(1,len(ids)//5),replace=False))
    val=[i for i,m in enumerate(meta) if m['mesh_sha256'] in valid_ids]
    train=[i for i,m in enumerate(meta) if m['mesh_sha256'] not in valid_ids]
    return _slice(data,train),_slice(data,val)


def _metrics(model,data):
    D,c,r,J,_=data
    model.eval()
    with torch.no_grad():
        z=model.encode_geometry(D)
        rp=model.moment(z,c)
        jp=model.jacobian(z,c)
    return {'r_mae':float((rp-r).abs().mean()),
            'Jc_mae':float((jp-J).abs().mean()),
            'negative_mass_fraction':float((rp[:,0]<-1e-8).float().mean()),
            'r_relative_l2':float((rp-r).norm()/r.norm().clamp_min(1e-12))}


def _fit(model,fit,val,*,seed,steps=80):
    schedule=torch.randint(len(fit[0]),(steps,8),generator=torch.Generator().manual_seed(seed+313))
    opt=torch.optim.Adam(model.parameters(),lr=.003)
    best=float('inf');best_at=0;stale=0;state=copy.deepcopy(model.state_dict())
    start=time.perf_counter();records=[]
    for step,idx in enumerate(schedule,1):
        model.train();D,c,r,J=(x[idx] for x in fit[:4])
        z=model.encode_geometry(D)
        rp=model.moment(z,c);jp=model.jacobian(z,c)
        loss=(rp-r).square().mean()+.5*(jp-J).square().mean()
        if not bool(torch.isfinite(loss)):raise FloatingPointError('NONFINITE_LOSS')
        opt.zero_grad(set_to_none=True);loss.backward();opt.step()
        if step%10==0 or step==steps:
            v=_metrics(model,val);score=v['r_mae']+.25*v['Jc_mae']
            records.append({'step':step,'validation_score':score})
            if score<best-1e-7:
                best=score;best_at=step;state=copy.deepcopy(model.state_dict());stale=0
            else:stale+=1
            if stale>=5:break
    duration=time.perf_counter()-start
    model.load_state_dict(state)
    return {'selected_step':best_at,'steps_executed':step,'max_steps':steps,
            'training_cpu_seconds':duration,'validation_score':best,
            'batch_schedule_sha256':hashlib.sha256(schedule.numpy().tobytes()).hexdigest(),
            'history':records}


def _probe_speed(model,D,c):
    model.eval()
    with torch.no_grad():z=model.encode_geometry(D)
    def timed(f):
        for _ in range(2):f()
        vals=[]
        for _ in range(7):
            start=time.perf_counter_ns();f();vals.append((time.perf_counter_ns()-start)*1e-6)
        return float(statistics.median(vals))
    with torch.no_grad():
        return {'cache_encode_ms':timed(lambda:model.encode_geometry(D)),
                'warm_r_ms':timed(lambda:model.moment(z,c)),
                'warm_J_ms':timed(lambda:model.jacobian(z,c))}


def _representation_study(*,seeds,resolutions=(8,16),shapes_per_seed=5):
    rows=[]
    for seed in seeds:
        for family,mesh,center,axes,hs in _shape_stream(('box','sphere','ellipsoid'),seed+401,shapes_per_seed):
            item={'seed':seed,'family':family,'mesh_sha256':mesh.identity,
                  'mesh_faces':len(mesh.faces),'true_mesh_mass':float(mesh.mesh_moments[0]),
                  'variants':{}}
            for n,samp in [(8,1)]+[(n,3 if n==8 else 2) for n in resolutions]:
                name=f'cells{n}_sub{samp}'
                start=time.perf_counter()
                sample=mesh_to_cells(mesh,resolution=n,samples_per_axis=samp)
                source_seconds=time.perf_counter()-start
                p=FrozenCellVolume(sample.D)
                full=p.evaluate(unit_vertical_native_c(-2.)).r
                cuterrs=[];jerrs=[];widths=[];covered=0
                for loc in hs:
                    h=float(center[2]+axes[2]*loc)
                    ref=_target_for_mesh(mesh,h)
                    result=p.evaluate(unit_vertical_native_c(h))
                    if result.Jc is None:raise RuntimeError('unexpected piecewise Jacobian failure')
                    l,u=p.mass_overlap_bracket(unit_vertical_native_c(h),sample)
                    covered+=int(l-1e-9<=ref.r[0]<=u+1e-9)
                    widths.append((u-l)/max(ref.r[0],1e-12))
                    cuterrs.append(float(np.abs(result.r-ref.r).mean()))
                    jerrs.append(float(np.abs(result.Jc-ref.Jc).mean()))
                item['variants'][name]={
                    'r_full_mae':float(np.abs(full-mesh.mesh_moments).mean()),
                    'mass_full_relative_error':float(abs(full[0]-mesh.mesh_moments[0])/mesh.mesh_moments[0]),
                    'cut_r_mae':float(np.mean(cuterrs)),
                    'cut_J_mae':float(np.mean(jerrs)),
                    'mass_cut_bounds_covered':covered,'mass_cut_bounds_cases':len(hs),
                    'mean_cut_interval_relative_width':float(np.mean(widths)),
                    'uncertain_cells':sample.uncertain_cells,
                    'geometry_encoding_seconds':source_seconds,
                    'source_voxel_sha256':sample.voxel_sha256,
                    'model_input_only':'SAME_4CH_VOXEL_D_NO_PRIMITIVE_PARAMS'}
            rows.append(item)
    names=sorted(rows[0]['variants'])
    agg={name:{key:float(statistics.mean(row['variants'][name][key] for row in rows))
          for key in ('r_full_mae','mass_full_relative_error','cut_r_mae','cut_J_mae',
                      'mean_cut_interval_relative_width','geometry_encoding_seconds')}
          for name in names}
    for name in names:
        agg[name]['mass_cut_bounds_covered']=sum(r['variants'][name]['mass_cut_bounds_covered'] for r in rows)
        agg[name]['mass_cut_bounds_cases']=sum(r['variants'][name]['mass_cut_bounds_cases'] for r in rows)
    return {'rows':rows,'aggregate':agg,'unique_meshes':len(rows)}


def run(*,seeds=(131,137,139),per_family_train=10,per_family_test=6,steps=80,
        representation_per_family=3,include_neural=True):
    if len(set(seeds))!=len(seeds) or not seeds or per_family_train<5 or per_family_test<1 or steps<1:
        raise ValueError('invalid protocol')
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    representation=_representation_study(seeds=seeds,shapes_per_seed=representation_per_family)
    model_receipts=[];counts={}
    if include_neural:
        for seed in seeds:
            data,_=_load_split(('box','sphere'),seed,per_family_train)
            held,_=_load_split(('ellipsoid',),seed+1,per_family_test)
            train,val=_train_valid(data,seed)
            ids=[{x['mesh_sha256'] for x in block[4]} for block in (train,val,held)]
            if ids[0]&ids[1] or ids[0]&ids[2] or ids[1]&ids[2]:raise RuntimeError('GEOMETRY_SPLIT_LEAK')
            row={'seed':seed,'train_full_sha256':_digest(data),'test_sha256':_digest(held),
                 'train_shapes':len(ids[0]),'val_shapes':len(ids[1]),'test_shapes':len(ids[2]),
                 'input_protocol':'SAME_FROZEN_TRI_MESH_VOXEL_8_3_SUB3_FOUR_CHANNELS',
                 'labels':'SOURCE_MESH_CONVEX_NUMERIC_PLANAR_CUT_NOT_W2','models':{}}
            for kind in ('w6_m7','w5_voxel_deeponet'):
                torch.manual_seed(seed)
                model=(RealizableUFNOMoment(temperature=.12,points_per_axis=6,hidden=32,grid_size=8)
                       if kind=='w6_m7' else W5VoxelDeepONet())
                params=num_real_parameters(model)
                counts[kind]=params
                rec=_fit(model,train,val,seed=seed,steps=steps)
                test=_metrics(model,held)
                speed=_probe_speed(model,held[0][:1],held[1][:1])
                row['models'][kind]={'training':rec,'heldout':test,'cpu_latency':speed}
            model_receipts.append(row)
    if include_neural and max(counts.values())/min(counts.values())>1.05:
        raise RuntimeError('MODEL_PARAMETER_BUDGET_MISMATCH')
    agg={kind:{k:float(statistics.mean(item['models'][kind]['heldout'][k] for item in model_receipts))
                for k in ('r_mae','Jc_mae','negative_mass_fraction','r_relative_l2')}
         for kind in counts}
    return {'schema':'W6_M13_MESH_SOURCE_AND_CELL_INTEGRAL_P0_V1','seeds':list(seeds),
            'original_W6_M12_parent':'bfa8d0c767fc3cb69216db6a8a2801e200b43365',
            'frozen_native_source':'0bcc187b3005478baa586a6d6f450e73811ca342',
            'W2_admitted_native_teacher_labels':0,'new_cherchi_calls':0,
            'source_only_preprocessing_no_analytic_shape_axes_after_mesh_generation':True,
            'source_labels':'CONVEX_MESH_VERTICAL_NUMERIC_P0_NOT_W2',
            'python':platform.python_version(),'torch':torch.__version__,'numpy':np.__version__,
            'cpu_only':True,'neural_training_steps_max':steps,'trainable_parameters':counts,
            'representation':representation,'trained_models':model_receipts,
            'matched_neural_aggregate':agg,
            'limitations':['Triangulated mesh may differ from original smooth primitive',
               'Mesh topology/embedding and original CAD Boolean not independently certified',
               'Conservative voxel bounds only conditional on mesh embedding; not exact CAD certificate',
               'Only positive vertical P0 plane; oblique and quadratic c rejected by local proxy',
               'Node and cell sampled D have distinct semantics; both models see same cell source',
               'No independent real Cherchi supervision or 10D Newton terminal',
               'No GPU or Faster native end-to-end timing']}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--seeds',default='131,137,139')
    p.add_argument('--per-family-train',type=int,default=10)
    p.add_argument('--per-family-test',type=int,default=6)
    p.add_argument('--representation-per-family',type=int,default=3)
    p.add_argument('--steps',type=int,default=80)
    p.add_argument('--no-neural',action='store_true')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    result=run(seeds=tuple(int(x) for x in args.seeds.split(',')),
               per_family_train=args.per_family_train,per_family_test=args.per_family_test,
               representation_per_family=args.representation_per_family,
               steps=args.steps,include_neural=not args.no_neural)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps({'schema':result['schema'],'seeds':result['seeds'],
                      'representation_aggregate':result['representation']['aggregate'],
                      'matched_neural_aggregate':result['matched_neural_aggregate'],
                      'parameters':result['trainable_parameters']},indent=2))

if __name__=='__main__':main()
