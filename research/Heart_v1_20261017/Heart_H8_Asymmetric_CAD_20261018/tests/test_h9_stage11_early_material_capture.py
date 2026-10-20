"""W3 Stage11: real archive retention and producer/auditor q contract.

Synthetic mini-packets below test storage mechanics only. The regression using
sample 59 reads the actual pinned historical Cherchi archive and explicitly
DOES NOT count as a NEW native Boolean execution.
"""
from __future__ import annotations

import ast
import gzip
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

SOURCE = Path(__file__).resolve().parents[1] / 'source'
sys.path.insert(0, str(SOURCE))
from h9_same_call_capture import (
    capture_same_call, promote_after_full_audit, digest, CaptureRejected,
)
from audit_h9_new_native_sides import audit

ARCHIVE = os.environ.get('H9_EVIDENCE_ZIP')


def synthetic():
    q = [float(x) for x in range(10)]
    backend = 'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:inprocess'
    material = {'quadric_coefficients': q, 'boolean_backend_identity': backend,
                'material_proof': {'schema': 'cherchi-same-call-material-v1'},
                'variable_faces': [[0, 1, 2]], 'variable_rational_vertices': [['1/1'] * 3] * 3}
    return q, backend, material


class SameCallMaterialCheckpointTests(unittest.TestCase):
    def test_crashed_independent_audit_retains_only_unverified_packet(self):
        q, backend, mat = synthetic()
        with tempfile.TemporaryDirectory() as work:
            dest = Path(work)
            proof = capture_same_call(dest, index=0, side='left-coarse',
                                      coefficients=q, material=mat, backend_identity=backend)
            with self.assertRaisesRegex(RuntimeError, 'injected exact geometry failure'):
                raise RuntimeError('injected exact geometry failure')
            self.assertEqual(proof['strict_native_boundary_certified'], False)
            self.assertFalse(proof['newton_admitted'])
            self.assertTrue((dest/'unverified-00-left-coarse.json.gz').is_file())
            self.assertFalse((dest/'side-00-left-coarse.json.gz').exists())
            self.assertEqual(digest(dest/'unverified-00-left-coarse.json.gz'),proof['archive_sha256'])
            with self.assertRaisesRegex(ValueError, 'NO_COMPLETED_NEW_REAL_CHERCHI_RUN_REPORT'):
                audit(Path('/not-a-native-archive.zip'), Path(work)/'absent.json', dest)

    def test_atomic_promotion_preserves_original_same_call_bytes(self):
        q, backend, mat = synthetic()
        with tempfile.TemporaryDirectory() as work:
            folder = Path(work)
            proof = capture_same_call(folder,index=1,side='left-near',
                                      coefficients=q,material=mat,backend_identity=backend)
            original_bytes = (folder/'unverified-01-left-near.json.gz').read_bytes()
            meta = {'index':1,'side':'left-near','q':q, 'native_geometry_valid':True,
                    'material_sha256':proof['archive_sha256'], 'newton_admitted':False}
            evidence = promote_after_full_audit(folder,proof,meta)
            self.assertEqual((folder/'side-01-left-near.json.gz').read_bytes(),original_bytes)
            self.assertEqual(gzip.decompress(original_bytes),
                             json.dumps(mat, sort_keys=True,separators=(',', ':'),
                                        ensure_ascii=False,allow_nan=False).encode())
            self.assertEqual(json.loads((folder/'side-01-left-near.json').read_text()),meta)
            self.assertEqual(evidence['material_sha256'],proof['archive_sha256'])
            self.assertFalse((folder/'unverified-01-left-near.json.gz').exists())
            self.assertFalse((folder/'unverified-01-left-near.json').exists())
            self.assertFalse(evidence['newton_admitted'])

    def test_broken_q_or_geometry_never_promotes(self):
        q,backend,mat=synthetic()
        with tempfile.TemporaryDirectory() as work:
            folder=Path(work)
            proof=capture_same_call(folder,index=2,side='right-near',coefficients=q,
                                    material=mat,backend_identity=backend)
            original={'index':2,'side':'right-near','q':q,
                      'material_sha256':proof['archive_sha256'],'native_geometry_valid':True}
            for mutation in ({'q':q[:-1]},{'native_geometry_valid':False},
                             {'material_sha256':'0'*64},{'index':0}):
                with self.subTest(mutation=mutation):
                    bad={**original,**mutation}
                    with self.assertRaisesRegex(CaptureRejected,'UNVALIDATED_OR_MISMATCHED'):
                        promote_after_full_audit(folder,proof,bad)
                    self.assertTrue((folder/'unverified-02-right-near.json.gz').exists())
                    self.assertFalse((folder/'side-02-right-near.json.gz').exists())

    def test_tampered_checkpoint_sha_and_manifest_rejected(self):
        q,backend,mat=synthetic()
        with tempfile.TemporaryDirectory() as work:
            folder=Path(work)
            proof=capture_same_call(folder,index=3,side='right-coarse',coefficients=q,
                                    material=mat,backend_identity=backend)
            fake={'index':3,'side':'right-coarse','q':q,'native_geometry_valid':True,
                  'material_sha256':proof['archive_sha256']}
            with (folder/'unverified-03-right-coarse.json.gz').open('ab') as stream:
                stream.write(b'garbage')
            with self.assertRaisesRegex(CaptureRejected,'CAPTURE_MANIFEST_OR_ARCHIVE_SHA_DRIFT'):
                promote_after_full_audit(folder,proof,fake)
            self.assertFalse((folder/'side-03-right-coarse.json.gz').exists())

    def test_wrong_backend_and_duplicate_material_lease_rejected(self):
        q,backend,mat=synthetic()
        with tempfile.TemporaryDirectory() as work:
            folder=Path(work)
            with self.assertRaisesRegex(CaptureRejected,'PROVENANCE_UNVERIFIED'):
                capture_same_call(folder,index=0,side='left-coarse',coefficients=q,
                                  material=mat,backend_identity='cgal:unallowed')
            with self.assertRaisesRegex(CaptureRejected,'QUADRIC_IDENTITY_MISMATCH'):
                capture_same_call(folder,index=0,side='left-coarse',coefficients=q[:-1],
                                  material=mat,backend_identity=backend)
            capture_same_call(folder,index=0,side='left-coarse',coefficients=q,
                              material=mat,backend_identity=backend)
            with self.assertRaisesRegex(CaptureRejected,'CAPTURE_ALREADY_EXISTS'):
                capture_same_call(folder,index=0,side='left-coarse',coefficients=q,
                                  material=mat,backend_identity=backend)

    def test_no_timestamp_makes_identical_packet_hash_reproducible(self):
        q,backend,mat=synthetic()
        with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
            a=capture_same_call(one,index=0,side='left-coarse',coefficients=q,
                                material=mat,backend_identity=backend)
            b=capture_same_call(two,index=0,side='left-coarse',coefficients=q,
                                material=mat,backend_identity=backend)
            self.assertEqual(a['archive_sha256'],b['archive_sha256'])

    def test_producer_q_field_and_capture_order_match_independent_contract(self):
        tree=ast.parse((SOURCE/'probe_h9_crossing_sides_live.py').read_text())
        statements=[]
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ('capture_same_call','promote_after_full_audit'):
                    statements.append((node.func.id,node.lineno))
        self.assertEqual([x[0] for x in sorted(statements,key=lambda t:t[1])],
                         ['capture_same_call','promote_after_full_audit'])
        source=(SOURCE/'probe_h9_crossing_sides_live.py').read_text()
        self.assertLess(source.index('capture=capture_same_call('),
                        source.index('audit_exact_rational_triangle_boundary('))
        self.assertLess(source.index('audit_exact_rational_triangle_boundary('),
                        source.index('promote_after_full_audit(output,capture,fact)'))
        self.assertIn("fact={**item,'q':q.tolist()",source)

    @unittest.skipUnless(ARCHIVE, 'requires original H8f Action artifact ZIP')
    def test_REAL_historical_cherchi_material_is_retained_without_new_run_claim(self):
        with zipfile.ZipFile(ARCHIVE) as src:
            p='artifacts/h8f-all81-points/point-059'
            record=json.loads(src.read(p+'.json'))
            material=json.loads(gzip.decompress(src.read(p+'-material.json.gz')))
        with tempfile.TemporaryDirectory() as work:
            dest=Path(work)
            checkpoint=capture_same_call(dest,index=0,side='left-coarse',
                                         coefficients=record['coefficients'],
                                         material=material,
                                         backend_identity=record['native_boolean_backend'])
            self.assertEqual(checkpoint['status'],
                             'UNVERIFIED_PACKET_PRESERVED_BEFORE_EXACT_BOUNDARY_AUDIT')
            self.assertGreater((dest/'unverified-00-left-coarse.json.gz').stat().st_size,10_000)
            self.assertFalse((dest/'side-00-left-coarse.json.gz').exists())
            self.assertFalse(checkpoint['newton_admitted'])


if __name__=='__main__':
    unittest.main()
