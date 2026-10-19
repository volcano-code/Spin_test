"""W0 M4: independently replay same-call Cherchi material, fail closed.

The pure exact-rational replay checks *numbers and indexed closed surfaces*,
not whether a Boolean actually constructed the intended solid. The live gate
requires a real frozen in-process producer and native ExactMaterialRegion;
neither path authorizes training or a smooth derivative by itself.

No imports of W2's separate development branch. No native work at import time.
"""
from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import time
import resource

ORDER = ('M','LX','LY','LZ','QXX','QYY','QZZ','QYZ','QXZ','QXY')
SHA = re.compile(r'[0-9a-f]{64}\Z')
RATIONAL = re.compile(r'-?(?:0b[01]+|0|[1-9][0-9]*)/(?:0b[01]+|[1-9][0-9]*)\Z')

class ReplayRejected(ValueError):
    """A same-call W0 teacher replay cannot validate the supplied artifact."""


def need(test, reason):
    if not test:
        raise ReplayRejected(reason)


def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ReplayRejected('INVALID_CANONICAL_PAYLOAD') from exc


def digest(value):
    return hashlib.sha256(canonical(value).encode('ascii')).hexdigest()


def sha256_file(filename):
    return hashlib.sha256(Path(filename).read_bytes()).hexdigest()


def finite_double(value, label):
    need(type(value) in (float,int), label+': NON_NUMERIC_OR_BOOL')
    try:
        x=float(value)
    except (ValueError,OverflowError,TypeError) as exc:
        raise ReplayRejected(label+': UNREPRESENTABLE_DOUBLE') from exc
    need(math.isfinite(x), label+': NONFINITE')
    return x


def vector10(value, label):
    if hasattr(value,'tolist'):
        value=value.tolist()
    need(isinstance(value,(list,tuple)) and len(value)==10, label+': TEN_VALUES_REQUIRED')
    return tuple(finite_double(v,label) for v in value)


def matrix10(value):
    if hasattr(value,'tolist'):
        value=value.tolist()
    need(isinstance(value,(list,tuple)) and len(value)==10,'Jc: TEN_ROWS_REQUIRED')
    return tuple(vector10(row,'Jc') for row in value)


def frac(value):
    # Exact rational bytes from the Cherchi constructor (not rounded OBJ).
    need(type(value) is str and bool(RATIONAL.fullmatch(value)), 'INVALID_EXACT_RATIONAL_TOKEN')
    a,b = value.split('/')
    number=lambda s: int(s,2 if s.lstrip('-').startswith('0b') else 10)
    return Fraction(number(a),number(b))


