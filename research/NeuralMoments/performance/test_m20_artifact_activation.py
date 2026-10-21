"""Real H8c Actions archive checksum / W1 inactive CI activation safety tests.

This tests a FOUND and REPAIRED deployment blocker; it is not fresh Boolean.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
WORKFLOW = HERE / 'm19-w1-real-h8e-stage-profile.workflow.template.yml'
STATUS = HERE / 'evidence/m19-runtime-status.json'
ERRATUM = HERE / 'evidence/m20-m19-h8c-sha-erratum.json'
GOOD = '78749e99abd25ab2d2571440991ffa4e907a1565b4c7faf5210496431389cdd7'
WRONG = '78749e99abd25ab2d2571440991ffa4e907a1565b4e20298f8516e061c'


def workflow_declared_h8c_checksum(text: str) -> str:
    # Fail if checksum or named artifact changes. The regex MUST NOT accept
    # a different archive or multiple competing declarations.
    matches = re.findall(r"echo '([0-9a-f]{64})  artifacts/w1-h8c-reference\.zip' \| sha256sum --check", text)
    if len(matches) != 1:
        raise ValueError('M20_ARCHIVE_CHECKSUM_GATE_MISSING_DUPLICATE_OR_CHANGED')
    return matches[0]


class TestM20H8cDeployment(unittest.TestCase):
    def test_checksum_matches_immutable_archive_authority(self):
        import m5_native_call_instrumentation as m5
        self.assertEqual(m5.ARCHIVE_SHA, GOOD)
        self.assertEqual(workflow_declared_h8c_checksum(WORKFLOW.read_text()), GOOD)
        self.assertNotIn(WRONG, WORKFLOW.read_text())

    def test_published_m19_status_and_erratum_tied_to_real_artifact(self):
        evidence = json.loads(STATUS.read_text())
        e = json.loads(ERRATUM.read_text())
        self.assertEqual(evidence['h8c_archive_sha256'], GOOD)
        self.assertEqual(e['h8c_artifact_id'], 12132634988)
        self.assertEqual(e['original_incorrect_sha256'], WRONG)
        self.assertEqual(e['independently_verified_sha256'], GOOD)
        self.assertEqual(e['actual_local_zip_sha256'], GOOD)
        self.assertIs(e['workflow_activated'], False)
        self.assertEqual(e['fresh_cherchi_boolean_runs'], 0)
        self.assertIsNone(e['production_speedup'])

    def test_tampered_or_wrong_sha_is_rejected(self):
        original = WORKFLOW.read_text()
        tampered = original.replace(GOOD, WRONG)
        with self.assertRaisesRegex(ValueError, 'M20_ARCHIVE_CHECKSUM_GATE'):
            workflow_declared_h8c_checksum(tampered)
        with self.assertRaisesRegex(ValueError, 'M20_ARCHIVE_CHECKSUM_GATE'):
            workflow_declared_h8c_checksum(original.replace('sha256sum --check', 'cat'))
        with self.assertRaisesRegex(ValueError, 'M20_ARCHIVE_CHECKSUM_GATE'):
            workflow_declared_h8c_checksum(original + "\necho '"+GOOD+"  artifacts/w1-h8c-reference.zip' | sha256sum --check\n")

    def test_checksum_before_native_build_and_no_main_or_other_branch(self):
        text = WORKFLOW.read_text()
        self.assertLess(text.index('sha256sum --check'), text.index('m13_pinned_native_build.py'))
        self.assertIn('ref: research/neuralmoments-w1-native-20261019', text)
        self.assertIn('workflow_dispatch:', text)
        self.assertNotIn('push:', text)
        self.assertIn('if: always()', text)
        self.assertIn('M19', (HERE/'M19_RESULTS.md').read_text())

    def test_authentic_replayed_github_artifact_bytes(self):
        fixture = os.environ.get('W1_M20_H8C_ARCHIVE')
        if not fixture:
            self.skipTest('Set W1_M20_H8C_ARCHIVE to actual GitHub Actions artifact')
        data = Path(fixture).read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), GOOD)
        # Corruption must be detectable, even with unchanged filenames.
        corrupt=bytearray(data); corrupt[-1]^=1
        self.assertNotEqual(hashlib.sha256(corrupt).hexdigest(), GOOD)


if __name__ == '__main__':
    unittest.main()
