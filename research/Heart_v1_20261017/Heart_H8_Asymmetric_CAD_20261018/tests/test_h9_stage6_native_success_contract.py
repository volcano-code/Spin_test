"""Stage6: exercise the formerly unreachable genuine-material success path.

The true sample-59 material is used only as an archived fixture. No test
claims this is a new native 4-point execution or authorizes Newton.
"""
from __future__ import annotations

import copy
import gzip
import json
import os
from pathlib import Path
import sys
import unittest
import zipfile

SRC = Path(__file__).resolve().parents[1] / 'source'
sys.path.insert(0, str(SRC))
from audit_h9_new_native_sides import validate_new_same_call_numerics
from h9_one_sided_derivative_audit import one_sided_diagnostics

ZIP = os.environ.get('H9_EVIDENCE_ZIP')


def make_rows():
    ts = (2.18e-6, 2.27e-6, 2.29e-6, 2.38e-6)
    sides = ('left-coarse', 'left-near', 'right-near', 'right-coarse')
    output = []
    for i, (t, side) in enumerate(zip(ts, sides)):
        slope = 3. if i < 2 else 5.
        output.append({'index':i,'side':side,'c7':t,
                       'recomputed_exact_moments':[1. + slope * t] * 10,
                       'native_recorded_jacobian_col7':[slope] * 10})
    return output


class IndependentPairDiagnosticTests(unittest.TestCase):
    def test_two_linear_same_side_slopes_pass_without_newton(self):
        result = one_sided_diagnostics(make_rows(),same_symbolic_left=True,same_symbolic_right=True)
        self.assertEqual(result['schema'],'heart-h9-two-sided-finite-jacobian-diagnostics-v1')
        self.assertTrue(result['both_finite_pairs_same_symbolic_support'])
        for item, expected in zip(result['finite_same_side_pairs'], [3.,5.]):
            self.assertAlmostEqual(item['independently_reintegrated_ten_moment_secant'][0],expected,places=7)
            self.assertLess(item['max_scaled_difference_vs_first_native_jacobian'],1e-8)
            self.assertFalse(item['qualified_continuous_smooth_branch'])
        self.assertFalse(result['newton_admitted'])
        self.assertFalse(result['cross_event_secant_is_smooth_derivative'])

    def test_pair_finite_semantic_change_does_not_certify_smoothness(self):
        result=one_sided_diagnostics(make_rows(),same_symbolic_left=False,same_symbolic_right=True)
        self.assertFalse(result['both_finite_pairs_same_symbolic_support'])
        self.assertFalse(result['finite_same_side_pairs'][0]['finite_pair_exact_symbolic_patch_identity_same'])
        self.assertFalse(result['newton_admitted'])

    def test_nonmonotone_q_rejected(self):
        rows=make_rows()
        rows[1]['c7']=rows[0]['c7']
        with self.assertRaisesRegex(ValueError,'NATIVE_SIDE_POINTS_NOT_STRICTLY_ORDERED'):
            one_sided_diagnostics(rows,same_symbolic_left=True,same_symbolic_right=True)

    def test_missing_packet_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'FOUR_FRESH_NATIVE_SIDE_ROWS_REQUIRED'):
            one_sided_diagnostics(make_rows()[:3],same_symbolic_left=True,same_symbolic_right=True)

    def test_nan_in_reintegrated_moments_rejected(self):
        rows=make_rows();rows[1]['recomputed_exact_moments'][4]=float('nan')
        with self.assertRaisesRegex(ValueError,'MISSING_REINTEGRATED_TEN_MOMENTS'):
            one_sided_diagnostics(rows,same_symbolic_left=True,same_symbolic_right=True)

    def test_nonboolean_same_support_not_accepted(self):
        with self.assertRaisesRegex(ValueError,'MISSING_EXACT_FINITE_PAIR_SEMANTICS'):
            one_sided_diagnostics(make_rows(),same_symbolic_left=1,same_symbolic_right=True)

    def test_wrong_side_order_rejected(self):
        rows=make_rows();rows[0]['side']='right-coarse'
        with self.assertRaisesRegex(ValueError,'UNEXPECTED_EVENT_SIDE_ORDER'):
            one_sided_diagnostics(rows,same_symbolic_left=True,same_symbolic_right=True)


@unittest.skipUnless(ZIP,'requires original real H8f Actions evidence')
class GenuineArchivedMaterialSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with zipfile.ZipFile(ZIP) as z:
            cls.material=json.loads(gzip.decompress(z.read('artifacts/h8f-all81-points/point-059-material.json.gz')))
            cls.point=json.loads(z.read('artifacts/h8f-all81-points/point-059.json'))
        cls.metadata={'independent_ten_mass_moments':cls.point['independent_variable_raw_moments'],
                      'independent_scaled_moment_error':cls.point['independent_moments_max_scaled_error'],
                      'native_moment_jacobian_column7':[row[7] for row in cls.material['moment_jacobian']]}

    def test_real_historical_packet_numerics_schema_reaches_success_path(self):
        result=validate_new_same_call_numerics(self.material,self.metadata)
        self.assertEqual(result['edge_structure']['triangle_count'],16910)
        self.assertEqual(result['edge_structure']['manifold_edges_checked'],25365)
        self.assertEqual(result['max_scaled_error_vs_archived_production'],0.)
        # This tests schema/reintegration, never four *new* native calls.

    def test_real_packet_wrong_material_raw_moment_fails(self):
        forged=copy.deepcopy(self.material)
        forged['variable_raw_moments'][0]+=0.01
        with self.assertRaisesRegex(ValueError,'NEW_NATIVE_SAVED_AND_PRODUCTION_TEN_MOMENT_MISMATCH'):
            validate_new_same_call_numerics(forged,self.metadata)

    def test_real_packet_full_jacobian_other_column_nan_fails(self):
        forged=copy.deepcopy(self.material)
        forged['moment_jacobian'][6][4]=float('nan')
        # This previously went unchecked, because only column seven was validated.
        with self.assertRaisesRegex(ValueError,'NEW_NATIVE_FULL_10X10_JACOBIAN_INVALID'):
            validate_new_same_call_numerics(forged,self.metadata)

    def test_real_packet_misreported_same_call_jacobian_fails(self):
        forged=copy.deepcopy(self.metadata)
        forged['native_moment_jacobian_column7'][1]+=1.e-3
        with self.assertRaisesRegex(ValueError,'NEW_NATIVE_JACOBIAN_COLUMN_NOT_FROM_SAME_MATERIAL'):
            validate_new_same_call_numerics(self.material,forged)

    def test_real_packet_forged_scaled_error_fails(self):
        forged=copy.deepcopy(self.metadata)
        forged['independent_scaled_moment_error']=0.01
        with self.assertRaisesRegex(ValueError,'NEW_NATIVE_INDEPENDENT_MOMENT_ERROR_NOT_REPRODUCED'):
            validate_new_same_call_numerics(self.material,forged)


if __name__=='__main__':
    unittest.main()