def boundary_rows(vertices, faces):
    need(isinstance(vertices,(list,tuple)) and len(vertices)>=4,'BOUNDARY_VERTICES_MISSING')
    points=[]
    for row in vertices:
        need(isinstance(row,(list,tuple)) and len(row)==3,'INVALID_VERTEX_TRIPLE')
        points.append(tuple(frac(x) for x in row))
    need(isinstance(faces,(list,tuple)) and len(faces)>=4,'BOUNDARY_FACES_MISSING')
    triangles=[]
    uses=defaultdict(list); neighbors=[defaultdict(set) for _ in points]
    seen=set(); incident=[set() for _ in points]
    for j, face in enumerate(faces):
        need(isinstance(face,(list,tuple)) and len(face)==3,'INVALID_TRIANGLE')
        need(all(type(v) is int and 0<=v<len(points) for v in face), 'INDEX_OUT_OF_RANGE_OR_BOOL')
        a,b,c=face
        need(len({a,b,c})==3, 'REPEATED_TRIANGLE_VERTEX')
        key=tuple(sorted(face))
        need(key not in seen, 'DUPLICATE_TRIANGLE')
        seen.add(key);triangles.append((a,b,c))
        for v in (a,b,c):incident[v].add(j)
        for u,v in ((a,b),(b,c),(c,a)):
            uses[tuple(sorted((u,v)))].append((u,v,j))
        pa,pb,pc=points[a],points[b],points[c]
        cross=((pb[1]-pa[1])*(pc[2]-pa[2])-(pb[2]-pa[2])*(pc[1]-pa[1]),
               (pb[2]-pa[2])*(pc[0]-pa[0])-(pb[0]-pa[0])*(pc[2]-pa[2]),
               (pb[0]-pa[0])*(pc[1]-pa[1])-(pb[1]-pa[1])*(pc[0]-pa[0]))
        need(any(cross),'DEGENERATE_TRIANGLE')
    for edge, pair in uses.items():
        need(len(pair)==2,'OPEN_OR_NONMANIFOLD_EDGE')
        (a,b,f),(c,d,g)=pair
        need(a==d and b==c,'INCONSISTENT_FACE_ORIENTATION')
        for vertex in edge:
            neighbors[vertex][f].add(g);neighbors[vertex][g].add(f)
    for vertex, faces_at_vertex in enumerate(incident):
        need(bool(faces_at_vertex), 'UNREFERENCED_VERTEX')
        seen_f=set();pending=[next(iter(faces_at_vertex))]
        while pending:
            i=pending.pop()
            if i not in seen_f:
                seen_f.add(i);pending.extend(neighbors[vertex].get(i,()))
        need(seen_f==faces_at_vertex, 'PINCHED_NONMANIFOLD_VERTEX')
    # Topological closure does NOT imply geometric embedding or nested shells.
    return tuple(points),tuple(triangles)


def exact_raw_moments(points, faces, density=Fraction(1)):
    """Exact signed tetrahedral moments, independent from the Cherchi integrator.

    Assumes input has passed boundary_rows. Performs no Boolean/embedding proof.
    """
    need(type(density) is Fraction and density>0,'INVALID_EXACT_DENSITY')
    rows=[Fraction(0) for _ in range(10)]
    for ia,ib,ic in faces:
        a,b,c=points[ia],points[ib],points[ic]
        cross=(b[1]*c[2]-b[2]*c[1],b[2]*c[0]-b[0]*c[2],b[0]*c[1]-b[1]*c[0])
        v=sum(a[k]*cross[k] for k in range(3))/6
        t=tuple(a[k]+b[k]+c[k] for k in range(3))
        rows[0]+=density*v
        for k in range(3):rows[k+1]+=density*v*t[k]/4
        for j,(u,w) in enumerate(((0,0),(1,1),(2,2),(1,2),(0,2),(0,1)),4):
            rows[j]+=density*v*(a[u]*a[w]+b[u]*b[w]+c[u]*c[w]+t[u]*t[w])/20
    need(rows[0]>0,'NONPOSITIVE_ORIENTED_VOLUME')
    return tuple(rows)


def affine_target_from_physical(points, *, origin, length, target_origin, target_axes):
    """Match frozen InProcessCherchiEvaluator._target_view *exact* binary64 map."""
    need(len(origin)==3 and len(target_origin)==3 and len(target_axes)==3 and
         all(len(row)==3 for row in target_axes),'INVALID_FRAME_SHAPE')
    l=Fraction.from_float(finite_double(length,'length'))
    need(l>0,'INVALID_NORMALIZATION_LENGTH')
    origin=tuple(Fraction.from_float(finite_double(x,'origin')) for x in origin)
    shifted=tuple(Fraction.from_float(finite_double(x,'target_origin')) for x in target_origin)
    axes=tuple(tuple(Fraction.from_float(finite_double(x,'axes')) for x in row) for row in target_axes)
    out=[]
    for p in points:
        model=tuple((p[i]-origin[i])/l-shifted[i] for i in range(3))
        out.append(tuple(sum(model[i]*axes[i][j] for i in range(3)) for j in range(3)))
    return tuple(out)


