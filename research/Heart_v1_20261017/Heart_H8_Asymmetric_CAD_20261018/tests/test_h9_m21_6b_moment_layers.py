"""W3 M21.6B offline exact polynomial audit tests; all samples synthetic."""
import copy
from fractions import Fraction as F
from hashlib import sha256
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
import h9_m21_6b_moment_layers as b


def key(i):
    if i==3:return ('LPI',((0,12),(0,13)),((1,0),(1,1),(1,2)))
    return ('EXPLICIT3D',((1,i),))


def tetra(t):
    # Smooth affine vertex motions, with exact positive tetrahedron orientation.
    keys=[key(i) for i in range(4)]
    coords=[(0,0,0),(1+t,0,0),(0,1,0),(0,0,1+2*t)]
    speeds=[(0,0,0),(1,0,0),(0,0,0),(0,0,2)]
    faces=[[1,2,3],[0,3,2],[0,1,3],[0,2,1]]
    semantic=[]
    for f in faces:
        s=tuple(keys[i] for i in f)
        semantic.append(min(s,s[1:]+s[:1],s[2:]+s[:2]))
    from collections import Counter
    return {'positions':dict(zip(keys,coords)),'motion':dict(zip(keys,speeds)),
            'slotkeys':keys,'faces':faces,'semantic_triangles':Counter(semantic),
            'source':[(0,0,0)],'source_faces':[[0,0,0]],'kinds':{'EXPLICIT3D':3,'LPI':1},
            'c7':float(t)}


