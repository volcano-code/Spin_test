import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from m29_locate_m9_baseline import search
from m29_locate_m9_baseline_fair import search_fair, RUN_NAME, path_status
from test_m29_locate_m9_baseline import fixture


def write_report(root, relative='baseline-performance.json', doc=None):
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fixture() if doc is None else doc))
    return path


class FairRecoveryTests(unittest.TestCase):
    def test_global_quota_regression_old_starves_later_root_new_finds_it(self):
        with tempfile.TemporaryDirectory() as td:
            first, second = Path(td)/'first', Path(td)/'second'
            (first/'deep').mkdir(parents=True)
            report = write_report(second)
            old = search([first, second], max_directories=1)
            self.assertEqual(old['matches'], [])
            self.assertTrue(old['limit_reached'])
            new = search_fair([first, second], directories_per_root=1)
            self.assertEqual(new['matches'][0]['report'], str(report))
            self.assertEqual(new['root_summaries'][0]['limit_reason'], 'DIRECTORIES_PER_ROOT')
            self.assertEqual(new['root_summaries'][1]['directories_scanned'], 1)

    def test_breadth_first_does_not_sink_into_library_before_sibling(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td)/'aaa_library'/'aaa_nested'/'aaa_deep').mkdir(parents=True)
            report = write_report(td, 'zzz_result/baseline-performance.json')
            result = search_fair([td], directories_per_root=3)
            self.assertEqual(result['matches'][0]['report'], str(report))
            self.assertEqual(result['root_summaries'][0]['max_depth_scanned'], 1)

    def test_known_run_prioritized_within_same_depth(self):
        with tempfile.TemporaryDirectory() as td:
            for i in range(30):
                (Path(td)/f'aaa_{i:02d}').mkdir()
            report = write_report(td, RUN_NAME+'/baseline-performance.json')
            result = search_fair([td], directories_per_root=2)
            self.assertEqual(result['matches'][0]['report'], str(report))
            self.assertIn(str(report.parent), result['run_directory_leads'])

    def test_missing_root_does_not_stop_later_root(self):
        with tempfile.TemporaryDirectory() as td:
            report = write_report(td)
            result = search_fair([Path(td)/'missing', td])
            self.assertEqual(result['root_summaries'][0]['status'], 'ROOT_UNAVAILABLE')
            self.assertEqual(result['matches'][0]['report'], str(report))

    def test_duplicate_roots_visible_and_reports_deduplicated(self):
        with tempfile.TemporaryDirectory() as td:
            write_report(td)
            result = search_fair([td, td])
            self.assertEqual(len(result['matches']), 1)
            self.assertEqual(result['root_summaries'][1]['status'], 'DUPLICATE_RESOLVED_ROOT')

    def test_depth_limit_visible(self):
        with tempfile.TemporaryDirectory() as td:
            write_report(td, 'one/two/baseline-performance.json')
            result = search_fair([td], max_depth=0)
            self.assertEqual(result['matches'], [])
            self.assertEqual(result['root_summaries'][0]['depth_cutoffs'], 1)

    def test_symlink_cycle_and_broken_link_are_leads_not_followed(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p/'m9-cycle').symlink_to(p, target_is_directory=True)
            (p/'m9-broken').symlink_to(p/'missing', target_is_directory=True)
            result = search_fair([td])
            self.assertEqual(result['directories_scanned'], 1)
            self.assertEqual(len(result['symlink_leads']), 2)
            self.assertEqual(result['root_summaries'][0]['symlinks_not_followed'], 2)

    def test_explicit_symlink_root_is_resolved_without_recursive_links(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            report = write_report(p/'storage')
            (p/'alias').symlink_to(p/'storage', target_is_directory=True)
            result = search_fair([p/'alias'])
            self.assertEqual(result['matches'][0]['report'], str(report))

    def test_original_path_status_does_not_create_missing_path(self):
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td)/RUN_NAME
            result = search_fair([td], known_run=missing)
            self.assertEqual(result['known_run_status']['status'], 'UNRESOLVED')
            self.assertFalse(missing.exists())

    def test_wrong_schema_still_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            doc = fixture(); doc['schema'] = 'w1-m5-native-h8-instrumented-sample-v1'
            write_report(td, doc=doc)
            result = search_fair([td])
            self.assertEqual(result['matches'], [])
            self.assertEqual(result['rejected_reports'][0]['reasons'], ['WRONG_SCHEMA'])

    def test_unicode_backup_and_report_digest_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            report = write_report(td, '\u5907\u4efd\u5b9e\u9a8c/m9-baseline-performance.json')
            raw = report.read_bytes(); timestamp = report.stat().st_mtime_ns
            result = search_fair([td])
            match = result['matches'][0]
            self.assertFalse(match['runner_filename_compatible'])
            self.assertEqual(match['sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(report.read_bytes(), raw)
            self.assertEqual(report.stat().st_mtime_ns, timestamp)
            self.assertEqual(result['files_mutated'], 0)

    def test_w1_archive_name_is_lead_but_not_extracted(self):
        with tempfile.TemporaryDirectory() as td:
            archive = Path(td)/'W1-evidence-backup.tar.gz'
            archive.write_bytes(b'invalid archive intentionally')
            result = search_fair([td])
            self.assertEqual(result['archive_candidates_not_opened'], [str(archive)])
            self.assertEqual(result['io_errors'], [])
            self.assertEqual(list(Path(td).iterdir()), [archive])

    def test_entry_limit_is_reported(self):
        with tempfile.TemporaryDirectory() as td:
            for name in ('a', 'b', 'c'):
                (Path(td)/name).write_text('x')
            result = search_fair([td], entries_per_directory=1)
            self.assertTrue(result['limit_reached'])
            self.assertEqual(result['root_summaries'][0]['directory_entry_cutoffs'], 1)

    def test_time_budget_is_restarted_for_every_root(self):
        with tempfile.TemporaryDirectory() as td:
            roots = [Path(td)/'a', Path(td)/'b']
            for root in roots: root.mkdir()
            # Each root times out before its first scan; both must be attempted.
            with patch('m29_locate_m9_baseline_fair.time.monotonic', side_effect=range(100)):
                result = search_fair(roots, seconds_per_root=0.1)
            self.assertEqual(len(result['roots']), 2)
            self.assertTrue(all(x['limit_reason']=='SECONDS_PER_ROOT' for x in result['root_summaries']))

    def test_pruned_directory_is_reported_and_not_read(self):
        with tempfile.TemporaryDirectory() as td:
            write_report(td, '.cache/baseline-performance.json')
            result = search_fair([td])
            self.assertEqual(result['matches'], [])
            self.assertEqual(result['root_summaries'][0]['skipped_named_directories'], 1)

    def test_fifo_report_is_not_opened(self):
        import os
        with tempfile.TemporaryDirectory() as td:
            os.mkfifo(Path(td)/'baseline-performance.json')
            result = search_fair([td])
            self.assertEqual(result['report_files_checked'], 0)

    def test_invalid_search_budget_fails(self):
        for kwargs in ({'seconds_per_root': float('nan')}, {'directories_per_root': 0},
                       {'max_depth': -1}, {'entries_per_directory': 0}):
            with self.assertRaises(ValueError): search_fair([], **kwargs)


if __name__ == '__main__':
    unittest.main()
