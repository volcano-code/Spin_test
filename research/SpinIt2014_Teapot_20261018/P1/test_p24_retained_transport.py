"""P24-A regression: accept the pinned direct/local form, reject unrelated helpers."""
import tempfile
from pathlib import Path
import unittest
from p23_rational_token_transport import wrapped


class TestRetainedInput(unittest.TestCase):
    def check(self, code):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp, "full_partition_m6.py")
            path.write_text("def audit_native_full_partition_once():\n" +
                            "\n".join("    " + line for line in code.splitlines()))
            return wrapped(path)

    def test_immediate_local(self):
        form = "v = canonical_mesh_rational_rows(saved['material_proof']['exact_vertices'])\n"
        self.assertTrue(self.check(form + "faces = saved['variable_faces']\nretained = MeshSnapshot.from_rationals(v, faces)"))
        for bad in ("v = raw", "v[0] = raw", "tamper(v)", "other = v"):
            with self.subTest(bad=bad):
                self.assertFalse(self.check(form + bad + "\nretained = MeshSnapshot.from_rationals(v, faces)"))

    def test_unrelated_field_or_unrelated_call(self):
        self.assertFalse(self.check("retained = MeshSnapshot.from_rationals(canonical_mesh_rational_rows(other), faces)"))
        self.assertFalse(self.check("other = MeshSnapshot.from_rationals(canonical_mesh_rational_rows(saved['material_proof']['exact_vertices']), faces)"))
