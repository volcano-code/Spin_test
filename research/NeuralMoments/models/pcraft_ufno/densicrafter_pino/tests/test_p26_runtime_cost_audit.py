import unittest
from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.p26_runtime_cost_audit import audit

class P26RuntimeCostAuditTests(unittest.TestCase):
    def test_paired_exact_baseline_and_hybrid_cost(self):
        rows = [
            {"sample_id":"a","pino_ms":2,"uqno_ms":1,"fallback_used":True,"exact_ms":4,"exact_reference_ms":10,"exact_backend":"cherchi","exact_provenance":"W2 native Cherchi build hash abc"},
            {"sample_id":"b","pino_ms":3,"uqno_ms":2,"fallback_used":False,"exact_reference_ms":20,"exact_backend":"cherchi","exact_provenance":"W2 native Cherchi build hash abc"},
        ]
        result = audit(rows)["backend_groups"]["cherchi"]
        self.assertEqual(result["fallback_fraction"], 0.5)
        self.assertEqual(result["mean_total_pipeline_ms"], 6.0)
        self.assertEqual(result["mean_exact_reference_ms"], 15.0)
        self.assertEqual(result["speedup_vs_exact_only"], 2.5)

    def test_missing_exact_provenance_is_rejected(self):
        rows = [{"sample_id":"a","pino_ms":1,"uqno_ms":1,"fallback_used":False,"exact_reference_ms":5,"exact_backend":"cherchi"}]
        with self.assertRaises(ValueError):
            audit(rows)

    def test_duplicate_sample_ids_are_rejected(self):
        row = {"sample_id":"a","pino_ms":1,"uqno_ms":1,"fallback_used":False,"exact_reference_ms":5,"exact_backend":"voxel_hardcut","exact_provenance":"independent voxel integral"}
        with self.assertRaises(ValueError):
            audit([row, dict(row)])

if __name__ == "__main__":
    unittest.main()
