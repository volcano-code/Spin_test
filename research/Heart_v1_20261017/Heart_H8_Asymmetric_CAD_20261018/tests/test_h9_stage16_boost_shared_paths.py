"""W3 H9: fail-closed shared Boost pathname handling (no native calls)."""
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))
import prepare_h9_pinned_native as build


class H9BoostSharedPathTests(unittest.TestCase):
    def exercise(self, input_text, expected=None, error=None, so_exists=None):
        if so_exists is None:
            so_exists = lambda path: True
        with tempfile.TemporaryDirectory() as folder:
            ninja = Path(folder) / 'build.ninja'
            ninja.write_text(input_text)
            actual_exists = Path.exists

            def fake_exists(path):
                if str(path).endswith('.so'):
                    return so_exists(path)
                return actual_exists(path)

            with patch.object(Path, 'exists', fake_exists):
                if error is not None:
                    with self.assertRaises(build.BuildBlocked) as caught:
                        build.boost_shared_rewrite(ninja)
                    self.assertIn(error, str(caught.exception))
                    self.assertEqual(ninja.read_text(), input_text)
                    return
                count = build.boost_shared_rewrite(ninja)
            self.assertEqual(count, expected[0])
            self.assertEqual(ninja.read_text(), expected[1])

    def test_standard_ubuntu_usr_lib(self):
        source = 'IN /usr/lib/x86_64-linux-gnu/libboost_thread.a /usr/lib/x86_64-linux-gnu/libboost_system.a'
        self.exercise(source, (2, source.replace('.a', '.so')))

    def test_ubuntu_usrmerge_lib_alias(self):
        source = 'IN /lib/x86_64-linux-gnu/libboost_thread.a /lib/x86_64-linux-gnu/libboost_system.a'
        self.exercise(source, (2, source.replace('.a', '.so')))

    def test_mixed_alias_and_preserve_unrelated_libraries(self):
        source = ('LINK_LIBRARIES = /lib/x86_64-linux-gnu/libboost_thread.a '
                  '/usr/lib/x86_64-linux-gnu/libboost_system.a '
                  '/usr/lib/libboost_filesystem.a')
        expected = (source.replace('libboost_thread.a', 'libboost_thread.so')
                          .replace('libboost_system.a', 'libboost_system.so'))
        self.exercise(source, (2, expected))

    def test_no_static_references_is_noop(self):
        self.exercise('ninja-rules = /tmp/example\n', (0, 'ninja-rules = /tmp/example\n'))

    def test_conda_archive_path_rejected_without_writing(self):
        self.exercise('IN /home/lin/anaconda3/lib/libboost_thread.a',
                      error='STATIC_BOOST_REFERENCES_REMAIN:')

    def test_missing_same_directory_shared_library_rejected(self):
        self.exercise('IN /lib/x86_64-linux-gnu/libboost_thread.a',
                      error='SHARED_BOOST_LIBRARY_NOT_INSTALLED:',
                      so_exists=lambda path: str(path).startswith('/usr/lib/'))

    def test_archive_name_containing_backup_suffix_is_not_rewritten(self):
        source = 'IN /usr/lib/x86_64-linux-gnu/libboost_thread.a.backup'
        self.exercise(source, (0, source))

    def test_unexpected_nested_absolute_prefix_rejected(self):
        self.exercise('IN /custom/usr/lib/x86_64-linux-gnu/libboost_thread.a',
                      error='STATIC_BOOST_REFERENCES_REMAIN:')

    def test_bare_archive_name_fails_closed(self):
        self.exercise('IN -l:libboost_thread.a',
                      error='STATIC_BOOST_REFERENCES_REMAIN:')


if __name__ == '__main__':
    unittest.main()
