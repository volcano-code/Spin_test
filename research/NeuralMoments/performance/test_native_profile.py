"""W1 smoke contract. Synthetic timing fixtures are never measurements."""
import json
from pathlib import Path
import tempfile
import unittest
from native_profile import StageClock, verify_history, audit, HISTORY

class TestW1(unittest.TestCase):
    def fixture(self, finished=True):
        stages = dict(source=2, boolean=3, derivative=5, integration=7,
                      map_check=11, opaque_native=13)
        return dict(schema="faster-exclusive-solver-timing-v1",
            exclusive_stage_ns=stages, measured_algorithm_ns=17,
            validation_ns=11, solver_completed=finished,
            solver_wall_ns=sum(stages.values()) if finished else None,
            unclassified_ns=13 if finished else None,
            unfinished_stages=[] if finished else ["native_newton_solver"])
    def test_complete_history(self):
        result=verify_history(self.fixture())
        self.assertEqual(result["solver_wall_ns"],41)
        self.assertIsNone(result["paper_comparable_seconds"])
    def test_unfinished_is_not_full_solve(self):
        result=verify_history(self.fixture(False))
        self.assertIsNone(result["solver_wall_ns"])
        bad=self.fixture(False);bad["solver_wall_ns"]=41
        with self.assertRaisesRegex(ValueError,"CANNOT_HAVE_WALL"):
            verify_history(bad)
    def test_reject_bad_wall(self):
        item=self.fixture();item["solver_wall_ns"]=999
        with self.assertRaisesRegex(ValueError,"WALL_MISMATCH"):
            verify_history(item)
    def test_stage_clock_failure(self):
        c=StageClock()
        self.assertEqual(c.measure("source",lambda:7),7)
        with self.assertRaisesRegex(ValueError,"OVERLAPPING"):
            c.measure("boolean",lambda:c.measure("integration",lambda:1))
        result=c.snapshot()
        self.assertFalse(result["all_returned"])
        self.assertGreaterEqual(result["unattributed_ns"],0)
    def test_audit_absent_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            result=audit(Path(temp))
            self.assertFalse(result["inputs"]["noodles_v7"]["available"])
            self.assertIsNone(result["end_to_end_solver_seconds"])
            self.assertEqual(len(result["native_samples"]),0)
            self.assertFalse(result["paper_speed_qualified"])
    def test_frozen_blob_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"experiments/faster_core_repair_20261012"
            p.mkdir(parents=True)
            (p/"noodles-historical-timing-scope-01.json").write_text("{}")
            with self.assertRaisesRegex(ValueError,"SOURCE_DRIFT"):
                audit(Path(temp))

if __name__=="__main__":
    unittest.main()
