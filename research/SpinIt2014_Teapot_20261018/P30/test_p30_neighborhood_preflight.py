"""P30 fail-closed controls: plan-only does not grant native or Newton admission."""
import json
import math
from pathlib import Path
import tempfile
import unittest
import p30_neighborhood_preflight as p30

C=[0.03640053031737869,-1.4100319353783204e-18,0.0,
   -0.2886365552481779,0.552377871982299,0.552377871982299,
   0.552377871982299,0.0,0.0,0.0]

def base():
    return {'c':C,
            'Jc':[[float(i==j) for j in range(10)] for i in range(10)],
            'pins':{'context_sha256':'a'*64},
            'saved_topology_hash':'b'*64,
            'saved_geometry_hash':'c'*64,
            'normalization':{'L':2.5716},'material_density_ref':1.0}

class P30Tangent(unittest.TestCase):
    def test_registered_real_native_c_sha(self):
        self.assertEqual(p30.canonical_hash(C),p30.C_SHA)
        self.assertLess(abs(math.sqrt(math.fsum(x*x for x in C))-1),1e-12)

    def test_unit_tangent_nine_dimensions(self):
        vectors=p30.gram_schmidt(C)
        self.assertEqual(len(vectors),9)
        for i,v in enumerate(vectors):
            self.assertLess(abs(math.fsum(a*b for a,b in zip(C,v))),1e-10)
            self.assertLess(abs(math.fsum(x*x for x in v)-1),1e-10)
            for prior in vectors[:i]:
                self.assertLess(abs(math.fsum(a*b for a,b in zip(v,prior))),1e-10)

    def test_plan_contains_only_unexecuted_real_coefficients(self):
        out=p30.plan(base())
        self.assertEqual(out['pilot_probe_count'],12)
        self.assertEqual(out['total_probe_count'],36)
        self.assertEqual(out['planned_native_evaluations'],36)
        self.assertEqual(out['completed_new_native_evaluations'],0)
        self.assertEqual(out['status'],'P30_PROBES_PLANNED_NOT_EVALUATED')
        self.assertIsNone(out['verified_feature_branch_sha256'])
        self.assertIsNone(out['W0_predeclared_max_normalized_jacobian_error'])
        self.assertIsNone(out['owner_approved_physical_tolerances'])
        for key in ('W0_owner_admitted','W2_teacher_training_allowed','Newton_accepted',
                    'native_derivative_neighborhood_certified','training_admissible'):
            self.assertIs(out[key],False)
        self.assertTrue(all(x['observed_material'] is None and x['sample_status']=='NOT_EVALUATED'
                            for x in out['probes']))
        self.assertEqual(sum(x['stage']=='PILOT_3_DIR' for x in out['probes']),12)

    def test_every_native_probe_matches_geodesic_formula(self):
        out=p30.plan(base());basis=out['tangent_basis_columns']
        for row in out['probes']:
            v=basis[row['direction_index']]
            angle=row['angle_radians']
            expected=[math.cos(angle)*a+math.sin(angle)*b for a,b in zip(C,v)]
            self.assertEqual(row['native_c'],expected)
            self.assertEqual(row['native_c_sha256'],p30.canonical_hash(expected))
            self.assertAlmostEqual(math.fsum(x*x for x in expected),1,places=12)

    def test_different_step_requires_a_new_plan(self):
        first=p30.plan(base(),step=0.002)
        other=p30.plan(base(),step=0.003)
        self.assertNotEqual(first['probes'][0]['native_c_sha256'],
                            other['probes'][0]['native_c_sha256'])
        self.assertEqual(first['scope'],other['scope'])

    def test_invalid_step_rejected(self):
        for step in (0.0,-1.0,0.101,float('inf'),float('nan'),1,True):
            with self.subTest(step=step),self.assertRaises(p30.PlanRejected):
                p30.plan(base(),step=step)

    def test_zero_or_nonunit_coefficients_rejected(self):
        for c in ([0.]*10,[0.5]*10,[0.]*9+[float('nan')],
                  [0.]*9+[True],['x']*10):
            with self.subTest(c=c),self.assertRaises(p30.PlanRejected):
                p30.gram_schmidt(c)

    def test_plan_retains_exact_parent_hashes(self):
        r=p30.plan(base())['evidence']
        self.assertEqual(r['archive_sha256'],p30.ARCHIVE_SHA)
        self.assertEqual(r['manifest_sha256'],p30.MANIFEST_SHA)
        self.assertEqual(r['lock_sha256'],p30.LOCK_SHA)
        self.assertEqual(r['base_native_c_sha256'],p30.C_SHA)
        self.assertEqual(r['same_call_Jc_binary_sha256'],p30.J_SHA)

    def test_tampered_or_missing_archive_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.tar.gz'
            p.write_bytes(b'fake-cherchi-result')
            with self.assertRaisesRegex(p30.PlanRejected,'PINNED_P27_ARCHIVE_MISMATCH'):
                p30.verify_archive(p)

    def test_json_duplicate_and_nonfinite_rejected(self):
        with self.assertRaisesRegex(p30.PlanRejected,'DUPLICATE_JSON_KEY'):
            p30.strict_json(b'{"x":1,"x":2}')
        with self.assertRaisesRegex(p30.PlanRejected,'NONFINITE'):
            p30.strict_json(b'{"x":NaN}')

    def test_no_fake_native_results_in_plan(self):
        text=json.dumps(p30.plan(base()))
        self.assertNotIn('NUMERIC_TANGENT_CHECK_PASS_SMOOTHNESS_NOT_PROVED',text)
        self.assertNotIn('smooth_neighborhood_certified": true',text)
        self.assertNotIn('training_admissible": true',text)

if __name__=='__main__':
    unittest.main()