class LayerMath(unittest.TestCase):
    def test_exact_rational_token_only(self):
        self.assertEqual(b.q('3/4'),F(3,4))
        self.assertEqual(b.token(F(-2,3)),'-2/3')
        for value in ('3','0.125','1/0','0/-2','a/2',float('inf')):
            with self.subTest(value=value),self.assertRaises(b.Refused):b.q(value)

    def test_dual_arithmetic_exact(self):
        x=b.Dual(F(2),F(1));y=b.Dual(F(3),F(-1))
        z=(x*y+x)/2
        self.assertEqual((z.x,z.d),(F(4),F(1)))

    def test_tetra_exact_volume_moments(self):
        state=tetra(F(0))
        groups,total=b.grouped_faces(state)
        self.assertEqual(total['moments'][0],F(1,6))
        self.assertEqual(total['j7'][0],F(1,2))
        self.assertEqual(total['moments'][1:4],[F(1,24)]*3)
        self.assertEqual(total['faces'],4)
        self.assertEqual(sum(v['faces'] for v in groups.values()),4)
        self.assertEqual(groups['MIXED_EXPLICIT_LPI']['faces'],3)
        self.assertEqual(groups['EXPLICIT_ONLY']['faces'],1)
        self.assertEqual(groups['TPI_TOUCHING']['faces'],0)

    def test_all_ten_dual_moment_derivatives_against_exact_polynomial_interpolation(self):
        # A moving tetrahedron has moment degree <=5 in t. The seven-point
        # central derivative stencil differentiates every degree<=6 polynomial
        # *exactly*: this is independent of the dual-number implementation.
        weights=[F(-1,60),F(3,20),F(-3,4),F(0),F(3,4),F(-3,20),F(1,60)]
        d=[F(0)]*10
        for t,w in zip(range(-3,4),weights):
            _,row=b.grouped_faces(tetra(F(t)))
            d=[x+w*y for x,y in zip(d,row['moments'])]
        _,reference=b.grouped_faces(tetra(F(0)))
        self.assertEqual(d,reference['j7'])

    def test_tetra_motion_j7_at_later_point(self):
        groups,tot=b.grouped_faces(tetra(F(1)))
        self.assertEqual(tot['moments'][0],F(1))
        self.assertEqual(tot['j7'][0],F(7,6))

    def test_affine_translation_tangent_zero(self):
        # Geometry and its velocities identically zero: all J7 entries must be 0.
        s=tetra(F(0));s['motion']={k:(0,0,0) for k in s['motion']}
        _,tot=b.grouped_faces(s)
        self.assertEqual(tot['j7'],[F(0)]*10)

    def test_native_vs_independent_exact_layer_split(self):
        rows=[]
        for t in (F(0),F(1)):
            group,total=b.grouped_faces(tetra(t))
            rows.append({'c7':float(t),'stem':str(t),'groups':group,'total':total,
                         'exact':total['moments'], 'native':list(total['j7']),
                         'face_counts':{k:v['faces'] for k,v in group.items()}})
        row=b.layer_interval(*rows,side='left',interval='full')
        self.assertEqual(row['component_diagnostics']['mass']['native_j7_residual_exact'],'0/1')
        self.assertEqual(row['ten_component_exact_layer_identites_verified'],10)
        self.assertGreater(row['max_independent_scaled_residual'],0)
        # Introduce a known C++-reference difference; exact residual identity holds.
        rows[0]['native'][0]+=F(1,1000)
        row=b.layer_interval(*rows,side='left',interval='full')
        self.assertEqual(row['component_diagnostics']['mass']['native_j7_residual_exact'],'-1/2000')
        self.assertEqual(row['component_diagnostics']['mass']['replayed_minus_native_endpoint_j7_exact'],'-1/2000')
        self.assertEqual(row['component_diagnostics']['mass']['replayed_j7_residual_exact'],'0/1')

    def test_layer_refuses_changed_face_class(self):
        a,brow=[] ,[]
        for t in (F(0),F(1)):
            g,total=b.grouped_faces(tetra(t))
            brow.append({'c7':float(t),'stem':str(t),'groups':g,'total':total,
                         'exact':total['moments'], 'native':total['j7'],
                         'face_counts':{k:v['faces'] for k,v in g.items()}})
        brow[1]['face_counts']['LPI_ONLY']=1
        with self.assertRaisesRegex(b.Refused,'FACE_KIND_COUNTS_CHANGED'):
            b.layer_interval(*brow,side='left',interval='full')

    def test_grouped_refuses_corrupt_semantic_face(self):
        st=tetra(F(0))
        st['semantic_triangles'].clear()
        with self.assertRaisesRegex(b.Refused,'SEMANTIC_TRIANGLES_MISMATCH'):
            b.grouped_faces(st)

    def test_grouped_refuses_missing_motion(self):
        st=tetra(F(0))
        st['motion']=None
        with self.assertRaisesRegex(b.Refused,'MISSING_EXACT_BOUNDARY_MOTION'):
            b.grouped_faces(st)

    def test_input_digest_rejects_tamper(self):
        with TemporaryDirectory() as root:
            path=Path(root)/'packet.json';path.write_text('{"sample":1}')
            good=b.digest(path)
            self.assertEqual(b.strict_json(path,good)['sample'],1)
            path.write_text('{"sample":2}')
            with self.assertRaisesRegex(b.Refused,'SHA_MISMATCH'):
                b.strict_json(path,good)

    def test_duplicate_json_key_is_refused(self):
        with TemporaryDirectory() as root:
            path=Path(root)/'packet.json';path.write_text('{"sample":1,"sample":1}')
            with self.assertRaisesRegex(b.Refused,'DUPLICATE_JSON_KEY'):
                b.strict_json(path,b.digest(path))

    def test_group_label_rejects_unknown(self):
        with self.assertRaisesRegex(b.Refused,'UNKNOWN_FACE_KIND'):
            b.kind_group([('UNKNOWN',),('UNKNOWN',),('UNKNOWN',)])

    def test_frozen_boundary_refuses_newton_claim(self):
        samples=[{'stem':s,'retained_vertex_count':8455,'source_vertex_count':162,
                  'construction_counts':{'EXPLICIT3D':7671,'LPI':784}} for s in b.STEMS]
        meta=[{'stem':s,'attachment_sha256':'v'+str(i)} for i,s in enumerate(b.STEMS)]
        ledger={'packets':[{'material_sha256':'m'+str(i)} for i in range(6)]}
        report={'schema':'heart-h9-m21-6a-all-retained-boundary-motion-v1',
                'status':'SIX_SAVED_PACKETS_FULL_BOUNDARY_DISCRETE_MOTION_DIAGNOSTIC_ONLY',
                'sample_count':6,'samples':samples,'intervals':[{}]*6,
                'claims':{'newton_admitted':False,'root_cause_determined':False,'new_boolean_calls':0},
                'inputs':{'precision_ledger_sha256':b.LEDGER_SHA,
                          'native_source_core_sha256':b.BINARY_SHA,
                          'm21_5b_lpi_sha256':b.LPI_SHA,
                          'six_material_sha256':['m'+str(i) for i in range(6)],
                          'six_motion_sha256':['v'+str(i) for i in range(6)],
                          'full_raw_six_packet_bytes_read':True,
                          'all_source_only_motion_attestations_replayed_and_hash_bound':True,
                          'runtime_origin_cryptographically_attested':False}}
        b.verify_report_inputs(report,ledger,meta)
        report['claims']['newton_admitted']=True
        with self.assertRaisesRegex(b.Refused,'BOUNDARY_OR_MATERIAL_IDENTITY_MISMATCH'):
            b.verify_report_inputs(report,ledger,meta)

if __name__=='__main__':unittest.main()