def compare_floats(actual, expected, *, label, ulps=32):
    """Numeric conversion fidelity, not a universal physical or 1% threshold."""
    need(len(actual)==len(expected),label+': SHAPE_MISMATCH')
    deltas=[];limits=[]
    for value,truth in zip(actual,expected):
        v=finite_double(value,label);e=float(truth)
        need(math.isfinite(e),label+': EXACT_VALUE_OVERFLOW')
        bound=ulps*math.ulp(max(1.,abs(e)))
        delta=abs(v-e)
        need(math.isfinite(delta) and delta<=bound,label+': INDEPENDENT_MOMENT_MISMATCH')
        deltas.append(delta);limits.append(bound)
    return max(deltas,default=0.),max(limits,default=0.)


def audit_same_call_material(material, mapped, *, native_c, density,
                             original_origin, normalization_length, target_origin, target_axes,
                             expected_fixed_r):
    """Verify independent exact numeric/serialized invariants.

    Returns an UNTRUSTED P0/PACKET result. The returned flag is never proof
    of actual Cherchi execution, exact Nef regions or derivative smoothness.
    """
    need(type(material) is dict and type(mapped) is dict,'EXPECTED_SAME_CALL_OBJECTS')
    c=vector10(native_c,'native_c')
    mc=vector10(material.get('quadric_coefficients'),'material.c')
    need(struct.pack('<10d',*mc)==struct.pack('<10d',*c),'SAVED_NATIVE_COEFFICIENT_BYTES_CHANGED')
    need(abs(math.sqrt(sum(x*x for x in c))-1.)<=1e-12,'NATIVE_C_NOT_UNIT')
    for field in ('geometry_hash','topology_hash','evaluation_map_identity','boolean_backend_identity','derivative_identity'):
        need(type(material.get(field)) is str and material[field]==mapped.get(field),
             'MATERIAL_MAP_BINDING_MISMATCH:'+field)
    need(material['boolean_backend_identity'].startswith(
            'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'),
         'UNPINNED_BOOLEAN_IMPLEMENTATION')
    proof=material.get('material_proof')
    need(type(proof) is dict and proof.get('schema')=='cherchi-same-call-material-v1',
         'MISSING_SAME_CALL_PROOF_SHAPE')
    physical_tokens=proof.get('exact_vertices')
    need(type(physical_tokens) in (list,tuple),'MISSING_EXACT_PHYSICAL_BOUNDARY')
    target_tokens=material.get('variable_rational_vertices')
    need(type(target_tokens) in (list,tuple),'MISSING_EXACT_TARGET_BOUNDARY')
    faces=material.get('variable_faces')
    physical,triangles=boundary_rows(physical_tokens,faces)
    target,target_faces=boundary_rows(target_tokens,faces)
    need(triangles==target_faces,'TARGET_TO_PHYSICAL_TOPOLOGY_MISMATCH')
    calculated_hash=digest(dict(vertices=physical_tokens,faces=faces))
    need(calculated_hash==material['geometry_hash'],'EXACT_PHYSICAL_GEOMETRY_HASH_MISMATCH')
    actual_target=affine_target_from_physical(physical, origin=original_origin,
        length=normalization_length,target_origin=target_origin,target_axes=target_axes)
    need(actual_target==target,'EXACT_TARGET_FRAME_IDENTITY_MISMATCH')
    displayed=material.get('variable_vertices')
    need(type(displayed) in (list,tuple) and len(displayed)==len(target),
         'DISPLAY_VERTEX_COUNT_MISMATCH')
    for display,point in zip(displayed,target):
        need(type(display) in (list,tuple) and len(display)==3,'INVALID_DISPLAY_VERTEX')
        for d,x in zip(display,point):
            y=finite_double(d,'display')
            need(struct.pack('<d',y)==struct.pack('<d',float(x)),
                 'DISPLAY_NOT_EXACT_TARGET_ROUNDOFF')
    rho=Fraction.from_float(finite_double(density,'density'))
    result=exact_raw_moments(target,triangles,rho)
    observed=vector10(mapped.get('variable_raw_moments'),'mapped.rD')
    value_error,conversion_bound=compare_floats(observed,result,label='r_D')
    other=vector10(material.get('variable_raw_moments'),'material.rD')
    need(struct.pack('<10d',*other)==struct.pack('<10d',*observed),'SAVED_rD_MISMATCH')
    fixed=vector10(expected_fixed_r,'independently prepared r_F')
    total=vector10(mapped.get('raw_moments'),'mapped.total')
    total_error,total_bound=compare_floats(total,[a+b for a,b in zip(fixed,result)],label='r_F_PLUS_r_D')
    j=matrix10(mapped.get('moment_jacobian'))
    saved_j=matrix10(material.get('moment_jacobian'))
    need(struct.pack('<100d',*(v for row in j for v in row))==
         struct.pack('<100d',*(v for row in saved_j for v in row)),
         'MATERIAL_JC_NOT_SAME_CALL')
    need(material.get('derivative_defined') is True and mapped.get('derivative_defined') is True,
         'POINTWISE_DERIVATIVE_UNDEFINED')
    src=material.get('quadric_source_identity')
    need(type(src) is str and SHA.fullmatch(src) and src==digest({
        'vertices':material.get('quadric_source_vertices'),
        'faces':material.get('quadric_source_faces'),
        'coefficients':list(c)}), 'QUADRIC_SOURCE_IDENTITY_MISMATCH')
    return dict(schema='W0_M4_EXACT_RATIONAL_NUMERIC_REPLAY_V1',
         source_geometry_sha256=calculated_hash,source_quadric_sha256=src,
         vertex_count=len(target),face_count=len(triangles),
         r_order=list(ORDER),r_D_max_absolute_error=value_error,
         r_D_conversion_bound=conversion_bound,
         total_max_absolute_error=total_error,total_conversion_bound=total_bound,
         fixed_count_policy='r_total=r_F+r_D;J_total=J_D',
         mathematical_replay_passed=True,native_region_proved=False,
         smooth_derivative_proved=False,training_admissible=False)


