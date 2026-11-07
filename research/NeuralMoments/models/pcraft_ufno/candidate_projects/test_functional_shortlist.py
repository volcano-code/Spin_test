"""Validates exhaustive W6 31-project functional shortlist vs frozen catalog."""
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parent
REGISTRY=json.loads((ROOT/"catalog.json").read_text())
SCREEN=json.loads((ROOT/"functional_shortlist_20261107.json").read_text())

class FunctionalSelectionTests(unittest.TestCase):
    def test_exhaustive_31_ids_no_duplicate(self):
        original=[x["id"] for x in REGISTRY["entries"]]
        reviewed=[x["id"] for x in SCREEN["items"]]
        self.assertEqual(len(reviewed),31)
        self.assertEqual(len(set(reviewed)),31)
        self.assertEqual(set(reviewed),set(original))
        self.assertEqual(SCREEN["counts"]["reviewed"],31)

    def test_only_pcraft_primary_backbone(self):
        core=[x for x in SCREEN["roles"] if x["tier"]=="CORE"]
        self.assertEqual(len(core),1)
        self.assertEqual(core[0]["project"],"p-craft-source")
        self.assertTrue(SCREEN["constraints"]["PINO_primary_only"])

    def test_primary_roles_have_source_ids_and_reuse_license(self):
        ids={x["id"]:x for x in SCREEN["items"]}
        for role in SCREEN["roles"]:
            self.assertIn(role["project"],ids)
            if role["tier"]=="P0":
                self.assertNotIn("LICENSE_HOLD",ids[role["project"]]["decision"])
                self.assertNotIn(ids[role["project"]]["license_from_audit"],
                  ("NO_ROOT_LICENSE_FOUND","REPOSITORY_IDENTITY_NOT_VERIFIED"))
        self.assertEqual(len(set(r["role"] for r in SCREEN["roles"])),len(SCREEN["roles"]))

    def test_negative_ablation_cannot_be_promoted(self):
        ids={x["id"]:x for x in SCREEN["items"]}
        for item in ("transolver-plus","tensorpils-preconditioned-pino"):
            self.assertTrue(ids[item]["decision"].startswith("NEGATIVE"))
        self.assertTrue(SCREEN["constraints"]["negative_ablation_preserved"])

    def test_all_prohibited_claims_are_false(self):
        self.assertTrue(all(v is False for v in SCREEN["prohibited_claims"].values()))

if __name__=="__main__":
    unittest.main()
