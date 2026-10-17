"""An archived V4 Heart diagnostic on the *actual* Cherchi-produced moment map.

This uses exactly the existing production InProcessCherchiEvaluator for the
Boolean material, intersection motion, ten moments and ten-by-ten Jacobian.
It does not substitute CGAL, voxelization or hand-coded approximate moments.
Frozen ORIGINAL Heart eval60 operands are not available in the public archive;
this explicit proxy never grants formal solve/derivative admission.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from heart_h6_authority import verify_v4_proxy

H6_ROOT=Path(__file__).resolve().parents[1]
SCALES=(3e-6,1.5e-6,0.75e-6)

def stored_sha256(file):return hashlib.sha256(Path(file).read_bytes()).hexdigest()

def make_engine(fixture,registration):
    from make_it_stand import spin
    from make_it_stand.verification.cherchi_inprocess import InProcessCherchiEvaluator
    p,r=verify_v4_proxy(fixture,registration)
    raw=p['requests'][1]['request'].copy()
    if raw['settings']['deterministic_seed'] != 1:
        raise ValueError('ARCHIVED_PROXY_SEED_NOT_1')
    raw['settings']=spin.SpinSolverConfig(**raw['settings'])
    req=spin.SpinItFasterRequest(**raw)
    options=p['evaluator_settings'].copy()
    options.update(paper_projective_hyperboloid=True,retain_fixed_normal_provenance=True)
    settings=spin.SpinEvaluatorConfig(**options)
    q=np.asarray(r['event']['quadric_coefficients'],dtype=np.float64)
    if q.shape!=(10,) or not np.isfinite(q).all() or abs(float(np.linalg.norm(q))-1)>1e-12:
        raise ValueError('ARCHIVED_QUADRIC_NOT_A_UNIT_COEFFICIENT')
    engine=InProcessCherchiEvaluator(req,settings,branch_identity_policy='SOURCE_FEATURE_BRANCH_V2',
             normalization={'origin':[0.,0.,0.],'L':1.},rational_arithmetic_backend='PYTHON_FRACTION_V1',
             fixed_boundary_reuse=False,integral_profile='EXACT_GMP_V1')
    if not engine.backend_identity.startswith('cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'):
        raise RuntimeError('CHERCHI_BACKEND_MISMATCH_NO_FALLBACK')
    return engine,q

def five_point_weights(actual_positions):
    """Derivative weights exact for polynomials up to degree 4 at observed abscissae."""
    x=np.asarray(actual_positions,dtype=np.float64)
    if x.shape!=(5,) or not np.isfinite(x).all() or len(set(x))!=5:
        raise ValueError('FIVE_DISTINCT_FD_POSITIONS_REQUIRED')
    scale=float(np.max(np.abs(x)))
    if scale<=0:raise ValueError('INVALID_FD_SCALE')
    v=np.vstack([(x/scale)**k for k in range(5)])
    w=np.linalg.solve(v,np.array([0.,1.,0.,0.,0.]))/scale
    if np.max(np.abs(v@(w*scale)-[0,1,0,0,0]))>1e-10:
        raise ValueError('FIVE_POINT_STENCIL_NOT_CERTIFIED')
    return w

def planned_samples(q,directions):
    samples=[np.asarray(q,dtype=np.float64).copy()]
    index={tuple(samples[0]):0}
    layouts=[]
    for col in directions:
        for h in SCALES:
            ids=[];positions=[]
            for shift in (-h,-h/2,0,h/2,h):
                at=q.copy();at[col]+=shift
                key=tuple(at)
                if key not in index:index[key]=len(samples);samples.append(at)
                ids.append(index[key]);positions.append(float(at[col]-q[col]))
            layouts.append(dict(column=col,h=h,indices=ids,positions=positions))
    if len(samples)!=1+8*len(directions):
        raise ValueError('FIVE_POINT_UNIQUE_SAMPLE_PROTOCOL_CHANGED')
    return samples,layouts

def evaluate(engine,q,directions,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    samples,layouts=planned_samples(q,directions)
    start=time.monotonic()
    data=[]
    with (output/'events.jsonl').open('x',encoding='utf8') as ev:
        for i,coefficients in enumerate(samples):
            t=time.monotonic()
            try:
                m=engine(coefficients)
                mass=np.asarray(m['raw_moments'],dtype=np.float64)
                jac=np.asarray(m['moment_jacobian'],dtype=np.float64)
                if mass.shape!=(10,) or jac.shape!=(10,10) or not np.isfinite(mass).all() or not np.isfinite(jac).all():
                    raise ValueError('CHERCHI_NONFINITE_MOMENT_OR_JACOBIAN')
                if not str(m['boolean_backend_identity']).startswith('cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'):
                    raise ValueError('NON_CHERCHI_MATERIAL_BACKEND_FORBIDDEN')
                rec=dict(index=i,quadric_coefficients=coefficients.tolist(),raw_moments=mass.tolist(),
                    branch=m['topology_hash'],material_hash=m['geometry_hash'],
                    backend=m['boolean_backend_identity'],moment_jacobian=jac.tolist() if i==0 else None,
                    elapsed_seconds=time.monotonic()-t)
                data.append(rec)
                ev.write(json.dumps({'index':i,'status':'ACTUAL_CHERCHI_MATERIAL_RETURNED',
                                      'branch':rec['branch'],'elapsed_seconds':rec['elapsed_seconds']})+'\n')
                ev.flush()
                print(f'H6 MATERIAL {i+1}/{len(samples)} {rec["elapsed_seconds"]:.2f}s',flush=True)
            except Exception as exc:
                ev.write(json.dumps({'index':i,'status':'ACTUAL_CHERCHI_MATERIAL_FAILED',
                                    'error':f'{type(exc).__name__}: {exc}'})+'\n');ev.flush()
                (output/'failure.json').write_text(json.dumps({'index':i,'error':str(exc),'completed':False},indent=2)+'\n')
                raise
    base=np.asarray(data[0]['moment_jacobian']);checks=[]
    for l in layouts:
        col=l['column'];w=five_point_weights(l['positions'])
        values=np.asarray([data[j]['raw_moments'] for j in l['indices']])
        numeric=w@values
        observed=base[:,col]
        scale=np.maximum(1.,np.abs(observed))
        maxerr=float(np.max(np.abs(numeric-observed)/scale))
        stability=all(data[j]['branch']==data[0]['branch'] for j in l['indices'])
        checks.append({'column':col,'step':l['h'],'sample_indices':l['indices'],
            'maximum_relative_error':maxerr,'numerical_tolerance':1e-6,
            'numeric_passed':bool(maxerr<=1e-6),
            'same_feature_branch':stability,
            'analytic':observed.tolist(),'independent_fd':numeric.tolist()})
    rad=float(np.linalg.norm(base@q))
    report=dict(schema='heart-h6-proxy-cherchi-10x10-jacobian-probe-v1',
      scope='ARCHIVED_V4_PROXY_NOT_AUTHORITATIVE_EVAL60_NOT_FORMAL_HEART',
      ten_by_ten_jacobian_computed=True,columns_evaluated=directions,
      sample_count=len(data),planned_full_protocol_samples=81,
      all_numerical_checks_passed=all(x['numeric_passed'] for x in checks),
      all_feature_branches_stable=all(x['same_feature_branch'] for x in checks),
      original_evaluation_60_reproduced=False,formal_heart_jacobian_qualified=False,
      physical_moments_independently_certified=False,original_newton_converged=False,
      coefficient_scale_null_norm=rad,raw_moments=data[0]['raw_moments'],
      jacobian=data[0]['moment_jacobian'],checks=checks,
      evaluated_points=[{k:v for k,v in d.items() if k!='moment_jacobian'} for d in data],
      backend=engine.backend_identity,call_counts=engine.call_counts,
      elapsed_seconds=time.monotonic()-start)
    (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print('H6_REPORT '+json.dumps({k:report[k] for k in ('sample_count','columns_evaluated','all_numerical_checks_passed','all_feature_branches_stable','coefficient_scale_null_norm','elapsed_seconds')}),flush=True)
    return report

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--archived-v4',type=Path,required=True)
    ap.add_argument('--registered-q',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--columns',default='0',help='comma-separated columns 0..9; full protocol use 0,1,2,3,4,5,6,7,8,9')
    args=ap.parse_args()
    cols=[int(x) for x in args.columns.split(',')]
    if not cols or len(set(cols))!=len(cols) or any(x<0 or x>=10 for x in cols):
        raise ValueError('INVALID_DIRECTION_LIST')
    engine,q=make_engine(args.archived_v4,args.registered_q)
    report=evaluate(engine,q,cols,args.output)
    if not report['all_numerical_checks_passed'] or not report['all_feature_branches_stable']:
        raise SystemExit(2)
if __name__=='__main__':main()
