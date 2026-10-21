"""Exact radial shaft protection and the frozen P18 outer-containment defect.

A positive construction guard is geometry.  It is never an epsilon in the
predicates below.  The new design proof recomputes embeddedness from saved OBJ
bytes; the historical outer defect authenticates the already frozen P18 proof.
Neither API grants physical approval or proves original-shaft containment in F.
"""
from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re

from p17_boundary_certificate import read_binary64_obj
from p17_material_candidate import typed_exact_equal
from p18_exact_surface import audit_exact_surface
from p18_shaft_domain import (
    projected_triangle_minimum_radius_squared, verify_shaft_prism_band,
)
from p18_solid_domain import (
    _without_timings, classify_point, exact_signed_volume, fraction_json,
    sqrt_bounds,
)


MINIMUM_GAP = Fraction(1, 500)
SQRT_GRID = 10 ** 12
FROZEN_OUTER_SHA256 = '4c2e4d480d1041f4817128a8b4b61675d80a699e448e7a5a253311c1805a3aa2'
ORIGINAL_SHAFT_SHA256 = '65d794715d580ebab231716669e25d79fea7f353da35c96d4a54f1779dc7e9f0'
P18_REPORT_SHA256 = '053611ba361212147aaba9d5ff40c017a2d0104d0065d6f6e07eda7421ddc613'
DENIED_FLAGS = {
    'native_Cherchi_implicit_region_partition_certified': False,
    'original_author_CAD_certified': False,
    'full_original_shaft_contained_in_fixed_material': False,
    'W0_physical_tip_or_FD_approved': False,
    'W2_teacher_training_allowed': False,
    'Faster_optimization_executed': False,
    'MuJoCo_real_optimized_before_after_executed': False,
    'printability_or_strength_certified': False,
}


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _require_hashes(expected, names):
    if not isinstance(expected, dict) or set(expected) != set(names):
        raise ValueError('P19_EXPLICIT_INPUT_SHA256_SET_REQUIRED')
    if any(type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None
           for value in expected.values()):
        raise ValueError('P19_INVALID_EXPECTED_SHA256')


def _load_bound(path, expected):
    mesh = read_binary64_obj(path)
    if mesh.sha256 != expected:
        raise ValueError('P19_GUARD_INPUT_SHA256_MISMATCH')
    return mesh


def _surface(path, expected, supplied):
    # A matching input hash and a caller-supplied True flag are not a proof.
    fresh = audit_exact_surface(path, expected)
    if supplied is not None and not typed_exact_equal(
            _without_timings(supplied), _without_timings(fresh)):
        raise ValueError('P19_SUPPLIED_SURFACE_CERTIFICATE_DIFFERS_FROM_REPLAY')
    return fresh


def _bounded_outward_solid(mesh, surface):
    return (surface['input']['sha256'] == mesh.sha256 and
            surface['frozen_sha256_checked'] is True and
            surface['exact_embedded_closed_oriented_2manifold'] is True and
            surface['topology']['surface_components'] == 1 and
            exact_signed_volume(mesh) > 0)


