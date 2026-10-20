"""W3 H9 stage 12: crash-safe checkpoint upgrade, no Cherchi simulation claims.

The mini-packets here exercise filesystem transitions ONLY. A real H8f sample
is also used to verify rollback retains genuine, SHA-pinned historical bytes.
There are zero NEW native Boolean evaluations in these tests.
"""
from __future__ import annotations

import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SOURCE = Path(__file__).resolve().parents[1] / 'source'
sys.path.insert(0, str(SOURCE))
import h9_same_call_capture as cp

ARTIFACT = os.environ.get('H9_EVIDENCE_ZIP')


def fixture():
    q = [float(n) for n in range(10)]
    backend = 'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:inprocess'
    material = {'quadric_coefficients': q, 'boolean_backend_identity': backend,
                'material_proof': {'schema': 'cherchi-same-call-material-v1'},
                'variable_faces': [[0, 1, 2]],
                'variable_rational_vertices': [['1/1']*3 for _ in range(3)]}
    return q,backend,material


def checkpoint(folder, material=None, q=None, backend=None):
    fq,fb,fm = fixture()
    return cp.capture_same_call(folder,index=0,side='left-coarse',
            coefficients=q or fq,backend_identity=backend or fb,material=material or fm)


def metadata(proof):
    return {'index':0,'side':'left-coarse','q':proof['coefficients'],
            'native_geometry_valid':True,'material_sha256':proof['archive_sha256'],
            'newton_admitted':False}


