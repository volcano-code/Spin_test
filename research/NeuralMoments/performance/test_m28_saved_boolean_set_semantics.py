"""M28 exact geometry and point-in-solid regression tests."""
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).with_name("m28_saved_boolean_set_semantics.py")
spec = importlib.util.spec_from_file_location("m28_saved_boolean_set_semantics", MODULE_PATH)
m28 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m28)


class TestM28ExactSemantics(unittest.TestCase):
    def setUp(self):
        self.vertices = [
            (Fraction(0), Fraction(0), Fraction(0)),
            (Fraction(1), Fraction(0), Fraction(0)),
            (Fraction(0), Fraction(1), Fraction(0)),
            (Fraction(0), Fraction(0), Fraction(1)),
        ]
        self.faces = [(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)]
        self.mesh = (self.vertices, self.faces)

    def test_exact_signed_volume_and_orientation(self):
        self.assertEqual(m28.signed_volume(self.mesh), Fraction(1, 6))

    def test_exact_ray_classifies_inside_outside_and_boundary(self):
        index = m28.RayIndex(self.mesh)
        self.assertEqual(index.classify((Fraction(1,4), Fraction(1,4), Fraction(1,4)))[0], "INSIDE")
        self.assertEqual(index.classify((Fraction(2), Fraction(2), Fraction(2)))[0], "OUTSIDE")
        self.assertEqual(index.classify((Fraction(0), Fraction(1,4), Fraction(1,4)))[0], "ON_BOUNDARY")

    def test_ray_direction_is_not_parallel_to_any_tetra_face(self):
        m = m28.choose_ray_m(self.mesh)
        for face in self.faces:
            tri = tuple(self.vertices[i] for i in face)
            normal = m28.cross(m28.sub(tri[1], tri[0]), m28.sub(tri[2], tri[0]))
            direction = (Fraction(1), Fraction(1,m), Fraction(1,m*m))
            self.assertNotEqual(m28.dot(normal, direction), 0)

    def test_plane_index_finds_exact_subtriangle_owner(self):
        index = m28.PlaneIndex(self.mesh)
        subtriangle = (
            (Fraction(0), Fraction(0), Fraction(0)),
            (Fraction(1,2), Fraction(0), Fraction(0)),
            (Fraction(0), Fraction(1,2), Fraction(0)),
        )
        matches = index.locate(subtriangle)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0][0], 0)

    def test_plane_index_rejects_triangle_outside_source_face(self):
        index = m28.PlaneIndex(self.mesh)
        outside = (
            (Fraction(2), Fraction(0), Fraction(0)),
            (Fraction(3), Fraction(0), Fraction(0)),
            (Fraction(2), Fraction(1), Fraction(0)),
        )
        self.assertEqual(index.locate(outside), [])

    def test_exact_plane_key_is_scale_and_orientation_invariant(self):
        base = tuple(self.vertices[i] for i in self.faces[0])
        reversed_scaled = (
            base[0],
            tuple(2*x for x in base[2]),
            tuple(2*x for x in base[1]),
        )
        self.assertEqual(m28.plane_key(base), m28.plane_key(reversed_scaled))


if __name__ == "__main__":
    unittest.main()


class TestM28M26CertificateAndCheckpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cert_path = Path(__file__).with_name("m26-saved-post-boolean-summary.json")
        cls.archive_sha = m28.ARCHIVE_SHA256
        cls.document, cls.points, cls.cert_sha = m28.load_m26_certificate(cls.cert_path, cls.archive_sha)

    def test_m26_certificate_is_pinned_to_exact_original_archive(self):
        self.assertEqual(set(self.points), {4, 116, 117, 123})
        self.assertEqual(self.document["test_failures"], 0)

    def test_m26_certificate_binds_point_4_packet(self):
        entry = self.points[4]
        mesh = ([None] * entry["vertices"], [None] * entry["faces"])
        result = m28.verify_m26_point_certificate(
            4, "intersection", mesh, entry["packet_sha256"], entry
        )
        self.assertFalse(result["repeated_expensive_surface_audit"])
        self.assertEqual(result["m26_candidate_pairs"], 250083)

    def test_m26_certificate_rejects_packet_sha_drift(self):
        entry = dict(self.points[4])
        with self.assertRaisesRegex(ValueError, "PACKET_SHA_MISMATCH"):
            m28.verify_m26_point_certificate(
                4, "intersection", ([None] * entry["vertices"], [None] * entry["faces"]),
                "0" * 64, entry
            )

    def test_m26_certificate_rejects_operation_drift(self):
        entry = dict(self.points[4])
        with self.assertRaisesRegex(ValueError, "OPERATION_MISMATCH"):
            m28.verify_m26_point_certificate(
                4, "difference", ([None] * entry["vertices"], [None] * entry["faces"]),
                entry["packet_sha256"], entry
            )

    def test_m26_certificate_rejects_geometry_size_drift(self):
        entry = dict(self.points[4])
        with self.assertRaisesRegex(ValueError, "GEOMETRY_SIZE_MISMATCH"):
            m28.verify_m26_point_certificate(
                4, "intersection", ([None] * (entry["vertices"]-1), [None] * entry["faces"]),
                entry["packet_sha256"], entry
            )

    def test_certificate_file_tampering_fails_closed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tampered.json"
            path.write_text(self.cert_path.read_text() + " ")
            with self.assertRaisesRegex(ValueError, "FILE_SHA256_MISMATCH"):
                m28.load_m26_certificate(path, self.archive_sha)

    def test_atomic_checkpoint_round_trip(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "checkpoint.json"
            m28.atomic_json(path, {"schema": "test", "value": 123})
            self.assertEqual(json.loads(path.read_text())["value"], 123)
            self.assertFalse(path.with_name(path.name + ".tmp").exists())