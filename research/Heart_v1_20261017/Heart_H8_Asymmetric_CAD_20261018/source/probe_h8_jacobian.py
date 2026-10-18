"""H8e: TRUE Cherchi/InProcess moment-map 10x10 Jacobian and FD pilot.

Uses the existing production InProcessCherchiEvaluator, NOT a finite-mesh
surrogate or a CGAL Boolean. This is an exploratory derivative audit, never a
formal smooth-stratum admission or Newton convergence claim.

Pilot protocol: 1 base + 8 perturbed evaluations per tested literal column.
The three scale widths and their five-point stencils are those used in H6.
"""
from __future__ import annotations
import argparse
from collections import Counter
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
import time
import traceback

import numpy as np

HERE=Path(__file__).resolve().parents[1]
H6=HERE.parent/'Cherchi_H6'
sys.path.insert(0,str(H6/'source'))
from heart_h6_cherchi_jacobian import planned_samples, five_point_weights
from probe_h8_native_cherchi import initial_ellipsoid_q, request_from_frozen
from verify_h8_exact_moments import independent_ten_raw_moments

BACKEND_PREFIX='cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'

def sha(path):
    return sha256(Path(path).read_bytes()).hexdigest()

def parse_columns(arg):
    try:
        cols=[int(x) for x in arg.split(',')]
    except (TypeError,ValueError) as exc:
        raise ValueError('INVALID_JACOBIAN_PILOT_COLUMNS') from exc
    if not cols or len(set(cols))!=len(cols) or any(x<0 or x>=10 for x in cols):
        raise ValueError('INVALID_JACOBIAN_PILOT_COLUMNS')
    return cols

def ten_by_ten_shape_check(values):
    jac=np.asarray(values,dtype=np.float64)
    if jac.shape!=(10,10) or not np.isfinite(jac).all():
        raise ValueError('ACTUAL_CHERCHI_JACOBIAN_MUST_BE_FINITE_10_X_10')
    return jac

def finite_checks(points,layouts,analytic,base_hash,tol=1e-6):
    """Pure 5-point independent numerics; not a smooth-branch proof."""
    rows=[]
    if any('independent_variable_raw_moments' not in row for row in points):
        raise ValueError('MISSING_INDEPENDENT_VARIABLE_MOMENTS')
    for layout in layouts:
        column=layout['column']
        values=np.array([points[i]['independent_variable_raw_moments'] for i in layout['indices']])
        weights=five_point_weights(layout['positions'])
        approximate=weights@values
        exact=analytic[:,column]
        scaled=float(np.max(np.abs(approximate-exact)/np.maximum(1.,np.abs(exact))))
        hashes=[points[i]['feature_branch_hash'] for i in layout['indices']]
        rows.append(dict(column=column,step=layout['h'],
            sample_indices=layout['indices'],
            max_scaled_derivative_error=scaled,
            numerical_passed=bool(scaled<=tol),
            feature_hash_stable=bool(all(h==base_hash for h in hashes)),
            comparison_meaning='FINITE_DIFFERENCE_ONLY_NOT_SMOOTH_TOPOLOGY_CERTIFICATE'))
    return rows