def audit_radial_shaft_guard(design_path, shaft_path, *, expected_sha256,
                            minimum_gap=MINIMUM_GAP, sqrt_grid=SQRT_GRID,
                            design_surface_certificate=None,
                            shaft_surface_certificate=None):
    """Prove an all-z gap between the full saved shaft and the bounded D solid.

    Let L be a proved lower bound on every D boundary point's XY radius and R
    an upper bound on every S boundary point's XY radius.  All shaft triangles,
    and hence its bounded regular solid, lie in the convex cylinder r<=R.
    If D is embedded and an axis point is outside D, the connected cylinder
    r<L is outside D: its interior contains no D boundary point.  Thus L-R is
    a Euclidean lower bound on the distance between the two complete solids.

    The registered required gap is exactly 1/500 reference unit.  An optional
    external surface certificate is compared with a new audit, never trusted.
    This is not a proof that S is contained in M or in the final fixed solid F.
    """
    _require_hashes(expected_sha256, ('design', 'shaft'))
    if expected_sha256['shaft'] != ORIGINAL_SHAFT_SHA256:
        raise ValueError('P19_ORIGINAL_SHAFT_IDENTITY_CHANGED')
    if isinstance(minimum_gap, bool) or Fraction(minimum_gap) != MINIMUM_GAP:
        raise ValueError('P19_PREREGISTERED_MINIMUM_GAP_CHANGED')
    if type(sqrt_grid) is not int or sqrt_grid <= 0:
        raise ValueError('P19_SQRT_GRID_MUST_BE_A_POSITIVE_INTEGER')
    design = _load_bound(design_path, expected_sha256['design'])
    shaft = _load_bound(shaft_path, expected_sha256['shaft'])
    design_surface = _surface(design_path, design.sha256, design_surface_certificate)
    shaft_surface = _surface(shaft_path, shaft.sha256, shaft_surface_certificate)
    valid_design = _bounded_outward_solid(design, design_surface)
    valid_shaft = _bounded_outward_solid(shaft, shaft_surface)

    minimum = None
    for index, triangle in enumerate(design.triangles):
        item = projected_triangle_minimum_radius_squared(triangle)
        if minimum is None or item['squared_distance'] < minimum['squared_distance']:
            minimum = dict(item, face_index=index)
    shaft_radii = tuple(point[0] ** 2 + point[1] ** 2 for point in shaft.vertices)
    maximum = max(shaft_radii)
    lower_design, upper_design = sqrt_bounds(minimum['squared_distance'], sqrt_grid)
    lower_shaft, upper_shaft = sqrt_bounds(maximum, sqrt_grid)
    gap = lower_design - upper_shaft
    minimum_z = min(point[2] for point in design.vertices)
    anchor = (Fraction(0), Fraction(0), minimum_z - 1)
    anchor_result = classify_point(design, anchor)
    axis_outside = anchor_result['classification'] == 'OUTSIDE'
    radial_gap = gap >= MINIMUM_GAP
    certified = valid_design and valid_shaft and axis_outside and radial_gap

    return dict(
        schema='W4P19ExactRadialShaftExclusionV1',
        status=('EXACT_COMPLETE_SHAFT_DESIGN_GAP_CERTIFIED_NOT_ADMITTED'
                if certified else 'EXACT_COMPLETE_SHAFT_DESIGN_GAP_NOT_CERTIFIED'),
        inputs={name: dict(sha256=item.sha256, vertices=len(item.vertices), faces=len(item.faces))
                for name, item in (('design', design), ('shaft', shaft))},
        arithmetic='EXACT_RATIONALS_OF_SAVED_BINARY64_COORDINATES',
        geometric_tolerance=None, geometry_modified=False,
        registered_minimum_gap_reference_exact=str(MINIMUM_GAP),
        sqrt_grid_denominator=sqrt_grid,
        design_triangles_exactly_processed=len(design.faces),
        shaft_vertices_exactly_processed=len(shaft.vertices),
        minimum_design_surface_projected_radius=dict(
            squared_distance_exact=str(minimum['squared_distance']),
            face_index=minimum['face_index'], feature=minimum['feature'],
            closest_xy_exact=[str(value) for value in minimum['closest_xy']],
            edge=minimum['edge'],
            edge_parameter_exact=(None if minimum['edge_parameter'] is None
                                  else str(minimum['edge_parameter'])),
            lower_bound_reference_exact=str(lower_design),
            upper_bound_reference_exact=str(upper_design)),
        maximum_shaft_vertex_projected_radius=dict(
            squared_distance_exact=str(maximum),
            vertex_index=shaft_radii.index(maximum),
            lower_bound_reference_exact=str(lower_shaft),
            upper_bound_reference_exact=str(upper_shaft)),
        radial_gap_lower_bound_reference=fraction_json(gap),
        full_solid_distance_lower_bound_reference=(fraction_json(gap) if certified else None),
        radial_bounds_meet_registered_gap=radial_gap,
        radial_bounds_alone_do_not_prove_full_solid_separation=True,
        axis_anchor_exact=[str(value) for value in anchor],
        axis_anchor_strictly_below_all_design_vertices=anchor[2] < minimum_z,
        axis_anchor_classification=anchor_result,
        surface_audits=dict(design=design_surface, shaft=shaft_surface),
        surface_certificates_recomputed_here=True,
        supplied_surface_certificates_compared=dict(
            design=design_surface_certificate is not None,
            shaft=shaft_surface_certificate is not None),
        design_embedded_connected_outward_bounded_solid=valid_design,
        shaft_embedded_connected_outward_bounded_solid=valid_shaft,
        all_z_axis_cylinder_excluded_from_design_solid=(valid_design and axis_outside and gap > 0),
        full_original_shaft_disjoint_from_design=certified,
        positive_full_solid_distance_certified=certified,
        full_original_shaft_in_F_requires_separate_outer_containment=True,
        proof_scope='Complete saved S and D regular solids, every z; no native implicit-set identity',
        optimization_admitted=False, training_admitted=False,
        scientific_flags=dict(DENIED_FLAGS))


