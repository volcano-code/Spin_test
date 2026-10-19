"""W0 M6: independent exact full F/D/retained/cavity partition of ONE Cherchi source.

This module has an arithmetic-only coordinate inverse and an actual native path.
The live path invokes M5 (one retained Cherchi Boolean), then reuses the SAVED
quadric source for its opposite-side Boolean. No second source triangulation.
It requires the real native ExactMaterialRegion predicates, not caller JSON.
A full partition is not a smooth-Jacobian or Newton terminal certificate.
"""
from __future__ import annotations

from fractions import Fraction
import math
import resource
import time

from .native_teacher_replay import (ReplayRejected, affine_target_from_physical,
    boundary_rows, compare_floats, exact_raw_moments, need, sha256_file,
    vector10, digest)
from .native_m5_bridge import audit_native_w0_w2_once


def _finite(value, description):
    need(type(value) in (int, float) and not isinstance(value, bool),
         f'{description}: EXPECTED_FROZEN_BINARY64')
    try:
        x=float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ReplayRejected(f'{description}: UNREPRESENTABLE') from exc
    need(math.isfinite(x), f'{description}: NONFINITE')
    return Fraction.from_float(x)


def _vec3(v, what):
    need(isinstance(v,(tuple,list)) and len(v)==3, f'{what}: THREE_COORDINATES_REQUIRED')
    return tuple(_finite(x,what) for x in v)


def _matrix3(rows):
    need(isinstance(rows,(tuple,list)) and len(rows)==3,
         'TARGET_AXES_SHAPE_INVALID')
    return tuple(_vec3(row,'axes') for row in rows)


def inverse3_exact(A):
    """Inverse of actual binary64 entries viewed as exact rationals.

    A may be slightly non-orthogonal in rational arithmetic even when an
    orthonormal binary64 frame passed the native frame tolerance.
    """
    rows=[list(row)+[Fraction(int(i==j)) for j in range(3)]
          for i,row in enumerate(_matrix3(A))]
    for k in range(3):
        pivot=next((i for i in range(k,3) if rows[i][k]),None)
        need(pivot is not None,'SINGULAR_EXACT_TARGET_FRAME')
        rows[k],rows[pivot]=rows[pivot],rows[k]
        scale=rows[k][k]
        rows[k]=[v/scale for v in rows[k]]
        for i in range(3):
            if i!=k:
                coeff=rows[i][k]
                rows[i]=[a-coeff*b for a,b in zip(rows[i],rows[k])]
    return tuple(tuple(row[3:]) for row in rows)


def to_rational_tokens(points):
    return [[f'{v.numerator}/{v.denominator}' for v in row] for row in points]


def parse_exact_points(tokens):
    from .native_teacher_replay import frac
    need(type(tokens) in (list,tuple),'MISSING_EXACT_TARGET_POINTS')
    rows=[]
    for row in tokens:
        need(type(row) in (list,tuple) and len(row)==3, 'INVALID_EXACT_TARGET_ROW')
        rows.append(tuple(frac(x) for x in row))
    need(rows,'EMPTY_EXACT_TARGET_ROWS')
    return tuple(rows)


def _physical_from_parsed_target(target, *, original_origin,
                                 normalization_length, target_origin, target_axes):
    axes=_matrix3(target_axes)
    inv=inverse3_exact(target_axes)
    norm_origin=_vec3(original_origin,'normalized_origin')
    shift=_vec3(target_origin,'target_origin')
    length=_finite(normalization_length,'length')
    need(length>0,'NONPOSITIVE_NORMALIZATION_LENGTH')
    out=[]
    for point in target:
        need(len(point)==3 and all(isinstance(v,Fraction) for v in point),
             'EXACT_TARGET_POINT_REQUIRED')
        model=tuple(sum((point[k]*inv[k][j] for k in range(3)),Fraction(0))
                    for j in range(3))
        physical=tuple((model[j]+shift[j])*length+norm_origin[j] for j in range(3))
        out.append(physical)
    # Roundtrip must match exactly, not by a 1e-6 or percent threshold.
    back=affine_target_from_physical(out,origin=tuple(map(float,norm_origin)),
        length=float(length),target_origin=tuple(map(float,shift)),
        target_axes=[[float(x) for x in row] for row in axes])
    need(back==tuple(target),'EXACT_AFFINE_INVERSE_NOT_IDENTITY')
    return tuple(out)


