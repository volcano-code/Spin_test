"""W3 M19 scientific guard tests; NO new Cherchi native call or Newton step."""
from __future__ import annotations

import copy
import gzip
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

SRC=Path(__file__).resolve().parents[1]/'source'
sys.path.insert(0,str(SRC))
import h9_stage19_multiscale as m19
import h9_stage19_native_midpoints as native


BIN={'core':'a'*64,'boolean':'b'*64,'arithmetic':'c'*64}
MAP='d'*64
SIDES=m19.SIDES
BACKEND='cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'+BIN['boolean']


def fixture():
    root=[0.1,-0.02,0.03,-0.04,0.05,-0.06,0.07,0.,0.,-0.0]
    ts=[2.1805862283444328e-6,2.2705862283444327e-6,
        2.2905862283444326e-6,2.3805862283444325e-6]
    rows=[]
    for i,x in enumerate(ts):
        q=list(root);q[7]=x
        rows.append({'index':i,'side':SIDES[i],'c7':x,'q':q,
                     'moments':[x+x*x for _ in range(10)],
                     'j7':[1+2*x for _ in range(10)],'material_sha256':'x'*64})
    return rows


def synthetic_producer(folder):
    baseline=fixture();records=[];plan=[]
    for r in baseline:
        i=r['index'];side=r['side']
        material={'quadric_coefficients':list(r['q']),
                  'evaluation_map_identity':MAP,
                  'boolean_backend_identity':BACKEND,
                  'rational_arithmetic_identity':{'backend':'NATIVE_GMP_SURFACE_V1',
                                                   'module_sha256':BIN['arithmetic']},
                  'material_proof':{'schema':'cherchi-same-call-material-v1'},
                  'variable_raw_moments':r['moments']}
        raw=gzip.compress(json.dumps(material).encode())
        digest=sha256(raw).hexdigest()
        name=f'side-{i:02d}-{side}'
        (folder/(name+'.json.gz')).write_bytes(raw)
        (folder/(name+'.json')).write_text(json.dumps({'index':i,'side':side,
             'c7':r['c7'],'q':r['q'],'material_sha256':digest}))
        records.append({'index':i,'side':side,'c7':r['c7'],
                        'new_same_call_material_sha256':digest,
                        'recomputed_exact_moments':r['moments'],
                        'native_recorded_jacobian_col7':r['j7']})
        plan.append({'index':i,'side':side,'c7':r['c7']})
    report={'schema':'heart-h9-crossing-sides-live-v1',
            'status':'FOUR_FRESH_REAL_SAMPLES_EVALUATED_NOT_SMOOTH_OR_NEWTON_CERTIFIED',
            'finished_indices':[0,1,2,3],'new_real_native_calls':4,
            'binary_hashes':BIN,'plan':plan,'newton_admitted':False}
    aud={'schema':'heart-h9-independent-new-side-material-audit-v1',
         'new_native_samples_reintegrated':4,
         'finite_symbolic_branch_split_at_new_four_samples':True,
         'every_new_side_reproduces_expected_oriented_edge_sign':True,
         'newton_admitted':False,'continuous_native_boolean_smooth_stratum_proven':False,
         'sample_diagnostics':records,'new_native_evaluation_map_identity':MAP}
    return baseline,report,aud


