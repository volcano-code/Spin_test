"""Recompute saved-material partition and complete original-shaft certificates.

The four input byte digests are mandatory; the shaft additionally has one fixed
historical digest.  No caller-supplied PASS or certificate is accepted.  Every
surface is freshly audited, and only this module's actual surface computations
populate the private cache reused by the full-shaft containment routine.

Partition, outer containment of the original shaft, and positive design/shaft
separation are distinct facts.  A successful design guard may coexist with a
rejected material or shaft-containment gate.  Neither outcome grants native
implicit-set identity, physical equivalence, or W0/W2 scientific admission.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import time

from p16_exact_binary64_chain import NAMES, exact_ten
from p17_boundary_certificate import certify_triangle_chain, read_binary64_obj
from p18_solid_domain import (
    classify_point, exact_signed_volume, fixed_component_correspondence,
    fraction_json, radial_ball_clearance,
)
from p19_guard_certificate import (
    ORIGINAL_SHAFT_SHA256, audit_radial_shaft_guard,
)
from p19_shaft_containment import audit_full_shaft_containment, verify_surface


CAVITY_CENTER = (Fraction(0), Fraction(0), Fraction.from_float(.67))
SCIENTIFIC_FLAGS = {
    'native_Cherchi_implicit_region_partition_certified': False,
    'raw_native_export_vs_repaired_set_equality_certified': False,
    'original_author_CAD_certified': False,
    'physical_equivalence_certified': False,
    'W0_physical_tip_or_FD_approved': False,
    'W2_teacher_training_allowed': False,
    'printability_or_strength_certified': False,
    'Faster_optimization_executed': False,
    'MuJoCo_real_optimized_before_after_executed': False,
}


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _validate_expected(expected, names):
    if type(expected) is not dict or set(expected) != set(names):
        raise ValueError('P19_MATERIAL_EXACT_INPUT_HASH_KEY_SET_REQUIRED')
    if any(type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None
           for value in expected.values()):
        raise ValueError('P19_MATERIAL_INVALID_EXPECTED_SHA256')


def _check_hashes(paths, expected, *, after=False):
    result = {name: _sha256(path) for name, path in paths.items()}
    for name, digest in result.items():
        if digest != expected[name]:
            prefix = ('P19_MATERIAL_INPUT_CHANGED_DURING_AUDIT_' if after else
                      'P19_MATERIAL_INPUT_SHA256_MISMATCH_')
            raise ValueError(prefix + name)
    return result


def _read_inputs(paths, expected):
    """Identity errors raise; malformed geometry remains a rejected diagnostic."""
    meshes, errors = {}, {}
    for name, path in paths.items():
        try:
            mesh = read_binary64_obj(path)
        except ValueError as error:
            meshes[name] = None
            errors[name] = str(error)
            continue
        if mesh.sha256 != expected[name]:
            raise ValueError('P19_MATERIAL_INPUT_CHANGED_DURING_REREAD_' + name)
        meshes[name] = mesh
    return meshes, errors


def _fresh_surfaces(paths, expected):
    reports = {}
    for name, path in paths.items():
        try:
            # verify_surface executes P18 now; it never accepts an outside dict.
            reports[name] = verify_surface(path, expected[name])
        except ValueError as error:
            # A malformed or degenerate OBJ is not an admissible surface. The
            # final all-input hash check still catches concurrent byte changes.
            reports[name] = {
                'status': 'EXACT_SURFACE_REJECTED_DURING_INPUT_VALIDATION',
                'input': {'sha256': expected[name]},
                'frozen_sha256_checked': True,
                'exact_embedded_closed_oriented_2manifold': False,
                'audit_error': str(error),
            }
    return reports


def _inputs_metadata(meshes, expected, errors):
    return {name: {
        'sha256': expected[name],
        'vertices': None if mesh is None else len(mesh.vertices),
        'faces': None if mesh is None else len(mesh.faces),
        'strict_binary64_triangle_parse_passed': mesh is not None,
        'input_geometry_error': errors.get(name),
    } for name, mesh in meshes.items()}


def _empty_partition(reason):
    return {
        'partition_geometry_valid': False,
        'design_strictly_inside_outer': False,
        'fixed_and_design_union_equals_outer': False,
        'fixed_and_design_interiors_disjoint': False,
        'M_and_D_single_embedded_outward_solids': False,
        'all_material_surfaces_exact_embedded_closed_oriented': False,
        'stop_reason': reason,
        'exact_ten_moment_partition': {
            'executed': False, 'all_ten_residuals_zero': False,
            'alone_is_not_region_partition_certificate': True,
        },
        'exact_signed_boundary_chain': {
            'executed': False, 'exact_signed_triangle_chain_zero': False,
        },
        'fixed_component_correspondence': {
            'executed': False, 'exact_outer_and_reversed_cavity_components': False,
        },
        'cavity_ball_and_clearance_certificate': {
            'executed': False, 'positive_gap_proved': False,
        },
        'center_in_outer': {'classification': 'NOT_CERTIFIED'},
    }


def _partition_from_recomputed_inputs(meshes, surfaces):
    """Private evaluator: only callers above provide freshly computed evidence."""
    if any(meshes[name] is None for name in ('M', 'F', 'D')):
        return _empty_partition('ONE_OR_MORE_MATERIAL_OBJS_FAILED_STRICT_VALIDATION')
    selected = {name: meshes[name] for name in ('M', 'F', 'D')}
    volumes = {name: exact_signed_volume(mesh) for name, mesh in selected.items()}
    # P16's independent tetrahedral integration rereads the exact binary64
    # values represented by Fraction. This roundtrip cannot round a new value.
    raw = {}
    for name, mesh in selected.items():
        vertices = tuple(tuple(float(x) for x in point) for point in mesh.vertices)
        if any(Fraction.from_float(x) != q for p, v in zip(mesh.vertices, vertices)
               for q, x in zip(p, v)):
            raise AssertionError('SAVED_BINARY64_COORDINATE_ROUNDTRIP_CHANGED')
        raw[name] = exact_ten(vertices, mesh.faces)
    residual = tuple(a-b-c for a, b, c in zip(raw['M'], raw['F'], raw['D']))
    volume_consistency = all(raw[name][0] == volumes[name] for name in selected)
    if not volume_consistency:
        raise AssertionError('INDEPENDENT_EXACT_VOLUME_AND_TEN_MOMENT_DISAGREE')
    moments = {
        'executed': True,
        'moment_order': list(NAMES),
        'cross_moment_convention': 'ORDINARY_UNDOUBLED',
        'raw_ten_exact': {name: {key: fraction_json(value) for key, value in zip(NAMES, values)}
                          for name, values in raw.items()},
        'M_minus_F_minus_D_exact': {key: fraction_json(value) for key, value in zip(NAMES, residual)},
        'all_ten_residuals_zero': not any(residual),
        'volume_residual_zero': residual[0] == 0,
        'independent_exact_volumes_match_ten_mass_components': volume_consistency,
        'alone_is_not_region_partition_certificate': True,
    }
    chain = certify_triangle_chain(((selected['M'], 1), (selected['F'], -1), (selected['D'], -1)))
    correspondence = fixed_component_correspondence(selected['M'], selected['F'], selected['D'])
    valid = {name: surfaces[name]['exact_embedded_closed_oriented_2manifold'] is True
             for name in selected}
    solids = {name: (valid[name] and surfaces[name]['topology']['surface_components'] == 1
                     and volumes[name] > 0) for name in ('M', 'D')}
    # The point test chooses the inside component of the entire connected ball;
    # it does not substitute for the exhaustive boundary-distance computation.
    if solids['M']:
        center = classify_point(selected['M'], CAVITY_CENTER)
    else:
        center = {'classification': 'NOT_CERTIFIED',
                  'reason': 'OUTER_NOT_AN_EMBEDDED_CONNECTED_OUTWARD_SOLID'}
    clearance = radial_ball_clearance(selected['M'], selected['D'], CAVITY_CENTER)
    contained = (all(solids.values()) and center['classification'] == 'INSIDE'
                 and clearance['positive_gap_proved'] is True)
    partition = (all(valid.values()) and contained
                 and correspondence['exact_outer_and_reversed_cavity_components'] is True
                 and chain['exact_signed_triangle_chain_zero'] is True
                 and moments['all_ten_residuals_zero'] is True
                 and volumes['M'] == volumes['F'] + volumes['D'] and volumes['F'] > 0)
    return {
        'partition_geometry_valid': partition,
        'design_strictly_inside_outer': contained,
        'fixed_and_design_union_equals_outer': partition,
        'fixed_and_design_interiors_disjoint': partition,
        'all_material_surfaces_exact_embedded_closed_oriented': all(valid.values()),
        'M_and_D_single_embedded_outward_solids': all(solids.values()),
        'individual_single_embedded_outward_solids': solids,
        'exact_signed_volumes': {name: fraction_json(value) for name, value in volumes.items()},
        'exact_ten_moment_partition': moments,
        'exact_signed_boundary_chain': chain,
        'fixed_component_correspondence': correspondence,
        'center_in_outer': center,
        'cavity_ball_and_clearance_certificate': clearance,
        'set_semantics': (('CERTIFIED: ' if partition else 'NOT_ESTABLISHED; required relation: ')
                          + 'M=F union D; int(F) intersect int(D) is empty; F and D share the cavity boundary'),
        'containment_proof': (
            'CERTIFIED: The convex enclosing ball contains the entire bounded D solid; '
            'its radius is strictly below the exact distance from the inside center '
            'to every M boundary triangle, so the entire D solid is strictly in M.'
            if contained else
            'NOT_ESTABLISHED: Whole D-in-M containment requires valid bounded embedded outward solids, '
            'the center INSIDE M, and positive exhaustive boundary-to-enclosing-ball clearance; '
            'one or more prerequisites failed.'),
        'literal_component_requirement_is_sufficient_not_necessary': True,
    }


def _common_fields():
    return {
        'arithmetic': 'EXACT_RATIONALS_OF_SAVED_BINARY64_COORDINATES',
        'cavity_center_exact': [str(x) for x in CAVITY_CENTER],
        'cavity_center_convention': 'EXACT_BINARY64_0_67_NOT_DECIMAL_67_OVER_100',
        'geometry_modified': False,
        'geometric_tolerance': None,
        'external_PASS_or_surface_certificate_accepted': False,
        'scientific_approval': False,
        'physical_approval': False,
        'optimization_admitted': False,
        'training_admitted': False,
        'scientific_flags': dict(SCIENTIFIC_FLAGS),
        'proof_scope': 'Saved binary64 regular solids only; raw/native/repaired physical equivalence and external admission are not certified.',
    }


def audit_partition_geometry(M, F, D, expected_sha256):
    """Low-level, freshly recomputed M/F/D proof; grants no shaft geometry gate.

    This helper permits small independent fixtures. It has no shaft input or
    permission to certify the original shaft. The production audit_material
    below always enforces the fixed original-shaft digest.
    """
    started = time.perf_counter()
    paths = dict(M=M, F=F, D=D)
    _validate_expected(expected_sha256, paths)
    _check_hashes(paths, expected_sha256)
    meshes, errors = _read_inputs(paths, expected_sha256)
    surfaces = _fresh_surfaces(paths, expected_sha256)
    partition = _partition_from_recomputed_inputs(meshes, surfaces)
    after = _check_hashes(paths, expected_sha256, after=True)
    return {
        'schema': 'W4P19RecomputedSavedMaterialPartitionV1',
        'status': ('EXACT_SAVED_MATERIAL_PARTITION_PASS_SHAFT_NOT_EVALUATED' if partition['partition_geometry_valid']
                   else 'SAVED_MATERIAL_PARTITION_NOT_CERTIFIED'),
        **_common_fields(), **partition,
        'inputs': _inputs_metadata(meshes, expected_sha256, errors),
        'exact_surface_audits': surfaces,
        'all_surfaces_freshly_recomputed_here': True,
        'input_sha256_checked_before_and_after': True,
        'after_input_sha256': after,
        'full_original_shaft_contained_in_outer': False,
        'design_shaft_separation_certified': False,
        'complete_original_shaft_in_fixed': False,
        'research_geometry_gate_passed': False,
        'shaft_evaluated': False,
        'audit_elapsed_seconds': time.perf_counter() - started,
    }


def audit_material(M, F, D, S, expected_sha256):
    """Audit all four fixed-byte geometries without accepting external proofs.

    Invalid geometric candidates produce explicit partial/rejected reports.
    Wrong identities, changed files, or inconsistent predicate computations
    raise: they cannot be interpreted as a report about the requested inputs.
    """
    started = time.perf_counter()
    paths = dict(M=M, F=F, D=D, S=S)
    _validate_expected(expected_sha256, paths)
    if expected_sha256['S'] != ORIGINAL_SHAFT_SHA256:
        raise ValueError('P19_MATERIAL_ORIGINAL_SHAFT_IDENTITY_CHANGED')
    _check_hashes(paths, expected_sha256)
    meshes, errors = _read_inputs(paths, expected_sha256)
    surfaces = _fresh_surfaces(paths, expected_sha256)
    partition = _partition_from_recomputed_inputs(meshes, surfaces)
    if meshes['M'] is not None and meshes['S'] is not None:
        shaft_containment = audit_full_shaft_containment(M, S,
            expected_sha256={'material': expected_sha256['M'], 'shaft': expected_sha256['S']},
            reuse_verified_surfaces=True)
    else:
        shaft_containment = {
            'status': 'WHOLE_SHAFT_CONTAINMENT_NOT_CERTIFIED',
            'full_original_shaft_contained_in_material': False,
            'stop_reason': 'OUTER_OR_SHAFT_FAILED_STRICT_OBJ_VALIDATION',
            'executed': False,
        }
    if meshes['D'] is not None and meshes['S'] is not None:
        shaft_guard = audit_radial_shaft_guard(D, S,
            expected_sha256={'design': expected_sha256['D'], 'shaft': expected_sha256['S']},
            design_surface_certificate=surfaces['D'], shaft_surface_certificate=surfaces['S'])
    else:
        shaft_guard = {
            'status': 'EXACT_COMPLETE_SHAFT_DESIGN_GAP_NOT_CERTIFIED',
            'positive_full_solid_distance_certified': False,
            'full_original_shaft_disjoint_from_design': False,
            'stop_reason': 'DESIGN_OR_SHAFT_FAILED_STRICT_OBJ_VALIDATION',
            'executed': False,
        }
    shaft_in_outer = shaft_containment['full_original_shaft_contained_in_material'] is True
    separated = (shaft_guard['positive_full_solid_distance_certified'] is True
                 and shaft_guard['full_original_shaft_disjoint_from_design'] is True)
    complete = partition['partition_geometry_valid'] and shaft_in_outer and separated
    if complete:
        status = 'EXACT_SAVED_MATERIAL_AND_COMPLETE_SHAFT_GEOMETRY_PASS_NOT_ADMITTED'
    elif separated and not shaft_in_outer:
        status = 'PARTIAL_GUARD_PASS_SHAFT_CONTAINMENT_REJECTED'
    elif separated:
        status = 'PARTIAL_GUARD_PASS_MATERIAL_PARTITION_REJECTED'
    elif partition['partition_geometry_valid']:
        status = 'PARTIAL_PARTITION_PASS_SHAFT_PROTECTION_REJECTED'
    else:
        status = 'SAVED_MATERIAL_RESEARCH_GEOMETRY_NOT_CERTIFIED'
    after = _check_hashes(paths, expected_sha256, after=True)
    return {
        'schema': 'W4P19RecomputedCompleteMaterialGeometryV1',
        'status': status,
        **_common_fields(), **partition,
        'inputs': _inputs_metadata(meshes, expected_sha256, errors),
        'exact_surface_audits': surfaces,
        'all_surfaces_freshly_recomputed_here': True,
        'input_sha256_checked_before_and_after': True,
        'after_input_sha256': after,
        'original_shaft_identity_enforced': True,
        'whole_shaft_containment': shaft_containment,
        'whole_shaft_design_gap': shaft_guard,
        'whole_shaft_design_gap_local_flag_scope': {
            'flag': 'scientific_flags.full_original_shaft_contained_in_fixed_material',
            'meaning': 'False in the standalone gap certificate means that certificate does not evaluate F or whole S-in-F containment.',
            'not_a_negative_whole_material_containment_result': True,
            'whole_material_conclusion_field': 'complete_original_shaft_in_fixed',
        },
        'full_original_shaft_contained_in_outer': shaft_in_outer,
        'design_shaft_separation_certified': separated,
        'complete_original_shaft_in_fixed': complete,
        'research_geometry_gate_passed': complete,
        'complete_shaft_proof': (
            'CERTIFIED: The regular partition is F=closure(M\\D); the complete original S is contained '
            'in M and has the registered strict positive distance from D, hence every point of S is in F.'
            if complete else
            'NOT_ESTABLISHED: Complete S-in-F requires all three independent facts: a valid M/F/D regular '
            'partition, whole original S contained in M, and the registered positive S-to-D distance. '
            'At least one fact is not certified; the individual gate fields retain the actual results.'),
        'shaft_evaluated': True,
        'audit_elapsed_seconds': time.perf_counter() - started,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outer', required=True)
    parser.add_argument('--fixed', required=True)
    parser.add_argument('--design', required=True)
    parser.add_argument('--shaft', required=True)
    parser.add_argument('--expected-sha256-json', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    target = Path(args.output)
    if target.exists():
        raise FileExistsError('P19_PRESERVE_EXISTING_MATERIAL_AUDIT')
    expected = json.loads(Path(args.expected_sha256_json).read_text())
    report = audit_material(args.outer, args.fixed, args.design, args.shaft, expected)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(json.dumps({key: report[key] for key in ('status', 'partition_geometry_valid',
        'full_original_shaft_contained_in_outer', 'design_shaft_separation_certified',
        'complete_original_shaft_in_fixed', 'research_geometry_gate_passed',
        'optimization_admitted')}, indent=2))
    return 0 if report['research_geometry_gate_passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
