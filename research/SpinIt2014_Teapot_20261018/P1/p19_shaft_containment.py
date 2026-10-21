"""Whole-shaft containment, including coincident surfaces and both end caps.

The saved shaft is independently certified as a closed embedded sphere. A
strict kernel point q lies on the inner side of EVERY outward shaft triangle.
Every ray from q crosses an outward triangle only from inside to outside, so
the closed tetrahedra conv(q, shaft_face) form an exact star decomposition.

Every material triangle is clipped against EVERY overlapping closed tetrahedron.
Within such a tetrahedron, positive barycentric weight of q means strict shaft
interior, even on an INTERNAL tetrahedral seam. Only the external base facet
(weight(q)=0) is allowed to coincide with a material boundary. Thus the audit
does not miss seam, shared-face, shared-edge, tip, or end-cap cases.

If no material-boundary point lies inside S and q is inside M, connected int(S)
cannot cross the embedded boundary of M. Therefore int(S) is in int(M), and
closedness gives the full S subset M statement. No finite-point sampling is
used as a substitute for exhaustive boundary exclusion.

This concerns saved binary64 polyhedra only. W0/W2, native implicit geometry,
printing, strength, optimization, and simulation approvals remain false.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
from functools import reduce
import hashlib
import json
import math
from pathlib import Path
import struct
import time

import numpy as np

from p17_boundary_certificate import read_binary64_obj
from p18_exact_surface import audit_exact_surface
from p18_solid_domain import classify_point, cross, dot, integer_lift, sub


DEFAULT_KERNEL = (Fraction(0), Fraction(0), Fraction(1, 64))
FALSE_FLAGS = {
    "native_Cherchi_implicit_geometry_certified": False,
    "original_native_vs_microweld_set_equality_certified": False,
    "original_author_CAD_certified": False,
    "W0_physical_tip_or_FD_approved": False,
    "W2_teacher_training_allowed": False,
    "printability_or_strength_certified": False,
    "Faster_optimization_executed": False,
    "MuJoCo_real_optimized_before_after_executed": False,
}

# Cache entries are produced only by this module's real P18 computation. Reports
# are stored as immutable JSON and returned as copies; external dicts are never
# accepted as surface proofs. This is an in-process computational cache, not an
# authentication/security boundary against arbitrary Python code execution.
_VERIFIED_SURFACE_CACHE = {}


def verify_surface(path, expected_sha256=None):
    """Actually execute P18, bind to bytes, cache internally, return a copy."""
    actual_sha = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if expected_sha256 is not None and actual_sha != expected_sha256:
        raise ValueError("SURFACE_FROZEN_SHA256_MISMATCH")
    report = audit_exact_surface(path, actual_sha)
    if report["input"]["sha256"] != actual_sha:
        raise AssertionError("surface audit/file identity changed")
    _VERIFIED_SURFACE_CACHE[actual_sha] = json.dumps(report, sort_keys=True)
    return json.loads(_VERIFIED_SURFACE_CACHE[actual_sha])


def _surface_proof(path, expected_sha, reuse):
    current = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if current != expected_sha:
        raise ValueError("SURFACE_CHANGED_DURING_CONTAINMENT_AUDIT")
    if reuse and current in _VERIFIED_SURFACE_CACHE:
        return json.loads(_VERIFIED_SURFACE_CACHE[current]), True
    return verify_surface(path, expected_sha), False


def _primitive_signed(coefficients):
    values = tuple(Fraction(x) for x in coefficients)
    scale = math.lcm(*(x.denominator for x in values))
    integers = tuple(x.numerator * (scale // x.denominator) for x in values)
    divisor = reduce(math.gcd, (abs(x) for x in integers))
    if not divisor:
        raise ValueError("DEGENERATE_TETRAHEDRON_PLANE")
    return tuple(x // divisor for x in integers)


def plane_value(plane, point):
    return dot(plane[:3], point) + plane[3]


def tetrahedron_inward_planes(tetrahedron):
    """Four exact halfspaces >=0, indexed by their opposite tetra vertex."""
    points = tuple(tuple(Fraction(x) if not isinstance(x, int) else x for x in p)
                   for p in tetrahedron)
    if len(points) != 4 or any(len(p) != 3 for p in points):
        raise ValueError("FOUR_3D_TETRAHEDRON_POINTS_REQUIRED")
    result = []
    for opposite in range(4):
        a, b, c = tuple(p for i, p in enumerate(points) if i != opposite)
        normal = cross(sub(b, a), sub(c, a))
        plane = _primitive_signed((*normal, -dot(normal, a)))
        sign = plane_value(plane, points[opposite])
        if sign == 0:
            raise ValueError("DEGENERATE_TETRAHEDRON")
        if sign < 0:
            plane = tuple(-x for x in plane)
        result.append(plane)
    return tuple(result)


def _deduplicate_polygon(polygon):
    result = []
    for item in polygon:
        if not result or item[0] != result[-1][0]:
            result.append(item)
    if len(result) > 1 and result[0][0] == result[-1][0]:
        result.pop()
    return result


def clip_triangle_to_tetrahedron(triangle, tetrahedron=None, *, inward_planes=None):
    """Closed exact intersection with original-triangle barycentric weights.

    Each result item is (point, three barycentric weights). The caller can test
    positive value of plane 0 for positive q weight when tetrahedron=(q,a,b,c).
    Internal tetra faces are deliberately NOT treated as shaft boundaries.
    """
    triangle = tuple(tuple(Fraction(x) if not isinstance(x, int) else x for x in p)
                     for p in triangle)
    if len(triangle) != 3 or any(len(p) != 3 for p in triangle):
        raise ValueError("THREE_TRIANGLE_POINTS_REQUIRED")
    planes = inward_planes if inward_planes is not None else tetrahedron_inward_planes(tetrahedron)
    if len(planes) != 4:
        raise ValueError("FOUR_TETRAHEDRON_HALFSPACES_REQUIRED")
    if any(all(plane_value(plane, point) < 0 for point in triangle) for plane in planes):
        return ()
    polygon = [(p, tuple(Fraction(int(i == j)) for j in range(3)))
               for i, p in enumerate(triangle)]
    for plane in planes:
        if not polygon:
            break
        if all(plane_value(plane, point) >= 0 for point, _ in polygon):
            continue
        output = []
        previous = polygon[-1]
        old_sign = plane_value(plane, previous[0])
        for current in polygon:
            new_sign = plane_value(plane, current[0])
            if (old_sign < 0 <= new_sign) or (new_sign < 0 <= old_sign):
                parameter = Fraction(old_sign) / Fraction(old_sign - new_sign)
                point = tuple(a + parameter * (b - a) for a, b in zip(previous[0], current[0]))
                weights = tuple(a + parameter * (b - a) for a, b in zip(previous[1], current[1]))
                output.append((point, weights))
            if new_sign >= 0:
                output.append(current)
            previous, old_sign = current, new_sign
        polygon = _deduplicate_polygon(output)
    return tuple(polygon)


def triangle_tetrahedron_aabb_pairs(triangles, tetrahedra):
    """Conservative exhaustive cross-AABB pairs; closed-box contact is included."""
    a = np.asarray(triangles, dtype=np.float64)
    b = np.asarray(tetrahedra, dtype=np.float64)
    if a.ndim != 3 or a.shape[1:] != (3, 3) or b.ndim != 3 or b.shape[1:] != (4, 3):
        raise ValueError("TRIANGLE_AND_TETRAHEDRON_ARRAY_SHAPES_REQUIRED")
    if not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        raise ValueError("NONFINITE_AABB_COORDINATE")
    alo, ahi, blo, bhi = a.min(1), a.max(1), b.min(1), b.max(1)
    order = np.argsort(blo[:, 0], kind="stable")
    lower_x = blo[order, 0]
    for i in range(len(a)):
        stop = np.searchsorted(lower_x, ahi[i, 0], side="right")
        candidates = order[:stop]
        mask = np.all(bhi[candidates] >= alo[i], axis=1) & np.all(blo[candidates] <= ahi[i], axis=1)
        for j in np.sort(candidates[mask]):
            yield i, int(j)


def audit_full_shaft_containment(material_path, shaft_path, expected_sha256=None, *,
                                 kernel_point=DEFAULT_KERNEL, max_witnesses=4,
                                 reuse_verified_surfaces=False):
    """Prove whole saved shaft S subset saved material M, or retain a counterexample.

    Optional expected_sha256 must contain exactly material and shaft. The cache
    switch can only reuse real audits created by verify_surface in this process;
    arbitrary caller-provided dictionaries are never treated as certificates.
    """
    started = time.perf_counter()
    material, shaft = map(read_binary64_obj, (material_path, shaft_path))
    if expected_sha256 is not None:
        if set(expected_sha256) != {"material", "shaft"}:
            raise ValueError("PIN_BOTH_MATERIAL_AND_SHAFT")
        if any(mesh.sha256 != expected_sha256[name] for name, mesh in (("material", material), ("shaft", shaft))):
            raise ValueError("FROZEN_SHAFT_OR_MATERIAL_SHA256_MISMATCH")
    if type(max_witnesses) is not int or max_witnesses < 0:
        raise ValueError("NONNEGATIVE_MAX_WITNESSES_REQUIRED")
    kernel = tuple(Fraction(x) for x in kernel_point)
    if len(kernel) != 3:
        raise ValueError("THREE_KERNEL_COORDINATES_REQUIRED")
    material_surface, reused_m = _surface_proof(material_path, material.sha256, reuse_verified_surfaces)
    shaft_surface, reused_s = _surface_proof(shaft_path, shaft.sha256, reuse_verified_surfaces)
    result = {
        "schema": "W4P19WholeShaftContainmentByExactStarTetrahedraV1",
        "status": "WHOLE_SHAFT_CONTAINMENT_NOT_CERTIFIED",
        "full_original_shaft_contained_in_material": False,
        "exact_material_boundary_excludes_shaft_open_interior": False,
        "inputs": {name: {"sha256": mesh.sha256, "vertices": len(mesh.vertices), "faces": len(mesh.faces)}
                   for name, mesh in (("material", material), ("shaft", shaft))},
        "frozen_sha256_manifest_checked": expected_sha256 is not None,
        "material_exact_surface": material_surface,
        "shaft_exact_surface": shaft_surface,
        "in_process_verified_surface_cache_reused": {"material": reused_m, "shaft": reused_s},
        "kernel_point_exact": [str(x) for x in kernel],
        "scientific_flags": dict(FALSE_FLAGS),
        "geometry_modified": False,
        "tolerance_used": None,
    }
    if not material_surface["exact_embedded_closed_oriented_2manifold"] or not shaft_surface["exact_embedded_closed_oriented_2manifold"]:
        result["stop_reason"] = "MATERIAL_OR_SHAFT_NOT_EXACT_EMBEDDED_CLOSED_ORIENTED_SURFACE"
        result["elapsed_seconds"] = time.perf_counter() - started
        return result
    if shaft_surface["topology"]["surface_components"] != 1 or shaft_surface["topology"]["euler_characteristic"] != 2:
        result["stop_reason"] = "THIS_CERTIFICATE_REQUIRES_ONE_SPHERICAL_SHAFT_BOUNDARY"
        result["elapsed_seconds"] = time.perf_counter() - started
        return result
    if Fraction(shaft_surface["component_signed_volumes_exact"][0]) <= 0:
        result["stop_reason"] = "SHAFT_OUTWARD_ORIENTATION_REQUIRED"
        result["elapsed_seconds"] = time.perf_counter() - started
        return result
    lifted, scale = integer_lift((*material.vertices, *shaft.vertices, kernel))
    mv = lifted[:len(material.vertices)]
    sv = lifted[len(material.vertices):-1]
    q = lifted[-1]
    m_triangles = tuple(tuple(mv[i] for i in f) for f in material.faces)
    s_triangles = tuple(tuple(sv[i] for i in f) for f in shaft.faces)
    inward_values = [dot(cross(sub(b, a), sub(c, a)), sub(q, a)) for a, b, c in s_triangles]
    result["strict_kernel"] = {
        "every_outward_face_value_strictly_negative": all(value < 0 for value in inward_values),
        "faces_checked": len(inward_values),
        "violating_face_indices": [i for i, value in enumerate(inward_values) if value >= 0],
        "largest_oriented_face_value_exact_original_units": str(Fraction(max(inward_values), scale ** 3)),
    }
    if not all(value < 0 for value in inward_values):
        result["stop_reason"] = "QUERY_POINT_IS_NOT_A_STRICT_STAR_KERNEL"
        result["elapsed_seconds"] = time.perf_counter() - started
        return result
    shaft_anchor = classify_point(shaft, kernel)
    material_anchor = classify_point(material, kernel)
    result["kernel_in_shaft"] = shaft_anchor
    result["kernel_in_material"] = material_anchor
    if shaft_anchor["classification"] != "INSIDE":
        raise AssertionError("strict kernel/surface orientation and exact ray must agree")
    tetrahedra = tuple((q, *triangle) for triangle in s_triangles)
    planes = tuple(tetrahedron_inward_planes(tetrahedron) for tetrahedron in tetrahedra)
    unscaled_tetrahedra = tuple((kernel, *triangle) for triangle in shaft.triangles)
    candidate_count = intersection_count = intrusion_pairs = 0
    affected_faces = set()
    witnesses = []
    digest = hashlib.sha256()
    for face_index, tetra_index in triangle_tetrahedron_aabb_pairs(material.triangles, unscaled_tetrahedra):
        candidate_count += 1
        digest.update(struct.pack("<QQ", face_index, tetra_index))
        polygon = clip_triangle_to_tetrahedron(m_triangles[face_index], inward_planes=planes[tetra_index])
        if not polygon:
            continue
        intersection_count += 1
        base_values = [plane_value(planes[tetra_index][0], p) for p, _ in polygon]
        if any(value < 0 for value in base_values):
            raise AssertionError("clipped polygon escaped tetrahedron")
        if not any(value > 0 for value in base_values):
            continue
        intrusion_pairs += 1
        affected_faces.add(face_index)
        if len(witnesses) < max_witnesses:
            count = len(polygon)
            point = tuple(sum(item[0][axis] for item in polygon) / Fraction(count) for axis in range(3))
            weights = tuple(sum(item[1][axis] for item in polygon) / Fraction(count) for axis in range(3))
            if min(weights) < 0 or sum(weights) != 1 or any(
                    point[axis] != sum(weights[j] * m_triangles[face_index][j][axis] for j in range(3)) for axis in range(3)):
                raise AssertionError("witness is not exactly on original material triangle")
            q_weight = Fraction(plane_value(planes[tetra_index][0], point)) / Fraction(plane_value(planes[tetra_index][0], q))
            if q_weight <= 0 or any(plane_value(plane, point) < 0 for plane in planes[tetra_index]):
                raise AssertionError("witness lacks strict shaft interior certificate")
            original_point = tuple(value / scale for value in point)
            # Independent ray confirmation of the strongest concrete witness;
            # exhaustive absence proof itself comes from all tetrahedron clips.
            shaft_witness = classify_point(shaft, original_point)
            if shaft_witness["classification"] != "INSIDE":
                raise AssertionError("star-tetrahedron and independent exact shaft ray disagree")
            witnesses.append({
                "material_face_index_zero_based": face_index,
                "shaft_base_face_index_zero_based": tetra_index,
                "point_exact": [str(value) for value in original_point],
                "point_decimal_projection": [float(value) for value in original_point],
                "original_material_triangle_barycentric_exact": [str(value) for value in weights],
                "strict_positive_kernel_barycentric_weight_exact": str(q_weight),
                "closed_tetrahedron_halfspaces_nonnegative": True,
                "independent_exact_shaft_ray": shaft_witness,
            })
    excluded = intrusion_pairs == 0
    contained = excluded and material_anchor["classification"] == "INSIDE"
    result.update({
        "status": ("EXACT_WHOLE_SAVED_SHAFT_CONTAINED" if contained else
                   "MATERIAL_BOUNDARY_INSIDE_SHAFT_COUNTEREXAMPLE" if intrusion_pairs else
                   "SHAFT_ANCHOR_NOT_INSIDE_MATERIAL"),
        "full_original_shaft_contained_in_material": contained,
        "exact_material_boundary_excludes_shaft_open_interior": excluded,
        "shaft_not_contained_counterexample_certified": bool(intrusion_pairs) or material_anchor["classification"] == "OUTSIDE",
        "positive_volume_shaft_minus_material_certified": bool(intrusion_pairs) or material_anchor["classification"] == "OUTSIDE",
        "coverage": {
            "material_triangles": len(material.faces), "shaft_star_tetrahedra": len(tetrahedra),
            "total_triangle_tetrahedron_pairs": len(material.faces) * len(tetrahedra),
            "closed_aabb_candidate_pairs": candidate_count,
            "strictly_disjoint_aabb_pairs": len(material.faces) * len(tetrahedra) - candidate_count,
            "exact_tetrahedron_clips_executed": candidate_count,
            "nonempty_closed_clip_pairs": intersection_count,
            "strict_shaft_interior_clip_pairs": intrusion_pairs,
            "material_faces_with_strict_shaft_intrusion": len(affected_faces),
            "intruding_material_face_indices": sorted(affected_faces),
            "candidate_pair_index_stream_sha256": digest.hexdigest(),
            "all_candidate_pairs_checked": True,
            "internal_tetrahedron_seams_excluded": 0,
            "coincident_external_base_facets_allowed": True,
        },
        "counterexample_witnesses": witnesses,
        "proof_scope": "Whole saved binary64 regular shaft, including boundary and both ends; no native implicit or physical approval.",
        "elapsed_seconds": time.perf_counter() - started,
    })
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--material", required=True)
    parser.add_argument("--shaft", required=True)
    parser.add_argument("--output")
    parser.add_argument("--expected-sha256-json")
    args = parser.parse_args()
    expected = json.loads(Path(args.expected_sha256_json).read_text()) if args.expected_sha256_json else None
    report = audit_full_shaft_containment(args.material, args.shaft, expected)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as stream:
            stream.write(text + "\n")
    print(text)
    return 0 if report["full_original_shaft_contained_in_material"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
