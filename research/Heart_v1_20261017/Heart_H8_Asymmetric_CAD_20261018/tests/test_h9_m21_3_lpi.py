import copy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))
import h9_m21_3_lpi as audit

P = [(0,0,0), (2,0,0), (1,0,0), (1,1,0), (1,0,1)]
V = [(0,0,0), (0,0,0), (3,0,0), (3,0,0), (3,0,0)]
CASES = {'sample': ((0,1), (0,1,2))}
REQUEST = dict(design_vertices=P[:2], target_origin=[0,0,0], target_axes=[[1,0,0],[0,1,0],[0,0,1]])


def fixture(order=(0,1,2,3,4)):
    ids = [(0,0), (0,1), (1,0), (1,1), (1,2)]
    operands = [dict(status='UNIQUE', source_vertices=[dict(input_object=ids[i][0], input_vertex=ids[i][1])])
                for i in order]
    return dict(variable_rational_vertices=[[1,0,0]], quadric_source_vertices=P[2:],
                material_proof=dict(schema='cherchi-same-call-material-v1', exact_vertices=[[1,0,0]],
                  construction_records=[dict(vertex_index=0, point_type='LPI',operand_coordinates_exact=[P[i] for i in order])],
                  resolved_construction_records=[dict(vertex_index=0,point_type='LPI',operands=operands)]))


class LpiAudit(unittest.TestCase):
    def test_translated_plane(self):
        r, x, v = audit.decompose(P,V)
        self.assertEqual((x,v), ((1,0,0),(3,0,0)))
        self.assertEqual((r['d'],r['d_prime'],r['t'],r['t_prime']), ('2','0','1/2','3/2'))

    def test_normal_and_denominator_cancel(self):
        v = [(0,0,0)]*3 + [(0,3,0),(0,0,0)]
        r, _, xp = audit.decompose(P,v)
        self.assertEqual((r['t_prime_numerator'],r['t_prime_denominator'],r['t_prime_normal_net']),('3/2','-3/2','0'))
        self.assertEqual(xp,(0,0,0))

    def test_moving_line(self):
        v = [(-1,2,0),(2,-2,0)] + [(0,0,0)]*3
        r,x,vx = audit.decompose(P,v)
        self.assertEqual(r['t_prime_line_motion'],'-1/4')
        self.assertEqual((x,vx),audit.construction('LPI',P,v))

    def test_singular(self):
        with self.assertRaisesRegex(ValueError, 'SINGULAR'):
            audit.decompose([P[0],(0,1,0)]+P[2:],V)

    def test_id_order_reversal(self):
        rows = [audit.selected_rows(fixture(o), REQUEST, V[2:], CASES)
                for o in [(0,1,2,3,4),(1,0,4,3,2)]]
        self.assertEqual(*rows)

    def test_reject_bad_geometry(self):
        for key in ('exact_vertices','operand_coordinates_exact'):
            m = fixture()
            if key == 'exact_vertices':
                m['material_proof'][key][0] = (0,1,0)
            else:
                m['material_proof']['construction_records'][0][key][2] = (2,2,2)
            with self.subTest(key=key), self.assertRaises(ValueError):
                audit.selected_rows(m, REQUEST, V[2:], CASES)

    def test_missing_duplicate_ambiguous(self):
        for what in ('missing','duplicate','ambiguous'):
            m = fixture()
            records = m['material_proof']['resolved_construction_records']
            if what == 'missing':
                records.clear()
            elif what == 'duplicate':
                records.extend(copy.deepcopy(records))
            else:
                records[0]['operands'][0]['status'] = 'AMBIGUOUS'
            with self.subTest(what=what), self.assertRaises(ValueError):
                audit.selected_rows(m, REQUEST, V[2:], CASES)

    def test_six_report_wrong_order(self):
        report = dict(schema='heart-h9-m21-layered-motion-diagnostic-v1',
                      status='SOURCE_MOTION_AND_EXACT_CHAIN_REPLAYED_DIAGNOSTIC_ONLY',
                      ledger_sha256=audit.LEDGER_SHA, native_core_sha256='core', new_native_source_calls_this_run=6,
                      new_boolean_calls_this_run=0, newton_admitted=False,
                      packet_results=[dict(stem=s) for s in audit.STEMS])
        self.assertEqual(len(audit.source_rows(report,'core')),6)
        report['packet_results'].reverse()
        with self.assertRaises(ValueError):
            audit.source_rows(report,'core')

    def test_attachment_content_and_byte_binding(self):
        with TemporaryDirectory() as tmp:
            worker = Path(tmp)
            path = worker/'s.source-motion.json'
            att = dict(schema='heart-h9-m21-source-only-motion-v1',material_sha256='mat',
                       native_core_sha256='core', boolean_calls=0,newton_admitted=False,
                       physical_source_velocity_column7=V[2:])
            path.write_text(json.dumps(att))
            ev = dict(stem='s',material_sha256='mat')
            row = dict(ev,source_motion_replayed=True,source_geometry_bitwise_matched=True,
                       source_motion_attachment_sha256=audit.file_hash(path))
            self.assertEqual(len(audit.read_motion(worker,row,ev,'core')),3)
            path.write_text(json.dumps(dict(att,material_sha256='swapped')))
            with self.assertRaisesRegex(ValueError,'INPUT_SHA'):
                audit.read_motion(worker,row,ev,'core')
            row['source_motion_attachment_sha256'] = audit.file_hash(path)
            with self.assertRaisesRegex(ValueError,'SOURCE_ATTACHMENT'):
                audit.read_motion(worker,row,ev,'core')
