"""M21 analytical/synthetic tests plus genuine historical H8f checks.

Synthetic fixtures are NOT the user's six new native packets. No test invokes
Cherchi Boolean or grants Newton. Historical archive required for its tests.
"""
from __future__ import annotations
import copy
from fractions import Fraction as F
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
import h9_m21_motion_math as mm
import h9_m21_layered_replay as run

ARCHIVE=Path(os.environ.get('H9_EVIDENCE_ZIP','/mnt/data/w3-h8f-evidence-12135528290.zip'))
LEDGER=Path(os.environ.get('H9_M20_LEDGER','/mnt/data/precision-ledger.json'))
FACES=[[0,2,1],[0,1,3],[0,3,2],[1,2,3]]
REQUEST={'design_vertices':[[8.,8.,8.]],'target_origin':[0.,0.,0.],
         'target_axes':[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]],'material_density':1.}


def token(x):
    x=F(x);return f'{x.numerator}/{x.denominator}'


def tetra(t=0.):
    s=1.+t
    points=[[0.,0.,0.],[s,0.,0.],[0.,s,0.],[0.,0.,s]]
    raw=[];resolved=[]
    for i,p in enumerate(points):
        raw.append(dict(vertex_index=i,point_type='EXPLICIT3D',operand_coordinates_exact=[[token(x) for x in p]]))
        resolved.append(dict(vertex_index=i,point_type='EXPLICIT3D',operands=[{
            'status':'UNIQUE','source_vertices':[{'input_object':1,'input_vertex':i}]}]))
    exact=[[token(x) for x in p] for p in points]
    q=[0.]*10;q[0]=1.;q[7]=t
    return dict(quadric_source_vertices=points,quadric_source_faces=FACES,
                variable_rational_vertices=exact,variable_faces=FACES,quadric_coefficients=q,
                boolean_operation='intersection',material_proof={'schema':'cherchi-same-call-material-v1',
                    'exact_vertices':exact,'construction_records':raw,'resolved_construction_records':resolved})


