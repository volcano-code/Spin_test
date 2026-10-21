"""Explicit, bounded collapse of disjoint native-serialization edge pairs.

This creates a distinct saved geometry.  It is neither a Boolean fallback nor
an assertion that a native implicit region and the repaired solid are equal.
No area epsilon is used: the only removed faces are the two combinatorial
faces collapsed by each authorized original edge.  Exact nonzero small faces
are retained for the subsequent P18 surface audit.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import math
from pathlib import Path
import re

from p17_boundary_certificate import read_binary64_obj


DISTANCE_LIMIT = Fraction(1, 10 ** 15)
MAX_PAIRS = 32
MAX_DELETED_FACES = 64
TEN_NAMES = ('M', 'LX', 'LY', 'LZ', 'QXX', 'QYY', 'QZZ', 'QYZ', 'QXZ', 'QXY')


@dataclass(frozen=True)
class NativeMesh:
    sha256: str
    vertices: tuple
    float_vertices: tuple
    faces: tuple
    zero_area_faces: tuple


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _zero_area(vertices, face):
    a, b, c = (vertices[index] for index in face)
    return not any(_cross(_sub(b, a), _sub(c, a)))


def _parse_native_obj(data):
    vertices, floats, faces = [], [], []
    for line_number, raw in enumerate(data.decode('utf-8').splitlines(), 1):
        words = raw.split('#', 1)[0].split()
        if not words:
            continue
        if words[0] == 'v':
            if len(words) != 4:
                raise ValueError('P19_NATIVE_OBJ_THREE_COORDINATES_REQUIRED')
            point = tuple(float(value) for value in words[1:])
            if not all(math.isfinite(value) for value in point):
                raise ValueError('P19_NATIVE_OBJ_NONFINITE_COORDINATE')
            floats.append(point)
            vertices.append(tuple(Fraction.from_float(value) for value in point))
        elif words[0] == 'f':
            if len(words) != 4:
                raise ValueError('P19_NATIVE_OBJ_TRIANGLES_REQUIRED')
            face = []
            for word in words[1:]:
                index = int(word.split('/', 1)[0])
                if index == 0:
                    raise ValueError('P19_NATIVE_OBJ_ZERO_INDEX')
                index = index - 1 if index > 0 else len(vertices) + index
                if not 0 <= index < len(vertices):
                    raise ValueError('P19_NATIVE_OBJ_INDEX_OUT_OF_RANGE')
                face.append(index)
            if len(set(face)) != 3:
                raise ValueError('P19_NATIVE_OBJ_REPEATED_FACE_INDEX')
            faces.append(tuple(face))
        elif words[0] not in ('o', 'g', 's', 'usemtl', 'mtllib', 'vn', 'vt'):
            raise ValueError(f'P19_NATIVE_OBJ_UNSUPPORTED_RECORD_AT_{line_number}')
    if not vertices or not faces:
        raise ValueError('P19_NATIVE_OBJ_EMPTY')
    zero = tuple(i for i, face in enumerate(faces) if _zero_area(vertices, face))
    return NativeMesh(hashlib.sha256(data).hexdigest(), tuple(vertices), tuple(floats),
                      tuple(faces), zero)


def read_native_obj_allow_zero_area(path):
    """Read authentic binary64 triangles without silently deleting degeneracies."""
    return _parse_native_obj(Path(path).read_bytes())


def exact_signed_ten_moments(vertices, faces):
    """Formal signed tetrahedral integrals, also defined for a degenerate chain."""
    vertices = tuple(tuple(Fraction(value) for value in point) for point in vertices)
    scale = 1
    for point in vertices:
        for value in point:
            scale = math.lcm(scale, value.denominator)
    integer = tuple(tuple(value.numerator * (scale // value.denominator) for value in point)
                    for point in vertices)
    totals = [0] * 10
    quadratic_pairs = ((0, 0), (1, 1), (2, 2), (1, 2), (0, 2), (0, 1))
    for face in faces:
        a, b, c = (integer[index] for index in face)
        bc = _cross(b, c)
        determinant = sum(x * y for x, y in zip(a, bc))
        sums = tuple(a[k] + b[k] + c[k] for k in range(3))
        totals[0] += determinant
        for k in range(3):
            totals[1 + k] += determinant * sums[k]
        for k, (i, j) in enumerate(quadratic_pairs):
            totals[4 + k] += determinant * (sums[i] * sums[j] +
                a[i] * a[j] + b[i] * b[j] + c[i] * c[j])
    denominators = (6 * scale ** 3,) + (24 * scale ** 4,) * 3 + (120 * scale ** 5,) * 6
    return tuple(Fraction(value, denominator) for value, denominator in zip(totals, denominators))


def _topology(vertices, faces):
    edges, directions, links, used = defaultdict(list), Counter(), defaultdict(list), set()
    for face_index, face in enumerate(faces):
        used.update(face)
        for k, a in enumerate(face):
            b, c = face[(k + 1) % 3], face[(k + 2) % 3]
            edge = tuple(sorted((a, b)))
            edges[edge].append(face_index)
            directions[edge] += 1 if a < b else -1
            links[a].append((b, c))
    bad_links = []
    for vertex, link_edges in links.items():
        graph = defaultdict(list)
        for a, b in link_edges:
            graph[a].append(b)
            graph[b].append(a)
        unseen = set(graph)
        stack = [unseen.pop()]
        while stack:
            for other in graph[stack.pop()]:
                if other in unseen:
                    unseen.remove(other)
                    stack.append(other)
        if (unseen or len(graph) < 3 or any(len(values) != 2 for values in graph.values()) or
                any(count != 1 for count in Counter(tuple(sorted(edge)) for edge in link_edges).values())):
            bad_links.append(vertex)
    duplicates = len(faces) - len({tuple(sorted(face)) for face in faces})
    record = dict(edge_incidence_errors=sum(len(items) != 2 for items in edges.values()),
                  edge_orientation_errors=sum(value != 0 for value in directions.values()),
                  vertex_link_non_circle_count=len(bad_links), duplicate_face_count=duplicates,
                  unused_vertex_count=len(vertices) - len(used), edges=len(edges))
    record['indexed_closed_consistently_oriented_two_manifold'] = not any(
        record[name] for name in ('edge_incidence_errors', 'edge_orientation_errors',
            'vertex_link_non_circle_count', 'duplicate_face_count', 'unused_vertex_count'))
    return record, edges


def _near_pairs(vertices, limit):
    """Conservative exact sorted-window broad phase; no floating search radius."""
    order = sorted(range(len(vertices)), key=lambda index: (vertices[index], index))
    left, pairs, x_candidates, box_candidates = 0, [], 0, 0
    limit2 = limit * limit
    for offset, index in enumerate(order):
        x, y, z = vertices[index]
        while left < offset and x - vertices[order[left]][0] > limit:
            left += 1
        for prior in order[left:offset]:
            x_candidates += 1
            point = vertices[prior]
            if abs(y - point[1]) > limit or abs(z - point[2]) > limit:
                continue
            box_candidates += 1
            distance2 = sum((a - b) ** 2 for a, b in zip(vertices[index], point))
            if distance2 <= limit2:
                a, b = sorted((prior, index))
                pairs.append((a, b, distance2))
    return tuple(sorted(pairs)), dict(
        method='EXACT_RATIONAL_X_SORT_AND_CLOSED_AXIS_WINDOW',
        x_window_candidate_pairs=x_candidates, exact_box_candidate_pairs=box_candidates,
        exact_euclidean_pairs_within_budget=len(pairs),
        all_close_pairs_enumerated_without_float_radius=True)


def _fraction_record(value):
    return dict(numerator=str(value.numerator), denominator=str(value.denominator),
                decimal_projection=float(value))


def _moment_record(values):
    return {name: _fraction_record(value) for name, value in zip(TEN_NAMES, values)}


def repair_native_serialization(input_path, output_path, expected_sha256, *,
                                distance_limit=DISTANCE_LIMIT, max_pairs=MAX_PAIRS,
                                max_deleted_faces=MAX_DELETED_FACES):
    """Create a new bounded repair or raise before publishing any output file.

    The maximum budgets are fixed: 1e-15 reference-unit displacement, 32
    disjoint original edge pairs, and 64 deleted faces.  Smaller budgets are
    allowed; larger ones are rejected.  No new coordinate is synthesized.
    """
    source, target = Path(input_path), Path(output_path)
    if source.resolve() == target.resolve() or target.exists() or target.is_symlink():
        raise FileExistsError('P19_REPAIR_OUTPUT_MUST_BE_A_NEW_DISTINCT_FILE')
    if type(expected_sha256) is not str or re.fullmatch('[0-9a-f]{64}', expected_sha256) is None:
        raise ValueError('P19_NATIVE_INPUT_SHA256_REQUIRED')
    if isinstance(distance_limit, bool):
        raise ValueError('P19_REPAIR_DISTANCE_BUDGET_INVALID')
    distance_limit = Fraction(distance_limit)
    if not 0 < distance_limit <= DISTANCE_LIMIT:
        raise ValueError('P19_REPAIR_DISTANCE_BUDGET_INVALID')
    if type(max_pairs) is not int or not 1 <= max_pairs <= MAX_PAIRS:
        raise ValueError('P19_REPAIR_PAIR_BUDGET_INVALID')
    if type(max_deleted_faces) is not int or not 1 <= max_deleted_faces <= MAX_DELETED_FACES:
        raise ValueError('P19_REPAIR_FACE_BUDGET_INVALID')
    native = read_native_obj_allow_zero_area(source)
    if native.sha256 != expected_sha256:
        raise ValueError('P19_NATIVE_INPUT_SHA256_MISMATCH')
    pairs, broadphase = _near_pairs(native.vertices, distance_limit)
    if not pairs:
        raise ValueError('P19_NO_AUTHORIZED_COLLAPSE_PAIRS')
    if len(pairs) > max_pairs:
        raise ValueError('P19_REPAIR_PAIR_BUDGET_EXCEEDED')
    if 2 * len(pairs) > max_deleted_faces:
        raise ValueError('P19_REPAIR_FACE_BUDGET_EXCEEDED')
    multiplicities = Counter(index for a, b, _ in pairs for index in (a, b))
    if any(count != 1 for count in multiplicities.values()):
        raise ValueError('P19_NEAR_VERTEX_CHAINS_NOT_ALLOWED')
    input_topology, edges = _topology(native.vertices, native.faces)
    mapping = list(range(len(native.vertices)))
    records = []
    for a, b, distance2 in pairs:
        edge_faces = edges.get((a, b))
        if edge_faces is None:
            raise ValueError('P19_CLOSE_PAIR_IS_NOT_AN_ORIGINAL_EDGE')
        if len(edge_faces) != 2:
            raise ValueError('P19_COLLAPSE_EDGE_NOT_EXACTLY_TWO_FACES')
        keep, remove = sorted((a, b), key=lambda index: (native.vertices[index], index))
        mapping[remove] = keep
        records.append(dict(original_vertex_indices=[a, b], kept_original_vertex_index=keep,
            removed_original_vertex_index=remove,
            original_points_exact=[[str(value) for value in native.vertices[index]] for index in (a, b)],
            displacement_squared_exact=str(distance2),
            original_incident_face_indices=list(edge_faces)))
    if input_topology['indexed_closed_consistently_oriented_two_manifold'] is not True:
        raise ValueError('P19_NATIVE_INDEXED_TOPOLOGY_OUTSIDE_REPAIR_SCOPE')
    retained, deleted = [], []
    for index, face in enumerate(native.faces):
        mapped = tuple(mapping[vertex] for vertex in face)
        if len(set(mapped)) < 3:
            deleted.append(index)
        else:
            if _zero_area(native.vertices, mapped):
                raise ValueError('P19_RETAINED_EXACT_ZERO_AREA_FACE_NOT_AUTHORIZED_FOR_DELETION')
            retained.append((index, mapped))
    expected_deleted = sorted(index for record in records for index in record['original_incident_face_indices'])
    if deleted != expected_deleted or len(deleted) != 2 * len(pairs):
        raise ValueError('P19_REMOVED_FACES_NOT_EXACTLY_TWO_PER_COLLAPSED_EDGE')
    representatives = sorted(set(mapping))
    used = {index for _, face in retained for index in face}
    if used != set(representatives):
        raise ValueError('P19_REPAIR_WOULD_ERASE_AN_UNAUTHORIZED_VERTEX_OR_COMPONENT')
    remap = {original: index for index, original in enumerate(representatives)}
    vertices = tuple(native.vertices[index] for index in representatives)
    floats = tuple(native.float_vertices[index] for index in representatives)
    faces = tuple(tuple(remap[index] for index in face) for _, face in retained)
    output_topology, _ = _topology(vertices, faces)
    if output_topology['indexed_closed_consistently_oriented_two_manifold'] is not True:
        raise ValueError('P19_REPAIRED_INDEXED_TOPOLOGY_INVALID')
    movement2 = tuple(sum((a - b) ** 2 for a, b in zip(native.vertices[index], native.vertices[mapping[index]]))
                      for index in range(len(native.vertices)))
    if any(value > distance_limit ** 2 for value in movement2):
        raise ValueError('P19_EXACT_DISPLACEMENT_BUDGET_EXCEEDED')
    original_points = set(native.vertices)
    if any(point not in original_points for point in vertices):
        raise AssertionError('P19_NEW_COORDINATE_NOT_AUTHORIZED')
    before = exact_signed_ten_moments(native.vertices, native.faces)
    after = exact_signed_ten_moments(vertices, faces)
    delta = tuple(b - a for a, b in zip(before, after))
    text = '# P19 explicit bounded native-serialization repair; no native set-equality claim\n'
    text += ''.join('v ' + ' '.join(format(value, '.17g') for value in point) + '\n' for point in floats)
    text += ''.join('f ' + ' '.join(str(index + 1) for index in face) + '\n' for face in faces)
    data = text.encode('ascii')
    predicted = _parse_native_obj(data)
    if (predicted.vertices != vertices or predicted.faces != faces or predicted.zero_area_faces):
        raise AssertionError('P19_REPAIR_SERIALIZATION_NOT_EXACTLY_REPLAYABLE')
    if hashlib.sha256(source.read_bytes()).hexdigest() != native.sha256:
        raise ValueError('P19_NATIVE_SOURCE_CHANGED_DURING_REPAIR')
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(data)
    saved = read_binary64_obj(target)
    if (saved.sha256 != predicted.sha256 or saved.vertices != vertices or saved.faces != faces or
            exact_signed_ten_moments(saved.vertices, saved.faces) != after):
        raise AssertionError('P19_SAVED_REPAIR_REREAD_MISMATCH')
    return dict(
        schema='W4P19ExplicitBoundedNativeSerializationRepairV1',
        status='BOUNDED_SAVED_REPAIR_CREATED_FULL_GEOMETRIC_CERTIFICATION_REQUIRED',
        input_sha256=native.sha256, output_sha256=saved.sha256,
        input_vertices=len(native.vertices), input_faces=len(native.faces),
        output_vertices=len(saved.vertices), output_faces=len(saved.faces),
        input_exact_zero_area_face_indices=list(native.zero_area_faces),
        output_exact_zero_area_face_count=0,
        distance_limit_reference_exact=str(distance_limit),
        distance_limit_squared_exact=str(distance_limit ** 2),
        configured_max_pairs=max_pairs, configured_max_deleted_faces=max_deleted_faces,
        close_pair_count=len(pairs), collapse_pairs=records,
        deleted_face_count=len(deleted), deleted_original_face_indices=deleted,
        kept_original_vertex_indices=representatives,
        retained_original_face_indices=[index for index, _ in retained],
        all_pairs_are_disjoint_existing_edges=True,
        each_pair_removes_exactly_two_original_incident_faces=True,
        kept_point_rule='LEXICOGRAPHIC_MINIMUM_EXACT_ORIGINAL_COORDINATE_THEN_INDEX',
        all_retained_coordinates_are_exact_original_points=True,
        every_original_vertex_displacement_exactly_checked=True,
        maximum_displacement_squared_exact=str(max(movement2)),
        maximum_displacement_decimal_projection=math.sqrt(float(max(movement2))),
        exact_displacement_within_budget=True,
        broadphase=broadphase, input_indexed_topology=input_topology,
        output_indexed_topology=output_topology,
        area_tolerance_used=None, arbitrary_small_area_face_deletions=0,
        exact_nonzero_small_faces_retained=True,
        signed_tetrahedral_ten_moments=dict(order=list(TEN_NAMES),
            before=_moment_record(before), after=_moment_record(after),
            delta_after_minus_before=_moment_record(delta),
            all_ten_moments_exactly_unchanged=not any(delta),
            before_is_formal_signed_chain_not_an_embedded_solid_mass_certificate=True),
        input_bytes_preserved=True, output_is_distinct_file=True,
        geometry_modified=True, new_native_Boolean_calls=0,
        native_provenance_authenticated_by_repair=False,
        native_implicit_vs_repaired_solid_set_equality_certified=False,
        saved_native_vs_repaired_solid_set_equality_certified=False,
        exact_embedded_solid_certified=False,
        independent_P18_exact_surface_audit_still_required=True,
        full_original_shaft_contained_in_fixed_material=False,
        W0_physical_tip_or_FD_approved=False, W2_teacher_training_allowed=False,
        Faster_optimization_executed=False, MuJoCo_real_optimized_before_after_executed=False)
