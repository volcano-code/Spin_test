"""Stage14: real multiprocess promotion race and crash-recovery guards.

Every material in this test is a storage fixture, never a new Cherchi call.
An optional sample59 test uses genuine H8f historical material as a fixture.
"""
from __future__ import annotations

import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile

SOURCE = Path(__file__).resolve().parents[1] / 'source'
sys.path.insert(0, str(SOURCE))
import h9_same_call_capture as cap

ZIP = os.environ.get('H9_EVIDENCE_ZIP')
BACKEND = 'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:inprocess'


def new_capture(root, index=0, material=None, q=None, backend=BACKEND):
    if q is None:
        q = [float(i) for i in range(10)]
    if material is None:
        material = {'quadric_coefficients':q, 'boolean_backend_identity':backend,
                    'material_proof':{'schema':'cherchi-same-call-material-v1'},
                    'variable_faces':[[0,1,2]]}
    return cap.capture_same_call(root,index=index,side=cap.SIDES[index],
                                 coefficients=q,material=material,backend_identity=backend)


def metadata(proof):
    return {'index':proof['index'],'side':proof['side'],'q':proof['coefficients'],
            'material_sha256':proof['archive_sha256'],'native_geometry_valid':True,
            'newton_admitted':False}


PROMOTE_WORKER = r'''
import json,sys,time,os
from pathlib import Path
sys.path.insert(0,sys.argv[1]); import h9_same_call_capture as cp
root=Path(sys.argv[2]); actor=sys.argv[3]
proof=json.loads((root/'seed-proof.json').read_text())
meta={'index':0,'side':'left-coarse','q':proof['coefficients'],
      'material_sha256':proof['archive_sha256'],'native_geometry_valid':True,'newton_admitted':False}
if actor=='A':
    real=cp._atomic_write_json
    def pause_metadata(path,document):
        if Path(path).name=='side-00-left-coarse.json':
            (root/'A_READY').write_text('linked')
            deadline=time.monotonic()+12
            while not (root/'RELEASE_A').exists() and time.monotonic()<deadline:
                time.sleep(.005)
        return real(path,document)
    cp._atomic_write_json=pause_metadata
try:
    cp.promote_after_full_audit(root,proof,meta)
    state={'who':actor,'outcome':'SUCCESS'}
except BaseException as exc:
    state={'who':actor,'outcome':'REJECTED','reason':str(exc)}
(root/('result_'+actor+'.json')).write_text(json.dumps(state))
'''


