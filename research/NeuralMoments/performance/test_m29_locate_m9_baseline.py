import json
from pathlib import Path
import tempfile
import unittest
from m29_locate_m9_baseline import search, validate_report, ARCHIVE_SHA, SOURCE_BLOB, MATERIAL_SHA, GEOMETRY_SHA, MODULES


def fixture():
    return {'schema': 'w1-m9-native-h8c-abba-v1', 'archive_sha256': ARCHIVE_SHA,
            'production_source_blob': SOURCE_BLOB, 'module_binary_sha256': dict(MODULES),
            'parity_and_timing': {'pass_all_four_material_and_jacobian_parity': True},
            'measurements': [dict(mode=mode, material_sha256=MATERIAL_SHA,
                                 geometry_hash=GEOMETRY_SHA, q=[1.] + [0.] * 9,
                                 ten=[0.] * 10, jacobian=[[0.] * 10 for _ in range(10)])
                             for mode in ('original', 'candidate', 'candidate', 'original')]}


class BaselineRecoveryTests(unittest.TestCase):
    def test_valid_fixture_identity(self):
        self.assertEqual(validate_report(fixture()), [])

    def test_wrong_material_rejected(self):
        doc = fixture(); doc['measurements'][0]['material_sha256'] = 'wrong'
        self.assertTrue(validate_report(doc))

    def test_wrong_native_module_rejected(self):
        doc = fixture(); doc['module_binary_sha256']['native_sha256'] = 'wrong'
        self.assertIn('MISMATCH:module_binary_sha256', validate_report(doc))

    def test_missing_or_nonfinite_jacobian_rejected(self):
        for matrix in ([], [[float('nan')] * 10 for _ in range(10)]):
            doc = fixture(); doc['measurements'][1]['jacobian'] = matrix
            self.assertTrue(validate_report(doc))

    def test_m5_and_fd_summaries_rejected(self):
        for schema in ('w1-m5-native-h8-instrumented-sample-v1', 'w1-m29-3-2-fresh-native-tangent-fd-v1'):
            doc = fixture(); doc['schema'] = schema
            self.assertEqual(validate_report(doc), ['WRONG_SCHEMA'])

    def test_moved_report_found_without_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'backup' / 'renamed-run' / 'baseline-performance.json'
            p.parent.mkdir(parents=True); p.write_text(json.dumps(fixture()))
            before = p.read_bytes()
            result = search([td])
            self.assertEqual(len(result['matches']), 1)
            self.assertEqual(result['matches'][0]['m9_run'], str(p.parent))
            self.assertTrue(result['matches'][0]['runner_filename_compatible'])
            self.assertEqual(p.read_bytes(), before)

    def test_multiple_matches_are_all_reported_not_selected(self):
        with tempfile.TemporaryDirectory() as td:
            for name in ('first', 'second'):
                p = Path(td) / name / 'baseline-performance.json'
                p.parent.mkdir(); p.write_text(json.dumps(fixture()))
            self.assertEqual(len(search([td])['matches']), 2)

    def test_missing_root_and_bounded_search_are_reported(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'a' / 'b' / 'baseline-performance.json'
            p.parent.mkdir(parents=True); p.write_text(json.dumps(fixture()))
            result = search([Path(td) / 'absent', td], max_depth=0)
            self.assertEqual(result['matches'], [])
            self.assertEqual(len(result['skipped_roots']), 1)
            self.assertGreater(result['depth_cutoffs'], 0)

    def test_archive_listed_but_not_opened(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'w1-m9-backup.tar.gz'; p.write_bytes(b'not an archive')
            result = search([td])
            self.assertEqual(result['archive_candidates_not_opened'], [str(p)])
            self.assertEqual(result['matches'], [])
            self.assertEqual(p.read_bytes(), b'not an archive')

    def test_directory_limit_is_visible(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / 'child').mkdir()
            result = search([td], max_directories=1)
            self.assertTrue(result['limit_reached'])
            self.assertEqual(result['directories_scanned'], 1)

    def test_renamed_report_requires_filename_recovery(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'm9-baseline-performance.json'; p.write_text(json.dumps(fixture()))
            result = search([td])
            self.assertEqual(len(result['matches']), 1)
            self.assertFalse(result['matches'][0]['runner_filename_compatible'])


if __name__ == '__main__':
    unittest.main()
