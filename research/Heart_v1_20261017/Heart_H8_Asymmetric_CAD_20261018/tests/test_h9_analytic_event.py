"""Exact fixed-point outward rounding + genuine H8f artifact-only H9 regression."""
from __future__ import annotations

from fractions import Fraction as F
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
from certify_h9_analytic_edge_event import (
    Interval, Jet, SCALE, bisect, load_evidence, solve,
)


class H9AnalyticIntervalContracts(unittest.TestCase):
    def test_rational_outward_rounding_add_mul_div(self):
        fractions=[F(0),F(1,17),F(-7,9),F(31,10**17),F(-13,3)]
        for x in fractions:
            X=Interval.const(x)
            self.assertLessEqual(F(X.lo,SCALE),x)
            self.assertGreaterEqual(F(X.hi,SCALE),x)
            for y in fractions:
                Y=Interval.const(y)
                expected=[(X+Y,x+y),(X-Y,x-y),(X*Y,x*y)]
                if y:
                    expected.append((X/Y,x/y))
                for interval,truth in expected:
                    self.assertLessEqual(F(interval.lo,SCALE),truth)
                    self.assertGreaterEqual(F(interval.hi,SCALE),truth)

    def test_sqrt_outward_and_derivative_interval(self):
        for x in [F(1,3),F(2),F(4),F(1,10**12)]:
            bound=Interval.const(x).sqrt()
            self.assertLessEqual(F(bound.lo,SCALE)**2,x)
            self.assertGreaterEqual(F(bound.hi,SCALE)**2,x)
        x=Jet.variable(F(1),F(2))
        y=x*x+1
        self.assertLessEqual(F(y.derivative.lo,SCALE),F(2))
        self.assertGreaterEqual(F(y.derivative.hi,SCALE),F(4))

    def test_refuses_divide_by_zero_and_negative_sqrt(self):
        with self.assertRaisesRegex(ValueError,'INTERVAL_DIVISION_BY_ZERO'):
            Interval.const(1) / Interval.between(-1,1)
        with self.assertRaisesRegex(ValueError,'NEGATIVE_SQUARE_ROOT_INTERVAL'):
            Interval.const(-1).sqrt()

    def test_wrong_zip_refused(self):
        with tempfile.TemporaryDirectory() as d:
            fake=Path(d)/'not_the_artifact.zip';fake.write_bytes(b'fabricated H8f material')
            with self.assertRaisesRegex(ValueError,'ARTIFACT_ZIP_SHA_DRIFT'):
                solve(fake)

    @unittest.skipUnless(os.environ.get('H9_EVIDENCE_ZIP'), 'requires actual 81-point Actions artifact')
    def test_real_81_point_archive_derivative_and_unique_surrogate_root(self):
        report=solve(Path(os.environ['H9_EVIDENCE_ZIP']))
        self.assertEqual(report['archive_samples_verified'],[0,57,58,59,60,61,62,63,64])
        self.assertEqual(report['archived_coordinate_comparisons'],108)
        self.assertLess(report['max_model_vs_actual_archived_coordinate_absolute_error'],2e-14)
        self.assertEqual(report['verified_surrogate_continuous_derivative_sign'],-1)
        self.assertLess(report['verified_surrogate_derivative_enclosure'][1],0)
        self.assertTrue(report['conditional_surrogate_unique_root'])
        bracket=report['surrogate_root_bracket_binary64_anchor0']
        self.assertLess(bracket['lower'],2.280586229e-6)
        self.assertGreater(bracket['upper'],2.280586228e-6)
        self.assertLess(bracket['width_float'],1e-18)
        self.assertLess(report['surrogate_root_anchor_estimate_spread_float'],1e-15)
        self.assertFalse(report['actual_native_cherchi_boolean_event_certified'])
        self.assertFalse(report['newton_admitted'])
        self.assertEqual(report['native_calls_performed_this_run'],0)
        self.assertFalse(report['final_heart_obj_produced'])


if __name__=='__main__':
    unittest.main()
