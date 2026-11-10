import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from p29_geometry_manifest import validate_manifest, validate_record


def valid_trellis_record():
    return {
        "asset_id": "trellis-bracket-0001",
        "lineage_id": "prompt-bracket-001",
        "source_type": "trellis_v1",
        "raw_asset_path": "raw/trellis/bracket-0001.glb",
        "raw_asset_sha256": "a" * 64,
        "units": "mm",
        "bbox_extent": [120.0, 48.0, 32.0],
        "transform_4x4": [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        "topology_class": "closed_manifold",
        "watertight": True,
        "winding_consistent": True,
        "self_intersections": False,
        "connected_components": 1,
        "volume": 184320.0,
        "density_kg_m3": 1200.0,
        "intended_track": "supervised_solid",
        "license": "generated; model checkpoint and prompt provenance recorded",
        "label_status": "pending",
        "generator_version": "TRELLIS-main-commit-placeholder",
        "checkpoint_id": "microsoft/TRELLIS-image-large",
        "generation_seed": 42,
    }


class P29GeometryManifestTests(unittest.TestCase):
    def test_valid_trellis_solid_passes_manifest_contract(self):
        row = valid_trellis_record()
        self.assertEqual(validate_record(row), [])
        report = validate_manifest([row])
        self.assertEqual(report["accepted_count"], 1)
        self.assertEqual(report["rejected_count"], 0)
        self.assertTrue(report["claims"]["accepted_means_manifest_contract_only"])

    def test_open_surface_cannot_enter_supervised_solid_track(self):
        row = valid_trellis_record()
        row["topology_class"] = "open_surface"
        row["watertight"] = False
        errors = validate_record(row)
        self.assertIn("solid_track_requires_closed_topology", errors)
        self.assertIn("solid_track_requires_watertight", errors)

    def test_open_surface_is_allowed_only_on_ood_track_without_solid_label(self):
        row = valid_trellis_record()
        row.update({
            "topology_class": "open_surface",
            "watertight": False,
            "intended_track": "robustness_ood",
            "label_status": "pending",
        })
        self.assertEqual(validate_record(row), [])

    def test_missing_generator_provenance_is_rejected(self):
        row = valid_trellis_record()
        del row["checkpoint_id"]
        self.assertIn("missing_generation_provenance:checkpoint_id", validate_record(row))

    def test_repaired_asset_requires_derived_hash_and_tool_version(self):
        row = valid_trellis_record()
        row["repair_applied"] = True
        errors = validate_record(row)
        self.assertIn("repair_requires_tool_and_version", errors)
        self.assertIn("repair_requires_derived_asset_sha256", errors)

    def test_duplicate_asset_ids_are_reported(self):
        row = valid_trellis_record()
        second = dict(row)
        second["lineage_id"] = "different-lineage"
        report = validate_manifest([row, second])
        self.assertEqual(report["accepted_count"], 1)
        self.assertEqual(report["rejected_count"], 1)
        self.assertIn("duplicate:asset_id", report["rejected"][0]["errors"])


if __name__ == "__main__":
    unittest.main()
