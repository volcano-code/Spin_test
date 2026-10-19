"""Real C++ build and process tests plus pure-Python fail-closed H8 smoke."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from h8_native_replay import (ExclusiveLedger, validate_native_audit, checked_parity,
                              EXPECTED_REQUEST_SHA256, evaluate)

class TestM2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("g++"):
            raise unittest.SkipTest("g++ missing")
        cls.temp=tempfile.TemporaryDirectory(prefix="w1-m2-cxx-")
        cls.binary=Path(cls.temp.name)/"prepared_material_probe"
        cls.build=subprocess.run(["g++","-std=c++17","-O2","-Wall","-Wextra","-pedantic",
            str(ROOT/"prepared_material_probe.cpp"),"-o",str(cls.binary),"-lgmpxx","-lgmp"],
            capture_output=True,text=True,timeout=120)
        if cls.build.returncode:
            raise AssertionError(cls.build.stderr)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls,"temp"): cls.temp.cleanup()

    def call(self,tetra,repeats):
        return subprocess.run([str(self.binary),str(tetra),str(repeats)],
                              capture_output=True,text=True,timeout=25)

    def test_gmp_negative_and_analytic(self):
        result=subprocess.run([str(self.binary),"--self-test"],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        record=json.loads(result.stdout)
        self.assertTrue(record["misoriented_rejected"])
        self.assertTrue(record["noncanonical_rejected"])
        self.assertTrue(record["out_of_range_rejected"])
        self.assertTrue(record["null_source_rejected"])
        self.assertEqual(record["analytic_volume"],"4/1029")

    def test_gmp_tetra_identity(self):
        result=self.call(1,1)
        self.assertEqual(result.returncode,0,result.stderr)
        record=json.loads(result.stdout)
        self.assertEqual(record["first_sample_ten_exact"][0],"4/1029")
        self.assertTrue(record["exact_ten_moments_equal"])
        self.assertTrue(record["identical_boundary_gate"])
        self.assertFalse(record["full_solver_measured"])

    def test_gmp_multiple_distinct_sources(self):
        result=self.call(24,7)
        self.assertEqual(result.returncode,0,result.stderr)
        record=json.loads(result.stdout)
        self.assertEqual(record["samples"],7)
        self.assertEqual(record["faces_per_sample"],96)
        self.assertTrue(record["exact_ten_moments_equal"])
        self.assertGreater(record["old_parse_ns"],0)

    def test_gmp_resource_limits(self):
        for invalid in ((0,1),(257,1),(1,31)):
            result=self.call(*invalid)
            self.assertNotEqual(result.returncode,0)
            self.assertIn("OUTSIDE_W1_SMALL_MICROBENCH_LIMITS",result.stderr)

    def test_ledger_rejects_nested(self):
        ledger=ExclusiveLedger()
        self.assertEqual(ledger.observe("source",lambda:42),42)
        with self.assertRaisesRegex(ValueError,"W1_STAGE_OVERLAP"):
            ledger.observe("boolean",lambda:ledger.observe("integration",lambda:None))
        self.assertFalse(ledger.summary()["all_stages_passed"])
        with self.assertRaisesRegex(ValueError,"UNREGISTERED"):
            ledger.observe("skip_exact_audit",lambda:None)

    def test_audit_rejects_missing_flags(self):
        with self.assertRaisesRegex(ValueError,"REQUIRED_FLAGS_FAILED"):
            validate_native_audit({})
        from h8_native_replay import AUDIT_TRUE
        flags={key:True for key in AUDIT_TRUE}
        flags["intersecting_pairs"]=[[0,1]]
        with self.assertRaisesRegex(ValueError,"INTERSECTION_OR_DEGENERACY"):
            validate_native_audit(flags)

    def test_ten_moment_jacobian_parity(self):
        import numpy as np
        geometry={"geometry_hash":"h", "topology_hash":"t", "quadric_source_identity":"s"}
        evaluated={"geometry_hash":"h", "topology_hash":"t",
            "variable_raw_moments":np.arange(1.,11.), "moment_jacobian":np.eye(10)}
        result=checked_parity(geometry,evaluated,[float(x) for x in range(1,11)])
        self.assertEqual(result["independent_scaled_error"],0)
        evaluated["moment_jacobian"]=np.zeros((9,10))
        with self.assertRaisesRegex(ValueError,"W1_BAD_TEN_OR_JACOBIAN"):
            checked_parity(geometry,evaluated,range(1,11))
        evaluated["moment_jacobian"]=np.eye(10)
        evaluated["variable_raw_moments"][3]+=0.01
        with self.assertRaisesRegex(ValueError,"W1_FRACTION_VS_GMP_DISAGREEMENT"):
            checked_parity(geometry,evaluated,range(1,11))

    def test_h8_missing_request_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)
            with self.assertRaisesRegex(FileNotFoundError,"FROZEN_REQUEST_NOT_AVAILABLE"):
                evaluate(p,p/"missing.json",p/"evidence")
            record=json.loads((p/"evidence/failure.json").read_text())
            self.assertEqual(record["status"],"FAILED_CLOSED")
            self.assertFalse(record["paper_speed_qualified"])
            self.assertFalse((p/"evidence/baseline-performance.json").exists())

    def test_h8_wrong_sha_fails_without_native_import(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)
            (p/"request.json").write_text("{}")
            with self.assertRaisesRegex(ValueError,"W1_H8_REQUEST_SHA_DRIFT"):
                evaluate(p,p/"request.json",p/"evidence")
            self.assertTrue((p/"evidence/failure.json").is_file())
            self.assertEqual(len(EXPECTED_REQUEST_SHA256),64)

if __name__=="__main__":
    unittest.main()
