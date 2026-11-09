import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("p32_triangle_screen", HERE / "p32_triangle_screen.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class P32TriangleScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = MODULE.run(HERE.parents[2])

    def test_schema_and_fail_closed_flags(self):
        self.assertEqual(self.result["schema"], "W4_P32_FLOATING_POINT_TRIANGLE_SCREEN_V1")
        self.assertEqual(self.result["status"], "DIAGNOSTIC_SCREEN_ONLY_NOT_ROBUST_CERTIFICATE")
        self.assertFalse(self.result["scientific_admission"])
        self.assertFalse(self.result["robust_solid_containment_certified"])
        self.assertFalse(self.result["printability_certified"])

    def test_source_blobs_and_mesh_counts(self):
        self.assertEqual(self.result["sources"]["M"]["vertices"], 4035)
        self.assertEqual(self.result["sources"]["M"]["faces"], 8070)
        self.assertEqual(self.result["sources"]["D"]["vertices"], 200)
        self.assertEqual(self.result["sources"]["D"]["faces"], 400)
        self.assertEqual(self.result["sources"]["S"]["vertices"], 258)
        self.assertEqual(self.result["sources"]["S"]["faces"], 512)

    def test_nonincident_self_screen(self):
        for name, expected in (("M_self", 10160), ("D_self", 439), ("S_self", 580)):
            self.assertEqual(self.result["checks"][name]["nonincident_pairs_tested"], expected)
            self.assertEqual(self.result["checks"][name]["sat_intersections"], 0)

    def test_cross_mesh_screen_and_contact_loci(self):
        self.assertEqual(self.result["checks"]["M_D"]["aabb_candidates"], 0)
        self.assertEqual(self.result["checks"]["D_S"]["aabb_candidates"], 0)
        ms = self.result["checks"]["M_S"]
        self.assertEqual(ms["aabb_candidates"], 6580)
        self.assertEqual(ms["sat_intersections"], 2144)
        self.assertEqual(ms["contact_localization"], {
            "top_plane_pairs": 1120,
            "common_apex_pairs": 1024,
            "other_pairs": 0,
        })


if __name__ == "__main__":
    unittest.main()
