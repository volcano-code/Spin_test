import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from p29_validate_generation_tasks import validate


class P29GenerationTaskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads(
            (ROOT / "p29_1_generation_tasks.json").read_text()
        )

    def test_exact_100_candidate_source_balance(self):
        result = validate(self.document)
        self.assertEqual(result["candidate_count"], 100)
        self.assertEqual(result["unique_lineages"], 100)
        self.assertEqual(result["status"], "VALID_PLAN_ONLY_NOT_GENERATED")

    def test_physical_labels_are_not_fabricated(self):
        for task in self.document["tasks"]:
            self.assertEqual(task["physical_label_status"], "pending")

    def test_adversarial_assets_are_ood_only(self):
        for task in self.document["tasks"]:
            if task["source_type"] == "adversarial_topology":
                self.assertEqual(task["intended_track"], "robustness_ood")

    def test_duplicate_task_ids_are_rejected(self):
        bad = dict(self.document)
        bad["tasks"] = list(self.document["tasks"])
        bad["tasks"][1] = dict(bad["tasks"][1])
        bad["tasks"][1]["task_id"] = bad["tasks"][0]["task_id"]
        with self.assertRaises(ValueError):
            validate(bad)


if __name__ == "__main__":
    unittest.main()
