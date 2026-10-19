"""W3 H9 exact archived endpoint and conditional analytic interior event contracts."""
from __future__ import annotations

from fractions import Fraction as Q
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
from certify_h9_interior_edge_crossing import (
    UNIT, I, J, exact_line_witness, solve, file_sha, ZIP_SHA,
)

ARTIFACT=os.environ.get('H9_EVIDENCE_ZIP')


class InteriorEdgeWitnessTests(unittest.TestCase):
    def test_exact_projected_interior_intersection(self):
        a=(Q(0),Q(0),Q(0));b=(Q(1),Q(0),Q(0))
        c=(Q(1,2),Q(-1),Q(0));d=(Q(1,2),Q(1),Q(0))
        witness=exact_line_witness(a,b,c,d)
        self.assertEqual(witness['source_segment_parameter'],Q(1,2))
        self.assertEqual(witness['design_segment_parameter'],Q(1,2))
        self.assertEqual(witness['determinant'],0)
        self.assertEqual(witness['infinite_line_min_squared_distance'],0)
        tilted_c=(Q(1,2),Q(-1),Q(1,10**12))
        tilted_d=(Q(1,2),Q(1),Q(1,10**12))
        skew=exact_line_witness(a,b,tilted_c,tilted_d)
        self.assertEqual(skew['source_segment_parameter'],Q(1,2))
        self.assertEqual(skew['design_segment_parameter'],Q(1,2))
        self.assertEqual(skew['infinite_line_min_squared_distance'],Q(1,10**24))
        self.assertNotEqual(skew['determinant'],0)

    def test_non_parallel_and_outside_are_not_false_certs(self):
        with self.assertRaisesRegex(ValueError,'PARALLEL_EXACT_INPUT_EDGES'):
            exact_line_witness((Q(0),)*3,(Q(1),Q(0),Q(0)),(Q(0),Q(1),Q(0)),(Q(1),Q(1),Q(0)))
        w=exact_line_witness((Q(0),)*3,(Q(1),Q(0),Q(0)),(Q(2),Q(-1),Q(0)),(Q(2),Q(1),Q(0)))
        self.assertGreater(w['source_segment_parameter'],1)

    def test_interval_outward_including_negative_divisors(self):
        test_values=[Q(-5,13),Q(1,31),Q(-1,3),Q(9,7),Q(1,10**17)]
        for x in test_values:
            X=I.of(x)
            self.assertLessEqual(Q(X.lo,UNIT),x)
            self.assertGreaterEqual(Q(X.hi,UNIT),x)
            for y in test_values:
                Y=I.of(y)
                candidates=[(X+Y,x+y),(X-Y,x-y),(X*Y,x*y),(X/Y,x/y)]
                for bound,actual in candidates:
                    self.assertLessEqual(Q(bound.lo,UNIT),actual)
                    self.assertGreaterEqual(Q(bound.hi,UNIT),actual)
        for x in (Q(1,3),Q(2),Q(4),Q(1,10**14)):
            r=I.of(x).sqrt()
            self.assertLessEqual(Q(r.lo,UNIT)**2,x)
            self.assertGreaterEqual(Q(r.hi,UNIT)**2,x)
        self.assertFalse(I.between(-1,1).strictly_unit())
        with self.assertRaisesRegex(ValueError,'INTERVAL_DIVISION_BY_ZERO'):
            I.of(1)/I.between(-1,1)

    def test_jet_and_zero_denominator_guards(self):
        x=J.variable(Q(1),Q(2));y=x*x+1
        self.assertLessEqual(Q(y.d.lo,UNIT),2)
        self.assertGreaterEqual(Q(y.d.hi,UNIT),4)
        with self.assertRaisesRegex(ValueError,'INTERVAL_SQRT_OF_NEGATIVE'):
            I.of(-1).sqrt()
        with self.assertRaisesRegex(ValueError,'DERIVATIVE_SQRT_ZERO'):
            J.variable(Q(0),Q(1)).sqrt()

    def test_bad_zip_fails_closed_before_any_interpretation(self):
        with tempfile.TemporaryDirectory() as path:
            fake=Path(path)/'fake.zip'
            fake.write_bytes(b'fake 81 points')
            with self.assertRaisesRegex(ValueError,'UNTRUSTED_ARCHIVE_SHA256'):
                solve(fake)

    @unittest.skipUnless(ARTIFACT,'requires real GitHub Actions H8f artifact')
    def test_real_h8f_endpoint_and_analytic_interior_certificate(self):
        report=solve(Path(ARTIFACT))
        self.assertEqual(file_sha(Path(ARTIFACT)),ZIP_SHA)
        self.assertEqual(report['real_native_endpoint_indices'],[59,60])
        self.assertEqual(report['verified_material_sample_indices'],[0,57,58,59,60,61,62,63,64])
        left=report['exact_native_binary64_projected_line_witnesses']['59']
        right=report['exact_native_binary64_projected_line_witnesses']['60']
        self.assertGreater(left['signed_determinant']['approximate'],0)
        self.assertLess(right['signed_determinant']['approximate'],0)
        for row in (left,right):
            for param in ('source_parameter','design_parameter'):
                self.assertGreater(row[param]['approximate'],0)
                self.assertLess(row[param]['approximate'],1)
            self.assertGreater(row['infinite_line_min_squared_distance']['approximate'],0)
        for label in ('whole_interval_source_parameter_bound','whole_interval_design_parameter_bound',
                      'at_surrogate_root_source_parameter_bound','at_surrogate_root_design_parameter_bound'):
            bounds=report[label]
            self.assertGreater(bounds['lower'],0)
            self.assertLess(bounds['upper'],1)
        self.assertLess(report['whole_interval_event_derivative_bound']['upper'],0)
        self.assertGreater(report['whole_interval_cross_squared_bound']['lower'],0)
        self.assertLess(report['surrogate_root_interval_width'],1e-18)
        self.assertTrue(report['conditional_analytic_interior_edge_crossing_certified'])
        self.assertEqual(report['actual_in_between_native_boolean_samples_evaluated'],0)
        self.assertFalse(report['newton_admitted'])
        self.assertFalse(report['native_production_continuity_or_topology_certified'])
        # Cross-check with independently delivered Stage 3 proxy root bracket.
        prior=Path('/mnt/data/w3h9_stage3/reports/H9_ANALYTIC_EVENT_CERTIFICATE.json')
        if prior.is_file():
            third=json.loads(prior.read_text())
            self.assertEqual(report['surrogate_root_exact_interval'],[
                third['surrogate_root_bracket_binary64_anchor0']['exact_lower_fraction'],
                third['surrogate_root_bracket_binary64_anchor0']['exact_upper_fraction']])

if __name__=='__main__':unittest.main()
