"""M20 tests: analytic/storage fixtures plus OPTIONAL genuine historical H8f.
No fixture is represented as a new native Boolean evaluation.
"""
from __future__ import annotations
import copy
from fractions import Fraction as F
import gzip
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
import h9_m20_precision_replay as m


def tetra():
    return {'variable_rational_vertices':[['0/1','0/1','0/1'],['1/1','0/1','0/1'],
             ['0/1','1/1','0/1'],['0/1','0/1','1/1']],
            'variable_faces':[[0,2,1],[0,1,3],[0,3,2],[1,2,3]]}


def row(x,value,derivative):
    return {'c7':float(x),'moments':[float(value)]*10,'exact':[F(value)]*10,
            'j7':[float(derivative)]*10}


def write(path,obj):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(obj,allow_nan=False,sort_keys=True)+'\n')


def fixture(root):
    """Fabricate ONLY a storage protocol fixture for non-native code paths."""
    old=root/'old';r19=root/'m19';native=r19/'native-two-midpoints'/'two-midpoint-native'
    old.mkdir();native.mkdir(parents=True)
    binary={'core':'a'*64,'boolean':'b'*64,'arithmetic':'c'*64};identity='d'*64
    moments=[float(v) for v in m.exact_surface_moments(tetra())]
    old_rows=[];aud_rows=[];base=[1.,0.,0.,0.,1.,1.,1.,0.,0.,0.]
    for i,(side,x) in enumerate(zip(m.SIDES,(2.18e-6,2.27e-6,2.29e-6,2.38e-6))):
        q=list(base);q[7]=x
        sha=packet(old,f'side-{i:02d}-{side}',i,side,q,moments,binary,identity,False)
        old_rows.append({'index':i,'side':side,'q':q,'c7':x,'moments':moments,'j7':[0.]*10,'material_sha256':sha})
        aud_rows.append({'index':i,'side':side,'c7':x,'new_same_call_material_sha256':sha,
                         'recomputed_exact_moments':moments,'native_recorded_jacobian_col7':[0.]*10})
    write(old/'report.json',{'binary_hashes':binary,'fixture_not_native':True})
    a18={'new_native_samples_reintegrated':4,'newton_admitted':False,
         'finite_symbolic_branch_split_at_new_four_samples':True,'sample_diagnostics':aud_rows,
         'new_native_evaluation_map_identity':identity,'new_native_run_report_sha256':m.file_hash(old/'report.json'),
         'fixture_not_native':True}
    a18_path=root/'a18.json';write(a18_path,a18);a18sha=m.file_hash(a18_path)
    proposals=[];new_records=[]
    for i,(lo,hi) in enumerate(((0,1),(2,3))):
        q=list(base);q[7]=float((F.from_float(old_rows[lo]['c7'])+F.from_float(old_rows[hi]['c7']))/2)
        side=m.MID_SIDES[i]
        proposals.append({'index':i,'side':side,'q':q,'c7':q[7]})
        h=packet(native,f'm19-mid-{i:02d}-{side}',i,side,q,moments,binary,identity,True)
        new_records.append({'index':i,'side':side,'sha256':h,'exact_symbolic_side_validated':True,
                            'independent_ten_moments_verified':True,'native_boolean_identity_bound':True})
    plan={'schema':'heart-h9-m19-two-midpoints-plan-v1','stage18_independent_audit_sha256':a18sha,
          'stage17_real_producer_report_sha256':m.file_hash(old/'report.json'),
          'stage17_current_binary_sha256':binary,'stage18_current_evaluation_map_identity':identity,
          'baseline_four_real_rows':old_rows,'predeclared_two_midpoints':proposals,'fixture_not_native':True}
    write(r19/'midpoint-plan.json',plan)
    write(native/'report.json',{'plan_sha256':m.file_hash(r19/'midpoint-plan.json'),
                               'binary_hashes':binary,'fixture_not_native':True})
    launch={'status':'TWO_NEW_NATIVE_MIDPOINTS_INDEPENDENTLY_VERIFIED_NO_NEWTON',
            'worker_exit_code':0,'audit_exit_code':0,'new_qualified_midpoints':2,'newton_admitted':False,
            'source_contract':{'head_sha':m.M19_HEAD},'fixture_not_native':True}
    write(native.parent/'launch_result.json',launch)
    empty={'trapezoid_errors_by_component':{n:0. for n in m.NAMES}}
    refinement={'schema':'heart-h9-m19-finite-refinement-diagnostics-v1','original_m18_audit_sha256':a18sha,
                'new_native_run_report_sha256':m.file_hash(native/'report.json'),
                'new_real_midpoint_materials_independently_verified':2,
                'newton_admitted':False,'continuous_neighborhood_certified':False,
                'new_midpoint_packets':new_records,'two_refined_sides':[
                    {'full_interval':empty,'two_half_intervals':[empty,empty]} for _ in range(2)],
                'fixture_not_native':True}
    write(native.parent/'independent-refinement.json',refinement)
    return a18_path,old,r19,a18sha