class Stage14PromotionLeaseTests(unittest.TestCase):
    def test_two_actual_processes_cannot_delete_successful_promotion(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);proof=new_capture(root)
            (root/'seed-proof.json').write_text(json.dumps(proof))
            procs=[]
            try:
                a=subprocess.Popen([sys.executable,'-c',PROMOTE_WORKER,str(SOURCE),str(root),'A'])
                procs.append(a)
                for _ in range(1200):
                    if (root/'A_READY').exists():break
                    time.sleep(.004)
                self.assertTrue((root/'A_READY').is_file(),'first process did not publish preliminary link')
                b=subprocess.Popen([sys.executable,'-c',PROMOTE_WORKER,str(SOURCE),str(root),'B'])
                procs.append(b)
                time.sleep(.18)
                self.assertIsNone(b.poll(), 'second process must block until first releases promotion lease')
                self.assertFalse((root/'result_B.json').exists())
                (root/'RELEASE_A').write_text('go')
                for proc in procs:
                    proc.wait(timeout=8)
                    self.assertEqual(proc.returncode,0)
                states=[json.loads((root/f'result_{who}.json').read_text()) for who in ('A','B')]
                self.assertEqual([x['outcome'] for x in states],['SUCCESS','REJECTED'])
                self.assertIn('VALIDATED_NATIVE_PACKET_ALREADY_PRESENT',states[1]['reason'])
                final=root/'side-00-left-coarse.json.gz'
                recorded=root/'side-00-left-coarse.json'
                self.assertTrue(final.is_file())
                self.assertTrue(recorded.is_file())
                self.assertEqual(cap.digest(final),proof['archive_sha256'])
                self.assertEqual(json.loads(recorded.read_text()),metadata(proof))
                self.assertFalse(json.loads(recorded.read_text())['newton_admitted'])
                self.assertTrue((root/'.h9-promotion-00-left-coarse.lock').is_file())
            finally:
                for proc in procs:
                    if proc.poll() is None:
                        proc.kill();proc.wait(timeout=5)

    def test_crashed_lock_owner_does_not_poison_next_promotion(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);proof=new_capture(root)
            script='''import os,sys
sys.path.insert(0,sys.argv[1]);import h9_same_call_capture as cp
from pathlib import Path
with cp._exclusive_promotion_lease(Path(sys.argv[2]), '00-left-coarse'):
    os._exit(83)
'''
            result=subprocess.run([sys.executable,'-c',script,str(SOURCE),str(root)],timeout=8)
            self.assertEqual(result.returncode,83)
            output=cap.promote_after_full_audit(root,proof,metadata(proof))
            self.assertFalse(output['newton_admitted'])
            self.assertTrue((root/'side-00-left-coarse.json.gz').is_file())

    def test_existing_lock_is_not_unlinked_on_success_or_failure(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);proof=new_capture(root)
            cap.promote_after_full_audit(root,proof,metadata(proof))
            lock=root/'.h9-promotion-00-left-coarse.lock'
            first=lock.stat().st_ino
            with self.assertRaisesRegex(cap.CaptureRejected,'VALIDATED_NATIVE_PACKET_ALREADY_PRESENT'):
                cap.promote_after_full_audit(root,proof,metadata(proof))
            self.assertEqual(lock.stat().st_ino,first)
            self.assertTrue((root/'side-00-left-coarse.json.gz').is_file())

    def test_lease_symlink_is_rejected_without_touching_forensic_files(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);proof=new_capture(root)
            evil=root/'foreign';evil.write_text('foreign')
            lock=root/'.h9-promotion-00-left-coarse.lock';lock.symlink_to(evil)
            with self.assertRaises((OSError,cap.CaptureRejected)):
                cap.promote_after_full_audit(root,proof,metadata(proof))
            self.assertEqual(evil.read_text(),'foreign')
            self.assertTrue((root/'unverified-00-left-coarse.json.gz').is_file())
            self.assertFalse((root/'side-00-left-coarse.json.gz').exists())

    def test_directory_lease_is_rejected_without_qualified_output(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);proof=new_capture(root)
            (root/'.h9-promotion-00-left-coarse.lock').mkdir()
            with self.assertRaises((OSError,cap.CaptureRejected)):
                cap.promote_after_full_audit(root,proof,metadata(proof))
            self.assertFalse((root/'side-00-left-coarse.json').exists())

    def test_four_sides_keep_distinct_lock_inodes(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work)
            locks=[]
            for i in range(4):
                proof=new_capture(root,index=i)
                cap.promote_after_full_audit(root,proof,metadata(proof))
                lock=root/f'.h9-promotion-{i:02d}-{cap.SIDES[i]}.lock'
                locks.append(lock.stat().st_ino)
            self.assertEqual(len(set(locks)),4)
            self.assertEqual(len(list(root.glob('side-*.json.gz'))),4)

    @unittest.skipUnless(ZIP,'requires the immutable original H8f archive')
    def test_real_archived_sample59_is_unchanged_by_lease_promotion(self):
        with zipfile.ZipFile(ZIP) as z:
            stem='artifacts/h8f-all81-points/point-059'
            observed=json.loads(z.read(stem+'.json'))
            material=json.loads(gzip.decompress(z.read(stem+'-material.json.gz')))
        with tempfile.TemporaryDirectory() as work:
            root=Path(work)
            proof=new_capture(root,material=material,q=observed['coefficients'],
                              backend=observed['native_boolean_backend'])
            cp=cap.promote_after_full_audit(root,proof,metadata(proof))
            actual=json.loads(gzip.decompress(Path(cp['archive']).read_bytes()))
            self.assertEqual(material,actual)
            self.assertEqual(cap.digest(cp['archive']),proof['archive_sha256'])
            self.assertFalse(cp['newton_admitted'])


if __name__=='__main__':unittest.main()