def audit_live_native_once(*, evaluator, problem, c, pins):
    """One REAL in-process Cherchi invocation + independent exact region gate.

    No mocks, duck typing, supplied 'native=True' flags or customer proof
    dictionaries can bypass missing production modules. Does not release
    training because a pointwise derivative lacks a neighborhood proof.
    """
    try:
        from make_it_stand.verification.cherchi_inprocess import InProcessCherchiEvaluator
        from make_it_stand.verification.spin_problem import MeshSnapshot, SpinArtifactProblem
        from make_it_stand.verification.faster_material import _prepare_external_fixed_material
        from make_it_stand.verification.spin_common import native
    except (ImportError,RuntimeError) as exc:
        raise ReplayRejected('NATIVE_CHERCHI_RUNTIME_UNAVAILABLE') from exc
    need(type(evaluator) is InProcessCherchiEvaluator,'REQUIRES_GENUINE_INPROCESS_CHERCHI_PRODUCER')
    need(type(pins) is dict and set(pins)=={'native_sha256','bridge_sha256','adapter_sha256',
          'c_sha256','problem_input_digest','context_sha256'},
         'EXTERNALLY_FROZEN_NATIVE_SHA_PINS_REQUIRED')
    for key,filename in [('native_sha256',evaluator.native.__file__),
                         ('bridge_sha256',evaluator.bridge.__file__),
                         ('adapter_sha256',__import__('sys').modules[InProcessCherchiEvaluator.__module__].__file__)]:
        expected=pins[key]
        need(type(expected) is str and SHA.fullmatch(expected),'INVALID_PRECOMMITTED_NATIVE_SHA')
        need(sha256_file(filename)==expected,'EXECUTABLE_SOURCE_SHA_MISMATCH:'+key)
    need(type(problem) is SpinArtifactProblem,
         'INDEPENDENT_LOCKED_SPIN_ARTIFACT_PROBLEM_REQUIRED')
    need(type(problem.input_digest) is str and SHA.fullmatch(problem.input_digest) and
         pins['problem_input_digest']==problem.input_digest,
         'FROZEN_ORIGINAL_FIXED_DESIGN_PROBLEM_IDENTITY_MISMATCH')
    need(type(evaluator.context_identity) is str and SHA.fullmatch(evaluator.context_identity) and
         pins['context_sha256']==evaluator.context_identity,
         'FROZEN_NATIVE_EVALUATION_CONTEXT_IDENTITY_MISMATCH')
    request=evaluator.request
    # Independently integrate original F from problem input exactly once.
    prepared=_prepare_external_fixed_material(problem,request)
    fixed=tuple(float(x) for x in prepared.moments)
    c=vector10(c,'native_c')
    need(type(pins['c_sha256']) is str and SHA.fullmatch(pins['c_sha256']) and
         pins['c_sha256']==digest(list(c)),
         'FROZEN_NATIVE_C_COEFFICIENT_IDENTITY_MISMATCH')
    before=dict(evaluator.call_counts)
    need(before.get('source',0)==0 and before.get('boolean',0)==0 and
         not getattr(evaluator,'_materials',None),
         'PRODUCER_NOT_FRESH_ONE_REQUEST_CONTEXT')
    old_stages=dict(evaluator.stage_seconds)
    rss_before=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024
    tic=time.perf_counter()
    mapped=evaluator(c)   # The ONLY Cherchi Boolean/source invocation in this function.
    elapsed=time.perf_counter()-tic
    rss_after=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024
    material=evaluator.material(c)  # Replay immutable saved output; no Boolean rebuild.
    evaluator.validate_same_call_material(material,c,request)
    need(evaluator.call_counts.get('source',0)==before.get('source',0)+1 and
         evaluator.call_counts.get('boolean',0)==before.get('boolean',0)+1,
         'REPLAY_NOT_EXACTLY_ONE_NATIVE_SOURCE_AND_BOOLEAN_CALL')
    observation=audit_same_call_material(material,mapped,native_c=c,
         density=request.material_density,
         original_origin=evaluator.normalization_origin.tolist(),
         normalization_length=evaluator.length,
         target_origin=request.target_origin,
         target_axes=request.target_axes,
         expected_fixed_r=fixed)
    # Native *independent* exact-region test on the ACTUAL PHYSICAL rational mesh.
    proof=material['material_proof']
    retained=MeshSnapshot.from_rationals(proof['exact_vertices'],material['variable_faces'])
    design=MeshSnapshot((evaluator.design.tolist(),[list(row) for row in request.design_faces]))
    subset=native().check_exact_material_subset(retained.exact_region(),design.exact_region())
    need(type(subset) is dict and subset.get('completed') is True and
         subset.get('a_subset_b') is True,'NATIVE_EXACT_DESIGN_SUBSET_NOT_CERTIFIED')
    observed_stages={name:float(value)-float(old_stages.get(name,0.))
                     for name,value in evaluator.stage_seconds.items()}
    need(all(math.isfinite(value) and value>=0 for value in observed_stages.values()),
         'INVALID_NATIVE_STAGE_TIMINGS')
    observation.update(native_region_proved=True,
         native_wall_seconds=elapsed,
         native_stage_seconds=observed_stages,
         process_rss_hwm_before_bytes=rss_before,
         process_rss_hwm_after_bytes=rss_after,
         rss_metric='LINUX_PROCESS_HIGH_WATER_MARK_NOT_PER_CALL_PEAK',
         native_execution_observed=True,
         native_source_sha256=pins['native_sha256'],
         native_bridge_sha256=pins['bridge_sha256'],
         native_adapter_sha256=pins['adapter_sha256'],
         frozen_problem_digest=pins['problem_input_digest'],
         frozen_native_c_sha256=pins['c_sha256'],
         frozen_context_sha256=pins['context_sha256'],
         fixed_preparation_identity=prepared.identity,
         smooth_derivative_proved=False,training_admissible=False,
         status='REAL_NATIVE_SINGLE_CALL_MOMENT_VERIFIED_DERIVATIVE_NEIGHBORHOOD_PENDING')
    return observation