class Stage12ForensicCommitTests(unittest.TestCase):
    def test_normal_promotion_has_one_final_copy_and_sha_stability(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); proof=checkpoint(root); old=(root/'unverified-00-left-coarse.json.gz').read_bytes()
            result=cp.promote_after_full_audit(root,proof,metadata(proof))
            completed=root/'side-00-left-coarse.json.gz'
            self.assertEqual(completed.read_bytes(),old)
            self.assertEqual(sha256(old).hexdigest(),result['material_sha256'])
            self.assertEqual(json.loads((root/'side-00-left-coarse.json').read_text()),metadata(proof))
            self.assertFalse(result['forensic_cleanup_incomplete'])
            self.assertFalse((root/'unverified-00-left-coarse.json.gz').exists())
            self.assertFalse((root/'unverified-00-left-coarse.json').exists())
            self.assertFalse(result['newton_admitted'])

    def test_metadata_write_fails_original_checkpoint_and_sha_remain(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); proof=checkpoint(root)
            checkpoint_path=root/'unverified-00-left-coarse.json.gz'
            raw=checkpoint_path.read_bytes(); manifest=(root/'unverified-00-left-coarse.json').read_bytes()
            with patch.object(cp,'_atomic_write_json',side_effect=OSError('simulated disk full')):
                with self.assertRaisesRegex(OSError,'simulated disk full'):
                    cp.promote_after_full_audit(root,proof,metadata(proof))
            self.assertEqual(checkpoint_path.read_bytes(),raw)
            self.assertEqual((root/'unverified-00-left-coarse.json').read_bytes(),manifest)
            self.assertFalse((root/'side-00-left-coarse.json').exists())
            self.assertFalse((root/'side-00-left-coarse.json.gz').exists())
            # The owner can retry after resolving storage failure; nothing was lost.
            self.assertEqual(cp.promote_after_full_audit(root,proof,metadata(proof))['material_sha256'],sha256(raw).hexdigest())

    def test_directory_sync_failure_rolls_back_without_losing_checkpoint(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); proof=checkpoint(root)
            with patch.object(cp,'_sync_directory',side_effect=OSError('simulated fsync error')):
                with self.assertRaisesRegex(OSError,'simulated fsync error'):
                    cp.promote_after_full_audit(root,proof,metadata(proof))
            self.assertTrue((root/'unverified-00-left-coarse.json.gz').is_file())
            self.assertTrue((root/'unverified-00-left-coarse.json').is_file())
            self.assertFalse((root/'side-00-left-coarse.json').exists())
            self.assertFalse((root/'side-00-left-coarse.json.gz').exists())

    def test_failed_hard_link_creation_never_moves_original(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); proof=checkpoint(root)
            with patch.object(cp.os,'link',side_effect=PermissionError('simulated readonly fs')):
                with self.assertRaisesRegex(PermissionError,'simulated readonly fs'):
                    cp.promote_after_full_audit(root,proof,metadata(proof))
            self.assertEqual(cp.digest(root/'unverified-00-left-coarse.json.gz'),proof['archive_sha256'])
            self.assertFalse((root/'side-00-left-coarse.json.gz').exists())

    def test_actual_process_crash_before_metadata_does_not_remove_original(self):
        # A separate interpreter intentionally kills itself at the checkpoint
        # metadata commit boundary; no in-process exception simulation alone.
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); proof=checkpoint(root)
            before=(root/'unverified-00-left-coarse.json.gz').read_bytes()
            script='''\
import json,os,sys
sys.path.insert(0,sys.argv[1])
import h9_same_call_capture as cp
from pathlib import Path
root=Path(sys.argv[2])
proof=json.loads((root/'unverified-00-left-coarse.json').read_text())
meta={'index':0,'side':'left-coarse','q':proof['coefficients'],
      'native_geometry_valid':True,'material_sha256':proof['archive_sha256']}
cp._atomic_write_json=lambda *args,**kw:os._exit(83)
cp.promote_after_full_audit(root,proof,meta)
'''
            proc=subprocess.run([sys.executable,'-c',script,str(SOURCE),str(root)],
                                check=False,capture_output=True,timeout=10)
            self.assertEqual(proc.returncode,83)
            self.assertEqual((root/'unverified-00-left-coarse.json.gz').read_bytes(),before)
            self.assertEqual(json.loads((root/'unverified-00-left-coarse.json').read_text()),proof)
            self.assertFalse((root/'side-00-left-coarse.json').exists())
            # It is safe for an interrupted run to leave an orphan hard link:
            # independent auditors REQUIRE the missing side JSON and must fail.
            self.assertTrue((root/'side-00-left-coarse.json.gz').exists())
            self.assertEqual(cp.digest(root/'side-00-left-coarse.json.gz'),proof['archive_sha256'])
            # Safe restart recognizes only the same inode and now commits the
            # existing validated data without rerunning native Cherchi.
            report=cp.promote_after_full_audit(root,proof,metadata(proof))
            self.assertEqual(report['material_sha256'],proof['archive_sha256'])
            self.assertFalse((root/'unverified-00-left-coarse.json.gz').exists())
            self.assertFalse(report['newton_admitted'])

    def test_foreign_orphan_is_never_automatically_deleted_or_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); proof=checkpoint(root)
            existing=root/'side-00-left-coarse.json.gz'
            existing.write_bytes((root/'unverified-00-left-coarse.json.gz').read_bytes())
            with self.assertRaisesRegex(cp.CaptureRejected,'FOREIGN_ORPHAN_NATIVE_SIDE_PACKET'):
                cp.promote_after_full_audit(root,proof,metadata(proof))
            self.assertTrue(existing.exists())
            self.assertTrue((root/'unverified-00-left-coarse.json.gz').exists())
            self.assertFalse((root/'side-00-left-coarse.json').exists())

    @unittest.skipUnless(ARTIFACT, 'requires pinned historical H8f artifact')
    def test_real_archived_cherchi_material_survives_failed_commit(self):
        with zipfile.ZipFile(ARTIFACT) as z:
            entry='artifacts/h8f-all81-points/point-059'
            point=json.loads(z.read(entry+'.json'))
            material=json.loads(gzip.decompress(z.read(entry+'-material.json.gz')))
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);proof=checkpoint(root,material=material,q=point['coefficients'],backend=point['native_boolean_backend'])
            with patch.object(cp,'_atomic_write_json',side_effect=OSError('synthetic failure post-Cherchi')):
                with self.assertRaisesRegex(OSError,'synthetic failure post-Cherchi'):
                    cp.promote_after_full_audit(root,proof,metadata(proof))
            packet=root/'unverified-00-left-coarse.json.gz'
            self.assertEqual(cp.digest(packet),proof['archive_sha256'])
            self.assertEqual(json.loads(gzip.decompress(packet.read_bytes())),material)
            self.assertGreater(packet.stat().st_size,10000)
            self.assertFalse((root/'side-00-left-coarse.json').exists())


if __name__ == '__main__': unittest.main()
