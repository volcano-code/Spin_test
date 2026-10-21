#!/usr/bin/env python3
"""Exact shaft/D exclusion at saved binary64 coordinates, without tolerance.

The shaft prism is verified against its actual wall triangles and both rings.
Every D triangle is clipped against every convex-prism half-plane. A strict
surface intrusion proves positive-volume overlap only when D is independently
certified as an embedded boundary of a bounded regular solid. No such external
certificate, W0 approval, or native implicit-point identity is inferred here.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import json
import math
from pathlib import Path

from p17_boundary_certificate import read_binary64_obj


def cross2(a, b):
    return a[0] * b[1] - a[1] * b[0]


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def convex_hull(points):
    points = sorted(set(points))
    if len(points) < 3:
        raise ValueError('SHAFT_RING_TOO_FEW_POINTS')
    lower, upper = [], []
    for stack, seq in ((lower, points), (upper, reversed(points))):
        for point in seq:
            while len(stack) >= 2 and cross2(sub(stack[-1], stack[-2]), sub(point, stack[-1])) <= 0:
                stack.pop()
            stack.append(point)
    hull = tuple(lower[:-1] + upper[:-1])
    if len(hull) != len(points):
        raise ValueError('SHAFT_RING_NOT_STRICTLY_CONVEX')
    return hull


def halfplanes(polygon):
    """CCW edge a->b: A*x+B*y+C >= 0, strict inequality inside."""
    result = []
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        dx, dy = sub(b, a)
        result.append((-dy, dx, dy * a[0] - dx * a[1]))
    return tuple(result)


def plane_value(plane, point):
    return plane[0] * point[0] + plane[1] * point[1] + plane[2]


def _closed_oriented_edges(mesh):
    uses = defaultdict(list)
    for face in mesh.faces:
        for a, b in zip(face, face[1:] + face[:1]):
            uses[tuple(sorted((a, b)))].append((a, b))
    if any(len(u) != 2 or u[0] != u[1][::-1] for u in uses.values()):
        raise ValueError('SHAFT_INDEXED_BOUNDARY_NOT_CLOSED_OR_ORIENTED')


def verify_shaft_prism_band(shaft, design_z_min, design_z_max, *, expected_sides=32):
    """Authenticate a prism throughout the full design z-band, from mesh faces.

    All faces crossing the open bracketing slab must be exactly the two
    outward-oriented triangles of every rectangular wall. Extra shells,
    intermediate heights, different upper/lower rings, missing walls and
    duplicate wall triangulations are rejected.
    """
    _closed_oriented_edges(shaft)
    levels = sorted({point[2] for point in shaft.vertices})
    below = [z for z in levels if z < design_z_min]
    above = [z for z in levels if z > design_z_max]
    if not below or not above or design_z_min >= design_z_max:
        raise ValueError('DESIGN_NOT_STRICTLY_BRACKETED_BY_SHAFT_HEIGHTS')
    lo, hi = max(below), min(above)
    if any(lo < z < hi for z in levels):
        raise ValueError('SHAFT_INTERMEDIATE_HEIGHT_WITHIN_PRISM_SLAB')
    active = [(i, tri) for i, tri in enumerate(shaft.triangles)
              if min(p[2] for p in tri) < hi and max(p[2] for p in tri) > lo]
    if any(any(p[2] not in (lo, hi) for p in tri) for _, tri in active):
        raise ValueError('SHAFT_CROSSING_FACE_NOT_RING_TO_RING')
    low_xy = {p[:2] for _, tri in active for p in tri if p[2] == lo}
    high_xy = {p[:2] for _, tri in active for p in tri if p[2] == hi}
    if low_xy != high_xy:
        raise ValueError('SHAFT_UPPER_LOWER_RINGS_DIFFER')
    polygon = convex_hull(low_xy)
    if len(polygon) != expected_sides:
        raise ValueError('SHAFT_PRISM_SIDE_COUNT_CHANGED')
    planes = halfplanes(polygon)
    if any(c <= 0 for _, _, c in planes):
        raise ValueError('SHAFT_AXIS_NOT_STRICTLY_INSIDE_RING')
    by_edge = defaultdict(list)
    for index, tri in active:
        supports = {p[:2] for p in tri}
        matches = [j for j, (a, b) in enumerate(zip(polygon, polygon[1:] + polygon[:1]))
                   if supports == {a, b}]
        if len(matches) != 1:
            raise ValueError('SHAFT_FACE_NOT_ON_ONE_PRISM_WALL')
        edge = matches[0]
        a, b = polygon[edge], polygon[(edge + 1) % len(polygon)]
        u, v = sub(tri[1], tri[0]), sub(tri[2], tri[0])
        normal_xy = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2])
        outward = (b[1] - a[1], a[0] - b[0])
        if sum(x * y for x, y in zip(normal_xy, outward)) <= 0:
            raise ValueError('SHAFT_WALL_NOT_OUTWARD_ORIENTED')
        by_edge[edge].append((index, frozenset(tri)))
    if len(active) != 2 * len(polygon) or set(by_edge) != set(range(len(polygon))):
        raise ValueError('SHAFT_RECTANGULAR_WALL_COVERAGE_INCOMPLETE')
    for j, items in by_edge.items():
        a, b = polygon[j], polygon[(j + 1) % len(polygon)]
        a0, b0, b1, a1 = (*a, lo), (*b, lo), (*b, hi), (*a, hi)
        diagonal1 = Counter([frozenset((a0, b0, b1)), frozenset((a0, b1, a1))])
        diagonal2 = Counter([frozenset((a0, b0, a1)), frozenset((b0, b1, a1))])
        actual = Counter(tri for _, tri in items)
        if actual != diagonal1 and actual != diagonal2:
            raise ValueError('SHAFT_RECTANGULAR_WALL_TRIANGULATION_INVALID')
    return dict(polygon=polygon, planes=planes, z_lo=lo, z_hi=hi,
                source_wall_face_indices=[i for i, _ in active],
                lower_upper_rings_equal=True, exact_wall_coverage=True)


def _deduplicate_clipped(polygon):
    answer = []
    for item in polygon:
        if not answer or item[0] != answer[-1][0]:
            answer.append(item)
    if len(answer) > 1 and answer[0][0] == answer[-1][0]:
        answer.pop()
    return answer


def clip_triangle_to_prism(triangle, planes):
    """Return a strict-interior witness with exact original-face barycentrics."""
    polygon = [(point, tuple(Fraction(int(i == j)) for j in range(3)))
               for i, point in enumerate(triangle)]
    for plane in planes:
        if not polygon:
            break
        clipped = []
        previous = polygon[-1]
        previous_sign = plane_value(plane, previous[0])
        for current in polygon:
            current_sign = plane_value(plane, current[0])
            if (previous_sign < 0 <= current_sign) or (current_sign < 0 <= previous_sign):
                t = previous_sign / (previous_sign - current_sign)
                point = tuple(a + t * (b - a) for a, b in zip(previous[0], current[0]))
                weights = tuple(a + t * (b - a) for a, b in zip(previous[1], current[1]))
                clipped.append((point, weights))
            if current_sign >= 0:
                clipped.append(current)
            previous, previous_sign = current, current_sign
        polygon = _deduplicate_clipped(clipped)
    if not polygon:
        return None
    count = len(polygon)
    point = tuple(sum(p[0][i] for p in polygon) / count for i in range(3))
    weights = tuple(sum(p[1][i] for p in polygon) / count for i in range(3))
    signs = tuple(plane_value(plane, point) for plane in planes)
    if not all(sign > 0 for sign in signs):
        return None
    if sum(weights) != 1 or min(weights) < 0 or any(
            point[k] != sum(weights[i] * triangle[i][k] for i in range(3)) for k in range(3)):
        raise AssertionError('EXACT_CLIP_WITNESS_BARYCENTRICS_INVALID')
    return dict(point=point, barycentric=weights, halfplane_signs=signs,
                clipped_vertex_count=count)


def projected_triangle_minimum_radius_squared(triangle):
    """Exact closest point of the XY projected closed triangle to the origin."""
    xy = tuple(p[:2] for p in triangle)
    signed_area = cross2(sub(xy[1], xy[0]), sub(xy[2], xy[0]))
    signs = [cross2(sub(b, a), (-a[0], -a[1])) for a, b in zip(xy, xy[1:] + xy[:1])]
    if signed_area and (all(s >= 0 for s in signs) or all(s <= 0 for s in signs)):
        return dict(squared_distance=Fraction(0), closest_xy=(Fraction(0), Fraction(0)),
                    feature='PROJECTED_TRIANGLE_CONTAINS_ORIGIN', edge=None, edge_parameter=None)
    candidates = []
    for i, (a, b) in enumerate(zip(xy, xy[1:] + xy[:1])):
        d = sub(b, a)
        length2 = sum(value * value for value in d)
        parameter = -sum(x * y for x, y in zip(a, d)) / length2 if length2 else Fraction(0)
        parameter = max(Fraction(0), min(Fraction(1), parameter))
        point = tuple(x + parameter * y for x, y in zip(a, d))
        candidates.append(dict(squared_distance=sum(x * x for x in point), closest_xy=point,
                               feature='PROJECTED_EDGE_OR_VERTEX', edge=i, edge_parameter=parameter))
    return min(candidates, key=lambda item: item['squared_distance'])


def rational_sqrt_lower_bound(value, *, denominator=10**12):
    """A proved rational floor sqrt, never a geometric comparison tolerance."""
    if value < 0 or not isinstance(denominator, int) or denominator <= 0:
        raise ValueError('SQRT_BOUND_ARGUMENT_INVALID')
    value = Fraction(value)
    numerator = math.isqrt(value.numerator * denominator * denominator // value.denominator)
    lower = Fraction(numerator, denominator)
    if not lower * lower <= value < (lower + Fraction(1, denominator)) ** 2:
        raise AssertionError('RATIONAL_SQRT_BRACKET_FAILED')
    return lower


def _strings(values):
    return [str(value) for value in values]


def audit_shaft_exclusion(design_path, shaft_path, *, expected_prism_sides=32,
                          expected_sha256=None):
    design, shaft = map(read_binary64_obj, (design_path, shaft_path))
    if expected_sha256 is not None:
        if set(expected_sha256) != {'design', 'shaft'} or any(
                mesh.sha256 != expected_sha256[name] for name, mesh in [('design', design), ('shaft', shaft)]):
            raise ValueError('FROZEN_SHAFT_OR_DESIGN_SHA256_MISMATCH')
    zmin, zmax = min(v[2] for v in design.vertices), max(v[2] for v in design.vertices)
    prism = verify_shaft_prism_band(shaft, zmin, zmax, expected_sides=expected_prism_sides)
    planes = prism['planes']
    inside_vertices = [i for i, point in enumerate(design.vertices)
                       if all(plane_value(plane, point) > 0 for plane in planes)]
    intruding_faces, witnesses, minimum = [], [], None
    for index, triangle in enumerate(design.triangles):
        witness = clip_triangle_to_prism(triangle, planes)
        if witness is not None:
            intruding_faces.append(index)
            if len(witnesses) < 4:
                witnesses.append(dict(face_index=index, triangle_exact=[_strings(p) for p in triangle],
                    point_exact=_strings(witness['point']), barycentric_exact=_strings(witness['barycentric']),
                    halfplane_signs_exact=_strings(witness['halfplane_signs']),
                    minimum_halfplane_sign_exact=str(min(witness['halfplane_signs'])),
                    minimum_halfplane_sign_float=float(min(witness['halfplane_signs'])),
                    clipped_vertex_count=witness['clipped_vertex_count']))
        radius = projected_triangle_minimum_radius_squared(triangle)
        if minimum is None or radius['squared_distance'] < minimum['squared_distance']:
            minimum = dict(radius, face_index=index)
    shaft_inradius2 = min(c * c / (a * a + b * b) for a, b, c in planes)
    available_radius2 = min(minimum['squared_distance'], shaft_inradius2)
    core_radius = rational_sqrt_lower_bound(available_radius2)
    # Strictly separate the cylinder from D's surface and the shaft side walls.
    if core_radius and core_radius * core_radius == available_radius2:
        core_radius -= Fraction(1, 10**12)
    core_exists = core_radius > 0
    anchor = (Fraction(0), Fraction(0), (prism['z_lo'] + zmin) / 2)
    anchor_below_bbox = anchor[2] < zmin
    return dict(
        schema='W4P18ExactShaftDesignExclusionV1',
        status=('STRICT_SHAFT_SURFACE_INTRUSION_FOUND_CONDITIONAL_POSITIVE_VOLUME_OVERLAP'
                if intruding_faces else 'NO_SHAFT_OPEN_INTERIOR_SURFACE_CONTACT_ANCHOR_AND_EMBEDDEDNESS_REQUIRED'),
        inputs=dict(design=dict(sha256=design.sha256, vertices=len(design.vertices), faces=len(design.faces)),
                    shaft=dict(sha256=shaft.sha256, vertices=len(shaft.vertices), faces=len(shaft.faces))),
        frozen_input_sha256_manifest_checked=expected_sha256 is not None,
        arithmetic='EXACT_FRACTIONS_OF_SAVED_BINARY64_OBJ_COORDINATES', tolerance_used=None,
        geometry_modified=False,
        verified_shaft_prism=dict(side_count=len(prism['polygon']),
            polygon_ccw_xy_exact=[_strings(p) for p in prism['polygon']],
            halfplanes_ABC_exact=[_strings(p) for p in planes],
            inside_rule='A*x+B*y+C>0 FOR EVERY WALL',
            z_lo_exact=str(prism['z_lo']), z_hi_exact=str(prism['z_hi']),
            design_z_min_exact=str(zmin), design_z_max_exact=str(zmax),
            source_wall_face_indices=prism['source_wall_face_indices'],
            lower_upper_rings_equal=True, exact_rectangle_wall_coverage=True,
            exhaustive_shaft_faces_in_slab_verified=True),
        design_triangles_exactly_processed=len(design.faces),
        strict_intruding_vertex_indices=inside_vertices, strict_intruding_vertex_count=len(inside_vertices),
        strict_intruding_face_indices=intruding_faces, strict_intruding_face_count=len(intruding_faces),
        strict_intrusion_witnesses=witnesses,
        positive_volume_overlap_certified_if_D_is_embedded_bounded_regular_solid=bool(intruding_faces),
        positive_volume_overlap_unconditionally_certified=False,
        entire_shaft_protected_certified=False,
        whole_shaft_exclusion_still_requires_D_embeddedness_and_outside_anchor=not bool(intruding_faces),
        minimum_design_surface_projected_radius=dict(
            squared_distance_exact=str(minimum['squared_distance']),
            squared_distance_float=float(minimum['squared_distance']),
            radius_float=math.sqrt(float(minimum['squared_distance'])),
            face_index=minimum['face_index'], feature=minimum['feature'],
            closest_xy_exact=_strings(minimum['closest_xy']), edge=minimum['edge'],
            edge_parameter_exact=None if minimum['edge_parameter'] is None else str(minimum['edge_parameter'])),
        conservative_axis_core=dict(
            positive_radius_available=core_exists, radius_reference_exact=str(core_radius),
            radius_reference_float=float(core_radius),
            shaft_inradius_squared_exact=str(shaft_inradius2),
            D_surface_radius_squared_lower_bound_exact=str(minimum['squared_distance']),
            squared_radius_strictly_below_D_surface=bool(core_exists and core_radius**2 < minimum['squared_distance']),
            squared_radius_strictly_below_shaft_walls=bool(core_exists and core_radius**2 < shaft_inradius2),
            cylinder_z_interval_exact=[str(prism['z_lo']), str(prism['z_hi'])],
            rational_sqrt_floor_denominator=10**12,
            sqrt_floor_is_proof_bound_not_geometric_tolerance=True,
            outside_anchor_reference_exact=_strings(anchor),
            anchor_strictly_below_all_D_boundary_vertices=anchor_below_bbox,
            anchor_is_inside_verified_shaft_prism=True,
            outside_anchor_ray_classification_performed=False,
            protected_if_D_is_embedded_bounded_regular_solid=bool(core_exists and anchor_below_bbox),
            unconditionally_protected=False,
            core_does_not_certify_entire_original_shaft=True),
        D_embeddedness_certificate_consumed=False,
        native_Cherchi_implicit_geometry_certified=False,
        W0_physical_tip_or_FD_approved=False, W2_teacher_training_allowed=False,
        Faster_optimization_executed=False, MuJoCo_real_optimized_before_after_executed=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--design', required=True)
    parser.add_argument('--shaft', required=True)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    report = audit_shaft_exclusion(args.design, args.shaft)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({key: report[key] for key in ('status', 'strict_intruding_vertex_count', 'strict_intruding_face_count')}, indent=2))
    return 2 if report['strict_intruding_face_count'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
