import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))

from h9_m21_6d_quarterpoints import (
    SAME, branch_status_is_valid, capture_stem, source_signature_matches,
    validate_point_contract,
)
from h9_m21_6d_quarterpoint_plan import (
    SCHEMA, STATUS, make_quarterpoint_plan,
)


def qrow(stem, c7, shift=0.0):
    q = [0.125 + i * 0.03125 + shift for i in range(10)]
    q[7] = c7
    return {'stem': stem, 'q': q}


def plan_fixture():
    samples = [
        qrow('side-00-left-coarse', 1.0e-6),
        qrow('side-01-left-near', 1.4e-6),
        qrow('side-02-right-near', 2.0e-6),
        qrow('side-03-right-coarse', 2.4e-6),
        qrow('m19-mid-00-left-mid', 1.2e-6),
        qrow('m19-mid-01-right-mid', 2.2e-6),
    ]
    plan = make_quarterpoint_plan(samples)
    plan['schema'] = SCHEMA
    plan['status'] = STATUS
    return plan


class QuarterpointNativeRunnerContractTests(unittest.TestCase):
    def test_four_predeclared_rows_are_accepted(self):
        plan = plan_fixture()
        for index in range(4):
            self.assertEqual(validate_point_contract(plan, index)['index'], index)

    def test_left_point_zero_interval_identity(self):
        point = validate_point_contract(plan_fixture(), 0)
        self.assertEqual(point['interval'], 'left-coarse-to-mid')
        self.assertEqual(point['expected_proxy_event_sign'], 1)

    def test_left_point_one_interval_identity(self):
        point = validate_point_contract(plan_fixture(), 1)
        self.assertEqual(point['interval'], 'left-mid-to-near')
        self.assertEqual(point['expected_proxy_event_sign'], 1)

    def test_right_point_two_interval_identity(self):
        point = validate_point_contract(plan_fixture(), 2)
        self.assertEqual(point['interval'], 'right-near-to-mid')
        self.assertEqual(point['expected_proxy_event_sign'], -1)

    def test_right_point_three_interval_identity(self):
        point = validate_point_contract(plan_fixture(), 3)
        self.assertEqual(point['interval'], 'right-mid-to-coarse')
        self.assertEqual(point['expected_proxy_event_sign'], -1)

    def test_capture_stems_are_unique_and_not_historical_side_names(self):
        stems = [capture_stem(validate_point_contract(plan_fixture(), i))
                 for i in range(4)]
        self.assertEqual(len(stems), len(set(stems)))
        self.assertTrue(all(x.startswith('q') for x in stems))
        self.assertTrue(all('side-00-left-coarse' not in x for x in stems))

    def test_refuses_wrong_index(self):
        with self.assertRaisesRegex(ValueError, 'QUARTERPOINT_INDEX_OUT_OF_RANGE'):
            validate_point_contract(plan_fixture(), 4)

    def test_refuses_plan_row_interval_tamper(self):
        plan = plan_fixture()
        plan['points'][2]['interval'] = 'left-mid-to-near'
        with self.assertRaisesRegex(ValueError, 'QUARTERPOINT_PLAN_ROW_IDENTITY_CHANGED'):
            validate_point_contract(plan, 2)

    def test_refuses_q_c7_mismatch(self):
        plan = plan_fixture()
        plan['points'][1]['q'][7] += 1e-12
        with self.assertRaisesRegex(ValueError, 'QUARTERPOINT_C7_Q_MISMATCH'):
            validate_point_contract(plan, 1)

    def test_refuses_nonfinite_q(self):
        plan = plan_fixture()
        plan['points'][0]['q'][2] = float('nan')
        with self.assertRaisesRegex(ValueError, 'QUARTERPOINT_Q_INVALID'):
            validate_point_contract(plan, 0)

    def test_left_branch_requires_left_anchor_only(self):
        self.assertTrue(branch_status_is_valid('left', SAME, 'CONSTRUCTION_CHANGED'))
        self.assertFalse(branch_status_is_valid('left', SAME, SAME))
        self.assertFalse(branch_status_is_valid('left', 'CONSTRUCTION_CHANGED', SAME))

    def test_right_branch_requires_right_anchor_only(self):
        self.assertTrue(branch_status_is_valid('right', 'CONSTRUCTION_CHANGED', SAME))
        self.assertFalse(branch_status_is_valid('right', SAME, SAME))
        self.assertFalse(branch_status_is_valid('right', SAME, 'CONSTRUCTION_CHANGED'))

    def test_source_signature_must_match_both_interval_endpoints(self):
        sig = {'surface_type': 'A', 'cap_face_count': 12, 'source_normal_edges': [[1, 2]]}
        self.assertTrue(source_signature_matches(sig, sig, sig))
        self.assertFalse(source_signature_matches(sig, sig, {'surface_type': 'B'}))

    def test_source_signature_normalizes_native_tuples_to_json_lists(self):
        native = {'surface_type': 1, 'source_normal_edges': ((1, 2), (3, 4))}
        saved = {'surface_type': 1, 'source_normal_edges': [[1, 2], [3, 4]]}
        self.assertTrue(source_signature_matches(native, saved, saved))

    def test_all_plan_rows_keep_newton_denied(self):
        plan = plan_fixture()
        self.assertFalse(plan['newton_admitted'])
        self.assertFalse(plan['continuous_neighborhood_certified'])
        self.assertFalse(plan['asymptotic_order_certified'])


if __name__ == '__main__':
    unittest.main()