def packet(folder,stem,index,side,q,moments,binary,identity,mid):
    data=tetra()
    data.update(quadric_coefficients=q,evaluation_map_identity=identity,
                boolean_backend_identity='cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'+binary['boolean'],
                rational_arithmetic_identity={'module_sha256':binary['arithmetic'],'backend':'NATIVE_GMP_SURFACE_V1'},
                material_proof={'schema':'cherchi-same-call-material-v1'},
                moment_jacobian=[[0.]*10 for _ in range(10)],variable_raw_moments=moments,
                fixture_not_native=True)
    packed=folder/(stem+'.json.gz');packed.write_bytes(gzip.compress(json.dumps(data).encode(),mtime=0))
    h=m.file_hash(packed)
    meta={'index':index,'side':side,'c7':q[7],'q':q,'material_sha256':h,
          'native_geometry_valid':True,'newton_admitted':False,'fixture_not_native':True}
    if mid:meta.update(independent_ten_raw_moments=moments,moment_jacobian_column7=[0.]*10)
    write(folder/(stem+'.json'),meta)
    return h


class PrecisionReplayTests(unittest.TestCase):
    def test_unit_tetrahedron_exact_ten(self):
        self.assertEqual(m.exact_surface_moments(tetra()),
                         [F(1,6),F(1,24),F(1,24),F(1,24),F(1,60),F(1,60),F(1,60),F(1,120),F(1,120),F(1,120)])

    def test_binary_rational_grammar(self):
        self.assertEqual(m.rational('-0b101/0b10'),F(-5,2))
        for value in ('1/0','nan','0b2/1','1/-1','1.0/2'):
            with self.subTest(value=value),self.assertRaises(ValueError):m.rational(value)

    def test_open_mesh_rejected(self):
        mat=tetra();mat['variable_faces'].pop()
        with self.assertRaisesRegex(ValueError,'OPEN_NONMANIFOLD'):m.exact_surface_moments(mat)

    def test_quadratic_trapezoid_exact(self):
        out=m.side_ledger(row(0,F(0),0),row(.5,F(1,4),1),row(1,F(1),2))
        self.assertEqual(out['full_interval']['max_exact_surface_scaled_error'],0.)
        self.assertIsNone(out['exact_surface_worst_half_over_full'])
        self.assertFalse(out['newton_admitted'])

    def test_cubic_true_second_order_unscaled_component(self):
        out=m.side_ledger(row(0,F(0),0),row(.5,F(1,8),.75),row(1,F(1),3))
        # Common scaling can differ per interval. Verify unscaled residuals.
        full=abs(out['full_interval']['components']['mass']['exact_surface_signed_residual'])
        halves=[abs(x['components']['mass']['exact_surface_signed_residual']) for x in out['two_half_intervals']]
        self.assertEqual(full/max(halves),4.)
        self.assertFalse(out['asymptotic_order_certified'])

    def test_midpoint_noise_cancels_in_full_interval(self):
        out=m.side_ledger(row(0,F(1),0),row(.5,F(1)+F(1,10**15),0),row(1,F(1),0))
        c=out['signed_cancellation_ledger']['Mzz']
        self.assertTrue(c['opposite_half_residual_signs'])
        self.assertEqual(c['weighted_cancellation_fraction'],0.)
        self.assertEqual(c['full_residual'],0.)

    def test_rounding_ledger_and_exact_float_conversion_not_recovery(self):
        a=row(0,F(1),0);b=row(1e-8,F(1)+F(1,10**17),0)
        out=m.interval_ledger(a,b)['components']['mass']
        self.assertEqual(out['binary64_secant'],0.)
        self.assertEqual(out['exact_arithmetic_on_saved_floats_secant'],0.)
        self.assertGreater(out['exact_surface_secant'],0.)
        self.assertTrue(out['exact_residual_decomposition_verified'])
        self.assertTrue(out['observed_moment_rounding_within_half_ulp_bound'])
        self.assertLess(out['rounded_moment_input_contribution_signed'],0.)

    def test_unequal_halves_partition_identity(self):
        out=m.side_ledger(row(0,F(1),2),row(.3,F(5,4),3),row(1,F(2),4))
        self.assertTrue(all(x['exact_partition_identity_verified'] for x in out['signed_cancellation_ledger'].values()))

    def test_duplicate_json_key_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'a.json';p.write_text('{"a":1,"a":2}')
            with self.assertRaisesRegex(ValueError,'DUPLICATE_JSON_KEY'):m.read_json(p)

    def test_full_synthetic_six_packet_replay_and_no_input_mutation(self):
        with tempfile.TemporaryDirectory() as t:
            args=fixture(Path(t));before={str(p):m.file_hash(p) for p in Path(t).rglob('*') if p.is_file()}
            with patch.object(m,'BASELINE_M18_SHA',args[3]):out=m.replay(*args[:3])
            after={str(p):m.file_hash(p) for p in Path(t).rglob('*') if p.is_file()}
            self.assertEqual(before,after)
            self.assertEqual(out['saved_materials_reintegrated'],6)
            self.assertEqual(out['new_native_calls_this_run'],0)
            self.assertFalse(out['newton_admitted'])
            self.assertFalse(out['native_geometry_generation_roundoff_removed'])

    def test_packet_corruption_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            args=fixture(Path(t));bad=args[1]/'side-00-left-coarse.json.gz'
            bad.write_bytes(bad.read_bytes()+b'bad')
            with patch.object(m,'BASELINE_M18_SHA',args[3]):
                with self.assertRaisesRegex(ValueError,'MATERIAL_SHA_MISMATCH'):m.replay(*args[:3])

    def test_wrong_stage18_audit_not_accepted(self):
        with tempfile.TemporaryDirectory() as t:
            args=fixture(Path(t))
            with self.assertRaisesRegex(ValueError,'STAGE18_AUDIT_SHA_MISMATCH'):m.replay(*args[:3])

    @unittest.skipUnless(os.environ.get('H9_EVIDENCE_ZIP'),'requires genuine historical H8f ZIP')
    def test_real_historical_sample59_integration_not_new_native(self):
        archive=Path(os.environ['H9_EVIDENCE_ZIP'])
        self.assertEqual(m.file_hash(archive),'99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9')
        with zipfile.ZipFile(archive) as z:
            stem='artifacts/h8f-all81-points/point-059'
            point=json.loads(z.read(stem+'.json'));raw=z.read(stem+'-material.json.gz')
            self.assertEqual(sha256(raw).hexdigest(),point['exact_same_call_material_archive_sha256'])
            mat=json.loads(gzip.decompress(raw))
        exact=m.exact_surface_moments(mat)
        self.assertEqual([float(x) for x in exact],point['independent_variable_raw_moments'])


if __name__=='__main__':unittest.main()
