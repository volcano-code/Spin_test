import tempfile, unittest
from pathlib import Path
from m23_p2_noodles_rebuild_readiness import audit, EXPECTED_BACKEND_SHA, EXPECTED_SOURCE_MANIFEST_SHA

class TestReadiness(unittest.TestCase):
    def test_missing_everything_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src=root/"sourceparts"; src.mkdir()
            out=root/"out"; out.mkdir()
            r=audit(src,out,root/"backend",root/"external",root/"audit.json",0)
            self.assertEqual(r["status"],"BLOCKED_PREREQUISITES_INCOMPLETE")
            self.assertIn("PINNED_CGAL_BACKEND_MISSING",r["errors"])
            self.assertFalse(r["cgal_launched"])
            self.assertIsNone(r["J_D"])
    def test_existing_outputs_are_reported_not_trusted(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src=root/"sourceparts"; src.mkdir()
            out=root/"out"; out.mkdir()
            (out/"design-rational.json").write_text("{}")
            r=audit(src,out,root/"backend",root/"external",root/"audit.json",0)
            self.assertTrue(r["historical_packet_outputs"]["design-rational.json"]["exists"])
            self.assertNotEqual(r["historical_packet_outputs"]["design-rational.json"]["sha256"],
                                "48e8d3008bba746823eafd9c3704b52d597595b802066450a921ecc0dcb7f611")
            self.assertIn("PINNED_CGAL_BACKEND_MISSING",r["errors"])
    def test_free_space_gate_is_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src=root/"sourceparts"; src.mkdir()
            out=root/"out"; out.mkdir()
            r=audit(src,out,root/"backend",root/"external",root/"audit.json",23*1024**3)
            self.assertIn("FREE_DISK_BELOW_24_GIB_REBUILD_RESERVE",r["errors"])
    def test_output_set_is_exactly_six_packets(self):
        from m23_p2_noodles_rebuild_readiness import REQUIRED_OUTPUTS
        self.assertEqual(len(REQUIRED_OUTPUTS),6)
        self.assertEqual(len(set(REQUIRED_OUTPUTS)),6)

if __name__=="__main__": unittest.main(verbosity=2)