class M19Numerics(unittest.TestCase):
    def test_midpoints_are_strictly_interior_binary64_and_same_side(self):
        rows=fixture();mid=m19.make_midpoint_plan(rows)
        self.assertEqual([x['side'] for x in mid],list(m19.MID_SIDES))
        self.assertEqual([x['expected_proxy_event_sign'] for x in mid],[1,-1])
        for k,(i,j) in enumerate(((0,1),(2,3))):
            self.assertLess(rows[i]['c7'],mid[k]['c7'])
            self.assertLess(mid[k]['c7'],rows[j]['c7'])
            self.assertEqual(mid[k]['c7_binary64_hex'],__import__('struct').pack('!d',mid[k]['c7']).hex())
            for c in range(10):
                if c!=7:self.assertTrue(m19.b64_same(rows[i]['q'][c],mid[k]['q'][c]))

    def test_only_event_coefficient_may_change(self):
        rows=fixture();rows[1]['q'][3]+=1e-4
        with self.assertRaisesRegex(m19.M19Rejected,'OTHER_COEFFICIENT_DIFFERS'):
            m19.make_midpoint_plan(rows)

    def test_shuffled_or_missing_old_rows_rejected(self):
        rows=fixture();rows[0],rows[1]=rows[1],rows[0]
        with self.assertRaisesRegex(m19.M19Rejected,'BASELINE_SIDE_ORDER_CHANGED'):
            m19.make_midpoint_plan(rows)
        with self.assertRaisesRegex(m19.M19Rejected,'FOUR_BASELINE_ROWS_REQUIRED'):
            m19.make_midpoint_plan(fixture()[:3])

    def test_binary64_ulp_and_signed_zero_distinguished(self):
        v=fixture()[0]['c7']
        self.assertFalse(m19.b64_same(v,math.nextafter(v,math.inf)))
        self.assertFalse(m19.b64_same(-0.0,0.0))
        self.assertFalse(m19.b64_same(True,1.0))
        self.assertFalse(m19.b64_same(float('nan'),float('nan')))

    def test_trapezoid_error_decreases_quadratically_for_cubic(self):
        step=1e-6
        def row(x,index,side):
            t=x/step
            return {'index':index,'side':side,'c7':x,
                    'moments':[0.01*step*t**3]*10,'j7':[0.03*t*t]*10}
        a,b,c=row(0.,0,'left-coarse'),row(step,1,'left-mid'),row(2*step,2,'left-near')
        whole=m19.trapezoid_error(a,c)
        halves=[m19.trapezoid_error(a,b),m19.trapezoid_error(b,c)]
        self.assertAlmostEqual(whole['max_trapezoid_scaled_error'],0.02,places=12)
        self.assertAlmostEqual(max(x['max_trapezoid_scaled_error'] for x in halves),0.005,places=12)

    def test_constant_linear_moments_have_zero_trapezoid_error(self):
        a={'c7':0.,'moments':[1.]*10,'j7':[1.]*10}
        b={'c7':1e-7,'moments':[1.+1e-7]*10,'j7':[1.]*10}
        self.assertLess(m19.trapezoid_error(a,b)['max_trapezoid_scaled_error'],1e-8)

    def test_compare_refinement_retains_newton_denial_and_two_scales(self):
        old=fixture();plan={'schema':m19.SCHEMA,'newton_admitted':False,
                             'baseline_four_real_rows':old,
                             'predeclared_two_midpoints':m19.make_midpoint_plan(old)}
        new=[]
        for p in plan['predeclared_two_midpoints']:
            x=p['c7'];new.append({'index':p['index'],'side':p['side'],'c7':x,
                                'moments':[x+x*x]*10,'j7':[1+2*x]*10})
        answer=m19.compare_refinement(plan,new)
        self.assertEqual(len(answer['two_refined_sides']),2)
        self.assertFalse(answer['newton_admitted'])
        self.assertFalse(answer['continuous_neighborhood_certified'])
        self.assertEqual([x['side'] for x in answer['two_refined_sides']],['left','right'])
        for item in answer['two_refined_sides']:
            self.assertEqual(len(item['two_half_intervals']),2)

    def test_compare_refinement_rejects_midpoint_on_wrong_side(self):
        old=fixture();plan={'schema':m19.SCHEMA,'newton_admitted':False,
                             'baseline_four_real_rows':old,
                             'predeclared_two_midpoints':m19.make_midpoint_plan(old)}
        new=[{'index':i,'side':p['side'],'c7':p['c7'],
              'moments':[1.]*10,'j7':[0.]*10} for i,p in enumerate(plan['predeclared_two_midpoints'])]
        new[0]['c7']=old[2]['c7']
        with self.assertRaisesRegex(m19.M19Rejected,'NEW_SIDE_IDENTITY_WRONG'):
            m19.compare_refinement(plan,new)

    def test_duplicate_json_and_nonfinite_json_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'bad.json';p.write_text('{"a":1,"a":2}')
            with self.assertRaisesRegex(m19.M19Rejected,'DUPLICATED_JSON_KEY'):m19.read_json(p)
            p.write_text('{"a":NaN}')
            with self.assertRaisesRegex(m19.M19Rejected,'NONFINITE_JSON_CONSTANT'):m19.read_json(p)


