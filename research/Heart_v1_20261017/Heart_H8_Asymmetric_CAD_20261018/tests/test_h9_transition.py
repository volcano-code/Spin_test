"""H9 native/live boundary and original 81-point signed-event regression."""
from fractions import Fraction
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE=Path(__file__).resolve().parents[1]/'source'
sys.path.insert(0,str(SOURCE))
from locate_h9_transition import locate, exact_secant, adjacent_face_ids
from probe_h9_transition_live import live_probe

ARCHIVE=os.environ.get('H9_EVIDENCE_ZIP')


class HeartH9TransitionTests(unittest.TestCase):
    def test_exact_secant_requires_opposite_signs(self):
        self.assertEqual(exact_secant(Fraction(1),Fraction(3),Fraction(3),Fraction(-1)),Fraction(5,2))
        with self.assertRaisesRegex(ValueError,'NO_OBSERVED_SIGN_BRACKET'):
            exact_secant(Fraction(1),Fraction(3),Fraction(3),Fraction(1))
        with self.assertRaisesRegex(ValueError,'NO_OBSERVED_SIGN_BRACKET'):
            exact_secant(Fraction(3),Fraction(1),Fraction(3),Fraction(-1))

    def test_expected_edge_incidence_not_many_or_one(self):
        faces=[[0,1,2],[1,0,3],[4,5,6]]
        self.assertEqual(adjacent_face_ids(faces,(0,1)),[(0,(0,1,2)),(1,(0,1,3))])

    def test_unverified_archive_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fake.zip';p.write_bytes(b'fabricated')
            with self.assertRaisesRegex(ValueError,'NOT_FROZEN_ACTIONS_ARTIFACT_ZIP_SHA256'):
                locate(p)

    @unittest.skipUnless(ARCHIVE,'set H9_EVIDENCE_ZIP to original Actions ZIP')
    def test_archived_sample_edge_event_sign_flip_and_moments(self):
        report=locate(Path(ARCHIVE))
        rows=report['real_archived_samples']
        self.assertEqual(len(rows),9)
        self.assertEqual([x['index'] for x in rows],[0,57,58,59,60,61,62,63,64])
        self.assertEqual([(x['index'],x['det_source24_90_design5517_5518']['sign']) for x in rows],
                         [(0,1),(57,1),(58,1),(59,1),(60,-1),(61,1),(62,1),(63,1),(64,1)])
        self.assertEqual(report['measured_opposite_sign_endpoints']['lower_index'],59)
        self.assertEqual(report['measured_opposite_sign_endpoints']['upper_index'],60)
        self.assertGreater(report['secant_predicted_c7_not_certified_event'],1.5e-6)
        self.assertLess(report['secant_predicted_c7_not_certified_event'],3e-6)
        self.assertLess(report['archived_finite_secant_59_to_60']['max_scaled_deviation_from_base_jacobian'],2e-5)
        self.assertFalse(report['continuous_smooth_neighborhood_proven'])
        self.assertEqual(report['new_native_calls_this_run'],0)
        self.assertFalse(report['newton_admitted'])

    @unittest.skipUnless(ARCHIVE,'set H9_EVIDENCE_ZIP to original Actions ZIP')
    def test_native_probe_fails_closed_when_extension_is_absent(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'live'
            # An absent extension cannot silently select floating surrogate or cached material.
            with patch.dict(sys.modules,{'_make_it_stand':None}):
                with self.assertRaisesRegex(RuntimeError,'REAL_NATIVE_CHERCHI_DEPENDENCIES_UNAVAILABLE_NO_FALLBACK'):
                    live_probe(Path(ARCHIVE),out)
            result=json.loads((out/'failure.json').read_text())
            self.assertEqual(result['failed_stage'],'LOAD_NATIVE_CHERCHI_BINARY')
            self.assertEqual(result['native_calls_completed'],0)
            self.assertFalse(result['newton_admitted'])
            self.assertFalse((out/'report.json').exists())


if __name__=='__main__':
    unittest.main()
