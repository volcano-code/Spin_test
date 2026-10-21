"""Frozen P19 packet, full evidence replay, and genuine Cherchi reconstruction.

The selected candidate is a fresh, unmodified-reference native construction.
Its saved binary64 solid proof does not certify native implicit point equality,
original author CAD, a physical material, teacher admission, or optimization.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import tempfile

from p17_boundary_certificate import read_binary64_obj, signed_triangle_key
from p17_material_candidate import physical_reports_equal, typed_exact_equal
from p17_physical_case import analyze_obj, build_physical_proposal, p13_case_config
from p18_solid_domain import _without_timings, fraction_json, sqrt_bounds
from p19_guard_construction import digest, native_call, write_dyadic_prism, write_new_json
from p19_material_audit import audit_material


MANIFEST_SHA256 = 'c6bd67f872f344da46c1f774f8b68c28a2ecfa4c5a5c000d9e6bf5229e3412d6'
P17_MANIFEST_SHA256 = '3eef5e245590ebee18ea46e1f0198c81d73c17ffbbb064143a6ceb95a00d5a70'
P18_COMMIT = 'b33fc93bd1fecd5b42fbd8d2eabfefd6ec9db7be'
SUCCESS = 'P19_EXACT_SAVED_SOLID_AND_COMPLETE_ORIGINAL_SHAFT_PASS_NOT_ADMITTED'
P1 = Path(__file__).resolve().parent
OLD_DEPENDENCIES = (
    'p7_cherchi_native_union.py', 'p7_cherchi_reference_cli/CMakeLists.txt',
    'p15_inherited_sliver_repair.py',
    'p16_exact_binary64_chain.py', 'p17_boundary_certificate.py',
    'p17_material_candidate.py', 'p17_physical_case.py',
    'p18_exact_surface.py', 'p18_shaft_domain.py', 'p18_solid_domain.py',
)


def validate_packet(packet):
    """Authenticate the external frozen manifest, all operands and receipts."""
    packet = Path(packet).absolute()
    if packet.is_symlink():
        raise ValueError('P19_PACKET_ROOT_SYMLINK_NOT_SELF_CONTAINED')
    packet = packet.resolve()
    if (packet / 'manifest.json').is_symlink():
        raise ValueError('P19_MANIFEST_SYMLINK_NOT_SELF_CONTAINED')
    if digest(packet / 'manifest.json') != MANIFEST_SHA256:
        raise ValueError('P19_EXTERNAL_FROZEN_MANIFEST_MISMATCH')
    manifest = json.loads((packet / 'manifest.json').read_text())
    expected_files = {'manifest.json', *manifest['files_sha256']}
    entries = list(packet.rglob('*'))
    if any(path.is_symlink() for path in entries):
        raise ValueError('P19_PACKET_SYMLINK_NOT_SELF_CONTAINED')
    if {str(path.relative_to(packet)) for path in entries if path.is_file()} != expected_files:
        raise ValueError('P19_PACKET_UNAUTHENTICATED_OR_MISSING_FILE')
    for rel, expected in manifest['files_sha256'].items():
        path = packet / rel
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            raise ValueError('P19_FROZEN_FILE_MISMATCH_' + rel)
    for name, op, operands in (
        ('M', 'union', ['source/body-reference.obj', 'inputs/shaft-envelope.obj']),
        ('D', 'subtraction', ['source/cavity-reference.obj', 'inputs/inner_guard.obj']),
        ('F', 'subtraction', ['material/M_native.obj', 'material/D_native.obj']),
    ):
        rec = json.loads((packet / 'receipts' / (name + '_native.obj.native.json')).read_text())
        expected_output = manifest['files_sha256'][manifest['material_files'][name]]
        if (rec['operation'] != op or type(rec['returncode']) is not int or rec['returncode'] != 0
                or rec['input_sha256'] != [manifest['files_sha256'][p] for p in operands]
                or rec['output_sha256'] != expected_output
                or rec['binary_sha256'] != manifest['historical_creation_binary_sha256']
                or any(rec.get(k) is not True for k in
                       ('inputs_unchanged', 'binary_unchanged', 'output_exists', 'new_native_process_launched'))):
            raise ValueError('P19_ACTUAL_NATIVE_RECEIPT_MISMATCH_' + name)
    if any(v is not False for v in manifest['scientific_flags'].values()):
        raise ValueError('P19_PREMATURE_SCIENTIFIC_APPROVAL')
    return manifest


def regenerate_guards(packet, output):
    """Reproduce exact frozen coordinates from the registered normative rule."""
    packet, output = Path(packet), Path(output)
    manifest = validate_packet(packet)
    output.mkdir(parents=True, exist_ok=False)
    shaft = read_binary64_obj(packet / 'source/shaft-reference.obj')
    plan = manifest['construction']['shaft_envelope']
    co = Fraction.from_float(float.fromhex(plan['cosine_binary64_hex']))
    si = Fraction.from_float(float.fromhex(plan['sine_binary64_hex']))
    radial = Fraction(plan['radial_scale_exact'])
    points = [(float(radial * (co*x-si*y)), float(radial * (si*x+co*y)), float(z))
              for x, y, z in shaft.vertices]
    path = output / 'shaft-envelope.obj'
    with path.open('x', encoding='ascii', newline='\n') as stream:
        stream.write('# P19 TIP-PRESERVING EXACT-AFFINE-THEN-BINARY64 SHAFT ENVELOPE PROPOSAL\n')
        for point in points:
            stream.write('v ' + ' '.join(format(c, '.17g') for c in point) + '\n')
        for face in shaft.faces:
            stream.write('f ' + ' '.join(str(i+1) for i in face) + '\n')
    write_dyadic_prism(output / 'inner_guard.obj',
        [['-1/16','-1/16'], ['1/16','-1/16'], ['1/16','1/16'], ['-1/16','1/16']],
        '3/8', '1')
    for name in ('shaft-envelope.obj', 'inner_guard.obj'):
        if digest(output / name) != manifest['files_sha256']['inputs/' + name]:
            raise ValueError('P19_REGISTERED_GUARD_BYTES_NOT_REPRODUCED_' + name)
    validate_packet(packet)
    return {name: digest(output / name) for name in ('shaft-envelope.obj', 'inner_guard.obj')}


def source_identities():
    files = set(OLD_DEPENDENCIES)
    files.add('P19_TEST_INVENTORY.json')
    files.update(p.name for p in P1.glob('p19*.py'))
    files.update(p.name for p in P1.glob('test_p19*.py'))
    return {name: digest(P1 / name) for name in sorted(files)}


def compare_saved_geometry(reference_path, actual_path):
    """Exact oriented-facet AND vertex multisets; only ordering/text may vary.