def run(request_file,output,columns):
    from make_it_stand.verification.cherchi_inprocess import InProcessCherchiEvaluator
    import _make_it_stand as native
    import _cherchi_core_boolean as boolean
    import _cherchi_rational_moments as arithmetic

    cols=parse_columns(columns)
    request,settings,evidence=request_from_frozen(request_file)
    if evidence.get('scope')!='H8_RECONSTRUCTED_CAD_ONLY_NOT_NATIVE_CERTIFIED_NOT_SOLVED':
        raise ValueError('H8_SOLVER_INPUT_SCOPE_CHANGED')
    if request.settings.equation_profile!='DUAL_MONOMIAL_RAW_V1':
        raise ValueError('UNREGISTERED_NEWTON_EQUATION_PROFILE')
    origin=np.asarray(request.target_origin,dtype=float)
    q=initial_ellipsoid_q(origin)
    samples,layouts=planned_samples(q,cols)
    if len(samples)!=1+8*len(cols):
        raise ValueError('INCOMPLETE_THREE_SCALE_PILOT_PROTOCOL')
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    report=dict(schema='heart-h8e-real-cherchi-jacobian-pilot-v1',
        scope='H8_RECONSTRUCTED_CAD_ONLY_NOT_AUTHOR_ORIGINAL',
        input_request_sha256=sha(request_file),actual_native_sha256=sha(native.__file__),
        actual_cherchi_sha256=sha(boolean.__file__),actual_arithmetic_sha256=sha(arithmetic.__file__),
        ambient_jacobian_shape=[10,10],columns_requested=cols,
        target_q=q.tolist(),planned_sample_count=len(samples),
        production_cherchi_calls=0,
        analytic_jacobian_at_base_computed=False,
        original_author_cad=False,complete_eighty_one_samples=False,
        qualified_branch_neighborhood=False,formal_newton_converged=False,
        objective_stationarity_certified=False)
    start=time.perf_counter()
    points=[]
    try:
        engine=InProcessCherchiEvaluator(request,settings,normalization={'origin':[0.,0.,0.],'L':1.},
            rational_arithmetic_backend='NATIVE_GMP_SURFACE_V1',
            fixed_boundary_reuse=False,integral_profile='EXACT_GMP_V1',
            branch_identity_policy='SOURCE_FEATURE_BRANCH_V2')
        if not engine.backend_identity.startswith(BACKEND_PREFIX):
            raise ValueError('DYNAMIC_BOOLEAN_NOT_PINNED_CHERCHI')
        base_jac=None
        with (output/'events.jsonl').open('x') as journal:
            for i,coefficients in enumerate(samples):
                stage='EVALUATE_INPROCESS_CHERCHI'
                tick=time.perf_counter()
                try:
                    previous=dict(engine.stage_seconds)
                    value=engine(coefficients)
                    stage='SAME_CALL_MATERIAL_ATTACHMENT'
                    material=engine.material(coefficients)
                    engine.validate_same_call_material(material,coefficients,request)
                    stage='EXACT_NATIVE_MATERIAL_GEOMETRY_AUDIT'
                    rational=material['variable_rational_vertices']
                    faces=np.asarray(material['variable_faces'],dtype=np.int32)
                    # This also verifies closedness, orientation and exact
                    # self-intersection on the actual target-frame boundary.
                    audit=dict(native.audit_exact_rational_triangle_boundary(rational,faces,'AnyNonzero'))
                    required=('boundary_valid','closed','edge_manifold','vertex_manifold',
                              'consistently_oriented','component_orientations_valid',
                              'self_intersection_completed','self_intersection_free')
                    if any(audit.get(k) is not True for k in required) or (
                        audit.get('intersecting_pairs') or audit.get('degenerate_faces')
                        or audit.get('intersection_error')):
                        raise ValueError('EVALUATED_MATERIAL_FAILED_NATIVE_EXACT_AUDIT')
                    stage='INDEPENDENT_FRACTION_MATERIAL_TEN_MOMENTS'
                    fractional=independent_ten_raw_moments(rational,faces.tolist())
                    independently=np.asarray([float(x) for x in fractional],dtype=np.float64)
                    reported=np.asarray(value['variable_raw_moments'],dtype=np.float64)
                    if independently.shape!=(10,) or reported.shape!=(10,) or not np.isfinite(reported).all():
                        raise ValueError('MOMENT_VECTOR_SHAPE_OR_FINITE_FAILED')
                    max_err=float(np.max(np.abs(independently-reported) /
                        np.maximum(1.,np.abs(reported))))
                    if max_err>1e-10:raise ValueError('INDEPENDENT_CHERCHI_MOMENTS_DIFFER')
                    jac=ten_by_ten_shape_check(value['moment_jacobian'])
                    if i==0:
                        base_jac=jac
                        report['analytic_jacobian_at_base_computed']=True
                        report['analytic_10_by_10_jacobian']=jac.tolist()
                        report['scale_null_direction_norm']=float(np.linalg.norm(jac@q))
                    stage='WRITE_EVIDENCE'
                    observed=dict(index=i,coefficients=coefficients.tolist(),
                        independent_variable_raw_moments=independently.tolist(),
                        production_variable_raw_moments=reported.tolist(),
                        full_raw_moments=np.asarray(value['raw_moments'],dtype=float).tolist(),
                        independent_moments_max_scaled_error=max_err,
                        vertex_count=len(rational),triangle_count=len(faces),
                        feature_branch_hash=str(value['topology_hash']),
                        material_geometry_hash=str(value['geometry_hash']),
                        exact_native_material_boundary_passed=True,
                        native_boolean_backend=value['boolean_backend_identity'],
                        stages_seconds={k:engine.stage_seconds[k]-previous.get(k,0.)
                            for k in engine.stage_seconds if engine.stage_seconds[k]-previous.get(k,0.)>0},
                        wall_seconds=time.perf_counter()-tick)
                    points.append(observed)
                    (output/f'point-{i:03d}.json').write_text(
                        json.dumps(observed,indent=2,allow_nan=False)+'\n')
                    report['production_cherchi_calls']=len(points)
                    journal.write(json.dumps(dict(index=i,status='ACTUAL_CHERCHI_10_MOMENTS_AND_JACOBIAN_RETURNED',
                        feature_branch_hash=observed['feature_branch_hash']))+'\n')
                    journal.flush()
                    print(f'H8e REAL_CHERCHI {i+1}/{len(samples)} '
                          f'{observed["wall_seconds"]:.2f}s',flush=True)
                except Exception as error:
                    journal.write(json.dumps(dict(index=i,status='FAILED',stage=stage,
                      error=f'{type(error).__name__}: {error}'))+'\n');journal.flush()
                    report.update(status='FAILED_NOT_CERTIFIED',failed_stage=stage,
                        failed_point_index=i,error=f'{type(error).__name__}: {error}',
                        completed_samples=len(points),time_seconds=time.perf_counter()-start)
                    (output/'failure.json').write_text(json.dumps(report,indent=2)+'\n')
                    raise
        if base_jac is None:raise ValueError('NO_BASE_JACOBIAN')
        checks=finite_checks(points,layouts,base_jac,points[0]['feature_branch_hash'])
        report.update(status='FINITE_JACOBIAN_DIAGNOSTIC_COMPLETED_NO_SMOOTH_ADMISSION',
            completed_samples=len(points),numeric_checks=checks,
            all_numerical_checks_passed=all(x['numerical_passed'] for x in checks),
            all_tested_stencils_same_feature_hash=all(x['feature_hash_stable'] for x in checks),
            changed_feature_hash_points=sum(p['feature_branch_hash']!=points[0]['feature_branch_hash'] for p in points[1:]),
            call_counts=engine.call_counts,stage_totals_seconds=engine.stage_seconds,
            wall_seconds=time.perf_counter()-start,
            qualified_branch_neighborhood=False,
            formal_newton_converged=False)
        (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        print('H8e_JACOBIAN',json.dumps({k:report[k] for k in
             ('completed_samples','columns_requested','all_numerical_checks_passed',
              'all_tested_stencils_same_feature_hash','changed_feature_hash_points',
              'scale_null_direction_norm','wall_seconds')}),flush=True)
        return report
    except Exception:
        if not (output/'failure.json').exists():
            report.update(status='FAILED_NOT_CERTIFIED',traceback=traceback.format_exc(),
                          completed_samples=len(points))
            (output/'failure.json').write_text(json.dumps(report,indent=2)+'\n')
        raise

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--request',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--columns',default='0',help='one column first, 0,4,8 after pilot')
    a=parser.parse_args()
    run(a.request,a.output,a.columns)
