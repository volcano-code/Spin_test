import unittest

from h9_m21_6d_quarterpoint_plan import (
    EXPECTED_STEMS, PlanRejected, make_quarterpoint_plan,
)
from h9_stage19_multiscale import b64_same, midpoint


def qrow(stem, c7, shift=0.0):
    q = [0.125 + i * 0.03125 + shift for i in range(10)]
    q[7] = c7
    return {'stem': stem, 'q': q}


def fixture():
    return [
        qrow('side-00-left-coarse', 1.0e-6),
        qrow('side-01-left-near', 1.4e-6),
        qrow('side-02-right-near', 2.0e-6),
        qrow('side-03-right-coarse', 2.4e-6),
        qrow('m19-mid-00-left-mid', 1.2e-6),
        qrow('m19-mid-01-right-mid', 2.2e-6),
    ]


class QuarterpointPlanTests(unittest.TestCase):
    def test_six_input_stem_contract(self):
        self.assertEqual(tuple(x['stem'] for x in fixture()), EXPECTED_STEMS)

    def test_exactly_four_points_in_deterministic_order(self):
        out = make_quarterpoint_plan(fixture())
        self.assertEqual(out['point_count'], 4)
        self.assertEqual(
            [x['interval'] for x in out['points']],
            ['left-coarse-to-mid', 'left-mid-to-near',
             'right-near-to-mid', 'right-mid-to-coarse'])

    def test_midpoints_use_binary64_exact_midpoint_round_once(self):
        out = make_quarterpoint_plan(fixture())
        expected = [
            midpoint(1.0e-6, 1.2e-6),
            midpoint(1.2e-6, 1.4e-6),
            midpoint(2.0e-6, 2.2e-6),
            midpoint(2.2e-6, 2.4e-6),
        ]
        for point, value in zip(out['points'], expected):
            self.assertTrue(b64_same(point['c7'], value))
            self.assertTrue(b64_same(point['q'][7], value))

    def test_all_points_strictly_inside_declared_segments(self):
        samples = fixture()
        by_stem = {x['stem']: x['q'][7] for x in samples}
        out = make_quarterpoint_plan(samples)
        for point in out['points']:
            self.assertLess(by_stem[point['from_stem']], point['c7'])
            self.assertLess(point['c7'], by_stem[point['to_stem']])

    def test_non_c7_coefficients_are_bitwise_preserved(self):
        samples = fixture()
        out = make_quarterpoint_plan(samples)
        for point in out['points']:
            left = next(x['q'] for x in samples if x['stem'] == point['from_stem'])
            right = next(x['q'] for x in samples if x['stem'] == point['to_stem'])
            for k in range(10):
                if k != 7:
                    self.assertTrue(b64_same(point['q'][k], left[k]))
                    self.assertTrue(b64_same(point['q'][k], right[k]))

    def test_left_and_right_event_signs_are_not_conflated(self):
        out = make_quarterpoint_plan(fixture())
        self.assertEqual([x['expected_proxy_event_sign'] for x in out['points']],
                         [1, 1, -1, -1])

    def test_refuses_changed_sample_order(self):
        samples = fixture()
        samples[0], samples[1] = samples[1], samples[0]
        with self.assertRaisesRegex(PlanRejected, 'SIX_SAMPLE_STEM_ORDER_CHANGED'):
            make_quarterpoint_plan(samples)

    def test_refuses_nonmonotone_same_side_c7(self):
        samples = fixture()
        samples[4]['q'][7] = 1.5e-6
        with self.assertRaisesRegex(PlanRejected, 'SAME_SIDE_C7_ORDER_INVALID:left'):
            make_quarterpoint_plan(samples)

    def test_refuses_non_c7_coefficient_drift(self):
        samples = fixture()
        samples[5]['q'][3] += 1e-12
        with self.assertRaisesRegex(PlanRejected, 'NON_C7_COEFFICIENT_CHANGED'):
            make_quarterpoint_plan(samples)

    def test_refuses_nonfinite_coefficients(self):
        samples = fixture()
        samples[2]['q'][4] = float('nan')
        with self.assertRaisesRegex(PlanRejected, 'NONFINITE_COEFFICIENT_VECTOR'):
            make_quarterpoint_plan(samples)

    def test_newton_and_smoothness_remain_denied(self):
        out = make_quarterpoint_plan(fixture())
        self.assertFalse(out['newton_admitted'])
        self.assertFalse(out['continuous_neighborhood_certified'])
        self.assertFalse(out['asymptotic_order_certified'])
        self.assertEqual(out['new_boolean_calls_executed'], 0)
        self.assertEqual(out['new_native_source_calls_executed'], 0)


if __name__ == '__main__':
    unittest.main()