class ConstructionMathTests(unittest.TestCase):
    def test_explicit(self):
        p,v=mm.construction('EXPLICIT3D',[[1,2,3]],[[4,5,6]])
        self.assertEqual(p,(1,2,3));self.assertEqual(v,(4,5,6))

    def test_lpi_moving_plane(self):
        p=[[0,0,0],[0,0,2],[0,0,1],[1,0,1],[0,1,1]]
        v=[[0,0,0],[0,0,0]]+[[0,0,3]]*3
        x,dx=mm.construction('LPI',p,v)
        self.assertEqual(x,(0,0,1));self.assertEqual(dx,(0,0,3))

    def test_lpi_operand_permutation(self):
        p=[[0,0,0],[0,0,2],[0,0,1],[1,0,1],[0,1,1]]
        v=[[0,0,1],[1,0,0],[0,0,3],[0,0,3],[0,0,3]]
        a=mm.construction('LPI',p,v)
        order=[1,0,4,3,2]
        self.assertEqual(a,mm.construction('LPI',[p[i] for i in order],[v[i] for i in order]))

    def test_tpi_translating_planes(self):
        p=[[1,0,0],[1,1,0],[1,0,1],[0,2,0],[1,2,0],[0,2,1],[0,0,3],[1,0,3],[0,1,3]]
        v=[[1,0,0]]*3+[[0,2,0]]*3+[[0,0,3]]*3
        self.assertEqual(mm.construction('TPI',p,v),((1,2,3),(1,2,3)))

    def test_singular_lpi_rejected(self):
        with self.assertRaisesRegex(ValueError,'SINGULAR'):
            mm.construction('LPI',[[0,0,0],[1,0,0],[0,0,1],[1,0,1],[0,1,1]],[[0,0,0]]*5)

    def test_singular_tpi_rejected(self):
        with self.assertRaisesRegex(ValueError,'SINGULAR'):
            mm.construction('TPI',[[0,0,1],[1,0,1],[0,1,1]]*3,[[0,0,0]]*9)

    def test_nan_and_bool_rejected(self):
        for v in (float('nan'),True):
            with self.assertRaises(ValueError):mm.frac(v)

    def test_tetra_exact_scale_tangent(self):
        mat=tetra();vel=mat['quadric_source_vertices']
        state=mm.material_state(mat,REQUEST,vel)
        actual,_=mm.moment_tangent(state)
        expected=[F(1,2)]+[F(1,6)]*3+[F(1,12)]*3+[F(1,24)]*3
        self.assertEqual(actual,expected)

    def test_tetra_translation_tangent(self):
        state=mm.material_state(tetra(),REQUEST,[[1,0,0]]*4)
        actual,_=mm.moment_tangent(state)
        self.assertEqual(actual,[F(0),F(1,6),F(0),F(0),F(1,12),F(0),F(0),F(0),F(1,24),F(1,24)])

    def test_source_velocity_missing_is_unknown_not_zero(self):
        s=mm.material_state(tetra(),REQUEST)
        self.assertIsNone(s['motion'])
        with self.assertRaisesRegex(ValueError,'NOT_AVAILABLE'):mm.moment_tangent(s)

    def test_zero_velocity_and_density(self):
        s=mm.material_state(tetra(),REQUEST,[[0,0,0]]*4)
        self.assertEqual(mm.moment_tangent(s,2)[0],[0]*10)
        s=mm.material_state(tetra(),REQUEST,tetra()['quadric_source_vertices'])
        self.assertEqual(mm.moment_tangent(s,2)[0][0],F(1))

    def test_broken_operand_binding_rejected(self):
        mat=tetra();mat['quadric_source_vertices'][1][0]=2.
        with self.assertRaisesRegex(ValueError,'OPERAND_NOT_BOUND'):mm.material_state(mat,REQUEST)

    def test_frame_mismatch_rejected(self):
        req=copy.deepcopy(REQUEST);req['target_origin'][0]=1.
        with self.assertRaisesRegex(ValueError,'TARGET_FRAME'):mm.material_state(tetra(),req)

    def test_ambiguous_operand_rejected(self):
        mat=tetra();mat['material_proof']['resolved_construction_records'][1]['operands'][0]['status']='AMBIGUOUS'
        with self.assertRaisesRegex(ValueError,'AMBIGUOUS'):mm.material_state(mat,REQUEST)

    def test_duplicate_vertex_slot_rejected(self):
        mat=tetra();mat['material_proof']['construction_records'][1]['vertex_index']=0
        with self.assertRaisesRegex(ValueError,'DUPLICATE'):mm.material_state(mat,REQUEST)

    def test_open_boundary_rejected(self):
        mat=tetra();mat['variable_faces']=FACES[:3]
        with self.assertRaisesRegex(ValueError,'OPEN_'):mm.material_state(mat,REQUEST)

    def test_slot_reorder_uses_feature_identity(self):
        a=tetra();b=tetra(.1);order=[2,0,3,1];inverse={old:new for new,old in enumerate(order)}
        for k in ('variable_rational_vertices',):b[k]=[b[k][i] for i in order]
        proof=b['material_proof'];proof['exact_vertices']=[proof['exact_vertices'][i] for i in order]
        for name in ('construction_records','resolved_construction_records'):
            records=proof[name];proof[name]=[dict(records[old],vertex_index=new) for new,old in enumerate(order)]
        b['variable_faces']=[[inverse[i] for i in face] for face in b['variable_faces']]
        result=mm.motion_pair(mm.material_state(a,REQUEST),mm.material_state(b,REQUEST))
        self.assertTrue(result['same_retained_constraints_and_oriented_triangles'])
        self.assertFalse(result['motion_available'])

    def test_finite_affine_source_pair(self):
        a=mm.material_state(tetra(0),REQUEST,[[0,0,0],[1,0,0],[0,1,0],[0,0,1]])
        b=mm.material_state(tetra(.5),REQUEST,[[0,0,0],[1,0,0],[0,1,0],[0,0,1]])
        result=mm.motion_pair(a,b)
        self.assertEqual(result['construction_groups']['EXPLICIT3D']['max_secant_vs_average_motion'],0.)
        self.assertFalse(result['newton_admitted'])


