"""Real 94-part frozen manifest verifies the unchanged 96-op Boolean DAG."""
from pathlib import Path
import os,tempfile,unittest
from zipfile import ZipFile, ZIP_STORED
import m20_csg_96_replay_plan as p
import m19_noodles_fda_audit as m19
SOURCE=Path(os.environ.get('W2_M18_SOURCE_BUNDLE',
    '/mnt/data/W2_M18_Noodles_V7_94_Source_Recovery.zip'))

class HistoricalPlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SOURCE.is_file():raise unittest.SkipTest('authentic recovered V7 bundle missing')
        cls.result=p.plan(SOURCE)
    def test_actual_96(self):
        self.assertEqual(len(self.result['ordered_operations']),96)
    def test_92_fixed_union(self):
        self.assertEqual(self.result['fixed_union_operations'],92)
    def test_4_exact_final_operations(self):
        tail=self.result['ordered_operations'][-4:]
        self.assertEqual([x['kind'] for x in tail],
                         ['difference','union','intersection','difference'])
        self.assertEqual([x['output'] for x in tail],
             ['design-rational.json','initial-rational.json',
              'fixed-inside-envelope-rational.json','fixed-outside-envelope-rational.json'])
    def test_old_receipt_remains_uncertified(self):
        self.assertFalse(self.result['all_original_six_CSG_output_bytes_present'])
        self.assertFalse(self.result['protocol_of_original_CGAL_binary_available'])
        self.assertEqual(self.result['current_native_operations'],0)
    def test_93_fixed_and_one_envelope(self):
        self.assertEqual(self.result['fixed_source_parts'],93)
        self.assertEqual(len(self.result['leaf_sources']),94)
    def test_original_6_digest_set(self):
        self.assertEqual(set(self.result['expected_historical_outputs']),set(m19.PACKETS))
        self.assertEqual(self.result['expected_historical_outputs']['fixed']['triangles'],114942)
    def test_no_training(self):
        self.assertIsNone(self.result['jacobian_J_D'])
        self.assertEqual(self.result['training_admitted'],0)
    def test_no_duplicate_output_paths(self):
        out=[v['output'] for v in self.result['ordered_operations']]
        self.assertEqual(len(set(out)),96)
    def test_invalid_zip_fails(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'fake.zip'
            with ZipFile(path,'w',compression=ZIP_STORED) as z:
                z.writestr(m19.BUNDLE_MANIFEST,'{}')
                z.writestr(m19.BUNDLE_CSG_RECEIPT,'{}')
            with self.assertRaisesRegex(m19.GateError,'ORIGINAL_MANIFEST_SHA256_MISMATCH'):
                p.plan(path)

if __name__=='__main__':unittest.main()
