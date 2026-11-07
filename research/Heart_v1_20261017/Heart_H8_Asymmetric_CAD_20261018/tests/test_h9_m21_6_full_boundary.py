"""M21.6A synthetic/saved-derived unit tests. NOT a native Cherchi test."""
import copy
from collections import Counter
from fractions import Fraction as F
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))
import h9_m21_6_full_boundary as m

CASES = {'Repeated': ((3756, 3813), (24, 86, 87)),
         'Left-full': ((9992, 10119), (31, 105, 110)),
         'Right-first': ((3168, 3618), (24, 151, 152))}
REQUEST = {'target_axes': [[1,0,0],[0,1,0],[0,0,1]], 'target_origin': [0,0,0]}
C = [0,2,10,12,1,11]
MAT = ['a'*64]*6
ATT = ['b'*64]*6


def identity_state(v, extra=True):
    c = F(v)
    pp = {}
    vv = {}
    for z, (label, (edge, face)) in enumerate(CASES.items()):
        key = ('LPI', tuple((0,i) for i in edge), tuple((1,i) for i in face))
        pp[key] = (c**3+z, F(0), F(0))
        vv[key] = (3*c*c, F(0), F(0))
    if extra:
        pp[('EXPLICIT3D', ((0,0),))] = (c, F(0), F(0))
        vv[('EXPLICIT3D', ((0,0),))] = (F(1), F(0), F(0))
        pp[('TPI', ((1,0),(1,1),(1,2)))] = (2*c, F(0), F(0))
        vv[('TPI', ((1,0),(1,1),(1,2)))] = (F(2), F(0), F(0))
    return {'positions':pp, 'motion':vv,
            'semantic_triangles':Counter({'saved-oriented-triangle':1}),
            'c7':float(c), 'source_faces':[[0,1,2]],
            'source':[(c*c,F(0),F(0)),(2*c,F(0),F(0))],
            'kinds':{k:sum(key[0]==k for key in pp) for k in m.KINDS}}


def source_v(c):
    c=F(c)
    return [(2*c, F(0), F(0)),(F(2),F(0),F(0))]


def make_fixture(extra=True):
    states = [identity_state(c,extra) for c in C]
    speeds = [source_v(c) for c in C]
    samples=[]
    for i, state in enumerate(states):
        cons=[]
        for label, (edge, face) in CASES.items():
            key=('LPI',tuple((0,z) for z in edge),tuple((1,z) for z in face))
            cons.append({'label':label,'reference_position_velocity_exact_match':True,
                         'position':[m.token(x) for x in state['positions'][key]],
                         'velocity':[m.token(x) for x in state['motion'][key]]})
        samples.append({'stem':m.STEMS[i],'c7':m.token(state['c7']),
                        'material_sha256':MAT[i],'attachment_sha256':ATT[i],
                        'constructions':cons})
    intervals=[]
    for side, seq in m.SEQUENCES.items():
        for name, a, b in m.INTERVALS:
            i,j=seq[a],seq[b]
            h=F(C[j]-C[i])
            features={}
            for label,(edge,face) in CASES.items():
                key=('LPI',tuple((0,z) for z in edge),tuple((1,z) for z in face))
                p0,p1=states[i]['positions'][key],states[j]['positions'][key]
                v0,v1=states[i]['motion'][key],states[j]['motion'][key]
                av=m.vec_scale(F(1,2),m.vec_add(v0,v1))
                e=m.vec_sub(m.vec_scale(1/h,m.vec_sub(p1,p0)),av)
                features[label]={'delta_c7':m.token(h),
                                 'signed_residual':[m.token(x) for x in e],
                                 'endpoint_average_velocity':[m.token(x) for x in av]}
            intervals.append({'side':side,'interval':name,
                              'from_stem':m.STEMS[i],'to_stem':m.STEMS[j],
                              'features':features})
    lpi={'schema':'heart-h9-m21-3-selected-lpi-motion-v1',
         'status':'SIX_SAVED_PACKETS_THREE_LPI_DIAGNOSTIC_ONLY',
         'precision_ledger_sha256':m.LEDGER_SHA,'native_core_sha256':m.CORE_SHA,
         'new_boolean_calls_this_run':0,'new_native_source_calls_this_run':0,
         'newton_admitted':False,'samples':samples,
         'same_side_interval_lpi_secants':intervals}
    return states, speeds, lpi


