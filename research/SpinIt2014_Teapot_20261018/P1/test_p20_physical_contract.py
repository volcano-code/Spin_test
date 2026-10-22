"""Independent exact algebra tests; never invoke Cherchi or a native module."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction as Q
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import unittest

import p20_physical_contract as contract


HERE = Path(__file__).resolve().parent
IDENTITY = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
EXPONENTS = ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1),
             (2, 0, 0), (0, 2, 0), (0, 0, 2), (0, 1, 1), (1, 0, 1), (1, 1, 0))


def analytic_box(lower, upper, density=Q(1)):
    """Independent tensor-product integrals, without triangle/frame helpers."""
    lower, upper, density = tuple(map(Q, lower)), tuple(map(Q, upper)), Q(density)
    result = []
    for exponent in EXPONENTS:
        value = density
        for lo, hi, power in zip(lower, upper, exponent):
            value *= (hi**(power+1)-lo**(power+1))/Q(power+1)
        result.append(value)
    return tuple(result)


def frame_for(origin=(3.0, -2.0, 5.0), length=8.0, density=4.0,
              tip=(1.0, 2.0, 3.0), axes=IDENTITY):
    normalization = dict(origin=list(origin), L=length, R=density,
                         axes=[list(map(float, row)) for row in IDENTITY],
                         authority='IMPLEMENTATION_DEFAULT', frame='INPUT_NORMALIZED_V1')
    target = [(tip[i]-origin[i])/length for i in range(3)]
    return contract.Frame.from_core(normalization, target, axes, requested_tip=tip)


def read_vertices(path):
    result = []
    for line in Path(path).read_text().splitlines():
        tokens = line.split()
        if tokens and tokens[0] == 'v':
            result.append(tuple(float(x) for x in tokens[1:]))
    return result


class ExactMomentTests(unittest.TestCase):
    def test_analytic_translated_noncentral_box_in_SI(self):
        lo, hi, rho = (Q(-2), Q(3), Q(5)), (Q(1), Q(7), Q(9)), Q(1)
        raw = analytic_box(lo, hi, rho)
        s = Q.from_float(0.025)
        direct = analytic_box(tuple(s*x for x in lo), tuple(s*x for x in hi), Q(1200))
        self.assertEqual(contract.raw10_reference_to_si(raw), direct)
        self.assertEqual(contract.raw10_si_to_reference(direct), raw)
        self.assertNotEqual(s, Q(1, 40))
        self.assertEqual(contract.MASS_KG_PER_REFERENCE, 1200*s**3)

    def test_all_ten_translation_terms_against_separate_box_integrals(self):
        lo, hi, shift = (Q(-3), Q(1), Q(4)), (Q(2), Q(6), Q(7)), (Q(5), Q(-2), Q(9))
        raw = analytic_box(lo, hi, Q(7, 3))
        direct = analytic_box(tuple(a+b for a, b in zip(lo, shift)),
                              tuple(a+b for a, b in zip(hi, shift)), Q(7, 3))
        self.assertEqual(contract.affine_raw10(raw, IDENTITY, shift), direct)
        self.assertNotEqual(direct[7:], raw[7:])

    def test_mass_measure_transform_has_no_hidden_volume_or_density_factor(self):
        lo, hi = (Q(1), Q(-2), Q(3)), (Q(4), Q(1), Q(5))
        a, shift = ((2, 0, 0), (0, 3, 0), (0, 0, 4)), (Q(5), Q(-1), Q(7))
        raw = analytic_box(lo, hi, Q(5))
        new_lo = tuple(Q(a[i][i])*lo[i]+shift[i] for i in range(3))
        new_hi = tuple(Q(a[i][i])*hi[i]+shift[i] for i in range(3))
        self.assertEqual(contract.affine_raw10(raw, a, shift), analytic_box(new_lo, new_hi, Q(5, 24)))
        self.assertEqual(contract.affine_raw10(raw, a, shift, mass_scale=24), analytic_box(new_lo, new_hi, Q(5)))

    def test_shear_retains_full_cross_moments(self):
        raw = analytic_box((-1, -1, -1), (1, 1, 1))
        actual = contract.affine_raw10(raw, ((1, 2, 0), (0, 1, 0), (0, 0, 3)), (0, 0, 0))
        self.assertEqual(actual, (Q(8), Q(), Q(), Q(), Q(40, 3), Q(8, 3), Q(24), Q(), Q(), Q(16, 3)))

    def test_density_and_target_axes_against_independent_box(self):
        axes = ((0, -1, 0), (1, 0, 0), (0, 0, 1))
        frame = frame_for(axes=axes)
        lo, hi = (Q(-3), Q(4), Q(11)), (Q(5), Q(10), Q(19))
        original = analytic_box(lo, hi, Q(2))
        # y=(x_y-2)/8, y_y=-(x_x-1)/8, y_z=(x_z-3)/8.
        target = analytic_box(((lo[1]-2)/8, -(hi[0]-1)/8, (lo[2]-3)/8),
                              ((hi[1]-2)/8, -(lo[0]-1)/8, (hi[2]-3)/8), Q(1, 2))
        self.assertEqual(contract.raw10_original_to_target(original, frame), target)
        self.assertEqual(contract.raw10_target_to_original(target, frame), original)

    def test_empty_moments_and_signed_components_preserved(self):
        zero = (Q(),)*10
        frame = frame_for()
        self.assertEqual(contract.raw10_original_to_target(zero, frame), zero)
        self.assertEqual(contract.raw10_target_to_original(zero, frame), zero)
        signed = tuple(-x for x in analytic_box((1, 2, 3), (4, 5, 6)))
        self.assertEqual(contract.raw10_target_to_original(contract.raw10_original_to_target(signed, frame), frame), signed)

    def test_wrong_scale_density_or_historical_transform_rejected(self):
        for key, value in (
                ('proposed_length_m_per_reference', 0.4), ('proposed_density_kg_m3', 1.0),
                ('input_density', 1200.0), ('length_unit', 'm'), ('mass_unit', 'kg'),
                ('tip_reference', [0.0, 0.0, 0.15]), ('spin_axis_reference', [0.0, 1.0, 0.0]),
                ('additional_reference_translation', [0.0, 0.0, 0.15]),
                ('additional_reference_linear', [[0.4, 0.0, 0.0], [0.0, 0.4, 0.0], [0.0, 0.0, 0.4]])):
            with self.subTest(key=key):
                units = contract.unit_contract()
                units[key] = value
                with self.assertRaisesRegex(ValueError, 'UNIT_CONTRACT_CHANGED'):
                    contract.raw10_reference_to_si((1,)*10, units=units)

    def test_boolean_string_nonfinite_and_lossy_core_inputs_rejected(self):
        for bad in (True, '1', float('inf'), float('nan'), {'value': 1}):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    contract.affine_raw10((bad,)+(1,)*9, IDENTITY, (0, 0, 0))
        units = contract.unit_contract()
        units['input_density'] = True
        with self.assertRaises(ValueError):
            contract.validate_unit_contract(units)
        units = contract.unit_contract()
        units['input_density'] = 1
        with self.assertRaises(ValueError):
            contract.validate_unit_contract(units)
        with self.assertRaises(ValueError):
            contract.core_normalization_from_vertices([(0, 0, 0), (2**54+1, 1, 1)])
        with self.assertRaises(ValueError):
            contract.affine_raw10((1,)*10, ((1, 0, 0), (0, 0, 0), (0, 0, 1)), (0, 0, 0))

    def test_fraction_payload_requires_canonical_typed_reduced_integers(self):
        for value in ({'numerator': 1, 'denominator': '2'}, {'numerator': '2', 'denominator': '4'},
                      {'numerator': '+1', 'denominator': '2'}, {'numerator': '01', 'denominator': '2'},
                      {'numerator': '1', 'denominator': '0'}, {'numerator': '1', 'denominator': '-2'},
                      {'numerator': '1', 'denominator': '2', 'float': .5}):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    contract.fraction_from_payload(value)
        self.assertEqual(contract.fraction_from_payload(contract.fraction_payload(Q(-13, 32))), Q(-13, 32))


class FrameAndCoefficientTests(unittest.TestCase):
    def test_actual_binary64_bbox_center_is_not_ideal_rational_average(self):
        norm = contract.core_normalization_from_vertices([(-1.1980000000000002, -.8, 0.0), (1.3736, .8, 1.71)])
        self.assertEqual(norm['L'], 2.5716)
        target_origin = [-x/norm['L'] for x in norm['origin']]
        # Core numpy subtraction uses +0.0 for (0.0 - 0.0), not unary -0.0.
        target_origin = [(0.0-x)/norm['L'] for x in norm['origin']]
        frame = contract.Frame.from_core(norm, target_origin, IDENTITY)
        expected = tuple(Q.from_float(norm['origin'][i])+Q.from_float(norm['L'])*Q.from_float(target_origin[i]) for i in range(3))
        self.assertEqual(frame.represented_tip, expected)
        self.assertNotEqual(frame.represented_tip, (Q(),)*3)
        self.assertEqual(frame.target_point_to_original((0, 0, 0)), expected)
        self.assertEqual(frame.target_point_to_original(frame.original_point_to_target((0, 0, 0))), (Q(),)*3)

    def test_double_target_translation_rejected(self):
        norm = dict(origin=[3.0, -2.0, 5.0], L=8.0, R=1.0,
                    axes=[list(row) for row in IDENTITY], authority='IMPLEMENTATION_DEFAULT', frame='INPUT_NORMALIZED_V1')
        once = [(0.0-x)/8.0 for x in norm['origin']]
        twice = [(once[i]-norm['origin'][i])/8.0 for i in range(3)]
        with self.assertRaisesRegex(ValueError, 'TIP_TRANSFORM_REAPPLIED'):
            contract.Frame.from_core(norm, twice, IDENTITY)
        with self.assertRaisesRegex(ValueError, 'TIP_TRANSFORM_REAPPLIED'):
            contract.Frame.from_core(norm, [0.0, 0.0, 0.0], IDENTITY)

    def test_nonorthogonal_rounded_or_reflected_axes_fail_closed(self):
        for axes in (((1, 1, 0), (0, 1, 0), (0, 0, 1)),
                     ((1, 0, 0), (0, 1, 0), (0, 0, -1)),
                     ((math.sqrt(.5), -math.sqrt(.5), 0), (math.sqrt(.5), math.sqrt(.5), 0), (0, 0, 1))):
            with self.subTest(axes=axes):
                with self.assertRaisesRegex(ValueError, 'EXACT_RIGHT_HANDED_ORTHONORMAL'):
                    frame_for(axes=axes)

    def test_actual_matrix_entry_cross_basis_and_raw_cross_moments(self):
        p = tuple(Q(i) for i in range(1, 11))
        point = (Q(2), Q(3), Q(5))
        x, y, z = point
        expected = 1+2*x+3*y+4*z+5*x*x+6*y*y+7*z*z+16*y*z+18*x*z+20*x*y
        self.assertEqual(contract.evaluate_quadric(p, point), expected)
        literal = contract.convert_coefficients(p, from_basis=contract.NATIVE_BASIS, to_basis=contract.LITERAL_BASIS)
        self.assertEqual(literal[7:], (Q(16), Q(18), Q(20)))
        self.assertEqual(contract.evaluate_quadric(literal, point, basis=contract.LITERAL_BASIS), expected)
        self.assertEqual(contract.convert_coefficients(literal, from_basis=contract.LITERAL_BASIS, to_basis=contract.NATIVE_BASIS), p)
        h = contract.coefficients_to_homogeneous(p)
        self.assertEqual(h[0][1], Q(10))
        self.assertEqual(h[0][3], Q(1))
        self.assertEqual(contract.homogeneous_to_coefficients(h), p)
        raw = analytic_box((1, 2, 3), (4, 5, 6))
        self.assertNotEqual(sum(a*b for a, b in zip(p, raw)), sum(a*b for a, b in zip(literal, raw)))

    def test_noncentral_quadric_exact_pullback_and_inverse(self):
        frame = frame_for(axes=((0, -1, 0), (1, 0, 0), (0, 0, 1)))
        p = (Q(2, 7), Q(-3), Q(5), Q(11), Q(1), Q(2), Q(3), Q(4), Q(5), Q(6))
        target = contract.quadric_original_to_target(p, frame)
        self.assertEqual(contract.quadric_target_to_original(target, frame), p)
        for point in ((Q(7), Q(-2), Q(8)), (Q(1, 3), Q(2, 5), Q(-7, 11)), (Q(), Q(), Q())):
            self.assertEqual(contract.evaluate_quadric(p, point),
                             contract.evaluate_quadric(target, frame.original_point_to_target(point)))
        asymmetric = [list(row) for row in contract.coefficients_to_homogeneous(p)]
        asymmetric[0][1] += 1
        with self.assertRaises(ValueError):
            contract.homogeneous_to_coefficients(asymmetric)

    def test_positive_scale_is_not_coefficient_or_J_identity(self):
        p = (Q(-1), Q(), Q(), Q(), Q(1), Q(1), Q(1), Q(), Q(), Q())
        result = contract.compare_coefficient_identity(p, tuple(7*x for x in p), basis=contract.NATIVE_BASIS, frame_identity='fixture-frame')
        self.assertTrue(result['positive_proportional_polynomial'])
        self.assertFalse(result['coefficient_identity_equal'])
        self.assertFalse(result['derivative_identity_certified'])
        self.assertNotEqual(result['first_identity_sha256'], result['second_identity_sha256'])
        self.assertEqual(contract.fraction_from_payload(result['positive_scale_factor_exact']), Q(7))
        self.assertNotEqual(contract.coefficient_identity(p, basis=contract.NATIVE_BASIS, frame_identity='a'),
                            contract.coefficient_identity(p, basis=contract.NATIVE_BASIS, frame_identity='b'))

    def test_explicit_new_unit_c_and_W0_digest_no_native_dispatch(self):
        frame = frame_for()
        seed = contract.register_p20_dyadic_seed(frame)
        record = seed['explicit_unit_normalization']
        c = record['native_c']
        self.assertEqual(seed['native_c'], c)
        self.assertLessEqual(abs(math.sqrt(math.fsum(x*x for x in c))-1), 1e-12)
        expected_digest = hashlib.sha256(json.dumps(c, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')).hexdigest()
        self.assertEqual(record['native_c_sha256'], expected_digest)
        self.assertEqual(seed['native_c_sha256'], expected_digest)
        self.assertEqual([Q.from_float(x) for x in c], [contract.fraction_from_payload(x) for x in record['native_c_exact']])
        self.assertFalse(record['derivative_identity_certified'])
        self.assertFalse(record['native_dispatch_performed'])
        self.assertFalse(seed['coefficients_sent_to_native'])
        self.assertEqual([contract.fraction_from_payload(x['polynomial_value_exact']) for x in seed['anchors']], [Q(-7, 1024), Q(5, 256)])
        for anchor in seed['anchors']:
            value = contract.fraction_from_payload(anchor['registered_native_c_value_exact'])
            self.assertGreater(value*anchor['sign'], 0)
        self.assertIn('NEW_PREREGISTRATION', seed['registration'])
        self.assertTrue(all(value is False for value in seed['scientific_flags'].values()))

    def test_coefficient_projection_discloses_rounding_without_normalizing(self):
        c = (Q(1, 3), Q(-7, 11), Q(), Q(), Q(2), Q(3), Q(4), Q(), Q(), Q())
        result = contract.binary64_coefficient_projection(c, basis=contract.NATIVE_BASIS, frame_identity='test')
        self.assertFalse(result['projection_was_exact'])
        self.assertTrue(result['unit_norm_not_applied'])
        for x, actual, delta in zip(c, result['vector_exact'], result['rounding_delta_exact']):
            self.assertEqual(contract.fraction_from_payload(actual)-x, contract.fraction_from_payload(delta))
        self.assertFalse(result['actual_native_normalized_vector_observed'])

    def test_polynomial_error_bound_covers_whole_box_cross_terms(self):
        a = (Q(1), Q(2), Q(3), Q(4), Q(5), Q(6), Q(7), Q(8), Q(9), Q(10))
        b = tuple(x+Q(1, i+2) for i, x in enumerate(a))
        bounds = ((Q(-2), Q(-3), Q(1)), (Q(4), Q(2), Q(5)))
        bound = contract.polynomial_difference_bound_on_box(a, b, bounds)
        for x in (Q(-2), Q(0), Q(4)):
            for y in (Q(-3), Q(0), Q(2)):
                for z in (Q(1), Q(3), Q(5)):
                    value = abs(contract.evaluate_quadric(a, (x, y, z))-contract.evaluate_quadric(b, (x, y, z)))
                    self.assertLessEqual(value, bound)
        self.assertEqual(contract.polynomial_difference_bound_on_box(a, a, bounds), 0)


class FrozenP19ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case_root = Path(os.environ.get('W4_P20_P19_CASE_ROOT', HERE/'P19_material_case'))
        cls.report_path = Path(os.environ.get('W4_P20_P19_REPORT_PATH', HERE/'P19_CANONICAL_SOURCE_COMPLETE_REPORT.json'))
        if not cls.case_root.is_dir() or not cls.report_path.is_file():
            raise AssertionError('Frozen P19 packet/report is required; missing inputs may not silently skip replay')
        cls.vertices = read_vertices(cls.case_root/'material/M_native.obj')
        cls.norm = contract.core_normalization_from_vertices(cls.vertices)
        cls.frame = contract.Frame.from_core(cls.norm, [(0.0-x)/cls.norm['L'] for x in cls.norm['origin']], IDENTITY)

    def test_real_P19_raw10_mass_COM_and_full_tensor_replay(self):
        replay = contract.replay_p19_physics(self.report_path, self.case_root)
        self.assertEqual(replay['status'], 'EXACT_PHYSICAL_ALGEBRA_REPLAY_PASS')
        self.assertEqual(set(replay['materials']), {'M', 'F', 'D', 'S'})
        self.assertTrue(replay['shaft_already_in_F_not_added_to_mass'])
        self.assertFalse(replay['source_meshes_reintegrated'])
        self.assertFalse(replay['native_owned_regions_examined'])
        for name, row in replay['materials'].items():
            raw = tuple(contract.fraction_from_payload(x) for x in row['reference_raw10_exact'])
            expected_si = tuple(value*Q(1200)*Q.from_float(.025)**(degree+3)
                                for value, degree in zip(raw, contract.RAW10_DEGREES))
            self.assertEqual(expected_si, tuple(contract.fraction_from_payload(x) for x in row['si_raw10_exact']))
            normalized = contract.raw10_original_to_target(raw, self.frame)
            self.assertEqual(contract.raw10_target_to_original(normalized, self.frame), raw)
            self.assertEqual(contract.raw10_reference_to_si(contract.raw10_target_to_original(normalized, self.frame)), expected_si)
            self.assertEqual(row['source_obj_sha256'], contract.P19_MATERIAL_SHA256[name])
        self.assertTrue(all(contract.fraction_from_payload(x) == 0 for x in replay['raw10_M_minus_F_minus_D_exact']))
        self.assertAlmostEqual(replay['materials']['M']['mass_kg'], .031118997336943656, places=17)

    def test_real_P19_effective_tip_and_scale_are_explicit(self):
        self.assertEqual(self.norm['L'], 2.5716)
        self.assertEqual(self.norm['R'], 1.0)
        self.assertNotEqual(self.frame.length, Q.from_float(.025))
        self.assertEqual(self.frame.target_axes, tuple(tuple(map(Q, row)) for row in IDENTITY))
        self.assertNotEqual(self.frame.represented_tip, (Q(),)*3)
        self.assertTrue(all(abs(x) < Q(1, 10**15) for x in self.frame.represented_tip))
        self.assertFalse(self.frame.report()['represented_tip_is_exact_requested_tip'])
        self.assertFalse(self.frame.report()['original_P19_mesh_or_tip_changed'])

    def test_real_two_D_anchors_verify_strict_inside_and_opposite_signs(self):
        result = contract.verify_seed_anchors(self.case_root/'material/D_native.obj')
        self.assertEqual([x['classification']['classification'] for x in result['anchors']], ['INSIDE', 'INSIDE'])
        self.assertFalse(result['native_source_triangulation_side_membership_certified'])
        self.assertFalse(result['full_native_partition_certified'])
        seed = contract.register_p20_dyadic_seed(self.frame)
        self.assertEqual([x['sign'] for x in seed['anchors']], [-1, 1])

    def test_report_or_material_mutation_cannot_self_authorize(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet = root/'packet'
            for relative in ('manifest.json', 'material/M_native.obj', 'material/F_native.obj',
                             'material/D_native.obj', 'source/shaft-reference.obj'):
                destination = packet/relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(self.case_root/relative, destination)
            report = root/'report.json'
            shutil.copyfile(self.report_path, report)
            report.write_bytes(report.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError, 'CANONICAL_REPORT_EXTERNAL_SHA256'):
                contract.replay_p19_physics(report, packet)
            shutil.copyfile(self.report_path, report)
            design = packet/'material/D_native.obj'
            design.write_bytes(design.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError, 'MATERIAL_EXTERNAL_SHA256'):
                contract.replay_p19_physics(report, packet)
            with self.assertRaisesRegex(ValueError, 'ANCHOR_DESIGN_SHA256'):
                contract.verify_seed_anchors(design)
            manifest = json.loads((packet/'manifest.json').read_text())
            manifest['files_sha256']['material/D_native.obj'] = hashlib.sha256(design.read_bytes()).hexdigest()
            (packet/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'MANIFEST_EXTERNAL_SHA256'):
                contract.replay_p19_physics(report, packet)


class FixedCoreContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        default = HERE.parents[2]
        configured = os.environ.get('W4_P20_CORE_SOURCE_ROOT')
        cls.core = Path(configured) if configured else default
        if not all((cls.core/key).is_file() for key in contract.CORE_SOURCE_SHA256):
            raise AssertionError('Set W4_P20_CORE_SOURCE_ROOT to the frozen actual core; source audit may not skip')

    def test_actual_core_source_SHA_and_basis_literals(self):
        result = contract.observe_core_sources(self.core)
        self.assertEqual(result['source_sha256'], contract.CORE_SOURCE_SHA256)
        self.assertFalse(result['native_core_executed'])
        common = (self.core/'python/make_it_stand/verification/spin_common.py').read_text()
        self.assertIn("ORDER = ('M', 'LX', 'LY', 'LZ', 'QXX', 'QYY', 'QZZ', 'QYZ', 'QXZ', 'QXY')", common)
        coefficients = (self.core/'src/spin/QuadricCoefficients.cpp').read_text()
        self.assertIn('coefficients_(4), coefficients_(9), coefficients_(8)', coefficients)
        self.assertIn('point.dot(quadraticMatrix() * point)', coefficients)

    def test_changed_core_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = next(iter(contract.CORE_SOURCE_SHA256))
            (root/first).parent.mkdir(parents=True)
            (root/first).write_bytes((self.core/first).read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError, 'FIXED_CORE_SOURCE_SHA256_MISMATCH'):
                contract.observe_core_sources(root)

    def test_bound_report_and_wrong_outer_scale_rejection(self):
        case = Path(os.environ.get('W4_P20_P19_CASE_ROOT', HERE/'P19_material_case'))
        report_path = Path(os.environ.get('W4_P20_P19_REPORT_PATH', HERE/'P19_CANONICAL_SOURCE_COMPLETE_REPORT.json'))
        norm = contract.core_normalization_from_vertices(read_vertices(case/'material/M_native.obj'))
        frame = contract.Frame.from_core(norm, [(0.0-x)/norm['L'] for x in norm['origin']], IDENTITY)
        report = contract.build_contract_report(frame, core_source_root=self.core, p19_case_root=case, p19_report_path=report_path)
        self.assertEqual(report['actual_frame'], frame.report())
        self.assertTrue(all(x['original_round_trip_exact'] for x in report['exact_affine_target_moment_replays'].values()))
        seed = report['new_probe_registration']['explicit_unit_normalization']
        self.assertGreater(contract.fraction_from_payload(seed['max_polynomial_representation_error_bound_on_entire_D_bbox_exact']), 0)
        self.assertFalse(report['native_dispatch_performed'])
        self.assertTrue(all(x is False for x in report['scientific_flags'].values()))
        wrong = deepcopy(norm)
        wrong['L'] = .025
        wrong_frame = contract.Frame.from_core(wrong, [(0.0-x)/wrong['L'] for x in wrong['origin']], IDENTITY)
        with self.assertRaises(ValueError):
            contract.build_contract_report(wrong_frame, core_source_root=self.core, p19_case_root=case, p19_report_path=report_path)


if __name__ == '__main__':
    unittest.main()
