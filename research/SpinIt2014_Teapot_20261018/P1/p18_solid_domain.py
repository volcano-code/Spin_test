"""Exact saved-coordinate containment and conservative cavity clearance.

All geometric decisions use Python integers or Fraction. Float projections in
reports are display-only. This certifies the frozen, explicitly repaired OBJ
representation; it is not a native Cherchi implicit-region or W0 admission.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
from math import isfinite, isqrt, lcm
from pathlib import Path
import time

from p17_boundary_certificate import ExactMesh, read_binary64_obj, signed_triangle_key


P17_COMMIT = 'c0f21c28b58fe05cf46a892934cfbcb2fccdac62'
P17_MANIFEST_SHA256 = '3eef5e245590ebee18ea46e1f0198c81d73c17ffbbb064143a6ceb95a00d5a70'
MATERIAL_NAMES = {'M': 'material/M_repaired_outer.obj',
                  'F': 'material/F_repaired_fixed_trial.obj',
                  'D': 'material/D_native_carveable_trial.obj'}
FALSE_FLAGS = {
    'native_Cherchi_implicit_region_partition_certified': False,
    'original_native_vs_microweld_set_equality_certified': False,
    'original_author_CAD_certified': False,
    'full_original_shaft_contained_in_fixed_material': False,
    'W0_physical_tip_or_FD_approved': False,
    'W2_teacher_training_allowed': False,
    'printability_or_strength_certified': False,
    'Faster_optimization_executed': False,
    'MuJoCo_real_optimized_before_after_executed': False,
}
DEPENDENCY_SNAPSHOT = {
    'observed_client_date': '2026-10-21',
    'observation_scope': 'Published W0/W2 records at the pinned commits; no claim about unpublished channels',
    'W0': {
        'head': '51cbfd33d08063404d7e0c40e4256dd0e38efa1a',
        'files_git_blob': {
            'research/ParallelLaunch/MASTER_BOARD.md': '2feff744f64807da424a0d93302e3c92294f266f',
            'research/NeuralMoments/contracts/README.md': '7c7c767c3c6c8efa48852587e3f1e115de4d839a',
            'research/NeuralMoments/contracts/schema_v1.json': '52c2cfa54567d7dc2164c4b9eb56e8385c0ee1dc',
            'research/NeuralMoments/contracts/M6_NATIVE_HANDOFF.md': 'd650228bbd69c8927f64e815fe9dc935463c55d9',
        },
        'material_specific_P17_admission_found_in_reviewed_records': False,
        'saved_surface_proof_does_not_replace_native_M6_region_predicates': True,
    },
    'W2': {
        'head': 'fef549dd57ea7b8bc72ab4ca4e5b307e4063762b',
        'files_git_blob': {
            'research/NeuralMoments/teacher/teacher_manifest.json': 'd58a26fd5eb053fd487b7db514938bec82db1586',
            'research/NeuralMoments/teacher/M19_EVIDENCE.md': '3e36f940202c862bbbaacf5bc07911297f95b068',
        },
        'latest_result_subject': 'Noodles 94 unmerged source components, 940 exact moments',
        'Teapot_native_teacher_receipt_found': False,
        'J_D_released': False,
        'training_samples': 0,
    },
    'reference_to_SI_scale_is_not_automatically_W0_optimizer_normalization': True,
}


def _fraction(value):
    if isinstance(value, bool):
        raise ValueError('boolean coordinate')
    if isinstance(value, float) and not isfinite(value):
        raise ValueError('nonfinite coordinate')
    return Fraction(value)


def _point(point):
    if len(point) != 3:
        raise ValueError('three coordinates required')
    return tuple(_fraction(x) for x in point)


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


def integer_lift(points):
    """One exact common scale, including non-dyadic rational query points."""
    points = tuple(_point(p) for p in points)
    scale = 1
    for p in points:
        for x in p:
            scale = lcm(scale, x.denominator)
    return tuple(tuple(x.numerator*(scale//x.denominator) for x in p)
                 for p in points), scale


def fraction_json(value):
    value = Fraction(value)
    return dict(numerator=str(value.numerator), denominator=str(value.denominator),
                decimal_projection=float(value))


def sqrt_bounds(value, denominator=10**9):
    value = Fraction(value)
    if value < 0 or type(denominator) is not int or denominator <= 0:
        raise ValueError('nonnegative square and positive integer grid required')
    floor = isqrt(value.numerator*denominator*denominator//value.denominator)
    low = Fraction(floor, denominator)
    high = low if low*low == value else Fraction(floor+1, denominator)
    assert low*low <= value <= high*high
    return low, high


def classify_point(mesh, point, *, directions=None):
    """Parity of an exact nondegenerate ray; ambiguous rays are never counted.

    The caller must separately prove an embedded closed surface if interpreting
    INSIDE as a solid. Boundary tests are exact, and every rejected direction is
    discarded in full. A finite exhausted direction set raises an error.
    """
    point = _point(point)
    lifted, scale = integer_lift((*mesh.vertices, point))
    query = lifted[-1]
    vertices = lifted[:-1]
    triangles = tuple(tuple(vertices[i] for i in f) for f in mesh.faces)
    if not triangles:
        raise ValueError('empty mesh')
    planes = []
    for tri in triangles:
        a,b,c = tri
        e1,e2 = sub(b,a),sub(c,a)
        normal = cross(e1,e2)
        if not any(normal):
            raise ValueError('degenerate triangle')
        q = sub(query,a)
        plane = dot(q,normal)
        if plane == 0:
            signs = [dot(cross(sub(y,x),sub(query,x)),normal)
                     for x,y in ((a,b),(b,c),(c,a))]
            if min(signs) >= 0:
                return dict(classification='BOUNDARY', method='EXACT_INTEGER_RAY',
                            point_exact=[str(x) for x in point],
                            rejected_degenerate_rays=0, crossings=None, direction=None)
        planes.append((a,e1,e2,q,plane))
    if directions is None:
        directions = [(1,k,k*k+1) for k in range(1,65)]
    rejected = 0
    for direction in directions:
        if len(direction)!=3 or any(type(x) is not int for x in direction) or not any(direction):
            raise ValueError('ray direction must be a nonzero integer triple')
        crossings = 0
        degenerate = False
        for a,e1,e2,q,plane in planes:
            h = cross(direction,e2)
            det = dot(e1,h)
            if det == 0:
                if plane == 0:
                    degenerate = True
                    break
                continue
            u = dot(q,h)
            r = cross(q,e1)
            v = dot(direction,r)
            t = dot(e2,r)
            if det < 0:
                det,u,v,t = -det,-u,-v,-t
            if t<=0 or u<0 or v<0 or u+v>det:
                continue
            if u==0 or v==0 or u+v==det:
                degenerate = True
                break
            crossings += 1
        if degenerate:
            rejected += 1
            continue
        return dict(classification='INSIDE' if crossings%2 else 'OUTSIDE',
                    method='EXACT_INTEGER_RAY', point_exact=[str(x) for x in point],
                    crossings=crossings, direction=list(direction),
                    rejected_degenerate_rays=rejected,
                    surface_validity_must_be_certified_separately=True)
    raise ValueError('NO_NONDEGENERATE_EXACT_RAY_DIRECTION')


def _segment_distance2_int(point,a,b):
    edge = sub(b,a)
    q = sub(point,a)
    denom = dot(edge,edge)
    if not denom:
        return Fraction(dot(q,q))
    numerator = dot(q,edge)
    if numerator<=0:
        return Fraction(dot(q,q))
    if numerator>=denom:
        end = sub(point,b)
        return Fraction(dot(end,end))
    return Fraction(dot(q,q)*denom-numerator*numerator,denom)


def _triangle_distance2_int(point,triangle):
    a,b,c = triangle
    normal = cross(sub(b,a),sub(c,a))
    nn = dot(normal,normal)
    if nn == 0:
        raise ValueError('degenerate triangle')
    signed = dot(sub(point,a),normal)
    projection_num = tuple(x*nn-signed*n for x,n in zip(point,normal))
    signs = [dot(cross(sub(y,x),tuple(q-z*nn for q,z in zip(projection_num,x))),normal)
             for x,y in ((a,b),(b,c),(c,a))]
    if min(signs)>=0:
        return Fraction(signed*signed,nn)
    return min(_segment_distance2_int(point,x,y) for x,y in ((a,b),(b,c),(c,a)))


def point_triangle_distance_squared(point,triangle):
    if len(triangle)!=3:
        raise ValueError('three triangle points required')
    lifted, scale = integer_lift((*triangle,point))
    return _triangle_distance2_int(lifted[-1],lifted[:3])/(scale*scale)


def radial_ball_clearance(outer,design,center,*,sqrt_grid=10**9):
    """Distance bounds alone; containment also needs valid solids and center inside."""
    center = _point(center)
    points, scale = integer_lift((*outer.vertices,*design.vertices,center))
    q = points[-1]
    ov = points[:len(outer.vertices)]
    dv = points[len(outer.vertices):-1]
    if not outer.faces or not design.faces:
        raise ValueError('empty boundary')
    distances = [_triangle_distance2_int(q,tuple(ov[i] for i in f))/(scale*scale)
                 for f in outer.faces]
    radii = [Fraction(dot(sub(v,q),sub(v,q)),scale*scale) for v in dv]
    minimum,maximum = min(distances),max(radii)
    lo,hi = sqrt_bounds(minimum,sqrt_grid)
    rlo,rhi = sqrt_bounds(maximum,sqrt_grid)
    gap = lo-rhi
    return dict(method='EXACT_POINT_TRIANGLE_DISTANCE_AND_CONVEX_ENCLOSING_BALL',
        center_exact=[str(x) for x in center],
        outer_faces_tested=len(outer.faces),design_vertices_tested=len(design.vertices),
        nearest_outer_face=distances.index(minimum),farthest_design_vertex=radii.index(maximum),
        minimum_center_to_outer_distance_squared=fraction_json(minimum),
        maximum_design_vertex_radius_squared=fraction_json(maximum),
        outer_distance_lower_bound=fraction_json(lo),
        outer_distance_upper_bound=fraction_json(hi),
        design_ball_radius_upper_bound=fraction_json(rhi),
        cavity_to_outer_clearance_lower_bound_reference=fraction_json(gap),
        sqrt_grid_denominator=sqrt_grid,positive_gap_proved=gap>0,
        entire_solid_containment_requires_closed_embedded_surfaces_and_center_inside=True,
        whole_object_wall_thickness_or_printability_certified=False)


def face_components(mesh):
    by_vertex = defaultdict(list)
    for i,face in enumerate(mesh.faces):
        for v in face:
            by_vertex[v].append(i)
    remaining = set(range(len(mesh.faces)))
    components = []
    while remaining:
        pending = [min(remaining)]
        current = set()
        while pending:
            i = pending.pop()
            if i in current:
                continue
            current.add(i)
            remaining.discard(i)
            for v in mesh.faces[i]:
                pending.extend(j for j in by_vertex[v] if j not in current)
        components.append(tuple(sorted(current)))
    return components


def component_chain(mesh,indices):
    chain = Counter()
    for i in indices:
        key,sign = signed_triangle_key(tuple(mesh.vertices[j] for j in mesh.faces[i]))
        chain[key] += sign
    return {key:value for key,value in chain.items() if value}


def fixed_component_correspondence(outer,fixed,design):
    expected = [component_chain(outer,range(len(outer.faces))),
                {key:-value for key,value in component_chain(design,range(len(design.faces))).items()}]
    pieces = face_components(fixed)
    actual = [component_chain(fixed,indices) for indices in pieces]
    # Require literal single facets, not a chain with hidden cancelling duplicates.
    no_hidden = all(len(chain)==len(indices) and all(abs(v)==1 for v in chain.values())
                    for chain,indices in zip(actual,pieces))
    matched = []
    for label,chain in zip(('M_outward','D_reversed'),expected):
        indices = [i for i,candidate in enumerate(actual) if candidate==chain]
        matched.append(dict(target=label,component=indices[0] if len(indices)==1 else None,
                            unique_match=len(indices)==1))
    passed = (len(pieces)==2 and no_hidden and all(row['unique_match'] for row in matched)
              and matched[0]['component']!=matched[1]['component'])
    return dict(exact_outer_and_reversed_cavity_components=passed,
                fixed_boundary_components=len(pieces),no_hidden_duplicate_cancellation=no_hidden,
                component_face_counts=[len(x) for x in pieces],matches=matched,
                alone_is_not_an_embedded_solid_certificate=True)


def exact_signed_volume(mesh):
    lifted,scale = integer_lift(mesh.vertices)
    return Fraction(sum(dot(lifted[a],cross(lifted[b],lifted[c]))
                        for a,b,c in mesh.faces),6*scale**3)


def cross_surface_audit(first,second,*,max_witnesses=8):
    from p18_exact_surface import aabb_candidate_pairs, exact_triangle_intersection
    points,scale = integer_lift((*first.vertices,*second.vertices))
    av,bv = points[:len(first.vertices)],points[len(first.vertices):]
    a = tuple(tuple(av[i] for i in f) for f in first.faces)
    b = tuple(tuple(bv[i] for i in f) for f in second.faces)
    candidates = contacts = 0
    witnesses = []
    for i,j in aabb_candidate_pairs(first.triangles,second.triangles):
        candidates += 1
        intersection = exact_triangle_intersection(a[i],b[j])
        if intersection:
            contacts += 1
            if len(witnesses)<max_witnesses:
                witnesses.append(dict(face_indices_zero_based=[i,j],
                    points_exact=[[str(Fraction(x,scale)) for x in p] for p in intersection]))
    return dict(method='EXACT_ALL_CROSS_SURFACE_TRIANGLE_PAIRS',
        total_cross_face_pairs=len(first.faces)*len(second.faces),
        aabb_candidate_pairs=candidates,exact_pairs_checked=candidates,
        all_candidate_pairs_checked=True,cross_index_adjacency_exclusions=0,
        contact_pair_count=contacts,contact_witnesses=witnesses,
        exact_surface_disjointness_certified=contacts==0)


def _identity(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _without_timings(value):
    if isinstance(value,dict):
        return {key:_without_timings(item) for key,item in value.items()
                if key not in ('elapsed_seconds','audit_elapsed_seconds')}
    if isinstance(value,list):
        return [_without_timings(item) for item in value]
    return value


def check_report_replay(saved,replayed):
    """The complete proof must replay; only measured execution times may differ."""
    from p17_material_candidate import typed_exact_equal
    if not typed_exact_equal(_without_timings(saved),_without_timings(replayed)):
        raise ValueError('P18_SAVED_PROOF_DIFFERS_FROM_EXACT_REPLAY')
    return dict(status='P18_EXACT_PROOF_REPLAY_MATCH',
                scientific_admission=saved['optimization_admitted'],
                saved_solid_partition=saved['saved_repaired_solid_partition_certified'],
                protected_shaft_exclusion=saved['shaft_excluded_from_design_domain'],
                timing_fields_only_ignored=True)


def audit_packet(packet):
    """Recompute all proof facts for the one immutable P17 candidate.

    A valid partition and an invalid protected domain can coexist. A report of
    that negative outcome is a successful audit, never optimization admission.
    """
    from p17_material_candidate import verify_packet, validate_packet_files
    from p18_exact_surface import audit_exact_surface
    from p18_shaft_domain import audit_shaft_exclusion
    started = time.perf_counter()
    packet = Path(packet)
    if _identity(packet/'manifest.json')!=P17_MANIFEST_SHA256:
        raise ValueError('P18_REQUIRES_THE_IMMUTABLE_P17_MANIFEST')
    manifest = validate_packet_files(packet)
    p17 = verify_packet(packet)
    paths = {key:packet/value for key,value in MATERIAL_NAMES.items()}
    meshes = {key:read_binary64_obj(path) for key,path in paths.items()}
    surfaces = {key:audit_exact_surface(path,manifest['files_sha256'][MATERIAL_NAMES[key]])
                for key,path in paths.items()}
    volumes = {key:exact_signed_volume(mesh) for key,mesh in meshes.items()}
    correspondence = fixed_component_correspondence(meshes['M'],meshes['F'],meshes['D'])
    cross_report = cross_surface_audit(meshes['M'],meshes['D'])
    center = (Fraction(0),Fraction(0),Fraction.from_float(.67))
    classification = {key:classify_point(mesh,center) for key,mesh in meshes.items()}
    design_boundary_point = classify_point(meshes['M'],meshes['D'].vertices[0])
    clearance = radial_ball_clearance(meshes['M'],meshes['D'],center)
    gap = clearance['cavity_to_outer_clearance_lower_bound_reference']
    gap = Fraction(int(gap['numerator']),int(gap['denominator']))
    scale = Fraction.from_float(json.loads((packet/'physical-case-proposal.json').read_text())['scale_m_per_unit'])
    clearance['cavity_to_outer_clearance_lower_bound_m'] = fraction_json(gap*scale)
    valid_surfaces = all(s['exact_embedded_closed_oriented_2manifold'] is True for s in surfaces.values())
    connected = all(surfaces[key]['topology']['surface_components']==1 for key in ('M','D'))
    outward = volumes['M']>0 and volumes['D']>0
    contained = (valid_surfaces and connected and outward and
                 cross_report['exact_surface_disjointness_certified'] and
                 classification['M']['classification']=='INSIDE' and
                 design_boundary_point['classification']=='INSIDE' and clearance['positive_gap_proved'])
    partition = (contained and correspondence['exact_outer_and_reversed_cavity_components']
                 and volumes['M']==volumes['F']+volumes['D'])
    shaft_path = packet/'source/shaft-reference.obj'
    shaft_hash = manifest['files_sha256']['source/shaft-reference.obj']
    shaft = audit_shaft_exclusion(paths['D'],shaft_path,
        expected_sha256={'design':meshes['D'].sha256,'shaft':shaft_hash})
    shaft_surface = audit_exact_surface(shaft_path,shaft_hash)
    shaft_mesh = read_binary64_obj(shaft_path)
    shaft_center = classify_point(shaft_mesh,center)
    # The shaft report's exact clipping facts are interpreted below, together
    # with this independently established embedded D and outside-axis anchor.
    prism = shaft['verified_shaft_prism']
    center_in_slab = Fraction(prism['z_lo_exact'])<center[2]<Fraction(prism['z_hi_exact'])
    section_valid = (prism['exact_rectangle_wall_coverage'] and
        prism['exhaustive_shaft_faces_in_slab_verified'] and
        shaft_surface['exact_embedded_closed_oriented_2manifold'] and
        shaft_surface['topology']['surface_components']==1 and
        exact_signed_volume(shaft_mesh)>0 and shaft_center['classification']=='INSIDE' and center_in_slab)
    strict_intrusion = shaft['strict_intruding_face_count']>0
    overlap = (partition and section_valid and strict_intrusion)
    shaft_excluded = (partition and section_valid and not strict_intrusion and
                      classification['D']['classification']=='OUTSIDE')
    core = shaft['conservative_axis_core']
    core_anchor = classify_point(meshes['D'],[Fraction(x) for x in core['outside_anchor_reference_exact']])
    core_excluded = (partition and section_valid and core['positive_radius_available'] and
        core['squared_radius_strictly_below_D_surface'] and
        core['squared_radius_strictly_below_shaft_walls'] and
        core_anchor['classification']=='OUTSIDE')
    status = ('SAVED_SOLID_PARTITION_CERTIFIED_PROTECTED_SHAFT_REJECTED' if overlap else
              'SAVED_SOLID_PARTITION_CERTIFIED_EXTERNAL_ADMISSION_PENDING' if partition else
              'SAVED_SOLID_PARTITION_NOT_CERTIFIED')
    source_files = ['p18_solid_domain.py','p18_exact_surface.py','p18_shaft_domain.py']
    source_hashes = {name:_identity(Path(__file__).with_name(name)) for name in source_files}
    result = dict(schema='W4P18ExactSavedSolidAndProtectedDomainV1',status=status,
        source_P17_commit=P17_COMMIT,source_P17_manifest_sha256=P17_MANIFEST_SHA256,
        p18_proof_source_sha256=source_hashes,
        material_sha256={key:mesh.sha256 for key,mesh in meshes.items()},
        P17_provenance_and_physical_replay=p17,
        geometry_modified=False,new_native_Boolean_calls=0,
        exact_surface_audits=surfaces,
        exact_signed_volumes={key:fraction_json(value) for key,value in volumes.items()},
        fixed_component_correspondence=correspondence,
        outer_design_cross_surface_audit=cross_report,
        center_point_classifications=classification,
        design_boundary_point_in_outer=design_boundary_point,
        cavity_ball_and_clearance_certificate=clearance,
        shaft_domain_audit=shaft,
        exact_shaft_surface_audit=shaft_surface,
        shaft_center_classification=shaft_center,
        shaft_section_center_in_verified_slab=center_in_slab,
        conservative_core_anchor_classification=core_anchor,
        conservative_axis_core_excluded_from_design_domain=core_excluded,
        conservative_axis_core_radius_m=fraction_json(Fraction(core['radius_reference_exact'])*scale),
        exact_saved_surface_boundaries_embedded=valid_surfaces,
        saved_repaired_solid_partition_certified=partition,
        design_strictly_inside_saved_outer=contained,
        fixed_and_design_union_equals_saved_outer=partition,
        fixed_and_design_have_no_positive_volume_overlap=partition,
        shaft_excluded_from_design_domain=shaft_excluded,
        positive_volume_design_shaft_overlap_proved=overlap,
        full_original_shaft_preservation_refuted_by_design_overlap=overlap,
        optimization_admitted=False,training_admitted=False,
        external_W0_material_specific_receipt=None,external_W2_Teapot_teacher_receipt=None,
        dependency_snapshot=DEPENDENCY_SNAPSHOT,
        scientific_flags=dict(FALSE_FLAGS),
        proof_scope='Regular closed solids represented by the saved binary64 repaired OBJ coordinates only',
        audit_elapsed_seconds=time.perf_counter()-started)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('audit','verify'))
    parser.add_argument('--packet',required=True)
    parser.add_argument('--report',required=True)
    args = parser.parse_args()
    target = Path(args.report)
    if args.command=='audit' and target.exists():
        raise FileExistsError('preserve previous evidence; use a new report path')
    report = audit_packet(args.packet)
    if args.command=='verify':
        result = check_report_replay(json.loads(target.read_text()),report)
        print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))
        return 0
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x',encoding='utf-8') as stream:
        json.dump(report,stream,indent=2,sort_keys=True,allow_nan=False)
        stream.write('\n')
    print(json.dumps({key:report[key] for key in ('status','saved_repaired_solid_partition_certified',
        'shaft_excluded_from_design_domain','positive_volume_design_shaft_overlap_proved',
        'optimization_admitted')},indent=2))
    return 0 if report['optimization_admitted'] else 2


if __name__=='__main__':
    raise SystemExit(main())

