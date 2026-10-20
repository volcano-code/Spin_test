"""M18 fail-closed scientific diagnostics. Synthetic ABBA fixtures are NOT native."""
from __future__ import annotations
import copy
import gzip
from hashlib import sha256
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from m18_jacobian_repeatability import (
    SCHEMA, EXPECTED, jacobian_difference, canonical_nonjac_bytes,
    shadow_abba, _ordered_bits, diagnostic_original_rerun)
from m18_merge_slices import combine, pinned_original
from m9_native_abba_gate import certify_abba
from m18_native_shadow_cli import analyze as analyze_shadow_output


def jmatrix():
    return [[float(i==j) for j in range(10)] for i in range(10)]


def make_synthetic_abba(root:Path, *, jitter=True):
    files=[];rows=[]
    names=('original','candidate','candidate','original')
    for idx,mode in enumerate(names):
        jac=jmatrix()
        if jitter and idx in (1,2):
            jac[0][0]=math.nextafter(1.,2.)
        ten=[1.]+[0.]*9
        material=dict(variable_raw_moments=ten,raw_moments=ten,
                      moment_jacobian=jac,geometry_hash='g',topology_hash='t',
                      quadric_source_identity='source',exact_vertices=[['0/1']*3],
                      other_native_mat='unchanged')
        uncompressed=json.dumps(material,sort_keys=True,allow_nan=False).encode()
        path=root/f'sample-{idx}.json.gz'
        path.write_bytes(gzip.compress(uncompressed,mtime=0))
        files.append(path)
        stages=[{'name':'native:boolean','inclusive_ns':10,'exclusive_ns':10,'status':'PASS'}]
        for name in ('audit:same_call_material','audit:native_exact_rational_boundary',
                     'audit:independent_fraction_ten','audit:exact_material_serialization'):
            stages.append({'name':name,'inclusive_ns':4,'exclusive_ns':4,'status':'PASS'})
        rows.append(dict(mode=mode,geometry_hash='g',topology_hash='t',
                    source_identity='source',backend_identity='cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:',
                    q=[1.]+[0.]*9,ten=ten,jacobian=jac,
                    vertices=8455,faces=16910,native_sha256='1'*64,
                    cherchi_sha256='2'*64,gmp_sha256='3'*64,
                    boundary_flags={name:True for name in (
                        'boundary_valid','closed','edge_manifold','vertex_manifold',
                        'consistently_oriented','component_orientations_valid',
                        'self_intersection_completed','self_intersection_free')},
                    material_sha256=sha256(uncompressed).hexdigest(),
                    independent_ten_max_scaled_error=0.,
                    historical_ten_max_abs_error=0.,
                    same_call_passed=True,exact_geometry_audit_passed=True,
                    setup_ns=2,eval_wall_ns=50,complete_validation_ns=100,
                    stage_ledger=dict(wall_ns=100,exclusive_ns=26,
                                      unattributed_ns=74,all_returned=True,
                                      exclusive_stages=stages)))
    return rows,files


class M18Math(unittest.TestCase):
    def test_bitwise_identical_matrix(self):
        q=jmatrix(); self.assertEqual(jacobian_difference(q,copy.deepcopy(q))['changed_entries'],0)

    def test_one_ulp_is_measured_not_math_admitted(self):
        x=jmatrix();y=copy.deepcopy(x);y[0][0]=math.nextafter(1.,2.)
        r=jacobian_difference(x,y)
        self.assertEqual(r['changed_entries'],1)
        self.assertEqual(r['max_ulp_distance'],1)
        self.assertEqual(r['changed_by_output_row'][0],1)
        self.assertEqual(r['changed_by_input_column'][0],1)

    def test_negative_float_order(self):
        a=-1.;b=math.nextafter(a,0.)
        self.assertEqual(abs(_ordered_bits(a)-_ordered_bits(b)),1)

    def test_signed_zero_is_detected(self):
        x=jmatrix();y=copy.deepcopy(x);x[1][2]=0.;y[1][2]=-0.
        self.assertEqual(jacobian_difference(x,y)['changed_entries'],1)

    def test_bad_jacobian_shape_denied(self):
        with self.assertRaisesRegex(ValueError,'FULL_FINITE_JACOBIAN'):
            jacobian_difference(jmatrix(),[[1.]])

    def test_nan_jacobian_denied(self):
        x=jmatrix();x[7][7]=float('nan')
        with self.assertRaisesRegex(ValueError,'FULL_FINITE_JACOBIAN'):
            jacobian_difference(jmatrix(),x)

    def test_nonjacobian_fingerprint_excludes_only_j(self):
        a=dict(moment_jacobian=jmatrix(),source='actual',mass=[1,2,3])
        b=copy.deepcopy(a);b['moment_jacobian'][0][0]=math.nextafter(1.,2.)
        self.assertEqual(canonical_nonjac_bytes(a),canonical_nonjac_bytes(b))
        b['mass'][0]=2
        self.assertNotEqual(canonical_nonjac_bytes(a),canonical_nonjac_bytes(b))


