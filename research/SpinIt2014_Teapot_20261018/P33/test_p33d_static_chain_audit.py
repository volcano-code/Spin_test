import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("p33d_static_chain_audit", HERE / "p33d_static_chain_audit.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class P33DStaticChainAuditTests(unittest.TestCase):
    def test_static_chain_consistency(self):
        result = MODULE.audit(HERE.parents[2])
        self.assertEqual(result["schema"], "W4_P33D_P30B_STATIC_CHAIN_AUDIT_V1")
        self.assertEqual(result["status"], "STATIC_SOURCE_CONSISTENCY_PASS_NOT_RUNTIME_ADMISSION")
        self.assertEqual(result["pilot"]["maximum_points"], 12)
        self.assertEqual(result["resource_envelope"]["docker_memory"], "24g")
        self.assertEqual(result["resource_envelope"]["docker_memory_swap_total"], "24g")
        self.assertEqual(result["pinned"]["archive_internal_run_root"], "formal-m6-run-20261107T050117Z")
        self.assertEqual(result["pinned"]["host_prepared_p27_run_directory"], "formal-m6-20261106T091202Z")
        self.assertNotEqual(result["pinned"]["archive_internal_run_root"],
                            result["pinned"]["host_prepared_p27_run_directory"])

    def test_all_scientific_release_flags_closed(self):
        result = MODULE.audit(HERE.parents[2])
        for key in ("runtime_observed", "owner_receipts_observed",
                    "external_lock_registered", "scientific_admission",
                    "Newton_accepted", "training_admissible",
                    "MuJoCo_optimized_before_after_executed"):
            self.assertIs(result[key], False)
        self.assertEqual(result["native_calls"], 0)


if __name__ == "__main__":
    unittest.main()