def audit_frozen_outer_shaft_intrusion(outer_path, shaft_path, *, p18_report_path):
    """Recompute exact witnesses that the frozen P17/P18 M fails to contain S.

    P18 already proves these exact two boundaries embedded and closed.  Its
    report is authenticated by a fixed external digest; it is not regenerated
    here.  All 3-D vertex/half-plane decisions and the explicit ray witnesses
    are recomputed from the frozen OBJ bytes on every call.
    """
    if _sha256(p18_report_path) != P18_REPORT_SHA256:
        raise ValueError('P19_FROZEN_P18_REPORT_SHA256_MISMATCH')
    historical = json.loads(Path(p18_report_path).read_text())
    outer = _load_bound(outer_path, FROZEN_OUTER_SHA256)
    shaft = _load_bound(shaft_path, ORIGINAL_SHAFT_SHA256)
    outer_certificate = historical['exact_surface_audits']['M']
    shaft_certificate = historical['exact_shaft_surface_audit']
    if not (_bounded_outward_solid(outer, outer_certificate) and
            _bounded_outward_solid(shaft, shaft_certificate)):
        raise ValueError('P19_FROZEN_P18_EMBEDDING_BINDING_FAILED')
    prism = verify_shaft_prism_band(shaft, Fraction(3, 8), Fraction(1))
    polygon = prism['polygon']
    intrusions = []
    for index, (x, y, z) in enumerate(outer.vertices):
        if not prism['z_lo'] < z < prism['z_hi']:
            continue
        # Independent edge determinants, not the clipping module's plane_value.
        signs = tuple((b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0])
                      for a, b in zip(polygon, polygon[1:] + polygon[:1]))
        if all(value > 0 for value in signs):
            intrusions.append(dict(vertex_index=index,
                point_exact=[str(value) for value in (x, y, z)],
                minimum_strict_wall_determinant_exact=str(min(signs))))
    witnesses = []
    for item in intrusions[:4]:
        point = outer.vertices[item['vertex_index']]
        witnesses.append(dict(item,
            outer_classification=classify_point(outer, point),
            shaft_classification=classify_point(shaft, point)))
    refuted = bool(witnesses) and all(
        row['outer_classification']['classification'] == 'BOUNDARY' and
        row['shaft_classification']['classification'] == 'INSIDE' for row in witnesses)
    zs = [outer.vertices[item['vertex_index']][2] for item in intrusions]
    return dict(
        schema='W4P19FrozenOuterShaftIntrusionV1',
        status=('FROZEN_OUTER_DOES_NOT_CONTAIN_COMPLETE_ORIGINAL_SHAFT'
                if refuted else 'NO_VERTEX_COUNTEREXAMPLE_FOUND_NOT_A_CONTAINMENT_PROOF'),
        frozen_outer_sha256=outer.sha256, original_shaft_sha256=shaft.sha256,
        authenticated_P18_report_sha256=P18_REPORT_SHA256,
        historical_embedding_certificate_authenticated=True,
        historical_embedding_certificate_recomputed_here=False,
        exact_vertex_and_ray_witnesses_recomputed_here=True,
        shaft_prism_z_interval_exact=[str(prism['z_lo']), str(prism['z_hi'])],
        shaft_prism_side_count=len(polygon),
        outer_vertices_exactly_scanned=len(outer.vertices),
        strict_intruding_vertex_count=len(intrusions),
        strict_intruding_vertices=intrusions,
        exact_boundary_and_inside_ray_witnesses=witnesses,
        strict_intruding_vertex_z_min_exact=None if not zs else str(min(zs)),
        strict_intruding_vertex_z_max_exact=None if not zs else str(max(zs)),
        full_original_shaft_subset_of_frozen_outer_refuted=refuted,
        positive_volume_shaft_outside_frozen_outer_proved=refuted,
        vertex_range_is_not_an_exhaustive_violating_face_extent=True,
        geometric_tolerance=None, geometry_modified=False,
        scientific_flags=dict(DENIED_FLAGS))
