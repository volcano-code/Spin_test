"""W5 M13: matched-data cell-volume vs W6-Gauss-capacity analytic P0 audit.

No neural weights are trained and no W2 or Cherchi data is loaded. The
nonnegative Gauss baseline is explicitly the *untrained maximum-density node
capacity* of W6 M7, NOT a trained W6 M7 prediction. For the Gauss hard atom
baseline J is unavailable (hard sign changes at nodes). No fictitious speedup,
CAD/Boolean volume or W0 smooth native teacher is claimed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import time

import numpy as np
import torch
from torch.nn.functional import grid_sample

from .m8_analytic_data import Shape,POWERS, dataset,sha_dataset
from .m13_cell_integrals import B
from .m13_cell_integrals import CellwiseMomentReference


def center_cell_voxel(shape: Shape, n: int) -> np.ndarray:
    """New source convention: sample analytic shape at the *center* of each cell.

    Oracle shape is used only to construct this controlled analytic P0 input.
    These bits do NOT represent a real CAD/physical signed material boundary.
    """
    if n<4 or not isinstance(shape,Shape):
        raise ValueError('invalid analytic shape or resolution')
    t=np.linspace(-1.+1/n,1.-1/n,n,dtype=np.float64)
    xyz=np.stack(np.meshgrid(t,t,t,indexing='ij'),axis=-1)
    u=(xyz-np.asarray(shape.center))/np.asarray(shape.axes)
    level=np.max(np.abs(u),axis=-1)-1 if shape.family=='box' else np.sqrt((u*u).sum(-1))-1
    occ=(level<=0).astype(np.float32)
    return np.stack((occ*shape.density,occ,level.astype(np.float32),
                     np.exp(-8*np.abs(level)).astype(np.float32)),axis=0)


def w6_gauss_maximum_atomic_moments(D: np.ndarray, c: np.ndarray,
                                     *, points_per_axis: int=6) -> np.ndarray:
    """W6 M7 *capacity ceiling* before its geometry-dependent learned sigmoid.

    Each positive mass cap uses Gauss volume weights * interpolated density *
    interpolated occupancy (W6 M7 exact convention). Then a HARD q.m>=0
    selector is used only to compare raw moments. It has NO valid smooth Jc.
    An actual W6 M7 model needs trained learned_gate and sigmoid temperature;
    this function is not its learned output and must not be ranked as such.
    """
    if D.ndim!=4 or D.shape[0]!=4 or not np.isfinite(D).all() or np.min(D[0])<0 or np.min(D[1])<0 or np.max(D[1])>1:
        raise ValueError('invalid four-channel density or occupancy')
    if c.shape!=(10,) or not np.isfinite(c).all():
        raise ValueError('native c shape')
    gauss,one=np.polynomial.legendre.leggauss(points_per_axis)
    coords=np.stack(np.meshgrid(gauss,gauss,gauss,indexing='ij'),-1).reshape(-1,3)
    vol=np.prod(np.stack(np.meshgrid(one,one,one,indexing='ij'),-1),-1).reshape(-1)
    grid=torch.tensor(coords[:,[2,1,0]],dtype=torch.float32).view(1,-1,1,1,3)
    voxel=torch.from_numpy(np.ascontiguousarray(D[:2])).float()[None]
    with torch.no_grad():
        samples=grid_sample(voxel,grid,mode='bilinear',padding_mode='zeros',align_corners=True)
    nodes=samples.flatten(2).squeeze(0).cpu().numpy()
    capacities=vol*nodes[0]*nodes[1]
    if not np.isfinite(capacities).all() or np.min(capacities)<-1e-9:
        raise ValueError('negative Gauss atomic capacity')
    mm=np.stack([np.prod(coords**np.array(p)[None,:],axis=-1) for p in POWERS],axis=-1)
    q=B*c
    active=(mm@q>=0).astype(np.float64)
    return np.einsum('k,ki->i',capacities*active,mm)


def run(*, seeds=(67,71,73), per_family=6, resolutions=(8,16,24),
        queries=2, also_legacy=True)->dict:
    if not seeds or len(set(seeds))!=len(seeds) or not resolutions or min(resolutions)<4:
        raise ValueError('nonempty unique seeds / resolutions>=4 required')
    if per_family<2 or queries<1:
        raise ValueError('insufficient independent analytic geometries/queries')
    torch.set_num_threads(1)
    rows=[]; source_hashes={}
    for seed in seeds:
        data=dataset(('box','sphere','ellipsoid'),per_family=per_family,seed=seed,
                     grid_size=8,queries=queries)
        source_hashes[str(seed)]=sha_dataset(data)
        observed=set()
        for i,meta in enumerate(data[4]):
            shape_data=meta['shape']
            shape=Shape(meta['family'],tuple(shape_data['center']),tuple(shape_data['axes']),shape_data['density'])
            gid=meta['geometry_id']
            if gid!=shape.identity:
                raise ValueError('geometry hash mismatch')
            c=np.asarray(data[1][i].numpy(),dtype=np.float64)
            expected_r=np.asarray(data[2][i].numpy(),dtype=np.float64)
            expected_J=np.asarray(data[3][i].numpy(),dtype=np.float64)
            # The saved c and expected J were produced at binary32 precision
            # by the frozen M8 generator; compare to that SAME native c.
            for n in resolutions:
                voxel=center_cell_voxel(shape,int(n))
                t0=time.perf_counter_ns()
                reference=CellwiseMomentReference.bind(voxel)
                encode_ms=(time.perf_counter_ns()-t0)*1e-6
                t0=time.perf_counter_ns();current=reference.evaluate(c)
                query_ms=(time.perf_counter_ns()-t0)*1e-6
                if current['Jc'] is None:
                    raise RuntimeError('unexpected stratum boundary; do not fill unavailable J')
                gauss=w6_gauss_maximum_atomic_moments(voxel,c)
                rows.append({'seed':seed,'family':shape.family,'geometry_id':gid,
                             'query_index':meta.get('query_index',i%queries),
                             'n':int(n),'input_sampling':'CELL_CENTER',
                             'source_sha256':reference.source_sha256,
                             'r_mae':float(np.abs(current['r']-expected_r).mean()),
                             'J_mae':float(np.abs(current['Jc']-expected_J).mean()),
                             'max_corrected_Jq_asymmetry':float(np.max(np.abs((current['Jc']/B[None,:])-(current['Jc']/B[None,:]).T))),
                             'gauss_m7_max_capacity_r_mae':float(np.abs(gauss-expected_r).mean()),
                             'gauss_m7_max_capacity_J_available':False,
                             'cell_cache_build_ms':encode_ms,'cell_r_J_ms':query_ms,
                             'real_teacher_samples_used':0})
            if also_legacy:
                # M8 supplies tensor values on linspace *nodes*, not cell centers.
                # Deliberately interpret same source as cell density to quantify
                # the resolution/convention mismatch, without re-labelling CAD.
                legacy=np.ascontiguousarray(data[0][i].numpy())
                ref=CellwiseMomentReference.bind(legacy)
                old=ref.evaluate(c)
                rows.append({'seed':seed,'family':shape.family,'geometry_id':gid,
                             'query_index':i%queries,'n':8,
                             'input_sampling':'LEGACY_NODE_AS_CELL_INVALID_MAPPING',
                             'source_sha256':ref.source_sha256,
                             'r_mae':float(np.abs(old['r']-expected_r).mean()),
                             'J_mae':float(np.abs(old['Jc']-expected_J).mean()) if old['Jc'] is not None else None,
                             'gauss_m7_max_capacity_r_mae':None,
                             'gauss_m7_max_capacity_J_available':False,
                             'cell_cache_build_ms':None,'cell_r_J_ms':None,
                             'real_teacher_samples_used':0})
    agg={}
    for mode,n in sorted({(x['input_sampling'],x['n']) for x in rows}):
        group=[x for x in rows if x['input_sampling']==mode and x['n']==n]
        def stats(key):
            vals=[x[key] for x in group if x.get(key) is not None]
            return {'mean':statistics.mean(vals) if vals else None,
                    'sample_sd':statistics.stdev(vals) if len(vals)>1 else None,
                    'count':len(vals)}
        agg[f'{mode}_n{n}']={key:stats(key) for key in (
            'r_mae','J_mae','gauss_m7_max_capacity_r_mae','cell_cache_build_ms','cell_r_J_ms')}
        agg[f'{mode}_n{n}']['independent_geometries']=len({x['geometry_id'] for x in group})
    return {'schema':'W5_M13_CONTINUOUS_VOXEL_CELL_P0_V1',
            'source':'ANALYTIC_PRIMITIVE_HELDOUT_REFERENCE_NOT_REAL_CAD',
            'W0_native_c':'CONST,X,Y,Z,XX,YY,ZZ,YZ,XZ,XY',
            'W0_B_diag':[1]*7+[2]*3,'raw_r_is_undoubled':True,
            'oracle_native_cherchi_queries':0,'formal_W2_J_training_labels':0,
            'source_density_policy':'DECLARED_PIECEWISE_CONSTANT_PER_CELL_NOT_CAD',
            'W6_comparator':'M7_GAUSS_NONNEGATIVE_ATOM_CAPACITY_HARD_CUT_UNTRAINED_NOT_M7_LEARNED_NETWORK',
            'W6_comparator_Jc_unavailable':True,
            'dataset_sha256_per_seed':source_hashes,
            'seeds':list(seeds),'per_family':per_family,'queries_per_geometry':queries,
            'resolutions':list(resolutions),'count':len(rows),
            'distinct_geometry_ids':len({r['geometry_id'] for r in rows}),
            'CPU_threads':torch.get_num_threads(),'torch_version':torch.__version__,
            'platform':platform.python_version(),'rows':rows,'aggregate':agg,
            'limitations':[
                'Ground truth is closed analytic continuum primitive, not true voxel/CAD/Boolean geometry',
                'Cellwise integral is exact only for its declared piecewise-constant proxy',
                'Saved M8 8^3 voxel was sampled at linspace nodes, so reinterpreting as cells is not exact frame mapping',
                'Gauss maximum capacity is NOT a trained W6 M7 model, nor a legal ambient Jacobian',
                'Nonvertical quadratic cuts, cell contacts, true Cherchi smoothness and final Newton are not covered',
                'Per-call CPU timings include small array overhead, are NOT native solver speedups',
            ]}


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--seeds',default='67,71,73')
    parser.add_argument('--per-family',type=int,default=6)
    parser.add_argument('--resolutions',default='8,16,24')
    parser.add_argument('--queries',type=int,default=2)
    parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args()
    out=run(seeds=tuple(map(int,a.seeds.split(','))),
            per_family=a.per_family,resolutions=tuple(map(int,a.resolutions.split(','))),
            queries=a.queries)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'schema':out['schema'],'seeds':out['seeds'],
                      'count':out['count'],'distinct_geometry_ids':out['distinct_geometry_ids'],
                      'aggregate':out['aggregate']},indent=2,sort_keys=True))

if __name__=='__main__':main()