def physical_from_target_points(target_tokens, *, original_origin,
                                normalization_length, target_origin, target_axes):
    return _physical_from_parsed_target(parse_exact_points(target_tokens),
        original_origin=original_origin, normalization_length=normalization_length,
        target_origin=target_origin,target_axes=target_axes)


def partition_result(facts, label, expected_parts):
    """Require every native output gate; pure dict alone NEVER certifies origin."""
    need(type(facts) is dict,f'{label}: NATIVE_PARTITION_FACTS_REQUIRED')
    for flag in ('completed','complete_partition','union_equals_whole',
                 'no_positive_volume_overlap'):
        need(facts.get(flag) is True,f'{label}: NATIVE_{flag.upper()}_FAILED')
    subsets=facts.get('part_subset_whole')
    need(type(subsets) in (list,tuple) and len(subsets)==expected_parts and
         all(v is True for v in subsets),f'{label}: NATIVE_PART_SUBSET_FAILED')
    for flag in ('missing_whole_content','excess_union_content'):
        need(facts.get(flag) is False,f'{label}: NATIVE_{flag.upper()}_FOUND')
    overlap=facts.get('positive_volume_overlap_pairs')
    need(type(overlap) in (list,tuple) and len(overlap)==0,
         f'{label}: NATIVE_OVERLAPPING_PAIRS')
    sha=facts.get('partition_digest')
    need(type(sha) is str and len(sha)==64 and all(c in '0123456789abcdef' for c in sha),
         f'{label}: MISSING_NATIVE_PARTITION_DIGEST')
    return {'label':label,'part_count':expected_parts,'partition_digest':sha,
            'structural_flags_checked':True,'proves_actual_native_execution':False}


def _region(native, mesh):
    region=mesh.exact_region()
    need(type(region) is native.ExactMaterialRegion,
         'NATIVE_OWNED_EXACT_MATERIAL_REGION_REQUIRED')
    facts=region.facts
    need(type(facts) is dict and facts.get('completed') is True and
         facts.get('valid') is True, 'INVALID_OWNED_EXACT_REGION')
    return region


def _physical_points_from_snapshot(mesh):
    rational=mesh.rational_vertices
    if rational is not None:
        return parse_exact_points(rational)
    v,_=mesh.arrays()
    need(len(v)>0,'EMPTY_LOCKED_MESH')
    return tuple(tuple(Fraction.from_float(float(x)) for x in row) for row in v)


def _r_target(mesh, *, evaluator, density):
    v,f=mesh.arrays()
    if mesh.explicit_empty:
        return (Fraction(0),)*10
    exact_points=_physical_points_from_snapshot(mesh)
    target=affine_target_from_physical(exact_points,
        origin=evaluator.normalization_origin.tolist(),length=evaluator.length,
        target_origin=evaluator.request.target_origin,target_axes=evaluator.request.target_axes)
    faces=tuple(tuple(int(i) for i in row) for row in f)
    rho=Fraction.from_float(float(density))
    return exact_raw_moments(target,faces,rho)


