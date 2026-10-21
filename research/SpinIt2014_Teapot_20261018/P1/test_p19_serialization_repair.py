"""Independent finite repair-budget, degeneracy and exact-moment regressions."""
from fractions import Fraction as Q
import hashlib
from pathlib import Path
import tempfile
import unittest

from p17_boundary_certificate import read_binary64_obj
from p19_serialization_repair import (
    DISTANCE_LIMIT, exact_signed_ten_moments, read_native_obj_allow_zero_area,
    repair_native_serialization,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_obj(path, vertices, faces):
    data = ''.join('v ' + ' '.join(format(float(value), '.17g') for value in point) + '\n'
                   for point in vertices)
    data += ''.join('f ' + ' '.join(str(i + 1) for i in face) + '\n' for face in faces)
    path.write_text(data, encoding='ascii')
    return path


def split_tetrahedron(*, displacement=Q(1, 2 ** 52), zero_area=False, thin=False):
    vertices = ((0, 0, 0), (1, 0, 0), (2, Q(1, 2 ** 100), 0) if thin else (0, 1, 0),
                (0, 0, 1), (0, displacement, 0) if zero_area else (displacement, 0, 0))
    faces = ((0, 2, 4), (4, 2, 1), (0, 4, 3), (4, 1, 3), (0, 3, 2), (1, 2, 3))
    return vertices, faces


def value(record):
    return Q(int(record['numerator']), int(record['denominator']))


class SerializationRepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = save_obj(self.root / 'native.obj', *split_tetrahedron())
        self.output = self.root / 'repaired.obj'

    def tearDown(self):
        self.temp.cleanup()

    def repair(self, **kwargs):
        return repair_native_serialization(self.source, self.output, sha(self.source), **kwargs)

    def test_disjoint_original_edge_collapse_and_all_point_identities(self):
        before = self.source.read_bytes()
        report = self.repair()
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(report['input_vertices'], 5)
        self.assertEqual(report['output_vertices'], 4)
        self.assertEqual(report['input_faces'], 6)
        self.assertEqual(report['output_faces'], 4)
        self.assertEqual(report['close_pair_count'], 1)
        self.assertEqual(report['deleted_original_face_indices'], [0, 2])
        pair = report['collapse_pairs'][0]
        self.assertEqual(pair['original_vertex_indices'], [0, 4])
        self.assertEqual(pair['kept_original_vertex_index'], 0)
        self.assertEqual(pair['removed_original_vertex_index'], 4)
        self.assertEqual(Q(pair['displacement_squared_exact']), Q(1, 2 ** 104))
        native, repaired = read_native_obj_allow_zero_area(self.source), read_binary64_obj(self.output)
        self.assertTrue(set(repaired.vertices).issubset(set(native.vertices)))
        self.assertEqual(sha(self.output), report['output_sha256'])
        self.assertIs(report['exact_displacement_within_budget'], True)
        self.assertIs(report['output_indexed_topology']['indexed_closed_consistently_oriented_two_manifold'], True)

    def test_exact_ten_moments_match_known_tetrahedron(self):
        report = self.repair()
        expected = (Q(1, 6), Q(1, 24), Q(1, 24), Q(1, 24),
                    Q(1, 60), Q(1, 60), Q(1, 60), Q(1, 120), Q(1, 120), Q(1, 120))
        moments = report['signed_tetrahedral_ten_moments']
        for name, answer in zip(moments['order'], expected):
            self.assertEqual(value(moments['before'][name]), answer)
            self.assertEqual(value(moments['after'][name]), answer)
            self.assertEqual(value(moments['delta_after_minus_before'][name]), 0)
        self.assertIs(moments['all_ten_moments_exactly_unchanged'], True)

    def test_zero_area_native_face_is_parsed_and_only_collapsed_faces_are_removed(self):
        save_obj(self.source, *split_tetrahedron(zero_area=True))
        raw = read_native_obj_allow_zero_area(self.source)
        self.assertEqual(raw.zero_area_faces, (0,))
        with self.assertRaisesRegex(ValueError, 'zero-area'):
            read_binary64_obj(self.source)
        report = self.repair()
        self.assertEqual(report['input_exact_zero_area_face_indices'], [0])
        self.assertEqual(report['deleted_original_face_indices'], [0, 2])
        self.assertEqual(report['arbitrary_small_area_face_deletions'], 0)
        moments = report['signed_tetrahedral_ten_moments']
        self.assertEqual(value(moments['delta_after_minus_before']['M']), Q(1, 6 * 2 ** 52))
        self.assertIs(moments['all_ten_moments_exactly_unchanged'], False)
        self.assertIs(report['native_implicit_vs_repaired_solid_set_equality_certified'], False)
        self.assertIs(report['saved_native_vs_repaired_solid_set_equality_certified'], False)

    def test_lexicographic_coordinate_not_index_selects_representative(self):
        vertices, faces = split_tetrahedron()
        # Swap the two close vertices' indices while preserving geometry.
        perm = (4, 1, 2, 3, 0)
        inverse = {old: new for new, old in enumerate(perm)}
        save_obj(self.source, tuple(vertices[i] for i in perm),
                 tuple(tuple(inverse[i] for i in f) for f in faces))
        result = self.repair()
        self.assertEqual(result['collapse_pairs'][0]['kept_original_vertex_index'], 4)
        self.assertEqual(result['collapse_pairs'][0]['removed_original_vertex_index'], 0)

    def test_small_nonzero_faces_are_retained_without_an_area_threshold(self):
        save_obj(self.source, *split_tetrahedron(thin=True))
        result = self.repair()
        self.assertEqual(result['output_faces'], 4)
        self.assertEqual(result['deleted_face_count'], 2)
        self.assertIsNone(result['area_tolerance_used'])
        self.assertIs(result['exact_nonzero_small_faces_retained'], True)
        result_mesh = read_binary64_obj(self.output)
        self.assertEqual(exact_signed_ten_moments(result_mesh.vertices, result_mesh.faces)[0], Q(1, 6 * 2 ** 100))

    def test_surviving_exact_zero_area_face_is_rejected_not_silently_deleted(self):
        vertices, faces = split_tetrahedron()
        vertices = list(vertices)
        vertices[2] = (2, 0, 0)
        save_obj(self.source, vertices, faces)
        with self.assertRaisesRegex(ValueError, 'RETAINED_EXACT_ZERO_AREA_FACE'):
            self.repair()
        self.assertFalse(self.output.exists())

    def test_near_vertex_chain_is_rejected_without_transitive_merging(self):
        delta = Q(1, 2 ** 52)
        vertices = ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1),
                    (delta, 0, 0), (2 * delta, 0, 0))
        faces = ((0, 2, 4), (4, 2, 5), (5, 2, 1),
                 (0, 4, 3), (4, 5, 3), (5, 1, 3), (0, 3, 2), (1, 2, 3))
        save_obj(self.source, vertices, faces)
        with self.assertRaisesRegex(ValueError, 'CHAINS_NOT_ALLOWED'):
            self.repair()
        self.assertFalse(self.output.exists())

    def test_close_nonedge_pair_is_rejected(self):
        vertices = ((0, 0, Q(1, 2 ** 52)), (0, 0, 0),
                    (1, 0, 0), (0, 1, 0), (-1, 0, 0), (0, -1, 0))
        faces = ((0, 2, 3), (0, 3, 4), (0, 4, 5), (0, 5, 2),
                 (1, 3, 2), (1, 4, 3), (1, 5, 4), (1, 2, 5))
        save_obj(self.source, vertices, faces)
        with self.assertRaisesRegex(ValueError, 'NOT_AN_ORIGINAL_EDGE'):
            self.repair()
        self.assertFalse(self.output.exists())

    def test_collapse_edge_must_have_exactly_two_incident_faces(self):
        vertices, faces = split_tetrahedron()
        save_obj(self.source, vertices, faces + (faces[0],))
        with self.assertRaisesRegex(ValueError, 'NOT_EXACTLY_TWO_FACES'):
            self.repair()
        self.assertFalse(self.output.exists())

    def test_exact_distance_budget_rejects_nearby_but_outside_points(self):
        save_obj(self.source, *split_tetrahedron(displacement=Q(1, 2 ** 49)))
        self.assertGreater(Q(1, 2 ** 49), DISTANCE_LIMIT)
        with self.assertRaisesRegex(ValueError, 'NO_AUTHORIZED_COLLAPSE_PAIRS'):
            self.repair()
        self.assertFalse(self.output.exists())

    def test_axis_box_candidate_still_needs_exact_euclidean_distance(self):
        vertices, faces = split_tetrahedron()
        vertices = list(vertices)
        delta = Q(3, 2 ** 52)
        vertices[4] = (delta, delta, delta)
        self.assertLess(delta, DISTANCE_LIMIT)
        self.assertGreater(3 * delta * delta, DISTANCE_LIMIT * DISTANCE_LIMIT)
        save_obj(self.source, vertices, faces)
        with self.assertRaisesRegex(ValueError, 'NO_AUTHORIZED_COLLAPSE_PAIRS'):
            self.repair()
        self.assertFalse(self.output.exists())

    def test_exact_distance_equal_to_a_smaller_registered_budget_is_included(self):
        limit = Q(1, 2 ** 50)
        save_obj(self.source, *split_tetrahedron(displacement=limit))
        result = self.repair(distance_limit=limit)
        self.assertEqual(Q(result['maximum_displacement_squared_exact']), limit * limit)
        self.assertEqual(result['close_pair_count'], 1)

    def test_pair_and_removed_face_limits_are_independent(self):
        vertices, faces = split_tetrahedron()
        translated = tuple((Q(x) + 3, y, z) for x, y, z in vertices)
        save_obj(self.source, vertices + translated, faces + tuple(tuple(i + 5 for i in f) for f in faces))
        with self.assertRaisesRegex(ValueError, 'PAIR_BUDGET_EXCEEDED'):
            self.repair(max_pairs=1)
        with self.assertRaisesRegex(ValueError, 'FACE_BUDGET_EXCEEDED'):
            self.repair(max_deleted_faces=2)
        self.assertFalse(self.output.exists())

    def test_global_budget_cannot_be_widened_or_changed_to_boolean(self):
        for kwargs in ({'distance_limit': Q(1, 10 ** 14)}, {'distance_limit': 0},
                       {'distance_limit': True}, {'max_pairs': 33}, {'max_pairs': True},
                       {'max_deleted_faces': 65}, {'max_deleted_faces': False}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.repair(**kwargs)
        self.assertFalse(self.output.exists())

    def test_source_hash_and_existing_destination_are_protected(self):
        original = self.source.read_bytes()
        with self.assertRaisesRegex(ValueError, 'INPUT_SHA256_MISMATCH'):
            repair_native_serialization(self.source, self.output, '0' * 64)
        with self.assertRaises(FileExistsError):
            repair_native_serialization(self.source, self.source, sha(self.source))
        self.output.write_bytes(b'previous evidence\n')
        with self.assertRaises(FileExistsError):
            self.repair()
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(self.output.read_bytes(), b'previous evidence\n')

    def test_output_symlink_is_not_followed(self):
        self.output.symlink_to(self.source)
        with self.assertRaises(FileExistsError):
            self.repair()
        self.assertTrue(self.output.is_symlink())

    def test_native_parser_retains_comments_binary64_coordinates_and_negative_indices(self):
        path = self.root / 'parse.obj'
        path.write_text('v 0.1 0 0 # binary64\nv 1 0 0\nv 0 1 0\nf -3 -2 -1 # triangle\n')
        raw = read_native_obj_allow_zero_area(path)
        self.assertEqual(raw.vertices[0][0], Q.from_float(0.1))
        self.assertNotEqual(raw.vertices[0][0], Q(1, 10))
        self.assertEqual(raw.faces, ((0, 1, 2),))
        for data in ('v nan 0 0\nf 1 1 1\n', 'v 0 0 0\nf 0 1 1\n',
                     'v 0 0 0\nf 1 2 3\n', 'v 0 0 0\np 1\n'):
            path.write_text(data)
            with self.subTest(data=data), self.assertRaises(ValueError):
                read_native_obj_allow_zero_area(path)

    def test_repairs_remain_explicit_candidates_without_scientific_promotion(self):
        report = self.repair()
        self.assertIs(report['geometry_modified'], True)
        self.assertEqual(report['new_native_Boolean_calls'], 0)
        self.assertIs(report['exact_embedded_solid_certified'], False)
        self.assertIs(report['independent_P18_exact_surface_audit_still_required'], True)
        for name in ('native_provenance_authenticated_by_repair',
                     'native_implicit_vs_repaired_solid_set_equality_certified',
                     'saved_native_vs_repaired_solid_set_equality_certified',
                     'full_original_shaft_contained_in_fixed_material',
                     'W0_physical_tip_or_FD_approved', 'W2_teacher_training_allowed',
                     'Faster_optimization_executed', 'MuJoCo_real_optimized_before_after_executed'):
            self.assertIs(report[name], False)


if __name__ == '__main__':
    unittest.main()