class SourceInterfaceTests(unittest.TestCase):
    def test_fake_source_only_backend_affine_binding(self):
        import numpy as np
        mat=tetra();source={'defined':True,'side_selection_defined':True,'vertices':mat['quadric_source_vertices'],
           'faces':FACES,'interior_is_positive':True,'vertex_velocity':np.zeros((4,30)),
           'surface_type':'SYNTHETIC','cap_face_count':0,'source_normal_edges':np.zeros((4,2),dtype=int)}
        class FakeNative:
            calls=0
            def evaluate_spin_it_faster_source_motion(self,*args):self.calls+=1;return source
        fake=FakeNative()
        velocity,_=run.source_snapshot(fake,np,None,REQUEST,mat)
        self.assertEqual(fake.calls,1);self.assertEqual(velocity,[[0.,0.,0.]]*4)
        source['vertices']=copy.deepcopy(mat['quadric_source_vertices']);source['vertices'][1][0]+=1e-8
        with self.assertRaisesRegex(ValueError,'NOT_BITWISE'):run.source_snapshot(fake,np,None,REQUEST,mat)

    def test_file_tamper_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'packet';p.write_bytes(b'a');sha=run.file_hash(p)
            p.write_bytes(b'b')
            with self.assertRaisesRegex(ValueError,'SHA'):run.bind_file(p,sha)
            q=Path(td)/'link';q.symlink_to(p)
            with self.assertRaisesRegex(ValueError,'SYMLINK'):run.bind_file(q,run.file_hash(p))


class RealEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ARCHIVE.is_file():raise RuntimeError('Real H8f ZIP required; not silently skipped')
        run.bind_file(ARCHIVE,run.ARTIFACT_SHA)
        with zipfile.ZipFile(ARCHIVE) as z:
            cls.request=json.loads(z.read('artifacts/h8-request/prepared-request.json'))['request']
            cls.materials=[json.loads(gzip.decompress(z.read(f'artifacts/h8f-all81-points/point-{i:03d}-material.json.gz')))
                           for i in (59,60)]

    def test_original_59_all_exact_constructions(self):
        s=mm.material_state(self.materials[0],self.request)
        self.assertEqual(len(s['positions']),8455)
        self.assertEqual(s['kinds'],{'EXPLICIT3D':7671,'LPI':784})
        self.assertIsNone(s['motion'])

    def test_original_60_all_exact_constructions_and_changed_features(self):
        a,b=[mm.material_state(m,self.request) for m in self.materials]
        self.assertEqual(len(b['positions']),8455)
        self.assertNotEqual(a['positions'].keys(),b['positions'].keys())
        result=mm.motion_pair(a,b)
        self.assertEqual(result['status'],'FEATURE_CHANGED_NO_VERTEX_MOTION_COMPARISON')
        self.assertFalse(result['newton_admitted'])

    def test_original_reversed_raw_record_storage(self):
        m=copy.deepcopy(self.materials[0]);m['material_proof']['construction_records'].reverse()
        s=mm.material_state(m,self.request)
        self.assertEqual(len(s['positions']),8455)

    def test_uploaded_m20_ledger_triage_is_not_raw_revalidation(self):
        ledger=run.load_ledger(LEDGER);r=run.ledger_review(ledger)
        self.assertEqual(len(r['packet_manifest']),6)
        self.assertFalse(r['raw_material_bytes_read']);self.assertFalse(r['root_cause_determined'])
        self.assertEqual(r['new_boolean_calls_this_run'],0)
        self.assertFalse(r['newton_admitted'])
        self.assertGreater(r['two_sides'][0]['worst_half_over_full'],4.)




