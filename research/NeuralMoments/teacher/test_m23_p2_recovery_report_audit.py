"""Read-only tests for the M23-P2 host recovery report parser."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from m23_p2_recovery_report_audit import PACKETS, audit_report

SAMPLE = """===== 六份精确材料 =====
FOUND: /data/noodles-balanced-full-input-job-01/output/design-rational.json
d0aec854f2207f2b8abad99507e915fc86ce0b6055ef07a7a3b0a20c3a1eb7f7  /data/noodles-balanced-full-input-job-01/output/design-rational.json
FOUND: /data/noodles-balanced-full-input-job-01/output/fixed-rational.json
a0e18f72355a0cd9b208c35bbb7aac195ce93401615125ef805a9935393a8953  /data/noodles-balanced-full-input-job-01/output/fixed-rational.json

===== 原始 CGAL 后端 =====

===== Noodles 历史压缩包 =====
"""


class TestM23P2Recovery(unittest.TestCase):
    def test_uploaded_report_shape_fails_closed_no_admission(self):
        r = audit_report(SAMPLE)
        self.assertEqual(r["found_candidate_count"], 2)
        self.assertEqual(r["historical_exact_matches_by_report"], 0)
        self.assertEqual(len(r["unreported_names"]), 4)
        self.assertEqual(r["packets"]["fixed-rational.json"]["status"], "FOUND_DIFFERENT_SHA")
        self.assertFalse(r["local_bytes_rehashed"])
        self.assertEqual(r["training_samples"], 0)
        self.assertIsNone(r["J_D"])

    def test_report_match_is_not_local_bytes(self):
        p = "/data/check/design-rational.json"
        s = ("===== 六份精确材料 =====\nFOUND: " + p + "\n"
             + PACKETS["design-rational.json"] + "  " + p
             + "\n===== 原始 CGAL 后端 =====\n===== Noodles 历史压缩包 =====\n")
        r = audit_report(s)
        self.assertEqual(r["historical_exact_matches_by_report"], 1)
        self.assertEqual(r["historical_exact_matches_independently_rehashed"], 0)

    def test_checksum_path_mismatch_rejected(self):
        s = SAMPLE.replace("  /data/noodles-balanced-full-input-job-01/output/design-rational.json",
                           "  /data/some-other-file.json")
        with self.assertRaisesRegex(ValueError, "FOUND_CHECKSUM_BINDING_INVALID"):
            audit_report(s)

    def test_missing_sha_rejected(self):
        s = SAMPLE.replace("d0aec854f2207f2b8abad99507e915fc86ce0b6055ef07a7a3b0a20c3a1eb7f7  /data/noodles-balanced-full-input-job-01/output/design-rational.json\n", "")
        with self.assertRaisesRegex(ValueError, "FOUND_PATH_MISSING_SHA"):
            audit_report(s)

    def test_truncated_report_rejected(self):
        with self.assertRaisesRegex(ValueError, "TRUNCATED_REPORT_SECTIONS"):
            audit_report("===== 六份精确材料 =====\n")

    def test_rehash_when_local_file_available(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "design-rational.json"
            path.write_bytes(b"not a historical packet")
            line = hashlib.sha256(path.read_bytes()).hexdigest()
            s = ("===== 六份精确材料 =====\nFOUND: " + str(path) + "\n"
                 + line + "  " + str(path) +
                 "\n===== 原始 CGAL 后端 =====\n===== Noodles 历史压缩包 =====\n")
            r = audit_report(s, actual_files=True)
            self.assertTrue(r["local_bytes_rehashed"])
            self.assertEqual(r["historical_exact_matches_independently_rehashed"], 0)


if __name__ == "__main__":
    unittest.main()