The orientation is part of each Counter key, never an algebraic coefficient:
an extra positive/negative pair cannot cancel. Unused or duplicated vertices
also cannot disappear from the vertex Counter. No tolerance or rewriting.
"""
    reference, actual = read_binary64_obj(reference_path), read_binary64_obj(actual_path)
    def triangles(mesh):
        return Counter(signed_triangle_key(tuple(mesh.vertices[i] for i in face))
                       for face in mesh.faces)
    vertices_equal = Counter(reference.vertices) == Counter(actual.vertices)
    triangles_equal = triangles(reference) == triangles(actual)
    return {
        'schema': 'W4P19ExactSavedOrientedMultisetComparisonV1',
        'reference_sha256': reference.sha256, 'actual_sha256': actual.sha256,
        'raw_bytes_equal': reference.sha256 == actual.sha256,
        'exact_vertex_multisets_equal': vertices_equal,
        'exact_oriented_triangle_multisets_equal': triangles_equal,
        'exact_saved_geometry_equal': vertices_equal and triangles_equal,
        'reference_vertices': len(reference.vertices), 'actual_vertices': len(actual.vertices),
        'reference_faces': len(reference.faces), 'actual_faces': len(actual.faces),
        'algebraic_face_cancellation_allowed': False,
        'coordinate_tolerance': None, 'mesh_rewritten': False,
        'allowed_difference': 'Only indexing, face order, cyclic face rotations, or numerically identical text',
    }


def geometry_change_and_physical_proposal(packet, previous_packet, manifest):
    packet, previous_packet = Path(packet), Path(previous_packet)
    if digest(previous_packet / 'manifest.json') != P17_MANIFEST_SHA256:
        raise ValueError('P19_PREVIOUS_PACKET_EXTERNAL_MANIFEST_MISMATCH')
    paths = {k: packet / rel for k, rel in manifest['material_files'].items()}
    expected = {k: manifest['files_sha256'][rel] for k, rel in manifest['material_files'].items()}
    physical = build_physical_proposal(paths, case_config=p13_case_config(), expected_sha256=expected)
    old_files = {
        'M': ('material/M_repaired_outer.obj', '4c2e4d480d1041f4817128a8b4b61675d80a699e448e7a5a253311c1805a3aa2'),
        'F': ('material/F_repaired_fixed_trial.obj', '47c08ee597d5666069416985e0dc8900d204481c590b73596f90daccd2b068d1'),
        'D': ('material/D_native_carveable_trial.obj', '1d4a0673e9297d95adfb5722158ba1d859a83099046d01116a2b363cb3cb386b'),
    }
    old = {k: analyze_obj(previous_packet / rel, scale_m_per_unit=.025, density_kg_m3=1200.,
                         expected_sha256=sha) for k, (rel, sha) in old_files.items()}
    changes = {}
    for name in ('M', 'F', 'D'):
        before, after = old[name], physical['materials'][name]
        a, b = before['source_raw_ten_exact'][0], after['source_raw_ten_exact'][0]
        old_volume, new_volume = (Fraction(int(v['numerator']), int(v['denominator'])) for v in (a, b))
        changes[name] = {
            'old_sha256': before['source_obj_sha256'], 'new_sha256': after['source_obj_sha256'],
            'old_volume_reference': fraction_json(old_volume),
            'new_volume_reference': fraction_json(new_volume),
            'volume_change_reference': fraction_json(new_volume-old_volume),
            'relative_volume_change': fraction_json((new_volume-old_volume)/old_volume),
            'old_mass_kg_proposed': before['mass_kg'], 'new_mass_kg_proposed': after['mass_kg'],
            'old_com_m_proposed': before['center_of_mass_m'], 'new_com_m_proposed': after['center_of_mass_m'],
            'old_faces': before['triangle_count'], 'new_faces': after['triangle_count'],
            'old_bounds_m': before['bounds_m'], 'new_bounds_m': after['bounds_m'],
        }
    S = read_binary64_obj(paths['S'])
    E = read_binary64_obj(packet / 'inputs/shaft-envelope.obj')
    M = read_binary64_obj(paths['M'])
    if S.faces != E.faces or len(S.vertices) != len(E.vertices):
        raise ValueError('P19_SHAFT_ENVELOPE_INDEX_CORRESPONDENCE_CHANGED')
    z_equal = all(a[2] == b[2] for a, b in zip(S.vertices, E.vertices))
    zero = (Fraction(0),) * 3
    if not z_equal or zero not in S.vertices or zero not in E.vertices or zero not in M.vertices:
        raise ValueError('P19_ORIGINAL_TIP_OR_HEIGHT_CHANGED')
    if min(p[2] for p in M.vertices) != 0 or max(p[2] for p in M.vertices) != max(p[2] for p in S.vertices):
        raise ValueError('P19_OUTER_VERTICAL_BOUNDS_CHANGED')
    squared_moves = [sum((a[i]-b[i])**2 for i in range(3)) for a, b in zip(S.vertices, E.vertices)]
    max_move = max(squared_moves)
    _, move_upper = sqrt_bounds(max_move, 10**12)
    _, envelope_radius_upper = sqrt_bounds(max(p[0]**2+p[1]**2 for p in E.vertices), 10**12)
    _, shaft_radius_upper = sqrt_bounds(max(p[0]**2+p[1]**2 for p in S.vertices), 10**12)
    if (digest(previous_packet / 'manifest.json') != P17_MANIFEST_SHA256 or
            any(digest(previous_packet / rel) != sha for rel, sha in old_files.values())):
        raise ValueError('P19_PREVIOUS_PACKET_CHANGED_DURING_COMPARISON')
    return {
        'physical_proposal': physical,
        'candidate_intentionally_differs_from_P18': True,
        'changes_from_P18_saved_materials': changes,
        'original_shaft_bytes_preserved': True,
        'original_tip_and_axis_preserved': True,
        'all_original_shaft_envelope_z_coordinates_preserved': z_equal,
        'tip_reference': [0., 0., 0.], 'axis_reference': [0., 0., 1.],
        'original_top_z_exact': str(max(p[2] for p in S.vertices)),
        'envelope_vertex_correspondence_max_displacement_squared': fraction_json(max_move),
        'envelope_vertex_correspondence_max_displacement_upper_reference': fraction_json(move_upper),
        'envelope_radius_upper_reference': fraction_json(envelope_radius_upper),
        'original_shaft_radius_upper_reference': fraction_json(shaft_radius_upper),
        'displacement_bound_is_not_outer_M_Hausdorff_or_native_implicit_error_bound': True,
        'geometry_change_is_not_mass_optimization': True,
        'physical_model_and_material_not_experimentally_validated': True,
    }


def audit_packet(packet, previous_packet=None):
    packet = Path(packet).absolute()
    previous_packet = Path(previous_packet or P1 / 'P17_material_case').resolve()
    manifest = validate_packet(packet)
    code_before = source_identities()
    with tempfile.TemporaryDirectory() as temp:
        regenerated = regenerate_guards(packet, Path(temp) / 'guards')
    paths = {k: packet / rel for k, rel in manifest['material_files'].items()}
    expected = {k: manifest['files_sha256'][rel] for k, rel in manifest['material_files'].items()}
    geometry = audit_material(paths['M'], paths['F'], paths['D'], paths['S'], expected)
    changes = geometry_change_and_physical_proposal(packet, previous_packet, manifest)
    validate_packet(packet)
    if code_before != source_identities():
        raise ValueError('P19_AUDIT_CODE_CHANGED_DURING_EXECUTION')
    return {
        'schema': 'W4P19FrozenNativeCandidateCompleteSavedGeometryV1',
        'status': SUCCESS if geometry['research_geometry_gate_passed'] else 'P19_FROZEN_CANDIDATE_REJECTED',
        'source_P18_commit': P18_COMMIT,
        'frozen_manifest_sha256': MANIFEST_SHA256,
        'source_code_and_test_sha256': code_before,
        'native_construction': {
            'classification': manifest['classification'],
            'upstream_commit': manifest['upstream_Cherchi_commit'],
            'historical_binary_sha256': manifest['historical_creation_binary_sha256'],
            'actual_selected_construction_calls': 3,
            'new_native_calls_in_this_saved_packet_audit': 0,
            'selected_outputs_modified_after_native_save': False,
            'APAP_exporter_used_for_selected_materials': False,
            'CGAL_used': False,
            'receipts_authenticated': True,
            'registered_guard_bytes_regenerated': regenerated,
            'implicit_rational_coordinate_equality_certified': False,
        },
        'geometry': geometry,
        **changes,
        'scientific_flags': dict(manifest['scientific_flags']),
        'optimization_admitted': False, 'training_admitted': False,
    }


def verify_report(packet, report_path, previous_packet=None):
    claimed = json.loads(Path(report_path).read_text())
    actual = audit_packet(packet, previous_packet)
    claimed, actual = _without_timings(claimed), _without_timings(actual)
    if type(claimed) is not dict or set(claimed) != set(actual):
        raise ValueError('P19_FROZEN_REPORT_RECOMPUTATION_MISMATCH')
    try:
        physical_equal = physical_reports_equal(claimed.pop('physical_proposal'),
                                                 actual.pop('physical_proposal'))
    except (KeyError, TypeError, AttributeError):
        physical_equal = False
    if not physical_equal or not typed_exact_equal(claimed, actual):
        raise ValueError('P19_FROZEN_REPORT_RECOMPUTATION_MISMATCH')
    return {'status': 'P19_COMPLETE_REPORT_RECOMPUTED_AND_VALIDATED',
            'report_status': actual['status'], 'optimization_admitted': False,
            'only_ignored_fields': ['elapsed_seconds', 'audit_elapsed_seconds'],
            'only_numerically_compared_fields': 'physical_proposal principal_inertia_kg_m2 only',
            'principal_inertia_display_relative_tolerance': 1e-12,
            'all_exact_moments_and_full_inertia_tensors_compared_exactly': True}


def rebuild_native(packet, binary, source, output):
    """Run three new Cherchi calls, compare exact facets, and audit actual bytes."""
    from p19_native_smoke import validate_native_identity
    packet = Path(packet).absolute()
    binary, source, output = map(lambda p: Path(p).resolve(), (binary, source, output))
    manifest = validate_packet(packet)
    identity = validate_native_identity(binary, source, mode='unmodified')
    output.mkdir(parents=True, exist_ok=False)
    plan = {'schema': 'W4P19SelectedThreeOperationNativeRebuildPlanV1',
            'frozen_manifest_sha256': MANIFEST_SHA256, 'binary_sha256': digest(binary),
            'native_identity': identity, 'all_calls_serial': True,
            'operations': [['union', 'body-reference.obj', 'shaft-envelope.obj', 'M.obj'],
                           ['subtraction', 'cavity-reference.obj', 'inner_guard.obj', 'D.obj'],
                           ['subtraction', 'M.obj', 'D.obj', 'F.obj']],
            'reconstruction_acceptance': 'EXACT_VERTEX_AND_ORIENTED_TRIANGLE_MULTISET_EQUALITY',
            'raw_byte_equality_reported_separately': True,
            'coordinate_tolerance': None, 'face_cancellation_allowed': False,
            'saved_output_postprocess_allowed': False, 'scientific_admission': False}
    write_new_json(output / 'registered-plan.json', plan)
    regenerate_guards(packet, output / 'guards')
    operations = [
        ('M', 'union', [packet / 'source/body-reference.obj', output / 'guards/shaft-envelope.obj']),
        ('D', 'subtraction', [packet / 'source/cavity-reference.obj', output / 'guards/inner_guard.obj']),
        ('F', 'subtraction', [output / 'M.obj', output / 'D.obj']),
    ]
    pinned = {output / 'registered-plan.json': digest(output / 'registered-plan.json'), binary: digest(binary)}
    pinned.update({output / 'guards' / n: manifest['files_sha256']['inputs/' + n]
                   for n in ('shaft-envelope.obj', 'inner_guard.obj')})
    records, comparisons, actual_hashes = [], {}, {}
    for name, operation, operands in operations:
        validate_packet(packet)
        if any(digest(p) != s for p, s in pinned.items()):
            raise ValueError('P19_NATIVE_REBUILD_PRIOR_BYTES_CHANGED')
        rec = native_call(binary, operation, operands, output / (name + '.obj'))
        records.append(rec)
        write_new_json(output / (name + '-operation-evidence.json'), rec)
        actual_path = output / (name + '.obj')
        if (rec['returncode'] != 0 or not actual_path.is_file()
                or rec.get('output_sha256') != digest(actual_path)
                or rec.get('input_sha256') != [digest(path) for path in operands]):
            raise ValueError('P19_NATIVE_REBUILD_SAVED_OUTPUT_DIFFERS_' + name)
        comparison = compare_saved_geometry(packet / manifest['material_files'][name], actual_path)
        comparisons[name] = comparison
        comparison_path = output / (name + '-exact-geometry-comparison.json')
        write_new_json(comparison_path, comparison)
        if not comparison['exact_saved_geometry_equal']:
            raise ValueError('P19_NATIVE_REBUILD_SAVED_OUTPUT_DIFFERS_' + name)
        actual_hashes[name] = digest(actual_path)
        pinned[actual_path] = actual_hashes[name]
        for path in (Path(str(actual_path) + '.native.json'),
                     output / (name + '-operation-evidence.json'), comparison_path):
            pinned[path] = digest(path)
    hashes = {**actual_hashes, 'S': manifest['files_sha256'][manifest['material_files']['S']]}
    geometry = audit_material(output / 'M.obj', output / 'F.obj', output / 'D.obj',
                              packet / 'source/shaft-reference.obj', hashes)
    validate_packet(packet)
    if any(digest(p) != s for p, s in pinned.items()):
        raise ValueError('P19_NATIVE_REBUILD_OUTPUT_CHANGED_DURING_AUDIT')
    validate_native_identity(binary, source, mode='unmodified')
    report = {'schema': 'W4P19ActualNewThreeCallNativeRebuildV1',
              'status': 'P19_NATIVE_EXACT_SAVED_GEOMETRY_REPRODUCED' if geometry['research_geometry_gate_passed'] else 'P19_NATIVE_REBUILD_REJECTED',
              'native_identity': identity, 'new_native_calls': len(records),
              'operations': records,
              'same_frozen_material_output_bytes': all(row['raw_bytes_equal'] for row in comparisons.values()),
              'exact_saved_oriented_facet_and_vertex_multisets_match': True,
              'exact_geometry_comparisons': comparisons,
              'geometry': geometry, 'postprocess_executed': False,
              'optimization_admitted': False, 'training_admitted': False}
    write_new_json(output / 'native-rebuild-report.json', report)
    if not geometry['research_geometry_gate_passed']:
        raise ValueError('P19_NATIVE_REBUILD_MATERIAL_GEOMETRY_REJECTED')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for action in ('audit', 'verify', 'rebuild'):
        cmd = sub.add_parser(action)
        cmd.add_argument('--packet', type=Path, required=True)
        if action in ('audit', 'verify'):
            cmd.add_argument('--report', type=Path, required=True)
            cmd.add_argument('--previous-packet', type=Path)
        else:
            cmd.add_argument('--native-bin', type=Path, required=True)
            cmd.add_argument('--upstream-checkout', type=Path, required=True)
            cmd.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'verify':
        result = verify_report(args.packet, args.report, args.previous_packet)
    elif args.command == 'rebuild':
        result = rebuild_native(args.packet, args.native_bin, args.upstream_checkout, args.out)
    else:
        if args.report.exists():
            raise FileExistsError('P19_REFUSE_TO_OVERWRITE_AUDIT_REPORT')
        result = audit_packet(args.packet, args.previous_packet)
        write_new_json(args.report, result)
    print(json.dumps({key: result[key] for key in ('status', 'optimization_admitted')}, indent=2))
    return 0 if result.get('status') != 'P19_FROZEN_CANDIDATE_REJECTED' else 2


if __name__ == '__main__':
    raise SystemExit(main())