class M19BaselineForensics(unittest.TestCase):
    def test_four_real_sides_sha_and_q_bound_in_test_fixture(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);base,report,aud=synthetic_producer(root)
            rows,hashes=m19.make_science_rows(aud,report,root,fixture()[0]['q'][:7]+[0]+fixture()[0]['q'][8:])
            self.assertEqual(len(rows),4);self.assertEqual(hashes,BIN)
            self.assertEqual([x['side'] for x in rows],list(SIDES))

    def test_one_changed_material_byte_is_rejected(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);base,report,aud=synthetic_producer(root)
            p=root/'side-00-left-coarse.json.gz'
            p.write_bytes(p.read_bytes()+b'X')
            with self.assertRaisesRegex(m19.M19Rejected,'MATERIAL_SHA_NOT_BOUND'):
                m19.make_science_rows(aud,report,root,base[0]['q'][:7]+[0]+base[0]['q'][8:])

    def test_one_ulp_tampered_q_rejected(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);base,report,aud=synthetic_producer(root)
            p=root/'side-00-left-coarse.json'
            data=json.loads(p.read_text());data['q'][1]=math.nextafter(data['q'][1],math.inf)
            p.write_text(json.dumps(data))
            with self.assertRaisesRegex(m19.M19Rejected,'SAME_CALL_FULL_Q_NOT_BOUND'):
                m19.make_science_rows(aud,report,root,base[0]['q'][:7]+[0]+base[0]['q'][8:])

    def test_non_matching_map_identity_rejected(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);base,report,aud=synthetic_producer(root)
            aud['new_native_evaluation_map_identity']='f'*64
            with self.assertRaisesRegex(m19.M19Rejected,'UNBOUND_CURRENT_NATIVE_PROVENANCE'):
                m19.make_science_rows(aud,report,root,base[0]['q'][:7]+[0]+base[0]['q'][8:])

    def test_incomplete_or_fake_four_point_report_rejected(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);base,report,aud=synthetic_producer(root)
            report['finished_indices']=[0,1,2]
            with self.assertRaisesRegex(m19.M19Rejected,'PRODUCER_REPORT_NOT_COMPLETE'):
                m19.make_science_rows(aud,report,root,base[0]['q'][:7]+[0]+base[0]['q'][8:])


class M19ForensicPublishing(unittest.TestCase):
    def test_same_call_unverified_capture_does_not_qualify_newton(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            q=[0.]*10;q[7]=2.225586228344433e-6
            plan={'index':0,'side':'left-mid','q':q}
            material={'quadric_coefficients':tuple(q),
                      'boolean_backend_identity':BACKEND,
                      'material_proof':{'schema':'cherchi-same-call-material-v1'}}
            proof,path=native._save_unverified(folder,plan,material,BACKEND)
            self.assertFalse(proof['newton_admitted'])
            self.assertEqual(native.file_hash(path),proof['archive_sha256'])
            self.assertTrue((folder/'m19-mid-00-left-mid.unverified.json').is_file())
            self.assertFalse((folder/'m19-mid-00-left-mid.json').exists())
            self.assertFalse((folder/'report.json').exists())
            with self.assertRaisesRegex(m19.M19Rejected,'DESTINATION_ALREADY_EXISTS'):
                native._save_unverified(folder,plan,material,BACKEND)

    def test_ulp_mutation_rejected_before_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);q=[0.]*10;q[7]=2e-6
            corrupted=list(q);corrupted[7]=math.nextafter(q[7],math.inf)
            with self.assertRaisesRegex(m19.M19Rejected,'PRODUCER_FULL_Q_MISMATCH'):
                native._save_unverified(folder,{'index':0,'side':'left-mid','q':q},
                     {'quadric_coefficients':tuple(corrupted),
                      'boolean_backend_identity':BACKEND,
                      'material_proof':{'schema':'cherchi-same-call-material-v1'}},BACKEND)
            self.assertEqual(list(folder.iterdir()),[])

    def test_exclusive_publish_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            first=native._exclusive_file(folder,'m19.json',b'original')
            with self.assertRaisesRegex(m19.M19Rejected,'DESTINATION_ALREADY_EXISTS'):
                native._exclusive_file(folder,'m19.json',b'changed')
            self.assertEqual(first.read_bytes(),b'original')

    def test_run_preflight_blocks_before_any_cherychi_binary_import(self):
        from prepare_h9_pinned_native import check_runtime
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            args=SimpleNamespace(output=folder/'blocked',repo=folder/'not-a-repo',
                artifact='missing',certificate='missing',stage18_audit='missing',
                stage17_native_dir='missing',plan='missing',build_evidence='missing')
            with patch('prepare_h9_pinned_native.check_runtime',return_value={
                    'ready':False,'blocked_reasons':['INSUFFICIENT_EFFECTIVE_MEMORY']}),\
                 patch('prepare_h9_pinned_native.native_module_smoke',
                       side_effect=AssertionError('not allowed')):
                code=native.parent_run(args)
            self.assertEqual(code,2)
            result=json.loads((folder/'blocked'/'launch_result.json').read_text())
            self.assertFalse(result['newton_admitted'])
            self.assertEqual(result['new_qualified_midpoints'],0)
            self.assertEqual(result['status'],'FAILED_CLOSED_NO_NEWTON')


if __name__=='__main__':unittest.main()
