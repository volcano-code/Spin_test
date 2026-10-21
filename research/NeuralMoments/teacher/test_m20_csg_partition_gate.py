"""W2 M20: real frozen source and synthetic exact F/D/A algebra; no fake native success."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

import m20_csg_partition_gate as gate
import m19_noodles_fda_audit as m19

SOURCE=Path(os.environ.get('W2_M18_SOURCE_BUNDLE',
    '/mnt/data/W2_M18_Noodles_V7_94_Source_Recovery.zip'))

# Synthetic rational voxel sets, NOT Noodles / original native CGAL evidence.
E={(x,y,z) for x in range(2) for y in range(2) for z in range(2)}
I={(1,0,0)}
O={(2,0,0)}
VOXELS={'envelope':E,'fixed':I|O,'design':E-I,
        'fixed-inside-envelope':I,'fixed-outside-envelope':O,'initial':E|O}


def surface(cells):
    vertex_ids={}; vertices=[]; faces=[]
    # Each oriented quad has the outward normal in its fixed grid direction.
    for x,y,z in sorted(cells):
        quads=[
            ((-1,0,0),((x,y,z),(x,y,z+1),(x,y+1,z+1),(x,y+1,z))),
            ((1,0,0),((x+1,y,z),(x+1,y+1,z),(x+1,y+1,z+1),(x+1,y,z+1))),
            ((0,-1,0),((x,y,z),(x+1,y,z),(x+1,y,z+1),(x,y,z+1))),
            ((0,1,0),((x,y+1,z),(x,y+1,z+1),(x+1,y+1,z+1),(x+1,y+1,z))),
            ((0,0,-1),((x,y,z),(x,y+1,z),(x+1,y+1,z),(x+1,y,z))),
            ((0,0,1),((x,y,z+1),(x+1,y,z+1),(x+1,y+1,z+1),(x,y+1,z+1)))
        ]
        for step,corners in quads:
            if (x+step[0],y+step[1],z+step[2]) in cells:continue
            indices=[]
            for coord in corners:
                if coord not in vertex_ids:
                    vertex_ids[coord]=len(vertices)
                    vertices.append([f'{t}/1' for t in coord])
                indices.append(vertex_ids[coord])
            a,b,c,d=indices;faces.extend(([a,b,c],[a,c,d]))
    return {'vertices':vertices,'faces':faces}


def prepare(dir):
    root=Path(dir);expected_sha={};expected_faces={}
    for name,cells in VOXELS.items():
        packet=surface(cells)
        path=root/(name+'-rational.json')
        b=json.dumps(packet,separators=(',',':'),allow_nan=False).encode()
        path.write_bytes(b)
        expected_sha[name]=hashlib.sha256(b).hexdigest()
        expected_faces[name]=len(packet['faces'])
    return expected_sha,expected_faces


class TestSyntheticExactPartition(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.dir=Path(self.tmp.name)
        self.sha,self.faces=prepare(self.dir)
    def tearDown(self):self.tmp.cleanup()
    def check(self):return gate.inspect_six_packets(self.dir,self.sha,self.faces,historic_sha_required=False)
    def test_six_exact_synthetic_volumes_and_relations(self):
        v=self.check()
        self.assertEqual(v['six_packet_sha_matched'],6)
        self.assertEqual(v['exact_additive_relations'],4)
        self.assertEqual(v['exact_ten_moment_components'],60)
        self.assertEqual(v['per_packet']['envelope']['volume'],'8')
        self.assertEqual(v['per_packet']['fixed']['volume'],'2')
        self.assertEqual(v['per_packet']['design']['volume'],'7')
        self.assertEqual(v['per_packet']['initial']['volume'],'9')
        self.assertFalse(v['boolean_semantics_independently_proven'])
        self.assertEqual(v['training_admitted'],0)
    def test_extra_only_one_volume_changed_detected_exactly(self):
        path=self.dir/'initial-rational.json';x=json.loads(path.read_text())
        # Extend one full synthetic solid face outward; remains algebraically wrong.
        x['vertices'][0][0]='1/3'
        b=json.dumps(x,separators=(',',':')).encode();path.write_bytes(b)
        self.sha['initial']=hashlib.sha256(b).hexdigest()
        with self.assertRaisesRegex(gate.AdmissionError,'EXACT_FDA_MOMENT_RELATION_FAILED'):
            self.check()
    def test_sha_tamper_rejected_before_parsing(self):
        (self.dir/'design-rational.json').write_text('{}')
        with self.assertRaisesRegex(gate.AdmissionError,'CSG_PACKET_SHA_MISMATCH'):
            self.check()
    def test_missing_packet_fails_closed(self):
        (self.dir/'design-rational.json').unlink()
        with self.assertRaisesRegex(gate.AdmissionError,'MISSING_OR_SYMLINK_CSG_PACKET'):
            self.check()
    def test_orientation_reversed_rejected(self):
        p=self.dir/'fixed-rational.json';o=json.loads(p.read_text());o['faces'][0].reverse()
        b=json.dumps(o,separators=(',',':')).encode();p.write_bytes(b)
        self.sha['fixed']=hashlib.sha256(b).hexdigest()
        with self.assertRaisesRegex(gate.AdmissionError,'NOT_CLOSED_OR_ORIENTED'):
            self.check()
    def test_absent_face_rejected(self):
        p=self.dir/'envelope-rational.json';o=json.loads(p.read_text());o['faces'].pop()
        b=json.dumps(o,separators=(',',':')).encode();p.write_bytes(b)
        self.sha['envelope']=hashlib.sha256(b).hexdigest();self.faces['envelope']-=1
        with self.assertRaisesRegex(gate.AdmissionError,'NOT_CLOSED_OR_ORIENTED'):
            self.check()
    def test_untrusted_decimal_float_rejected(self):
        p=self.dir/'design-rational.json';o=json.loads(p.read_text());o['vertices'][0][0]=0.5
        b=json.dumps(o,separators=(',',':')).encode();p.write_bytes(b)
        self.sha['design']=hashlib.sha256(b).hexdigest()
        with self.assertRaisesRegex(gate.AdmissionError,'COORDINATE_REQUIRES_EXACT_RATIONAL_TOKEN'):
            self.check()
    def test_packet_face_count_requires_external_pinning(self):
        self.faces['fixed']+=1
        with self.assertRaisesRegex(gate.AdmissionError,'CSG_PACKET_FACE_COUNT_MISMATCH'):
            self.check()
    def test_symlink_rejected(self):
        p=self.dir/'fixed-rational.json';p.unlink();p.symlink_to(self.dir/'envelope-rational.json')
        with self.assertRaisesRegex(gate.AdmissionError,'MISSING_OR_SYMLINK_CSG_PACKET'):
            self.check()
    def test_degenerate_face_rejected(self):
        p=self.dir/'fixed-rational.json';o=json.loads(p.read_text());o['faces'][0]=[0,0,1]
        b=json.dumps(o,separators=(',',':')).encode();p.write_bytes(b)
        self.sha['fixed']=hashlib.sha256(b).hexdigest()
        with self.assertRaisesRegex(gate.AdmissionError,'INVALID_TRIANGLE'):
            self.check()
    def test_bad_external_set_rejected(self):
        self.sha.pop('fixed')
        with self.assertRaisesRegex(gate.AdmissionError,'SIX_EXTERNAL_PACKET_IDENTITIES_REQUIRED'):
            self.check()


class TestRealHistoricalReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SOURCE.is_file():raise unittest.SkipTest('M18 authentic 188-OBJ source bundle unavailable')
        cls.result=gate.review(SOURCE)
    def test_full_real_source_is_pinned(self):
        self.assertEqual(self.result['source_parts_verified'],94)
        self.assertEqual(self.result['model_and_SI_sources_verified'],188)
    def test_old_CGAL_calls_are_not_fresh(self):
        self.assertEqual(self.result['historical_CGAL_boolean_count_reported_not_reexecuted'],96)
        self.assertEqual(self.result['native_new_CSG_operations'],0)
    def test_historic_six_sha_and_face_counts_are_preserved(self):
        x=self.result['historic_6_outputs_expected']
        self.assertEqual(len(x),6)
        self.assertEqual(next(y for y in x if y['name']=='fixed')['faces'],114942)
        self.assertEqual(next(y for y in x if y['name']=='design')['faces'],108804)
    def test_no_fake_native_teacher(self):
        self.assertEqual(self.result['training_admitted'],0)
        self.assertIsNone(self.result['J_D'])
        self.assertIn('BLOCKED_NO_SIX_',self.result['status'])
    def test_actual_memory_and_cgal_preflight(self):
        status=self.result['current_native_preflight']
        self.assertFalse(status['native_launch_authorized'])
        self.assertFalse(status['backend_protocol_and_compilation_provenance_verified'])
    def test_missing_full_historical_packets_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(gate.AdmissionError,'MISSING_OR_SYMLINK_CSG_PACKET'):
                gate.review(SOURCE,csg_dir=d)
    def test_historical_receipt_unpinned_rejected(self):
        with self.assertRaisesRegex(m19.GateError,'HISTORIC_CSG_RECEIPT_SHA256_MISMATCH'):
            gate.historic_expectations(b'{}')


if __name__=='__main__':unittest.main()