class M18Shadow(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.rows,self.files=make_synthetic_abba(Path(self.tmp.name))

    def test_shadow_detects_realistic_jitter_but_never_admits(self):
        r=shadow_abba(self.rows,self.files)
        self.assertTrue(r['nonjacobian_material_and_ten_exact_all_four'])
        self.assertFalse(r['material_sha_bitwise_all_four'])
        self.assertFalse(r['jacobian_bitwise_all_four'])
        self.assertFalse(r['eligible_for_w1_production_speed_claim'])
        self.assertIsNone(r['w0_approved_jacobian_tolerance'])
        with self.assertRaisesRegex(ValueError,'SCIENTIFIC_OUTPUT_DRIFT'):
            certify_abba(self.rows)

    def test_inactive_cloud_handoff_preserves_native_failure_and_saves_shadow(self):
        text=(HERE/'m17-w1-real-native-abba.workflow.template.yml').read_text()
        self.assertIn('INACTIVE HANDOFF',text)
        self.assertIn('m18_native_shadow_cli.py',text)
        self.assertIn('if: always()',text)
        self.assertIn('m18-shadow-exit.txt',text)
        self.assertIn('m13_pinned_native_build.py',text)
        self.assertNotIn('pull_request:',text)

    def test_without_jitter_is_still_not_release(self):
        rows,paths=make_synthetic_abba(Path(self.tmp.name),jitter=False)
        r=shadow_abba(rows,paths)
        self.assertTrue(r['jacobian_bitwise_all_four'])
        self.assertFalse(r['eligible_for_w1_production_speed_claim'])

    def test_wrong_order_denied(self):
        a=copy.deepcopy(self.rows);a[1]['mode']='original'
        with self.assertRaisesRegex(ValueError,'ORDER'):
            shadow_abba(a,self.files)

    def test_exact_ten_drift_denied(self):
        a=copy.deepcopy(self.rows);a[2]['ten'][0]=1.0000000000000002
        with self.assertRaisesRegex(ValueError,'TEN_VECTOR'):
            shadow_abba(a,self.files)

    def test_source_provenance_drift_denied(self):
        a=copy.deepcopy(self.rows);a[2]['source_identity']='forged'
        with self.assertRaisesRegex(ValueError,'SOURCE_IDENTITY_DRIFT'):
            shadow_abba(a,self.files)

    def test_missing_native_exact_boundary_denied(self):
        a=copy.deepcopy(self.rows);a[1]['boundary_flags']['self_intersection_free']=False
        with self.assertRaisesRegex(ValueError,'BOUNDARY_FLAGS'):
            shadow_abba(a,self.files)

    def test_skipped_independent_fraction_denied(self):
        a=copy.deepcopy(self.rows)
        a[1]['stage_ledger']['exclusive_stages'][3]['name']='no_fraction'
        with self.assertRaisesRegex(ValueError,'AUDITS_MISSING'):
            shadow_abba(a,self.files)

    def test_wall_forgery_denied(self):
        a=copy.deepcopy(self.rows);a[1]['complete_validation_ns']=70
        with self.assertRaisesRegex(ValueError,'TIMING_NOT_SAME_WINDOW'):
            shadow_abba(a,self.files)

    def test_missing_binary_sha_denied(self):
        a=copy.deepcopy(self.rows);a[1]['gmp_sha256']='unverified'
        with self.assertRaisesRegex(ValueError,'BINARY_IDENTITY'):
            shadow_abba(a,self.files)

    def test_saved_snapshot_tamper_denied(self):
        mat=json.loads(gzip.decompress(self.files[1].read_bytes()))
        mat['other_native_mat']='tampered'
        self.files[1].write_bytes(gzip.compress(json.dumps(mat,sort_keys=True).encode(),mtime=0))
        with self.assertRaisesRegex(ValueError,'MATERIAL_NOT_BOUND'):
            shadow_abba(self.rows,self.files)

    def test_fake_signed_jacobian_denied(self):
        a=copy.deepcopy(self.rows);a[1]['jacobian'][0][0]+=0.1
        with self.assertRaisesRegex(ValueError,'JACOBIAN_NOT_ACTUALLY_SAVED'):
            shadow_abba(a,self.files)

    def test_duplicate_json_keys_denied(self):
        raw=gzip.decompress(self.files[2].read_bytes()).decode()
        tampered=raw[:-1]+',"extra":1,"extra":2}'
        self.files[2].write_bytes(gzip.compress(tampered.encode(),mtime=0))
        a=copy.deepcopy(self.rows);a[2]['material_sha256']=sha256(tampered.encode()).hexdigest()
        with self.assertRaisesRegex(ValueError,'DUPLICATE_JSON_KEY'):
            shadow_abba(a,self.files)


class M18FailedNativeHandoff(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.rows,paths=make_synthetic_abba(self.root)
        for index,(row,source) in enumerate(zip(self.rows,paths)):
            variant=row['mode']
            stem=f'point-{index:03d}-{variant}'
            (self.root/(stem+'.json')).write_text(
                json.dumps(dict(row,iteration=index),allow_nan=False))
            (self.root/(stem+'.json.gz')).write_bytes(source.read_bytes())
        self.fail=dict(schema='w1-m9-fail-closed-v1',
            status='BLOCKED_OR_FAILED_NO_NATIVE_ABBA_CERTIFICATE',
            completed_points=4,stage='REAL_CHERCHI_ABBA',
            error='M9_ABBA_SCIENTIFIC_OUTPUT_DRIFT_AT_1')
        (self.root/'failure.json').write_text(json.dumps(self.fail))

    def test_full_four_saved_failures_can_be_diagnosed_but_not_admitted(self):
        d=analyze_shadow_output(self.root)
        self.assertEqual(d['saved_call_count'],4)
        self.assertFalse(d['W1_production_speedup_admitted'])
        self.assertFalse(d['science_diagnostic']['jacobian_bitwise_all_four'])
        self.assertTrue(d['original_strict_m9_failure_unchanged'])

    def test_missing_original_failure_fails_closed(self):
        (self.root/'failure.json').unlink()
        with self.assertRaisesRegex(ValueError,'M9_JSON_MISSING'):
            analyze_shadow_output(self.root)

    def test_three_points_never_pretend_four_native_calls(self):
        (self.root/'point-003-original.json').unlink()
        with self.assertRaisesRegex(ValueError,'M9_JSON_MISSING'):
            analyze_shadow_output(self.root)

    def test_nonmatching_saved_failure_count_rejected(self):
        self.fail['completed_points']=3
        (self.root/'failure.json').write_text(json.dumps(self.fail))
        with self.assertRaisesRegex(ValueError,'FULL_FOUR_SAVED'):
            analyze_shadow_output(self.root)

    def test_wrong_index_rejected(self):
        p=self.root/'point-001-candidate.json'
        row=json.loads(p.read_text());row['iteration']=17;p.write_text(json.dumps(row))
        with self.assertRaisesRegex(ValueError,'WRONG_SAVED_CALL'):
            analyze_shadow_output(self.root)

    def test_nonfinite_json_rejected(self):
        p=self.root/'point-001-candidate.json'
        row=p.read_text().replace('"eval_wall_ns": 50','"eval_wall_ns": NaN')
        p.write_text(row)
        with self.assertRaisesRegex(ValueError,'NONFINITE'):
            analyze_shadow_output(self.root)


class M18TrueCloudReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=HERE/'evidence'
        cls.files=sorted(cls.root.glob('m18-slice-[0-9][0-9]-[0-9][0-9].json'))
        cls.prior=cls.root/'m17-crossrun-25point.json'
        if len(cls.files)!=6 or not cls.prior.is_file():
            raise AssertionError('M18_REAL_CLOUD_SLICES_NOT_READY')

    def test_all_25_real_samples_merge_and_remain_blocked(self):
        r=combine(self.files,self.prior)
        self.assertEqual(r['complete_real_native_points'],25)
        self.assertEqual(r['jacobian_bitwise_unequal_elements'],1096)
        self.assertEqual(r['jacobian_max_abs_difference'],1.7763568394002505e-15)
        self.assertFalse(r['production_cherchi_ABBA_executed'])
        self.assertIsNone(r['w0_approved_jacobian_comparison'])

    def test_one_slice_missing_denied(self):
        with self.assertRaisesRegex(ValueError,'MISSING_REAL_CLOUD'):
            combine(self.files[:-1],self.prior)

    def test_duplicate_slice_denied(self):
        with self.assertRaisesRegex(ValueError,'DUPLICATE_POINT'):
            combine([*self.files,self.files[0]],self.prior)

    def test_one_changed_entry_forgery_denied(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'tampered.json'
            obj=json.loads(self.files[0].read_text())
            obj['entries'][0]['jacobian_changed_elements']+=1
            p.write_text(json.dumps(obj))
            with self.assertRaisesRegex(ValueError,'JACOBIAN_DATA'):
                combine([p,*self.files[1:]],self.prior)

    def test_claimed_W0_release_denied(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'claim.json'
            obj=json.loads(self.files[0].read_text())
            obj['w0_approved_jacobian_tolerance']=1e-12
            p.write_text(json.dumps(obj))
            with self.assertRaisesRegex(ValueError,'INADMISSIBLE'):
                combine([p,*self.files[1:]],self.prior)

    def test_original_git_blob_pinned(self):
        self.assertEqual(pinned_original(self.prior)['jacobian_bitwise_unequal_entries_across_2500'],1096)

    def test_source_receipt_edit_denied(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'fake.json';p.write_text(self.prior.read_text()+'\n')
            with self.assertRaisesRegex(ValueError,'PRECOMMITTED'):
                pinned_original(p)


if __name__=='__main__':unittest.main()