def six_fixture(folder):
    """Synthetic I/O fixture; intentionally no native origin is asserted."""
    root=Path(folder);old=root/'old';new=root/'m19';mid=new/'native-two-midpoints/two-midpoint-native'
    old.mkdir();mid.mkdir(parents=True)
    run.dump(old/'report.json',{'scope':'SYNTHETIC_TEST'})
    run.dump(mid/'report.json',{'scope':'SYNTHETIC_TEST'})
    points=[.0,.2,.4,.6,.1,.5];binaries={'core':'a'*64,'boolean':'b'*64,'arithmetic':'c'*64}
    records=[];props=[]
    for i,(stem,t) in enumerate(zip(run.STEMS,points)):
        mat=tetra(t);j=[[0.]*10 for _ in range(10)]
        mat.update(moment_jacobian=j,evaluation_map_identity='d'*64,
            boolean_backend_identity='cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'+binaries['boolean'],
            rational_arithmetic_identity={'module_sha256':binaries['arithmetic']},
            derivative_defined=True,derivative_identity='cherchi-constructed-vertex-motion-v1')
        folder=old if i<4 else mid;raw=folder/(stem+'.json.gz')
        raw.write_bytes(gzip.compress(json.dumps(mat).encode(),mtime=0))
        key='native_moment_jacobian_column7' if i<4 else 'moment_jacobian_column7'
        meta={'material_sha256':run.file_hash(raw),'native_geometry_valid':True,'newton_admitted':False,
              'q':mat['quadric_coefficients'],key:[0.]*10}
        meta_path=folder/(stem+'.json');run.dump(meta_path,meta)
        records.append({'stem':stem,'material_sha256':run.file_hash(raw),'metadata_sha256':run.file_hash(meta_path)})
        props.append({'q':mat['quadric_coefficients']})
    plan={'stage18_independent_audit_sha256':run.M18_SHA,'baseline_four_real_rows':props[:4],
          'predeclared_two_midpoints':props[4:],'stage17_current_binary_sha256':binaries,
          'stage18_current_evaluation_map_identity':'d'*64,
          'stage17_real_producer_report_sha256':run.file_hash(old/'report.json')}
    run.dump(new/'midpoint-plan.json',plan)
    run.dump(new/'native-two-midpoints/launch_result.json',{'worker_exit_code':0,'audit_exit_code':0,
                                                          'new_qualified_midpoints':2,'newton_admitted':False})
    run.dump(new/'native-two-midpoints/independent-refinement.json',{'new_native_run_report_sha256':run.file_hash(mid/'report.json')})
    ledger={'packets':records,'m19_plan_sha256':run.file_hash(new/'midpoint-plan.json'),
            'm19_original_launch_sha256':run.file_hash(new/'native-two-midpoints/launch_result.json'),
            'm19_refinement_sha256':run.file_hash(new/'native-two-midpoints/independent-refinement.json')}
    return SimpleNamespace(m19_run=new,stage17_native_dir=old),ledger


class SixPacketIntegrationTests(unittest.TestCase):
    def test_six_packet_read_and_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            args,ledger=six_fixture(tmp)
            packets,plan,hashes=run.load_six(args,ledger)
            self.assertEqual(len(packets),6)
            states=[mm.material_state(mat,REQUEST) for mat,_,_ in packets]
            for a,b in ((0,4),(4,1),(2,5),(5,3)):
                self.assertTrue(mm.motion_pair(states[a],states[b])['same_retained_constraints_and_oriented_triangles'])
            self.assertGreater(len(hashes),12)

    def test_metadata_sha_drift_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            args,ledger=six_fixture(tmp)
            p=args.stage17_native_dir/(run.STEMS[0]+'.json')
            p.write_text(p.read_text()+' ')
            with self.assertRaisesRegex(ValueError,'SHA_MISMATCH'):run.load_six(args,ledger)

    def test_launch_failure_rejected_even_in_bound_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            args,ledger=six_fixture(tmp)
            p=args.m19_run/'native-two-midpoints/launch_result.json'
            obj=json.loads(p.read_text());obj['audit_exit_code']=1;p.write_text(json.dumps(obj))
            ledger['m19_original_launch_sha256']=run.file_hash(p)
            with self.assertRaisesRegex(ValueError,'NOT_FINITE_ACCEPTED'):run.load_six(args,ledger)

    def test_source_supervisor_nonzero_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=SimpleNamespace(precision_ledger=LEDGER,artifact=ARCHIVE,
                                 stage17_native_dir='not-used',m19_run='not-used',repo='not-used')
            fake=SimpleNamespace(pid=12345,wait=lambda timeout:1,poll=lambda:1)
            with patch.object(run.subprocess,'Popen',return_value=fake):
                with self.assertRaisesRegex(ValueError,'WORKER_FAILED'):run.source_supervisor(args,Path(tmp))
            result=json.loads((Path(tmp)/'launch_result.json').read_text())
            self.assertEqual(result['worker_exit_code'],1);self.assertFalse(result['newton_admitted'])


if __name__=='__main__':unittest.main()
