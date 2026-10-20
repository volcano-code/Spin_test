"""W3 Stage13: actual filesystem fault tests, NOT real new Cherchi evaluations.

The archived-H8f regression checks true pinned material bytes. Other fixtures
exercise atomic publication and are never eligible to count as native samples.
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
import h9_same_call_capture as capture

ZIP = os.environ.get('H9_EVIDENCE_ZIP')
BACKEND = 'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:inprocess'


def fixture():
    q = [float(i) for i in range(10)]
    material = {'quadric_coefficients': q, 'boolean_backend_identity': BACKEND,
                'material_proof': {'schema': 'cherchi-same-call-material-v1'},
                'variable_faces': [[0, 1, 2]],
                'variable_rational_vertices': [['1/1']*3 for _ in range(3)]}
    return q, material


def new_checkpoint(folder, *, material=None, q=None, backend=None):
    default_q, default_material = fixture()
    return capture.capture_same_call(folder,index=0,side='left-coarse',
             coefficients=default_q if q is None else q,
             material=default_material if material is None else material,
             backend_identity=BACKEND if backend is None else backend)


def meta(proof):
    return {'index': 0, 'side': 'left-coarse', 'q': proof['coefficients'],
            'native_geometry_valid': True, 'material_sha256': proof['archive_sha256'],
            'newton_admitted': False}


class ExclusiveDurabilityTest(unittest.TestCase):
    def test_exclusive_json_writer_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'proof.json'
            capture._atomic_write_json(target, {'original': 7})
            before = target.read_bytes()
            with self.assertRaisesRegex(FileExistsError,'ALREADY_EXISTS'):
                capture._atomic_write_json(target, {'forged': 99})
            self.assertEqual(target.read_bytes(), before)
            self.assertFalse(list(Path(directory).glob('.*.tmp')))

    def test_concurrent_raw_destination_creation_cannot_be_clobbered(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); raw=root/'unverified-00-left-coarse.json.gz'
            original_link=os.link
            def racing_link(source, dest, *args, **kwargs):
                if Path(dest)==raw:
                    raw.write_bytes(b'foreign capture')
                return original_link(source,dest,*args,**kwargs)
            with patch.object(capture.os,'link',side_effect=racing_link):
                with self.assertRaises(FileExistsError):
                    new_checkpoint(root)
            self.assertEqual(raw.read_bytes(),b'foreign capture')
            self.assertFalse((root/'unverified-00-left-coarse.json').exists())
            self.assertFalse(list(root.glob('.capture-*')))

    def test_broken_symlink_capture_name_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            target=root/'unverified-00-left-coarse.json.gz'
            target.symlink_to(root/'not-present')
            with self.assertRaisesRegex(capture.CaptureRejected,'ALREADY_EXISTS'):
                new_checkpoint(root)
            self.assertTrue(target.is_symlink())
            self.assertFalse((root/'unverified-00-left-coarse.json').exists())

    def test_unverified_capture_and_final_pair_are_directory_synced(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            original_sync=capture._sync_directory
            calls=[]
            def check(folder):
                calls.append(str(folder))
                original_sync(folder)
            with patch.object(capture,'_sync_directory',side_effect=check):
                proof=new_checkpoint(root)
                capture.promote_after_full_audit(root,proof,meta(proof))
            self.assertGreaterEqual(len(calls),5)
            self.assertEqual(set(calls),{str(root)})
            self.assertTrue((root/'side-00-left-coarse.json.gz').is_file())
            self.assertTrue((root/'side-00-left-coarse.json').is_file())

    def test_crash_between_raw_link_and_manifest_leaves_unverified_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            script='''\
import os,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import h9_same_call_capture as cap
q=[float(i) for i in range(10)]
backend='cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:inprocess'
material={'quadric_coefficients':q,'boolean_backend_identity':backend,
'material_proof':{'schema':'cherchi-same-call-material-v1'}}
cap._atomic_write_json=lambda *_args,**_kwargs:os._exit(79)
cap.capture_same_call(Path(sys.argv[2]),index=0,side='left-coarse',
    coefficients=q,material=material,backend_identity=backend)
'''
            run=subprocess.run([sys.executable,'-c',script,str(SOURCE),str(root)],
                                capture_output=True,timeout=15)
            self.assertEqual(run.returncode,79)
            orphan=root/'unverified-00-left-coarse.json.gz'
            self.assertTrue(orphan.is_file())
            self.assertFalse((root/'unverified-00-left-coarse.json').exists())
            self.assertFalse((root/'side-00-left-coarse.json').exists())
            self.assertEqual(gzip.decompress(orphan.read_bytes())[:1],b'{')
            with self.assertRaisesRegex(capture.CaptureRejected,'ALREADY_EXISTS'):
                new_checkpoint(root)

    def test_competing_metadata_race_preserves_foreign_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            proof=new_checkpoint(root)
            target=root/'side-00-left-coarse.json'
            link=os.link
            def injected(source,dest,*a,**k):
                if Path(dest)==target:
                    target.write_text('rival-owner',encoding='utf8')
                return link(source,dest,*a,**k)
            with patch.object(capture.os,'link',side_effect=injected):
                with self.assertRaises(FileExistsError):
                    capture.promote_after_full_audit(root,proof,meta(proof))
            self.assertEqual(target.read_text(), 'rival-owner')
            self.assertFalse((root/'side-00-left-coarse.json.gz').exists())
            self.assertEqual(capture.digest(root/'unverified-00-left-coarse.json.gz'),proof['archive_sha256'])

    def test_mutated_linked_archive_rejected_before_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            proof=new_checkpoint(root)
            dest=root/'side-00-left-coarse.json.gz'
            link=os.link
            def mutate_after_link(source,target,*a,**k):
                result=link(source,target,*a,**k)
                if Path(target)==dest:
                    # Deliberately corrupt the *same inode*, emulating an
                    # external write between precheck and metadata commit.
                    with open(source,'ab') as f:
                        f.write(b'corrupted')
                return result
            with patch.object(capture.os,'link',side_effect=mutate_after_link):
                with self.assertRaisesRegex(capture.CaptureRejected,'GZIP_BYTES_CHANGED'):
                    capture.promote_after_full_audit(root,proof,meta(proof))
            self.assertFalse(dest.exists())
            self.assertFalse((root/'side-00-left-coarse.json').exists())
            self.assertTrue((root/'unverified-00-left-coarse.json.gz').exists())

    def test_sync_failure_on_cleanup_does_not_false_fail_valid_side(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            proof=new_checkpoint(root)
            sync=capture._sync_directory
            count=0
            def last_sync_error(folder):
                nonlocal count
                count+=1
                if count==3:
                    raise OSError('cleanup only')
                return sync(folder)
            # Promotion: 1 = metadata fsync, 2 = committed pair fsync,
            # 3 = optional unverified cleanup fsync.
            with patch.object(capture,'_sync_directory',side_effect=last_sync_error):
                result=capture.promote_after_full_audit(root,proof,meta(proof))
            self.assertTrue(result['forensic_cleanup_incomplete'])
            self.assertIn('directory_sync:OSError',result['forensic_cleanup_errors'])
            self.assertEqual(capture.digest(root/'side-00-left-coarse.json.gz'),proof['archive_sha256'])
            self.assertEqual(json.loads((root/'side-00-left-coarse.json').read_text()),meta(proof))
            self.assertFalse(result['newton_admitted'])

    def test_two_real_processes_race_for_one_checkpoint_only_one_can_win(self):
        """Use OS processes, not only mocked collisions, to check O_EXCL behavior."""
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            gate=root/'start'
            child_script='''\
import json,sys,time
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import h9_same_call_capture as cp
folder=Path(sys.argv[2]); who=sys.argv[3]
q=[float(i) for i in range(10)]
b='cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:inprocess'
material={'quadric_coefficients':q,'boolean_backend_identity':b,
 'material_proof':{'schema':'cherchi-same-call-material-v1'},'fixture_owner':who}
for _ in range(1500):
 if (folder/'start').exists():break
 time.sleep(.002)
try:
 cp.capture_same_call(folder,index=0,side='left-coarse',
    coefficients=q,material=material,backend_identity=b)
 result={'status':'CAPTURED','owner':who}
except (ValueError,FileExistsError) as exc:
 result={'status':'BLOCKED','owner':who,'error':str(exc)}
(folder/('result-'+who+'.json')).write_text(json.dumps(result))
'''
            processes=[subprocess.Popen([sys.executable,'-c',child_script,
                 str(SOURCE),str(root),x],stdout=subprocess.PIPE,
                 stderr=subprocess.PIPE) for x in ('one','two')]
            gate.write_text('go')
            try:
                for proc in processes:
                    stdout,stderr=proc.communicate(timeout=15)
                    self.assertEqual(proc.returncode,0,stderr.decode(errors='replace'))
            finally:
                for proc in processes:
                    if proc.poll() is None:
                        proc.kill();proc.wait(timeout=5)
            results=[json.loads((root/('result-'+x+'.json')).read_text()) for x in ('one','two')]
            self.assertEqual(sorted(x['status'] for x in results),['BLOCKED','CAPTURED'])
            manifest=json.loads((root/'unverified-00-left-coarse.json').read_text())
            material=json.loads(gzip.decompress((root/'unverified-00-left-coarse.json.gz').read_bytes()))
            self.assertEqual(capture.digest(root/'unverified-00-left-coarse.json.gz'),manifest['archive_sha256'])
            self.assertEqual(material['fixture_owner'],next(x['owner'] for x in results if x['status']=='CAPTURED'))
            self.assertFalse((root/'side-00-left-coarse.json').exists())

    @unittest.skipUnless(ZIP,'requires original 81-point H8f artifact')
    def test_real_archived_material_exclusive_capture_round_trip(self):
        with zipfile.ZipFile(ZIP) as z:
            name='artifacts/h8f-all81-points/point-059'
            point=json.loads(z.read(name+'.json'))
            original=z.read(name+'-material.json.gz')
            self.assertEqual(sha256(original).hexdigest(),point['exact_same_call_material_archive_sha256'])
            material=json.loads(gzip.decompress(original))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            proof=new_checkpoint(root,material=material,q=point['coefficients'],backend=point['native_boolean_backend'])
            self.assertEqual(proof['archive_sha256'],capture.digest(root/'unverified-00-left-coarse.json.gz'))
            self.assertEqual(json.loads(gzip.decompress((root/'unverified-00-left-coarse.json.gz').read_bytes())),material)
            output=capture.promote_after_full_audit(root,proof,meta(proof))
            self.assertEqual(output['material_sha256'],capture.digest(root/'side-00-left-coarse.json.gz'))
            self.assertFalse(output['newton_admitted'])


if __name__=='__main__':
    unittest.main()
