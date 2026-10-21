"""Exact embedded closed oriented two-manifold checks for saved binary64 OBJ.

All topology uses the ORIGINAL OBJ vertex indices. Duplicate coordinates at
different indices are rejected; neither exact nor near points are welded.
Coordinates are exact dyadic rationals, uniformly scaled to Python integers for
the predicates. Broadphase is conservative AABB overlap; every candidate,
INCLUDING adjacent triangles, is accounted for. The exact intersection must
equal precisely the combinatorial simplex shared by the two original faces.

This certifies the saved mesh only. It does not certify native Cherchi implicit
points, solid interior orientation/nesting, wall thickness, or W0 admission.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
from functools import reduce
import hashlib
import json
import math
from pathlib import Path
import struct
import time

import numpy as np

from p17_boundary_certificate import FALSE_FLAGS, read_binary64_obj


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _ratio(numerator, denominator):
    return Fraction(numerator) / Fraction(denominator)


def _lerp(a, b, t):
    return tuple(x + t * (y - x) for x, y in zip(a, b))


def _exact_triangle(triangle):
    result = []
    for point in triangle:
        row = []
        for value in point:
            if isinstance(value, Fraction):
                row.append(value)
            elif isinstance(value, (int, np.integer)):
                row.append(int(value))
            elif isinstance(value, (float, np.floating)) and math.isfinite(float(value)):
                row.append(Fraction.from_float(float(value)))
            else:
                raise ValueError("triangle coordinates must be finite integers, Fractions, or binary64 values")
        if len(row) != 3:
            raise ValueError("triangle points must have three coordinates")
        result.append(tuple(row))
    if len(result) != 3:
        raise ValueError("exactly three triangle vertices required")
    return tuple(result)


def exact_plane(triangle):
    """Canonical primitive integer coefficients n.x+d=0, for rational input."""
    triangle = _exact_triangle(triangle)
    normal = _cross(_sub(triangle[1], triangle[0]), _sub(triangle[2], triangle[0]))
    coefficients = (*normal, -_dot(normal, triangle[0]))
    denominators = [x.denominator if isinstance(x, Fraction) else 1 for x in coefficients]
    scale = math.lcm(*denominators)
    integers = tuple(int(x * scale) for x in coefficients)
    divisor = reduce(math.gcd, (abs(x) for x in integers))
    if not divisor:
        raise ValueError("exact degenerate triangle")
    integers = tuple(x // divisor for x in integers)
    return integers if next(x for x in integers if x) > 0 else tuple(-x for x in integers)


def _plane_value(plane, point):
    return _dot(plane[:3], point) + plane[3]


def _project(triangle, normal):
    drop = next(i for i, x in enumerate(normal) if x)
    axes = tuple(i for i in range(3) if i != drop)
    return tuple(tuple(p[i] for i in axes) for p in triangle), axes


def _orient2(a, b, point):
    return (b[0] - a[0]) * (point[1] - a[1]) - (b[1] - a[1]) * (point[0] - a[0])


def _plane_section(triangle, distances):
    points = {p for p, distance in zip(triangle, distances) if distance == 0}
    for i, a in enumerate(triangle):
        j = (i + 1) % 3
        da, db = distances[i], distances[j]
        if da * db < 0:
            points.add(_lerp(a, triangle[j], _ratio(da, da - db)))
    return tuple(points)


def exact_triangle_intersection(triangle_a, triangle_b, plane_a=None, plane_b=None):
    """Return the exact convex intersection vertices, including point/edge contact.

    The two triangles MUST use a common coordinate system. Inputs may be Python
    integers, Fractions, or binary64 values (converted to exact Fractions).
    No same-index/adjacency shortcut is taken here, so this public helper is
    also safe for cross-surface comparisons.
    """
    a, b = _exact_triangle(triangle_a), _exact_triangle(triangle_b)
    pa = plane_a if plane_a is not None else exact_plane(a)
    pb = plane_b if plane_b is not None else exact_plane(b)
    db = tuple(_plane_value(pa, p) for p in b)
    da = tuple(_plane_value(pb, p) for p in a)
    if (all(x > 0 for x in da) or all(x < 0 for x in da)
            or all(x > 0 for x in db) or all(x < 0 for x in db)):
        return ()
    direction = _cross(pa[:3], pb[:3])
    if any(direction):
        cut_a, cut_b = _plane_section(a, da), _plane_section(b, db)
        if not cut_a or not cut_b:
            return ()
        axis = next(i for i, value in enumerate(direction) if value)
        by_parameter = {p[axis]: p for p in cut_a + cut_b}
        lower = max(min(p[axis] for p in cut_a), min(p[axis] for p in cut_b))
        upper = min(max(p[axis] for p in cut_a), max(p[axis] for p in cut_b))
        if lower > upper:
            return ()
        return tuple(dict.fromkeys((by_parameter[lower], by_parameter[upper])))
    if any(db):
        return ()
    projected_b, axes = _project(b, pa[:3])
    orientation = 1 if _orient2(*projected_b) > 0 else -1
    polygon = list(a)
    for i, start in enumerate(projected_b):
        end = projected_b[(i + 1) % 3]
        if not polygon:
            break
        result = []
        previous = polygon[-1]
        d_previous = orientation * _orient2(start, end, tuple(previous[j] for j in axes))
        for point in polygon:
            distance = orientation * _orient2(start, end, tuple(point[j] for j in axes))
            if (distance >= 0) != (d_previous >= 0):
                result.append(_lerp(previous, point, _ratio(d_previous, d_previous - distance)))
            if distance >= 0:
                result.append(point)
            previous, d_previous = point, distance
        polygon = list(dict.fromkeys(result))
    return tuple(polygon)


def intersection_equals_shared_simplex(points, shared_points):
    """Check equality, not merely containment, with the expected shared simplex."""
    points, shared = tuple(points), tuple(shared_points)
    if not shared:
        return not points
    if len(shared) == 1:
        return bool(points) and all(p == shared[0] for p in points)
    if len(shared) == 2:
        if not points:
            return False
        a, b = shared
        direction = _sub(b, a)
        if not any(direction):
            return False
        axis = next(i for i, value in enumerate(direction) if value)
        parameters = []
        for p in points:
            if any(_cross(_sub(p, a), direction)):
                return False
            parameters.append(_ratio(p[axis] - a[axis], direction[axis]))
        return min(parameters) == 0 and max(parameters) == 1
    return False  # Sharing all three indices is a duplicate face, not adjacency.


def _intersection_dimension(points):
    if not points:
        return -1
    distinct = tuple(dict.fromkeys(points))
    if len(distinct) == 1:
        return 0
    direction = _sub(distinct[1], distinct[0])
    return 2 if any(any(_cross(direction, _sub(p, distinct[0]))) for p in distinct[2:]) else 1


def _strict_triangle_interior(point, triangle, plane):
    projected, axes = _project(triangle, plane[:3])
    q = tuple(point[i] for i in axes)
    orientation = 1 if _orient2(*projected) > 0 else -1
    return all(orientation * _orient2(projected[i], projected[(i + 1) % 3], q) > 0 for i in range(3))


def _classify_forbidden(points, a, b, pa, pb, shared_count):
    if shared_count == 3:
        return "duplicate_face"
    dimension = _intersection_dimension(points)
    if dimension == 2:
        return "coplanar_area_overlap"
    if dimension == 0:
        return "illegal_point_contact"
    if dimension == 1:
        center = tuple(sum(p[i] for p in points) / Fraction(len(points)) for i in range(3))
        if pa != pb and _strict_triangle_interior(center, a, pa) and _strict_triangle_interior(center, b, pb):
            return "transverse_penetration"
        return "illegal_edge_contact"
    return "missing_expected_shared_simplex"


def aabb_candidate_pairs(triangles_a, triangles_b=None):
    """Enumerate all overlapping closed AABBs, including touching and adjacency.

    With a second mesh, ALL pairs (i,j) are considered; equal numeric indices
    have no significance across meshes. With only one mesh, pairs satisfy i<j.
    min/max/comparison on saved binary64 coordinates have no geometric rounding.
    General finite rational inputs also remain conservative because conversion
    to binary64 is monotone (rounding may add candidates, never remove overlap).
    """
    self_check = triangles_b is None
    a = np.asarray(triangles_a, dtype=np.float64)
    b = a if self_check else np.asarray(triangles_b, dtype=np.float64)
    if a.ndim != 3 or b.ndim != 3 or a.shape[1:] != (3, 3) or b.shape[1:] != (3, 3):
        raise ValueError("expected triangle arrays with shape (N,3,3)")
    if not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        raise ValueError("nonfinite broadphase coordinate")
    alo, ahi, blo, bhi = a.min(1), a.max(1), b.min(1), b.max(1)
    order = np.argsort(blo[:, 0], kind="stable")
    ordered_lower_x = blo[order, 0]
    for i in range(len(a)):
        stop = np.searchsorted(ordered_lower_x, ahi[i, 0], side="right")
        candidates = order[:stop]
        mask = np.all(bhi[candidates] >= alo[i], axis=1) & np.all(blo[candidates] <= ahi[i], axis=1)
        if self_check:
            mask &= candidates > i
        for j in np.sort(candidates[mask]):
            yield i, int(j)


def _topology(points, faces):
    coordinates = defaultdict(list)
    for index, point in enumerate(points):
        coordinates[point].append(index)
    duplicate_coordinates = [indices for indices in coordinates.values() if len(indices) > 1]
    face_counts = Counter(tuple(sorted(face)) for face in faces)
    duplicate_faces = [face for face, count in face_counts.items() if count > 1]
    edge_faces, edge_directions = defaultdict(list), Counter()
    links, used = defaultdict(list), set()
    adjacency = [set() for _ in faces]
    for face_index, face in enumerate(faces):
        used.update(face)
        for i, vertex in enumerate(face):
            following, previous = face[(i + 1) % 3], face[(i + 2) % 3]
            edge = tuple(sorted((vertex, following)))
            edge_faces[edge].append(face_index)
            edge_directions[edge] += 1 if vertex < following else -1
            links[vertex].append((following, previous))
    bad_edges = [edge for edge, uses in edge_faces.items() if len(uses) != 2]
    bad_orientations = [edge for edge in edge_faces if edge_directions[edge] != 0]
    for uses in edge_faces.values():
        for index in uses:
            adjacency[index].update(other for other in uses if other != index)
    unseen = set(range(len(faces)))
    components = []
    while unseen:
        stack, component = [unseen.pop()], []
        while stack:
            face_index = stack.pop()
            component.append(face_index)
            for other in adjacency[face_index]:
                if other in unseen:
                    unseen.remove(other)
                    stack.append(other)
        components.append(component)
    bad_links = []
    for vertex, edge_list in links.items():
        graph = defaultdict(list)
        for a, b in edge_list:
            graph[a].append(b)
            graph[b].append(a)
        counts = Counter(tuple(sorted(edge)) for edge in edge_list)
        failed = (len(graph) < 3 or any(len(neighbors) != 2 for neighbors in graph.values())
                  or any(count != 1 for count in counts.values()))
        remaining = set(graph)
        stack = [remaining.pop()]
        while stack:
            for other in graph[stack.pop()]:
                if other in remaining:
                    remaining.remove(other)
                    stack.append(other)
        if failed or remaining:
            bad_links.append(vertex)
    unused = sorted(set(range(len(points))) - used)
    passed = not any((duplicate_coordinates, duplicate_faces, bad_edges, bad_orientations, bad_links, unused))
    return {
        "indexed_closed_consistently_oriented_2manifold": passed,
        "duplicate_coordinate_index_groups": len(duplicate_coordinates),
        "duplicate_coordinate_index_witnesses": duplicate_coordinates[:8],
        "duplicate_face_groups": len(duplicate_faces),
        "edge_incidence_error_count": len(bad_edges),
        "edge_orientation_error_count": len(bad_orientations),
        "vertex_link_non_circle_count": len(bad_links),
        "vertex_link_witnesses": bad_links[:8],
        "unused_vertex_count": len(unused),
        "surface_components": len(components),
        "component_face_counts": [len(c) for c in components],
        "indexed_edges": len(edge_faces),
        "euler_characteristic": len(used) - len(edge_faces) + len(faces),
    }, components


def audit_exact_surface(path, expected_sha256=None, *, max_witnesses=8):
    """Exhaustively certify one saved indexed surface; no adjacency pairs skipped.

    Bad/degenerate OBJ and SHA mismatch raise ValueError. Otherwise every AABB
    candidate is checked even if a separate topology failure already exists.
    A noncoplanar shared-edge pair is checked by an exact analytic theorem:
    two distinct planes sharing that edge intersect on its supporting line,
    and each nondegenerate triangle intersects that line in exactly that edge.
    This path is separately counted, not silently excluded from coverage.
    """
    started = time.perf_counter()
    mesh = read_binary64_obj(path)
    if expected_sha256 is not None and mesh.sha256 != expected_sha256:
        raise ValueError("frozen surface SHA256 mismatch")
    if not isinstance(max_witnesses, int) or max_witnesses < 0:
        raise ValueError("max_witnesses must be a nonnegative integer")
    scale = max(coordinate.denominator for point in mesh.vertices for coordinate in point)
    if scale & (scale - 1):
        raise AssertionError("binary64 coordinates must be dyadic")
    points = tuple(tuple(coordinate.numerator * (scale // coordinate.denominator)
                         for coordinate in point) for point in mesh.vertices)
    triangles = tuple(tuple(points[index] for index in face) for face in mesh.faces)
    planes = tuple(exact_plane(triangle) for triangle in triangles)
    topology, components = _topology(points, mesh.faces)
    denominated_volume = 6 * scale ** 3
    component_volumes = []
    for component in components:
        six_volume = sum(_dot(triangles[i][0], _cross(triangles[i][1], triangles[i][2])) for i in component)
        component_volumes.append(str(Fraction(six_volume, denominated_volume)))
    sharing_counts, forbidden_kinds = Counter(), Counter()
    candidates = analytic_edges = narrowphase = forbidden_count = 0
    witnesses = []
    pair_digest = hashlib.sha256()
    for i, j in aabb_candidate_pairs(mesh.triangles):
        candidates += 1
        pair_digest.update(struct.pack("<QQ", i, j))
        shared_indices = tuple(sorted(set(mesh.faces[i]).intersection(mesh.faces[j])))
        shared_count = len(shared_indices)
        sharing_counts[str(shared_count)] += 1
        if shared_count == 2 and planes[i] != planes[j]:
            analytic_edges += 1
            continue
        narrowphase += 1
        intersection = exact_triangle_intersection(triangles[i], triangles[j], planes[i], planes[j])
        shared_points = tuple(points[k] for k in shared_indices)
        if not intersection_equals_shared_simplex(intersection, shared_points):
            forbidden_count += 1
            kind = _classify_forbidden(intersection, triangles[i], triangles[j], planes[i], planes[j], shared_count)
            forbidden_kinds[kind] += 1
            if len(witnesses) < max_witnesses:
                witnesses.append({
                    "face_indices_zero_based": [i, j], "shared_original_vertex_indices": list(shared_indices),
                    "kind": kind, "intersection_dimension": _intersection_dimension(intersection),
                    "intersection_vertices_exact_original_units": [[str(Fraction(x) / scale) for x in p] for p in intersection],
                })
    if candidates != analytic_edges + narrowphase or candidates != sum(sharing_counts.values()):
        raise AssertionError("every candidate must be accounted for exactly once")
    passed = topology["indexed_closed_consistently_oriented_2manifold"] and forbidden_count == 0
    result = {
        "status": "EXACT_SAVED_BINARY64_EMBEDDED_CLOSED_ORIENTED_2MANIFOLD_PASS" if passed else "EXACT_SURFACE_REJECTED",
        "exact_embedded_closed_oriented_2manifold": passed,
        "input": {"sha256": mesh.sha256, "vertices": len(points), "faces": len(mesh.faces)},
        "frozen_sha256_checked": expected_sha256 is not None,
        "exact_predicate_arithmetic": "Python integers plus Fraction for rational intersections; no tolerance",
        "common_integer_coordinate_scale_power_of_two": scale.bit_length() - 1,
        "all_triangles_exactly_nondegenerate": True,
        "topology": topology,
        "component_signed_volumes_exact": component_volumes,
        "coverage": {
            "total_unordered_face_pairs": len(mesh.faces) * (len(mesh.faces) - 1) // 2,
            "aabb_candidate_pairs": candidates,
            "strictly_disjoint_aabb_pairs": len(mesh.faces) * (len(mesh.faces) - 1) // 2 - candidates,
            "candidate_pairs_by_shared_original_vertex_count": {str(i): sharing_counts[str(i)] for i in range(4)},
            "exact_noncoplanar_shared_edge_theorem_checks": analytic_edges,
            "exact_triangle_intersection_checks": narrowphase,
            "candidate_pair_index_stream_sha256": pair_digest.hexdigest(),
            "all_candidate_pairs_checked": True,
            "adjacent_candidates_excluded": 0,
        },
        "forbidden_intersection_pair_count": forbidden_count,
        "forbidden_intersection_kinds": dict(forbidden_kinds),
        "forbidden_intersection_witnesses": witnesses,
        "elapsed_seconds": time.perf_counter() - started,
        "scientific_flags": dict(FALSE_FLAGS),
        "saved_surface_only_not_native_implicit_certificate": True,
        "geometry_modified": False,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", required=True)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--output")
    args = parser.parse_args()
    report = audit_exact_surface(args.mesh, args.expected_sha256)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as stream:
            stream.write(text + "\n")
    print(text)
    return 0 if report["exact_embedded_closed_oriented_2manifold"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
