"""W1 M17: original-original REAL cloud rerun scientific repeatability checks."""
from __future__ import annotations
import copy
import gzip
import json
from pathlib import Path
import sys
import unittest
from zipfile import ZipFile

sys.path.insert(0,str(Path(__file__).resolve().parent))
from m17_repeated_native_baseline import (
    EXPECTED, NATIVE_SHA, PREFIX, compare_material, numeric_matrix, verify_report, digest,
)


def fake():
    return dict(moment_jacobian=[[float(i==j) for j in range(10)] for i in range(10)],
                variable_raw_moments=[float(i) for i in range(10)],
                raw_moments=[float(i+1) for i in range(10)],
                geometry_hash='g',topology_hash='t',
                source_identity='same')


class M17Unit(unittest.TestCase):
    def test_same_original_exact_succeeds(self):
        x=fake();d=compare_material(x,copy.deepcopy(x))
        self.assertTrue(d['jacobian_bitwise_equal']);self.assertEqual(d['changed_jacobian_entries'],0)

    def test_subulp_jacobian_difference_is_reported_not_silenced(self):
        x=fake();y=copy.deepcopy(x);y['moment_jacobian'][0][0]=1.0000000000000002
        d=compare_material(x,y)
        self.assertFalse(d['jacobian_bitwise_equal'])
        self.assertEqual(d['changed_jacobian_entries'],1)
        self.assertTrue(d['nonjacobian_full_material_equivalent'])
        self.assertGreater(d['max_abs_jacobian_difference'],0)

    def test_jacobian_stays_full_10_by_10(self):
        x=fake();y=copy.deepcopy(x);y['moment_jacobian'][0]=[1.,2.]
        with self.assertRaisesRegex(ValueError,'JACOBIAN_SHAPE'):
            compare_material(x,y)

    def test_jacobian_nonfinite_denied(self):
        x=fake();y=copy.deepcopy(x);y['moment_jacobian'][5][7]=float('nan')
        with self.assertRaisesRegex(ValueError,'JACOBIAN_SHAPE'):
            compare_material(x,y)

    def test_exact_moment_changes_denied(self):
        x=fake();y=copy.deepcopy(x);y['variable_raw_moments'][3]+=1e-12
        with self.assertRaisesRegex(ValueError,'TEN_MOMENTS_NOT_BITWISE_EQUAL'):
            compare_material(x,y)

    def test_signed_zero_moment_drift_is_denied(self):
        x=fake();y=copy.deepcopy(x);y['raw_moments'][0]=-0.
        x['raw_moments'][0]=0.
        with self.assertRaisesRegex(ValueError,'TEN_MOMENTS_NOT_BITWISE_EQUAL'):
            compare_material(x,y)

    def test_geometry_and_provenance_drift_denied(self):
        x=fake();y=copy.deepcopy(x);y['geometry_hash']='different'
        with self.assertRaisesRegex(ValueError,'NONJACOBIAN_MATERIAL_DIFFERENCE'):
            compare_material(x,y)

    def test_missing_material_field_denied(self):
        x=fake();y=copy.deepcopy(x);y['unverified_entry']=False
        with self.assertRaisesRegex(ValueError,'MATERIAL_KEYS_DRIFT'):
            compare_material(x,y)

    def test_bitwise_nan_is_denied(self):
        self.assertRaisesRegex(ValueError,'JACOBIAN_SHAPE',numeric_matrix,
                               [[float('inf')]*10]*10)

    def test_report_cannot_promote_historical_failed_branch(self):
        template=dict(input_request_sha256='a'*64,**NATIVE_SHA,
          columns_requested=[0,4,8],target_q=[0.]*10,completed_samples=25,
          all_numerical_checks_passed=True,all_tested_stencils_same_feature_hash=False,
          changed_feature_hash_points=8,ambient_jacobian_shape=[10,10],
          formal_newton_converged=False,original_author_cad=False,
          analytic_10_by_10_jacobian=[[0.]*10]*10)
        self.assertTrue(verify_report(template,copy.deepcopy(template)))
        bad=copy.deepcopy(template);bad['all_tested_stencils_same_feature_hash']=True
        with self.assertRaisesRegex(ValueError,'FAILURE_STATUS_DRIFT'):
            verify_report(template,bad)

    def test_archive_digests_are_pinned_independently(self):
        self.assertEqual(len(EXPECTED),2)
        self.assertNotEqual(EXPECTED['attempt_1'],EXPECTED['attempt_2'])


class M17TrueArtifactBasePoint(unittest.TestCase):
    def test_one_real_unchanged_geometry_but_jittered_jacobian(self):
        root=Path('/mnt/data')
        paths=[root/'h8e-25point-39121571756.zip',
               root/'h8e-25point-rerun-attempt2-12275408088.zip']
        if not all(p.is_file() for p in paths):self.skipTest('archived ZIPs unavailable')
        items=[]
        for p in paths:
            with ZipFile(p) as z:
                blob=z.read(PREFIX+'point-000-material.json.gz')
                obj=json.loads(gzip.decompress(blob))
                items.append((digest(blob),obj))
        self.assertNotEqual(items[0][0],items[1][0])
        evidence=compare_material(items[0][1],items[1][1])
        self.assertTrue(evidence['nonjacobian_full_material_equivalent'])
        self.assertTrue(evidence['raw_moments_bitwise_equivalent'])
        self.assertGreater(evidence['changed_jacobian_entries'],0)
        self.assertLess(evidence['max_scaled_jacobian_difference'],1e-12)


class M17CloudHandoff(unittest.TestCase):
    def test_workflow_template_is_explicitly_inactive_and_pinned(self):
        template = (Path(__file__).resolve().parent /
                    'm17-w1-real-native-abba.workflow.template.yml').read_text()
        self.assertIn('INACTIVE HANDOFF',template)
        self.assertIn('research/neuralmoments-w1-native-20261019',template)
        self.assertIn('0bcc187b3005478baa586a6d6f450e73811ca342',template)
        self.assertIn('12132634988',template)
        self.assertIn('78749e99abd25ab2d2571440991ffa4e907a1565b4c7faf5210496431389cdd7',template)
        self.assertIn('m13_pinned_native_build.py',template)
        self.assertIn('m14_native_build_custody.py',template)
        self.assertIn('if: always()',template)
        self.assertNotIn('branches:\n      - main',template)
        try:
            import yaml
        except ImportError:
            return
        job=yaml.load(template,Loader=yaml.BaseLoader)
        self.assertEqual(list(job['on']),['workflow_dispatch'])
        self.assertEqual(job['jobs']['w1-native']['runs-on'],'ubuntu-24.04')


if __name__=='__main__':unittest.main()
