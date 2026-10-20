"""W2 M14 offline fail-closed tests; uses authentic M13 evidence, not new Cherchi."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from m14_algebraic_handoff import inspect,strict_json,rational,M13_SHA

class TestM14(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        value=os.environ.get("W2_M13_FULL_REPORT")
        if not value or not Path(value).is_file():
            raise unittest.SkipTest("M13 full SHA-pinned report must be supplied")
        cls.source=Path(value)
        cls.result=inspect(cls.source)
    def test_full_81(self):self.assertEqual(self.result["checked_raw_coefficient_vectors"],81)
    def test_distinct_rays(self):self.assertEqual(self.result["distinct_positive_integer_rays"],81)
    def test_17_64(self):self.assertEqual((self.result["unit_compatible_raw_vectors"],self.result["nonunit_raw_vectors"]),(17,64))
    def test_original_failure(self):self.assertEqual(self.result["original_workflow_conclusion"],"failure")
    def test_training_zero(self):self.assertEqual(self.result["training_admitted"],0)
    def test_no_j(self):self.assertIsNone(self.result["J_D"])
    def test_no_approval(self):self.assertFalse(self.result["w0_projective_protocol_approved"])
    def test_no_new_native(self):self.assertEqual(self.result["new_native_calls"],0)
    def test_point60(self):self.assertTrue(self.result["point60_feature_change_preserved"])
    def test_sha_pin(self):self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(),M13_SHA)
    def test_bad_fraction(self):
        for s in ("0/0","1/-2","nan/1","1.2/3"):
            with self.assertRaises(ValueError):rational(s)
    def test_duplicate_json(self):
        with self.assertRaisesRegex(ValueError,"DUPLICATE_JSON_KEY"):strict_json('{"x":1,"x":2}')
    def test_nan_json(self):
        with self.assertRaisesRegex(ValueError,"NONFINITE_JSON_NUMBER"):strict_json('{"x":NaN}')
    def test_changed_evidence_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"tampered.json";p.write_bytes(self.source.read_bytes()+b" ")
            with self.assertRaisesRegex(ValueError,"UNPINNED_M13_FULL_REPORT"):inspect(p)
    def test_forged_w0_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"forged.json";p.write_text("{}")
            with self.assertRaisesRegex(ValueError,"w0_schema_BLOB_DRIFT"):inspect(self.source,w0_schema=p)
    def test_forged_w3_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"forged.json";p.write_text("{}")
            with self.assertRaisesRegex(ValueError,"w3_stage11_BLOB_DRIFT"):inspect(self.source,w3_report=p)

if __name__=="__main__":unittest.main()