def mock_w3_modules():
    lpi=types.ModuleType('h9_m21_3_lpi');lpi.CASES=CASES
    mm=types.ModuleType('h9_m21_motion_math')
    mm.to_target=lambda p, req, velocity=False: tuple(p)
    return patch.dict(sys.modules, {'h9_m21_3_lpi':lpi,'h9_m21_motion_math':mm})


class FullBoundary(unittest.TestCase):
    def test_fraction_partition_cubic_and_zero_linear(self):
        z=(F(0),)*3
        p=lambda c:(F(c)**3,F(0),F(0))
        v=lambda c:(3*F(c)**2,F(0),F(0))
        a,b,full,corr=m.partition_identity(p(0),p(1),p(2),v(0),v(1),v(2),1,1)
        self.assertEqual((a[0],b[0],full[0],corr[0]),
                         (F(-1,2),F(-1,2),F(-2),F(-3,2)))
        a,b,full,corr=m.partition_identity((0,0,0),(1,0,0),(2,0,0),
                                           (1,0,0),(1,0,0),(1,0,0),1,1)
        self.assertEqual((a,b,full,corr),(z,z,z,z))

    def test_complete_synthetic_six_point_feature_groups(self):
        states,vel,lpi=make_fixture()
        with mock_w3_modules():
            out=m.analyze(states,vel,m.STEMS,lpi,REQUEST,top_k=2,
                          packet_hashes=MAT,attachment_hashes=ATT)
        self.assertEqual(out['status'],'SELECTED_OR_SYNTHETIC_SUBSET_DIAGNOSTIC_NOT_FULL_BOUNDARY')
        self.assertEqual(len(out['intervals']),6)
        self.assertEqual([len(x['group_residuals']['LPI']['top']) for x in out['intervals']],[2]*6)
        self.assertEqual(sum(x['group_residuals']['LPI']['count'] for x in out['intervals']),18)
        self.assertEqual(out['crosschecks']['m21_5b_lpi_sample_positions_and_velocities'],18)
        self.assertEqual(out['crosschecks']['m21_5b_lpi_interval_selected_features_present'],18)
        self.assertEqual(sum(x['exact_partition_identities_verified'] for x in out['full_half_exact_partition_checks']),14)
        self.assertEqual(out['intervals'][0]['group_residuals']['LPI']['max_residual_norm'],2.)
        self.assertEqual(out['intervals'][1]['group_residuals']['LPI']['max_residual_norm'],.5)
        self.assertEqual(out['intervals'][0]['group_residuals']['EXPLICIT3D']['max_residual_norm'],0.)
        self.assertEqual(out['intervals'][0]['source_residuals']['max_residual_norm'],0.)
        self.assertFalse(out['claims']['newton_admitted'])

    def test_feature_identity_mismatch_fails_closed(self):
        states,vel,lpi=make_fixture()
        bad=copy.deepcopy(states[1])
        key=next(k for k in bad['positions'] if k[0]=='LPI')
        bad['positions'][('LPI',((0,123),),((1,456),))]=bad['positions'].pop(key)
        with self.assertRaisesRegex(m.Refused,'CHANGED_RETAINED_CONSTRUCTION_IDENTITIES'):
            m.pair_interval(states[0],bad,vel[0],vel[1],side='left',interval='full',
                            from_stem=m.STEMS[0],to_stem=m.STEMS[1])

    def test_changed_semantic_triangulation_rejected(self):
        states,vel,lpi=make_fixture()
        states[1]['semantic_triangles']=Counter({'new-triangle':1})
        with self.assertRaisesRegex(m.Refused,'CHANGED_ORIENTED_SEMANTIC_TRIANGLES'):
            m.pair_interval(states[0],states[1],vel[0],vel[1],side='left',interval='full',
                            from_stem=m.STEMS[0],to_stem=m.STEMS[1])

    def test_source_movement_signature_and_count(self):
        states,vel,lpi=make_fixture()
        bad=copy.deepcopy(states[1]);bad['source_faces']=[[0,2,1]]
        with self.assertRaisesRegex(m.Refused,'CHANGED_SOURCE_FACE_SIGNATURE'):
            m.pair_interval(states[0],bad,vel[0],vel[1],side='left',interval='full',
                            from_stem=m.STEMS[0],to_stem=m.STEMS[1])
        with self.assertRaisesRegex(m.Refused,'SOURCE_MOTION_INDEXING_MISMATCH'):
            m.pair_interval(states[0],states[1],vel[0],vel[1][1:],side='left',interval='full',
                            from_stem=m.STEMS[0],to_stem=m.STEMS[1])

    def test_selected_raw_tangent_forgery_rejected(self):
        states,vel,lpi=make_fixture()
        lpi['samples'][0]['constructions'][0]['velocity'][0]='999/1'
        with mock_w3_modules(),self.assertRaisesRegex(m.Refused,'LPI_SELECTED_POSITION_OR_VELOCITY_DRIFT'):
            m.analyze(states,vel,m.STEMS,lpi,REQUEST,packet_hashes=MAT,attachment_hashes=ATT)

    def test_selected_interval_residual_forgery_rejected(self):
        states,vel,lpi=make_fixture()
        lpi['same_side_interval_lpi_secants'][0]['features']['Left-full']['signed_residual'][0]='0/1'
        with mock_w3_modules(),self.assertRaisesRegex(m.Refused,'LPI_SELECTED_INTERVAL_RESIDUAL_DRIFT'):
            m.analyze(states,vel,m.STEMS,lpi,REQUEST,packet_hashes=MAT,attachment_hashes=ATT)

    def test_provenance_digest_forgery_rejected(self):
        states,vel,lpi=make_fixture()
        lpi['samples'][2]['attachment_sha256']='f'*64
        with mock_w3_modules(),self.assertRaisesRegex(m.Refused,'LPI_ATTACHMENT_SHA_DRIFT'):
            m.analyze(states,vel,m.STEMS,lpi,REQUEST,packet_hashes=MAT,attachment_hashes=ATT)

    def test_wrong_interval_parameter_rejected(self):
        states,vel,lpi=make_fixture()
        states[1]['c7']=F(-1)
        with self.assertRaisesRegex(m.Refused,'NONPOSITIVE_PARAMETER_INTERVAL'):
            m.pair_interval(states[0],states[1],vel[0],vel[1],side='left',interval='full',
                            from_stem=m.STEMS[0],to_stem=m.STEMS[1])

    def test_no_full_boundary_claim_for_three_lpi_subset(self):
        states,vel,lpi=make_fixture(extra=False)
        with mock_w3_modules(),self.assertRaisesRegex(m.Refused,'EXPECTED_FULL_BOUNDARY_OR_SOURCE_MISSING'):
            m.analyze(states,vel,m.STEMS,lpi,REQUEST,expected_boundary_count=8455)

    def test_strict_json_sha_duplicate_and_oversize(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'blob.json'
            path.write_text('{"a":1,"a":2}')
            with self.assertRaisesRegex(m.Refused,'DUPLICATE_JSON_KEY'):
                m.read_strict_json(path)
            path.write_text('{"status":true}')
            with self.assertRaisesRegex(m.Refused,'INPUT_SHA_MISMATCH'):
                m.read_strict_json(path, '0'*64)
            path.write_text('{"v":NaN}')
            with self.assertRaisesRegex(m.Refused,'NONFINITE_JSON_NUMBER'):
                m.read_strict_json(path)

    def test_partition_mismatch_rejected(self):
        states,vel,lpi=make_fixture()
        states[4]['semantic_triangles']=Counter({'changed':1})
        with self.assertRaisesRegex(m.Refused,'PARTITION_CHANGED_ORIENTED_SEMANTIC_TRIANGLES'):
            m.summarize_partition(states,vel,'left',m.SEQUENCES['left'])


if __name__ == '__main__':unittest.main()