def audit_native_full_partition_once(*,evaluator,problem,c,pins):
    """Run ONE source, retained + complementary exact Boolean, verify three partitions.

    By design still returns training_admissible=False, even if every geometry
    predicate passes. The Newton terminal and derivative neighborhood are
    independent tasks; saved claims/JSON flags are not executable proof.
    """
    baseline=audit_native_w0_w2_once(evaluator=evaluator,problem=problem,c=c,pins=pins)
    need(type(baseline) is dict and baseline.get('schema')=='W0_M5_LIVE_W0_W2_PARITY_V1'
         and baseline.get('training_admissible') is False,
         'REAL_M5_NATIVE_AUDIT_REQUIRED')
    m4=baseline.get('m4_native_evidence')
    need(type(m4) is dict and m4.get('native_execution_observed') is True and
         m4.get('native_region_proved') is True,
         'AUTHENTIC_M4_NATIVE_PROVENANCE_REQUIRED')
    try:
        from make_it_stand.verification.cherchi_inprocess import InProcessCherchiEvaluator
        from make_it_stand.verification.spin_problem import MeshSnapshot, SpinArtifactProblem
        from make_it_stand.verification.spin_common import native
    except (RuntimeError,ImportError) as exc:
        raise ReplayRejected('NATIVE_EXACT_PARTITION_RUNTIME_UNAVAILABLE') from exc
    need(type(evaluator) is InProcessCherchiEvaluator and
         type(problem) is SpinArtifactProblem,
         'Genuine_CHERCHI_AND_IMMUTABLE_PROBLEM_REQUIRED')
    n=native()
    for meth in ('check_exact_material_partition','make_exact_material_region_from_rationals'):
        need(callable(getattr(n,meth,None)), 'NATIVE_EXACT_PARTITION_FUNCTION_UNAVAILABLE:'+meth)
    need(len(problem.design_regions)==1,'EXACTLY_ONE_DESIGN_REGION_REQUIRED')
    fixed_regions=tuple(problem.fixed_regions)
    c=vector10(c,'native_c')
    saved=evaluator.material(c)
    source_before=int(evaluator.call_counts.get('source',0))
    boolean_before=int(evaluator.call_counts.get('boolean',0))
    old_stage=dict(evaluator.stage_seconds)
    before_rss=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024
    before_time=time.perf_counter()
    complement=InProcessCherchiEvaluator.complement_of_saved_source(evaluator,saved)
    complement_wall_seconds=time.perf_counter()-before_time
    after_rss=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024
    complement_stages={name:float(seconds)-float(old_stage.get(name,0.))
                       for name,seconds in evaluator.stage_seconds.items()}
    need(math.isfinite(complement_wall_seconds) and complement_wall_seconds>=0 and
         all(math.isfinite(v) and v>=0 for v in complement_stages.values()),
         'INVALID_COMPLEMENT_TIMINGS')
    need(evaluator.call_counts.get('source',0)==source_before and
         evaluator.call_counts.get('boolean',0)==boolean_before+1,
         'COMPLEMENT_REBUILT_SOURCE_OR_SKIPPED_BOOLEAN')
    for key in ('quadric_source_identity','quadric_source_vertices','quadric_source_faces'):
        need(complement.get(key)==saved.get(key),
             'OPPOSITE_MATERIAL_SOURCE_IDENTITY_MISMATCH:'+key)
    before=saved.get('boolean_operation')
    need(before in ('intersection','subtraction') and
         complement.get('boolean_operation')!=before and
         complement.get('boolean_operation') in ('intersection','subtraction'),
         'COMPLEMENT_NOT_OPPOSITE_BOOLEAN')
    rho=Fraction.from_float(float(evaluator.request.material_density))
    need(rho>0,'NONPOSITIVE_DESIGN_DENSITY')
    original=_region(n,problem.original)
    design=_region(n,problem.design_regions[0].mesh)
    fixed=[_region(n,region.mesh) for region in fixed_regions if not region.mesh.explicit_empty]
    # Retained physical coordinates, as certified in M4: exact authored
    # constructor boundary; cannot infer from rendered binary64 vertices.
    retained_v=saved['material_proof']['exact_vertices']
    retained_f=saved['variable_faces']
    retained=MeshSnapshot.from_rationals(retained_v,retained_f)
    retained_region=_region(n,retained)
    cavity_tokens=complement.get('variable_rational_vertices')
    faces=complement.get('variable_faces')
    if cavity_tokens == [] and faces == []:
        cavity=MeshSnapshot(None)
        cavity_target=(Fraction(0),)*10
    else:
        need(type(faces) is list and len(faces)>0,'MISSING_CAVITY_BOUNDARY')
        physical=physical_from_target_points(cavity_tokens,
             original_origin=evaluator.normalization_origin.tolist(),
             normalization_length=evaluator.length,
             target_origin=evaluator.request.target_origin,
             target_axes=evaluator.request.target_axes)
        cavity=MeshSnapshot.from_rationals(to_rational_tokens(physical),faces)
        cavity_target=exact_raw_moments(parse_exact_points(cavity_tokens),
             tuple(tuple(int(i) for i in row) for row in faces),rho)
        reported=vector10(complement.get('variable_raw_moments'),'complement.rD')
        compare_floats(reported,cavity_target,label='CAVITY_EXACT_MOMENTS')
    cavity_region=_region(n,cavity)
    parts=(('fixed_plus_design',[*fixed,design]),
           ('design_cut',[retained_region,cavity_region]),
           ('full_outer',[*fixed,retained_region,cavity_region]))
    results=[]
    for label,regions in parts:
        whole=design if label=='design_cut' else original
        fact=n.check_exact_material_partition(whole,regions)
        summary=partition_result(fact,label,len(regions))
        summary['native_predicate_facts']=fact  # Keep original full witness, not just pass bits.
        results.append(summary)
    retained_target=_r_target(retained,evaluator=evaluator,
                              density=evaluator.request.material_density)
    design_target=_r_target(problem.design_regions[0].mesh,evaluator=evaluator,
                            density=evaluator.request.material_density)
    need(all(a+b==d for a,b,d in zip(retained_target,cavity_target,design_target)),
         'EXACT_CARVE_PLUS_RETAIN_MOMENTS_DIFFER_FROM_DESIGN')
    fixed_total=[Fraction(0)]*10
    density_ref=float(problem.normalization['R'])
    need(math.isfinite(density_ref) and density_ref>0,'INVALID_FROZEN_DENSITY_NORMALIZATION')
    for region in fixed_regions:
        if region.mesh.explicit_empty:continue
        normalized_density=float(region.density)/density_ref
        x=_r_target(region.mesh,evaluator=evaluator,density=normalized_density)
        fixed_total=[a+b for a,b in zip(fixed_total,x)]
    observed_fixed=vector10(evaluator.fixed,'frozen.rF')
    compare_floats(observed_fixed,fixed_total,label='FROZEN_FIXED_REGIONS_EXACT_R')
    return {
        'schema':'W0_M6_NATIVE_COMPLETE_MATERIAL_PARTITION_V1',
        'status':'REAL_EXACT_FULL_PARTITION_VERIFIED_DERIVATIVE_AND_TERMINAL_PENDING',
        'exact_partition_predicates':results,
        'retained_plus_cavity_equals_design_r10_exact':True,
        'fixed_plus_retained_density_weighted_moments_verified':True,
        'observed_native_source_calls':evaluator.call_counts.get('source',0),
        'observed_native_boolean_calls':evaluator.call_counts.get('boolean',0),
        'complement_additional_source_calls':0,
        'complement_additional_boolean_calls':1,
        'M5_evidence':baseline,
        'complement_wall_seconds':complement_wall_seconds,
        'complement_stage_seconds':complement_stages,
        'process_rss_hwm_before_bytes':before_rss,
        'process_rss_hwm_after_bytes':after_rss,
        'rss_metric':'LINUX_PROCESS_LIFETIME_HWM_NOT_PER_CALL_PEAK',
        'native_full_partition_certified':True,
        'smooth_derivative_certified':False,
        'newton_terminal_certified':False,
        'training_admissible':False,
        'scope':'EXACT_REPRESENTED_POLYHEDRAL_SETS_AND_R10_ONLY',
    }
