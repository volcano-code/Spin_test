"""Independent analytic simplex tests and optional real frozen archive replay."""
from fractions import Fraction
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

import numpy as np

from p17_physical_case import (
    DENIED_FLAGS, analyze_mesh, analyze_obj, build_physical_proposal, p13_case_config,
)


VERTICES = [(0., 0., 0.), (1., 0., 0.), (0., 1., 0.), (0., 0., 1.)]
FACES = [(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)]


def fractions(payload):
    return tuple(Fraction(int(x['numerator']), int(x['denominator'])) for x in payload)


def save_obj(path, vertices=VERTICES, faces=FACES):
    rows = ['v ' + ' '.join(format(float(x), '.17g') for x in p) for p in vertices]
    rows += ['f ' + ' '.join(str(i + 1) for i in face) for face in faces]
    path.write_text('\n'.join(rows) + '\n', encoding='utf-8')
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PhysicalCaseTests(unittest.TestCase):
    def analyze(self, vertices=VERTICES, faces=FACES, scale=1., density=1.):
        return analyze_mesh(vertices, faces, scale_m_per_unit=scale, density_kg_m3=density)

    def test_unit_simplex_analytic_ordinary_ten(self):
        # Dirichlet simplex integrals, independently known analytically:
        # int x^a y^b z^c = a! b! c! / (a+b+c+3)!.
        result = self.analyze()
        expected = (Fraction(1, 6), *([Fraction(1, 24)] * 3),
                    *([Fraction(1, 60)] * 3), *([Fraction(1, 120)] * 3))
        self.assertEqual(fractions(result['source_raw_ten_exact']), expected)
        self.assertEqual(fractions(result['si_raw_ten_exact']), expected)
        self.assertEqual(result['cross_moment_convention'], 'ORDINARY_UNDOUBLED')

    def test_scale_cubed_fourth_fifth_and_known_principal_inertias(self):
        result = self.analyze(scale=2., density=3.)
        expected_si = (Fraction(4), *([Fraction(2)] * 3),
                       *([Fraction(8, 5)] * 3), *([Fraction(4, 5)] * 3))
        self.assertEqual(fractions(result['si_raw_ten_exact']), expected_si)
        self.assertEqual(result['center_of_mass_m'], [.5, .5, .5])
        np.testing.assert_allclose(result['full_inertia_com_kg_m2'],
                                   [[1.2, .2, .2], [.2, 1.2, .2], [.2, .2, 1.2]], atol=1e-15)
        np.testing.assert_allclose(result['principal_inertia_kg_m2'], [1., 1., 1.6], atol=1e-15)

    def test_anisotropic_tetrahedron_full_tensor_and_undoubled_cross_terms(self):
        vertices = [(0., 0., 0.), (2., 0., 0.), (0., 3., 0.), (0., 0., 4.)]
        result = self.analyze(vertices=vertices, scale=.5, density=8.)
        self.assertEqual(result['mass_kg'], 4.)
        self.assertEqual(result['center_of_mass_m'], [.25, .375, .5])
        np.testing.assert_allclose(result['full_inertia_origin_kg_m2'],
                                   [[2.5, -.3, -.4], [-.3, 2., -.6], [-.4, -.6, 1.3]], atol=1e-15)
        # Simplex covariance: var(x_i)=3*a_i^2/80, cov(x_i,x_j)=-a_i*a_j/80.
        np.testing.assert_allclose(result['full_inertia_com_kg_m2'],
                                   [[.9375, .075, .1], [.075, .75, .15], [.1, .15, .4875]], atol=1e-15)

    def test_large_reference_translation_does_not_corrupt_center_inertia(self):
        shift = np.array([2.**20, -2.**19, 2.**18])
        result = self.analyze(vertices=np.array(VERTICES) + shift, scale=.025, density=1200.)
        baseline = self.analyze(scale=.025, density=1200.)
        self.assertEqual(result['full_inertia_com_kg_m2'], baseline['full_inertia_com_kg_m2'])
        np.testing.assert_allclose(result['center_of_mass_m'], (.25 + shift) * .025, rtol=1e-15)

    def test_proper_frame_rotation_preserves_principal_inertia(self):
        rotation = np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])
        vertices = np.array(VERTICES) * [2., 3., 4.]
        before = self.analyze(vertices=vertices)
        after = self.analyze(vertices=vertices @ rotation.T)
        np.testing.assert_allclose(after['full_inertia_com_kg_m2'],
                                   rotation @ before['full_inertia_com_kg_m2'] @ rotation.T, atol=1e-15)
        np.testing.assert_allclose(after['principal_inertia_kg_m2'], before['principal_inertia_kg_m2'], atol=1e-15)

    def test_invalid_scale_and_density_rejected(self):
        for value in [0., -1., float('inf'), float('nan'), True, '0.025']:
            with self.subTest(value=value):
                with self.assertRaises(ValueError): self.analyze(scale=value)
                with self.assertRaises(ValueError): self.analyze(density=value)

    def test_nonfinite_vertices_rejected(self):
        vertices = np.array(VERTICES)
        for value in [float('nan'), float('inf')]:
            vertices[0, 0] = value
            with self.assertRaisesRegex(ValueError, 'NONFINITE_VERTEX'):
                self.analyze(vertices=vertices)

    def test_invalid_face_indices_rejected(self):
        for face in [(0, 1, 4), (0, 0, 1), (-1, 0, 1), (0., 1., 2.), (False, 1, 2)]:
            with self.subTest(face=face), self.assertRaises(ValueError):
                self.analyze(faces=[face, *FACES[1:]])

    def test_open_or_inconsistently_oriented_surface_rejected(self):
        with self.assertRaisesRegex(ValueError, 'EDGE_BOUNDARY'):
            self.analyze(faces=FACES[:-1])
        with self.assertRaisesRegex(ValueError, 'INCONSISTENT_FACE_ORIENTATION'):
            self.analyze(faces=[FACES[0][::-1], *FACES[1:]])

    def test_nonpositive_volume_rejected(self):
        with self.assertRaisesRegex(ValueError, 'SIGNED_VOLUME'):
            self.analyze(faces=[face[::-1] for face in FACES])
        vertices = np.array(VERTICES)
        vertices[3] = [.25, .25, 0.]
        with self.assertRaisesRegex(ValueError, 'SIGNED_VOLUME'):
            self.analyze(vertices=vertices)

    def test_obj_reread_pins_binary64_not_decimal_rational(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'tetra.obj'
            vertices = copy.deepcopy(VERTICES)
            vertices[1] = (.1, 0., 0.)
            digest = save_obj(path, vertices)
            result = analyze_obj(path, scale_m_per_unit=.025, density_kg_m3=1200., expected_sha256=digest)
            self.assertEqual(fractions(result['source_raw_ten_exact'])[0], Fraction.from_float(.1) / 6)
            self.assertNotEqual(fractions(result['source_raw_ten_exact'])[0], Fraction(1, 60))
            self.assertTrue(result['frozen_input_sha256_verified'])
            with self.assertRaisesRegex(ValueError, 'SHA256_MISMATCH'):
                analyze_obj(path, scale_m_per_unit=.025, density_kg_m3=1200., expected_sha256='0' * 64)

    def test_unified_case_is_explicit_p13_unapproved_proposal(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'tetra.obj'
            digest = save_obj(path)
            result = build_physical_proposal({'M': path}, case_config=p13_case_config(), expected_sha256={'M': digest})
            self.assertEqual(result['case_config']['scale_m_per_unit'], .025)
            self.assertEqual(result['case_config']['density_kg_m3'], 1200.)
            self.assertEqual(result['spin_axis_reference'], [0., 0., 1.])
            self.assertEqual(result['tip_m'], [0., 0., 0.])
            self.assertEqual(result['physical_table'][0]['mass_kg'], result['materials']['M']['mass_kg'])
            self.assertTrue(result['old_P12_15cm_or_0_25kg_case_not_used'])
            for flag in DENIED_FLAGS:
                self.assertIs(result[flag], False)
                self.assertIs(result['materials']['M'][flag], False)
            json.dumps(result, allow_nan=False)

    def test_case_config_and_false_approval_flags_are_strict(self):
        changes = [dict(scale_m_per_unit=.15), dict(density_kg_m3=1240.),
                   dict(spin_axis_reference=[1., 0., 0.]), dict(tip_reference=[0., 0., .1]),
                   dict(W0_physical_tip_or_FD_approved=True), dict(W0_physical_tip_or_FD_approved=0),
                   dict(new_unknown_setting='silently ignored')]
        for change in changes:
            config = p13_case_config()
            config.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                build_physical_proposal({'M': 'missing.obj'}, case_config=config, expected_sha256={'M': '0' * 64})

    def test_all_meshes_require_matching_frozen_digest_names(self):
        with self.assertRaisesRegex(ValueError, 'HASH_NAMES_MISMATCH'):
            build_physical_proposal({'M': 'missing.obj'}, case_config=p13_case_config(), expected_sha256={})

    @unittest.skipUnless(os.environ.get('W4_P17_P14_ROOT') and os.environ.get('W4_P17_P15_ROOT'),
                         'Original SHA-pinned P14/P15 archives not supplied')
    def test_actual_saved_p15_candidate_m_f_d_physical_additivity(self):
        from p16_exact_binary64_chain import check_sources
        _, outer, cases = check_sources(Path(os.environ['W4_P17_P14_ROOT']), Path(os.environ['W4_P17_P15_ROOT']))
        source = cases['rotate_1p5']
        paths = {'M': outer, 'F': source['cleanF'], 'D': source['nativeD']}
        hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}
        result = build_physical_proposal(paths, case_config=p13_case_config(), expected_sha256=hashes)
        records = result['materials']
        m, f, d = (fractions(records[key]['si_raw_ten_exact']) for key in ['M', 'F', 'D'])
        self.assertEqual(tuple(a - b - c for a, b, c in zip(m, f, d)), (Fraction(0),) * 10)
        self.assertGreater(records['M']['mass_kg'], records['F']['mass_kg'])
        self.assertLess(records['M']['mass_kg'], .04)
        self.assertGreater(records['M']['mass_kg'], .03)
        self.assertIs(result['W0_physical_tip_or_FD_approved'], False)


if __name__ == '__main__':
    unittest.main()
