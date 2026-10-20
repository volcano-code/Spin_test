"""M15 historical Heart real input, negative identity and Noodles readiness tests."""
import copy,json,os,tempfile,unittest
from pathlib import Path
from m15_real_heart_spec import create_heart_spec
from m15_noodles_readiness import inspect

ARCHIVE=os.environ.get("W2_H8F_ARCHIVE")

@unittest.skipUnless(ARCHIVE and Path(ARCHIVE).is_file(),
                     "real H8f archive not available; never fabricate samples")
class TestRealHeartInput(unittest.TestCase):
    def test_real_h8f_freeze(self):
        from run_native_smoke import parse_spec
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"prepared"
            result=create_heart_spec(ARCHIVE,path)
            self.assertEqual(result["model_vertices"],15646)
            self.assertEqual(result["model_faces"],31288)
            self.assertTrue(result["exact_outer_binding_verified"])
            spec=parse_spec(path/"single_native_heart_spec.json")
            self.assertEqual(len(spec["native_c"]),10)
            self.assertFalse(result["training_admitted"])
    def test_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"already";path.mkdir()
            with self.assertRaises(FileExistsError):
                create_heart_spec(ARCHIVE,path)

class TestNoodlesEvidence(unittest.TestCase):
    def test_no_frozen_inputs_blocks_native(self):
        with tempfile.TemporaryDirectory() as d:
            result=inspect(d)
            self.assertEqual(result["status"],"BLOCKED_MISSING_FROZEN_DATA")
            self.assertIn("request",result["missing_required_sources"])
            self.assertEqual(result["new_native_cherchi_calls"],0)
            self.assertIsNone(result["J_D"])
    def test_historical_finite_stencil_not_teacher(self):
        from m15_noodles_readiness import REQUIRED
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/REQUIRED["finite"];p.parent.mkdir(parents=True)
            p.write_text(json.dumps(dict(point_count=81,maximum_fd_error=5.536038294451373e-11,
                neighborhood_certification=False,case_admission=False)))
            result=inspect(d)
            self.assertEqual(result["finite_sample"]["count"],81)
            self.assertFalse(result["historical_finite_point_data_is_native_teacher_certification"])
            self.assertFalse(result["training_admitted"])
    def test_reject_forged_finite_admission(self):
        from m15_noodles_readiness import REQUIRED
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/REQUIRED["finite"];p.parent.mkdir(parents=True)
            p.write_text(json.dumps(dict(neighborhood_certification=True,case_admission=True)))
            with self.assertRaisesRegex(ValueError,"SCIENTIFIC_FLAGS_CHANGED"):
                inspect(d)
if __name__=="__main__":unittest.main()
