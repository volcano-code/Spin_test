"""H9 exact arithmetic and frozen-artifact regression (stdlib unittest)."""
from fractions import Fraction
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'source' / 'audit_h9_branch_decision.py'
spec = importlib.util.spec_from_file_location('heart_h9_branch_decision', SOURCE)
h9 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h9)


class HeartH9BranchDecisionTests(unittest.TestCase):
    def test_det4_is_exact_and_detects_distinct_planes(self):
        origin = (Fraction(0),) * 3
        x, y, z = ((Fraction(1), Fraction(0), Fraction(0)),
                   (Fraction(0), Fraction(1), Fraction(0)),
                   (Fraction(0), Fraction(0), Fraction(1, 10**18)))
        self.assertEqual(h9.det4(origin, x, y, z), Fraction(1, 10**18))
        self.assertEqual(h9.det4(origin, x, y, origin), 0)
        self.assertEqual(h9.sign(-Fraction(1, 10**50)), -1)

    def test_frozen_artifact_digest_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / 'fake.zip'
            fake.write_bytes(b'not the GitHub Actions artifact')
            with self.assertRaisesRegex(ValueError, 'NOT_FROZEN_ACTIONS_ARTIFACT_ZIP_SHA256'):
                h9.replay(fake)

    @unittest.skipUnless(os.environ.get('H9_EVIDENCE_ZIP'), 'set H9_EVIDENCE_ZIP to actual Actions artifact')
    def test_real_actions_81_point_archive_sample60_replay(self):
        result = h9.replay(Path(os.environ['H9_EVIDENCE_ZIP']))
        self.assertEqual(result['replayed_indices'], [0, 57, 59, 60, 62, 64])
        self.assertEqual(result['sample_60_first_difference']['changed_face_slot_count'], 434)
        self.assertEqual(result['sample_60_first_difference']['removed_semantic_triangles'], 17)
        self.assertEqual(result['sample_60_first_difference']['added_semantic_triangles'], 17)
        self.assertEqual(result['decision'], 'DENY_CHERCHI_FASTER_NEWTON_ADMISSION')
        witness = result['sample_60_exact_rational_counterexample']
        self.assertEqual(witness['trial_lpi_8043_on_new_source_facet']['sign'], 0)
        self.assertEqual(witness['trial_lpi_8043_off_old_source_facet']['sign'], 1)
        self.assertEqual(witness['trial_lpi_8044_on_new_design_facet']['sign'], 0)
        self.assertEqual(witness['trial_lpi_8044_off_old_design_facet']['sign'], -1)
        self.assertFalse(result['continuous_smooth_neighborhood_proven'])
        self.assertFalse(result['boolean_set_discontinuity_proven'])


if __name__ == '__main__':
    unittest.main()
